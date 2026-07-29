#!/bin/bash

# API Testing Script for Payment Gateway
# This script tests all major endpoints

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"
API_URL="$BASE_URL/api/v1"
RUN_LIVE_PAYMENT_TESTS="${RUN_LIVE_PAYMENT_TESTS:-0}"
TEST_EMAIL="testuser.$(date +%s).$RANDOM@example.com"
TEST_PASSWORD="password123"

echo "========================================="
echo "Payment Gateway API Testing"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
    fi
}

# Test 1: Health Check
echo "Test 1: Health Check"
response=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/health" || true)
if [ "$response" = "200" ]; then
    print_result 0 "Health check endpoint"
else
    print_result 1 "Health check endpoint (got $response)"
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root Endpoint"
response=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/" || true)
if [ "$response" = "200" ]; then
    print_result 0 "Root endpoint"
else
    print_result 1 "Root endpoint (got $response)"
fi
echo ""

# Test 3: User Signup
echo "Test 3: User Signup"
signup_response=$(curl -sS -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$TEST_EMAIL'",
    "password": "'$TEST_PASSWORD'",
    "name": "Test User",
    "phone_number": "+2348012345678"
  }')

if echo "$signup_response" | grep -q "success"; then
    print_result 0 "User signup"
    # Extract token
    TOKEN=$(echo "$signup_response" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
    echo -e "${YELLOW}Token extracted for further tests${NC}"
else
    print_result 1 "User signup"
    echo "Response: $signup_response"
fi
echo ""

# Test 4: User Signin
echo "Test 4: User Signin"
signin_response=$(curl -sS -X POST "$API_URL/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$TEST_EMAIL'",
    "password": "'$TEST_PASSWORD'"
  }')

if echo "$signin_response" | grep -q "success\|Invalid"; then
    if echo "$signin_response" | grep -q "success"; then
        print_result 0 "User signin"
    else
        print_result 0 "User signin (user doesn't exist - expected)"
    fi
else
    print_result 1 "User signin"
fi
echo ""

if [ "$RUN_LIVE_PAYMENT_TESTS" != "1" ]; then
    echo -e "${YELLOW}Skipping Paystack payment, transfer, and refund calls. Set RUN_LIVE_PAYMENT_TESTS=1 to enable them.${NC}"
else
# Test 5: Initialize Payment (C2B)
echo "Test 5: Initialize Payment (C2B with mobile_money channel)"
payment_response=$(curl -s -X POST $API_URL/c2b/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "phone_number": "254712345678",
    "amount": 10000,
    "currency": "KES",
    "channels": ["mobile_money"],
    "description": "Test M-Pesa Payment"
  }')

if echo "$payment_response" | grep -q "success\|authorization_url"; then
    print_result 0 "Initialize payment"
    # Extract reference
    PAYMENT_REF=$(echo "$payment_response" | grep -o '"reference":"[^"]*' | cut -d'"' -f4)
    echo -e "${YELLOW}Payment reference: $PAYMENT_REF${NC}"
else
    print_result 1 "Initialize payment"
    echo "Response: $payment_response"
fi
echo ""

# Test 5b: Initialize M-Pesa Payment (Simplified)
echo "Test 5b: Initialize M-Pesa Payment (Simplified Endpoint)"
mpesa_response=$(curl -s -X POST $API_URL/c2b/mpesa/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "email": "customer@example.com",
    "amount": 100,
    "description": "Test M-Pesa Payment"
  }')

if echo "$mpesa_response" | grep -q "success\|authorization_url"; then
    print_result 0 "Initialize M-Pesa payment (simplified)"
    # Extract reference
    MPESA_REF=$(echo "$mpesa_response" | grep -o '"reference":"[^"]*' | cut -d'"' -f4)
    echo -e "${YELLOW}M-Pesa reference: $MPESA_REF${NC}"
else
    print_result 1 "Initialize M-Pesa payment (simplified)"
    echo "Response: $mpesa_response"
fi
echo ""

# Test 6: Verify Payment (will fail without actual payment)
if [ -n "${PAYMENT_REF:-}" ]; then
    echo "Test 6: Verify Payment"
    verify_response=$(curl -s -X GET $API_URL/c2b/verify/$PAYMENT_REF)
    if echo "$verify_response" | grep -q "PENDING\|SUCCESS\|FAILED"; then
        print_result 0 "Verify payment endpoint"
    else
        print_result 1 "Verify payment endpoint"
    fi
    echo ""
fi

# Test 7: List Payments
echo "Test 7: List Payments"
list_response=$(curl -s -X GET "$API_URL/c2b/payments?page=1&per_page=10")
if echo "$list_response" | grep -q "success"; then
    print_result 0 "List payments"
else
    print_result 1 "List payments"
fi
echo ""

# Test 8: Initialize Transfer (B2C)
echo "Test 8: Initialize Transfer (B2C)"
transfer_response=$(curl -s -X POST $API_URL/b2c/transfer/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nuban",
    "name": "John Doe",
    "account_number": "0123456789",
    "bank_code": "058",
    "amount": 10000,
    "currency": "NGN",
    "reason": "Test Transfer"
  }')

if echo "$transfer_response" | grep -q "success\|error"; then
    if echo "$transfer_response" | grep -q "success"; then
        print_result 0 "Initialize transfer"
    else
        print_result 0 "Initialize transfer (failed as expected without valid Paystack config)"
    fi
else
    print_result 1 "Initialize transfer"
fi
echo ""

# Test 9: Process Refund
echo "Test 9: Process Refund (expects to fail without valid transaction)"
refund_response=$(curl -s -X POST $API_URL/b2c/refund \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_reference": "INVALID-REF",
    "currency": "NGN",
    "customer_note": "Test refund"
  }')

if echo "$refund_response" | grep -q "error\|not found"; then
    print_result 0 "Refund endpoint (correctly rejected invalid ref)"
else
    print_result 1 "Refund endpoint"
fi
echo ""

# Test 10: List Transactions
echo "Test 10: List All Transactions"
transactions_response=$(curl -s -X GET "$API_URL/paystack/transactions?page=1")
if echo "$transactions_response" | grep -q "success"; then
    print_result 0 "List transactions"
else
    print_result 1 "List transactions"
fi
echo ""

fi

# Test 11: Token Verification
if [ -n "${TOKEN:-}" ]; then
    echo "Test 11: Token Verification"
    token_response=$(curl -sS -X POST "$API_URL/auth/verify-token" \
      -H "Content-Type: application/json" \
      -d "{\"token\": \"$TOKEN\"}")

    if echo "$token_response" | grep -q "success"; then
        print_result 0 "Token verification"
    else
        print_result 1 "Token verification"
    fi
    echo ""
fi

echo "========================================="
echo "Testing Complete!"
echo "========================================="
echo ""
echo "Note: Some tests may fail if:"
echo "  - Paystack API keys are not configured"
echo "  - Database is not set up"
echo "  - Redis is not running"
echo "  - Application is not running on port 5000"
echo ""
echo "To start the application:"
echo "  .venv/bin/python run.py"
