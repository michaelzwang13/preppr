from flask import Blueprint, request, jsonify, session, current_app
from src.database import get_db
from src.subscription_utils import check_subscription_limit, SubscriptionLimitExceeded, increment_usage

pantry_bp = Blueprint("pantry", __name__, url_prefix="/api")

@pantry_bp.route("/pantry/items", methods=["GET"])
def get_pantry_items():
    """Get all pantry items for the current user with tags"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    # Get filter parameters
    storage_filter = request.args.get("storage_type", "")
    category_filter = request.args.get("category", "")
    expiry_filter = request.args.get("expiry_status", "")

    try:
        # Build query with filters - get basic item info
        query = """
            SELECT p.*, 
                   CASE 
                       WHEN p.expiration_date IS NULL THEN 'no_expiry'
                       WHEN p.expiration_date < CURDATE() THEN 'expired'
                       WHEN p.expiration_date <= DATE_ADD(CURDATE(), INTERVAL 3 DAY) THEN 'expiring_soon'
                       ELSE 'fresh'
                   END as expiry_status,
                   DATEDIFF(p.expiration_date, CURDATE()) as days_until_expiry
            FROM pantry_items p
            WHERE p.user_id = %s AND p.is_consumed = FALSE
        """
        params = [user_ID]

        # Add storage filter
        if storage_filter:
            query += " AND p.storage_type = %s"
            params.append(storage_filter)

        # Add category filter
        if category_filter:
            query += " AND p.category = %s"
            params.append(category_filter)

        query += " ORDER BY p.expiration_date ASC, p.date_added DESC"

        cursor.execute(query, params)
        all_items = cursor.fetchall()

        # Get tags for all items
        item_ids = [item['pantry_item_id'] for item in all_items]
        item_tags = {}
        
        if item_ids:
            # Get tags for all items in one query
            tags_query = """
                SELECT pit.pantry_item_id, pt.tag_name, pt.tag_color
                FROM pantry_item_tags pit
                JOIN pantry_tags pt ON pit.tag_id = pt.tag_id
                WHERE pit.pantry_item_id IN (%s)
                ORDER BY pt.tag_name
            """ % ','.join(['%s'] * len(item_ids))
            
            cursor.execute(tags_query, item_ids)
            tag_results = cursor.fetchall()
            
            # Group tags by item
            for tag_result in tag_results:
                item_id = tag_result['pantry_item_id']
                if item_id not in item_tags:
                    item_tags[item_id] = []
                item_tags[item_id].append({
                    'name': tag_result['tag_name'],
                    'color': tag_result['tag_color']
                })

        # Add tags to items
        for item in all_items:
            item['tags'] = item_tags.get(item['pantry_item_id'], [])

        # Apply expiry filter if needed (post-query filtering for computed field)
        items = []
        for item in all_items:
            if expiry_filter:
                if expiry_filter == "expired" and item["expiry_status"] != "expired":
                    continue
                elif (
                    expiry_filter == "expiring_soon"
                    and item["expiry_status"] != "expiring_soon"
                ):
                    continue
                elif expiry_filter == "fresh" and item["expiry_status"] not in [
                    "fresh",
                    "no_expiry",
                ]:
                    continue
            items.append(item)

        # Group items by category for better organization
        categorized_items = {}
        for item in items:
            category = item["category"] or "Other"
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)

        return jsonify(
            {
                "success": True,
                "items": items,
                "categorized_items": categorized_items,
                "total_items": len(items),
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Failed to get pantry items: {str(e)}"}
        )
    finally:
        cursor.close()


@pantry_bp.route("/pantry/items", methods=["POST"])
def add_pantry_item():
    """Add a new item to pantry manually"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    data = request.get_json()
    user_ID = session["user_ID"]
    
    # Check subscription limits - free tier limited to 50 pantry items
    try:
        check_subscription_limit(user_ID, 'pantry_items')
    except SubscriptionLimitExceeded as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'limit_type': e.limit_type,
            'current_limit': e.current_limit,
            'requires_upgrade': True
        }), 403

    # Required fields
    item_name = data.get("item_name", "").strip()
    quantity = data.get("quantity", 1)
    unit = data.get("unit", "pcs")

    # Optional fields
    category = data.get("category", "Other")
    storage_type = data.get("storage_type", "pantry")
    expiration_date = data.get("expiration_date")  # YYYY-MM-DD format
    use_ai_prediction = data.get("ai_predict_expiry", False)  # Fixed parameter name
    notes = data.get("notes", "")
    tag_ids = data.get("tag_ids", [])  # List of tag IDs to assign
    
    print(f'Tag IDS: {tag_ids}')

    if not item_name:
        return jsonify({"success": False, "message": "Item name is required"})

    try:
        quantity = float(quantity)
        if quantity <= 0:
            return jsonify({"success": False, "message": "Quantity must be positive"})
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid quantity"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Handle AI expiration prediction and category prediction
        is_ai_predicted = False
        predicted_category = None
        if use_ai_prediction and not expiration_date:
            prediction_result = predict_expiration_and_category(item_name, storage_type)
            if prediction_result:
                expiration_date = prediction_result.get('expiration_date')
                predicted_category = prediction_result.get('category')
                if expiration_date:
                    is_ai_predicted = True
                if predicted_category and category == 'Other':
                    category = predicted_category

        # Insert pantry item
        query = """
            INSERT INTO pantry_items (
                user_id, item_name, quantity, unit, category, storage_type,
                expiration_date, source_type, is_ai_predicted_expiry, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Debug: print the values being inserted
        print(
            f"DEBUG: Inserting pantry item - user_ID: {user_ID}, item_name: {item_name}, quantity: {quantity}"
        )

        cursor.execute(
            query,
            (
                user_ID,
                item_name,
                quantity,
                unit,
                category,
                storage_type,
                expiration_date,
                "manual",
                is_ai_predicted,
                notes,
            ),
        )

        item_id = cursor.lastrowid
        
        # Handle tags if provided
        if tag_ids:
            # Verify tags belong to user
            placeholders = ','.join(['%s'] * len(tag_ids))
            tag_verify_query = f"""
                SELECT tag_id FROM pantry_tags 
                WHERE tag_id IN ({placeholders}) AND user_id = %s
            """
            cursor.execute(tag_verify_query, tag_ids + [user_ID])
            valid_tags = [row['tag_id'] for row in cursor.fetchall()]
            
            # Add valid tags to item
            for tag_id in valid_tags:
                try:
                    cursor.execute(
                        "INSERT INTO pantry_item_tags (pantry_item_id, tag_id) VALUES (%s, %s)",
                        (item_id, tag_id)
                    )
                    cursor.execute(
                        "UPDATE pantry_tags SET usage_count = usage_count + 1 WHERE tag_id = %s",
                        (tag_id,)
                    )
                except:
                    continue  # Skip duplicates (likely due to unique constraint)
        
        db.commit()
        
        # Increment pantry items usage counter (for subscription limits)
        increment_usage(user_ID, 'pantry_items')

        # Return the created item with tags
        cursor.execute("SELECT * FROM pantry_items WHERE pantry_item_id = %s", (item_id,))
        new_item = cursor.fetchone()
        
        # Get tags for the new item
        tags_query = """
            SELECT pt.tag_name, pt.tag_color
            FROM pantry_item_tags pit
            JOIN pantry_tags pt ON pit.tag_id = pt.tag_id
            WHERE pit.pantry_item_id = %s
        """
        cursor.execute(tags_query, (item_id,))
        item_tags = cursor.fetchall()
        new_item['tags'] = [{'name': tag['tag_name'], 'color': tag['tag_color']} for tag in item_tags]
        
        print(f'New Item: {new_item}')

        return jsonify(
            {
                "success": True,
                "item": new_item,
                "ai_predicted": is_ai_predicted,
                "message": "Item added successfully",
            }
        )

    except Exception as e:
        db.rollback()
        return jsonify(
            {"success": False, "message": f"Failed to add pantry item: {str(e)}"}
        )
    finally:
        cursor.close()


@pantry_bp.route("/pantry/transfer-from-trip", methods=["POST"])
def transfer_shopping_trip_to_pantry():
    """Transfer items from a completed shopping trip to pantry"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    data = request.get_json()
    user_ID = session["user_ID"]
    cart_id = data.get("cart_id")
    items_data = data.get("items", [])  # List of items with pantry details

    if not cart_id:
        return jsonify({"success": False, "message": "Cart ID is required"})

    print(f"DEBUG: Transfer request - cart_id: {cart_id}, items: {len(items_data)}")

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify cart belongs to user and is completed
        verify_query = """
            SELECT cart_ID FROM shopping_cart 
            WHERE cart_ID = %s AND user_ID = %s AND status = 'purchased'
        """
        cursor.execute(verify_query, (cart_id, user_ID))
        if not cursor.fetchone():
            return jsonify(
                {
                    "success": False,
                    "message": "Shopping trip not found or not completed",
                }
            )

        # Check if already transferred
        check_query = (
            "SELECT transfer_id FROM pantry_transfer_sessions WHERE cart_id = %s"
        )
        cursor.execute(check_query, (cart_id,))
        if cursor.fetchone():
            return jsonify(
                {
                    "success": False,
                    "message": "Items from this trip have already been transferred",
                }
            )

        # Create transfer session
        session_query = """
            INSERT INTO pantry_transfer_sessions (user_id, cart_id, items_transferred)
            VALUES (%s, %s, %s)
        """
        cursor.execute(session_query, (user_ID, cart_id, len(items_data)))
        transfer_id = cursor.lastrowid

        # Add items to pantry
        items_added = 0
        for item_data in items_data:
            item_id = item_data.get("item_id")

            # Get the original item details from cart_item table
            item_query = "SELECT * FROM cart_item WHERE item_ID = %s AND cart_ID = %s"
            cursor.execute(item_query, (item_id, cart_id))
            original_item = cursor.fetchone()

            if not original_item:
                print(f"DEBUG: Item {item_id} not found in cart {cart_id}")
                continue

            # Use original item name, but allow override of other properties
            item_name = original_item["item_name"]
            quantity = item_data.get("quantity", original_item.get("quantity", 1))
            unit = item_data.get("unit", original_item.get("unit", "pcs"))
            category = item_data.get("category", "Other")
            storage_type = item_data.get("storage_type", "pantry")
            expiration_date = item_data.get("expiration_date")
            use_ai_prediction = item_data.get(
                "ai_predict_expiry", False
            )  # Fixed parameter name
            notes = item_data.get("notes", "")

            print(
                f"DEBUG: Processing item - name: {item_name}, quantity: {quantity}, ai_predict: {use_ai_prediction}"
            )

            if not item_name:
                continue

            # Handle AI prediction if requested
            is_ai_predicted = False
            predicted_category = None
            if use_ai_prediction and not expiration_date:
                prediction_result = predict_expiration_and_category(item_name, storage_type)
                if prediction_result:
                    expiration_date = prediction_result.get('expiration_date')
                    predicted_category = prediction_result.get('category')
                    if expiration_date:
                        is_ai_predicted = True
                    if predicted_category and category == 'Other':
                        category = predicted_category

            # Insert pantry item
            insert_query = """
                INSERT INTO pantry_items (
                    user_id, item_name, quantity, unit, category, storage_type,
                    expiration_date, source_type, source_cart_id, is_ai_predicted_expiry, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                insert_query,
                (
                    user_ID,
                    item_name,
                    quantity,
                    unit,
                    category,
                    storage_type,
                    expiration_date,
                    "shopping_trip",
                    cart_id,
                    is_ai_predicted,
                    notes,
                ),
            )
            items_added += 1
            print(f"DEBUG: Added item {item_name} to pantry")

        db.commit()

        return jsonify(
            {
                "success": True,
                "transfer_id": transfer_id,
                "items_added": items_added,
                "message": f"Successfully added {items_added} items to pantry",
            }
        )

    except Exception as e:
        db.rollback()
        print(f"DEBUG: Transfer error: {str(e)}")
        return jsonify(
            {"success": False, "message": f"Failed to transfer items: {str(e)}"}
        )
    finally:
        cursor.close()


def predict_expiration_date(item_name, storage_type):
    """Predict expiration date using AI or cached predictions (backward compatibility)"""
    result = predict_expiration_and_category(item_name, storage_type)
    return result.get('expiration_date') if result else None


def predict_expiration_and_category(item_name, storage_type):
    """Predict expiration date and category using AI or cached predictions"""
    db = get_db()
    cursor = db.cursor()

    try:
        # First check if we have a cached prediction
        cache_query = """
            SELECT predicted_days FROM expiry_predictions 
            WHERE item_name = %s AND storage_type = %s
        """
        cursor.execute(cache_query, (item_name.lower(), storage_type))
        cached = cursor.fetchone()

        if cached:
            # Update usage count
            cursor.execute(
                """
                UPDATE expiry_predictions 
                SET used_count = used_count + 1 
                WHERE item_name = %s AND storage_type = %s
            """,
                (item_name.lower(), storage_type),
            )

            # Calculate expiration date
            from datetime import datetime, timedelta

            expiry_date = datetime.now().date() + timedelta(
                days=cached["predicted_days"]
            )
            cursor.close()
            
            # For cached predictions, predict category using simple heuristics
            predicted_category = get_simple_category_prediction(item_name)
            
            return {
                'expiration_date': expiry_date.strftime("%Y-%m-%d"),
                'category': predicted_category
            }

        # Use Gemini AI to predict expiration and category
        prediction_result = get_gemini_prediction_with_category(item_name, storage_type)

        if prediction_result and prediction_result.get('days'):
            predicted_days = prediction_result['days']
            predicted_category = prediction_result.get('category', 'Other')
            
            # Cache the prediction
            cursor.execute(
                """
                INSERT INTO expiry_predictions (item_name, storage_type, predicted_days)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                used_count = used_count + 1, 
                predicted_days = VALUES(predicted_days)
            """,
                (item_name.lower(), storage_type, predicted_days),
            )

            # Calculate expiration date
            from datetime import datetime, timedelta

            expiry_date = datetime.now().date() + timedelta(days=predicted_days)
            cursor.close()
            
            return {
                'expiration_date': expiry_date.strftime("%Y-%m-%d"),
                'category': predicted_category
            }

        cursor.close()
        return None

    except Exception as e:
        print(f"Error predicting expiration and category: {str(e)}")
        cursor.close()
        return None


def get_gemini_prediction_with_category(item_name, storage_type):
    """Use Gemini AI to predict expiration date and category based on item and storage type, with OpenAI fallback"""
    import os
    import google.generativeai as genai
    from src.openai_utils import openai_expiry_prediction

    try:
        # Configure Gemini with API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(
                "WARNING: GEMINI_API_KEY not found in environment, trying OpenAI fallback"
            )
            # Try OpenAI fallback
            openai_result = openai_expiry_prediction(item_name, storage_type)
            if openai_result:
                print(f"DEBUG: OpenAI fallback successful for {item_name}")
                return openai_result
            return get_simple_prediction_with_category(item_name, storage_type)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        # Create a specific prompt for food expiration and category prediction
        prompt = f"""You are a food safety expert. I need to know how many days a food item will last and its category.

Item: {item_name}
Storage: {storage_type} (pantry, fridge, or freezer)

Based on typical food safety guidelines:
1. How many days will this item last from today if stored in the {storage_type}?
2. What category does this item belong to?

Available categories: Produce, Meat, Dairy, Grains, Canned Goods, Frozen Foods, Beverages, Snacks, Condiments, Spices, Bread, Other, Fresh Herbs, Oils & Vinegars, Baking Supplies

Important instructions:
- Respond with ONLY a JSON object in this exact format: {{"days": NUMBER, "category": "CATEGORY_NAME"}}
- Use conservative estimates for food safety
- For pantry items, assume they are in a cool, dry place
- For fridge items, assume proper refrigeration (35-40°F)
- For freezer items, assume proper freezing (0°F or below)

Examples:
- Fresh milk in fridge: {{"days": 7, "category": "Dairy"}}
- Bread in pantry: {{"days": 5, "category": "Bread"}}
- Frozen chicken in freezer: {{"days": 365, "category": "Meat"}}
- Bananas in pantry: {{"days": 5, "category": "Produce"}}

Respond only with the JSON object:"""

        # Generate prediction
        response = model.generate_content(prompt)
        prediction_text = response.text.strip()

        # Log the actual response for debugging
        print(
            f"DEBUG: Gemini raw response for {item_name} in {storage_type}: '{prediction_text}'"
        )

        # Parse JSON response
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]*\}', prediction_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                days = result.get('days', 0)
                category = result.get('category', 'Other')
                
                # Validate the prediction (sanity check)
                if 1 <= days <= 3650:  # Between 1 day and 10 years
                    return {'days': days, 'category': category}
                else:
                    print(
                        f"WARNING: Gemini prediction {days} days seems unrealistic, falling back"
                    )
                    return get_simple_prediction_with_category(item_name, storage_type)
            except json.JSONDecodeError:
                print(f"WARNING: Could not parse JSON from Gemini response: {prediction_text}")
                return get_simple_prediction_with_category(item_name, storage_type)
        else:
            print(f"WARNING: No JSON found in Gemini response: {prediction_text}")
            return get_simple_prediction_with_category(item_name, storage_type)

    except Exception as e:
        print(
            f"ERROR: Gemini prediction failed: {str(e)}, trying OpenAI fallback"
        )
        # Try OpenAI fallback
        openai_result = openai_expiry_prediction(item_name, storage_type)
        if openai_result:
            print(f"DEBUG: OpenAI fallback successful for {item_name} after Gemini failure")
            return openai_result
        print("WARNING: OpenAI fallback also failed, using simple prediction")
        return get_simple_prediction_with_category(item_name, storage_type)


def get_gemini_prediction(item_name, storage_type):
    """Use Gemini AI to predict expiration date based on item and storage type, with OpenAI fallback"""
    import os
    import google.generativeai as genai
    from src.openai_utils import openai_expiry_prediction

    try:
        # Configure Gemini with API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(
                "WARNING: GEMINI_API_KEY not found in environment, trying OpenAI fallback"
            )
            # Try OpenAI fallback
            openai_result = openai_expiry_prediction(item_name, storage_type)
            if openai_result:
                print(f"DEBUG: OpenAI fallback successful for {item_name}")
                return openai_result.get('days')
            return get_simple_prediction(item_name, storage_type)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        # Create a specific prompt for food expiration prediction
        prompt = f"""You are a food safety expert. I need to know how many days a food item will last.

Item: {item_name}
Storage: {storage_type} (pantry, fridge, or freezer)

Based on typical food safety guidelines, how many days will this item last from today if stored in the {storage_type}?

Important instructions:
- Only respond with a single number (the number of days)
- Consider typical shelf life for opened/unopened items
- Use conservative estimates for food safety
- For pantry items, assume they are in a cool, dry place
- For fridge items, assume proper refrigeration (35-40°F)
- For freezer items, assume proper freezing (0°F or below)

Examples:
- Fresh milk in fridge: 7
- Bread in pantry: 5
- Frozen chicken in freezer: 365
- Bananas in pantry: 5

Just respond with the number of days:"""

        # Generate prediction
        response = model.generate_content(prompt)
        prediction_text = response.text.strip()

        # Log the actual response for debugging
        print(
            f"DEBUG: Gemini raw response for {item_name} in {storage_type}: '{prediction_text}'"
        )

        # Extract number from response
        import re

        numbers = re.findall(r"\d+", prediction_text)
        if numbers:
            predicted_days = int(numbers[0])
            print(
                f"DEBUG: Extracted {predicted_days} days from response: '{prediction_text}'"
            )

            # Validate the prediction (sanity check)
            if 1 <= predicted_days <= 3650:  # Between 1 day and 10 years
                return predicted_days
            else:
                print(
                    f"WARNING: Gemini prediction {predicted_days} days seems unrealistic, falling back"
                )
                return get_simple_prediction(item_name, storage_type)
        else:
            print(f"WARNING: Could not parse Gemini response: {prediction_text}")
            return get_simple_prediction(item_name, storage_type)

    except Exception as e:
        print(
            f"ERROR: Gemini prediction failed: {str(e)}, trying OpenAI fallback"
        )
        # Try OpenAI fallback
        openai_result = openai_expiry_prediction(item_name, storage_type)
        if openai_result:
            print(f"DEBUG: OpenAI fallback successful for {item_name} after Gemini failure")
            return openai_result.get('days')
        print("WARNING: OpenAI fallback also failed, using simple prediction")
        return get_simple_prediction(item_name, storage_type)


def get_simple_prediction_with_category(item_name, storage_type):
    """Simple heuristic-based expiration and category prediction"""
    item_lower = item_name.lower()

    # Storage-based multipliers
    storage_multiplier = {"freezer": 30, "fridge": 1, "pantry": 1}

    # Item category predictions (base days for fridge)
    if any(word in item_lower for word in ["milk", "dairy", "yogurt", "cheese", "butter", "cream"]):
        return {"days": 14 * storage_multiplier.get(storage_type, 1), "category": "Dairy"}
    elif any(word in item_lower for word in ["meat", "chicken", "beef", "pork", "fish", "turkey", "lamb"]):
        return {"days": 3 * storage_multiplier.get(storage_type, 1), "category": "Meat"}
    elif any(word in item_lower for word in ["bread", "bagel", "muffin", "baguette", "roll"]):
        return {"days": 5 * storage_multiplier.get(storage_type, 1), "category": "Bread"}
    elif any(word in item_lower for word in ["apple", "banana", "orange", "fruit", "vegetable", "lettuce", "carrot", "tomato", "onion", "potato"]):
        return {"days": 7 * storage_multiplier.get(storage_type, 1), "category": "Produce"}
    elif any(word in item_lower for word in ["rice", "pasta", "grain", "cereal", "oats", "quinoa", "barley"]):
        return {"days": 365 * storage_multiplier.get(storage_type, 1), "category": "Grains"}
    elif any(word in item_lower for word in ["canned", "can", "jar"]):
        return {"days": 730 * storage_multiplier.get(storage_type, 1), "category": "Canned Goods"}
    elif any(word in item_lower for word in ["frozen", "ice cream"]):
        return {"days": 90 * storage_multiplier.get(storage_type, 1), "category": "Frozen Foods"}
    elif any(word in item_lower for word in ["juice", "soda", "water", "beer", "wine", "coffee", "tea"]):
        return {"days": 30 * storage_multiplier.get(storage_type, 1), "category": "Beverages"}
    elif any(word in item_lower for word in ["chips", "crackers", "cookies", "candy", "chocolate"]):
        return {"days": 60 * storage_multiplier.get(storage_type, 1), "category": "Snacks"}
    elif any(word in item_lower for word in ["ketchup", "mustard", "mayo", "sauce", "dressing", "vinegar"]):
        return {"days": 180 * storage_multiplier.get(storage_type, 1), "category": "Condiments"}
    elif any(word in item_lower for word in ["salt", "pepper", "spice", "herb", "oregano", "basil", "thyme"]):
        return {"days": 1095 * storage_multiplier.get(storage_type, 1), "category": "Spices"}
    elif any(word in item_lower for word in ["parsley", "cilantro", "mint", "dill", "chives"]):
        return {"days": 7 * storage_multiplier.get(storage_type, 1), "category": "Fresh Herbs"}
    elif any(word in item_lower for word in ["oil", "olive oil", "coconut oil", "vinegar", "balsamic"]):
        return {"days": 365 * storage_multiplier.get(storage_type, 1), "category": "Oils & Vinegars"}
    elif any(word in item_lower for word in ["flour", "sugar", "baking powder", "baking soda", "vanilla", "cocoa"]):
        return {"days": 730 * storage_multiplier.get(storage_type, 1), "category": "Baking Supplies"}
    else:
        # Default prediction
        base_days = (
            30 if storage_type == "pantry" else 14 if storage_type == "fridge" else 90
        )
        return {"days": base_days, "category": "Other"}


def get_simple_category_prediction(item_name):
    """Simple heuristic-based category prediction"""
    item_lower = item_name.lower()
    
    if any(word in item_lower for word in ["milk", "dairy", "yogurt", "cheese", "butter", "cream"]):
        return "Dairy"
    elif any(word in item_lower for word in ["meat", "chicken", "beef", "pork", "fish", "turkey", "lamb"]):
        return "Meat"
    elif any(word in item_lower for word in ["bread", "bagel", "muffin", "baguette", "roll"]):
        return "Bread"
    elif any(word in item_lower for word in ["apple", "banana", "orange", "fruit", "vegetable", "lettuce", "carrot", "tomato", "onion", "potato"]):
        return "Produce"
    elif any(word in item_lower for word in ["rice", "pasta", "grain", "cereal", "oats", "quinoa", "barley"]):
        return "Grains"
    elif any(word in item_lower for word in ["canned", "can", "jar"]):
        return "Canned Goods"
    elif any(word in item_lower for word in ["frozen", "ice cream"]):
        return "Frozen Foods"
    elif any(word in item_lower for word in ["juice", "soda", "water", "beer", "wine", "coffee", "tea"]):
        return "Beverages"
    elif any(word in item_lower for word in ["chips", "crackers", "cookies", "candy", "chocolate"]):
        return "Snacks"
    elif any(word in item_lower for word in ["ketchup", "mustard", "mayo", "sauce", "dressing", "vinegar"]):
        return "Condiments"
    elif any(word in item_lower for word in ["salt", "pepper", "spice", "herb", "oregano", "basil", "thyme"]):
        return "Spices"
    elif any(word in item_lower for word in ["parsley", "cilantro", "mint", "dill", "chives"]):
        return "Fresh Herbs"
    elif any(word in item_lower for word in ["oil", "olive oil", "coconut oil", "vinegar", "balsamic"]):
        return "Oils & Vinegars"
    elif any(word in item_lower for word in ["flour", "sugar", "baking powder", "baking soda", "vanilla", "cocoa"]):
        return "Baking Supplies"
    else:
        return "Other"


def get_simple_prediction(item_name, storage_type):
    """Simple heuristic-based expiration prediction (backward compatibility)"""
    result = get_simple_prediction_with_category(item_name, storage_type)
    return result.get("days") if result else None


@pantry_bp.route("/pantry/items/<int:item_id>", methods=["GET"])
def get_pantry_item(item_id):
    """Get a single pantry item by ID"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]

    try:
        db = get_db()
        cursor = db.cursor()

        # Get the specific item
        query = "SELECT * FROM pantry_items WHERE pantry_item_id = %s AND user_id = %s"
        cursor.execute(query, (item_id, user_id))
        item = cursor.fetchone()

        if not item:
            return jsonify(
                {"success": False, "message": "Item not found or access denied"}
            )

        # Get tags for the item
        tags_query = """
            SELECT pt.tag_id, pt.tag_name, pt.tag_color
            FROM pantry_item_tags pit
            JOIN pantry_tags pt ON pit.tag_id = pt.tag_id
            WHERE pit.pantry_item_id = %s
        """
        cursor.execute(tags_query, (item_id,))
        item_tags = cursor.fetchall()
        item['tags'] = [{'id': tag['tag_id'], 'name': tag['tag_name'], 'color': tag['tag_color']} for tag in item_tags]

        cursor.close()
        return jsonify({"success": True, "item": item})

    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"})
    finally:
        if cursor:
            cursor.close()


@pantry_bp.route("/pantry/items/<int:item_id>", methods=["PUT"])
def update_pantry_item(item_id):
    """Update a pantry item"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()

    # Required fields
    item_name = data.get("item_name", "").strip()
    quantity = data.get("quantity", 1)
    unit = data.get("unit", "pcs")

    # Optional fields
    category = data.get("category", "Other")
    storage_type = data.get("storage_type", "pantry")
    expiration_date = data.get("expiration_date")
    use_ai_prediction = data.get("ai_predict_expiry", False)
    notes = data.get("notes", "")
    tag_ids = data.get("tag_ids", [])  # List of tag IDs to assign

    if not item_name:
        return jsonify({"success": False, "message": "Item name is required"})

    try:
        quantity = float(quantity)
        if quantity <= 0:
            return jsonify({"success": False, "message": "Quantity must be positive"})
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid quantity"})

    try:
        db = get_db()
        cursor = db.cursor()

        # Verify the item belongs to the user
        verify_query = "SELECT pantry_item_id FROM pantry_items WHERE pantry_item_id = %s AND user_id = %s"
        cursor.execute(verify_query, (item_id, user_id))
        if not cursor.fetchone():
            return jsonify(
                {"success": False, "message": "Item not found or access denied"}
            )

        # Handle AI prediction if requested
        is_ai_predicted = False
        predicted_category = None
        if use_ai_prediction and not expiration_date:
            prediction_result = predict_expiration_and_category(item_name, storage_type)
            if prediction_result:
                expiration_date = prediction_result.get('expiration_date')
                predicted_category = prediction_result.get('category')
                if expiration_date:
                    is_ai_predicted = True
                if predicted_category and category == 'Other':
                    category = predicted_category

        # Update the item
        update_query = """
            UPDATE pantry_items SET 
                item_name = %s, quantity = %s, unit = %s, category = %s, 
                storage_type = %s, expiration_date = %s, is_ai_predicted_expiry = %s, notes = %s,
                date_updated = CURRENT_TIMESTAMP
            WHERE pantry_item_id = %s AND user_id = %s
        """
        cursor.execute(
            update_query,
            (
                item_name,
                quantity,
                unit,
                category,
                storage_type,
                expiration_date,
                is_ai_predicted,
                notes,
                item_id,
                user_id,
            ),
        )

        # Handle tag updates
        # First, get current tags to update usage counts
        current_tags_query = """
            SELECT tag_id FROM pantry_item_tags 
            WHERE pantry_item_id = %s
        """
        cursor.execute(current_tags_query, (item_id,))
        current_tag_ids = [row['tag_id'] for row in cursor.fetchall()]
        
        # Remove all current tags
        cursor.execute("DELETE FROM pantry_item_tags WHERE pantry_item_id = %s", (item_id,))
        
        # Update usage counts for removed tags
        for old_tag_id in current_tag_ids:
            cursor.execute("UPDATE pantry_tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE tag_id = %s", (old_tag_id,))
        
        # Add new tags if provided
        if tag_ids:
            # Verify tags belong to user
            placeholders = ','.join(['%s'] * len(tag_ids))
            tag_verify_query = f"""
                SELECT tag_id FROM pantry_tags 
                WHERE tag_id IN ({placeholders}) AND user_id = %s
            """
            cursor.execute(tag_verify_query, tag_ids + [user_id])
            valid_tags = [row['tag_id'] for row in cursor.fetchall()]
            
            # Add valid tags to item
            for tag_id in valid_tags:
                try:
                    cursor.execute(
                        "INSERT INTO pantry_item_tags (pantry_item_id, tag_id) VALUES (%s, %s)",
                        (item_id, tag_id)
                    )
                    cursor.execute(
                        "UPDATE pantry_tags SET usage_count = usage_count + 1 WHERE tag_id = %s",
                        (tag_id,)
                    )
                except:
                    continue  # Skip duplicates (shouldn't happen since we deleted all first)

        db.commit()

        # Return the updated item with tags
        cursor.execute("SELECT * FROM pantry_items WHERE pantry_item_id = %s", (item_id,))
        updated_item = cursor.fetchone()
        
        # Get tags for the updated item
        tags_query = """
            SELECT pt.tag_name, pt.tag_color
            FROM pantry_item_tags pit
            JOIN pantry_tags pt ON pit.tag_id = pt.tag_id
            WHERE pit.pantry_item_id = %s
        """
        cursor.execute(tags_query, (item_id,))
        item_tags = cursor.fetchall()
        updated_item['tags'] = [{'name': tag['tag_name'], 'color': tag['tag_color']} for tag in item_tags]

        return jsonify(
            {
                "success": True,
                "item": updated_item,
                "ai_predicted": is_ai_predicted,
                "message": "Item updated successfully",
            }
        )

    except Exception as e:
        db.rollback()
        return jsonify(
            {"success": False, "message": f"Failed to update pantry item: {str(e)}"}
        )
    finally:
        cursor.close()


@pantry_bp.route("/pantry/items/<int:item_id>", methods=["DELETE"])
def delete_pantry_item(item_id):
    """Delete a pantry item"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]

    try:
        db = get_db()
        cursor = db.cursor()

        # Verify the item belongs to the user before deleting
        query = "SELECT pantry_item_id FROM pantry_items WHERE pantry_item_id = %s AND user_id = %s"
        cursor.execute(query, (item_id, user_id))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            return jsonify(
                {"success": False, "message": "Item not found or access denied"}
            )

        # Get tags associated with this item to update usage counts
        tags_query = """
            SELECT tag_id FROM pantry_item_tags 
            WHERE pantry_item_id = %s
        """
        cursor.execute(tags_query, (item_id,))
        tag_ids = [row['tag_id'] for row in cursor.fetchall()]
        
        # Update usage counts for all tags before deleting
        for tag_id in tag_ids:
            cursor.execute("UPDATE pantry_tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE tag_id = %s", (tag_id,))

        # Delete the item (this will also delete associated tags due to CASCADE)
        delete_query = (
            "DELETE FROM pantry_items WHERE pantry_item_id = %s AND user_id = %s"
        )
        cursor.execute(delete_query, (item_id, user_id))
        db.commit()
        cursor.close()

        return jsonify({"success": True, "message": "Item deleted successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"})


@pantry_bp.route("/pantry/test-gemini", methods=["GET"])
def test_gemini():
    """Test Gemini AI integration"""
    item_name = request.args.get("item_name", "banana")
    storage_type = request.args.get("storage_type", "pantry")

    try:
        predicted_days = get_gemini_prediction(item_name, storage_type)
        return jsonify(
            {
                "success": True,
                "item_name": item_name,
                "storage_type": storage_type,
                "predicted_days": predicted_days,
                "message": f"Gemini predicted {predicted_days} days for {item_name} in {storage_type}",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Gemini test failed: {str(e)}"})


@pantry_bp.route("/pantry/test-gemini-category", methods=["GET"])
def test_gemini_category():
    """Test Gemini AI integration with category prediction"""
    item_name = request.args.get("item_name", "banana")
    storage_type = request.args.get("storage_type", "pantry")

    try:
        prediction_result = get_gemini_prediction_with_category(item_name, storage_type)
        return jsonify(
            {
                "success": True,
                "item_name": item_name,
                "storage_type": storage_type,
                "prediction_result": prediction_result,
                "message": f"Gemini predicted {prediction_result.get('days', 'unknown')} days and category '{prediction_result.get('category', 'unknown')}' for {item_name} in {storage_type}",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Gemini category test failed: {str(e)}"})


# Tag management endpoints

@pantry_bp.route("/pantry/tags", methods=["GET"])
def get_user_tags():
    """Get all tags for the current user"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        query = """
            SELECT tag_id, tag_name, tag_color, usage_count, created_at
            FROM pantry_tags 
            WHERE user_id = %s 
            ORDER BY usage_count DESC, tag_name ASC
        """
        cursor.execute(query, (user_ID,))
        tags = cursor.fetchall()

        return jsonify({"success": True, "tags": tags})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get tags: {str(e)}"})
    finally:
        cursor.close()


@pantry_bp.route("/pantry/tags", methods=["POST"])
def create_tag():
    """Create a new tag for the current user"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_ID = session["user_ID"]
    data = request.get_json()
    
    tag_name = data.get("tag_name", "").strip()
    tag_color = data.get("tag_color", "#3B82F6")
    
    if not tag_name:
        return jsonify({"success": False, "message": "Tag name is required"})
    
    if len(tag_name) > 50:
        return jsonify({"success": False, "message": "Tag name must be 50 characters or less"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Check if tag already exists for this user
        check_query = "SELECT tag_id FROM pantry_tags WHERE user_id = %s AND tag_name = %s"
        cursor.execute(check_query, (user_ID, tag_name))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Tag already exists"})

        # Create new tag
        insert_query = """
            INSERT INTO pantry_tags (user_id, tag_name, tag_color)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (user_ID, tag_name, tag_color))
        tag_id = cursor.lastrowid
        db.commit()

        # Return the created tag
        cursor.execute("SELECT * FROM pantry_tags WHERE tag_id = %s", (tag_id,))
        new_tag = cursor.fetchone()

        return jsonify({"success": True, "tag": new_tag, "message": "Tag created successfully"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to create tag: {str(e)}"})
    finally:
        cursor.close()


@pantry_bp.route("/pantry/items/<int:item_id>/tags", methods=["POST"])
def add_tag_to_item(item_id):
    """Add a tag to a pantry item"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_ID = session["user_ID"]
    data = request.get_json()
    tag_ids = data.get("tag_ids", [])
    
    if not tag_ids:
        return jsonify({"success": False, "message": "At least one tag_id is required"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify item belongs to user
        verify_query = "SELECT pantry_item_id FROM pantry_items WHERE pantry_item_id = %s AND user_id = %s"
        cursor.execute(verify_query, (item_id, user_ID))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Item not found or access denied"})

        # Verify all tags belong to user
        tag_verify_query = "SELECT tag_id FROM pantry_tags WHERE tag_id IN (%s) AND user_id = %s" % ','.join(['%s'] * len(tag_ids))
        cursor.execute(tag_verify_query, tag_ids + [user_ID])
        valid_tags = [row['tag_id'] for row in cursor.fetchall()]
        
        if len(valid_tags) != len(tag_ids):
            return jsonify({"success": False, "message": "One or more tags not found or access denied"})

        # Add tags to item (ignore duplicates)
        added_count = 0
        for tag_id in tag_ids:
            try:
                insert_query = "INSERT INTO pantry_item_tags (pantry_item_id, tag_id) VALUES (%s, %s)"
                cursor.execute(insert_query, (item_id, tag_id))
                added_count += 1
                
                # Update tag usage count
                cursor.execute("UPDATE pantry_tags SET usage_count = usage_count + 1 WHERE tag_id = %s", (tag_id,))
            except:
                # Tag already exists for this item, skip
                continue

        db.commit()
        return jsonify({"success": True, "added_count": added_count, "message": f"Added {added_count} tags to item"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to add tags: {str(e)}"})
    finally:
        cursor.close()


@pantry_bp.route("/pantry/items/<int:item_id>/tags/<int:tag_id>", methods=["DELETE"])
def remove_tag_from_item(item_id, tag_id):
    """Remove a tag from a pantry item"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_ID = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify item belongs to user and tag exists
        verify_query = """
            SELECT pit.item_tag_id 
            FROM pantry_item_tags pit
            JOIN pantry_items p ON pit.pantry_item_id = p.pantry_item_id
            JOIN pantry_tags pt ON pit.tag_id = pt.tag_id
            WHERE pit.pantry_item_id = %s AND pit.tag_id = %s AND p.user_id = %s AND pt.user_id = %s
        """
        cursor.execute(verify_query, (item_id, tag_id, user_ID, user_ID))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Tag assignment not found or access denied"})

        # Remove tag from item
        delete_query = "DELETE FROM pantry_item_tags WHERE pantry_item_id = %s AND tag_id = %s"
        cursor.execute(delete_query, (item_id, tag_id))
        
        # Update tag usage count
        cursor.execute("UPDATE pantry_tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE tag_id = %s", (tag_id,))
        
        db.commit()
        return jsonify({"success": True, "message": "Tag removed from item"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to remove tag: {str(e)}"})
    finally:
        cursor.close()