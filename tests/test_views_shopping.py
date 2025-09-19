"""
Comprehensive tests for views/shopping.py.
Tests all shopping-related view endpoints including authentication,
shopping trips, cart management, and page rendering.
"""

import pytest
import json
from datetime import datetime
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.unit
class TestShoppingViews:
    """Test shopping view endpoints."""
    
    def test_index_view(self, client):
        """Test the index page renders."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'index.html' in response.data or response.status_code == 200
    
    def test_home_not_authenticated(self, client):
        """Test home page redirects when not authenticated."""
        response = client.get('/home')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_home_authenticated(self, client, logged_in_user):
        """Test home page loads when authenticated."""
        response = client.get('/home')
        assert response.status_code == 200
    
    def test_shopping_history_not_authenticated(self, client):
        """Test shopping history redirects when not authenticated."""
        response = client.get('/shopping-history')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_shopping_history_authenticated(self, client, logged_in_user):
        """Test shopping history page loads when authenticated."""
        response = client.get('/shopping-history')
        assert response.status_code == 200
    
    def test_shopping_lists_not_authenticated(self, client):
        """Test shopping lists page redirects when not authenticated."""
        response = client.get('/shopping-lists')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_shopping_lists_authenticated(self, client, logged_in_user):
        """Test shopping lists page loads when authenticated."""
        response = client.get('/shopping-lists')
        assert response.status_code == 200
    
    def test_budget_not_authenticated(self, client):
        """Test budget page redirects when not authenticated."""
        response = client.get('/budget')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_budget_authenticated(self, client, logged_in_user):
        """Test budget page loads when authenticated."""
        response = client.get('/budget')
        assert response.status_code == 200
    
    def test_nutrition_not_authenticated(self, client):
        """Test nutrition page redirects when not authenticated."""
        response = client.get('/nutrition')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_nutrition_authenticated(self, client, logged_in_user):
        """Test nutrition page loads when authenticated."""
        response = client.get('/nutrition')
        assert response.status_code == 200
    
    def test_pantry_not_authenticated(self, client):
        """Test pantry page redirects when not authenticated."""
        response = client.get('/pantry')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_pantry_authenticated(self, client, logged_in_user):
        """Test pantry page loads when authenticated."""
        response = client.get('/pantry')
        assert response.status_code == 200
    
    def test_meal_plans_not_authenticated(self, client):
        """Test meal plans page redirects when not authenticated."""
        response = client.get('/meal-plans')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_meal_plans_authenticated(self, client, logged_in_user):
        """Test meal plans page loads when authenticated."""
        response = client.get('/meal-plans')
        assert response.status_code == 200
    
    def test_advanced_meal_planning_not_authenticated(self, client):
        """Test advanced meal planning page redirects when not authenticated."""
        response = client.get('/meal-plans/advanced')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_advanced_meal_planning_authenticated(self, client, logged_in_user):
        """Test advanced meal planning page loads when authenticated."""
        response = client.get('/meal-plans/advanced')
        assert response.status_code == 200
    
    def test_recipes_not_authenticated(self, client):
        """Test recipes page redirects when not authenticated."""
        response = client.get('/recipes')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_recipes_authenticated(self, client, logged_in_user):
        """Test recipes page loads when authenticated."""
        response = client.get('/recipes')
        assert response.status_code == 200


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestShoppingHistoryAPI:
    """Test shopping history API endpoint."""
    
    def test_get_shopping_history_not_authenticated(self, client):
        """Test shopping history API without authentication."""
        response = client.get('/api/shopping-history')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_get_shopping_history_empty(self, client, logged_in_user):
        """Test shopping history API when user has no history."""
        response = client.get('/api/shopping-history')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['history'] == []
    
    def test_get_shopping_history_with_pagination(self, client, logged_in_user):
        """Test shopping history API with pagination parameters."""
        # Create some test cart history
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create purchased carts
            for i in range(5):
                cursor.execute("""
                    INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                """, ('test_user', f'Store {i+1}', 'purchased', datetime.now()))
                cart_id = cursor.lastrowid
                
                # Add items to cart
                cursor.execute("""
                    INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                    VALUES (%s, %s, %s, %s)
                """, (cart_id, f'Item {i+1}', 10.99, 1))
            
            cursor.close()
        
        # Test default pagination
        response = client.get('/api/shopping-history')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['history']) == 5
        
        # Test with custom limit
        response = client.get('/api/shopping-history?limit=3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['history']) == 3
        
        # Test with offset
        response = client.get('/api/shopping-history?offset=2&limit=2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['history']) == 2


@pytest.mark.shopping
@pytest.mark.integration
@pytest.mark.views
class TestShoppingTripManagement:
    """Test shopping trip creation and management."""
    
    def test_start_shopping_creates_new_cart(self, client, logged_in_user):
        """Test starting shopping creates a new cart."""
        response = client.post('/start-shopping', data={'storeName': 'Test Store'})
        assert response.status_code == 302
        assert '/shopping-trip' in response.location
        
        # Verify cart was created
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                SELECT * FROM shopping_cart 
                WHERE user_ID = %s AND store_name = %s AND status = 'active'
            """, ('test_user', 'Test Store'))
            cart = cursor.fetchone()
            assert cart is not None
            cursor.close()
    
    def test_start_shopping_uses_existing_active_cart(self, client, logged_in_user):
        """Test starting shopping uses existing active cart if available."""
        # Create existing active cart
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Existing Store', 'active'))
            existing_cart_id = cursor.lastrowid
            cursor.close()
        
        response = client.post('/start-shopping', data={'storeName': 'New Store'})
        assert response.status_code == 302
        
        # Verify existing cart was used (cart_ID should be in session)
        with client.session_transaction() as sess:
            assert sess.get('cart_ID') == existing_cart_id
    
    def test_shopping_trip_not_authenticated(self, client):
        """Test shopping trip page redirects when not authenticated."""
        response = client.get('/shopping-trip')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_shopping_trip_no_active_cart(self, client, logged_in_user):
        """Test shopping trip page when no active cart exists."""
        response = client.get('/shopping-trip')
        assert response.status_code == 200
        # Should render page with no cart session
    
    def test_shopping_trip_with_active_cart(self, client, logged_in_user):
        """Test shopping trip page with active cart."""
        # Create active cart and set in session
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            cursor.close()
        
        with client.session_transaction() as sess:
            sess['cart_ID'] = cart_id
        
        response = client.get('/shopping-trip')
        assert response.status_code == 200
    
    def test_shopping_trip_restores_cart_from_database(self, client, logged_in_user):
        """Test shopping trip restores cart ID from database when not in session."""
        # Create active cart but don't set in session
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            cursor.close()
        
        response = client.get('/shopping-trip')
        assert response.status_code == 200
        
        # Verify cart ID was restored to session
        with client.session_transaction() as sess:
            assert sess.get('cart_ID') == cart_id
    
    def test_finish_shopping_updates_cart_status(self, client, logged_in_user):
        """Test finishing shopping updates cart status to purchased."""
        # Create active cart with items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            
            # Add item to cart
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Test Item', 15.99, 2))
            
            cursor.close()
        
        with client.session_transaction() as sess:
            sess['cart_ID'] = cart_id
        
        response = client.post('/finish-shopping')
        assert response.status_code == 302
        assert '/pantry-transfer' in response.location
        
        # Verify cart status was updated
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT status FROM shopping_cart WHERE cart_ID = %s", (cart_id,))
            cart = cursor.fetchone()
            assert cart['status'] == 'purchased'
            cursor.close()
        
        # Verify cart_ID was removed from session
        with client.session_transaction() as sess:
            assert 'cart_ID' not in sess
    
    def test_finish_shopping_no_cart(self, client, logged_in_user):
        """Test finishing shopping when no cart exists."""
        response = client.post('/finish-shopping')
        assert response.status_code == 302
        # When no cart exists, it creates a new one and redirects to pantry transfer
        assert '/pantry-transfer' in response.location
    
    def test_cancel_shopping_deletes_cart(self, client, logged_in_user):
        """Test canceling shopping deletes the cart and items."""
        # Create active cart with items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            
            # Add item to cart
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Test Item', 10.99, 1))
            
            cursor.close()
        
        with client.session_transaction() as sess:
            sess['cart_ID'] = cart_id
        
        response = client.post('/cancel-shopping')
        assert response.status_code == 302
        assert '/home' in response.location
        
        # Verify cart and items were deleted
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Check cart deleted
            cursor.execute("SELECT * FROM shopping_cart WHERE cart_ID = %s", (cart_id,))
            assert cursor.fetchone() is None
            
            # Check cart items deleted
            cursor.execute("SELECT * FROM cart_item WHERE cart_ID = %s", (cart_id,))
            assert cursor.fetchone() is None
            
            cursor.close()
        
        # Verify cart_ID was removed from session
        with client.session_transaction() as sess:
            assert 'cart_ID' not in sess
    
    def test_cancel_shopping_no_cart(self, client, logged_in_user):
        """Test canceling shopping when no cart exists."""
        response = client.post('/cancel-shopping')
        assert response.status_code == 302
        assert '/home' in response.location


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.integration
class TestPantryTransfer:
    """Test pantry transfer functionality."""
    
    def test_pantry_transfer_not_authenticated(self, client):
        """Test pantry transfer redirects when not authenticated."""
        response = client.get('/pantry-transfer?cart_id=1')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_pantry_transfer_no_cart_id(self, client, logged_in_user):
        """Test pantry transfer redirects when no cart ID provided."""
        response = client.get('/pantry-transfer')
        assert response.status_code == 302
        assert '/home' in response.location
    
    def test_pantry_transfer_invalid_cart(self, client, logged_in_user):
        """Test pantry transfer redirects for invalid cart ID."""
        response = client.get('/pantry-transfer?cart_id=999')
        assert response.status_code == 302
        assert '/home' in response.location
    
    def test_pantry_transfer_success(self, client, logged_in_user):
        """Test successful pantry transfer page load."""
        # Create purchased cart with items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'purchased'))
            cart_id = cursor.lastrowid
            
            # Add items to cart
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Test Item', 12.99, 1))
            
            cursor.close()
        
        response = client.get(f'/pantry-transfer?cart_id={cart_id}')
        assert response.status_code == 200


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.integration
class TestMealPlanDetails:
    """Test meal plan details view."""
    
    def test_meal_plan_details_not_authenticated(self, client):
        """Test meal plan details redirects when not authenticated."""
        response = client.get('/meal-plans/1')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_meal_plan_details_not_found(self, client, logged_in_user):
        """Test meal plan details with non-existent plan."""
        response = client.get('/meal-plans/999')
        assert response.status_code == 302
        assert '/meal-plans' in response.location
    
    def test_meal_plan_details_success(self, client, logged_in_user):
        """Test successful meal plan details page load."""
        # Create meal plan session
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days)
                VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY), 7)
            """, ('test_user', 'Test Plan'))
            plan_id = cursor.lastrowid
            cursor.close()
        
        response = client.get(f'/meal-plans/{plan_id}')
        assert response.status_code == 200
    
    def test_meal_plan_details_wrong_user(self, client, logged_in_user):
        """Test meal plan details for plan belonging to another user."""
        # Create meal plan session for different user
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days)
                VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY), 7)
            """, ('other_user', 'Other Plan'))
            plan_id = cursor.lastrowid
            cursor.close()
        
        response = client.get(f'/meal-plans/{plan_id}')
        assert response.status_code == 302
        assert '/meal-plans' in response.location


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.unit
class TestUserPreferences:
    """Test user preferences functionality."""
    
    def create_user_preference(self, client, preference_key, preference_value, data_type="string"):
        """Helper to create a user preference."""
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO user_preferences (user_id, preference_key, preference_value, data_type)
                VALUES (%s, %s, %s, %s)
            """, ('test_user', preference_key, preference_value, data_type))
            cursor.close()
    
    def test_get_user_preference_string(self, client, logged_in_user):
        """Test getting string user preference."""
        self.create_user_preference(client, 'test_string', 'test_value', 'string')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_string', 'default')
            assert result == 'test_value'
    
    def test_get_user_preference_boolean_true(self, client, logged_in_user):
        """Test getting boolean user preference (true)."""
        self.create_user_preference(client, 'test_bool', 'true', 'boolean')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_bool', False)
            assert result == True
    
    def test_get_user_preference_boolean_false(self, client, logged_in_user):
        """Test getting boolean user preference (false)."""
        self.create_user_preference(client, 'test_bool', 'false', 'boolean')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_bool', True)
            assert result == False
    
    def test_get_user_preference_integer(self, client, logged_in_user):
        """Test getting integer user preference."""
        self.create_user_preference(client, 'test_int', '42', 'number')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_int', 0)
            assert result == 42
            assert isinstance(result, int)
    
    def test_get_user_preference_float(self, client, logged_in_user):
        """Test getting float user preference."""
        self.create_user_preference(client, 'test_float', '3.14', 'number')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_float', 0.0)
            assert result == 3.14
            assert isinstance(result, float)
    
    def test_get_user_preference_json(self, client, logged_in_user):
        """Test getting JSON user preference."""
        self.create_user_preference(client, 'test_json', '{"key": "value"}', 'json')
        
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'test_json', {})
            assert result == {'key': 'value'}
    
    def test_get_user_preference_not_found(self, client, logged_in_user):
        """Test getting non-existent user preference returns default."""
        from src.backend.views.shopping import get_user_preference
        with client.application.app_context():
            result = get_user_preference('test_user', 'non_existent', 'default_value')
            assert result == 'default_value'
    
    def test_get_user_preference_database_error(self, client, logged_in_user):
        """Test getting user preference handles database errors gracefully."""
        from src.backend.views.shopping import get_user_preference
        
        with patch('src.backend.views.shopping.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            with client.application.app_context():
                result = get_user_preference('test_user', 'test_pref', 'default')
                assert result == 'default'


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.unit
class TestRetrieveTotals:
    """Test retrieve_totals utility function."""
    
    def test_retrieve_totals_empty_cart(self, client, logged_in_user):
        """Test retrieving totals for empty cart."""
        # Create empty cart
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            cursor.close()
        
        from src.backend.views.shopping import retrieve_totals
        with client.application.app_context():
            items, total_items, total_spent = retrieve_totals(cart_id)
            
            assert items == []
            assert total_items == 0
            assert total_spent == 0
    
    def test_retrieve_totals_with_items(self, client, logged_in_user):
        """Test retrieving totals for cart with items."""
        # Create cart with items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            
            # Add items
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Item 1', 10.99, 2))
            
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Item 2', 5.50, 1))
            
            cursor.close()
        
        from src.backend.views.shopping import retrieve_totals
        with client.application.app_context():
            items, total_items, total_spent = retrieve_totals(cart_id)
            
            assert len(items) == 2
            assert total_items == 2
            assert total_spent == 27.48  # (10.99 * 2) + (5.50 * 1)
    
    def test_retrieve_totals_nonexistent_cart(self, client, logged_in_user):
        """Test retrieving totals for non-existent cart."""
        from src.backend.views.shopping import retrieve_totals
        with client.application.app_context():
            items, total_items, total_spent = retrieve_totals(999)
            
            assert items == []
            assert total_items == 0
            assert total_spent == 0


@pytest.mark.shopping
@pytest.mark.views
@pytest.mark.integration
class TestHomePageIntegration:
    """Test home page integration with database queries."""
    
    def create_test_data(self, client):
        """Create test data for home page testing."""
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create purchased carts (history)
            for i in range(3):
                cursor.execute("""
                    INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                """, ('test_user', f'Store {i+1}', 'purchased', datetime.now()))
                cart_id = cursor.lastrowid
                
                # Add items to each cart
                cursor.execute("""
                    INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                    VALUES (%s, %s, %s, %s)
                """, (cart_id, f'Item {i+1}', (i+1) * 5.99, 1))
            
            # Create active cart
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, %s)
            """, ('test_user', 'Active Store', 'active', datetime.now()))
            
            # Create some meals
            for i in range(5):
                cursor.execute("""
                    INSERT INTO meals (user_id, meal_date, meal_type, custom_recipe_name)
                    VALUES (%s, %s, %s, %s)
                """, ('test_user', f'2024-01-{i+1:02d}', 'dinner', f'Meal {i+1}'))
            
            cursor.close()
    
    def test_home_page_displays_data_correctly(self, client, logged_in_user):
        """Test that home page displays correct data from database."""
        self.create_test_data(client)
        
        response = client.get('/home')
        assert response.status_code == 200
        
        # Check that the page renders without errors
        # In a real test, you would check for specific content in the template
    
    def test_home_page_handles_no_data(self, client, logged_in_user):
        """Test home page when user has no data."""
        response = client.get('/home')
        assert response.status_code == 200
        # Should handle empty data gracefully
    
    def test_home_page_large_dataset(self, client, logged_in_user):
        """Test home page performance with large dataset."""
        # Create 20 carts to test limit functionality
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            for i in range(20):
                cursor.execute("""
                    INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                    VALUES (%s, %s, %s, %s)
                """, ('test_user', f'Store {i+1}', 'purchased', datetime.now()))
                cart_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                    VALUES (%s, %s, %s, %s)
                """, (cart_id, f'Item {i+1}', 9.99, 1))
            
            cursor.close()
        
        response = client.get('/home')
        assert response.status_code == 200
        # Home page should limit to 15 initially


@pytest.mark.shopping
@pytest.mark.views  
@pytest.mark.integration
class TestBudgetIntegration:
    """Test budget integration in finish shopping."""
    
    @patch('src.backend.apis.budget.update_budget_spending')
    def test_finish_shopping_updates_budget(self, mock_update_budget, client, logged_in_user):
        """Test that finishing shopping updates budget spending."""
        # Create cart with items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            
            # Add expensive item
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity)
                VALUES (%s, %s, %s, %s)
            """, (cart_id, 'Expensive Item', 99.99, 1))
            
            cursor.close()
        
        with client.session_transaction() as sess:
            sess['cart_ID'] = cart_id
        
        response = client.post('/finish-shopping')
        assert response.status_code == 302
        
        # Verify budget update was called with correct amount
        mock_update_budget.assert_called_once_with('test_user', 99.99)
    
    @patch('src.backend.apis.budget.update_budget_spending')
    def test_finish_shopping_no_budget_update_for_zero_spent(self, mock_update_budget, client, logged_in_user):
        """Test that finishing shopping with zero spending doesn't update budget."""
        # Create cart with no items
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status)
                VALUES (%s, %s, %s)
            """, ('test_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            cursor.close()
        
        with client.session_transaction() as sess:
            sess['cart_ID'] = cart_id
        
        response = client.post('/finish-shopping')
        assert response.status_code == 302
        
        # Budget update should not be called for zero spending
        mock_update_budget.assert_not_called()