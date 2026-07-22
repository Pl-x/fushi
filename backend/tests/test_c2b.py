"""
Tests for C2B (Customer to Business) payment endpoints
"""
import pytest
from unittest.mock import patch, MagicMock
from src.app.models import Payment


class TestInitializePayment:
    """Test payment initialization endpoint"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_initialize_payment_success(self, mock_paystack, client, db_session):
        """Test successful payment initialization"""
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/test123',
                'access_code': 'test_code_123',
                'reference': 'TEST-REF-001'
            }
        }
        
        response = client.post('/api/v1/c2b/initialize', json={
            'email': 'customer@example.com',
            'phone_number': '254712345678',
            'amount': 10000,
            'currency': 'KES',
            'channels': ['mobile_money']
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'authorization_url' in data['data']
        assert 'reference' in data['data']
        
        # Check database
        payment = Payment.query.first()
        assert payment is not None
        assert payment.email == 'customer@example.com'
        assert payment.phone_number == '254712345678'
    
    def test_initialize_payment_missing_email(self, client):
        """Test initialization without email"""
        response = client.post('/api/v1/c2b/initialize', json={
            'amount': 10000
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_initialize_payment_missing_amount(self, client):
        """Test initialization without amount"""
        response = client.post('/api/v1/c2b/initialize', json={
            'email': 'customer@example.com'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    @patch('src.app.routes.C2B.paystack')
    def test_initialize_payment_with_idempotency_key(self, mock_paystack, client, db_session):
        """Test payment initialization with idempotency key"""
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/test123',
                'access_code': 'test_code_123',
                'reference': 'TEST-REF-002'
            }
        }
        
        # First request
        response1 = client.post('/api/v1/c2b/initialize',
            headers={'Idempotency-Key': 'test-idem-001'},
            json={
                'email': 'customer@example.com',
                'amount': 10000,
                'currency': 'KES'
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.get_json()
        reference1 = data1['data']['reference']
        
        # Second request with same key
        response2 = client.post('/api/v1/c2b/initialize',
            headers={'Idempotency-Key': 'test-idem-001'},
            json={
                'email': 'customer@example.com',
                'amount': 10000,
                'currency': 'KES'
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['data']['reference'] == reference1
        assert data2['data'].get('idempotent') is True
        
        # Should only have one payment in database
        payments = Payment.query.all()
        assert len(payments) == 1


class TestInitializeMpesa:
    """Test M-Pesa specific initialization endpoint"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_initialize_mpesa_success(self, mock_paystack, client, db_session):
        """Test successful M-Pesa payment initialization"""
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/mpesa123',
                'access_code': 'mpesa_code_123',
                'reference': 'MPESA-TEST-001'
            }
        }
        
        response = client.post('/api/v1/c2b/mpesa/initialize', json={
            'phone_number': '254712345678',
            'email': 'customer@example.com',
            'amount': 100,
            'description': 'Test M-Pesa payment'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['amount_kes'] == 100.0
        assert data['data']['phone_number'] == '254712345678'
        
        # Check database - amount should be in cents
        payment = Payment.query.first()
        assert payment.amount == 10000  # 100 KES = 10000 cents
        assert payment.currency == 'KES'
        assert payment.channel == 'mobile_money'
    
    def test_initialize_mpesa_invalid_phone_format(self, client):
        """Test M-Pesa with invalid phone number format"""
        response = client.post('/api/v1/c2b/mpesa/initialize', json={
            'phone_number': '0712345678',  # Wrong format
            'email': 'customer@example.com',
            'amount': 100
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert '254' in data['message']
    
    def test_initialize_mpesa_phone_too_short(self, client):
        """Test M-Pesa with short phone number"""
        response = client.post('/api/v1/c2b/mpesa/initialize', json={
            'phone_number': '25471234',  # Too short
            'email': 'customer@example.com',
            'amount': 100
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_initialize_mpesa_missing_fields(self, client):
        """Test M-Pesa with missing required fields"""
        response = client.post('/api/v1/c2b/mpesa/initialize', json={
            'phone_number': '254712345678'
            # Missing email and amount
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    @patch('src.app.routes.C2B.paystack')
    def test_initialize_mpesa_idempotency(self, mock_paystack, client, db_session):
        """Test M-Pesa idempotency"""
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/mpesa123',
                'access_code': 'mpesa_code_123',
                'reference': 'MPESA-IDEM-001'
            }
        }
        
        payload = {
            'phone_number': '254712345678',
            'email': 'customer@example.com',
            'amount': 100,
            'idempotency_key': 'mpesa-idem-001'
        }
        
        # First request
        response1 = client.post('/api/v1/c2b/mpesa/initialize', json=payload)
        assert response1.status_code == 200
        
        # Duplicate request
        response2 = client.post('/api/v1/c2b/mpesa/initialize', json=payload)
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['data'].get('idempotent') is True


class TestVerifyPayment:
    """Test payment verification endpoint"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_verify_payment_success(self, mock_paystack, client, sample_payment, db_session):
        """Test successful payment verification"""
        mock_paystack.transaction.verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': sample_payment.paystack_reference,
                'channel': 'mobile_money',
                'id': 12345,
                'authorization': {
                    'authorization_code': 'AUTH_test123'
                }
            }
        }
        
        response = client.get(f'/api/v1/c2b/verify/{sample_payment.paystack_reference}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['status'] == 'SUCCESS'
        
        # Check database updated
        db_session.session.refresh(sample_payment)
        assert sample_payment.status == 'SUCCESS'
    
    @patch('src.app.routes.C2B.paystack')
    def test_verify_payment_failed(self, mock_paystack, client, sample_payment, db_session):
        """Test failed payment verification"""
        mock_paystack.transaction.verify.return_value = {
            'status': True,
            'data': {
                'status': 'failed',
                'reference': sample_payment.paystack_reference
            }
        }
        
        response = client.get(f'/api/v1/c2b/verify/{sample_payment.paystack_reference}')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        
        # Check database updated
        db_session.session.refresh(sample_payment)
        assert sample_payment.status == 'FAILED'
    
    def test_verify_nonexistent_payment(self, client):
        """Test verifying non-existent payment"""
        response = client.get('/api/v1/c2b/verify/NONEXISTENT-REF')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'


class TestChargeAuthorization:
    """Test charging saved authorization"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_charge_authorization_success(self, mock_paystack, client, db_session):
        """Test successful authorization charge"""
        mock_paystack.transaction.charge.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': 'CHARGE-REF-001',
                'channel': 'card'
            }
        }
        
        response = client.post('/api/v1/c2b/charge', json={
            'email': 'customer@example.com',
            'amount': 10000,
            'authorization_code': 'AUTH_test123',
            'currency': 'KES'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Check payment created
        payment = Payment.query.first()
        assert payment is not None
        assert payment.status == 'SUCCESS'
        assert payment.authorization_code == 'AUTH_test123'
    
    def test_charge_authorization_missing_code(self, client):
        """Test charge without authorization code"""
        response = client.post('/api/v1/c2b/charge', json={
            'email': 'customer@example.com',
            'amount': 10000
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestListPayments:
    """Test listing payments endpoint"""
    
    def test_list_payments_empty(self, client, db_session):
        """Test listing when no payments exist"""
        response = client.get('/api/v1/c2b/payments')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 0
    
    def test_list_payments_with_data(self, client, sample_payment, db_session):
        """Test listing existing payments"""
        response = client.get('/api/v1/c2b/payments')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert 'pagination' in data
    
    def test_list_payments_with_status_filter(self, client, sample_payment, successful_payment, db_session):
        """Test filtering payments by status"""
        response = client.get('/api/v1/c2b/payments?status=SUCCESS')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['data'][0]['status'] == 'SUCCESS'
    
    def test_list_payments_pagination(self, client, db_session):
        """Test pagination"""
        # Create multiple payments
        for i in range(25):
            payment = Payment(
                email=f'customer{i}@example.com',
                amount=10000,
                currency='KES',
                payment_provider='PAYSTACK',
                account_reference=f'TEST-{i}',
                transaction_desc=f'Test {i}',
                paystack_reference=f'REF-{i}'
            )
            db_session.session.add(payment)
        db_session.session.commit()
        
        response = client.get('/api/v1/c2b/payments?page=1&per_page=10')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] == 25
