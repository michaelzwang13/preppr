from flask import Blueprint, request, jsonify, session
from src.database import get_db
from src.timezone_utils import get_user_current_date
from src.subscription_utils import subscription_required, check_subscription_limit, SubscriptionLimitExceeded, increment_usage, get_user_subscription_info
import json
from datetime import datetime, timedelta

meals_bp = Blueprint("meals", __name__, url_prefix="/api")


def filter_nutrition_data_by_subscription(user_id, nutrition_data):
    """
    Filter nutrition data based on user's subscription tier.
    Free tier: calories + protein only
    Premium tier: all macro data
    """
    subscription_info = get_user_subscription_info(user_id)
    
    if subscription_info['tier'] == 'premium':
        # Premium users get full nutrition data
        return nutrition_data
    
    # Free tier users only get calories and protein
    filtered_data = {}
    
    # Always include these for free tier
    if 'calories' in nutrition_data:
        filtered_data['calories'] = nutrition_data['calories']
    if 'protein' in nutrition_data:
        filtered_data['protein'] = nutrition_data['protein']
    
    # Hide other macros for free tier
    filtered_data['carbs'] = None
    filtered_data['fat'] = None
    filtered_data['fiber'] = None
    filtered_data['sodium'] = None
    
    # Add upgrade prompts
    filtered_data['_upgrade_message'] = "Track your full macros & nutrients — Upgrade to Preppr+."
    filtered_data['_limited_tier'] = True
    
    return filtered_data


@meals_bp.route("/nutrition/<int:meal_id>", methods=["GET"])
def get_meal_nutrition(meal_id):
    """Get nutrition data for a specific meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
        
    try:
        # Get meal nutrition data
        nutrition_query = """
            SELECT mn.*, m.meal_type, m.meal_date, rt.recipe_name as recipe_name
            FROM meal_nutrition mn
            JOIN meals m ON mn.meal_id = m.meal_id
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE mn.meal_id = %s AND mn.user_id = %s
        """
        cursor.execute(nutrition_query, (meal_id, user_id))
        nutrition_data = cursor.fetchone()
        
        if not nutrition_data:
            return jsonify({"success": False, "message": "Nutrition data not found"})
        
        # Prepare nutrition data
        raw_nutrition_data = {
            "calories": float(nutrition_data["calories"]) if nutrition_data["calories"] else None,
            "protein": float(nutrition_data["protein_g"]) if nutrition_data["protein_g"] else None,
            "carbs": float(nutrition_data["carbohydrates_g"]) if nutrition_data["carbohydrates_g"] else None,
            "fat": float(nutrition_data["fat_g"]) if nutrition_data["fat_g"] else None,
            "fiber": float(nutrition_data["fiber_g"]) if nutrition_data["fiber_g"] else None,
            "sodium": float(nutrition_data["sodium_mg"]) if nutrition_data["sodium_mg"] else None
        }
        
        # Filter based on subscription tier
        filtered_nutrition = filter_nutrition_data_by_subscription(user_id, raw_nutrition_data)
        
        # Format the response
        response_data = {
            "success": True,
            "nutrition": {
                "meal_id": nutrition_data["meal_id"],
                "recipe_name": nutrition_data["recipe_name"],
                "meal_type": nutrition_data["meal_type"],
                "meal_date": nutrition_data["meal_date"].strftime("%Y-%m-%d"),
                "calories": filtered_nutrition["calories"],
                "macros": {
                    "protein": filtered_nutrition["protein"],
                    "carbs": filtered_nutrition["carbs"],
                    "fat": filtered_nutrition["fat"]
                },
                "fiber": filtered_nutrition["fiber"],
                "sodium": filtered_nutrition["sodium"],
                "servings": nutrition_data["servings"],
                "serving_size": nutrition_data["serving_size"],
                "source_type": nutrition_data["source_type"],
                "created_at": nutrition_data["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Add subscription-related metadata
        if '_upgrade_message' in filtered_nutrition:
            response_data['_upgrade_message'] = filtered_nutrition['_upgrade_message']
            response_data['_limited_tier'] = filtered_nutrition['_limited_tier']
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get nutrition data: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/nutrition/daily/<string:date>", methods=["GET"])
def get_daily_nutrition_summary(date):
    """Get daily nutrition summary for a specific date"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"})
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get all meals and nutrition for the specific date
        meals_query = """
            SELECT m.meal_id, m.meal_type, rt.name as recipe_name,
                   mn.calories, mn.protein_g, mn.carbohydrates_g, mn.fat_g,
                   mn.fiber_g, mn.sodium_mg, mn.servings, mn.serving_size,
                   m.is_completed
            FROM meals m
            LEFT JOIN meal_nutrition mn ON m.meal_id = mn.meal_id
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE m.user_id = %s AND m.meal_date = %s
            ORDER BY 
                CASE m.meal_type 
                    WHEN 'breakfast' THEN 1
                    WHEN 'lunch' THEN 2
                    WHEN 'dinner' THEN 3
                    WHEN 'snack' THEN 4
                    ELSE 5
                END
        """
        cursor.execute(meals_query, (user_id, target_date))
        meals_data = cursor.fetchall()
        
        # Calculate daily totals
        daily_totals = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
            "sodium": 0
        }
        
        meals_with_nutrition = []
        
        for meal in meals_data:
            # Prepare raw nutrition data
            raw_meal_nutrition = {
                "calories": float(meal["calories"]) if meal["calories"] else 0,
                "protein": float(meal["protein_g"]) if meal["protein_g"] else 0,
                "carbs": float(meal["carbohydrates_g"]) if meal["carbohydrates_g"] else 0,
                "fat": float(meal["fat_g"]) if meal["fat_g"] else 0,
                "fiber": float(meal["fiber_g"]) if meal["fiber_g"] else 0,
                "sodium": float(meal["sodium_mg"]) if meal["sodium_mg"] else 0
            }
            
            # Filter based on subscription tier
            filtered_meal_nutrition = filter_nutrition_data_by_subscription(user_id, raw_meal_nutrition)
            
            meal_nutrition = {
                "meal_id": meal["meal_id"],
                "meal_type": meal["meal_type"],
                "recipe_name": meal["recipe_name"],
                "is_completed": meal["is_completed"],
                "nutrition": {
                    "calories": filtered_meal_nutrition["calories"],
                    "protein": filtered_meal_nutrition["protein"],
                    "carbs": filtered_meal_nutrition["carbs"],
                    "fat": filtered_meal_nutrition["fat"],
                    "fiber": filtered_meal_nutrition["fiber"],
                    "sodium": filtered_meal_nutrition["sodium"]
                },
                "servings": meal["servings"],
                "serving_size": meal["serving_size"]
            }
            
            # Add to daily totals if meal is completed (or if we want to show planned vs actual)
            if meal["is_completed"]:
                daily_totals["calories"] += meal_nutrition["nutrition"]["calories"] or 0
                daily_totals["protein"] += meal_nutrition["nutrition"]["protein"] or 0
                daily_totals["carbs"] += meal_nutrition["nutrition"]["carbs"] or 0
                daily_totals["fat"] += meal_nutrition["nutrition"]["fat"] or 0
                daily_totals["fiber"] += meal_nutrition["nutrition"]["fiber"] or 0
                daily_totals["sodium"] += meal_nutrition["nutrition"]["sodium"] or 0
            
            meals_with_nutrition.append(meal_nutrition)
        
        # Filter daily totals based on subscription tier
        filtered_daily_totals = filter_nutrition_data_by_subscription(user_id, daily_totals)
        
        response_data = {
            "success": True,
            "date": date,
            "daily_totals": filtered_daily_totals,
            "meals": meals_with_nutrition,
            "total_meals": len(meals_data),
            "completed_meals": len([m for m in meals_data if m["is_completed"]])
        }
        
        # Add subscription-related metadata
        if '_upgrade_message' in filtered_daily_totals:
            response_data['_upgrade_message'] = filtered_daily_totals['_upgrade_message']
            response_data['_limited_tier'] = filtered_daily_totals['_limited_tier']
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get daily nutrition summary: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/generate-meal-plan", methods=["POST"])
def generate_meal_plan():
    """Generate a meal plan and store as individual meals"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    data = request.get_json()
    user_id = session["user_ID"]

    # Check subscription limits first
    try:
        # Check active meal plans limit (3 for free tier)
        check_subscription_limit(user_id, 'meal_plans_active')
        
        # Check advance planning limit
        days = int(data.get("days", 7))
        start_date_str = data.get("start_date")
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = datetime.now().date()
        
        # Calculate how many days in advance this plan starts
        days_in_advance = (start_date - datetime.now().date()).days
        
        # Free tier can't plan more than 7 days in advance
        if days_in_advance > 7:
            check_subscription_limit(user_id, 'meal_plans_advance_days')
    
    except SubscriptionLimitExceeded as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'limit_type': e.limit_type,
            'current_limit': e.current_limit,
            'requires_upgrade': True
        }), 403

    # Required fields (reuse from above checks)

    # Optional fields with defaults
    ingredients = data.get("ingredients", [])
    dietary_preference = data.get("dietary_preference", "none")
    budget = data.get("budget")
    cooking_time = data.get("cooking_time", 60)
    minimal_cooking_sessions = data.get("minimal_cooking_sessions", False)
    selected_meals = data.get("selected_meals", None)  # New parameter for meal selection
    nutrition_tracking_enabled = True

    try:
        days = int(days)
        if days < 1 or days > 7:
            return jsonify({"success": False, "message": "Days must be between 1 and 7"})
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid number of days"})

    # Parse start date or use today
    if not start_date:  
        start_date = datetime.now().date()
    elif type(start_date) == str:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid start date format. Use YYYY-MM-DD"})

    end_date = start_date + timedelta(days=days - 1)

    try:
        cooking_time = int(cooking_time)
        if cooking_time < 10 or cooking_time > 300:
            return jsonify({"success": False, "message": "Cooking time must be between 10 and 300 minutes"})
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid cooking time"})

    if budget:
        try:
            budget = float(budget)
            if budget < 10 or budget > 1000:
                return jsonify({"success": False, "message": "Budget must be between $10 and $1000"})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid budget amount"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Get user's pantry items for ingredient context
        if not ingredients:
            pantry_query = """
                SELECT item_name, quantity, unit, storage_type, expiration_date
                FROM pantry_items 
                WHERE user_id = %s AND is_consumed = FALSE
                ORDER BY expiration_date ASC
            """
            cursor.execute(pantry_query, (user_id,))
            pantry_items = cursor.fetchall()
            ingredients = [
                f"{item['item_name']} ({item['quantity']} {item['unit']})"
                for item in pantry_items[:20]
            ]

        # Check for existing meals in date range
        existing_meals_query = """
            SELECT meal_date, meal_type, is_locked 
            FROM meals 
            WHERE user_id = %s AND meal_date BETWEEN %s AND %s
        """
        cursor.execute(existing_meals_query, (user_id, start_date, end_date))
        existing_meals = cursor.fetchall()
        
        # Check if there are any existing meals in the date range
        if existing_meals:
            existing_dates = set()
            locked_meals = []
            unlocked_meals = []
            
            for meal in existing_meals:
                meal_date_str = meal['meal_date'].strftime('%Y-%m-%d')
                existing_dates.add(meal_date_str)
                
                if meal['is_locked']:
                    locked_meals.append(f"{meal_date_str} ({meal['meal_type']})")
                else:
                    unlocked_meals.append(f"{meal_date_str} ({meal['meal_type']})")
            
            # Create detailed error message
            error_parts = []
            if locked_meals:
                error_parts.append(f"Locked meals: {', '.join(locked_meals)}")
            if unlocked_meals:
                error_parts.append(f"Existing meals: {', '.join(unlocked_meals)}")
            
            error_message = f"Cannot generate meal plan. The selected date range conflicts with existing meals. {' | '.join(error_parts)}. Please choose a different date range or delete conflicting meals first."
            
            return jsonify({
                "success": False, 
                "message": error_message,
                "conflicting_dates": list(existing_dates),
                "locked_meals": locked_meals,
                "unlocked_meals": unlocked_meals
            })
        
        # No existing meals, safe to proceed
        blocked_slots = set()

        # Generate meal plan using AI
        meal_plan_data = generate_meal_plan_with_ai(
            days=days,
            start_date=start_date,
            ingredients=ingredients,
            dietary_preference=dietary_preference,
            budget=budget,
            cooking_time=cooking_time,
            blocked_slots=blocked_slots,
            minimal_cooking_sessions=minimal_cooking_sessions,
            selected_meals=selected_meals,
            nutrition_tracking_enabled=nutrition_tracking_enabled
        )

        if not meal_plan_data:
            return jsonify({"success": False, "message": "Failed to generate meal plan. Please try again."})

        # Create meal plan session
        session_name = f"Meal Plan - {start_date.strftime('%b %d')}"
        generation_prompt = f"Generated plan for {days} days with {len(ingredients)} ingredients, {dietary_preference} diet, ${budget} budget, {cooking_time}min cooking time"

        session_query = """
            INSERT INTO meal_plan_sessions (
                user_id, session_name, start_date, end_date, total_days,
                dietary_preference, budget_limit, max_cooking_time, generation_prompt
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(session_query, (
            user_id, session_name, start_date, end_date, days,
            dietary_preference, budget, cooking_time, generation_prompt
        ))
        session_id = cursor.lastrowid

        # Check if nutrition tracking is enabled for this user
        from src.backend.views.shopping import get_user_preference
        nutrition_tracking_enabled = get_user_preference(user_id, "nutrition_tracking_enabled", True)
        
        # Process each day and create individual meals
        created_meals = []
        recipe_template_map = {}

        # Create a lookup for selected meals if provided
        selected_meals_lookup = {}
        if selected_meals:
            for meal_selection in selected_meals:
                day = meal_selection["day"]
                meals = meal_selection["meals"]
                selected_meals_lookup[day] = meals

        for day_data in meal_plan_data.get("days", []):
            day_value = day_data.get("day", 1)
            print(f"DEBUG: day_value = {day_value}, type = {type(day_value)}")
            
            # Handle different possible formats for the day field
            if isinstance(day_value, str):
                # Check if it's a date string
                if '-' in str(day_value):
                    # It's a date string, extract day number from index
                    day_number = meal_plan_data.get("days", []).index(day_data) + 1
                    print(f"DEBUG: Using index-based day number: {day_number}")
                else:
                    # It's a string number
                    day_number = int(day_value)
            else:
                # It's already a number
                day_number = int(day_value)
            
            meal_date = start_date + timedelta(days=day_number - 1)
            print(f"DEBUG: Final meal_date = {meal_date}")
            
            for meal_type in ["breakfast", "lunch", "dinner"]:
                # Check if this meal type should be processed based on selected_meals
                if selected_meals and day_number in selected_meals_lookup:
                    if meal_type not in selected_meals_lookup[day_number]:
                        print(f"DEBUG: Skipping {meal_type} for day {day_number} - not selected")
                        continue
                
                if meal_type in day_data:
                    recipe_data = day_data[meal_type]
                    
                    # Check if this is a reused meal
                    if "reused_from_day" in recipe_data:
                        reused_day = recipe_data["reused_from_day"]
                        print(f"DEBUG: Found reused meal from day {reused_day}")
                        
                        # Find the original meal from the specified day
                        original_meal = None
                        for original_day_data in meal_plan_data.get("days", []):
                            original_day_number = original_day_data.get("day")
                            if original_day_number == reused_day and meal_type in original_day_data:
                                original_meal = original_day_data[meal_type]
                                break
                        
                        if original_meal:
                            original_name = original_meal.get("name", f"Custom {meal_type.title()}")
                            recipe_name = f"Leftovers of {original_name}"
                            
                            # Copy the original recipe data but update the name
                            recipe_data = original_meal.copy()
                            recipe_data["name"] = recipe_name
                            
                            print(f"DEBUG: Created leftover meal: {recipe_name}")
                        else:
                            # Fallback if original meal not found
                            recipe_name = f"Leftovers of Custom {meal_type.title()}"
                            recipe_data = {"name": recipe_name}
                    else:
                        recipe_name = recipe_data.get("name", "")

                    # Get or create recipe template
                    print(f"DEBUG: Creating template for {recipe_name} ({meal_type})")
                    template_id = get_or_create_recipe_template(cursor, recipe_data, meal_type)
                    print(f"DEBUG: Created template_id = {template_id}")
                    recipe_template_map[template_id] = recipe_data

                    # Create individual meal
                    meal_query = """
                        INSERT INTO meals (
                            user_id, meal_date, meal_type, recipe_template_id, session_id
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(meal_query, (user_id, meal_date, meal_type, template_id, session_id))
                    meal_id = cursor.lastrowid
                    
                    # Store nutrition data if available and nutrition tracking is enabled
                    if nutrition_tracking_enabled:
                        store_meal_nutrition(cursor, meal_id, user_id, recipe_data)
                    
                    created_meals.append({
                        "meal_id": meal_id,
                        "date": meal_date.strftime("%Y-%m-%d"),
                        "type": meal_type,
                        "recipe_name": recipe_name
                    })

        # Generate session shopping list and batch prep
        generate_session_shopping_list_with_fuzzy_matching(cursor, session_id, user_id, recipe_template_map)
        generate_session_batch_prep(cursor, session_id, meal_plan_data.get("batch_prep", []))

        db.commit()
        
        # Increment active meal plans usage counter (for subscription limits)
        increment_usage(user_id, 'meal_plans_active')

        return jsonify({
            "success": True,
            "session_id": session_id,
            "session_name": session_name,
            "created_meals": created_meals,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "message": f"Successfully generated {len(created_meals)} meals"
        })

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to generate meal plan: {str(e)}"})
    finally:
        cursor.close()


def get_or_create_recipe_template(cursor, recipe_data, meal_type):
    """Get existing recipe template or create new one"""
    recipe_name = recipe_data.get("name", "")
    
    # Handle instructions - convert array to string if needed
    instructions_raw = recipe_data.get("instructions", "")
    if isinstance(instructions_raw, list):
        # Check if steps are already numbered
        instructions_list = []
        for i, step in enumerate(instructions_raw):
            step_str = str(step).strip()
            # Check if step already starts with a number and period (e.g., "1. ")
            if step_str and not (step_str[0].isdigit() and '. ' in step_str[:4]):
                # Add numbering if not already numbered
                instructions_list.append(f"{i+1}. {step_str}")
            else:
                # Keep as-is if already numbered
                instructions_list.append(step_str)
        instructions = "\n".join(instructions_list)
        print(f"DEBUG: Converted instructions array to string: {len(instructions_raw)} steps")
    else:
        instructions = instructions_raw
    
    print(f"DEBUG: Final instructions type: {type(instructions)}")
    
    # Check if template already exists
    check_query = """
        SELECT template_id FROM recipe_templates 
        WHERE recipe_name = %s AND meal_type = %s AND instructions = %s
    """
    cursor.execute(check_query, (recipe_name, meal_type, instructions))
    existing = cursor.fetchone()
    
    if existing:
        return existing['template_id']
    
    # Create new template
    template_query = """
        INSERT INTO recipe_templates (
            recipe_name, description, meal_type, prep_time, cook_time,
            servings, estimated_cost, difficulty, calories_per_serving, instructions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(template_query, (
        recipe_name,
        recipe_data.get("description", ""),
        meal_type,
        recipe_data.get("prep_time", 0),
        recipe_data.get("cook_time", 0),
        recipe_data.get("servings", 1),
        recipe_data.get("cost", 0),
        recipe_data.get("difficulty", "medium"),
        recipe_data.get("calories", 0),
        instructions
    ))
    template_id = cursor.lastrowid
    
    # Add ingredients
    ingredients_list = recipe_data.get("ingredients", [])
    print(f"DEBUG: Adding {len(ingredients_list)} ingredients for template {template_id}")
    
    for i, ingredient in enumerate(ingredients_list):
        print(f"DEBUG: Ingredient {i}: {ingredient}")
        ingredient_query = """
            INSERT INTO template_ingredients (
                template_id, ingredient_name, quantity, unit, notes, estimated_cost
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        ingredient_values = (
            template_id,
            ingredient.get("name", ""),
            ingredient.get("quantity", 1),
            ingredient.get("unit", ""),
            ingredient.get("notes", ""),
            ingredient.get("cost", 0)
        )
        print(f"DEBUG: Ingredient values: {ingredient_values}")
        cursor.execute(ingredient_query, ingredient_values)
    
    return template_id


@meals_bp.route("/meals", methods=["GET"])
def get_meals():
    """Get meals for date range (for calendar view) - timezone-aware"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"success": False, "message": "start_date and end_date are required"})

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"})

    db = get_db()
    cursor = db.cursor()

    try:
        query = """
            SELECT 
                m.meal_id,
                m.meal_date,
                m.meal_type,
                m.is_locked,
                m.is_completed,
                m.notes,
                m.session_id,
                rt.recipe_name,
                rt.prep_time,
                rt.cook_time,
                rt.difficulty,
                m.custom_recipe_name,
                mps.session_name
            FROM meals m
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            LEFT JOIN meal_plan_sessions mps ON m.session_id = mps.session_id
            WHERE m.user_id = %s AND m.meal_date BETWEEN %s AND %s
            ORDER BY m.meal_date, FIELD(m.meal_type, 'breakfast', 'lunch', 'dinner', 'snack')
        """
        cursor.execute(query, (user_id, start_date, end_date))
        meals = cursor.fetchall()

        # Format for frontend with timezone awareness for "today" detection
        formatted_meals = []
        user_today = get_user_current_date(user_id)
        
        for meal in meals:
            meal_name = meal['recipe_name'] or meal['custom_recipe_name'] or f"Custom {meal['meal_type']}"
            formatted_meals.append({
                "meal_id": meal['meal_id'],
                "date": meal['meal_date'].strftime("%Y-%m-%d"),
                "type": meal['meal_type'],
                "name": meal_name,
                "prep_time": meal['prep_time'],
                "cook_time": meal['cook_time'],
                "difficulty": meal['difficulty'],
                "is_locked": meal['is_locked'],
                "is_completed": meal['is_completed'],
                "notes": meal['notes'],
                "session_id": meal['session_id'],
                "session_name": meal['session_name'],
                "is_today": meal['meal_date'] == user_today,
                "is_future": meal['meal_date'] > user_today
            })

        return jsonify({"success": True, "meals": formatted_meals, "user_today": user_today.strftime("%Y-%m-%d")})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get meals: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/meals/today", methods=["GET"])
def get_todays_meals():
    """Get today's meals based on user's timezone"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    
    try:
        # Get user's current date in their timezone
        user_today = get_user_current_date(user_id)
        
        db = get_db()
        cursor = db.cursor()

        query = """
            SELECT 
                m.meal_id,
                m.meal_date,
                m.meal_type,
                m.is_locked,
                m.is_completed,
                m.notes,
                m.session_id,
                rt.recipe_name,
                rt.prep_time,
                rt.cook_time,
                rt.difficulty,
                rt.instructions,
                rt.estimated_cost,
                m.custom_recipe_name,
                m.custom_instructions,
                mps.session_name
            FROM meals m
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            LEFT JOIN meal_plan_sessions mps ON m.session_id = mps.session_id
            WHERE m.user_id = %s AND m.meal_date = %s
            ORDER BY FIELD(m.meal_type, 'breakfast', 'lunch', 'dinner', 'snack')
        """
        cursor.execute(query, (user_id, user_today))
        meals = cursor.fetchall()
        
        # Format for frontend
        formatted_meals = []
        for meal in meals:
            meal_name = meal['recipe_name'] or meal['custom_recipe_name'] or f"Custom {meal['meal_type']}"
            instructions = meal['instructions'] or meal['custom_instructions'] or "No instructions available"
            
            formatted_meals.append({
                "meal_id": meal['meal_id'],
                "date": meal['meal_date'].strftime("%Y-%m-%d"),
                "type": meal['meal_type'],
                "name": meal_name,
                "instructions": instructions,
                "prep_time": meal['prep_time'],
                "cook_time": meal['cook_time'],
                "difficulty": meal['difficulty'],
                "estimated_cost": float(meal['estimated_cost']) if meal['estimated_cost'] else None,
                "is_locked": meal['is_locked'],
                "is_completed": meal['is_completed'],
                "notes": meal['notes'],
                "session_id": meal['session_id'],
                "session_name": meal['session_name']
            })

        return jsonify({
            "success": True, 
            "meals": formatted_meals,
            "date": user_today.strftime("%Y-%m-%d"),
            "total_meals": len(formatted_meals),
            "completed_meals": len([m for m in formatted_meals if m['is_completed']])
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get today's meals: {str(e)}"})
    finally:
        if 'cursor' in locals():
            cursor.close()


@meals_bp.route("/meals/<int:meal_id>", methods=["GET"])
def get_meal_details(meal_id):
    """Get detailed information for a specific meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Get meal with recipe template details
        meal_query = """
            SELECT 
                m.*,
                rt.recipe_name,
                rt.description,
                rt.prep_time,
                rt.cook_time,
                rt.servings,
                rt.estimated_cost,
                rt.difficulty,
                rt.calories_per_serving,
                rt.instructions,
                rt.cuisine_type,
                rt.dietary_tags
            FROM meals m
            LEFT JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE m.meal_id = %s AND m.user_id = %s
        """
        cursor.execute(meal_query, (meal_id, user_id))
        meal = cursor.fetchone()

        if not meal:
            return jsonify({"success": False, "message": "Meal not found"})

        # Get ingredients (template + custom)
        ingredients = []
        
        if meal['recipe_template_id']:
            # Get template ingredients
            template_ingredients_query = """
                SELECT ingredient_name, quantity, unit, notes, estimated_cost, FALSE as is_custom
                FROM template_ingredients 
                WHERE template_id = %s
            """
            cursor.execute(template_ingredients_query, (meal['recipe_template_id'],))
            ingredients.extend(cursor.fetchall())

        # Format response
        meal_details = {
            "meal_id": meal['meal_id'],
            "date": meal['meal_date'].strftime("%Y-%m-%d"),
            "type": meal['meal_type'],
            "name": meal['recipe_name'] or meal['custom_recipe_name'],
            "description": meal['description'],
            "instructions": meal['instructions'] or meal['custom_instructions'],
            "prep_time": meal['prep_time'],
            "cook_time": meal['cook_time'],
            "servings": meal['servings'],
            "estimated_cost": meal['estimated_cost'],
            "difficulty": meal['difficulty'],
            "calories_per_serving": meal['calories_per_serving'],
            "cuisine_type": meal['cuisine_type'],
            "dietary_tags": json.loads(meal['dietary_tags'] or '[]'),
            "is_locked": meal['is_locked'],
            "is_completed": meal['is_completed'],
            "notes": meal['notes'],
            "ingredients": ingredients,
            "session_id": meal['session_id']
        }

        return jsonify({"success": True, "meal": meal_details})

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get meal details: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/meals/<int:meal_id>", methods=["PUT"])
def update_meal(meal_id):
    """Update a specific meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify meal belongs to user and get meal date
        verify_query = "SELECT meal_id, meal_date FROM meals WHERE meal_id = %s AND user_id = %s"
        cursor.execute(verify_query, (meal_id, user_id))
        meal_info = cursor.fetchone()
        if not meal_info:
            return jsonify({"success": False, "message": "Meal not found or access denied"})
        
        # Check if trying to complete a future meal (timezone-aware)
        if 'is_completed' in data and data['is_completed']:
            meal_date = meal_info['meal_date']
            user_today = get_user_current_date(user_id)
            if meal_date > user_today:
                return jsonify({
                    "success": False, 
                    "message": "Cannot mark future meals as completed. You can only complete meals for today or past dates."
                })

        # Update meal fields
        update_fields = []
        params = []
        
        if 'custom_recipe_name' in data:
            update_fields.append("custom_recipe_name = %s")
            params.append(data['custom_recipe_name'])
            
        if 'custom_instructions' in data:
            update_fields.append("custom_instructions = %s")
            params.append(data['custom_instructions'])
            
        if 'is_locked' in data:
            update_fields.append("is_locked = %s")
            params.append(data['is_locked'])
            
        if 'is_completed' in data:
            update_fields.append("is_completed = %s")
            params.append(data['is_completed'])
            
        if 'notes' in data:
            update_fields.append("notes = %s")
            params.append(data['notes'])

        if update_fields:
            update_fields.append("updated_at = NOW()")
            params.extend([meal_id, user_id])
            
            update_query = f"""
                UPDATE meals SET {', '.join(update_fields)}
                WHERE meal_id = %s AND user_id = %s
            """
            cursor.execute(update_query, params)

        db.commit()
        return jsonify({"success": True, "message": "Meal updated successfully"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to update meal: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/meals/<int:meal_id>", methods=["DELETE"])
def delete_meal(meal_id):
    """Delete a specific meal"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()

    try:
        # Verify meal belongs to user
        verify_query = "SELECT meal_id FROM meals WHERE meal_id = %s AND user_id = %s"
        cursor.execute(verify_query, (meal_id, user_id))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Meal not found or access denied"})

        # Delete meal (cascades will handle custom ingredients)
        cursor.execute("DELETE FROM meals WHERE meal_id = %s AND user_id = %s", (meal_id, user_id))
        
        db.commit()
        return jsonify({"success": True, "message": "Meal deleted successfully"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to delete meal: {str(e)}"})
    finally:
        cursor.close()


# Import AI generation function from the old file
def generate_meal_plan_with_ai(days, start_date, ingredients, dietary_preference, budget, cooking_time, blocked_slots=None, minimal_cooking_sessions=False, selected_meals=None, nutrition_tracking_enabled=True):
    """Use Gemini AI to generate a structured meal plan, with OpenAI fallback"""
    import os
    import google.generativeai as genai
    from src.openai_utils import openai_meal_plan_generation

    try:
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not found, trying OpenAI fallback")
            # Build the prompt first for OpenAI fallback
            prompt = _build_meal_plan_prompt(days, start_date, ingredients, dietary_preference, budget, cooking_time, blocked_slots, minimal_cooking_sessions, selected_meals, nutrition_tracking_enabled)
            openai_result = openai_meal_plan_generation(prompt)
            if openai_result:
                print("DEBUG: OpenAI fallback successful for meal plan generation")
                return openai_result
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        # Build the prompt
        prompt = _build_meal_plan_prompt(days, start_date, ingredients, dietary_preference, budget, cooking_time, blocked_slots, minimal_cooking_sessions, selected_meals, nutrition_tracking_enabled)

        # Generate the meal plan
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean the response to extract just the JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end]
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end]

        # Parse JSON response
        try:
            meal_plan = json.loads(response_text)
            print("FULL RAW RESPONSE:\n", response.text)
            print(f"DEBUG: Successfully parsed meal plan with {len(meal_plan.get('days', []))} days")
            return meal_plan
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON parse error: {str(e)}")
            print("FULL RAW RESPONSE:\n", response.text)
            return None

    except Exception as e:
        print(f"ERROR: Gemini meal plan generation failed: {str(e)}, trying OpenAI fallback")
        # Try OpenAI fallback
        prompt = _build_meal_plan_prompt(days, start_date, ingredients, dietary_preference, budget, cooking_time, blocked_slots, minimal_cooking_sessions, selected_meals, nutrition_tracking_enabled)
        openai_result = openai_meal_plan_generation(prompt)
        if openai_result:
            print("DEBUG: OpenAI fallback successful for meal plan generation after Gemini failure")
            return openai_result
        print("WARNING: OpenAI fallback also failed")
        return None


def _build_meal_plan_prompt(days, start_date, ingredients, dietary_preference, budget, cooking_time, blocked_slots, minimal_cooking_sessions, selected_meals, nutrition_tracking_enabled):
    """Helper function to build the meal plan prompt for both Gemini and OpenAI"""
    # Format ingredients list
    ingredients_text = ", ".join(ingredients) if ingredients else "No specific ingredients provided"
    
    # Format blocked slots
    blocked_info = ""
    if blocked_slots:
        blocked_list = [f"{date.strftime('%Y-%m-%d')} {meal_type}" for date, meal_type in blocked_slots]
        blocked_info = f"\nSKIP these locked meal slots: {', '.join(blocked_list)}"

    # Format the minimal cooking sessions mode setting
    minimal_sessions_text = "true" if minimal_cooking_sessions else "false"
    budget_text = f"${budget}" if budget else "No limit"
    start_date_text = start_date.strftime('%B %d, %Y')
    
    # Format selected meals information
    selected_meals_info = ""
    if selected_meals:
        selected_meals_info = "\n\nSELECTED MEALS ONLY:\n"
        for meal_selection in selected_meals:
            day = meal_selection["day"]
            meals = meal_selection["meals"]
            selected_meals_info += f"- Day {day}: Generate only {', '.join(meals)}\n"
        selected_meals_info += "IMPORTANT: Only generate recipes for the specified meals above. Omit any meals not listed."
    
    # Create detailed prompt for meal planning
    nutrition_role = "nutrition planner" if nutrition_tracking_enabled else "meal planner"
    prompt = f'''You are a professional meal prep consultant and {nutrition_role}. Create a detailed {days}-day meal plan starting from {start_date_text} with the following requirements:

IMPORTANT: Use numeric day numbers (1, 2, 3, etc.) NOT dates in the "day" field.

REQUIREMENTS:
- Days: {days}
- Available ingredients: {ingredients_text}
- Dietary preference: {dietary_preference}
- Budget limit: {budget_text}
- Max cooking time per day: {cooking_time} minutes
- Minimal cooking sessions mode: {minimal_sessions_text} (true or false)
- Include breakfast, lunch, and dinner for each day (unless specified otherwise below)
- Focus on meal prep efficiency and batch cooking
- Prioritize using available ingredients first{blocked_info}{selected_meals_info}

If "minimal_cooking_sessions" is true:
- Minimize recipe variety by reusing the same meals for multiple days
- Show repeated meals using the "reused_from_day" field
- Plan larger batch prep sessions covering multiple days
- Add a "storage_plan" section listing fridge/freezer life for each recipe
- Emphasize cost savings and fewer total ingredients

If "minimal_cooking_sessions" is false:
- Provide unique recipes for each meal with more variety in flavors and ingredients
- Focus on balanced variety while still using pantry items first

For all plans:
- Make cooking "instructions" a step-by-step array with clear numbered steps, each including timing and equipment
- Include "make_ahead_tips", "storage", and "reheat_instructions" for every recipe
- Provide "macros" (protein, carbs, fat in grams) along with "calories"
- Include "alternate_ingredients" for substitutions
- Maintain flavor and ingredient balance across the plan

{f"""
NUTRITION REQUIREMENTS:
- Provide detailed and accurate macro estimates for each recipe
- Calculate "calories" per serving
- Break down "macros" with protein, carbs, fat in grams
- Add "fiber" and "sodium" estimates in grams/milligrams  
- Include "serving_size" description (e.g., "1 cup", "1 plate")
- Ensure nutrition data is realistic based on ingredients and portions""" if nutrition_tracking_enabled else ""}

Do not use fractions like 1/2 - convert them to decimals (e.g., 0.5) to ensure valid JSON
Do not wrap any times like (10 min) in the instructions. Just add times in the instructions themselves such as Roast broccoli for 20 minutes
Ingredient quantity must be a number. Use quantifiable units, do not use splash, taste, bunch, etc.

CRITICAL: In the JSON response, the "day" field must be a NUMBER (1, 2, 3, etc.), never a date string.

Respond with a valid JSON object in exactly this format:

{{
  "minimal_cooking_sessions": {minimal_sessions_text},
  "days": [
    {{
      "day": 1,
      "breakfast": {{
        "name": "Recipe Name",
        "description": "Brief description",
        "prep_time": 15,
        "cook_time": 20,
        "servings": 2,
        "cost": 4.50,
        "difficulty": "easy",{f"""
        "calories": 350,
        "macros": {{"protein": 20, "carbs": 30, "fat": 10}},
        "fiber": 8,
        "sodium": 150,
        "serving_size": "1 cup",""" if nutrition_tracking_enabled else ""}
        "instructions": [
          "Step 1: ...",
          "Step 2: ..."
        ],
        "ingredients": [
          {{"name": "eggs", "quantity": 2, "unit": "pcs", "notes": "", "cost": 1.00}}
        ],
        "make_ahead_tips": "Chop vegetables the night before",
        "storage": "Store in airtight container for up to 3 days in fridge",
        "reheat_instructions": "Microwave for 60 seconds or reheat in skillet on low heat for 5 minutes",
        "notes": "Can be prepped night before"
      }},
      "lunch": {{"...": "..."}},
      "dinner": {{"...": "..."}}
    }},
    {{
      "day": 2,
      "breakfast": {{"reused_from_day": 1}},
      "lunch": {{"reused_from_day": 1}},
      "dinner": {{"reused_from_day": 1}}
    }}
  ],
  "batch_prep": [
    {{
      "session_name": "Main Cooking Session",
      "order": 1,
      "description": "Prepare all breakfasts, lunches, and dinners for Days 1-4 in one batch",
      "time": 180,
      "recipes": "All meals for Days 1-4",
      "equipment": "Large pot, oven, storage containers",
      "tips": "Cool completely before refrigerating or freezing"
    }}
  ],
  "storage_plan": [
    {{
      "recipe": "Overnight Oats with Berries",
      "fridge_life_days": 4,
      "freezer_life_days": 0,
      "notes": "Best eaten fresh"
    }}
  ]
}}

Generate the complete meal plan now. Remember to convert fractions into decimal'''
    
    return prompt


def generate_session_shopping_list_with_fuzzy_matching(cursor, session_id, user_id, recipe_template_map):
    """Generate shopping list for a meal plan session with fuzzy matching integration"""
    try:
        # Get all meals in this session
        meals_query = """
            SELECT m.meal_id, rt.template_id
            FROM meals m
            JOIN recipe_templates rt ON m.recipe_template_id = rt.template_id
            WHERE m.session_id = %s
        """
        cursor.execute(meals_query, (session_id,))
        session_meals = cursor.fetchall()

        if not session_meals:
            return

        # Get ingredients for all templates used in this session
        template_ids = [meal['template_id'] for meal in session_meals]
        print(f"DEBUG: template_ids = {template_ids}")
        
        if not template_ids:
            print("DEBUG: No template IDs found, skipping ingredient generation")
            return
        
        placeholders = ','.join(['%s'] * len(template_ids))
        
        ingredients_query = f"""
            SELECT ti.template_id, ti.ingredient_name, ti.quantity, ti.unit, ti.estimated_cost
            FROM template_ingredients ti
            WHERE ti.template_id IN ({placeholders})
        """
        print(f"DEBUG: ingredients_query = {ingredients_query}")
        print(f"DEBUG: template_ids for query = {template_ids}")
        cursor.execute(ingredients_query, template_ids)
        ingredients = cursor.fetchall()

        # Consolidate ingredients by name
        consolidated = {}
        meal_usage = {}
        
        for ingredient in ingredients:
            name = ingredient["ingredient_name"].lower()
            if name not in consolidated:
                consolidated[name] = {
                    "name": ingredient["ingredient_name"],
                    "total_quantity": 0,
                    "unit": ingredient["unit"],
                    "total_cost": 0,
                    "meals_using": []
                }

            consolidated[name]["total_quantity"] += float(ingredient["quantity"] or 0)
            consolidated[name]["total_cost"] += float(ingredient["estimated_cost"] or 0)
            
            # Track which meals use this ingredient
            for meal in session_meals:
                if meal['template_id'] == ingredient['template_id']:
                    consolidated[name]["meals_using"].append(meal['meal_id'])

        # Use enhanced shopping generation with fuzzy matching
        from src.services.enhanced_shopping_generation import enhanced_shopping_generator
        
        # Prepare ingredients for fuzzy matching
        ingredients_for_matching = [
            {
                "ingredient_name": item_data["name"],
                "quantity": item_data["total_quantity"],
                "unit": item_data["unit"]
            }
            for item_data in consolidated.values()
        ]
        
        # Perform fuzzy matching and get enhanced results
        if ingredients_for_matching:
            from src.services.fuzzy_matching import fuzzy_matching_service
            matching_results = fuzzy_matching_service.batch_match_ingredients(user_id, ingredients_for_matching)
            
            # Create shopping generation session
            cursor.execute("""
                INSERT INTO shopping_generation_sessions 
                (user_id, meal_plan_session_id, generation_type, total_ingredients)
                VALUES (%s, %s, 'meal_plan', %s)
            """, [user_id, session_id, len(matching_results)])
            
            generation_id = cursor.lastrowid
            
            # Process matching results and create shopping list entries
            auto_matched = 0
            confirm_needed = 0
            missing = 0
            
            for i, result in enumerate(matching_results):
                original_data = list(consolidated.values())[i]
                
                # Skip items with zero or negative required quantities
                if result.required_quantity <= 0:
                    print(f"DEBUG: Skipping zero-quantity ingredient: {result.ingredient_name}")
                    continue
                
                # Store detailed matching result
                cursor.execute("""
                    INSERT INTO generation_ingredient_matches 
                    (generation_id, ingredient_name, required_quantity, required_unit, 
                     pantry_item_id, pantry_available_quantity, match_confidence, 
                     match_type, needs_to_buy_quantity, estimated_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    generation_id,
                    result.ingredient_name,
                    result.required_quantity,
                    result.required_unit,
                    result.best_match.pantry_item_id if result.best_match else None,
                    result.best_match.available_quantity if result.best_match else None,
                    result.best_match.confidence_score if result.best_match else None,
                    result.match_type,
                    result.needs_to_buy,
                    original_data["total_cost"]
                ])
                
                # Count match types
                if result.match_type == "auto":
                    auto_matched += 1
                elif result.match_type == "confirm":
                    confirm_needed += 1
                else:
                    missing += 1
                
                # Insert into session shopping list (original table for compatibility)
                category = categorize_ingredient(result.ingredient_name)
                
                shopping_query = """
                    INSERT INTO session_shopping_lists (
                        session_id, ingredient_name, total_quantity, unit,
                        estimated_cost, category, meals_using
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(shopping_query, (
                    session_id,
                    result.ingredient_name,
                    result.required_quantity,  # Show total required quantity, not just what's needed
                    result.required_unit,
                    original_data["total_cost"],
                    category,
                    json.dumps(original_data["meals_using"])
                ))
            
            # Update generation session with summary
            cursor.execute("""
                UPDATE shopping_generation_sessions 
                SET auto_matched_count = %s, confirm_needed_count = %s, 
                    missing_count = %s, completed_at = NOW()
                WHERE generation_id = %s
            """, [auto_matched, confirm_needed, missing, generation_id])
            
            print(f"DEBUG: Enhanced shopping list generated - Auto: {auto_matched}, Confirm: {confirm_needed}, Missing: {missing}")
        
        else:
            # No ingredients found, create empty session for tracking
            cursor.execute("""
                INSERT INTO shopping_generation_sessions 
                (user_id, meal_plan_session_id, generation_type, total_ingredients, completed_at)
                VALUES (%s, %s, 'meal_plan', 0, NOW())
            """, [user_id, session_id])

    except Exception as e:
        print(f"ERROR: Failed to generate enhanced shopping list: {str(e)}")
        # Fallback to basic generation if fuzzy matching fails
        generate_session_shopping_list_basic(cursor, session_id, consolidated if 'consolidated' in locals() else {})


def generate_session_shopping_list_basic(cursor, session_id, consolidated):
    """Fallback basic shopping list generation without fuzzy matching"""
    try:
        # Insert consolidated shopping list items using basic method
        for item_data in consolidated.values():
            # Skip items with zero or negative quantities
            if item_data["total_quantity"] <= 0:
                print(f"DEBUG: Skipping zero-quantity item: {item_data['name']}")
                continue
                
            category = categorize_ingredient(item_data["name"])
            
            shopping_query = """
                INSERT INTO session_shopping_lists (
                    session_id, ingredient_name, total_quantity, unit,
                    estimated_cost, category, meals_using
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(shopping_query, (
                session_id,
                item_data["name"],
                item_data["total_quantity"],
                item_data["unit"],
                item_data["total_cost"],
                category,
                json.dumps(item_data["meals_using"])
            ))
            
        print(f"DEBUG: Basic shopping list generated with {len(consolidated)} items")
        
    except Exception as e:
        print(f"ERROR: Failed to generate basic shopping list: {str(e)}")


def generate_session_batch_prep(cursor, session_id, batch_prep_data):
    """Generate batch prep steps for a meal plan session"""
    try:
        for step_data in batch_prep_data:
            step_query = """
                INSERT INTO session_batch_prep (
                    session_id, prep_session_name, step_order, description,
                    estimated_time, equipment_needed, tips
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(step_query, (
                session_id,
                step_data.get("session_name", "Prep Session"),
                step_data.get("order", 1),
                step_data.get("description", ""),
                step_data.get("time", 30),
                step_data.get("equipment", ""),
                step_data.get("tips", "")
            ))
    except Exception as e:
        print(f"ERROR: Failed to generate batch prep: {str(e)}")


def store_meal_nutrition(cursor, meal_id, user_id, recipe_data):
    """Store nutrition data for a meal if available in recipe_data"""
    try:
        # Extract nutrition data from recipe
        calories = recipe_data.get("calories")
        macros = recipe_data.get("macros", {})
        fiber = recipe_data.get("fiber")
        sodium = recipe_data.get("sodium")
        servings = recipe_data.get("servings", 1)
        serving_size = recipe_data.get("serving_size")
        
        # Only store if we have at least calories or macros
        if calories is not None or macros:
            nutrition_query = """
                INSERT INTO meal_nutrition (
                    meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, 
                    fiber_g, sodium_mg, servings, serving_size, source_type, ai_model_used
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(nutrition_query, (
                meal_id,
                user_id,
                calories,
                macros.get("protein"),
                macros.get("carbs"),
                macros.get("fat"), 
                fiber,
                sodium,
                servings,
                serving_size,
                'ai_generated',
                'gemini-1.5-flash-latest'
            ))
            
            print(f"DEBUG: Stored nutrition for meal_id {meal_id}: {calories} calories")
    except Exception as e:
        print(f"ERROR: Failed to store nutrition for meal_id {meal_id}: {str(e)}")


def categorize_ingredient(ingredient_name):
    """Simple ingredient categorization"""
    name = ingredient_name.lower()

    if any(word in name for word in ["apple", "banana", "orange", "lettuce", "tomato", "potato", "carrot", "onion"]):
        return "Produce"
    elif any(word in name for word in ["chicken", "beef", "pork", "fish", "meat"]):
        return "Meat & Seafood"
    elif any(word in name for word in ["milk", "cheese", "yogurt", "butter", "egg"]):
        return "Dairy"
    elif any(word in name for word in ["rice", "pasta", "bread", "flour"]):
        return "Grains"
    elif any(word in name for word in ["oil", "salt", "pepper", "spice"]):
        return "Condiments"
    else:
        return "Other"


@meals_bp.route("/user/preferences", methods=["GET", "POST"])
def user_preferences():
    """Get or set user preferences"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        if request.method == "GET":
            # Get user preferences
            preferences_query = """
                SELECT preference_key, preference_value, data_type 
                FROM user_preferences 
                WHERE user_id = %s
            """
            cursor.execute(preferences_query, (user_id,))
            preferences_data = cursor.fetchall()
            
            preferences = {}
            for pref in preferences_data:
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
            
            return jsonify({
                "success": True,
                "preferences": preferences
            })
        
        elif request.method == "POST":
            # Update user preferences
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "message": "No data provided"})
            
            for key, value in data.items():
                # Determine data type
                if isinstance(value, bool):
                    data_type = "boolean"
                    value_str = str(value).lower()
                elif isinstance(value, (int, float)):
                    data_type = "number"
                    value_str = str(value)
                elif isinstance(value, (dict, list)):
                    data_type = "json"
                    import json
                    value_str = json.dumps(value)
                else:
                    data_type = "string"
                    value_str = str(value)
                
                # Insert or update preference
                upsert_query = """
                    INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        preference_value = VALUES(preference_value),
                        data_type = VALUES(data_type),
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(upsert_query, (user_id, key, value_str, data_type))
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Preferences updated successfully"
            })
        
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to manage preferences: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/user/preferences/<preference_key>", methods=["GET", "POST"])
def single_user_preference(preference_key):
    """Get or set a single user preference"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    db = get_db()
    cursor = db.cursor()
    
    try:
        if request.method == "GET":
            # Get single preference
            preference_query = """
                SELECT preference_value, data_type 
                FROM user_preferences 
                WHERE user_id = %s AND preference_key = %s
            """
            cursor.execute(preference_query, (user_id, preference_key))
            preference_data = cursor.fetchone()
            
            if preference_data:
                value = preference_data["preference_value"]
                data_type = preference_data["data_type"]
                
                # Convert value based on data type
                if data_type == "boolean":
                    converted_value = value.lower() == "true"
                elif data_type == "number":
                    converted_value = float(value) if '.' in value else int(value)
                elif data_type == "json":
                    import json
                    converted_value = json.loads(value)
                else:
                    converted_value = value
                
                return jsonify({
                    "success": True,
                    "preference_key": preference_key,
                    "value": converted_value
                })
            else:
                # Return default values for known preferences
                defaults = {
                    "nutrition_tracking_enabled": True,
                    "email_notifications": True,
                    "theme_preference": "system",
                    "measurement_unit": "imperial"
                }
                
                default_value = defaults.get(preference_key, None)
                return jsonify({
                    "success": True,
                    "preference_key": preference_key,
                    "value": default_value,
                    "is_default": True
                })
        
        elif request.method == "POST":
            # Update single preference
            data = request.get_json()
            if not data or "value" not in data:
                return jsonify({"success": False, "message": "No value provided"})
            
            value = data["value"]
            
            # Determine data type
            if isinstance(value, bool):
                data_type = "boolean"
                value_str = str(value).lower()
            elif isinstance(value, (int, float)):
                data_type = "number"
                value_str = str(value)
            elif isinstance(value, (dict, list)):
                data_type = "json"
                import json
                value_str = json.dumps(value)
            else:
                data_type = "string"
                value_str = str(value)
            
            # Insert or update preference
            upsert_query = """
                INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    preference_value = VALUES(preference_value),
                    data_type = VALUES(data_type),
                    updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(upsert_query, (user_id, preference_key, value_str, data_type))
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": f"Preference '{preference_key}' updated successfully"
            })
        
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to manage preference: {str(e)}"})
    finally:
        cursor.close()


@meals_bp.route("/advanced-meal-planning/chat", methods=["POST"])
def advanced_meal_planning_chat():
    """Handle natural language requests for advanced meal planning"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    data = request.get_json()
    user_id = session["user_ID"]
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"success": False, "message": "Message is required"})
    
    # Get context from sidebar inputs
    context = {
        "pantry_items": data.get("pantry_items", []),
        "food_restrictions": data.get("food_restrictions", []),
        "dietary_preference": data.get("dietary_preference", "none"),
        "conversation_history": data.get("conversation_history", [])
    }
    
    try:
        # Check subscription limits for advanced features
        check_subscription_limit(user_id, 'ai_chat_requests')
        
        # Generate response using AI
        response = generate_chat_response(message, context, user_id)
        
        if response:
            # Increment usage counter
            increment_usage(user_id, 'ai_chat_requests')
            
            return jsonify({
                "success": True,
                "response": response["message"],
                "suggestions": response.get("suggestions", []),
                "action_required": response.get("action_required", False),
                "meal_plan_data": response.get("meal_plan_data")
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Sorry, I'm having trouble processing your request right now. Please try again."
            })
    
    except SubscriptionLimitExceeded as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'limit_type': e.limit_type,
            'current_limit': e.current_limit,
            'requires_upgrade': True
        }), 403
    except Exception as e:
        print(f"ERROR: Advanced meal planning chat failed: {str(e)}")
        return jsonify({
            "success": False, 
            "message": "An error occurred while processing your request."
        })


def generate_chat_response(message, context, user_id):
    """Generate AI response for meal planning chat"""
    try:
        # Build conversation prompt
        prompt = build_chat_prompt(message, context, user_id)
        
        # Try Gemini first, then OpenAI fallback
        response = gemini_chat_response(prompt)
        if not response:
            response = openai_chat_response(prompt)
        
        return response
        
    except Exception as e:
        print(f"ERROR: Chat response generation failed: {str(e)}")
        return None


def build_chat_prompt(message, context, user_id):
    """Build the prompt for AI chat response"""
    # Get user's current pantry items
    pantry_items = get_user_pantry_items(user_id)
    pantry_text = ", ".join([f"{item['item_name']} ({item['quantity']} {item['unit'] or ''})" for item in pantry_items[:10]]) if pantry_items else "No pantry items available"
    
    # Build restrictions text
    restrictions_text = ", ".join(context["food_restrictions"]) if context["food_restrictions"] else "None specified"
    
    # Build conversation history
    history_text = ""
    if context["conversation_history"]:
        for i, msg in enumerate(context["conversation_history"][-6:]):  # Last 6 messages for context
            sender = "User" if msg.get("sender") == "user" else "Assistant"
            history_text += f"{sender}: {msg.get('message', '')}\n"
    
    prompt = f"""You are an expert meal planning assistant. Help the user create personalized meal plans based on their needs, pantry items, and preferences.

CONTEXT:
- Available pantry items: {pantry_text}
- Food restrictions: {restrictions_text}
- Dietary preference: {context['dietary_preference']}

CONVERSATION HISTORY:
{history_text}

USER MESSAGE: {message}

INSTRUCTIONS:
1. Respond in a conversational, helpful tone
2. Ask clarifying questions when needed
3. Suggest meal plans based on available ingredients
4. Consider dietary preferences and restrictions
5. Keep responses concise but informative
6. If the user wants to generate a meal plan, gather: days, start date, special requests

RESPONSE FORMAT (JSON):
{{
    "message": "Your conversational response",
    "suggestions": ["Quick suggestion 1", "Quick suggestion 2"],
    "action_required": false,
    "meal_plan_data": null
}}

If ready to generate a meal plan, set action_required to true and include meal_plan_data with:
{{
    "days": number,
    "start_date": "YYYY-MM-DD",
    "dietary_preference": "preference",
    "ingredients": ["ingredient1", "ingredient2"],
    "food_restrictions": ["restriction1"],
    "budget": number or null,
    "cooking_time": number
}}

Respond with valid JSON only:"""
    
    return prompt


def get_user_pantry_items(user_id):
    """Get user's current pantry items"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT item_name, quantity, unit, storage_type, expiration_date
            FROM pantry_items 
            WHERE user_id = %s AND is_consumed = FALSE
            ORDER BY expiration_date ASC, item_name
            LIMIT 20
        """
        cursor.execute(query, (user_id,))
        items = cursor.fetchall()
        cursor.close()
        return items
        
    except Exception as e:
        print(f"ERROR: Failed to get pantry items: {str(e)}")
        return []


def gemini_chat_response(prompt):
    """Generate response using Gemini AI"""
    try:
        import requests
        import os
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Extract JSON from response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end]
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end]
                
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    print(f"DEBUG: Gemini response not valid JSON: {response_text}")
                    return None
                    
    except Exception as e:
        print(f"ERROR: Gemini chat failed: {str(e)}")
        return None


def openai_chat_response(prompt):
    """Generate response using OpenAI as fallback"""
    try:
        import requests
        import os
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return None
            
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and result['choices']:
                response_text = result['choices'][0]['message']['content'].strip()
                
                # Extract JSON from response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end]
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end]
                
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    print(f"DEBUG: OpenAI response not valid JSON: {response_text}")
                    return None
                    
    except Exception as e:
        print(f"ERROR: OpenAI chat failed: {str(e)}")
        return None