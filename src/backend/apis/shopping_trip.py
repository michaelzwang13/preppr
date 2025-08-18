from flask import Blueprint, request, jsonify, session, current_app
import requests
from src.database import get_db
from src import helper

shopping_trip_bp = Blueprint("shopping_trip", __name__, url_prefix="/api")


@shopping_trip_bp.route("/shopping-trip/add-item", methods=["POST"])
def add_item():
    if "user_ID" not in session or "cart_ID" not in session:
        return jsonify({"error": "User or cart not in session"}), 400

    data = request.get_json()
    required_fields = ["upc", "quantity", "itemName", "imageUrl"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Price is now optional, default to 0 if not provided
    price = data.get("price", 0)
    if price is None:
        price = 0

    db = get_db()
    cursor = db.cursor()
    
    try:
        # Insert the cart item
        ins = "INSERT INTO cart_item (cart_ID, user_ID, quantity, item_name, price, upc, item_lifetime, image_url) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(
            ins,
            (
                session["cart_ID"],
                session["user_ID"],
                data["quantity"],
                data["itemName"],
                price,
                data["upc"],
                7,
                data["imageUrl"],
            ),
        )
        cart_item_id = cursor.lastrowid
        
        # Check if this item matches any shopping list item and link if requested
        list_item_id = data.get("list_item_id")
        if list_item_id:
            # Update the shopping list mapping to link this cart item
            update_mapping_query = """
                UPDATE shopping_list_cart_mapping 
                SET cart_item_id = %s, is_found = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE cart_id = %s AND list_item_id = %s
            """
            cursor.execute(update_mapping_query, (cart_item_id, session["cart_ID"], list_item_id))
            
            # Also mark the original shopping list item as completed
            update_list_item_query = """
                UPDATE shopping_list_items sli
                JOIN shopping_list_cart_mapping slcm ON sli.item_id = slcm.list_item_id
                SET sli.is_completed = TRUE, sli.updated_at = CURRENT_TIMESTAMP
                WHERE slcm.cart_id = %s AND slcm.list_item_id = %s
            """
            cursor.execute(update_list_item_query, (session["cart_ID"], list_item_id))

        db.commit()

        query = "SELECT * FROM cart_item WHERE cart_ID = %s"
        cursor.execute(query, (session["cart_ID"],))
        items = cursor.fetchall()
        
        return jsonify({"status": "success", "items": items}), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to add item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_trip_bp.route("/shopping-trip/remove-last-item", methods=["POST"])
def remove_last_item():
    """Remove the most recently added item from the cart"""
    if "user_ID" not in session or "cart_ID" not in session:
        return jsonify({"error": "User or cart not in session"}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        # Get the most recently added item
        query = "SELECT item_ID FROM cart_item WHERE cart_ID = %s ORDER BY item_ID DESC LIMIT 1"
        cursor.execute(query, (session["cart_ID"],))
        last_item = cursor.fetchone()

        if last_item:
            # Update shopping list mapping if this item was linked
            update_mapping_query = """
                UPDATE shopping_list_cart_mapping 
                SET cart_item_id = NULL, is_found = FALSE 
                WHERE cart_item_id = %s
            """
            cursor.execute(update_mapping_query, (last_item["item_ID"],))
            
            # Delete the item
            delete_query = "DELETE FROM cart_item WHERE item_ID = %s"
            cursor.execute(delete_query, (last_item["item_ID"],))
            db.commit()

            # Return updated cart items
            query = "SELECT * FROM cart_item WHERE cart_ID = %s"
            cursor.execute(query, (session["cart_ID"],))
            items = cursor.fetchall()
            cursor.close()

            return jsonify({"status": "success", "items": items}), 200
        else:
            return jsonify({"error": "No items to remove"}), 400

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to remove item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_trip_bp.route("/shopping-trip/update-item", methods=["POST"])
def update_item_quantity():
    """Update the quantity of an item in the cart"""
    if "user_ID" not in session or "cart_ID" not in session:
        return jsonify({"error": "User or cart not in session"}), 400

    data = request.get_json()
    if not data or "item_id" not in data or "quantity" not in data:
        return jsonify({"error": "Missing item_id or quantity"}), 400

    item_id = data["item_id"]
    quantity = data["quantity"]

    try:
        quantity = int(quantity)
        if quantity < 1:
            return jsonify({"error": "Quantity must be at least 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quantity"}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the item belongs to the current user's cart
        verify_query = "SELECT item_ID FROM cart_item WHERE item_ID = %s AND cart_ID = %s AND user_ID = %s"
        cursor.execute(verify_query, (item_id, session["cart_ID"], session["user_ID"]))
        if not cursor.fetchone():
            return jsonify({"error": "Item not found"}), 404

        # Update the quantity
        update_query = "UPDATE cart_item SET quantity = %s WHERE item_ID = %s"
        cursor.execute(update_query, (quantity, item_id))
        db.commit()

        # Return updated cart items
        query = "SELECT item_ID, item_name, price, quantity, image_url FROM cart_item WHERE cart_ID = %s"
        cursor.execute(query, (session["cart_ID"],))
        items = cursor.fetchall()

        # Calculate totals
        total_items = sum(item["quantity"] for item in items)
        total_spent = sum(item["price"] * item["quantity"] for item in items)
        allocated_budget = 1000
        remaining = allocated_budget - total_spent

        cursor.close()

        return (
            jsonify(
                {
                    "status": "success",
                    "items": items,
                    "total_items": total_items,
                    "total_spent": total_spent,
                    "allocated_budget": allocated_budget,
                    "remaining": remaining,
                }
            ),
            200,
        )

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to update item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_trip_bp.route("/shopping-trip/delete-item", methods=["POST"])
def delete_item():
    """Delete a specific item from the cart"""
    if "user_ID" not in session or "cart_ID" not in session:
        return jsonify({"error": "User or cart not in session"}), 400

    data = request.get_json()
    if not data or "item_id" not in data:
        return jsonify({"error": "Missing item_id"}), 400

    item_id = data["item_id"]

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the item belongs to the current user's cart
        verify_query = "SELECT item_ID FROM cart_item WHERE item_ID = %s AND cart_ID = %s AND user_ID = %s"
        cursor.execute(verify_query, (item_id, session["cart_ID"], session["user_ID"]))
        if not cursor.fetchone():
            return jsonify({"error": "Item not found"}), 404

        # Update shopping list mapping if this item was linked
        update_mapping_query = """
            UPDATE shopping_list_cart_mapping 
            SET cart_item_id = NULL, is_found = FALSE 
            WHERE cart_item_id = %s
        """
        cursor.execute(update_mapping_query, (item_id,))
        
        # Delete the item
        delete_query = "DELETE FROM cart_item WHERE item_ID = %s"
        cursor.execute(delete_query, (item_id,))
        db.commit()

        # Return updated cart items
        query = "SELECT item_ID, item_name, price, quantity, image_url FROM cart_item WHERE cart_ID = %s"
        cursor.execute(query, (session["cart_ID"],))
        items = cursor.fetchall()

        # Calculate totals
        total_items = sum(item["quantity"] for item in items)
        total_spent = sum(item["price"] * item["quantity"] for item in items)
        allocated_budget = 1000
        remaining = allocated_budget - total_spent

        cursor.close()

        return (
            jsonify(
                {
                    "status": "success",
                    "items": items,
                    "total_items": total_items,
                    "total_spent": total_spent,
                    "allocated_budget": allocated_budget,
                    "remaining": remaining,
                }
            ),
            200,
        )

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to delete item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_trip_bp.route("/shopping-trip/items", methods=["GET"])
def get_cart_items():
    if "cart_ID" not in session or not session["cart_ID"]:
        return jsonify(
            {
                "items": [],
                "total_items": 0,
                "total_spent": 0,
                "allocated_budget": 1000,
                "remaining": 1000,
            }
        )

    db = get_db()
    cursor = db.cursor()

    # Get items
    query = "SELECT item_ID, item_name, price, quantity, image_url FROM cart_item WHERE cart_ID = %s"
    cursor.execute(query, (session["cart_ID"],))
    items = cursor.fetchall()

    # Calculate totals
    total_items = sum(item["quantity"] for item in items)
    total_spent = sum(item["price"] * item["quantity"] for item in items)
    allocated_budget = 1000  # You can make this dynamic later
    remaining = allocated_budget - total_spent

    cursor.close()

    return jsonify(
        {
            "items": items,
            "total_items": total_items,
            "total_spent": total_spent,
            "allocated_budget": allocated_budget,
            "remaining": remaining,
        }
    )


@shopping_trip_bp.route('/shopping-trip/details', methods=['GET'])
def get_shopping_trip_details():
    """Get detailed items for a specific shopping trip"""
    if 'user_ID' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_ID = session['user_ID']
    cart_id = request.args.get('cart_id')
    
    if not cart_id:
        return jsonify({'error': 'Cart ID parameter required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get cart info and verify ownership
        cart_query = """
            SELECT cart_ID, store_name, created_at
            FROM shopping_cart 
            WHERE cart_ID = %s AND user_ID = %s AND status = 'purchased'
        """
        cursor.execute(cart_query, (cart_id, user_ID))
        cart = cursor.fetchone()
        
        if not cart:
            return jsonify({'error': 'Shopping trip not found'}), 404
        
        # Get all items for this cart
        items_query = """
            SELECT item_name, quantity, price, image_url
            FROM cart_item 
            WHERE cart_ID = %s
            ORDER BY item_name ASC
        """
        cursor.execute(items_query, (cart_id,))
        items = cursor.fetchall()
        
        # Calculate totals
        total_items = sum(item['quantity'] for item in items)
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        cursor.close()
        
        return jsonify({
            'cart_id': cart['cart_ID'],
            'store_name': cart['store_name'], 
            'created_at': cart['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'items': items,
            'total_items': total_items,
            'total_amount': float(total_amount)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get shopping trip details: {str(e)}'}), 500
    finally:
        cursor.close()


@shopping_trip_bp.route("/searchitem", methods=["GET"])
def searchitem():
    """Search for item by UPC using Nutritionix API"""
    api_id = current_app.config.get("NUTRITIONIX_API_ID")
    api_key = current_app.config.get("NUTRITIONIX_API_KEY")

    if not api_id or not api_key:
        return (
            jsonify({"error": "Nutritionix API keys are not configured", "foods": []}),
            500,
        )

    upc = request.args.get("upc")
    if not upc:
        return jsonify({"error": "UPC parameter is required"}), 400

    # Clean UPC - remove any whitespace and validate basic format
    upc = upc.strip()
    if not upc.isdigit() or len(upc) < 8:
        return jsonify({"error": "Invalid UPC format", "foods": []}), 400

    url = f"https://trackapi.nutritionix.com/v2/search/item?upc={upc}"
    headers = {
        "x-app-id": api_id,
        "x-app-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            # Item not found in Nutritionix database
            return jsonify(
                {
                    "foods": [],
                    "message": "Product not found in database",
                    "fallback": create_fallback_item(upc),
                }
            )

        response.raise_for_status()
        api_data = response.json()

        # Return the API response with enhanced structure
        return jsonify(
            {
                "foods": api_data.get("foods", []),
                "message": "Product found successfully",
                "upc": upc,
            }
        )

    except requests.exceptions.Timeout:
        return (
            jsonify(
                {
                    "error": "API request timed out",
                    "foods": [],
                    "fallback": create_fallback_item(upc),
                }
            ),
            408,
        )

    except requests.exceptions.RequestException as e:
        return (
            jsonify(
                {
                    "error": f"API request failed: {str(e)}",
                    "foods": [],
                    "fallback": create_fallback_item(upc),
                }
            ),
            500,
        )


def create_fallback_item(upc):
    """Create a fallback item when API fails or item not found"""
    return {
        "food_name": f"Unknown Product (UPC: {upc})",
        "brand_name": "Unknown Brand",
        "nf_total_carbohydrate": 0,
        "nf_sugars": 0,
        "nf_sodium": 0,
        "nf_saturated_fat": 0,
        "nf_calories": 0,
        "photo": {
            "thumb": "https://t4.ftcdn.net/jpg/02/51/95/53/360_F_251955356_FAQH0U1y1TZw3ZcdPGybwUkH90a3VAhb.jpg"
        },
        "upc": upc,
        "is_fallback": True,
    }


# Additional route alias for better API consistency
@shopping_trip_bp.route("/upc-lookup", methods=["GET"])
def upc_lookup():
    """Alias for searchitem endpoint for better API naming"""
    return searchitem()


@shopping_trip_bp.route("/predict")
def predict():
    carbs = request.args.get("carbs", 0)
    sugar = request.args.get("sugar", 0)
    sodium = request.args.get("sodium", 0)
    fat = request.args.get("fat", 0)

    if helper.model is None:
        return jsonify({"error": "Model not loaded"}), 500

    prediction = helper.predict_impulsive_purchase(carbs, sugar, sodium, fat).item()
    return jsonify({"prediction": int(prediction)})


@shopping_trip_bp.route("/learn")
def learn():
    carbs = request.args.get("carbs", 0)
    sugar = request.args.get("sugar", 0)
    sodium = request.args.get("sodium", 0)
    fat = request.args.get("fat", 0)

    if helper.model is None:
        return jsonify({"error": "Model not loaded"}), 500

    helper.model_learn(carbs, sugar, sodium, fat)
    return jsonify({"status": "learned"}), 200