"""
Tests for authentication endpoints (AAA routes)
"""
import pytest
import jwt
from src.app.routes.AAA import hash_password, verify_password, generate_jwt_token, verify_jwt_token


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = 'testpassword123'
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = 'testpassword123'
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = 'testpassword123'
        wrong_password = 'wrongpassword'
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)"""
        password = 'testpassword123'
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Test JWT token generation and verification"""
    
    def test_generate_token(self):
        """Test generating JWT token"""
        token = generate_jwt_token(1, 'test@example.com')
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test verifying valid token"""
        token = generate_jwt_token(1, 'test@example.com')
        payload = verify_jwt_token(token)
        
        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['email'] == 'test@example.com'
    
    def test_verify_invalid_token(self):
        """Test verifying invalid token"""
        invalid_token = 'invalid.token.here'
        payload = verify_jwt_token(invalid_token)
        
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test verifying expired token"""
        import os
        import time
        
        # Temporarily set very short expiration
        original_delta = os.environ.get('JWT_EXPIRATION_DELTA')
        os.environ['JWT_EXPIRATION_DELTA'] = '1'  # 1 second
        
        token = generate_jwt_token(1, 'test@example.com')
        time.sleep(2)  # Wait for token to expire
        
        payload = verify_jwt_token(token)
        assert payload is None
        
        # Restore original setting
        if original_delta:
            os.environ['JWT_EXPIRATION_DELTA'] = original_delta


class TestSignupEndpoint:
    """Test user signup endpoint"""
    
    def test_signup_success(self, client, db_session):
        """Test successful user signup"""
        response = client.post('/api/v1/auth/signup', json={
            'email': 'newuser@example.com',
            'password': 'password123',
            'name': 'New User',
            'phone_number': '+254712345678'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'token' in data['data']
        assert data['data']['user']['email'] == 'newuser@example.com'
    
    def test_signup_missing_email(self, client):
        """Test signup without email"""
        response = client.post('/api/v1/auth/signup', json={
            'password': 'password123',
            'name': 'New User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'email' in data['message'].lower()
    
    def test_signup_missing_password(self, client):
        """Test signup without password"""
        response = client.post('/api/v1/auth/signup', json={
            'email': 'test@example.com',
            'name': 'New User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_signup_short_password(self, client):
        """Test signup with short password"""
        response = client.post('/api/v1/auth/signup', json={
            'email': 'test@example.com',
            'password': 'short',
            'name': 'New User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert '8 characters' in data['message']
    
    def test_signup_invalid_email(self, client):
        """Test signup with invalid email"""
        response = client.post('/api/v1/auth/signup', json={
            'email': 'invalid-email',
            'password': 'password123',
            'name': 'New User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_signup_duplicate_email(self, client, sample_user):
        """Test signup with existing email"""
        response = client.post('/api/v1/auth/signup', json={
            'email': 'test@example.com',  # Already exists
            'password': 'password123',
            'name': 'Another User'
        })
        
        assert response.status_code == 409
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'already registered' in data['message'].lower()


class TestSigninEndpoint:
    """Test user signin endpoint"""
    
    def test_signin_success(self, client, sample_user):
        """Test successful signin"""
        response = client.post('/api/v1/auth/signin', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'token' in data['data']
    
    def test_signin_wrong_password(self, client, sample_user):
        """Test signin with wrong password"""
        response = client.post('/api/v1/auth/signin', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_signin_nonexistent_user(self, client):
        """Test signin with non-existent user"""
        response = client.post('/api/v1/auth/signin', json={
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_signin_missing_credentials(self, client):
        """Test signin without credentials"""
        response = client.post('/api/v1/auth/signin', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestVerifyTokenEndpoint:
    """Test token verification endpoint"""
    
    def test_verify_valid_token(self, client, auth_token):
        """Test verifying valid token"""
        response = client.post('/api/v1/auth/verify-token', json={
            'token': auth_token
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'user' in data['data']
    
    def test_verify_invalid_token(self, client):
        """Test verifying invalid token"""
        response = client.post('/api/v1/auth/verify-token', json={
            'token': 'invalid.token.here'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_verify_missing_token(self, client):
        """Test verify without token"""
        response = client.post('/api/v1/auth/verify-token', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestChangePasswordEndpoint:
    """Test password change endpoint"""
    
    def test_change_password_success(self, client, auth_token):
        """Test successful password change"""
        response = client.post('/api/v1/auth/change-password', json={
            'token': auth_token,
            'old_password': 'password123',
            'new_password': 'newpassword123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_change_password_wrong_old_password(self, client, auth_token):
        """Test change password with wrong old password"""
        response = client.post('/api/v1/auth/change-password', json={
            'token': auth_token,
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_change_password_short_new_password(self, client, auth_token):
        """Test change password with short new password"""
        response = client.post('/api/v1/auth/change-password', json={
            'token': auth_token,
            'old_password': 'password123',
            'new_password': 'short'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
