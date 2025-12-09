#!/usr/bin/env python3
"""
Embedding Service - OpenAI Embeddings for User Matching

Generates personality embeddings for users using OpenAI's text-embedding-3-large model.
Stores embeddings in both Supabase (pgvector) and LanceDB for similarity search.
"""

import os
from typing import List, Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not installed. Install with: pip install openai")

# Supabase client
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  Supabase not installed. Install with: pip install supabase")

# LanceDB client
try:
    from lancedb_service import store_embedding as lancedb_store_embedding, get_embedding as lancedb_get_embedding
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("⚠️  LanceDB service not available")

# Initialize clients
openai_client = None
supabase_client = None

def get_openai_client():
    """Get or create OpenAI client."""
    global openai_client
    if not OPENAI_AVAILABLE:
        return None
    
    if openai_client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not set in .env")
            return None
        openai_client = OpenAI(api_key=api_key)
    
    return openai_client

def get_supabase_client():
    """Get or create Supabase client.
    Uses service_role key if available (for admin/backend operations),
    otherwise falls back to anon key.
    """
    global supabase_client
    if not SUPABASE_AVAILABLE:
        return None
    
    if supabase_client is None:
        url = os.getenv('SUPABASE_URL')
        # Prefer service_role key for admin operations (bypasses RLS)
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not url or not key:
            print("⚠️  SUPABASE_URL or SUPABASE_KEY not set")
            return None
        
        # Check if using service_role key
        using_service_role = bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        if using_service_role:
            print("   ✅ Using Supabase service_role key (admin access)")
        else:
            print("   ⚠️  Using Supabase anon key (may have RLS restrictions)")
        
        supabase_client = create_client(url, key)
    
    return supabase_client

def generate_user_embedding(profile: dict) -> Optional[List[float]]:
    """
    Generate embedding vector for user profile using OpenAI.
    
    Args:
        profile: Dict with name, school, age, hobbies
    
    Returns:
        1536-dimensional embedding vector, or None if error
    """
    client = get_openai_client()
    if not client:
        return None
    
    try:
        # Combine profile into text for embedding
        name = profile.get('name', '')
        school = profile.get('school', '')
        age = profile.get('age', '')
        hobbies = profile.get('hobbies', '')
        
        # Create personality text
        personality_text = f"""
Name: {name}
School: {school}
Age: {age}
Hobbies: {hobbies}
"""
        
        print(f"   🧠 Generating embedding for: {name} ({school}, {age})")
        
        # Call OpenAI embeddings API
        # text-embedding-3-large returns 3072 by default, but we need 1536 for pgvector
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=personality_text.strip(),
            dimensions=1536  # Specify 1536 dimensions to match database schema
        )
        
        vector = response.data[0].embedding
        
        print(f"   ✅ Generated {len(vector)}-dimensional embedding")
        return vector
        
    except Exception as e:
        print(f"   ❌ Error generating embedding: {e}")
        return None

def store_embedding(user_id: str, vector: List[float], profile: Optional[Dict] = None) -> bool:
    """
    Store user embedding in both Supabase (for backup/legacy) and LanceDB (for fast search).
    
    Args:
        user_id: User phone number
        vector: 1536-dimensional embedding vector
        profile: Optional dict with name, school, age, hobbies for LanceDB
    
    Returns:
        True if at least one storage succeeded, False otherwise
    """
    supabase_success = False
    lancedb_success = False
    
    # Store in Supabase (backup/legacy)
    client = get_supabase_client()
    if client:
        try:
            # Supabase pgvector expects the vector as a list/array
            # The Python client should handle the conversion automatically
            data = {
                'user_id': user_id,
                'vector': vector,  # Pass as list, Supabase will handle conversion
                'updated_at': 'now()'
            }
            
            # Upsert embedding
            result = client.table('user_embeddings').upsert(data).execute()
            supabase_success = True
            print(f"   ✅ Stored embedding in Supabase for {user_id}")
        except Exception as e:
            print(f"   ⚠️  Error storing embedding in Supabase: {e}")
    
    # Store in LanceDB (primary for fast search)
    if LANCEDB_AVAILABLE:
        try:
            lancedb_success = lancedb_store_embedding(user_id, vector, profile)
        except Exception as e:
            print(f"   ⚠️  Error storing embedding in LanceDB: {e}")
    
    # Return True if at least one succeeded
    return supabase_success or lancedb_success

def get_user_vector(user_id: str) -> Optional[List[float]]:
    """
    Retrieve user's embedding vector from database.
    Tries LanceDB first (faster), then falls back to Supabase.
    
    Args:
        user_id: User phone number
    
    Returns:
        Embedding vector, or None if not found
    """
    # Try LanceDB first (faster, primary storage)
    if LANCEDB_AVAILABLE:
        try:
            vector = lancedb_get_embedding(user_id)
            if vector:
                return vector
        except Exception as e:
            print(f"   ⚠️  Error retrieving vector from LanceDB: {e}")
    
    # Fallback to Supabase
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.table('user_embeddings').select('vector').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            vector = response.data[0].get('vector')
            if vector:
                # Supabase returns vector as list or string depending on version
                # Handle both cases
                if isinstance(vector, str):
                    import json
                    try:
                        vector = json.loads(vector)
                    except:
                        # If it's a space-separated string, split it
                        vector = [float(x) for x in vector.strip('[]').split(',')]
                elif isinstance(vector, list):
                    # Already a list, use as-is
                    pass
                return vector
        
        return None
        
    except Exception as e:
        print(f"   ❌ Error retrieving vector from Supabase: {e}")
        return None

