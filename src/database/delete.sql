-- Delete all tables script
-- Run this to clean up the database completely
-- Tables are dropped in dependency order to avoid foreign key constraint errors

USE hacknyu25_test;

-- Disable foreign key checks temporarily to avoid dependency issues
SET FOREIGN_KEY_CHECKS = 0;

-- Drop tables with foreign key dependencies first
DROP TABLE IF EXISTS code_redemption_attempts;
DROP TABLE IF EXISTS code_redemptions;
DROP TABLE IF EXISTS recipe_usage_log;
DROP TABLE IF EXISTS saved_recipe_ingredients;
DROP TABLE IF EXISTS saved_recipes;
DROP TABLE IF EXISTS weekly_meal_goals;
DROP TABLE IF EXISTS user_tip_history;
DROP TABLE IF EXISTS subscription_limits;
DROP TABLE IF EXISTS generation_ingredient_matches;
DROP TABLE IF EXISTS shopping_generation_sessions;
DROP TABLE IF EXISTS ingredient_match_suggestions;
DROP TABLE IF EXISTS fuzzy_match_feedback;
DROP TABLE IF EXISTS ingredient_pantry_matches;
DROP TABLE IF EXISTS session_shopping_lists;
DROP TABLE IF EXISTS session_batch_prep;
DROP TABLE IF EXISTS meals;
DROP TABLE IF EXISTS template_ingredients;
DROP TABLE IF EXISTS monthly_meal_goals;
DROP TABLE IF EXISTS pantry_item_tags;
DROP TABLE IF EXISTS pantry_tags;
DROP TABLE IF EXISTS expiry_predictions;
DROP TABLE IF EXISTS pantry_transfer_sessions;
DROP TABLE IF EXISTS shopping_list_cart_mapping;
DROP TABLE IF EXISTS shopping_list_items;
DROP TABLE IF EXISTS budget;
DROP TABLE IF EXISTS cart_item;
DROP TABLE IF EXISTS meal_nutrition;
DROP TABLE IF EXISTS daily_nutrition_summary;
DROP TABLE IF EXISTS user_nutrition_goals;

-- Drop intermediate tables
DROP TABLE IF EXISTS shopping_lists;
DROP TABLE IF EXISTS shopping_cart;
DROP TABLE IF EXISTS pantry_items;
DROP TABLE IF EXISTS meal_plan_sessions;
DROP TABLE IF EXISTS recipe_templates;
DROP TABLE IF EXISTS promotional_codes;
DROP TABLE IF EXISTS tips;
DROP TABLE IF EXISTS subscription_tier_features;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS user_budget_settings;
DROP TABLE IF EXISTS pantry_categories;
DROP TABLE IF EXISTS user_meal_preferences;

-- Drop main tables last
DROP TABLE IF EXISTS user_account;

-- Drop views if they exist
DROP VIEW IF EXISTS active_promotional_codes;

-- Drop functions if they exist
DROP FUNCTION IF EXISTS is_code_valid_for_user;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Show remaining tables (should be empty)
SHOW TABLES;