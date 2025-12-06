-- Migration: Add user_updates table for /update command feature
-- This allows users to post updates (like Instagram Notes) and view updates from their network

-- Create user_updates table
CREATE TABLE IF NOT EXISTS public.user_updates (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.sessions(user_id) ON DELETE CASCADE,
    update_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE, -- Optional: auto-expire after 48 hours
    is_active BOOLEAN DEFAULT true,
    view_count INTEGER DEFAULT 0,
    CONSTRAINT user_updates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.sessions(user_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_updates_user_id ON public.user_updates(user_id);
CREATE INDEX IF NOT EXISTS idx_user_updates_created_at ON public.user_updates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_updates_active ON public.user_updates(is_active, expires_at);

-- Enable RLS
ALTER TABLE public.user_updates ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role can manage user_updates
DROP POLICY IF EXISTS "Service role can manage user_updates" ON public.user_updates;
CREATE POLICY "Service role can manage user_updates" ON public.user_updates
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

-- Optional: Function to auto-expire updates after 48 hours
CREATE OR REPLACE FUNCTION expire_old_updates()
RETURNS void AS $$
BEGIN
    UPDATE public.user_updates
    SET is_active = false
    WHERE is_active = true
    AND expires_at IS NOT NULL
    AND expires_at < now();
END;
$$ LANGUAGE plpgsql;

