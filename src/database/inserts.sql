-- Sample data for meal planning application
USE hacknyu25;

-- Insert sample users
INSERT INTO user_account (user_ID, email, password, first_name, last_name, timezone) VALUES
('user001', 'john.doe@email.com', 'password123', 'John', 'Doe', 'America/New_York'),
('user002', 'jane.smith@email.com', 'password123', 'Jane', 'Smith', 'America/Los_Angeles'),
('user003', 'mike.wilson@email.com', 'password123', 'Mike', 'Wilson', 'America/Chicago'),
('test_user', 'demo@preppr.com', 'demo123', 'Demo', 'User', 'America/New_York');

-- Insert user meal preferences
INSERT INTO user_meal_preferences (user_id, dietary_restrictions, favorite_cuisines, cooking_skill_level, max_daily_cooking_time, preferred_budget_per_meal) VALUES
('user001', '["vegetarian"]', '["Italian", "Mediterranean"]', 'intermediate', 45, 10.00),
('user002', '["gluten-free"]', '["Asian", "Mexican"]', 'advanced', 60, 12.00),
('user003', NULL, '["American", "BBQ"]', 'beginner', 30, 8.00),
('test_user', '["dairy-free"]', '["Italian", "Asian", "Mexican"]', 'intermediate', 50, 15.00);

-- Insert user budget settings
INSERT INTO user_budget_settings (user_id, monthly_budget, budget_period, alert_threshold) VALUES
('user001', 800.00, 'monthly', 75.00),
('user002', 1200.00, 'monthly', 80.00),
('user003', 600.00, 'monthly', 85.00),
('test_user', 1000.00, 'monthly', 80.00);

-- Insert sample pantry tags
INSERT INTO pantry_tags (user_id, tag_name, tag_color, usage_count) VALUES
('test_user', 'Organic', '#10B981', 5),
('test_user', 'Sale Item', '#F59E0B', 3),
('test_user', 'Bulk Purchase', '#8B5CF6', 2),
('test_user', 'Local', '#34D399', 4),
('test_user', 'Quick Use', '#EF4444', 6),
('user001', 'Vegetarian', '#10B981', 8),
('user001', 'Protein', '#F59E0B', 4),
('user002', 'Gluten-Free', '#8B5CF6', 7),
('user002', 'Asian Cooking', '#34D399', 5);

-- Insert sample pantry items
INSERT INTO pantry_items (user_id, item_name, quantity, unit, category, storage_type, expiration_date, source_type, notes) VALUES
-- Demo user pantry
('test_user', 'Whole Wheat Bread', 1, 'loaf', 'Bread', 'pantry', DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'manual', 'Freshly baked from local bakery'),
('test_user', 'Organic Eggs', 12, 'pcs', 'Dairy', 'fridge', DATE_ADD(CURDATE(), INTERVAL 14 DAY), 'manual', 'Free-range organic'),
('test_user', 'Baby Spinach', 5, 'oz', 'Produce', 'fridge', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'manual', 'Triple washed'),
('test_user', 'Chicken Breast', 2, 'lbs', 'Meat', 'fridge', DATE_ADD(CURDATE(), INTERVAL 3 DAY), 'manual', 'Boneless, skinless'),
('test_user', 'Brown Rice', 2, 'lbs', 'Grains', 'pantry', DATE_ADD(CURDATE(), INTERVAL 365 DAY), 'manual', 'Long grain'),
('test_user', 'Olive Oil', 500, 'ml', 'Oils & Vinegars', 'pantry', DATE_ADD(CURDATE(), INTERVAL 180 DAY), 'manual', 'Extra virgin'),
('test_user', 'Canned Tomatoes', 4, 'cans', 'Canned Goods', 'pantry', DATE_ADD(CURDATE(), INTERVAL 730 DAY), 'manual', 'San Marzano style'),
('test_user', 'Greek Yogurt', 32, 'oz', 'Dairy', 'fridge', DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'manual', 'Plain, full-fat'),
('test_user', 'Bananas', 6, 'pcs', 'Produce', 'pantry', DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'manual', 'Perfect for smoothies'),
('test_user', 'Garlic', 1, 'head', 'Produce', 'pantry', DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'manual', 'Fresh bulb'),
-- User001 pantry
('user001', 'Tofu', 14, 'oz', 'Meat', 'fridge', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'manual', 'Extra firm'),
('user001', 'Quinoa', 1, 'lb', 'Grains', 'pantry', DATE_ADD(CURDATE(), INTERVAL 365 DAY), 'manual', 'Tri-color blend'),
('user001', 'Almond Milk', 64, 'fl oz', 'Dairy', 'fridge', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'manual', 'Unsweetened'),
('user001', 'Bell Peppers', 3, 'pcs', 'Produce', 'fridge', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'manual', 'Mixed colors'),
-- User002 pantry
('user002', 'Gluten-Free Pasta', 1, 'box', 'Grains', 'pantry', DATE_ADD(CURDATE(), INTERVAL 365 DAY), 'manual', 'Brown rice pasta'),
('user002', 'Coconut Oil', 16, 'fl oz', 'Oils & Vinegars', 'pantry', DATE_ADD(CURDATE(), INTERVAL 365 DAY), 'manual', 'Unrefined'),
('user002', 'Fresh Ginger', 4, 'oz', 'Produce', 'fridge', DATE_ADD(CURDATE(), INTERVAL 14 DAY), 'manual', 'Organic root');

-- Link pantry items to tags
INSERT INTO pantry_item_tags (pantry_item_id, tag_id) VALUES
-- Demo user tags
(2, 1), -- Organic eggs -> Organic
(3, 1), -- Baby spinach -> Organic
(9, 5), -- Bananas -> Quick Use
(1, 5), -- Bread -> Quick Use
-- User001 tags
(11, 6), -- Tofu -> Vegetarian
(11, 7), -- Tofu -> Protein
(12, 6), -- Quinoa -> Vegetarian
-- User002 tags
(15, 8), -- GF Pasta -> Gluten-Free
(17, 9); -- Ginger -> Asian Cooking

-- Insert sample recipe templates
INSERT INTO recipe_templates (recipe_name, description, meal_type, prep_time, cook_time, servings, estimated_cost, difficulty, calories_per_serving, instructions, cuisine_type, dietary_tags, notes) VALUES
-- Breakfast recipes
('Scrambled Eggs with Spinach', 'Fluffy scrambled eggs with fresh spinach', 'breakfast', 5, 8, 2, 4.50, 'easy', 220, 'Heat oil in non-stick pan. Add spinach and cook until wilted. Beat eggs with salt and pepper. Add to pan and scramble gently until set.', 'American', '["vegetarian", "gluten-free"]', 'Perfect protein-packed breakfast'),
('Overnight Oats', 'Creamy oats with fruit and nuts', 'breakfast', 5, 0, 1, 3.00, 'easy', 350, 'Mix oats, milk, chia seeds, and honey in jar. Add fruit and nuts. Refrigerate overnight. Serve cold.', 'American', '["vegetarian", "vegan-option"]', 'Make ahead for busy mornings'),
('Avocado Toast', 'Smashed avocado on toasted bread', 'breakfast', 10, 3, 2, 5.00, 'easy', 280, 'Toast bread until golden. Mash avocado with lime juice, salt, and pepper. Spread on toast. Top with tomatoes and herbs.', 'American', '["vegetarian", "vegan"]', 'Add an egg for extra protein'),

-- Lunch recipes
('Mediterranean Quinoa Bowl', 'Nutritious bowl with quinoa and vegetables', 'lunch', 15, 20, 2, 8.00, 'medium', 420, 'Cook quinoa according to package directions. Roast vegetables with olive oil. Combine with quinoa, add feta and herbs. Drizzle with lemon vinaigrette.', 'Mediterranean', '["vegetarian", "gluten-free"]', 'Great meal prep option'),
('Chicken Caesar Salad', 'Classic Caesar with grilled chicken', 'lunch', 20, 15, 2, 9.50, 'medium', 380, 'Season and grill chicken breast. Prepare Caesar dressing. Toss romaine with dressing, add chicken, croutons, and parmesan.', 'Italian', '["high-protein"]', 'Make your own croutons for best flavor'),
('Asian Lettuce Wraps', 'Fresh lettuce wraps with seasoned protein', 'lunch', 25, 10, 4, 7.00, 'medium', 180, 'Cook ground chicken with Asian seasonings. Prepare sauce with soy sauce, sesame oil, and ginger. Serve in lettuce cups with toppings.', 'Asian', '["gluten-free-option", "low-carb"]', 'Use ground turkey for lighter option'),

-- Dinner recipes
('Spaghetti Carbonara', 'Classic Italian pasta with eggs and cheese', 'dinner', 10, 15, 4, 6.50, 'medium', 480, 'Cook pasta until al dente. In pan, cook pancetta until crispy. Beat eggs with parmesan. Toss hot pasta with egg mixture and pancetta. Season with pepper.', 'Italian', '[""]', 'The key is to work quickly with hot pasta'),
('Grilled Salmon with Vegetables', 'Herb-crusted salmon with roasted vegetables', 'dinner', 15, 25, 2, 14.00, 'medium', 420, 'Season salmon with herbs and lemon. Grill 4-5 minutes per side. Roast vegetables with olive oil and seasonings. Serve together.', 'American', '["high-protein", "gluten-free"]', 'Don\'t overcook the salmon'),
('Vegetable Stir Fry', 'Colorful mixed vegetables in savory sauce', 'dinner', 15, 8, 3, 5.50, 'easy', 240, 'Heat oil in wok. Add garlic and ginger. Stir-fry harder vegetables first, then softer ones. Add sauce and toss until coated.', 'Asian', '["vegetarian", "vegan", "gluten-free-option"]', 'Serve over rice or noodles'),

-- Snack recipes
('Hummus with Vegetables', 'Creamy hummus with fresh vegetable sticks', 'snack', 10, 0, 4, 4.00, 'easy', 150, 'Blend chickpeas, tahini, lemon juice, garlic, and olive oil until smooth. Season with salt and pepper. Serve with cut vegetables.', 'Mediterranean', '["vegan", "gluten-free"]', 'Store hummus covered in refrigerator');

-- Insert ingredients for the recipes
INSERT INTO template_ingredients (template_id, ingredient_name, quantity, unit, notes, estimated_cost) VALUES
-- Scrambled Eggs with Spinach (template_id: 1)
(1, 'eggs', 4, 'pcs', 'large', 1.00),
(1, 'fresh spinach', 2, 'cups', 'washed', 2.00),
(1, 'olive oil', 1, 'tbsp', '', 0.25),
(1, 'salt', 0.25, 'tsp', 'to taste', 0.05),
(1, 'black pepper', 0.125, 'tsp', 'freshly ground', 0.05),

-- Overnight Oats (template_id: 2)
(2, 'rolled oats', 0.5, 'cup', 'old-fashioned', 0.50),
(2, 'milk', 0.5, 'cup', 'dairy or plant-based', 0.75),
(2, 'chia seeds', 1, 'tbsp', '', 0.50),
(2, 'honey', 1, 'tbsp', 'or maple syrup', 0.25),
(2, 'mixed berries', 0.25, 'cup', 'fresh or frozen', 1.00),

-- Mediterranean Quinoa Bowl (template_id: 4)
(4, 'quinoa', 1, 'cup', 'rinsed', 2.00),
(4, 'cucumber', 1, 'pc', 'diced', 1.00),
(4, 'cherry tomatoes', 1, 'cup', 'halved', 1.50),
(4, 'red onion', 0.25, 'cup', 'diced', 0.50),
(4, 'feta cheese', 0.5, 'cup', 'crumbled', 2.00),
(4, 'olive oil', 3, 'tbsp', 'extra virgin', 0.75),
(4, 'lemon juice', 2, 'tbsp', 'fresh', 0.25),

-- Spaghetti Carbonara (template_id: 7)
(7, 'spaghetti', 1, 'lb', '', 1.50),
(7, 'pancetta', 4, 'oz', 'diced', 3.00),
(7, 'eggs', 3, 'pcs', 'large, room temperature', 0.75),
(7, 'parmesan cheese', 1, 'cup', 'grated', 2.00),
(7, 'black pepper', 0.5, 'tsp', 'freshly ground', 0.05),

-- Grilled Salmon (template_id: 8)
(8, 'salmon fillets', 2, 'pcs', '6 oz each', 8.00),
(8, 'asparagus', 1, 'lb', 'trimmed', 2.00),
(8, 'bell peppers', 2, 'pcs', 'sliced', 2.00),
(8, 'olive oil', 2, 'tbsp', '', 0.50),
(8, 'lemon', 1, 'pc', 'juiced and zested', 0.50),
(8, 'dried herbs', 1, 'tsp', 'mixed', 0.25);

-- Insert sample meal plan sessions
INSERT INTO meal_plan_sessions (user_id, session_name, start_date, end_date, total_days, dietary_preference, max_cooking_time, status, generation_prompt) VALUES
('test_user', 'Weekly Meal Plan - March 2025', '2025-03-10', '2025-03-16', 7, 'balanced', 45, 'active', 'Generated a balanced 7-day meal plan with 45 minutes max cooking time per day'),
('user001', 'Vegetarian Week', '2025-03-08', '2025-03-14', 7, 'vegetarian', 30, 'active', 'Vegetarian meal plan focusing on quick 30-minute meals'),
('test_user', 'Quick & Easy Plan', '2025-02-24', '2025-02-28', 5, 'none', 30, 'completed', 'Quick 5-day meal plan for busy week with 30 minutes max cooking time');

-- Insert sample meals
INSERT INTO meals (user_id, meal_date, meal_type, recipe_template_id, session_id, is_completed, notes) VALUES
-- Demo user's current week meals
('test_user', '2025-03-10', 'breakfast', 1, 1, FALSE, 'Using spinach from pantry'),
('test_user', '2025-03-10', 'lunch', 4, 1, FALSE, ''),
('test_user', '2025-03-10', 'dinner', 8, 1, FALSE, 'Salmon from freezer'),
('test_user', '2025-03-11', 'breakfast', 2, 1, FALSE, ''),
('test_user', '2025-03-11', 'lunch', 5, 1, FALSE, ''),
('test_user', '2025-03-11', 'dinner', 9, 1, FALSE, ''),
('test_user', '2025-03-12', 'breakfast', 3, 1, FALSE, ''),
('test_user', '2025-03-12', 'lunch', 6, 1, FALSE, ''),
('test_user', '2025-03-12', 'dinner', 7, 1, FALSE, ''),

-- User001's vegetarian meals
('user001', '2025-03-08', 'breakfast', 2, 2, TRUE, 'Made with almond milk'),
('user001', '2025-03-08', 'lunch', 4, 2, TRUE, 'Extra quinoa from pantry'),
('user001', '2025-03-08', 'dinner', 9, 2, FALSE, 'Adding tofu for protein'),
('user001', '2025-03-09', 'breakfast', 3, 2, FALSE, ''),
('user001', '2025-03-09', 'lunch', 4, 2, FALSE, ''),

-- Some standalone meals not part of meal plans
('test_user', '2025-03-05', 'breakfast', 1, NULL, TRUE, 'Quick breakfast before work'),
('user002', '2025-03-07', 'lunch', 6, NULL, TRUE, 'Used gluten-free sauce');

-- Insert sample batch prep steps
INSERT INTO session_batch_prep (session_id, prep_session_name, step_order, description, estimated_time, equipment_needed, tips) VALUES
(1, 'Sunday Prep Session', 1, 'Wash and chop all vegetables for the week', 30, 'Sharp knife, cutting board, storage containers', 'Store in airtight containers with paper towels to absorb moisture'),
(1, 'Sunday Prep Session', 2, 'Cook quinoa and brown rice in bulk', 25, 'Rice cooker or large pot', 'Make extra and freeze portions for future use'),
(1, 'Sunday Prep Session', 3, 'Prep protein marinades and season meats', 15, 'Mixing bowls, measuring spoons', 'Marinate overnight for best flavor'),
(2, 'Weekend Vegetarian Prep', 1, 'Prepare large batch of hummus and cut vegetables', 20, 'Food processor, storage containers', 'Hummus keeps for up to a week in refrigerator'),
(2, 'Weekend Vegetarian Prep', 2, 'Cook and portion tofu for multiple meals', 25, 'Large pan, storage containers', 'Press tofu first to remove excess water');

-- Insert sample shopping list items for meal plan sessions
INSERT INTO session_shopping_lists (session_id, ingredient_name, total_quantity, unit, estimated_cost, category, meals_using) VALUES
-- Shopping list for test_user's meal plan (session_id: 1)
(1, 'salmon fillets', 4, 'pcs', 16.00, 'Meat & Seafood', '[1,3]'),
(1, 'asparagus', 2, 'lbs', 4.00, 'Produce', '[3,6]'),
(1, 'cherry tomatoes', 2, 'cups', 3.00, 'Produce', '[2,4,7]'),
(1, 'pancetta', 4, 'oz', 3.00, 'Meat & Seafood', '[9]'),
(1, 'parmesan cheese', 1.5, 'cups', 3.00, 'Dairy', '[7,9]'),
(1, 'mixed berries', 1, 'cup', 4.00, 'Produce', '[4,5]'),

-- Shopping list for user001's vegetarian plan (session_id: 2)
(2, 'extra firm tofu', 28, 'oz', 6.00, 'Meat & Seafood', '[10,13]'),
(2, 'avocados', 4, 'pcs', 4.00, 'Produce', '[13,14]'),
(2, 'whole grain bread', 1, 'loaf', 3.50, 'Grains', '[13]'),
(2, 'tahini', 1, 'jar', 5.00, 'Condiments', '[11]'),
(2, 'chickpeas', 2, 'cans', 2.00, 'Canned Goods', '[11]');

-- Insert sample shopping lists (for shopping trip functionality)
INSERT INTO shopping_lists (user_id, list_name, description, is_active) VALUES
('test_user', 'Weekly Groceries', 'Regular weekly shopping trip', TRUE),
('test_user', 'Meal Plan Shopping', 'Ingredients for this week\'s meal plan', TRUE),
('user001', 'Vegetarian Essentials', 'Stock up on vegetarian proteins and produce', FALSE),
('user002', 'Gluten-Free Pantry', 'Restock gluten-free staples', TRUE);

-- Insert shopping list items
INSERT INTO shopping_list_items (list_id, item_name, quantity, notes, is_completed) VALUES
-- Demo user's weekly groceries
(1, 'Bananas', 6, 'For smoothies and snacks', FALSE),
(1, 'Greek Yogurt', 2, 'Large containers', FALSE),
(1, 'Olive Oil', 1, 'Extra virgin', TRUE),
(1, 'Fresh Basil', 1, 'For pasta dishes', FALSE),
(1, 'Chicken Thighs', 2, 'Family pack', FALSE),

-- Demo user's meal plan shopping
(2, 'Salmon Fillets', 4, '6 oz each', FALSE),
(2, 'Asparagus', 2, 'pounds', FALSE),
(2, 'Cherry Tomatoes', 1, 'container', TRUE),
(2, 'Pancetta', 1, '4 oz package', FALSE),

-- User002's gluten-free items
(4, 'Gluten-Free Bread', 2, 'Whole grain if available', FALSE),
(4, 'Rice Flour', 1, 'For baking', FALSE),
(4, 'Gluten-Free Pasta', 3, 'Different shapes', TRUE);

-- Insert sample shopping carts (completed trips)
INSERT INTO shopping_cart (user_ID, store_name, status, shopping_list_id) VALUES
('test_user', 'Whole Foods', 'purchased', 1),
('test_user', 'Trader Joes', 'purchased', NULL),
('user001', 'Safeway', 'purchased', 3);

-- Insert cart items from shopping trips
INSERT INTO cart_item (cart_ID, user_ID, quantity, item_name, price, item_lifetime) VALUES
-- Demo user's Whole Foods trip
(1, 'test_user', 6, 'Organic Bananas', 3.99, 5),
(1, 'test_user', 2, 'Greek Yogurt', 8.98, 10),
(1, 'test_user', 1, 'Extra Virgin Olive Oil', 12.99, 365),
(1, 'test_user', 1, 'Fresh Basil', 2.49, 7),
(1, 'test_user', 2, 'Organic Chicken Thighs', 14.50, 3),

-- Demo user's Trader Joe's trip  
(2, 'test_user', 4, 'Salmon Fillets', 19.96, 2),
(2, 'test_user', 1, 'Asparagus Bundle', 3.99, 7),
(2, 'test_user', 1, 'Cherry Tomatoes', 2.99, 7),

-- User001's Safeway trip
(3, 'user001', 2, 'Extra Firm Tofu', 5.98, 7),
(3, 'user001', 1, 'Quinoa', 4.99, 365),
(3, 'user001', 1, 'Unsweetened Almond Milk', 3.49, 7);

-- Insert monthly meal goals
INSERT INTO monthly_meal_goals (user_id, month, year, meal_plans_goal, meals_completed_goal, new_recipes_goal) VALUES
('test_user', 3, 2025, 4, 80, 15),
('test_user', 2, 2025, 3, 60, 12),
('user001', 3, 2025, 2, 50, 10),
('user002', 3, 2025, 3, 70, 8);

-- Insert expiry predictions to help with AI predictions
INSERT INTO expiry_predictions (item_name, storage_type, predicted_days, confidence_score, used_count) VALUES
('bananas', 'pantry', 5, 0.90, 15),
('milk', 'fridge', 7, 0.85, 23),
('bread', 'pantry', 5, 0.80, 18),
('eggs', 'fridge', 14, 0.95, 12),
('chicken breast', 'fridge', 3, 0.90, 8),
('spinach', 'fridge', 7, 0.75, 10),
('yogurt', 'fridge', 10, 0.85, 16),
('cheese', 'fridge', 21, 0.80, 7),
('apples', 'fridge', 14, 0.85, 11),
('carrots', 'fridge', 21, 0.90, 9);