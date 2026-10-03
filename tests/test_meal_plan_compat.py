"""
Comprehensive tests for meal plan compatibility API endpoints.
Tests backward compatibility for existing meal plan structure while using new individual meals database.
"""

import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

@pytest.mark.api
@pytest.mark.meal_planning
class TestGetMealPlans:
    """Test getting all meal plan sessions for a user."""
    
    def test_get_meal_plans_success(self, client, logged_in_user, test_db):
        """Test successfully getting meal plans with fuzzy matching data."""
        cursor = test_db.cursor()
        
        # Create a meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days, dietary_preference, budget_limit, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Test Plan", date.today(), date.today() + timedelta(days=6), 7, "vegetarian", 100.50, "active"))
        session_id = cursor.lastrowid
        
        # Create shopping generation session
        cursor.execute("""
            INSERT INTO shopping_generation_sessions
            (user_id, generation_type, meal_plan_session_id, auto_matched_count, confirm_needed_count, missing_count, total_ingredients)
            VALUES (%s, 'meal_plan', %s, %s, %s, %s, %s)
        """, (logged_in_user, session_id, 5, 2, 1, 8))
        
        # Add some meals
        cursor.execute("""
            INSERT INTO meals (user_id, session_id, meal_date, meal_type, is_completed)
            VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
        """, (logged_in_user, session_id, "2024-01-15", "breakfast", True,
              logged_in_user, session_id, "2024-01-15", "lunch", False))
        
        response = client.get("/api/meal-plans")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert len(data["plans"]) == 1
        
        plan = data["plans"][0]
        assert plan["plan_name"] == "Test Plan"
        assert plan["total_days"] == 7
        assert plan["dietary_preference"] == "vegetarian"
        assert plan["budget_limit"] == "100.50"
        assert plan["status"] == "active"
        
        # Check fuzzy matching summary
        assert "fuzzy_matching_summary" in plan
        fuzzy = plan["fuzzy_matching_summary"]
        assert fuzzy["auto_matched"] == 5
        assert fuzzy["confirm_needed"] == 2
        assert fuzzy["missing"] == 1
        assert fuzzy["total_ingredients"] == 8
        assert fuzzy["pantry_utilization_rate"] == 62.5
    
    def test_get_meal_plans_not_authenticated(self, client):
        """Test getting meal plans when not authenticated."""
        response = client.get("/api/meal-plans")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_get_meal_plans_empty_list(self, client, logged_in_user):
        """Test getting meal plans when user has no plans."""
        response = client.get("/api/meal-plans")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["plans"] == []
    
    def test_get_meal_plans_status_calculation(self, client, logged_in_user, test_db):
        """Test meal plan status calculation based on dates and completion."""
        cursor = test_db.cursor()
        today = date.today()
        
        # Past plan with completed meals
        past_start = today - timedelta(days=10)
        past_end = today - timedelta(days=3)
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Past Completed", past_start, past_end, 7, "active"))
        past_session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO meals (user_id, session_id, meal_date, meal_type, is_completed)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, past_session_id, past_start, "breakfast", True))
        
        # Past plan with no completed meals
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Past Expired", past_start, past_end, 7, "active"))
        expired_session_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO meals (user_id, session_id, meal_date, meal_type, is_completed)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, expired_session_id, past_start, "lunch", False))
        
        # Current active plan
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Current Active", today, today + timedelta(days=6), 7, "active"))
        
        response = client.get("/api/meal-plans")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert len(data["plans"]) == 3
        
        # Find each plan by name and check status
        plans_by_name = {plan["plan_name"]: plan for plan in data["plans"]}
        assert plans_by_name["Past Completed"]["status"] == "completed"
        assert plans_by_name["Past Expired"]["status"] == "expired"
        assert plans_by_name["Current Active"]["status"] == "active"
    
    def test_get_meal_plans_database_error(self, client, logged_in_user):
        """Test handling database errors."""
        with patch('src.backend.apis.meal_plan_compat.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database connection error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/meal-plans")
            assert response.status_code == 200
            
            data = response.get_json()
            assert data["success"] is False
            assert "Failed to get meal plans" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestGetMealPlanDetails:
    """Test getting detailed meal plan with recipes and batch prep steps."""
    
    def test_get_meal_plan_details_success(self, client, logged_in_user, test_db):
        """Test successfully getting meal plan details."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days, dietary_preference)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Detailed Plan", "2024-01-15", "2024-01-21", 7, "balanced"))
        session_id = cursor.lastrowid
        
        # Create recipe template
        cursor.execute("""
            INSERT INTO recipe_templates 
            (recipe_name, description, prep_time, cook_time, servings, difficulty, instructions)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ("Test Recipe", "A test recipe", 10, 20, 2, "easy", "Test instructions"))
        template_id = cursor.lastrowid
        
        # Add ingredients to template
        cursor.execute("""
            INSERT INTO template_ingredients (template_id, ingredient_name, quantity, unit)
            VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
        """, (template_id, "chicken breast", 1, "lb", template_id, "olive oil", 2, "tbsp"))
        
        # Create meal with template
        cursor.execute("""
            INSERT INTO meals 
            (user_id, session_id, meal_date, meal_type, recipe_template_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, session_id, "2024-01-15", "dinner", template_id, "Day 1 dinner"))
        
        # Create custom meal without template
        cursor.execute("""
            INSERT INTO meals 
            (user_id, session_id, meal_date, meal_type, custom_recipe_name, custom_instructions)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, session_id, "2024-01-16", "breakfast", "Custom Oats", "Mix oats with milk"))
        
        # Add batch prep steps
        cursor.execute("""
            INSERT INTO session_batch_prep (session_id, prep_session_name, step_order, description)
            VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
        """, (session_id, "Sunday Prep", 1, "Chop vegetables", session_id, "Sunday Prep", 2, "Marinate chicken"))
        
        # Add shopping list items
        cursor.execute("""
            INSERT INTO session_shopping_lists (session_id, ingredient_name, total_quantity, unit, category)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, "chicken breast", 2, "lbs", "Meat"))
        
        response = client.get(f"/api/meal-plans/{session_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        meal_plan = data["meal_plan"]
        assert meal_plan["plan_info"]["plan_name"] == "Detailed Plan"
        assert meal_plan["plan_info"]["total_days"] == 7
        
        # Check recipes are organized by day
        assert "recipes" in meal_plan
        recipes = meal_plan["recipes"]
        assert "1" in recipes  # Day 1 (JSON object keys are strings)
        assert "2" in recipes  # Day 2
        
        # Check day 1 dinner recipe
        day1_dinner = recipes["1"]["dinner"]
        assert day1_dinner["name"] == "Test Recipe"
        assert day1_dinner["prep_time"] == 10
        assert day1_dinner["cook_time"] == 20
        assert len(day1_dinner["ingredients"]) == 2
        
        # Check day 2 custom breakfast
        day2_breakfast = recipes["2"]["breakfast"]
        assert day2_breakfast["name"] == "Custom Oats"
        assert day2_breakfast["instructions"] == "Mix oats with milk"
        
        # Check batch prep steps
        assert len(meal_plan["batch_prep"]) == 2
        
        # Check shopping list
        assert len(meal_plan["shopping_list"]) == 1
        assert meal_plan["shopping_list"][0]["ingredient_name"] == "chicken breast"
    
    def test_get_meal_plan_details_not_found(self, client, logged_in_user):
        """Test getting details for non-existent meal plan."""
        response = client.get("/api/meal-plans/99999")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found" in data["message"]
    
    def test_get_meal_plan_details_not_authenticated(self, client):
        """Test getting meal plan details when not authenticated."""
        response = client.get("/api/meal-plans/1")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_get_meal_plan_details_with_fuzzy_matching(self, client, logged_in_user, test_db):
        """Test getting meal plan details with fuzzy matching data."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Plan with Matching", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Create shopping generation session
        cursor.execute("""
            INSERT INTO shopping_generation_sessions
            (user_id, generation_type, meal_plan_session_id, auto_matched_count, confirm_needed_count, missing_count, total_ingredients)
            VALUES (%s, 'meal_plan', %s, %s, %s, %s, %s)
        """, (logged_in_user, session_id, 3, 1, 1, 5))
        generation_id = cursor.lastrowid
        
        # Create pantry item
        cursor.execute("""
            INSERT INTO pantry_items (user_id, item_name, quantity, unit, storage_type, expiration_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "chicken breast", 2, "lbs", "fridge", "2024-01-20"))
        pantry_item_id = cursor.lastrowid
        
        # Create matching result
        cursor.execute("""
            INSERT INTO generation_ingredient_matches 
            (generation_id, ingredient_name, required_quantity, required_unit, pantry_item_id, 
             pantry_available_quantity, match_type, match_confidence, needs_to_buy_quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (generation_id, "chicken breast", 1.5, "lbs", pantry_item_id, 2.0, "auto", 95.5, 0))
        
        response = client.get(f"/api/meal-plans/{session_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        meal_plan = data["meal_plan"]
        
        # Check fuzzy matching data is included
        assert "fuzzy_matching" in meal_plan
        fuzzy = meal_plan["fuzzy_matching"]
        assert fuzzy["summary"]["auto_matched"] == 3
        assert fuzzy["summary"]["total_ingredients"] == 5
        assert fuzzy["summary"]["pantry_utilization_rate"] == 60.0
        
        # Check ingredient match details
        matches = fuzzy["ingredient_matches"]
        assert "chicken breast" in matches
        chicken_match = matches["chicken breast"]
        assert chicken_match["match_type"] == "auto"
        assert chicken_match["confidence"] == 95.5
        assert chicken_match["needs_to_buy"] == 0
    
    def test_get_meal_plan_details_without_fuzzy_matching(self, client, logged_in_user, test_db):
        """Test getting meal plan details when no fuzzy matching data exists."""
        cursor = test_db.cursor()
        
        # Create meal plan session without shopping generation
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Plan without Matching", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.get(f"/api/meal-plans/{session_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        meal_plan = data["meal_plan"]
        assert meal_plan["fuzzy_matching"] is None


@pytest.mark.api
@pytest.mark.meal_planning
class TestDeleteMealPlan:
    """Test deleting meal plans and associated data."""
    
    def test_delete_meal_plan_success(self, client, logged_in_user, test_db):
        """Test successfully deleting a meal plan."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Plan to Delete", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Create associated data
        cursor.execute("""
            INSERT INTO meals (user_id, session_id, meal_date, meal_type)
            VALUES (%s, %s, %s, %s)
        """, (logged_in_user, session_id, "2024-01-15", "breakfast"))
        
        cursor.execute("""
            INSERT INTO shopping_generation_sessions (user_id, generation_type, meal_plan_session_id, total_ingredients)
            VALUES (%s, 'meal_plan', %s, %s)
        """, (logged_in_user, session_id, 5))
        
        response = client.delete(f"/api/meal-plans/{session_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
        
        # Verify meal plan was deleted
        cursor.execute("SELECT * FROM meal_plan_sessions WHERE session_id = %s", (session_id,))
        assert cursor.fetchone() is None
        
        # Verify associated meals were deleted
        cursor.execute("SELECT * FROM meals WHERE session_id = %s", (session_id,))
        assert cursor.fetchone() is None
    
    def test_delete_meal_plan_not_found(self, client, logged_in_user):
        """Test deleting non-existent meal plan."""
        response = client.delete("/api/meal-plans/99999")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found or access denied" in data["message"]
    
    def test_delete_meal_plan_not_authenticated(self, client):
        """Test deleting meal plan when not authenticated."""
        response = client.delete("/api/meal-plans/1")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_delete_meal_plan_access_denied(self, client, logged_in_user, test_db):
        """Test deleting meal plan belonging to another user."""
        cursor = test_db.cursor()
        
        # Create meal plan for different user
        cursor.execute("""
            INSERT INTO user_account (user_ID, email, password)
            VALUES (%s, %s, %s)
        """, ("other_user", "other@example.com", "x"))
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, ("other_user", "Other User Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.delete(f"/api/meal-plans/{session_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found or access denied" in data["message"]
    
    def test_delete_meal_plan_database_error(self, client, logged_in_user, test_db):
        """Test handling database errors during deletion."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Error Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        with patch('src.backend.apis.meal_plan_compat.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"session_id": session_id}
            mock_cursor.execute.side_effect = [None, Exception("Delete error")]
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.delete(f"/api/meal-plans/{session_id}")
            assert response.status_code == 200
            
            data = response.get_json()
            assert data["success"] is False
            assert "Failed to delete meal plan" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestRefreshPantryMatches:
    """Test refreshing fuzzy matching data for meal plans."""
    
    def test_refresh_pantry_matches_success(self, client, logged_in_user, test_db):
        """Test successfully refreshing pantry matches."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Refresh Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Create generation session
        cursor.execute("""
            INSERT INTO shopping_generation_sessions
            (user_id, generation_type, meal_plan_session_id, auto_matched_count, total_ingredients)
            VALUES (%s, 'meal_plan', %s, %s, %s)
        """, (logged_in_user, session_id, 0, 2))
        generation_id = cursor.lastrowid
        
        # Add ingredients to match
        cursor.execute("""
            INSERT INTO generation_ingredient_matches 
            (generation_id, ingredient_name, required_quantity, required_unit, match_type)
            VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
        """, (generation_id, "chicken breast", 2, "lbs", "missing",
              generation_id, "olive oil", 0.25, "cup", "missing"))
        
        # Add matching pantry item
        cursor.execute("""
            INSERT INTO pantry_items (user_id, item_name, quantity, unit, storage_type, is_consumed)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "chicken breast", 3, "lbs", "fridge", False))
        
        response = client.post(f"/api/meal-plans/{session_id}/refresh-matches")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["refreshed_count"] == 1  # Only chicken breast should match
        assert data["total_ingredients"] == 2
        assert "Refreshed 1 ingredient matches" in data["message"]
    
    def test_refresh_pantry_matches_not_found(self, client, logged_in_user):
        """Test refreshing matches for non-existent meal plan."""
        response = client.post("/api/meal-plans/99999/refresh-matches")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found or access denied" in data["message"]
    
    def test_refresh_pantry_matches_no_generation(self, client, logged_in_user, test_db):
        """Test refreshing matches when no generation session exists."""
        cursor = test_db.cursor()
        
        # Create meal plan session without generation
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "No Generation Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.post(f"/api/meal-plans/{session_id}/refresh-matches")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "No fuzzy matching data found" in data["message"]
    
    def test_refresh_pantry_matches_not_authenticated(self, client):
        """Test refreshing matches when not authenticated."""
        response = client.post("/api/meal-plans/1/refresh-matches")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestUpdateMealPlanName:
    """Test updating meal plan names."""
    
    def test_update_meal_plan_name_success(self, client, logged_in_user, test_db):
        """Test successfully updating meal plan name."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Old Name", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.put(f"/api/meal-plans/{session_id}/name", 
                            json={"name": "New Name"})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["new_name"] == "New Name"
        assert "updated successfully" in data["message"]
        
        # Verify name was updated
        cursor.execute("SELECT session_name FROM meal_plan_sessions WHERE session_id = %s", (session_id,))
        result = cursor.fetchone()
        assert result["session_name"] == "New Name"
    
    def test_update_meal_plan_name_empty(self, client, logged_in_user, test_db):
        """Test updating with empty name."""
        cursor = test_db.cursor()
        
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Valid Name", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.put(f"/api/meal-plans/{session_id}/name", 
                            json={"name": "   "})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "cannot be empty" in data["message"]
    
    def test_update_meal_plan_name_too_long(self, client, logged_in_user, test_db):
        """Test updating with name too long."""
        cursor = test_db.cursor()
        
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Valid Name", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        long_name = "A" * 22  # Over 21 character limit
        response = client.put(f"/api/meal-plans/{session_id}/name", 
                            json={"name": long_name})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "21 characters or less" in data["message"]
    
    def test_update_meal_plan_name_not_found(self, client, logged_in_user):
        """Test updating name for non-existent meal plan."""
        response = client.put("/api/meal-plans/99999/name", 
                            json={"name": "New Name"})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found or access denied" in data["message"]
    
    def test_update_meal_plan_name_not_authenticated(self, client):
        """Test updating name when not authenticated."""
        response = client.put("/api/meal-plans/1/name", 
                            json={"name": "New Name"})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
@pytest.mark.shopping
class TestAddItemsToShoppingList:
    """Test adding meal plan items to shopping lists."""
    
    def test_add_items_to_shopping_list_success(self, client, logged_in_user, test_db):
        """Test successfully adding items to shopping list."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Shopping Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        items_to_add = [
            {"ingredient_name": "chicken breast", "quantity": 2, "unit": "lbs"},
            {"ingredient_name": "olive oil", "quantity": 1, "unit": "bottle"}
        ]
        
        response = client.post(f"/api/meal-plans/{session_id}/shopping-list", 
                             json={"items": items_to_add})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["added_count"] == 2
        assert "list_id" in data
        
        # Verify shopping list was created
        cursor.execute("""
            SELECT list_name FROM shopping_lists 
            WHERE list_id = %s AND user_id = %s
        """, (data["list_id"], logged_in_user))
        result = cursor.fetchone()
        assert "Shopping Plan" in result["list_name"]
        
        # Verify items were added
        cursor.execute("""
            SELECT item_name, quantity, notes FROM shopping_list_items 
            WHERE list_id = %s ORDER BY item_name
        """, (data["list_id"],))
        items = cursor.fetchall()
        assert len(items) == 2
        assert items[0]["item_name"] == "chicken breast"
        assert items[0]["quantity"] == 2
        assert "2 lbs" in items[0]["notes"]
    
    def test_add_items_to_existing_shopping_list(self, client, logged_in_user, test_db):
        """Test adding items to existing shopping list."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Existing Shopping Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Create existing shopping list for this meal plan
        cursor.execute("""
            INSERT INTO shopping_lists 
            (user_id, list_name, meal_plan_session_id, is_meal_plan_list)
            VALUES (%s, %s, %s, %s)
        """, (logged_in_user, "Existing List", session_id, True))
        list_id = cursor.lastrowid
        
        # Add existing item
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, notes)
            VALUES (%s, %s, %s, %s)
        """, (list_id, "chicken breast", 1, "1 lb"))
        
        # Add items including duplicate
        items_to_add = [
            {"ingredient_name": "chicken breast", "quantity": 1, "unit": "lb"},  # Duplicate
            {"ingredient_name": "rice", "quantity": 2, "unit": "cups"}  # New
        ]
        
        response = client.post(f"/api/meal-plans/{session_id}/shopping-list", 
                             json={"items": items_to_add})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["added_count"] == 2
        
        # Verify chicken breast quantity was updated
        cursor.execute("""
            SELECT quantity, notes FROM shopping_list_items 
            WHERE list_id = %s AND item_name = %s
        """, (list_id, "chicken breast"))
        result = cursor.fetchone()
        assert result["quantity"] == 2  # 1 + 1
        assert "1 lb, 1 lb" in result["notes"]
    
    def test_add_items_empty_list(self, client, logged_in_user, test_db):
        """Test adding empty items list."""
        cursor = test_db.cursor()
        
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Empty Items Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        response = client.post(f"/api/meal-plans/{session_id}/shopping-list", 
                             json={"items": []})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "No items provided" in data["message"]
    
    def test_add_items_not_authenticated(self, client):
        """Test adding items when not authenticated."""
        response = client.post("/api/meal-plans/1/shopping-list", 
                             json={"items": [{"ingredient_name": "test", "quantity": 1}]})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Not authenticated" in data["message"]
    
    def test_add_items_plan_not_found(self, client, logged_in_user):
        """Test adding items to non-existent meal plan."""
        response = client.post("/api/meal-plans/99999/shopping-list", 
                             json={"items": [{"ingredient_name": "test", "quantity": 1}]})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is False
        assert "Meal plan not found or access denied" in data["message"]


@pytest.mark.api
@pytest.mark.meal_planning
class TestOrganizeRecipesByDay:
    """Test the recipe organization helper function."""
    
    def test_organize_recipes_by_day_success(self):
        """Test organizing recipes by day and meal type."""
        from src.backend.apis.meal_plan_compat import organize_recipes_by_day
        
        recipe_data = [
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "recipe_id": 1,
                "recipe_name": "Oats",
                "description": "Healthy breakfast",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "estimated_cost": 2.50,
                "difficulty": "easy",
                "calories_per_serving": 300,
                "instructions": "Mix oats with milk",
                "notes": "Add fruits",
                "ingredient_name": "oats",
                "quantity": 1,
                "unit": "cup",
                "ingredient_notes": "rolled oats"
            },
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "recipe_id": 1,
                "recipe_name": "Oats",
                "description": "Healthy breakfast",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "estimated_cost": 2.50,
                "difficulty": "easy",
                "calories_per_serving": 300,
                "instructions": "Mix oats with milk",
                "notes": "Add fruits",
                "ingredient_name": "milk",
                "quantity": 0.5,
                "unit": "cup",
                "ingredient_notes": "whole milk"
            },
            {
                "day_number": 1,
                "meal_type": "lunch",
                "recipe_id": 2,
                "recipe_name": "Salad",
                "description": "Fresh salad",
                "prep_time": 10,
                "cook_time": 0,
                "servings": 1,
                "estimated_cost": 4.00,
                "difficulty": "easy",
                "calories_per_serving": 250,
                "instructions": "Mix ingredients",
                "notes": "Seasonal vegetables",
                "ingredient_name": "lettuce",
                "quantity": 2,
                "unit": "cups",
                "ingredient_notes": "fresh lettuce"
            }
        ]
        
        organized = organize_recipes_by_day(recipe_data)
        
        # Check structure
        assert 1 in organized
        assert "breakfast" in organized[1]
        assert "lunch" in organized[1]
        
        # Check breakfast recipe
        breakfast = organized[1]["breakfast"]
        assert breakfast["recipe_id"] == 1
        assert breakfast["name"] == "Oats"
        assert breakfast["prep_time"] == 5
        assert len(breakfast["ingredients"]) == 2
        
        # Check ingredients
        oats_ingredient = next(ing for ing in breakfast["ingredients"] if ing["name"] == "oats")
        assert oats_ingredient["quantity"] == 1
        assert oats_ingredient["unit"] == "cup"
        assert oats_ingredient["notes"] == "rolled oats"
        
        # Check lunch recipe
        lunch = organized[1]["lunch"]
        assert lunch["recipe_id"] == 2
        assert lunch["name"] == "Salad"
        assert len(lunch["ingredients"]) == 1
    
    def test_organize_recipes_by_day_empty_data(self):
        """Test organizing empty recipe data."""
        from src.backend.apis.meal_plan_compat import organize_recipes_by_day
        
        organized = organize_recipes_by_day([])
        assert organized == {}
    
    def test_organize_recipes_by_day_no_ingredients(self):
        """Test organizing recipes without ingredients."""
        from src.backend.apis.meal_plan_compat import organize_recipes_by_day
        
        recipe_data = [
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "recipe_id": 1,
                "recipe_name": "Simple Recipe",
                "description": "No ingredients",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "estimated_cost": 1.00,
                "difficulty": "easy",
                "calories_per_serving": 100,
                "instructions": "Just eat it",
                "notes": "",
                "ingredient_name": None,
                "quantity": None,
                "unit": None,
                "ingredient_notes": None
            }
        ]
        
        organized = organize_recipes_by_day(recipe_data)
        
        assert 1 in organized
        assert "breakfast" in organized[1]
        breakfast = organized[1]["breakfast"]
        assert breakfast["name"] == "Simple Recipe"
        assert len(breakfast["ingredients"]) == 0


@pytest.mark.api
@pytest.mark.meal_planning
class TestMealPlanCompatEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_meal_plan_with_zero_ingredients(self, client, logged_in_user, test_db):
        """Test fuzzy matching with zero total ingredients."""
        cursor = test_db.cursor()
        
        # Create meal plan session
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "Zero Ingredients", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Create generation session with zero ingredients
        cursor.execute("""
            INSERT INTO shopping_generation_sessions
            (user_id, generation_type, meal_plan_session_id, auto_matched_count, total_ingredients)
            VALUES (%s, 'meal_plan', %s, %s, %s)
        """, (logged_in_user, session_id, 0, 0))
        
        response = client.get("/api/meal-plans")
        assert response.status_code == 200
        
        data = response.get_json()
        plan = data["plans"][0]
        
        # Should handle division by zero gracefully
        fuzzy = plan["fuzzy_matching_summary"]
        assert fuzzy["pantry_utilization_rate"] == 0
    
    def test_get_meal_plans_cursor_close_on_exception(self, client, logged_in_user):
        """Test that cursor is properly closed on exception."""
        with patch('src.backend.apis.meal_plan_compat.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Test error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/meal-plans")
            assert response.status_code == 200
            
            # Verify cursor.close() was called
            mock_cursor.close.assert_called_once()
    
    def test_invalid_json_handling(self, client, logged_in_user, test_db):
        """Test handling of invalid JSON in requests."""
        cursor = test_db.cursor()
        
        cursor.execute("""
            INSERT INTO meal_plan_sessions 
            (user_id, session_name, start_date, end_date, total_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (logged_in_user, "JSON Test Plan", "2024-01-15", "2024-01-21", 7))
        session_id = cursor.lastrowid
        
        # Send invalid JSON
        response = client.put(f"/api/meal-plans/{session_id}/name", 
                            data="invalid json",
                            content_type='application/json')
        
        # Flask should handle JSON parsing errors
        assert response.status_code in [400, 415]  # Bad request or unsupported media type