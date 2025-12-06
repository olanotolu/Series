-- Create sessions table for storing conversation history
-- Run this in your Supabase SQL Editor

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.sessions (
    user_id TEXT PRIMARY KEY,
    history JSONB DEFAULT '[]'::jsonb,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Profile fields
    name TEXT,
    school TEXT,
    age INTEGER,
    hobbies TEXT,
    onboarding_complete BOOLEAN DEFAULT false,
    onboarding_state TEXT
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

-- Create user_embeddings table for AI-powered matching
CREATE TABLE IF NOT EXISTS public.user_embeddings (
    user_id TEXT PRIMARY KEY REFERENCES sessions(user_id) ON DELETE CASCADE,
    vector vector(1536),  -- OpenAI text-embedding-3-large dimension
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS user_embeddings_vector_idx 
ON user_embeddings USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- Create matches table for tracking user matches
CREATE TABLE IF NOT EXISTS public.matches (
    id SERIAL PRIMARY KEY,
    user1_id TEXT REFERENCES sessions(user_id) ON DELETE CASCADE,
    user2_id TEXT REFERENCES sessions(user_id) ON DELETE CASCADE,
    score FLOAT,
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'declined'
    UNIQUE(user1_id, user2_id)
);

CREATE INDEX IF NOT EXISTS matches_user1_idx ON matches(user1_id);
CREATE INDEX IF NOT EXISTS matches_user2_idx ON matches(user2_id);
CREATE INDEX IF NOT EXISTS matches_score_idx ON matches(score DESC);

-- Enable RLS on new tables
ALTER TABLE public.user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- Create policies for user_embeddings
CREATE POLICY "Service role can manage embeddings"
    ON public.user_embeddings
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Create policies for matches
CREATE POLICY "Service role can manage matches"
    ON public.matches
    FOR ALL
    USING (true)
    WITH CHECK (true);

SELECT 'Embedding and matching tables created successfully!' AS status;

