"""
Enhanced Authentication Utilities with JWT and Stronger Bcrypt
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app, request, jsonify, session, g
from src.database import get_db
from src.logging_config import get_logger

logger = get_logger("preppr.auth_utils")


class AuthUtils:
    """Enhanced authentication utilities with JWT support"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with configurable rounds
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        rounds = current_app.config.get('BCRYPT_ROUNDS', 12)
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against bcrypt hash
        
        Args:
            password: Plain text password
            hashed_password: Bcrypt hash to verify against
            
        Returns:
            True if password is valid, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

    @staticmethod
    def generate_tokens(user_id: str) -> dict:
        """
        Generate JWT access and refresh tokens for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing access_token and refresh_token
        """
        now = datetime.now(timezone.utc)
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(seconds=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
            'jti': f"access_{user_id}_{int(now.timestamp())}"  # JWT ID for token revocation
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(seconds=current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000)),
            'jti': f"refresh_{user_id}_{int(now.timestamp())}"
        }
        
        secret_key = current_app.config.get('JWT_SECRET_KEY')
        
        access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm='HS256')
        
        logger.info(f"Generated tokens for user: {user_id}")
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        }

    @staticmethod
    def verify_token(token: str, token_type: str = 'access') -> dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            secret_key = current_app.config.get('JWT_SECRET_KEY')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Verify token type
            if payload.get('type') != token_type:
                logger.warning(f"Token type mismatch. Expected: {token_type}, Got: {payload.get('type')}")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """
        Generate new access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token pair or None if refresh token is invalid
        """
        payload = AuthUtils.verify_token(refresh_token, 'refresh')
        if not payload:
            return None
            
        user_id = payload.get('user_id')
        if not user_id:
            return None
            
        # Verify user still exists and is active
        if not AuthUtils.is_user_active(user_id):
            logger.warning(f"Attempted token refresh for inactive user: {user_id}")
            return None
            
        return AuthUtils.generate_tokens(user_id)

    @staticmethod
    def is_user_active(user_id: str) -> bool:
        """
        Check if user account is active
        
        Args:
            user_id: User identifier
            
        Returns:
            True if user is active, False otherwise
        """
        try:
            db = get_db()
            cursor = db.cursor()
            
            query = "SELECT user_ID FROM user_account WHERE user_ID = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking user status: {str(e)}")
            return False

    @staticmethod
    def get_user_from_token(token: str) -> dict:
        """
        Get user information from valid access token
        
        Args:
            token: JWT access token
            
        Returns:
            User data dictionary or None if invalid
        """
        payload = AuthUtils.verify_token(token, 'access')
        if not payload:
            return None
            
        user_id = payload.get('user_id')
        if not user_id:
            return None
            
        try:
            db = get_db()
            cursor = db.cursor()
            
            query = "SELECT user_ID, email, first_name, last_name FROM user_account WHERE user_ID = %s"
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()
            cursor.close()
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error fetching user data: {str(e)}")
            return None


def jwt_required(f):
    """
    Decorator to require valid JWT token for API endpoints
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        # Fall back to session-based auth if no JWT token
        if not token:
            if 'user_ID' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            g.current_user_id = session['user_ID']
            return f(*args, **kwargs)
        
        # Verify JWT token
        payload = AuthUtils.verify_token(token, 'access')
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({'error': 'Invalid token payload'}), 401
            
        # Store user info in g for use in the endpoint
        g.current_user_id = user_id
        g.jwt_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated


def optional_jwt(f):
    """
    Decorator for endpoints that optionally use JWT authentication
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                pass
        
        if token:
            payload = AuthUtils.verify_token(token, 'access')
            if payload:
                g.current_user_id = payload.get('user_id')
                g.jwt_payload = payload
        
        # Fall back to session-based auth
        if not hasattr(g, 'current_user_id') and 'user_ID' in session:
            g.current_user_id = session['user_ID']
        
        return f(*args, **kwargs)
    
    return decorated