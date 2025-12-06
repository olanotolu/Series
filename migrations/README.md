# Database Migrations

Run these migrations in order in your Supabase SQL Editor:

## Migration Order

1. **setup_supabase_table.sql** - Initial schema (sessions, user_embeddings, matches)
2. **migrate_add_profile_columns.sql** - Add profile fields to sessions
3. **migrate_add_matching_tables.sql** - Matching system tables
4. **migrate_add_group_chats.sql** - Group chat tables
5. **migrate_add_pending_match.sql** - Pending match support
6. **migrate_group_chat_intelligence.sql** - Intelligence features
7. **migrate_add_user_updates.sql** - User updates feature
8. **fix_match_embeddings_rpc.sql** - Fix RPC function (if needed)
9. **verify_schema.sql** - Verify all tables exist

## Running Migrations

1. Go to Supabase Dashboard → SQL Editor
2. Copy and paste each migration file
3. Run in order
4. Verify with `verify_schema.sql`

## Notes

- All migrations are idempotent (safe to run multiple times)
- Use service_role key for migrations
- Check RLS policies after each migration

