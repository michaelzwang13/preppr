"""
Enhanced Shopping List Generation with Fuzzy Matching

This service integrates fuzzy matching into the shopping list generation process,
providing intelligent ingredient-to-pantry matching for meal plan workflows.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from src.database import get_db
from src.services.fuzzy_matching import fuzzy_matching_service, MatchingResult
from src.logging_config import get_logger

logger = get_logger("preppr.enhanced_shopping")

class EnhancedShoppingGenerator:
    """Enhanced shopping list generator with fuzzy matching capabilities"""
    
    def __init__(self):
        self.db = None
        self.cursor = None
        self.fuzzy_service = fuzzy_matching_service
    
    def _get_db_connection(self):
        """Get database connection and cursor"""
        if not self.db:
            self.db = get_db()
            self.cursor = self.db.cursor()
        return self.db, self.cursor
    
    def generate_smart_shopping_list(self, user_id: str, meal_plan_session_id: int, 
                                   auto_confirm_threshold: float = 85.0) -> Dict:
        """
        Generate an intelligent shopping list using fuzzy matching
        
        Args:
            user_id: User ID
            meal_plan_session_id: Meal plan session to generate list for
            auto_confirm_threshold: Confidence threshold for auto-confirming matches
            
        Returns:
            Dict containing shopping list data and matching results
        """
        db, cursor = self._get_db_connection()
        
        try:
            # Get ingredients from meal plan session
            cursor.execute("""
                SELECT ingredient_name, total_quantity, unit, estimated_cost, category
                FROM session_shopping_lists 
                WHERE session_id = %s
                ORDER BY category, ingredient_name
            """, [meal_plan_session_id])
            
            raw_ingredients = cursor.fetchall()
            
            if not raw_ingredients:
                return {
                    "success": False,
                    "message": "No ingredients found for meal plan",
                    "shopping_items": [],
                    "matching_summary": {}
                }
            
            # Create shopping generation session
            cursor.execute("""
                INSERT INTO shopping_generation_sessions 
                (user_id, meal_plan_session_id, generation_type, total_ingredients)
                VALUES (%s, %s, 'meal_plan', %s)
            """, [user_id, meal_plan_session_id, len(raw_ingredients)])
            
            generation_id = cursor.lastrowid
            
            # Prepare ingredients for fuzzy matching
            ingredients_for_matching = [
                {
                    "ingredient_name": ing["ingredient_name"],
                    "quantity": float(ing["total_quantity"]),
                    "unit": ing["unit"]
                }
                for ing in raw_ingredients
            ]
            
            # Perform batch fuzzy matching
            matching_results = self.fuzzy_service.batch_match_ingredients(user_id, ingredients_for_matching)
            
            # Process results and create shopping items
            shopping_items = []
            confirmed_matches = []
            summary = {
                "total_ingredients": len(matching_results),
                "auto_matched": 0,
                "confirm_needed": 0, 
                "missing": 0,
                "partially_available": 0
            }
            
            for i, result in enumerate(matching_results):
                original_ingredient = raw_ingredients[i]
                
                # Store detailed matching result in database
                cursor.execute("""
                    INSERT INTO generation_ingredient_matches 
                    (generation_id, ingredient_name, required_quantity, required_unit, 
                     pantry_item_id, pantry_available_quantity, match_confidence, 
                     match_type, needs_to_buy_quantity, estimated_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    generation_id,
                    result.ingredient_name,
                    result.required_quantity,
                    result.required_unit,
                    result.best_match.pantry_item_id if result.best_match else None,
                    result.best_match.available_quantity if result.best_match else None,
                    result.best_match.confidence_score if result.best_match else None,
                    result.match_type,
                    result.needs_to_buy,
                    float(original_ingredient.get("estimated_cost", 0))
                ])
                
                # Determine final status based on confidence and auto-confirm threshold
                final_match_type = result.match_type
                if (result.best_match and 
                    result.best_match.confidence_score >= auto_confirm_threshold and 
                    result.match_type == "confirm"):
                    final_match_type = "auto"
                
                # Create shopping item based on matching result
                shopping_item = {
                    "ingredient_name": result.ingredient_name,
                    "required_quantity": result.required_quantity,
                    "required_unit": result.required_unit,
                    "category": original_ingredient.get("category", "Other"),
                    "estimated_cost": float(original_ingredient.get("estimated_cost", 0)),
                    "match_type": final_match_type,
                    "needs_to_buy": result.needs_to_buy,
                    "pantry_match": None,
                    "user_action_required": False
                }
                
                # Add pantry match information if available
                if result.best_match:
                    shopping_item["pantry_match"] = {
                        "pantry_item_id": result.best_match.pantry_item_id,
                        "pantry_item_name": result.best_match.pantry_item_name,
                        "available_quantity": result.best_match.available_quantity,
                        "available_unit": result.best_match.available_unit,
                        "confidence_score": result.best_match.confidence_score,
                        "storage_type": result.best_match.storage_type,
                        "expiration_date": result.best_match.expiration_date
                    }
                
                # Handle different match types
                if final_match_type == "auto":
                    summary["auto_matched"] += 1
                    if result.needs_to_buy > 0:
                        summary["partially_available"] += 1
                        shopping_item["status"] = "partial_match"
                        shopping_items.append(shopping_item)
                    else:
                        shopping_item["status"] = "fully_available"
                        confirmed_matches.append(shopping_item)
                        
                elif final_match_type == "confirm":
                    summary["confirm_needed"] += 1
                    shopping_item["user_action_required"] = True
                    shopping_item["status"] = "needs_confirmation"
                    shopping_items.append(shopping_item)
                    
                else:  # missing
                    summary["missing"] += 1
                    shopping_item["status"] = "not_in_pantry"
                    shopping_items.append(shopping_item)
                
            # Update generation session with summary
            cursor.execute("""
                UPDATE shopping_generation_sessions 
                SET auto_matched_count = %s, confirm_needed_count = %s, 
                    missing_count = %s, completed_at = NOW()
                WHERE generation_id = %s
            """, [
                summary["auto_matched"], 
                summary["confirm_needed"], 
                summary["missing"], 
                generation_id
            ])
            
            db.commit()
            
            # Calculate estimated savings from pantry usage
            total_estimated_cost = sum(float(ing.get("estimated_cost", 0)) for ing in raw_ingredients)
            shopping_cost = sum(item.get("estimated_cost", 0) for item in shopping_items)
            estimated_savings = total_estimated_cost - shopping_cost
            
            return {
                "success": True,
                "generation_id": generation_id,
                "shopping_items": shopping_items,
                "confirmed_matches": confirmed_matches,
                "matching_summary": summary,
                "cost_analysis": {
                    "total_recipe_cost": total_estimated_cost,
                    "shopping_list_cost": shopping_cost,
                    "estimated_savings": estimated_savings,
                    "pantry_utilization_rate": (summary["auto_matched"] / summary["total_ingredients"]) * 100
                },
                "recommendations": self._generate_recommendations(summary, shopping_items)
            }
            
        except Exception as e:
            logger.error(f"Error generating smart shopping list: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to generate shopping list: {str(e)}",
                "shopping_items": [],
                "matching_summary": {}
            }
    
    def _generate_recommendations(self, summary: Dict, shopping_items: List[Dict]) -> List[str]:
        """Generate user-friendly recommendations based on matching results"""
        recommendations = []
        
        # High pantry utilization
        if summary["total_ingredients"] > 0:
            utilization_rate = (summary["auto_matched"] / summary["total_ingredients"]) * 100
            
            if utilization_rate >= 70:
                recommendations.append("Excellent pantry utilization! You're using most ingredients from your existing pantry.")
            elif utilization_rate >= 50:
                recommendations.append("Good pantry usage. Consider stocking up on frequently used items.")
            else:
                recommendations.append("Low pantry utilization. Consider updating your pantry inventory.")
        
        # Confirmation needed items
        if summary["confirm_needed"] > 0:
            recommendations.append(f"Please review {summary['confirm_needed']} ingredient matches for accuracy.")
        
        # Expiring items
        expiring_items = [
            item for item in shopping_items 
            if item.get("pantry_match") and item["pantry_match"].get("expiration_date")
        ]
        if expiring_items:
            recommendations.append("Some pantry matches are approaching expiration - prioritize using them first.")
        
        # Cost savings
        return recommendations
    
    def confirm_ingredient_match(self, generation_id: int, ingredient_name: str, 
                               pantry_item_id: Optional[int], user_id: str) -> Dict:
        """
        Confirm or override an ingredient match
        
        Args:
            generation_id: Shopping generation session ID
            ingredient_name: Name of ingredient being confirmed
            pantry_item_id: ID of pantry item to match (None if no match)
            user_id: User ID for verification
        """
        db, cursor = self._get_db_connection()
        
        try:
            # Verify user owns this generation
            cursor.execute("""
                SELECT * FROM shopping_generation_sessions 
                WHERE generation_id = %s AND user_id = %s
            """, [generation_id, user_id])
            
            if not cursor.fetchone():
                return {"success": False, "message": "Generation not found"}
              
            print(f'Pantry Item: {pantry_item_id}, Generation ID: {generation_id}, Ingredient Name: {ingredient_name}')
            
            # Update the match record
            if pantry_item_id:
                # User confirmed a match
                cursor.execute("""
                    UPDATE generation_ingredient_matches 
                    SET pantry_item_id = %s, match_type = 'user_override', 
                        is_user_confirmed = TRUE, updated_at = NOW()
                    WHERE generation_id = %s AND ingredient_name = %s
                """, [pantry_item_id, generation_id, ingredient_name])
                
                # Record positive feedback
                self.fuzzy_service.record_user_feedback(
                    user_id, ingredient_name, None, None, "accepted"
                )
                
            else:
                # User rejected match - mark as missing
                cursor.execute("""
                    UPDATE generation_ingredient_matches 
                    SET pantry_item_id = NULL, match_type = 'missing', 
                        is_user_confirmed = TRUE, updated_at = NOW()
                    WHERE generation_id = %s AND ingredient_name = %s
                """, [generation_id, ingredient_name])
                
                # Record negative feedback
                self.fuzzy_service.record_user_feedback(
                    user_id, ingredient_name, None, None, "rejected"
                )
            
            db.commit()
            return {"success": True, "message": "Match confirmed"}
            
        except Exception as e:
            logger.error(f"Error confirming match: {str(e)}", exc_info=True)
            return {"success": False, "message": "Failed to confirm match"}

# Global instance
enhanced_shopping_generator = EnhancedShoppingGenerator()