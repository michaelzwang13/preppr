"""
Comprehensive tests for shopping list integration API endpoints.
Tests integration between shopping lists and shopping cart functionality.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

@pytest.mark.api
@pytest.mark.shopping
class TestCreateCartWithList:
    """Test creating shopping carts and importing shopping lists."""
    
    def test_create_cart_success(self, client, logged_in_user, test_db):
        """Test successfully creating a new shopping cart."""
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "Target"
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["store_name"] == "Target"
        assert "cart_id" in data
        assert data["imported_list"] is False
        
        cursor = test_db.cursor()
        
        # Verify cart was created in database
        cursor.execute("SELECT * FROM shopping_cart WHERE cart_ID = %s", (data["cart_id"],))
        cart = cursor.fetchone()
        assert cart["store_name"] == "Target"
        assert cart["status"] == "active"
    
    def test_create_cart_with_existing_active_cart(self, client, logged_in_user, test_db):
        """Test creating cart when user already has active cart."""
        cursor = test_db.cursor()
        
        # Create existing active cart
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Old Store", "active"))
        existing_cart_id = cursor.lastrowid
        
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "New Store"
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["cart_id"] == existing_cart_id
        assert data["store_name"] == "New Store"
        
        # Verify store name was updated
        cursor.execute("SELECT store_name FROM shopping_cart WHERE cart_ID = %s", (existing_cart_id,))
        result = cursor.fetchone()
        assert result["store_name"] == "New Store"
    
    def test_create_cart_with_shopping_list_import(self, client, logged_in_user, test_db):
        """Test creating cart with shopping list import."""
        cursor = test_db.cursor()
        
        # Create shopping list
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Grocery List", True))
        list_id = cursor.lastrowid
        
        # Add items to shopping list
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, notes, is_completed)
            VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
        """, (list_id, "milk", 1, "whole milk", False,
              list_id, "bread", 2, "wheat bread", True))
        
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "Walmart",
            "import_list_id": list_id
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        assert data["imported_list"] is True
        
        # Verify mappings were created
        cursor.execute("""
            SELECT COUNT(*) as mapping_count 
            FROM shopping_list_cart_mapping 
            WHERE cart_id = %s
        """, (data["cart_id"],))
        result = cursor.fetchone()
        assert result["mapping_count"] == 2
    
    def test_create_cart_missing_store_name(self, client, logged_in_user):
        """Test creating cart without store name."""
        response = client.post("/api/shopping-trip/create-cart", json={})
        assert response.status_code == 400
        
        data = response.get_json()
        assert "Store name is required" in data["error"]
    
    def test_create_cart_empty_store_name(self, client, logged_in_user):
        """Test creating cart with empty store name."""
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "   "
        })
        assert response.status_code == 400
        
        data = response.get_json()
        assert "Store name is required" in data["error"]
    
    def test_create_cart_invalid_shopping_list(self, client, logged_in_user):
        """Test creating cart with invalid shopping list ID."""
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "Store",
            "import_list_id": 99999
        })
        assert response.status_code == 404
        
        data = response.get_json()
        assert "Shopping list not found" in data["error"]
    
    def test_create_cart_not_authenticated(self, client):
        """Test creating cart when not authenticated."""
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "Store"
        })
        assert response.status_code == 401
        
        data = response.get_json()
        assert "Not authenticated" in data["error"]
    
    def test_create_cart_shopping_list_link_failure(self, client, logged_in_user, test_db):
        """Test handling shopping_list_id column not existing."""
        cursor = test_db.cursor()
        
        # Create shopping list
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity)
            VALUES (%s, %s, %s)
        """, (list_id, "test item", 1))
        
        # Mock the update query to fail (simulating missing shopping_list_id column)
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            
            # Setup cursor calls in order
            call_count = 0
            def cursor_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 4:  # existing cart check, INSERT cart, verify list, then UPDATE shopping_cart
                    raise Exception("Column 'shopping_list_id' doesn't exist")
                return None
            
            mock_cursor.execute.side_effect = cursor_side_effect
            mock_cursor.fetchone.side_effect = [
                None,  # existing cart check
                {"list_id": list_id, "list_name": "Test List"},  # shopping list verification
                {"item_id": 1, "item_name": "test item", "quantity": 1, "notes": None, "is_completed": False}
            ]
            mock_cursor.fetchall.return_value = [
                {"item_id": 1, "item_name": "test item", "quantity": 1, "notes": None, "is_completed": False}
            ]
            mock_cursor.lastrowid = 123  # cart_id
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.post("/api/shopping-trip/create-cart", json={
                "store_name": "Test Store",
                "import_list_id": list_id
            })
            
            # Should still succeed even if linking fails
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
    
    def test_create_cart_database_error(self, client, logged_in_user):
        """Test handling database errors during cart creation."""
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database connection error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.post("/api/shopping-trip/create-cart", json={
                "store_name": "Test Store"
            })
            assert response.status_code == 500
            
            data = response.get_json()
            assert "Failed to create shopping cart" in data["error"]


@pytest.mark.api
@pytest.mark.shopping
class TestGetShoppingListStatus:
    """Test getting shopping list status for active trips."""
    
    def test_get_shopping_list_status_success(self, client, logged_in_user, test_db):
        """Test successfully getting shopping list status."""
        cursor = test_db.cursor()
        
        # Create shopping list
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Trip List", True))
        list_id = cursor.lastrowid
        
        # Create shopping cart linked to list
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status, shopping_list_id)
            VALUES (%s, %s, %s, %s)
        """, (logged_in_user, "Store", "active", list_id))
        cart_id = cursor.lastrowid
        
        # Add items to shopping list
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, notes, is_completed)
            VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
        """, (list_id, "apples", 5, "red apples", False,
              list_id, "bananas", 3, "ripe bananas", True))
        
        item_ids = []
        cursor.execute("SELECT item_id FROM shopping_list_items WHERE list_id = %s ORDER BY item_name", (list_id,))
        item_ids = [row["item_id"] for row in cursor.fetchall()]
        
        # Create cart item and link to shopping list item
        cursor.execute("""
            INSERT INTO cart_item (cart_ID, item_name, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (cart_id, "bananas", 3, 2.99))
        cart_item_id = cursor.lastrowid
        
        # Create mappings
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found, cart_item_id)
            VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
        """, (cart_id, item_ids[0], False, None,  # apples not found
              cart_id, item_ids[1], True, cart_item_id))  # bananas found and in cart
        
        response = client.get(f"/api/shopping-trip/list-status?cart_id={cart_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["has_list"] is True
        assert data["list_name"] == "Trip List"
        assert len(data["items"]) == 2
        
        # Check items details
        items_by_name = {item["name"]: item for item in data["items"]}
        
        apples = items_by_name["apples"]
        assert apples["quantity"] == 5
        assert apples["notes"] == "red apples"
        assert apples["originally_completed"] is False
        assert apples["is_found"] is False
        assert apples["in_cart"] is False
        
        bananas = items_by_name["bananas"]
        assert bananas["originally_completed"] is True
        assert bananas["is_found"] is True
        assert bananas["in_cart"] is True
        assert bananas["cart_details"]["name"] == "bananas"
        assert bananas["cart_details"]["price"] == 2.99
    
    def test_get_shopping_list_status_no_list(self, client, logged_in_user, test_db):
        """Test getting status for cart with no linked shopping list."""
        cursor = test_db.cursor()
        
        # Create cart without shopping list
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        response = client.get(f"/api/shopping-trip/list-status?cart_id={cart_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["has_list"] is False
    
    def test_get_shopping_list_status_missing_cart_id(self, client, logged_in_user):
        """Test getting status without cart_id parameter."""
        response = client.get("/api/shopping-trip/list-status")
        assert response.status_code == 400
        
        data = response.get_json()
        assert "cart_id is required" in data["error"]
    
    def test_get_shopping_list_status_not_authenticated(self, client):
        """Test getting status when not authenticated."""
        response = client.get("/api/shopping-trip/list-status?cart_id=1")
        assert response.status_code == 401
        
        data = response.get_json()
        assert "Not authenticated" in data["error"]
    
    def test_get_shopping_list_status_cart_not_found(self, client, logged_in_user):
        """Test getting status for non-existent cart."""
        response = client.get("/api/shopping-trip/list-status?cart_id=99999")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["has_list"] is False
    
    def test_get_shopping_list_status_database_error(self, client, logged_in_user):
        """Test handling database errors."""
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/shopping-trip/list-status?cart_id=1")
            assert response.status_code == 500
            
            data = response.get_json()
            assert "Failed to get shopping list status" in data["error"]


@pytest.mark.api
@pytest.mark.shopping
class TestMarkItemFound:
    """Test marking shopping list items as found during shopping."""
    
    def test_mark_item_found_success(self, client, logged_in_user, test_db):
        """Test successfully marking an item as found."""
        cursor = test_db.cursor()
        
        # Create shopping list and cart
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, is_completed)
            VALUES (%s, %s, %s, %s)
        """, (list_id, "eggs", 12, False))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        # Create mapping
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
            VALUES (%s, %s, %s)
        """, (cart_id, item_id, False))
        
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": item_id,
            "cart_id": cart_id,
            "is_found": True
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Verify mapping was updated
        cursor.execute("""
            SELECT is_found FROM shopping_list_cart_mapping 
            WHERE cart_id = %s AND list_item_id = %s
        """, (cart_id, item_id))
        result = cursor.fetchone()
        assert result["is_found"] == 1
        
        # Verify original list item was updated
        cursor.execute("""
            SELECT is_completed FROM shopping_list_items WHERE item_id = %s
        """, (item_id,))
        result = cursor.fetchone()
        assert result["is_completed"] == 1
    
    def test_mark_item_not_found(self, client, logged_in_user, test_db):
        """Test marking an item as not found."""
        cursor = test_db.cursor()
        
        # Setup data
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, is_completed)
            VALUES (%s, %s, %s, %s)
        """, (list_id, "special item", 1, True))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
            VALUES (%s, %s, %s)
        """, (cart_id, item_id, True))
        
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": item_id,
            "cart_id": cart_id,
            "is_found": False
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Verify updates
        cursor.execute("""
            SELECT is_found FROM shopping_list_cart_mapping 
            WHERE cart_id = %s AND list_item_id = %s
        """, (cart_id, item_id))
        result = cursor.fetchone()
        assert result["is_found"] == 0
        
        cursor.execute("""
            SELECT is_completed FROM shopping_list_items WHERE item_id = %s
        """, (item_id,))
        result = cursor.fetchone()
        assert result["is_completed"] == 0
    
    def test_mark_item_found_missing_parameters(self, client, logged_in_user):
        """Test marking item with missing required parameters."""
        response = client.post("/api/shopping-trip/mark-found", json={
            "cart_id": 1
            # Missing list_item_id
        })
        assert response.status_code == 400
        
        data = response.get_json()
        assert "list_item_id and cart_id are required" in data["error"]
    
    def test_mark_item_found_cart_not_found(self, client, logged_in_user):
        """Test marking item for non-existent cart."""
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": 1,
            "cart_id": 99999,
            "is_found": True
        })
        assert response.status_code == 404
        
        data = response.get_json()
        assert "Shopping cart not found" in data["error"]
    
    def test_mark_item_found_mapping_not_found(self, client, logged_in_user, test_db):
        """Test marking item with non-existent mapping."""
        cursor = test_db.cursor()
        
        # Create cart but no mapping
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": 99999,
            "cart_id": cart_id,
            "is_found": True
        })
        assert response.status_code == 404
        
        data = response.get_json()
        assert "Shopping list item mapping not found" in data["error"]
    
    def test_mark_item_found_not_authenticated(self, client):
        """Test marking item when not authenticated."""
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": 1,
            "cart_id": 1,
            "is_found": True
        })
        assert response.status_code == 401
        
        data = response.get_json()
        assert "Not authenticated" in data["error"]


@pytest.mark.api
@pytest.mark.shopping
class TestLinkCartItem:
    """Test linking cart items to shopping list items."""
    
    def test_link_cart_item_success(self, client, logged_in_user, test_db):
        """Test successfully linking a cart item to shopping list item."""
        cursor = test_db.cursor()
        
        # Create shopping list and cart
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Link Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity)
            VALUES (%s, %s, %s)
        """, (list_id, "pasta", 2))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO cart_item (cart_ID, item_name, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (cart_id, "penne pasta", 2, 1.99))
        cart_item_id = cursor.lastrowid
        
        # Create mapping
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
            VALUES (%s, %s, %s)
        """, (cart_id, item_id, False))
        
        response = client.post("/api/shopping-trip/link-cart-item", json={
            "list_item_id": item_id,
            "cart_item_id": cart_item_id,
            "cart_id": cart_id
        })
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["success"] is True
        
        # Verify mapping was updated
        cursor.execute("""
            SELECT cart_item_id, is_found FROM shopping_list_cart_mapping 
            WHERE cart_id = %s AND list_item_id = %s
        """, (cart_id, item_id))
        result = cursor.fetchone()
        assert result["cart_item_id"] == cart_item_id
        assert result["is_found"] == 1
        
        # Verify original list item was marked completed
        cursor.execute("""
            SELECT is_completed FROM shopping_list_items WHERE item_id = %s
        """, (item_id,))
        result = cursor.fetchone()
        assert result["is_completed"] == 1
    
    def test_link_cart_item_missing_parameters(self, client, logged_in_user):
        """Test linking with missing required parameters."""
        response = client.post("/api/shopping-trip/link-cart-item", json={
            "list_item_id": 1,
            "cart_id": 1
            # Missing cart_item_id
        })
        assert response.status_code == 400
        
        data = response.get_json()
        assert "list_item_id, cart_item_id, and cart_id are required" in data["error"]
    
    def test_link_cart_item_cart_not_found(self, client, logged_in_user):
        """Test linking item for non-existent cart."""
        response = client.post("/api/shopping-trip/link-cart-item", json={
            "list_item_id": 1,
            "cart_item_id": 1,
            "cart_id": 99999
        })
        assert response.status_code == 404
        
        data = response.get_json()
        assert "Shopping cart not found" in data["error"]
    
    def test_link_cart_item_mapping_not_found(self, client, logged_in_user, test_db):
        """Test linking with non-existent mapping."""
        cursor = test_db.cursor()
        
        # Create cart but no mapping
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        response = client.post("/api/shopping-trip/link-cart-item", json={
            "list_item_id": 99999,
            "cart_item_id": 1,
            "cart_id": cart_id
        })
        assert response.status_code == 404
        
        data = response.get_json()
        assert "Shopping list item mapping not found" in data["error"]
    
    def test_link_cart_item_not_authenticated(self, client):
        """Test linking cart item when not authenticated."""
        response = client.post("/api/shopping-trip/link-cart-item", json={
            "list_item_id": 1,
            "cart_item_id": 1,
            "cart_id": 1
        })
        assert response.status_code == 401
        
        data = response.get_json()
        assert "Not authenticated" in data["error"]


@pytest.mark.api
@pytest.mark.shopping
class TestGetAvailableLists:
    """Test getting available shopping lists for the user."""
    
    def test_get_available_lists_success(self, client, logged_in_user, test_db):
        """Test successfully getting available shopping lists."""
        cursor = test_db.cursor()
        
        # Create shopping lists
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, description, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s), (%s, %s, %s, %s, %s, %s)
        """, (logged_in_user, "Grocery List", "Weekly groceries", True, "2024-01-15 10:00:00", "2024-01-15 11:00:00",
              logged_in_user, "Party Supplies", "Birthday party", True, "2024-01-14 09:00:00", "2024-01-14 10:00:00"))
        
        list_ids = []
        cursor.execute("SELECT list_id FROM shopping_lists WHERE user_id = %s ORDER BY created_at DESC", (logged_in_user,))
        list_ids = [row["list_id"] for row in cursor.fetchall()]
        
        # Add items to lists
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, is_completed)
            VALUES (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s)
        """, (list_ids[0], "milk", 1, False,
              list_ids[0], "bread", 1, True,
              list_ids[1], "balloons", 10, False))
        
        response = client.get("/api/shopping-trip/available-lists")
        assert response.status_code == 200
        
        data = response.get_json()
        assert "lists" in data
        assert len(data["lists"]) == 2
        
        # Check lists are ordered by updated_at DESC
        lists = data["lists"]
        assert lists[0]["name"] == "Grocery List"
        assert lists[0]["description"] == "Weekly groceries"
        assert lists[0]["item_count"] == 2
        assert lists[0]["completed_count"] == 1
        
        assert lists[1]["name"] == "Party Supplies"
        assert lists[1]["description"] == "Birthday party"
        assert lists[1]["item_count"] == 1
        assert lists[1]["completed_count"] == 0
    
    def test_get_available_lists_empty(self, client, logged_in_user):
        """Test getting lists when user has no lists."""
        response = client.get("/api/shopping-trip/available-lists")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["lists"] == []
    
    def test_get_available_lists_only_active(self, client, logged_in_user, test_db):
        """Test that only active lists are returned."""
        cursor = test_db.cursor()
        
        # Create active and inactive lists
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s), (%s, %s, %s)
        """, (logged_in_user, "Active List", True,
              logged_in_user, "Inactive List", False))
        
        response = client.get("/api/shopping-trip/available-lists")
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data["lists"]) == 1
        assert data["lists"][0]["name"] == "Active List"
    
    def test_get_available_lists_not_authenticated(self, client):
        """Test getting lists when not authenticated."""
        response = client.get("/api/shopping-trip/available-lists")
        assert response.status_code == 401
        
        data = response.get_json()
        assert "Not authenticated" in data["error"]
    
    def test_get_available_lists_database_error(self, client, logged_in_user):
        """Test handling database errors."""
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/shopping-trip/available-lists")
            assert response.status_code == 500
            
            data = response.get_json()
            assert "Failed to get shopping lists" in data["error"]


@pytest.mark.api
@pytest.mark.shopping
class TestShoppingListIntegrationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_create_cart_session_persistence(self, client, logged_in_user, test_db):
        """Test that cart ID is stored in session."""
        cursor = test_db.cursor()
        
        response = client.post("/api/shopping-trip/create-cart", json={
            "store_name": "Session Test Store"
        })
        assert response.status_code == 200
        
        data = response.get_json()
        cart_id = data["cart_id"]
        
        # Check that cart_ID is in session (simulate checking session)
        with client.session_transaction() as sess:
            assert sess.get("cart_ID") == cart_id
    
    def test_shopping_list_status_with_null_values(self, client, logged_in_user, test_db):
        """Test getting status with NULL values in database."""
        cursor = test_db.cursor()
        
        # Create shopping list with NULL description
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Null Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status, shopping_list_id)
            VALUES (%s, %s, %s, %s)
        """, (logged_in_user, "Store", "active", list_id))
        cart_id = cursor.lastrowid
        
        # Add item with NULL notes
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity, notes, is_completed)
            VALUES (%s, %s, %s, %s, %s)
        """, (list_id, "test item", 1, None, False))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
            VALUES (%s, %s, %s)
        """, (cart_id, item_id, False))
        
        response = client.get(f"/api/shopping-trip/list-status?cart_id={cart_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["has_list"] is True
        assert len(data["items"]) == 1
        
        item = data["items"][0]
        assert item["notes"] is None
        assert item["cart_details"] is None
    
    def test_mapping_creation_failure_resilience(self, client, logged_in_user, test_db):
        """Test resilience when some mappings fail to create."""
        cursor = test_db.cursor()
        
        # Create shopping list with items
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Fail Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity)
            VALUES (%s, %s, %s), (%s, %s, %s)
        """, (list_id, "item1", 1, list_id, "item2", 2))
        
        # Mock to make one mapping creation fail
        original_get_db = None
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            
            call_count = 0
            def execute_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                # Let most calls succeed, but make one mapping insertion fail
                if call_count == 10:  # Approximate position of mapping creation
                    raise Exception("Mapping creation failed")
                return None
                
            mock_cursor.execute.side_effect = execute_side_effect
            mock_cursor.fetchone.side_effect = [
                None,  # existing cart check
                {"list_id": list_id, "list_name": "Fail Test List"},  # shopping list verification
            ]
            mock_cursor.fetchall.return_value = [
                {"item_id": 1, "item_name": "item1", "quantity": 1, "notes": None, "is_completed": False},
                {"item_id": 2, "item_name": "item2", "quantity": 2, "notes": None, "is_completed": False}
            ]
            mock_cursor.lastrowid = 456
            mock_db.cursor.return_value = mock_cursor
            mock_db.commit = MagicMock()
            mock_get_db.return_value = mock_db
            
            response = client.post("/api/shopping-trip/create-cart", json={
                "store_name": "Resilience Store",
                "import_list_id": list_id
            })
            
            # Should still succeed even if some mappings fail
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
    
    def test_cart_item_price_conversion(self, client, logged_in_user, test_db):
        """Test that cart item prices are properly converted to float."""
        cursor = test_db.cursor()
        
        # Create data with decimal price
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Price Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status, shopping_list_id)
            VALUES (%s, %s, %s, %s)
        """, (logged_in_user, "Store", "active", list_id))
        cart_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity)
            VALUES (%s, %s, %s)
        """, (list_id, "expensive item", 1))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO cart_item (cart_ID, item_name, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (cart_id, "expensive item", 1, 19.99))
        cart_item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found, cart_item_id)
            VALUES (%s, %s, %s, %s)
        """, (cart_id, item_id, True, cart_item_id))
        
        response = client.get(f"/api/shopping-trip/list-status?cart_id={cart_id}")
        assert response.status_code == 200
        
        data = response.get_json()
        item = data["items"][0]
        
        # Price should be properly converted to float
        assert isinstance(item["cart_details"]["price"], float)
        assert item["cart_details"]["price"] == 19.99
    
    def test_mark_found_default_value(self, client, logged_in_user, test_db):
        """Test that is_found defaults to True when not provided."""
        cursor = test_db.cursor()
        
        # Setup data
        cursor.execute("""
            INSERT INTO shopping_lists (user_id, list_name, is_active)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Default Test List", True))
        list_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_items (list_id, item_name, quantity)
            VALUES (%s, %s, %s)
        """, (list_id, "default item", 1))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_cart (user_ID, store_name, status)
            VALUES (%s, %s, %s)
        """, (logged_in_user, "Store", "active"))
        cart_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO shopping_list_cart_mapping (cart_id, list_item_id, is_found)
            VALUES (%s, %s, %s)
        """, (cart_id, item_id, False))
        
        # Don't provide is_found parameter
        response = client.post("/api/shopping-trip/mark-found", json={
            "list_item_id": item_id,
            "cart_id": cart_id
        })
        assert response.status_code == 200
        
        # Should default to True
        cursor.execute("""
            SELECT is_found FROM shopping_list_cart_mapping 
            WHERE cart_id = %s AND list_item_id = %s
        """, (cart_id, item_id))
        result = cursor.fetchone()
        assert result["is_found"] == 1
    
    def test_database_cursor_cleanup_on_errors(self, client, logged_in_user):
        """Test that database cursors are properly closed on errors."""
        with patch('src.backend.apis.shopping_list_integration.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_db.cursor.return_value = mock_cursor
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/shopping-trip/available-lists")
            assert response.status_code == 500
            
            # Verify cursor.close() was called
            mock_cursor.close.assert_called_once()