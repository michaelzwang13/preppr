"""
Comprehensive tests for views/auth.py.
Tests authentication views including login, registration, 
password hashing, cart restoration, and error handling.
"""

import pytest
import json
import re
from unittest.mock import patch, MagicMock
from src.database import get_db
from src.auth_utils import AuthUtils


@pytest.mark.auth
@pytest.mark.views
@pytest.mark.unit
class TestAuthViews:
    """Test authentication view endpoints."""
    
    def test_login_get_request(self, client):
        """Test login page renders for GET request."""
        response = client.get('/login')
        assert response.status_code == 200
    
    def test_login_missing_credentials(self, client):
        """Test login with missing username or password."""
        # Missing username
        response = client.post('/login', data={
            'user_ID': '',
            'password': 'testpass'
        })
        assert response.status_code == 200
        assert b'Username and password are required' in response.data
        
        # Missing password
        response = client.post('/login', data={
            'user_ID': 'testuser',
            'password': ''
        })
        assert response.status_code == 200
        assert b'Username and password are required' in response.data
        
        # Missing both
        response = client.post('/login', data={
            'user_ID': '',
            'password': ''
        })
        assert response.status_code == 200
        assert b'Username and password are required' in response.data
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent username."""
        response = client.post('/login', data={
            'user_ID': 'nonexistent_user',
            'password': 'testpass'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_login_wrong_password(self, client, auth):
        """Test login with wrong password."""
        # Register user first
        auth.register(user_id='test_user', password='correct_password')
        
        # Try wrong password
        response = client.post('/login', data={
            'user_ID': 'test_user',
            'password': 'wrong_password'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_login_success(self, client, auth):
        """Test successful login."""
        # Register user first
        auth.register(user_id='test_user', password='testpass123')
        
        # Login with correct credentials
        response = client.post('/login', data={
            'user_ID': 'test_user',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        assert '/home' in response.location
        
        # Check that user is in session
        with client.session_transaction() as sess:
            assert sess['user_ID'] == 'test_user'
    
    def test_login_with_whitespace(self, client, auth):
        """Test login handles whitespace in username."""
        # Register user
        auth.register(user_id='test_user', password='testpass123')
        
        # Login with whitespace around username
        response = client.post('/login', data={
            'user_ID': '  test_user  ',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        assert '/home' in response.location
    
    @patch('src.backend.views.auth.get_db')
    def test_login_database_error(self, mock_get_db, client):
        """Test login handles database errors gracefully."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        response = client.post('/login', data={
            'user_ID': 'testuser',
            'password': 'testpass'
        })
        assert response.status_code == 200
        assert b'Login failed. Please try again.' in response.data


@pytest.mark.auth
@pytest.mark.views
@pytest.mark.unit
class TestRegistrationViews:
    """Test user registration functionality."""
    
    def test_register_get_request(self, client):
        """Test registration page renders for GET request."""
        response = client.get('/register')
        assert response.status_code == 200
    
    def test_register_missing_required_fields(self, client):
        """Test registration with missing required fields."""
        # Missing email
        response = client.post('/register', data={
            'user_ID': 'testuser',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': ''
        })
        assert response.status_code == 200
        assert b'Email, username, and password are required' in response.data
        
        # Missing username
        response = client.post('/register', data={
            'user_ID': '',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'Email, username, and password are required' in response.data
        
        # Missing password
        response = client.post('/register', data={
            'user_ID': 'testuser',
            'password': '',
            'confirmPassword': '',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'Email, username, and password are required' in response.data
    
    def test_register_invalid_email_format(self, client):
        """Test registration with invalid email format."""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'test@',
            'test.example.com',
            'test@.com',
            'test@example.',
            'test@example..com'
        ]
        
        for email in invalid_emails:
            response = client.post('/register', data={
                'user_ID': 'testuser',
                'password': 'testpass123',
                'confirmPassword': 'testpass123',
                'email_address': email
            })
            assert response.status_code == 200
            assert b'Please enter a valid email address' in response.data
    
    def test_register_username_too_short(self, client):
        """Test registration with username too short."""
        response = client.post('/register', data={
            'user_ID': 'ab',  # Only 2 characters
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'Username must be at least 3 characters long' in response.data
    
    def test_register_password_too_short(self, client):
        """Test registration with password too short."""
        response = client.post('/register', data={
            'user_ID': 'testuser',
            'password': '12345',  # Only 5 characters
            'confirmPassword': '12345',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'Password must be at least 6 characters long' in response.data
    
    def test_register_password_mismatch(self, client):
        """Test registration with password confirmation mismatch."""
        response = client.post('/register', data={
            'user_ID': 'testuser',
            'password': 'testpass123',
            'confirmPassword': 'different_password',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'Passwords do not match' in response.data
    
    def test_register_duplicate_username(self, client, auth):
        """Test registration with existing username."""
        # Register first user
        auth.register(user_id='testuser', email='first@example.com')
        
        # Try to register with same username
        response = client.post('/register', data={
            'user_ID': 'testuser',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'second@example.com'
        })
        assert response.status_code == 200
        assert b'This username already exists' in response.data
    
    def test_register_duplicate_email(self, client, auth):
        """Test registration with existing email."""
        # Register first user
        auth.register(user_id='firstuser', email='test@example.com')
        
        # Try to register with same email
        response = client.post('/register', data={
            'user_ID': 'seconduser',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'test@example.com'
        })
        assert response.status_code == 200
        assert b'This email address is already registered' in response.data
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post('/register', data={
            'user_ID': 'newuser',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'newuser@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        })
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Verify user was created in database
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM user_account WHERE user_ID = %s", ('newuser',))
            user = cursor.fetchone()
            assert user is not None
            assert user['email'] == 'newuser@example.com'
            assert user['first_name'] == 'Test'
            assert user['last_name'] == 'User'
            cursor.close()
    
    def test_register_success_without_optional_fields(self, client):
        """Test successful registration without first/last name."""
        response = client.post('/register', data={
            'user_ID': 'minimal_user',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'minimal@example.com'
        })
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Verify user was created
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM user_account WHERE user_ID = %s", ('minimal_user',))
            user = cursor.fetchone()
            assert user is not None
            assert user['email'] == 'minimal@example.com'
            cursor.close()
    
    def test_register_handles_whitespace(self, client):
        """Test registration handles whitespace in input fields."""
        response = client.post('/register', data={
            'user_ID': '  spaceuser  ',
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': '  space@example.com  ',
            'first_name': '  Test  ',
            'last_name': '  User  '
        })
        assert response.status_code == 302
        
        # Verify user was created with trimmed values
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM user_account WHERE user_ID = %s", ('spaceuser',))
            user = cursor.fetchone()
            assert user is not None
            assert user['email'] == 'space@example.com'
            assert user['first_name'] == 'Test'
            assert user['last_name'] == 'User'
            cursor.close()


@pytest.mark.auth
@pytest.mark.views
@pytest.mark.unit
class TestPasswordUtilities:
    """Test password hashing and verification utilities."""
    
    def test_hash_password_bcrypt(self, app):
        """Test password hashing function."""
        from src.backend.views.auth import hash_password_bcrypt
        
        with app.app_context():
            password = "test_password_123"
            hashed = hash_password_bcrypt(password)
            
            # Verify hash is different from original password
            assert hashed != password
            # Verify hash starts with bcrypt identifier
            assert hashed.startswith('$2b$')
            # Verify hash is consistent length
            assert len(hashed) == 60
    
    def test_verify_password_bcrypt(self, app):
        """Test password verification function."""
        from src.backend.views.auth import hash_password_bcrypt, verify_password_bcrypt
        
        with app.app_context():
            password = "test_password_123"
            hashed = hash_password_bcrypt(password)
            
            # Verify correct password
            assert verify_password_bcrypt(password, hashed) == True
            
            # Verify wrong password
            assert verify_password_bcrypt("wrong_password", hashed) == False
    
    def test_password_functions_use_auth_utils(self, app):
        """Test that password functions delegate to AuthUtils."""
        with patch('src.backend.views.auth.AuthUtils') as mock_auth_utils:
            from src.backend.views.auth import hash_password_bcrypt, verify_password_bcrypt
            
            mock_auth_utils.hash_password.return_value = 'hashed_password'
            mock_auth_utils.verify_password.return_value = True
            
            with app.app_context():
                # Test hash function delegation
                result = hash_password_bcrypt('test_password')
                mock_auth_utils.hash_password.assert_called_once_with('test_password')
                assert result == 'hashed_password'
                
                # Test verify function delegation
                result = verify_password_bcrypt('test_password', 'hashed_password')
                mock_auth_utils.verify_password.assert_called_once_with('test_password', 'hashed_password')
                assert result == True


@pytest.mark.auth
@pytest.mark.views
@pytest.mark.integration
class TestCartRestoration:
    """Test shopping cart restoration after login."""
    
    def test_restore_active_cart_success(self, client, auth):
        """Test successful cart restoration after login."""
        # Register the user properly using the auth fixture
        auth.register(user_id='cart_user', email='cart@test.com', password='testpass123')
        
        # Create active cart for user
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, NOW())
            """, ('cart_user', 'Test Store', 'active'))
            cart_id = cursor.lastrowid
            cursor.close()
        
        # Login user
        response = client.post('/login', data={
            'user_ID': 'cart_user',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        
        # Verify cart was restored to session
        with client.session_transaction() as sess:
            assert sess.get('cart_ID') == cart_id
    
    def test_restore_active_cart_no_cart(self, client, auth):
        """Test cart restoration when user has no active cart."""
        # Register the user properly using the auth fixture
        auth.register(user_id='no_cart_user', email='nocart@test.com', password='testpass123')
        
        # Login user
        response = client.post('/login', data={
            'user_ID': 'no_cart_user',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        
        # Verify no cart in session
        with client.session_transaction() as sess:
            assert 'cart_ID' not in sess
    
    def test_restore_active_cart_multiple_carts(self, client, auth):
        """Test cart restoration selects most recent active cart."""
        # Register the user properly using the auth fixture
        auth.register(user_id='multi_cart_user', email='multi@test.com', password='testpass123')
        
        # Create multiple carts in database
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create multiple active carts (older first)
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, %s)
            """, ('multi_cart_user', 'Old Store', 'active', '2024-01-01 10:00:00'))
            old_cart_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, %s)
            """, ('multi_cart_user', 'New Store', 'active', '2024-01-02 10:00:00'))
            new_cart_id = cursor.lastrowid
            
            cursor.close()
        
        # Login user
        response = client.post('/login', data={
            'user_ID': 'multi_cart_user',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        
        # Verify most recent cart was restored
        with client.session_transaction() as sess:
            assert sess.get('cart_ID') == new_cart_id
    
    def test_restore_active_cart_ignores_purchased_carts(self, client, auth):
        """Test cart restoration ignores purchased carts."""
        # Register the user properly using the auth fixture
        auth.register(user_id='purchased_cart_user', email='purchased@test.com', password='testpass123')
        
        # Create purchased cart in database
        with client.application.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Create purchased cart (should be ignored)
            cursor.execute("""
                INSERT INTO shopping_cart (user_ID, store_name, status, created_at)
                VALUES (%s, %s, %s, NOW())
            """, ('purchased_cart_user', 'Purchased Store', 'purchased'))
            
            cursor.close()
        
        # Login user
        response = client.post('/login', data={
            'user_ID': 'purchased_cart_user',
            'password': 'testpass123'
        })
        assert response.status_code == 302
        
        # Verify no cart in session
        with client.session_transaction() as sess:
            assert 'cart_ID' not in sess
    
    def test_restore_active_cart_database_error(self, client, auth):
        """Test cart restoration handles database errors gracefully."""
        # Register the user properly using the auth fixture
        auth.register(user_id='error_user', email='error@test.com', password='testpass123')
        
        # Mock the restore_active_cart function to raise an exception
        with patch('src.backend.views.auth.restore_active_cart') as mock_restore:
            mock_restore.side_effect = Exception("Cart restoration error")
            
            # Login should still succeed even if cart restoration fails
            response = client.post('/login', data={
                'user_ID': 'error_user',
                'password': 'testpass123'
            })
            assert response.status_code == 302
            assert '/home' in response.location
            
            # Verify restore function was called
            mock_restore.assert_called_once_with('error_user')


@pytest.mark.auth
@pytest.mark.views
@pytest.mark.unit
class TestAuthenticationFlow:
    """Test complete authentication flow scenarios."""
    
    def test_full_registration_login_flow(self, client):
        """Test complete flow from registration to login."""
        # Step 1: Register new user
        response = client.post('/register', data={
            'user_ID': 'flow_user',
            'password': 'secure_password_123',
            'confirmPassword': 'secure_password_123',
            'email_address': 'flow@example.com',
            'first_name': 'Flow',
            'last_name': 'User'
        })
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Step 2: Login with registered credentials
        response = client.post('/login', data={
            'user_ID': 'flow_user',
            'password': 'secure_password_123'
        })
        assert response.status_code == 302
        assert '/home' in response.location
        
        # Step 3: Verify user is logged in
        with client.session_transaction() as sess:
            assert sess['user_ID'] == 'flow_user'
    
    def test_case_sensitive_login(self, client, auth):
        """Test that login is case-sensitive for usernames."""
        # Register with lowercase username
        auth.register(user_id='testuser', password='testpass123')
        
        # Try login with different case
        response = client.post('/login', data={
            'user_ID': 'TestUser',  # Different case
            'password': 'testpass123'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_sql_injection_protection(self, client):
        """Test that authentication is protected against SQL injection."""
        # Attempt SQL injection in username
        response = client.post('/login', data={
            'user_ID': "'; DROP TABLE user_account; --",
            'password': 'testpass123'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
        
        # Attempt SQL injection in registration
        response = client.post('/register', data={
            'user_ID': "'; INSERT INTO user_account VALUES ('hacked'); --",
            'password': 'testpass123',
            'confirmPassword': 'testpass123',
            'email_address': 'hack@example.com'
        })
        # Should either fail validation or handle safely
        assert response.status_code in [200, 302]
    
    def test_password_special_characters(self, client):
        """Test registration and login with special characters in password."""
        special_password = "P@ssw0rd!#$%^&*()"
        
        # Register with special characters
        response = client.post('/register', data={
            'user_ID': 'special_user',
            'password': special_password,
            'confirmPassword': special_password,
            'email_address': 'special@example.com'
        })
        assert response.status_code == 302
        
        # Login with special characters
        response = client.post('/login', data={
            'user_ID': 'special_user',
            'password': special_password
        })
        assert response.status_code == 302
        assert '/home' in response.location