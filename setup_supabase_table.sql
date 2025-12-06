-- Create sessions table for storing conversation history
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.sessions (
    user_id TEXT PRIMARY KEY,
    history JSONB DEFAULT '[]'::jsonb,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_seen ON public.sessions(last_seen);

-- Enable Row Level Security (RLS)
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role to read/write (for your backend)
CREATE POLICY "Service role can manage sessions"
    ON public.sessions
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Optional: Create policy for authenticated users (if you add user auth later)
-- CREATE POLICY "Users can manage their own sessions"
--     ON public.sessions
--     FOR ALL
--     USING (auth.uid()::text = user_id)
--     WITH CHECK (auth.uid()::text = user_id);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON public.sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify table was created
SELECT 'Table created successfully!' AS status;

