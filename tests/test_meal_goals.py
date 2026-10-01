"""
Comprehensive tests for meal goals API endpoints.
Tests monthly and weekly meal goal management including progress tracking.
"""

import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

@pytest.mark.api
@pytest.mark.meal_planning
class TestGetMealGoals:
    """Test getting monthly meal goals."""
    
    def test_get_meal_goals_success(self, client, logged_in_user, test_db):
        """Test successfully getting existing meal goals."""
        cursor = test_db.cursor()
        
        # Create meal goals for current month
        current_date = datetime.now()
        cursor.execute("""
            INSERT INTO monthly_meal_goals 
            (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, current_date.month, current_date.year, 5, 80, 15))
        
        response = client.get(f"/api/meal-goals?month={current_date.month}&year={current_date.year}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        goals = data["goals"]
        assert goals["meal_plans_goal"] == 5
        assert goals["meals_completed_goal"] == 80
        assert goals["new_recipes_goal"] == 15
        assert goals["month"] == current_date.month
        assert goals["year"] == current_date.year
        assert goals["created_at"] is not None
        assert goals["updated_at"] is not None
    
    def test_get_meal_goals_default_values(self, client, logged_in_user):
        """Test getting default goals when none exist."""
        future_date = datetime.now() + timedelta(days=365)
        
        response = client.get(f"/api/meal-goals?month={future_date.month}&year={future_date.year}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        goals = data["goals"]
        assert goals["meal_plans_goal"] == 4  # Default value
        assert goals["meals_completed_goal"] == 60  # Default value
        assert goals["new_recipes_goal"] == 12  # Default value
        assert goals["created_at"] is None
        assert goals["updated_at"] is None
    
    def test_get_meal_goals_current_month_default(self, client, logged_in_user):
        """Test getting goals without specifying month/year uses current month."""
        response = client.get("/api/meal-goals")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        current_date = datetime.now()
        goals = data["goals"]
        assert goals["month"] == current_date.month
        assert goals["year"] == current_date.year
    
    def test_get_meal_goals_invalid_month(self, client, logged_in_user):
        """Test getting goals with invalid month."""
        response = client.get("/api/meal-goals?month=13&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid month" in data["message"]
        
        # Test month 0
        response = client.get("/api/meal-goals?month=0&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid month" in data["message"]
    
    def test_get_meal_goals_invalid_year(self, client, logged_in_user):
        """Test getting goals with invalid year."""
        response = client.get("/api/meal-goals?month=6&year=2019")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid year" in data["message"]
        
        # Test year too far in future
        response = client.get("/api/meal-goals?month=6&year=2031")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid year" in data["message"]
    
    def test_get_meal_goals_invalid_format(self, client, logged_in_user):
        """Test getting goals with invalid month/year format."""
        response = client.get("/api/meal-goals?month=abc&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid month or year format" in data["message"]
    
    def test_get_meal_goals_not_authenticated(self, client):
        """Test getting goals when not authenticated."""
        response = client.get("/api/meal-goals")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_get_meal_goals_database_error(self, client, logged_in_user):
        """Test handling database errors."""
        with patch('src.backend.apis.meal_goals.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/meal-goals")
            assert response.status_code == 200
            
            data = response.get_json()
            assert data["success"] is False
            assert "Failed to get meal goals" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestSaveMealGoals:
    """Test saving/updating meal goals."""
    
    def test_save_meal_goals_new_success(self, client, logged_in_user, test_db):
        """Test successfully saving new meal goals."""
        cursor = test_db.cursor()
        
        goals_data = {
            "month": 6,
            "year": 2024,
            "meal_plans_goal": 8,
            "meals_completed_goal": 120,
            "new_recipes_goal": 20
        }
        
        response = client.post("/api/meal-goals", json=goals_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert "saved successfully" in data["message"]
        
        returned_goals = data["goals"]
        assert returned_goals["meal_plans_goal"] == 8
        assert returned_goals["meals_completed_goal"] == 120
        assert returned_goals["new_recipes_goal"] == 20
        
        # Verify in database
        cursor.execute("""
            SELECT * FROM monthly_meal_goals 
            WHERE user_id = %s AND month = %s AND year = %s
        """, (logged_in_user, 6, 2024))
        db_result = cursor.fetchone()
        
        assert db_result["meal_plans_goal"] == 8
        assert db_result["meals_completed_goal"] == 120
        assert db_result["new_recipes_goal"] == 20
    
    def test_save_meal_goals_update_existing(self, client, logged_in_user, test_db):
        """Test updating existing meal goals."""
        cursor = test_db.cursor()
        
        # Create existing goals
        cursor.execute("""
            INSERT INTO monthly_meal_goals 
            (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, 7, 2024, 5, 60, 10))
        
        # Update goals
        updated_goals = {
            "month": 7,
            "year": 2024,
            "meal_plans_goal": 10,
            "meals_completed_goal": 100,
            "new_recipes_goal": 25
        }
        
        response = client.post("/api/meal-goals", json=updated_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Verify updated values in database
        cursor.execute("""
            SELECT * FROM monthly_meal_goals 
            WHERE user_id = %s AND month = %s AND year = %s
        """, (logged_in_user, 7, 2024))
        db_result = cursor.fetchone()
        
        assert db_result["meal_plans_goal"] == 10
        assert db_result["meals_completed_goal"] == 100
        assert db_result["new_recipes_goal"] == 25
    
    def test_save_meal_goals_put_method(self, client, logged_in_user):
        """Test saving goals using PUT method."""
        goals_data = {
            "month": 8,
            "year": 2024,
            "meal_plans_goal": 6,
            "meals_completed_goal": 90,
            "new_recipes_goal": 18
        }
        
        response = client.put("/api/meal-goals", json=goals_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
    
    def test_save_meal_goals_missing_fields(self, client, logged_in_user):
        """Test saving goals with missing required fields."""
        incomplete_data = {
            "month": 6,
            "year": 2024,
            "meal_plans_goal": 5
            # Missing meals_completed_goal and new_recipes_goal
        }
        
        response = client.post("/api/meal-goals", json=incomplete_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Missing required field" in data["message"]
    
    def test_save_meal_goals_invalid_ranges(self, client, logged_in_user):
        """Test saving goals with values outside valid ranges."""
        # Test meal plans goal too high
        invalid_goals = {
            "month": 6,
            "year": 2024,
            "meal_plans_goal": 25,  # Max is 20
            "meals_completed_goal": 100,
            "new_recipes_goal": 15
        }
        
        response = client.post("/api/meal-goals", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 1 and 20" in data["message"]
        
        # Test meals completed goal too low
        invalid_goals["meal_plans_goal"] = 5
        invalid_goals["meals_completed_goal"] = 5  # Min is 10
        
        response = client.post("/api/meal-goals", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 10 and 200" in data["message"]
        
        # Test new recipes goal too high
        invalid_goals["meals_completed_goal"] = 100
        invalid_goals["new_recipes_goal"] = 60  # Max is 50
        
        response = client.post("/api/meal-goals", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 1 and 50" in data["message"]
    
    def test_save_meal_goals_invalid_data_types(self, client, logged_in_user):
        """Test saving goals with invalid data types."""
        invalid_data = {
            "month": "june",  # Should be int
            "year": 2024,
            "meal_plans_goal": 5,
            "meals_completed_goal": 100,
            "new_recipes_goal": 15
        }
        
        response = client.post("/api/meal-goals", json=invalid_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid data types" in data["message"]
    
    def test_save_meal_goals_not_authenticated(self, client):
        """Test saving goals when not authenticated."""
        goals_data = {
            "month": 6,
            "year": 2024,
            "meal_plans_goal": 5,
            "meals_completed_goal": 100,
            "new_recipes_goal": 15
        }
        
        response = client.post("/api/meal-goals", json=goals_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestGetGoalsProgress:
    """Test getting progress towards meal goals."""
    
    def test_get_goals_progress_success(self, client, logged_in_user, test_db):
        """Test successfully getting goals progress."""
        cursor = test_db.cursor()
        
        # Create test data for current month
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1)
        
        # Create meal plan sessions
        cursor.execute("""
            INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s), (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Plan 1", "2024-01-15", "2024-01-21", 7, start_of_month,
              logged_in_user, "Plan 2", "2024-01-22", "2024-01-28", 7, start_of_month + timedelta(days=5)))
        
        # Create completed meals
        for i in range(8):  # 8 completed meals
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, is_completed)
                VALUES (%s, %s, %s, %s)
            """, (logged_in_user, start_of_month + timedelta(days=i), "breakfast", True))
        
        # Create recipe templates and meals with templates (for unique recipes count)
        cursor.execute("""
            INSERT INTO recipe_templates (recipe_name, description, meal_type, instructions)
            VALUES (%s, %s, 'dinner', 'Cook it'), (%s, %s, 'dinner', 'Cook it'), (%s, %s, 'dinner', 'Cook it')
        """, ("Recipe 1", "Test recipe 1", "Recipe 2", "Test recipe 2", "Recipe 3", "Test recipe 3"))
        
        template_ids = []
        cursor.execute("SELECT template_id FROM recipe_templates ORDER BY template_id DESC LIMIT 3")
        template_ids = [row["template_id"] for row in cursor.fetchall()]
        
        # Create meals with different recipe templates
        for i, template_id in enumerate(template_ids):
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, recipe_template_id)
                VALUES (%s, %s, %s, %s)
            """, (logged_in_user, start_of_month + timedelta(days=i), "dinner", template_id))
        
        response = client.get(f"/api/meal-goals/progress?month={current_date.month}&year={current_date.year}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        progress = data["progress"]
        assert progress["meal_plans_count"] == 2
        assert progress["completed_meals_count"] == 8
        assert progress["new_recipes_count"] == 3
        assert progress["month"] == current_date.month
        assert progress["year"] == current_date.year
    
    def test_get_goals_progress_empty_data(self, client, logged_in_user):
        """Test getting progress with no data."""
        # Use future month with no data
        future_date = datetime.now() + timedelta(days=365)
        
        response = client.get(f"/api/meal-goals/progress?month={future_date.month}&year={future_date.year}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        progress = data["progress"]
        assert progress["meal_plans_count"] == 0
        assert progress["completed_meals_count"] == 0
        assert progress["new_recipes_count"] == 0
    
    def test_get_goals_progress_current_month_default(self, client, logged_in_user):
        """Test getting progress defaults to current month."""
        response = client.get("/api/meal-goals/progress")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        current_date = datetime.now()
        progress = data["progress"]
        assert progress["month"] == current_date.month
        assert progress["year"] == current_date.year
    
    def test_get_goals_progress_invalid_format(self, client, logged_in_user):
        """Test getting progress with invalid month/year format."""
        response = client.get("/api/meal-goals/progress?month=invalid&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid month or year format" in data["message"]
    
    def test_get_goals_progress_not_authenticated(self, client):
        """Test getting progress when not authenticated."""
        response = client.get("/api/meal-goals/progress")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_get_goals_progress_date_calculation(self, client, logged_in_user, test_db):
        """Test correct date range calculation for different months."""
        cursor = test_db.cursor()
        
        # Test December (edge case for next year calculation)
        cursor.execute("""
            INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "December Plan", "2023-12-15", "2023-12-21", 7, "2023-12-01"))
        
        response = client.get("/api/meal-goals/progress?month=12&year=2023")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        progress = data["progress"]
        assert progress["meal_plans_count"] == 1


@pytest.mark.api
@pytest.mark.meal_planning
class TestDeleteMealGoals:
    """Test deleting meal goals."""
    
    def test_delete_meal_goals_success(self, client, logged_in_user, test_db):
        """Test successfully deleting meal goals."""
        cursor = test_db.cursor()
        
        # Create meal goals
        cursor.execute("""
            INSERT INTO monthly_meal_goals 
            (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, 9, 2024, 6, 90, 18))
        
        response = client.delete("/api/meal-goals?month=9&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
        
        # Verify deleted from database
        cursor.execute("""
            SELECT * FROM monthly_meal_goals 
            WHERE user_id = %s AND month = %s AND year = %s
        """, (logged_in_user, 9, 2024))
        result = cursor.fetchone()
        assert result is None
    
    def test_delete_meal_goals_not_found(self, client, logged_in_user):
        """Test deleting non-existent meal goals."""
        response = client.delete("/api/meal-goals?month=10&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "No goals found" in data["message"]
    
    def test_delete_meal_goals_current_month_default(self, client, logged_in_user):
        """Test deleting goals defaults to current month."""
        response = client.delete("/api/meal-goals")
        assert response.status_code == 200
        
        # Should work even if no goals exist
        data = response.get_json()
        assert data["success"] is False  # No goals to delete
        assert "No goals found" in data["message"]
    
    def test_delete_meal_goals_invalid_format(self, client, logged_in_user):
        """Test deleting goals with invalid month/year format."""
        response = client.delete("/api/meal-goals?month=invalid&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid month or year format" in data["message"]
    
    def test_delete_meal_goals_not_authenticated(self, client):
        """Test deleting goals when not authenticated."""
        response = client.delete("/api/meal-goals?month=9&year=2024")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestWeeklyMealGoals:
    """Test weekly meal goals functionality."""
    
    def test_get_week_start_date_function(self):
        """Test the week start date calculation function."""
        from src.backend.apis.meal_goals import get_week_start_date
        
        # Test Monday (should return same date)
        monday = date(2024, 1, 15)  # This is a Monday
        assert get_week_start_date(monday) == monday
        
        # Test Wednesday (should return previous Monday)
        wednesday = date(2024, 1, 17)
        expected_monday = date(2024, 1, 15)
        assert get_week_start_date(wednesday) == expected_monday
        
        # Test Sunday (should return previous Monday)
        sunday = date(2024, 1, 21)
        expected_monday = date(2024, 1, 15)
        assert get_week_start_date(sunday) == expected_monday
    
    def test_get_weekly_meal_goals_success(self, client, logged_in_user, test_db):
        """Test successfully getting weekly meal goals."""
        cursor = test_db.cursor()
        
        # Calculate current week start
        current_date = datetime.now().date()
        days_since_monday = current_date.weekday()
        week_start = current_date - timedelta(days=days_since_monday)
        
        # Create weekly goals
        cursor.execute("""
            INSERT INTO weekly_meal_goals 
            (user_id, week_start_date, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, week_start, 3, 25, 5))
        
        response = client.get("/api/meal-goals/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        goals = data["goals"]
        assert goals["meal_plans_goal"] == 3
        assert goals["meals_completed_goal"] == 25
        assert goals["new_recipes_goal"] == 5
        assert goals["week_start_date"] == week_start.isoformat()
        assert goals["created_at"] is not None
    
    def test_get_weekly_meal_goals_default_values(self, client, logged_in_user):
        """Test getting default weekly goals when none exist."""
        response = client.get("/api/meal-goals/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        goals = data["goals"]
        assert goals["meal_plans_goal"] == 2  # Default weekly value
        assert goals["meals_completed_goal"] == 15  # Default weekly value
        assert goals["new_recipes_goal"] == 3  # Default weekly value
        assert goals["created_at"] is None
        assert goals["updated_at"] is None
    
    def test_save_weekly_meal_goals_success(self, client, logged_in_user, test_db):
        """Test successfully saving weekly meal goals."""
        cursor = test_db.cursor()
        
        goals_data = {
            "meal_plans_goal": 4,
            "meals_completed_goal": 20,
            "new_recipes_goal": 6
        }
        
        response = client.post("/api/meal-goals/weekly", json=goals_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert "saved successfully" in data["message"]
        
        returned_goals = data["goals"]
        assert returned_goals["meal_plans_goal"] == 4
        assert returned_goals["meals_completed_goal"] == 20
        assert returned_goals["new_recipes_goal"] == 6
        
        # Verify in database
        current_date = datetime.now().date()
        days_since_monday = current_date.weekday()
        week_start = current_date - timedelta(days=days_since_monday)
        
        cursor.execute("""
            SELECT * FROM weekly_meal_goals 
            WHERE user_id = %s AND week_start_date = %s
        """, (logged_in_user, week_start))
        db_result = cursor.fetchone()
        
        assert db_result["meal_plans_goal"] == 4
        assert db_result["meals_completed_goal"] == 20
        assert db_result["new_recipes_goal"] == 6
    
    def test_save_weekly_meal_goals_update_existing(self, client, logged_in_user, test_db):
        """Test updating existing weekly meal goals."""
        cursor = test_db.cursor()
        
        # Calculate current week start
        current_date = datetime.now().date()
        days_since_monday = current_date.weekday()
        week_start = current_date - timedelta(days=days_since_monday)
        
        # Create existing goals
        cursor.execute("""
            INSERT INTO weekly_meal_goals 
            (user_id, week_start_date, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, week_start, 2, 10, 3))
        
        # Update goals
        updated_goals = {
            "meal_plans_goal": 5,
            "meals_completed_goal": 30,
            "new_recipes_goal": 8
        }
        
        response = client.post("/api/meal-goals/weekly", json=updated_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Verify updated values
        cursor.execute("""
            SELECT * FROM weekly_meal_goals 
            WHERE user_id = %s AND week_start_date = %s
        """, (logged_in_user, week_start))
        db_result = cursor.fetchone()
        
        assert db_result["meal_plans_goal"] == 5
        assert db_result["meals_completed_goal"] == 30
        assert db_result["new_recipes_goal"] == 8
    
    def test_save_weekly_meal_goals_invalid_ranges(self, client, logged_in_user):
        """Test saving weekly goals with invalid ranges."""
        # Test meal plans goal too high
        invalid_goals = {
            "meal_plans_goal": 15,  # Max is 10 for weekly
            "meals_completed_goal": 25,
            "new_recipes_goal": 5
        }
        
        response = client.post("/api/meal-goals/weekly", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 1 and 10" in data["message"]
        
        # Test meals completed goal too low
        invalid_goals["meal_plans_goal"] = 3
        invalid_goals["meals_completed_goal"] = 3  # Min is 5 for weekly
        
        response = client.post("/api/meal-goals/weekly", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 5 and 50" in data["message"]
        
        # Test new recipes goal too high
        invalid_goals["meals_completed_goal"] = 25
        invalid_goals["new_recipes_goal"] = 20  # Max is 15 for weekly
        
        response = client.post("/api/meal-goals/weekly", json=invalid_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "must be between 1 and 15" in data["message"]
    
    def test_get_weekly_goals_progress_success(self, client, logged_in_user, test_db):
        """Test successfully getting weekly goals progress."""
        cursor = test_db.cursor()
        
        # Calculate current week dates
        current_date = datetime.now().date()
        days_since_monday = current_date.weekday()
        week_start = current_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        # Create test data for current week
        cursor.execute("""
            INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Weekly Plan", week_start, week_end, 7, datetime.now()))
        
        # Create completed meals for this week
        for i in range(5):  # 5 completed meals
            meal_date = week_start + timedelta(days=i)
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, is_completed)
                VALUES (%s, %s, %s, %s)
            """, (logged_in_user, meal_date, "lunch", True))
        
        # Create meals with recipe templates
        cursor.execute("""
            INSERT INTO recipe_templates (recipe_name, description, meal_type, instructions)
            VALUES (%s, %s, 'dinner', 'Cook it'), (%s, %s, 'dinner', 'Cook it')
        """, ("Weekly Recipe 1", "Test recipe", "Weekly Recipe 2", "Another recipe"))
        
        cursor.execute("SELECT template_id FROM recipe_templates ORDER BY template_id DESC LIMIT 2")
        template_ids = [row["template_id"] for row in cursor.fetchall()]
        
        for i, template_id in enumerate(template_ids):
            meal_date = week_start + timedelta(days=i)
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, recipe_template_id)
                VALUES (%s, %s, %s, %s)
            """, (logged_in_user, meal_date, "dinner", template_id))
        
        response = client.get("/api/meal-goals/progress/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        progress = data["progress"]
        assert progress["meal_plans_count"] == 1
        assert progress["completed_meals_count"] == 5
        assert progress["new_recipes_count"] == 2
        assert progress["week_start_date"] == week_start.isoformat()
        assert progress["week_end_date"] == week_end.isoformat()
    
    def test_get_weekly_goals_progress_custom_dates(self, client, logged_in_user, test_db):
        """Test getting weekly progress with custom date range."""
        cursor = test_db.cursor()
        
        # Use specific date range
        start_date = "2024-01-15"  # Monday
        end_date = "2024-01-21"    # Sunday
        
        # Create test data for specific week
        cursor.execute("""
            INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Custom Week Plan", start_date, end_date, 7, "2024-01-15"))
        
        response = client.get(f"/api/meal-goals/progress/weekly?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        progress = data["progress"]
        assert progress["meal_plans_count"] == 1
        assert progress["week_start_date"] == start_date
        assert progress["week_end_date"] == end_date
    
    def test_get_weekly_goals_progress_invalid_date_format(self, client, logged_in_user):
        """Test weekly progress with invalid date format."""
        response = client.get("/api/meal-goals/progress/weekly?start_date=invalid-date&end_date=2024-01-21")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid date format" in data["message"]
    
    def test_weekly_meal_goals_not_authenticated(self, client):
        """Test weekly goals endpoints when not authenticated."""
        # Get weekly goals
        response = client.get("/api/meal-goals/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
        
        # Save weekly goals
        response = client.post("/api/meal-goals/weekly", json={"meal_plans_goal": 3, "meals_completed_goal": 15, "new_recipes_goal": 3})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
        
        # Get weekly progress
        response = client.get("/api/meal-goals/progress/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestMealGoalsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_save_goals_with_none_values(self, client, logged_in_user):
        """Test saving goals with None values."""
        goals_data = {
            "month": 6,
            "year": 2024,
            "meal_plans_goal": None,  # Invalid
            "meals_completed_goal": 100,
            "new_recipes_goal": 15
        }
        
        response = client.post("/api/meal-goals", json=goals_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid data types" in data["message"]
    
    def test_progress_with_null_dates(self, client, logged_in_user, test_db):
        """Test progress calculation with NULL dates in database."""
        cursor = test_db.cursor()
        
        # Create meal plan with NULL generated_at (should not be counted)
        cursor.execute("""
            INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Null Date Plan", "2024-01-15", "2024-01-21", 7))
        
        current_date = datetime.now()
        response = client.get(f"/api/meal-goals/progress?month={current_date.month}&year={current_date.year}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        # Should handle NULL dates gracefully
    
    def test_database_connection_cleanup(self, client, logged_in_user):
        """Test that database cursors are properly closed on errors."""
        with patch('src.backend.apis.meal_goals.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Test error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/meal-goals")
            assert response.status_code == 200
            
            # Verify cursor.close() was called
            mock_cursor.close.assert_called_once()
    
    def test_monthly_to_weekly_goal_conversion(self, client, logged_in_user, test_db):
        """Test that weekly and monthly goals are separate entities."""
        cursor = test_db.cursor()
        
        current_date = datetime.now()
        
        # Create monthly goals
        cursor.execute("""
            INSERT INTO monthly_meal_goals 
            (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, current_date.month, current_date.year, 20, 200, 50))
        
        # Weekly goals should still return defaults (separate from monthly)
        response = client.get("/api/meal-goals/weekly")
        assert response.status_code == 200
        
        data = response.get_json()
        goals = data["goals"]
        
        # Should be weekly defaults, not monthly values
        assert goals["meal_plans_goal"] == 2
        assert goals["meals_completed_goal"] == 15
        assert goals["new_recipes_goal"] == 3
    
    def test_goals_boundary_values(self, client, logged_in_user):
        """Test boundary values for goal limits."""
        # Test minimum valid monthly values
        min_goals = {
            "month": 1,
            "year": 2020,
            "meal_plans_goal": 1,
            "meals_completed_goal": 10,
            "new_recipes_goal": 1
        }
        
        response = client.post("/api/meal-goals", json=min_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Test maximum valid monthly values
        max_goals = {
            "month": 12,
            "year": 2030,
            "meal_plans_goal": 20,
            "meals_completed_goal": 200,
            "new_recipes_goal": 50
        }
        
        response = client.post("/api/meal-goals", json=max_goals)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Test minimum valid weekly values
        min_weekly = {
            "meal_plans_goal": 1,
            "meals_completed_goal": 5,
            "new_recipes_goal": 1
        }
        
        response = client.post("/api/meal-goals/weekly", json=min_weekly)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True