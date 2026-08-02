"""Reviewer portal and admin APIs."""
import os
import datetime
import uuid
from functools import wraps
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
import jwt
from sqlalchemy.exc import DataError, IntegrityError

from ..extensions import db
from ..models import Hotel, HotelReview, PlatformSetting, PayoutRequest, ReviewerProfile, Transfer, User
from ..paystack_client import InvalidDataError, Paystack
from .AAA import verify_jwt_token, verify_password

portal_bp = Blueprint('portal', __name__)


def _current_user():
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    payload = verify_jwt_token(token)
    return db.session.get(User, payload['user_id']) if payload else None


def login_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        user = _current_user()
        if not user:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        return handler(user, *args, **kwargs)
    return wrapped


def admin_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        try:
            payload = jwt.decode(token, os.getenv('SECRET_KEY', 'supersecretkey'), algorithms=['HS256'])
        except jwt.InvalidTokenError:
            payload = {}
        user = db.session.get(User, payload.get('user_id'))
        if not user or not user.is_active or not user.is_admin:
            return jsonify({'status': 'error', 'message': 'Administrator access required'}), 403
        return handler(*args, **kwargs)
    return wrapped


def _profile(user):
    profile = user.reviewer_profile
    if not profile:
        profile = ReviewerProfile(user_id=user.id, username=user.email.split('@')[0].replace('.', '_'))
        db.session.add(profile)
        db.session.commit()
    return profile


def _payouts_enabled():
    setting = db.session.get(PlatformSetting, 'payouts_enabled')
    return setting is not None and setting.value == 'true'


def _paystack_client():
    secret = os.getenv('PAYSTACK_SECRET_KEY')
    return Paystack(secret) if secret else None


def _kenyan_mobile_number(phone_number):
    digits = ''.join(character for character in (phone_number or '') if character.isdigit())
    if digits.startswith('0') and len(digits) == 10:
        digits = f'254{digits[1:]}'
    elif digits.startswith('7') and len(digits) == 9:
        digits = f'254{digits}'
    if len(digits) != 12 or not digits.startswith('2547'):
        return None
    return digits


def _reward_cents(data, default=102100):
    """Read an admin-entered KES amount and store it in minor units."""
    value = data.get('review_reward_kes')
    if value in (None, ''):
        return default
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return None
    cents = int(amount * 100)
    return cents if 1 <= cents <= 100_000_000 else None


@portal_bp.get('/me')
@login_required
def me(user):
    profile = _profile(user)
    reviews = HotelReview.query.filter_by(user_id=user.id).order_by(HotelReview.created_at.desc()).all()
    paid = sum(review.reward_cents for review in reviews if review.status == 'PAID')
    available = sum(review.reward_cents for review in reviews if review.status == 'APPROVED')
    in_progress = sum(review.reward_cents for review in reviews if review.status == 'PAYOUT_REQUESTED')
    return jsonify({'status': 'success', 'data': {'user': user.to_dict(), 'profile': profile.to_dict(), 'balance_cents': available, 'paid_cents': paid, 'payout_in_progress_cents': in_progress, 'reviews': [review.to_dict() for review in reviews], 'payouts_enabled': _payouts_enabled()}})


@portal_bp.patch('/me')
@login_required
def update_profile(user):
    data = request.get_json(silent=True) or {}
    profile = _profile(user)
    if data.get('name'):
        user.name = data['name'].strip()
    if data.get('phone_number'):
        user.phone_number = data['phone_number'].strip()
    if data.get('username'):
        profile.username = data['username'].strip().lstrip('@')
    if data.get('location'):
        profile.location = data['location'].strip()
    db.session.commit()
    return jsonify({'status': 'success', 'data': {'user': user.to_dict(), 'profile': profile.to_dict()}})


@portal_bp.get('/hotels')
@login_required
def hotels(user):
    category = request.args.get('category')
    query = Hotel.query.filter_by(is_active=True)
    if category and category.lower() != 'all':
        query = query.filter(db.func.lower(Hotel.category) == category.lower())
    return jsonify({'status': 'success', 'data': [hotel.to_dict() for hotel in query.order_by(Hotel.created_at.desc()).all()]})


@portal_bp.post('/reviews')
@login_required
def create_review(user):
    data = request.get_json(silent=True) or {}
    hotel = db.session.get(Hotel, data.get('hotel_id'))
    ratings = ('cleanliness', 'service', 'location_rating', 'value')
    if not hotel or any(not isinstance(data.get(key), int) or not 1 <= data[key] <= 5 for key in ratings):
        return jsonify({'status': 'error', 'message': 'Hotel and four ratings from 1 to 5 are required'}), 400
    if HotelReview.query.filter_by(user_id=user.id, hotel_id=hotel.id).first():
        return jsonify({'status': 'error', 'message': 'You have already reviewed this hotel'}), 409
    review = HotelReview(user_id=user.id, hotel_id=hotel.id, reward_cents=hotel.review_reward_cents, **{key: data[key] for key in ratings})
    db.session.add(review)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Review submitted. KES {review.reward_cents / 100:,.2f} is available for payout.', 'data': review.to_dict()}), 201


@portal_bp.post('/payouts')
@login_required
def request_payout(user):
    if not _payouts_enabled():
        return jsonify({'status': 'error', 'message': 'Payouts are temporarily disabled by the administrator'}), 423
    amount = sum(r.reward_cents for r in HotelReview.query.filter_by(user_id=user.id, status='APPROVED').all())
    if amount <= 0:
        return jsonify({'status': 'error', 'message': 'No approved earnings are available'}), 400
    payout = PayoutRequest(user_id=user.id, amount_cents=amount)
    HotelReview.query.filter_by(user_id=user.id, status='APPROVED').update({'status': 'PAYOUT_REQUESTED'})
    db.session.add(payout)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Payout request submitted for administrator processing', 'data': payout.to_dict()}), 201


@portal_bp.post('/admin/login')
def admin_login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    user = User.query.filter(db.func.lower(User.email) == email).first() if email else None
    if not user or not user.is_active or not user.is_admin or not verify_password(password, user.password_hash):
        return jsonify({'status': 'error', 'message': 'Invalid administrator credentials'}), 401
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'is_admin': True,
        'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=8),
    }, os.getenv('SECRET_KEY', 'supersecretkey'), algorithm='HS256')
    return jsonify({'status': 'success', 'data': {'token': token}})


@portal_bp.get('/admin/hotels')
@admin_required
def admin_hotels():
    return jsonify({'status': 'success', 'data': [hotel.to_dict() for hotel in Hotel.query.order_by(Hotel.created_at.desc()).all()]})


@portal_bp.post('/admin/hotels')
@admin_required
def create_hotel():
    data = request.get_json(silent=True) or {}
    required = ('name', 'location', 'address', 'category', 'nightly_rate', 'image_url')
    if any(not data.get(field) for field in required):
        return jsonify({'status': 'error', 'message': 'Missing hotel fields'}), 400
    image_url = data['image_url'].strip()
    parsed_url = urlparse(image_url)
    if parsed_url.scheme not in ('http', 'https') or not parsed_url.netloc:
        return jsonify({'status': 'error', 'message': 'Image URL must be a complete http:// or https:// URL'}), 400
    if parsed_url.netloc.lower().endswith('brave.com'):
        return jsonify({'status': 'error', 'message': 'Brave search links are not image files. Use a direct image URL or upload the image first.'}), 400
    if len(image_url) > 10000:
        return jsonify({'status': 'error', 'message': 'Image URL is too long'}), 400
    try:
        rating = float(data.get('rating', 0))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Rating must be a number'}), 400
    reward_cents = _reward_cents(data)
    if reward_cents is None:
        return jsonify({'status': 'error', 'message': 'Review reward must be a valid KES amount'}), 400
    hotel = Hotel(**{field: data[field].strip() for field in required}, rating=rating, review_reward_cents=reward_cents)
    db.session.add(hotel)
    try:
        db.session.commit()
    except (DataError, IntegrityError):
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'The hotel details could not be saved'}), 400
    return jsonify({'status': 'success', 'data': hotel.to_dict()}), 201


@portal_bp.patch('/admin/hotels/<int:hotel_id>')
@admin_required
def update_hotel(hotel_id):
    hotel = db.session.get(Hotel, hotel_id)
    if not hotel:
        return jsonify({'status': 'error', 'message': 'Hotel not found'}), 404
    data = request.get_json(silent=True) or {}
    for field in ('name', 'location', 'address', 'category', 'nightly_rate', 'image_url', 'is_active', 'rating'):
        if field in data:
            setattr(hotel, field, data[field])
    if 'review_reward_kes' in data:
        reward_cents = _reward_cents(data, hotel.review_reward_cents)
        if reward_cents is None:
            return jsonify({'status': 'error', 'message': 'Review reward must be a valid KES amount'}), 400
        hotel.review_reward_cents = reward_cents
    db.session.commit()
    return jsonify({'status': 'success', 'data': hotel.to_dict()})


@portal_bp.delete('/admin/hotels/<int:hotel_id>')
@admin_required
def delete_hotel(hotel_id):
    hotel = db.session.get(Hotel, hotel_id)
    if not hotel:
        return jsonify({'status': 'error', 'message': 'Hotel not found'}), 404
    if HotelReview.query.filter_by(hotel_id=hotel.id).first():
        return jsonify({
            'status': 'error',
            'message': 'This hotel has reviews and cannot be deleted. Hide it instead to preserve review history.'
        }), 409
    db.session.delete(hotel)
    db.session.commit()
    return '', 204


@portal_bp.patch('/admin/payouts')
@admin_required
def set_payouts():
    enabled = bool((request.get_json(silent=True) or {}).get('enabled'))
    setting = PlatformSetting(key='payouts_enabled', value=str(enabled).lower())
    db.session.merge(setting)
    db.session.commit()
    return jsonify({'status': 'success', 'data': {'payouts_enabled': enabled}})


@portal_bp.get('/admin/payout-requests')
@admin_required
def payout_requests():
    requests = PayoutRequest.query.order_by(PayoutRequest.created_at.desc()).all()
    return jsonify({'status': 'success', 'data': [{**payout.to_dict(), 'reviewer': payout.user.name, 'phone_number': payout.user.phone_number} for payout in requests]})


@portal_bp.patch('/admin/payout-requests/<int:request_id>')
@admin_required
def review_payout_request(request_id):
    payout = db.session.get(PayoutRequest, request_id)
    action = (request.get_json(silent=True) or {}).get('action')
    if not payout or action not in ('approve', 'decline'):
        return jsonify({'status': 'error', 'message': 'Valid payout request and action are required'}), 400
    if payout.status != 'PENDING':
        return jsonify({'status': 'error', 'message': f'Payout is already {payout.status.lower()}'}), 409
    if action == 'decline':
        payout.status = 'DECLINED'
        HotelReview.query.filter_by(user_id=payout.user_id, status='PAYOUT_REQUESTED').update({'status': 'APPROVED'})
        db.session.commit()
        return jsonify({'status': 'success', 'data': payout.to_dict()})

    phone_number = _kenyan_mobile_number(payout.user.phone_number)
    if not phone_number:
        return jsonify({'status': 'error', 'message': 'Reviewer needs a valid Kenyan M-Pesa number before payout'}), 400
    paystack = _paystack_client()
    if not paystack:
        return jsonify({'status': 'error', 'message': 'Paystack is not configured'}), 503

    reference = f'PAYOUT-{payout.id}-{uuid.uuid4().hex[:12].upper()}'
    transfer = Transfer(
        idempotency_key=f'payout:{payout.id}', recipient_type='mobile_money',
        account_number=phone_number, account_name=payout.user.name, bank_code='MPESA',
        amount=payout.amount_cents, currency='KES', reason=f'Reviewer payout #{payout.id}',
        reference=reference, status='CREATING',
    )
    db.session.add(transfer)
    db.session.flush()
    payout.transfer_id = transfer.id
    payout.status = 'PROCESSING'
    db.session.commit()
    try:
        recipient = paystack.transfer_recipient.create(
            type='mobile_money', name=payout.user.name, account_number=phone_number,
            bank_code='MPESA', currency='KES',
        )
        transfer.recipient_code = recipient['data']['recipient_code']
        result = paystack.transfer.initiate(
            source='balance', amount=transfer.amount, recipient=transfer.recipient_code,
            reason=transfer.reason, reference=transfer.reference, currency='KES',
        )
        transfer.transfer_code = result['data'].get('transfer_code')
        needs_otp = result['data'].get('status') == 'otp'
        transfer.status = 'OTP_REQUIRED' if needs_otp else 'PENDING'
        payout.status = 'OTP_REQUIRED' if needs_otp else 'PROCESSING'
        db.session.commit()
        message = 'Transfer requires the Paystack OTP to continue' if needs_otp else 'Transfer initiated and awaiting Paystack confirmation'
        return jsonify({'status': 'success', 'message': message, 'data': payout.to_dict()}), 202
    except InvalidDataError as error:
        transfer.status = 'FAILED'
        payout.status = 'FAILED'
        db.session.commit()
        return jsonify({'status': 'error', 'message': str(error), 'data': payout.to_dict()}), 400


@portal_bp.post('/admin/payout-requests/<int:request_id>/finalize')
@admin_required
def finalize_payout_request(request_id):
    payout = db.session.get(PayoutRequest, request_id)
    otp = (request.get_json(silent=True) or {}).get('otp', '').strip()
    if not payout or payout.status != 'OTP_REQUIRED' or not payout.transfer or not otp:
        return jsonify({'status': 'error', 'message': 'A payout awaiting OTP and a valid OTP are required'}), 400
    paystack = _paystack_client()
    if not paystack:
        return jsonify({'status': 'error', 'message': 'Paystack is not configured'}), 503
    try:
        paystack.transfer.finalize(payout.transfer.transfer_code, otp)
        payout.transfer.status = 'PENDING'
        payout.status = 'PROCESSING'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'OTP accepted. Awaiting Paystack transfer confirmation.', 'data': payout.to_dict()}), 202
    except InvalidDataError as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400
