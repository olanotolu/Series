# Fix RLS Policy Issue

## Problem
The RLS policy requires `auth.role() = 'service_role'`, but your code is using the `anon` key, which has role `anon`.

## Solution: Use Service Role Key

### Step 1: Get Your Service Role Key from Supabase

1. Go to your Supabase project: https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **API**
4. Find **Project API keys**
5. Copy the **`service_role`** key (NOT the `anon` key)
   - ⚠️ **WARNING**: The service_role key has admin access. Keep it secret!

### Step 2: Update Your .env File

Add the service role key to your `.env` file:

```bash
# Existing (anon key - for public access)
SUPABASE_URL=https://kugbwhdljdigakumufwu.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # This is anon key

# Add service role key (for backend/admin access)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Your service_role key here
```

### Step 3: Update Code to Use Service Role Key

The code will automatically use the service role key if available, falling back to the anon key.

## Alternative: Disable RLS (For Testing Only)

If you just want to test quickly, you can temporarily disable RLS:

```sql
-- Run in Supabase SQL Editor
ALTER TABLE public.group_chat_participant_engagement DISABLE ROW LEVEL SECURITY;
```

**⚠️ Warning**: This removes security. Only use for testing. Re-enable after testing:
```sql
ALTER TABLE public.group_chat_participant_engagement ENABLE ROW LEVEL SECURITY;
```

## How to Verify

After updating, check the terminal logs. You should see:
- ✅ No more RLS errors
- ✅ Engagement records being created
- ✅ Boring scores being calculated and stored

