"""
Comprehensive tests for pantry.py API.
Tests all endpoints for pantry management including CRUD operations,
filtering, searching, AI predictions, shopping trip transfers, and subscription limits.
"""

import pytest
import json
from datetime import datetime, timedelta, date
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.pantry
@pytest.mark.api
@pytest.mark.unit
class TestPantryItemsAPI:
    """Test pantry items CRUD operations."""
    
    def test_get_pantry_items_not_authenticated(self, client):
        """Test getting pantry items without authentication."""
        response = client.get('/api/pantry/items')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_get_pantry_items_empty(self, client, logged_in_user):
        """Test getting pantry items when user has none."""
        response = client.get('/api/pantry/items')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['items'] == []
        assert data['categorized_items'] == {}
        assert data['total_items'] == 0
    
    def test_add_pantry_item_not_authenticated(self, client):
        """Test adding pantry item without authentication."""
        item_data = {
            'item_name': 'Test Item',
            'quantity': 1,
            'unit': 'pcs'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_add_pantry_item_missing_name(self, client, logged_in_user):
        """Test adding pantry item without name."""
        item_data = {
            'quantity': 1,
            'unit': 'pcs'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Item name is required'
    
    def test_add_pantry_item_empty_name(self, client, logged_in_user):
        """Test adding pantry item with empty name."""
        item_data = {
            'item_name': '   ',
            'quantity': 1,
            'unit': 'pcs'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Item name is required'
    
    def test_add_pantry_item_invalid_quantity(self, client, logged_in_user):
        """Test adding pantry item with invalid quantity."""
        # Negative quantity
        item_data = {
            'item_name': 'Test Item',
            'quantity': -1,
            'unit': 'pcs'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Quantity must be positive'
        
        # Zero quantity
        item_data['quantity'] = 0
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Quantity must be positive'
        
        # Non-numeric quantity
        item_data['quantity'] = 'invalid'
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Invalid quantity'
    
    def test_add_pantry_item_success(self, client, logged_in_user):
        """Test successful pantry item addition."""
        item_data = {
            'item_name': 'Test Item',
            'quantity': 2.5,
            'unit': 'lbs',
            'category': 'Meat',
            'storage_type': 'freezer',
            'expiration_date': '2024-12-31',
            'notes': 'Test notes'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['item']['item_name'] == 'Test Item'
        assert data['item']['quantity'] == 2.5
        assert data['item']['unit'] == 'lbs'
        assert data['item']['category'] == 'Meat'
        assert data['item']['storage_type'] == 'freezer'
        assert data['message'] == 'Item added successfully'
    
    def test_add_pantry_item_with_defaults(self, client, logged_in_user):
        """Test adding pantry item with default values."""
        item_data = {
            'item_name': 'Minimal Item'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['item']['quantity'] == 1
        assert data['item']['unit'] == 'pcs'
        assert data['item']['category'] == 'Other'
        assert data['item']['storage_type'] == 'pantry'
    
    def test_add_pantry_item_with_tags(self, client, logged_in_user):
        """Test adding pantry item with tags."""
        # Create test tags first
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO pantry_tags (user_id, tag_name, tag_color)
                VALUES (%s, %s, %s)
            """, ('test_user', 'organic', '#green'))
            tag_id = cursor.lastrowid
            cursor.close()
        
        item_data = {
            'item_name': 'Tagged Item',
            'quantity': 1,
            'tag_ids': [tag_id]
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['item']['tags']) == 1
        assert data['item']['tags'][0]['name'] == 'organic'
    
    @patch('src.backend.apis.pantry.predict_expiration_and_category')
    def test_add_pantry_item_with_ai_prediction(self, mock_predict, client, logged_in_user):
        """Test adding pantry item with AI expiration prediction."""
        # Mock AI prediction
        mock_predict.return_value = {
            'expiration_date': '2024-01-15',
            'category': 'Produce'
        }
        
        item_data = {
            'item_name': 'Apple',
            'quantity': 5,
            'ai_predict_expiry': True,
            'storage_type': 'fridge'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['ai_predicted'] == True
        assert data['item']['category'] == 'Produce'  # Should use predicted category
        
        # Verify AI function was called
        mock_predict.assert_called_once_with('Apple', 'fridge')


@pytest.mark.pantry
@pytest.mark.subscription
@pytest.mark.unit
class TestPantrySubscriptionLimits:
    """Test subscription limits for pantry items."""
    
    @patch('src.backend.apis.pantry.check_subscription_limit')
    @patch('src.backend.apis.pantry.increment_usage')
    def test_add_item_within_free_limit(self, mock_increment, mock_check, client, logged_in_user):
        """Test adding item within free tier limits."""
        mock_check.return_value = None
        
        item_data = {
            'item_name': 'Free Tier Item',
            'quantity': 1
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        mock_check.assert_called_once_with('test_user', 'pantry_items')
        mock_increment.assert_called_once_with('test_user', 'pantry_items')
    
    @patch('src.backend.apis.pantry.check_subscription_limit')
    def test_add_item_exceeds_free_limit(self, mock_check, client, logged_in_user):
        """Test adding item when exceeding free tier limits."""
        from src.subscription_utils import SubscriptionLimitExceeded
        
        mock_check.side_effect = SubscriptionLimitExceeded(
            limit_type='pantry_items',
            current_limit=50,
            message='Free tier allows maximum 50 pantry items'
        )
        
        item_data = {
            'item_name': 'Over Limit Item',
            'quantity': 1
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['requires_upgrade'] == True
        assert data['limit_type'] == 'pantry_items'
        assert data['current_limit'] == 50


@pytest.mark.pantry
@pytest.mark.api
@pytest.mark.integration
class TestPantryFiltering:
    """Test pantry items filtering and searching."""
    
    def create_test_items(self, client):
        """Helper to create test pantry items."""
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create items with different properties
            test_items = [
                ('Milk', 1, 'gallon', 'Dairy', 'fridge', date.today() + timedelta(days=2)),  # expiring_soon
                ('Rice', 5, 'lbs', 'Grains', 'pantry', date.today() + timedelta(days=365)),  # fresh
                ('Bread', 1, 'loaf', 'Bakery', 'pantry', date.today() - timedelta(days=1)),  # expired
                ('Chicken', 2, 'lbs', 'Meat', 'freezer', None),  # no_expiry
                ('Apples', 6, 'pcs', 'Produce', 'fridge', date.today() + timedelta(days=7))  # fresh
            ]
            
            item_ids = []
            for item_name, quantity, unit, category, storage, expiry in test_items:
                cursor.execute("""
                    INSERT INTO pantry_items (user_id, item_name, quantity, unit, category, storage_type, expiration_date, source_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('test_user', item_name, quantity, unit, category, storage, expiry, 'manual'))
                item_ids.append(cursor.lastrowid)
            
            cursor.close()
            return item_ids
    
    def test_get_pantry_items_with_data(self, client, logged_in_user):
        """Test getting pantry items with test data."""
        self.create_test_items(client)
        
        response = client.get('/api/pantry/items')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 5
        assert len(data['categorized_items']) > 0
        
        # Verify categories are present
        assert 'Dairy' in data['categorized_items']
        assert 'Grains' in data['categorized_items']
        assert 'Meat' in data['categorized_items']
    
    def test_filter_by_storage_type(self, client, logged_in_user):
        """Test filtering pantry items by storage type."""
        self.create_test_items(client)
        
        response = client.get('/api/pantry/items?storage_type=fridge')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Should only return fridge items (Milk and Apples)
        assert data['total_items'] == 2
        for item in data['items']:
            assert item['storage_type'] == 'fridge'
    
    def test_filter_by_category(self, client, logged_in_user):
        """Test filtering pantry items by category."""
        self.create_test_items(client)
        
        response = client.get('/api/pantry/items?category=Dairy')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Should only return dairy items (Milk)
        assert data['total_items'] == 1
        assert data['items'][0]['category'] == 'Dairy'
        assert data['items'][0]['item_name'] == 'Milk'
    
    def test_filter_by_expiry_status(self, client, logged_in_user):
        """Test filtering pantry items by expiry status."""
        self.create_test_items(client)
        
        # Test expired filter
        response = client.get('/api/pantry/items?expiry_status=expired')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 1
        assert data['items'][0]['expiry_status'] == 'expired'
        
        # Test expiring soon filter
        response = client.get('/api/pantry/items?expiry_status=expiring_soon')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 1
        assert data['items'][0]['expiry_status'] == 'expiring_soon'
        
        # Test fresh filter (includes no_expiry items)
        response = client.get('/api/pantry/items?expiry_status=fresh')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 3  # Rice, Chicken (no expiry), Apples
    
    def test_search_functionality(self, client, logged_in_user):
        """Test search functionality in pantry items."""
        self.create_test_items(client)
        
        # Search by item name
        response = client.get('/api/pantry/items?search=milk')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 1
        assert data['items'][0]['item_name'] == 'Milk'
        
        # Search by category
        response = client.get('/api/pantry/items?search=dairy')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 1
        assert data['items'][0]['category'] == 'Dairy'
    
    def test_combined_filters(self, client, logged_in_user):
        """Test combining multiple filters."""
        self.create_test_items(client)
        
        # Filter by storage and category
        response = client.get('/api/pantry/items?storage_type=fridge&category=Produce')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['total_items'] == 1
        assert data['items'][0]['item_name'] == 'Apples'
        assert data['items'][0]['storage_type'] == 'fridge'
        assert data['items'][0]['category'] == 'Produce'


@pytest.mark.pantry
@pytest.mark.api
@pytest.mark.integration
class TestShoppingTripTransfer:
    """Test transferring items from shopping trips to pantry."""
    
    def create_test_shopping_cart(self, client):
        """Helper to create test shopping cart with items."""
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create purchased cart
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, NOW())
            """, ('test_user', 'Test Store', 'purchased'))
            cart_id = cursor.lastrowid
            
            # Add cart items
            cursor.execute("""
                INSERT INTO cart_item (cart_ID, item_name, price, quantity, unit)
                VALUES (%s, %s, %s, %s, %s)
            """, (cart_id, 'Shopping Milk', 3.99, 1, 'gallon'))
            item_id = cursor.lastrowid
            
            cursor.close()
            return cart_id, item_id
    
    def test_transfer_not_authenticated(self, client):
        """Test transfer without authentication."""
        transfer_data = {
            'cart_id': 1,
            'items': []
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Not authenticated'
    
    def test_transfer_missing_cart_id(self, client, logged_in_user):
        """Test transfer without cart ID."""
        transfer_data = {
            'items': []
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Cart ID is required'
    
    def test_transfer_invalid_cart(self, client, logged_in_user):
        """Test transfer with invalid cart ID."""
        transfer_data = {
            'cart_id': 999,
            'items': []
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['message'] == 'Shopping trip not found or not completed'
    
    def test_transfer_success(self, client, logged_in_user):
        """Test successful transfer from shopping trip."""
        cart_id, item_id = self.create_test_shopping_cart(client)
        
        transfer_data = {
            'cart_id': cart_id,
            'items': [
                {
                    'item_id': item_id,
                    'quantity': 1,
                    'unit': 'gallon',
                    'category': 'Dairy',
                    'storage_type': 'fridge',
                    'expiration_date': '2024-01-10',
                    'notes': 'From shopping trip'
                }
            ]
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['items_added'] == 1
        assert 'transfer_id' in data
        
        # Verify item was added to pantry
        response = client.get('/api/pantry/items')
        pantry_data = json.loads(response.data)
        assert len(pantry_data['items']) == 1
        assert pantry_data['items'][0]['item_name'] == 'Shopping Milk'
        assert pantry_data['items'][0]['source_type'] == 'shopping_trip'
    
    def test_transfer_already_completed(self, client, logged_in_user):
        """Test transfer when cart has already been transferred."""
        cart_id, item_id = self.create_test_shopping_cart(client)
        
        # Create existing transfer session
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO pantry_transfer_sessions (user_id, cart_id, items_transferred)
                VALUES (%s, %s, %s)
            """, ('test_user', cart_id, 1))
            cursor.close()
        
        transfer_data = {
            'cart_id': cart_id,
            'items': []
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'already been transferred' in data['message']
    
    @patch('src.backend.apis.pantry.predict_expiration_and_category')
    def test_transfer_with_ai_prediction(self, mock_predict, client, logged_in_user):
        """Test transfer with AI expiration prediction."""
        cart_id, item_id = self.create_test_shopping_cart(client)
        
        mock_predict.return_value = {
            'expiration_date': '2024-01-15',
            'category': 'Dairy'
        }
        
        transfer_data = {
            'cart_id': cart_id,
            'items': [
                {
                    'item_id': item_id,
                    'quantity': 1,
                    'storage_type': 'fridge',
                    'ai_predict_expiry': True
                }
            ]
        }
        response = client.post('/api/pantry/transfer-from-trip',
                              data=json.dumps(transfer_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Verify AI prediction was called
        mock_predict.assert_called_once_with('Shopping Milk', 'fridge')


@pytest.mark.pantry
@pytest.mark.unit
class TestPantryUtilityFunctions:
    """Test pantry utility functions."""
    
    @patch('src.backend.apis.pantry.get_db')
    def test_predict_expiration_date_cached(self, mock_get_db, app):
        """Test expiration prediction with cached data."""
        # Mock database response for cached prediction
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'predicted_days': 7}
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        from src.backend.apis.pantry import predict_expiration_date
        
        with app.app_context():
            result = predict_expiration_date('apple', 'fridge')
            
            # Should return a date 7 days from now
            expected_date = date.today() + timedelta(days=7)
            assert result == expected_date.strftime('%Y-%m-%d')
    
    @patch('src.backend.apis.pantry.get_db')
    def test_predict_expiration_date_not_cached(self, mock_get_db, app):
        """Test expiration prediction without cached data."""
        # Mock database response for no cached prediction
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        from src.backend.apis.pantry import predict_expiration_date
        
        with app.app_context():
            result = predict_expiration_date('unknown_item', 'pantry')
            
            # Should return None when no prediction available
            assert result is None
    
    @patch('src.backend.apis.pantry.get_db')
    def test_predict_expiration_and_category(self, mock_get_db, app):
        """Test combined expiration and category prediction."""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'predicted_days': 14}
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        from src.backend.apis.pantry import predict_expiration_and_category
        
        with app.app_context():
            result = predict_expiration_and_category('banana', 'counter')
            
            assert result is not None
            assert 'expiration_date' in result
            assert 'category' in result
            
            # Should return date 14 days from now
            expected_date = date.today() + timedelta(days=14)
            assert result['expiration_date'] == expected_date.strftime('%Y-%m-%d')


@pytest.mark.pantry
@pytest.mark.api
@pytest.mark.unit
class TestPantryErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_data(self, client, logged_in_user):
        """Test handling of invalid JSON data."""
        response = client.post('/api/pantry/items',
                              data='invalid json',
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_add_item_database_error(self, client, logged_in_user):
        """Test handling of database errors during item addition."""
        with patch('src.backend.apis.pantry.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            item_data = {
                'item_name': 'Test Item',
                'quantity': 1
            }
            response = client.post('/api/pantry/items',
                                  data=json.dumps(item_data),
                                  content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Failed to add pantry item' in data['message']
    
    def test_transfer_database_error(self, client, logged_in_user):
        """Test handling of database errors during transfer."""
        with patch('src.backend.apis.pantry.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            transfer_data = {
                'cart_id': 1,
                'items': []
            }
            response = client.post('/api/pantry/transfer-from-trip',
                                  data=json.dumps(transfer_data),
                                  content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Failed to transfer items' in data['message']
    
    def test_get_items_database_error(self, client, logged_in_user):
        """Test handling of database errors when getting items."""
        with patch('src.backend.apis.pantry.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db = MagicMock()
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get('/api/pantry/items')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Failed to get pantry items' in data['message']
    
    def test_quantity_type_conversion(self, client, logged_in_user):
        """Test that quantity is properly converted to float."""
        # String quantity should be converted
        item_data = {
            'item_name': 'String Quantity Item',
            'quantity': '3.14'
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['item']['quantity'] == 3.14
    
    def test_empty_tag_list_handling(self, client, logged_in_user):
        """Test handling of empty tag list."""
        item_data = {
            'item_name': 'No Tags Item',
            'quantity': 1,
            'tag_ids': []
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['item']['tags'] == []
    
    def test_invalid_tag_ids_filtering(self, client, logged_in_user):
        """Test filtering out invalid tag IDs."""
        item_data = {
            'item_name': 'Invalid Tags Item',
            'quantity': 1,
            'tag_ids': [999, 1000]  # Non-existent tag IDs
        }
        response = client.post('/api/pantry/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['item']['tags'] == []  # Invalid tags should be filtered out


@pytest.mark.pantry
@pytest.mark.premium
@pytest.mark.integration
class TestPantryPremiumFeatures:
    """Test premium tier features for pantry management."""
    
    def test_premium_unlimited_items(self, client, premium_user):
        """Test that premium users have unlimited pantry items."""
        # Premium users should not hit pantry item limits
        for i in range(10):  # Add multiple items
            item_data = {
                'item_name': f'Premium Item {i+1}',
                'quantity': 1
            }
            response = client.post('/api/pantry/items',
                                  data=json.dumps(item_data),
                                  content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
    
    def test_premium_advanced_features(self, client, premium_user):
        """Test advanced features available to premium users."""
        # Premium users can use AI predictions without limits
        with patch('src.backend.apis.pantry.predict_expiration_and_category') as mock_predict:
            mock_predict.return_value = {
                'expiration_date': '2024-02-15',
                'category': 'Premium Produce'
            }
            
            item_data = {
                'item_name': 'Premium Apple',
                'quantity': 1,
                'ai_predict_expiry': True
            }
            response = client.post('/api/pantry/items',
                                  data=json.dumps(item_data),
                                  content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['ai_predicted'] == True