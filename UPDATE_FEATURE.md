# /update Feature - User Updates (Instagram Notes-like)

## Overview
Users can post updates and view updates from their network using the `/update` command.

## Setup

### 1. Run Database Migration
Run the migration to create the `user_updates` table:

```sql
-- In Supabase SQL Editor, run:
-- migrate_add_user_updates.sql
```

Or run it directly:
```bash
# Connect to your Supabase database and run the SQL file
```

### 2. Restart Consumer
After running the migration, restart your consumer:
```bash
python consumer.py
```

## Usage

### Post an Update
```
/update I got a new job
/update Just finished a great workout
/update Excited about the new project!
```

The AI will respond: "✅ Update posted! People in your network will see this."

### View Updates Feed
```
/update
```

The AI will show all updates from your network:
```
📢 Updates from your network:

• Ola: I got a new job (2h ago)
• Siddharth: Just finished a great workout (5h ago)
• Zara (AI Friend): Excited to help connect more people! (1d ago)

Type /update <your message> to share your own update!
```

## Features

- **Auto-expiration**: Updates expire after 48 hours (like Instagram Notes)
- **One active update per user**: New update replaces old one
- **Network-wide visibility**: Everyone in the network can see updates
- **Time formatting**: Shows "2h ago", "5d ago", etc.

## Database Schema

The `user_updates` table stores:
- `user_id`: User who posted the update
- `update_text`: The update message (max 500 chars)
- `created_at`: When it was posted
- `expires_at`: When it expires (48 hours)
- `is_active`: Whether it's still active
- `view_count`: How many times it's been viewed

## Future Enhancements

- Reactions (👍 ❤️)
- Comments on updates
- Mentions (@username)
- Private updates (only to matches)
- Daily digest notifications

