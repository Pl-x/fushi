"""
B2C (Business to Customer) routes for handling payouts, refunds, and rewards
"""
import os
import logging
from flask import request, jsonify, Blueprint
from ..paystack_client import Paystack, InvalidDataError, UnwantedDataError
from ..extensions import db
from ..models import Transfer, Refund, Payment
from ..guards.jwtguard import admin_required
import datetime
import uuid

logger = logging.getLogger(__name__)

b2c_bp = Blueprint('b2c', __name__)

# Initialize Paystack client
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
paystack = Paystack(secret_key=PAYSTACK_SECRET_KEY) if PAYSTACK_SECRET_KEY else None


@b2c_bp.route("/transfer/initiate", methods=['POST'])
@admin_required
def initiate_transfer():
    """
    Initiate a transfer/payout to a recipient
    Expected payload:
    {
        "type": "nuban",  // nuban, mobile_money, basa, authorization
        "name": "John Doe",
        "account_number": "0123456789",
        "bank_code": "058",  // Bank code (for nuban)
        "amount": 50000,  // Amount in kobo
        "currency": "NGN",
        "reason": "Payout for services",
        "reference": "unique-ref-123",  // Optional
        "idempotency_key": "unique-key-123"  // Optional: for preventing duplicate transfers
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required_fields = ['type', 'name', 'account_number', 'amount']
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
            existing_transfer = Transfer.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_transfer:
                logger.info(f"Idempotent transfer request detected: {idempotency_key}")
                return jsonify({
                    'status': 'success',
                    'message': 'Transfer already initiated (idempotent)',
                    'data': existing_transfer.to_dict()
                }), 200
        
        # Create or get transfer recipient
        recipient_type = data['type']
        account_number = data['account_number']
        name = data['name']
        bank_code = data.get('bank_code')
        currency = data.get('currency', 'NGN')
        
        try:
            # Create transfer recipient
            recipient_response = paystack.transfer_recipient.create(
                type=recipient_type,
                name=name,
                account_number=account_number,
                bank_code=bank_code,
                currency=currency
            )
            
            if not recipient_response['status']:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to create recipient',
                    'details': recipient_response.get('message')
                }), 400
            
            recipient_code = recipient_response['data']['recipient_code']
            
        except Exception as e:
            logger.error(f"Error creating recipient: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to create recipient'
            }), 400
        
        # Initiate transfer
        amount = int(data['amount'])
        reason = data.get('reason', 'Transfer')
        reference = data.get('reference', f"TRF-{uuid.uuid4().hex[:12].upper()}")
        
        transfer_response = paystack.transfer.initiate(
            source="balance",
            amount=amount,
            recipient=recipient_code,
            reason=reason,
            reference=reference,
            currency=currency
        )
        
        if transfer_response['status']:
            # Save transfer record to database
            transfer = Transfer(
                recipient_type=recipient_type,
                recipient_code=recipient_code,
                account_number=account_number,
                account_name=name,
                bank_code=bank_code,
                amount=amount,
                currency=currency,
                reason=reason,
                reference=reference,
                status='PENDING',
                transfer_code=transfer_response['data'].get('transfer_code'),
                idempotency_key=idempotency_key
            )
            
            db.session.add(transfer)
            db.session.commit()
            
            logger.info(f"Transfer initiated: {reference}")
            
            return jsonify({
                'status': 'success',
                'message': 'Transfer initiated',
                'data': transfer.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': transfer_response.get('message', 'Failed to initiate transfer')
            }), 400
            
    except (InvalidDataError, UnwantedDataError) as e:
        logger.error(f"Paystack validation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error initiating transfer: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@b2c_bp.route("/transfer/verify/<reference>", methods=['GET'])
@admin_required
def verify_transfer(reference):
    """
    Verify a transfer status
    """
    try:
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Get transfer from database
        transfer = Transfer.query.filter_by(reference=reference).first()
        
        if not transfer:
            return jsonify({'status': 'error', 'message': 'Transfer not found'}), 404
        
        # Verify with Paystack
        response = paystack.transfer.verify(reference=reference)
        
        if response['status']:
            transfer_data = response['data']
            
            # Update transfer status
            if transfer_data['status'] == 'success':
                transfer.status = 'SUCCESS'
                transfer.completed_at = datetime.datetime.utcnow()
            elif transfer_data['status'] == 'failed':
                transfer.status = 'FAILED'
            elif transfer_data['status'] == 'reversed':
                transfer.status = 'REVERSED'
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Transfer verified',
                'data': transfer.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to verify transfer'
            }), 400
            
    except Exception as e:
        logger.error(f"Error verifying transfer: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@b2c_bp.route("/refund", methods=['POST'])
@admin_required
def process_refund():
    """
    Process a refund for a transaction
    Expected payload:
    {
        "transaction_reference": "TXN-123",
        "amount": 10000,  // Optional, null for full refund
        "currency": "NGN",
        "customer_note": "Refund reason",
        "merchant_note": "Internal note",
        "idempotency_key": "unique-key-123"  // Optional: for preventing duplicate refunds
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        if not data.get('transaction_reference'):
            return jsonify({
                'status': 'error',
                'message': 'transaction_reference is required'
            }), 400
        
        if not paystack:
            return jsonify({'status': 'error', 'message': 'Paystack not configured'}), 500
        
        # Check for idempotency key
        idempotency_key = data.get('idempotency_key') or request.headers.get('Idempotency-Key')
        
        transaction_reference = data['transaction_reference']
        
        # Find the original payment
        payment = Payment.query.filter_by(
            paystack_reference=transaction_reference
        ).first()
        
        if not payment:
            return jsonify({
                'status': 'error',
                'message': 'Transaction not found'
            }), 404
        
        # Check if idempotency key already used for this payment
        if idempotency_key:
            existing_refund = Refund.query.filter_by(
                idempotency_key=idempotency_key
            ).first()
            if existing_refund:
                logger.info(f"Idempotent refund request detected: {idempotency_key}")
                return jsonify({
                    'status': 'success',
                    'message': 'Refund already processed (idempotent)',
                    'data': existing_refund.to_dict()
                }), 200

        if payment.status != 'SUCCESS':
            return jsonify({
                'status': 'error',
                'message': 'Can only refund successful transactions'
            }), 400
        
        # Check if already refunded
        existing_refund = Refund.query.filter_by(
            payment_id=payment.id,
            status='SUCCESS'
        ).first()
        
        if existing_refund:
            return jsonify({
                'status': 'error',
                'message': 'Transaction already refunded'
            }), 400
        
        # Process refund with Paystack
        amount = data.get('amount')  # None means full refund
        currency = data.get('currency', payment.currency)
        customer_note = data.get('customer_note', 'Refund processed')
        merchant_note = data.get('merchant_note', '')
        
        refund_response = paystack.refund.create(
            transaction=transaction_reference,
            amount=amount,
            currency=currency,
            customer_note=customer_note,
            merchant_note=merchant_note
        )
        
        if refund_response['status']:
            # Create refund record
            refund = Refund(
                payment_id=payment.id,
                transaction_reference=transaction_reference,
                amount=amount if amount else payment.amount,
                currency=currency,
                merchant_note=merchant_note,
                customer_note=customer_note,
                status='PROCESSING',
                refund_reference=refund_response['data'].get('transaction', {}).get('reference'),
                idempotency_key=idempotency_key
            )
            
            db.session.add(refund)
            
            # Update payment status
            payment.status = 'REFUNDED'
            
            db.session.commit()
            
            logger.info(f"Refund processed for transaction: {transaction_reference}")
            
            return jsonify({
                'status': 'success',
                'message': 'Refund initiated',
                'data': refund.to_dict()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': refund_response.get('message', 'Failed to process refund')
            }), 400
            
    except (InvalidDataError, UnwantedDataError) as e:
        logger.error(f"Paystack validation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@b2c_bp.route("/transfers", methods=['GET'])
@admin_required
def list_transfers():
    """
    List all transfers with optional filters
    Query params: status, page, per_page
    """
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Transfer.query
        
        if status:
            query = query.filter_by(status=status.upper())
        
        pagination = query.order_by(Transfer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [transfer.to_dict() for transfer in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@b2c_bp.route("/refunds", methods=['GET'])
@admin_required
def list_refunds():
    """
    List all refunds with optional filters
    Query params: status, page, per_page
    """
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Refund.query
        
        if status:
            query = query.filter_by(status=status.upper())
        
        pagination = query.order_by(Refund.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [refund.to_dict() for refund in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing refunds: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
