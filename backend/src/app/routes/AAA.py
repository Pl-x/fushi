"""
AAA (Authentication, Authorization, and Accounting) routes
"""
import os
import logging
from flask import request, jsonify, Blueprint
from ..extensions import db
from ..models import User
import datetime
import jwt
import bcrypt

logger = logging.getLogger(__name__)

aaa_bp = Blueprint('aaa', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')
JWT_EXPIRATION_DELTA = int(os.getenv('JWT_EXPIRATION_DELTA', 3600))


def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_jwt_token(user_id, email):
    """Generate a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION_DELTA),
        'iat': datetime.datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token


def verify_jwt_token(token):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@aaa_bp.route("/signup", methods=['POST'])
def signup():
    """
    Register a new user
    Expected payload:
    {
        "email": "user@example.com",
        "password": "securepassword",
        "name": "John Doe",
        "phone_number": "+234XXXXXXXXXX"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'{field} is required'
                }), 400
        
        email = data['email']
        password = data['password']
        name = data['name']
        phone_number = data.get('phone_number')
        
        # Validate email format
        if '@' not in email:
            return jsonify({
                'status': 'error',
                'message': 'Invalid email format'
            }), 400
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({
                'status': 'error',
                'message': 'Password must be at least 8 characters long'
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'status': 'error',
                'message': 'Email already registered'
            }), 409
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create new user
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            phone_number=phone_number
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Generate JWT token
        token = generate_jwt_token(user.id, user.email)
        
        logger.info(f"User registered successfully: {email}")
        
        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'data': {
                'user': user.to_dict(),
                'token': token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during signup: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@aaa_bp.route("/signin", methods=['POST'])
def signin():
    """
    Sign in an existing user
    Expected payload:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'status': 'error',
                'message': 'Email and password are required'
            }), 400
        
        email = data['email']
        password = data['password']
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                'status': 'error',
                'message': 'Account is deactivated'
            }), 403
        
        # Update last login
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        
        # Generate JWT token
        token = generate_jwt_token(user.id, user.email)
        
        logger.info(f"User signed in successfully: {email}")
        
        return jsonify({
            'status': 'success',
            'message': 'Signed in successfully',
            'data': {
                'user': user.to_dict(),
                'token': token
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error during signin: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@aaa_bp.route("/verify-token", methods=['POST'])
def verify_token():
    """
    Verify a JWT token
    Expected payload:
    {
        "token": "jwt_token_here"
    }
    """
    try:
        data = request.get_json()
        
        if not data.get('token'):
            return jsonify({
                'status': 'error',
                'message': 'Token is required'
            }), 400
        
        token = data['token']
        
        # Verify token
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token'
            }), 401
        
        # Get user details
        user = User.query.get(payload['user_id'])
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': 'Token is valid',
            'data': {
                'user': user.to_dict()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@aaa_bp.route("/change-password", methods=['POST'])
def change_password():
    """
    Change user password
    Expected payload:
    {
        "token": "jwt_token_here",
        "old_password": "oldpassword",
        "new_password": "newpassword"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['token', 'old_password', 'new_password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'{field} is required'
                }), 400
        
        token = data['token']
        old_password = data['old_password']
        new_password = data['new_password']
        
        # Verify token
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token'
            }), 401
        
        # Get user
        user = User.query.get(payload['user_id'])
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Verify old password
        if not verify_password(old_password, user.password_hash):
            return jsonify({
                'status': 'error',
                'message': 'Old password is incorrect'
            }), 401
        
        # Validate new password
        if len(new_password) < 8:
            return jsonify({
                'status': 'error',
                'message': 'New password must be at least 8 characters long'
            }), 400
        
        # Update password
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@aaa_bp.route("/forgot-password", methods=['POST'])
def forgot_password():
    """
    Initiate password reset (placeholder - requires email service)
    Expected payload:
    {
        "email": "user@example.com"
    }
    """
    try:
        data = request.get_json()
        
        if not data.get('email'):
            return jsonify({
                'status': 'error',
                'message': 'Email is required'
            }), 400
        
        email = data['email']
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        # For security, always return success even if user doesn't exist
        # This prevents email enumeration attacks
        
        if user:
            # TODO: Generate password reset token
            # TODO: Send password reset email
            logger.info(f"Password reset requested for: {email}")
        
        return jsonify({
            'status': 'success',
            'message': 'If the email exists, a password reset link has been sent'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@aaa_bp.route("/users", methods=['GET'])
def list_users():
    """
    List all users (admin only - placeholder for role-based access)
    Query params: page, per_page
    """
    try:
        # TODO: Add authentication check
        # TODO: Add authorization check (admin only)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = User.query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': [user.to_dict() for user in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
