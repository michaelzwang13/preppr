from flask import Blueprint, request, jsonify, session, current_app
import requests
from src.database import get_db
from src import helper
from src.subscription_utils import subscription_required

shopping_list_bp = Blueprint("shopping_list", __name__, url_prefix="/api")

# Shopping Lists API Routes


@shopping_list_bp.route("/shopping-lists", methods=["GET"])
def get_shopping_lists():
    """Get all shopping lists for the current user"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Get all shopping lists for the user
        query = """
            SELECT list_id, list_name, description, created_at, updated_at, is_active
            FROM shopping_lists 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY updated_at DESC
        """
        cursor.execute(query, (user_ID,))
        lists = cursor.fetchall()

        # For each list, get its items
        for shopping_list in lists:
            list_id = shopping_list["list_id"]
            items_query = """
                SELECT item_id, item_name, quantity, notes, is_completed, created_at, updated_at
                FROM shopping_list_items 
                WHERE list_id = %s
                ORDER BY created_at ASC
            """
            cursor.execute(items_query, (list_id,))
            items = cursor.fetchall()

            # Convert items to list format expected by frontend
            shopping_list["items"] = [
                {
                    "id": item["item_id"],
                    "name": item["item_name"],
                    "quantity": item["quantity"],
                    "notes": item["notes"],
                    "is_completed": bool(item["is_completed"]),
                    "created_at": (
                        item["created_at"].isoformat() if item["created_at"] else None
                    ),
                    "updated_at": (
                        item["updated_at"].isoformat() if item["updated_at"] else None
                    ),
                }
                for item in items
            ]

            # Convert list timestamps to strings
            shopping_list["id"] = shopping_list["list_id"]
            shopping_list["name"] = shopping_list["list_name"]
            shopping_list["created_at"] = (
                shopping_list["created_at"].isoformat()
                if shopping_list["created_at"]
                else None
            )
            shopping_list["updated_at"] = (
                shopping_list["updated_at"].isoformat()
                if shopping_list["updated_at"]
                else None
            )

        return jsonify({"lists": lists})

    except Exception as e:
        return jsonify({"error": f"Failed to fetch shopping lists: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists", methods=["POST"])
@subscription_required('shopping_lists_per_day')
def create_shopping_list():
    """Create a new shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    user_ID = session["user_ID"]
    list_name = data.get("name", "").strip()
    description = data.get("description", "").strip()

    if not list_name:
        return jsonify({"error": "List name is required"}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        # Insert new shopping list
        query = """
            INSERT INTO shopping_lists (user_id, list_name, description)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (user_ID, list_name, description))
        list_id = cursor.lastrowid
        db.commit()

        # Return the created list
        new_list = {
            "id": list_id,
            "name": list_name,
            "description": description,
            "items": [],
            "created_at": None,  # Will be set by database
            "updated_at": None,
        }

        return jsonify({"list": new_list}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to create shopping list: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists/<int:list_id>", methods=["PATCH"])
def update_shopping_list(list_id):
    """Update a shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    user_ID = session["user_ID"]

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the list belongs to the user
        verify_query = (
            "SELECT list_id FROM shopping_lists WHERE list_id = %s AND user_id = %s"
        )
        cursor.execute(verify_query, (list_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"error": "Shopping list not found"}), 404

        # Update the list
        update_fields = []
        update_values = []

        if "name" in data:
            update_fields.append("list_name = %s")
            update_values.append(data["name"].strip())

        if "description" in data:
            update_fields.append("description = %s")
            update_values.append(data["description"].strip())

        if update_fields:
            update_values.append(list_id)
            query = f"UPDATE shopping_lists SET {', '.join(update_fields)} WHERE list_id = %s"
            cursor.execute(query, update_values)
            db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to update shopping list: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists/<int:list_id>", methods=["DELETE"])
def delete_shopping_list(list_id):
    """Delete a shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the list belongs to the user
        verify_query = (
            "SELECT list_id FROM shopping_lists WHERE list_id = %s AND user_id = %s"
        )
        cursor.execute(verify_query, (list_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"error": "Shopping list not found"}), 404

        # Set is_active to FALSE instead of deleting (soft delete)
        query = "UPDATE shopping_lists SET is_active = FALSE WHERE list_id = %s"
        cursor.execute(query, (list_id,))
        db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to delete shopping list: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists/<int:list_id>/items", methods=["POST"])
def add_item_to_list(list_id):
    """Add an item to a shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    user_ID = session["user_ID"]
    item_name = data.get("name", "").strip()
    quantity = data.get("quantity", 1)
    notes = data.get("notes", "").strip()

    if not item_name:
        return jsonify({"error": "Item name is required"}), 400

    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the list belongs to the user and check item count
        verify_query = """
            SELECT sl.list_id, COUNT(sli.item_id) as item_count
            FROM shopping_lists sl
            LEFT JOIN shopping_list_items sli ON sl.list_id = sli.list_id
            WHERE sl.list_id = %s AND sl.user_id = %s AND sl.is_active = TRUE
            GROUP BY sl.list_id
        """
        cursor.execute(verify_query, (list_id, user_ID))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Shopping list not found"}), 404

        # Check 25 item limit
        if result["item_count"] >= 25:
            return (
                jsonify({"error": "Cannot add more items. Maximum 25 items per list."}),
                400,
            )

        # Insert new item
        query = """
            INSERT INTO shopping_list_items (list_id, item_name, quantity, notes)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (list_id, item_name, quantity, notes))
        item_id = cursor.lastrowid
        db.commit()

        # Return the created item
        new_item = {
            "id": item_id,
            "name": item_name,
            "quantity": quantity,
            "notes": notes,
            "is_completed": False,
        }

        return jsonify({"item": new_item}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to add item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route(
    "/shopping-lists/<int:list_id>/items/<int:item_id>/toggle", methods=["PATCH"]
)
def toggle_item_completion(list_id, item_id):
    """Toggle item completion status"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the item belongs to a list owned by the user
        verify_query = """
            SELECT sli.item_id, sli.is_completed
            FROM shopping_list_items sli
            JOIN shopping_lists sl ON sli.list_id = sl.list_id
            WHERE sli.item_id = %s AND sli.list_id = %s AND sl.user_id = %s AND sl.is_active = TRUE
        """
        cursor.execute(verify_query, (item_id, list_id, user_ID))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Item not found"}), 404

        # Toggle completion status
        new_status = not bool(result["is_completed"])
        query = "UPDATE shopping_list_items SET is_completed = %s WHERE item_id = %s"
        cursor.execute(query, (new_status, item_id))
        db.commit()

        return jsonify({"success": True, "is_completed": new_status})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to toggle item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists/<int:list_id>/items/<int:item_id>", methods=["PATCH"])
def update_shopping_list_item(list_id, item_id):
    """Update a shopping list item (name or quantity)"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    user_ID = session["user_ID"]

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the item belongs to a list owned by the user
        verify_query = """
            SELECT sli.item_id
            FROM shopping_list_items sli
            JOIN shopping_lists sl ON sli.list_id = sl.list_id
            WHERE sli.item_id = %s AND sli.list_id = %s AND sl.user_id = %s AND sl.is_active = TRUE
        """
        cursor.execute(verify_query, (item_id, list_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"error": "Item not found"}), 404

        # Update the item
        update_fields = []
        update_values = []

        if "name" in data:
            item_name = data["name"].strip()
            if not item_name:
                return jsonify({"error": "Item name cannot be empty"}), 400
            update_fields.append("item_name = %s")
            update_values.append(item_name)

        if "quantity" in data:
            try:
                quantity = int(data["quantity"])
                if quantity < 1:
                    return jsonify({"error": "Quantity must be at least 1"}), 400
                update_fields.append("quantity = %s")
                update_values.append(quantity)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid quantity"}), 400

        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400

        # Add updated timestamp and item_id for WHERE clause
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(item_id)

        query = f"UPDATE shopping_list_items SET {', '.join(update_fields)} WHERE item_id = %s"
        cursor.execute(query, update_values)
        db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to update item: {str(e)}"}), 500
    finally:
        cursor.close()


@shopping_list_bp.route("/shopping-lists/<int:list_id>/items/<int:item_id>", methods=["DELETE"])
def delete_item_from_list(list_id, item_id):
    """Delete an item from a shopping list"""
    if "user_ID" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify the item belongs to a list owned by the user
        verify_query = """
            SELECT sli.item_id
            FROM shopping_list_items sli
            JOIN shopping_lists sl ON sli.list_id = sl.list_id
            WHERE sli.item_id = %s AND sli.list_id = %s AND sl.user_id = %s AND sl.is_active = TRUE
        """
        cursor.execute(verify_query, (item_id, list_id, user_ID))

        if not cursor.fetchone():
            return jsonify({"error": "Item not found"}), 404

        # Delete the item
        query = "DELETE FROM shopping_list_items WHERE item_id = %s"
        cursor.execute(query, (item_id,))
        db.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Failed to delete item: {str(e)}"}), 500
    finally:
        cursor.close()