"""
Tests for B2C (Business to Customer) transfer and refund endpoints
"""
import pytest
from unittest.mock import patch
from src.app.models import Transfer, Refund


class TestInitiateTransfer:
    """Test transfer initiation endpoint"""
    
    @patch('src.app.routes.B2C.paystack')
    def test_initiate_transfer_success(self, mock_paystack, client, db_session):
        """Test successful transfer initiation"""
        mock_paystack.transfer_recipient.create.return_value = {
            'status': True,
            'data': {
                'recipient_code': 'RCP_test123'
            }
        }
        
        mock_paystack.transfer.initiate.return_value = {
            'status': True,
            'data': {
                'transfer_code': 'TRF_test123',
                'reference': 'TRF-001'
            }
        }
        
        response = client.post('/api/v1/b2c/transfer/initiate', json={
            'type': 'mobile_money',
            'name': 'John Doe',
            'account_number': '254712345678',
            'amount': 50000,
            'currency': 'KES',
            'reason': 'Test payout'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Check database
        transfer = Transfer.query.first()
        assert transfer is not None
        assert transfer.amount == 50000
        assert transfer.account_number == '254712345678'
    
    def test_initiate_transfer_missing_fields(self, client):
        """Test transfer with missing required fields"""
        response = client.post('/api/v1/b2c/transfer/initiate', json={
            'type': 'mobile_money'
            # Missing other required fields
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    @patch('src.app.routes.B2C.paystack')
    def test_initiate_transfer_with_idempotency(self, mock_paystack, client, db_session):
        """Test transfer with idempotency key"""
        mock_paystack.transfer_recipient.create.return_value = {
            'status': True,
            'data': {'recipient_code': 'RCP_test123'}
        }
        
        mock_paystack.transfer.initiate.return_value = {
            'status': True,
            'data': {
                'transfer_code': 'TRF_idem_test',
                'reference': 'TRF-IDEM-001'
            }
        }
        
        payload = {
            'type': 'mobile_money',
            'name': 'John Doe',
            'account_number': '254712345678',
            'amount': 50000,
            'currency': 'KES',
            'idempotency_key': 'transfer-idem-001'
        }
        
        # First request
        response1 = client.post('/api/v1/b2c/transfer/initiate', json=payload)
        assert response1.status_code == 200
        
        # Duplicate request
        response2 = client.post('/api/v1/b2c/transfer/initiate', json=payload)
        assert response2.status_code == 200
        
        # Should only have one transfer
        transfers = Transfer.query.all()
        assert len(transfers) == 1
    
    @patch('src.app.routes.B2C.paystack')
    def test_initiate_transfer_recipient_creation_fails(self, mock_paystack, client):
        """Test transfer when recipient creation fails"""
        mock_paystack.transfer_recipient.create.return_value = {
            'status': False,
            'message': 'Invalid account number'
        }
        
        response = client.post('/api/v1/b2c/transfer/initiate', json={
            'type': 'nuban',
            'name': 'John Doe',
            'account_number': '0123456789',
            'bank_code': '058',
            'amount': 50000,
            'currency': 'NGN'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestVerifyTransfer:
    """Test transfer verification endpoint"""
    
    @patch('src.app.routes.B2C.paystack')
    def test_verify_transfer_success(self, mock_paystack, client, sample_transfer, db_session):
        """Test successful transfer verification"""
        mock_paystack.transfer.verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': sample_transfer.reference
            }
        }
        
        response = client.get(f'/api/v1/b2c/transfer/verify/{sample_transfer.reference}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Check database updated
        db_session.session.refresh(sample_transfer)
        assert sample_transfer.status == 'SUCCESS'
    
    @patch('src.app.routes.B2C.paystack')
    def test_verify_transfer_failed(self, mock_paystack, client, sample_transfer, db_session):
        """Test failed transfer verification"""
        mock_paystack.transfer.verify.return_value = {
            'status': True,
            'data': {
                'status': 'failed',
                'reference': sample_transfer.reference
            }
        }
        
        response = client.get(f'/api/v1/b2c/transfer/verify/{sample_transfer.reference}')
        
        assert response.status_code == 200
        db_session.session.refresh(sample_transfer)
        assert sample_transfer.status == 'FAILED'
    
    def test_verify_nonexistent_transfer(self, client):
        """Test verifying non-existent transfer"""
        response = client.get('/api/v1/b2c/transfer/verify/NONEXISTENT-REF')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'


class TestProcessRefund:
    """Test refund processing endpoint"""
    
    @patch('src.app.routes.B2C.paystack')
    def test_process_refund_success(self, mock_paystack, client, successful_payment, db_session):
        """Test successful refund processing"""
        mock_paystack.refund.create.return_value = {
            'status': True,
            'data': {
                'transaction': {
                    'reference': 'REFUND-REF-001'
                }
            }
        }
        
        response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': successful_payment.paystack_reference,
            'customer_note': 'Refund for cancelled order'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Check refund created
        refund = Refund.query.first()
        assert refund is not None
        assert refund.payment_id == successful_payment.id
        assert refund.status == 'PROCESSING'
        
        # Check payment updated
        db_session.session.refresh(successful_payment)
        assert successful_payment.status == 'REFUNDED'
    
    @patch('src.app.routes.B2C.paystack')
    def test_process_partial_refund(self, mock_paystack, client, successful_payment, db_session):
        """Test partial refund"""
        mock_paystack.refund.create.return_value = {
            'status': True,
            'data': {
                'transaction': {
                    'reference': 'PARTIAL-REFUND-001'
                }
            }
        }
        
        response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': successful_payment.paystack_reference,
            'amount': 5000,  # Partial amount
            'customer_note': 'Partial refund'
        })
        
        assert response.status_code == 200
        
        refund = Refund.query.first()
        assert refund.amount == 5000
    
    def test_refund_nonexistent_transaction(self, client):
        """Test refund for non-existent transaction"""
        response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': 'NONEXISTENT-REF'
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_refund_pending_transaction(self, client, sample_payment):
        """Test refund for pending transaction"""
        response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': sample_payment.paystack_reference
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'successful' in data['message'].lower()
    
    @patch('src.app.routes.B2C.paystack')
    def test_refund_already_refunded(self, mock_paystack, client, successful_payment, db_session):
        """Test refund for already refunded transaction"""
        # Create existing refund
        refund = Refund(
            payment_id=successful_payment.id,
            transaction_reference=successful_payment.paystack_reference,
            amount=successful_payment.amount,
            currency='KES',
            status='SUCCESS'
        )
        db_session.session.add(refund)
        db_session.session.commit()
        
        response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': successful_payment.paystack_reference
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'already refunded' in data['message'].lower()
    
    @patch('src.app.routes.B2C.paystack')
    def test_refund_with_idempotency(self, mock_paystack, client, successful_payment, db_session):
        """Test refund with idempotency key"""
        mock_paystack.refund.create.return_value = {
            'status': True,
            'data': {
                'transaction': {
                    'reference': 'REFUND-IDEM-001'
                }
            }
        }
        
        payload = {
            'transaction_reference': successful_payment.paystack_reference,
            'idempotency_key': 'refund-idem-001'
        }
        
        # First request
        response1 = client.post('/api/v1/b2c/refund', json=payload)
        assert response1.status_code == 200
        
        # Duplicate request
        response2 = client.post('/api/v1/b2c/refund', json=payload)
        assert response2.status_code == 200
        
        # Should only have one refund
        refunds = Refund.query.all()
        assert len(refunds) == 1


class TestListTransfers:
    """Test listing transfers endpoint"""
    
    def test_list_transfers_empty(self, client, db_session):
        """Test listing when no transfers exist"""
        response = client.get('/api/v1/b2c/transfers')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 0
    
    def test_list_transfers_with_data(self, client, sample_transfer, db_session):
        """Test listing existing transfers"""
        response = client.get('/api/v1/b2c/transfers')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 1
    
    def test_list_transfers_with_filter(self, client, db_session):
        """Test filtering transfers by status"""
        # Create transfers with different statuses
        transfer1 = Transfer(
            recipient_type='mobile_money',
            account_number='254712345678',
            account_name='John',
            amount=5000,
            currency='KES',
            reference='TRF-001',
            status='SUCCESS'
        )
        transfer2 = Transfer(
            recipient_type='mobile_money',
            account_number='254712345679',
            account_name='Jane',
            amount=6000,
            currency='KES',
            reference='TRF-002',
            status='PENDING'
        )
        db_session.session.add_all([transfer1, transfer2])
        db_session.session.commit()
        
        response = client.get('/api/v1/b2c/transfers?status=SUCCESS')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['status'] == 'SUCCESS'


class TestListRefunds:
    """Test listing refunds endpoint"""
    
    def test_list_refunds_empty(self, client, db_session):
        """Test listing when no refunds exist"""
        response = client.get('/api/v1/b2c/refunds')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 0
    
    def test_list_refunds_with_data(self, client, successful_payment, db_session):
        """Test listing existing refunds"""
        refund = Refund(
            payment_id=successful_payment.id,
            transaction_reference=successful_payment.paystack_reference,
            amount=10000,
            currency='KES',
            status='SUCCESS'
        )
        db_session.session.add(refund)
        db_session.session.commit()
        
        response = client.get('/api/v1/b2c/refunds')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']) == 1
