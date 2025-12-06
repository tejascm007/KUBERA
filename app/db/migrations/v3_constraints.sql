-- ============================================================================
-- KUBERA STOCK ANALYSIS CHATBOT - DATABASE CONSTRAINTS v3.0
-- Foreign keys, check constraints, and data integrity rules
-- ============================================================================

-- Set timezone
SET timezone = 'Asia/Kolkata';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS
-- ============================================================================

-- REFRESH TOKENS -> USERS
ALTER TABLE refresh_tokens
ADD CONSTRAINT fk_refresh_tokens_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- CHATS -> USERS
ALTER TABLE chats
ADD CONSTRAINT fk_chats_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- MESSAGES -> CHATS
ALTER TABLE messages
ADD CONSTRAINT fk_messages_chat
FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
ON DELETE CASCADE;

-- MESSAGES -> USERS
ALTER TABLE messages
ADD CONSTRAINT fk_messages_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- USER PORTFOLIO -> USERS
ALTER TABLE user_portfolio
ADD CONSTRAINT fk_portfolio_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- RATE LIMIT TRACKING -> USERS
ALTER TABLE rate_limit_tracking
ADD CONSTRAINT fk_rate_tracking_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- RATE LIMIT VIOLATIONS -> USERS
ALTER TABLE rate_limit_violations
ADD CONSTRAINT fk_rate_violations_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- RATE LIMIT VIOLATIONS -> CHATS (optional, can be NULL)
ALTER TABLE rate_limit_violations
ADD CONSTRAINT fk_rate_violations_chat
FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
ON DELETE SET NULL;

-- ADMIN ACTIVITY LOGS -> ADMINS
ALTER TABLE admin_activity_logs
ADD CONSTRAINT fk_admin_logs_admin
FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
ON DELETE CASCADE;

-- EMAIL PREFERENCES -> USERS
ALTER TABLE email_preferences
ADD CONSTRAINT fk_email_prefs_user
FOREIGN KEY (user_id) REFERENCES users(user_id)
ON DELETE CASCADE;

-- ============================================================================
-- CHECK CONSTRAINTS
-- ============================================================================

-- USERS: Email format validation
ALTER TABLE users
ADD CONSTRAINT check_users_email_format
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- USERS: Username length
ALTER TABLE users
ADD CONSTRAINT check_users_username_length
CHECK (LENGTH(username) >= 3 AND LENGTH(username) <= 100);

-- USERS: Phone format (optional, Indian format)
ALTER TABLE users
ADD CONSTRAINT check_users_phone_format
CHECK (phone IS NULL OR phone ~* '^\+?[0-9]{10,15}$');

-- OTPS: Attempt count limit
ALTER TABLE otps
ADD CONSTRAINT check_otps_attempt_count
CHECK (attempt_count >= 0 AND attempt_count <= 10);

-- CHATS: Total prompts non-negative
ALTER TABLE chats
ADD CONSTRAINT check_chats_total_prompts
CHECK (total_prompts >= 0);

-- MESSAGES: Tokens used non-negative
ALTER TABLE messages
ADD CONSTRAINT check_messages_tokens_used
CHECK (tokens_used IS NULL OR tokens_used >= 0);

-- MESSAGES: Processing time non-negative
ALTER TABLE messages
ADD CONSTRAINT check_messages_processing_time
CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0);

-- MESSAGES: Charts generated non-negative
ALTER TABLE messages
ADD CONSTRAINT check_messages_charts_generated
CHECK (charts_generated >= 0);

-- USER PORTFOLIO: Quantity positive
ALTER TABLE user_portfolio
ADD CONSTRAINT check_portfolio_quantity
CHECK (quantity > 0);

-- USER PORTFOLIO: Buy price positive
ALTER TABLE user_portfolio
ADD CONSTRAINT check_portfolio_buy_price
CHECK (buy_price > 0);

-- USER PORTFOLIO: Current price positive (if not NULL)
ALTER TABLE user_portfolio
ADD CONSTRAINT check_portfolio_current_price
CHECK (current_price IS NULL OR current_price > 0);

-- USER PORTFOLIO: Buy date not in future
ALTER TABLE user_portfolio
ADD CONSTRAINT check_portfolio_buy_date
CHECK (buy_date <= CURRENT_DATE);

-- RATE LIMIT CONFIG: Limits positive
ALTER TABLE rate_limit_config
ADD CONSTRAINT check_rate_config_burst_limit
CHECK (burst_limit_per_minute > 0);

ALTER TABLE rate_limit_config
ADD CONSTRAINT check_rate_config_per_chat_limit
CHECK (per_chat_limit > 0);

ALTER TABLE rate_limit_config
ADD CONSTRAINT check_rate_config_per_hour_limit
CHECK (per_hour_limit > 0);

ALTER TABLE rate_limit_config
ADD CONSTRAINT check_rate_config_per_day_limit
CHECK (per_day_limit > 0);

-- RATE LIMIT TRACKING: Counters non-negative
ALTER TABLE rate_limit_tracking
ADD CONSTRAINT check_rate_tracking_minute_counter
CHECK (prompts_current_minute >= 0);

ALTER TABLE rate_limit_tracking
ADD CONSTRAINT check_rate_tracking_hour_counter
CHECK (prompts_current_hour >= 0);

ALTER TABLE rate_limit_tracking
ADD CONSTRAINT check_rate_tracking_24h_counter
CHECK (prompts_current_24h >= 0);

-- RATE LIMIT VIOLATIONS: Limit and usage positive
ALTER TABLE rate_limit_violations
ADD CONSTRAINT check_rate_violations_limit_value
CHECK (limit_value > 0);

ALTER TABLE rate_limit_violations
ADD CONSTRAINT check_rate_violations_prompts_used
CHECK (prompts_used >= 0);

-- SYSTEM STATUS: Portfolio report day of week (0-6, Monday-Sunday)
ALTER TABLE system_status
ADD CONSTRAINT check_system_report_day_weekly
CHECK (portfolio_report_send_day_weekly >= 0 AND portfolio_report_send_day_weekly <= 6);

-- SYSTEM STATUS: Portfolio report day of month (1-31)
ALTER TABLE system_status
ADD CONSTRAINT check_system_report_day_monthly
CHECK (portfolio_report_send_day_monthly >= 1 AND portfolio_report_send_day_monthly <= 31);

-- ============================================================================
-- UNIQUE CONSTRAINTS
-- ============================================================================

-- USER PORTFOLIO: One entry per user per stock
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_user_stock
ON user_portfolio(user_id, stock_symbol);

-- RATE LIMIT TRACKING: One tracking record per user
-- (Already enforced by UNIQUE constraint on user_id column)

-- EMAIL PREFERENCES: One preference record per user
-- (Already enforced by UNIQUE constraint on user_id column)

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT COLUMNS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at column
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_chats_updated_at
    BEFORE UPDATE ON chats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_portfolio_updated_at
    BEFORE UPDATE ON user_portfolio
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_config_updated_at
    BEFORE UPDATE ON rate_limit_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_tracking_updated_at
    BEFORE UPDATE ON rate_limit_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_admins_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_email_prefs_updated_at
    BEFORE UPDATE ON email_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_system_status_updated_at
    BEFORE UPDATE ON system_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRIGGERS FOR CHAT STATISTICS
-- ============================================================================

-- Function to update chat statistics on new message
CREATE OR REPLACE FUNCTION update_chat_statistics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chats
    SET 
        total_prompts = total_prompts + 1,
        last_message_at = NEW.created_at,
        updated_at = CURRENT_TIMESTAMP
    WHERE chat_id = NEW.chat_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to increment chat prompt count on new message
CREATE TRIGGER trigger_messages_update_chat_stats
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_statistics();

-- ============================================================================
-- UPDATE SCHEMA VERSION
-- ============================================================================
INSERT INTO schema_version (version, description) 
VALUES ('v3.0', 'Foreign keys, constraints, and triggers added');

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'CONSTRAINTS v3.0 CREATED SUCCESSFULLY';
    RAISE NOTICE 'Foreign key constraints added';
    RAISE NOTICE 'Check constraints added';
    RAISE NOTICE 'Triggers created';
    RAISE NOTICE 'Database integrity enforced';
    RAISE NOTICE '';
    RAISE NOTICE 'DATABASE SETUP COMPLETE!';
    RAISE NOTICE 'Total tables: 15';
    RAISE NOTICE 'Total foreign keys: 10';
    RAISE NOTICE 'Total check constraints: 25+';
    RAISE NOTICE 'Total triggers: 9';
END $$;
