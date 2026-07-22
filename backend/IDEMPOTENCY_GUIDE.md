# Idempotency Guide

## What is Idempotency?

Idempotency ensures that performing the same operation multiple times has the same effect as performing it once. This is critical for payment systems to prevent:

- **Duplicate charges** due to network retries
- **Multiple transfers** from button double-clicks
- **Repeated refunds** from retry logic

## How It Works

### 1. Client Generates Unique Key
The client creates a unique idempotency key for each distinct operation:

```python
import uuid

idempotency_key = f"payment-{uuid.uuid4()}"
```

### 2. Include Key in Request
Send the key either in the request body or header:

**Option A: Request Body**
```json
{
  "phone_number": "254712345678",
  "email": "customer@example.com",
  "amount": 100,
  "idempotency_key": "payment-abc123def456"
}
```

**Option B: HTTP Header**
```http
POST /api/v1/c2b/mpesa/initialize
Idempotency-Key: payment-abc123def456
Content-Type: application/json

{
  "phone_number": "254712345678",
  "email": "customer@example.com",
  "amount": 100
}
```

### 3. Server Checks for Duplicate
The server checks if a transaction with this idempotency key already exists:

- **First Request**: Creates new transaction, stores idempotency key
- **Duplicate Request**: Returns the existing transaction (no new charge)

## Supported Endpoints

### ✅ Payment Collection (C2B)

#### 1. Initialize Payment
```http
POST /api/v1/c2b/initialize
Idempotency-Key: payment-abc123

{
  "email": "customer@example.com",
  "phone_number": "254712345678",
  "amount": 10000,
  "currency": "KES"
}
```

#### 2. Initialize M-Pesa Payment
```http
POST /api/v1/c2b/mpesa/initialize
Idempotency-Key: mpesa-payment-xyz789

{
  "phone_number": "254712345678",
  "email": "customer@example.com",
  "amount": 100
}
```

### ✅ Transfers/Payouts (B2C)

#### 3. Initiate Transfer
```http
POST /api/v1/b2c/transfer/initiate
Idempotency-Key: transfer-payout-123

{
  "type": "mobile_money",
  "name": "John Doe",
  "account_number": "254712345678",
  "amount": 50000,
  "currency": "KES"
}
```

### ✅ Refunds

#### 4. Process Refund
```http
POST /api/v1/b2c/refund
Idempotency-Key: refund-order-456

{
  "transaction_reference": "MPESA-ABC123",
  "customer_note": "Refund for cancelled order"
}
```

## Response Format

### First Request (New Transaction)
```json
{
  "status": "success",
  "message": "M-Pesa payment initialized",
  "data": {
    "reference": "MPESA-ABC123",
    "payment_id": 1,
    "amount_kes": 100.0,
    ...
  }
}
```

### Duplicate Request (Idempotent)
```json
{
  "status": "success",
  "message": "M-Pesa payment already initialized (idempotent)",
  "data": {
    "reference": "MPESA-ABC123",
    "payment_id": 1,
    "amount_kes": 100.0,
    "idempotent": true,
    ...
  }
}
```

**Key difference**: `"idempotent": true` flag indicates this is a duplicate request.

## Best Practices

### 1. Generate Unique Keys
Use a combination that ensures uniqueness:

```python
# Good: UUID-based
idempotency_key = f"payment-{uuid.uuid4()}"

# Good: Order-based (one payment per order)
idempotency_key = f"order-{order_id}-payment"

# Good: Timestamp + Random
import time
idempotency_key = f"payment-{int(time.time())}-{uuid.uuid4().hex[:8]}"

# Bad: Not unique enough
idempotency_key = "payment-1"  # Will conflict!
```

### 2. Store Keys on Client
Keep track of idempotency keys to handle retries:

```python
class PaymentClient:
    def __init__(self):
        self.pending_payments = {}  # order_id -> idempotency_key
    
    def create_payment(self, order_id, amount):
        # Reuse key for same order
        if order_id in self.pending_payments:
            key = self.pending_payments[order_id]
        else:
            key = f"order-{order_id}-payment-{uuid.uuid4()}"
            self.pending_payments[order_id] = key
        
        response = requests.post(
            '/api/v1/c2b/mpesa/initialize',
            headers={'Idempotency-Key': key},
            json={'amount': amount, ...}
        )
        
        if response.status_code == 200:
            # Clear key after success
            self.pending_payments.pop(order_id, None)
        
        return response.json()
```

### 3. Handle Network Retries
Use idempotency keys with retry logic:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def initialize_payment_with_retry(phone, email, amount):
    idempotency_key = f"payment-{uuid.uuid4()}"
    
    response = requests.post(
        'http://localhost:5000/api/v1/c2b/mpesa/initialize',
        headers={'Idempotency-Key': idempotency_key},
        json={
            'phone_number': phone,
            'email': email,
            'amount': amount
        }
    )
    
    response.raise_for_status()
    return response.json()
```

### 4. Frontend Implementation

#### React Example
```jsx
import { v4 as uuidv4 } from 'uuid';

function PaymentForm() {
  const [idempotencyKey, setIdempotencyKey] = useState(null);
  
  const handlePayment = async () => {
    // Generate key once per payment attempt
    const key = idempotencyKey || `payment-${uuidv4()}`;
    setIdempotencyKey(key);
    
    try {
      const response = await fetch('/api/v1/c2b/mpesa/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': key
        },
        body: JSON.stringify({
          phone_number: phone,
          email: email,
          amount: amount
        })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        // Payment successful, clear key for next payment
        setIdempotencyKey(null);
        window.location.href = data.data.authorization_url;
      }
    } catch (error) {
      // Network error - key is preserved for retry
      console.error('Payment failed:', error);
    }
  };
  
  return (
    <button onClick={handlePayment}>
      Pay with M-Pesa
    </button>
  );
}
```

#### JavaScript/Vanilla
```javascript
class PaymentManager {
  constructor() {
    this.currentKey = null;
  }
  
  generateKey() {
    if (!this.currentKey) {
      this.currentKey = `payment-${this.uuidv4()}`;
    }
    return this.currentKey;
  }
  
  clearKey() {
    this.currentKey = null;
  }
  
  async initializePayment(phone, email, amount) {
    const key = this.generateKey();
    
    const response = await fetch('/api/v1/c2b/mpesa/initialize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': key
      },
      body: JSON.stringify({ phone_number: phone, email, amount })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      this.clearKey();
    }
    
    return data;
  }
  
  uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}
```

## Common Scenarios

### Scenario 1: Network Timeout
```
1. Client sends payment request with key: payment-abc123
2. Network timeout occurs
3. Client retries with SAME key: payment-abc123
4. Server finds existing transaction, returns it
✅ No duplicate charge
```

### Scenario 2: Double-Click Prevention
```
1. User clicks "Pay" button
2. First request sent with key: payment-xyz789
3. User accidentally clicks again
4. Second request sent with SAME key: payment-xyz789
5. Server finds existing transaction, returns it
✅ No duplicate charge
```

### Scenario 3: Concurrent Requests
```
1. Two requests arrive simultaneously with same key
2. Database uniqueness constraint ensures only one is created
3. Second request gets existing transaction
✅ No duplicate charge
```

## Key Expiration

Idempotency keys are stored permanently in the database. This ensures:

- **Historical audit trail** - Track all idempotent requests
- **Long-term retry safety** - Even delayed retries are caught
- **Compliance** - Maintain records for reconciliation

If you need to process the same transaction again (e.g., new order for same customer), use a **new idempotency key**.

## Testing Idempotency

### Test 1: Basic Idempotency
```bash
# First request
curl -X POST http://localhost:5000/api/v1/c2b/mpesa/initialize \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-payment-001" \
  -d '{
    "phone_number": "254712345678",
    "email": "test@example.com",
    "amount": 100
  }'

# Duplicate request (same key)
curl -X POST http://localhost:5000/api/v1/c2b/mpesa/initialize \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-payment-001" \
  -d '{
    "phone_number": "254712345678",
    "email": "test@example.com",
    "amount": 100
  }'

# Expected: Both return same transaction
```

### Test 2: Different Keys
```bash
# First payment
curl -X POST http://localhost:5000/api/v1/c2b/mpesa/initialize \
  -H "Idempotency-Key: test-payment-001" \
  ...

# Second payment (different key)
curl -X POST http://localhost:5000/api/v1/c2b/mpesa/initialize \
  -H "Idempotency-Key: test-payment-002" \
  ...

# Expected: Two separate transactions created
```

### Test 3: Refund Idempotency
```bash
# First refund attempt
curl -X POST http://localhost:5000/api/v1/b2c/refund \
  -H "Idempotency-Key: refund-order-123" \
  -d '{
    "transaction_reference": "MPESA-ABC123"
  }'

# Duplicate refund attempt
curl -X POST http://localhost:5000/api/v1/b2c/refund \
  -H "Idempotency-Key: refund-order-123" \
  -d '{
    "transaction_reference": "MPESA-ABC123"
  }'

# Expected: Only one refund processed
```

## Database Schema

The idempotency key is stored in the database models:

```sql
-- Payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(100) UNIQUE,
    ...
);

-- Transfers table
CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(100) UNIQUE,
    ...
);

-- Refunds table
CREATE TABLE refunds (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(100) UNIQUE,
    ...
);
```

The `UNIQUE` constraint ensures no duplicate keys can be inserted.

## Troubleshooting

### Issue: "Duplicate key value violates unique constraint"
**Cause**: Same idempotency key used twice  
**Solution**: This is expected behavior! The second request returns the existing transaction.

### Issue: Key not working as expected
**Check**:
1. Key is exactly the same in both requests
2. Key is not null or empty
3. No trailing spaces in the key
4. Using correct endpoint

### Issue: Want to retry failed transaction
**Solution**: 
- If transaction failed, you can reuse the same key
- If transaction succeeded, use a NEW key

## Security Considerations

1. **Key Format**: Use UUIDs or similar to prevent guessing
2. **Key Length**: Min 20 characters recommended
3. **Namespace**: Include operation type in key (`payment-`, `transfer-`, etc.)
4. **Audit**: All idempotent requests are logged

## Summary

✅ **Do:**
- Generate unique keys per transaction
- Store keys for retry scenarios
- Use keys in headers or body
- Keep keys client-side until success

❌ **Don't:**
- Reuse keys for different operations
- Use predictable keys (e.g., sequential numbers)
- Rely on keys for authentication
- Share keys between different users/sessions

## Further Reading

- [Stripe's Idempotency Guide](https://stripe.com/docs/api/idempotent_requests)
- [RFC 5789 - PATCH Method](https://tools.ietf.org/html/rfc5789)
- [Designing Idempotent APIs](https://blog.stripe.com/idempotency)

---

**Your payment gateway now supports full idempotency!** 🎉

Use idempotency keys in all payment, transfer, and refund operations to ensure safe retries and prevent duplicate transactions.
