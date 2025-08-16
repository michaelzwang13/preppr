"""
Comprehensive admin and promotional code tests.
Tests promo code validation, redemption, admin functions, and error handling.
"""

import pytest
import json
from datetime import datetime, timedelta
from src.database import get_db
from unittest.mock import patch, MagicMock


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.api
class TestPromoCodeValidationAPI:
    """Test promotional code validation API."""
    
    def test_validate_promo_code_not_authenticated(self, client):
        """Test validating promo code without authentication."""
        response = client.post('/api/promo-codes/validate',
                              data=json.dumps({'code': 'TEST123'}),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'authentication_required'
    
    def test_validate_promo_code_missing_code(self, client, logged_in_user):
        """Test validating promo code with missing code."""
        response = client.post('/api/promo-codes/validate',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'missing_code'
    
    def test_validate_promo_code_empty_code(self, client, logged_in_user):
        """Test validating promo code with empty code."""
        response = client.post('/api/promo-codes/validate',
                              data=json.dumps({'code': '   '}),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'empty_code'
    
    def test_validate_promo_code_invalid(self, client, logged_in_user):
        """Test validating non-existent promo code."""
        # Mock validation function to return invalid
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.return_value = {'valid': False}
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'INVALID123'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['valid'] == False
        assert data['error'] == 'invalid_code'
    
    def test_validate_promo_code_expired(self, client, logged_in_user):
        """Test validating expired promo code."""
        from src.promo_code_utils import PromoCodeExpired
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.side_effect = PromoCodeExpired("Code has expired")
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'EXPIRED123'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'code_expired'
        assert 'expired' in data['message']
    
    def test_validate_promo_code_exhausted(self, client, logged_in_user):
        """Test validating exhausted promo code."""
        from src.promo_code_utils import PromoCodeExhausted
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.side_effect = PromoCodeExhausted("Code fully redeemed")
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'EXHAUSTED123'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'code_exhausted'
    
    def test_validate_promo_code_user_limit_reached(self, client, logged_in_user):
        """Test validating promo code when user limit is reached."""
        from src.promo_code_utils import PromoCodeUserLimitReached
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.side_effect = PromoCodeUserLimitReached("Already used")
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'USEDCODE'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'user_limit_reached'
        assert 'already used' in data['message']
    
    def test_validate_promo_code_not_eligible(self, client, logged_in_user):
        """Test validating promo code when user is not eligible."""
        from src.promo_code_utils import PromoCodeNotEligible
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.side_effect = PromoCodeNotEligible("Account too new")
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'PREMIUM123'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'not_eligible'
        assert 'Account too new' in data['message']
    
    def test_validate_promo_code_rate_limited(self, client, logged_in_user):
        """Test validating promo code when rate limited."""
        from src.promo_code_utils import PromoCodeError
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.side_effect = PromoCodeError("Rate limit exceeded")
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'TESTCODE'}),
                                  content_type='application/json')
        
        assert response.status_code == 429
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'rate_limited'
    
    def test_validate_promo_code_valid_discount(self, client, logged_in_user):
        """Test validating valid discount promo code."""
        mock_code_data = {
            'code': 'DISCOUNT10',
            'code_type': 'percentage',
            'description': '10% off subscription',
            'discount_value': 10,
            'subscription_duration_months': None
        }
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'code_data': mock_code_data
            }
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'DISCOUNT10'}),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['valid'] == True
        assert data['code_details']['type'] == 'percentage'
        assert data['code_details']['discount_value'] == 10
        assert '10% off' in data['preview_message']
    
    def test_validate_promo_code_valid_free_month(self, client, logged_in_user):
        """Test validating valid free month promo code."""
        mock_code_data = {
            'code': 'FREEMONTH',
            'code_type': 'free_month',
            'description': 'Free month of premium',
            'discount_value': None,
            'subscription_duration_months': 1
        }
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'code_data': mock_code_data
            }
            
            response = client.post('/api/promo-codes/validate',
                                  data=json.dumps({'code': 'FREEMONTH'}),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['valid'] == True
        assert data['code_details']['type'] == 'free_month'
        assert '1 month of Premium' in data['preview_message']


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.api
class TestPromoCodeRedemptionAPI:
    """Test promotional code redemption API."""
    
    def test_redeem_promo_code_not_authenticated(self, client):
        """Test redeeming promo code without authentication."""
        response = client.post('/api/promo-codes/redeem',
                              data=json.dumps({'code': 'TEST123'}),
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'authentication_required'
    
    def test_redeem_promo_code_missing_code(self, client, logged_in_user):
        """Test redeeming promo code with missing code."""
        response = client.post('/api/promo-codes/redeem',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'missing_code'
    
    def test_redeem_promo_code_successful_discount(self, client, logged_in_user):
        """Test successfully redeeming discount promo code."""
        mock_redemption_result = {
            'code_type': 'percentage',
            'message': 'Successfully applied 10% discount!',
            'benefits_applied': {
                'discount_percentage': 10,
                'savings_amount': 2.50
            }
        }
        
        with patch('src.backend.apis.promo_codes.redeem_promotional_code') as mock_redeem:
            mock_redeem.return_value = mock_redemption_result
            
            response = client.post('/api/promo-codes/redeem',
                                  data=json.dumps({'code': 'DISCOUNT10'}),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['redeemed'] == True
        assert data['code_type'] == 'percentage'
        assert 'discount' in data['message']
        assert 'discount_percentage' in data['benefits_applied']
    
    def test_redeem_promo_code_successful_upgrade(self, client, logged_in_user):
        """Test successfully redeeming upgrade promo code."""
        mock_redemption_result = {
            'code_type': 'free_month',
            'message': 'Premium access granted for 1 month!',
            'benefits_applied': {
                'subscription_tier': 'premium',
                'duration_months': 1,
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
            }
        }
        
        with patch('src.backend.apis.promo_codes.redeem_promotional_code') as mock_redeem:
            mock_redeem.return_value = mock_redemption_result
            
            response = client.post('/api/promo-codes/redeem',
                                  data=json.dumps({'code': 'FREEMONTH'}),
                                  content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['redeemed'] == True
        assert data['code_type'] == 'free_month'
        assert data['redirect_to'] == '/settings'
        assert 'Premium access' in data['message']
    
    def test_redeem_promo_code_already_used(self, client, logged_in_user):
        """Test redeeming promo code that's already been used."""
        from src.promo_code_utils import PromoCodeUserLimitReached
        
        with patch('src.backend.apis.promo_codes.redeem_promotional_code') as mock_redeem:
            mock_redeem.side_effect = PromoCodeUserLimitReached("Already used")
            
            response = client.post('/api/promo-codes/redeem',
                                  data=json.dumps({'code': 'USEDCODE'}),
                                  content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['redeemed'] == False
        assert 'userlimitreached' in data['error']
    
    def test_redeem_promo_code_system_error(self, client, logged_in_user):
        """Test redeeming promo code with system error."""
        with patch('src.backend.apis.promo_codes.redeem_promotional_code') as mock_redeem:
            mock_redeem.side_effect = Exception("Database error")
            
            response = client.post('/api/promo-codes/redeem',
                                  data=json.dumps({'code': 'TESTCODE'}),
                                  content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'system_error'


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.api
class TestPromoCodeHistoryAPI:
    """Test promotional code redemption history API."""
    
    def test_get_redemption_history_not_authenticated(self, client):
        """Test getting redemption history without authentication."""
        response = client.get('/api/promo-codes/history')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error'] == 'authentication_required'
    
    def test_get_redemption_history_empty(self, client, logged_in_user):
        """Test getting redemption history when user has no history."""
        with patch('src.backend.apis.promo_codes.get_user_redemption_history') as mock_history:
            mock_history.return_value = []
            
            response = client.get('/api/promo-codes/history')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['history'] == []
        assert data['total_records'] == 0
    
    def test_get_redemption_history_with_data(self, client, logged_in_user):
        """Test getting redemption history with existing data."""
        mock_history = [
            {
                'redeemed_at': datetime.now() - timedelta(days=5),
                'code': 'DISCOUNT10',
                'code_type': 'percentage',
                'description': '10% off subscription',
                'redemption_result': 'success',
                'applied_discount': 2.50,
                'subscription_granted_until': None,
                'notes': 'Applied to monthly subscription'
            },
            {
                'redeemed_at': datetime.now() - timedelta(days=30),
                'code': 'FREEMONTH',
                'code_type': 'free_month',
                'description': 'Free month premium',
                'redemption_result': 'success',
                'applied_discount': None,
                'subscription_granted_until': datetime.now() + timedelta(days=365),
                'notes': 'Premium upgrade'
            }
        ]
        
        with patch('src.backend.apis.promo_codes.get_user_redemption_history') as mock_get_history:
            mock_get_history.return_value = mock_history
            
            response = client.get('/api/promo-codes/history')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['history']) == 2
        assert data['total_records'] == 2
        
        # Check first record
        first_record = data['history'][0]
        assert first_record['code'] == 'DISCOUNT10'
        assert first_record['code_type'] == 'percentage'
        assert first_record['status'] == 'success'
        assert first_record['discount_applied'] == 2.50
    
    def test_get_redemption_history_with_limit(self, client, logged_in_user):
        """Test getting redemption history with limit parameter."""
        with patch('src.backend.apis.promo_codes.get_user_redemption_history') as mock_history:
            mock_history.return_value = []
            
            response = client.get('/api/promo-codes/history?limit=5')
            
            # Verify limit was passed correctly
            mock_history.assert_called_with(logged_in_user, 5)
        
        assert response.status_code == 200
    
    def test_get_redemption_history_limit_capped(self, client, logged_in_user):
        """Test that redemption history limit is capped at 50."""
        with patch('src.backend.apis.promo_codes.get_user_redemption_history') as mock_history:
            mock_history.return_value = []
            
            response = client.get('/api/promo-codes/history?limit=100')
            
            # Verify limit was capped at 50
            mock_history.assert_called_with(logged_in_user, 50)
        
        assert response.status_code == 200


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.api
class TestPromoCodeAvailabilityAPI:
    """Test promotional code availability check API."""
    
    def test_check_code_availability_not_found(self, client, app):
        """Test checking availability of non-existent code."""
        with app.app_context():
            response = client.get('/api/promo-codes/check-availability/NONEXISTENT')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['exists'] == False
        assert data['available'] == False
        assert 'not found' in data['message']
    
    def test_check_code_availability_exists_active(self, client, app):
        """Test checking availability of active code."""
        # Create test promo code
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            # Clean up any existing test data first
            cursor.execute('DELETE FROM promotional_codes WHERE code = %s', ('TESTACTIVE',))
            cursor.execute('''
                INSERT INTO promotional_codes 
                (code, code_type, description, discount_value, max_uses, current_uses, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', ('TESTACTIVE', 'percentage', 'Test active code', 25.0, 100, 5, True, 'test_admin'))
            # db.commit()
            cursor.close()
        
        response = client.get('/api/promo-codes/check-availability/TESTACTIVE')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['exists'] == True
        assert data['available'] == True
        assert data['code_type'] == 'percentage'
        assert data['description'] == 'Test active code'
        assert 'available' in data['message']
    
    def test_check_code_availability_inactive(self, client, app):
        """Test checking availability of inactive code."""
        # Create inactive promo code
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO promotional_codes 
                (code, code_type, description, discount_value, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('TESTINACTIVE', 'percentage', 'Test inactive code', 15.0, False, 'test_admin'))
            # db.commit()
            cursor.close()
        
        response = client.get('/api/promo-codes/check-availability/TESTINACTIVE')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['exists'] == True
        assert data['available'] == False
        assert 'no longer active' in data['message']
    
    def test_check_code_availability_expired(self, client, app):
        """Test checking availability of expired code."""
        # Create expired promo code
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            past_date = datetime.now() - timedelta(days=1)
            cursor.execute('''
                INSERT INTO promotional_codes 
                (code, code_type, description, discount_value, expires_at, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', ('TESTEXPIRED', 'percentage', 'Test expired code', 20.0, past_date, True, 'test_admin'))
            # db.commit()
            cursor.close()
        
        response = client.get('/api/promo-codes/check-availability/TESTEXPIRED')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['exists'] == True
        assert data['available'] == False
        assert 'expired' in data['message']
    
    def test_check_code_availability_exhausted(self, client, app):
        """Test checking availability of exhausted code."""
        # Create exhausted promo code
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO promotional_codes 
                (code, code_type, description, discount_value, max_uses, current_uses, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', ('TESTEXHAUSTED', 'percentage', 'Test exhausted code', 10.0, 10, 10, True, 'test_admin'))
            # db.commit()
            cursor.close()
        
        response = client.get('/api/promo-codes/check-availability/TESTEXHAUSTED')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['exists'] == True
        assert data['available'] == False
        assert 'fully redeemed' in data['message']


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.jwt
class TestPromoCodeJWTEndpoints:
    """Test JWT-protected promotional code endpoints."""
    
    def test_jwt_validate_promo_code_no_token(self, client):
        """Test JWT validate endpoint without token."""
        response = client.post('/api/promo-codes/jwt/validate',
                              data=json.dumps({'code': 'TEST123'}),
                              content_type='application/json')
        # Should return 401 due to missing JWT token
        assert response.status_code == 401
    
    def test_jwt_redeem_promo_code_no_token(self, client):
        """Test JWT redeem endpoint without token."""
        response = client.post('/api/promo-codes/jwt/redeem',
                              data=json.dumps({'code': 'TEST123'}),
                              content_type='application/json')
        # Should return 401 due to missing JWT token
        assert response.status_code == 401
    
    def test_jwt_history_no_token(self, client):
        """Test JWT history endpoint without token."""
        response = client.get('/api/promo-codes/jwt/history')
        # Should return 401 due to missing JWT token
        assert response.status_code == 401
    
    @patch('src.auth_utils.jwt_required')
    def test_jwt_validate_with_mocked_auth(self, mock_jwt, client):
        """Test JWT validate endpoint with mocked authentication."""
        # Mock JWT authentication to set g.current_user_id
        def mock_auth_decorator(f):
            def wrapper(*args, **kwargs):
                from flask import g
                g.current_user_id = 'jwt_test_user'
                return f(*args, **kwargs)
            return wrapper
        
        mock_jwt.return_value = mock_auth_decorator
        
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.return_value = {'valid': False}
            
            response = client.post('/api/promo-codes/jwt/validate',
                                  data=json.dumps({'code': 'TEST123'}),
                                  content_type='application/json')
        
        assert response.status_code == 400  # Invalid code
        data = json.loads(response.data)
        assert data['success'] == False


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.integration
class TestPromoCodeDatabaseIntegration:
    """Test promotional code database integration."""
    
    def test_promotional_codes_table_schema(self, app):
        """Test promotional codes table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE promotional_codes")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'code_id', 'code', 'code_type', 'discount_value', 'subscription_duration_months',
                'max_uses', 'current_uses', 'max_uses_per_user', 'expires_at', 'is_active',
                'created_at', 'created_by', 'description', 'minimum_account_age_days',
                'allowed_user_tiers'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"
    
    def test_code_redemptions_table_schema(self, app):
        """Test code redemptions table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE code_redemptions")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'redemption_id', 'code_id', 'user_id', 'redeemed_at', 'redemption_result',
                'failure_reason', 'subscription_granted_until', 'ip_address'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"
    
    def test_promo_code_foreign_key_constraints(self, app, logged_in_user):
        """Test foreign key constraints in promo code tables."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Test code_redemptions foreign key to promotional_codes
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO code_redemptions (code_id, user_id, redemption_result)
                    VALUES (%s, %s, %s)
                ''', (99999, logged_in_user, 'success'))
                # db.commit()
            
            # Test code_redemptions foreign key to user_account
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO code_redemptions (code_id, user_id, redemption_result)
                    VALUES (%s, %s, %s)
                ''', (1, 'nonexistent_user', 'success'))
                # db.commit()
            
            cursor.close()
    
    def test_promo_code_enum_constraints(self, app):
        """Test enum constraints in promotional codes table."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Test invalid code_type
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO promotional_codes (code, code_type, created_by)
                    VALUES (%s, %s, %s)
                ''', ('TESTCODE', 'invalid_type', 'admin'))
                # db.commit()
            
            # Test invalid redemption_result
            cursor.execute('''
                INSERT INTO promotional_codes (code, code_type, created_by)
                VALUES (%s, %s, %s)
            ''', ('TESTCODE2', 'discount', 'admin'))
            code_id = cursor.lastrowid
            # db.commit()
            
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO code_redemptions (code_id, user_id, redemption_result)
                    VALUES (%s, %s, %s)
                ''', (code_id, 'test_user', 'invalid_result'))
                # db.commit()
            
            cursor.close()
    
    def test_promo_code_unique_constraints(self, app):
        """Test unique constraints in promotional codes table."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Insert first code
            cursor.execute('''
                INSERT INTO promotional_codes (code, code_type, created_by)
                VALUES (%s, %s, %s)
            ''', ('UNIQUECODE', 'discount', 'admin'))
            # db.commit()
            
            # Try to insert duplicate code
            with pytest.raises(Exception):
                cursor.execute('''
                    INSERT INTO promotional_codes (code, code_type, created_by)
                    VALUES (%s, %s, %s)
                ''', ('UNIQUECODE', 'discount', 'admin'))
                # db.commit()
            
            cursor.close()


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.unit
class TestPromoCodeUtilities:
    """Test promotional code utility functions."""
    
    def test_promo_code_validation_types(self, app):
        """Test different promo code validation scenarios."""
        with app.app_context():
            # Test with sample promotional codes from conftest
            db = get_db()
            cursor = db.cursor()
            
            # Get sample codes
            cursor.execute('SELECT * FROM promotional_codes WHERE is_active = TRUE')
            codes = cursor.fetchall()
            cursor.close()
            
        assert len(codes) >= 3  # Should have at least the sample codes
        
        # Find specific code types
        code_types = [code['code_type'] for code in codes]
        assert 'free_trial' in code_types
        assert 'discount' in code_types
        assert 'free_month' in code_types
    
    def test_promo_code_error_handling(self):
        """Test promotional code error classes."""
        from src.promo_code_utils import (
            PromoCodeError, PromoCodeExpired, PromoCodeExhausted,
            PromoCodeInvalid, PromoCodeUserLimitReached, PromoCodeNotEligible
        )
        
        # Test error inheritance
        assert issubclass(PromoCodeExpired, PromoCodeError)
        assert issubclass(PromoCodeExhausted, PromoCodeError)
        assert issubclass(PromoCodeInvalid, PromoCodeError)
        assert issubclass(PromoCodeUserLimitReached, PromoCodeError)
        assert issubclass(PromoCodeNotEligible, PromoCodeError)
        
        # Test error instantiation
        expired_error = PromoCodeExpired("Code expired")
        assert str(expired_error) == "Code expired"
        
        invalid_error = PromoCodeInvalid("Invalid code")
        assert str(invalid_error) == "Invalid code"


@pytest.mark.admin
@pytest.mark.promo_codes
@pytest.mark.integration
@pytest.mark.slow
class TestPromoCodePerformance:
    """Test promotional code system performance."""
    
    def test_promo_code_validation_performance(self, client, logged_in_user, app):
        """Test promo code validation performance with large dataset."""
        # Create many promotional codes
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            for i in range(100):
                cursor.execute('''
                    INSERT INTO promotional_codes 
                    (code, code_type, description, created_by, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (f'TESTCODE{i}', 'discount', f'Test code {i}', 'admin', True))
            
            # db.commit()
            cursor.close()
        
        import time
        
        # Test validation performance
        with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
            mock_validate.return_value = {'valid': False}
            
            start_time = time.time()
            
            for i in range(10):
                response = client.post('/api/promo-codes/validate',
                                      data=json.dumps({'code': f'TESTCODE{i}'}),
                                      content_type='application/json')
                assert response.status_code == 400
            
            end_time = time.time()
            avg_response_time = (end_time - start_time) / 10
        
        assert avg_response_time < 0.1  # Average should be under 100ms
    
    def test_concurrent_promo_code_operations(self, client, logged_in_user, app):
        """Test concurrent promotional code operations."""
        # Create test promotional code
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO promotional_codes 
                (code, code_type, description, max_uses, current_uses, created_by, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', ('CONCURRENT', 'discount', 'Concurrent test', 100, 0, 'admin', True))
            # db.commit()
            cursor.close()
        
        import threading
        results = []
        
        def validate_code():
            with patch('src.backend.apis.promo_codes.validate_promotional_code') as mock_validate:
                mock_validate.return_value = {'valid': False}
                response = client.post('/api/promo-codes/validate',
                                      data=json.dumps({'code': 'CONCURRENT'}),
                                      content_type='application/json')
                results.append(response)
        
        # Make concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_code)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should complete successfully
        for response in results:
            assert response.status_code == 400  # Invalid code as mocked
    
    def test_large_redemption_history_retrieval(self, client, logged_in_user):
        """Test retrieving large redemption history."""
        # Mock large history
        large_history = []
        for i in range(50):
            large_history.append({
                'redeemed_at': datetime.now() - timedelta(days=i),
                'code': f'CODE{i}',
                'code_type': 'discount',
                'description': f'Test code {i}',
                'redemption_result': 'success',
                'applied_discount': i * 1.5,
                'subscription_granted_until': None,
                'notes': f'Test redemption {i}'
            })
        
        with patch('src.backend.apis.promo_codes.get_user_redemption_history') as mock_history:
            mock_history.return_value = large_history
            
            import time
            start_time = time.time()
            
            response = client.get('/api/promo-codes/history?limit=50')
            
            end_time = time.time()
            response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        data = json.loads(response.data)
        assert len(data['history']) == 50
        assert data['total_records'] == 50