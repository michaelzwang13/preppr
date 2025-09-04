"""
Comprehensive Budget API tests.
Tests budget overview, spending trends, spending details, settings, and helper functions.
"""

import pytest
import json
from datetime import datetime, timedelta, date
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.budget
@pytest.mark.api
class TestBudgetOverviewAPI:
    """Test budget overview API endpoint."""
    
    def test_get_budget_overview_not_authenticated(self, client):
        """Test getting budget overview without authentication."""
        response = client.get('/api/budget/overview')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_get_budget_overview_new_user_defaults(self, client, logged_in_user, app):
        """Test getting budget overview for new user creates defaults."""
        user_id = logged_in_user
        
        # Clean up any existing settings first
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                api_conn.commit()
                cursor.close()
        
        response = client.get('/api/budget/overview')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check default values are created
        assert data['monthly_budget'] == 1000.0
        assert data['total_spent'] == 0.0
        assert data['remaining'] == 1000.0
        assert data['daily_average'] >= 0
        assert data['total_trips'] == 0
        assert data['alert_threshold'] == 80.0
        assert data['budget_period'] == 'monthly'
    
    def test_get_budget_overview_existing_settings(self, client, logged_in_user, app):
        """Test getting budget overview with existing settings."""
        user_id = logged_in_user
        
        # Create existing budget settings using regular DB connection
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Clean first
            cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
            cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
            
            # Insert custom settings
            cursor.execute('''
                INSERT INTO user_budget_settings 
                (user_id, monthly_budget, alert_threshold, budget_period)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, 1500.0, 75.0, 'monthly'))
            
            # Insert budget entry
            cursor.execute('''
                INSERT INTO budget 
                (user_id, allocated_amount, total_spent, remaining_amount, alert_threshold)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, 1500.0, 350.0, 1150.0, 0.75))
            
            db.commit()
            cursor.close()
        
        response = client.get('/api/budget/overview')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['monthly_budget'] == 1500.0
        assert data['total_spent'] == 350.0
        assert data['remaining'] == 1150.0
        assert data['alert_threshold'] == 75.0
        assert data['budget_period'] == 'monthly'
    
    def test_get_budget_overview_with_shopping_trips(self, client, logged_in_user, app):
        """Test budget overview includes shopping trip counts."""
        user_id = logged_in_user
        
        # Create shopping trips for this month
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Clean first
            cursor.execute('DELETE FROM shopping_cart WHERE user_ID = %s', (user_id,))
            
            # Insert purchased shopping carts for current month
            current_date = datetime.now()
            for i in range(3):
                cart_date = current_date - timedelta(days=i)
                cursor.execute('''
                    INSERT INTO shopping_cart 
                    (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, f'Store {i}', 'purchased', cart_date))
            
            db.commit()
            cursor.close()
        
        response = client.get('/api/budget/overview')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total_trips'] == 3
    
    def test_get_budget_overview_database_error(self, client, logged_in_user):
        """Test budget overview handles database errors gracefully."""
        with patch('src.backend.apis.budget.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database connection failed")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get('/api/budget/overview')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'Failed to get budget overview' in data['error']


@pytest.mark.budget
@pytest.mark.api
class TestBudgetSpendingTrendsAPI:
    """Test budget spending trends API endpoint."""
    
    def test_get_spending_trends_not_authenticated(self, client):
        """Test getting spending trends without authentication."""
        response = client.get('/api/budget/spending-trends')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_get_spending_trends_7d_period(self, client, logged_in_user, app):
        """Test getting 7-day spending trends."""
        user_id = logged_in_user
        
        # Create shopping data for the last 7 days
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Clean first
            cursor.execute('DELETE FROM cart_item WHERE cart_ID IN (SELECT cart_ID FROM shopping_cart WHERE user_ID = %s)', (user_id,))
            cursor.execute('DELETE FROM shopping_cart WHERE user_ID = %s', (user_id,))
            
            # Create carts and items for specific days
            for i in range(3):  # Last 3 days
                cart_date = datetime.now() - timedelta(days=i)
                cursor.execute('''
                    INSERT INTO shopping_cart 
                    (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, f'Store {i}', 'purchased', cart_date))
                cart_id = cursor.lastrowid
                
                # Add items to cart
                cursor.execute('''
                    INSERT INTO cart_item 
                    (cart_ID, item_name, quantity, price)
                    VALUES (%s, %s, %s, %s)
                ''', (cart_id, f'Item {i}', 2, 25.0))
            
            db.commit()
            cursor.close()
        
        response = client.get('/api/budget/spending-trends?period=7d')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period'] == '7d'
        assert 'trends' in data
        assert len(data['trends']) == 7  # Should return 7 days of data
        
        # Check that each trend has the expected structure
        for trend in data['trends']:
            assert 'date' in trend
            assert 'label' in trend  
            assert 'amount' in trend
            assert isinstance(trend['amount'], (int, float))
    
    def test_get_spending_trends_1m_period(self, client, logged_in_user):
        """Test getting 1-month spending trends (weekly buckets)."""
        response = client.get('/api/budget/spending-trends?period=1m')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period'] == '1m'
        assert 'trends' in data
        assert len(data['trends']) <= 5  # Should return up to 5 weeks
        
        for trend in data['trends']:
            assert 'date' in trend
            assert 'label' in trend
            assert 'Week of' in trend['label']  # Should have week labels
            assert 'amount' in trend
    
    def test_get_spending_trends_3m_period(self, client, logged_in_user):
        """Test getting 3-month spending trends (weekly buckets)."""
        response = client.get('/api/budget/spending-trends?period=3m')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period'] == '3m'
        assert 'trends' in data
        assert len(data['trends']) <= 13  # Should return up to 13 weeks
    
    def test_get_spending_trends_1y_period(self, client, logged_in_user):
        """Test getting 1-year spending trends (monthly buckets)."""
        response = client.get('/api/budget/spending-trends?period=1y')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period'] == '1y'
        assert 'trends' in data
        assert len(data['trends']) == 12  # Should return 12 months
        
        for trend in data['trends']:
            assert 'date' in trend
            assert 'label' in trend
            # Monthly labels should contain year
            assert any(str(year) in trend['label'] for year in [datetime.now().year - 1, datetime.now().year])
            assert 'amount' in trend
    
    def test_get_spending_trends_default_period(self, client, logged_in_user):
        """Test getting spending trends defaults to 7d period."""
        response = client.get('/api/budget/spending-trends')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['period'] == '7d'  # Should default to 7d
    
    def test_get_spending_trends_database_error(self, client, logged_in_user):
        """Test spending trends handles database errors gracefully."""
        with patch('src.database.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Query failed")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get('/api/budget/spending-trends')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'Failed to get spending trends' in data['error']


@pytest.mark.budget
@pytest.mark.api
class TestBudgetSpendingDetailsAPI:
    """Test budget spending details API endpoint."""
    
    def test_get_spending_details_not_authenticated(self, client):
        """Test getting spending details without authentication."""
        response = client.get('/api/budget/spending-details')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_get_spending_details_missing_date(self, client, logged_in_user):
        """Test getting spending details without date parameter."""
        response = client.get('/api/budget/spending-details')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Date parameter required'
    
    def test_get_spending_details_invalid_date_format(self, client, logged_in_user):
        """Test getting spending details with invalid date format."""
        response = client.get('/api/budget/spending-details?date=invalid-date')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Invalid date format'
    
    def test_get_spending_details_7d_period(self, client, logged_in_user, app):
        """Test getting spending details for single day (7d period)."""
        user_id = logged_in_user
        test_date = datetime.now().date()
        
        # Create shopping data for the test date
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM cart_item WHERE cart_ID IN (SELECT cart_ID FROM shopping_cart WHERE user_ID = %s)', (user_id,))
                cursor.execute('DELETE FROM shopping_cart WHERE user_ID = %s', (user_id,))
                
                # Create cart for test date
                cursor.execute('''
                    INSERT INTO shopping_cart 
                    (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, 'Test Store', 'purchased', test_date))
                cart_id = cursor.lastrowid
                
                # Add multiple items to cart
                items = [
                    ('Apples', 3, 4.50, 'apple.jpg'),
                    ('Bread', 1, 2.99, 'bread.jpg')
                ]
                for name, qty, price, image in items:
                    cursor.execute('''
                        INSERT INTO cart_item 
                        (cart_ID, item_name, quantity, price, image_url)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (cart_id, name, qty, price, image))
                
                api_conn.commit()
                cursor.close()
        
        response = client.get(f'/api/budget/spending-details?period=7d&date={test_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'period_label' in data
        assert data['total_amount'] == 16.49  # (3 * 4.50) + (1 * 2.99)
        assert data['total_trips'] == 1
        assert data['total_items'] == 2
        assert len(data['trips']) == 1
        
        trip = data['trips'][0]
        assert trip['store_name'] == 'Test Store'
        assert len(trip['items']) == 2
        assert trip['trip_total'] == 16.49
    
    def test_get_spending_details_1m_period_week_range(self, client, logged_in_user, app):
        """Test getting spending details for week range (1m period)."""
        user_id = logged_in_user
        # Use Monday of current week as test date
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        
        # Create shopping data across the week
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM cart_item WHERE cart_ID IN (SELECT cart_ID FROM shopping_cart WHERE user_ID = %s)', (user_id,))
                cursor.execute('DELETE FROM shopping_cart WHERE user_ID = %s', (user_id,))
                
                # Create carts for Monday and Wednesday of the week
                for day_offset in [0, 2]:  # Monday and Wednesday
                    cart_date = monday + timedelta(days=day_offset)
                    cursor.execute('''
                        INSERT INTO shopping_cart 
                        (user_ID, store_name, status, created_at)
                        VALUES (%s, %s, %s, %s)
                    ''', (user_id, f'Store {day_offset}', 'purchased', cart_date))
                    cart_id = cursor.lastrowid
                    
                    cursor.execute('''
                        INSERT INTO cart_item 
                        (cart_ID, item_name, quantity, price)
                        VALUES (%s, %s, %s, %s)
                    ''', (cart_id, f'Item {day_offset}', 1, 10.0))
                
                api_conn.commit()
                cursor.close()
        
        response = client.get(f'/api/budget/spending-details?period=1m&date={monday}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'Week of' in data['period_label']
        assert data['total_amount'] == 20.0
        assert data['total_trips'] == 2
        assert data['total_items'] == 2
    
    def test_get_spending_details_1y_period_month_range(self, client, logged_in_user, app):
        """Test getting spending details for entire month (1y period)."""
        user_id = logged_in_user
        # Use first day of current month
        today = datetime.now().date()
        first_of_month = today.replace(day=1)
        
        # Create shopping data for the month
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first  
                cursor.execute('DELETE FROM cart_item WHERE cart_ID IN (SELECT cart_ID FROM shopping_cart WHERE user_ID = %s)', (user_id,))
                cursor.execute('DELETE FROM shopping_cart WHERE user_ID = %s', (user_id,))
                
                # Create cart for middle of the month
                mid_month = first_of_month + timedelta(days=15)
                cursor.execute('''
                    INSERT INTO shopping_cart 
                    (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, 'Monthly Store', 'purchased', mid_month))
                cart_id = cursor.lastrowid
                
                cursor.execute('''
                    INSERT INTO cart_item 
                    (cart_ID, item_name, quantity, price)
                    VALUES (%s, %s, %s, %s)
                ''', (cart_id, 'Monthly Item', 5, 8.0))
                
                api_conn.commit()
                cursor.close()
        
        response = client.get(f'/api/budget/spending-details?period=1y&date={first_of_month}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert first_of_month.strftime('%B %Y') in data['period_label']
        assert data['total_amount'] == 40.0
        assert data['total_trips'] == 1
    
    def test_get_spending_details_no_data(self, client, logged_in_user):
        """Test getting spending details when no data exists."""
        test_date = (datetime.now() - timedelta(days=365)).date()  # A year ago, likely no data
        
        response = client.get(f'/api/budget/spending-details?period=7d&date={test_date}')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total_amount'] == 0
        assert data['total_trips'] == 0
        assert data['total_items'] == 0
        assert len(data['trips']) == 0


@pytest.mark.budget
@pytest.mark.api
class TestBudgetSettingsAPI:
    """Test budget settings update API endpoint."""
    
    def test_update_budget_settings_not_authenticated(self, client):
        """Test updating budget settings without authentication."""
        response = client.post('/api/budget/settings',
                              data=json.dumps({'monthly_budget': 1500}),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_update_budget_settings_no_data(self, client, logged_in_user):
        """Test updating budget settings with no data provided."""
        response = client.post('/api/budget/settings',
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No data provided'
    
    def test_update_budget_settings_new_user(self, client, logged_in_user, app):
        """Test updating budget settings for new user (creates new record)."""
        user_id = logged_in_user
        
        # Clean up any existing settings first
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                api_conn.commit()
                cursor.close()
        
        settings_data = {
            'monthly_budget': 2000,
            'budget_period': 'monthly',
            'alert_threshold': 85,
            'category_limits': 'enabled'
        }
        
        response = client.post('/api/budget/settings',
                              data=json.dumps(settings_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['message'] == 'Budget settings updated successfully'
        
        # Verify settings were created in database
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM user_budget_settings WHERE user_id = %s', (user_id,))
            settings = cursor.fetchone()
            cursor.close()
            
            assert settings is not None
            assert float(settings['monthly_budget']) == 2000.0
            assert settings['budget_period'] == 'monthly'
            assert float(settings['alert_threshold']) == 85.0
            assert settings['category_limits_enabled'] == 1
    
    def test_update_budget_settings_existing_user(self, client, logged_in_user, app):
        """Test updating budget settings for existing user (updates record)."""
        user_id = logged_in_user
        
        # Create existing settings
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                
                # Insert existing settings
                cursor.execute('''
                    INSERT INTO user_budget_settings 
                    (user_id, monthly_budget, alert_threshold, budget_period, category_limits_enabled)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, 1000.0, 80.0, 'monthly', 1))
                
                api_conn.commit()
                cursor.close()
        
        # Update with new settings
        updated_settings = {
            'monthly_budget': 1800,
            'budget_period': 'weekly',
            'alert_threshold': 90,
            'category_limits': 'disabled'
        }
        
        response = client.post('/api/budget/settings',
                              data=json.dumps(updated_settings),
                              content_type='application/json')
        assert response.status_code == 200
        
        # Verify settings were updated
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM user_budget_settings WHERE user_id = %s', (user_id,))
            settings = cursor.fetchone()
            cursor.close()
            
            assert float(settings['monthly_budget']) == 1800.0
            assert settings['budget_period'] == 'weekly'
            assert float(settings['alert_threshold']) == 90.0
            assert settings['category_limits_enabled'] == 0
    
    def test_update_budget_settings_default_values(self, client, logged_in_user, app):
        """Test updating budget settings uses default values for missing fields."""
        user_id = logged_in_user
        
        # Clean up first
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                api_conn.commit()
                cursor.close()
        
        # Send minimal data (only monthly_budget)
        minimal_settings = {
            'monthly_budget': 1200
        }
        
        response = client.post('/api/budget/settings',
                              data=json.dumps(minimal_settings),
                              content_type='application/json')
        assert response.status_code == 200
        
        # Verify defaults were applied
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM user_budget_settings WHERE user_id = %s', (user_id,))
            settings = cursor.fetchone()
            cursor.close()
            
            assert float(settings['monthly_budget']) == 1200.0
            assert settings['budget_period'] == 'monthly'  # Default
            assert float(settings['alert_threshold']) == 80.0  # Default
    
    def test_update_budget_settings_updates_current_budget(self, client, logged_in_user, app):
        """Test updating settings also updates current month's budget allocation."""
        user_id = logged_in_user
        
        # Create existing budget entry for current month
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                
                # Insert current budget
                cursor.execute('''
                    INSERT INTO budget 
                    (user_id, allocated_amount, total_spent, remaining_amount, alert_threshold)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, 1000.0, 0.0, 1000.0, 0.8))
                
                api_conn.commit()
                cursor.close()
        
        # Update settings with new budget
        new_settings = {
            'monthly_budget': 2500,
            'alert_threshold': 75
        }
        
        response = client.post('/api/budget/settings',
                              data=json.dumps(new_settings),
                              content_type='application/json')
        assert response.status_code == 200
        
        # Verify current budget was updated
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT allocated_amount, alert_threshold 
                FROM budget 
                WHERE user_id = %s 
                AND MONTH(created_at) = MONTH(CURRENT_DATE())
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                AND list_id IS NULL
            ''', (user_id,))
            budget = cursor.fetchone()
            cursor.close()
            
            assert float(budget['allocated_amount']) == 2500.0
            assert float(budget['alert_threshold']) == 0.75
    
    def test_update_budget_settings_database_error(self, client, logged_in_user):
        """Test budget settings update handles database errors gracefully."""
        with patch('src.database.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database update failed")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            settings_data = {
                'monthly_budget': 1500,
                'alert_threshold': 85
            }
            
            response = client.post('/api/budget/settings',
                                  data=json.dumps(settings_data),
                                  content_type='application/json')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'Failed to update budget settings' in data['error']


@pytest.mark.budget
@pytest.mark.api  
class TestBudgetHelperFunctions:
    """Test budget helper functions like update_budget_spending."""
    
    def test_update_budget_spending_existing_budget(self, app, logged_in_user):
        """Test update_budget_spending with existing budget entry."""
        from src.backend.apis.budget import update_budget_spending
        user_id = logged_in_user
        
        # Create existing budget entry
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                
                # Insert budget entry
                cursor.execute('''
                    INSERT INTO budget 
                    (user_id, allocated_amount, total_spent, remaining_amount, alert_threshold)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, 1000.0, 100.0, 900.0, 0.8))
                
                api_conn.commit()
                cursor.close()
            
            # Call the helper function
            update_budget_spending(user_id, 50.0)
            
            # Verify spending was updated
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT total_spent 
                FROM budget 
                WHERE user_id = %s 
                AND MONTH(created_at) = MONTH(CURRENT_DATE())
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                AND list_id IS NULL
            ''', (user_id,))
            budget = cursor.fetchone()
            cursor.close()
            
            assert float(budget['total_spent']) == 150.0  # 100.0 + 50.0
    
    def test_update_budget_spending_no_existing_budget(self, app, logged_in_user):
        """Test update_budget_spending creates new budget entry when none exists."""
        from src.backend.apis.budget import update_budget_spending
        user_id = logged_in_user
        
        # Create budget settings for the user
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean first
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                
                # Insert budget settings
                cursor.execute('''
                    INSERT INTO user_budget_settings 
                    (user_id, monthly_budget, alert_threshold, budget_period)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, 1500.0, 75.0, 'monthly'))
                
                api_conn.commit()
                cursor.close()
            
            # Call the helper function
            update_budget_spending(user_id, 75.0)
            
            # Verify new budget entry was created
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT allocated_amount, total_spent, alert_threshold 
                FROM budget 
                WHERE user_id = %s 
                AND MONTH(created_at) = MONTH(CURRENT_DATE())
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                AND list_id IS NULL
            ''', (user_id,))
            budget = cursor.fetchone()
            cursor.close()
            
            assert budget is not None
            assert float(budget['allocated_amount']) == 1500.0
            assert float(budget['total_spent']) == 75.0
            assert float(budget['alert_threshold']) == 0.75
    
    def test_update_budget_spending_no_settings_uses_defaults(self, app, logged_in_user):
        """Test update_budget_spending uses default values when no settings exist."""
        from src.backend.apis.budget import update_budget_spending
        user_id = logged_in_user
        
        with app.app_context():
            from flask import current_app
            from tests.conftest import get_test_database_manager
            
            manager = get_test_database_manager(current_app.config)
            api_conn = manager.get_api_connection() if manager else None
            
            if api_conn:
                cursor = api_conn.cursor()
                # Clean everything
                cursor.execute('DELETE FROM budget WHERE user_id = %s', (user_id,))
                cursor.execute('DELETE FROM user_budget_settings WHERE user_id = %s', (user_id,))
                api_conn.commit()
                cursor.close()
            
            # Call the helper function
            update_budget_spending(user_id, 25.0)
            
            # Verify defaults were used
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT allocated_amount, total_spent, alert_threshold 
                FROM budget 
                WHERE user_id = %s 
                AND MONTH(created_at) = MONTH(CURRENT_DATE())
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                AND list_id IS NULL
            ''', (user_id,))
            budget = cursor.fetchone()
            cursor.close()
            
            assert budget is not None
            assert float(budget['allocated_amount']) == 1000.0  # Default
            assert float(budget['total_spent']) == 25.0
            assert float(budget['alert_threshold']) == 0.8  # Default 80%
    
    def test_update_budget_spending_database_error_handled(self, app, logged_in_user):
        """Test update_budget_spending handles database errors gracefully."""
        from src.backend.apis.budget import update_budget_spending
        user_id = logged_in_user
        
        with app.app_context():
            with patch('src.database.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.execute.side_effect = Exception("Database error")
                mock_db.cursor.return_value = mock_cursor
                mock_get_db.return_value = mock_db
                
                # Should not raise exception, should handle gracefully
                try:
                    update_budget_spending(user_id, 30.0)
                    # If no exception is raised, the function handled the error
                    assert True
                except Exception:
                    # If an exception is raised, the test fails
                    assert False, "update_budget_spending should handle database errors gracefully"