-- Promotional Codes System Migration
-- Run this migration to add promotional code functionality

USE hacknyu25;

-- Create promotional codes table
CREATE TABLE promotional_codes (
    code_id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    code_type ENUM('percentage', 'fixed_amount', 'free_trial', 'upgrade', 'free_month', 'free_year') NOT NULL DEFAULT 'upgrade',
    discount_value DECIMAL(10,2) DEFAULT NULL, -- percentage (0-100) or fixed amount
    subscription_duration_months INT DEFAULT NULL, -- for free_trial, free_month, free_year
    max_uses INT DEFAULT NULL, -- NULL = unlimited uses
    current_uses INT DEFAULT 0,
    max_uses_per_user INT DEFAULT 1, -- how many times one user can use this code
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system', -- admin who created it
    description TEXT,
    minimum_account_age_days INT DEFAULT 0, -- require account to be X days old
    allowed_user_tiers SET('free', 'premium') DEFAULT 'free', -- which tiers can use this code
    
    INDEX idx_code (code),
    INDEX idx_active_expires (is_active, expires_at),
    INDEX idx_type (code_type),
    INDEX idx_created_at (created_at)
);

-- Create code redemptions tracking table
CREATE TABLE code_redemptions (
    redemption_id INT AUTO_INCREMENT PRIMARY KEY,
    code_id INT NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45), -- supports both IPv4 and IPv6
    user_agent TEXT,
    redemption_result ENUM('success', 'failed', 'expired', 'limit_exceeded', 'invalid_user') DEFAULT 'success',
    applied_discount DECIMAL(10,2) DEFAULT NULL, -- actual discount applied
    subscription_granted_until TIMESTAMP NULL, -- if code granted subscription time
    notes TEXT,
    
    FOREIGN KEY (code_id) REFERENCES promotional_codes(code_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_account(user_ID) ON DELETE CASCADE,
    
    INDEX idx_user_redemptions (user_id),
    INDEX idx_code_redemptions (code_id),
    INDEX idx_redemption_date (redeemed_at),
    INDEX idx_redemption_result (redemption_result)
);

-- Create code redemption attempts table (for rate limiting and security)
CREATE TABLE code_redemption_attempts (
    attempt_id INT AUTO_INCREMENT PRIMARY KEY,
    code_attempted VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    ip_address VARCHAR(45) NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    failure_reason VARCHAR(255),
    user_agent TEXT,
    
    INDEX idx_ip_attempts (ip_address, attempted_at),
    INDEX idx_user_attempts (user_id, attempted_at),
    INDEX idx_code_attempts (code_attempted, attempted_at)
);

-- Create a view for active, non-expired codes (for easier querying)
CREATE VIEW active_promotional_codes AS
SELECT 
    pc.*,
    CASE 
        WHEN pc.expires_at IS NULL THEN TRUE
        WHEN pc.expires_at > CURRENT_TIMESTAMP THEN TRUE
        ELSE FALSE
    END as is_valid,
    CASE 
        WHEN pc.max_uses IS NULL THEN TRUE
        WHEN pc.current_uses < pc.max_uses THEN TRUE
        ELSE FALSE
    END as has_uses_remaining
FROM promotional_codes pc
WHERE pc.is_active = TRUE;

-- Create indexes for better performance on the view
CREATE INDEX idx_promo_active_valid ON promotional_codes(is_active, expires_at, current_uses, max_uses);

-- Add some constraints to ensure data integrity
ALTER TABLE promotional_codes 
ADD CONSTRAINT chk_discount_value 
CHECK (
    (code_type IN ('percentage') AND discount_value BETWEEN 0 AND 100) OR
    (code_type IN ('fixed_amount') AND discount_value >= 0) OR
    (code_type NOT IN ('percentage', 'fixed_amount'))
);

ALTER TABLE promotional_codes 
ADD CONSTRAINT chk_usage_limits 
CHECK (max_uses IS NULL OR max_uses >= 0);

ALTER TABLE promotional_codes 
ADD CONSTRAINT chk_duration 
CHECK (subscription_duration_months IS NULL OR subscription_duration_months > 0);

-- Create a function to check if a code is valid for a specific user
DELIMITER //
CREATE FUNCTION is_code_valid_for_user(
    p_code VARCHAR(50),
    p_user_id VARCHAR(50)
) RETURNS BOOLEAN
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_count INT DEFAULT 0;
    DECLARE v_max_uses_per_user INT DEFAULT 1;
    DECLARE v_code_id INT;
    
    -- Get code details
    SELECT code_id, max_uses_per_user INTO v_code_id, v_max_uses_per_user
    FROM active_promotional_codes 
    WHERE code = p_code AND is_valid = TRUE AND has_uses_remaining = TRUE
    LIMIT 1;
    
    -- If code not found or invalid, return false
    IF v_code_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check user usage count for this specific code
    SELECT COUNT(*) INTO v_count
    FROM code_redemptions 
    WHERE code_id = v_code_id 
    AND user_id = p_user_id 
    AND redemption_result = 'success';
    
    -- Return true if user hasn't exceeded their limit for this code
    RETURN v_count < v_max_uses_per_user;
END //
DELIMITER ;

COMMIT;