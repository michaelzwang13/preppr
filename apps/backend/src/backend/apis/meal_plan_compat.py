"""
Compatibility layer for existing meal plan endpoints
This module provides backward compatibility for the old meal plan structure
while using the new individual meals database structure underneath.
"""

from flask import Blueprint, request, jsonify, session
from src.database import get_db
from datetime import date

meal_plan_compat_bp = Blueprint("meal_plan_compat", __name__, url_prefix="/api")


@meal_plan_compat_bp.route("/meal-plans", methods=["GET"])
def get_meal_plans():
    """Get all meal plan sessions for the current user (backward compatibility)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get meal plan sessions with fuzzy matching summary and meal completion data
        query = """
            SELECT mps.session_id as plan_id, mps.session_name as plan_name, 
                   mps.start_date, mps.end_date, mps.total_days,
                   mps.dietary_preference, mps.budget_limit, mps.max_cooking_time,
                   mps.generated_at, mps.status,
                   sgs.generation_id, sgs.auto_matched_count, sgs.confirm_needed_count, 
                   sgs.missing_count, sgs.total_ingredients,
                   COUNT(m.meal_id) as total_meals,
                   COUNT(CASE WHEN m.is_completed = TRUE THEN 1 END) as completed_meals
            FROM meal_plan_sessions mps
            LEFT JOIN shopping_generation_sessions sgs ON mps.session_id = sgs.meal_plan_session_id
                AND sgs.generation_id = (
                    SELECT MAX(generation_id) FROM shopping_generation_sessions 
                    WHERE meal_plan_session_id = mps.session_id
                )
            LEFT JOIN meals m ON mps.session_id = m.session_id
            WHERE mps.user_id = %s
            GROUP BY mps.session_id, sgs.generation_id
            ORDER BY ABS(DATEDIFF(mps.start_date, CURDATE())), mps.start_date ASC
        """
        cursor.execute(query, (user_id,))
        plans = cursor.fetchall()

        # Format dates as strings and add fuzzy matching summary
        formatted_plans = []
        for plan in plans:
            plan_copy = dict(plan)
            plan_copy['start_date'] = plan['start_date'].strftime("%Y-%m-%d") if hasattr(plan['start_date'], 'strftime') else plan['start_date']
            plan_copy['end_date'] = plan['end_date'].strftime("%Y-%m-%d") if hasattr(plan['end_date'], 'strftime') else plan['end_date']
            
            # Calculate dynamic status based on completion and dates
            today = date.today()
            start_date = plan['start_date'] if hasattr(plan['start_date'], 'year') else plan['start_date']
            end_date = plan['end_date'] if hasattr(plan['end_date'], 'year') else plan['end_date']
            completed_meals = plan['completed_meals'] or 0
            
            # Determine status based on completion and dates
            if start_date <= today <= end_date:
                # Plan is currently active (includes today's date)
                plan_copy['status'] = 'active'
            elif end_date < today:
                # Plan is in the past
                if completed_meals > 0:
                    # At least one meal was completed
                    plan_copy['status'] = 'completed'
                else:
                    # No meals were completed
                    plan_copy['status'] = 'expired'
            else:
                # Plan is in the future
                plan_copy['status'] = 'active'
            
            # Add fuzzy matching summary if available
            if plan.get('generation_id'):
                plan_copy['fuzzy_matching_summary'] = {
                    "auto_matched": plan['auto_matched_count'] or 0,
                    "confirm_needed": plan['confirm_needed_count'] or 0,
                    "missing": plan['missing_count'] or 0,
                    "total_ingredients": plan['total_ingredients'] or 0,
                    "pantry_utilization_rate": (plan['auto_matched_count'] / plan['total_ingredients'] * 100) if (plan['total_ingredients'] and plan['total_ingredients'] > 0) else 0
                }
            else:
                plan_copy['fuzzy_matching_summary'] = None
                
            # Remove the generation fields from the main plan object
            fields_to_remove = ['generation_id', 'auto_matched_count', 'confirm_needed_count', 'missing_count', 'total_ingredients', 'total_meals', 'completed_meals']
            for field in fields_to_remove:
                plan_copy.pop(field, None)
                
            formatted_plans.append(plan_copy)

        return jsonify({"success": True, "plans": formatted_plans})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get meal plans: {str(e)}"})
    finally:
        cursor.close()


@meal_plan_compat_bp.route("/meal-plans/<int:plan_id>", methods=["GET"])
def get_meal_plan_details(plan_id):
    """Get detailed meal plan with recipes and batch prep steps (backward compatibility)"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify session belongs to user (plan_id is actually session_id in new structure)
        verify_query = "SELECT * FROM meal_plan_sessions WHERE session_id = %s AND user_id = %s"
        cursor.execute(verify_query, (plan_id, user_id))
        session_info = cursor.fetchone()

        if not session_info:
            return jsonify({"success": False, "message": "Meal plan not found"})

        # Get meals for this session and convert to old recipe format
        meals_query = """
            SELECT 
                m.meal_id,
                m.meal_date,
                m.meal_type,
                m.notes,
                rt.recipe_name,
                rt.description,
                rt.prep_time,
                rt.cook_time,
                rt.servings,
                rt.estimated_cost,
                rt.difficulty,
                rt.calories_per_serving,
                rt.instructions,
                m.custom_recipe_name,
                m.custom_instructions
            FROM meals m
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE m.session_id = %s
            ORDER BY m.meal_date, FIELD(m.meal_type, 'breakfast', 'lunch', 'dinner', 'snack')
        """
        cursor.execute(meals_query, (plan_id,))
        meal_data = cursor.fetchall()

        # Get ingredients for each meal
        recipes_with_ingredients = []
        for meal in meal_data:
            # Calculate day number relative to session start
            start_date = session_info['start_date']
            meal_date = meal['meal_date']
            day_number = (meal_date - start_date).days + 1

            # Get ingredients (template + custom)
            ingredients = []
            
            if meal['recipe_name']:  # Has template
                template_query = """
                    SELECT rt.template_id FROM recipe_templates rt 
                    WHERE rt.recipe_name = %s
                """
                cursor.execute(template_query, (meal['recipe_name'],))
                template = cursor.fetchone()
                
                if template:
                    ingredients_query = """
                        SELECT ingredient_name, quantity, unit, notes as ingredient_notes
                        FROM template_ingredients 
                        WHERE template_id = %s
                    """
                    cursor.execute(ingredients_query, (template['template_id'],))
                    ingredients.extend(cursor.fetchall())

            # Format as old recipe structure
            recipe_entry = {
                "recipe_id": meal['meal_id'],  # Use meal_id as recipe_id for compatibility
                "meal_type": meal['meal_type'],
                "day_number": day_number,
                "recipe_name": meal['recipe_name'] or meal['custom_recipe_name'] or f"Custom {meal['meal_type']}",
                "description": meal['description'] or "",
                "prep_time": meal['prep_time'] or 0,
                "cook_time": meal['cook_time'] or 0,
                "servings": meal['servings'] or 1,
                "estimated_cost": meal['estimated_cost'] or 0,
                "difficulty": meal['difficulty'] or "medium",
                "calories_per_serving": meal['calories_per_serving'] or 0,
                "instructions": meal['instructions'] or meal['custom_instructions'] or "",
                "notes": meal['notes'] or "",
                "ingredient_name": None,
                "quantity": None,
                "unit": None,
                "ingredient_notes": None
            }

            # Add one entry per ingredient (for compatibility with old structure)
            if ingredients:
                for ingredient in ingredients:
                    recipe_copy = recipe_entry.copy()
                    recipe_copy.update({
                        "ingredient_name": ingredient['ingredient_name'],
                        "quantity": ingredient['quantity'],
                        "unit": ingredient['unit'],
                        "ingredient_notes": ingredient['ingredient_notes']
                    })
                    recipes_with_ingredients.append(recipe_copy)
            else:
                recipes_with_ingredients.append(recipe_entry)

        # Get batch prep steps
        steps_query = """
            SELECT * FROM session_batch_prep 
            WHERE session_id = %s
            ORDER BY prep_session_name, step_order
        """
        cursor.execute(steps_query, (plan_id,))
        prep_steps = cursor.fetchall()

        # Get shopping list with fuzzy matching data
        shopping_query = """
            SELECT * FROM session_shopping_lists 
            WHERE session_id = %s
            ORDER BY category, ingredient_name
        """
        cursor.execute(shopping_query, (plan_id,))
        shopping_items = cursor.fetchall()
        
        # Get fuzzy matching results if they exist
        fuzzy_matching_data = {}
        generation_summary = None
        
        try:
            # Get the latest generation session for this meal plan
            generation_query = """
                SELECT generation_id, auto_matched_count, confirm_needed_count, 
                       missing_count, total_ingredients, generated_at
                FROM shopping_generation_sessions 
                WHERE meal_plan_session_id = %s 
                ORDER BY generated_at DESC 
                LIMIT 1
            """
            cursor.execute(generation_query, (plan_id,))
            generation_session = cursor.fetchone()
            
            if generation_session:
                generation_summary = {
                    "generation_id": generation_session["generation_id"],
                    "auto_matched": generation_session["auto_matched_count"],
                    "confirm_needed": generation_session["confirm_needed_count"],
                    "missing": generation_session["missing_count"],
                    "total_ingredients": generation_session["total_ingredients"],
                    "generated_at": generation_session["generated_at"].isoformat() if generation_session["generated_at"] else None,
                    "pantry_utilization_rate": (generation_session["auto_matched_count"] / generation_session["total_ingredients"] * 100) if generation_session["total_ingredients"] > 0 else 0
                }
                
                # Get detailed matching results
                matches_query = """
                    SELECT gim.*, pi.item_name as pantry_item_name, pi.unit, pi.storage_type, pi.expiration_date
                    FROM generation_ingredient_matches gim
                    LEFT JOIN pantry_items pi ON gim.pantry_item_id = pi.pantry_item_id
                    WHERE gim.generation_id = %s
                    ORDER BY gim.ingredient_name
                """
                cursor.execute(matches_query, (generation_session["generation_id"],))
                matching_results = cursor.fetchall()
                
                # Organize matching data by ingredient name
                for match in matching_results:
                    fuzzy_matching_data[match["ingredient_name"]] = {
                        "match_type": match["match_type"],
                        "confidence": float(match["match_confidence"]) if match["match_confidence"] else None,
                        "pantry_item": {
                            "id": match["pantry_item_id"],
                            "name": match.get("pantry_item_name"),
                            "available_quantity": float(match["pantry_available_quantity"]) if match["pantry_available_quantity"] else None,
                            "available_unit": match.get("unit"),
                            "storage_type": match.get("storage_type"),
                            "expiration_date": match.get("expiration_date").strftime("%Y-%m-%d") if match.get("expiration_date") else None
                        } if match["pantry_item_id"] else None,
                        "needs_to_buy": float(match["needs_to_buy_quantity"]),
                        "is_user_confirmed": bool(match["is_user_confirmed"])
                    }
                    
        except Exception as e:
            print(f"DEBUG: Failed to get fuzzy matching data: {str(e)}")
            # Continue without fuzzy matching data

        # Structure the response in old format (use raw dates from database)
        structured_plan = {
            "plan_info": {
                "plan_id": session_info['session_id'],
                "plan_name": session_info['session_name'],
                "start_date": session_info['start_date'].strftime("%Y-%m-%d") if hasattr(session_info['start_date'], 'strftime') else session_info['start_date'],
                "end_date": session_info['end_date'].strftime("%Y-%m-%d") if hasattr(session_info['end_date'], 'strftime') else session_info['end_date'],
                "total_days": session_info['total_days'],
                "dietary_preference": session_info['dietary_preference'],
                "budget_limit": session_info['budget_limit'],
                "max_cooking_time": session_info['max_cooking_time'],
                "generated_at": session_info['generated_at'],
                "status": session_info['status'],
                "ai_model_used": session_info['ai_model_used'],
                "generation_prompt": session_info['generation_prompt']
            },
            "recipes": organize_recipes_by_day(recipes_with_ingredients),
            "batch_prep": prep_steps,
            "shopping_list": shopping_items,
            "fuzzy_matching": {
                "summary": generation_summary,
                "ingredient_matches": fuzzy_matching_data
            } if generation_summary else None
        }

        return jsonify({"success": True, "meal_plan": structured_plan})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get meal plan: {str(e)}"})
    finally:
        cursor.close()


@meal_plan_compat_bp.route("/meal-plans/<int:plan_id>", methods=["DELETE"])
def delete_meal_plan(plan_id):
    """Delete a meal plan and all associated data"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First verify the meal plan belongs to the current user
        cursor.execute("""
            SELECT session_id FROM meal_plan_sessions 
            WHERE session_id = %s AND user_id = %s
        """, (plan_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Meal plan not found or access denied"})
        
        # Delete in order to respect foreign key constraints
        # 1. Delete shopping generation sessions (and their child records via CASCADE)
        cursor.execute("""
            DELETE FROM shopping_generation_sessions WHERE meal_plan_session_id = %s
        """, (plan_id,))
        
        # 2. Delete custom ingredients for meals in this session
        cursor.execute("""
            DELETE rt FROM recipe_templates rt
            INNER JOIN meals m ON rt.template_id = m.recipe_template_id
            WHERE m.session_id = %s
        """, (plan_id,))
        
        # 3. Delete meals in this session
        cursor.execute("""
            DELETE FROM meals WHERE session_id = %s
        """, (plan_id,))
        
        # 4. Delete meal plan session
        cursor.execute("""
            DELETE FROM meal_plan_sessions WHERE session_id = %s
        """, (plan_id,))
        
        db.commit()
        
        return jsonify({
            "success": True, 
            "message": "Meal plan deleted successfully"
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False, 
            "message": f"Failed to delete meal plan: {str(e)}"
        })
    finally:
        cursor.close()


@meal_plan_compat_bp.route("/meal-plans/<int:plan_id>/refresh-matches", methods=["POST"])
def refresh_pantry_matches(plan_id):
    """Refresh fuzzy matching data for a specific meal plan"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First verify the meal plan belongs to the current user
        cursor.execute("""
            SELECT session_id FROM meal_plan_sessions 
            WHERE session_id = %s AND user_id = %s
        """, (plan_id, user_id))
        
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Meal plan not found or access denied"})
        
        # Get the latest generation session for this meal plan
        cursor.execute("""
            SELECT generation_id FROM shopping_generation_sessions 
            WHERE meal_plan_session_id = %s 
            ORDER BY generated_at DESC LIMIT 1
        """, (plan_id,))
        
        generation_result = cursor.fetchone()
        if not generation_result:
            return jsonify({"success": False, "message": "No fuzzy matching data found for this meal plan"})
        
        generation_id = generation_result["generation_id"]
        
        # Re-run fuzzy matching for all ingredients in this generation session
        # This is a simplified version - in a full implementation, you'd call the fuzzy matching service
        cursor.execute("""
            SELECT ingredient_name, required_quantity, required_unit 
            FROM generation_ingredient_matches 
            WHERE generation_id = %s
        """, (generation_id,))
        
        ingredients_to_refresh = cursor.fetchall()
        
        refreshed_count = 0
        for ingredient in ingredients_to_refresh:
            # Find current pantry items that might match this ingredient
            cursor.execute("""
                SELECT pantry_item_id, item_name, quantity, unit, storage_type, expiration_date
                FROM pantry_items 
                WHERE user_id = %s 
                    AND is_consumed = FALSE
                    AND (item_name LIKE %s OR item_name LIKE %s)
                ORDER BY 
                    CASE 
                        WHEN LOWER(item_name) = LOWER(%s) THEN 1
                        WHEN LOWER(item_name) LIKE LOWER(%s) THEN 2
                        ELSE 3
                    END,
                    expiration_date ASC
                LIMIT 1
            """, (
                user_id,
                f"%{ingredient['ingredient_name']}%",
                f"%{ingredient['ingredient_name'].split()[0]}%",
                ingredient['ingredient_name'],
                f"{ingredient['ingredient_name']}%"
            ))
            
            pantry_match = cursor.fetchone()
            
            if pantry_match:
                # Update the match with the found pantry item
                available_qty = float(pantry_match['quantity'])
                required_qty = float(ingredient['required_quantity'])
                needs_to_buy = max(0, required_qty - available_qty)
                
                cursor.execute("""
                    UPDATE generation_ingredient_matches 
                    SET pantry_item_id = %s,
                        pantry_available_quantity = %s,
                        match_type = 'auto',
                        match_confidence = 85.0,
                        needs_to_buy_quantity = %s,
                        is_user_confirmed = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE generation_id = %s AND ingredient_name = %s
                """, (
                    pantry_match['pantry_item_id'],
                    available_qty,
                    needs_to_buy,
                    generation_id,
                    ingredient['ingredient_name']
                ))
                refreshed_count += 1
            else:
                # No match found - mark as missing
                cursor.execute("""
                    UPDATE generation_ingredient_matches 
                    SET pantry_item_id = NULL,
                        pantry_available_quantity = NULL,
                        match_type = 'missing',
                        match_confidence = NULL,
                        needs_to_buy_quantity = %s,
                        is_user_confirmed = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE generation_id = %s AND ingredient_name = %s
                """, (
                    ingredient['required_quantity'],
                    generation_id,
                    ingredient['ingredient_name']
                ))
        
        # Update the shopping generation session counts
        cursor.execute("""
            UPDATE shopping_generation_sessions sgs
            SET 
                sgs.auto_matched_count = (
                    SELECT COUNT(*) FROM generation_ingredient_matches gim 
                    WHERE gim.generation_id = %s AND gim.match_type = 'auto'
                ),
                sgs.confirm_needed_count = (
                    SELECT COUNT(*) FROM generation_ingredient_matches gim 
                    WHERE gim.generation_id = %s AND gim.match_type = 'confirm'
                ),
                sgs.missing_count = (
                    SELECT COUNT(*) FROM generation_ingredient_matches gim 
                    WHERE gim.generation_id = %s AND gim.match_type = 'missing'
                )
            WHERE generation_id = %s
        """, (generation_id, generation_id, generation_id, generation_id))
        
        db.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Refreshed {refreshed_count} ingredient matches",
            "refreshed_count": refreshed_count,
            "total_ingredients": len(ingredients_to_refresh)
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False, 
            "message": f"Failed to refresh matches: {str(e)}"
        })
    finally:
        cursor.close()


@meal_plan_compat_bp.route("/meal-plans/<int:plan_id>/name", methods=["PUT"])
def update_meal_plan_name(plan_id):
    """Update meal plan name"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()
    new_name = data.get("name", "").strip()
    
    # Validate name length and content
    if not new_name:
        return jsonify({"success": False, "message": "Plan name cannot be empty"})
    
    if len(new_name) > 21:
        return jsonify({"success": False, "message": "Plan name must be 21 characters or less"})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First verify the meal plan belongs to the current user
        cursor.execute("""
            SELECT session_name FROM meal_plan_sessions 
            WHERE session_id = %s AND user_id = %s
        """, (plan_id, user_id))
        
        meal_plan = cursor.fetchone()
        if not meal_plan:
            return jsonify({"success": False, "message": "Meal plan not found or access denied"})
        
        # Update the meal plan name
        cursor.execute("""
            UPDATE meal_plan_sessions 
            SET session_name = %s 
            WHERE session_id = %s AND user_id = %s
        """, (new_name, plan_id, user_id))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Meal plan name updated successfully",
            "new_name": new_name
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False, 
            "message": f"Failed to update meal plan name: {str(e)}"
        })
    finally:
        cursor.close()


@meal_plan_compat_bp.route("/meal-plans/<int:plan_id>/shopping-list", methods=["POST"])
def add_items_to_shopping_list(plan_id):
    """Add selected meal plan items to shopping list"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()
    items = data.get("items", [])
    
    if not items:
        return jsonify({"success": False, "message": "No items provided"})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First verify the meal plan belongs to the current user
        cursor.execute("""
            SELECT session_name FROM meal_plan_sessions 
            WHERE session_id = %s AND user_id = %s
        """, (plan_id, user_id))
        
        meal_plan = cursor.fetchone()
        if not meal_plan:
            return jsonify({"success": False, "message": "Meal plan not found or access denied"})
        
        # Check if there's already a shopping list for this meal plan
        cursor.execute("""
            SELECT list_id FROM shopping_lists 
            WHERE user_id = %s AND meal_plan_session_id = %s AND is_meal_plan_list = TRUE
        """, (user_id, plan_id))
        
        existing_list = cursor.fetchone()
        
        if existing_list:
            list_id = existing_list["list_id"]
        else:
            # Create new shopping list for this meal plan
            list_name = f"Shopping List - {meal_plan['session_name']}"
            cursor.execute("""
                INSERT INTO shopping_lists (user_id, list_name, meal_plan_session_id, is_meal_plan_list, description)
                VALUES (%s, %s, %s, TRUE, 'Generated from meal plan ingredients')
            """, (user_id, list_name, plan_id))
            list_id = cursor.lastrowid
        
        # Add items to the shopping list
        added_count = 0
        for item in items:
            # Check if item already exists in the list
            cursor.execute("""
                SELECT item_id FROM shopping_list_items 
                WHERE list_id = %s AND item_name = %s
            """, (list_id, item["ingredient_name"]))
            
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update quantity if item exists
                cursor.execute("""
                    UPDATE shopping_list_items 
                    SET quantity = quantity + %s,
                        notes = CASE 
                            WHEN notes IS NULL THEN CONCAT(%s, ' ', %s)
                            ELSE CONCAT(notes, ', ', %s, ' ', %s)
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE item_id = %s
                """, (
                    int(item["quantity"]),
                    item["quantity"], item["unit"],
                    item["quantity"], item["unit"],
                    existing_item["item_id"]
                ))
            else:
                # Add new item
                notes = f"{item['quantity']} {item['unit']}" if item.get('unit') else str(item["quantity"])
                cursor.execute("""
                    INSERT INTO shopping_list_items (list_id, item_name, quantity, notes)
                    VALUES (%s, %s, %s, %s)
                """, (list_id, item["ingredient_name"], int(item["quantity"]), notes))
                
            added_count += 1
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": f"Added {added_count} items to shopping list",
            "list_id": list_id,
            "added_count": added_count
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False, 
            "message": f"Failed to add items to shopping list: {str(e)}"
        })
    finally:
        cursor.close()


def organize_recipes_by_day(recipe_data):
    """Organize recipe data by day and meal type (backward compatibility)"""
    organized = {}

    for row in recipe_data:
        day = row["day_number"]
        meal_type = row["meal_type"]

        if day not in organized:
            organized[day] = {}

        if meal_type not in organized[day]:
            organized[day][meal_type] = {
                "recipe_id": row["recipe_id"],
                "name": row["recipe_name"],
                "description": row["description"],
                "prep_time": row["prep_time"],
                "cook_time": row["cook_time"],
                "servings": row["servings"],
                "estimated_cost": row["estimated_cost"],
                "difficulty": row["difficulty"],
                "calories_per_serving": row["calories_per_serving"],
                "instructions": row["instructions"],
                "notes": row["notes"],
                "ingredients": [],
            }

        # Add ingredient if present
        if row["ingredient_name"]:
            organized[day][meal_type]["ingredients"].append(
                {
                    "name": row["ingredient_name"],
                    "quantity": row["quantity"],
                    "unit": row["unit"],
                    "notes": row["ingredient_notes"],
                }
            )

    return organized