-- Verify Current Schema Completeness
-- Run this in Supabase SQL Editor to check if everything is in place

-- 1. Check UNIQUE constraints
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name
FROM pg_constraint
WHERE contype = 'u'
AND conrelid::regclass::text IN (
    'public.group_chat_analytics',
    'public.group_chat_participant_engagement',
    'public.group_chat_summaries'
)
ORDER BY table_name, constraint_name;

-- 2. Check if last_activity_at column exists
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'group_chats'
AND column_name = 'last_activity_at';

-- 3. Check if update_group_chat_health_score function exists
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'update_group_chat_health_score';

-- 4. Check indexes on intelligence tables
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements',
    'group_chat_messages'
)
ORDER BY tablename, indexname;

-- 5. Summary check
SELECT 
    'Tables' AS check_type,
    COUNT(*) AS count
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements',
    'group_chat_messages',
    'group_chat_participants',
    'group_chats',
    'matches',
    'sessions',
    'user_embeddings',
    'user_updates'
)
UNION ALL
SELECT 
    'UNIQUE Constraints' AS check_type,
    COUNT(*) AS count
FROM pg_constraint
WHERE contype = 'u'
AND conrelid::regclass::text IN (
    'public.group_chat_analytics',
    'public.group_chat_participant_engagement',
    'public.group_chat_summaries'
)
UNION ALL
SELECT 
    'Indexes' AS check_type,
    COUNT(*) AS count
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements',
    'group_chat_messages'
)
UNION ALL
SELECT 
    'Functions' AS check_type,
    COUNT(*) AS count
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'update_group_chat_health_score';

