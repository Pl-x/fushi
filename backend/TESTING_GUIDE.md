# Testing Guide - Payment Gateway

## Overview

Comprehensive test suite for the Kenya M-Pesa payment gateway covering:
- ✅ Unit tests
- ✅ Integration tests  
- ✅ API endpoint tests
- ✅ Database model tests
- ✅ Authentication tests
- ✅ Idempotency tests

## Test Coverage

### Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `test_models.py` | Database models | 15+ tests |
| `test_auth.py` | Authentication & JWT | 20+ tests |
| `test_c2b.py` | Payment collection | 25+ tests |
| `test_b2c.py` | Transfers & refunds | 20+ tests |
| `test_health.py` | Health checks | 5+ tests |
| `test_integration.py` | End-to-end workflows | 10+ tests |

**Total: 95+ comprehensive tests**

## Quick Start

### 1. Install Test Dependencies

```bash
cd /mnt/sub0_2/projectX/backend

# Install test requirements
pip install -r tests/test_requirements.txt
```

### 2. Run Tests

```bash
# Run all tests
./run_tests.sh

# Or using pytest directly
pytest tests/
```

## Running Tests

### All Tests

```bash
./run_tests.sh all
```

### Specific Test Categories

```bash
# Unit tests only
./run_tests.sh unit

# Integration tests
./run_tests.sh integration

# Authentication tests
./run_tests.sh auth

# Payment tests (C2B)
./run_tests.sh payment

# Transfer/refund tests (B2C)
./run_tests.sh transfer

# Model tests
./run_tests.sh model

# Health check tests
./run_tests.sh health
```

### With Coverage Report

```bash
# Generate HTML coverage report
./run_tests.sh coverage

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Quick Tests (No Coverage)

```bash
# Fast test run without coverage
./run_tests.sh quick
```

### Failed Tests Only

```bash
# Re-run only failed tests
./run_tests.sh failed
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
./run_tests.sh parallel
```

### Verbose Output

```bash
# Verbose output
./run_tests.sh all -v

# Very verbose
./run_tests.sh all -vv

# Show print statements
./run_tests.sh all -s
```

## Test Structure

### conftest.py

Provides pytest fixtures:

```python
@pytest.fixture
def client(app):
    """Test client for making requests"""
    return app.test_client()

@pytest.fixture
def sample_user(db_session):
    """Create a test user"""
    ...

@pytest.fixture
def auth_token(client, sample_user):
    """Get authentication token"""
    ...
```

### Using Fixtures

```python
def test_something(client, auth_token):
    """Test using fixtures"""
    response = client.post('/api/endpoint',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={'data': 'value'}
    )
    assert response.status_code == 200
```

## Writing Tests

### Test Structure

```python
class TestFeatureName:
    """Test specific feature"""
    
    def test_success_case(self, client, db_session):
        """Test successful operation"""
        # Arrange
        data = {'field': 'value'}
        
        # Act
        response = client.post('/api/endpoint', json=data)
        
        # Assert
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'
    
    def test_failure_case(self, client):
        """Test error handling"""
        # Act
        response = client.post('/api/endpoint', json={})
        
        # Assert
        assert response.status_code == 400
        assert 'error' in response.get_json()['status']
```

### Mocking Paystack API

```python
from unittest.mock import patch

@patch('src.app.routes.C2B.paystack')
def test_with_mock_paystack(mock_paystack, client):
    """Test with mocked Paystack"""
    # Configure mock
    mock_paystack.transaction.initialize.return_value = {
        'status': True,
        'data': {
            'reference': 'TEST-REF',
            'authorization_url': 'https://...'
        }
    }
    
    # Make request
    response = client.post('/api/v1/c2b/initialize', json={...})
    
    # Assert
    assert response.status_code == 200
```

### Testing Database Operations

```python
def test_create_payment(db_session):
    """Test creating a payment record"""
    from src.app.models import Payment
    
    payment = Payment(
        email='test@example.com',
        amount=10000,
        currency='KES',
        payment_provider='PAYSTACK',
        account_reference='TEST-001',
        transaction_desc='Test'
    )
    
    db_session.session.add(payment)
    db_session.session.commit()
    
    assert payment.id is not None
    assert Payment.query.count() == 1
```

### Testing Idempotency

```python
def test_idempotency(client, db_session):
    """Test idempotent requests"""
    payload = {
        'email': 'test@example.com',
        'amount': 10000
    }
    
    # First request
    response1 = client.post('/api/endpoint',
        headers={'Idempotency-Key': 'test-key-001'},
        json=payload
    )
    
    # Duplicate request
    response2 = client.post('/api/endpoint',
        headers={'Idempotency-Key': 'test-key-001'},
        json=payload
    )
    
    # Should return same result
    assert response1.get_json()['data']['id'] == \
           response2.get_json()['data']['id']
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_logic():
    """Unit test"""
    pass

@pytest.mark.integration
def test_complete_flow():
    """Integration test"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Slow test"""
    pass
```

Run specific markers:

```bash
pytest -m unit         # Run unit tests only
pytest -m integration  # Run integration tests only
pytest -m "not slow"   # Skip slow tests
```

## Coverage Goals

Target coverage: **≥ 80%**

Current coverage by module:
- Models: ~90%
- Authentication: ~85%
- C2B Routes: ~80%
- B2C Routes: ~80%
- Health checks: 100%

Check coverage:

```bash
pytest --cov=src/app --cov-report=term-missing
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/test_requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=src/app
```

## Troubleshooting

### Tests Fail with Import Errors

```bash
# Make sure you're in the backend directory
cd /mnt/sub0_2/projectX/backend

# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

### Database Errors

Tests use in-memory SQLite, so no database setup needed. If you see errors:

```bash
# Clear any cached files
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Re-run tests
pytest tests/
```

### Mock Not Working

Make sure you're patching the correct import path:

```python
# Wrong
@patch('pypaystack2.Paystack')

# Correct (patch where it's used)
@patch('src.app.routes.C2B.paystack')
```

### Fixture Not Found

Check that conftest.py is in the tests directory and properly imported.

## Best Practices

### ✅ Do

- Write descriptive test names
- Test both success and failure cases
- Use fixtures for common setup
- Mock external APIs (Paystack)
- Test edge cases
- Keep tests independent
- Clean up test data

### ❌ Don't

- Test implementation details
- Make tests dependent on each other
- Use real API keys in tests
- Skip test cleanup
- Write overly complex tests
- Test framework code

## Test Data

### Sample Data

```python
# Valid M-Pesa phone numbers
VALID_PHONES = [
    '254712345678',
    '254733456789',
    '254755123456'
]

# Invalid phone numbers
INVALID_PHONES = [
    '0712345678',      # Missing country code
    '+254712345678',   # Has + sign
    '254712',          # Too short
]

# Test amounts (in cents)
TEST_AMOUNTS = {
    'small': 100,      # 1 KES
    'normal': 10000,   # 100 KES
    'large': 1000000,  # 10,000 KES
}
```

## Performance Testing

For load testing:

```bash
# Install locust
pip install locust

# Create locustfile.py with load test scenarios
# Run load tests
locust -f locustfile.py
```

## Security Testing

Check for common vulnerabilities:

```bash
# Install safety
pip install safety

# Check for known vulnerabilities
safety check

# SQL injection testing (use responsibly)
pytest tests/ -k "injection or xss or security"
```

## Test Reporting

Generate different report formats:

```bash
# HTML report
pytest tests/ --html=report.html

# JUnit XML (for CI)
pytest tests/ --junitxml=junit.xml

# JSON report
pytest tests/ --json-report
```

## Tips for Kenya M-Pesa Testing

1. **Phone Number Format**: Always test with 254XXXXXXXXX format
2. **Currency**: Use KES for Kenya tests
3. **Amount Conversion**: Remember 100 KES = 10000 cents
4. **Idempotency**: Test retry scenarios thoroughly
5. **Mock Paystack**: Don't make real API calls in tests

## Next Steps

1. Run the test suite: `./run_tests.sh`
2. Check coverage: `./run_tests.sh coverage`
3. Add tests for new features
4. Keep coverage above 80%
5. Run tests before pushing code

## Support

For testing issues:
1. Check test output for error messages
2. Review this guide
3. Check pytest documentation: https://docs.pytest.org/

---

**Happy Testing!** 🧪 ✅

Run `./run_tests.sh help` for more options.
