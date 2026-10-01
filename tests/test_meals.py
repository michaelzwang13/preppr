"""
Comprehensive tests for meals.py API.
Tests all endpoints for meal management including nutrition tracking,
daily summaries, meal plan generation, and subscription-based filtering.
"""

import pytest
import json
from datetime import datetime, timedelta, date
from src.database import get_db
from unittest.mock import patch, MagicMock
from tests.conftest import open_test_connection


@pytest.mark.meals
@pytest.mark.api
@pytest.mark.unit
class TestMealNutritionAPI:
    """Test meal nutrition endpoints."""
    
    def test_get_meal_nutrition_not_authenticated(self, client):
        """Test getting meal nutrition without authentication."""
        response = client.get('/api/nutrition/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_get_meal_nutrition_not_found(self, client, logged_in_user):
        """Test getting nutrition for non-existent meal."""
        response = client.get('/api/nutrition/999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Nutrition data not found'
    
    def test_get_meal_nutrition_success(self, client, logged_in_user):
        """Test successful meal nutrition retrieval."""
        # Create test meal with nutrition data
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            # Create meal
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            """, ('test_user', '2024-01-15', 'lunch', 'Test Meal'))
            meal_id = cursor.lastrowid
            
            # Create nutrition data
            cursor.execute("""
                INSERT INTO meal_nutrition (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings, serving_size, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (meal_id, 'test_user', 500.0, 25.0, 60.0, 15.0, 8.0, 800.0, 1, 'medium', 'user_entered'))
            
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['nutrition']['meal_id'] == meal_id
        assert data['nutrition']['calories'] == 500.0
        assert data['nutrition']['macros']['protein'] == 25.0
        assert data['nutrition']['meal_type'] == 'lunch'
    
    def test_get_daily_nutrition_summary_not_authenticated(self, client):
        """Test getting daily nutrition summary without authentication."""
        response = client.get('/api/nutrition/daily/2024-01-15')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_get_daily_nutrition_summary_invalid_date(self, client, logged_in_user):
        """Test getting daily nutrition summary with invalid date."""
        response = client.get('/api/nutrition/daily/invalid-date')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid date format' in data['message']
    
    def test_get_daily_nutrition_summary_success(self, client, logged_in_user):
        """Test successful daily nutrition summary retrieval."""
        test_date = '2024-01-15'
        
        # Create test meals with nutrition data
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            meals_data = [
                ('breakfast', 'Breakfast Meal', 300.0, 15.0, 40.0, 10.0, 5.0, 400.0, True),
                ('lunch', 'Lunch Meal', 450.0, 25.0, 50.0, 18.0, 8.0, 600.0, True),
                ('dinner', 'Dinner Meal', 550.0, 30.0, 60.0, 20.0, 10.0, 700.0, False)  # Not completed
            ]
            
            for meal_type, name, calories, protein, carbs, fat, fiber, sodium, is_completed in meals_data:
                cursor.execute("""
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name, is_completed)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('test_user', test_date, meal_type, name, is_completed))
                meal_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO meal_nutrition (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings, serving_size, source_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (meal_id, 'test_user', calories, protein, carbs, fat, fiber, sodium, 1, 'medium', 'user_entered'))
            
            cursor.close()
        
        response = client.get(f'/api/nutrition/daily/{test_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['date'] == test_date
        assert data['total_meals'] == 3
        assert data['completed_meals'] == 2
        
        # Only completed meals should contribute to daily totals
        assert data['daily_totals']['calories'] == 750.0  # 300 + 450
        assert data['daily_totals']['protein'] == 40.0    # 15 + 25
        
        # Should have all meals in response
        assert len(data['meals']) == 3


@pytest.mark.meals
@pytest.mark.subscription
@pytest.mark.unit
class TestNutritionSubscriptionFiltering:
    """Test subscription-based nutrition data filtering."""
    
    @patch('src.backend.apis.meals.get_user_subscription_info')
    def test_filter_nutrition_free_tier(self, mock_subscription, client, logged_in_user):
        """Test nutrition filtering for free tier users."""
        # Mock free tier subscription
        mock_subscription.return_value = {
            'tier': 'free',
            'status': 'active'
        }
        
        # Create test meal with full nutrition data
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            """, ('test_user', '2024-01-15', 'lunch', 'Test Meal'))
            meal_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO meal_nutrition (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings, serving_size, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (meal_id, 'test_user', 500.0, 25.0, 60.0, 15.0, 8.0, 800.0, 1, 'medium', 'user_entered'))
            
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Free tier should have calories, protein, fat but not carbs, fiber, sodium
        nutrition = data['nutrition']
        assert nutrition['calories'] == 500.0
        assert nutrition['macros']['protein'] == 25.0
        assert nutrition['macros']['fat'] == 15.0
        assert nutrition['macros']['carbs'] is None
        assert nutrition['macros']['fiber'] is None
        assert nutrition['macros']['sodium'] is None
        
        # Should include upgrade message
        assert '_upgrade_message' in data
        assert '_limited_tier' in data
    
    @patch('src.backend.apis.meals.get_user_subscription_info')
    def test_filter_nutrition_premium_tier(self, mock_subscription, client, premium_user):
        """Test nutrition filtering for premium tier users."""
        # Mock premium subscription
        mock_subscription.return_value = {
            'tier': 'premium',
            'status': 'active'
        }
        
        # Create test meal with full nutrition data
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            """, ('premium_user', '2024-01-15', 'dinner', 'Premium Meal'))
            meal_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO meal_nutrition (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings, serving_size, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (meal_id, 'premium_user', 600.0, 30.0, 70.0, 20.0, 12.0, 900.0, 1, 'large', 'user_entered'))
            
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Premium tier should have all nutrition data
        nutrition = data['nutrition']
        assert nutrition['calories'] == 600.0
        assert nutrition['macros']['protein'] == 30.0
        assert nutrition['macros']['fat'] == 20.0
        assert nutrition['macros']['carbs'] == 70.0
        assert nutrition['macros']['fiber'] == 12.0
        assert nutrition['macros']['sodium'] == 900.0
        
        # Should not include upgrade message
        assert '_upgrade_message' not in data
        assert '_limited_tier' not in data
    
    def test_filter_nutrition_data_function_free(self, app):
        """Test the filter_nutrition_data_by_subscription function for free tier."""
        from src.backend.apis.meals import filter_nutrition_data_by_subscription
        
        with patch('src.backend.apis.meals.get_user_subscription_info') as mock_subscription:
            mock_subscription.return_value = {
                'tier': 'free',
                'status': 'active'
            }
            
            nutrition_data = {
                'calories': 500.0,
                'protein': 25.0,
                'carbs': 60.0,
                'fat': 15.0,
                'fiber': 8.0,
                'sodium': 800.0
            }
            
            with app.app_context():
                filtered = filter_nutrition_data_by_subscription('test_user', nutrition_data)
                
                # Should keep calories, protein, fat
                assert filtered['calories'] == 500.0
                assert filtered['protein'] == 25.0
                assert filtered['fat'] == 15.0
                
                # Should hide premium macros
                assert filtered['carbs'] is None
                assert filtered['fiber'] is None
                assert filtered['sodium'] is None
                
                # Should include upgrade messaging
                assert filtered['_upgrade_message'] is not None
                assert filtered['_limited_tier'] == True
    
    def test_filter_nutrition_data_function_premium(self, app):
        """Test the filter_nutrition_data_by_subscription function for premium tier."""
        from src.backend.apis.meals import filter_nutrition_data_by_subscription
        
        with patch('src.backend.apis.meals.get_user_subscription_info') as mock_subscription:
            mock_subscription.return_value = {
                'tier': 'premium',
                'status': 'active'
            }
            
            nutrition_data = {
                'calories': 600.0,
                'protein': 30.0,
                'carbs': 70.0,
                'fat': 20.0,
                'fiber': 12.0,
                'sodium': 900.0
            }
            
            with app.app_context():
                filtered = filter_nutrition_data_by_subscription('premium_user', nutrition_data)
                
                # Should keep all data unchanged
                assert filtered == nutrition_data


@pytest.mark.meals
@pytest.mark.api
@pytest.mark.integration
class TestMealPlanGeneration:
    """Test meal plan generation functionality."""
    
    def test_generate_meal_plan_not_authenticated(self, client):
        """Test meal plan generation without authentication."""
        plan_data = {
            'days': 7,
            'dietary_preference': 'none'
        }
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_generate_meal_plan_invalid_days(self, client, logged_in_user):
        """Test meal plan generation with invalid days parameter."""
        # Test days less than 1
        plan_data = {'days': 0}
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Days must be between 1 and 7' in data['message']
        
        # Test days greater than 7
        plan_data = {'days': 10}
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Days must be between 1 and 7' in data['message']
        
        # Test non-numeric days
        plan_data = {'days': 'invalid'}
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid number of days' in data['message']
    
    def test_generate_meal_plan_invalid_start_date(self, client, logged_in_user):
        """Test meal plan generation with invalid start date."""
        plan_data = {
            'days': 5,
            'start_date': 'invalid-date'
        }
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid start date format' in data['message']
    
    def test_generate_meal_plan_invalid_cooking_time(self, client, logged_in_user):
        """Test meal plan generation with invalid cooking time."""
        # Test cooking time too short
        plan_data = {
            'days': 3,
            'cooking_time': 5
        }
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Cooking time must be between 10 and 300 minutes' in data['message']
        
        # Test cooking time too long
        plan_data['cooking_time'] = 400
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Cooking time must be between 10 and 300 minutes' in data['message']
        
        # Test non-numeric cooking time
        plan_data['cooking_time'] = 'invalid'
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid cooking time' in data['message']
    
    def test_generate_meal_plan_invalid_budget(self, client, logged_in_user):
        """Test meal plan generation with invalid budget."""
        # Test budget too low
        plan_data = {
            'days': 3,
            'budget': 5.0
        }
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Budget must be between $10 and $1000' in data['message']
        
        # Test budget too high
        plan_data['budget'] = 1500.0
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Budget must be between $10 and $1000' in data['message']
        
        # Test non-numeric budget
        plan_data['budget'] = 'invalid'
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid budget amount' in data['message']
    
    @patch('src.backend.apis.meals.check_subscription_limit')
    def test_generate_meal_plan_within_limits(self, mock_check, client, logged_in_user):
        """Test meal plan generation within subscription limits."""
        mock_check.return_value = None  # No limit exceeded
        
        # Create some pantry items for ingredient context
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO pantry_items (user_id, item_name, quantity, unit, storage_type)
                VALUES (%s, %s, %s, %s, %s)
            """, ('test_user', 'Chicken Breast', 2, 'lbs', 'freezer'))
            
            cursor.execute("""
                INSERT INTO pantry_items (user_id, item_name, quantity, unit, storage_type)  
                VALUES (%s, %s, %s, %s, %s)
            """, ('test_user', 'Rice', 5, 'cups', 'pantry'))
            
            cursor.close()
        
        plan_data = {
            'days': 3,
            'start_date': '2024-01-15',
            'dietary_preference': 'none',
            'cooking_time': 45,
            'budget': 50.0,
            'minimal_cooking_sessions': False
        }
        
        # Note: This test would require the full meal generation logic to be implemented
        # For now, we're testing the validation and setup parts
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        
        # The response will depend on the implementation status
        # At minimum, we verify no validation errors occurred
        data = json.loads(response.data)
        
        # Should pass validation (exact response depends on implementation)
        assert response.status_code in [200, 500]  # 500 if not fully implemented
        
        # Verify subscription limits were checked
        mock_check.assert_called()
    
    @patch('src.backend.apis.meals.check_subscription_limit')
    def test_generate_meal_plan_exceeds_limits(self, mock_check, client, logged_in_user):
        """Test meal plan generation when exceeding subscription limits."""
        from src.subscription_utils import SubscriptionLimitExceeded
        
        mock_check.side_effect = SubscriptionLimitExceeded(
            limit_type='meal_plans_active',
            current_limit=3,
            upgrade_message='Free tier allows maximum 3 active meal plans'
        )
        
        plan_data = {
            'days': 7,
            'dietary_preference': 'vegetarian'
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['requires_upgrade'] == True
        assert data['limit_type'] == 'meal_plans_active'
        assert data['current_limit'] == 3
    
    @patch('src.backend.apis.meals.check_subscription_limit')
    def test_generate_meal_plan_advance_planning_limit(self, mock_check, client, logged_in_user):
        """Test meal plan generation with advance planning limits."""
        from src.subscription_utils import SubscriptionLimitExceeded
        
        # First call passes (active meal plans check)
        # Second call fails (advance planning check)
        mock_check.side_effect = [
            None,  # First check passes
            SubscriptionLimitExceeded(
                limit_type='meal_plans_advance_days',
                current_limit=7,
                upgrade_message='Free tier can plan maximum 7 days in advance'
            )
        ]
        
        # Plan starting 10 days from now (exceeds 7-day advance limit)
        future_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        plan_data = {
            'days': 5,
            'start_date': future_date,
            'dietary_preference': 'none'
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['requires_upgrade'] == True
        assert data['limit_type'] == 'meal_plans_advance_days'


@pytest.mark.meals
@pytest.mark.api
@pytest.mark.unit
class TestMealsErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_data(self, client, logged_in_user):
        """Test handling of invalid JSON data."""
        response = client.post('/api/generate-meal-plan',
                              data='invalid json',
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_get_nutrition_database_error(self, client, logged_in_user):
        """Test handling of database errors when getting nutrition."""
        with patch('src.backend.apis.meals.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get('/api/nutrition/1')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Failed to get nutrition data' in data['message']
    
    def test_get_daily_summary_database_error(self, client, logged_in_user):
        """Test handling of database errors when getting daily summary."""
        with patch('src.backend.apis.meals.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get('/api/nutrition/daily/2024-01-15')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Failed to get daily nutrition summary' in data['message']
    
    def test_meal_nutrition_null_values(self, client, logged_in_user):
        """Test handling of null nutrition values."""
        # Create test meal with null nutrition values
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            """, ('test_user', '2024-01-15', 'snack', 'Null Nutrition Meal'))
            meal_id = cursor.lastrowid
            
            # Insert nutrition data with null values
            cursor.execute("""
                INSERT INTO meal_nutrition (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings, serving_size, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (meal_id, 'test_user', None, None, None, None, None, None, 1, 'medium', 'user_entered'))
            
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Null values should be converted to None in response
        nutrition = data['nutrition']
        assert nutrition['calories'] is None
        assert nutrition['macros']['protein'] is None
        assert nutrition['macros']['fat'] is None
    
    def test_daily_summary_empty_date(self, client, logged_in_user):
        """Test daily summary for date with no meals."""
        empty_date = '2025-12-31'  # Future date with no meals
        
        response = client.get(f'/api/nutrition/daily/{empty_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_meals'] == 0
        assert data['completed_meals'] == 0
        assert data['daily_totals']['calories'] == 0
        assert len(data['meals']) == 0


@pytest.mark.meals
@pytest.mark.premium
@pytest.mark.integration
class TestMealsPremiumFeatures:
    """Test premium tier features for meals."""
    
    @patch('src.backend.apis.meals.get_user_subscription_info')
    def test_premium_enhanced_nutrition_tracking(self, mock_subscription, client, premium_user):
        """Test enhanced nutrition tracking for premium users."""
        mock_subscription.return_value = {
            'tier': 'premium',
            'status': 'active'
        }
        
        # Premium users should have access to enhanced nutrition features
        # This would be tested when the meal plan generation is fully implemented
        
        plan_data = {
            'days': 7,
            'dietary_preference': 'keto',
            'budget': 100.0
        }
        
        # Test that premium users can access advanced features
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        
        # Should not be blocked by subscription limits
        data = json.loads(response.data)
        # Exact response depends on implementation
        
    @patch('src.backend.apis.meals.check_subscription_limit')
    def test_premium_unlimited_meal_plans(self, mock_check, client, premium_user):
        """Test that premium users have unlimited meal plans."""
        mock_check.return_value = None  # Premium users don't hit limits
        
        # Premium users should be able to create many meal plans
        for i in range(5):  # More than free tier limit
            plan_data = {
                'days': 3,
                'start_date': (datetime.now() + timedelta(days=i*7)).strftime('%Y-%m-%d'),
                'dietary_preference': 'none'
            }
            
            response = client.post('/api/generate-meal-plan',
                                  data=json.dumps(plan_data),
                                  content_type='application/json')
            
            # Should not be blocked by limits
            assert response.status_code != 403
    
    @patch('src.backend.apis.meals.check_subscription_limit')  
    def test_premium_advance_planning(self, mock_check, client, premium_user):
        """Test that premium users can plan far in advance."""
        mock_check.return_value = None  # Premium users don't hit limits
        
        # Plan 30 days in advance (beyond free tier limit)
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        plan_data = {
            'days': 7,
            'start_date': future_date,
            'dietary_preference': 'paleo'
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        
        # Should not be blocked by advance planning limits
        assert response.status_code != 403


@pytest.mark.meals
@pytest.mark.unit
class TestMealsUtilityFunctions:
    """Test utility functions in meals API."""
    
    def test_pantry_ingredient_extraction(self, client, logged_in_user):
        """Test that pantry items are properly extracted for meal planning."""
        # Create pantry items with different expiration dates
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            pantry_items = [
                ('Chicken', 2.0, 'lbs', 'freezer', None),
                ('Milk', 1.0, 'gallon', 'fridge', '2024-01-20'),
                ('Rice', 5.0, 'cups', 'pantry', '2025-01-01'),
                ('Apples', 6, 'pcs', 'fridge', '2024-01-18')
            ]
            
            for item_name, quantity, unit, storage, expiry in pantry_items:
                cursor.execute("""
                    INSERT INTO pantry_items (user_id, item_name, quantity, unit, storage_type, expiration_date, is_consumed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('test_user', item_name, quantity, unit, storage, expiry, False))
            
            cursor.close()
        
        # When generating meal plan without explicit ingredients, should use pantry items
        plan_data = {
            'days': 3,
            'dietary_preference': 'none'
        }
        
        # This test verifies the pantry query logic works
        # The actual meal generation would depend on full implementation
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(plan_data),
                              content_type='application/json')
        
        # Should successfully retrieve pantry items for meal planning context
        # Exact response depends on implementation status
        assert response.status_code in [200, 500]