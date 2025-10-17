from flask import Blueprint, request, jsonify, session
from src.database import get_db

shopping_list_integration_bp = Blueprint("shopping_list_integration", __name__, url_prefix="/api")

@shopping_list_integration_bp.route("/shopping-trip/create-cart", methods=["POST"])
def create_cart_with_list():
    """Create a new shopping cart and optionally import a shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    store_name = data.get("store_name", "").strip()
    import_list_id = data.get("import_list_id")

    if not store_name:
        return jsonify({"error": "Store name is required"}), 400

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        print(f"[DEBUG] Creating cart with store_name='{store_name}', import_list_id={import_list_id}")
        
        # Check if user already has an active cart
        existing_query = 'SELECT cart_ID FROM shopping_cart WHERE user_ID = %s AND status = "active" ORDER BY created_at DESC LIMIT 1'
        cursor.execute(existing_query, (user_ID,))
        existing_cart = cursor.fetchone()

        if existing_cart:
            # Use existing active cart
            cart_id = existing_cart["cart_ID"]
            print(f"[DEBUG] Using existing cart: {cart_id}")
            # Update store name if different
            update_query = "UPDATE shopping_cart SET store_name = %s WHERE cart_ID = %s"
            cursor.execute(update_query, (store_name, cart_id))
        else:
            # Create new cart
            create_query = "INSERT INTO shopping_cart (user_ID, store_name, status) VALUES(%s, %s, %s)"
            cursor.execute(create_query, (user_ID, store_name, "active"))
            cart_id = cursor.lastrowid
            print(f"[DEBUG] Created new cart: {cart_id}")

        # Store cart ID in session
        session["cart_ID"] = cart_id

        # If importing a list, do that now
        if import_list_id:
            print(f"[DEBUG] Importing list {import_list_id} into cart {cart_id}")
            
            # Verify the shopping list belongs to the user
            verify_list_query = """
                SELECT list_id, list_name FROM shopping_lists 
                WHERE list_id = %s AND user_id = %s AND is_active = TRUE
            """
            cursor.execute(verify_list_query, (import_list_id, user_ID))
            shopping_list = cursor.fetchone()

            if not shopping_list:
                print(f"[DEBUG] Shopping list {import_list_id} not found for user {user_ID}")
                db.rollback()
                return jsonify({"error": "Shopping list not found"}), 404

            print(f"[DEBUG] Found shopping list: {shopping_list['list_name']}")

            # Try to link the shopping list to the cart (this might fail if column doesn't exist)
            try:
                update_cart_query = """
                    UPDATE shopping_cart SET shopping_list_id = %s WHERE cart_ID = %s
                """
                cursor.execute(update_cart_query, (import_list_id, cart_id))
                print(f"[DEBUG] Successfully linked list {import_list_id} to cart {cart_id}")
            except Exception as update_error:
                print(f"[DEBUG] Failed to update cart with shopping_list_id: {update_error}")
                # Continue without linking - the mapping table will still work

            # Get all items from the shopping list
            get_items_query = """
                SELECT item_id, item_name, quantity, notes, is_completed
                FROM shopping_list_items 
                WHERE list_id = %s
                ORDER BY created_at ASC
            """
            cursor.execute(get_items_query, (import_list_id,))
            list_items = cursor.fetchall()
            print(f"[DEBUG] Found {len(list_items)} items in shopping list")

            # Create mappings for each list item
            mapping_count = 0
            for item in list_items:
                try:
                    mapping_query = """
                        INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                    """
                    cursor.execute(mapping_query, (cart_id, item["item_id"], item["is_completed"]))
                    mapping_count += 1
                except Exception as mapping_error:
                    print(f"[DEBUG] Failed to create mapping for item {item['item_id']}: {mapping_error}")
            
            print(f"[DEBUG] Created {mapping_count} mappings")

        db.commit()
        print(f"[DEBUG] Transaction committed successfully")

        return jsonify({
            "success": True,
            "cart_id": cart_id,
            "store_name": store_name,
            "imported_list": import_list_id is not None
        }), 200

    except Exception as e:
        print(f"[DEBUG] Error in create_cart_with_list: {e}")
        db.rollback()
        return jsonify({"error": f"Failed to create shopping cart: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_integration_bp.route("/shopping-trip/list-status", methods=["GET"])
def get_shopping_list_status():
    """Get the current shopping list status for an active trip"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    cart_id = request.args.get("cart_id")
    if not cart_id:
        return jsonify({"error": "cart_id is required"}), 400

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Get the shopping list linked to this cart
        cart_query = """
            SELECT sc.shopping_list_id, sl.list_name
            FROM shopping_cart sc
            LEFT JOIN shopping_lists sl ON sc.shopping_list_id = sl.list_id
            WHERE sc.cart_ID = %s AND sc.user_ID = %s AND sc.status = 'active'
        """
        cursor.execute(cart_query, (cart_id, user_ID))
        cart_info = cursor.fetchone()

        if not cart_info or not cart_info["shopping_list_id"]:
            return jsonify({"has_list": False})

        # Get all list items with their status
        items_query = """
            SELECT 
                sli.item_id,
                sli.item_name,
                sli.quantity,
                sli.notes,
                sli.is_completed as originally_completed,
                slcm.is_found,
                slcm.cart_item_id,
                ci.item_name as cart_item_name,
                ci.quantity as cart_quantity,
                ci.price as cart_price
            FROM shopping_list_items sli
            LEFT JOIN shopping_list_cart_mapping slcm ON sli.item_id = slcm.list_item_id 
                AND slcm.cart_id = %s
            LEFT JOIN cart_item ci ON slcm.cart_item_id = ci.item_ID
            WHERE sli.list_id = %s
            ORDER BY sli.created_at ASC
        """
        cursor.execute(items_query, (cart_id, cart_info["shopping_list_id"]))
        items = cursor.fetchall()

        # Format the response
        formatted_items = []
        for item in items:
            formatted_items.append({
                "list_item_id": item["item_id"],
                "name": item["item_name"],
                "quantity": item["quantity"],
                "notes": item["notes"],
                "originally_completed": bool(item["originally_completed"]),
                "is_found": bool(item["is_found"]),
                "in_cart": item["cart_item_id"] is not None,
                "cart_item_id": item["cart_item_id"],
                "cart_details": {
                    "name": item["cart_item_name"],
                    "quantity": item["cart_quantity"],
                    "price": float(item["cart_price"]) if item["cart_price"] else None
                } if item["cart_item_id"] else None
            })

        return jsonify({
            "has_list": True,
            "list_name": cart_info["list_name"],
            "items": formatted_items
        })

    except Exception as e:
        return jsonify({"error": f"Failed to get shopping list status: {str(e)}"}), 500
    finally:
        cursor.close()

@shopping_list_integration_bp.route("/shopping-trip/mark-found", methods=["POST"])
def mark_item_found():
    """Mark a shopping list item as found during shopping"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    list_item_id = data.get("list_item_id")
    cart_id = data.get("cart_id")
    is_found = data.get("is_found", True)

    if not list_item_id or not cart_id:
        return jsonify({"error": "list_item_id and cart_id are required"}), 400

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the cart belongs to the user
        verify_query = """
            SELECT cart_ID FROM shopping_cart 
            WHERE cart_ID = %s AND user_ID = %s AND status = 'active'
        """
        cursor.execute(verify_query, (cart_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"error": "Shopping cart not found"}), 404

        # Update the mapping
        update_query = """
            UPDATE shopping_list_cart_mapping 
            SET is_found = %s, updated_at = CURRENT_TIMESTAMP
            WHERE cart_id = %s AND list_item_id = %s
        """
        cursor.execute(update_query, (is_found, cart_id, list_item_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Shopping list item mapping not found"}), 404

        # Also update the original shopping list item
        update_original_query = """
            UPDATE shopping_list_items sli
            JOIN shopping_list_cart_mapping slcm ON sli.item_id = slcm.list_item_id
            SET sli.is_completed = %s, sli.updated_at = CURRENT_TIMESTAMP
            WHERE slcm.cart_id = %s AND slcm.list_item_id = %s
        """
        cursor.execute(update_original_query, (is_found, cart_id, list_item_id))

        db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to update item status: {str(e)}"}), 500
    finally:
        cursor.close()

@shopping_list_integration_bp.route("/shopping-trip/link-cart-item", methods=["POST"])
def link_cart_item():
    """Link a cart item to a shopping list item"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    list_item_id = data.get("list_item_id")
    cart_item_id = data.get("cart_item_id")
    cart_id = data.get("cart_id")

    if not list_item_id or not cart_item_id or not cart_id:
        return jsonify({"error": "list_item_id, cart_item_id, and cart_id are required"}), 400

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify ownership
        verify_query = """
            SELECT sc.cart_ID 
            FROM shopping_cart sc
            WHERE sc.cart_ID = %s AND sc.user_ID = %s AND sc.status = 'active'
        """
        cursor.execute(verify_query, (cart_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"error": "Shopping cart not found"}), 404

        # Update the mapping to link cart item
        update_query = """
            UPDATE shopping_list_cart_mapping 
            SET cart_item_id = %s, is_found = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE cart_id = %s AND list_item_id = %s
        """
        cursor.execute(update_query, (cart_item_id, cart_id, list_item_id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Shopping list item mapping not found"}), 404

        # Also mark the original list item as completed
        update_original_query = """
            UPDATE shopping_list_items sli
            JOIN shopping_list_cart_mapping slcm ON sli.item_id = slcm.list_item_id
            SET sli.is_completed = TRUE, sli.updated_at = CURRENT_TIMESTAMP
            WHERE slcm.cart_id = %s AND slcm.list_item_id = %s
        """
        cursor.execute(update_original_query, (cart_id, list_item_id))

        db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to link cart item: {str(e)}"}), 500
    finally:
        cursor.close()

@shopping_list_integration_bp.route("/shopping-trip/available-lists", methods=["GET"])  
def get_available_lists():
    """Get all available shopping lists for the user"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Get all active shopping lists for the user
        query = """
            SELECT 
                sl.list_id,
                sl.list_name,
                sl.description,
                sl.created_at,
                sl.updated_at,
                COUNT(sli.item_id) as item_count,
                COUNT(CASE WHEN sli.is_completed = TRUE THEN 1 END) as completed_count
            FROM shopping_lists sl
            LEFT JOIN shopping_list_items sli ON sl.list_id = sli.list_id
            WHERE sl.user_id = %s AND sl.is_active = TRUE
            GROUP BY sl.list_id, sl.list_name, sl.description, sl.created_at, sl.updated_at
            ORDER BY sl.updated_at DESC
        """
        cursor.execute(query, (user_ID,))
        lists = cursor.fetchall()

        formatted_lists = []
        for lst in lists:
            formatted_lists.append({
                "id": lst["list_id"],
                "name": lst["list_name"],
                "description": lst["description"],
                "item_count": lst["item_count"],
                "completed_count": lst["completed_count"],
                "created_at": lst["created_at"].isoformat() if lst["created_at"] else None,
                "updated_at": lst["updated_at"].isoformat() if lst["updated_at"] else None
            })

        return jsonify({"lists": formatted_lists})

    except Exception as e:
        return jsonify({"error": f"Failed to get shopping lists: {str(e)}"}), 500
    finally:
        cursor.close()