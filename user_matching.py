#!/usr/bin/env python3
"""
User Matching Module - AI-Powered Matching with Embeddings

Finds compatible users using vector similarity on personality embeddings.
Uses LanceDB for fast similarity search, with Supabase fallback.
Generates Series-style match messages.
"""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Supabase client
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  Supabase not installed. Install with: pip install supabase")

# LanceDB client
try:
    from lancedb_service import search_similar_users
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("⚠️  LanceDB service not available")

from embedding_service import get_user_vector, get_supabase_client

def find_matches(user_id: str, limit: int = 5) -> List[Dict]:
    """
    Find matching users using LanceDB vector similarity search (primary).
    Falls back to Supabase if LanceDB is unavailable.
    
    Args:
        user_id: Current user's phone number
        limit: Maximum number of matches to return
    
    Returns:
        List of matches with user_id, score, and profile data
    """
    # Get user's embedding vector
    user_vector = get_user_vector(user_id)
    if not user_vector:
        print(f"   ⚠️  No embedding found for {user_id}")
        return []
    
    # Try LanceDB first (fast, scalable)
    if LANCEDB_AVAILABLE:
        try:
            matches = search_similar_users(user_vector, exclude_user_id=user_id, limit=limit)
            if matches:
                print(f"   ✅ Found {len(matches)} match(es) via LanceDB for {user_id}")
                return matches
            else:
                print(f"   ℹ️  No matches found in LanceDB for {user_id}")
        except Exception as e:
            print(f"   ⚠️  LanceDB search error (using Supabase fallback): {e}")
    
    # Fallback to Supabase (legacy support)
    return find_matches_supabase_fallback(user_id, limit)

def find_matches_supabase_fallback(user_id: str, limit: int = 5) -> List[Dict]:
    """
    Fallback matching using Supabase (for legacy support or when LanceDB unavailable).
    """
    client = get_supabase_client()
    if not client:
        return []
    
    user_vector = get_user_vector(user_id)
    if not user_vector:
        return []
    
    try:
        # Get all other users' embeddings
        response = client.table('user_embeddings').select('user_id, vector').neq('user_id', user_id).execute()
        
        if not response.data:
            return []
        
        # Calculate cosine similarity manually
        matches = []
        for row in response.data:
            other_vector = row.get('vector')
            if not other_vector:
                continue
            
            # Handle vector format (list or string)
            if isinstance(other_vector, str):
                import json
                try:
                    other_vector = json.loads(other_vector)
                except:
                    # If it's a space-separated string, split it
                    other_vector = [float(x) for x in other_vector.strip('[]').split(',')]
            elif not isinstance(other_vector, list):
                continue
            
            # Calculate cosine similarity
            score = cosine_similarity(user_vector, other_vector)
            
            matches.append({
                'user_id': row.get('user_id'),
                'score': score
            })
        
        # Sort by score (highest first) and return top matches
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]
        
    except Exception as e:
        print(f"   ❌ Error in fallback matching: {e}")
        return []

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def get_match_profiles(match_results: List[Dict]) -> List[Dict]:
    """
    Enrich match results with full profile data.
    If matches already have profile data (from LanceDB), use it.
    Otherwise, fetch from Supabase.
    
    Args:
        match_results: List of matches with user_id and score (may include profile data)
    
    Returns:
        List of enriched matches with profile data
    """
    enriched_matches = []
    
    for match in match_results:
        user_id = match.get('user_id')
        if not user_id:
            continue
        
        # Check if profile data already exists (from LanceDB)
        if all(key in match for key in ['name', 'school', 'age', 'hobbies']):
            # Already enriched, use as-is
            enriched_matches.append(match)
            continue
        
        # Fetch from Supabase
        client = get_supabase_client()
        if not client:
            continue
        
        try:
            # Get profile
            response = client.table('sessions').select('name, school, age, hobbies').eq('user_id', user_id).execute()
            
            if response.data and len(response.data) > 0:
                profile = response.data[0]
                enriched_match = {
                    'user_id': user_id,
                    'score': match.get('score', 0.0),
                    'name': profile.get('name'),
                    'school': profile.get('school'),
                    'age': profile.get('age'),
                    'hobbies': profile.get('hobbies')
                }
                enriched_matches.append(enriched_match)
        except Exception as e:
            print(f"   ⚠️  Error getting profile for {user_id}: {e}")
            continue
    
    return enriched_matches

def calculate_common_hobbies(hobbies1: str, hobbies2: str) -> List[str]:
    """
    Calculate common hobbies between two users.
    
    Args:
        hobbies1: First user's hobbies (comma-separated or space-separated)
        hobbies2: Second user's hobbies
    
    Returns:
        List of common hobby words/phrases
    """
    if not hobbies1 or not hobbies2:
        return []
    
    # Normalize and split hobbies
    def normalize_hobbies(hobbies_str):
        # Split by comma, semicolon, or space
        import re
        hobbies = re.split(r'[,;]|\s+', hobbies_str.lower())
        # Remove empty strings and strip
        return [h.strip() for h in hobbies if h.strip()]
    
    hobbies1_list = normalize_hobbies(hobbies1)
    hobbies2_list = normalize_hobbies(hobbies2)
    
    # Find common hobbies (case-insensitive)
    common = []
    for h1 in hobbies1_list:
        for h2 in hobbies2_list:
            # Check for exact match or substring match
            if h1 == h2 or (len(h1) > 3 and h1 in h2) or (len(h2) > 3 and h2 in h1):
                if h1 not in common:
                    common.append(h1)
    
    return common

def format_match_message(matched_profile: Dict, score: float, common_hobbies: List[str] = None) -> str:
    """
    Generate Series-style cinematic match message.
    
    Args:
        matched_profile: Dict with name, school, age, hobbies
        score: Similarity score (0.0 to 1.0)
        common_hobbies: List of common hobbies (optional)
    
    Returns:
        Formatted match message
    """
    name = matched_profile.get('name', 'Someone')
    age = matched_profile.get('age', '')
    school = matched_profile.get('school', '')
    hobbies = matched_profile.get('hobbies', '')
    
    # Calculate common hobbies if not provided
    if common_hobbies is None:
        # This would need the current user's hobbies - handled in consumer
        common_hobbies = []
    
    # Format age
    age_str = f"{age}" if age else ""
    
    # Format school
    school_str = school if school else "a school"
    
    # Format common hobbies
    if common_hobbies:
        if len(common_hobbies) == 1:
            hobbies_str = common_hobbies[0]
        elif len(common_hobbies) == 2:
            hobbies_str = f"{common_hobbies[0]} and {common_hobbies[1]}"
        else:
            hobbies_str = ", ".join(common_hobbies[:-1]) + f", and {common_hobbies[-1]}"
    else:
        hobbies_str = "similar interests"
    
    # Calculate match percentage
    match_percent = int(score * 100)
    
    # Generate message
    message = f"""Alright—your profile is live. And we already found someone who feels *weirdly close* to you.

**{name}**{f", {age}" if age_str else ""}, {school_str}.
Match strength: **{match_percent}%**.

You two share the same energy around: {hobbies_str}.

Want me to open the chat?"""
    
    return message

