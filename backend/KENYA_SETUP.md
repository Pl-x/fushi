# Kenya M-Pesa Setup - Complete Guide

## ✅ What's Been Configured for Kenya

Your payment gateway is now fully configured for **M-Pesa payments in Kenya** using Paystack:

### 1. M-Pesa Payment Collection ✓
- Simplified endpoint: `POST /api/v1/c2b/mpesa/initialize`
- Phone number validation (254XXXXXXXXX format)
- Automatic KES to cents conversion
- Mobile money channel pre-configured

### 2. Database Models ✓
- Phone number field for M-Pesa
- KES currency support
- Mobile money channel tracking
- Paystack and M-Pesa field support

### 3. API Endpoints ✓
- M-Pesa specific initialization
- Payment verification
- Transaction listing
- Webhook handling

## Quick Setup for Kenya

### 1. Install Dependencies
```bash
cd /mnt/sub0_2/projectX/backend
pip install -e .
```

### 2. Get Paystack Kenya Account
1. Visit: https://paystack.com/ke
2. Sign up with Kenyan business details
3. Get test API keys from dashboard

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```env
SECRET_KEY=your-secret-key-here
PAYSTACK_SECRET_KEY=sk_test_your_kenya_key
DEFAULT_CURRENCY=KES
POSTGRES_PASSWORD=your-db-password
```

### 4. Set Up Database
```bash
createdb payment_gateway
```

### 5. Start Services
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start App
python run.py
```

## Test M-Pesa Payment

### Using cURL
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

### Expected Response
```json
{
  "status": "success",
  "message": "M-Pesa payment initialized",
  "data": {
    "authorization_url": "https://checkout.paystack.com/xyz",
    "reference": "MPESA-ABC123",
    "amount_kes": 100.0,
    "phone_number": "254712345678"
  }
}
```

## Phone Number Format

✅ **Correct Formats:**
- `254712345678` (Safaricom)
- `254733456789` (Safaricom)
- `254755123456` (Airtel Money)

❌ **Wrong Formats:**
- `+254712345678` (remove +)
- `0712345678` (must include 254)
- `712345678` (must include 254)

## Available Endpoints

### M-Pesa Specific
```
POST   /api/v1/c2b/mpesa/initialize     - Initialize M-Pesa payment
GET    /api/v1/c2b/verify/{reference}   - Verify payment
GET    /api/v1/c2b/payments              - List all payments
```

### General Payments
```
POST   /api/v1/c2b/initialize            - Initialize with full options
POST   /api/v1/c2b/charge                - Recurring payments
```

### Payouts (Send Money)
```
POST   /api/v1/b2c/transfer/initiate     - Send money to M-Pesa
GET    /api/v1/b2c/transfer/verify/{ref} - Verify transfer
```

### Refunds
```
POST   /api/v1/b2c/refund                - Process refund
GET    /api/v1/b2c/refunds               - List refunds
```

### Authentication
```
POST   /api/v1/auth/signup               - Register user
POST   /api/v1/auth/signin               - Login user
POST   /api/v1/auth/verify-token         - Verify JWT token
```

## Payment Flow

1. **Initialize Payment**
   - Customer provides phone number and amount
   - Your app calls `/c2b/mpesa/initialize`
   - Paystack returns authorization URL

2. **Customer Pays**
   - Customer visits authorization URL
   - Receives STK push on phone
   - Enters M-Pesa PIN

3. **Webhook Notification**
   - Paystack sends webhook to your server
   - Payment status updated automatically

4. **Verify Payment**
   - Call `/c2b/verify/{reference}`
   - Get final payment status

## Testing Checklist

- [ ] Health check works: `curl http://localhost:5000/health`
- [ ] Can create user account
- [ ] Can initialize M-Pesa payment
- [ ] Payment reference is returned
- [ ] Can verify payment status
- [ ] Webhook endpoint is accessible

## Going Live

### 1. Complete Paystack KYC
- Submit business documents
- Wait for approval (usually 2-3 days)

### 2. Switch to Live Keys
```env
PAYSTACK_SECRET_KEY=sk_live_your_live_key
```

### 3. Configure Webhook
In Paystack Dashboard:
- URL: `https://yourdomain.com/api/v1/paystack/webhook`
- Events: All payment events

### 4. Set Up HTTPS
- Get SSL certificate (Let's Encrypt)
- Configure reverse proxy (Nginx)
- Update webhook URL to HTTPS

### 5. Test with Real Money
- Start with small amounts (KES 1)
- Test full payment flow
- Verify webhook notifications

## M-Pesa Transaction Limits

### Standard M-Pesa Account
- Minimum: KES 1
- Maximum per transaction: KES 150,000
- Daily limit: KES 300,000

### Business Account
- Higher limits available
- Check with Safaricom

## Fees

### Paystack Fees (Kenya)
Check current rates: https://paystack.com/ke/pricing
- Typically: ~2.9% + KES 30 per transaction

### M-Pesa Charges
- Customer pays M-Pesa transaction fees
- Variable based on amount
- See: https://www.safaricom.co.ke/mpesa_rates

## Troubleshooting

### "Paystack not configured"
- Check `PAYSTACK_SECRET_KEY` in `.env`
- Ensure no spaces in the key
- Restart the application

### "Database connection error"
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Create database: `createdb payment_gateway`

### "Redis connection error"
- Start Redis: `redis-server`
- Check Redis is running: `redis-cli ping`

### Phone number rejected
- Must be exactly 12 digits
- Must start with 254
- No spaces or special characters

## Documentation Files

1. **KENYA_MPESA_GUIDE.md** - Comprehensive M-Pesa integration guide
2. **README.md** - Full API documentation
3. **QUICKSTART.md** - 5-minute setup guide
4. **KENYA_SETUP.md** - This file
5. **test_api.sh** - Automated testing script

## Support

### Paystack Kenya
- Website: https://paystack.com/ke
- Docs: https://paystack.com/docs/payments/mobile-money
- Email: support@paystack.com

### M-Pesa Kenya
- Website: https://www.safaricom.co.ke/personal/m-pesa
- Support: Dial *234# or call 100

### Technical Support
- Check logs: `tail -f logs/app.log`
- Test webhook: Use ngrok for local testing
- Postman collection: `api_collection.json`

## Next Steps

1. ✅ Set up Paystack Kenya account
2. ✅ Get test API keys
3. ✅ Configure `.env` file
4. ✅ Start the application
5. ✅ Test M-Pesa payment
6. ⏳ Complete KYC verification
7. ⏳ Go live with real payments

## Example Integration (Frontend)

```javascript
// Initialize M-Pesa payment
async function payWithMpesa() {
  const response = await fetch('/api/v1/c2b/mpesa/initialize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: '254712345678',
      email: 'customer@example.com',
      amount: 100,
      description: 'Payment for order'
    })
  });
  
  const data = await response.json();
  
  if (data.status === 'success') {
    // Redirect to Paystack checkout
    window.location.href = data.data.authorization_url;
  }
}
```

## Production Deployment

### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "src.app.main:app"
```

### Using Docker
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.app.main:app"]
```

### Environment Variables (Production)
```env
FLASK_DEBUG=False
PAYSTACK_SECRET_KEY=sk_live_xxxxx
SECRET_KEY=<strong-random-key>
POSTGRES_HOST=<db-host>
REDIS_URL=redis://<redis-host>:6379
```

## Success! 🎉

Your M-Pesa payment gateway is ready for Kenya! Start testing and accepting payments.

**Happy coding!** 🇰🇪 🚀
