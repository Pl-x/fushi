"""
Tests for database models
"""
import pytest
from datetime import datetime
from src.app.models import Payment, Transfer, Refund, User, customer, merchant


class TestPaymentModel:
    """Test Payment model"""
    
    def test_create_payment(self, db_session):
        """Test creating a payment record"""
        payment = Payment(
            email='test@example.com',
            phone_number='254712345678',
            amount=10000,
            currency='KES',
            status='PENDING',
            payment_provider='PAYSTACK',
            account_reference='TEST-001',
            transaction_desc='Test payment'
        )
        
        db_session.session.add(payment)
        db_session.session.commit()
        
        assert payment.id is not None
        assert payment.email == 'test@example.com'
        assert payment.amount == 10000
        assert payment.currency == 'KES'
        assert payment.status == 'PENDING'
    
    def test_payment_with_idempotency_key(self, db_session):
        """Test payment with idempotency key"""
        payment = Payment(
            email='test@example.com',
            amount=10000,
            currency='KES',
            payment_provider='PAYSTACK',
            account_reference='TEST-002',
            transaction_desc='Test',
            idempotency_key='test-idem-key-001'
        )
        
        db_session.session.add(payment)
        db_session.session.commit()
        
        assert payment.idempotency_key == 'test-idem-key-001'
    
    def test_duplicate_idempotency_key(self, db_session):
        """Test that duplicate idempotency keys are not allowed"""
        payment1 = Payment(
            email='test1@example.com',
            amount=10000,
            currency='KES',
            payment_provider='PAYSTACK',
            account_reference='TEST-003',
            transaction_desc='Test 1',
            idempotency_key='duplicate-key'
        )
        
        payment2 = Payment(
            email='test2@example.com',
            amount=20000,
            currency='KES',
            payment_provider='PAYSTACK',
            account_reference='TEST-004',
            transaction_desc='Test 2',
            idempotency_key='duplicate-key'
        )
        
        db_session.session.add(payment1)
        db_session.session.commit()
        
        db_session.session.add(payment2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.session.commit()
    
    def test_payment_to_dict(self, sample_payment):
        """Test payment to_dict method"""
        payment_dict = sample_payment.to_dict()
        
        assert 'id' in payment_dict
        assert 'email' in payment_dict
        assert 'amount' in payment_dict
        assert 'currency' in payment_dict
        assert 'status' in payment_dict
        assert payment_dict['email'] == 'customer@example.com'
        assert payment_dict['amount'] == 10000
    
    def test_payment_timestamps(self, db_session):
        """Test automatic timestamp creation"""
        payment = Payment(
            email='test@example.com',
            amount=10000,
            currency='KES',
            payment_provider='PAYSTACK',
            account_reference='TEST-005',
            transaction_desc='Test'
        )
        
        db_session.session.add(payment)
        db_session.session.commit()
        
        assert payment.created_at is not None
        assert payment.updated_at is not None
        assert isinstance(payment.created_at, datetime)


class TestTransferModel:
    """Test Transfer model"""
    
    def test_create_transfer(self, db_session):
        """Test creating a transfer record"""
        transfer = Transfer(
            recipient_type='mobile_money',
            account_number='254712345678',
            account_name='John Doe',
            amount=5000,
            currency='KES',
            reason='Test transfer',
            reference='TRF-TEST-001'
        )
        
        db_session.session.add(transfer)
        db_session.session.commit()
        
        assert transfer.id is not None
        assert transfer.amount == 5000
        assert transfer.status == 'PENDING'
    
    def test_transfer_with_idempotency_key(self, db_session):
        """Test transfer with idempotency key"""
        transfer = Transfer(
            recipient_type='mobile_money',
            account_number='254712345678',
            account_name='John Doe',
            amount=5000,
            currency='KES',
            reason='Test',
            reference='TRF-TEST-002',
            idempotency_key='transfer-idem-001'
        )
        
        db_session.session.add(transfer)
        db_session.session.commit()
        
        assert transfer.idempotency_key == 'transfer-idem-001'
    
    def test_transfer_to_dict(self, sample_transfer):
        """Test transfer to_dict method"""
        transfer_dict = sample_transfer.to_dict()
        
        assert 'id' in transfer_dict
        assert 'amount' in transfer_dict
        assert 'reference' in transfer_dict
        assert transfer_dict['amount'] == 5000


class TestRefundModel:
    """Test Refund model"""
    
    def test_create_refund(self, db_session, successful_payment):
        """Test creating a refund record"""
        refund = Refund(
            payment_id=successful_payment.id,
            transaction_reference=successful_payment.paystack_reference,
            amount=10000,
            currency='KES',
            merchant_note='Test refund',
            customer_note='Refund processed'
        )
        
        db_session.session.add(refund)
        db_session.session.commit()
        
        assert refund.id is not None
        assert refund.payment_id == successful_payment.id
        assert refund.status == 'PENDING'
    
    def test_refund_relationship(self, db_session, successful_payment):
        """Test refund-payment relationship"""
        refund = Refund(
            payment_id=successful_payment.id,
            transaction_reference=successful_payment.paystack_reference,
            amount=5000,
            currency='KES'
        )
        
        db_session.session.add(refund)
        db_session.session.commit()
        
        assert refund.payment == successful_payment
        assert refund in successful_payment.refunds


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, db_session):
        """Test creating a user"""
        from src.app.routes.AAA import hash_password
        
        user = User(
            email='newuser@example.com',
            password_hash=hash_password('password123'),
            name='New User',
            phone_number='254712345678'
        )
        
        db_session.session.add(user)
        db_session.session.commit()
        
        assert user.id is not None
        assert user.email == 'newuser@example.com'
        assert user.is_active is True
    
    def test_user_to_dict(self, sample_user):
        """Test user to_dict method"""
        user_dict = sample_user.to_dict()
        
        assert 'id' in user_dict
        assert 'email' in user_dict
        assert 'name' in user_dict
        assert 'password_hash' not in user_dict  # Should not expose password
    
    def test_unique_email(self, db_session, sample_user):
        """Test that email must be unique"""
        user2 = User(
            email='test@example.com',  # Same as sample_user
            password_hash='hashed',
            name='Another User'
        )
        
        db_session.session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.session.commit()
