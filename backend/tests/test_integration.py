"""
Integration tests - Testing complete workflows
"""
import pytest
from unittest.mock import patch


class TestCompletePaymentFlow:
    """Test complete payment workflow"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_mpesa_payment_complete_flow(self, mock_paystack, client, db_session):
        """Test complete M-Pesa payment flow from initialization to verification"""
        # Mock Paystack responses
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/test',
                'access_code': 'test_access',
                'reference': 'MPESA-FLOW-001'
            }
        }
        
        mock_paystack.transaction.verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': 'MPESA-FLOW-001',
                'channel': 'mobile_money',
                'id': 99999
            }
        }
        
        # Step 1: Initialize payment
        init_response = client.post('/api/v1/c2b/mpesa/initialize', json={
            'phone_number': '254712345678',
            'email': 'customer@example.com',
            'amount': 100
        })
        
        assert init_response.status_code == 200
        init_data = init_response.get_json()
        reference = init_data['data']['reference']
        
        # Step 2: Simulate customer completing payment and verify
        verify_response = client.get(f'/api/v1/c2b/verify/{reference}')
        
        assert verify_response.status_code == 200
        verify_data = verify_response.get_json()
        assert verify_data['data']['status'] == 'SUCCESS'
    
    @patch('src.app.routes.C2B.paystack')
    @patch('src.app.routes.B2C.paystack')
    def test_payment_and_refund_flow(self, mock_b2c_paystack, mock_c2b_paystack, client, db_session):
        """Test payment followed by refund"""
        # Mock payment initialization
        mock_c2b_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/test',
                'access_code': 'test_access',
                'reference': 'PAY-REFUND-001'
            }
        }
        
        # Mock payment verification (successful)
        mock_c2b_paystack.transaction.verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': 'PAY-REFUND-001',
                'channel': 'mobile_money',
                'id': 88888
            }
        }
        
        # Mock refund processing
        mock_b2c_paystack.refund.create.return_value = {
            'status': True,
            'data': {
                'transaction': {
                    'reference': 'REFUND-001'
                }
            }
        }
        
        # Step 1: Initialize and verify payment
        init_response = client.post('/api/v1/c2b/initialize', json={
            'email': 'customer@example.com',
            'amount': 10000,
            'currency': 'KES'
        })
        assert init_response.status_code == 200
        reference = init_response.get_json()['data']['reference']
        
        verify_response = client.get(f'/api/v1/c2b/verify/{reference}')
        assert verify_response.status_code == 200
        
        # Step 2: Process refund
        refund_response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': reference,
            'customer_note': 'Customer cancelled order'
        })
        
        assert refund_response.status_code == 200
        refund_data = refund_response.get_json()
        assert refund_data['status'] == 'success'


class TestAuthenticationFlow:
    """Test complete authentication workflow"""
    
    def test_signup_signin_change_password_flow(self, client, db_session):
        """Test complete user authentication flow"""
        # Step 1: Sign up
        signup_response = client.post('/api/v1/auth/signup', json={
            'email': 'newuser@example.com',
            'password': 'password123',
            'name': 'New User',
            'phone_number': '+254712345678'
        })
        
        assert signup_response.status_code == 201
        signup_data = signup_response.get_json()
        token = signup_data['data']['token']
        
        # Step 2: Verify token
        verify_response = client.post('/api/v1/auth/verify-token', json={
            'token': token
        })
        
        assert verify_response.status_code == 200
        
        # Step 3: Change password
        change_response = client.post('/api/v1/auth/change-password', json={
            'token': token,
            'old_password': 'password123',
            'new_password': 'newpassword456'
        })
        
        assert change_response.status_code == 200
        
        # Step 4: Sign in with new password
        signin_response = client.post('/api/v1/auth/signin', json={
            'email': 'newuser@example.com',
            'password': 'newpassword456'
        })
        
        assert signin_response.status_code == 200
        
        # Step 5: Old password should not work
        old_signin_response = client.post('/api/v1/auth/signin', json={
            'email': 'newuser@example.com',
            'password': 'password123'
        })
        
        assert old_signin_response.status_code == 401


class TestIdempotencyAcrossEndpoints:
    """Test idempotency across different operations"""
    
    @patch('src.app.routes.C2B.paystack')
    def test_payment_idempotency_across_methods(self, mock_paystack, client, db_session):
        """Test that idempotency works with both header and body"""
        mock_paystack.transaction.initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.paystack.com/test',
                'access_code': 'test_access',
                'reference': 'IDEM-TEST-001'
            }
        }
        
        idempotency_key = 'test-idem-key-123'
        
        # Request 1: Using header
        response1 = client.post('/api/v1/c2b/initialize',
            headers={'Idempotency-Key': idempotency_key},
            json={
                'email': 'customer@example.com',
                'amount': 10000,
                'currency': 'KES'
            }
        )
        
        assert response1.status_code == 200
        payment_id1 = response1.get_json()['data']['payment_id']
        
        # Request 2: Using body
        response2 = client.post('/api/v1/c2b/initialize', json={
            'email': 'customer@example.com',
            'amount': 10000,
            'currency': 'KES',
            'idempotency_key': idempotency_key
        })
        
        assert response2.status_code == 200
        payment_id2 = response2.get_json()['data']['payment_id']
        
        # Should return same payment
        assert payment_id1 == payment_id2
    
    @patch('src.app.routes.B2C.paystack')
    def test_transfer_refund_idempotency_independence(self, mock_paystack, client, successful_payment, db_session):
        """Test that transfer and refund idempotency keys are independent"""
        mock_paystack.transfer_recipient.create.return_value = {
            'status': True,
            'data': {'recipient_code': 'RCP_test'}
        }
        
        mock_paystack.transfer.initiate.return_value = {
            'status': True,
            'data': {'transfer_code': 'TRF_test', 'reference': 'TRF-001'}
        }
        
        mock_paystack.refund.create.return_value = {
            'status': True,
            'data': {'transaction': {'reference': 'REFUND-001'}}
        }
        
        same_key = 'same-idempotency-key'
        
        # Create transfer with key
        transfer_response = client.post('/api/v1/b2c/transfer/initiate', json={
            'type': 'mobile_money',
            'name': 'John',
            'account_number': '254712345678',
            'amount': 5000,
            'currency': 'KES',
            'idempotency_key': same_key
        })
        
        assert transfer_response.status_code == 200
        
        # Create refund with same key (should work, different model)
        refund_response = client.post('/api/v1/b2c/refund', json={
            'transaction_reference': successful_payment.paystack_reference,
            'idempotency_key': same_key
        })
        
        assert refund_response.status_code == 200
        
        # Both should exist
        from src.app.models import Transfer, Refund
        assert Transfer.query.count() == 1
        assert Refund.query.count() == 1


class TestErrorHandling:
    """Test error handling across the application"""
    
    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON"""
        response = client.post('/api/v1/auth/signin',
            data='invalid json',
            content_type='application/json'
        )
        
        # Should handle gracefully, not crash
        assert response.status_code in [400, 415, 500]
    
    def test_missing_content_type(self, client):
        """Test request without content-type header"""
        response = client.post('/api/v1/auth/signin',
            data='{"email": "test@example.com"}',
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 415]
    
    @patch('src.app.routes.C2B.paystack', None)
    def test_paystack_not_configured(self, client):
        """Test behavior when Paystack is not configured"""
        response = client.post('/api/v1/c2b/initialize', json={
            'email': 'customer@example.com',
            'amount': 10000
        })
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'not configured' in data['message'].lower()
