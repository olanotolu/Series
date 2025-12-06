-- Migration script to add AI-powered matching tables
-- Run this in your Supabase SQL Editor
-- This script is safe to run multiple times (uses IF NOT EXISTS)

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create user_embeddings table for AI-powered matching
CREATE TABLE IF NOT EXISTS public.user_embeddings (
    user_id TEXT PRIMARY KEY REFERENCES sessions(user_id) ON DELETE CASCADE,
    vector vector(1536),  -- OpenAI text-embedding-3-large dimension
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search (only if it doesn't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'user_embeddings_vector_idx'
    ) THEN
        CREATE INDEX user_embeddings_vector_idx 
        ON user_embeddings USING ivfflat (vector vector_cosine_ops)
        WITH (lists = 100);
    END IF;
END $$;

-- Step 3: Create matches table for tracking user matches
CREATE TABLE IF NOT EXISTS public.matches (
    id SERIAL PRIMARY KEY,
    user1_id TEXT REFERENCES sessions(user_id) ON DELETE CASCADE,
    user2_id TEXT REFERENCES sessions(user_id) ON DELETE CASCADE,
    score FLOAT,
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'declined'
    UNIQUE(user1_id, user2_id)
);

-- Create indexes for matches table (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'matches_user1_idx') THEN
        CREATE INDEX matches_user1_idx ON matches(user1_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'matches_user2_idx') THEN
        CREATE INDEX matches_user2_idx ON matches(user2_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'matches_score_idx') THEN
        CREATE INDEX matches_score_idx ON matches(score DESC);
    END IF;
END $$;

-- Step 4: Enable RLS on new tables (if not already enabled)
ALTER TABLE public.user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- Step 5: Create policies for user_embeddings (drop and recreate to avoid conflicts)
DROP POLICY IF EXISTS "Service role can manage embeddings" ON public.user_embeddings;
CREATE POLICY "Service role can manage embeddings"
    ON public.user_embeddings
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Step 6: Create policies for matches (drop and recreate to avoid conflicts)
DROP POLICY IF EXISTS "Service role can manage matches" ON public.matches;
CREATE POLICY "Service role can manage matches"
    ON public.matches
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Verify tables were created
SELECT 
    '✅ pgvector extension enabled' AS status
UNION ALL
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'user_embeddings') 
         THEN '✅ user_embeddings table created'
         ELSE '❌ user_embeddings table NOT created'
    END
UNION ALL
SELECT 
    CASE WHEN EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'matches') 
         THEN '✅ matches table created'
         ELSE '❌ matches table NOT created'
    END;

