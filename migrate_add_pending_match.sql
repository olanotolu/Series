-- Migration: Add pending_match_user_id column to sessions table
-- This column stores the user_id of a matched user when waiting for confirmation

-- Add column if it doesn't exist
ALTER TABLE public.sessions 
ADD COLUMN IF NOT EXISTS pending_match_user_id text;

-- Add comment
COMMENT ON COLUMN public.sessions.pending_match_user_id IS 'Stores the user_id of a matched user when waiting for match confirmation';

