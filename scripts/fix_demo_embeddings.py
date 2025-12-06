#!/usr/bin/env python3
"""
Generate embeddings for existing demo users.
Run this after fixing the embedding dimension issue.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_service import generate_user_embedding, store_embedding

load_dotenv()

def fix_embeddings():
    """Generate embeddings for all users who don't have them yet."""
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ SUPABASE_URL or SUPABASE_KEY not set")
        return False
    
    supabase = create_client(url, key)
    
    print("🔧 Generating embeddings for existing users...")
    print("")
    
    # Get all users with completed onboarding
    response = supabase.table('sessions').select('user_id, name, school, age, hobbies').eq('onboarding_complete', True).execute()
    
    if not response.data:
        print("⚠️  No users found with completed onboarding")
        return False
    
    # Get users who already have embeddings
    embeddings_response = supabase.table('user_embeddings').select('user_id').execute()
    existing_embeddings = {row['user_id'] for row in (embeddings_response.data or [])}
    
    fixed_count = 0
    
    for user in response.data:
        user_id = user['user_id']
        name = user.get('name', user_id)
        
        if user_id in existing_embeddings:
            print(f"⏭️  {name} ({user_id}) already has embedding, skipping...")
            continue
        
        print(f"🧠 Generating embedding for {name} ({user_id})...")
        
        profile = {
            'name': user.get('name', ''),
            'school': user.get('school', ''),
            'age': str(user.get('age', '')),
            'hobbies': user.get('hobbies', '')
        }
        
        vector = generate_user_embedding(profile)
        
        if vector:
            if len(vector) != 1536:
                print(f"   ⚠️  Wrong dimension: {len(vector)} (expected 1536)")
                continue
            
            stored = store_embedding(user_id, vector)
            if stored:
                print(f"   ✅ Embedding stored ({len(vector)} dimensions)")
                fixed_count += 1
            else:
                print(f"   ❌ Failed to store embedding")
        else:
            print(f"   ❌ Failed to generate embedding")
        
        print("")
    
    print("=" * 60)
    print(f"✅ Generated {fixed_count} embeddings")
    print("")
    print("🧪 Test matching:")
    print("   python test_matching.py")
    
    return True

if __name__ == "__main__":
    success = fix_embeddings()
    exit(0 if success else 1)

