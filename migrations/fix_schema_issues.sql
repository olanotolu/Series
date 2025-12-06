-- Quick Fix Script for Supabase Schema Issues
-- Run this in Supabase SQL Editor to fix missing constraints, columns, and function

-- 1. Add UNIQUE constraints (prevents duplicate data)
-- PostgreSQL doesn't support IF NOT EXISTS with ADD CONSTRAINT, so we use DO blocks

DO $$
BEGIN
    -- Add UNIQUE constraint to group_chat_analytics
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'group_chat_analytics_unique'
    ) THEN
        ALTER TABLE public.group_chat_analytics
        ADD CONSTRAINT group_chat_analytics_unique 
        UNIQUE (group_chat_id, period_start, period_type);
    END IF;

    -- Add UNIQUE constraint to group_chat_participant_engagement
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'group_chat_participant_engagement_unique'
    ) THEN
        ALTER TABLE public.group_chat_participant_engagement
        ADD CONSTRAINT group_chat_participant_engagement_unique 
        UNIQUE (group_chat_id, phone_number);
    END IF;

    -- Add UNIQUE constraint to group_chat_summaries
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'group_chat_summaries_unique'
    ) THEN
        ALTER TABLE public.group_chat_summaries
        ADD CONSTRAINT group_chat_summaries_unique 
        UNIQUE (group_chat_id, period_start, summary_type);
    END IF;
END $$;

-- 2. Add missing column
ALTER TABLE public.group_chats
ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE;

-- 3. Create health score function
CREATE OR REPLACE FUNCTION update_group_chat_health_score(p_group_chat_id INTEGER)
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_health_score NUMERIC := 0.5;
    v_activity_score NUMERIC := 0.5;
    v_engagement_score NUMERIC := 0.5;
    v_sentiment_score NUMERIC := 0.5;
    v_balance_score NUMERIC := 0.5;
    v_recent_messages INTEGER;
    v_avg_sentiment NUMERIC;
    v_participant_count INTEGER;
    v_engagement_avg NUMERIC;
BEGIN
    -- Activity score: based on recent message count (last 24 hours)
    SELECT COUNT(*) INTO v_recent_messages
    FROM public.group_chat_messages
    WHERE group_chat_id = p_group_chat_id
    AND sent_at > NOW() - INTERVAL '24 hours';
    
    v_activity_score := LEAST(v_recent_messages / 20.0, 1.0); -- Normalize to 0-1
    
    -- Sentiment score: average sentiment of recent messages
    SELECT COALESCE(AVG(sentiment_score), 0.0) INTO v_avg_sentiment
    FROM public.group_chat_messages
    WHERE group_chat_id = p_group_chat_id
    AND sent_at > NOW() - INTERVAL '24 hours'
    AND sentiment_score IS NOT NULL;
    
    v_sentiment_score := (v_avg_sentiment + 1.0) / 2.0; -- Convert -1 to 1 range to 0 to 1
    
    -- Engagement score: average engagement of participants
    SELECT COUNT(*), COALESCE(AVG(engagement_score), 0.5) INTO v_participant_count, v_engagement_avg
    FROM public.group_chat_participant_engagement
    WHERE group_chat_id = p_group_chat_id;
    
    v_engagement_score := v_engagement_avg;
    
    -- Balance score: how balanced participation is (lower variance = better balance)
    SELECT COALESCE(1.0 - STDDEV(participation_balance), 0.5) INTO v_balance_score
    FROM public.group_chat_participant_engagement
    WHERE group_chat_id = p_group_chat_id;
    
    -- Composite health score (weighted average)
    v_health_score := (
        v_activity_score * 0.3 +
        v_engagement_score * 0.3 +
        v_sentiment_score * 0.2 +
        v_balance_score * 0.2
    );
    
    -- Update group chat health score
    UPDATE public.group_chats
    SET health_score = v_health_score,
        updated_at = NOW()
    WHERE id = p_group_chat_id;
    
    RETURN v_health_score;
END;
$$;

-- 4. Add missing indexes (for performance)
CREATE INDEX IF NOT EXISTS idx_group_chat_analytics_group_chat_id ON public.group_chat_analytics(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_analytics_period ON public.group_chat_analytics(period_start, period_type);

CREATE INDEX IF NOT EXISTS idx_group_chat_topics_group_chat_id ON public.group_chat_topics(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_topics_relevance ON public.group_chat_topics(relevance_score DESC);

CREATE INDEX IF NOT EXISTS idx_group_chat_participant_engagement_group_chat_id ON public.group_chat_participant_engagement(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_participant_engagement_user_id ON public.group_chat_participant_engagement(user_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_participant_engagement_score ON public.group_chat_participant_engagement(engagement_score DESC);

CREATE INDEX IF NOT EXISTS idx_group_chat_summaries_group_chat_id ON public.group_chat_summaries(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_summaries_period ON public.group_chat_summaries(period_start, summary_type);

CREATE INDEX IF NOT EXISTS idx_group_chat_reminders_group_chat_id ON public.group_chat_reminders(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_reminders_status ON public.group_chat_reminders(status, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_group_chat_match_replacements_group_chat_id ON public.group_chat_match_replacements(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_match_replacements_user_id ON public.group_chat_match_replacements(user_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_match_replacements_status ON public.group_chat_match_replacements(status);

CREATE INDEX IF NOT EXISTS idx_group_chat_messages_sentiment ON public.group_chat_messages(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_group_chat_messages_engagement ON public.group_chat_messages(engagement_level);
CREATE INDEX IF NOT EXISTS idx_group_chat_messages_boring_score ON public.group_chat_messages(boring_score);

-- Success message
SELECT 'Schema fixes applied successfully! ✅' AS status;

