# Quick Start Guide - Kenya M-Pesa Integration

Get your M-Pesa payment gateway up and running in 5 minutes!

## 🇰🇪 For Kenyan Businesses

This guide helps you set up M-Pesa payment collection using Paystack.

## Prerequisites Check

```bash
# Check Python version (need 3.13+)
python --version

# Check PostgreSQL
psql --version

# Check Redis
redis-cli --version
```

## 1. Install Dependencies

```bash
cd /mnt/sub0_2/projectX/backend

# Using pip
pip install -e .

# OR using uv (faster)
pip install uv
uv pip install -e .
```

## 2. Set Up Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your favorite editor
```

**Minimum required settings:**
```env
SECRET_KEY=your-random-secret-key-here
PAYSTACK_SECRET_KEY=sk_test_your_kenya_test_key_from_paystack
POSTGRES_PASSWORD=your_postgres_password
DEFAULT_CURRENCY=KES
```

**Get Paystack Keys:**
1. Sign up at [https://paystack.com/ke](https://paystack.com/ke) (Kenya)
2. Go to Settings → API Keys
3. Copy your Test Secret Key

## 3. Set Up Database

```bash
# Option A: Create database manually
createdb payment_gateway

# Option B: Using psql
psql -U postgres
# Then in psql:
CREATE DATABASE payment_gateway;
\q
```

## 4. Start Redis

```bash
# On Linux/Mac
redis-server

# On Windows (if using WSL)
sudo service redis-server start

# Verify it's running
redis-cli ping  # Should return PONG
```

## 5. Run the Application

```bash
python run.py
```

You should see:
```
Database tables created successfully!
Starting Flask application on port 5000
Debug mode: true
 * Running on http://0.0.0.0:5000
```

## 6. Test the API

### Health Check
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "healthy"}
```

### Create a User
```bash
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

### Initialize a Payment
```bash
curl -X POST http://localhost:5000/api/v1/c2b/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "phone_number": "254712345678",
    "amount": 10000,
    "currency": "KES",
    "channels": ["mobile_money"],
    "description": "Test M-Pesa Payment"
  }'
```

### Initialize M-Pesa Payment (Simplified)
```bash
curl -X POST http://localhost:5000/api/v1/c2b/mpesa/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "email": "customer@example.com",
    "amount": 100,
    "description": "Test Payment"
  }'
```

## 7. Get Your Paystack Test Keys

1. Go to [https://paystack.com/ke](https://paystack.com/ke) (Kenya)
2. Sign up or log in
3. Go to Settings → API Keys & Webhooks
4. Copy your **Test Secret Key** (starts with `sk_test_`)
5. Add it to your `.env` file

## M-Pesa Payment Testing

### Phone Number Format
Use format: **254XXXXXXXXX** (no + sign, 12 digits)

Examples:
- Safaricom: `254712345678`
- Airtel: `254733456789`

### Amount Format
- Use KES amount directly (e.g., `100` = 100 KES)
- System converts to cents automatically

## 📖 Full M-Pesa Guide

For complete M-Pesa integration documentation, see:
**[KENYA_MPESA_GUIDE.md](KENYA_MPESA_GUIDE.md)**

## Common Issues & Solutions

### Issue: Database connection error
**Solution:**
```bash
# Make sure PostgreSQL is running
sudo systemctl start postgresql  # Linux
# or
brew services start postgresql   # Mac
```

### Issue: Redis connection error
**Solution:**
```bash
# Install Redis if not installed
sudo apt install redis-server    # Ubuntu/Debian
brew install redis               # Mac

# Start Redis
redis-server
```

### Issue: Module not found
**Solution:**
```bash
# Reinstall dependencies
pip install -e .
```

### Issue: Port already in use
**Solution:**
```bash
# Change port in .env
PORT=5001

# Or kill process using port 5000
lsof -ti:5000 | xargs kill -9
```

## Next Steps

1. **Test Payments**: Use Paystack test cards to test payment flow
2. **Set Up Webhooks**: Configure webhook URL in Paystack dashboard
3. **Explore API**: Check `README.md` for full API documentation
4. **Customize**: Modify models and routes for your specific needs

## Test Cards (Paystack)

### Successful Payment
```
Card: 4084 0840 8408 4081
CVV: 408
Expiry: Any future date
PIN: 0000
OTP: 123456
```

### Failed Payment
```
Card: 5060 6666 6666 6666 6666
CVV: 123
Expiry: Any future date
```

### M-Pesa Testing
Check Paystack Kenya sandbox docs for M-Pesa test procedures.

## API Endpoint Summary (Kenya Focus)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/auth/signup` | POST | Register user |
| `/api/v1/auth/signin` | POST | Login user |
| `/api/v1/c2b/mpesa/initialize` | POST | M-Pesa payment (simple) |
| `/api/v1/c2b/initialize` | POST | Start payment (full options) |
| `/api/v1/c2b/verify/{ref}` | GET | Verify payment |
| `/api/v1/b2c/transfer/initiate` | POST | Send M-Pesa payout |
| `/api/v1/b2c/refund` | POST | Process refund |

## Support

- **M-Pesa Guide**: [KENYA_MPESA_GUIDE.md](KENYA_MPESA_GUIDE.md)
- **Paystack Kenya**: https://paystack.com/ke
- **Paystack Docs**: https://paystack.com/docs/payments/mobile-money
- **Paystack Python**: https://github.com/PaystackOSS/paystack-python
- **Flask Docs**: https://flask.palletsprojects.com/

Happy coding! 🇰🇪 🚀
