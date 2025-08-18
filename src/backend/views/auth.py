from flask import Blueprint, render_template, request, session, url_for, redirect, g, jsonify
import bcrypt

from src.database import get_db
from src.logging_config import get_logger
from src.auth_utils import AuthUtils, jwt_required
from src.subscription_utils import get_user_limits_status

auth_bp = Blueprint("auth", __name__)
logger = get_logger("preppr.auth")


def hash_password_bcrypt(password):
    """Legacy function - use AuthUtils.hash_password instead"""
    return AuthUtils.hash_password(password)


def verify_password_bcrypt(password, hashed_password):
    """Legacy function - use AuthUtils.verify_password instead"""
    return AuthUtils.verify_password(password, hashed_password)


def restore_active_cart(user_ID):
    """Restore active shopping cart for user after login"""
    try:
        db = get_db()
        cursor = db.cursor()

        # Look for active shopping cart for this user
        query = 'SELECT cart_ID FROM shopping_cart WHERE user_ID = %s AND status = "active" ORDER BY created_at DESC LIMIT 1'
        cursor.execute(query, (user_ID,))
        active_cart = cursor.fetchone()

        if active_cart:
            session["cart_ID"] = active_cart["cart_ID"]
            logger.info(
                "Restored active cart for user",
                extra={
                    "user_id": user_ID,
                    "cart_id": active_cart["cart_ID"],
                    "request_id": getattr(g, "request_id", None),
                },
            )
        else:
            logger.debug(
                "No active cart found for user",
                extra={
                    "user_id": user_ID,
                    "request_id": getattr(g, "request_id", None),
                },
            )

        cursor.close()
    except Exception as e:
        logger.error(
            "Failed to restore active cart",
            extra={
                "user_id": user_ID,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        # Don't raise error - just log it


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_ID = request.form["user_ID"].strip()
        password = request.form["password"]

        logger.info(
            "Login attempt",
            extra={"user_id": user_ID, "request_id": getattr(g, "request_id", None)},
        )

        # Basic validation
        if not user_ID or not password:
            logger.warning(
                "Login failed - missing credentials",
                extra={
                    "user_id": user_ID,
                    "request_id": getattr(g, "request_id", None),
                },
            )
            error = "Username and password are required"
            return render_template("login.html", error=error)

        try:
            db = get_db()
            cursor = db.cursor()
            query = "SELECT * FROM user_account WHERE user_ID = %s"
            cursor.execute(query, (user_ID,))
            data = cursor.fetchone()
            cursor.close()

            if data and verify_password_bcrypt(password, data["password"]):
                session["user_ID"] = user_ID
                logger.info(
                    "Login successful",
                    extra={
                        "user_id": user_ID,
                        "request_id": getattr(g, "request_id", None),
                    },
                )
                # Check for active shopping cart and restore it
                restore_active_cart(user_ID)
                return redirect(url_for("shopping.home"))
            else:
                logger.warning(
                    "Login failed - invalid credentials",
                    extra={
                        "user_id": user_ID,
                        "user_exists": data is not None,
                        "request_id": getattr(g, "request_id", None),
                    },
                )
                error = "Invalid username or password"
                return render_template("login.html", error=error)
        except Exception as e:
            logger.error(
                "Login failed - database error",
                extra={
                    "user_id": user_ID,
                    "error": str(e),
                    "request_id": getattr(g, "request_id", None),
                },
                exc_info=True,
            )
            error = "Login failed. Please try again."
            return render_template("login.html", error=error)

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        user_ID = request.form["user_ID"].strip()
        password = request.form["password"]
        email_address = request.form["email_address"].strip()
        confirm_password = request.form.get("confirmPassword", "")

        # Validation - first_name and last_name are optional
        if not user_ID or not password or not email_address:
            error = "Email, username, and password are required"
            return render_template("register.html", error=error)

        # Email format validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_address):
            error = "Please enter a valid email address"
            return render_template("register.html", error=error)

        if len(user_ID) < 3:
            error = "Username must be at least 3 characters long"
            return render_template("register.html", error=error)

        if len(password) < 6:
            error = "Password must be at least 6 characters long"
            return render_template("register.html", error=error)

        if password != confirm_password:
            error = "Passwords do not match"
            return render_template("register.html", error=error)

        # Hash password
        hashed_password = hash_password_bcrypt(password)

        db = get_db()
        cursor = db.cursor()

        # Check if username already exists
        query = "SELECT * FROM user_account WHERE user_ID = %s"
        cursor.execute(query, (user_ID,))
        data = cursor.fetchone()

        if data:
            cursor.close()
            error = "This username already exists"
            return render_template("register.html", error=error)

        # Check if email already exists
        query = "SELECT * FROM user_account WHERE email = %s"
        cursor.execute(query, (email_address,))
        data = cursor.fetchone()

        if data:
            cursor.close()
            error = "This email address is already registered"
            return render_template("register.html", error=error)

        try:
            # Insert new user
            ins = (
                "INSERT INTO user_account (user_ID, email, password, first_name, last_name) VALUES(%s, %s, %s, %s, %s)"
            )
            cursor.execute(ins, (user_ID, email_address, hashed_password, first_name, last_name))
            
            # Set default theme preference to light mode for new users
            theme_pref_query = """
                INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type)
                VALUES (%s, 'theme_preference', 'light', 'string')
            """
            cursor.execute(theme_pref_query, (user_ID,))
            
            db.commit()
            cursor.close()
            session["user_ID"] = user_ID
            # Check for any active carts (shouldn't exist for new user, but just in case)
            restore_active_cart(user_ID)
            return redirect(url_for("shopping.home"))
        except Exception as e:
            cursor.close()
            error = "Registration failed. Please try again."
            return render_template("register.html", error=error)

    return render_template("register.html")


@auth_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    user_ID = session["user_ID"]
    
    if request.method == "POST":
        form_type = request.form.get("form_type")
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            if form_type == "personal_info":
                # Update personal information
                first_name = request.form["first_name"].strip()
                last_name = request.form["last_name"].strip()
                email = request.form["email"].strip()
                timezone = request.form.get("timezone", "UTC").strip()
                
                # Validation
                if not first_name or not last_name or not email:
                    error = "All fields are required"
                    return render_settings_with_user_data(user_ID, error=error)
                
                # Validate timezone
                if not timezone:
                    timezone = "UTC"
                
                # Check if email is already used by another user
                query = "SELECT user_ID FROM user_account WHERE email = %s AND user_ID != %s"
                cursor.execute(query, (email, user_ID))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    error = "This email address is already in use by another account"
                    return render_settings_with_user_data(user_ID, error=error)
                
                # Update user information including timezone
                update_query = "UPDATE user_account SET first_name = %s, last_name = %s, email = %s, timezone = %s WHERE user_ID = %s"
                cursor.execute(update_query, (first_name, last_name, email, timezone, user_ID))
                db.commit()
                
                success = "Personal information updated successfully"
                return render_settings_with_user_data(user_ID, success=success)
                
            elif form_type == "account_settings":
                # Update account settings
                username = request.form["username"].strip()
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                
                # Validation
                if not username:
                    error = "Username is required"
                    return render_settings_with_user_data(user_ID, error=error)
                
                if len(username) < 3:
                    error = "Username must be at least 3 characters long"
                    return render_settings_with_user_data(user_ID, error=error)
                
                # Get current user data
                query = "SELECT password FROM user_account WHERE user_ID = %s"
                cursor.execute(query, (user_ID,))
                user_data = cursor.fetchone()
                
                # Check if username is already taken by another user
                if username != user_ID:
                    query = "SELECT user_ID FROM user_account WHERE user_ID = %s"
                    cursor.execute(query, (username,))
                    existing_user = cursor.fetchone()
                    
                    if existing_user:
                        error = "This username is already taken"
                        return render_settings_with_user_data(user_ID, error=error)
                
                # Handle password change
                if new_password:
                    if not current_password:
                        error = "Current password is required to set a new password"
                        return render_settings_with_user_data(user_ID, error=error)
                    
                    if not verify_password_bcrypt(current_password, user_data["password"]):
                        error = "Current password is incorrect"
                        return render_settings_with_user_data(user_ID, error=error)
                    
                    if len(new_password) < 6:
                        error = "New password must be at least 6 characters long"
                        return render_settings_with_user_data(user_ID, error=error)
                    
                    # Update username and password
                    hashed_password = hash_password_bcrypt(new_password)
                    update_query = "UPDATE user_account SET user_ID = %s, password = %s WHERE user_ID = %s"
                    cursor.execute(update_query, (username, hashed_password, user_ID))
                else:
                    # Update only username
                    update_query = "UPDATE user_account SET user_ID = %s WHERE user_ID = %s"
                    cursor.execute(update_query, (username, user_ID))
                
                db.commit()
                
                # Update session if username changed
                if username != user_ID:
                    session["user_ID"] = username
                
                success = "Account settings updated successfully"
                return render_settings_with_user_data(username, success=success)
            
            cursor.close()
                
        except Exception as e:
            logger.error(
                "Settings update failed",
                extra={
                    "user_id": user_ID,
                    "form_type": form_type,
                    "error": str(e),
                    "request_id": getattr(g, "request_id", None),
                },
                exc_info=True,
            )
            error = "Failed to update settings. Please try again."
            return render_settings_with_user_data(user_ID, error=error)
    
    # GET request - show settings page
    return render_settings_with_user_data(user_ID)


def render_settings_with_user_data(user_ID, success=None, error=None):
    """Helper function to render settings page with user data"""
    try:
        db = get_db()
        cursor = db.cursor()
        query = "SELECT user_ID, email, first_name, last_name, timezone FROM user_account WHERE user_ID = %s"
        cursor.execute(query, (user_ID,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return redirect(url_for("auth.login"))
        
        # Get subscription status
        from src.subscription_utils import get_user_limits_status
        subscription_status = get_user_limits_status(user_ID)
        
        return render_template("settings.html", user=user, subscription_status=subscription_status, success=success, error=error)
    except Exception as e:
        logger.error(
            "Failed to load user data for settings",
            extra={
                "user_id": user_ID,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return redirect(url_for("shopping.home"))


@auth_bp.route("/logout")
def logout():
    # Only clear user authentication, preserve cart for later
    user_ID = session.get("user_ID")
    cart_ID = session.get("cart_ID")

    # Clear session but preserve cart association in database
    session.clear()

    return redirect(url_for("auth.login"))


@auth_bp.route("/upgrade", methods=["GET"])
def upgrade():
    """Show premium upgrade page with pricing and payment options"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_ID"]
    
    try:
        # Get current subscription status
        subscription_status = get_user_limits_status(user_id)
        
        # If user is already premium, redirect to settings
        if subscription_status.get('tier') == 'premium':
            return redirect(url_for("auth.settings"))
        
        # Prepare pricing data
        pricing_data = {
            "monthly": {
                "price": 7.99,
                "billing": "monthly",
                "savings": None
            },
            "annual": {
                "price": 59.99,
                "billing": "annually", 
                "monthly_equivalent": 4.99,
                "savings": 37
            }
        }
        
        # Premium features list
        premium_features = [
            {
                "icon": "fas fa-infinity",
                "title": "Unlimited Meal Plans",
                "description": "Create unlimited meal plans and plan weeks in advance"
            },
            {
                "icon": "fas fa-warehouse", 
                "title": "Unlimited Pantry Storage",
                "description": "Store unlimited ingredients and track everything you have"
            },
            {
                "icon": "fas fa-chart-line",
                "title": "Full Macro Tracking", 
                "description": "Track all macros, micronutrients, and view detailed history"
            },
            {
                "icon": "fas fa-bookmark",
                "title": "Unlimited Recipe Saving",
                "description": "Save and organize unlimited recipes for your family"
            },
            {
                "icon": "fas fa-list-ul",
                "title": "Unlimited Shopping Lists", 
                "description": "Generate unlimited shopping lists whenever you need"
            },
            {
                "icon": "fas fa-barcode",
                "title": "Unlimited UPC Scanning",
                "description": "Scan unlimited products to build your pantry quickly"
            },
            {
                "icon": "fas fa-brain",
                "title": "Advanced AI Features",
                "description": "Priority AI processing and smart suggestions"
            },
            {
                "icon": "fas fa-mobile-alt",
                "title": "Mobile App Access",
                "description": "Full access to our mobile apps (coming soon)"
            }
        ]
        
        return render_template("upgrade.html", 
                             subscription_status=subscription_status,
                             pricing=pricing_data,
                             features=premium_features)
        
    except Exception as e:
        logger.error(
            "Failed to load upgrade page",
            extra={
                "user_id": user_id,
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return redirect(url_for("shopping.home"))


# JWT API Endpoints
@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """JWT-based login endpoint for API access"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must be JSON"}), 400
            
        user_id = data.get("user_id", "").strip()
        password = data.get("password", "")
        
        if not user_id or not password:
            return jsonify({"error": "Username and password are required"}), 400
            
        # Authenticate user
        db = get_db()
        cursor = db.cursor()
        query = "SELECT * FROM user_account WHERE user_ID = %s"
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        
        if not user_data or not verify_password_bcrypt(password, user_data["password"]):
            logger.warning(
                "API login failed - invalid credentials",
                extra={
                    "user_id": user_id,
                    "request_id": getattr(g, "request_id", None),
                },
            )
            return jsonify({"error": "Invalid username or password"}), 401
            
        # Generate JWT tokens
        from src.auth_utils import AuthUtils
        tokens = AuthUtils.generate_tokens(user_id)
        
        logger.info(
            "API login successful",
            extra={
                "user_id": user_id,
                "request_id": getattr(g, "request_id", None),
            },
        )
        
        return jsonify({
            "message": "Login successful",
            "user": {
                "user_id": user_data["user_ID"],
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"]
            },
            **tokens
        }), 200
        
    except Exception as e:
        logger.error(
            "API login failed - server error",
            extra={
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return jsonify({"error": "Login failed. Please try again."}), 500


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    """JWT-based registration endpoint for API access"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must be JSON"}), 400
            
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        user_id = data.get("user_id", "").strip()
        password = data.get("password", "")
        email = data.get("email", "").strip()
        
        # Validation
        if not user_id or not password or not email:
            return jsonify({"error": "Email, username, and password are required"}), 400
            
        # Email format validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({"error": "Please enter a valid email address"}), 400
            
        if len(user_id) < 3:
            return jsonify({"error": "Username must be at least 3 characters long"}), 400
            
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400
            
        db = get_db()
        cursor = db.cursor()
        
        # Check if username exists
        query = "SELECT user_ID FROM user_account WHERE user_ID = %s"
        cursor.execute(query, (user_id,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "This username already exists"}), 409
            
        # Check if email exists
        query = "SELECT user_ID FROM user_account WHERE email = %s"
        cursor.execute(query, (email,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"error": "This email address is already registered"}), 409
            
        # Create user
        hashed_password = hash_password_bcrypt(password)
        insert_query = (
            "INSERT INTO user_account (user_ID, email, password, first_name, last_name) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        cursor.execute(insert_query, (user_id, email, hashed_password, first_name, last_name))
        
        # Set default theme preference to light mode for new users
        theme_pref_query = """
            INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type)
            VALUES (%s, 'theme_preference', 'light', 'string')
        """
        cursor.execute(theme_pref_query, (user_id,))
        
        db.commit()
        cursor.close()
        
        # Generate JWT tokens
        from src.auth_utils import AuthUtils
        tokens = AuthUtils.generate_tokens(user_id)
        
        logger.info(
            "API registration successful",
            extra={
                "user_id": user_id,
                "request_id": getattr(g, "request_id", None),
            },
        )
        
        return jsonify({
            "message": "Registration successful",
            "user": {
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            },
            **tokens
        }), 201
        
    except Exception as e:
        logger.error(
            "API registration failed - server error",
            extra={
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return jsonify({"error": "Registration failed. Please try again."}), 500


@auth_bp.route("/api/auth/refresh", methods=["POST"])
def api_refresh():
    """Refresh JWT access token using refresh token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must be JSON"}), 400
            
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400
            
        from src.auth_utils import AuthUtils
        new_tokens = AuthUtils.refresh_access_token(refresh_token)
        
        if not new_tokens:
            return jsonify({"error": "Invalid or expired refresh token"}), 401
            
        return jsonify({
            "message": "Token refreshed successfully",
            **new_tokens
        }), 200
        
    except Exception as e:
        logger.error(
            "Token refresh failed",
            extra={
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required
def api_me():
    """Get current user information using JWT token"""
    try:
        user_id = g.current_user_id
        
        db = get_db()
        cursor = db.cursor()
        query = "SELECT user_ID, email, first_name, last_name FROM user_account WHERE user_ID = %s"
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({
            "user": {
                "user_id": user_data["user_ID"],
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"]
            }
        }), 200
        
    except Exception as e:
        logger.error(
            "Get user info failed",
            extra={
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return jsonify({"error": "Failed to get user information"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
@jwt_required
def api_logout():
    """Logout endpoint for JWT tokens (token invalidation would require blacklist)"""
    try:
        # Note: In a production system, you would typically implement a token blacklist
        # For now, we'll just return success as tokens will expire naturally
        
        logger.info(
            "API logout",
            extra={
                "user_id": g.current_user_id,
                "request_id": getattr(g, "request_id", None),
            },
        )
        
        return jsonify({
            "message": "Logout successful. Token will expire naturally."
        }), 200
        
    except Exception as e:
        logger.error(
            "API logout failed",
            extra={
                "error": str(e),
                "request_id": getattr(g, "request_id", None),
            },
            exc_info=True,
        )
        return jsonify({"error": "Logout failed"}), 500


# Admin Promotional Code Management Routes
@auth_bp.route("/admin/promo-codes", methods=["GET"])
def admin_list_promo_codes():
    """List all promotional codes (admin only)"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    # Basic admin check (you might want to add proper admin role checking)
    user_id = session["user_ID"]
    if not user_id.startswith('admin'):  # Simple admin check - replace with proper role system
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status_filter = request.args.get('status', 'all')  # all, active, expired, exhausted
        
        # Build query based on filters
        where_conditions = []
        params = []
        
        if status_filter == 'active':
            where_conditions.append("is_active = TRUE AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP) AND (max_uses IS NULL OR current_uses < max_uses)")
        elif status_filter == 'expired':
            where_conditions.append("expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP")
        elif status_filter == 'exhausted':
            where_conditions.append("max_uses IS NOT NULL AND current_uses >= max_uses")
        elif status_filter == 'inactive':
            where_conditions.append("is_active = FALSE")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM promotional_codes {where_clause}"
        cursor.execute(count_query, params)
        total_codes = cursor.fetchone()['total']
        
        # Get paginated results
        offset = (page - 1) * per_page
        list_query = f"""
            SELECT 
                code_id, code, code_type, discount_value, subscription_duration_months,
                max_uses, current_uses, max_uses_per_user, expires_at, is_active,
                created_at, created_by, description,
                CASE 
                    WHEN expires_at IS NULL THEN TRUE
                    WHEN expires_at > CURRENT_TIMESTAMP THEN TRUE
                    ELSE FALSE
                END as not_expired,
                CASE 
                    WHEN max_uses IS NULL THEN TRUE
                    WHEN current_uses < max_uses THEN TRUE
                    ELSE FALSE
                END as has_uses_remaining
            FROM promotional_codes 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(list_query, params + [per_page, offset])
        codes = cursor.fetchall()
        
        # Calculate pagination info
        total_pages = (total_codes + per_page - 1) // per_page
        
        return jsonify({
            "success": True,
            "codes": codes,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_codes,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing promo codes: {e}")
        return jsonify({"success": False, "message": "Failed to list promotional codes"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()


@auth_bp.route("/admin/promo-codes", methods=["POST"])
def admin_create_promo_code():
    """Create a new promotional code (admin only)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Authentication required"}), 401
    
    user_id = session["user_ID"]
    if not user_id.startswith('admin'):  # Simple admin check
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request data required"}), 400
    
    # Validate required fields
    required_fields = ['code', 'code_type', 'description']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "message": f"{field} is required"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if code already exists
        check_query = "SELECT code_id FROM promotional_codes WHERE code = %s"
        cursor.execute(check_query, (data['code'].upper(),))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Code already exists"}), 409
        
        # Insert new promotional code
        insert_query = """
            INSERT INTO promotional_codes 
            (code, code_type, discount_value, subscription_duration_months, max_uses, 
             max_uses_per_user, expires_at, description, created_by, minimum_account_age_days, allowed_user_tiers)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Parse expiration date if provided
        expires_at = None
        if data.get('expires_at'):
            from datetime import datetime
            expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        cursor.execute(insert_query, (
            data['code'].upper(),
            data['code_type'],
            data.get('discount_value'),
            data.get('subscription_duration_months'),
            data.get('max_uses'),
            data.get('max_uses_per_user', 1),
            expires_at,
            data['description'],
            user_id,
            data.get('minimum_account_age_days', 0),
            data.get('allowed_user_tiers', 'free')
        ))
        
        code_id = cursor.lastrowid
        db.commit()
        
        logger.info(f"Admin {user_id} created promo code: {data['code']}")
        
        return jsonify({
            "success": True,
            "message": f"Promotional code '{data['code']}' created successfully",
            "code_id": code_id
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating promo code: {e}")
        return jsonify({"success": False, "message": "Failed to create promotional code"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()


@auth_bp.route("/admin/promo-codes/<int:code_id>", methods=["PUT"])
def admin_update_promo_code(code_id):
    """Update a promotional code (admin only)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Authentication required"}), 401
    
    user_id = session["user_ID"]
    if not user_id.startswith('admin'):  # Simple admin check
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request data required"}), 400
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if code exists
        check_query = "SELECT code FROM promotional_codes WHERE code_id = %s"
        cursor.execute(check_query, (code_id,))
        existing_code = cursor.fetchone()
        if not existing_code:
            return jsonify({"success": False, "message": "Promotional code not found"}), 404
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        updateable_fields = [
            'description', 'discount_value', 'subscription_duration_months', 
            'max_uses', 'max_uses_per_user', 'expires_at', 'is_active',
            'minimum_account_age_days', 'allowed_user_tiers'
        ]
        
        for field in updateable_fields:
            if field in data:
                if field == 'expires_at' and data[field]:
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    update_fields.append(f"{field} = %s")
                    params.append(expires_at)
                else:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
        
        if not update_fields:
            return jsonify({"success": False, "message": "No fields to update"}), 400
        
        update_query = f"""
            UPDATE promotional_codes 
            SET {', '.join(update_fields)}
            WHERE code_id = %s
        """
        
        params.append(code_id)
        cursor.execute(update_query, params)
        db.commit()
        
        logger.info(f"Admin {user_id} updated promo code ID {code_id}")
        
        return jsonify({
            "success": True,
            "message": "Promotional code updated successfully"
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating promo code: {e}")
        return jsonify({"success": False, "message": "Failed to update promotional code"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()


@auth_bp.route("/admin/promo-codes/<int:code_id>", methods=["DELETE"])
def admin_delete_promo_code(code_id):
    """Deactivate a promotional code (admin only)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Authentication required"}), 401
    
    user_id = session["user_ID"]
    if not user_id.startswith('admin'):  # Simple admin check
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if code exists
        check_query = "SELECT code FROM promotional_codes WHERE code_id = %s"
        cursor.execute(check_query, (code_id,))
        existing_code = cursor.fetchone()
        if not existing_code:
            return jsonify({"success": False, "message": "Promotional code not found"}), 404
        
        # Deactivate instead of delete to preserve redemption history
        update_query = "UPDATE promotional_codes SET is_active = FALSE WHERE code_id = %s"
        cursor.execute(update_query, (code_id,))
        db.commit()
        
        logger.info(f"Admin {user_id} deactivated promo code ID {code_id}")
        
        return jsonify({
            "success": True,
            "message": f"Promotional code '{existing_code['code']}' deactivated successfully"
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deactivating promo code: {e}")
        return jsonify({"success": False, "message": "Failed to deactivate promotional code"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()


@auth_bp.route("/admin/promo-codes/<int:code_id>/stats", methods=["GET"])
def admin_promo_code_stats(code_id):
    """Get statistics for a promotional code (admin only)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Authentication required"}), 401
    
    user_id = session["user_ID"]
    if not user_id.startswith('admin'):  # Simple admin check
        return jsonify({"success": False, "message": "Admin access required"}), 403
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get code details
        code_query = """
            SELECT code, code_type, description, max_uses, current_uses, 
                   created_at, expires_at, is_active
            FROM promotional_codes 
            WHERE code_id = %s
        """
        cursor.execute(code_query, (code_id,))
        code_data = cursor.fetchone()
        
        if not code_data:
            return jsonify({"success": False, "message": "Promotional code not found"}), 404
        
        # Get redemption statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_redemptions,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(CASE WHEN redemption_result = 'success' THEN 1 ELSE 0 END) as successful_redemptions,
                SUM(CASE WHEN redemption_result = 'failed' THEN 1 ELSE 0 END) as failed_redemptions,
                MIN(redeemed_at) as first_redemption,
                MAX(redeemed_at) as last_redemption
            FROM code_redemptions 
            WHERE code_id = %s
        """
        cursor.execute(stats_query, (code_id,))
        stats = cursor.fetchone()
        
        # Get recent redemptions
        recent_query = """
            SELECT cr.redeemed_at, cr.user_id, cr.redemption_result, cr.ip_address
            FROM code_redemptions cr
            WHERE cr.code_id = %s
            ORDER BY cr.redeemed_at DESC
            LIMIT 10
        """
        cursor.execute(recent_query, (code_id,))
        recent_redemptions = cursor.fetchall()
        
        return jsonify({
            "success": True,
            "code_details": code_data,
            "statistics": stats,
            "recent_redemptions": recent_redemptions
        })
        
    except Exception as e:
        logger.error(f"Error getting promo code stats: {e}")
        return jsonify({"success": False, "message": "Failed to get promotional code statistics"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()


@auth_bp.route("/api/user/preferences", methods=["GET"])
def get_user_preferences():
    """Get user preferences"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get all preferences for the user
        query = """
            SELECT preference_key, preference_value, data_type 
            FROM user_preferences 
            WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        preferences_raw = cursor.fetchall()
        
        # Convert to a dictionary
        preferences = {}
        for pref in preferences_raw:
            key = pref["preference_key"]
            value = pref["preference_value"]
            data_type = pref["data_type"]
            
            # Convert value based on data type
            if data_type == "boolean":
                preferences[key] = value.lower() == "true"
            elif data_type == "number":
                preferences[key] = float(value) if '.' in value else int(value)
            elif data_type == "json":
                import json
                preferences[key] = json.loads(value)
            else:
                preferences[key] = value
        
        cursor.close()
        return jsonify({
            "success": True,
            "preferences": preferences
        })
        
    except Exception as e:
        cursor.close()
        logger.error(f"Error getting user preferences: {e}")
        return jsonify({"success": False, "message": "Failed to get preferences"}), 500


@auth_bp.route("/api/user/preferences", methods=["POST"])
def save_user_preferences():
    """Save user preferences"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Process each preference
        for key, value in data.items():
            # Determine data type
            if isinstance(value, bool):
                data_type = "boolean"
                value_str = "true" if value else "false"
            elif isinstance(value, (int, float)):
                data_type = "number"
                value_str = str(value)
            elif isinstance(value, (list, dict)):
                data_type = "json"
                import json
                value_str = json.dumps(value)
            else:
                data_type = "string"
                value_str = str(value)
            
            # Use INSERT ... ON DUPLICATE KEY UPDATE for MySQL
            upsert_query = """
                INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                preference_value = VALUES(preference_value),
                data_type = VALUES(data_type),
                updated_at = NOW()
            """
            cursor.execute(upsert_query, (user_id, key, value_str, data_type))
        
        db.commit()
        cursor.close()
        
        logger.info(f"User preferences saved for user {user_id}")
        
        return jsonify({
            "success": True,
            "message": "Preferences saved successfully"
        })
        
    except Exception as e:
        db.rollback()
        cursor.close()
        logger.error(f"Error saving user preferences: {e}")
        return jsonify({"success": False, "message": "Failed to save preferences"}), 500


@auth_bp.route("/api/user/subscription-status", methods=["GET"])
def get_subscription_status():
    """Get user's subscription status and limits"""
    if 'user_ID' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    try:
        user_id = session['user_ID']
        status = get_user_limits_status(user_id)
        
        return jsonify({
            "success": True,
            "tier": status['tier'],
            "unlimited": status['unlimited'],
            "limits": status.get('limits', {})
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return jsonify({"success": False, "message": "Failed to get subscription status"}), 500
