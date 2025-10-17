"""
OpenAI API utilities for fallback when Gemini API fails.
"""

import os
import json
from openai import OpenAI

def get_openai_client():
    """Get configured OpenAI client"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def openai_expiry_prediction(item_name, storage_type):
    """
    Use OpenAI to predict expiration days and category for food items.
    Returns dict with 'days' and 'category' or None if failed.
    """
    client = get_openai_client()
    if not client:
        return None
    
    try:
        prompt = f"""You are a food safety expert. I need to know how many days a food item will last and its category.

Item: {item_name}
Storage: {storage_type}

Respond with ONLY a JSON object in this exact format:
{{"days": <number>, "category": "<category_name>"}}

Categories: Produce, Meat, Dairy, Grains, Canned Goods, Frozen Foods, Beverages, Snacks, Condiments, Spices, Bread, Other, Fresh Herbs, Oils & Vinegars, Baking Supplies

Example: {{"days": 7, "category": "Produce"}}

Be realistic and conservative with expiration estimates. Consider the storage type when determining shelf life."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean the response to extract JSON
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end]
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end]
        
        # Parse the JSON response
        result = json.loads(content)
        
        # Validate the response format
        if isinstance(result, dict) and 'days' in result and 'category' in result:
            days = result['days']
            category = result['category']
            
            # Validate days is a reasonable number
            if isinstance(days, (int, float)) and 0 <= days <= 365:
                return {
                    'days': int(days),
                    'category': str(category)
                }
        
        return None
        
    except Exception as e:
        print(f"OpenAI expiry prediction error: {str(e)}")
        return None

def openai_meal_plan_generation(prompt):
    """
    Use OpenAI to generate meal plans when Gemini fails.
    Returns parsed JSON meal plan or None if failed.
    """
    client = get_openai_client()
    if not client:
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o for better meal planning
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean the response to extract JSON
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end]
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end]
        
        # Parse the JSON response
        meal_plan = json.loads(content)
        
        # Basic validation that it's a meal plan
        if isinstance(meal_plan, dict) and 'days' in meal_plan:
            print("DEBUG: OpenAI meal plan generated successfully")
            return meal_plan
        
        return None
        
    except Exception as e:
        print(f"OpenAI meal plan generation error: {str(e)}")
        return None