"""
Test configuration and fixtures for Preppr application.

Tests run against a real MySQL database that must be named hacknyu25_test.
The app commits freely, so instead of rolling back transactions every test
starts from a known state: all tables are emptied, the reference rows loaded
by the schema files are restored, and populate_test_data() seeds test data.
"""

import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pymysql
import pymysql.cursors
import pytest

from src import create_app
from src.database import get_db

TEST_DB_NAME = "hacknyu25_test"

# Rows inserted by the schema files themselves; restored before every test.
REFERENCE_TABLES = ("pantry_categories", "subscription_tier_features", "tips")

_reference_rows = None


def open_test_connection():
    """Open an autocommit connection to the test database (caller closes it).

    Autocommit makes test setup visible to the app immediately and lets later
    reads see what the app committed.
    """
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 8889)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        db=TEST_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def validate_test_environment():
    """Refuse to run unless the configured database is the test database."""
    from dotenv import load_dotenv

    load_dotenv()
    db_name = os.getenv("DB_NAME_TEST", os.getenv("DB_NAME", ""))
    if db_name != TEST_DB_NAME:
        raise RuntimeError(
            f"Refusing to run tests against database '{db_name}'. "
            f"Set DB_NAME_TEST={TEST_DB_NAME}."
        )


def reset_database():
    """Empty every table, then restore the schema's reference rows."""
    global _reference_rows

    conn = open_test_connection()
    try:
        with conn.cursor() as cursor:
            # A connection left open by an earlier test (e.g. one kept alive by a
            # failure traceback) can hold row locks that would block the wipe.
            cursor.execute(
                "SELECT id FROM information_schema.processlist "
                "WHERE db = %s AND id <> CONNECTION_ID()",
                (TEST_DB_NAME,),
            )
            for row in cursor.fetchall():
                try:
                    cursor.execute(f"KILL {int(row['id'])}")
                except pymysql.err.OperationalError:
                    pass  # already gone

            if _reference_rows is None:
                _reference_rows = {}
                for table in REFERENCE_TABLES:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    _reference_rows[table] = cursor.fetchall()

            cursor.execute(
                "SELECT table_name AS name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (TEST_DB_NAME,),
            )
            # pantry_items first: its delete triggers write to other tables
            tables = sorted(
                (row["name"] for row in cursor.fetchall()),
                key=lambda name: name != "pantry_items",
            )
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables:
                cursor.execute(f"DELETE FROM `{table}`")
            for table, rows in _reference_rows.items():
                if rows:
                    columns = ", ".join(f"`{col}`" for col in rows[0])
                    placeholders = ", ".join(["%s"] * len(rows[0]))
                    cursor.executemany(
                        f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})",
                        [tuple(row.values()) for row in rows],
                    )
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def app():
    """Create an app bound to a freshly reset test database."""
    validate_test_environment()
    original_db_name = os.environ.get("DB_NAME")
    os.environ["DB_NAME"] = TEST_DB_NAME

    try:
        test_app = create_app()
        test_app.config.update(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                # DB_HOST/PORT/USER/PASSWORD come from the environment via Config
                "DB_NAME": TEST_DB_NAME,
                "DB_NAME_TEST": TEST_DB_NAME,
                "LOG_LEVEL": "DEBUG",
                "JWT_SECRET_KEY": "test-jwt-secret-key-that-is-at-least-32-bytes",
                "JWT_ACCESS_TOKEN_EXPIRES": 3600,
                "JWT_REFRESH_TOKEN_EXPIRES": 2592000,
                "BCRYPT_ROUNDS": 4,
            }
        )

        reset_database()
        with test_app.app_context():
            populate_test_data()

        yield test_app
    finally:
        if original_db_name is not None:
            os.environ["DB_NAME"] = original_db_name
        else:
            os.environ.pop("DB_NAME", None)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def test_db(app):
    """An autocommit connection to the test database for setup and assertions."""
    conn = open_test_connection()
    try:
        yield conn
    finally:
        conn.close()


def populate_test_data():
    """Populate test database with sample data."""
    db = get_db()
    cursor = db.cursor()
    
    try:
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
    
    def login(self, user_id='test_user', password='testpass123'):
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
    
    # Register the user using the normal auth system
    auth.register(user_id=user_id, email='premium@example.com')
    
    api_connection = open_test_connection()
    
    try:
        cursor = api_connection.cursor()
        end_date = datetime.now() + timedelta(days=365)
        cursor.execute('''
            UPDATE user_account 
            SET subscription_tier = 'premium',
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = %s
            WHERE user_ID = %s
        ''', (end_date, user_id))
        api_connection.commit()
        cursor.close()
    finally:
        api_connection.close()
    
    # Set session manually to ensure it persists for the test
    with client.session_transaction() as sess:
        sess['user_ID'] = user_id
    
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
def mock_datetime():
    """Mock datetime for consistent tip rotation testing."""
    fixed_time = datetime(2024, 1, 15, 14, 30, 0)  # Monday 2:30 PM
    with patch('src.backend.apis.tips.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt
