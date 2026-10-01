"""
Subscription tier utilities for managing free vs premium features.
"""

from functools import wraps
from flask import session, jsonify, request
from src.database import get_db
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SubscriptionLimitExceeded(Exception):
    """Raised when user exceeds their subscription tier limits"""
    def __init__(self, limit_type, current_limit, upgrade_message=None):
        self.limit_type = limit_type
        self.current_limit = current_limit
        self.upgrade_message = upgrade_message or f"Upgrade to Premium to exceed the {current_limit} limit for {limit_type}"
        super().__init__(self.upgrade_message)

def get_user_subscription_info(user_id):
    """Get user's subscription tier and status"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        query = """
        SELECT subscription_tier, subscription_status, subscription_end_date 
        FROM user_account 
        WHERE user_ID = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return {
                'tier': 'free', 
                'status': 'active', 
                'expires_at': None, 
                'unlimited': False
            }
        
        tier = result['subscription_tier'] or 'free'
        status = result['subscription_status'] or 'active'
        end_date = result['subscription_end_date']
        
        # Check if subscription has expired
        is_expired = end_date and end_date < datetime.now()
        if is_expired and status != 'expired':
            # Update status to expired but keep tier for record-keeping
            update_query = """
            UPDATE user_account 
            SET subscription_status = 'expired'
            WHERE user_ID = %s
            """
            cursor.execute(update_query, (user_id,))
            db.commit()
            status = 'expired'
        
        # Determine if user has unlimited access
        unlimited = (tier == 'premium' and status == 'active' and not is_expired)
        
        return {
            'tier': tier,
            'status': status,
            'expires_at': end_date,
            'unlimited': unlimited
        }
    finally:
        cursor.close()

def get_tier_limit(tier, feature_name):
    """Get the limit for a specific feature based on subscription tier"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        query = """
        SELECT limit_value 
        FROM subscription_tier_features 
        WHERE tier = %s AND feature_name = %s
        """
        cursor.execute(query, (tier, feature_name))
        result = cursor.fetchone()
        
        if not result:
            return 0  # Default to 0 if feature not found
        
        return result['limit_value']
    finally:
        cursor.close()

# Limits on how many of something a user has right now. Usage is counted from
# the live rows, so deleting a pantry item, recipe or plan frees up its slot.
COUNTED_LIMITS = {
    'pantry_items': "SELECT COUNT(*) AS n FROM pantry_items WHERE user_id = %s AND is_consumed = FALSE",
    'saved_recipes': "SELECT COUNT(*) AS n FROM saved_recipes WHERE user_id = %s",
    'meal_plans_active': "SELECT COUNT(*) AS n FROM meal_plan_sessions WHERE user_id = %s AND end_date >= CURDATE()",
}

# Limits on the size of a single request rather than on accumulated usage; the
# caller passes the requested amount as the increment.
PER_REQUEST_LIMITS = {'meal_plans_advance_days'}

def get_current_usage(user_id, limit_type):
    """Get current usage for a specific limit type"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        if limit_type in COUNTED_LIMITS:
            cursor.execute(COUNTED_LIMITS[limit_type], (user_id,))
            return cursor.fetchone()['n']

        query = """
        SELECT current_usage, last_reset_date
        FROM subscription_limits 
        WHERE user_id = %s AND limit_type = %s
        """
        cursor.execute(query, (user_id, limit_type))
        result = cursor.fetchone()
        
        if not result:
            # Initialize usage tracking if doesn't exist. A concurrent request
            # may have just created the row, so make the insert a no-op then.
            insert_query = """
            INSERT INTO subscription_limits (user_id, limit_type, current_usage, last_reset_date)
            VALUES (%s, %s, 0, CURRENT_DATE)
            ON DUPLICATE KEY UPDATE user_id = user_id
            """
            cursor.execute(insert_query, (user_id, limit_type))
            db.commit()
            return 0
        
        # Check if we need to reset daily/weekly counters
        today = datetime.now().date()
        last_reset = result['last_reset_date']
        
        if limit_type in ['shopping_lists_per_day'] and last_reset < today:
            # Reset daily counter
            reset_query = """
            UPDATE subscription_limits 
            SET current_usage = 0, last_reset_date = CURRENT_DATE
            WHERE user_id = %s AND limit_type = %s
            """
            cursor.execute(reset_query, (user_id, limit_type))
            db.commit()
            return 0
        elif limit_type in ['upc_scans_per_week'] and (today - last_reset).days >= 7:
            # Reset weekly counter
            reset_query = """
            UPDATE subscription_limits 
            SET current_usage = 0, last_reset_date = CURRENT_DATE
            WHERE user_id = %s AND limit_type = %s
            """
            cursor.execute(reset_query, (user_id, limit_type))
            db.commit()
            return 0
        
        return result['current_usage']
    finally:
        cursor.close()

def increment_usage(user_id, limit_type, increment=1):
    """Increment usage counter for a specific limit type"""
    if limit_type in COUNTED_LIMITS:
        return  # usage is counted from the live rows

    db = get_db()
    cursor = db.cursor()
    
    try:
        query = """
        UPDATE subscription_limits 
        SET current_usage = current_usage + %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND limit_type = %s
        """
        cursor.execute(query, (increment, user_id, limit_type))
        db.commit()
    finally:
        cursor.close()

def check_subscription_limit(user_id, feature_name, increment=1):
    """
    Check if user can perform an action based on their subscription tier limits.
    Returns True if allowed, raises SubscriptionLimitExceeded if not.
    """
    subscription_info = get_user_subscription_info(user_id)
    tier = subscription_info['tier']
    
    # Premium users have no limits
    if tier == 'premium':
        return True
    
    # Get the limit for this feature on free tier
    limit = get_tier_limit('free', feature_name)
    
    # -1 means unlimited (shouldn't happen for free tier, but handle it)
    if limit == -1:
        return True
    
    # Get current usage
    if feature_name in PER_REQUEST_LIMITS:
        current_usage = 0
    else:
        current_usage = get_current_usage(user_id, feature_name)
    
    # Check if adding the increment would exceed the limit
    if current_usage + increment > limit:
        raise SubscriptionLimitExceeded(
            feature_name, 
            limit,
            get_upgrade_message(feature_name)
        )
    
    return True

def get_upgrade_message(feature_name):
    """Get contextual upgrade message for different features"""
    messages = {
        'meal_plans_active': "You've reached your free meal plan limit — unlock unlimited plans with Preppr Premium!",
        'pantry_items': "You've reached your 100 item pantry limit — upgrade to Premium for unlimited pantry storage!",
        'shopping_lists_per_day': "You've reached your daily shopping list limit — upgrade to Premium for unlimited list generation!",
        'saved_recipes': "You've reached your 10 recipe limit — save unlimited recipes with Preppr Premium!",
        'upc_scans_per_trip': "You've reached your UPC scan limit for this trip — upgrade to Premium for unlimited scanning!",
        'upc_scans_per_week': "You've reached your weekly UPC scan limit — upgrade to Premium for unlimited scanning!"
    }
    return messages.get(feature_name, f"Upgrade to Preppr Premium to unlock unlimited {feature_name}!")

def subscription_required(feature_name):
    """
    Decorator to check subscription limits before executing a function.
    Use on API endpoints that should be limited by subscription tier.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_ID' not in session:
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            
            try:
                check_subscription_limit(session['user_ID'], feature_name)
                # If check passes, increment the usage after successful execution
                result = f(*args, **kwargs)
                increment_usage(session['user_ID'], feature_name)
                return result
            except SubscriptionLimitExceeded as e:
                return jsonify({
                    'success': False,
                    'message': str(e),
                    'limit_type': e.limit_type,
                    'current_limit': e.current_limit,
                    'requires_upgrade': True
                }), 403
                
        return decorated_function
    return decorator

def get_user_limits_status(user_id):
    """Get comprehensive status of user's subscription limits"""
    subscription_info = get_user_subscription_info(user_id)
    tier = subscription_info['tier']
    
    if tier == 'premium':
        return {
            'tier': 'premium',
            'status': subscription_info['status'],
            'expires_at': subscription_info['expires_at'],
            'limits': {},
            'unlimited': subscription_info['unlimited']
        }
    
    # Get all free tier limits
    db = get_db()
    cursor = db.cursor()
    
    try:
        limits_query = """
        SELECT feature_name, limit_value, description
        FROM subscription_tier_features
        WHERE tier = 'free' AND limit_value > 0
        """
        cursor.execute(limits_query)
        features = cursor.fetchall()
    finally:
        cursor.close()
    
    status = {
        'tier': 'free',
        'status': subscription_info['status'],
        'expires_at': subscription_info['expires_at'],
        'limits': {},
        'unlimited': subscription_info['unlimited']
    }
    
    for feature in features:
        current_usage = get_current_usage(user_id, feature['feature_name'])
        status['limits'][feature['feature_name']] = {
            'current': current_usage,
            'limit': feature['limit_value'],
            'description': feature['description'],
            'percentage_used': (current_usage / feature['limit_value']) * 100 if feature['limit_value'] > 0 else 0
        }
    
    return status

def requires_premium(feature_description="this feature"):
    """
    Simple decorator for features that are premium-only.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_ID' not in session:
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            
            subscription_info = get_user_subscription_info(session['user_ID'])
            if subscription_info['tier'] != 'premium':
                return jsonify({
                    'success': False,
                    'message': f'Premium subscription required to access {feature_description}',
                    'requires_upgrade': True
                }), 403
                
            return f(*args, **kwargs)
                
        return decorated_function
    return decorator

# Test helper functions for backward compatibility
def check_user_limit(user_id, feature_name, current_count=None, auto_count=False):
    """
    Test helper function that provides the API expected by tests.
    Returns a dict with limit information instead of raising exceptions.
    """
    try:
        subscription_info = get_user_subscription_info(user_id)
        tier = subscription_info['tier']
        
        # Premium users have unlimited access
        if tier == 'premium':
            return {
                'allowed': True,
                'limit': -1,
                'current': current_count or 0,
                'remaining': -1
            }
        
        # Get the limit for this feature on free tier
        limit = get_tier_limit('free', feature_name)
        
        # Get current usage if auto_count is requested
        if auto_count:
            current_count = get_current_usage(user_id, feature_name)
        elif current_count is None:
            current_count = 0
        
        # Check if at or over limit
        allowed = current_count < limit
        remaining = max(0, limit - current_count)
        
        return {
            'allowed': allowed,
            'limit': limit,
            'current': current_count,
            'remaining': remaining
        }
    except Exception:
        # Return safe defaults on error
        return {
            'allowed': False,
            'limit': 0,
            'current': current_count or 0,
            'remaining': 0
        }

def increment_user_limit(user_id, limit_type, increment=1):
    """
    Test helper function that increments usage and returns success/failure.
    Returns True if increment was successful, False if it would exceed limits.
    """
    try:
        # Check if increment would exceed limit first
        limit_check = check_user_limit(user_id, limit_type, auto_count=True)
        if not limit_check['allowed'] and limit_check['limit'] != -1:
            return False
        
        # If allowed, increment the usage
        increment_usage(user_id, limit_type, increment)
        return True
    except Exception:
        return False

def reset_daily_limits(user_id):
    """
    Test helper function to reset daily limits for a user.
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Reset all daily limits
        reset_query = """
        UPDATE subscription_limits 
        SET current_usage = 0, last_reset_date = CURRENT_DATE
        WHERE user_id = %s AND limit_type LIKE '%%_per_day'
        """
        cursor.execute(reset_query, (user_id,))
        db.commit()
    finally:
        cursor.close()