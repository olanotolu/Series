# Fixes Applied for Boring Score System

## Issues Fixed

### 1. **Async/Await Error in `match_replacement.py`**
   - **Problem**: `check_and_offer_replacements` was not async but used `await`
   - **Fix**: Made the function `async def check_and_offer_replacements()`
   - **File**: `match_replacement.py` line 290

### 2. **LLM API Error - Wrong Task Type**
   - **Problem**: Using `text_generation` but model only supports `conversational` task
   - **Fix**: Changed all LLM calls to use `chat_completion` instead
   - **Files**: 
     - `group_chat_intelligence.py` (sentiment, boring score, topic extraction)

### 3. **Missing Column Reference**
   - **Problem**: Code referenced `last_activity_at` column that doesn't exist
   - **Fix**: Removed reference from `get_group_chat_health_metrics()`
   - **File**: `group_chat_manager.py` line 271

### 4. **Boring Score Fallback**
   - **Problem**: If LLM fails, boring score always returns 5.0 (neutral)
   - **Fix**: Added heuristic-based calculation as fallback
   - **Heuristic**: 
     - Short messages (≤3 chars) = +3.0 (very boring)
     - Very short (≤10 chars) = +2.0
     - Short (≤20 chars) = +1.0
     - Common boring words = +2.0
     - Questions = -1.0 (more interesting)
     - Long messages (>50 chars) = -1.0 (more interesting)
   - **File**: `group_chat_intelligence.py` - `calculate_boring_score_heuristic()`

### 5. **Better Logging**
   - **Added**: More detailed logging for boring score checking
   - **Shows**: Average boring score, threshold comparison, replacement offers
   - **File**: `consumer.py` line 1174-1182

## Remaining Issues

### RLS Policy Error
- **Error**: `'new row violates row-level security policy for table "group_chat_participant_engagement"'`
- **Cause**: Row Level Security policies may not be set up correctly
- **Solution**: Run the migration script `migrate_group_chat_intelligence.sql` to ensure RLS policies are created
- **Or**: Temporarily disable RLS for testing:
  ```sql
  ALTER TABLE public.group_chat_participant_engagement DISABLE ROW LEVEL SECURITY;
  ```

## How Boring Score Works Now

1. **Message Analysis**: Every message in a group chat is analyzed
2. **Boring Score Calculation**:
   - Tries LLM first (if available)
   - Falls back to heuristic if LLM fails
   - Score: 1 (interesting) to 10 (boring)
3. **Average Calculation**: Average of last 50 messages
4. **Threshold Check**: If avg_boring_score >= 4.0, replacement is offered
5. **Replacement Offer**: System finds next best match and offers it privately

## Testing

To test the boring score system:
1. Send several short, boring messages: "ok", "yeah", "cool", "hmm"
2. Check terminal logs for: `📊 Average boring score: X.X`
3. When score >= 4.0, you should see: `⚠️  Boring score X.X >= 4.0 - checking for replacement offers...`
4. Replacement offers will be logged: `💬 Found X replacement offer(s)`

## Next Steps

1. **Fix RLS Policy**: Run migration or disable RLS for testing
2. **Test Boring Score**: Send boring messages and verify scores are calculated
3. **Verify Replacement Offers**: Check if offers are generated when score >= 4.0
4. **Send Private Messages**: Implement sending replacement offers to users' direct chats

