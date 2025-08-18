-- Select the database
USE hacknyu25_test;

-- Create the user table (renamed to user_account)
CREATE TABLE user_account (
    user_ID VARCHAR(50),
    email VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(72) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    subscription_tier ENUM('free', 'premium') DEFAULT 'free' NOT NULL,
    subscription_start_date TIMESTAMP NULL,
    subscription_end_date TIMESTAMP NULL,
    subscription_status ENUM('active', 'expired', 'cancelled') DEFAULT 'active' NOT NULL,
    PRIMARY KEY (user_ID)
);

CREATE INDEX idx_subscription_tier ON user_account(subscription_tier);
CREATE INDEX idx_subscription_status ON user_account(subscription_status);
CREATE INDEX idx_subscription_end_date ON user_account(subscription_end_date);

-- Create meal_plan_sessions table for storing meal planning sessions
CREATE TABLE meal_plan_sessions (
    session_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    session_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days INT NOT NULL,
    dietary_preference VARCHAR(50) DEFAULT 'none', -- vegetarian, vegan, keto, paleo, etc.
    budget_limit DECIMAL(10, 2),
    max_cooking_time INT NULL, -- minutes per day
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'completed', 'archived') DEFAULT 'active',
    ai_model_used VARCHAR(50) DEFAULT 'gemini-1.5-flash-latest',
    generation_prompt TEXT NULL, -- store the prompt used for generation
    PRIMARY KEY (session_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    INDEX idx_user_sessions (user_id),
    INDEX idx_session_dates (start_date, end_date),
    INDEX idx_session_status (status)
);

-- Create the shopping_lists table (list metadata)
CREATE TABLE shopping_lists (
    list_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    list_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    meal_plan_session_id INT NULL,
    is_meal_plan_list BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (list_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    FOREIGN KEY (meal_plan_session_id) REFERENCES meal_plan_sessions(session_id) ON DELETE SET NULL,
    INDEX idx_shopping_list_meal_plan (meal_plan_session_id),
    CONSTRAINT unique_meal_plan_shopping_list UNIQUE (meal_plan_session_id, is_meal_plan_list)
);

-- Create the shopping_cart table
CREATE TABLE shopping_cart (
    cart_ID INT AUTO_INCREMENT,
    user_ID VARCHAR(50),
    store_name VARCHAR(25) NOT NULL,
    status ENUM('active', 'purchased') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shopping_list_id INT NULL,
    PRIMARY KEY (cart_ID),                         
    FOREIGN KEY (user_ID) REFERENCES user_account(user_ID),
    FOREIGN KEY (shopping_list_id) REFERENCES shopping_lists(list_id)
);

-- Create the cart_item table
CREATE TABLE cart_item (
    item_ID INT AUTO_INCREMENT,
    cart_ID INT NOT NULL,
    user_ID VARCHAR(50), 
    quantity INT NOT NULL,
    item_name VARCHAR(50) NOT NULL,
    price DECIMAL(10,2),
    upc BIGINT, 
    item_lifetime INT, -- # of DAYS
    image_url VARCHAR(500),
    PRIMARY KEY (item_ID),
    FOREIGN KEY (cart_ID) REFERENCES shopping_cart(cart_ID),
    FOREIGN KEY (user_ID) REFERENCES user_account(user_ID)
);


-- Create the budget table
CREATE TABLE budget (
    budget_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    list_id INT NULL,  -- optional link to a specific shopping list
    allocated_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,  -- planned budget
    total_spent DECIMAL(10, 2) DEFAULT 0.00,               -- running total
    remaining_amount DECIMAL(10, 2) GENERATED ALWAYS AS (allocated_amount - total_spent) STORED,
    alert_threshold DECIMAL(5, 2) DEFAULT 0.80,             -- trigger alert when 80% of budget used
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (budget_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    FOREIGN KEY (list_id) REFERENCES shopping_lists(list_id)
);

-- Create user budget settings table for preferences
CREATE TABLE user_budget_settings (
    user_id VARCHAR(50) PRIMARY KEY,
    monthly_budget DECIMAL(10, 2) DEFAULT 1000.00,
    budget_period ENUM('weekly', 'biweekly', 'monthly') DEFAULT 'monthly',
    alert_threshold DECIMAL(5, 2) DEFAULT 80.00,
    category_limits_enabled BOOLEAN DEFAULT TRUE,
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID)
);

-- Create the shopping_list_items table (individual items)
CREATE TABLE shopping_list_items (
    item_id INT AUTO_INCREMENT,
    list_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    notes TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id),
    FOREIGN KEY (list_id) REFERENCES shopping_lists(list_id) ON DELETE CASCADE
);

CREATE TABLE shopping_list_cart_mapping (
    mapping_id INT AUTO_INCREMENT,
    cart_id INT NOT NULL,
    list_item_id INT NOT NULL,
    cart_item_id INT NULL, -- NULL if not yet added to cart
    is_found BOOLEAN DEFAULT FALSE, -- Whether the item was found and added during shopping
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (mapping_id),
    FOREIGN KEY (cart_id) REFERENCES shopping_cart(cart_ID) ON DELETE CASCADE,
    FOREIGN KEY (list_item_id) REFERENCES shopping_list_items(item_id) ON DELETE CASCADE,
    FOREIGN KEY (cart_item_id) REFERENCES cart_item(item_ID) ON DELETE SET NULL,
    UNIQUE KEY unique_cart_list_item (cart_id, list_item_id)
);

-- Create user_meal_preferences table for storing user preferences (NOT IMPLEMENTED YET)
CREATE TABLE user_meal_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    dietary_restrictions TEXT NULL, -- JSON array of restrictions
    favorite_cuisines TEXT NULL, -- JSON array of cuisines
    disliked_ingredients TEXT NULL, -- JSON array of ingredients to avoid
    cooking_skill_level ENUM('beginner', 'intermediate', 'advanced') DEFAULT 'intermediate',
    preferred_meal_prep_day ENUM('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday') DEFAULT 'sunday',
    max_daily_cooking_time INT DEFAULT 60, -- minutes
    preferred_budget_per_meal DECIMAL(6,2) DEFAULT 8.00,
    kitchen_equipment TEXT NULL, -- JSON array of available equipment
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID)
);

-- Create pantry_items table for tracking user pantry inventory
CREATE TABLE pantry_items (
    pantry_item_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.00,
    unit VARCHAR(20) NOT NULL DEFAULT 'pcs', -- pcs, g, ml, kg, lbs, oz, etc.
    category VARCHAR(50) DEFAULT 'Other', -- Produce, Meat, Grains, Dairy, etc.
    storage_type ENUM('pantry', 'fridge', 'freezer') DEFAULT 'pantry',
    expiration_date DATE NULL, -- can be NULL if no expiry
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_type ENUM('manual', 'shopping_trip') DEFAULT 'manual',
    source_cart_id INT NULL, -- reference to shopping_cart if from trip
    is_ai_predicted_expiry BOOLEAN DEFAULT FALSE, -- if expiry was AI predicted
    notes TEXT NULL,
    is_consumed BOOLEAN DEFAULT FALSE, -- if item has been used up
    PRIMARY KEY (pantry_item_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    FOREIGN KEY (source_cart_id) REFERENCES shopping_cart(cart_ID),
    INDEX idx_user_pantry (user_id),
    INDEX idx_expiration (expiration_date),
    INDEX idx_category (category)
);

-- Create pantry_categories table for standardized categories
CREATE TABLE pantry_categories (
    category_id INT AUTO_INCREMENT,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    default_storage_type ENUM('pantry', 'fridge', 'freezer') DEFAULT 'pantry',
    typical_shelf_life_days INT NULL, -- default shelf life for category
    PRIMARY KEY (category_id)
);

-- Insert common pantry categories
INSERT INTO pantry_categories (category_name, default_storage_type, typical_shelf_life_days) VALUES
('Produce', 'fridge', 7),
('Meat', 'fridge', 3),
('Dairy', 'fridge', 14),
('Grains', 'pantry', 365),
('Canned Goods', 'pantry', 730),
('Frozen Foods', 'freezer', 90),
('Beverages', 'fridge', 30),
('Snacks', 'pantry', 60),
('Condiments', 'pantry', 180),
('Spices', 'pantry', 1095),
('Bread', 'pantry', 5),
('Other', 'pantry', 30),
('Fresh Herbs', 'fridge', 7),
('Oils & Vinegars', 'pantry', 365),
('Baking Supplies', 'pantry', 730);

-- Create pantry_transfer_sessions table to track bulk transfers from shopping trips
CREATE TABLE pantry_transfer_sessions (
    transfer_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    cart_id INT NOT NULL,
    transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items_transferred INT DEFAULT 0,
    notes TEXT NULL,
    PRIMARY KEY (transfer_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    FOREIGN KEY (cart_id) REFERENCES shopping_cart(cart_ID),
    INDEX idx_user_transfers (user_id),
    INDEX idx_cart_transfers (cart_id)
);

-- Create expiry_predictions table to cache AI predictions and improve performance
CREATE TABLE expiry_predictions (
    prediction_id INT AUTO_INCREMENT,
    item_name VARCHAR(100) NOT NULL,
    storage_type ENUM('pantry', 'fridge', 'freezer') NOT NULL,
    predicted_days INT NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 0.5, -- 0.0 to 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_count INT DEFAULT 1, -- how many times this prediction was used
    PRIMARY KEY (prediction_id),
    UNIQUE KEY unique_prediction (item_name, storage_type),
    INDEX idx_item_storage (item_name, storage_type)
);

-- Create tags table to store unique tags per user
CREATE TABLE pantry_tags (
    tag_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    tag_name VARCHAR(50) NOT NULL,
    tag_color VARCHAR(7) DEFAULT '#3B82F6', -- hex color code for UI
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INT DEFAULT 0, -- track how often tag is used
    PRIMARY KEY (tag_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    UNIQUE KEY unique_user_tag (user_id, tag_name), -- prevent duplicate tags per user
    INDEX idx_user_tags (user_id),
    INDEX idx_tag_name (tag_name)
);

-- Create junction table for many-to-many relationship between pantry items and tags
CREATE TABLE pantry_item_tags (
    item_tag_id INT AUTO_INCREMENT,
    pantry_item_id INT NOT NULL,
    tag_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_tag_id),
    FOREIGN KEY (pantry_item_id) REFERENCES pantry_items(pantry_item_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES pantry_tags(tag_id) ON DELETE CASCADE,
    UNIQUE KEY unique_item_tag (pantry_item_id, tag_id), -- prevent duplicate tag assignments
    INDEX idx_item_tags (pantry_item_id),
    INDEX idx_tag_items (tag_id)
);

-- Create monthly meal goals table
CREATE TABLE monthly_meal_goals (
    goal_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    month INT NOT NULL CHECK (month >= 1 AND month <= 12),
    year INT NOT NULL CHECK (year >= 2020 AND year <= 2030),
    meal_plans_goal INT DEFAULT 4 CHECK (meal_plans_goal >= 1 AND meal_plans_goal <= 20),
    meals_completed_goal INT DEFAULT 60 CHECK (meals_completed_goal >= 10 AND meals_completed_goal <= 200),
    new_recipes_goal INT DEFAULT 12 CHECK (new_recipes_goal >= 1 AND new_recipes_goal <= 50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (goal_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    UNIQUE KEY unique_user_month (user_id, month, year),
    INDEX idx_user_goals (user_id),
    INDEX idx_month_year (month, year)
);

-- Create recipe_templates table for storing reusable recipe templates
CREATE TABLE recipe_templates (
    template_id INT AUTO_INCREMENT,
    recipe_name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL,
    prep_time INT NULL, -- minutes
    cook_time INT NULL, -- minutes
    servings INT DEFAULT 1,
    estimated_cost DECIMAL(8,2) NULL,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    calories_per_serving INT NULL,
    instructions TEXT NOT NULL,
    cuisine_type VARCHAR(50) NULL, -- Italian, Mexican, Asian, etc.
    dietary_tags TEXT NULL, -- JSON array of dietary tags (vegetarian, gluten-free, etc.)
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (template_id),
    INDEX idx_recipe_name (recipe_name),
    INDEX idx_meal_type (meal_type),
    INDEX idx_cuisine_type (cuisine_type),
    INDEX idx_difficulty (difficulty)
);

-- Create template_ingredients table for storing ingredients per recipe template
CREATE TABLE template_ingredients (
    ingredient_id INT AUTO_INCREMENT,
    template_id INT NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL, -- cups, tsp, lbs, oz, etc.
    notes VARCHAR(200) NULL, -- "diced", "optional", etc.
    is_pantry_item BOOLEAN DEFAULT FALSE, -- if typically available in user's pantry
    estimated_cost DECIMAL(6,2) NULL,
    PRIMARY KEY (ingredient_id),
    FOREIGN KEY (template_id) REFERENCES recipe_templates(template_id) ON DELETE CASCADE,
    INDEX idx_template_ingredients (template_id),
    INDEX idx_ingredient_name (ingredient_name)
);

-- Create meals table for storing individual meal instances
CREATE TABLE meals (
    meal_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    meal_date DATE NOT NULL,
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL,
    recipe_template_id INT NULL, -- reference to recipe template (if using template)
    session_id INT NULL, -- reference to meal plan session (if part of plan)
    custom_recipe_name VARCHAR(200) NULL, -- if not using template
    custom_instructions TEXT NULL, -- if not using template
    is_completed BOOLEAN DEFAULT FALSE,
    notes TEXT NULL,
    is_locked BOOLEAN DEFAULT FALSE, -- prevents AI from overwriting
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (meal_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    FOREIGN KEY (recipe_template_id) REFERENCES recipe_templates(template_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES meal_plan_sessions(session_id) ON DELETE SET NULL,
    INDEX idx_user_meals (user_id),
    INDEX idx_meal_date (meal_date),
    INDEX idx_meal_type (meal_type),
    INDEX idx_session_meals (session_id),
    INDEX idx_template_meals (recipe_template_id),
    UNIQUE KEY unique_user_meal_slot (user_id, meal_date, meal_type)
);

-- Create session_batch_prep table for storing batch preparation steps per meal plan session
CREATE TABLE session_batch_prep (
    prep_step_id INT AUTO_INCREMENT,
    session_id INT NOT NULL,
    prep_session_name VARCHAR(100) NOT NULL DEFAULT 'Prep Session',
    step_order INT DEFAULT 1,
    description TEXT NOT NULL,
    estimated_time INT NULL, -- estimated time in minutes for this prep step
    equipment_needed TEXT NULL, -- equipment required for this prep step
    tips TEXT NULL, -- helpful tips for this prep step
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (prep_step_id),
    FOREIGN KEY (session_id) REFERENCES meal_plan_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_prep (session_id),
    INDEX idx_step_order (step_order)
);

-- Create session_shopping_lists table for storing consolidated shopping lists per meal plan session
CREATE TABLE session_shopping_lists (
    shopping_item_id INT AUTO_INCREMENT,
    session_id INT NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    total_quantity DECIMAL(10,2) NOT NULL, -- consolidated quantity needed
    unit VARCHAR(20) NOT NULL, -- cups, tsp, lbs, oz, etc.
    estimated_cost DECIMAL(8,2) NULL, -- estimated total cost for this ingredient
    category VARCHAR(50) DEFAULT 'Other', -- Produce, Meat, Dairy, etc. (from categorize_ingredient function)
    meals_using TEXT NULL, -- JSON array of meal_ids that use this ingredient
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (shopping_item_id),
    FOREIGN KEY (session_id) REFERENCES meal_plan_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_shopping (session_id),
    INDEX idx_shopping_category (category),
    INDEX idx_ingredient_shopping (ingredient_name),
    -- Prevent duplicate ingredients per session (consolidate quantities instead)
    UNIQUE KEY unique_session_ingredient (session_id, ingredient_name, unit)
);

-- Create table to store fuzzy matching results to improve performance over time
CREATE TABLE ingredient_pantry_matches (
    match_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    pantry_item_name VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL, -- 0.00 to 100.00
    match_type ENUM('auto', 'confirm', 'missing') NOT NULL,
    is_user_confirmed BOOLEAN DEFAULT FALSE, -- if user manually confirmed this match
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INT DEFAULT 1,
    PRIMARY KEY (match_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    INDEX idx_user_matches (user_id),
    INDEX idx_ingredient_name (ingredient_name),
    INDEX idx_pantry_name (pantry_item_name),
    INDEX idx_confidence (confidence_score),
    INDEX idx_match_type (match_type),
    -- Prevent duplicate matches for same user/ingredient/pantry combination
    UNIQUE KEY unique_user_ingredient_pantry (user_id, ingredient_name, pantry_item_name)
);

-- Create table to store user feedback on fuzzy matches to improve future matching
CREATE TABLE fuzzy_match_feedback (
    feedback_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    suggested_pantry_item VARCHAR(100) NULL, -- what the system suggested
    actual_pantry_item VARCHAR(100) NULL, -- what the user actually selected
    action_taken ENUM('accepted', 'rejected', 'corrected', 'ignored') NOT NULL,
    original_confidence DECIMAL(5,2) NULL,
    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_context VARCHAR(50) NULL, -- meal_plan, shopping_list, etc.
    PRIMARY KEY (feedback_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    INDEX idx_user_feedback (user_id),
    INDEX idx_ingredient_feedback (ingredient_name),
    INDEX idx_action_taken (action_taken),
    INDEX idx_feedback_date (feedback_date)
);

-- Create table to store pre-computed fuzzy match suggestions for better performance
CREATE TABLE ingredient_match_suggestions (
    suggestion_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    suggested_matches TEXT NOT NULL, -- JSON array of {pantry_item_name, confidence_score, match_type}
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL, -- cache expiration (e.g., when pantry changes significantly)
    is_stale BOOLEAN DEFAULT FALSE, -- mark as stale when pantry is updated
    PRIMARY KEY (suggestion_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    INDEX idx_user_suggestions (user_id),
    INDEX idx_ingredient_suggestions (ingredient_name),
    INDEX idx_computed_at (computed_at),
    INDEX idx_expires_at (expires_at),
    -- Prevent duplicate suggestions for same user/ingredient
    UNIQUE KEY unique_user_ingredient_suggestion (user_id, ingredient_name)
);

-- Create table to track shopping list generation sessions with fuzzy matching
CREATE TABLE shopping_generation_sessions (
    generation_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    meal_plan_session_id INT NULL, -- if generated from meal plan
    generation_type ENUM('meal_plan', 'manual', 'recipe') NOT NULL,
    total_ingredients INT DEFAULT 0,
    auto_matched_count INT DEFAULT 0,
    confirm_needed_count INT DEFAULT 0,
    missing_count INT DEFAULT 0,
    user_reviewed BOOLEAN DEFAULT FALSE,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    notes TEXT NULL,
    PRIMARY KEY (generation_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    FOREIGN KEY (meal_plan_session_id) REFERENCES meal_plan_sessions(session_id) ON DELETE SET NULL,
    INDEX idx_user_generations (user_id),
    INDEX idx_generation_type (generation_type),
    INDEX idx_meal_plan_generations (meal_plan_session_id),
    INDEX idx_generated_at (generated_at)
);

-- Create table to store detailed ingredient matching results for each generation session
CREATE TABLE generation_ingredient_matches (
    match_result_id INT AUTO_INCREMENT,
    generation_id INT NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    required_quantity DECIMAL(10,2) NOT NULL,
    required_unit VARCHAR(20) NOT NULL,
    pantry_item_id INT NULL, -- matched pantry item (if any)
    pantry_available_quantity DECIMAL(10,2) NULL,
    match_confidence DECIMAL(5,2) NULL,
    match_type ENUM('auto', 'confirm', 'missing', 'user_override') NOT NULL,
    is_user_confirmed BOOLEAN DEFAULT FALSE,
    needs_to_buy_quantity DECIMAL(10,2) DEFAULT 0.00, -- how much still needed after pantry check
    estimated_cost DECIMAL(8,2) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (match_result_id),
    FOREIGN KEY (generation_id) REFERENCES shopping_generation_sessions(generation_id) ON DELETE CASCADE,
    FOREIGN KEY (pantry_item_id) REFERENCES pantry_items(pantry_item_id) ON DELETE SET NULL,
    INDEX idx_generation_matches (generation_id),
    INDEX idx_ingredient_match_name (ingredient_name),
    INDEX idx_pantry_item_match (pantry_item_id),
    INDEX idx_match_type_result (match_type),
    -- Prevent duplicate ingredient matches per generation
    UNIQUE KEY unique_generation_ingredient (generation_id, ingredient_name, required_unit)
);

-- Create indexes for performance optimization on existing tables
CREATE INDEX idx_pantry_item_name ON pantry_items(item_name);
CREATE INDEX idx_template_ingredient_name ON template_ingredients(ingredient_name);
CREATE INDEX idx_session_shopping_ingredient ON session_shopping_lists(ingredient_name);


-- Add nutrition tracking tables to existing database

-- Create meal_nutrition table to store macro information for each meal
CREATE TABLE meal_nutrition (
    nutrition_id INT AUTO_INCREMENT,
    meal_id INT NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    
    -- Macro nutrients (per serving)
    calories DECIMAL(8,2) NULL,
    protein_g DECIMAL(8,2) NULL,
    carbohydrates_g DECIMAL(8,2) NULL,
    fat_g DECIMAL(8,2) NULL,
    fiber_g DECIMAL(8,2) NULL,
    sugar_g DECIMAL(8,2) NULL,
    sodium_mg DECIMAL(10,2) NULL,
    
    -- Serving information
    servings INT DEFAULT 1,
    serving_size VARCHAR(50) NULL, -- e.g., "1 cup", "1 plate"
    
    -- Data source and confidence
    source_type ENUM('ai_generated', 'user_entered', 'api_lookup') DEFAULT 'ai_generated',
    confidence_score DECIMAL(5,2) NULL, -- 0-100 confidence in accuracy
    ai_model_used VARCHAR(50) NULL, -- track which AI model generated the data
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    notes TEXT NULL,
    
    PRIMARY KEY (nutrition_id),
    FOREIGN KEY (meal_id) REFERENCES meals(meal_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    
    -- Ensure one nutrition record per meal
    UNIQUE KEY unique_meal_nutrition (meal_id),
    
    INDEX idx_user_nutrition (user_id),
    INDEX idx_meal_nutrition (meal_id),
    INDEX idx_nutrition_date (created_at)
);

-- Create daily_nutrition_summary table for tracking daily totals
CREATE TABLE daily_nutrition_summary (
    summary_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    
    -- Daily totals
    total_calories DECIMAL(10,2) DEFAULT 0.00,
    total_protein_g DECIMAL(10,2) DEFAULT 0.00,
    total_carbohydrates_g DECIMAL(10,2) DEFAULT 0.00,
    total_fat_g DECIMAL(10,2) DEFAULT 0.00,
    total_fiber_g DECIMAL(10,2) DEFAULT 0.00,
    total_sugar_g DECIMAL(10,2) DEFAULT 0.00,
    total_sodium_mg DECIMAL(12,2) DEFAULT 0.00,
    
    -- Meal breakdown
    breakfast_calories DECIMAL(8,2) DEFAULT 0.00,
    lunch_calories DECIMAL(8,2) DEFAULT 0.00,
    dinner_calories DECIMAL(8,2) DEFAULT 0.00,
    snack_calories DECIMAL(8,2) DEFAULT 0.00,
    
    -- Tracking
    meals_logged INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (summary_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    
    -- Ensure one summary per user per day
    UNIQUE KEY unique_daily_summary (user_id, date),
    
    INDEX idx_user_daily_nutrition (user_id),
    INDEX idx_nutrition_summary_date (date)
);

-- Create user_nutrition_goals table for tracking user targets
CREATE TABLE user_nutrition_goals (
    goal_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    
    -- Daily targets
    daily_calories_goal DECIMAL(8,2) NULL,
    calories_type ENUM('goal', 'limit') DEFAULT 'goal',
    
    daily_protein_goal_g DECIMAL(8,2) NULL,
    protein_type ENUM('goal', 'limit') DEFAULT 'goal',
    
    daily_carbs_goal_g DECIMAL(8,2) NULL,
    carbs_type ENUM('goal', 'limit') DEFAULT 'goal',

    daily_fat_goal_g DECIMAL(8,2) NULL,
    fat_type ENUM('goal', 'limit') DEFAULT 'limit',
    
    daily_fiber_goal_g DECIMAL(8,2) NULL,
    fiber_type ENUM('goal', 'limit') DEFAULT 'goal',
  
    daily_sodium_limit_mg DECIMAL(10,2) NULL,
    sodium_type ENUM('goal', 'limit') DEFAULT 'limit',
    
    -- Goal settings
    goal_type ENUM('weight_loss', 'weight_gain', 'maintenance', 'muscle_gain', 'custom') DEFAULT 'maintenance',
    activity_level ENUM('sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active') DEFAULT 'moderately_active',
    
    -- User info for calculations
    age INT NULL,
    gender ENUM('male', 'female', 'other') NULL,
    weight_lbs DECIMAL(5,1) NULL,
    height_inches DECIMAL(4,1) NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    PRIMARY KEY (goal_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID),
    
    INDEX idx_user_goals (user_id),
    INDEX idx_active_goals (is_active)
);

CREATE INDEX idx_goal_types ON user_nutrition_goals(calories_type, protein_type, carbs_type, fat_type, fiber_type, sodium_type);

-- Create subscription limits table for tracking usage against limits
CREATE TABLE subscription_limits (
    limit_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    limit_type ENUM('meal_plans_active', 'meal_plans_advance_days', 'pantry_items', 'shopping_lists_per_day', 'saved_recipes', 'upc_scans_per_trip', 'upc_scans_per_week') NOT NULL,
    current_usage INT DEFAULT 0,
    last_reset_date DATE DEFAULT (CURRENT_DATE),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (limit_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    UNIQUE KEY unique_user_limit_type (user_id, limit_type),
    INDEX idx_user_limits (user_id),
    INDEX idx_limit_type (limit_type)
);

-- Create subscription tier features table for configuration
CREATE TABLE subscription_tier_features (
    tier ENUM('free', 'premium') NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    limit_value INT NOT NULL, -- -1 means unlimited
    description TEXT NULL,
    PRIMARY KEY (tier, feature_name),
    INDEX idx_tier (tier),
    INDEX idx_feature (feature_name)
);

-- Insert feature limits for free tier
INSERT INTO subscription_tier_features (tier, feature_name, limit_value, description) VALUES
('free', 'meal_plans_active', 3, 'Maximum number of active meal plans'),
('free', 'meal_plans_advance_days', 7, 'Cannot plan more than 7 days in advance'),
('free', 'pantry_items', 100, 'Maximum pantry ingredients'),
('free', 'shopping_lists_per_day', 1, 'Shopping list generations per day'),
('free', 'saved_recipes', 10, 'Maximum saved recipes'),
('free', 'upc_scans_per_trip', 20, 'UPC scans per shopping trip'),
('free', 'upc_scans_per_week', 50, 'UPC scans per week'),
('free', 'macro_tracking', 0, 'Basic macro tracking (calories + protein only)'),
('free', 'macro_history', 0, 'No macro history view');

-- Insert feature limits for premium tier (unlimited for most)
INSERT INTO subscription_tier_features (tier, feature_name, limit_value, description) VALUES
('premium', 'meal_plans_active', -1, 'Unlimited active meal plans'),
('premium', 'meal_plans_advance_days', -1, 'Plan unlimited days in advance'),
('premium', 'pantry_items', -1, 'Unlimited pantry ingredients'),
('premium', 'shopping_lists_per_day', -1, 'Unlimited shopping list generations'),
('premium', 'saved_recipes', -1, 'Unlimited saved recipes'),
('premium', 'upc_scans_per_trip', -1, 'Unlimited UPC scans per trip'),
('premium', 'upc_scans_per_week', -1, 'Unlimited UPC scans per week'),
('premium', 'macro_tracking', 1, 'Full macro tracking with all nutrients'),
('premium', 'macro_history', 1, 'Full macro history and trends');

-- User Preferences Table
-- Stores various user preferences and settings

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    data_type ENUM('boolean', 'string', 'number', 'json') DEFAULT 'string',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    
    -- Ensure unique preference per user
    UNIQUE KEY unique_user_preference (user_id, preference_key),
    
    -- Index for faster lookups
    INDEX idx_user_preferences (user_id, preference_key)
);

-- Migration for saved recipes feature

-- Create saved_recipes table for recipes users have saved from their meals
CREATE TABLE saved_recipes (
    saved_recipe_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    recipe_name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    meal_type ENUM('breakfast', 'lunch', 'dinner', 'snack') NOT NULL,
    
    -- Recipe details
    prep_time INT NULL, -- minutes
    cook_time INT NULL, -- minutes
    servings INT DEFAULT 1,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    instructions TEXT NOT NULL,
    
    -- Optional details
    cuisine_type VARCHAR(50) NULL,
    notes TEXT NULL,
    estimated_cost DECIMAL(8,2) NULL,
    calories_per_serving INT NULL,
    
    -- Source information
    source_meal_id INT NULL, -- original meal this was saved from (if any)
    source_template_id INT NULL, -- original template (if saved from template)
    
    -- User customizations
    is_favorite BOOLEAN DEFAULT FALSE,
    custom_tags TEXT NULL, -- JSON array of user tags
    times_used INT DEFAULT 0, -- how many times user has cooked this
    last_used_date DATE NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (saved_recipe_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    FOREIGN KEY (source_meal_id) REFERENCES meals(meal_id) ON DELETE SET NULL,
    FOREIGN KEY (source_template_id) REFERENCES recipe_templates(template_id) ON DELETE SET NULL,
    
    INDEX idx_user_saved_recipes (user_id),
    INDEX idx_recipe_name (recipe_name),
    INDEX idx_meal_type (meal_type),
    INDEX idx_favorite (is_favorite),
    INDEX idx_source_meal (source_meal_id),
    INDEX idx_source_template (source_template_id),
    INDEX idx_times_used (times_used DESC),
    INDEX idx_last_used (last_used_date DESC)
);

-- Create saved_recipe_ingredients table for storing ingredients per saved recipe
CREATE TABLE saved_recipe_ingredients (
    ingredient_id INT AUTO_INCREMENT,
    saved_recipe_id INT NOT NULL,
    ingredient_name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    notes VARCHAR(200) NULL,
    estimated_cost DECIMAL(6,2) NULL,
    
    PRIMARY KEY (ingredient_id),
    FOREIGN KEY (saved_recipe_id) REFERENCES saved_recipes(saved_recipe_id) ON DELETE CASCADE,
    
    INDEX idx_saved_recipe_ingredients (saved_recipe_id),
    INDEX idx_ingredient_name (ingredient_name)
);

-- Create recipe_usage_log table to track when recipes are used
CREATE TABLE recipe_usage_log (
    usage_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    saved_recipe_id INT NOT NULL,
    used_for_meal_id INT NULL, -- which meal this recipe was used for
    usage_date DATE NOT NULL,
    usage_context ENUM('meal_plan', 'direct_cook', 'replaced_meal') NOT NULL,
    notes TEXT NULL,
    
    PRIMARY KEY (usage_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    FOREIGN KEY (saved_recipe_id) REFERENCES saved_recipes(saved_recipe_id) ON DELETE CASCADE,
    FOREIGN KEY (used_for_meal_id) REFERENCES meals(meal_id) ON DELETE SET NULL,
    
    INDEX idx_user_usage (user_id),
    INDEX idx_recipe_usage (saved_recipe_id),
    INDEX idx_usage_date (usage_date DESC)
);

-- Create weekly meal goals table
CREATE TABLE weekly_meal_goals (
    goal_id INT AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    week_start_date DATE NOT NULL, -- Monday of the week
    meal_plans_goal INT DEFAULT 2 CHECK (meal_plans_goal >= 1 AND meal_plans_goal <= 10),
    meals_completed_goal INT DEFAULT 15 CHECK (meals_completed_goal >= 5 AND meals_completed_goal <= 50),
    new_recipes_goal INT DEFAULT 3 CHECK (new_recipes_goal >= 1 AND new_recipes_goal <= 15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (goal_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    UNIQUE KEY unique_user_week (user_id, week_start_date),
    INDEX idx_user_week (user_id, week_start_date),
    INDEX idx_week_date (week_start_date)
);

-- Table to store all available tips
CREATE TABLE IF NOT EXISTS tips (
    tip_id INT AUTO_INCREMENT PRIMARY KEY,
    tip_text TEXT NOT NULL,
    tip_category VARCHAR(50) DEFAULT 'general',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_category (tip_category)
);

-- Table to track which tips each user has seen and when
CREATE TABLE IF NOT EXISTS user_tip_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    tip_id INT NOT NULL,
    shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    FOREIGN KEY (tip_id) REFERENCES tips(tip_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_tip (user_id, tip_id),
    INDEX idx_user_shown (user_id, shown_at),
    INDEX idx_shown_date (shown_at)
);