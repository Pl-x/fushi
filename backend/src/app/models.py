'''This is the database model for PostgreSQL using SQLAlchemy.'''
from .extensions import db
import datetime


class Payment(db.Model):
    '''Database model for payments - supports both M-Pesa and Paystack.'''
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    
    # Common fields
    phone_number = db.Column(db.String(20), nullable=True)  # For M-Pesa: 2547XXXXXXXX
    email = db.Column(db.String(100), nullable=True)  # For Paystack
    amount = db.Column(db.Integer, nullable=False)  # Amount in smallest currency unit (kobo/cents)
    currency = db.Column(db.String(3), default="NGN")  # NGN, KES, etc.
    status = db.Column(db.String(20), default="PENDING")  # PENDING, SUCCESS, FAILED, ABANDONED
    payment_provider = db.Column(db.String(20), nullable=False)  # PAYSTACK, MPESA
    account_reference = db.Column(db.String(100), nullable=False)
    transaction_desc = db.Column(db.String(255), nullable=False)
    
    # Idempotency key for preventing duplicate transactions
    idempotency_key = db.Column(db.String(100), unique=True, index=True, nullable=True)
    
    # M-Pesa Specific Fields
    result_code = db.Column(db.String(20), nullable=True)
    result_desc = db.Column(db.String(255), nullable=True)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    checkout_request_id = db.Column(db.String(100), nullable=True)
    
    # Paystack Specific Fields
    paystack_reference = db.Column(db.String(100), unique=True, nullable=True)  # Paystack transaction reference
    paystack_access_code = db.Column(db.String(100), nullable=True)  # For transaction initialization
    authorization_code = db.Column(db.String(100), nullable=True)  # For recurring charges
    customer_code = db.Column(db.String(100), nullable=True)  # Paystack customer code
    channel = db.Column(db.String(50), nullable=True)  # card, bank, ussd, qr, mobile_money, bank_transfer
    
    # Common tracking fields
    receipt_number = db.Column(db.String(50), nullable=True)  # Transaction receipt
    transaction_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.id} - {self.currency} {self.amount/100} - {self.status} - {self.payment_provider}>"

    def to_dict(self):
        """Convert payment object to dictionary"""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'email': self.email,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'payment_provider': self.payment_provider,
            'account_reference': self.account_reference,
            'transaction_desc': self.transaction_desc,
            'paystack_reference': self.paystack_reference,
            'receipt_number': self.receipt_number,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'created_at': self.created_at.isoformat(),
            'channel': self.channel,
            'idempotency_key': self.idempotency_key
        }


class customer(db.Model):
    '''Database model for customers.'''
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Customer {self.id} - {self.name} - {self.email}>"


class transaction(db.Model):
    '''Database model for transactions.'''
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey(
        'payments.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey(
        'customers.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    payment = db.relationship(
        'Payment', backref=db.backref('transactions', lazy=True))
    customer = db.relationship(
        'customer', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<Transaction {self.id} - Payment ID: {self.payment_id} - Customer ID: {self.customer_id}>"


class merchant(db.Model):
    '''Database model for merchants.'''
    __tablename__ = 'merchants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Merchant {self.id} - {self.name} - {self.email}>"


class merchant_transaction(db.Model):
    '''Database model for merchant transactions.'''
    __tablename__ = 'merchant_transactions'
    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey(
        'merchants.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey(
        'transactions.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    merchant = db.relationship('merchant', backref=db.backref(
        'merchant_transactions', lazy=True))
    transaction = db.relationship(
        'transaction', backref=db.backref('merchant_transactions', lazy=True))

    def __repr__(self):
        return f"<MerchantTransaction {self.id} - Merchant ID: {self.merchant_id} - Transaction ID: {self.transaction_id}>"


class payment_method(db.Model):
    '''Database model for payment methods.'''
    __tablename__ = 'payment_methods'
    id = db.Column(db.Integer, primary_key=True)
    method_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<PaymentMethod {self.id} - {self.method_name}>"


class payment_method_transaction(db.Model):
    '''Database model for payment method transactions.'''
    __tablename__ = 'payment_method_transactions'
    id = db.Column(db.Integer, primary_key=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey(
        'payment_methods.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey(
        'transactions.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    payment_method = db.relationship('payment_method', backref=db.backref(
        'payment_method_transactions', lazy=True))
    transaction = db.relationship('transaction', backref=db.backref(
        'payment_method_transactions', lazy=True))

    def __repr__(self):
        return f"<PaymentMethodTransaction {self.id} - Payment Method ID: {self.payment_method_id} - Transaction ID: {self.transaction_id}>"


class payment_status(db.Model):
    '''Database model for payment status.'''
    __tablename__ = 'payment_status'
    id = db.Column(db.Integer, primary_key=True)
    status_name = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<PaymentStatus {self.id} - {self.status_name}>"


class Transfer(db.Model):
    '''Database model for payouts/transfers (B2C).'''
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    
    # Idempotency key for preventing duplicate transfers
    idempotency_key = db.Column(db.String(100), unique=True, index=True, nullable=True)
    
    # Recipient details
    recipient_type = db.Column(db.String(20), nullable=False)  # nuban, mobile_money, basa, etc.
    recipient_code = db.Column(db.String(100), nullable=True)  # Paystack recipient code
    account_number = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100), nullable=True)
    bank_code = db.Column(db.String(20), nullable=True)  # Bank code for bank transfers
    
    # Transfer details
    amount = db.Column(db.Integer, nullable=False)  # Amount in kobo/cents
    currency = db.Column(db.String(3), default="NGN")
    reason = db.Column(db.String(255), nullable=True)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default="PENDING")  # PENDING, SUCCESS, FAILED, REVERSED
    transfer_code = db.Column(db.String(100), nullable=True)  # Paystack transfer code
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Transfer {self.id} - {self.currency} {self.amount/100} - {self.status}>"

    def to_dict(self):
        """Convert transfer object to dictionary"""
        return {
            'id': self.id,
            'recipient_type': self.recipient_type,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'amount': self.amount,
            'currency': self.currency,
            'reason': self.reason,
            'reference': self.reference,
            'status': self.status,
            'transfer_code': self.transfer_code,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'idempotency_key': self.idempotency_key
        }


class Refund(db.Model):
    '''Database model for refunds.'''
    __tablename__ = 'refunds'
    id = db.Column(db.Integer, primary_key=True)
    
    # Idempotency key for preventing duplicate refunds
    idempotency_key = db.Column(db.String(100), unique=True, index=True, nullable=True)
    
    # Reference to original payment
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    transaction_reference = db.Column(db.String(100), nullable=False)  # Original transaction ref
    
    # Refund details
    amount = db.Column(db.Integer, nullable=True)  # Amount to refund (null = full refund)
    currency = db.Column(db.String(3), default="NGN")
    merchant_note = db.Column(db.String(255), nullable=True)
    customer_note = db.Column(db.String(255), nullable=True)
    
    # Status tracking
    status = db.Column(db.String(20), default="PENDING")  # PENDING, PROCESSING, SUCCESS, FAILED
    refund_reference = db.Column(db.String(100), unique=True, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    payment = db.relationship('Payment', backref=db.backref('refunds', lazy=True))

    def __repr__(self):
        return f"<Refund {self.id} - Payment {self.payment_id} - {self.status}>"

    def to_dict(self):
        """Convert refund object to dictionary"""
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'transaction_reference': self.transaction_reference,
            'amount': self.amount,
            'currency': self.currency,
            'merchant_note': self.merchant_note,
            'customer_note': self.customer_note,
            'status': self.status,
            'refund_reference': self.refund_reference,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'idempotency_key': self.idempotency_key
        }


class User(db.Model):
    '''Database model for users (authentication).'''
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Administrative access is granted explicitly in the database; ordinary
    # users can never obtain it through the public signup route.
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.id} - {self.email}>"

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone_number': self.phone_number,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat()
        }


class ReviewerProfile(db.Model):
    __tablename__ = 'reviewer_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    username = db.Column(db.String(60), unique=True, nullable=False)
    location = db.Column(db.String(100), default='Nairobi, Kenya')
    user = db.relationship('User', backref=db.backref('reviewer_profile', uselist=False))

    def to_dict(self):
        return {'username': self.username, 'location': self.location}


class Hotel(db.Model):
    __tablename__ = 'hotels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, default=0)
    nightly_rate = db.Column(db.String(80), nullable=False)
    review_reward_cents = db.Column(db.Integer, default=102100, nullable=False)
    # Image search-result links can be long, and hosted image/CDN URLs do not
    # have a practical 500-character limit. Keep the complete source URL.
    image_url = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {key: getattr(self, key) for key in ('id', 'name', 'location', 'address', 'category', 'rating', 'nightly_rate', 'review_reward_cents', 'image_url', 'is_active')}


class HotelReview(db.Model):
    __tablename__ = 'hotel_reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    cleanliness = db.Column(db.Integer, nullable=False)
    service = db.Column(db.Integer, nullable=False)
    location_rating = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='APPROVED', nullable=False)
    # Amounts use the currency's minor unit. KES 1,021.00 is 102100 cents.
    reward_cents = db.Column(db.Integer, default=102100, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    hotel = db.relationship('Hotel')
    user = db.relationship('User')

    def to_dict(self):
        return {'id': self.id, 'hotel': self.hotel.name, 'hotel_id': self.hotel_id, 'status': self.status, 'reward_cents': self.reward_cents, 'created_at': self.created_at.isoformat()}


class PlatformSetting(db.Model):
    __tablename__ = 'platform_settings'
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(255), nullable=False)


class PayoutRequest(db.Model):
    __tablename__ = 'payout_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='PENDING', nullable=False)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User')
    transfer = db.relationship('Transfer')

    def to_dict(self):
        return {
            'id': self.id, 'amount_cents': self.amount_cents, 'status': self.status,
            'transfer_reference': self.transfer.reference if self.transfer else None,
            'created_at': self.created_at.isoformat(),
        }
