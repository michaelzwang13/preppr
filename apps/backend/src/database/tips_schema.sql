-- Insert initial collection of 35 cooking and meal planning tips
INSERT INTO tips (tip_text, tip_category) VALUES
-- Meal Planning Tips
('Plan your meals for the week on Sunday to save time and reduce food waste.', 'meal_planning'),
('Prep ingredients in bulk on weekends - wash, chop, and store vegetables for easy weekday cooking.', 'meal_planning'),
('Keep a running grocery list to avoid forgetting ingredients and reduce multiple store trips.', 'meal_planning'),
('Theme nights like "Meatless Monday" or "Taco Tuesday" can simplify meal planning decisions.', 'meal_planning'),
('Cook double portions and freeze half for busy weeks when you need quick meals.', 'meal_planning'),
('Check your pantry before grocery shopping to avoid buying duplicates and save money.', 'meal_planning'),
('Plan meals around seasonal produce for better flavor and lower costs.', 'meal_planning'),

-- Cooking Tips
('Salt pasta water until it tastes like seawater - this is the only chance to season the pasta itself.', 'cooking'),
('Let meat rest for 5-10 minutes after cooking to redistribute juices for maximum tenderness.', 'cooking'),
('Taste your food as you cook and adjust seasonings - cooking is about constant tasting and adjusting.', 'cooking'),
('Use a meat thermometer to ensure perfect doneness - guessing leads to overcooked or unsafe food.', 'cooking'),
('Mise en place: prepare all ingredients before you start cooking for a smoother cooking process.', 'cooking'),
('Preheat your pan before adding oil to prevent sticking and achieve better searing.', 'cooking'),
('Season food at multiple stages of cooking, not just at the end, for better flavor development.', 'cooking'),
('Don''t overcrowd the pan when searing - this causes steaming instead of browning.', 'cooking'),

-- Kitchen Organization & Storage
('Store herbs like flowers: trim stems and place in water, then cover with a plastic bag.', 'storage'),
('Freeze fresh herbs in olive oil using ice cube trays for convenient flavor additions.', 'storage'),
('Keep your knives sharp - a dull knife is more dangerous and makes cooking harder.', 'storage'),
('Store potatoes and onions separately - they produce gases that spoil each other faster.', 'storage'),
('Organize your fridge with zones: dairy on top shelf, meat on bottom, vegetables in crisper.', 'storage'),
('Use clear containers for leftovers so you can see what needs to be eaten first.', 'storage'),

-- Budget & Shopping Tips
('Shop the perimeter of the grocery store first - that''s where the fresh, whole foods are located.', 'shopping'),
('Buy versatile ingredients that work in multiple dishes to maximize your grocery budget.', 'shopping'),
('Frozen vegetables are just as nutritious as fresh and often more budget-friendly.', 'shopping'),
('Buy meat in bulk when on sale and freeze in meal-sized portions for future use.', 'shopping'),
('Generic/store brands are often 20-40% cheaper than name brands with similar quality.', 'shopping'),

-- Nutrition & Health
('Fill half your plate with vegetables to naturally balance your meals and increase nutrition.', 'nutrition'),
('Drink a glass of water before meals to help with portion control and hydration.', 'nutrition'),
('Choose whole grains over refined grains for better nutrition and sustained energy.', 'nutrition'),
('Eat the rainbow - different colored fruits and vegetables provide different nutrients.', 'nutrition'),
('Include a protein source in every meal to help maintain stable blood sugar levels.', 'nutrition'),

-- Time-Saving Tips
('Use a slow cooker or instant pot for hands-off cooking while you focus on other tasks.', 'time_saving'),
('Batch cook grains and proteins on Sunday to mix and match throughout the week.', 'time_saving'),
('Keep a well-stocked pantry with basics like pasta, rice, canned beans, and spices for quick meals.', 'time_saving'),
('Pre-cut vegetables when you have time and store them for quick weekday cooking.', 'time_saving'),
('One-pot meals save time on both cooking and cleanup - perfect for busy weeknights.', 'time_saving'),

-- Food Safety
('When in doubt, throw it out - food safety is more important than avoiding waste.', 'safety'),
('Use separate cutting boards for raw meat and vegetables to prevent cross-contamination.', 'safety'),
('Cool leftovers quickly by dividing into shallow containers before refrigerating.', 'safety');