"""
C2B (Customer to Business) routes for receiving payments from customers
"""
import os
import logging
from flask import request, jsonify, Blueprint
from ..paystack_client import Paystack, InvalidDataError, UnwantedDataError
from ..extensions import db
from ..models import Payment
import datetime
import uuid

logger = logging.getLogger(__name__)

c2b_bp = Blueprint('c2b', __name__)

# Initialize Paystack client
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
paystack = Paystack(secret_key=PAYSTACK_SECRET_KEY) if PAYSTACK_SECRET_KEY else None


@c2b_bp.route("/initialize", methods=['POST'])
def initialize_payment():
    """
    Initialize a payment collection from customer (supports M-Pesa for Kenya)
    Expected payload:
    {
        "phone_number": "254712345678",  // For M-Pesa (optional if email provided)
        "email": "customer@email.com",  // Required
        "amount": 1000,  // Amount in cents (for KES: 1000 = 10 KES)
        "currency": "KES",  // Default KES for Kenya
        "description": "Payment for order #123",
        "callback_url": "https://yoursite.com/callback",
        "metadata": {
            "order_id": "123"
        },
        "channels": ["mobile_money"],  // For M-Pesa, use mobile_money channel
        "idempotency_key": "unique-key-123"  // Optional: for preventing duplicate payments
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        if not data.get('email'):
            return jsonify({'status': 'error', 'message': 'Email is required'}), 400
        
        if not data.get('amount'):
            return jsonify({'status': 'error', 'message': 'Amount is required'}), 400
        
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Check for idempotency key
        idempotency_key = data.get('idempotency_key') or request.headers.get('Idempotency-Key')
        
        if idempotency_key:
            # Check if we already processed this request
            existing_payment = Payment.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_payment:
                logger.info(f"Idempotent request detected: {idempotency_key}")
                return jsonify({
                    'status': 'success',
                    'message': 'Payment already initialized (idempotent)',
                    'data': {
                        'authorization_url': f"https://checkout.paystack.com/{existing_payment.paystack_access_code}",
                        'access_code': existing_payment.paystack_access_code,
                        'reference': existing_payment.paystack_reference,
                        'payment_id': existing_payment.id,
                        'idempotent': True
                    }
                }), 200
        
        # Prepare payment data for Kenya M-Pesa
        email = data['email']
        phone_number = data.get('phone_number')  # M-Pesa phone number (254XXXXXXXXX)
        amount = int(data['amount'])
        currency = data.get('currency', 'KES')  # Default to KES for Kenya
        reference = data.get('reference', f"C2B-{uuid.uuid4().hex[:12].upper()}")
        callback_url = data.get('callback_url')
        metadata = data.get('metadata', {})
        
        # Default to mobile_money channel for M-Pesa in Kenya
        channels = data.get('channels', ['mobile_money'])
        
        # Add phone number to metadata if provided
        if phone_number:
            metadata['phone_number'] = phone_number
        
        # Add idempotency key to metadata
        if idempotency_key:
            metadata['idempotency_key'] = idempotency_key
        
        # Initialize transaction with Paystack
        response = paystack.transaction.initialize(
            email=email,
            amount=amount,
            currency=currency,
            reference=reference,
            callback_url=callback_url,
            metadata=metadata,
            channels=channels
        )
        
        if response['status']:
            # Save payment record to database
            payment = Payment(
                email=email,
                phone_number=phone_number,  # Store M-Pesa phone number
                amount=amount,
                currency=currency,
                status='PENDING',
                payment_provider='PAYSTACK',
                account_reference=reference,
                transaction_desc=data.get('description', 'M-Pesa Payment via Paystack'),
                paystack_reference=response['data']['reference'],
                paystack_access_code=response['data']['access_code'],
                channel='mobile_money',  # M-Pesa channel
                idempotency_key=idempotency_key
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"C2B payment initialized: {reference}")
            
            return jsonify({
                'status': 'success',
                'message': 'Payment initialized',
                'data': {
                    'authorization_url': response['data']['authorization_url'],
                    'access_code': response['data']['access_code'],
                    'reference': response['data']['reference'],
                    'payment_id': payment.id
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': response.get('message', 'Failed to initialize payment')
            }), 400
            
    except (InvalidDataError, UnwantedDataError) as e:
        logger.error(f"Paystack validation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error initializing payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@c2b_bp.route("/charge", methods=['POST'])
def charge_authorization():
    """
    Charge a customer using a previously saved authorization
    Expected payload:
    {
        "email": "customer@email.com",
        "amount": 50000,
        "authorization_code": "AUTH_xxx",
        "reference": "unique-ref-123",
        "currency": "NGN"
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required_fields = ['email', 'amount', 'authorization_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'{field} is required'
                }), 400
        
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        email = data['email']
        amount = int(data['amount'])
        authorization_code = data['authorization_code']
        reference = data.get('reference', f"CHG-{uuid.uuid4().hex[:12].upper()}")
        currency = data.get('currency', 'NGN')
        
        # Charge the authorization
        response = paystack.transaction.charge(
            email=email,
            amount=amount,
            authorization_code=authorization_code,
            reference=reference,
            currency=currency
        )
        
        if response['status'] and response['data']['status'] == 'success':
            # Save payment record
            payment = Payment(
                email=email,
                amount=amount,
                currency=currency,
                status='SUCCESS',
                payment_provider='PAYSTACK',
                account_reference=reference,
                transaction_desc='Recurring charge',
                paystack_reference=response['data']['reference'],
                authorization_code=authorization_code,
                channel=response['data'].get('channel'),
                transaction_date=datetime.datetime.utcnow()
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Authorization charged successfully: {reference}")
            
            return jsonify({
                'status': 'success',
                'message': 'Charge successful',
                'data': payment.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': response.get('message', 'Failed to charge authorization'),
                'data': response.get('data')
            }), 400
            
    except (InvalidDataError, UnwantedDataError) as e:
        logger.error(f"Paystack validation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error charging authorization: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@c2b_bp.route("/verify/<reference>", methods=['GET'])
def verify_payment(reference):
    """
    Verify a C2B payment
    """
    try:
        payment = Payment.query.filter_by(paystack_reference=reference).first()
        if not payment:
            return jsonify({
                'status': 'error',
                'message': 'Payment record not found'
            }), 404

        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Verify transaction with Paystack
        response = paystack.transaction.verify(reference=reference)
        
        if response['status']:
            if response['data']['status'] != 'success':
                payment.status = 'FAILED'
                db.session.commit()
                return jsonify({
                    'status': 'error',
                    'message': 'Payment verification failed',
                    'data': payment.to_dict()
                }), 400

            payment.status = 'SUCCESS'
            payment.channel = response['data'].get('channel')
            payment.receipt_number = str(response['data'].get('id'))
            payment.transaction_date = datetime.datetime.utcnow()
            payment.authorization_code = response['data'].get('authorization', {}).get('authorization_code')
            payment.customer_code = response['data'].get('customer', {}).get('customer_code')
            db.session.commit()
            logger.info(f"C2B payment verified: {reference} - Status: {payment.status}")
            return jsonify({
                'status': 'success',
                'message': 'Payment verified',
                'data': payment.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Payment verification failed'
            }), 400
            
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@c2b_bp.route("/payments", methods=['GET'])
def list_payments():
    """
    List all C2B payments with optional filters
    Query params: status, email, page, per_page
    """
    try:
        status = request.args.get('status')
        email = request.args.get('email')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Payment.query.filter_by(payment_provider='PAYSTACK')
        
        if status:
            query = query.filter_by(status=status.upper())
        
        if email:
            query = query.filter_by(email=email)
        
        pagination = query.order_by(Payment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [payment.to_dict() for payment in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing payments: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@c2b_bp.route("/payment/<int:payment_id>", methods=['GET'])
def get_payment(payment_id):
    """
    Get a specific payment by ID
    """
    try:
        payment = Payment.query.filter_by(
            id=payment_id,
            payment_provider='PAYSTACK'
        ).first()
        
        if not payment:
            return jsonify({'status': 'error', 'message': 'Payment not found'}), 404
        
        return jsonify({
            'status': 'success',
            'data': payment.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@c2b_bp.route("/mpesa/initialize", methods=['POST'])
def initialize_mpesa():
    """
    Initialize M-Pesa payment (Kenya-specific)
    Simplified endpoint for M-Pesa payments
    Expected payload:
    {
        "phone_number": "254712345678",  // M-Pesa phone number
        "email": "customer@email.com",   // Required by Paystack
        "amount": 100,  // Amount in KES (will be converted to cents)
        "description": "Payment for order #123",
        "idempotency_key": "unique-key-123"  // Optional: for preventing duplicate payments
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required_fields = ['phone_number', 'email', 'amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'{field} is required'
                }), 400
        
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Check for idempotency key
        idempotency_key = data.get('idempotency_key') or request.headers.get('Idempotency-Key')
        
        if idempotency_key:
            # Check if we already processed this request
            existing_payment = Payment.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_payment:
                logger.info(f"Idempotent M-Pesa request detected: {idempotency_key}")
                return jsonify({
                    'status': 'success',
                    'message': 'M-Pesa payment already initialized (idempotent)',
                    'data': {
                        'authorization_url': f"https://checkout.paystack.com/{existing_payment.paystack_access_code}",
                        'access_code': existing_payment.paystack_access_code,
                        'reference': existing_payment.paystack_reference,
                        'payment_id': existing_payment.id,
                        'amount_kes': existing_payment.amount / 100,
                        'phone_number': existing_payment.phone_number,
                        'instructions': 'Customer will receive M-Pesa prompt on their phone',
                        'idempotent': True
                    }
                }), 200
        
        # Validate phone number format (254XXXXXXXXX)
        phone_number = data['phone_number']
        if not phone_number.startswith('254') or len(phone_number) != 12:
            return jsonify({
                'status': 'error',
                'message': 'Phone number must be in format 254XXXXXXXXX (12 digits)'
            }), 400
        
        # Prepare M-Pesa payment data
        email = data['email']
        amount_kes = float(data['amount'])
        amount_cents = int(amount_kes * 100)  # Convert KES to cents
        reference = f"MPESA-{uuid.uuid4().hex[:10].upper()}"
        description = data.get('description', 'M-Pesa Payment')
        
        metadata = {
            'phone_number': phone_number,
            'payment_method': 'mpesa',
            'description': description
        }
        
        if idempotency_key:
            metadata['idempotency_key'] = idempotency_key
        
        # Initialize transaction with Paystack - M-Pesa channel
        response = paystack.transaction.initialize(
            email=email,
            amount=amount_cents,
            currency='KES',
            reference=reference,
            metadata=metadata,
            channels=['mobile_money']  # M-Pesa uses mobile_money channel
        )
        
        if response['status']:
            # Save payment record
            payment = Payment(
                email=email,
                phone_number=phone_number,
                amount=amount_cents,
                currency='KES',
                status='PENDING',
                payment_provider='PAYSTACK',
                account_reference=reference,
                transaction_desc=description,
                paystack_reference=response['data']['reference'],
                paystack_access_code=response['data']['access_code'],
                channel='mobile_money',
                idempotency_key=idempotency_key
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"M-Pesa payment initialized: {reference} for {phone_number}")
            
            return jsonify({
                'status': 'success',
                'message': 'M-Pesa payment initialized',
                'data': {
                    'authorization_url': response['data']['authorization_url'],
                    'access_code': response['data']['access_code'],
                    'reference': response['data']['reference'],
                    'payment_id': payment.id,
                    'amount_kes': amount_kes,
                    'phone_number': phone_number,
                    'instructions': 'Customer will receive M-Pesa prompt on their phone'
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': response.get('message', 'Failed to initialize M-Pesa payment')
            }), 400
            
    except ValueError as e:
        logger.error(f"Value error in M-Pesa initialization: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Invalid amount format'}), 400
    except Exception as e:
        logger.error(f"Error initializing M-Pesa payment: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
