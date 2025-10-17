from flask import Blueprint, request, jsonify, session
from src.database import get_db
from datetime import datetime, timedelta

meal_goals_bp = Blueprint("meal_goals", __name__, url_prefix="/api")


@meal_goals_bp.route("/meal-goals", methods=["GET"])
def get_meal_goals():
    """Get meal goals for a specific month/year"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    month = request.args.get("month", datetime.now().month)
    year = request.args.get("year", datetime.now().year)

    try:
        month = int(month)
        year = int(year)
        
        if not (1 <= month <= 12):
            return jsonify({"success": False, "message": "Invalid month"})
        if not (2020 <= year <= 2030):
            return jsonify({"success": False, "message": "Invalid year"})
            
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid month or year format"})

    db = get_db()
    cursor = db.cursor()

    try:
        query = """
            SELECT meal_plans_goal, meals_completed_goal, new_recipes_goal, 
                   created_at, updated_at
            FROM monthly_meal_goals 
            WHERE user_id = %s AND month = %s AND year = %s
        """
        cursor.execute(query, (user_id, month, year))
        goals = cursor.fetchone()

        if goals:
            return jsonify({
                "success": True,
                "goals": {
                    "meal_plans_goal": goals["meal_plans_goal"],
                    "meals_completed_goal": goals["meals_completed_goal"],
                    "new_recipes_goal": goals["new_recipes_goal"],
                    "month": month,
                    "year": year,
                    "created_at": goals["created_at"].isoformat() if goals["created_at"] else None,
                    "updated_at": goals["updated_at"].isoformat() if goals["updated_at"] else None
                }
            })
        else:
            # Return default goals if none exist
            return jsonify({
                "success": True,
                "goals": {
                    "meal_plans_goal": 4,
                    "meals_completed_goal": 60,
                    "new_recipes_goal": 12,
                    "month": month,
                    "year": year,
                    "created_at": None,
                    "updated_at": None
                }
            })

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get meal goals: {str(e)}"})
    finally:
        cursor.close()


@meal_goals_bp.route("/meal-goals", methods=["POST", "PUT"])
def save_meal_goals():
    """Save or update meal goals for a specific month/year"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    data = request.get_json()

    # Validate required fields
    required_fields = ["month", "year", "meal_plans_goal", "meals_completed_goal", "new_recipes_goal"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"})

    try:
        month = int(data["month"])
        year = int(data["year"])
        meal_plans_goal = int(data["meal_plans_goal"])
        meals_completed_goal = int(data["meals_completed_goal"])
        new_recipes_goal = int(data["new_recipes_goal"])

        # Validate ranges
        if not (1 <= month <= 12):
            return jsonify({"success": False, "message": "Month must be between 1 and 12"})
        if not (2020 <= year <= 2030):
            return jsonify({"success": False, "message": "Year must be between 2020 and 2030"})
        if not (1 <= meal_plans_goal <= 20):
            return jsonify({"success": False, "message": "Meal plans goal must be between 1 and 20"})
        if not (10 <= meals_completed_goal <= 200):
            return jsonify({"success": False, "message": "Meals completed goal must be between 10 and 200"})
        if not (1 <= new_recipes_goal <= 50):
            return jsonify({"success": False, "message": "New recipes goal must be between 1 and 50"})

    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid data types for goal values"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert functionality
        upsert_query = """
            INSERT INTO monthly_meal_goals 
            (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                meal_plans_goal = VALUES(meal_plans_goal),
                meals_completed_goal = VALUES(meals_completed_goal),
                new_recipes_goal = VALUES(new_recipes_goal),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(upsert_query, (
            user_id, month, year, meal_plans_goal, 
            meals_completed_goal, new_recipes_goal
        ))
        
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Meal goals saved successfully",
            "goals": {
                "meal_plans_goal": meal_plans_goal,
                "meals_completed_goal": meals_completed_goal,
                "new_recipes_goal": new_recipes_goal,
                "month": month,
                "year": year
            }
        })

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to save meal goals: {str(e)}"})
    finally:
        cursor.close()


@meal_goals_bp.route("/meal-goals/progress", methods=["GET"])
def get_goals_progress():
    """Get current progress towards meal goals for a specific month"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    month = request.args.get("month", datetime.now().month)
    year = request.args.get("year", datetime.now().year)

    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid month or year format"})

    db = get_db()
    cursor = db.cursor()

    try:
        # Get the start and end dates for the month
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        # Get meal plans created this month
        meal_plans_query = """
            SELECT COUNT(*) as plan_count
            FROM meal_plan_sessions
            WHERE user_id = %s 
            AND generated_at >= %s 
            AND generated_at < %s
        """
        cursor.execute(meal_plans_query, (user_id, start_date, end_date))
        meal_plans_result = cursor.fetchone()
        meal_plans_count = meal_plans_result["plan_count"] if meal_plans_result else 0

        # Get completed meals this month
        completed_meals_query = """
            SELECT COUNT(*) as completed_count
            FROM meals
            WHERE user_id = %s 
            AND is_completed = TRUE
            AND meal_date >= %s 
            AND meal_date < %s
        """
        cursor.execute(completed_meals_query, (user_id, start_date, end_date))
        completed_meals_result = cursor.fetchone()
        completed_meals_count = completed_meals_result["completed_count"] if completed_meals_result else 0

        # For new recipes, we'll count unique recipe templates used this month
        new_recipes_query = """
            SELECT COUNT(DISTINCT m.recipe_template_id) as unique_recipes
            FROM meals m
            WHERE m.user_id = %s 
            AND m.recipe_template_id IS NOT NULL
            AND m.meal_date >= %s 
            AND m.meal_date < %s
        """
        cursor.execute(new_recipes_query, (user_id, start_date, end_date))
        new_recipes_result = cursor.fetchone()
        new_recipes_count = new_recipes_result["unique_recipes"] if new_recipes_result else 0


        return jsonify({
            "success": True,
            "progress": {
                "meal_plans_count": meal_plans_count,
                "completed_meals_count": completed_meals_count,
                "new_recipes_count": new_recipes_count,
                "month": month,
                "year": year
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to get goals progress: {str(e)}"})
    finally:
        cursor.close()


@meal_goals_bp.route("/meal-goals", methods=["DELETE"])
def delete_meal_goals():
    """Delete meal goals for a specific month/year"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    month = request.args.get("month", datetime.now().month)
    year = request.args.get("year", datetime.now().year)

    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid month or year format"})

    db = get_db()
    cursor = db.cursor()

    try:
        delete_query = """
            DELETE FROM monthly_meal_goals 
            WHERE user_id = %s AND month = %s AND year = %s
        """
        cursor.execute(delete_query, (user_id, month, year))
        db.commit()

        if cursor.rowcount > 0:
            return jsonify({"success": True, "message": "Meal goals deleted successfully"})
        else:
            return jsonify({"success": False, "message": "No goals found for the specified month/year"})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to delete meal goals: {str(e)}"})
    finally:
        cursor.close()


# ============================================================================
# WEEKLY MEAL GOALS API ENDPOINTS
# ============================================================================

def get_week_start_date(date_obj):
    """Get the Monday of the week for a given date"""
    days_since_monday = date_obj.weekday()
    week_start = date_obj - timedelta(days=days_since_monday)
    return week_start


@meal_goals_bp.route("/meal-goals/weekly", methods=["GET"])
def get_weekly_meal_goals():
    """Get meal goals for the current week"""
    print("GET /api/meal-goals/weekly called")
    
    if "user_ID" not in session:
        print("User not authenticated")
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    print(f"User ID: {user_id}")
    
    # Get current week start (Monday)
    current_date = datetime.now().date()
    week_start = get_week_start_date(current_date)
    print(f"Week start: {week_start}")

    db = get_db()
    cursor = db.cursor()

    try:
        query = """
            SELECT meal_plans_goal, meals_completed_goal, new_recipes_goal, 
                   week_start_date, created_at, updated_at
            FROM weekly_meal_goals 
            WHERE user_id = %s AND week_start_date = %s
        """
        print(f"Executing query with user_id={user_id}, week_start={week_start}")
        cursor.execute(query, (user_id, week_start))
        goals = cursor.fetchone()
        print(f"Query result: {goals}")

        if goals:
            result = {
                "success": True,
                "goals": {
                    "meal_plans_goal": goals["meal_plans_goal"],
                    "meals_completed_goal": goals["meals_completed_goal"],
                    "new_recipes_goal": goals["new_recipes_goal"],
                    "week_start_date": goals["week_start_date"].isoformat(),
                    "created_at": goals["created_at"].isoformat() if goals["created_at"] else None,
                    "updated_at": goals["updated_at"].isoformat() if goals["updated_at"] else None
                }
            }
            print(f"Returning existing goals: {result}")
            return jsonify(result)
        else:
            # Return default weekly goals if none exist
            result = {
                "success": True,
                "goals": {
                    "meal_plans_goal": 2,
                    "meals_completed_goal": 15,
                    "new_recipes_goal": 3,
                    "week_start_date": week_start.isoformat(),
                    "created_at": None,
                    "updated_at": None
                }
            }
            print(f"Returning default goals: {result}")
            return jsonify(result)

    except Exception as e:
        print(f"Error in get_weekly_meal_goals: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to get weekly meal goals: {str(e)}"})
    finally:
        cursor.close()


@meal_goals_bp.route("/meal-goals/weekly", methods=["POST", "PUT"])
def save_weekly_meal_goals():
    """Save or update weekly meal goals"""
    print("POST /api/meal-goals/weekly called")
    
    if "user_ID" not in session:
        print("User not authenticated")
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    print(f"User ID: {user_id}")
    
    data = request.get_json()
    print(f"Request data: {data}")

    # Validate required fields
    required_fields = ["meal_plans_goal", "meals_completed_goal", "new_recipes_goal"]
    for field in required_fields:
        if field not in data:
            print(f"Missing field: {field}")
            return jsonify({"success": False, "message": f"Missing required field: {field}"})

    try:
        meal_plans_goal = int(data["meal_plans_goal"])
        meals_completed_goal = int(data["meals_completed_goal"])
        new_recipes_goal = int(data["new_recipes_goal"])
        print(f"Parsed goals: plans={meal_plans_goal}, meals={meals_completed_goal}, recipes={new_recipes_goal}")

        # Validate ranges for weekly goals
        if not (1 <= meal_plans_goal <= 10):
            return jsonify({"success": False, "message": "Meal plans goal must be between 1 and 10"})
        if not (5 <= meals_completed_goal <= 50):
            return jsonify({"success": False, "message": "Meals completed goal must be between 5 and 50"})
        if not (1 <= new_recipes_goal <= 15):
            return jsonify({"success": False, "message": "New recipes goal must be between 1 and 15"})

    except (ValueError, TypeError) as e:
        print(f"Data parsing error: {e}")
        return jsonify({"success": False, "message": "Invalid data types for goal values"})

    # Get current week start
    current_date = datetime.now().date()
    week_start = get_week_start_date(current_date)
    print(f"Week start: {week_start}")

    db = get_db()
    cursor = db.cursor()

    try:
        # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert functionality
        upsert_query = """
            INSERT INTO weekly_meal_goals 
            (user_id, week_start_date, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                meal_plans_goal = VALUES(meal_plans_goal),
                meals_completed_goal = VALUES(meals_completed_goal),
                new_recipes_goal = VALUES(new_recipes_goal),
                updated_at = CURRENT_TIMESTAMP
        """
        
        print(f"Executing upsert with: user_id={user_id}, week_start={week_start}")
        cursor.execute(upsert_query, (
            user_id, week_start, meal_plans_goal, 
            meals_completed_goal, new_recipes_goal
        ))
        
        db.commit()
        print("Database commit successful")
        
        result = {
            "success": True,
            "message": "Weekly meal goals saved successfully",
            "goals": {
                "meal_plans_goal": meal_plans_goal,
                "meals_completed_goal": meals_completed_goal,
                "new_recipes_goal": new_recipes_goal,
                "week_start_date": week_start.isoformat()
            }
        }
        print(f"Returning result: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"Database error: {str(e)}")
        db.rollback()
        return jsonify({"success": False, "message": f"Failed to save weekly meal goals: {str(e)}"})
    finally:
        cursor.close()


@meal_goals_bp.route("/meal-goals/progress/weekly", methods=["GET"])
def get_weekly_goals_progress():
    """Get current progress towards weekly meal goals"""
    print("GET /api/meal-goals/progress/weekly called")
    
    if "user_ID" not in session:
        print("User not authenticated")
        return jsonify({"success": False, "message": "Not authenticated"})

    user_id = session["user_ID"]
    print(f"User ID: {user_id}")
    
    # Get date range from query params or use current week
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    print(f"Date params: start={start_date_str}, end={end_date_str}")
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"})
    else:
        # Use current week
        current_date = datetime.now().date()
        start_date = get_week_start_date(current_date)
        end_date = start_date + timedelta(days=6)
    
    print(f"Using date range: {start_date} to {end_date}")

    db = get_db()
    cursor = db.cursor()

    try:
        # Get meal plans created this week
        meal_plans_query = """
            SELECT COUNT(*) as plan_count
            FROM meal_plan_sessions
            WHERE user_id = %s 
            AND DATE(generated_at) >= %s 
            AND DATE(generated_at) <= %s
        """
        cursor.execute(meal_plans_query, (user_id, start_date, end_date))
        meal_plans_result = cursor.fetchone()
        meal_plans_count = meal_plans_result["plan_count"] if meal_plans_result else 0
        print(f"Meal plans count: {meal_plans_count}")

        # Get completed meals this week
        completed_meals_query = """
            SELECT COUNT(*) as completed_count
            FROM meals
            WHERE user_id = %s 
            AND is_completed = TRUE
            AND meal_date >= %s 
            AND meal_date <= %s
        """
        cursor.execute(completed_meals_query, (user_id, start_date, end_date))
        completed_meals_result = cursor.fetchone()
        completed_meals_count = completed_meals_result["completed_count"] if completed_meals_result else 0
        print(f"Completed meals count: {completed_meals_count}")

        # For new recipes, count unique recipe templates used this week
        new_recipes_query = """
            SELECT COUNT(DISTINCT m.recipe_template_id) as unique_recipes
            FROM meals m
            WHERE m.user_id = %s 
            AND m.recipe_template_id IS NOT NULL
            AND m.meal_date >= %s 
            AND m.meal_date <= %s
        """
        cursor.execute(new_recipes_query, (user_id, start_date, end_date))
        new_recipes_result = cursor.fetchone()
        new_recipes_count = new_recipes_result["unique_recipes"] if new_recipes_result else 0
        print(f"New recipes count: {new_recipes_count}")

        result = {
            "success": True,
            "progress": {
                "meal_plans_count": meal_plans_count,
                "completed_meals_count": completed_meals_count,
                "new_recipes_count": new_recipes_count,
                "week_start_date": start_date.isoformat(),
                "week_end_date": end_date.isoformat()
            }
        }
        print(f"Returning progress result: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"Error in get_weekly_goals_progress: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to get weekly goals progress: {str(e)}"})
    finally:
        cursor.close()