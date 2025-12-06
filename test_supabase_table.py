#!/usr/bin/env python3
"""Test if Supabase sessions table exists and what should happen."""

from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

if not url or not key:
    print("❌ SUPABASE_URL or SUPABASE_KEY not set")
    exit(1)

client = create_client(url, key)

print("🔍 Testing Supabase sessions table...")
print()

# Test if table exists
try:
    result = client.table('sessions').select('*').limit(1).execute()
    print("✅ Sessions table EXISTS!")
    print(f"   Found {len(result.data)} row(s)")
    if result.data:
        print(f"   Sample: {result.data[0]}")
    print()
except Exception as e:
    error_msg = str(e)
    if "Could not find the table" in error_msg or "PGRST205" in error_msg:
        print("❌ Sessions table DOES NOT EXIST")
        print()
        print("📋 To create it:")
        print("   1. Go to: https://kugbwhdljdigakumufwu.supabase.co")
        print("   2. Click 'SQL Editor'")
        print("   3. Run the SQL from setup_supabase_table.sql")
        print()
    else:
        print(f"❌ Error: {error_msg}")

# Show what SHOULD happen
print("=" * 60)
print("📝 What SHOULD happen when you send a message:")
print("=" * 60)
print()
print("1. ✅ Message received from phone")
print("2. ✅ LLM generates response")
print("3. ✅ Response sent back")
print("4. 💾 SAVE to Supabase sessions table:")
print("   - user_id: Your phone number (+13474591567)")
print("   - history: [")
print("       {role: 'user', content: 'HI', timestamp: '...'},")
print("       {role: 'assistant', content: 'it's great to see you again', timestamp: '...'}")
print("     ]")
print("   - last_seen: Current timestamp")
print()
print("5. 🧠 Next message will use this history for context!")
print()
print("=" * 60)

