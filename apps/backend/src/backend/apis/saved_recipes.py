from flask import Blueprint, request, jsonify, session
from src.database import get_db
from src.timezone_utils import get_user_current_date
from src.subscription_utils import check_subscription_limit, SubscriptionLimitExceeded, increment_usage
import json
from datetime import datetime, date

saved_recipes_bp = Blueprint("saved_recipes", __name__, url_prefix="/api/saved-recipes")


@saved_recipes_bp.route("", methods=["GET"])
def get_saved_recipes():
    """Get all saved recipes for a user with filtering options"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    # Query parameters for filtering
    meal_type = request.args.get("meal_type")
    is_favorite = request.args.get("is_favorite")
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "created_at")  # created_at, name, times_used, last_used
    sort_order = request.args.get("sort_order", "desc")  # asc, desc
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Build dynamic query based on filters
        where_conditions = ["sr.user_id = %s"]
        params = [user_id]
        
        if meal_type:
            where_conditions.append("sr.meal_type = %s")
            params.append(meal_type)
        
        if is_favorite and is_favorite.lower() == "true":
            where_conditions.append("sr.is_favorite = TRUE")
        
        if search:
            where_conditions.append("(sr.recipe_name LIKE %s OR sr.description LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        # Build ORDER BY clause
        valid_sort_fields = {
            "created_at": "sr.created_at",
            "name": "sr.recipe_name", 
            "times_used": "sr.times_used",
            "last_used": "sr.last_used_date"
        }
        sort_field = valid_sort_fields.get(sort_by, "sr.created_at")
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        
        query = f"""
            SELECT 
                sr.saved_recipe_id,
                sr.recipe_name,
                sr.description,
                sr.meal_type,
                sr.prep_time,
                sr.cook_time,
                sr.servings,
                sr.difficulty,
                sr.cuisine_type,
                sr.estimated_cost,
                sr.calories_per_serving,
                sr.is_favorite,
                sr.custom_tags,
                sr.times_used,
                sr.last_used_date,
                sr.created_at,
                COUNT(sri.ingredient_id) as ingredient_count
            FROM saved_recipes sr
            LEFT JOIN saved_recipe_ingredients sri ON sr.saved_recipe_id = sri.saved_recipe_id
            WHERE {' AND '.join(where_conditions)}
            GROUP BY sr.saved_recipe_id
            ORDER BY {sort_field} {sort_direction}
        """
        
        cursor.execute(query, params)
        recipes = cursor.fetchall()
        
        # Format response
        formatted_recipes = []
        for recipe in recipes:
            formatted_recipes.append({
                "saved_recipe_id": recipe["saved_recipe_id"],
                "recipe_name": recipe["recipe_name"],
                "description": recipe["description"],
                "meal_type": recipe["meal_type"],
                "prep_time": recipe["prep_time"],
                "cook_time": recipe["cook_time"],
                "total_time": (recipe["prep_time"] or 0) + (recipe["cook_time"] or 0),
                "servings": recipe["servings"],
                "difficulty": recipe["difficulty"],
                "cuisine_type": recipe["cuisine_type"],
                "estimated_cost": float(recipe["estimated_cost"]) if recipe["estimated_cost"] else None,
                "calories_per_serving": recipe["calories_per_serving"],
                "is_favorite": recipe["is_favorite"],
                "custom_tags": json.loads(recipe["custom_tags"]) if recipe["custom_tags"] else [],
                "times_used": recipe["times_used"],
                "last_used_date": recipe["last_used_date"].strftime("%Y-%m-%d") if recipe["last_used_date"] else None,
                "created_at": recipe["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "ingredient_count": recipe["ingredient_count"]
            })
        
        return jsonify({
            "success": True,
            "recipes": formatted_recipes,
            "total_count": len(formatted_recipes),
            "filters": {
                "meal_type": meal_type,
                "is_favorite": is_favorite,
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get saved recipes: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_saved_recipe_details(recipe_id):
    """Get detailed information for a specific saved recipe"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get recipe details
        recipe_query = """
            SELECT sr.*, 
                   m.meal_date as source_meal_date,
                   m.meal_type as source_meal_type,
                   rt.recipe_name as source_template_name
            FROM saved_recipes sr
            LEFT JOIN meals m ON sr.source_meal_id = m.meal_id
            LEFT JOIN recipe_templates rt ON sr.source_template_id = rt.template_id
            WHERE sr.saved_recipe_id = %s AND sr.user_id = %s
        """
        cursor.execute(recipe_query, (recipe_id, user_id))
        recipe = cursor.fetchone()
        
        if not recipe:
            return jsonify({"success": False, "message": "Recipe not found"})
        
        # Get ingredients
        ingredients_query = """
            SELECT ingredient_name, quantity, unit, notes, estimated_cost
            FROM saved_recipe_ingredients
            WHERE saved_recipe_id = %s
            ORDER BY ingredient_id
        """
        cursor.execute(ingredients_query, (recipe_id,))
        ingredients = cursor.fetchall()
        
        # Get recent usage
        usage_query = """
            SELECT usage_date, usage_context, notes
            FROM recipe_usage_log
            WHERE saved_recipe_id = %s
            ORDER BY usage_date DESC
            LIMIT 5
        """
        cursor.execute(usage_query, (recipe_id,))
        recent_usage = cursor.fetchall()
        
        # Format response
        recipe_details = {
            "saved_recipe_id": recipe["saved_recipe_id"],
            "recipe_name": recipe["recipe_name"],
            "description": recipe["description"],
            "meal_type": recipe["meal_type"],
            "prep_time": recipe["prep_time"],
            "cook_time": recipe["cook_time"],
            "total_time": (recipe["prep_time"] or 0) + (recipe["cook_time"] or 0),
            "servings": recipe["servings"],
            "difficulty": recipe["difficulty"],
            "instructions": recipe["instructions"],
            "cuisine_type": recipe["cuisine_type"],
            "notes": recipe["notes"],
            "estimated_cost": float(recipe["estimated_cost"]) if recipe["estimated_cost"] else None,
            "calories_per_serving": recipe["calories_per_serving"],
            "is_favorite": recipe["is_favorite"],
            "custom_tags": json.loads(recipe["custom_tags"]) if recipe["custom_tags"] else [],
            "times_used": recipe["times_used"],
            "last_used_date": recipe["last_used_date"].strftime("%Y-%m-%d") if recipe["last_used_date"] else None,
            "created_at": recipe["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "ingredients": [
                {
                    "name": ing["ingredient_name"],
                    "quantity": float(ing["quantity"]),
                    "unit": ing["unit"],
                    "notes": ing["notes"],
                    "estimated_cost": float(ing["estimated_cost"]) if ing["estimated_cost"] else None
                }
                for ing in ingredients
            ],
            "source": {
                "meal_date": recipe["source_meal_date"].strftime("%Y-%m-%d") if recipe["source_meal_date"] else None,
                "meal_type": recipe["source_meal_type"],
                "template_name": recipe["source_template_name"]
            },
            "recent_usage": [
                {
                    "date": usage["usage_date"].strftime("%Y-%m-%d"),
                    "context": usage["usage_context"],
                    "notes": usage["notes"]
                }
                for usage in recent_usage
            ]
        }
        
        return jsonify({"success": True, "recipe": recipe_details})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get recipe details: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/save-from-meal/<int:meal_id>", methods=["POST"])
def save_recipe_from_meal(meal_id):
    """Save a recipe from an existing meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    # Check subscription limits for saved recipes (free tier: 10 recipes)
    try:
        check_subscription_limit(user_id, 'saved_recipes')
    except SubscriptionLimitExceeded as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'limit_type': e.limit_type,
            'current_limit': e.current_limit,
            'requires_upgrade': True
        }), 403
    
    data = request.get_json() or {}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get meal details
        meal_query = """
            SELECT m.*, rt.recipe_name, rt.description, rt.prep_time, rt.cook_time,
                   rt.servings, rt.difficulty, rt.instructions, rt.cuisine_type,
                   rt.estimated_cost, rt.calories_per_serving
            FROM meals m
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE m.meal_id = %s AND m.user_id = %s
        """
        cursor.execute(meal_query, (meal_id, user_id))
        meal = cursor.fetchone()
        
        if not meal:
            return jsonify({"success": False, "message": "Meal not found"})
        
        # Use custom recipe data if template doesn't exist
        recipe_name = data.get("recipe_name") or meal["recipe_name"] or meal["custom_recipe_name"] or f"Custom {meal['meal_type'].title()}"
        description = data.get("description") or meal["description"] or ""
        instructions = data.get("instructions") or meal["instructions"] or meal["custom_instructions"] or "No instructions available"
        
        # Check if recipe already exists
        check_query = """
            SELECT saved_recipe_id FROM saved_recipes
            WHERE user_id = %s AND recipe_name = %s AND meal_type = %s
        """
        cursor.execute(check_query, (user_id, recipe_name, meal["meal_type"]))
        existing_recipe = cursor.fetchone()
        
        if existing_recipe:
            return jsonify({
                "success": False, 
                "message": "A recipe with this name and meal type already exists in your saved recipes",
                "existing_recipe_id": existing_recipe["saved_recipe_id"]
            })
        
        # Create saved recipe
        insert_recipe_query = """
            INSERT INTO saved_recipes (
                user_id, recipe_name, description, meal_type, prep_time, cook_time,
                servings, difficulty, instructions, cuisine_type, notes,
                estimated_cost, calories_per_serving, source_meal_id, source_template_id,
                custom_tags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_recipe_query, (
            user_id,
            recipe_name,
            description,
            meal["meal_type"],
            meal["prep_time"],
            meal["cook_time"],
            meal["servings"],
            meal["difficulty"] or "medium",
            instructions,
            meal["cuisine_type"],
            data.get("notes"),
            meal["estimated_cost"],
            meal["calories_per_serving"],
            meal_id,
            meal["recipe_template_id"],
            json.dumps(data.get("custom_tags", []))
        ))
        
        saved_recipe_id = cursor.lastrowid
        
        # Get and save ingredients if from template
        if meal["recipe_template_id"]:
            ingredients_query = """
                SELECT ingredient_name, quantity, unit, notes, estimated_cost
                FROM template_ingredients
                WHERE template_id = %s
            """
            cursor.execute(ingredients_query, (meal["recipe_template_id"],))
            ingredients = cursor.fetchall()
            
            for ingredient in ingredients:
                insert_ingredient_query = """
                    INSERT INTO saved_recipe_ingredients (
                        saved_recipe_id, ingredient_name, quantity, unit, notes, estimated_cost
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_ingredient_query, (
                    saved_recipe_id,
                    ingredient["ingredient_name"],
                    ingredient["quantity"],
                    ingredient["unit"],
                    ingredient["notes"],
                    ingredient["estimated_cost"]
                ))
        
        db.commit()
        
        # Increment saved recipes usage counter (for subscription limits)
        increment_usage(user_id, 'saved_recipes')
        
        return jsonify({
            "success": True,
            "message": f"Recipe '{recipe_name}' saved successfully",
            "saved_recipe_id": saved_recipe_id,
            "recipe_name": recipe_name
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to save recipe: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("", methods=["POST"])
def create_saved_recipe():
    """Create a new saved recipe from scratch"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    # Check subscription limits for saved recipes (free tier: 10 recipes)
    try:
        check_subscription_limit(user_id, 'saved_recipes')
    except SubscriptionLimitExceeded as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'limit_type': e.limit_type,
            'current_limit': e.current_limit,
            'requires_upgrade': True
        }), 403
    
    data = request.get_json()
    
    if not data or not data.get("recipe_name") or not data.get("meal_type") or not data.get("instructions"):
        return jsonify({"success": False, "message": "Recipe name, meal type, and instructions are required"})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Check if recipe already exists
        check_query = """
            SELECT saved_recipe_id FROM saved_recipes
            WHERE user_id = %s AND recipe_name = %s AND meal_type = %s
        """
        cursor.execute(check_query, (user_id, data["recipe_name"], data["meal_type"]))
        existing_recipe = cursor.fetchone()
        
        if existing_recipe:
            return jsonify({
                "success": False, 
                "message": "A recipe with this name and meal type already exists",
                "existing_recipe_id": existing_recipe["saved_recipe_id"]
            })
        
        # Create saved recipe
        insert_recipe_query = """
            INSERT INTO saved_recipes (
                user_id, recipe_name, description, meal_type, prep_time, cook_time,
                servings, difficulty, instructions, cuisine_type, notes,
                estimated_cost, calories_per_serving, custom_tags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_recipe_query, (
            user_id,
            data["recipe_name"],
            data.get("description"),
            data["meal_type"],
            data.get("prep_time"),
            data.get("cook_time"),
            data.get("servings", 1),
            data.get("difficulty", "medium"),
            data["instructions"],
            data.get("cuisine_type"),
            data.get("notes"),
            data.get("estimated_cost"),
            data.get("calories_per_serving"),
            json.dumps(data.get("custom_tags", []))
        ))
        
        saved_recipe_id = cursor.lastrowid
        
        # Add ingredients if provided
        ingredients = data.get("ingredients", [])
        for ingredient in ingredients:
            if not ingredient.get("name") or not ingredient.get("quantity"):
                continue
                
            insert_ingredient_query = """
                INSERT INTO saved_recipe_ingredients (
                    saved_recipe_id, ingredient_name, quantity, unit, notes, estimated_cost
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_ingredient_query, (
                saved_recipe_id,
                ingredient["name"],
                ingredient["quantity"],
                ingredient.get("unit", ""),
                ingredient.get("notes"),
                ingredient.get("estimated_cost")
            ))
        
        db.commit()
        
        # Increment saved recipes usage counter (for subscription limits)
        increment_usage(user_id, 'saved_recipes')
        
        return jsonify({
            "success": True,
            "message": f"Recipe '{data['recipe_name']}' created successfully",
            "saved_recipe_id": saved_recipe_id
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to create recipe: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/<int:recipe_id>", methods=["PUT"])
def update_saved_recipe(recipe_id):
    """Update a saved recipe"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Verify ownership
        verify_query = "SELECT saved_recipe_id FROM saved_recipes WHERE saved_recipe_id = %s AND user_id = %s"
        cursor.execute(verify_query, (recipe_id, user_id))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Recipe not found or access denied"})
        
        # Update recipe
        update_fields = []
        params = []
        
        for field in ["recipe_name", "description", "meal_type", "prep_time", "cook_time", 
                     "servings", "difficulty", "instructions", "cuisine_type", "notes",
                     "estimated_cost", "calories_per_serving", "is_favorite"]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if "custom_tags" in data:
            update_fields.append("custom_tags = %s")
            params.append(json.dumps(data["custom_tags"]))
        
        if update_fields:
            update_fields.append("updated_at = NOW()")
            params.extend([recipe_id, user_id])
            
            update_query = f"""
                UPDATE saved_recipes SET {', '.join(update_fields)}
                WHERE saved_recipe_id = %s AND user_id = %s
            """
            cursor.execute(update_query, params)
        
        # Update ingredients if provided
        if "ingredients" in data:
            # Delete existing ingredients
            cursor.execute("DELETE FROM saved_recipe_ingredients WHERE saved_recipe_id = %s", (recipe_id,))
            
            # Add new ingredients
            for ingredient in data["ingredients"]:
                if not ingredient.get("name") or not ingredient.get("quantity"):
                    continue
                    
                insert_ingredient_query = """
                    INSERT INTO saved_recipe_ingredients (
                        saved_recipe_id, ingredient_name, quantity, unit, notes, estimated_cost
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_ingredient_query, (
                    recipe_id,
                    ingredient["name"],
                    ingredient["quantity"],
                    ingredient.get("unit", ""),
                    ingredient.get("notes"),
                    ingredient.get("estimated_cost")
                ))
        
        db.commit()
        return jsonify({"success": True, "message": "Recipe updated successfully"})
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to update recipe: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
def delete_saved_recipe(recipe_id):
    """Delete a saved recipe"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Verify ownership
        verify_query = "SELECT recipe_name FROM saved_recipes WHERE saved_recipe_id = %s AND user_id = %s"
        cursor.execute(verify_query, (recipe_id, user_id))
        recipe = cursor.fetchone()
        
        if not recipe:
            return jsonify({"success": False, "message": "Recipe not found or access denied"})
        
        # Delete recipe (cascades will handle ingredients and usage logs)
        cursor.execute("DELETE FROM saved_recipes WHERE saved_recipe_id = %s AND user_id = %s", (recipe_id, user_id))
        
        db.commit()
        return jsonify({
            "success": True, 
            "message": f"Recipe '{recipe['recipe_name']}' deleted successfully"
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to delete recipe: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/<int:recipe_id>/use", methods=["POST"])
def use_saved_recipe(recipe_id):
    """Use a saved recipe by creating a meal or replacing an existing meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json() or {}
    
    # Required: date, meal_type, usage_context
    meal_date = data.get("meal_date")
    meal_type = data.get("meal_type")
    usage_context = data.get("usage_context", "meal_plan")  # meal_plan, direct_cook, replaced_meal
    replace_existing = data.get("replace_existing", False)
    
    if not meal_date or not meal_type:
        return jsonify({"success": False, "message": "meal_date and meal_type are required"})
    
    try:
        meal_date = datetime.strptime(meal_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get saved recipe details
        recipe_query = """
            SELECT * FROM saved_recipes 
            WHERE saved_recipe_id = %s AND user_id = %s
        """
        cursor.execute(recipe_query, (recipe_id, user_id))
        recipe = cursor.fetchone()
        
        if not recipe:
            return jsonify({"success": False, "message": "Recipe not found"})
        
        # Check for existing meal
        existing_meal_query = """
            SELECT meal_id FROM meals 
            WHERE user_id = %s AND meal_date = %s AND meal_type = %s
        """
        cursor.execute(existing_meal_query, (user_id, meal_date, meal_type))
        existing_meal = cursor.fetchone()
        
        if existing_meal and not replace_existing:
            return jsonify({
                "success": False,
                "message": "A meal already exists for this date and meal type. Set replace_existing=true to replace it.",
                "existing_meal_id": existing_meal["meal_id"],
                "requires_confirmation": True
            })
        
        meal_id = None
        
        if existing_meal and replace_existing:
            # Update existing meal
            update_meal_query = """
                UPDATE meals SET
                    recipe_template_id = NULL,
                    custom_recipe_name = %s,
                    custom_instructions = %s,
                    notes = %s,
                    updated_at = NOW()
                WHERE meal_id = %s
            """
            cursor.execute(update_meal_query, (
                recipe["recipe_name"],
                recipe["instructions"],
                f"Using saved recipe: {recipe['recipe_name']}",
                existing_meal["meal_id"]
            ))
            meal_id = existing_meal["meal_id"]
        else:
            # Create new meal
            create_meal_query = """
                INSERT INTO meals (
                    user_id, meal_date, meal_type, custom_recipe_name, custom_instructions, notes
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(create_meal_query, (
                user_id,
                meal_date,
                meal_type,
                recipe["recipe_name"],
                recipe["instructions"],
                f"Using saved recipe: {recipe['recipe_name']}"
            ))
            meal_id = cursor.lastrowid
        
        # Log recipe usage
        usage_log_query = """
            INSERT INTO recipe_usage_log (
                user_id, saved_recipe_id, used_for_meal_id, usage_date, usage_context, notes
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(usage_log_query, (
            user_id,
            recipe_id,
            meal_id,
            meal_date,
            usage_context,
            data.get("notes")
        ))
        
        # Update recipe usage count and last used date
        update_recipe_query = """
            UPDATE saved_recipes SET
                times_used = times_used + 1,
                last_used_date = %s,
                updated_at = NOW()
            WHERE saved_recipe_id = %s
        """
        cursor.execute(update_recipe_query, (meal_date, recipe_id))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": f"Recipe '{recipe['recipe_name']}' added to your meal plan for {meal_date}",
            "meal_id": meal_id,
            "recipe_name": recipe["recipe_name"],
            "meal_date": meal_date.strftime("%Y-%m-%d"),
            "meal_type": meal_type,
            "action": "replaced" if (existing_meal and replace_existing) else "created"
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to use recipe: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/<int:recipe_id>/favorite", methods=["POST"])
def toggle_recipe_favorite(recipe_id):
    """Toggle favorite status of a saved recipe"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get current favorite status
        query = "SELECT is_favorite, recipe_name FROM saved_recipes WHERE saved_recipe_id = %s AND user_id = %s"
        cursor.execute(query, (recipe_id, user_id))
        recipe = cursor.fetchone()
        
        if not recipe:
            return jsonify({"success": False, "message": "Recipe not found"})
        
        # Toggle favorite status
        new_status = not recipe["is_favorite"]
        update_query = """
            UPDATE saved_recipes SET is_favorite = %s, updated_at = NOW()
            WHERE saved_recipe_id = %s AND user_id = %s
        """
        cursor.execute(update_query, (new_status, recipe_id, user_id))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": f"Recipe '{recipe['recipe_name']}' {'added to' if new_status else 'removed from'} favorites",
            "is_favorite": new_status
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to update favorite status: {str(e)}"})
    finally:
        cursor.close()


@saved_recipes_bp.route("/stats", methods=["GET"])
def get_recipe_stats():
    """Get statistics about user's saved recipes"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get overall stats
        stats_query = """
            SELECT 
                COUNT(*) as total_recipes,
                COUNT(CASE WHEN is_favorite = TRUE THEN 1 END) as favorite_recipes,
                SUM(times_used) as total_uses,
                AVG(times_used) as avg_uses_per_recipe,
                COUNT(CASE WHEN meal_type = 'breakfast' THEN 1 END) as breakfast_recipes,
                COUNT(CASE WHEN meal_type = 'lunch' THEN 1 END) as lunch_recipes,
                COUNT(CASE WHEN meal_type = 'dinner' THEN 1 END) as dinner_recipes,
                COUNT(CASE WHEN meal_type = 'snack' THEN 1 END) as snack_recipes
            FROM saved_recipes
            WHERE user_id = %s
        """
        cursor.execute(stats_query, (user_id,))
        stats = cursor.fetchone()
        
        # Get most used recipes
        most_used_query = """
            SELECT recipe_name, times_used, last_used_date
            FROM saved_recipes
            WHERE user_id = %s AND times_used > 0
            ORDER BY times_used DESC, last_used_date DESC
            LIMIT 5
        """
        cursor.execute(most_used_query, (user_id,))
        most_used = cursor.fetchall()
        
        # Get recently added recipes
        recent_query = """
            SELECT recipe_name, meal_type, created_at
            FROM saved_recipes
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """
        cursor.execute(recent_query, (user_id,))
        recent = cursor.fetchall()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_recipes": stats["total_recipes"],
                "favorite_recipes": stats["favorite_recipes"],
                "total_uses": stats["total_uses"] or 0,
                "avg_uses_per_recipe": round(float(stats["avg_uses_per_recipe"] or 0), 1),
                "by_meal_type": {
                    "breakfast": stats["breakfast_recipes"],
                    "lunch": stats["lunch_recipes"],
                    "dinner": stats["dinner_recipes"],
                    "snack": stats["snack_recipes"]
                }
            },
            "most_used_recipes": [
                {
                    "recipe_name": recipe["recipe_name"],
                    "times_used": recipe["times_used"],
                    "last_used_date": recipe["last_used_date"].strftime("%Y-%m-%d") if recipe["last_used_date"] else None
                }
                for recipe in most_used
            ],
            "recently_added": [
                {
                    "recipe_name": recipe["recipe_name"],
                    "meal_type": recipe["meal_type"],
                    "created_at": recipe["created_at"].strftime("%Y-%m-%d")
                }
                for recipe in recent
            ]
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get recipe stats: {str(e)}"})
    finally:
        cursor.close()