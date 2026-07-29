"""
Paystack payment routes for handling payments, refunds, and payouts
"""
import os
import logging
from flask import request, jsonify, Blueprint
from ..paystack_client import Paystack, InvalidDataError, UnwantedDataError
from ..extensions import db
from ..models import Payment, Transfer, Refund
import datetime

logger = logging.getLogger(__name__)

paystack_bp = Blueprint('paystack', __name__)

# Initialize Paystack client
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
if not PAYSTACK_SECRET_KEY:
    logger.warning("PAYSTACK_SECRET_KEY not set in environment variables")

paystack = Paystack(secret_key=PAYSTACK_SECRET_KEY) if PAYSTACK_SECRET_KEY else None


def verify_paystack_signature(payload, signature):
    """Verify webhook signature from Paystack"""
    import hmac
    import hashlib
    
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)


@paystack_bp.route("/initialize", methods=['POST'])
def initialize_transaction():
    """
    Initialize a Paystack transaction
    Expected payload:
    {
        "email": "customer@email.com",
        "amount": 10000,  // Amount in kobo (100 kobo = 1 NGN)
        "currency": "NGN",  // Optional, defaults to NGN
        "reference": "unique-ref-123",  // Optional
        "callback_url": "https://yoursite.com/callback",  // Optional
        "metadata": {  // Optional
            "custom_fields": []
        }
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
        
        # Prepare transaction data
        amount = int(data['amount'])
        email = data['email']
        currency = data.get('currency', 'NGN')
        reference = data.get('reference')
        callback_url = data.get('callback_url')
        metadata = data.get('metadata', {})
        
        # Initialize transaction with Paystack
        response = paystack.transaction.initialize(
            email=email,
            amount=amount,
            currency=currency,
            reference=reference,
            callback_url=callback_url,
            metadata=metadata
        )
        
        if response['status']:
            # Save payment record to database
            payment = Payment(
                email=email,
                amount=amount,
                currency=currency,
                status='PENDING',
                payment_provider='PAYSTACK',
                account_reference=response['data']['reference'],
                transaction_desc=data.get('description', 'Payment transaction'),
                paystack_reference=response['data']['reference'],
                paystack_access_code=response['data']['access_code']
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Payment initialized: {response['data']['reference']}")
            
            return jsonify({
                'status': 'success',
                'message': 'Transaction initialized',
                'data': {
                    'authorization_url': response['data']['authorization_url'],
                    'access_code': response['data']['access_code'],
                    'reference': response['data']['reference']
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': response.get('message', 'Failed to initialize transaction')
            }), 400
            
    except (InvalidDataError, UnwantedDataError) as e:
        logger.error(f"Paystack validation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error initializing transaction: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@paystack_bp.route("/verify/<reference>", methods=['GET'])
def verify_transaction(reference):
    """
    Verify a Paystack transaction
    """
    try:
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Verify transaction with Paystack
        response = paystack.transaction.verify(reference=reference)
        
        if response['status'] and response['data']['status'] == 'success':
            # Update payment record in database
            payment = Payment.query.filter_by(paystack_reference=reference).first()
            
            if payment:
                payment.status = 'SUCCESS'
                payment.channel = response['data'].get('channel')
                payment.receipt_number = response['data'].get('id')
                payment.transaction_date = datetime.datetime.utcnow()
                payment.authorization_code = response['data'].get('authorization', {}).get('authorization_code')
                
                db.session.commit()
                
                logger.info(f"Payment verified successfully: {reference}")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Transaction verified',
                    'data': payment.to_dict()
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Payment record not found'
                }), 404
        else:
            # Update payment as failed
            payment = Payment.query.filter_by(paystack_reference=reference).first()
            if payment:
                payment.status = 'FAILED'
                db.session.commit()
            
            return jsonify({
                'status': 'error',
                'message': 'Transaction verification failed',
                'data': response['data']
            }), 400
            
    except Exception as e:
        logger.error(f"Error verifying transaction: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@paystack_bp.route("/webhook", methods=['POST'])
def webhook():
    """
    Handle Paystack webhook events
    Events include: charge.success, transfer.success, transfer.failed, refund.processed, etc.
    """
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Paystack-Signature')
        if not signature:
            return jsonify({'status': 'error', 'message': 'No signature provided'}), 400
        
        payload = request.get_data()
        if not verify_paystack_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
        # Process webhook event
        data = request.get_json(silent=True) or {}
        event = data.get('event')
        
        logger.info(f"Webhook received: {event}")
        
        if event == 'charge.success':
            # Handle successful charge
            transaction_data = data['data']
            reference = transaction_data['reference']
            
            payment = Payment.query.filter_by(paystack_reference=reference).first()
            if payment:
                payment.status = 'SUCCESS'
                payment.channel = transaction_data.get('channel')
                payment.receipt_number = str(transaction_data.get('id'))
                payment.transaction_date = datetime.datetime.utcnow()
                db.session.commit()
                
        elif event == 'transfer.success':
            # Handle successful transfer
            transfer_data = data['data']
            reference = transfer_data.get('reference')
            
            transfer = Transfer.query.filter_by(reference=reference).first()
            if transfer:
                transfer.status = 'SUCCESS'
                transfer.transfer_code = transfer_data.get('transfer_code')
                transfer.completed_at = datetime.datetime.utcnow()
                db.session.commit()
                
        elif event == 'transfer.failed':
            # Handle failed transfer
            transfer_data = data['data']
            reference = transfer_data.get('reference')
            
            transfer = Transfer.query.filter_by(reference=reference).first()
            if transfer:
                transfer.status = 'FAILED'
                db.session.commit()
        
        elif event == 'refund.processed':
            # Handle processed refund
            refund_data = data['data']
            transaction_ref = refund_data.get('transaction_reference')
            
            # Update refund status
            payment = Payment.query.filter_by(paystack_reference=transaction_ref).first()
            if payment:
                refund = Refund.query.filter_by(payment_id=payment.id).first()
                if refund:
                    refund.status = 'SUCCESS'
                    refund.processed_at = datetime.datetime.utcnow()
                    db.session.commit()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@paystack_bp.route("/transactions", methods=['GET'])
def list_transactions():
    """
    List all transactions with optional filters
    Query params: status, page, per_page
    """
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Payment.query.filter_by(payment_provider='PAYSTACK')
        
        if status:
            query = query.filter_by(status=status.upper())
        
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
        logger.error(f"Error listing transactions: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@paystack_bp.route("/transaction/<int:transaction_id>", methods=['GET'])
def get_transaction(transaction_id):
    """
    Get a specific transaction by ID
    """
    try:
        payment = Payment.query.filter_by(
            id=transaction_id,
            payment_provider='PAYSTACK'
        ).first()
        
        if not payment:
            return jsonify({'status': 'error', 'message': 'Transaction not found'}), 404
        
        return jsonify({
            'status': 'success',
            'data': payment.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting transaction: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
