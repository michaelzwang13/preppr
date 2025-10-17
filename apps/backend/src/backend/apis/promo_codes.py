"""
Promotional codes API endpoints for validation and redemption.
"""

from flask import Blueprint, request, jsonify, session, g
from src.database import get_db
from src.promo_code_utils import (
    validate_promotional_code, 
    redeem_promotional_code,
    get_user_redemption_history,
    PromoCodeError,
    PromoCodeExpired,
    PromoCodeExhausted,
    PromoCodeInvalid,
    PromoCodeUserLimitReached,
    PromoCodeNotEligible,
    log_redemption_attempt
)
from src.auth_utils import jwt_required
from src.logging_config import get_logger

promo_codes_bp = Blueprint("promo_codes", __name__, url_prefix="/api/promo-codes")
logger = get_logger("preppr.promo_codes")

@promo_codes_bp.route("/validate", methods=["POST"])
def validate_promo_code():
    """Validate a promotional code for the current user"""
    
    # Check authentication (support both session and JWT)
    user_id = None
    if "user_ID" in session:
        user_id = session["user_ID"]
    elif hasattr(g, 'current_user_id'):
        user_id = g.current_user_id
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "authentication_required",
            "message": "You must be logged in to validate promotional codes"
        }), 401
    
    # Get request data
    data = request.get_json()
    if not data or not data.get("code"):
        return jsonify({
            "success": False,
            "error": "missing_code",
            "message": "Promotional code is required"
        }), 400
    
    code = data["code"].strip()
    
    if not code:
        return jsonify({
            "success": False,
            "error": "empty_code",
            "message": "Please enter a promotional code"
        }), 400
    
    try:
        # Validate the promotional code
        validation_result = validate_promotional_code(code, user_id)
        
        if validation_result["valid"]:
            code_data = validation_result["code_data"]
            
            # Return validation success with code details
            response_data = {
                "success": True,
                "valid": True,
                "message": "Promotional code is valid!",
                "code_details": {
                    "code": code_data["code"],
                    "type": code_data["code_type"],
                    "description": code_data["description"],
                    "discount_value": float(code_data["discount_value"]) if code_data["discount_value"] else None,
                    "subscription_duration_months": code_data["subscription_duration_months"]
                }
            }
            
            # Add type-specific messaging
            if code_data["code_type"] == "upgrade":
                response_data["preview_message"] = "This code will upgrade you to Premium!"
            elif code_data["code_type"] == "free_month":
                response_data["preview_message"] = "This code grants 1 month of Premium access!"
            elif code_data["code_type"] == "free_year":
                response_data["preview_message"] = "This code grants 1 year of Premium access!"
            elif code_data["code_type"] == "percentage":
                discount = code_data["discount_value"]
                response_data["preview_message"] = f"This code gives you {discount}% off!"
            elif code_data["code_type"] == "fixed_amount":
                amount = code_data["discount_value"]
                response_data["preview_message"] = f"This code gives you ${amount} off!"
            
            logger.info(
                "Promo code validation successful",
                extra={
                    "user_id": user_id,
                    "code": code,
                    "code_type": code_data["code_type"],
                    "request_id": getattr(g, "request_id", None),
                }
            )
            
            return jsonify(response_data), 200
        else:
            return jsonify({
                "success": False,
                "valid": False,
                "error": "invalid_code",
                "message": "Invalid promotional code"
            }), 400
            
    except PromoCodeExpired:
        return jsonify({
            "success": False,
            "valid": False,
            "error": "code_expired",
            "message": "This promotional code has expired"
        }), 400
        
    except PromoCodeExhausted:
        return jsonify({
            "success": False,
            "valid": False,
            "error": "code_exhausted",
            "message": "This promotional code has been fully redeemed"
        }), 400
        
    except PromoCodeUserLimitReached:
        return jsonify({
            "success": False,
            "valid": False,
            "error": "user_limit_reached",
            "message": "You have already used this promotional code"
        }), 400
        
    except PromoCodeNotEligible as e:
        return jsonify({
            "success": False,
            "valid": False,
            "error": "not_eligible",
            "message": str(e)
        }), 400
        
    except PromoCodeInvalid:
        return jsonify({
            "success": False,
            "valid": False,
            "error": "invalid_code",
            "message": "Invalid promotional code"
        }), 400
        
    except PromoCodeError as e:
        # Rate limiting or other promo code errors
        error_message = str(e)
        if "rate limit" in error_message.lower():
            return jsonify({
                "success": False,
                "valid": False,
                "error": "rate_limited",
                "message": error_message
            }), 429
        else:
            return jsonify({
                "success": False,
                "valid": False,
                "error": "validation_error",
                "message": error_message
            }), 400
            
    except Exception as e:
        logger.error(
            "Unexpected error validating promo code",
            extra={
                "user_id": user_id,
                "code": code,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True
        )
        
        return jsonify({
            "success": False,
            "valid": False,
            "error": "system_error",
            "message": "Unable to validate promotional code. Please try again."
        }), 500

@promo_codes_bp.route("/redeem", methods=["POST"])
def redeem_promo_code():
    """Redeem a promotional code for the current user"""
    
    # Check authentication
    user_id = None
    if "user_ID" in session:
        user_id = session["user_ID"]
    elif hasattr(g, 'current_user_id'):
        user_id = g.current_user_id
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "authentication_required",
            "message": "You must be logged in to redeem promotional codes"
        }), 401
    
    # Get request data
    data = request.get_json()
    if not data or not data.get("code"):
        return jsonify({
            "success": False,
            "error": "missing_code",
            "message": "Promotional code is required"
        }), 400
    
    code = data["code"].strip()
    
    if not code:
        return jsonify({
            "success": False,
            "error": "empty_code",
            "message": "Please enter a promotional code"
        }), 400
    
    try:
        # Redeem the promotional code
        redemption_result = redeem_promotional_code(code, user_id)
        
        logger.info(
            "Promo code redeemed successfully",
            extra={
                "user_id": user_id,
                "code": code,
                "code_type": redemption_result["code_type"],
                "request_id": getattr(g, "request_id", None),
            }
        )
        
        # Return success response
        response_data = {
            "success": True,
            "redeemed": True,
            "message": redemption_result["message"],
            "code_type": redemption_result["code_type"],
            "benefits_applied": redemption_result["benefits_applied"]
        }
        
        # Add redirect instructions for upgrade codes
        if redemption_result["code_type"] in ["upgrade", "free_month", "free_year", "free_trial"]:
            response_data["redirect_to"] = "/settings"
            response_data["redirect_message"] = "Redirecting to your account settings..."
        
        return jsonify(response_data), 200
        
    except (PromoCodeExpired, PromoCodeExhausted, PromoCodeUserLimitReached, 
            PromoCodeNotEligible, PromoCodeInvalid) as e:
        # These errors should have been caught in validation, but handle them anyway
        error_type = type(e).__name__.lower().replace("promocode", "")
        
        return jsonify({
            "success": False,
            "redeemed": False,
            "error": error_type,
            "message": str(e)
        }), 400
        
    except PromoCodeError as e:
        error_message = str(e)
        if "rate limit" in error_message.lower():
            return jsonify({
                "success": False,
                "redeemed": False,
                "error": "rate_limited",
                "message": error_message
            }), 429
        else:
            return jsonify({
                "success": False,
                "redeemed": False,
                "error": "redemption_error",
                "message": error_message
            }), 400
            
    except Exception as e:
        logger.error(
            "Unexpected error redeeming promo code",
            extra={
                "user_id": user_id,
                "code": code,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True
        )
        
        return jsonify({
            "success": False,
            "redeemed": False,
            "error": "system_error",
            "message": "Unable to redeem promotional code. Please try again."
        }), 500

@promo_codes_bp.route("/history", methods=["GET"])
def get_redemption_history():
    """Get the current user's promotional code redemption history"""
    
    # Check authentication
    user_id = None
    if "user_ID" in session:
        user_id = session["user_ID"]
    elif hasattr(g, 'current_user_id'):
        user_id = g.current_user_id
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "authentication_required",
            "message": "You must be logged in to view redemption history"
        }), 401
    
    try:
        # Get query parameters
        limit = min(int(request.args.get("limit", 10)), 50)  # Max 50 records
        
        # Get user's redemption history
        history = get_user_redemption_history(user_id, limit)
        
        # Format response
        formatted_history = []
        for record in history:
            formatted_record = {
                "redeemed_at": record["redeemed_at"].isoformat() if record["redeemed_at"] else None,
                "code": record["code"],
                "code_type": record["code_type"],
                "description": record["description"],
                "status": record["redemption_result"],
                "discount_applied": float(record["applied_discount"]) if record["applied_discount"] else None,
                "subscription_granted_until": record["subscription_granted_until"].isoformat() if record["subscription_granted_until"] else None,
                "notes": record["notes"]
            }
            formatted_history.append(formatted_record)
        
        return jsonify({
            "success": True,
            "history": formatted_history,
            "total_records": len(formatted_history)
        }), 200
        
    except Exception as e:
        logger.error(
            "Error getting redemption history",
            extra={
                "user_id": user_id,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True
        )
        
        return jsonify({
            "success": False,
            "error": "system_error",
            "message": "Unable to retrieve redemption history"
        }), 500

@promo_codes_bp.route("/check-availability/<code>", methods=["GET"])
def check_code_availability(code):
    """Quick check if a promotional code exists and is generally available (public endpoint)"""
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Basic check for code existence and general availability
        query = """
            SELECT 
                code,
                code_type,
                description,
                CASE 
                    WHEN expires_at IS NULL THEN TRUE
                    WHEN expires_at > CURRENT_TIMESTAMP THEN TRUE
                    ELSE FALSE
                END as not_expired,
                CASE 
                    WHEN max_uses IS NULL THEN TRUE
                    WHEN current_uses < max_uses THEN TRUE
                    ELSE FALSE
                END as has_uses_remaining,
                is_active
            FROM promotional_codes
            WHERE code = %s
        """
        
        cursor.execute(query, (code.strip().upper(),))
        code_data = cursor.fetchone()
        
        if not code_data:
            return jsonify({
                "exists": False,
                "available": False,
                "message": "Promotional code not found"
            }), 404
        
        available = (code_data["is_active"] and 
                    code_data["not_expired"] and 
                    code_data["has_uses_remaining"])
        
        response = {
            "exists": True,
            "available": available,
            "code_type": code_data["code_type"],
            "description": code_data["description"]
        }
        
        if not available:
            if not code_data["is_active"]:
                response["message"] = "This promotional code is no longer active"
            elif not code_data["not_expired"]:
                response["message"] = "This promotional code has expired"
            elif not code_data["has_uses_remaining"]:
                response["message"] = "This promotional code has been fully redeemed"
        else:
            response["message"] = "Promotional code is available"
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error checking code availability: {e}")
        return jsonify({
            "exists": False,
            "available": False,
            "error": "system_error",
            "message": "Unable to check code availability"
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()

# JWT-protected endpoints (same functionality, different auth)
@promo_codes_bp.route("/jwt/validate", methods=["POST"])
@jwt_required
def jwt_validate_promo_code():
    """JWT version of validate endpoint"""
    return validate_promo_code()

@promo_codes_bp.route("/jwt/redeem", methods=["POST"])
@jwt_required
def jwt_redeem_promo_code():
    """JWT version of redeem endpoint"""
    return redeem_promo_code()

@promo_codes_bp.route("/jwt/history", methods=["GET"])
@jwt_required
def jwt_get_redemption_history():
    """JWT version of history endpoint"""
    return get_redemption_history()