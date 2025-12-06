-- Fix match_embeddings RPC function
-- This version handles edge cases and ensures it works correctly

-- Drop and recreate the function
DROP FUNCTION IF EXISTS match_embeddings(vector(1536), int, text);

-- Create improved version with better error handling
CREATE OR REPLACE FUNCTION match_embeddings(
    target vector(1536),
    match_limit int DEFAULT 5,
    exclude_id text DEFAULT NULL
)
RETURNS TABLE (
    user_id text,
    score float
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ue.user_id,
        (1 - (ue.vector <=> target))::float as score
    FROM user_embeddings ue
    WHERE 
        ue.vector IS NOT NULL
        AND (exclude_id IS NULL OR ue.user_id != exclude_id)
        AND array_length(ue.vector::float[], 1) = 1536  -- Ensure correct dimensions
    ORDER BY ue.vector <=> target
    LIMIT match_limit;
END;
$$;

-- Alternative simpler version (if above doesn't work)
-- DROP FUNCTION IF EXISTS match_embeddings(vector(1536), int, text);
-- CREATE OR REPLACE FUNCTION match_embeddings(
--     target vector(1536),
--     match_limit int DEFAULT 5,
--     exclude_id text DEFAULT NULL
-- )
-- RETURNS TABLE (
--     user_id text,
--     score float
-- )
-- LANGUAGE sql STABLE AS $$
--     SELECT 
--         ue.user_id,
--         (1 - (ue.vector <=> target))::float as score
--     FROM user_embeddings ue
--     WHERE 
--         ue.vector IS NOT NULL
--         AND (exclude_id IS NULL OR ue.user_id != exclude_id)
--     ORDER BY ue.vector <=> target
--     LIMIT match_limit;
-- $$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION match_embeddings(vector(1536), int, text) TO authenticated;
GRANT EXECUTE ON FUNCTION match_embeddings(vector(1536), int, text) TO service_role;

-- Test query to verify function works
-- SELECT * FROM match_embeddings(
--     (SELECT vector FROM user_embeddings LIMIT 1),
--     5,
--     NULL
-- );

