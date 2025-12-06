#!/usr/bin/env python3
"""
Test the matching system with demo users.
Shows which users match with each other and their similarity scores.
"""

import os
from dotenv import load_dotenv
from user_matching import find_matches, get_match_profiles, format_match_message, calculate_common_hobbies
from session_manager_supabase import SessionManager

load_dotenv()

def test_matching():
    """Test matching between demo users."""
    
    print("🧪 Testing Matching System")
    print("=" * 60)
    print("")
    
    session_manager = SessionManager()
    
    # Demo user IDs
    demo_users = [
        '+15551000001',  # Alex
        '+15551000002',  # Sarah
        '+15551000003',  # Jordan
        '+15551000004',  # Taylor
        '+15551000005',  # Casey
        '+15551000006',  # Morgan
        '+15551000007',  # Riley
        '+15551000008',  # Sam
    ]
    
    print("🔍 Finding matches for each user...")
    print("")
    
    all_matches = {}
    
    for user_id in demo_users:
        # Get user profile
        profile = session_manager.get_profile(user_id)
        if not profile or not profile.get('name'):
            print(f"⏭️  User {user_id} not found, skipping...")
            continue
        
        name = profile.get('name', user_id)
        print(f"👤 {name} ({user_id})")
        print(f"   Profile: {profile.get('school')}, Age {profile.get('age')}")
        print(f"   Hobbies: {profile.get('hobbies')}")
        print("")
        
        # Find matches
        matches = find_matches(user_id, limit=3)
        
        if not matches:
            print("   ⚠️  No matches found")
            print("")
            continue
        
        # Get enriched match data
        enriched = get_match_profiles(matches)
        
        if not enriched:
            print("   ⚠️  No enriched matches")
            print("")
            continue
        
        print(f"   🎯 Top {len(enriched)} matches:")
        
        for i, match in enumerate(enriched, 1):
            match_name = match.get('name', 'Unknown')
            match_score = match.get('score', 0.0)
            match_hobbies = match.get('hobbies', '')
            
            # Calculate common hobbies
            current_hobbies = profile.get('hobbies', '')
            common = calculate_common_hobbies(current_hobbies, match_hobbies)
            
            score_percent = int(match_score * 100)
            
            print(f"      {i}. {match_name} - {score_percent}% match")
            print(f"         School: {match.get('school')}, Age: {match.get('age')}")
            if common:
                print(f"         Common: {', '.join(common)}")
            print("")
        
        all_matches[user_id] = enriched
        print("   " + "-" * 50)
        print("")
    
    # Show example match message
    if all_matches:
        first_user = list(all_matches.keys())[0]
        matches = all_matches[first_user]
        
        if matches:
            profile = session_manager.get_profile(first_user)
            top_match = matches[0]
            
            current_hobbies = profile.get('hobbies', '')
            matched_hobbies = top_match.get('hobbies', '')
            common = calculate_common_hobbies(current_hobbies, matched_hobbies)
            
            match_msg = format_match_message(top_match, top_match.get('score', 0.0), common)
            
            print("=" * 60)
            print("📨 Example Match Message:")
            print("=" * 60)
            print(match_msg)
            print("")
    
    print("✅ Matching test complete!")
    return True

if __name__ == "__main__":
    success = test_matching()
    exit(0 if success else 1)

