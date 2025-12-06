-- Schema Verification Script
-- Run this in Supabase SQL Editor to check if everything is set up correctly

-- 1. Check if all required columns exist in group_chat_messages
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'group_chat_messages'
  AND column_name IN ('sentiment_score', 'topic_ids', 'engagement_level', 'boring_score')
ORDER BY column_name;

-- 2. Check if all required columns exist in group_chats
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'group_chats'
  AND column_name IN ('common_hobbies', 'last_summary_at', 'health_score', 'last_reminder_sent_at', 'avg_boring_score', 'last_replacement_offer_at')
ORDER BY column_name;

-- 3. Check if all new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements'
  )
ORDER BY table_name;

-- 4. Check for missing UNIQUE constraints
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'UNIQUE'
  AND tc.table_schema = 'public'
  AND tc.table_name IN (
    'group_chat_analytics',
    'group_chat_participant_engagement',
    'group_chat_summaries'
  )
ORDER BY tc.table_name, tc.constraint_name;

-- 5. Check for missing indexes
SELECT 
    indexname,
    tablename
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

-- 6. Check if RLS is enabled and policies exist
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements'
  )
ORDER BY tablename;

SELECT 
    schemaname,
    tablename,
    policyname
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'group_chat_analytics',
    'group_chat_topics',
    'group_chat_participant_engagement',
    'group_chat_summaries',
    'group_chat_reminders',
    'group_chat_match_replacements'
  )
ORDER BY tablename, policyname;

-- 7. Check if the health score function exists
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'update_group_chat_health_score';

-- 8. Check array column types (should be TEXT[] not just ARRAY)
SELECT 
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (column_name LIKE '%topics%' OR column_name LIKE '%hobbies%' OR column_name LIKE '%ids%')
  AND data_type = 'ARRAY'
ORDER BY table_name, column_name;

