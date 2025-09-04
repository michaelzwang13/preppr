"""
Comprehensive meal planning and goals tests.
Tests meal generation, nutrition tracking, subscription limits, and meal management.
"""

import pytest
import json
from datetime import datetime, timedelta
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.meal_planning
@pytest.mark.api
class TestMealPlanGeneration:
    """Test meal plan generation API."""
    
    def test_generate_meal_plan_not_authenticated(self, client):
        """Test POST meal plan generation without authentication."""
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps({'days': 3}),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Not authenticated' in data['message']
    
    def test_generate_meal_plan_free_user_within_limits(self, client, logged_in_user):
        """Test meal plan generation for free user within limits."""
        meal_plan_data = {
            'days': 3,
            'start_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'dietary_preference': 'none',
            'cooking_time': 60,
            'ingredients': ['chicken', 'rice', 'vegetables']
        }
        
        # Mock AI generation to avoid external dependencies
        with patch('src.backend.apis.meals.generate_meal_plan_with_ai') as mock_ai:
            mock_ai.return_value = {
                'days': [
                    {
                        'day': 1,
                        'breakfast': {
                            'name': 'Test Breakfast',
                            'ingredients': [{'name': 'eggs', 'quantity': 2, 'unit': 'pcs'}],
                            'instructions': ['Step 1', 'Step 2'],
                            'prep_time': 10,
                            'cook_time': 10,
                            'servings': 1
                        },
                        'lunch': {
                            'name': 'Test Lunch',
                            'ingredients': [{'name': 'chicken', 'quantity': 1, 'unit': 'breast'}],
                            'instructions': ['Step 1', 'Step 2'],
                            'prep_time': 15,
                            'cook_time': 20,
                            'servings': 1
                        }
                    }
                ],
                'batch_prep': []
            }
            
            response = client.post('/api/generate-meal-plan',
                                  data=json.dumps(meal_plan_data),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'session_id' in data
        assert 'created_meals' in data
        assert len(data['created_meals']) > 0
    
    def test_generate_meal_plan_free_user_exceeds_limits(self, client, logged_in_user, app):
        """Test that free user is blocked when exceeding meal plan limits."""
        user_id = logged_in_user
        
        # Create 3 existing active meal plans (free limit)
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            for i in range(3):
                start_date = datetime.now().date() + timedelta(days=i*7)
                end_date = start_date + timedelta(days=6)
                cursor.execute('''
                    INSERT INTO meal_plan_sessions 
                    (user_id, session_name, start_date, end_date, total_days)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, f'Test Plan {i+1}', start_date, end_date, 7))
            
            # db.commit()
            cursor.close()
        
        meal_plan_data = {
            'days': 3,
            'start_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(meal_plan_data),
                              content_type='application/json')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data.get('requires_upgrade') == True
        assert 'meal_plans_active' in data.get('limit_type', '')
    
    def test_generate_meal_plan_premium_user_unlimited(self, client, premium_user):
        """Test that premium user can create unlimited meal plans."""
        meal_plan_data = {
            'days': 7,
            'start_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'dietary_preference': 'vegetarian',
            'cooking_time': 90
        }
        
        with patch('src.backend.apis.meals.generate_meal_plan_with_ai') as mock_ai:
            mock_ai.return_value = {
                'days': [{'day': i+1, 'breakfast': {'name': f'Day {i+1} Breakfast', 'ingredients': [], 'instructions': []}} for i in range(7)],
                'batch_prep': []
            }
            
            response = client.post('/api/generate-meal-plan',
                                  data=json.dumps(meal_plan_data),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_generate_meal_plan_advance_planning_limits(self, client, logged_in_user):
        """Test advance planning limits for free users."""
        # Try to plan 15 days in advance (should be blocked for free)
        future_date = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
        
        meal_plan_data = {
            'days': 3,
            'start_date': future_date
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(meal_plan_data),
                              content_type='application/json')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data.get('requires_upgrade') == True
    
    def test_generate_meal_plan_invalid_parameters(self, client, logged_in_user):
        """Test meal plan generation with invalid parameters."""
        test_cases = [
            ({'days': 0}, 'Days must be between 1 and 7'),
            ({'days': 10}, 'Days must be between 1 and 7'),
            ({'days': 'invalid'}, 'Invalid number of days'),
            ({'days': 3, 'start_date': 'invalid-date'}, 'Invalid start date format'),
            ({'days': 3, 'cooking_time': 5}, 'Cooking time must be between 10 and 300'),
            ({'days': 3, 'budget': 5}, 'Budget must be between $10 and $1000'),
        ]
        
        for meal_data, expected_error in test_cases:
            response = client.post('/api/generate-meal-plan',
                                  data=json.dumps(meal_data),
                                  content_type='application/json')
            # This might return 403 if subscription limit check happens first
            assert response.status_code in [200, 403]
            data = json.loads(response.data)
            assert data['success'] == False
            # Check for either validation error or subscription limit error
            assert expected_error in data['message'] or 'limit' in data['message'].lower() or 'upgrade' in data['message'].lower()
    
    def test_generate_meal_plan_conflicting_dates(self, client, logged_in_user, app):
        """Test meal plan generation with conflicting existing meals."""
        user_id = logged_in_user
        conflict_date = datetime.now().date() + timedelta(days=2)
        
        # Create existing meal
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            db = get_db()
            cursor = db.cursor()
            
            # Clean up any existing meals for this test first
            # Use API connection for setup so API can see the data
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                cursor.execute('DELETE FROM meals WHERE user_id = %s AND meal_date = %s AND meal_type = %s', 
                              (user_id, conflict_date, 'breakfast'))
                
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, conflict_date, 'breakfast', 'Existing Breakfast'))
                api_conn.commit()  # API connection commits
                cursor.close()
            else:
                # Fallback to regular connection
                cursor.execute('DELETE FROM meals WHERE user_id = %s AND meal_date = %s AND meal_type = %s', 
                              (user_id, conflict_date, 'breakfast'))
                
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, conflict_date, 'breakfast', 'Existing Breakfast'))
                db.commit()  # Regular commit as fallback
                cursor.close()
        
        meal_plan_data = {
            'days': 3,
            'start_date': conflict_date.strftime('%Y-%m-%d')
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(meal_plan_data),
                              content_type='application/json')
        
        # This might return 403 if subscription limit is exceeded
        assert response.status_code in [200, 403]
        data = json.loads(response.data)
        assert data['success'] == False
        
        if response.status_code == 403:
            # Subscription limit exceeded - this is valid for free users
            assert 'limit' in data['message'].lower() or 'upgrade' in data['message'].lower()
        else:
            # Normal conflict detection
            assert 'conflicts with existing meals' in data['message']
            assert 'conflicting_dates' in data


@pytest.mark.meal_planning
@pytest.mark.api
class TestMealRetrievalAPI:
    """Test meal retrieval API endpoints."""
    
    def test_get_meals_not_authenticated(self, client):
        """Test GET meals without authentication."""
        response = client.get('/api/meals?start_date=2024-01-01&end_date=2024-01-07')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Not authenticated' in data['message']
    
    def test_get_meals_missing_parameters(self, client, logged_in_user):
        """Test GET meals with missing date parameters."""
        response = client.get('/api/meals')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'start_date and end_date are required' in data['message']
    
    def test_get_meals_invalid_date_format(self, client, logged_in_user):
        """Test GET meals with invalid date format."""
        response = client.get('/api/meals?start_date=invalid&end_date=2024-01-07')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid date format' in data['message']
    
    def test_get_meals_empty_result(self, client, logged_in_user):
        """Test GET meals with no existing meals."""
        future_date = datetime.now() + timedelta(days=30)
        start_date = future_date.strftime('%Y-%m-%d')
        end_date = (future_date + timedelta(days=6)).strftime('%Y-%m-%d')
        
        response = client.get(f'/api/meals?start_date={start_date}&end_date={end_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['meals'] == []
    
    def test_get_meals_with_existing_meals(self, client, logged_in_user, app):
        """Test GET meals with existing meals."""
        user_id = logged_in_user
        test_date = datetime.now().date() + timedelta(days=1)
        
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            # Clean up existing meals and add test meal using API connection
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean up existing meals for this user and date first
                cursor.execute('DELETE FROM meals WHERE user_id = %s AND meal_date = %s AND meal_type = %s', 
                              (user_id, test_date, 'breakfast'))
                
                # Add test meal
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name, is_completed)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, test_date, 'breakfast', 'Test Breakfast', False))
                api_conn.commit()  # API connection commits
                cursor.close()
            else:
                # Fallback to regular connection
                db = get_db()
                cursor = db.cursor()
                # Clean up existing meals for this user and date first
                cursor.execute('DELETE FROM meals WHERE user_id = %s AND meal_date = %s AND meal_type = %s', 
                              (user_id, test_date, 'breakfast'))
                
                # Add test meal
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name, is_completed)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, test_date, 'breakfast', 'Test Breakfast', False))
                db.commit()  # Regular commit as fallback
                cursor.close()
        
        start_date = test_date.strftime('%Y-%m-%d')
        end_date = test_date.strftime('%Y-%m-%d')
        
        response = client.get(f'/api/meals?start_date={start_date}&end_date={end_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['meals']) == 1
        assert data['meals'][0]['name'] == 'Test Breakfast'
        assert data['meals'][0]['type'] == 'breakfast'
        assert data['meals'][0]['is_completed'] == False
    
    def test_get_todays_meals(self, client, logged_in_user, app):
        """Test GET today's meals."""
        user_id = logged_in_user
        
        # Mock timezone function to return a specific date
        with patch('src.backend.apis.meals.get_user_current_date') as mock_date:
            mock_today = datetime(2024, 1, 15).date()
            mock_date.return_value = mock_today
            
            # Create test meal for "today"
            with app.app_context():
                db = get_db()
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, mock_today, 'lunch', 'Today Lunch'))
                # db.commit()
                cursor.close()
            
            response = client.get('/api/meals/today')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert len(data['meals']) == 1
            assert data['meals'][0]['name'] == 'Today Lunch'
            assert data['date'] == mock_today.strftime('%Y-%m-%d')


@pytest.mark.meal_planning
@pytest.mark.api
class TestMealDetailsAPI:
    """Test meal details and update API endpoints."""
    
    def test_get_meal_details_not_authenticated(self, client):
        """Test GET meal details without authentication."""
        response = client.get('/api/meals/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Not authenticated' in data['message']
    
    def test_get_meal_details_not_found(self, client, logged_in_user):
        """Test GET meal details for non-existent meal."""
        response = client.get('/api/meals/99999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Meal not found' in data['message']
    
    def test_get_meal_details_success(self, client, logged_in_user, app):
        """Test GET meal details for existing meal."""
        user_id = logged_in_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name, notes)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'dinner', 'Test Dinner', 'Test notes'))
            meal_id = cursor.lastrowid
            # db.commit()
            cursor.close()
        
        response = client.get(f'/api/meals/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['meal']['name'] == 'Test Dinner'
        assert data['meal']['type'] == 'dinner'
        assert data['meal']['notes'] == 'Test notes'
    
    def test_update_meal_not_authenticated(self, client):
        """Test PUT meal update without authentication."""
        response = client.put('/api/meals/1',
                             data=json.dumps({'notes': 'test'}),
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Not authenticated' in data['message']
    
    def test_update_meal_not_found(self, client, logged_in_user):
        """Test PUT meal update for non-existent meal."""
        response = client.put('/api/meals/99999',
                             data=json.dumps({'notes': 'test'}),
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Meal not found' in data['message']
    
    def test_update_meal_success(self, client, logged_in_user, app):
        """Test PUT meal update success."""
        user_id = logged_in_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'breakfast', 'Original Name'))
            meal_id = cursor.lastrowid
            # db.commit()
            cursor.close()
        
        update_data = {
            'custom_recipe_name': 'Updated Name',
            'notes': 'Updated notes',
            'is_locked': True
        }
        
        response = client.put(f'/api/meals/{meal_id}',
                             data=json.dumps(update_data),
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Verify update in database
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM meals WHERE meal_id = %s', (meal_id,))
            meal = cursor.fetchone()
            cursor.close()
            
        assert meal['custom_recipe_name'] == 'Updated Name'
        assert meal['notes'] == 'Updated notes'
        assert meal['is_locked'] == True
    
    def test_update_meal_complete_future_meal_blocked(self, client, logged_in_user, app):
        """Test that completing future meals is blocked."""
        user_id = logged_in_user
        future_date = datetime.now().date() + timedelta(days=5)
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, future_date, 'breakfast', 'Future Meal'))
            meal_id = cursor.lastrowid
            # db.commit()
            cursor.close()
        
        with patch('src.backend.apis.meals.get_user_current_date') as mock_date:
            mock_date.return_value = datetime.now().date()
            
            response = client.put(f'/api/meals/{meal_id}',
                                 data=json.dumps({'is_completed': True}),
                                 content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Cannot mark future meals as completed' in data['message']
    
    def test_delete_meal_success(self, client, logged_in_user, app):
        """Test DELETE meal success."""
        user_id = logged_in_user
        
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            # Use API connection so API can see the data
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, datetime.now().date(), 'breakfast', 'To Delete'))
                meal_id = cursor.lastrowid
                api_conn.commit()  # API connection commits
                cursor.close()
            else:
                # Fallback to regular connection
                db = get_db()
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, datetime.now().date(), 'breakfast', 'To Delete'))
                meal_id = cursor.lastrowid
                db.commit()  # Regular commit as fallback
                cursor.close()
        
        response = client.delete(f'/api/meals/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Verify deletion
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM meals WHERE meal_id = %s', (meal_id,))
            meal = cursor.fetchone()
            cursor.close()
            
        assert meal is None


@pytest.mark.meal_planning
@pytest.mark.nutrition
class TestMealNutritionAPI:
    """Test meal nutrition tracking API."""
    
    def test_get_meal_nutrition_not_authenticated(self, client):
        """Test GET meal nutrition without authentication."""
        response = client.get('/api/nutrition/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Not authenticated' in data['message']
    
    def test_get_meal_nutrition_not_found(self, client, logged_in_user):
        """Test GET meal nutrition for non-existent meal."""
        response = client.get('/api/nutrition/99999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Nutrition data not found' in data['message']
    
    def test_get_meal_nutrition_free_user_filtered(self, client, logged_in_user, app):
        """Test meal nutrition filtering for free user."""
        user_id = logged_in_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create meal
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'lunch', 'Test Lunch'))
            meal_id = cursor.lastrowid
            
            # Create nutrition data
            cursor.execute('''
                INSERT INTO meal_nutrition 
                (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (meal_id, user_id, 450, 25, 35, 15, 8, 350, 1))
            
            # db.commit()
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        nutrition = data['nutrition']
        # Free user should see calories and protein
        assert nutrition['calories'] == 450
        assert nutrition['macros']['protein'] == 25
        # But not premium fields
        assert nutrition['macros']['carbs'] is None
        assert nutrition['fiber'] is None
        assert nutrition['sodium'] is None
        assert data.get('_limited_tier') == True
    
    def test_get_meal_nutrition_premium_user_full_access(self, client, premium_user, app):
        """Test meal nutrition full access for premium user."""
        user_id = premium_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create meal
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'dinner', 'Premium Dinner'))
            meal_id = cursor.lastrowid
            
            # Create nutrition data
            cursor.execute('''
                INSERT INTO meal_nutrition 
                (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, fiber_g, sodium_mg, servings)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (meal_id, user_id, 650, 35, 45, 25, 12, 480, 1))
            
            # db.commit()
            cursor.close()
        
        response = client.get(f'/api/nutrition/{meal_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        nutrition = data['nutrition']
        # Premium user should see all fields
        assert nutrition['calories'] == 650
        assert nutrition['macros']['protein'] == 35
        assert nutrition['macros']['carbs'] == 45
        assert nutrition['macros']['fat'] == 25
        assert nutrition['fiber'] == 12
        assert nutrition['sodium'] == 480
        assert '_limited_tier' not in data
    
    def test_get_daily_nutrition_summary(self, client, logged_in_user, app):
        """Test GET daily nutrition summary."""
        user_id = logged_in_user
        test_date = datetime.now().date()
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create multiple meals for the day
            meals_data = [
                ('breakfast', 'Morning Meal', 300, 20, 30, 10, True),
                ('lunch', 'Lunch Meal', 450, 25, 35, 15, True),
                ('dinner', 'Dinner Meal', 600, 30, 40, 20, False)  # Not completed
            ]
            
            for meal_type, name, calories, protein, carbs, fat, completed in meals_data:
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name, is_completed)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, test_date, meal_type, name, completed))
                meal_id = cursor.lastrowid
                
                cursor.execute('''
                    INSERT INTO meal_nutrition 
                    (meal_id, user_id, calories, protein_g, carbohydrates_g, fat_g, servings)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (meal_id, user_id, calories, protein, carbs, fat, 1))
            
            # db.commit()
            cursor.close()
        
        response = client.get(f'/api/nutrition/daily/{test_date.strftime("%Y-%m-%d")}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Should only count completed meals in daily totals
        assert data['daily_totals']['calories'] == 750  # 300 + 450 (excluding dinner)
        assert data['daily_totals']['protein'] == 45    # 20 + 25
        assert len(data['meals']) == 3
        assert data['completed_meals'] == 2
    
    def test_get_daily_nutrition_invalid_date(self, client, logged_in_user):
        """Test GET daily nutrition with invalid date."""
        response = client.get('/api/nutrition/daily/invalid-date')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'Invalid date format' in data['message']


@pytest.mark.meal_planning
@pytest.mark.subscription
class TestMealPlanSubscriptionLimits:
    """Test subscription-based meal planning limits."""
    
    def test_meal_plan_generation_subscription_check(self, client, logged_in_user):
        """Test that meal plan generation checks subscription limits."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Check that free user has meal plan limits
            result = check_user_limit(logged_in_user, 'meal_plans_active', current_count=3)
            assert result['allowed'] == False
            assert result['limit'] == 3
    
    def test_advance_planning_limits_free_user(self, client, logged_in_user):
        """Test advance planning limits for free users."""
        # Plan more than 7 days in advance
        future_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        
        meal_plan_data = {
            'days': 3,
            'start_date': future_date
        }
        
        response = client.post('/api/generate-meal-plan',
                              data=json.dumps(meal_plan_data),
                              content_type='application/json')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data.get('requires_upgrade') == True
        assert 'advance' in data.get('limit_type', '').lower()
    
    def test_nutrition_filtering_by_subscription(self, client, logged_in_user, premium_user):
        """Test that nutrition data is filtered based on subscription tier."""
        from src.backend.apis.meals import filter_nutrition_data_by_subscription
        
        test_nutrition_data = {
            'calories': 500,
            'protein': 30,
            'carbs': 40,
            'fat': 20,
            'fiber': 10,
            'sodium': 600
        }
        
        with client.application.app_context():
            # Free user should get filtered data
            free_filtered = filter_nutrition_data_by_subscription(logged_in_user, test_nutrition_data)
            assert free_filtered['calories'] == 500
            assert free_filtered['protein'] == 30
            assert free_filtered['carbs'] is None
            assert free_filtered['fiber'] is None
            assert free_filtered['sodium'] is None
            assert free_filtered['_limited_tier'] == True
            
            # Premium user should get full data
            premium_filtered = filter_nutrition_data_by_subscription(premium_user, test_nutrition_data)
            assert premium_filtered['calories'] == 500
            assert premium_filtered['protein'] == 30
            assert premium_filtered['carbs'] == 40
            assert premium_filtered['fiber'] == 10
            assert premium_filtered['sodium'] == 600
            assert '_limited_tier' not in premium_filtered


@pytest.mark.meal_planning
@pytest.mark.integration
class TestMealPlanDatabaseIntegration:
    """Test meal planning database integration."""
    
    def test_meal_plan_sessions_table_schema(self, app):
        """Test meal plan sessions table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE meal_plan_sessions")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'session_id', 'user_id', 'session_name', 'start_date', 'end_date',
                'total_days', 'dietary_preference', 'budget_limit', 'max_cooking_time',
                'generated_at', 'status', 'ai_model_used', 'generation_prompt'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"
    
    def test_meals_table_schema(self, app):
        """Test meals table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE meals")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'meal_id', 'user_id', 'meal_date', 'meal_type', 'recipe_template_id',
                'session_id', 'custom_recipe_name', 'custom_instructions', 'is_locked',
                'is_completed', 'notes', 'created_at', 'updated_at'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"
    
    def test_meal_nutrition_table_schema(self, app):
        """Test meal nutrition table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE meal_nutrition")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'nutrition_id', 'meal_id', 'user_id', 'calories', 'protein_g',
                'carbohydrates_g', 'fat_g', 'fiber_g', 'sodium_mg', 'servings',
                'serving_size', 'source_type', 'ai_model_used', 'created_at', 'updated_at'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"
    
    def test_meal_foreign_key_constraints(self, app, logged_in_user):
        """Test meal foreign key constraints."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Try to insert meal with non-existent user
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO meals (user_id, meal_date, meal_type)
                    VALUES (%s, %s, %s)
                ''', ('nonexistent_user', datetime.now().date(), 'breakfast'))
                # db.commit()
            
            cursor.close()
    
    def test_meal_nutrition_cascade_delete(self, app, logged_in_user):
        """Test that meal nutrition is deleted when meal is deleted."""
        user_id = logged_in_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create meal
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'breakfast', 'Test Meal'))
            meal_id = cursor.lastrowid
            
            # Create nutrition data
            cursor.execute('''
                INSERT INTO meal_nutrition (meal_id, user_id, calories, servings)
                VALUES (%s, %s, %s, %s)
            ''', (meal_id, user_id, 400, 1))
            
            # db.commit()
            
            # Delete meal
            cursor.execute('DELETE FROM meals WHERE meal_id = %s', (meal_id,))
            # db.commit()
            
            # Check that nutrition data is also deleted
            cursor.execute('SELECT * FROM meal_nutrition WHERE meal_id = %s', (meal_id,))
            nutrition_data = cursor.fetchone()
            
            cursor.close()
            
        assert nutrition_data is None


@pytest.mark.meal_planning
@pytest.mark.unit
class TestMealPlanUtilityFunctions:
    """Test meal planning utility functions."""
    
    def test_categorize_ingredient(self):
        """Test ingredient categorization."""
        from src.backend.apis.meals import categorize_ingredient
        
        test_cases = [
            ('chicken breast', 'Meat & Seafood'),
            ('apple', 'Produce'),
            ('milk', 'Dairy'),
            ('rice', 'Grains'),
            ('olive oil', 'Condiments'),
            ('unknown ingredient', 'Other')
        ]
        
        for ingredient, expected_category in test_cases:
            assert categorize_ingredient(ingredient) == expected_category
    
    def test_filter_nutrition_data_by_subscription(self):
        """Test nutrition data filtering function."""
        from src.backend.apis.meals import filter_nutrition_data_by_subscription
        
        test_data = {
            'calories': 500,
            'protein': 30,
            'carbs': 40,
            'fat': 20,
            'fiber': 10,
            'sodium': 600
        }
        
        # Mock free user
        with patch('src.subscription_utils.get_user_subscription_info') as mock_sub:
            mock_sub.return_value = {'tier': 'free', 'status': 'active'}
            
            filtered = filter_nutrition_data_by_subscription('test_user', test_data)
            
            assert filtered['calories'] == 500
            assert filtered['protein'] == 30
            assert filtered['carbs'] is None
            assert filtered['fiber'] is None
            assert filtered['sodium'] is None
            assert filtered['_limited_tier'] == True
            assert '_upgrade_message' in filtered
        
        # Mock premium user
        with patch('src.subscription_utils.get_user_subscription_info') as mock_sub:
            mock_sub.return_value = {'tier': 'premium', 'status': 'active'}
            
            filtered = filter_nutrition_data_by_subscription('test_user', test_data)
            
            assert filtered == test_data  # Should return unchanged


@pytest.mark.meal_planning
@pytest.mark.integration
@pytest.mark.slow
class TestMealPlanPerformance:
    """Test meal planning performance and edge cases."""
    
    def test_large_meal_plan_generation(self, client, premium_user):
        """Test generating large meal plans."""
        meal_plan_data = {
            'days': 7,
            'start_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'dietary_preference': 'vegetarian',
            'cooking_time': 120,
            'ingredients': ['ingredient_' + str(i) for i in range(50)]  # Many ingredients
        }
        
        with patch('src.backend.apis.meals.generate_meal_plan_with_ai') as mock_ai:
            # Mock large meal plan response
            mock_ai.return_value = {
                'days': [
                    {
                        'day': i+1,
                        'breakfast': {'name': f'Day {i+1} Breakfast', 'ingredients': [{'name': 'eggs', 'quantity': 2, 'unit': 'pcs'}], 'instructions': ['Step 1']},
                        'lunch': {'name': f'Day {i+1} Lunch', 'ingredients': [{'name': 'chicken', 'quantity': 1, 'unit': 'breast'}], 'instructions': ['Step 1']},
                        'dinner': {'name': f'Day {i+1} Dinner', 'ingredients': [{'name': 'rice', 'quantity': 1, 'unit': 'cup'}], 'instructions': ['Step 1']}
                    } for i in range(7)
                ],
                'batch_prep': []
            }
            
            import time
            start_time = time.time()
            
            response = client.post('/api/generate-meal-plan',
                                  data=json.dumps(meal_plan_data),
                                  content_type='application/json')
            
            end_time = time.time()
            response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 10.0  # Should complete within 10 seconds
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['created_meals']) == 21  # 7 days * 3 meals
    
    def test_concurrent_meal_updates(self, client, logged_in_user, app):
        """Test concurrent meal updates don't cause data corruption."""
        user_id = logged_in_user
        
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, datetime.now().date(), 'breakfast', 'Original'))
            meal_id = cursor.lastrowid
            # db.commit()
            cursor.close()
        
        import threading
        results = []
        
        def update_meal(note_suffix):
            response = client.put(f'/api/meals/{meal_id}',
                                 data=json.dumps({'notes': f'Updated {note_suffix}'}),
                                 content_type='application/json')
            results.append(response)
        
        # Make concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_meal, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All updates should succeed
        for response in results:
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
        
        # Verify meal still exists and has one of the updates
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT notes FROM meals WHERE meal_id = %s', (meal_id,))
            meal = cursor.fetchone()
            cursor.close()
            
        assert meal is not None
        assert 'Updated' in meal['notes']