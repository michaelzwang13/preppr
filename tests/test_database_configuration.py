"""
Test database configuration verification.
Ensures tests are running against the correct database.
"""

import pytest
import os
from src.database import get_db


@pytest.mark.unit
def test_database_configuration_is_test_db(app):
    """Verify that tests are configured to use the test database."""
    
    # Check app config
    assert app.config['DB_NAME'] == 'hacknyu25_test', f"App config DB_NAME is {app.config['DB_NAME']}, should be hacknyu25_test"
    
    # Check environment variable
    env_db_name = os.environ.get('DB_NAME')
    assert env_db_name == 'hacknyu25_test', f"Environment DB_NAME is {env_db_name}, should be hacknyu25_test"
    
    # Check actual database connection
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE() as current_db")
        current_db = cursor.fetchone()['current_db']
        cursor.close()
        
        assert current_db == 'hacknyu25_test', f"Connected to database {current_db}, should be hacknyu25_test"
    
    print(f"✅ All database configuration checks passed:")
    print(f"   App config: {app.config['DB_NAME']}")
    print(f"   Environment: {env_db_name}")
    print(f"   Connected DB: {current_db}")


@pytest.mark.unit
def test_not_connected_to_production_database(app):
    """Critical safety test - ensure we're NOT connected to production database."""
    
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE() as current_db")
        current_db = cursor.fetchone()['current_db']
        cursor.close()
        
        # This is the critical safety check
        assert current_db != 'hacknyu25', f"DANGER: Tests are connected to PRODUCTION database {current_db}!"
        assert current_db == 'hacknyu25_test', f"Tests should connect to hacknyu25_test, but connected to {current_db}"
    
    print(f"✅ SAFETY CHECK PASSED: Not connected to production database")


@pytest.mark.integration
def test_can_write_to_test_database(client, auth):
    """Test that we can write to the test database and it gets rolled back."""
    
    # This should work without affecting production
    response = auth.register(user_id='db_config_test', email='dbconfig@test.com')
    
    # Registration should succeed (we're in test db)
    assert response.status_code == 302  # Redirect after success
    
    print(f"✅ Successfully wrote test data to test database")
    # Data will be automatically rolled back


@pytest.mark.integration
def test_environment_isolation_from_production():
    """Test that our test environment is properly isolated."""
    
    # Check that we're not accidentally inheriting production settings
    testing_flag = os.environ.get('TESTING')
    flask_env = os.environ.get('FLASK_ENV')
    db_name = os.environ.get('DB_NAME')
    
    assert testing_flag == 'true', f"TESTING flag should be 'true', got '{testing_flag}'"
    assert flask_env == 'testing', f"FLASK_ENV should be 'testing', got '{flask_env}'"
    assert db_name == 'hacknyu25_test', f"DB_NAME should be 'hacknyu25_test', got '{db_name}'"
    
    print(f"✅ Environment isolation verified:")
    print(f"   TESTING={testing_flag}")
    print(f"   FLASK_ENV={flask_env}")
    print(f"   DB_NAME={db_name}")