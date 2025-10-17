USE hacknyu25;

DELIMITER //

-- Add trigger to update fuzzy matching data when pantry items are deleted
CREATE TRIGGER update_fuzzy_matches_on_pantry_delete
    AFTER DELETE ON pantry_items
    FOR EACH ROW
BEGIN
    -- Update any generation_ingredient_matches that referenced this deleted pantry item
    -- Set match_type to 'missing' and needs_to_buy_quantity to full required_quantity
    UPDATE generation_ingredient_matches gim
    INNER JOIN shopping_generation_sessions sgs ON gim.generation_id = sgs.generation_id
    SET 
        gim.match_type = 'missing',
        gim.match_confidence = NULL,
        gim.needs_to_buy_quantity = gim.required_quantity,
        gim.is_user_confirmed = FALSE,
        gim.updated_at = CURRENT_TIMESTAMP
    WHERE gim.pantry_item_id = OLD.pantry_item_id
        AND sgs.user_id = OLD.user_id;
    
    -- Create notifications for affected meal plans
    INSERT INTO pantry_change_notifications (user_id, meal_plan_session_id, change_type, affected_item_name)
    SELECT DISTINCT OLD.user_id, sgs.meal_plan_session_id, 'item_deleted', OLD.item_name
    FROM generation_ingredient_matches gim
    INNER JOIN shopping_generation_sessions sgs ON gim.generation_id = sgs.generation_id
    WHERE gim.pantry_item_id = OLD.pantry_item_id
        AND sgs.meal_plan_session_id IS NOT NULL
        AND sgs.user_id = OLD.user_id;
    
    -- Update the shopping generation session counts
    UPDATE shopping_generation_sessions sgs
    SET 
        sgs.auto_matched_count = (
            SELECT COUNT(*) FROM generation_ingredient_matches gim 
            WHERE gim.generation_id = sgs.generation_id AND gim.match_type = 'auto'
        ),
        sgs.confirm_needed_count = (
            SELECT COUNT(*) FROM generation_ingredient_matches gim 
            WHERE gim.generation_id = sgs.generation_id AND gim.match_type = 'confirm'
        ),
        sgs.missing_count = (
            SELECT COUNT(*) FROM generation_ingredient_matches gim 
            WHERE gim.generation_id = sgs.generation_id AND gim.match_type = 'missing'
        )
    WHERE sgs.user_id = OLD.user_id
        AND EXISTS (
            SELECT 1 FROM generation_ingredient_matches gim 
            WHERE gim.generation_id = sgs.generation_id 
                AND gim.pantry_item_id IS NULL 
                AND gim.match_type = 'missing'
                AND gim.updated_at = CURRENT_TIMESTAMP
        );
END//

DELIMITER ;

-- Add trigger to mark match suggestions as stale when pantry items are modified
DELIMITER //
CREATE TRIGGER pantry_update_stale_suggestions
    AFTER UPDATE ON pantry_items
    FOR EACH ROW
BEGIN
    -- Mark suggestions as stale when pantry item name changes or item is consumed
    IF OLD.item_name != NEW.item_name OR OLD.is_consumed != NEW.is_consumed THEN
        UPDATE ingredient_match_suggestions 
        SET is_stale = TRUE 
        WHERE user_id = NEW.user_id;
    END IF;
END//

CREATE TRIGGER pantry_insert_stale_suggestions
    AFTER INSERT ON pantry_items
    FOR EACH ROW
BEGIN
    -- Mark suggestions as stale when new pantry items are added
    UPDATE ingredient_match_suggestions 
    SET is_stale = TRUE 
    WHERE user_id = NEW.user_id;
END//

CREATE TRIGGER pantry_delete_stale_suggestions
    AFTER DELETE ON pantry_items
    FOR EACH ROW
BEGIN
    -- Mark suggestions as stale when pantry items are deleted
    UPDATE ingredient_match_suggestions 
    SET is_stale = TRUE 
    WHERE user_id = OLD.user_id;
END//
DELIMITER ;