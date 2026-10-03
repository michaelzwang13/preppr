"""
Comprehensive tests for ingredient_matching.py API.
Tests all endpoints for ingredient fuzzy matching, batch processing,
shopping list generation, and user feedback functionality.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from tests.conftest import open_test_connection


class MockMatchResult:
    """Mock class for MatchingResult objects."""
    def __init__(self, ingredient_name, required_quantity=1.0, required_unit="pcs", 
                 match_type="auto", needs_to_buy=0.0, estimated_cost=None):
        self.ingredient_name = ingredient_name
        self.required_quantity = required_quantity
        self.required_unit = required_unit
        self.match_type = match_type
        self.needs_to_buy = needs_to_buy
        self.estimated_cost = estimated_cost
        self.matches = []
        self.best_match = None


class MockPantryMatch:
    """Mock class for pantry match objects."""
    def __init__(self, pantry_item_name, pantry_item_id=1, available_quantity=1.0,
                 available_unit="pcs", confidence_score=95.0, match_type="auto",
                 storage_type="pantry", expiration_date=None):
        self.pantry_item_name = pantry_item_name
        self.pantry_item_id = pantry_item_id
        self.available_quantity = available_quantity
        self.available_unit = available_unit
        self.confidence_score = confidence_score
        self.match_type = match_type
        self.storage_type = storage_type
        self.expiration_date = expiration_date


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestIngredientMatchingAPI:
    """Test single ingredient matching API."""
    
    def test_match_single_ingredient_not_authenticated(self, client):
        """Test matching ingredient without authentication."""
        data = {"ingredient_name": "chicken breast", "quantity": 1.0, "unit": "lbs"}
        response = client.post('/api/ingredients/match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_match_single_ingredient_missing_name(self, client, logged_in_user):
        """Test matching ingredient without ingredient name."""
        data = {"quantity": 1.0, "unit": "lbs"}
        response = client.post('/api/ingredients/match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'ingredient_name' in response_data['message']
    
    def test_match_single_ingredient_no_data(self, client, logged_in_user):
        """Test matching ingredient with an empty JSON body is rejected."""
        response = client.post('/api/ingredients/match',
                              content_type='application/json')
        assert response.status_code == 400
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_match_single_ingredient_success(self, mock_service, client, logged_in_user):
        """Test successful single ingredient matching."""
        # Setup mock result
        mock_match = MockPantryMatch("chicken breast", confidence_score=95.0)
        mock_result = MockMatchResult("chicken breast", 2.0, "lbs", "auto", 0.5, 8.99)
        mock_result.matches = [mock_match]
        mock_result.best_match = mock_match
        
        mock_service.match_ingredient_to_pantry.return_value = mock_result
        
        data = {"ingredient_name": "chicken breast", "quantity": 2.0, "unit": "lbs"}
        response = client.post('/api/ingredients/match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        result = response_data['result']
        assert result['ingredient_name'] == 'chicken breast'
        assert result['required_quantity'] == 2.0
        assert result['required_unit'] == 'lbs'
        assert result['match_type'] == 'auto'
        assert result['needs_to_buy'] == 0.5
        assert result['estimated_cost'] == 8.99
        assert len(result['matches']) == 1
        assert result['best_match'] is not None
        
        # Verify service was called correctly
        mock_service.match_ingredient_to_pantry.assert_called_once_with(
            user_id='test_user',
            ingredient_name='chicken breast',
            required_quantity=2.0,
            required_unit='lbs'
        )
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_match_single_ingredient_default_values(self, mock_service, client, logged_in_user):
        """Test ingredient matching with default quantity and unit."""
        mock_result = MockMatchResult("tomato", 1.0, "pcs", "missing", 1.0, None)
        mock_result.matches = []
        mock_result.best_match = None
        
        mock_service.match_ingredient_to_pantry.return_value = mock_result
        
        data = {"ingredient_name": "tomato"}
        response = client.post('/api/ingredients/match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        # Verify defaults were used
        mock_service.match_ingredient_to_pantry.assert_called_once_with(
            user_id='test_user',
            ingredient_name='tomato',
            required_quantity=1.0,
            required_unit='pcs'
        )
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_match_single_ingredient_service_error(self, mock_service, client, logged_in_user):
        """Test handling of service errors during matching."""
        mock_service.match_ingredient_to_pantry.side_effect = Exception("Service error")
        
        data = {"ingredient_name": "chicken breast", "quantity": 1.0, "unit": "lbs"}
        response = client.post('/api/ingredients/match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to match ingredient'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestBatchIngredientMatching:
    """Test batch ingredient matching API."""
    
    def test_batch_match_not_authenticated(self, client):
        """Test batch matching without authentication."""
        data = {"ingredients": [{"ingredient_name": "chicken", "quantity": 1}]}
        response = client.post('/api/ingredients/batch-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_batch_match_missing_ingredients(self, client, logged_in_user):
        """Test batch matching without ingredients field."""
        data = {}
        response = client.post('/api/ingredients/batch-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'ingredients' in response_data['message']
    
    def test_batch_match_invalid_ingredients_type(self, client, logged_in_user):
        """Test batch matching with non-list ingredients."""
        data = {"ingredients": "not a list"}
        response = client.post('/api/ingredients/batch-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'must be a list' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_batch_match_success(self, mock_service, client, logged_in_user):
        """Test successful batch ingredient matching."""
        # Setup mock results
        mock_match1 = MockPantryMatch("chicken breast", confidence_score=95.0)
        mock_result1 = MockMatchResult("chicken breast", 1.0, "lbs", "auto", 0.0, 5.99)
        mock_result1.matches = [mock_match1]
        mock_result1.best_match = mock_match1
        
        mock_result2 = MockMatchResult("onion", 2.0, "pcs", "confirm", 1.0, 2.50)
        mock_result2.matches = []
        mock_result2.best_match = None
        
        mock_result3 = MockMatchResult("rare spice", 1.0, "tsp", "missing", 1.0, 15.00)
        mock_result3.matches = []
        mock_result3.best_match = None
        
        mock_service.batch_match_ingredients.return_value = [mock_result1, mock_result2, mock_result3]
        
        data = {
            "ingredients": [
                {"ingredient_name": "chicken breast", "quantity": 1.0, "unit": "lbs"},
                {"ingredient_name": "onion", "quantity": 2.0, "unit": "pcs"},
                {"ingredient_name": "rare spice", "quantity": 1.0, "unit": "tsp"}
            ]
        }
        response = client.post('/api/ingredients/batch-match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        results = response_data['results']
        assert len(results) == 3
        
        # Check summary counts
        summary = response_data['summary']
        assert summary['total_ingredients'] == 3
        assert summary['auto_matched'] == 1
        assert summary['confirm_needed'] == 1
        assert summary['missing'] == 1
        
        # Verify service was called correctly
        mock_service.batch_match_ingredients.assert_called_once_with('test_user', data['ingredients'])
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_batch_match_service_error(self, mock_service, client, logged_in_user):
        """Test handling of service errors during batch matching."""
        mock_service.batch_match_ingredients.side_effect = Exception("Batch service error")
        
        data = {"ingredients": [{"ingredient_name": "test", "quantity": 1}]}
        response = client.post('/api/ingredients/batch-match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to batch match ingredients'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.integration
class TestShoppingListGeneration:
    """Test shopping list generation with matching."""
    
    def create_test_meal_plan_session(self, client):
        """Helper to create a test meal plan session with ingredients."""
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            # Create the meal plan session the ingredients belong to
            cursor.execute("""
                INSERT INTO meal_plan_sessions
                (session_id, user_id, session_name, start_date, end_date, total_days)
                VALUES (1, %s, 'Test Meal Plan', CURDATE(), CURDATE() + INTERVAL 6 DAY, 7)
            """, ('test_user',))
            
            # Pantry item the mocked matches point at (pantry_item_id=1)
            cursor.execute("""
                INSERT INTO pantry_items (pantry_item_id, user_id, item_name, quantity, unit)
                VALUES (1, %s, 'chicken breast', 1.0, 'lbs')
            """, ('test_user',))
            
            # Create session shopping list entries
            cursor.execute("""
                INSERT INTO session_shopping_lists (session_id, ingredient_name, total_quantity, unit, estimated_cost, category)
                VALUES 
                (1, 'chicken breast', 2.0, 'lbs', 8.99, 'Meat'),
                (1, 'onion', 1.0, 'pcs', 1.50, 'Vegetables'),
                (1, 'rice', 1.0, 'cup', 2.00, 'Grains')
            """)
            cursor.close()
    
    def test_generate_shopping_list_not_authenticated(self, client):
        """Test generating shopping list without authentication."""
        data = {"meal_plan_session_id": 1}
        response = client.post('/api/shopping/generate-with-matching',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_generate_shopping_list_missing_session_id(self, client, logged_in_user):
        """Test generating shopping list without meal plan session ID."""
        data = {}
        response = client.post('/api/shopping/generate-with-matching',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'meal_plan_session_id' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_generate_shopping_list_no_ingredients(self, mock_service, client, logged_in_user):
        """Test generating shopping list when no ingredients found."""
        data = {"meal_plan_session_id": 999}
        response = client.post('/api/shopping/generate-with-matching',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'No ingredients found' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_generate_shopping_list_success(self, mock_service, client, logged_in_user):
        """Test successful shopping list generation with matching."""
        self.create_test_meal_plan_session(client)
        
        # Setup mock results
        mock_match = MockPantryMatch("chicken breast", confidence_score=90.0)
        mock_result1 = MockMatchResult("chicken breast", 2.0, "lbs", "auto", 1.0, 8.99)
        mock_result1.matches = [mock_match]
        mock_result1.best_match = mock_match
        
        mock_result2 = MockMatchResult("onion", 1.0, "pcs", "missing", 1.0, 1.50)
        mock_result2.matches = []
        mock_result2.best_match = None
        
        mock_result3 = MockMatchResult("rice", 1.0, "cup", "confirm", 0.5, 2.00)
        mock_result3.matches = []
        mock_result3.best_match = None
        
        mock_service.batch_match_ingredients.return_value = [mock_result1, mock_result2, mock_result3]
        
        data = {"meal_plan_session_id": 1, "generation_type": "meal_plan"}
        response = client.post('/api/shopping/generate-with-matching',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        assert 'generation_id' in response_data
        assert 'shopping_items' in response_data
        assert 'matching_summary' in response_data
        
        # Verify summary
        summary = response_data['matching_summary']
        assert summary['total_ingredients'] == 3
        assert summary['auto_matched'] == 1
        assert summary['confirm_needed'] == 1
        assert summary['missing'] == 1
        
        # Verify shopping items (only items that need to be bought)
        shopping_items = response_data['shopping_items']
        assert len(shopping_items) == 3  # chicken (1.0 needed), onion (1.0 needed), rice (0.5 needed)


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestMatchingFeedback:
    """Test ingredient matching feedback functionality."""
    
    def test_submit_feedback_not_authenticated(self, client):
        """Test submitting feedback without authentication."""
        data = {
            "ingredient_name": "chicken",
            "action_taken": "corrected"
        }
        response = client.post('/api/ingredients/feedback',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_submit_feedback_missing_fields(self, client, logged_in_user):
        """Test submitting feedback with missing required fields."""
        # Missing ingredient_name
        data = {"action_taken": "corrected"}
        response = client.post('/api/ingredients/feedback',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'ingredient_name' in response_data['message']
        
        # Missing action_taken
        data = {"ingredient_name": "chicken"}
        response = client.post('/api/ingredients/feedback',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'action_taken' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_submit_feedback_success(self, mock_service, client, logged_in_user):
        """Test successful feedback submission."""
        mock_service.record_user_feedback.return_value = None
        
        data = {
            "ingredient_name": "chicken breast",
            "suggested_item": "chicken thighs",
            "actual_item": "chicken breast",
            "action_taken": "corrected",
            "original_confidence": 75.5
        }
        response = client.post('/api/ingredients/feedback',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        assert response_data['message'] == 'Feedback recorded successfully'
        
        # Verify service was called correctly
        mock_service.record_user_feedback.assert_called_once_with(
            user_id='test_user',
            ingredient_name='chicken breast',
            suggested_item='chicken thighs',
            actual_item='chicken breast',
            action_taken='corrected',
            original_confidence=75.5
        )
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_submit_feedback_service_error(self, mock_service, client, logged_in_user):
        """Test handling of service errors during feedback submission."""
        mock_service.record_user_feedback.side_effect = Exception("Feedback error")
        
        data = {
            "ingredient_name": "chicken",
            "action_taken": "accepted"
        }
        response = client.post('/api/ingredients/feedback',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to record feedback'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestMatchingStatistics:
    """Test ingredient matching statistics functionality."""
    
    def test_get_statistics_not_authenticated(self, client):
        """Test getting statistics without authentication."""
        response = client.get('/api/ingredients/matching-stats')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_get_statistics_success(self, mock_service, client, logged_in_user):
        """Test successful statistics retrieval."""
        mock_stats = {
            "total_matches": 150,
            "auto_matches": 120,
            "confirm_matches": 20,
            "missing_matches": 10,
            "average_confidence": 87.5,
            "recent_activity": []
        }
        mock_service.get_matching_statistics.return_value = mock_stats
        
        response = client.get('/api/ingredients/matching-stats')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        assert response_data['stats'] == mock_stats
        
        # Verify service was called with default days (30)
        mock_service.get_matching_statistics.assert_called_once_with('test_user', 30)
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_get_statistics_with_custom_days(self, mock_service, client, logged_in_user):
        """Test statistics retrieval with custom days parameter."""
        mock_service.get_matching_statistics.return_value = {}
        
        response = client.get('/api/ingredients/matching-stats?days=7')
        
        assert response.status_code == 200
        # Verify service was called with custom days
        mock_service.get_matching_statistics.assert_called_once_with('test_user', 7)
    
    @patch('src.backend.apis.ingredient_matching.fuzzy_matching_service')
    def test_get_statistics_service_error(self, mock_service, client, logged_in_user):
        """Test handling of service errors during statistics retrieval."""
        mock_service.get_matching_statistics.side_effect = Exception("Stats error")
        
        response = client.get('/api/ingredients/matching-stats')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to get statistics'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.integration
class TestShoppingGenerationHistory:
    """Test shopping generation history functionality."""
    
    def create_test_generation_data(self, client):
        """Helper to create test generation data."""
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            
            # Create the meal plan session the ingredients belong to
            cursor.execute("""
                INSERT INTO meal_plan_sessions
                (session_id, user_id, session_name, start_date, end_date, total_days)
                VALUES (1, %s, 'Test Meal Plan', CURDATE(), CURDATE() + INTERVAL 6 DAY, 7)
            """, ('test_user',))
            
            # Create shopping generation session
            cursor.execute("""
                INSERT INTO shopping_generation_sessions 
                (user_id, meal_plan_session_id, generation_type, total_ingredients,
                 auto_matched_count, confirm_needed_count, missing_count, generated_at)
                VALUES (%s, 1, 'meal_plan', 5, 3, 1, 1, NOW())
            """, ('test_user',))
            
            generation_id = cursor.lastrowid
            cursor.close()
            return generation_id
    
    def test_get_generations_not_authenticated(self, client):
        """Test getting generations without authentication."""
        response = client.get('/api/shopping/generations')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_get_generations_success(self, client, logged_in_user):
        """Test successful generation history retrieval."""
        generation_id = self.create_test_generation_data(client)
        
        response = client.get('/api/shopping/generations')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        generations = response_data['generations']
        assert len(generations) == 1
        
        generation = generations[0]
        assert generation['generation_id'] == generation_id
        assert generation['generation_type'] == 'meal_plan'
        assert generation['total_ingredients'] == 5
        assert generation['auto_matched_count'] == 3
        assert generation['confirm_needed_count'] == 1
        assert generation['missing_count'] == 1
    
    def test_get_generation_details_not_authenticated(self, client):
        """Test getting generation details without authentication."""
        response = client.get('/api/shopping/generation/1/details')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_get_generation_details_not_found(self, client, logged_in_user):
        """Test getting details for non-existent generation."""
        response = client.get('/api/shopping/generation/999/details')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Generation not found'
    
    def test_get_generation_details_success(self, client, logged_in_user):
        """Test successful generation details retrieval."""
        generation_id = self.create_test_generation_data(client)
        
        # Add some match data
        with client.application.app_context():
            db = open_test_connection()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO generation_ingredient_matches
                (generation_id, ingredient_name, required_quantity, required_unit,
                 match_type, needs_to_buy_quantity, estimated_cost)
                VALUES (%s, 'chicken breast', 2.0, 'lbs', 'auto', 1.0, 8.99)
            """, (generation_id,))
            cursor.close()
        
        response = client.get(f'/api/shopping/generation/{generation_id}/details')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        
        assert 'generation' in response_data
        assert 'matches' in response_data
        
        generation = response_data['generation']
        assert generation['generation_id'] == generation_id
        
        matches = response_data['matches']
        assert len(matches) == 1
        assert matches[0]['ingredient_name'] == 'chicken breast'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestSmartShoppingGeneration:
    """Test smart shopping list generation."""
    
    def test_smart_generate_not_authenticated(self, client):
        """Test smart generation without authentication."""
        data = {"meal_plan_session_id": 1}
        response = client.post('/api/shopping/smart-generate',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_smart_generate_missing_session_id(self, client, logged_in_user):
        """Test smart generation without meal plan session ID."""
        data = {}
        response = client.post('/api/shopping/smart-generate',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'meal_plan_session_id' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.enhanced_shopping_generator')
    def test_smart_generate_success(self, mock_generator, client, logged_in_user):
        """Test successful smart shopping list generation."""
        mock_result = {
            "success": True,
            "generation_id": 123,
            "shopping_items": [],
            "confirmed_matches": [],
            "matching_summary": {"total_ingredients": 5},
            "cost_analysis": {"total_estimated": 25.99},
            "recommendations": []
        }
        mock_generator.generate_smart_shopping_list.return_value = mock_result
        
        data = {
            "meal_plan_session_id": 1,
            "auto_confirm_threshold": 90.0
        }
        response = client.post('/api/shopping/smart-generate',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data == mock_result
        
        # Verify service was called correctly
        mock_generator.generate_smart_shopping_list.assert_called_once_with(
            user_id='test_user',
            meal_plan_session_id=1,
            auto_confirm_threshold=90.0
        )
    
    @patch('src.backend.apis.ingredient_matching.enhanced_shopping_generator')
    def test_smart_generate_service_error(self, mock_generator, client, logged_in_user):
        """Test handling of service errors during smart generation."""
        mock_generator.generate_smart_shopping_list.side_effect = Exception("Smart generation error")
        
        data = {"meal_plan_session_id": 1}
        response = client.post('/api/shopping/smart-generate',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to generate smart shopping list'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestIngredientMatchConfirmation:
    """Test ingredient match confirmation functionality."""
    
    def test_confirm_match_not_authenticated(self, client):
        """Test confirming match without authentication."""
        data = {
            "generation_id": 1,
            "ingredient_name": "chicken",
            "pantry_item_id": 123
        }
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Not authenticated'
    
    def test_confirm_match_missing_fields(self, client, logged_in_user):
        """Test confirming match with missing required fields."""
        # Missing generation_id
        data = {"ingredient_name": "chicken"}
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'generation_id' in response_data['message']
        
        # Missing ingredient_name
        data = {"generation_id": 1}
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert 'ingredient_name' in response_data['message']
    
    @patch('src.backend.apis.ingredient_matching.enhanced_shopping_generator')
    def test_confirm_match_success(self, mock_generator, client, logged_in_user):
        """Test successful match confirmation."""
        mock_result = {
            "success": True,
            "message": "Match confirmed successfully"
        }
        mock_generator.confirm_ingredient_match.return_value = mock_result
        
        data = {
            "generation_id": 123,
            "ingredient_name": "chicken breast",
            "pantry_item_id": 456
        }
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data == mock_result
        
        # Verify service was called correctly
        mock_generator.confirm_ingredient_match.assert_called_once_with(
            generation_id=123,
            ingredient_name='chicken breast',
            pantry_item_id=456,
            user_id='test_user'
        )
    
    @patch('src.backend.apis.ingredient_matching.enhanced_shopping_generator')
    def test_confirm_match_reject(self, mock_generator, client, logged_in_user):
        """Test rejecting a match (pantry_item_id = null)."""
        mock_result = {
            "success": True,
            "message": "Match rejected successfully"
        }
        mock_generator.confirm_ingredient_match.return_value = mock_result
        
        data = {
            "generation_id": 123,
            "ingredient_name": "rare ingredient",
            "pantry_item_id": None
        }
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data == mock_result
        
        # Verify service was called with None for pantry_item_id
        mock_generator.confirm_ingredient_match.assert_called_once_with(
            generation_id=123,
            ingredient_name='rare ingredient',
            pantry_item_id=None,
            user_id='test_user'
        )
    
    @patch('src.backend.apis.ingredient_matching.enhanced_shopping_generator')
    def test_confirm_match_service_error(self, mock_generator, client, logged_in_user):
        """Test handling of service errors during match confirmation."""
        mock_generator.confirm_ingredient_match.side_effect = Exception("Confirm error")
        
        data = {
            "generation_id": 1,
            "ingredient_name": "chicken"
        }
        response = client.post('/api/shopping/confirm-match',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        assert response_data['message'] == 'Failed to confirm match'


@pytest.mark.shopping
@pytest.mark.api
@pytest.mark.unit
class TestIngredientMatchingErrorHandling:
    """Test error handling and edge cases for ingredient matching."""
    
    def test_invalid_json_data(self, client, logged_in_user):
        """Test handling of invalid JSON data."""
        response = client.post('/api/ingredients/match',
                              data='invalid json',
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_quantity_type_conversion(self, client, logged_in_user):
        """Test that quantity is properly converted to float."""
        with patch('src.backend.apis.ingredient_matching.fuzzy_matching_service') as mock_service:
            mock_result = MockMatchResult("test", 1.0, "pcs")
            mock_service.match_ingredient_to_pantry.return_value = mock_result
            
            # Test string quantity
            data = {"ingredient_name": "test", "quantity": "2.5"}
            response = client.post('/api/ingredients/match',
                                  data=json.dumps(data),
                                  content_type='application/json')
            
            assert response.status_code == 200
            # Verify service was called with float
            mock_service.match_ingredient_to_pantry.assert_called_with(
                user_id='test_user',
                ingredient_name='test',
                required_quantity=2.5,
                required_unit='pcs'
            )
    
    def test_database_error_handling(self, client, logged_in_user):
        """Test handling of database errors during shopping list generation."""
        # Use invalid session ID to trigger database error
        data = {"meal_plan_session_id": -1}
        response = client.post('/api/shopping/generate-with-matching',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] == False
        # Should handle database error gracefully
    
    def test_empty_ingredient_list_batch_match(self, client, logged_in_user):
        """Test batch matching with empty ingredient list."""
        with patch('src.backend.apis.ingredient_matching.fuzzy_matching_service') as mock_service:
            mock_service.batch_match_ingredients.return_value = []
            
            data = {"ingredients": []}
            response = client.post('/api/ingredients/batch-match',
                                  data=json.dumps(data),
                                  content_type='application/json')
            
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['success'] == True
            assert response_data['results'] == []
            assert response_data['summary']['total_ingredients'] == 0