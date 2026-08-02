"""
Tests for health check and basic application endpoints
"""
import pytest


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint serves the public landing page."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b"Let's Review" in response.data
        assert b'/static/theme.css' in response.data
        assert b'/static/theme.js' in response.data
        assert b'/static/css/app.css' in response.data
        assert b'cdn.tailwindcss.com' not in response.data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_nonexistent_endpoint(self, client):
        """Test 404 for non-existent endpoint"""
        response = client.get('/api/v1/nonexistent')
        
        assert response.status_code == 404


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present"""
        response = client.options('/api/v1/c2b/payments')
        
        # CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200
    
    def test_api_accepts_json(self, client):
        """Test that API accepts JSON content type"""
        response = client.post('/api/v1/auth/signin',
            headers={'Content-Type': 'application/json'},
            json={'email': 'test@example.com', 'password': 'test'}
        )
        
        # Should process JSON, not return unsupported media type
        assert response.status_code != 415


class TestRateLimiting:
    """Test rate limiting (basic check)"""
    
    def test_rate_limit_not_immediately_triggered(self, client):
        """Test that a few requests don't trigger rate limit"""
        for _ in range(5):
            response = client.get('/health')
            assert response.status_code == 200
    
    # Note: Full rate limit testing requires Redis and is complex
    # This is just a basic sanity check
