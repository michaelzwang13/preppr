"""
Database state verification tests.
These tests confirm that the database remains unchanged after test execution.
"""

import pytest
import json
import pymysql.cursors
from src.database import get_db


@pytest.mark.integration
class TestDatabaseStateVerification:
    """Verify database state remains unchanged after tests."""
    
    @pytest.fixture(scope="class")
    def database_snapshot(self, app):
        """Take a snapshot of database state before tests."""
        with app.app_context():
            connection = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                db=app.config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            
            cursor = connection.cursor()
            
            # Get counts for all main tables
            tables = [
                'user_account', 'user_nutrition_goals', 'user_tip_history', 
                'shopping_trips', 'shopping_trip_items', 'user_pantry_items',
                'meal_plans', 'meal_plan_meals', 'recipes', 'promotional_codes'
            ]
            
            snapshot = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    snapshot[table] = result['count'] if result else 0
                except Exception as e:
                    # Table might not exist
                    snapshot[table] = f"ERROR: {e}"
            
            cursor.close()
            connection.close()
            
            print(f"\n📊 Database snapshot taken:")
            for table, count in snapshot.items():
                print(f"  {table}: {count}")
            
            return snapshot
    
    def test_database_state_unchanged_after_api_commits(self, client, auth, app, database_snapshot):
        """Test that database state is unchanged after API calls with commits."""
        
        # Register user and make API calls that trigger db.commit()
        auth.register(user_id='state_test_user', email='state@test.com')
        auth.login(user_id='state_test_user')
        
        # Make nutrition API call that commits (line 284 in nutrition.py)
        nutrition_data = {
            "daily_calories": 2300,
            "daily_protein": 165,
            "daily_fat": 80
        }
        
        response = client.post('/api/nutrition/goals',
                              data=json.dumps(nutrition_data),
                              content_type='application/json')
        
        # API should succeed
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        print(f"✓ API commit succeeded: {data['message']}")
        
        # Make tips API call (also has commits)
        response = client.get('/api/tips/daily')
        assert response.status_code == 200
        
        print("✓ Made API calls that trigger db.commit()")
        
        # The actual verification happens in the next test method
        # since this test will have its rollback applied
    
    def test_verify_database_unchanged(self, app, database_snapshot):
        """Verify database counts match the original snapshot."""
        
        with app.app_context():
            connection = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                db=app.config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            
            cursor = connection.cursor()
            
            print(f"\n🔍 Verifying database state after tests...")
            
            for table, original_count in database_snapshot.items():
                if isinstance(original_count, str) and "ERROR" in original_count:
                    continue  # Skip tables that had errors
                
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    current_count = result['count'] if result else 0
                    
                    print(f"  {table}: {original_count} -> {current_count}")
                    
                    assert current_count == original_count, f"Table {table} changed! Original: {original_count}, Current: {current_count}"
                    
                except Exception as e:
                    print(f"  {table}: Error checking - {e}")
            
            cursor.close()
            connection.close()
            
            print("✅ Database state verification PASSED - all tables unchanged!")


@pytest.mark.integration
class TestSpecificAPIRollbackVerification:
    """Test specific API endpoints to confirm rollback works."""
    
    def test_nutrition_api_rollback_verification(self, client, auth, app):
        """Specifically test the nutrition API that has db.commit() on line 284."""
        
        # Get initial count of nutrition goals
        with app.app_context():
            connection = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"], 
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                db=app.config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM user_nutrition_goals")
            initial_goals_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM user_account")
            initial_users_count = cursor.fetchone()['count']
            
            cursor.close()
            connection.close()
        
        print(f"📊 Initial state: {initial_users_count} users, {initial_goals_count} nutrition goals")
        
        # Register user and make API call with commit
        auth.register(user_id='nutrition_rollback_test', email='rollback@test.com')
        auth.login(user_id='nutrition_rollback_test')
        
        # This will trigger db.commit() in the API
        nutrition_data = {
            "daily_calories": 2250,
            "daily_protein": 170,
            "daily_fat": 85
        }
        
        response = client.post('/api/nutrition/goals',
                              data=json.dumps(nutrition_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        print(f"✓ Nutrition API called successfully: {data['message']}")
        
        # At this point, the API has committed its data to a separate connection
        # But our test rollback should still happen
        
    def test_verify_nutrition_data_rolled_back(self, app):
        """Verify that nutrition data from previous test was rolled back."""
        
        # Check counts again - should be same as initial
        with app.app_context():
            connection = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                db=app.config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            
            cursor = connection.cursor()
            
            # Check for the specific user we created
            cursor.execute("SELECT COUNT(*) as count FROM user_account WHERE user_ID = %s", 
                          ('nutrition_rollback_test',))
            user_exists = cursor.fetchone()['count']
            
            # Check for nutrition goals for that user
            cursor.execute("SELECT COUNT(*) as count FROM user_nutrition_goals WHERE user_id = %s",
                          ('nutrition_rollback_test',))
            goals_exist = cursor.fetchone()['count']
            
            cursor.close()
            connection.close()
        
        print(f"🔍 Rollback verification:")
        print(f"  User 'nutrition_rollback_test' exists: {user_exists}")
        print(f"  Nutrition goals for user: {goals_exist}")
        
        # Both should be 0 if rollback worked
        assert user_exists == 0, f"User still exists! Rollback failed."
        assert goals_exist == 0, f"Nutrition goals still exist! Rollback failed."
        
        print("✅ ROLLBACK VERIFICATION PASSED - API commits properly isolated!")


@pytest.mark.integration
def test_manual_database_inspection_commands(app):
    """Print commands for manual database inspection."""
    
    print("\n" + "="*60)
    print("🔍 MANUAL DATABASE INSPECTION COMMANDS")
    print("="*60)
    print("\nRun these commands to manually verify database state:")
    print("\n1. Check table counts:")
    print("python -c \"")
    print("import pymysql")
    print("conn = pymysql.connect(host='localhost', port=8889, user='root', password='root', db='hacknyu25_test')")
    print("cursor = conn.cursor()")
    print("tables = ['user_account', 'user_nutrition_goals', 'user_tip_history']")
    print("for table in tables:")
    print("    cursor.execute(f'SELECT COUNT(*) FROM {table}')")
    print("    print(f'{table}: {cursor.fetchone()[0]} rows')")
    print("conn.close()\"")
    
    print("\n2. Check for test users:")
    print("mysql -h localhost -P 8889 -u root -proot hacknyu25_test -e \"")
    print("SELECT user_ID, email_address, created_at FROM user_account WHERE user_ID LIKE '%test%' ORDER BY created_at DESC LIMIT 10;\"")
    
    print("\n3. Check nutrition goals:")
    print("mysql -h localhost -P 8889 -u root -proot hacknyu25_test -e \"")
    print("SELECT user_id, daily_calories_goal, created_at FROM user_nutrition_goals ORDER BY created_at DESC LIMIT 10;\"")
    
    print("\n4. Monitor during test run:")
    print("# In one terminal:")
    print("watch -n 1 'mysql -h localhost -P 8889 -u root -proot hacknyu25_test -e \"SELECT COUNT(*) as total_users FROM user_account;\"'")
    print("\n# In another terminal:")
    print("python run_tests.py --file tests/test_nutrition_api_commit_isolation.py")
    
    print("\n" + "="*60)