from flask import Blueprint, request, jsonify, session
from src.database import get_db
from src.subscription_utils import get_user_subscription_info

nutrition_bp = Blueprint("nutrition", __name__, url_prefix="/api")

def get_accessible_nutrition_fields(user_id):
    """Get which nutrition fields the user can access based on their subscription"""
    subscription_info = get_user_subscription_info(user_id)
    is_premium = subscription_info['tier'] == 'premium' and subscription_info['status'] == 'active'
    
    # Free users can access calories, protein, and fat
    # Premium users can access all fields
    if is_premium:
        return {
            'calories': True,
            'protein': True, 
            'carbs': True,
            'fat': True,
            'fiber': True,
            'sodium': True
        }
    else:
        return {
            'calories': True,
            'protein': True,
            'carbs': False,  # Premium only
            'fat': True,
            'fiber': False,  # Premium only
            'sodium': False  # Premium only
        }


@nutrition_bp.route("/nutrition/goals", methods=["GET"])
def get_nutrition_goals():
    """Get user's nutrition goals and preferences"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    accessible_fields = get_accessible_nutrition_fields(user_id)
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        query = """
            SELECT daily_calories_goal, calories_type,
                   daily_protein_goal_g, protein_type,
                   daily_carbs_goal_g, carbs_type,
                   daily_fat_goal_g, fat_type,
                   daily_fiber_goal_g, fiber_type,
                   daily_sodium_limit_mg, sodium_type,
                   goal_type, activity_level,
                   age, gender, weight_lbs, height_inches
            FROM user_nutrition_goals 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY updated_at DESC
            LIMIT 1
        """
        cursor.execute(query, (user_id,))
        goals = cursor.fetchone()

        # Build response based on accessible fields
        response_goals = {}
        
        if goals:
            # Always include basic accessible fields (convert to int for consistency)
            response_goals["daily_calories"] = int(float(goals["daily_calories_goal"]))
            response_goals["calories_type"] = goals["calories_type"]
            response_goals["daily_protein"] = int(float(goals["daily_protein_goal_g"]))
            response_goals["protein_type"] = goals["protein_type"]
            response_goals["daily_fat"] = int(float(goals["daily_fat_goal_g"]))
            response_goals["fat_type"] = goals["fat_type"]
            
            # Include premium fields only if accessible (convert to int for consistency)
            if accessible_fields["carbs"]:
                response_goals["daily_carbs"] = int(float(goals["daily_carbs_goal_g"]))
                response_goals["carbs_type"] = goals["carbs_type"]
            
            if accessible_fields["fiber"]:
                response_goals["daily_fiber"] = int(float(goals["daily_fiber_goal_g"]))
                response_goals["fiber_type"] = goals["fiber_type"]
            
            if accessible_fields["sodium"]:
                response_goals["daily_sodium"] = int(float(goals["daily_sodium_limit_mg"]))
                response_goals["sodium_type"] = goals["sodium_type"]
            
            # Include metadata
            response_goals["goal_type"] = goals["goal_type"]
            response_goals["activity_level"] = goals["activity_level"]
            response_goals["age"] = goals["age"]
            response_goals["gender"] = goals["gender"]
            response_goals["weight_lbs"] = goals["weight_lbs"]
            response_goals["height_inches"] = goals["height_inches"]
        else:
            # Return default goals based on accessible fields
            response_goals["daily_calories"] = 2000
            response_goals["calories_type"] = "goal"
            response_goals["daily_protein"] = 150
            response_goals["protein_type"] = "goal"
            response_goals["daily_fat"] = 70
            response_goals["fat_type"] = "goal"
            
            if accessible_fields["carbs"]:
                response_goals["daily_carbs"] = 250
                response_goals["carbs_type"] = "goal"
            
            if accessible_fields["fiber"]:
                response_goals["daily_fiber"] = 25
                response_goals["fiber_type"] = "goal"
            
            if accessible_fields["sodium"]:
                response_goals["daily_sodium"] = 2300
                response_goals["sodium_type"] = "limit"
            
            response_goals["goal_type"] = "maintenance"
            response_goals["activity_level"] = "moderately_active"
            response_goals["age"] = None
            response_goals["gender"] = None
            response_goals["weight_lbs"] = None
            response_goals["height_inches"] = None

        return jsonify({
            "success": True,
            "goals": response_goals
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get nutrition goals: {str(e)}"})
    finally:
        cursor.close()


@nutrition_bp.route("/nutrition/goals", methods=["POST"])
def save_nutrition_goals():
    """Save or update user's nutrition goals and preferences"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()
    print(f"Received data from frontend: {data}")
    accessible_fields = get_accessible_nutrition_fields(user_id)

    # Check premium field access for free users
    premium_fields = ["daily_carbs", "daily_fiber", "daily_sodium"]
    for field in premium_fields:
        field_name = field.replace("daily_", "")
        if field in data and not accessible_fields[field_name]:
            return jsonify({
                "success": False, 
                "message": f"Premium subscription required to set {field_name} goals",
                "requires_upgrade": True,
                "premium_field": field_name
            })

    # Build required fields list based on accessible fields
    required_fields = ["daily_calories", "daily_protein", "daily_fat"]
    if accessible_fields["carbs"]:
        required_fields.append("daily_carbs")
    if accessible_fields["fiber"]:
        required_fields.append("daily_fiber")
    if accessible_fields["sodium"]:
        required_fields.append("daily_sodium")
    
    # Validate required fields
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"})

    try:
        # Extract values and types for accessible fields only
        daily_calories = float(data["daily_calories"])
        calories_type = data.get("calories_type", "goal")
        daily_protein = float(data["daily_protein"])
        protein_type = data.get("protein_type", "goal")
        daily_fat = float(data["daily_fat"])
        fat_type = data.get("fat_type", "goal")
        
        # Only extract premium fields if accessible
        daily_carbs = float(data["daily_carbs"]) if accessible_fields["carbs"] and "daily_carbs" in data else None
        carbs_type = data.get("carbs_type", "goal") if accessible_fields["carbs"] else None
        daily_fiber = float(data["daily_fiber"]) if accessible_fields["fiber"] and "daily_fiber" in data else None
        fiber_type = data.get("fiber_type", "goal") if accessible_fields["fiber"] else None
        daily_sodium = float(data["daily_sodium"]) if accessible_fields["sodium"] and "daily_sodium" in data else None
        sodium_type = data.get("sodium_type", "limit") if accessible_fields["sodium"] else None
        
        print(f"Extracted types - calories: {calories_type}, protein: {protein_type}, carbs: {carbs_type}, fat: {fat_type}, fiber: {fiber_type}, sodium: {sodium_type}")
        
        goal_type = data.get("goal_type", "custom")
        activity_level = data.get("activity_level", "moderately_active")
        age = data.get("age")
        gender = data.get("gender")
        weight_lbs = data.get("weight_lbs")
        height_inches = data.get("height_inches")

        # Validate goal/limit types for accessible fields
        valid_types = ["goal", "limit"]
        type_fields = [calories_type, protein_type, fat_type]
        if accessible_fields["carbs"] and carbs_type:
            type_fields.append(carbs_type)
        if accessible_fields["fiber"] and fiber_type:
            type_fields.append(fiber_type)
        if accessible_fields["sodium"] and sodium_type:
            type_fields.append(sodium_type)
        
        if not all(t in valid_types for t in type_fields):
            return jsonify({"success": False, "message": "Invalid goal/limit type specified"})

        # Validate ranges for accessible fields
        if not (1200 <= daily_calories <= 5000):
            return jsonify({"success": False, "message": "Daily calories must be between 1200 and 5000"})
        if not (50 <= daily_protein <= 300):
            return jsonify({"success": False, "message": "Daily protein must be between 50g and 300g"})
        if not (20 <= daily_fat <= 150):
            return jsonify({"success": False, "message": "Daily fat must be between 20g and 150g"})
        
        # Validate premium fields only if accessible and provided
        if accessible_fields["carbs"] and daily_carbs is not None:
            if not (50 <= daily_carbs <= 500):
                return jsonify({"success": False, "message": "Daily carbs must be between 50g and 500g"})
        if accessible_fields["fiber"] and daily_fiber is not None:
            if not (15 <= daily_fiber <= 50):
                return jsonify({"success": False, "message": "Daily fiber must be between 15g and 50g"})
        if accessible_fields["sodium"] and daily_sodium is not None:
            if not (1500 <= daily_sodium <= 4000):
                return jsonify({"success": False, "message": "Daily sodium must be between 1500mg and 4000mg"})

    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid data types for nutrition values"})

    db = get_db()
    cursor = db.cursor()

    try:
        print(f"Starting database operations for user {user_id}")
        
        # First, deactivate any existing goals
        deactivate_query = """
            UPDATE user_nutrition_goals 
            SET is_active = FALSE 
            WHERE user_id = %s
        """
        cursor.execute(deactivate_query, (user_id,))
        print(f"Deactivated existing goals for user {user_id}")
        
        # Insert new goals (use default values for inaccessible fields)
        insert_query = """
            INSERT INTO user_nutrition_goals 
            (user_id, daily_calories_goal, calories_type,
             daily_protein_goal_g, protein_type,
             daily_carbs_goal_g, carbs_type,
             daily_fat_goal_g, fat_type,
             daily_fiber_goal_g, fiber_type,
             daily_sodium_limit_mg, sodium_type,
             goal_type, activity_level,
             age, gender, weight_lbs, height_inches)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Use sensible defaults for inaccessible fields to maintain database integrity
        carbs_value = daily_carbs if daily_carbs is not None else 250
        carbs_type_value = carbs_type if carbs_type is not None else "goal"
        fiber_value = daily_fiber if daily_fiber is not None else 25
        fiber_type_value = fiber_type if fiber_type is not None else "goal"
        sodium_value = daily_sodium if daily_sodium is not None else 2300
        sodium_type_value = sodium_type if sodium_type is not None else "limit"
        
        print(f"About to insert: calories={daily_calories}/{calories_type}, protein={daily_protein}/{protein_type}, carbs={carbs_value}/{carbs_type_value}, fat={daily_fat}/{fat_type}, fiber={fiber_value}/{fiber_type_value}, sodium={sodium_value}/{sodium_type_value}")
        
        cursor.execute(insert_query, (
            user_id, daily_calories, calories_type,
            daily_protein, protein_type,
            carbs_value, carbs_type_value,
            daily_fat, fat_type,
            fiber_value, fiber_type_value,
            sodium_value, sodium_type_value,
            goal_type, activity_level,
            age, gender, weight_lbs, height_inches
        ))
        
        print("Insert query executed successfully")
        db.commit()
        print("Database committed successfully")
        
        # Build response with only accessible fields
        response_goals = {
            "daily_calories": daily_calories,
            "calories_type": calories_type,
            "daily_protein": daily_protein,
            "protein_type": protein_type,
            "daily_fat": daily_fat,
            "fat_type": fat_type,
            "goal_type": goal_type,
            "activity_level": activity_level
        }
        
        # Include premium fields only if accessible
        if accessible_fields["carbs"] and daily_carbs is not None:
            response_goals["daily_carbs"] = daily_carbs
            response_goals["carbs_type"] = carbs_type
        if accessible_fields["fiber"] and daily_fiber is not None:
            response_goals["daily_fiber"] = daily_fiber
            response_goals["fiber_type"] = fiber_type
        if accessible_fields["sodium"] and daily_sodium is not None:
            response_goals["daily_sodium"] = daily_sodium
            response_goals["sodium_type"] = sodium_type
            
        print(response_goals)
        
        return jsonify({
            "success": True,
            "message": "Nutrition goals saved successfully",
            "goals": response_goals
        })

    except Exception as e:
        print(f"Database error occurred: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to save nutrition goals: {str(e)}"})
    finally:
        cursor.close()



@nutrition_bp.route("/nutrition/stats", methods=["GET"])
def get_nutrition_stats():
    """Get nutrition statistics and daily summaries"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    
    # This would be implemented when nutrition tracking is fully built out
    # For now, return placeholder data
    return jsonify({
        "success": True,
        "stats": {
            "calories_today": 1650,
            "protein_today": 120,
            "carbs_today": 180,
            "fat_today": 55,
            "fiber_today": 20,
            "sodium_today": 1800,
            "goal_progress": 85
        }
    })