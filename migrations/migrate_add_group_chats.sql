-- Migration: Add Group Chats Support
-- This adds tables to track group chats and enable AI participation

-- Table to track group chats
CREATE TABLE IF NOT EXISTS public.group_chats (
    id SERIAL PRIMARY KEY,
    chat_id TEXT UNIQUE NOT NULL,  -- Series API chat_id
    display_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    match_id INTEGER REFERENCES public.matches(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    CONSTRAINT group_chats_chat_id_key UNIQUE (chat_id)
);

-- Table to track participants in group chats
CREATE TABLE IF NOT EXISTS public.group_chat_participants (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER REFERENCES public.group_chats(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES public.sessions(user_id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_ai BOOLEAN DEFAULT false,  -- True if this is the AI participant
    CONSTRAINT group_chat_participants_unique UNIQUE (group_chat_id, phone_number)
);

-- Table to track group chat messages (for context/history)
CREATE TABLE IF NOT EXISTS public.group_chat_messages (
    id SERIAL PRIMARY KEY,
    group_chat_id INTEGER REFERENCES public.group_chats(id) ON DELETE CASCADE,
    message_id TEXT,  -- Series API message ID
    from_phone TEXT NOT NULL,
    from_user_id TEXT REFERENCES public.sessions(user_id) ON DELETE SET NULL,
    text TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_from_ai BOOLEAN DEFAULT false
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_group_chats_chat_id ON public.group_chats(chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chats_match_id ON public.group_chats(match_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_participants_group_chat_id ON public.group_chat_participants(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_participants_user_id ON public.group_chat_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_messages_group_chat_id ON public.group_chat_messages(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_group_chat_messages_from_phone ON public.group_chat_messages(from_phone);

-- Add RLS policies (if using Row Level Security)
-- Allow service role full access
ALTER TABLE public.group_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_chat_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_chat_messages ENABLE ROW LEVEL SECURITY;

-- Policy for service role (full access)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'group_chats' 
        AND policyname = 'Service role can manage group chats'
    ) THEN
        CREATE POLICY "Service role can manage group chats" ON public.group_chats
            FOR ALL USING (true);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'group_chat_participants' 
        AND policyname = 'Service role can manage participants'
    ) THEN
        CREATE POLICY "Service role can manage participants" ON public.group_chat_participants
            FOR ALL USING (true);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'group_chat_messages' 
        AND policyname = 'Service role can manage messages'
    ) THEN
        CREATE POLICY "Service role can manage messages" ON public.group_chat_messages
            FOR ALL USING (true);
    END IF;
END $$;

-- Add comment to matches table for group_chat_id (optional, for reference)
COMMENT ON TABLE public.group_chats IS 'Tracks group chats created from matches';
COMMENT ON TABLE public.group_chat_participants IS 'Tracks participants in group chats, including AI';
COMMENT ON TABLE public.group_chat_messages IS 'Stores message history for group chats';

