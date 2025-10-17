"""
API endpoints for ingredient fuzzy matching functionality
"""

from flask import Blueprint, request, jsonify, session
from src.database import get_db
from src.services.fuzzy_matching import fuzzy_matching_service, MatchingResult
from src.logging_config import get_logger
from datetime import datetime
import json

logger = get_logger("preppr.ingredient_matching_api")

ingredient_matching_bp = Blueprint("ingredient_matching", __name__, url_prefix="/api")

@ingredient_matching_bp.route("/ingredients/match", methods=["POST"])
def match_single_ingredient():
    """
    Match a single ingredient to pantry items using fuzzy matching
    
    Request body:
    {
        "ingredient_name": "chicken breast",
        "quantity": 2.0,
        "unit": "lbs"
    }
    
    Response:
    {
        "success": true,
        "result": {
            "ingredient_name": "chicken breast",
            "required_quantity": 2.0,
            "required_unit": "lbs",
            "matches": [...],
            "best_match": {...},
            "match_type": "auto|confirm|missing",
            "needs_to_buy": 0.5,
            "estimated_cost": 8.99
        }
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    if not data or "ingredient_name" not in data:
        return jsonify({"success": False, "message": "Missing required field: ingredient_name"})
    
    try:
        result = fuzzy_matching_service.match_ingredient_to_pantry(
            user_id=user_id,
            ingredient_name=data["ingredient_name"],
            required_quantity=float(data.get("quantity", 1.0)),
            required_unit=data.get("unit", "pcs")
        )
        
        # Convert result to JSON-serializable format
        result_dict = {
            "ingredient_name": result.ingredient_name,
            "required_quantity": result.required_quantity,
            "required_unit": result.required_unit,
            "matches": [
                {
                    "pantry_item_name": match.pantry_item_name,
                    "pantry_item_id": match.pantry_item_id,
                    "available_quantity": match.available_quantity,
                    "available_unit": match.available_unit,
                    "confidence_score": match.confidence_score,
                    "match_type": match.match_type,
                    "storage_type": match.storage_type,
                    "expiration_date": match.expiration_date
                }
                for match in result.matches
            ],
            "best_match": {
                "pantry_item_name": result.best_match.pantry_item_name,
                "pantry_item_id": result.best_match.pantry_item_id,
                "available_quantity": result.best_match.available_quantity,
                "available_unit": result.best_match.available_unit,
                "confidence_score": result.best_match.confidence_score,
                "match_type": result.best_match.match_type,
                "storage_type": result.best_match.storage_type,
                "expiration_date": result.best_match.expiration_date
            } if result.best_match else None,
            "match_type": result.match_type,
            "needs_to_buy": result.needs_to_buy,
            "estimated_cost": result.estimated_cost
        }
        
        return jsonify({"success": True, "result": result_dict})
        
    except Exception as e:
        logger.error(f"Error matching ingredient: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to match ingredient"})

@ingredient_matching_bp.route("/ingredients/batch-match", methods=["POST"])
def batch_match_ingredients():
    """
    Match multiple ingredients to pantry items in batch
    
    Request body:
    {
        "ingredients": [
            {"ingredient_name": "chicken breast", "quantity": 2.0, "unit": "lbs"},
            {"ingredient_name": "onion", "quantity": 1, "unit": "pcs"}
        ]
    }
    
    Response:
    {
        "success": true,
        "results": [...],
        "summary": {
            "total_ingredients": 2,
            "auto_matched": 1,
            "confirm_needed": 1,
            "missing": 0
        }
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    if not data or "ingredients" not in data:
        return jsonify({"success": False, "message": "Missing required field: ingredients"})
    
    ingredients = data["ingredients"]
    if not isinstance(ingredients, list):
        return jsonify({"success": False, "message": "ingredients must be a list"})
    
    try:
        results = fuzzy_matching_service.batch_match_ingredients(user_id, ingredients)
        
        # Convert results to JSON-serializable format
        results_dict = []
        summary = {"auto_matched": 0, "confirm_needed": 0, "missing": 0}
        
        for result in results:
            result_dict = {
                "ingredient_name": result.ingredient_name,
                "required_quantity": result.required_quantity,
                "required_unit": result.required_unit,
                "matches": [
                    {
                        "pantry_item_name": match.pantry_item_name,
                        "pantry_item_id": match.pantry_item_id,
                        "available_quantity": match.available_quantity,
                        "available_unit": match.available_unit,
                        "confidence_score": match.confidence_score,
                        "match_type": match.match_type,
                        "storage_type": match.storage_type,
                        "expiration_date": match.expiration_date
                    }
                    for match in result.matches
                ],
                "best_match": {
                    "pantry_item_name": result.best_match.pantry_item_name,
                    "pantry_item_id": result.best_match.pantry_item_id,
                    "available_quantity": result.best_match.available_quantity,
                    "available_unit": result.best_match.available_unit,
                    "confidence_score": result.best_match.confidence_score,
                    "match_type": result.best_match.match_type,
                    "storage_type": result.best_match.storage_type,
                    "expiration_date": result.best_match.expiration_date
                } if result.best_match else None,
                "match_type": result.match_type,
                "needs_to_buy": result.needs_to_buy,
                "estimated_cost": result.estimated_cost
            }
            results_dict.append(result_dict)
            
            # Update summary counts
            if result.match_type == "auto":
                summary["auto_matched"] += 1
            elif result.match_type == "confirm":
                summary["confirm_needed"] += 1
            else:
                summary["missing"] += 1
        
        summary["total_ingredients"] = len(results)
        
        return jsonify({
            "success": True, 
            "results": results_dict, 
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Error batch matching ingredients: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to batch match ingredients"})

@ingredient_matching_bp.route("/shopping/generate-with-matching", methods=["POST"])
def generate_shopping_list_with_matching():
    """
    Generate shopping list from meal plan with fuzzy matching
    
    Request body:
    {
        "meal_plan_session_id": 123,
        "generation_type": "meal_plan"
    }
    
    Response:
    {
        "success": true,
        "generation_id": 456,
        "shopping_items": [...],
        "matching_summary": {
            "total_ingredients": 15,
            "auto_matched": 8,
            "confirm_needed": 4,
            "missing": 3
        }
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    if not data or "meal_plan_session_id" not in data:
        return jsonify({"success": False, "message": "Missing required field: meal_plan_session_id"})
    
    meal_plan_session_id = data["meal_plan_session_id"]
    generation_type = data.get("generation_type", "meal_plan")
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get ingredients from meal plan session
        cursor.execute("""
            SELECT ingredient_name, total_quantity, unit, estimated_cost
            FROM session_shopping_lists 
            WHERE session_id = %s
            ORDER BY category, ingredient_name
        """, [meal_plan_session_id])
        
        ingredients = cursor.fetchall()
        
        if not ingredients:
            return jsonify({"success": False, "message": "No ingredients found for meal plan"})
        
        # Create shopping generation session
        cursor.execute("""
            INSERT INTO shopping_generation_sessions 
            (user_id, meal_plan_session_id, generation_type, total_ingredients)
            VALUES (%s, %s, %s, %s)
        """, [user_id, meal_plan_session_id, generation_type, len(ingredients)])
        
        generation_id = cursor.lastrowid
        
        # Batch match ingredients
        ingredients_list = [
            {
                "ingredient_name": ing["ingredient_name"],
                "quantity": float(ing["total_quantity"]),
                "unit": ing["unit"]
            }
            for ing in ingredients
        ]
        
        matching_results = fuzzy_matching_service.batch_match_ingredients(user_id, ingredients_list)
        
        # Store detailed matching results
        shopping_items = []
        summary = {"auto_matched": 0, "confirm_needed": 0, "missing": 0}
        
        for i, result in enumerate(matching_results):
            original_ingredient = ingredients[i]
            
            # Insert generation match result
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
                original_ingredient.get("estimated_cost")
            ])
            
            # Create shopping item if needed
            if result.needs_to_buy > 0:
                shopping_item = {
                    "ingredient_name": result.ingredient_name,
                    "quantity_needed": result.needs_to_buy,
                    "unit": result.required_unit,
                    "match_type": result.match_type,
                    "pantry_match": {
                        "item_name": result.best_match.pantry_item_name,
                        "confidence": result.best_match.confidence_score,
                        "available": result.best_match.available_quantity
                    } if result.best_match else None,
                    "estimated_cost": original_ingredient.get("estimated_cost"),
                    "category": original_ingredient.get("category", "Other")
                }
                shopping_items.append(shopping_item)
            
            # Update summary
            if result.match_type == "auto":
                summary["auto_matched"] += 1
            elif result.match_type == "confirm":
                summary["confirm_needed"] += 1
            else:
                summary["missing"] += 1
        
        # Update generation session with summary
        cursor.execute("""
            UPDATE shopping_generation_sessions 
            SET auto_matched_count = %s, confirm_needed_count = %s, missing_count = %s
            WHERE generation_id = %s
        """, [summary["auto_matched"], summary["confirm_needed"], summary["missing"], generation_id])
        
        db.commit()
        
        summary["total_ingredients"] = len(matching_results)
        
        return jsonify({
            "success": True,
            "generation_id": generation_id,
            "shopping_items": shopping_items,
            "matching_summary": summary
        })
        
    except Exception as e:
        logger.error(f"Error generating shopping list with matching: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to generate shopping list"})

@ingredient_matching_bp.route("/ingredients/feedback", methods=["POST"])
def submit_matching_feedback():
    """
    Submit user feedback on fuzzy matching results
    
    Request body:
    {
        "ingredient_name": "chicken breast",
        "suggested_item": "chicken thighs",
        "actual_item": "chicken breast",
        "action_taken": "corrected",
        "original_confidence": 75.5
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    required_fields = ["ingredient_name", "action_taken"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"})
    
    try:
        fuzzy_matching_service.record_user_feedback(
            user_id=user_id,
            ingredient_name=data["ingredient_name"],
            suggested_item=data.get("suggested_item"),
            actual_item=data.get("actual_item"),
            action_taken=data["action_taken"],
            original_confidence=data.get("original_confidence")
        )
        
        return jsonify({"success": True, "message": "Feedback recorded successfully"})
        
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to record feedback"})

@ingredient_matching_bp.route("/ingredients/matching-stats", methods=["GET"])
def get_matching_statistics():
    """Get user's fuzzy matching statistics"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    days = int(request.args.get("days", 30))
    
    try:
        stats = fuzzy_matching_service.get_matching_statistics(user_id, days)
        return jsonify({"success": True, "stats": stats})
        
    except Exception as e:
        logger.error(f"Error getting matching statistics: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to get statistics"})

@ingredient_matching_bp.route("/shopping/generations", methods=["GET"])
def get_shopping_generations():
    """Get user's shopping generation history with matching details"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get recent generation sessions
        cursor.execute("""
            SELECT sgs.*, mps.session_name as meal_plan_name
            FROM shopping_generation_sessions sgs
            LEFT JOIN meal_plan_sessions mps ON sgs.meal_plan_session_id = mps.session_id
            WHERE sgs.user_id = %s
            ORDER BY sgs.generated_at DESC
            LIMIT 10
        """, [user_id])
        
        generations = cursor.fetchall()
        
        return jsonify({
            "success": True,
            "generations": [
                {
                    "generation_id": gen["generation_id"],
                    "generation_type": gen["generation_type"],
                    "meal_plan_name": gen.get("meal_plan_name"),
                    "total_ingredients": gen["total_ingredients"],
                    "auto_matched_count": gen["auto_matched_count"],
                    "confirm_needed_count": gen["confirm_needed_count"],
                    "missing_count": gen["missing_count"],
                    "user_reviewed": bool(gen["user_reviewed"]),
                    "generated_at": gen["generated_at"].isoformat() if gen["generated_at"] else None,
                    "completed_at": gen["completed_at"].isoformat() if gen["completed_at"] else None
                }
                for gen in generations
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting shopping generations: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to get generation history"})

@ingredient_matching_bp.route("/shopping/generation/<int:generation_id>/details", methods=["GET"])
def get_generation_details(generation_id):
    """Get detailed matching results for a specific generation"""
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Verify user owns this generation
        cursor.execute("""
            SELECT * FROM shopping_generation_sessions 
            WHERE generation_id = %s AND user_id = %s
        """, [generation_id, user_id])
        
        generation = cursor.fetchone()
        if not generation:
            return jsonify({"success": False, "message": "Generation not found"})
        
        # Get detailed matching results
        cursor.execute("""
            SELECT gim.*, pi.item_name as pantry_item_name, pi.storage_type
            FROM generation_ingredient_matches gim
            LEFT JOIN pantry_items pi ON gim.pantry_item_id = pi.pantry_item_id
            WHERE gim.generation_id = %s
            ORDER BY gim.ingredient_name
        """, [generation_id])
        
        matches = cursor.fetchall()
        
        return jsonify({
            "success": True,
            "generation": {
                "generation_id": generation["generation_id"],
                "generation_type": generation["generation_type"],
                "total_ingredients": generation["total_ingredients"],
                "auto_matched_count": generation["auto_matched_count"],
                "confirm_needed_count": generation["confirm_needed_count"],
                "missing_count": generation["missing_count"],
                "generated_at": generation["generated_at"].isoformat() if generation["generated_at"] else None
            },
            "matches": [
                {
                    "ingredient_name": match["ingredient_name"],
                    "required_quantity": float(match["required_quantity"]),
                    "required_unit": match["required_unit"],
                    "pantry_item_name": match.get("pantry_item_name"),
                    "pantry_available_quantity": float(match["pantry_available_quantity"]) if match["pantry_available_quantity"] else None,
                    "match_confidence": float(match["match_confidence"]) if match["match_confidence"] else None,
                    "match_type": match["match_type"],
                    "is_user_confirmed": bool(match["is_user_confirmed"]),
                    "needs_to_buy_quantity": float(match["needs_to_buy_quantity"]),
                    "estimated_cost": float(match["estimated_cost"]) if match["estimated_cost"] else None,
                    "storage_type": match.get("storage_type"),
                    "notes": match.get("notes")
                }
                for match in matches
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting generation details: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to get generation details"})

@ingredient_matching_bp.route("/shopping/smart-generate", methods=["POST"])
def generate_smart_shopping_list():
    """
    Generate an enhanced shopping list with fuzzy matching for a meal plan
    
    Request body:
    {
        "meal_plan_session_id": 123,
        "auto_confirm_threshold": 85.0
    }
    
    Response:
    {
        "success": true,
        "generation_id": 456,
        "shopping_items": [...],
        "confirmed_matches": [...],
        "matching_summary": {...},
        "cost_analysis": {...},
        "recommendations": [...]
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    if not data or "meal_plan_session_id" not in data:
        return jsonify({"success": False, "message": "Missing required field: meal_plan_session_id"})
    
    try:
        from src.services.enhanced_shopping_generation import enhanced_shopping_generator
        
        result = enhanced_shopping_generator.generate_smart_shopping_list(
            user_id=user_id,
            meal_plan_session_id=data["meal_plan_session_id"],
            auto_confirm_threshold=float(data.get("auto_confirm_threshold", 85.0))
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating smart shopping list: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to generate smart shopping list"})

@ingredient_matching_bp.route("/shopping/confirm-match", methods=["POST"])
def confirm_ingredient_match():
    """
    Confirm or override an ingredient match
    
    Request body:
    {
        "generation_id": 456,
        "ingredient_name": "chicken breast",
        "pantry_item_id": 789  // null to reject match
    }
    """
    if "user_ID" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    user_id = session["user_ID"]
    data = request.get_json()
    
    print(f'DATA: {data}')
    
    required_fields = ["generation_id", "ingredient_name"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"})
    
    try:
        from src.services.enhanced_shopping_generation import enhanced_shopping_generator
        
        result = enhanced_shopping_generator.confirm_ingredient_match(
            generation_id=data["generation_id"],
            ingredient_name=data["ingredient_name"],
            pantry_item_id=data.get("pantry_item_id"),
            user_id=user_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error confirming ingredient match: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to confirm match"})