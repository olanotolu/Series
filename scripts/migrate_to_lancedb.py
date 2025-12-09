#!/usr/bin/env python3
"""
Migration Script - Move embeddings from Supabase to LanceDB

Fetches all existing user embeddings and profiles from Supabase
and bulk inserts them into LanceDB for fast similarity search.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from embedding_service import get_supabase_client
from lancedb_service import store_embedding as lancedb_store_embedding

def migrate_embeddings():
    """Migrate all embeddings from Supabase to LanceDB."""
    print("🚀 Starting migration from Supabase to LanceDB...")
    
    # Get Supabase client
    client = get_supabase_client()
    if not client:
        print("❌ Could not connect to Supabase")
        return False
    
    try:
        # Fetch all user embeddings from Supabase
        print("📥 Fetching embeddings from Supabase...")
        response = client.table('user_embeddings').select('user_id, vector').execute()
        
        if not response.data:
            print("ℹ️  No embeddings found in Supabase")
            return True
        
        print(f"   Found {len(response.data)} embeddings in Supabase")
        
        # Fetch profiles for each user
        print("📥 Fetching user profiles...")
        migrated_count = 0
        failed_count = 0
        
        for embedding_row in response.data:
            user_id = embedding_row.get('user_id')
            vector = embedding_row.get('vector')
            
            if not user_id or not vector:
                print(f"   ⚠️  Skipping invalid embedding for user_id: {user_id}")
                failed_count += 1
                continue
            
            # Handle vector format
            if isinstance(vector, str):
                import json
                try:
                    vector = json.loads(vector)
                except:
                    # If it's a space-separated string, split it
                    vector = [float(x) for x in vector.strip('[]').split(',')]
            elif not isinstance(vector, list):
                print(f"   ⚠️  Invalid vector format for {user_id}")
                failed_count += 1
                continue
            
            # Get profile data from sessions table
            profile = None
            try:
                profile_response = client.table('sessions').select('name, school, age, hobbies').eq('user_id', user_id).limit(1).execute()
                if profile_response.data and len(profile_response.data) > 0:
                    profile = profile_response.data[0]
            except Exception as e:
                print(f"   ⚠️  Could not fetch profile for {user_id}: {e}")
            
            # Store in LanceDB
            try:
                success = lancedb_store_embedding(user_id, vector, profile)
                if success:
                    migrated_count += 1
                    print(f"   ✅ Migrated {user_id} ({profile.get('name', 'Unknown') if profile else 'No profile'})")
                else:
                    failed_count += 1
                    print(f"   ❌ Failed to migrate {user_id}")
            except Exception as e:
                failed_count += 1
                print(f"   ❌ Error migrating {user_id}: {e}")
        
        print(f"\n✅ Migration complete!")
        print(f"   Migrated: {migrated_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total: {len(response.data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("LanceDB Migration Script")
    print("=" * 60)
    print()
    
    success = migrate_embeddings()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("   LanceDB is now ready for fast similarity search.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
