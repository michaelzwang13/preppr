from flask import Blueprint, render_template, request, session, url_for, redirect, flash, jsonify
from src.database import get_db


def get_user_preference(user_id, preference_key, default_value=None):
    """Get a user preference value"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        query = """
            SELECT preference_value, data_type 
            FROM user_preferences 
            WHERE user_id = %s AND preference_key = %s
        """
        cursor.execute(query, (user_id, preference_key))
        result = cursor.fetchone()
        
        if result:
            value = result["preference_value"]
            data_type = result["data_type"]
            
            # Convert value based on data type
            if data_type == "boolean":
                return value.lower() == "true"
            elif data_type == "number":
                return float(value) if '.' in value else int(value)
            elif data_type == "json":
                import json
                return json.loads(value)
            else:
                return value
        else:
            return default_value
    except Exception as e:
        print(f"Error getting user preference {preference_key}: {e}")
        return default_value
    finally:
        cursor.close()

shopping_bp = Blueprint("shopping", __name__)


def retrieve_totals(cart_ID):
    db = get_db()
    cursor = db.cursor()

    query_items = "SELECT * FROM cart_item WHERE cart_ID = %s"
    cursor.execute(query_items, (cart_ID,))
    items = cursor.fetchall()

    query_totals = "SELECT COUNT(*) as num_items, SUM(price * quantity) AS total_spent FROM cart_item WHERE cart_ID = %s"
    cursor.execute(query_totals, (cart_ID,))
    totals = cursor.fetchone()

    total_items = totals.get("num_items", 0) if totals else 0
    total_spent = totals.get("total_spent", 0) if totals else 0

    return items, total_items, total_spent


@shopping_bp.route("/")
def index():
    return render_template("index.html")


@shopping_bp.route("/home")
def home():
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    user_ID = session["user_ID"]

    db = get_db()
    cursor = db.cursor()

    # Get user's first name
    user_query = "SELECT first_name FROM user_account WHERE user_ID = %s"
    cursor.execute(user_query, (user_ID,))
    user_data = cursor.fetchone()
    user_first_name = user_data.get("first_name") if user_data and user_data.get("first_name") else None

    # Get cart history (completed carts) - limit to 15 initially
    query = """
    SELECT c.cart_ID, c.store_name, c.created_at,
           (SELECT COUNT(*) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_items,
           (SELECT SUM(i.price * i.quantity) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_spent
    FROM shopping_cart c
    WHERE c.user_ID = %s 
      AND c.status = 'purchased'
      AND EXISTS (SELECT 1 FROM cart_item i WHERE i.cart_ID = c.cart_ID)
    ORDER BY c.created_at DESC
    LIMIT 15
    """
    cursor.execute(query, (user_ID,))
    cart_history = cursor.fetchall()

    # Check if there are more than 15 trips total
    count_query = """
    SELECT COUNT(*) as total_count
    FROM shopping_cart c
    WHERE c.user_ID = %s 
      AND c.status = 'purchased'
      AND EXISTS (SELECT 1 FROM cart_item i WHERE i.cart_ID = c.cart_ID)
    """
    cursor.execute(count_query, (user_ID,))
    count_result = cursor.fetchone()
    total_trips = count_result.get("total_count", 0) if count_result else 0

    # Check for active shopping trip
    active_query = """
    SELECT c.cart_ID, c.store_name, c.created_at,
           (SELECT COUNT(*) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_items,
           (SELECT SUM(i.price * i.quantity) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_spent
    FROM shopping_cart c
    WHERE c.user_ID = %s AND c.status = 'active'
    ORDER BY c.created_at DESC LIMIT 1
  """
    cursor.execute(active_query, (user_ID,))
    active_trip = cursor.fetchone()

    # Get count of meals prepped (individual meals created)
    meals_prepped_query = """
    SELECT COUNT(*) as meals_prepped
    FROM meals m
    WHERE m.user_id = %s
    """
    cursor.execute(meals_prepped_query, (user_ID,))
    meals_prepped_result = cursor.fetchone()
    meals_prepped = meals_prepped_result.get("meals_prepped", 0) if meals_prepped_result else 0

    cursor.close()

    # Get user preferences
    nutrition_tracking_enabled = get_user_preference(user_ID, "nutrition_tracking_enabled", True)
    
    return render_template(
        "home.html", 
        user_ID=user_ID, 
        user_first_name=user_first_name, 
        cart_history=cart_history, 
        active_trip=active_trip, 
        total_trips=total_trips, 
        meals_prepped=meals_prepped,
        nutrition_tracking_enabled=nutrition_tracking_enabled
    )


@shopping_bp.route("/shopping-history")
def shopping_history():
    """Shopping history page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    # Get all cart history (completed carts)
    query = """
    SELECT c.cart_ID, c.store_name, c.created_at,
           (SELECT COUNT(*) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_items,
           (SELECT SUM(i.price * i.quantity) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_spent
    FROM shopping_cart c
    WHERE c.user_ID = %s 
      AND c.status = 'purchased'
      AND EXISTS (SELECT 1 FROM cart_item i WHERE i.cart_ID = c.cart_ID)
    ORDER BY c.created_at DESC
    """
    cursor.execute(query, (user_ID,))
    cart_history = cursor.fetchall()
    
    # Get total count for pagination
    count_query = """
    SELECT COUNT(*) as total_count
    FROM shopping_cart c
    WHERE c.user_ID = %s 
      AND c.status = 'purchased'
      AND EXISTS (SELECT 1 FROM cart_item i WHERE i.cart_ID = c.cart_ID)
    """
    cursor.execute(count_query, (user_ID,))
    count_result = cursor.fetchone()
    total_trips = count_result.get("total_count", 0) if count_result else 0
    
    cursor.close()
    
    return render_template(
        "shopping_history.html", 
        cart_history=cart_history,
        total_trips=total_trips
    )


@shopping_bp.route("/api/shopping-history")
def get_shopping_history():
    """API endpoint to get extended shopping history"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 35, type=int)  # Default to 35 more (15 + 35 = 50 total)

    db = get_db()
    cursor = db.cursor()

    # Get additional cart history
    query = """
    SELECT c.cart_ID, c.store_name, c.created_at,
           (SELECT COUNT(*) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_items,
           (SELECT SUM(i.price * i.quantity) FROM cart_item i WHERE i.cart_ID = c.cart_ID) as total_spent
    FROM shopping_cart c
    WHERE c.user_ID = %s 
      AND c.status = 'purchased'
      AND EXISTS (SELECT 1 FROM cart_item i WHERE i.cart_ID = c.cart_ID)
    ORDER BY c.created_at DESC
    LIMIT %s OFFSET %s
    """
    cursor.execute(query, (user_ID, limit, offset))
    additional_history = cursor.fetchall()
    cursor.close()

    return jsonify({"history": additional_history})
    
    
@shopping_bp.route("/start-shopping", methods=["POST"])
def start_shopping():
    store_name = request.form.get("storeName")
    user_ID = session["user_ID"]

    db = get_db()
    cursor = db.cursor()

    # Check if user already has an active cart
    query = 'SELECT cart_ID FROM shopping_cart WHERE user_ID = %s AND status = "active" ORDER BY created_at DESC LIMIT 1'
    cursor.execute(query, (user_ID,))
    existing_cart = cursor.fetchone()

    if existing_cart:
        # Use existing active cart
        session["cart_ID"] = existing_cart["cart_ID"]
        cursor.close()
        return redirect(url_for("shopping.shopping_trip"))
    else:
        # Create new cart
        ins = (
            "INSERT INTO shopping_cart (user_ID, store_name, status) VALUES(%s, %s, %s)"
        )
        cursor.execute(ins, (user_ID, store_name, "active"))
        db.commit()
        session["cart_ID"] = cursor.lastrowid
        cursor.close()

        return redirect(url_for("shopping.shopping_trip"))
    
    
@shopping_bp.route("/shopping-trip")
def shopping_trip():
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    cart_session = None
    items = []
    total_items = 0
    total_spent = 0
    cart_ID = None

    # First check if cart_ID is in session
    if "cart_ID" in session and session["cart_ID"]:
        cart_ID = session["cart_ID"]
    else:
        # If not in session, look for active cart in database
        user_ID = session["user_ID"]
        db = get_db()
        cursor = db.cursor()
        query = 'SELECT cart_ID FROM shopping_cart WHERE user_ID = %s AND status = "active" ORDER BY created_at DESC LIMIT 1'
        cursor.execute(query, (user_ID,))
        active_cart = cursor.fetchone()

        if active_cart:
            cart_ID = active_cart["cart_ID"]
            session["cart_ID"] = cart_ID  # Restore to session

        cursor.close()

    # If we have a cart_ID, get the cart details
    if cart_ID:
        db = get_db()
        cursor = db.cursor()
        query = 'SELECT * FROM shopping_cart WHERE cart_ID = %s AND status = "active"'
        cursor.execute(query, (cart_ID,))
        cart_session = cursor.fetchone()

        if cart_session:
            items, total_items, total_spent = retrieve_totals(cart_ID)
        else:
            # Cart was completed or doesn't exist, clear from session
            session.pop("cart_ID", None)

        cursor.close()

    return render_template(
        "shopping_trip.html",
        cart_session=cart_session,
        allocated_budget=1000,
        remaining=1000 - (total_spent or 0),
        cart_items=items,
        total_items=total_items,
        total_spent=total_spent,
    )


@shopping_bp.route("/finish-shopping", methods=["POST"])
def finish_shopping():
    cart_ID = session.pop("cart_ID", None)
    if cart_ID:
        db = get_db()
        cursor = db.cursor()

        # Calculate total spent for this cart
        total_query = "SELECT SUM(price * quantity) AS total_spent FROM cart_item WHERE cart_ID = %s"
        cursor.execute(total_query, (cart_ID,))
        total_result = cursor.fetchone()
        total_spent = float(total_result["total_spent"] or 0)

        # Update cart status to purchased
        query = "UPDATE shopping_cart SET status = 'purchased' WHERE cart_ID = %s"
        cursor.execute(query, (cart_ID,))
        db.commit()
        cursor.close()

        # Update budget with this spending
        if "user_ID" in session and total_spent > 0:
            from src.backend.apis.budget import update_budget_spending

            update_budget_spending(session["user_ID"], total_spent)

        # Redirect to pantry transfer page
        return redirect(url_for("shopping.pantry_transfer", cart_id=cart_ID))

    return redirect(url_for("shopping.home"))


@shopping_bp.route("/cancel-shopping", methods=["POST"])
def cancel_shopping():
    cart_ID = session.pop("cart_ID", None)
    if cart_ID:
        db = get_db()
        cursor = db.cursor()
        try:
            # Delete in proper order to avoid foreign key constraint violations
            # 1. Delete shopping list cart mappings first
            cursor.execute("DELETE FROM shopping_list_cart_mapping WHERE cart_id = %s", (cart_ID,))
            # 2. Delete cart items
            cursor.execute("DELETE FROM cart_item WHERE cart_ID = %s", (cart_ID,))
            # 3. Finally delete the cart
            cursor.execute("DELETE FROM shopping_cart WHERE cart_ID = %s", (cart_ID,))
            db.commit()
            flash("Your shopping trip has been canceled.", "info")
        except Exception as e:
            db.rollback()
            flash(f"Error canceling shopping trip: {str(e)}", "error")
        finally:
            cursor.close()
    return redirect(url_for("shopping.home"))


@shopping_bp.route("/shopping-lists")
def shopping_lists():
    """Show the shopping lists page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    return render_template("shopping_list.html")



@shopping_bp.route("/budget")
def budget():
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    # Get user preferences
    nutrition_tracking_enabled = get_user_preference(session["user_ID"], "nutrition_tracking_enabled", True)
    
    return render_template("budget.html", nutrition_tracking_enabled=nutrition_tracking_enabled)


@shopping_bp.route("/nutrition")
def nutrition():
    """Show nutrition analytics and goals page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
      
    # Check if nutrition tracking is enabled
    nutrition_tracking_enabled = get_user_preference(session["user_ID"], "nutrition_tracking_enabled", True)
        
    # Always show the nutrition page, but with different states
    return render_template("nutrition.html", nutrition_tracking_enabled=nutrition_tracking_enabled)


@shopping_bp.route("/pantry-transfer")
def pantry_transfer():
    """Show pantry transfer page after completing shopping trip"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    cart_id = request.args.get("cart_id")
    if not cart_id:
        return redirect(url_for("shopping.home"))

    db = get_db()
    cursor = db.cursor()

    # Get cart details and items
    cart_query = "SELECT * FROM shopping_cart WHERE cart_ID = %s AND user_ID = %s"
    cursor.execute(cart_query, (cart_id, session["user_ID"]))
    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        return redirect(url_for("shopping.home"))

    # Get cart items
    items_query = "SELECT * FROM cart_item WHERE cart_ID = %s"
    cursor.execute(items_query, (cart_id,))
    items = cursor.fetchall()

    cursor.close()

    return render_template("pantry_transfer.html", cart=cart, items=items)


@shopping_bp.route("/pantry")
def pantry():
    """Show user's pantry management page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    return render_template("pantry.html")


@shopping_bp.route("/meal-plans")
def meal_plans():
    """Show meal plans page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    # Get user preferences
    nutrition_tracking_enabled = get_user_preference(session["user_ID"], "nutrition_tracking_enabled", True)
    
    return render_template("meal_plans.html", nutrition_tracking_enabled=nutrition_tracking_enabled)


@shopping_bp.route("/meal-plans/advanced")
def advanced_meal_planning():
    """Show advanced meal planning page with AI chatbot"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))
    
    # Get user preferences
    nutrition_tracking_enabled = get_user_preference(session["user_ID"], "nutrition_tracking_enabled", True)
    
    return render_template("advanced_meal_planning.html", nutrition_tracking_enabled=nutrition_tracking_enabled)


@shopping_bp.route("/meal-plans/<int:plan_id>")
def meal_plan_details(plan_id):
    """Show detailed view of a specific meal plan"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Verify plan belongs to user and get basic info
        verify_query = "SELECT * FROM meal_plan_sessions WHERE session_id = %s AND user_id = %s"
        cursor.execute(verify_query, (plan_id, user_id))
        plan = cursor.fetchone()

        if not plan:
            flash("Meal plan not found.", "error")
            return redirect(url_for("shopping.meal_plans"))

        # Get user preferences
        nutrition_tracking_enabled = get_user_preference(user_id, "nutrition_tracking_enabled", True)
        
        cursor.close()
        return render_template("meal_plan_details.html", plan_id=plan_id, plan=plan, nutrition_tracking_enabled=nutrition_tracking_enabled)

    except Exception as e:
        cursor.close()
        flash(f"Error loading meal plan: {str(e)}", "error")
        return redirect(url_for("shopping.meal_plans"))


@shopping_bp.route("/recipes")
def recipes():
    """Show saved recipes page"""
    if "user_ID" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_ID"]
    return render_template("recipes.html")
