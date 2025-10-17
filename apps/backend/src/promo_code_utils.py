"""
Promotional code utilities for validation, redemption, and management.
"""

from flask import request, g
from src.database import get_db
from src.subscription_utils import get_user_subscription_info
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, Tuple, Any
import ipaddress

logger = logging.getLogger(__name__)

class PromoCodeError(Exception):
    """Base exception for promotional code errors"""
    pass

class PromoCodeExpired(PromoCodeError):
    """Raised when promotional code has expired"""
    pass

class PromoCodeExhausted(PromoCodeError):
    """Raised when promotional code has reached maximum uses"""
    pass

class PromoCodeInvalid(PromoCodeError):
    """Raised when promotional code is invalid or not found"""
    pass

class PromoCodeUserLimitReached(PromoCodeError):
    """Raised when user has already used this code maximum times"""
    pass

class PromoCodeNotEligible(PromoCodeError):
    """Raised when user is not eligible for this code"""
    pass

def get_client_ip() -> str:
    """Get client IP address from request"""
    # Check for forwarded IP first (for reverse proxies)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or '127.0.0.1'

def log_redemption_attempt(code: str, user_id: Optional[str], success: bool, failure_reason: Optional[str] = None) -> None:
    """Log a promotional code redemption attempt for security and analytics"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', '')[:1000]  # Limit length
        
        insert_query = """
            INSERT INTO code_redemption_attempts 
            (code_attempted, user_id, ip_address, success, failure_reason, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (code, user_id, ip_address, success, failure_reason, user_agent))
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to log redemption attempt: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()

def check_rate_limit(user_id: Optional[str], ip_address: str, window_minutes: int = 15, max_attempts: int = 10) -> bool:
    """Check if user/IP has exceeded rate limit for code attempts"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        window_start = datetime.now() - timedelta(minutes=window_minutes)
        
        # Check attempts by IP and user
        query = """
            SELECT COUNT(*) as attempt_count
            FROM code_redemption_attempts 
            WHERE (ip_address = %s OR user_id = %s) 
            AND attempted_at > %s
        """
        
        cursor.execute(query, (ip_address, user_id, window_start))
        result = cursor.fetchone()
        
        return result['attempt_count'] < max_attempts
        
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow on error to not block legitimate users
    finally:
        if 'cursor' in locals():
            cursor.close()

def validate_promotional_code(code: str, user_id: str) -> Dict[str, Any]:
    """
    Validate a promotional code for a specific user.
    
    Returns:
        Dict containing validation result and code details
    """
    code = code.strip().upper()  # Normalize code
    ip_address = get_client_ip()
    
    # Check rate limiting first
    if not check_rate_limit(user_id, ip_address):
        log_redemption_attempt(code, user_id, False, "rate_limit_exceeded")
        raise PromoCodeError("Too many redemption attempts. Please try again later.")
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get code details with validation
        query = """
            SELECT 
                pc.*,
                CASE 
                    WHEN pc.expires_at IS NULL THEN TRUE
                    WHEN pc.expires_at > CURRENT_TIMESTAMP THEN TRUE
                    ELSE FALSE
                END as is_not_expired,
                CASE 
                    WHEN pc.max_uses IS NULL THEN TRUE
                    WHEN pc.current_uses < pc.max_uses THEN TRUE
                    ELSE FALSE
                END as has_uses_remaining
            FROM promotional_codes pc
            WHERE pc.code = %s AND pc.is_active = TRUE
        """
        
        cursor.execute(query, (code,))
        code_data = cursor.fetchone()
        
        if not code_data:
            log_redemption_attempt(code, user_id, False, "code_not_found")
            raise PromoCodeInvalid("Invalid promotional code")
        
        # Check if code has expired
        if not code_data['is_not_expired']:
            log_redemption_attempt(code, user_id, False, "code_expired")
            raise PromoCodeExpired("This promotional code has expired")
        
        # Check if code has remaining uses
        if not code_data['has_uses_remaining']:
            log_redemption_attempt(code, user_id, False, "code_exhausted")
            raise PromoCodeExhausted("This promotional code has been fully redeemed")
        
        # Check user-specific usage limits
        user_usage_query = """
            SELECT COUNT(*) as user_redemptions
            FROM code_redemptions cr
            WHERE cr.code_id = %s AND cr.user_id = %s AND cr.redemption_result = 'success'
        """
        
        cursor.execute(user_usage_query, (code_data['code_id'], user_id))
        user_usage = cursor.fetchone()
        
        if user_usage['user_redemptions'] >= code_data['max_uses_per_user']:
            log_redemption_attempt(code, user_id, False, "user_limit_reached")
            raise PromoCodeUserLimitReached("You have already used this promotional code")
        
        # Check user eligibility (account age, subscription tier, etc.)
        eligibility_result = check_user_eligibility(code_data, user_id, cursor)
        if not eligibility_result['eligible']:
            log_redemption_attempt(code, user_id, False, f"not_eligible_{eligibility_result['reason']}")
            raise PromoCodeNotEligible(eligibility_result['message'])
        
        # Code is valid!
        log_redemption_attempt(code, user_id, True)
        
        return {
            'valid': True,
            'code_data': code_data,
            'message': 'Promotional code is valid'
        }
        
    except (PromoCodeError, PromoCodeExpired, PromoCodeExhausted, 
            PromoCodeInvalid, PromoCodeUserLimitReached, PromoCodeNotEligible):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        logger.error(f"Unexpected error validating promo code: {e}")
        log_redemption_attempt(code, user_id, False, f"system_error_{str(e)[:100]}")
        raise PromoCodeError("Unable to validate promotional code. Please try again.")
    finally:
        if 'cursor' in locals():
            cursor.close()

def check_user_eligibility(code_data: Dict, user_id: str, cursor) -> Dict[str, Any]:
    """Check if user is eligible for this promotional code"""
    
    # Get user account info
    user_query = """
        SELECT user_ID, email, created_at, subscription_tier, subscription_status
        FROM user_account 
        WHERE user_ID = %s
    """
    cursor.execute(user_query, (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        return {'eligible': False, 'reason': 'user_not_found', 'message': 'User account not found'}
    
    # Check minimum account age
    if code_data['minimum_account_age_days'] > 0:
        account_age = datetime.now() - user_data['created_at']
        required_age = timedelta(days=code_data['minimum_account_age_days'])
        
        if account_age < required_age:
            return {
                'eligible': False, 
                'reason': 'account_too_new',
                'message': f'Account must be at least {code_data["minimum_account_age_days"]} days old'
            }
    
    # Check allowed user tiers
    user_tier = user_data.get('subscription_tier', 'free')
    allowed_tiers = code_data['allowed_user_tiers'].split(',') if code_data['allowed_user_tiers'] else ['free']
    
    if user_tier not in allowed_tiers:
        return {
            'eligible': False,
            'reason': 'tier_not_allowed',
            'message': f'This code is not available for {user_tier} users'
        }
    
    return {'eligible': True, 'reason': 'eligible', 'message': 'User is eligible'}

def redeem_promotional_code(code: str, user_id: str) -> Dict[str, Any]:
    """
    Redeem a promotional code for a user.
    
    Returns:
        Dict containing redemption result and applied benefits
    """
    # First validate the code
    validation_result = validate_promotional_code(code, user_id)
    
    if not validation_result['valid']:
        raise PromoCodeInvalid("Code validation failed")
    
    code_data = validation_result['code_data']
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Begin transaction
        db.begin()
        
        # Apply the code benefits based on type
        redemption_result = apply_code_benefits(code_data, user_id, cursor)
        
        # Record the successful redemption
        record_redemption(code_data, user_id, redemption_result, cursor)
        
        # Increment usage counter
        increment_code_usage(code_data['code_id'], cursor)
        
        # Commit transaction
        db.commit()
        
        logger.info(f"Successfully redeemed promo code {code} for user {user_id}")
        
        return {
            'success': True,
            'message': get_redemption_message(code_data, redemption_result),
            'benefits_applied': redemption_result,
            'code_type': code_data['code_type']
        }
        
    except Exception as e:
        # Rollback on any error
        if 'db' in locals():
            db.rollback()
        
        logger.error(f"Failed to redeem promo code {code} for user {user_id}: {e}")
        
        # Record failed redemption
        try:
            record_failed_redemption(code_data, user_id, str(e), cursor)
            db.commit()
        except:
            pass
        
        raise PromoCodeError(f"Failed to redeem promotional code: {str(e)}")
    
    finally:
        if 'cursor' in locals():
            cursor.close()

def apply_code_benefits(code_data: Dict, user_id: str, cursor) -> Dict[str, Any]:
    """Apply the benefits of a promotional code to a user account"""
    
    code_type = code_data['code_type']
    result = {'type': code_type}
    
    if code_type == 'upgrade':
        # Grant premium subscription for specified duration
        duration_months = code_data.get('subscription_duration_months', 1)
        result.update(grant_premium_subscription(user_id, duration_months, cursor))
        
    elif code_type == 'free_month':
        # Grant 1 month free premium
        result.update(grant_premium_subscription(user_id, 1, cursor))
        
    elif code_type == 'free_year':
        # Grant 1 year free premium
        result.update(grant_premium_subscription(user_id, 12, cursor))
        
    elif code_type == 'percentage':
        # Apply percentage discount (would integrate with payment processing)
        discount_percent = code_data['discount_value']
        result.update({
            'discount_type': 'percentage',
            'discount_value': discount_percent,
            'message': f'{discount_percent}% discount applied to next payment'
        })
        
    elif code_type == 'fixed_amount':
        # Apply fixed amount discount (would integrate with payment processing)
        discount_amount = code_data['discount_value']
        result.update({
            'discount_type': 'fixed_amount',
            'discount_value': discount_amount,
            'message': f'${discount_amount} discount applied to next payment'
        })
        
    elif code_type == 'free_trial':
        # Grant free trial period
        trial_months = code_data.get('subscription_duration_months', 1)
        result.update(grant_premium_subscription(user_id, trial_months, cursor, is_trial=True))
    
    return result

def grant_premium_subscription(user_id: str, duration_months: int, cursor, is_trial: bool = False) -> Dict[str, Any]:
    """Grant premium subscription to a user for specified duration"""
    
    # Get current subscription status
    current_query = """
        SELECT subscription_tier, subscription_end_date, subscription_status 
        FROM user_account 
        WHERE user_ID = %s
    """
    cursor.execute(current_query, (user_id,))
    current_sub = cursor.fetchone()
    
    # Calculate new end date
    now = datetime.now()
    
    if current_sub and current_sub['subscription_tier'] == 'premium' and current_sub['subscription_end_date']:
        # Extend existing premium subscription
        start_date = max(current_sub['subscription_end_date'], now)
    else:
        # New premium subscription
        start_date = now
    
    # Add duration
    if duration_months == 12:
        end_date = start_date.replace(year=start_date.year + 1)
    else:
        # Handle month addition carefully for different month lengths
        month = start_date.month
        year = start_date.year
        month += duration_months
        
        while month > 12:
            month -= 12
            year += 1
            
        try:
            end_date = start_date.replace(year=year, month=month)
        except ValueError:
            # Handle case where day doesn't exist in target month (e.g., Jan 31 -> Feb 31)
            end_date = start_date.replace(year=year, month=month, day=1)
            end_date = end_date.replace(day=min(start_date.day, 28))  # Safe fallback
    
    # Update user subscription
    update_query = """
        UPDATE user_account 
        SET 
            subscription_tier = 'premium',
            subscription_status = %s,
            subscription_start_date = %s,
            subscription_end_date = %s
        WHERE user_ID = %s
    """
    
    status = 'trial' if is_trial else 'active'
    cursor.execute(update_query, (status, now, end_date, user_id))
    
    return {
        'subscription_granted': True,
        'subscription_type': 'trial' if is_trial else 'premium',
        'duration_months': duration_months,
        'start_date': now,
        'end_date': end_date,
        'message': f'Premium subscription granted until {end_date.strftime("%B %d, %Y")}'
    }

def record_redemption(code_data: Dict, user_id: str, redemption_result: Dict, cursor) -> None:
    """Record a successful promotional code redemption"""
    
    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')[:1000]
    
    # Determine values to record based on redemption type
    applied_discount = redemption_result.get('discount_value')
    subscription_end = redemption_result.get('end_date')
    
    insert_query = """
        INSERT INTO code_redemptions 
        (code_id, user_id, ip_address, user_agent, redemption_result, 
         applied_discount, subscription_granted_until, notes)
        VALUES (%s, %s, %s, %s, 'success', %s, %s, %s)
    """
    
    notes = f"Code type: {code_data['code_type']}, " + redemption_result.get('message', '')
    
    cursor.execute(insert_query, (
        code_data['code_id'], user_id, ip_address, user_agent,
        applied_discount, subscription_end, notes
    ))

def record_failed_redemption(code_data: Dict, user_id: str, error_message: str, cursor) -> None:
    """Record a failed promotional code redemption attempt"""
    
    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')[:1000]
    
    insert_query = """
        INSERT INTO code_redemptions 
        (code_id, user_id, ip_address, user_agent, redemption_result, notes)
        VALUES (%s, %s, %s, %s, 'failed', %s)
    """
    
    cursor.execute(insert_query, (
        code_data['code_id'], user_id, ip_address, user_agent, error_message[:500]
    ))

def increment_code_usage(code_id: int, cursor) -> None:
    """Increment the usage counter for a promotional code"""
    
    update_query = """
        UPDATE promotional_codes 
        SET current_uses = current_uses + 1 
        WHERE code_id = %s
    """
    
    cursor.execute(update_query, (code_id,))

def get_redemption_message(code_data: Dict, redemption_result: Dict) -> str:
    """Generate a user-friendly message about the redemption"""
    
    code_type = code_data['code_type']
    
    if code_type in ['upgrade', 'free_month', 'free_year', 'free_trial']:
        return redemption_result.get('message', 'Premium subscription activated!')
    elif code_type in ['percentage', 'fixed_amount']:
        return redemption_result.get('message', 'Discount applied to your account!')
    else:
        return 'Promotional code redeemed successfully!'

def get_user_redemption_history(user_id: str, limit: int = 10) -> list:
    """Get a user's promotional code redemption history"""
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT 
                cr.redeemed_at,
                pc.code,
                pc.code_type,
                pc.description,
                cr.redemption_result,
                cr.applied_discount,
                cr.subscription_granted_until,
                cr.notes
            FROM code_redemptions cr
            JOIN promotional_codes pc ON cr.code_id = pc.code_id
            WHERE cr.user_id = %s
            ORDER BY cr.redeemed_at DESC
            LIMIT %s
        """
        
        cursor.execute(query, (user_id, limit))
        return cursor.fetchall()
        
    except Exception as e:
        logger.error(f"Failed to get redemption history for user {user_id}: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()

def cleanup_old_attempts(days_old: int = 30) -> None:
    """Clean up old redemption attempts (for maintenance)"""
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        delete_query = """
            DELETE FROM code_redemption_attempts 
            WHERE attempted_at < %s
        """
        
        cursor.execute(delete_query, (cutoff_date,))
        deleted_count = cursor.rowcount
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old redemption attempts")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old attempts: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()