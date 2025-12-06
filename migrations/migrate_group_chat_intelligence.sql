-- Migration: Enhanced Group Chat Intelligence System
-- Adds analytics, topic tracking, engagement metrics, summaries, and reminders

-- 1. Add new analytics and intelligence tables

-- Group chat analytics (daily/weekly metrics)
CREATE TABLE IF NOT EXISTS public.group_chat_analytics (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type TEXT NOT NULL DEFAULT 'daily', -- 'daily' or 'weekly'
    message_count INTEGER DEFAULT 0,
    active_participants INTEGER DEFAULT 0,
    avg_response_time_seconds NUMERIC,
    sentiment_score NUMERIC DEFAULT 0, -- -1 to 1
    health_score NUMERIC DEFAULT 0.5, -- 0 to 1
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT group_chat_analytics_unique UNIQUE (group_chat_id, period_start, period_type)
);

-- Group chat topics (extracted from conversations)
CREATE TABLE IF NOT EXISTS public.group_chat_topics (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    topic_text TEXT NOT NULL,
    relevance_score NUMERIC DEFAULT 0.5, -- 0 to 1
    first_mentioned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_mentioned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    mention_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Participant engagement tracking
CREATE TABLE IF NOT EXISTS public.group_chat_participant_engagement (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES public.sessions(user_id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT now(),
    avg_response_time_seconds NUMERIC,
    engagement_score NUMERIC DEFAULT 0.5, -- 0 to 1
    participation_balance NUMERIC DEFAULT 0.5, -- 0 to 1 (0 = very quiet, 1 = very active)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT group_chat_participant_engagement_unique UNIQUE (group_chat_id, phone_number)
);

-- Conversation summaries
CREATE TABLE IF NOT EXISTS public.group_chat_summaries (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    summary_type TEXT NOT NULL DEFAULT 'daily', -- 'daily' or 'weekly'
    summary_text TEXT NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    key_topics TEXT[], -- Array of topic texts
    participant_contributions JSONB, -- {"user_id": "contribution_summary"}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT group_chat_summaries_unique UNIQUE (group_chat_id, period_start, summary_type)
);

-- Smart reminders
CREATE TABLE IF NOT EXISTS public.group_chat_reminders (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    reminder_type TEXT NOT NULL DEFAULT 'quiet_chat', -- 'quiet_chat', 'topic_suggestion', etc.
    reminder_message TEXT,
    suggested_topics TEXT[],
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'cancelled'
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Match replacement tracking
CREATE TABLE IF NOT EXISTS public.group_chat_match_replacements (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER NOT NULL REFERENCES public.group_chats(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES public.sessions(user_id) ON DELETE CASCADE,
    original_match_user_id TEXT NOT NULL REFERENCES public.sessions(user_id) ON DELETE CASCADE,
    offered_replacement_user_id TEXT REFERENCES public.sessions(user_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'offered', -- 'offered', 'accepted', 'declined'
    offered_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    responded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 2. Enhance existing tables

-- Add columns to group_chat_messages
ALTER TABLE public.group_chat_messages
ADD COLUMN IF NOT EXISTS sentiment_score NUMERIC DEFAULT 0,
ADD COLUMN IF NOT EXISTS topic_ids INTEGER[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS engagement_level TEXT DEFAULT 'medium', -- 'high', 'medium', 'low'
ADD COLUMN IF NOT EXISTS boring_score NUMERIC DEFAULT 5; -- 1 (interesting) to 10 (boring)

-- Add columns to group_chats
ALTER TABLE public.group_chats
ADD COLUMN IF NOT EXISTS common_hobbies TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS last_summary_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS health_score NUMERIC DEFAULT 0.5, -- 0 to 1
ADD COLUMN IF NOT EXISTS last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS avg_boring_score NUMERIC DEFAULT 5, -- 1 (interesting) to 10 (boring)
ADD COLUMN IF NOT EXISTS last_replacement_offer_at TIMESTAMP WITH TIME ZONE;

-- 3. Create indexes for performance

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

-- 4. Enable RLS (Row Level Security) for new tables

ALTER TABLE public.group_chat_analytics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_analytics" ON public.group_chat_analytics;
CREATE POLICY "Service role can manage group_chat_analytics" ON public.group_chat_analytics
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.group_chat_topics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_topics" ON public.group_chat_topics;
CREATE POLICY "Service role can manage group_chat_topics" ON public.group_chat_topics
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.group_chat_participant_engagement ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_participant_engagement" ON public.group_chat_participant_engagement;
CREATE POLICY "Service role can manage group_chat_participant_engagement" ON public.group_chat_participant_engagement
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.group_chat_summaries ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_summaries" ON public.group_chat_summaries;
CREATE POLICY "Service role can manage group_chat_summaries" ON public.group_chat_summaries
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.group_chat_reminders ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_reminders" ON public.group_chat_reminders;
CREATE POLICY "Service role can manage group_chat_reminders" ON public.group_chat_reminders
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.group_chat_match_replacements ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role can manage group_chat_match_replacements" ON public.group_chat_match_replacements;
CREATE POLICY "Service role can manage group_chat_match_replacements" ON public.group_chat_match_replacements
    FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

-- 5. Helper function to update group chat health score
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

