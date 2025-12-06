-- ============================================================================
-- KUBERA STOCK ANALYSIS CHATBOT - DATABASE INDEXES v2.0
-- Performance optimization indexes
-- ============================================================================

-- Set timezone
SET timezone = 'Asia/Kolkata';

-- ============================================================================
-- USERS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at DESC);

-- ============================================================================
-- OTPs TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_otps_email ON otps(email);
CREATE INDEX IF NOT EXISTS idx_otps_email_type ON otps(email, otp_type);
CREATE INDEX IF NOT EXISTS idx_otps_created_at ON otps(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_otps_is_verified ON otps(is_verified);

-- ============================================================================
-- REFRESH TOKENS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_jti ON refresh_tokens(jti);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked ON refresh_tokens(revoked);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================================
-- CHATS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON chats(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at DESC);

-- ============================================================================
-- MESSAGES TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_response_completed ON messages(response_completed_at);

-- GIN indexes for array columns
CREATE INDEX IF NOT EXISTS idx_messages_mcp_servers ON messages USING GIN(mcp_servers_called);
CREATE INDEX IF NOT EXISTS idx_messages_mcp_tools ON messages USING GIN(mcp_tools_used);

-- ============================================================================
-- USER PORTFOLIO TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_stock_symbol ON user_portfolio(stock_symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_user_stock ON user_portfolio(user_id, stock_symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_exchange ON user_portfolio(exchange);
CREATE INDEX IF NOT EXISTS idx_portfolio_buy_date ON user_portfolio(buy_date DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_last_price_update ON user_portfolio(last_price_update);

-- ============================================================================
-- RATE LIMIT TRACKING TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_user_id ON rate_limit_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_last_prompt ON rate_limit_tracking(last_prompt_at DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_minute_window ON rate_limit_tracking(minute_window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_hour_window ON rate_limit_tracking(hour_window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_24h_window ON rate_limit_tracking(window_24h_start);

-- ============================================================================
-- RATE LIMIT VIOLATIONS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_rate_violations_user_id ON rate_limit_violations(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_violations_chat_id ON rate_limit_violations(chat_id);
CREATE INDEX IF NOT EXISTS idx_rate_violations_type ON rate_limit_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_rate_violations_violated_at ON rate_limit_violations(violated_at DESC);
CREATE INDEX IF NOT EXISTS idx_rate_violations_user_violated ON rate_limit_violations(user_id, violated_at DESC);

-- ============================================================================
-- ADMINS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);
CREATE INDEX IF NOT EXISTS idx_admins_is_super_admin ON admins(is_super_admin);
CREATE INDEX IF NOT EXISTS idx_admins_last_login ON admins(last_login_at DESC);

-- ============================================================================
-- ADMIN ACTIVITY LOGS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_activity_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_type ON admin_activity_logs(target_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_id ON admin_activity_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_performed_at ON admin_activity_logs(performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_performed ON admin_activity_logs(admin_id, performed_at DESC);

-- ============================================================================
-- EMAIL LOGS TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent ON email_logs(sent);
CREATE INDEX IF NOT EXISTS idx_email_logs_failed ON email_logs(failed);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC);

-- ============================================================================
-- EMAIL PREFERENCES TABLE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_email_prefs_user_id ON email_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_email_prefs_portfolio_reports ON email_preferences(portfolio_reports) WHERE portfolio_reports = TRUE;
CREATE INDEX IF NOT EXISTS idx_email_prefs_system_notif ON email_preferences(system_notifications) WHERE system_notifications = TRUE;

-- ============================================================================
-- COMPOSITE INDEXES FOR COMMON QUERIES
-- ============================================================================

-- User chats with messages count
CREATE INDEX IF NOT EXISTS idx_chats_user_total_prompts ON chats(user_id, total_prompts DESC);

-- Portfolio with gain/loss filtering
CREATE INDEX IF NOT EXISTS idx_portfolio_user_gain ON user_portfolio(user_id, gain_loss DESC);

-- Messages with token usage
CREATE INDEX IF NOT EXISTS idx_messages_user_tokens ON messages(user_id, tokens_used);

-- Rate limit violations by type and user
CREATE INDEX IF NOT EXISTS idx_violations_type_user ON rate_limit_violations(violation_type, user_id, violated_at DESC);

-- ============================================================================
-- UPDATE SCHEMA VERSION
-- ============================================================================
INSERT INTO schema_version (version, description) 
VALUES ('v2.0', 'Performance indexes added - 60+ indexes created');

-- ============================================================================
-- ANALYZE TABLES
-- ============================================================================
ANALYZE users;
ANALYZE otps;
ANALYZE refresh_tokens;
ANALYZE chats;
ANALYZE messages;
ANALYZE user_portfolio;
ANALYZE rate_limit_config;
ANALYZE rate_limit_tracking;
ANALYZE rate_limit_violations;
ANALYZE admins;
ANALYZE admin_activity_logs;
ANALYZE email_logs;
ANALYZE email_preferences;
ANALYZE system_status;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE ' INDEXES v2.0 CREATED SUCCESSFULLY';
    RAISE NOTICE ' 60+ indexes created for performance optimization';
    RAISE NOTICE ' Tables analyzed';
END $$;
