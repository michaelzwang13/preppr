"""
Fuzzy Matching Service for Ingredient-Pantry Matching

This service uses RapidFuzz to match recipe ingredients against user's pantry items.
It provides confidence-based classification and caching for improved performance.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from rapidfuzz import fuzz, process
from src.database import get_db
from src.logging_config import get_logger

logger = get_logger("preppr.fuzzy_matching")

@dataclass
class IngredientMatch:
    """Represents a fuzzy match between an ingredient and pantry item"""
    ingredient_name: str
    pantry_item_name: str
    pantry_item_id: int
    available_quantity: float
    available_unit: str
    confidence_score: float
    match_type: str  # 'auto', 'confirm', 'missing'
    storage_type: str
    expiration_date: Optional[str] = None

@dataclass
class MatchingResult:
    """Represents the result of fuzzy matching for shopping list generation"""
    ingredient_name: str
    required_quantity: float
    required_unit: str
    matches: List[IngredientMatch]
    best_match: Optional[IngredientMatch]
    match_type: str
    needs_to_buy: float = 0.0
    estimated_cost: Optional[float] = None

class FuzzyMatchingService:
    """Service for fuzzy matching ingredients to pantry items"""
    
    # Confidence thresholds
    AUTO_MATCH_THRESHOLD = 90.0
    CONFIRM_THRESHOLD = 70.0
    
    # Cache expiration (24 hours)
    CACHE_EXPIRATION_HOURS = 24
    
    def __init__(self):
        self.db = None
        self.cursor = None
    
    def _get_db_connection(self):
        """Get database connection and cursor"""
        # Always get fresh connection from Flask's g context
        self.db = get_db()
        self.cursor = self.db.cursor()
        return self.db, self.cursor
    
    def _convert_units(self, quantity: float, from_unit: str, to_unit: str) -> Optional[float]:
        """
        Convert between common cooking units
        Returns None if conversion is not possible
        """
        if from_unit == to_unit:
            return quantity
        
        # Normalize unit names (lowercase, remove plurals)
        from_unit = from_unit.lower().rstrip('s')
        to_unit = to_unit.lower().rstrip('s')
        
        if from_unit == to_unit:
            return quantity
        
        # Basic unit conversion mappings
        conversions = {
            # Weight conversions (to grams)
            'g': 1,
            'gram': 1,
            'kg': 1000,
            'kilogram': 1000,
            'lb': 453.592,
            'pound': 453.592,
            'oz': 28.3495,
            'ounce': 28.3495,
            
            # Volume conversions (to ml)
            'ml': 1,
            'milliliter': 1,
            'l': 1000,
            'liter': 1000,
            'cup': 240,
            'tbsp': 15,
            'tablespoon': 15,
            'tsp': 5,
            'teaspoon': 5,
            'fl oz': 29.5735,
            'fluid ounce': 29.5735,
            'pint': 473.176,
            'quart': 946.353,
            'gallon': 3785.41,
        }
        
        # Get conversion factors
        from_factor = conversions.get(from_unit)
        to_factor = conversions.get(to_unit)
        
        # If both units are in the same category (weight or volume), convert
        if from_factor and to_factor:
            # Convert from source unit to base unit, then to target unit
            base_quantity = quantity * from_factor
            return base_quantity / to_factor
        
        # Special case: pieces/count units
        count_units = {'pc', 'pcs', 'piece', 'count', 'item', 'unit'}
        if from_unit in count_units and to_unit in count_units:
            return quantity
            
        # No conversion possible
        return None

    def normalize_ingredient_name(self, ingredient_name: str) -> str:
        """Normalize ingredient name for better matching"""
        # Convert to lowercase
        normalized = ingredient_name.lower().strip()
        
        # Remove common prefixes/suffixes that might interfere with matching
        remove_words = ['fresh', 'dried', 'organic', 'raw', 'cooked', 'chopped', 'diced', 'sliced']
        words = normalized.split()
        filtered_words = [word for word in words if word not in remove_words]
        
        # If we removed all words, use original
        if not filtered_words:
            return normalized
            
        return ' '.join(filtered_words)
    
    def get_pantry_items(self, user_id: str) -> List[Dict]:
        """Get all active pantry items for a user"""
        db, cursor = self._get_db_connection()
        
        query = """
            SELECT pantry_item_id, item_name, quantity, unit, storage_type, 
                   expiration_date, category
            FROM pantry_items 
            WHERE user_id = %s AND is_consumed = FALSE
            ORDER BY item_name
        """
        
        cursor.execute(query, [user_id])
        return cursor.fetchall()
    
    def find_fuzzy_matches(self, ingredient_name: str, pantry_items: List[Dict], 
                          limit: int = 5) -> List[Tuple[Dict, float]]:
        """Find fuzzy matches for an ingredient against pantry items"""
        normalized_ingredient = self.normalize_ingredient_name(ingredient_name)
        
        # Create list of pantry item names for fuzzy matching
        pantry_names = [item['item_name'] for item in pantry_items]
        normalized_pantry_names = [self.normalize_ingredient_name(name) for name in pantry_names]
        
        # Use RapidFuzz to find best matches
        matches = process.extract(
            normalized_ingredient, 
            normalized_pantry_names, 
            scorer=fuzz.ratio, 
            limit=limit
        )
        
        # Map back to original pantry items with scores
        result = []
        for match_name, score, index in matches:
            pantry_item = pantry_items[index]
            result.append((pantry_item, float(score)))
        
        return result
    
    def classify_match(self, confidence_score: float) -> str:
        """Classify match based on confidence score"""
        if confidence_score >= self.AUTO_MATCH_THRESHOLD:
            return 'auto'
        elif confidence_score >= self.CONFIRM_THRESHOLD:
            return 'confirm'
        else:
            return 'missing'
    
    def get_cached_suggestions(self, user_id: str, ingredient_name: str) -> Optional[List[Dict]]:
        """Get cached fuzzy match suggestions for an ingredient"""
        try:
            db, cursor = self._get_db_connection()
            
            # Check for non-stale cached suggestions
            query = """
                SELECT suggested_matches, computed_at 
                FROM ingredient_match_suggestions 
                WHERE user_id = %s AND ingredient_name = %s 
                  AND is_stale = FALSE 
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY computed_at DESC 
                LIMIT 1
            """
            
            logger.debug(f"Executing cache query for user_id={user_id}, ingredient={ingredient_name}")
            cursor.execute(query, [user_id, ingredient_name])
            result = cursor.fetchone()
            
            logger.debug(f"Cache query result type: {type(result)}, value: {result}")
            
            if result:
                try:
                    suggestions = json.loads(result['suggested_matches'])
                    logger.debug(f"Found cached suggestions for {ingredient_name}", 
                               extra={'user_id': user_id, 'ingredient': ingredient_name})
                    return suggestions
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Failed to parse cached suggestions for {ingredient_name}: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error in get_cached_suggestions: {e}", exc_info=True)
            return None
    
    def cache_suggestions(self, user_id: str, ingredient_name: str, suggestions: List[Dict]):
        """Cache fuzzy match suggestions for future use"""
        db, cursor = self._get_db_connection()
        
        suggestions_json = json.dumps(suggestions)
        expires_at = datetime.now() + timedelta(hours=self.CACHE_EXPIRATION_HOURS)
        
        # Upsert cached suggestions
        query = """
            INSERT INTO ingredient_match_suggestions 
            (user_id, ingredient_name, suggested_matches, expires_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                suggested_matches = VALUES(suggested_matches),
                computed_at = CURRENT_TIMESTAMP,
                expires_at = VALUES(expires_at),
                is_stale = FALSE
        """
        
        cursor.execute(query, [user_id, ingredient_name, suggestions_json, expires_at])
        db.commit()
        
        logger.debug(f"Cached suggestions for {ingredient_name}", 
                    extra={'user_id': user_id, 'ingredient': ingredient_name})
    
    def match_ingredient_to_pantry(self, user_id: str, ingredient_name: str, 
                                 required_quantity: float = 1.0, 
                                 required_unit: str = 'pcs') -> MatchingResult:
        """
        Match a single ingredient to pantry items using fuzzy matching
        
        Args:
            user_id: User ID
            ingredient_name: Name of ingredient to match
            required_quantity: Quantity needed for recipe
            required_unit: Unit of measurement
            
        Returns:
            MatchingResult with matches and recommendations
        """
        # Check cache first
        cached_suggestions = self.get_cached_suggestions(user_id, ingredient_name)
        
        if cached_suggestions:
            # Use cached results
            matches = []
            for suggestion in cached_suggestions:
                match = IngredientMatch(
                    ingredient_name=ingredient_name,
                    pantry_item_name=suggestion['pantry_item_name'],
                    pantry_item_id=suggestion['pantry_item_id'],
                    available_quantity=suggestion['available_quantity'],
                    available_unit=suggestion['available_unit'],
                    confidence_score=suggestion['confidence_score'],
                    match_type=suggestion['match_type'],
                    storage_type=suggestion.get('storage_type', 'pantry'),
                    expiration_date=suggestion.get('expiration_date')
                )
                matches.append(match)
        else:
            # Perform fresh fuzzy matching
            pantry_items = self.get_pantry_items(user_id)
            
            if not pantry_items:
                # No pantry items available
                return MatchingResult(
                    ingredient_name=ingredient_name,
                    required_quantity=required_quantity,
                    required_unit=required_unit,
                    matches=[],
                    best_match=None,
                    match_type='missing',
                    needs_to_buy=required_quantity
                )
            
            # Find fuzzy matches
            fuzzy_matches = self.find_fuzzy_matches(ingredient_name, pantry_items)
            
            # Convert to IngredientMatch objects
            matches = []
            suggestions_to_cache = []
            
            for pantry_item, confidence in fuzzy_matches:
                match_type = self.classify_match(confidence)
                
                match = IngredientMatch(
                    ingredient_name=ingredient_name,
                    pantry_item_name=pantry_item['item_name'],
                    pantry_item_id=pantry_item['pantry_item_id'],
                    available_quantity=float(pantry_item['quantity']),
                    available_unit=pantry_item['unit'],
                    confidence_score=confidence,
                    match_type=match_type,
                    storage_type=pantry_item['storage_type'],
                    expiration_date=str(pantry_item['expiration_date']) if pantry_item['expiration_date'] else None
                )
                matches.append(match)
                
                # Prepare for caching
                suggestions_to_cache.append({
                    'pantry_item_name': match.pantry_item_name,
                    'pantry_item_id': match.pantry_item_id,
                    'available_quantity': match.available_quantity,
                    'available_unit': match.available_unit,
                    'confidence_score': match.confidence_score,
                    'match_type': match.match_type,
                    'storage_type': match.storage_type,
                    'expiration_date': match.expiration_date
                })
            
            # Cache the suggestions
            if suggestions_to_cache:
                self.cache_suggestions(user_id, ingredient_name, suggestions_to_cache)
        
        # Determine best match and calculate needs
        best_match = matches[0] if matches else None
        overall_match_type = best_match.match_type if best_match else 'missing'
        needs_to_buy = required_quantity
        
        if best_match and best_match.match_type in ['auto', 'confirm']:
            # Calculate how much is still needed after using pantry item
            available_in_required_unit = self._convert_units(
                best_match.available_quantity, 
                best_match.available_unit, 
                required_unit
            )
            
            if available_in_required_unit is not None:
                needs_to_buy = max(0, required_quantity - available_in_required_unit)
            else:
                # If conversion fails, assume we need to buy the full amount
                # but log this for improvement
                logger.warning(f"Unit conversion failed: {best_match.available_unit} -> {required_unit}")
                needs_to_buy = required_quantity
        
        return MatchingResult(
            ingredient_name=ingredient_name,
            required_quantity=required_quantity,
            required_unit=required_unit,
            matches=matches,
            best_match=best_match,
            match_type=overall_match_type,
            needs_to_buy=needs_to_buy
        )
    
    def batch_match_ingredients(self, user_id: str, 
                              ingredients: List[Dict]) -> List[MatchingResult]:
        """
        Match multiple ingredients to pantry items in batch
        
        Args:
            user_id: User ID
            ingredients: List of dicts with keys: ingredient_name, quantity, unit
            
        Returns:
            List of MatchingResult objects
        """
        results = []
        
        for ingredient in ingredients:
            result = self.match_ingredient_to_pantry(
                user_id=user_id,
                ingredient_name=ingredient['ingredient_name'],
                required_quantity=float(ingredient.get('quantity', 1.0)),
                required_unit=ingredient.get('unit', 'pcs')
            )
            results.append(result)
        
        logger.info(f"Batch matched {len(ingredients)} ingredients for user {user_id}")
        return results
    
    def record_user_feedback(self, user_id: str, ingredient_name: str, 
                           suggested_item: Optional[str], actual_item: Optional[str],
                           action_taken: str, original_confidence: Optional[float] = None):
        """Record user feedback on fuzzy matching for future improvement"""
        db, cursor = self._get_db_connection()
        
        query = """
            INSERT INTO fuzzy_match_feedback 
            (user_id, ingredient_name, suggested_pantry_item, actual_pantry_item, 
             action_taken, original_confidence)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, [
            user_id, ingredient_name, suggested_item, actual_item, 
            action_taken, original_confidence
        ])
        db.commit()
        
        logger.info(f"Recorded feedback: {action_taken} for {ingredient_name}", 
                   extra={'user_id': user_id})
    
    def get_matching_statistics(self, user_id: str, days: int = 30) -> Dict:
        """Get fuzzy matching statistics for a user"""
        db, cursor = self._get_db_connection()
        
        query = """
            SELECT 
                COUNT(*) as total_generations,
                AVG(auto_matched_count) as avg_auto_matched,
                AVG(confirm_needed_count) as avg_confirm_needed,
                AVG(missing_count) as avg_missing
            FROM shopping_generation_sessions 
            WHERE user_id = %s 
              AND generated_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        cursor.execute(query, [user_id, days])
        stats = cursor.fetchone()
        
        return {
            'total_generations': stats['total_generations'] or 0,
            'avg_auto_matched': float(stats['avg_auto_matched'] or 0),
            'avg_confirm_needed': float(stats['avg_confirm_needed'] or 0),
            'avg_missing': float(stats['avg_missing'] or 0)
        }

# Global instance
fuzzy_matching_service = FuzzyMatchingService()