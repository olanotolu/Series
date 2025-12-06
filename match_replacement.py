"""
Match Replacement System
Detects low boring scores and offers users alternative matches.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from embedding_service import get_supabase_client
from user_matching import find_matches
from dotenv import load_dotenv

load_dotenv()

# Hugging Face for LLM-based message generation
try:
    from huggingface_hub import AsyncInferenceClient
    HF_TOKEN = os.getenv('HF_TOKEN', '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')
    hf_client = None
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Hugging Face not available for match replacement")


async def init_hf_client():
    """Initialize Hugging Face client for LLM message generation."""
    global hf_client
    if not HF_AVAILABLE:
        return False
    
    if hf_client is None:
        try:
            hf_client = AsyncInferenceClient(token=HF_TOKEN)
            return True
        except Exception as e:
            print(f"   ⚠️  Error initializing HF client: {e}")
            return False
    return True


def check_boring_score(group_chat_id: int, threshold: float = 4.0) -> bool:
    """
    Check if a group chat's average boring score is below the threshold.
    Lower scores = more interesting, Higher scores = more boring.
    So if avg_boring_score >= threshold, the conversation is boring.
    
    Args:
        group_chat_id: Internal database ID
        threshold: Boring score threshold (default 4.0 means if score is 4 or higher, it's boring)
    
    Returns:
        True if boring score is at or above threshold (conversation is boring)
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        gc = client.table('group_chats')\
            .select('avg_boring_score, last_replacement_offer_at')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        if not gc.data:
            return False
        
        avg_boring_score = gc.data[0].get('avg_boring_score')
        if avg_boring_score is None:
            return False
        
        # Check if replacement was offered recently (avoid spam)
        last_offer = gc.data[0].get('last_replacement_offer_at')
        if last_offer:
            last_offer_dt = datetime.fromisoformat(last_offer.replace('Z', '+00:00'))
            now = datetime.now(last_offer_dt.tzinfo) if last_offer_dt.tzinfo else datetime.now()
            hours_since_offer = (now - last_offer_dt).total_seconds() / 3600
            if hours_since_offer < 24:  # Don't offer again if offered in last 24 hours
                return False
        
        # Score is 1-10, where higher = more boring
        # If avg_boring_score >= threshold, conversation is boring
        return float(avg_boring_score) >= threshold
        
    except Exception as e:
        print(f"   ⚠️  Error checking boring score: {e}")
        return False


def get_group_chat_participants(group_chat_id: int) -> List[Dict]:
    """Get all participants in a group chat (excluding AI)."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        participants = client.table('group_chat_participants')\
            .select('user_id, phone_number')\
            .eq('group_chat_id', group_chat_id)\
            .eq('is_ai', False)\
            .execute()
        
        return participants.data if participants.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting participants: {e}")
        return []


def get_original_match_user_id(group_chat_id: int, user_id: str) -> Optional[str]:
    """Get the original match user_id for a given user in a group chat."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get the match from group chat
        gc = client.table('group_chats')\
            .select('match_id')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        if not gc.data or not gc.data[0].get('match_id'):
            return None
        
        match_id = gc.data[0].get('match_id')
        
        # Get the match record
        match = client.table('matches')\
            .select('user1_id, user2_id')\
            .eq('id', match_id)\
            .limit(1)\
            .execute()
        
        if not match.data:
            return None
        
        match_data = match.data[0]
        user1_id = match_data.get('user1_id')
        user2_id = match_data.get('user2_id')
        
        # Return the other user's ID
        if user1_id == user_id:
            return user2_id
        elif user2_id == user_id:
            return user1_id
        
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error getting original match: {e}")
        return None


async def find_replacement_match(user_id: str, exclude_user_id: str) -> Optional[Dict]:
    """
    Find the next best match for a user, excluding their current match.
    
    Args:
        user_id: User looking for replacement
        exclude_user_id: User to exclude (current match)
    
    Returns:
        Match dict with user_id, score, profile info, or None
    """
    try:
        # Get matches (excluding current match)
        matches = find_matches(user_id, limit=5)
        
        if not matches:
            return None
        
        # Filter out the current match
        filtered_matches = [m for m in matches if m.get('user_id') != exclude_user_id]
        
        if not filtered_matches:
            return None
        
        # Return the best match (first one, since they're sorted by score)
        return filtered_matches[0]
        
    except Exception as e:
        print(f"   ⚠️  Error finding replacement match: {e}")
        return None


async def generate_replacement_offer_message(replacement_user: Dict) -> str:
    """
    Generate a message offering a replacement match.
    
    Args:
        replacement_user: Dict with user_id, name, age, hobbies, score
    
    Returns:
        Message text
    """
    if not await init_hf_client():
        # Fallback message
        name = replacement_user.get('name', 'someone')
        age = replacement_user.get('age', '')
        hobbies = replacement_user.get('hobbies', '')
        score = replacement_user.get('score', 0)
        
        return f"Hey! I noticed the conversation has been a bit quiet. Would you like to try chatting with {name}{f', {age}' if age else ''}? They're interested in {hobbies}. Match strength: {int(score * 100)}%."
    
    try:
        name = replacement_user.get('name', 'someone')
        age = replacement_user.get('age', '')
        hobbies = replacement_user.get('hobbies', '')
        score = replacement_user.get('score', 0)
        
        prompt = f"""Write a friendly, casual private message offering a new match to a user.

The current conversation has been a bit quiet/dry, so you're offering them a new person to chat with.

New match details:
- Name: {name}
- Age: {age if age else 'Not specified'}
- Interests: {hobbies if hobbies else 'Various interests'}
- Match strength: {int(score * 100)}%

Write a brief (2-3 sentences), friendly message that:
1. Acknowledges the current conversation might not be clicking
2. Offers the new match as an alternative
3. Mentions why they might be a good fit (interests, match strength)
4. Asks if they want to try chatting with this new person

Keep it casual, non-pushy, and supportive.

Message:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=150,
            temperature=0.7
        )
        
        return response.strip()
        
    except Exception as e:
        print(f"   ⚠️  Error generating replacement message: {e}")
        # Fallback
        name = replacement_user.get('name', 'someone')
        return f"Hey! The conversation has been a bit quiet. Would you like to try chatting with {name} instead?"


def create_replacement_offer(group_chat_id: int, user_id: str, original_match_user_id: str, 
                            replacement_user_id: str) -> Optional[int]:
    """
    Create a replacement offer record in the database.
    
    Returns:
        Replacement offer ID if successful
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        data = {
            'group_chat_id': group_chat_id,
            'user_id': user_id,
            'original_match_user_id': original_match_user_id,
            'offered_replacement_user_id': replacement_user_id,
            'status': 'offered',
            'offered_at': datetime.now().isoformat()
        }
        
        response = client.table('group_chat_match_replacements').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            replacement_id = response.data[0].get('id')
            
            # Update group chat last_replacement_offer_at
            client.table('group_chats')\
                .update({'last_replacement_offer_at': datetime.now().isoformat()})\
                .eq('id', group_chat_id)\
                .execute()
            
            return replacement_id
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error creating replacement offer: {e}")
        return None


async def check_and_offer_replacements(group_chat_id: int) -> List[Dict]:
    """
    Check if group chat has low boring score and offer replacements to participants.
    
    Returns:
        List of replacement offers created (with user_id, message, etc.)
    """
    if not check_boring_score(group_chat_id, threshold=4.0):
        return []
    
    participants = get_group_chat_participants(group_chat_id)
    if len(participants) < 2:
        return []  # Need at least 2 participants
    
    offers = []
    
    for participant in participants:
        user_id = participant.get('user_id')
        if not user_id:
            continue
        
        # Get original match
        original_match_user_id = get_original_match_user_id(group_chat_id, user_id)
        if not original_match_user_id:
            continue
        
        # Find replacement match
        replacement_match = await find_replacement_match(user_id, original_match_user_id)
        if not replacement_match:
            continue
        
        # Generate offer message
        message = await generate_replacement_offer_message(replacement_match)
        
        # Create offer record
        replacement_id = create_replacement_offer(
            group_chat_id,
            user_id,
            original_match_user_id,
            replacement_match.get('user_id')
        )
        
        if replacement_id:
            offers.append({
                'replacement_id': replacement_id,
                'user_id': user_id,
                'phone_number': participant.get('phone_number'),
                'message': message,
                'replacement_user': replacement_match
            })
    
    return offers


def get_pending_replacement_offers(user_id: str) -> List[Dict]:
    """Get pending replacement offers for a user."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_match_replacements')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'offered')\
            .order('offered_at', desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting pending offers: {e}")
        return []


def accept_replacement(replacement_id: int) -> bool:
    """Mark a replacement offer as accepted."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.table('group_chat_match_replacements')\
            .update({
                'status': 'accepted',
                'responded_at': datetime.now().isoformat()
            })\
            .eq('id', replacement_id)\
            .execute()
        
        return True
    except Exception as e:
        print(f"   ⚠️  Error accepting replacement: {e}")
        return False


def decline_replacement(replacement_id: int) -> bool:
    """Mark a replacement offer as declined."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.table('group_chat_match_replacements')\
            .update({
                'status': 'declined',
                'responded_at': datetime.now().isoformat()
            })\
            .eq('id', replacement_id)\
            .execute()
        
        return True
    except Exception as e:
        print(f"   ⚠️  Error declining replacement: {e}")
        return False

