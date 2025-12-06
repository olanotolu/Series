-- Migration: Add profile columns to existing sessions table
-- Run this in your Supabase SQL Editor if the table already exists

-- Add profile columns if they don't exist
DO $$ 
BEGIN
    -- Add name column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'name') THEN
        ALTER TABLE public.sessions ADD COLUMN name TEXT;
    END IF;
    
    -- Add school column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'school') THEN
        ALTER TABLE public.sessions ADD COLUMN school TEXT;
    END IF;
    
    -- Add age column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'age') THEN
        ALTER TABLE public.sessions ADD COLUMN age INTEGER;
    END IF;
    
    -- Add hobbies column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'hobbies') THEN
        ALTER TABLE public.sessions ADD COLUMN hobbies TEXT;
    END IF;
    
    -- Add onboarding_complete column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'onboarding_complete') THEN
        ALTER TABLE public.sessions ADD COLUMN onboarding_complete BOOLEAN DEFAULT false;
    END IF;
    
    -- Add onboarding_state column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'sessions' 
                   AND column_name = 'onboarding_state') THEN
        ALTER TABLE public.sessions ADD COLUMN onboarding_state TEXT;
    END IF;
END $$;

-- Verify columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'sessions'
  AND column_name IN ('name', 'school', 'age', 'hobbies', 'onboarding_complete', 'onboarding_state')
ORDER BY column_name;

SELECT 'Migration completed successfully!' AS status;

