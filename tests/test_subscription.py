"""
Comprehensive subscription and tier testing.
Tests subscription status, tier-based feature access, limits tracking, and upgrades/downgrades.
"""

import pytest
import json
from datetime import datetime, timedelta
from src.database import get_db
from unittest.mock import patch


@pytest.mark.subscription
@pytest.mark.unit
class TestSubscriptionUtils:
    """Test subscription utility functions."""
    
    def test_get_user_subscription_info_free_user(self, app, logged_in_user):
        """Test subscription info for free user."""
        from src.subscription_utils import get_user_subscription_info
        
        with app.app_context():
            info = get_user_subscription_info(logged_in_user)
        
        assert info['tier'] == 'free'
        assert info['status'] == 'active'
        assert info['unlimited'] == False
        assert info['expires_at'] is None
    
    def test_get_user_subscription_info_premium_user(self, app, premium_user):
        """Test subscription info for premium user."""
        from src.subscription_utils import get_user_subscription_info
        
        with app.app_context():
            info = get_user_subscription_info(premium_user)
        
        assert info['tier'] == 'premium'
        assert info['status'] == 'active'
        assert info['unlimited'] == True
        assert info['expires_at'] is not None
    
    def test_get_user_subscription_info_expired_user(self, app, expired_premium_user):
        """Test subscription info for expired premium user."""
        from src.subscription_utils import get_user_subscription_info
        
        with app.app_context():
            info = get_user_subscription_info(expired_premium_user)
        
        assert info['tier'] == 'premium'  # Still premium tier in DB
        assert info['status'] == 'expired'  # But expired status
        assert info['unlimited'] == False  # No unlimited access due to expiration
        assert info['expires_at'] is not None
    
    def test_get_user_subscription_info_nonexistent_user(self, app):
        """Test subscription info for non-existent user."""
        from src.subscription_utils import get_user_subscription_info
        
        with app.app_context():
            info = get_user_subscription_info('nonexistent_user')
        
        # Should return free tier as default
        assert info['tier'] == 'free'
        assert info['status'] == 'active'
        assert info['unlimited'] == False


@pytest.mark.subscription
@pytest.mark.unit
class TestSubscriptionLimits:
    """Test subscription limits and feature restrictions."""
    
    def test_get_user_limits_status_free_user(self, app, logged_in_user):
        """Test limits status for free user."""
        from src.subscription_utils import get_user_limits_status
        
        with app.app_context():
            status = get_user_limits_status(logged_in_user)
        
        assert status['tier'] == 'free'
        assert status['unlimited'] == False
        assert 'limits' in status
        
        # Check specific free tier limits
        limits = status['limits']
        assert 'meal_plans_active' in limits
        assert 'pantry_items' in limits
        assert 'saved_recipes' in limits
        assert limits['meal_plans_active']['limit'] == 3
        assert limits['pantry_items']['limit'] == 50
        assert limits['saved_recipes']['limit'] == 10
    
    def test_get_user_limits_status_premium_user(self, app, premium_user):
        """Test limits status for premium user."""
        from src.subscription_utils import get_user_limits_status
        
        with app.app_context():
            status = get_user_limits_status(premium_user)
        
        assert status['tier'] == 'premium'
        assert status['unlimited'] == True
        assert 'limits' in status
        
        # Premium users should have empty limits dict (they're unlimited)
        limits = status['limits']
        assert limits == {}  # Premium users don't need limit tracking
    
    def test_check_user_limit_within_bounds_free(self, app, logged_in_user):
        """Test checking limit when user is within bounds."""
        from src.subscription_utils import check_user_limit
        
        with app.app_context():
            result = check_user_limit(logged_in_user, 'saved_recipes', current_count=5)
        
        assert result['allowed'] == True
        assert result['limit'] == 10
        assert result['current'] == 5
        assert result['remaining'] == 5
    
    def test_check_user_limit_at_bounds_free(self, app, logged_in_user):
        """Test checking limit when user is at the limit."""
        from src.subscription_utils import check_user_limit
        
        with app.app_context():
            result = check_user_limit(logged_in_user, 'saved_recipes', current_count=10)
        
        assert result['allowed'] == False
        assert result['limit'] == 10
        assert result['current'] == 10
        assert result['remaining'] == 0
    
    def test_check_user_limit_premium_unlimited(self, app, premium_user):
        """Test checking limit for premium user (should be unlimited)."""
        from src.subscription_utils import check_user_limit
        
        with app.app_context():
            result = check_user_limit(premium_user, 'saved_recipes', current_count=50)
        
        assert result['allowed'] == True
        assert result['limit'] == -1  # Unlimited
        assert result['current'] == 50
        assert result['remaining'] == -1  # Unlimited
    
    def test_increment_user_limit_tracking(self, app, logged_in_user):
        """Test incrementing user limit tracking."""
        from src.subscription_utils import increment_user_limit
        
        with app.app_context():
            # First increment should create the record
            result = increment_user_limit(logged_in_user, 'upc_scans_per_week')
            assert result == True
            
            # Verify record was created
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT current_usage FROM subscription_limits 
                WHERE user_id = %s AND limit_type = %s
            ''', (logged_in_user, 'upc_scans_per_week'))
            record = cursor.fetchone()
            cursor.close()
            
            assert record is not None
            assert record['current_usage'] == 1
    
    def test_reset_user_limits_daily(self, app, logged_in_user):
        """Test resetting daily limits."""
        from src.subscription_utils import increment_user_limit, reset_daily_limits
        
        with app.app_context():
            # Create some usage
            increment_user_limit(logged_in_user, 'shopping_lists_per_day')
            increment_user_limit(logged_in_user, 'shopping_lists_per_day')
            
            # Reset daily limits
            reset_daily_limits(logged_in_user)
            
            # Verify limits were reset
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT current_usage FROM subscription_limits 
                WHERE user_id = %s AND limit_type LIKE '%_per_day'
            ''', (logged_in_user,))
            records = cursor.fetchall()
            cursor.close()
            
            for record in records:
                assert record['current_usage'] == 0


@pytest.mark.subscription
@pytest.mark.integration
class TestSubscriptionFeatureAccess:
    """Test feature access based on subscription tier."""
    
    def test_nutrition_field_access_by_tier(self, app):
        """Test nutrition field access varies by subscription tier."""
        from src.backend.apis.nutrition import get_accessible_nutrition_fields
        
        with app.app_context():
            # Mock different subscription statuses
            with patch('src.subscription_utils.get_user_subscription_info') as mock_sub:
                # Free user
                mock_sub.return_value = {'tier': 'free', 'status': 'active'}
                free_fields = get_accessible_nutrition_fields('test_user')
                
                # Premium user
                mock_sub.return_value = {'tier': 'premium', 'status': 'active'}
                premium_fields = get_accessible_nutrition_fields('test_user')
                
                # Expired premium user
                mock_sub.return_value = {'tier': 'premium', 'status': 'expired'}
                expired_fields = get_accessible_nutrition_fields('test_user')
        
        # Free user should have limited access
        assert free_fields['calories'] == True
        assert free_fields['protein'] == True
        assert free_fields['carbs'] == False
        assert free_fields['fiber'] == False
        assert free_fields['sodium'] == False
        
        # Premium user should have full access
        assert premium_fields['calories'] == True
        assert premium_fields['protein'] == True
        assert premium_fields['carbs'] == True
        assert premium_fields['fiber'] == True
        assert premium_fields['sodium'] == True
        
        # Expired premium should be like free
        assert expired_fields['carbs'] == False
        assert expired_fields['fiber'] == False
        assert expired_fields['sodium'] == False
    
    def test_meal_plan_limits_by_tier(self, client, logged_in_user, premium_user):
        """Test meal plan creation limits by tier."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Free user should be limited to 3 active meal plans
            free_result = check_user_limit(logged_in_user, 'meal_plans_active', current_count=3)
            assert free_result['allowed'] == False
            assert free_result['limit'] == 3
            
            # Premium user should have unlimited meal plans
            premium_result = check_user_limit(premium_user, 'meal_plans_active', current_count=100)
            assert premium_result['allowed'] == True
            assert premium_result['limit'] == -1
    
    def test_pantry_item_limits_by_tier(self, client, logged_in_user, premium_user):
        """Test pantry item limits by tier."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Free user should be limited to 50 pantry items
            free_result = check_user_limit(logged_in_user, 'pantry_items', current_count=50)
            assert free_result['allowed'] == False
            assert free_result['limit'] == 50
            
            # Premium user should have unlimited pantry items
            premium_result = check_user_limit(premium_user, 'pantry_items', current_count=500)
            assert premium_result['allowed'] == True
            assert premium_result['limit'] == -1
    
    def test_upc_scan_limits_by_tier(self, client, logged_in_user, premium_user):
        """Test UPC scan limits by tier."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Free user should be limited in UPC scans
            free_weekly = check_user_limit(logged_in_user, 'upc_scans_per_week', current_count=25)
            assert free_weekly['allowed'] == False
            assert free_weekly['limit'] == 25
            
            free_per_trip = check_user_limit(logged_in_user, 'upc_scans_per_trip', current_count=10)
            assert free_per_trip['allowed'] == False
            assert free_per_trip['limit'] == 10
            
            # Premium user should have unlimited UPC scans
            premium_weekly = check_user_limit(premium_user, 'upc_scans_per_week', current_count=1000)
            assert premium_weekly['allowed'] == True
            assert premium_weekly['limit'] == -1


@pytest.mark.subscription
@pytest.mark.integration
class TestSubscriptionUpgradeDowngrade:
    """Test subscription upgrade and downgrade scenarios."""
    
    def test_upgrade_free_to_premium(self, app, logged_in_user):
        """Test upgrading user from free to premium."""
        user_id = logged_in_user
        
        with app.app_context():
            # Verify user starts as free
            from src.subscription_utils import get_user_subscription_info
            initial_info = get_user_subscription_info(user_id)
            assert initial_info['tier'] == 'free'
            
            # Upgrade to premium
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
            # db.commit()
            cursor.close()
            
            # Verify upgrade
            upgraded_info = get_user_subscription_info(user_id)
            assert upgraded_info['tier'] == 'premium'
            assert upgraded_info['status'] == 'active'
            assert upgraded_info['unlimited'] == True
    
    def test_downgrade_premium_to_free_on_expiry(self, app, premium_user):
        """Test that premium features are restricted when subscription expires."""
        user_id = premium_user
        
        with app.app_context():
            # Verify user starts as premium
            from src.subscription_utils import get_user_subscription_info
            initial_info = get_user_subscription_info(user_id)
            assert initial_info['tier'] == 'premium'
            assert initial_info['unlimited'] == True
            
            # Expire the subscription
            db = get_db()
            cursor = db.cursor()
            past_date = datetime.now() - timedelta(days=1)
            cursor.execute('''
                UPDATE user_account 
                SET subscription_status = 'expired',
                    subscription_end_date = %s
                WHERE user_ID = %s
            ''', (past_date, user_id))
            # db.commit()
            cursor.close()
            
            # Verify downgrade behavior
            expired_info = get_user_subscription_info(user_id)
            assert expired_info['tier'] == 'premium'  # Still premium tier in DB
            assert expired_info['status'] == 'expired'  # But expired
            assert expired_info['unlimited'] == False  # No unlimited access
    
    def test_cancelled_subscription_handling(self, app, premium_user):
        """Test handling of cancelled subscriptions."""
        user_id = premium_user
        
        with app.app_context():
            # Cancel the subscription
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                UPDATE user_account 
                SET subscription_status = 'cancelled'
                WHERE user_ID = %s
            ''', (user_id,))
            # db.commit()
            cursor.close()
            
            # Verify cancelled subscription behavior
            from src.subscription_utils import get_user_subscription_info
            cancelled_info = get_user_subscription_info(user_id)
            assert cancelled_info['status'] == 'cancelled'
            assert cancelled_info['unlimited'] == False


@pytest.mark.subscription
@pytest.mark.api
class TestSubscriptionAPIIntegration:
    """Test how subscription status affects API responses."""
    
    def test_nutrition_api_free_user_premium_field_rejection(self, client, logged_in_user):
        """Test that nutrition API rejects premium fields for free users."""
        goals_data = {
            'daily_calories': 2200,
            'daily_protein': 160,
            'daily_fat': 75,
            'daily_carbs': 250  # Premium field
        }
        
        response = client.post('/api/nutrition/goals',
                              data=json.dumps(goals_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data.get('requires_upgrade') == True
        assert 'Premium subscription required' in data['message']
    
    def test_nutrition_api_premium_user_all_fields_accepted(self, client, premium_user):
        """Test that nutrition API accepts all fields for premium users."""
        goals_data = {
            'daily_calories': 2200,
            'daily_protein': 160,
            'daily_fat': 75,
            'daily_carbs': 250,
            'daily_fiber': 30,
            'daily_sodium': 2000
        }
        
        response = client.post('/api/nutrition/goals',
                              data=json.dumps(goals_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'daily_carbs' in data['goals']
        assert 'daily_fiber' in data['goals']
        assert 'daily_sodium' in data['goals']
    
    def test_nutrition_api_expired_premium_treated_as_free(self, client, expired_premium_user):
        """Test that expired premium users are treated as free for API access."""
        goals_data = {
            'daily_calories': 2200,
            'daily_protein': 160,
            'daily_fat': 75,
            'daily_carbs': 250  # Should be rejected for expired premium
        }
        
        response = client.post('/api/nutrition/goals',
                              data=json.dumps(goals_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == False
        assert data.get('requires_upgrade') == True


@pytest.mark.subscription
@pytest.mark.unit
class TestSubscriptionTierFeatures:
    """Test subscription tier features configuration."""
    
    def test_subscription_tier_features_table_populated(self, app):
        """Test that subscription tier features are properly configured."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT tier, feature_name, limit_value 
                FROM subscription_tier_features 
                ORDER BY tier, feature_name
            ''')
            features = cursor.fetchall()
            cursor.close()
            
            # Convert to dict for easier testing
            feature_map = {}
            for feature in features:
                tier = feature['tier']
                if tier not in feature_map:
                    feature_map[tier] = {}
                feature_map[tier][feature['feature_name']] = feature['limit_value']
            
            # Test free tier limits
            assert 'free' in feature_map
            free_features = feature_map['free']
            assert free_features['meal_plans_active'] == 3
            assert free_features['pantry_items'] == 50
            assert free_features['saved_recipes'] == 10
            assert free_features['upc_scans_per_week'] == 25
            
            # Test premium tier limits (should be unlimited -1)
            assert 'premium' in feature_map
            premium_features = feature_map['premium']
            assert premium_features['meal_plans_active'] == -1
            assert premium_features['pantry_items'] == -1
            assert premium_features['saved_recipes'] == -1
            assert premium_features['upc_scans_per_week'] == -1
    
    def test_subscription_limits_tracking_schema(self, app):
        """Test subscription limits tracking table schema."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DESCRIBE subscription_limits")
            columns = cursor.fetchall()
            cursor.close()
            
            column_names = [col['Field'] for col in columns]
            expected_columns = [
                'limit_id', 'user_id', 'limit_type', 'current_usage', 
                'last_reset_date', 'created_at', 'updated_at'
            ]
            
            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"


@pytest.mark.subscription
@pytest.mark.premium
class TestPremiumFeatureAccess:
    """Test premium-only feature access."""
    
    def test_premium_nutrition_fields_access(self, client, premium_user):
        """Test that premium users can access advanced nutrition fields."""
        # GET request should include premium fields
        response = client.get('/api/nutrition/goals')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        goals = data['goals']
        # Premium fields should be present with default values
        assert 'daily_carbs' in goals
        assert 'daily_fiber' in goals
        assert 'daily_sodium' in goals
    
    def test_premium_unlimited_limits(self, client, premium_user):
        """Test that premium users have unlimited access to features."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Test various limits - all should be unlimited for premium
            features_to_test = [
                'meal_plans_active',
                'pantry_items', 
                'saved_recipes',
                'shopping_lists_per_day',
                'upc_scans_per_week',
                'upc_scans_per_trip'
            ]
            
            for feature in features_to_test:
                result = check_user_limit(premium_user, feature, current_count=1000)
                assert result['allowed'] == True, f"Premium user should have unlimited {feature}"
                assert result['limit'] == -1, f"Premium user limit should be -1 for {feature}"
    
    def test_free_user_feature_restrictions(self, client, logged_in_user):
        """Test that free users are properly restricted."""
        from src.subscription_utils import check_user_limit
        
        with client.application.app_context():
            # Test that free users hit limits
            restricted_features = {
                'meal_plans_active': 3,
                'pantry_items': 50,
                'saved_recipes': 10,
                'shopping_lists_per_day': 2,
                'upc_scans_per_week': 25,
                'upc_scans_per_trip': 10
            }
            
            for feature, limit in restricted_features.items():
                # Test at the limit - should be blocked
                result = check_user_limit(logged_in_user, feature, current_count=limit)
                assert result['allowed'] == False, f"Free user should be blocked at {feature} limit"
                assert result['limit'] == limit, f"Free user limit should be {limit} for {feature}"
                
                # Test below the limit - should be allowed
                result = check_user_limit(logged_in_user, feature, current_count=limit-1)
                assert result['allowed'] == True, f"Free user should be allowed below {feature} limit"


@pytest.mark.subscription
@pytest.mark.integration
@pytest.mark.slow
class TestSubscriptionLimitEnforcement:
    """Test subscription limit enforcement across different scenarios."""
    
    def test_limit_enforcement_with_real_usage(self, app, logged_in_user):
        """Test limit enforcement with actual usage increments."""
        from src.subscription_utils import increment_user_limit, check_user_limit
        
        with app.app_context():
            user_id = logged_in_user
            limit_type = 'shopping_lists_per_day'
            
            # Free user limit is 2 per day
            # Increment usage to limit
            assert increment_user_limit(user_id, limit_type) == True  # Usage = 1
            assert increment_user_limit(user_id, limit_type) == True  # Usage = 2
            
            # Check that we're at the limit
            result = check_user_limit(user_id, limit_type, auto_count=True)
            assert result['allowed'] == False
            assert result['current'] == 2
            assert result['limit'] == 2
            
            # Try to increment beyond limit
            assert increment_user_limit(user_id, limit_type) == False  # Should be blocked
    
    def test_limit_reset_functionality(self, app, logged_in_user):
        """Test that limits reset properly."""
        from src.subscription_utils import increment_user_limit, reset_daily_limits
        
        with app.app_context():
            user_id = logged_in_user
            limit_type = 'shopping_lists_per_day'
            
            # Use up the daily limit
            increment_user_limit(user_id, limit_type)
            increment_user_limit(user_id, limit_type)
            
            # Reset limits
            reset_daily_limits(user_id)
            
            # Should be able to use again
            assert increment_user_limit(user_id, limit_type) == True
    
    def test_weekly_limit_tracking(self, app, logged_in_user):
        """Test weekly limit tracking."""
        from src.subscription_utils import increment_user_limit, check_user_limit
        
        with app.app_context():
            user_id = logged_in_user
            limit_type = 'upc_scans_per_week'
            
            # Free user weekly limit is 25
            for i in range(25):
                result = increment_user_limit(user_id, limit_type)
                assert result == True, f"Should be able to increment usage to {i+1}"
            
            # 26th attempt should fail
            result = increment_user_limit(user_id, limit_type)
            assert result == False, "Should be blocked at weekly limit"
            
            # Verify limit status
            status = check_user_limit(user_id, limit_type, auto_count=True)
            assert status['allowed'] == False
            assert status['current'] == 25
            assert status['limit'] == 25


@pytest.mark.subscription
@pytest.mark.api
@pytest.mark.integration
class TestSubscriptionErrorHandling:
    """Test subscription system error handling."""
    
    def test_subscription_info_database_error_fallback(self, app):
        """Test that subscription info falls back gracefully on database errors."""
        from src.subscription_utils import get_user_subscription_info
        
        with app.app_context():
            # Test with invalid database connection
            with patch('src.database.get_db') as mock_db:
                mock_db.side_effect = Exception("Database error")
                
                info = get_user_subscription_info('test_user')
                
                # Should fall back to free tier
                assert info['tier'] == 'free'
                assert info['status'] == 'active'
                assert info['end_date'] == None
    
    def test_limits_check_with_invalid_feature(self, app, logged_in_user):
        """Test limits check with non-existent feature type."""
        from src.subscription_utils import check_user_limit
        
        with app.app_context():
            result = check_user_limit(logged_in_user, 'nonexistent_feature')
            
            # Should return safe defaults
            assert result['allowed'] == False
            assert result['limit'] == 0
            assert result['current'] == 0
    
    def test_subscription_template_global_error_handling(self, app):
        """Test that template global function handles errors gracefully."""
        with app.app_context():
            # Test the template global function
            template_func = app.jinja_env.globals['get_user_limits_status']
            
            # Should not raise exception even with invalid user
            result = template_func('invalid_user')
            
            # Should return safe fallback
            assert result['tier'] == 'free'
            assert result['unlimited'] == False