#!/usr/bin/env python3
"""
Quick test script to verify embedding generation works.
Run this to test your OpenAI API key and embedding service.
"""

from embedding_service import generate_user_embedding, store_embedding, get_user_vector
import os
from dotenv import load_dotenv

load_dotenv()

def test_embedding():
    print("🧪 Testing Embedding Service...")
    print("")
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.strip() == '' or api_key == 'sk-':
        print("❌ OPENAI_API_KEY not set or empty in .env")
        print("   Get your key from: https://platform.openai.com/api-keys")
        print("   Add to .env: OPENAI_API_KEY=sk-your-actual-key")
        return False
    
    print("✅ OPENAI_API_KEY found")
    print("")
    
    # Test profile
    profile = {
        'name': 'Test User',
        'school': 'Test University',
        'age': '20',
        'hobbies': 'coding, basketball, music'
    }
    
    print(f"📝 Test Profile:")
    print(f"   Name: {profile['name']}")
    print(f"   School: {profile['school']}")
    print(f"   Age: {profile['age']}")
    print(f"   Hobbies: {profile['hobbies']}")
    print("")
    
    # Generate embedding
    print("🧠 Generating embedding...")
    vector = generate_user_embedding(profile)
    
    if not vector:
        print("❌ Failed to generate embedding")
        return False
    
    print(f"✅ Generated {len(vector)}-dimensional vector")
    print(f"   First 5 values: {vector[:5]}")
    print(f"   Last 5 values: {vector[-5:]}")
    print("")
    
    # Test storage (use test phone number)
    test_user_id = '+1234567890'
    print(f"💾 Storing embedding for {test_user_id}...")
    stored = store_embedding(test_user_id, vector)
    
    if not stored:
        print("❌ Failed to store embedding")
        return False
    
    print("✅ Embedding stored!")
    print("")
    
    # Test retrieval
    print(f"📥 Retrieving embedding for {test_user_id}...")
    retrieved = get_user_vector(test_user_id)
    
    if not retrieved:
        print("❌ Failed to retrieve embedding")
        return False
    
    print(f"✅ Retrieved {len(retrieved)}-dimensional vector")
    print("")
    
    # Verify they match
    if len(vector) == len(retrieved):
        print("✅ Vector dimensions match!")
        print("")
        print("🎉 All tests passed! Embedding service is working.")
        return True
    else:
        print("❌ Vector dimensions don't match")
        return False

if __name__ == "__main__":
    success = test_embedding()
    exit(0 if success else 1)

