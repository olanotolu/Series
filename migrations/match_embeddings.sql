-- PostgreSQL function for vector similarity matching using pgvector
-- Run this in your Supabase SQL Editor after running migrate_add_matching_tables.sql

-- Drop function if it exists (to allow updates)
DROP FUNCTION IF EXISTS match_embeddings(vector(1536), int, text);

-- Create the function
CREATE OR REPLACE FUNCTION match_embeddings(
    target vector(1536),
    match_limit int DEFAULT 5,
    exclude_id text DEFAULT NULL
)
RETURNS TABLE (
    user_id text,
    score float
)
LANGUAGE sql STABLE AS $$
    SELECT 
        ue.user_id,
        (1 - (ue.vector <=> target)) as score
    FROM user_embeddings ue
    WHERE (exclude_id IS NULL OR ue.user_id != exclude_id)
    ORDER BY ue.vector <=> target
    LIMIT match_limit;
$$;

-- Verify function was created
SELECT 
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'match_embeddings'
    ) 
    THEN '✅ match_embeddings function created successfully!'
    ELSE '❌ match_embeddings function NOT created'
    END AS status;

