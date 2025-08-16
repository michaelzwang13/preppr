"""
Test configuration and fixtures for Preppr application.
Comprehensive test setup for all app features including nutrition, subscriptions, tips, etc.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from src import create_app
from src.database import get_db
from unittest.mock import patch, MagicMock


def execute_sql_file(db, sql_file_path, test_db_name='hacknyu25_test'):
    """
    Execute a SQL file using mysql command line tool for better SQL parsing.
    
    Args:
        db: Database connection (used to get connection info)
        sql_file_path: Path to the SQL file
        test_db_name: Name of the test database (default: hacknyu25_test)
    """
    import subprocess
    import tempfile
    
    try:
        # Read the SQL file and substitute database name
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Replace production database name with test database name
        sql_content = sql_content.replace('USE hacknyu25;', f'USE {test_db_name};')
        sql_content = sql_content.replace('hacknyu25.', f'{test_db_name}.')
        
        # Create a temporary file with the modified SQL
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_file.write(sql_content)
            temp_sql_path = temp_file.name
        
        # Get database connection info from the app config
        from flask import current_app
        db_config = current_app.config
        
        # Execute using mysql command line tool
        mysql_cmd = [
            'mysql',
            f"--host={db_config.get('DB_HOST', 'localhost')}",
            f"--port={db_config.get('DB_PORT', 3306)}",
            f"--user={db_config.get('DB_USER', 'root')}",
            f"--password={db_config.get('DB_PASSWORD', '')}",
            test_db_name
        ]
        
        with open(temp_sql_path, 'r') as sql_file:
            result = subprocess.run(
                mysql_cmd,
                stdin=sql_file,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode != 0:
            print(f"MySQL command failed for {os.path.basename(sql_file_path)}")
            print(f"Error: {result.stderr}")
            # Don't raise exception, just log - some errors are expected in test environment
        else:
            print(f"Successfully executed {os.path.basename(sql_file_path)}")
        
        # Clean up temporary file
        os.unlink(temp_sql_path)
        
    except subprocess.TimeoutExpired:
        print(f"Timeout executing {os.path.basename(sql_file_path)}")
        # Clean up temporary file
        if 'temp_sql_path' in locals():
            os.unlink(temp_sql_path)
    except Exception as e:
        print(f"Error executing SQL file {sql_file_path}: {e}")
        # Clean up temporary file
        if 'temp_sql_path' in locals():
            os.unlink(temp_sql_path)
        # Don't raise - continue with other files


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create test app with test configuration
    test_app = create_app()
    test_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'DB_HOST': 'localhost',
        'DB_PORT': 8889,
        'DB_USER': 'root',
        'DB_PASSWORD': 'root',
        'DB_NAME': 'hacknyu25_test',
        'LOG_LEVEL': 'DEBUG',
        # JWT Configuration for testing
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
        'JWT_ACCESS_TOKEN_EXPIRES': 3600,  # 1 hour
        'JWT_REFRESH_TOKEN_EXPIRES': 2592000,  # 30 days
        'BCRYPT_ROUNDS': 4  # Lower rounds for faster testing
    })
    
    with test_app.app_context():
        # Initialize test database
        init_test_db()
        # Populate test data
        populate_test_data()
    
    yield test_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(autouse=True)
def db_transaction(app):
    """
    Wrap each test in a database transaction that gets rolled back automatically.
    This ensures test isolation and prevents data pollution between tests.
    """
    with app.app_context():
        # Create a new database connection for the transaction
        import pymysql.cursors
        from flask import g
        
        db_connection = pymysql.connect(
            host=app.config["DB_HOST"],
            port=app.config["DB_PORT"],
            user=app.config["DB_USER"],
            password=app.config["DB_PASSWORD"],
            db=app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False  # Ensure we can control transactions
        )
        
        # Start a transaction
        db_connection.begin()
        
        # Replace the Flask g.db with our transactional connection
        original_db = g.get('db', None)
        g.db = db_connection
        
        try:
            yield db_connection
        finally:
            # Always rollback the transaction, regardless of test success/failure
            try:
                db_connection.rollback()
            except Exception as e:
                # If rollback fails, log it but don't raise to avoid masking the original test failure
                print(f"Warning: Failed to rollback test transaction: {e}")
            finally:
                try:
                    db_connection.close()
                except Exception:
                    pass
                # Restore original db connection in g
                if original_db is not None:
                    g.db = original_db
                else:
                    g.pop('db', None)


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


def init_test_db():
    """Database schema is already created manually - no initialization needed."""
    # The database schema has been manually synchronized with production.
    # No table creation, modification, or cleanup is performed.
    pass


def populate_test_data():
    """Populate test database with sample data."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Insert subscription tier features
        tier_features = [
            ('free', 'meal_plans_active', 3, 'Maximum active meal plans'),
            ('free', 'pantry_items', 50, 'Maximum pantry items'),
            ('free', 'shopping_lists_per_day', 2, 'Shopping lists per day'),
            ('free', 'saved_recipes', 10, 'Maximum saved recipes'),
            ('free', 'upc_scans_per_trip', 10, 'UPC scans per shopping trip'),
            ('free', 'upc_scans_per_week', 25, 'UPC scans per week'),
            ('premium', 'meal_plans_active', -1, 'Unlimited meal plans'),
            ('premium', 'pantry_items', -1, 'Unlimited pantry items'),
            ('premium', 'shopping_lists_per_day', -1, 'Unlimited shopping lists'),
            ('premium', 'saved_recipes', -1, 'Unlimited saved recipes'),
            ('premium', 'upc_scans_per_trip', -1, 'Unlimited UPC scans'),
            ('premium', 'upc_scans_per_week', -1, 'Unlimited UPC scans'),
        ]
        
        for tier, feature, limit, desc in tier_features:
            cursor.execute('''
                INSERT IGNORE INTO subscription_tier_features 
                (tier, feature_name, limit_value, description)
                VALUES (%s, %s, %s, %s)
            ''', (tier, feature, limit, desc))
        
        # Insert sample tips
        sample_tips = [
            ("Prep vegetables on Sunday for quick weekday cooking", "meal_prep"),
            ("Store herbs in water like flowers to keep them fresh longer", "storage"),
            ("Use the freezer to extend the life of bread, berries, and nuts", "storage"),
            ("Cook once, eat twice - make extra portions for easy leftovers", "meal_prep"),
            ("Check your pantry before shopping to avoid duplicate purchases", "shopping"),
            ("Group similar items together when organizing your pantry", "organization"),
            ("Use clear containers to easily see what ingredients you have", "organization"),
            ("Plan meals around ingredients you already have to reduce waste", "meal_planning"),
            ("Keep a running grocery list throughout the week", "shopping"),
            ("Batch cook grains and proteins at the start of the week", "meal_prep"),
        ]
        
        for tip_text, category in sample_tips:
            cursor.execute('''
                INSERT IGNORE INTO tips (tip_text, tip_category)
                VALUES (%s, %s)
            ''', (tip_text, category))
        
        # Insert sample promotional codes
        cursor.execute('''
            INSERT IGNORE INTO promotional_codes 
            (code, code_type, discount_value, subscription_duration_months, max_uses, created_by, description)
            VALUES 
            ('TESTFREE30', 'free_trial', NULL, 1, 100, 'admin_test', 'Test 30-day free trial'),
            ('WELCOME10', 'percentage', 10.0, NULL, 50, 'admin_test', 'Welcome 10% discount'),
            ('PREMIUM6M', 'free_month', NULL, 6, 25, 'admin_test', 'Free 6 months premium')
        ''')
        
        db.commit()
        
    except Exception as e:
        print(f"Error populating test data: {e}")
        db.rollback()
        raise
    finally:
        cursor.close()


class AuthActions:
    """Helper class for authentication actions in tests."""
    
    def __init__(self, client):
        self._client = client
    
    def register(self, user_id='test_user', email='test@example.com', 
                password='testpass123', confirm_password=None, 
                first_name='Test', last_name='User'):
        """Register a new user."""
        if confirm_password is None:
            confirm_password = password
            
        return self._client.post('/register', data={
            'user_ID': user_id,
            'email_address': email,
            'password': password,
            'confirmPassword': confirm_password,
            'first_name': first_name,
            'last_name': last_name
        })
    
    def login(self, user_id='test_user', password='demo123'):
        """Login a user."""
        return self._client.post('/login', data={
            'user_ID': user_id,
            'password': password
        })
    
    def logout(self):
        """Logout the current user."""
        return self._client.get('/logout')
    
    def api_register(self, user_id='api_user', email='api@example.com',
                    password='testpass123', first_name='API', last_name='User'):
        """Register via API and return JWT tokens."""
        response = self._client.post('/api/auth/register',
            data=json.dumps({
                'user_id': user_id,
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name
            }),
            content_type='application/json'
        )
        return response
    
    def api_login(self, user_id='api_user', password='testpass123'):
        """Login via API and return JWT tokens."""
        response = self._client.post('/api/auth/login',
            data=json.dumps({
                'user_id': user_id,
                'password': password
            }),
            content_type='application/json'
        )
        return response


@pytest.fixture
def auth(client):
    """Authentication helper fixture."""
    return AuthActions(client)


@pytest.fixture
def logged_in_user(client, auth):
    """Create and login a test user."""
    # Try to register (will fail if user exists, which is OK)
    auth.register()
    # Login with the existing or newly created user
    auth.login()
    return 'test_user'


@pytest.fixture
def premium_user(client, auth, app):
    """Create a premium user for testing premium features."""
    user_id = 'premium_user'
    auth.register(user_id=user_id, email='premium@example.com')
    
    with app.app_context():
        # Set user as premium
        db = get_db()
        cursor = db.cursor()
        end_date = datetime.now() + timedelta(days=365)
        cursor.execute('''
            UPDATE user_account 
            SET subscription_tier = 'premium',
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = %s
            WHERE user_ID = %s
        ''', (end_date, user_id))
        db.commit()
        cursor.close()
    
    auth.login(user_id=user_id)
    return user_id


@pytest.fixture
def expired_premium_user(client, auth, app):
    """Create an expired premium user for testing tier downgrades."""
    user_id = 'expired_user'
    auth.register(user_id=user_id, email='expired@example.com')
    
    with app.app_context():
        # Set user as expired premium
        db = get_db()
        cursor = db.cursor()
        end_date = datetime.now() - timedelta(days=1)
        cursor.execute('''
            UPDATE user_account 
            SET subscription_tier = 'premium',
                subscription_status = 'expired',
                subscription_start_date = %s,
                subscription_end_date = %s
            WHERE user_ID = %s
        ''', (end_date - timedelta(days=365), end_date, user_id))
        db.commit()
        cursor.close()
    
    auth.login(user_id=user_id)
    return user_id


@pytest.fixture 
def admin_user(client, auth):
    """Create an admin user for testing admin features."""
    user_id = 'admin_test'
    auth.register(user_id=user_id, email='admin@example.com')
    auth.login(user_id=user_id)
    return user_id


@pytest.fixture
def sample_nutrition_data():
    """Sample nutrition goals data for testing."""
    return {
        'daily_calories': 2200,
        'calories_type': 'goal',
        'daily_protein': 160,
        'protein_type': 'goal',
        'daily_carbs': 275,
        'carbs_type': 'goal',
        'daily_fat': 75,
        'fat_type': 'goal',
        'daily_fiber': 30,
        'fiber_type': 'goal',
        'daily_sodium': 2000,
        'sodium_type': 'limit',
        'goal_type': 'custom',
        'activity_level': 'very_active'
    }


@pytest.fixture
def sample_pantry_items():
    """Sample pantry items for testing."""
    return [
        {
            'name': 'chicken breast',
            'quantity': 2.0,
            'unit': 'lbs',
            'category': 'Meat',
            'storage_type': 'fridge',
            'days_to_expire': 3
        },
        {
            'name': 'brown rice',
            'quantity': 1.0,
            'unit': 'bag',
            'category': 'Grains',
            'storage_type': 'pantry',
            'days_to_expire': 365
        },
        {
            'name': 'whole milk',
            'quantity': 1.0,
            'unit': 'gallon',
            'category': 'Dairy',
            'storage_type': 'fridge',
            'days_to_expire': 7
        }
    ]


@pytest.fixture
def sample_recipe():
    """Sample recipe data for testing."""
    return {
        'recipe_name': 'Grilled Chicken Salad',
        'ingredients': json.dumps([
            {'name': 'chicken breast', 'amount': '6 oz'},
            {'name': 'mixed greens', 'amount': '2 cups'},
            {'name': 'cherry tomatoes', 'amount': '1 cup'},
            {'name': 'olive oil', 'amount': '2 tbsp'}
        ]),
        'instructions': 'Season and grill chicken. Arrange greens and tomatoes. Slice chicken and serve over salad.',
        'prep_time': 15,
        'cook_time': 20,
        'servings': 2,
        'category': 'main',
        'tags': json.dumps(['healthy', 'protein', 'low-carb']),
        'nutrition_info': json.dumps({
            'calories': 350,
            'protein': 45,
            'carbs': 8,
            'fat': 15
        })
    }


@pytest.fixture
def sample_meal_plan():
    """Sample meal plan data for testing."""
    return {
        'plan_name': 'Weekly Test Plan',
        'plan_date': '2024-01-15',
        'meals': [
            {
                'meal_type': 'breakfast',
                'recipe_name': 'Overnight Oats',
                'servings': 1
            },
            {
                'meal_type': 'lunch', 
                'recipe_name': 'Grilled Chicken Salad',
                'servings': 1
            },
            {
                'meal_type': 'dinner',
                'recipe_name': 'Salmon with Vegetables',
                'servings': 2
            }
        ]
    }


@pytest.fixture
def shopping_cart_data():
    """Sample shopping cart data for testing."""
    return {
        'store_name': 'Test Store',
        'items': [
            {
                'upc': '123456789012',
                'price': 5.99,
                'quantity': 2,
                'itemName': 'Test Item 1',
                'imageUrl': 'http://example.com/image1.jpg'
            },
            {
                'upc': '987654321098',
                'price': 3.49,
                'quantity': 1,
                'itemName': 'Test Item 2',
                'imageUrl': 'http://example.com/image2.jpg'
            }
        ]
    }


@pytest.fixture
def mock_ai_service():
    """Mock AI service responses for testing."""
    with patch('src.backend.apis.ingredient_matching.get_ingredient_matches') as mock:
        mock.return_value = [
            {'ingredient': 'chicken breast', 'confidence': 0.95},
            {'ingredient': 'chicken thigh', 'confidence': 0.87}
        ]
        yield mock


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent tip rotation testing."""
    fixed_time = datetime(2024, 1, 15, 14, 30, 0)  # Monday 2:30 PM
    with patch('src.backend.apis.tips.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt


# Pytest markers for test organization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.auth = pytest.mark.auth
pytest.mark.nutrition = pytest.mark.nutrition
pytest.mark.subscription = pytest.mark.subscription
pytest.mark.tips = pytest.mark.tips
pytest.mark.meal_planning = pytest.mark.meal_planning
pytest.mark.shopping = pytest.mark.shopping
pytest.mark.pantry = pytest.mark.pantry
pytest.mark.recipes = pytest.mark.recipes
pytest.mark.admin = pytest.mark.admin
pytest.mark.api = pytest.mark.api
pytest.mark.premium = pytest.mark.premium