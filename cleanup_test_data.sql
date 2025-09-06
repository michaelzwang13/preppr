-- Cleanup script for removing test data from hacknyu25_test database
-- Run this when test data accumulates and interferes with subscription limits

USE hacknyu25_test;

-- Disable foreign key checks temporarily to avoid constraint issues
SET FOREIGN_KEY_CHECKS = 0;

-- Delete test shopping cart items first (references shopping_lists)
DELETE FROM shopping_cart WHERE user_id = 'test_user';

-- Delete test shopping cart items that reference shopping lists owned by test users
DELETE FROM shopping_cart WHERE shopping_list_id IN (
    SELECT list_id FROM shopping_lists WHERE user_id = 'test_user'
);

-- Delete test shopping list items
DELETE FROM shopping_list_items WHERE list_id IN (
    SELECT list_id FROM shopping_lists WHERE user_id = 'test_user'
);

-- Now delete test shopping lists
DELETE FROM shopping_lists WHERE user_id = 'test_user';

-- Delete test saved recipe ingredients first
DELETE FROM saved_recipe_ingredients WHERE saved_recipe_id IN (
    SELECT saved_recipe_id FROM saved_recipes WHERE user_id = 'test_user'
);

-- Delete test saved recipes
DELETE FROM saved_recipes WHERE user_id = 'test_user';

-- Delete test meal ingredients first
DELETE FROM template_ingredients WHERE template_id IN (
    SELECT meal_id FROM meals WHERE user_id = 'test_user'
);

-- Delete test meals
DELETE FROM meals WHERE user_id = 'test_user';

-- Delete test pantry items
DELETE FROM pantry_items WHERE user_id = 'test_user';

-- Reset usage tracking for test users (if table exists)
-- DELETE FROM user_usage_tracking WHERE user_id IN ('test_user', 'premium_user');

-- Clean up any test users that might have been created during tests
DELETE FROM user_account WHERE user_ID IN (
    'test_user_temp', 'cart_user', 'other_user', 'temp_user'
);

-- Reset any subscription tracking for test users
UPDATE user_account SET 
    subscription_tier = 'free',
    subscription_status = 'active',
    subscription_end_date = NULL
WHERE user_ID IN ('test_user', 'premium_user');

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Show remaining counts for verification
SELECT 'Shopping Lists' as table_name, COUNT(*) as count FROM shopping_lists WHERE user_id = 'test_user'
UNION ALL
SELECT 'Saved Recipes', COUNT(*) FROM saved_recipes WHERE user_id = 'test_user'  
UNION ALL
SELECT 'Meals', COUNT(*) FROM meals WHERE user_id = 'test_user'
UNION ALL
SELECT 'Pantry Items', COUNT(*) FROM pantry_items WHERE user_id = 'test_user'
UNION ALL
SELECT 'Shopping Cart Items', COUNT(*) FROM shopping_cart WHERE user_id = 'test_user';

