# Quick Start - Your Consumer is Running! 🚀

## Current Status ✅

Your consumer is:
- ✅ Running and connected to Kafka
- ✅ Connected to Supabase
- ✅ Assigned to Partition 1
- ✅ Waiting for new messages (positioned at offset 34)

## What to Do Now

### 1. Detach from Screen (Keep It Running)

**Press:** `Ctrl+A` then `D`

You'll see: `[detached from consumer]`

Your consumer keeps running in the background! 🎉

### 2. Test It!

Send a message from your phone to: **+16463769330**

Or send a text message like "Hey" or "Hello"

### 3. See the Response

**Reattach to screen to see logs:**
```bash
screen -r consumer
```

You'll see:
- Incoming message
- LLM processing
- Response being sent

### 4. Detach Again

Press `Ctrl+A` then `D` to detach again.

## Screen Commands Cheat Sheet

| Command | What It Does |
|---------|-------------|
| `Ctrl+A` then `D` | Detach (keep running) |
| `screen -r consumer` | Reattach to see logs |
| `screen -ls` | List all screen sessions |
| `screen -X -S consumer quit` | Kill screen session |

## Fix Supabase Table (Optional)

The consumer works without it, but conversation history won't be saved.

**To enable history:**
1. Go to: https://kugbwhdljdigakumufwu.supabase.co
2. Click "SQL Editor"
3. Run the SQL from `setup_supabase_table.sql`

## Troubleshooting

**Consumer stopped?**
- Check if screen is still running: `screen -ls`
- If not, start again: `screen -S consumer` then `python consumer.py`

**Not receiving messages?**
- Make sure consumer is running: `screen -ls`
- Check you're sending to: +16463769330
- Reattach to see logs: `screen -r consumer`

**Want to stop consumer?**
```bash
screen -r consumer
# Press Ctrl+C to stop
# Type: exit
```

## Summary

1. ✅ Consumer is running
2. Press `Ctrl+A` then `D` to detach
3. Send a test message
4. `screen -r consumer` to see logs
5. Done! 🎉

