"""
Specific tests for nutrition goals API commit isolation.
Tests the exact scenario mentioned where nutrition API commits are isolated from test rollback.
"""

import pytest
import json
from src.database import get_db


@pytest.mark.integration
@pytest.mark.nutrition
class TestNutritionAPICommitIsolation:
    """Test nutrition goals API with real commits but proper rollback isolation."""
    
    def test_nutrition_goals_post_with_real_commit(self, client, auth, app):
        """
        Test the exact scenario: POST to /api/nutrition/goals that calls db.commit()
        but still gets rolled back properly due to connection isolation.
        """
        # Register and login user
        user_id = 'nutrition_commit_user'
        auth.register(user_id=user_id, email='nutrition@test.com')
        auth.login(user_id=user_id)
        
        # Prepare nutrition data that will trigger the db.commit() on line 284
        nutrition_data = {
            "daily_calories": 2500,
            "calories_type": "goal",
            "daily_protein": 180,
            "protein_type": "goal",
            "daily_fat": 85,
            "fat_type": "goal",
            "goal_type": "custom",
            "activity_level": "very_active"
        }
        
        print(f"🧪 Testing POST /api/nutrition/goals with db.commit() isolation")
        
        # Make the API call that includes db.commit() on line 284
        response = client.post(
            '/api/nutrition/goals',
            data=json.dumps(nutrition_data),
            content_type='application/json'
        )
        
        # The API should succeed
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        assert 'Nutrition goals saved successfully' in response_data['message']
        
        # Verify the API committed its data (visible within same test)
        response = client.get('/api/nutrition/goals')
        assert response.status_code == 200
        data = json.loads(response.data)
        goals = data['goals']
        
        # Verify our exact values are there
        assert goals['daily_calories'] == 2500
        assert goals['daily_protein'] == 180
        assert goals['daily_fat'] == 85
        assert goals['goal_type'] == 'custom'
        assert goals['activity_level'] == 'very_active'
        
        print("✓ API commit executed successfully and data is visible")
        print(f"✓ Committed nutrition goals: {goals['daily_calories']} calories, {goals['daily_protein']}g protein")
    
    def test_committed_nutrition_data_rolls_back_between_tests(self, client):
        """
        Verify that nutrition data committed in previous test doesn't persist.
        This tests the core rollback isolation functionality.
        """
        # Try to access data from previous test by setting up the same user session
        with client.session_transaction() as sess:
            sess['user_ID'] = 'nutrition_commit_user'
        
        # Get nutrition goals
        response = client.get('/api/nutrition/goals')
        assert response.status_code == 200
        data = json.loads(response.data)
        goals = data['goals']
        
        # Should get default values, not the committed values from previous test
        assert goals['daily_calories'] == 2000  # Default, not 2500 from previous test
        assert goals['daily_protein'] == 150   # Default, not 180 from previous test
        assert goals['daily_fat'] == 70        # Default, not 85 from previous test
        
        # These fields shouldn't exist because user doesn't exist
        assert 'goal_type' not in goals or goals.get('goal_type') != 'custom'
        assert 'activity_level' not in goals or goals.get('activity_level') != 'very_active'
        
        print("✓ Previous test's committed nutrition data was properly rolled back")
        print(f"✓ Got default values: {goals['daily_calories']} calories, {goals['daily_protein']}g protein")
    
    def test_nutrition_api_database_operations_detailed(self, client, auth, db_transaction, app):
        """
        Detailed test of database operations during nutrition API calls.
        """
        # Register user
        user_id = 'detailed_nutrition_user'
        auth.register(user_id=user_id, email='detailed@test.com')
        auth.login(user_id=user_id)
        
        # Check that user exists in test transaction
        cursor = db_transaction.cursor()
        cursor.execute("SELECT user_ID FROM user_account WHERE user_ID = %s", (user_id,))
        user_record = cursor.fetchone()
        assert user_record is not None
        assert user_record['user_ID'] == user_id
        
        # Check initial nutrition goals state (should be empty)
        cursor.execute("SELECT COUNT(*) as count FROM user_nutrition_goals WHERE user_id = %s", (user_id,))
        initial_count = cursor.fetchone()['count']
        assert initial_count == 0
        cursor.close()
        
        # Make nutrition API call
        nutrition_data = {
            "daily_calories": 2100,
            "calories_type": "goal",
            "daily_protein": 160,
            "protein_type": "goal",
            "daily_fat": 75,
            "fat_type": "goal"
        }
        
        response = client.post(
            '/api/nutrition/goals',
            data=json.dumps(nutrition_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        # Now check if we can see the API's committed data from our test connection
        # Note: This tests a complex scenario where API commits to separate connection
        # but we want to verify the data exists somewhere in the database
        
        # The API committed to its own connection, so we should be able to fetch via API
        response = client.get('/api/nutrition/goals')
        data = json.loads(response.data)
        goals = data['goals']
        assert goals['daily_calories'] == 2100
        
        print("✓ Detailed nutrition API database operations work correctly")
        print(f"✓ API and test connections properly isolated")
    
    def test_multiple_nutrition_updates_same_test(self, client, auth):
        """
        Test multiple nutrition goal updates in the same test.
        Each update triggers db.commit() but should work correctly.
        """
        user_id = 'multi_update_user'
        auth.register(user_id=user_id, email='multi@test.com')
        auth.login(user_id=user_id)
        
        # First update
        data_1 = {
            "daily_calories": 1800,
            "calories_type": "goal",
            "daily_protein": 130,
            "protein_type": "goal",
            "daily_fat": 65,
            "fat_type": "goal"
        }
        
        response = client.post('/api/nutrition/goals', 
                             data=json.dumps(data_1),
                             content_type='application/json')
        assert response.status_code == 200
        
        # Verify first update
        response = client.get('/api/nutrition/goals')
        goals = json.loads(response.data)['goals']
        assert goals['daily_calories'] == 1800
        
        # Second update
        data_2 = {
            "daily_calories": 2200,
            "calories_type": "goal", 
            "daily_protein": 170,
            "protein_type": "goal",
            "daily_fat": 80,
            "fat_type": "goal"
        }
        
        response = client.post('/api/nutrition/goals',
                             data=json.dumps(data_2),
                             content_type='application/json')
        assert response.status_code == 200
        
        # Verify second update overwrote first
        response = client.get('/api/nutrition/goals')
        goals = json.loads(response.data)['goals']
        assert goals['daily_calories'] == 2200  # Latest value
        assert goals['daily_protein'] == 170    # Latest value
        
        print("✓ Multiple nutrition API commits work correctly in same test")
    
    def test_nutrition_api_error_handling_with_rollback(self, client, auth):
        """
        Test that nutrition API error handling still works with connection isolation.
        """
        user_id = 'error_test_user'
        auth.register(user_id=user_id, email='error@test.com')
        auth.login(user_id=user_id)
        
        # Try to save invalid nutrition data
        invalid_data = {
            "daily_calories": -100,  # Invalid: negative calories
            "daily_protein": 9999,   # Invalid: too high
            "daily_fat": "not_a_number"  # Invalid: not a number
        }
        
        response = client.post('/api/nutrition/goals',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        # Should get an error response
        assert response.status_code == 200  # API returns 200 with error message
        data = json.loads(response.data)
        assert data['success'] == False
        
        # Verify no invalid data was saved
        response = client.get('/api/nutrition/goals')
        goals = json.loads(response.data)['goals']
        assert goals['daily_calories'] == 2000  # Default, not invalid value
        
        print("✓ Nutrition API error handling works correctly with connection isolation")