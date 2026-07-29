# API reference

Development base URL: `http://localhost:5000`. All `POST` bodies use JSON.

## Pages

`GET /`, `/health`, `/welcome`, `/signin`, `/signup`, `/dashboard`, `/hotels`, `/review`, and `/receipt` are implemented by `create_app` in `src/app/config.py`.

## API routes

| Prefix | Routes and functions |
| --- | --- |
| `/api/v1/auth` | `POST /signup` (`signup`), `/signin` (`signin`), `/verify-token` (`verify_token`), `/change-password` (`change_password`), `/forgot-password` (`forgot_password`); `GET /users` (`list_users`). |
| `/api/v1/c2b` | `POST /initialize` (`initialize_payment`), `/mpesa/initialize` (`initialize_mpesa`), `/charge` (`charge_authorization`); `GET /verify/<reference>` (`verify_payment`), `/payments` (`list_payments`), `/payment/<id>` (`get_payment`). |
| `/api/v1/b2c` | `POST /transfer/initiate` (`initiate_transfer`), `/refund` (`process_refund`); `GET /transfer/verify/<reference>` (`verify_transfer`), `/transfers` (`list_transfers`), `/refunds` (`list_refunds`). |
| `/api/v1/paystack` | `POST /initialize` (`initialize_transaction`), `/webhook` (`webhook`); `GET /verify/<reference>` (`verify_transaction`), `/transactions` (`list_transactions`), `/transaction/<id>` (`get_transaction`). |

## Request contracts

- Sign-up: `email`, `password` (8+ characters), `name`; `phone_number` optional.
- Sign-in: `email`, `password`.
- Paystack checkout: `email`, `amount`; optional `currency`, `reference`, `callback_url`, `metadata`, `channels`.
- M-Pesa checkout: `email`, `phone_number` in `254XXXXXXXXX` format, `amount` in KES.
- Transfer: `type`, `name`, `account_number`, `amount`; `bank_code`, `currency`, `reason`, and `reference` optional.
- Refund: `transaction_reference`; `amount`, `currency`, `customer_note`, and `merchant_note` optional.

## Supporting functions

- Authentication helpers: `hash_password`, `verify_password`, `generate_jwt_token`, `verify_jwt_token` in `src/app/routes/AAA.py`.
- Webhook helper: `verify_paystack_signature(payload, signature)` in `src/app/routes/paystack.py`; it validates `X-Paystack-Signature` with HMAC-SHA512.
- Paystack HTTP client: `transaction.initialize`, `transaction.verify`, `transaction.charge`, `transfer_recipient.create`, `transfer.initiate`, `transfer.verify`, and `refund.create` in `src/app/paystack_client.py`.

## Configuration

Set `PAYSTACK_SECRET_KEY` to `sk_test_...` in development, `RATELIMIT_STORAGE_URI=redis://localhost:6379`, and `AUTO_CREATE_SCHEMA=true`. Gunicorn startup uses a PostgreSQL advisory lock before creating missing development tables.

## Idempotency

`Payment`, `Transfer`, and `Refund` persist an `idempotency_key` with a database unique constraint. Supply it as JSON `idempotency_key` or an `Idempotency-Key` header for all retry-sensitive money operations.
