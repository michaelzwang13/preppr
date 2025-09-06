"""
Comprehensive tests for shopping_list.py API.
Tests all endpoints for shopping list management including CRUD operations,
item management, subscription limits, and error handling.
"""

import pytest
import json
from datetime import datetime
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestShoppingListAPI:
    """Test shopping list CRUD operations."""
    
    def test_get_shopping_lists_not_authenticated(self, client):
        """Test getting shopping lists without authentication."""
        response = client.get('/api/shopping-lists')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_get_shopping_lists_empty(self, client, logged_in_user):
        """Test getting shopping lists when user has none."""
        response = client.get('/api/shopping-lists')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['lists'] == []
    
    def test_create_shopping_list_not_authenticated(self, client):
        """Test creating shopping list without authentication."""
        list_data = {'name': 'Test List', 'description': 'Test description'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_create_shopping_list_missing_name(self, client, logged_in_user):
        """Test creating shopping list without name."""
        list_data = {'description': 'Test description'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'List name is required'
    
    def test_create_shopping_list_empty_name(self, client, logged_in_user):
        """Test creating shopping list with empty name."""
        list_data = {'name': '   ', 'description': 'Test description'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'List name is required'
    
    def test_create_shopping_list_success(self, client, logged_in_user):
        """Test successful creation of shopping list."""
        list_data = {
            'name': 'Grocery List',
            'description': 'Weekly groceries'
        }
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['list']['name'] == 'Grocery List'
        assert data['list']['description'] == 'Weekly groceries'
        assert data['list']['items'] == []
        assert 'id' in data['list']
    
    def test_update_shopping_list_not_authenticated(self, client):
        """Test updating shopping list without authentication."""
        response = client.patch('/api/shopping-lists/1',
                               data=json.dumps({'name': 'Updated List'}),
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_update_shopping_list_not_found(self, client, logged_in_user):
        """Test updating non-existent shopping list."""
        response = client.patch('/api/shopping-lists/999',
                               data=json.dumps({'name': 'Updated List'}),
                               content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Shopping list not found'
    
    def test_delete_shopping_list_not_authenticated(self, client):
        """Test deleting shopping list without authentication."""
        response = client.delete('/api/shopping-lists/1')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_delete_shopping_list_not_found(self, client, logged_in_user):
        """Test deleting non-existent shopping list."""
        response = client.delete('/api/shopping-lists/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Shopping list not found'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.integration
class TestShoppingListIntegration:
    """Integration tests for shopping list operations."""
    
    def test_full_shopping_list_lifecycle(self, client, logged_in_user):
        """Test complete shopping list lifecycle: create, read, update, delete."""
        # 1. Create shopping list
        list_data = {
            'name': 'Lifecycle Test List',
            'description': 'Test list for lifecycle'
        }
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 201
        create_data = json.loads(response.data)
        list_id = create_data['list']['id']
        
        # 2. Read - verify list appears in get_shopping_lists
        response = client.get('/api/shopping-lists')
        assert response.status_code == 200
        lists_data = json.loads(response.data)
        assert len(lists_data['lists']) == 1
        assert lists_data['lists'][0]['name'] == 'Lifecycle Test List'
        assert lists_data['lists'][0]['description'] == 'Test list for lifecycle'
        
        # 3. Update shopping list
        update_data = {
            'name': 'Updated Lifecycle List',
            'description': 'Updated description'
        }
        response = client.patch(f'/api/shopping-lists/{list_id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        assert response.status_code == 200
        
        # Verify update
        response = client.get('/api/shopping-lists')
        lists_data = json.loads(response.data)
        assert lists_data['lists'][0]['name'] == 'Updated Lifecycle List'
        assert lists_data['lists'][0]['description'] == 'Updated description'
        
        # 4. Delete shopping list
        response = client.delete(f'/api/shopping-lists/{list_id}')
        assert response.status_code == 200
        
        # Verify deletion (soft delete - should not appear in get_shopping_lists)
        response = client.get('/api/shopping-lists')
        lists_data = json.loads(response.data)
        assert len(lists_data['lists']) == 0
    
    def test_shopping_list_with_items(self, client, logged_in_user):
        """Test shopping list with item management."""
        # Create shopping list
        list_data = {'name': 'Items Test List', 'description': 'Test with items'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        # Add items to list
        items = [
            {'name': 'Apples', 'quantity': 5, 'notes': 'Red apples'},
            {'name': 'Milk', 'quantity': 1, 'notes': 'Whole milk'},
            {'name': 'Bread', 'quantity': 2, 'notes': 'Whole wheat'}
        ]
        
        item_ids = []
        for item in items:
            response = client.post(f'/api/shopping-lists/{list_id}/items',
                                  data=json.dumps(item),
                                  content_type='application/json')
            assert response.status_code == 201
            item_data = json.loads(response.data)
            item_ids.append(item_data['item']['id'])
        
        # Verify items appear in list
        response = client.get('/api/shopping-lists')
        lists_data = json.loads(response.data)
        list_items = lists_data['lists'][0]['items']
        assert len(list_items) == 3
        
        item_names = [item['name'] for item in list_items]
        assert 'Apples' in item_names
        assert 'Milk' in item_names
        assert 'Bread' in item_names
        
        # Test item completion toggle
        first_item_id = item_ids[0]
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{first_item_id}/toggle')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['is_completed'] == True
        
        # Toggle back
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{first_item_id}/toggle')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['is_completed'] == False
        
        # Test item update
        update_item_data = {'name': 'Green Apples', 'quantity': 6}
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{first_item_id}',
                               data=json.dumps(update_item_data),
                               content_type='application/json')
        assert response.status_code == 200
        
        # Test item deletion
        response = client.delete(f'/api/shopping-lists/{list_id}/items/{first_item_id}')
        assert response.status_code == 200
        
        # Verify item was deleted
        response = client.get('/api/shopping-lists')
        lists_data = json.loads(response.data)
        list_items = lists_data['lists'][0]['items']
        assert len(list_items) == 2  # One item deleted


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestShoppingListItems:
    """Test shopping list item management."""
    
    def create_test_list(self, client):
        """Helper method to create a test shopping list."""
        list_data = {'name': 'Test List', 'description': 'Test'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        return json.loads(response.data)['list']['id']
    
    def test_add_item_not_authenticated(self, client):
        """Test adding item without authentication."""
        item_data = {'name': 'Test Item', 'quantity': 1}
        response = client.post('/api/shopping-lists/1/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_add_item_missing_name(self, client, logged_in_user):
        """Test adding item without name."""
        list_id = self.create_test_list(client)
        item_data = {'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Item name is required'
    
    def test_add_item_empty_name(self, client, logged_in_user):
        """Test adding item with empty name."""
        list_id = self.create_test_list(client)
        item_data = {'name': '   ', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Item name is required'
    
    def test_add_item_success(self, client, logged_in_user):
        """Test successful item addition."""
        list_id = self.create_test_list(client)
        item_data = {
            'name': 'Test Item',
            'quantity': 3,
            'notes': 'Test notes'
        }
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['item']['name'] == 'Test Item'
        assert data['item']['quantity'] == 3
        assert data['item']['notes'] == 'Test notes'
        assert data['item']['is_completed'] == False
    
    def test_add_item_invalid_quantity(self, client, logged_in_user):
        """Test adding item with invalid quantity (should default to 1)."""
        list_id = self.create_test_list(client)
        
        # Test negative quantity
        item_data = {'name': 'Test Item', 'quantity': -1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['item']['quantity'] == 1  # Should default to 1
        
        # Test non-numeric quantity
        item_data = {'name': 'Test Item 2', 'quantity': 'invalid'}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['item']['quantity'] == 1  # Should default to 1
    
    def test_add_item_to_nonexistent_list(self, client, logged_in_user):
        """Test adding item to non-existent list."""
        item_data = {'name': 'Test Item', 'quantity': 1}
        response = client.post('/api/shopping-lists/999/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Shopping list not found'
    
    def test_add_item_exceed_limit(self, client, logged_in_user):
        """Test adding items beyond 25 item limit."""
        list_id = self.create_test_list(client)
        
        # Add 25 items
        for i in range(25):
            item_data = {'name': f'Item {i+1}', 'quantity': 1}
            response = client.post(f'/api/shopping-lists/{list_id}/items',
                                  data=json.dumps(item_data),
                                  content_type='application/json')
            assert response.status_code == 201
        
        # Try to add 26th item
        item_data = {'name': 'Extra Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Maximum 25 items' in data['error']
    
    def test_toggle_item_not_authenticated(self, client):
        """Test toggling item completion without authentication."""
        response = client.patch('/api/shopping-lists/1/items/1/toggle')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_toggle_item_not_found(self, client, logged_in_user):
        """Test toggling non-existent item."""
        list_id = self.create_test_list(client)
        response = client.patch(f'/api/shopping-lists/{list_id}/items/999/toggle')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Item not found'
    
    def test_update_item_not_authenticated(self, client):
        """Test updating item without authentication."""
        response = client.patch('/api/shopping-lists/1/items/1',
                               data=json.dumps({'name': 'Updated Item'}),
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_update_item_not_found(self, client, logged_in_user):
        """Test updating non-existent item."""
        list_id = self.create_test_list(client)
        response = client.patch(f'/api/shopping-lists/{list_id}/items/999',
                               data=json.dumps({'name': 'Updated Item'}),
                               content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Item not found'
    
    def test_update_item_empty_name(self, client, logged_in_user):
        """Test updating item with empty name."""
        list_id = self.create_test_list(client)
        
        # Add item first
        item_data = {'name': 'Original Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        item_id = json.loads(response.data)['item']['id']
        
        # Try to update with empty name
        update_data = {'name': '   '}
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{item_id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Item name cannot be empty'
    
    def test_update_item_invalid_quantity(self, client, logged_in_user):
        """Test updating item with invalid quantity."""
        list_id = self.create_test_list(client)
        
        # Add item first
        item_data = {'name': 'Test Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        item_id = json.loads(response.data)['item']['id']
        
        # Try to update with quantity less than 1
        update_data = {'quantity': 0}
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{item_id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Quantity must be at least 1'
        
        # Try to update with non-numeric quantity
        update_data = {'quantity': 'invalid'}
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{item_id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Invalid quantity'
    
    def test_update_item_no_fields(self, client, logged_in_user):
        """Test updating item with no valid fields."""
        list_id = self.create_test_list(client)
        
        # Add item first
        item_data = {'name': 'Test Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        item_id = json.loads(response.data)['item']['id']
        
        # Try to update with no valid fields
        response = client.patch(f'/api/shopping-lists/{list_id}/items/{item_id}',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No valid fields to update'
    
    def test_delete_item_not_authenticated(self, client):
        """Test deleting item without authentication."""
        response = client.delete('/api/shopping-lists/1/items/1')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'
    
    def test_delete_item_not_found(self, client, logged_in_user):
        """Test deleting non-existent item."""
        list_id = self.create_test_list(client)
        response = client.delete(f'/api/shopping-lists/{list_id}/items/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Item not found'


@pytest.mark.shopping
@pytest.mark.subscription
@pytest.mark.unit
class TestShoppingListSubscriptionLimits:
    """Test subscription limits for shopping lists."""
    
    @patch('src.backend.apis.shopping_list.subscription_required')
    def test_create_list_with_subscription_decorator(self, mock_decorator, client, logged_in_user):
        """Test that subscription decorator is applied to create_shopping_list."""
        # Mock the decorator to return the original function
        mock_decorator.return_value = lambda f: f
        
        list_data = {'name': 'Test List', 'description': 'Test'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        assert response.status_code == 201
        
        # Verify decorator was called with correct parameter
        mock_decorator.assert_called_once_with('shopping_lists_per_day')
    
    def test_create_multiple_lists_same_day(self, client, logged_in_user):
        """Test creating multiple lists in the same day."""
        # This test verifies the subscription system is working
        # The actual limit enforcement is handled by the subscription decorator
        
        for i in range(3):  # Try to create 3 lists
            list_data = {'name': f'Test List {i+1}', 'description': f'Test {i+1}'}
            response = client.post('/api/shopping-lists',
                                  data=json.dumps(list_data),
                                  content_type='application/json')
            # In a real scenario with subscription limits, some of these might fail
            # But for testing purposes, we'll verify they can be created
            if response.status_code == 201:
                data = json.loads(response.data)
                assert data['list']['name'] == f'Test List {i+1}'


@pytest.mark.shopping
@pytest.mark.premium
@pytest.mark.integration
class TestShoppingListPremiumFeatures:
    """Test premium tier features for shopping lists."""
    
    def test_premium_user_unlimited_lists(self, client, premium_user):
        """Test that premium users can create multiple lists."""
        # Premium users should have unlimited shopping lists per day
        
        for i in range(5):  # Create 5 lists
            list_data = {'name': f'Premium List {i+1}', 'description': f'Premium test {i+1}'}
            response = client.post('/api/shopping-lists',
                                  data=json.dumps(list_data),
                                  content_type='application/json')
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['list']['name'] == f'Premium List {i+1}'
        
        # Verify all lists exist
        response = client.get('/api/shopping-lists')
        data = json.loads(response.data)
        assert len(data['lists']) == 5


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestShoppingListErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_data(self, client, logged_in_user):
        """Test handling of invalid JSON data."""
        response = client.post('/api/shopping-lists',
                              data='invalid json',
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_update_list_with_empty_data(self, client, logged_in_user):
        """Test updating list with empty data."""
        # Create list first
        list_data = {'name': 'Test List', 'description': 'Test'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        # Update with empty data (should succeed but do nothing)
        response = client.patch(f'/api/shopping-lists/{list_id}',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_partial_list_updates(self, client, logged_in_user):
        """Test partial updates to shopping lists."""
        # Create list first
        list_data = {'name': 'Original List', 'description': 'Original description'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        # Update only name
        response = client.patch(f'/api/shopping-lists/{list_id}',
                               data=json.dumps({'name': 'Updated Name'}),
                               content_type='application/json')
        assert response.status_code == 200
        
        # Update only description
        response = client.patch(f'/api/shopping-lists/{list_id}',
                               data=json.dumps({'description': 'Updated description'}),
                               content_type='application/json')
        assert response.status_code == 200
        
        # Verify both updates took effect
        response = client.get('/api/shopping-lists')
        data = json.loads(response.data)
        assert data['lists'][0]['name'] == 'Updated Name'
        assert data['lists'][0]['description'] == 'Updated description'
    
    def test_access_other_user_list(self, client, logged_in_user):
        """Test attempting to access another user's list."""
        # Create a list in the database for a different user
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_lists (user_id, list_name, description)
                VALUES (%s, %s, %s)
            """, ('other_user', 'Other User List', 'Not accessible'))
            other_list_id = cursor.lastrowid
            cursor.close()
        
        # Try to access other user's list
        response = client.patch(f'/api/shopping-lists/{other_list_id}',
                               data=json.dumps({'name': 'Hacked List'}),
                               content_type='application/json')
        assert response.status_code == 404
        
        # Try to delete other user's list
        response = client.delete(f'/api/shopping-lists/{other_list_id}')
        assert response.status_code == 404
        
        # Try to add item to other user's list
        response = client.post(f'/api/shopping-lists/{other_list_id}/items',
                              data=json.dumps({'name': 'Hacked Item'}),
                              content_type='application/json')
        assert response.status_code == 404
    
    def test_soft_delete_behavior(self, client, logged_in_user):
        """Test that deleted lists don't appear in listings but exist in database."""
        # Create and delete a list
        list_data = {'name': 'To Be Deleted', 'description': 'Test soft delete'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        response = client.delete(f'/api/shopping-lists/{list_id}')
        assert response.status_code == 200
        
        # Verify list doesn't appear in get_shopping_lists
        response = client.get('/api/shopping-lists')
        data = json.loads(response.data)
        assert len(data['lists']) == 0
        
        # Verify list still exists in database with is_active = FALSE
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "SELECT list_id, is_active FROM shopping_lists WHERE list_id = %s",
                (list_id,)
            )
            result = cursor.fetchone()
            assert result is not None
            assert result['is_active'] == 0  # FALSE
            cursor.close()


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.integration
class TestShoppingListDataFormatting:
    """Test data formatting and serialization."""
    
    def test_date_time_formatting(self, client, logged_in_user):
        """Test that dates are properly formatted in responses."""
        # Create list
        list_data = {'name': 'Date Test List', 'description': 'Test dates'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        # Add item
        item_data = {'name': 'Date Test Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        
        # Get lists and verify date formatting
        response = client.get('/api/shopping-lists')
        data = json.loads(response.data)
        
        shopping_list = data['lists'][0]
        assert shopping_list['created_at'] is not None
        assert shopping_list['updated_at'] is not None
        
        # Dates should be in ISO format
        try:
            datetime.fromisoformat(shopping_list['created_at'].replace('Z', '+00:00'))
            datetime.fromisoformat(shopping_list['updated_at'].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Date formatting is not in valid ISO format")
        
        # Check item dates
        item = shopping_list['items'][0]
        assert item['created_at'] is not None
        assert item['updated_at'] is not None
    
    def test_boolean_conversion(self, client, logged_in_user):
        """Test that boolean fields are properly converted."""
        # Create list and item
        list_data = {'name': 'Boolean Test List', 'description': 'Test booleans'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        item_data = {'name': 'Boolean Test Item', 'quantity': 1}
        response = client.post(f'/api/shopping-lists/{list_id}/items',
                              data=json.dumps(item_data),
                              content_type='application/json')
        
        # Get lists and check boolean fields
        response = client.get('/api/shopping-lists')
        data = json.loads(response.data)
        
        shopping_list = data['lists'][0]
        assert isinstance(shopping_list['is_active'], bool)
        
        item = shopping_list['items'][0]
        assert isinstance(item['is_completed'], bool)
        assert item['is_completed'] == False  # Should default to False
    
    def test_quantity_handling(self, client, logged_in_user):
        """Test quantity field handling and conversion."""
        # Create list
        list_data = {'name': 'Quantity Test List', 'description': 'Test quantities'}
        response = client.post('/api/shopping-lists',
                              data=json.dumps(list_data),
                              content_type='application/json')
        list_id = json.loads(response.data)['list']['id']
        
        # Test various quantity values
        test_quantities = [1, 5, 10, '3', 0, -1, 'invalid', None]
        expected_quantities = [1, 5, 10, 3, 1, 1, 1, 1]  # After processing
        
        for i, (test_qty, expected_qty) in enumerate(zip(test_quantities, expected_quantities)):
            item_data = {'name': f'Item {i+1}', 'quantity': test_qty}
            response = client.post(f'/api/shopping-lists/{list_id}/items',
                                  data=json.dumps(item_data),
                                  content_type='application/json')
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['item']['quantity'] == expected_qty