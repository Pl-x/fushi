# Payment Gateway Backend (Kenya - M-Pesa Integration)

A comprehensive payment processing backend built with Flask and Paystack integration, **optimized for M-Pesa payments in Kenya**. This application supports payment collection (C2B), payouts/transfers (B2C), refunds, and user authentication.

## 🇰🇪 Kenya M-Pesa Support

This system is specifically configured for **Kenyan businesses** and supports:
- **M-Pesa payments** (Safaricom)
- **Airtel Money**
- **Bank transfers**
- **Card payments**

Currency: **KES (Kenya Shillings)**

> **Note**: See [KENYA_MPESA_GUIDE.md](KENYA_MPESA_GUIDE.md) for detailed M-Pesa integration instructions.

## Features

### Payment Processing (Paystack Integration - Kenya Focus)
- **M-Pesa Integration**: Simplified M-Pesa payment collection via Paystack
- **C2B (Customer to Business)**: Receive payments from customers
- **B2C (Business to Customer)**: Send payouts/transfers to M-Pesa accounts
- **Refunds**: Process full or partial refunds
- **Webhook Support**: Real-time payment status updates
- **Multiple Payment Channels**: M-Pesa, Airtel Money, Bank Transfer, Cards

### Authentication & Authorization
- User registration and login
- JWT-based authentication
- Password hashing with bcrypt
- Token verification and validation
- Password change functionality

### Database Models
- Payment tracking (Paystack & M-Pesa support)
- Transfer/Payout records
- Refund management
- User management
- Transaction history

### Security Features
- Rate limiting (via Redis)
- CORS configuration
- JWT token expiration
- Webhook signature verification
- Password strength validation

## Tech Stack

- **Framework**: Flask 3.0+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Payment Provider**: Paystack (via pypaystack2)
- **Authentication**: JWT (PyJWT)
- **Password Hashing**: bcrypt
- **Rate Limiting**: Flask-Limiter with Redis
- **Migrations**: Flask-Migrate

## Project Structure

```
backend/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # App initialization & health endpoints
│       ├── config.py            # App configuration & factory
│       ├── extensions.py        # Flask extensions setup
│       ├── models.py            # Database models
│       ├── guards/
│       │   └── jwtguard.py      # JWT authentication decorator
│       └── routes/
│           ├── paystack.py      # General Paystack routes
│           ├── C2B.py           # Customer-to-Business payments
│           ├── B2C.py           # Business-to-Customer payouts
│           └── AAA.py           # Authentication routes
├── run.py                       # Application entry point
├── pyproject.toml              # Dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Installation

### Prerequisites
- Python 3.13+
- PostgreSQL
- Redis (for rate limiting)
- **Paystack account (Kenya)** - [Sign up here](https://paystack.com/ke)

### Setup Steps

1. **Clone the repository**
```bash
cd /mnt/sub0_2/projectX/backend
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -e .
# or using uv:
uv pip install -e .
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

5. **Set up PostgreSQL database**
```bash
# Create database
createdb payment_gateway

# Or using psql:
psql -U postgres
CREATE DATABASE payment_gateway;
```

6. **Initialize database**
```bash
# Run migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Or let the app create tables automatically on first run
python run.py
```

7. **Start Redis** (for rate limiting)
```bash
redis-server
```

## Running the Application

### Development Mode
```bash
python run.py
```

The application will start on `http://localhost:5000`

### Production Mode
```bash
export FLASK_DEBUG=False
gunicorn -w 4 -b 0.0.0.0:5000 "src.app.main:app"
```

## API Documentation

### Base URL
```
http://localhost:5000/api/v1
```

### Authentication Endpoints (`/auth`)

#### 1. Sign Up
```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe",
  "phone_number": "+2348012345678"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "phone_number": "+2348012345678"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### 2. Sign In
```http
POST /api/v1/auth/signin
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### 3. Verify Token
```http
POST /api/v1/auth/verify-token
Content-Type: application/json

{
  "token": "your-jwt-token"
}
```

#### 4. Change Password
```http
POST /api/v1/auth/change-password
Content-Type: application/json

{
  "token": "your-jwt-token",
  "old_password": "oldpassword",
  "new_password": "newpassword123"
}
```

### C2B Endpoints (Receive Payments) (`/c2b`)

#### 1. Initialize M-Pesa Payment (Simplified - Kenya)
```http
POST /api/v1/c2b/mpesa/initialize
Content-Type: application/json

{
  "phone_number": "254712345678",
  "email": "customer@example.com",
  "amount": 100,
  "description": "Payment for Order #123"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "M-Pesa payment initialized",
  "data": {
    "authorization_url": "https://checkout.paystack.com/xyz123",
    "access_code": "xyz123abc",
    "reference": "MPESA-ABC123",
    "amount_kes": 100.0,
    "phone_number": "254712345678",
    "instructions": "Customer will receive M-Pesa prompt on their phone"
  }
}
```

#### 2. Initialize Payment (Full Options)
```http
POST /api/v1/c2b/initialize
Content-Type: application/json

{
  "email": "customer@example.com",
  "phone_number": "254712345678",
  "amount": 10000,
  "currency": "KES",
  "description": "Payment for Order #123",
  "channels": ["mobile_money"],
  "callback_url": "https://yoursite.com/payment/callback",
  "metadata": {
    "order_id": "123"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Payment initialized",
  "data": {
    "authorization_url": "https://checkout.paystack.com/xyz123",
    "access_code": "xyz123abc",
    "reference": "C2B-ABC123DEF456"
  }
}
```

#### 3. Verify Payment
```http
GET /api/v1/c2b/verify/{reference}
```

#### 3. Charge Saved Authorization (Recurring Payments)
```http
POST /api/v1/c2b/charge
Content-Type: application/json

{
  "email": "customer@example.com",
  "amount": 10000,
  "authorization_code": "AUTH_xyz123",
  "currency": "KES"
}
```

#### 4. List Payments
```http
GET /api/v1/c2b/payments?status=SUCCESS&page=1&per_page=20
```

## 🇰🇪 M-Pesa Integration Details

### Phone Number Format
Phone numbers must be in format: **254XXXXXXXXX** (12 digits, no `+` sign)

Examples:
- Safaricom: `254712345678`
- Airtel: `254733456789`

### Amount Format
- Amount in KES (e.g., `100` for KES 100)
- System automatically converts to cents for Paystack

### Payment Flow
1. Initialize M-Pesa payment → Customer gets STK push on phone
2. Customer enters M-Pesa PIN
3. Payment processes
4. Webhook notifies your system
5. Verify payment status

**See [KENYA_MPESA_GUIDE.md](KENYA_MPESA_GUIDE.md) for complete M-Pesa documentation.**

### B2C Endpoints (Payouts & Refunds) (`/b2c`)

#### 1. Initiate Transfer/Payout
```http
POST /api/v1/b2c/transfer/initiate
Content-Type: application/json

{
  "type": "nuban",
  "name": "John Doe",
  "account_number": "0123456789",
  "bank_code": "058",
  "amount": 50000,
  "currency": "NGN",
  "reason": "Freelance payment"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Transfer initiated",
  "data": {
    "id": 1,
    "reference": "TRF-ABC123",
    "amount": 50000,
    "status": "PENDING",
    "account_number": "0123456789",
    "account_name": "John Doe"
  }
}
```

#### 2. Verify Transfer
```http
GET /api/v1/b2c/transfer/verify/{reference}
```

#### 3. Process Refund
```http
POST /api/v1/b2c/refund
Content-Type: application/json

{
  "transaction_reference": "C2B-ABC123DEF456",
  "amount": 50000,
  "currency": "NGN",
  "customer_note": "Refund for cancelled order",
  "merchant_note": "Customer requested cancellation"
}
```

#### 4. List Transfers
```http
GET /api/v1/b2c/transfers?status=SUCCESS&page=1&per_page=20
```

#### 5. List Refunds
```http
GET /api/v1/b2c/refunds?status=SUCCESS&page=1&per_page=20
```

### Paystack General Endpoints (`/paystack`)

#### 1. Initialize Transaction
```http
POST /api/v1/paystack/initialize
Content-Type: application/json

{
  "email": "customer@example.com",
  "amount": 10000,
  "currency": "NGN"
}
```

#### 2. Verify Transaction
```http
GET /api/v1/paystack/verify/{reference}
```

#### 3. Webhook Handler
```http
POST /api/v1/paystack/webhook
X-Paystack-Signature: signature-from-paystack
Content-Type: application/json

{
  "event": "charge.success",
  "data": {
    ...
  }
}
```

#### 4. List Transactions
```http
GET /api/v1/paystack/transactions?status=SUCCESS&page=1&per_page=20
```

### Health Check Endpoints

#### 1. Root Endpoint
```http
GET /
```

**Response:**
```json
{
  "status": "success",
  "message": "Payment Gateway API is running",
  "version": "1.0.0"
}
```

#### 2. Health Check
```http
GET /health
```

## Webhook Configuration

To receive real-time payment updates, configure webhooks in your Paystack dashboard:

1. Go to Settings → Webhooks in your Paystack dashboard
2. Add webhook URL: `https://yourdomain.com/api/v1/paystack/webhook`
3. The application automatically verifies webhook signatures

**Supported Events:**
- `charge.success` - Payment successful
- `transfer.success` - Transfer successful
- `transfer.failed` - Transfer failed
- `refund.processed` - Refund completed

## Database Models

### Payment
Stores all payment transactions (both Paystack and M-Pesa)
- Common fields: amount, currency, status, provider
- Paystack fields: reference, access_code, authorization_code
- M-Pesa fields: merchant_request_id, checkout_request_id

### Transfer
Stores payout/transfer records
- Recipient details: account_number, bank_code, recipient_code
- Transfer tracking: status, reference, transfer_code

### Refund
Stores refund transactions
- Links to original payment
- Tracks refund status and amount

### User
Stores user accounts
- Authentication: email, password_hash
- JWT token management

## Security Best Practices

1. **Environment Variables**: Never commit `.env` file
2. **Secret Keys**: Use strong, random secret keys
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Configured via Redis
5. **Webhook Verification**: Always verify Paystack signatures
6. **Password Policy**: Minimum 8 characters enforced

## Testing with Paystack (Kenya)

### Test Mode
Use test API keys from Paystack Kenya dashboard.

### M-Pesa Test
Check Paystack Kenya documentation for test phone numbers and procedures.

### Test Bank Codes (Kenya)
- KCB Bank: 01
- Equity Bank: 68
- Co-operative Bank: 11
- MPESA: Use mobile_money channel

## Rate Limiting

Default limits:
- 20 requests per minute
- 2 requests per second
- 200 requests per day
- 50 requests per hour

Configure in `extensions.py` and `config.py`

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U postgres -h localhost -p 5432
```

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### Paystack API Errors
- Verify API keys are correct
- Check you're using test keys for development
- Ensure webhook signatures are being verified

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For Paystack integration issues, visit:
- [Paystack Documentation](https://paystack.com/docs)
- [Paystack Python Library](https://github.com/PaystackOSS/paystack-python)

For application issues, open an issue in the repository.

## Deployment

### Using Gunicorn (Production)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "src.app.main:app"
```

### Using Docker
```dockerfile
# Dockerfile example
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.app.main:app"]
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| SECRET_KEY | Flask secret key | supersecretkey | Yes |
| FLASK_DEBUG | Debug mode | True | No |
| PORT | Server port | 5000 | No |
| JWT_EXPIRATION_DELTA | JWT token lifetime (seconds) | 3600 | No |
| POSTGRES_HOST | PostgreSQL host | localhost | Yes |
| POSTGRES_PORT | PostgreSQL port | 5432 | Yes |
| POSTGRES_USER | Database user | postgres | Yes |
| POSTGRES_PASSWORD | Database password | - | Yes |
| POSTGRES_DB | Database name | payment_gateway | Yes |
| PAYSTACK_SECRET_KEY | Paystack secret key | - | Yes |
| PAYSTACK_PUBLIC_KEY | Paystack public key | - | No |
| REDIS_URL | Redis connection URL | redis://localhost:6379 | Yes |

## Next Steps

1. Set up your Paystack account and get API keys
2. Configure your database and Redis
3. Customize the payment flows for your use case
4. Implement additional features:
   - Email notifications
   - SMS notifications
   - Admin dashboard
   - Payment analytics
   - Subscription management
   - Multi-currency support

