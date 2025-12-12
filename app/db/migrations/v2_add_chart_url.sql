-- ============================================================================
-- MIGRATION: Add chart_url to messages table
-- Purpose: Store chart URLs so they persist when chat is reloaded
-- ============================================================================

-- Add chart_url column to store Supabase Storage URLs for generated charts
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS chart_url TEXT;

-- Add comment
COMMENT ON COLUMN messages.chart_url IS 'Supabase Storage URL for generated chart HTML files';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Check the column was added:
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'messages' AND column_name = 'chart_url';
