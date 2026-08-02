"""
JWT Guard for protecting routes with authentication
"""
import os
import jwt
from functools import wraps
from flask import request, jsonify
from ..models import User

SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')


def jwt_required(f):
    """
    Decorator to protect routes with JWT authentication
    Usage: @jwt_required before route handler
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Authorization header is required'
            }), 401
        
        # Extract token from "Bearer <token>" format
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid authorization header format. Use: Bearer <token>'
            }), 401
        
        # Verify token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            # Get user from database
            user = User.query.get(payload['user_id'])
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 404
            
            if not user.is_active:
                return jsonify({
                    'status': 'error',
                    'message': 'Account is deactivated'
                }), 403
            
            # Add user to request context
            request.current_user = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'status': 'error',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_jwt(f):
    """
    Decorator that adds user context if valid JWT is provided, but doesn't require it
    Usage: @optional_jwt before route handler
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                user = User.query.get(payload['user_id'])
                
                if user and user.is_active:
                    request.current_user = user
            except (IndexError, jwt.InvalidTokenError, jwt.ExpiredSignatureError):
                pass
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """Require an active, database-confirmed administrator for sensitive routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split(' ', 1)
        if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1].strip():
            return jsonify({'status': 'error', 'message': 'Authorization header is required'}), 401
        try:
            payload = jwt.decode(parts[1], SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'error', 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

        user = User.query.get(payload.get('user_id'))
        if not user or not user.is_active:
            return jsonify({'status': 'error', 'message': 'Administrator access required'}), 403
        if not user.is_admin:
            return jsonify({'status': 'error', 'message': 'Administrator access required'}), 403
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function
