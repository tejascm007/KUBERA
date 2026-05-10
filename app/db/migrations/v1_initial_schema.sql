-- ============================================================================
-- KUBERA STOCK ANALYSIS CHATBOT - FULL RESTORE SCRIPT
-- Run this in your new Supabase project's SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: EXTENSIONS & SEQUENCE
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SEQUENCE IF NOT EXISTS schema_version_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- ============================================================================
-- STEP 2: TABLES (in dependency order — no FK errors)
-- ============================================================================

-- Independent tables first (no foreign keys)

CREATE TABLE IF NOT EXISTS public.users (
  user_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  email VARCHAR(255) NOT NULL UNIQUE CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
  username VARCHAR(100) NOT NULL UNIQUE CHECK (LENGTH(username) >= 3 AND LENGTH(username) <= 100),
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  phone VARCHAR(20) CHECK (phone IS NULL OR phone ~* '^\+?[0-9]{10,15}$'),
  date_of_birth DATE,
  investment_style VARCHAR(50),
  risk_tolerance VARCHAR(50),
  interested_sectors TEXT[],
  account_status VARCHAR(20) DEFAULT 'active' CHECK (account_status = ANY (ARRAY['active', 'deactivated', 'suspended'])),
  email_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT users_pkey PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS public.admins (
  admin_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  email VARCHAR(255) NOT NULL UNIQUE,
  full_name VARCHAR(255) NOT NULL,
  is_super_admin BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT admins_pkey PRIMARY KEY (admin_id)
);

CREATE TABLE IF NOT EXISTS public.otps (
  otp_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  email VARCHAR(255) NOT NULL,
  otp_hash VARCHAR(255) NOT NULL,
  otp_type VARCHAR(50) NOT NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  attempt_count INTEGER DEFAULT 0 CHECK (attempt_count >= 0 AND attempt_count <= 10),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  verified_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT otps_pkey PRIMARY KEY (otp_id)
);

CREATE TABLE IF NOT EXISTS public.email_log (
  log_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  recipient_email VARCHAR(255) NOT NULL,
  email_type VARCHAR(100) NOT NULL,
  subject VARCHAR(500),
  send_status VARCHAR(50) DEFAULT 'pending',
  retry_count INTEGER DEFAULT 0,
  last_error TEXT,
  sent_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT email_log_pkey PRIMARY KEY (log_id)
);

CREATE TABLE IF NOT EXISTS public.rate_limit_config (
  config_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  burst_limit_per_minute INTEGER DEFAULT 10 CHECK (burst_limit_per_minute > 0),
  per_chat_limit INTEGER DEFAULT 50 CHECK (per_chat_limit > 0),
  per_hour_limit INTEGER DEFAULT 150 CHECK (per_hour_limit > 0),
  per_day_limit INTEGER DEFAULT 1000 CHECK (per_day_limit > 0),
  user_specific_overrides JSONB DEFAULT '{}'::jsonb,
  whitelisted_users UUID[] DEFAULT ARRAY[]::UUID[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_by VARCHAR(255),
  CONSTRAINT rate_limit_config_pkey PRIMARY KEY (config_id)
);

CREATE TABLE IF NOT EXISTS public.system_status (
  status_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  current_status VARCHAR(50) DEFAULT 'running',
  portfolio_report_frequency VARCHAR(20) DEFAULT 'disabled',
  portfolio_report_send_time TIME DEFAULT '09:00:00',
  portfolio_report_send_day_weekly INTEGER DEFAULT 1 CHECK (portfolio_report_send_day_weekly >= 0 AND portfolio_report_send_day_weekly <= 6),
  portfolio_report_send_day_monthly INTEGER DEFAULT 1 CHECK (portfolio_report_send_day_monthly >= 1 AND portfolio_report_send_day_monthly <= 31),
  portfolio_report_last_sent TIMESTAMP WITH TIME ZONE,
  portfolio_report_next_scheduled TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT system_status_pkey PRIMARY KEY (status_id)
);

CREATE TABLE IF NOT EXISTS public.schema_version (
  version_id INTEGER NOT NULL DEFAULT nextval('schema_version_version_id_seq'::regclass),
  version VARCHAR(50) NOT NULL,
  description TEXT,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT schema_version_pkey PRIMARY KEY (version_id)
);

-- Tables that depend on users

CREATE TABLE IF NOT EXISTS public.refresh_tokens (
  token_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  jti VARCHAR(255) NOT NULL UNIQUE,
  revoked BOOLEAN DEFAULT FALSE,
  revoked_at TIMESTAMP WITH TIME ZONE,
  revoke_reason VARCHAR(255),
  revoked_reason VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  last_used_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT refresh_tokens_pkey PRIMARY KEY (token_id),
  CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.chats (
  chat_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  chat_name VARCHAR(255) DEFAULT 'New Chat',
  total_prompts INTEGER DEFAULT 0 CHECK (total_prompts >= 0),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  last_message_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT chats_pkey PRIMARY KEY (chat_id),
  CONSTRAINT fk_chats_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.email_preferences (
  preference_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE,
  portfolio_reports BOOLEAN DEFAULT TRUE,
  security_alerts BOOLEAN DEFAULT TRUE,
  rate_limit_notifications BOOLEAN DEFAULT TRUE,
  system_notifications BOOLEAN DEFAULT TRUE,
  promotional_emails BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT email_preferences_pkey PRIMARY KEY (preference_id),
  CONSTRAINT fk_email_prefs_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.rate_limit_tracking (
  tracking_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE,
  prompts_current_minute INTEGER DEFAULT 0 CHECK (prompts_current_minute >= 0),
  minute_window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  prompts_current_hour INTEGER DEFAULT 0 CHECK (prompts_current_hour >= 0),
  hour_window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  prompts_current_24h INTEGER DEFAULT 0 CHECK (prompts_current_24h >= 0),
  window_24h_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  last_prompt_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT rate_limit_tracking_pkey PRIMARY KEY (tracking_id),
  CONSTRAINT fk_rate_tracking_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.user_portfolio (
  portfolio_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  stock_symbol VARCHAR(50) NOT NULL,
  exchange VARCHAR(10) DEFAULT 'NSE',
  quantity DECIMAL(15,4) NOT NULL CHECK (quantity > 0),
  buy_price DECIMAL(15,2) NOT NULL CHECK (buy_price > 0),
  buy_date DATE NOT NULL CHECK (buy_date <= CURRENT_DATE),
  current_price DECIMAL(15,2) CHECK (current_price IS NULL OR current_price > 0),
  last_price_update TIMESTAMP WITH TIME ZONE,
  invested_amount DECIMAL(20,2),
  current_value DECIMAL(20,2),
  gain_loss DECIMAL(20,2),
  gain_loss_percent DECIMAL(10,2),
  notes TEXT,
  investment_type VARCHAR(50),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT user_portfolio_pkey PRIMARY KEY (portfolio_id),
  CONSTRAINT fk_portfolio_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

-- Tables that depend on both users and chats

CREATE TABLE IF NOT EXISTS public.messages (
  message_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL,
  user_id UUID NOT NULL,
  user_message TEXT NOT NULL,
  assistant_response TEXT,
  tokens_used INTEGER CHECK (tokens_used IS NULL OR tokens_used >= 0),
  processing_time_ms INTEGER CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0),
  mcp_servers_called TEXT[],
  mcp_tools_used TEXT[],
  charts_generated INTEGER DEFAULT 0 CHECK (charts_generated >= 0),
  llm_model VARCHAR(100),
  chart_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  response_completed_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT messages_pkey PRIMARY KEY (message_id),
  CONSTRAINT fk_messages_chat FOREIGN KEY (chat_id) REFERENCES public.chats(chat_id) ON DELETE CASCADE,
  CONSTRAINT fk_messages_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.rate_limit_violations (
  violation_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  chat_id UUID,
  violation_type VARCHAR(50) NOT NULL,
  limit_value INTEGER NOT NULL CHECK (limit_value > 0),
  prompts_used INTEGER NOT NULL CHECK (prompts_used >= 0),
  action_taken VARCHAR(50) DEFAULT 'blocked',
  user_message TEXT,
  ip_address INET,
  user_agent TEXT,
  violated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT rate_limit_violations_pkey PRIMARY KEY (violation_id),
  CONSTRAINT fk_rate_violations_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_rate_violations_chat FOREIGN KEY (chat_id) REFERENCES public.chats(chat_id) ON DELETE SET NULL
);

-- Table that depends on admins

CREATE TABLE IF NOT EXISTS public.admin_activity_logs (
  log_id UUID NOT NULL DEFAULT uuid_generate_v4(),
  admin_id UUID NOT NULL,
  action VARCHAR(100) NOT NULL,
  target_type VARCHAR(50),
  target_id UUID,
  old_value JSONB,
  new_value JSONB,
  ip_address INET,
  user_agent TEXT,
  performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT admin_activity_logs_pkey PRIMARY KEY (log_id),
  CONSTRAINT fk_admin_logs_admin FOREIGN KEY (admin_id) REFERENCES public.admins(admin_id) ON DELETE CASCADE
);

-- ============================================================================
-- STEP 3: INDEXES (v2_indexes.sql)
-- ============================================================================

SET timezone = 'Asia/Kolkata';

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at DESC);

-- OTPs
CREATE INDEX IF NOT EXISTS idx_otps_email ON otps(email);
CREATE INDEX IF NOT EXISTS idx_otps_email_type ON otps(email, otp_type);
CREATE INDEX IF NOT EXISTS idx_otps_created_at ON otps(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_otps_is_verified ON otps(is_verified);

-- Refresh Tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_jti ON refresh_tokens(jti);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked ON refresh_tokens(revoked);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Chats
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON chats(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at DESC);

-- Messages
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_response_completed ON messages(response_completed_at);
CREATE INDEX IF NOT EXISTS idx_messages_mcp_servers ON messages USING GIN(mcp_servers_called);
CREATE INDEX IF NOT EXISTS idx_messages_mcp_tools ON messages USING GIN(mcp_tools_used);

-- User Portfolio
CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_stock_symbol ON user_portfolio(stock_symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_user_stock ON user_portfolio(user_id, stock_symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_exchange ON user_portfolio(exchange);
CREATE INDEX IF NOT EXISTS idx_portfolio_buy_date ON user_portfolio(buy_date DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_last_price_update ON user_portfolio(last_price_update);

-- Rate Limit Tracking
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_user_id ON rate_limit_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_last_prompt ON rate_limit_tracking(last_prompt_at DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_minute_window ON rate_limit_tracking(minute_window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_hour_window ON rate_limit_tracking(hour_window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limit_tracking_24h_window ON rate_limit_tracking(window_24h_start);

-- Rate Limit Violations
CREATE INDEX IF NOT EXISTS idx_rate_violations_user_id ON rate_limit_violations(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_violations_chat_id ON rate_limit_violations(chat_id);
CREATE INDEX IF NOT EXISTS idx_rate_violations_type ON rate_limit_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_rate_violations_violated_at ON rate_limit_violations(violated_at DESC);
CREATE INDEX IF NOT EXISTS idx_rate_violations_user_violated ON rate_limit_violations(user_id, violated_at DESC);

-- Admins
CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);
CREATE INDEX IF NOT EXISTS idx_admins_is_super_admin ON admins(is_super_admin);
CREATE INDEX IF NOT EXISTS idx_admins_last_login ON admins(last_login_at DESC);

-- Admin Activity Logs
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_activity_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_type ON admin_activity_logs(target_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_id ON admin_activity_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_performed_at ON admin_activity_logs(performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_performed ON admin_activity_logs(admin_id, performed_at DESC);

-- Email Logs
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_log(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_log(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_log(created_at DESC);

-- Email Preferences
CREATE INDEX IF NOT EXISTS idx_email_prefs_user_id ON email_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_email_prefs_portfolio_reports ON email_preferences(portfolio_reports) WHERE portfolio_reports = TRUE;
CREATE INDEX IF NOT EXISTS idx_email_prefs_system_notif ON email_preferences(system_notifications) WHERE system_notifications = TRUE;

-- Composite Indexes
CREATE INDEX IF NOT EXISTS idx_chats_user_total_prompts ON chats(user_id, total_prompts DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_user_gain ON user_portfolio(user_id, gain_loss DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_tokens ON messages(user_id, tokens_used);
CREATE INDEX IF NOT EXISTS idx_violations_type_user ON rate_limit_violations(violation_type, user_id, violated_at DESC);

-- Unique index from v3
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_user_stock ON user_portfolio(user_id, stock_symbol);

-- ============================================================================
-- STEP 4: TRIGGERS (from v3_constraints.sql)
-- ============================================================================

-- Function: auto-update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_chats_updated_at
    BEFORE UPDATE ON chats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_portfolio_updated_at
    BEFORE UPDATE ON user_portfolio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_config_updated_at
    BEFORE UPDATE ON rate_limit_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_tracking_updated_at
    BEFORE UPDATE ON rate_limit_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_admins_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_email_prefs_updated_at
    BEFORE UPDATE ON email_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_system_status_updated_at
    BEFORE UPDATE ON system_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function: auto-update chat stats on new message
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

CREATE TRIGGER trigger_messages_update_chat_stats
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION update_chat_statistics();

-- ============================================================================
-- STEP 5: DEFAULT DATA
-- ============================================================================

INSERT INTO public.system_status (current_status)
VALUES ('running')
ON CONFLICT DO NOTHING;

INSERT INTO public.rate_limit_config (
    burst_limit_per_minute,
    per_chat_limit,
    per_hour_limit,
    per_day_limit
) VALUES (10, 50, 150, 1000)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 6: SCHEMA VERSION LOG
-- ============================================================================

INSERT INTO public.schema_version (version, description) VALUES
    ('v1.0', 'Initial schema - 15 tables created'),
    ('v2.0', 'Performance indexes added'),
    ('v2.1', 'chart_url column added to messages'),
    ('v3.0', 'Triggers and constraints added');

-- ============================================================================
-- DONE! 15 tables, 60+ indexes, triggers all set.
-- ============================================================================