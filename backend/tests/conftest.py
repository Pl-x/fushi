"""
Pytest configuration and fixtures
"""
import os
import pytest
from src.app.config import create_app
from src.app.extensions import db
from src.app.models import Payment, Transfer, Refund, User


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    # Set test configuration
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'True'
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # Create application context
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(autouse=True)
def authorize_legacy_financial_flow_tests(request, client, db_session):
    """Give legacy payment-flow tests an explicit database admin token.

    Production code never bypasses authorization. Dedicated guard tests keep
    exercising the unauthenticated and reviewer-denied paths.
    """
    module = request.module.__name__.rsplit('.', 1)[-1]
    if module not in {'test_b2c', 'test_c2b', 'test_integration'}:
        yield
        return

    from src.app.routes.AAA import generate_jwt_token, hash_password

    admin = User(
        email='financial-test-admin@example.com',
        password_hash=hash_password('financial-test-password'),
        name='Financial Test Admin',
        is_admin=True,
    )
    db_session.session.add(admin)
    db_session.session.commit()
    token = generate_jwt_token(admin.id, admin.email)
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    yield


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for each test"""
    with app.app_context():
        # Clear all tables
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield db
        db.session.remove()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing"""
    from src.app.routes.AAA import hash_password
    
    user = User(
        email='test@example.com',
        password_hash=hash_password('password123'),
        name='Test User',
        phone_number='+254712345678'
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def auth_token(client, sample_user):
    """Get authentication token for testing"""
    response = client.post('/api/v1/auth/signin', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    data = response.get_json()
    if data and data.get('status') == 'success':
        return data['data']['token']
    return None


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers for testing"""
    if auth_token:
        return {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    return {'Content-Type': 'application/json'}


@pytest.fixture
def sample_payment(db_session):
    """Create a sample payment for testing"""
    payment = Payment(
        email='customer@example.com',
        phone_number='254712345678',
        amount=10000,
        currency='KES',
        status='PENDING',
        payment_provider='PAYSTACK',
        account_reference='TEST-REF-001',
        transaction_desc='Test payment',
        paystack_reference='TEST-PAYSTACK-REF-001',
        paystack_access_code='test-access-code'
    )
    db_session.session.add(payment)
    db_session.session.commit()
    return payment


@pytest.fixture
def successful_payment(db_session):
    """Create a successful payment for testing refunds"""
    payment = Payment(
        email='customer@example.com',
        phone_number='254712345678',
        amount=10000,
        currency='KES',
        status='SUCCESS',
        payment_provider='PAYSTACK',
        account_reference='TEST-SUCCESS-REF',
        transaction_desc='Successful test payment',
        paystack_reference='TEST-SUCCESS-PAYSTACK-REF',
        receipt_number='TEST-RECEIPT-001'
    )
    db_session.session.add(payment)
    db_session.session.commit()
    return payment


@pytest.fixture
def sample_transfer(db_session):
    """Create a sample transfer for testing"""
    transfer = Transfer(
        recipient_type='mobile_money',
        account_number='254712345678',
        account_name='John Doe',
        amount=5000,
        currency='KES',
        reason='Test transfer',
        reference='TEST-TRANSFER-001',
        status='PENDING'
    )
    db_session.session.add(transfer)
    db_session.session.commit()
    return transfer


@pytest.fixture
def mock_paystack_success(monkeypatch):
    """Mock successful Paystack API responses"""
    class MockPaystack:
        class Transaction:
            @staticmethod
            def initialize(**kwargs):
                return {
                    'status': True,
                    'message': 'Authorization URL created',
                    'data': {
                        'authorization_url': 'https://checkout.paystack.com/test123',
                        'access_code': 'test_access_code_123',
                        'reference': kwargs.get('reference', 'TEST-REF-123')
                    }
                }
            
            @staticmethod
            def verify(reference):
                return {
                    'status': True,
                    'message': 'Verification successful',
                    'data': {
                        'status': 'success',
                        'reference': reference,
                        'amount': 10000,
                        'channel': 'mobile_money',
                        'id': 12345,
                        'authorization': {
                            'authorization_code': 'AUTH_test123'
                        }
                    }
                }
        
        class Transfer:
            @staticmethod
            def initiate(**kwargs):
                return {
                    'status': True,
                    'message': 'Transfer initiated',
                    'data': {
                        'transfer_code': 'TRF_test123',
                        'reference': kwargs.get('reference', 'TEST-TRANSFER-123')
                    }
                }
        
        class TransferRecipient:
            @staticmethod
            def create(**kwargs):
                return {
                    'status': True,
                    'message': 'Recipient created',
                    'data': {
                        'recipient_code': 'RCP_test123'
                    }
                }
        
        class Refund:
            @staticmethod
            def create(**kwargs):
                return {
                    'status': True,
                    'message': 'Refund initiated',
                    'data': {
                        'transaction': {
                            'reference': 'REFUND-TEST-123'
                        }
                    }
                }
        
        transaction = Transaction()
        transfer = Transfer()
        transfer_recipient = TransferRecipient()
        refund = Refund()
    
    return MockPaystack()


@pytest.fixture
def mock_paystack_failure(monkeypatch):
    """Mock failed Paystack API responses"""
    class MockPaystack:
        class Transaction:
            @staticmethod
            def initialize(**kwargs):
                return {
                    'status': False,
                    'message': 'Invalid parameters'
                }
            
            @staticmethod
            def verify(reference):
                return {
                    'status': True,
                    'message': 'Verification successful',
                    'data': {
                        'status': 'failed',
                        'reference': reference
                    }
                }
        
        transaction = Transaction()
    
    return MockPaystack()
