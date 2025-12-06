#!/usr/bin/env python3
"""
Add demo users to test the AI-powered matching system.
Creates diverse profiles with different hobbies to demonstrate matching.
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_service import generate_user_embedding, store_embedding

load_dotenv()

# Demo users with diverse profiles
DEMO_USERS = [
    {
        'user_id': '+15551000001',
        'name': 'Alex',
        'school': 'MIT',
        'age': 20,
        'hobbies': 'coding, machine learning, basketball, chess'
    },
    {
        'user_id': '+15551000002',
        'name': 'Sarah',
        'school': 'Stanford',
        'age': 21,
        'hobbies': 'coding, basketball, music, photography'
    },
    {
        'user_id': '+15551000003',
        'name': 'Jordan',
        'school': 'UC Berkeley',
        'age': 19,
        'hobbies': 'music, guitar, basketball, hiking'
    },
    {
        'user_id': '+15551000004',
        'name': 'Taylor',
        'school': 'Harvard',
        'age': 22,
        'hobbies': 'reading, writing, chess, philosophy'
    },
    {
        'user_id': '+15551000005',
        'name': 'Casey',
        'school': 'NYU',
        'age': 20,
        'hobbies': 'photography, music, art, design'
    },
    {
        'user_id': '+15551000006',
        'name': 'Morgan',
        'school': 'Georgia Tech',
        'age': 21,
        'hobbies': 'coding, machine learning, data science, chess'
    },
    {
        'user_id': '+15551000007',
        'name': 'Riley',
        'school': 'UCLA',
        'age': 19,
        'hobbies': 'basketball, fitness, hiking, outdoor sports'
    },
    {
        'user_id': '+15551000008',
        'name': 'Sam',
        'school': 'Columbia',
        'age': 22,
        'hobbies': 'writing, reading, philosophy, debate'
    }
]

def add_demo_users():
    """Add demo users to Supabase and generate their embeddings."""
    
    # Initialize Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ SUPABASE_URL or SUPABASE_KEY not set in .env")
        return False
    
    supabase = create_client(url, key)
    
    print("🚀 Adding demo users...")
    print("")
    
    added_count = 0
    embedding_count = 0
    
    for user in DEMO_USERS:
        user_id = user['user_id']
        name = user['name']
        
        try:
            # Check if user already exists
            existing = supabase.table('sessions').select('user_id').eq('user_id', user_id).execute()
            
            if existing.data:
                print(f"⏭️  {name} ({user_id}) already exists, skipping...")
                continue
            
            # Create user session
            session_data = {
                'user_id': user_id,
                'name': user['name'],
                'school': user['school'],
                'age': user['age'],
                'hobbies': user['hobbies'],
                'onboarding_complete': True,
                'onboarding_state': 'complete',
                'history': []
            }
            
            result = supabase.table('sessions').insert(session_data).execute()
            
            if result.data:
                print(f"✅ Added {name} ({user_id})")
                print(f"   School: {user['school']}, Age: {user['age']}")
                print(f"   Hobbies: {user['hobbies']}")
                added_count += 1
                
                # Generate embedding
                print(f"   🧠 Generating embedding...")
                profile = {
                    'name': user['name'],
                    'school': user['school'],
                    'age': str(user['age']),
                    'hobbies': user['hobbies']
                }
                
                vector = generate_user_embedding(profile)
                
                if vector:
                    stored = store_embedding(user_id, vector)
                    if stored:
                        print(f"   ✅ Embedding stored")
                        embedding_count += 1
                    else:
                        print(f"   ⚠️  Failed to store embedding")
                else:
                    print(f"   ⚠️  Failed to generate embedding")
                
                print("")
            else:
                print(f"❌ Failed to add {name}")
                print("")
                
        except Exception as e:
            print(f"❌ Error adding {name}: {e}")
            print("")
    
    print("=" * 60)
    print(f"✅ Added {added_count} users")
    print(f"✅ Generated {embedding_count} embeddings")
    print("")
    print("🎯 Expected Matches:")
    print("  • Alex ↔ Sarah (coding, basketball)")
    print("  • Alex ↔ Morgan (coding, ML, chess)")
    print("  • Sarah ↔ Jordan (basketball, music)")
    print("  • Sarah ↔ Casey (music, photography)")
    print("  • Jordan ↔ Casey (music)")
    print("  • Taylor ↔ Sam (reading, writing, philosophy)")
    print("  • Morgan ↔ Alex (coding, ML, chess)")
    print("")
    print("🧪 Test matching by running:")
    print("  python test_matching.py")
    
    return True

if __name__ == "__main__":
    success = add_demo_users()
    exit(0 if success else 1)

