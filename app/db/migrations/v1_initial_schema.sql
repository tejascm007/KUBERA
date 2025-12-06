-- ============================================================================
-- KUBERA STOCK ANALYSIS CHATBOT - DATABASE SCHEMA v1.0
-- Initial Schema Creation - 15 Tables
-- Database: PostgreSQL 14+
-- Timezone: Asia/Kolkata (IST)
-- ============================================================================

-- Set timezone
SET timezone = 'Asia/Kolkata';

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE 1: USERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    
    -- Profile preferences
    investment_style VARCHAR(50),
    risk_tolerance VARCHAR(50),
    interested_sectors TEXT[],
    
    -- Account status
    account_status VARCHAR(20) DEFAULT 'active' CHECK (account_status IN ('active', 'deactivated', 'suspended')),
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE users IS 'User accounts and profiles';
COMMENT ON COLUMN users.account_status IS 'active, deactivated, suspended';
COMMENT ON COLUMN users.investment_style IS 'value, growth, dividend, swing';
COMMENT ON COLUMN users.risk_tolerance IS 'low, medium, high';

-- ============================================================================
-- TABLE 2: OTPs
-- ============================================================================
CREATE TABLE IF NOT EXISTS otps (
    otp_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    otp_type VARCHAR(50) NOT NULL,
    
    -- Verification tracking
    is_verified BOOLEAN DEFAULT FALSE,
    attempt_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE otps IS 'OTP verification for registration, password reset, admin login';
COMMENT ON COLUMN otps.otp_type IS 'registration, password_reset, admin_login';

-- ============================================================================
-- TABLE 3: REFRESH TOKENS
-- ============================================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    jti VARCHAR(255) UNIQUE NOT NULL,
    
    -- Token status
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for session management';

-- ============================================================================
-- TABLE 4: CHATS
-- ============================================================================
CREATE TABLE IF NOT EXISTS chats (
    chat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    chat_name VARCHAR(255) DEFAULT 'New Chat',
    
    -- Chat statistics
    total_prompts INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE chats IS 'User chat sessions';

-- ============================================================================
-- TABLE 5: MESSAGES
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Message content
    user_message TEXT NOT NULL,
    assistant_response TEXT,
    
    -- Metadata
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    mcp_servers_called TEXT[],
    mcp_tools_used TEXT[],
    charts_generated INTEGER DEFAULT 0,
    llm_model VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_completed_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE messages IS 'Chat messages with LLM responses and metadata';

-- ============================================================================
-- TABLE 6: USER PORTFOLIO
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_portfolio (
    portfolio_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    
    -- Stock details
    stock_symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(10) DEFAULT 'NSE',
    quantity DECIMAL(15, 4) NOT NULL,
    buy_price DECIMAL(15, 2) NOT NULL,
    buy_date DATE NOT NULL,
    
    -- Current values
    current_price DECIMAL(15, 2),
    last_price_update TIMESTAMP WITH TIME ZONE,
    
    -- Calculated fields (computed from buy_price and current_price)
    invested_amount DECIMAL(20, 2) GENERATED ALWAYS AS (quantity * buy_price) STORED,
    current_value DECIMAL(20, 2) GENERATED ALWAYS AS (quantity * COALESCE(current_price, buy_price)) STORED,
    gain_loss DECIMAL(20, 2) GENERATED ALWAYS AS (quantity * (COALESCE(current_price, buy_price) - buy_price)) STORED,
    gain_loss_percent DECIMAL(10, 2) GENERATED ALWAYS AS (
        CASE 
            WHEN buy_price > 0 THEN ((COALESCE(current_price, buy_price) - buy_price) / buy_price * 100)
            ELSE 0 
        END
    ) STORED,
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_portfolio IS 'User stock portfolio with holdings';
COMMENT ON COLUMN user_portfolio.exchange IS 'NSE or BSE';

-- ============================================================================
-- TABLE 7: RATE LIMIT CONFIG
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_config (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Global rate limits
    burst_limit_per_minute INTEGER DEFAULT 10,
    per_chat_limit INTEGER DEFAULT 50,
    per_hour_limit INTEGER DEFAULT 150,
    per_day_limit INTEGER DEFAULT 1000,
    
    -- User-specific overrides (JSONB)
    user_specific_overrides JSONB DEFAULT '{}'::jsonb,
    
    -- Whitelisted users (no limits)
    whitelisted_users UUID[] DEFAULT ARRAY[]::UUID[],
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

COMMENT ON TABLE rate_limit_config IS 'Global and user-specific rate limit configuration';

-- ============================================================================
-- TABLE 8: RATE LIMIT TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL,
    
    -- Minute window (burst)
    prompts_current_minute INTEGER DEFAULT 0,
    minute_window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Hour window
    prompts_current_hour INTEGER DEFAULT 0,
    hour_window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 24-hour window
    prompts_current_24h INTEGER DEFAULT 0,
    window_24h_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Timestamps
    last_prompt_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rate_limit_tracking IS 'Per-user rate limit tracking with sliding windows';

-- ============================================================================
-- TABLE 9: RATE LIMIT VIOLATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_violations (
    violation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    chat_id UUID,
    
    -- Violation details
    violation_type VARCHAR(50) NOT NULL,
    limit_value INTEGER NOT NULL,
    prompts_used INTEGER NOT NULL,
    
    -- Action taken
    action_taken VARCHAR(50) DEFAULT 'blocked',
    user_message TEXT,
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    
    -- Timestamp
    violated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rate_limit_violations IS 'Log of rate limit violations';
COMMENT ON COLUMN rate_limit_violations.violation_type IS 'burst, per_chat, hourly, daily';

-- ============================================================================
-- TABLE 10: ADMINS
-- ============================================================================
CREATE TABLE IF NOT EXISTS admins (
    admin_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    
    -- Admin level
    is_super_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE admins IS 'Admin users for system management';

-- ============================================================================
-- TABLE 11: ADMIN ACTIVITY LOGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL,
    
    -- Action details
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    
    -- Changes
    old_value JSONB,
    new_value JSONB,
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    
    -- Timestamp
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE admin_activity_logs IS 'Audit log of admin actions';
COMMENT ON COLUMN admin_activity_logs.action IS 'user_deactivated, rate_limit_updated, system_stopped, etc.';

-- ============================================================================
-- TABLE 12: EMAIL LOGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS email_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_email VARCHAR(255) NOT NULL,
    
    -- Email details
    email_type VARCHAR(100) NOT NULL,
    subject VARCHAR(500),
    
    -- Send status
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    failed BOOLEAN DEFAULT FALSE,
    failure_reason TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE email_logs IS 'Log of all emails sent by the system';
COMMENT ON COLUMN email_logs.email_type IS 'otp_registration, welcome, password_changed, rate_limit_burst, etc.';

-- ============================================================================
-- TABLE 13: EMAIL PREFERENCES
-- ============================================================================
CREATE TABLE IF NOT EXISTS email_preferences (
    preference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL,
    
    -- Notification preferences
    portfolio_reports BOOLEAN DEFAULT TRUE,
    rate_limit_notifications BOOLEAN DEFAULT TRUE,
    system_notifications BOOLEAN DEFAULT TRUE,
    security_alerts BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE email_preferences IS 'User email notification preferences';

-- ============================================================================
-- TABLE 14: SYSTEM STATUS
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_status (
    status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- System state
    current_status VARCHAR(50) DEFAULT 'running',
    
    -- Portfolio report settings
    portfolio_report_frequency VARCHAR(20) DEFAULT 'disabled',
    portfolio_report_send_time TIME DEFAULT '09:00:00',
    portfolio_report_send_day_weekly INTEGER DEFAULT 1,
    portfolio_report_send_day_monthly INTEGER DEFAULT 1,
    portfolio_report_last_sent TIMESTAMP WITH TIME ZONE,
    portfolio_report_next_scheduled TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE system_status IS 'Global system status and settings';
COMMENT ON COLUMN system_status.current_status IS 'running, stopped, maintenance';
COMMENT ON COLUMN system_status.portfolio_report_frequency IS 'disabled, daily, weekly, monthly';

-- ============================================================================
-- INSERT DEFAULT SYSTEM STATUS ROW
-- ============================================================================
INSERT INTO system_status (current_status) 
VALUES ('running')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INSERT DEFAULT RATE LIMIT CONFIG
-- ============================================================================
INSERT INTO rate_limit_config (
    burst_limit_per_minute,
    per_chat_limit,
    per_hour_limit,
    per_day_limit
) VALUES (10, 50, 150, 1000)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version_id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version, description) 
VALUES ('v1.0', 'Initial schema - 15 tables created');

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ SCHEMA v1.0 CREATED SUCCESSFULLY';
    RAISE NOTICE '✅ 15 tables created';
    RAISE NOTICE '✅ Default data inserted';
END $$;
