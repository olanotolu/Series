"""
Topic Suggester
Generates contextual topic suggestions based on common interests, recent topics, and participant profiles.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from embedding_service import get_supabase_client
from dotenv import load_dotenv

load_dotenv()

# Hugging Face for LLM-based topic suggestion
try:
    from huggingface_hub import AsyncInferenceClient
    HF_TOKEN = os.getenv('HF_TOKEN', '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')
    hf_client = None
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Hugging Face not available for topic suggestions")


async def init_hf_client():
    """Initialize Hugging Face client for LLM topic suggestion."""
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


def get_common_hobbies(group_chat_id: int) -> List[str]:
    """Get common hobbies/interests for a group chat from the match."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        gc = client.table('group_chats')\
            .select('common_hobbies, match_id')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        if gc.data and gc.data[0].get('common_hobbies'):
            return gc.data[0].get('common_hobbies', [])
        
        return []
    except Exception as e:
        print(f"   ⚠️  Error getting common hobbies: {e}")
        return []


def get_recent_topics(group_chat_id: int, limit: int = 5) -> List[str]:
    """Get recent conversation topics."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        topics = client.table('group_chat_topics')\
            .select('topic_text')\
            .eq('group_chat_id', group_chat_id)\
            .order('last_mentioned_at', desc=True)\
            .limit(limit)\
            .execute()
        
        if topics.data:
            return [t.get('topic_text') for t in topics.data if t.get('topic_text')]
        return []
    except Exception as e:
        print(f"   ⚠️  Error getting recent topics: {e}")
        return []


def get_participant_interests(group_chat_id: int) -> List[str]:
    """Get hobbies/interests from participant profiles."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # Get participants
        participants = client.table('group_chat_participants')\
            .select('user_id')\
            .eq('group_chat_id', group_chat_id)\
            .eq('is_ai', False)\
            .execute()
        
        if not participants.data:
            return []
        
        user_ids = [p.get('user_id') for p in participants.data if p.get('user_id')]
        if not user_ids:
            return []
        
        # Get profiles
        profiles = client.table('sessions')\
            .select('hobbies')\
            .in_('user_id', user_ids)\
            .execute()
        
        all_hobbies = []
        if profiles.data:
            for p in profiles.data:
                hobbies = p.get('hobbies', '')
                if hobbies:
                    # Split hobbies if comma-separated
                    hobby_list = [h.strip() for h in hobbies.split(',') if h.strip()]
                    all_hobbies.extend(hobby_list)
        
        # Return unique hobbies
        return list(set(all_hobbies))
        
    except Exception as e:
        print(f"   ⚠️  Error getting participant interests: {e}")
        return []


async def generate_topic_suggestions(group_chat_id: int, context: str = 'general', limit: int = 3) -> List[str]:
    """
    Generate contextual topic suggestions for a group chat.
    
    Args:
        group_chat_id: Internal database ID
        context: 'general', 'icebreaker', 'lull' (conversation lull), 'deep' (deeper topics)
        limit: Number of suggestions to generate
    
    Returns:
        List of topic suggestion strings
    """
    if not await init_hf_client():
        return []
    
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # Get group chat info
        gc = client.table('group_chats')\
            .select('display_name')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        display_name = gc.data[0].get('display_name', 'Group Chat') if gc.data else 'Group Chat'
        
        # Gather context
        common_hobbies = get_common_hobbies(group_chat_id)
        recent_topics = get_recent_topics(group_chat_id, limit=5)
        participant_interests = get_participant_interests(group_chat_id)
        
        # Build context string
        context_parts = []
        if common_hobbies:
            context_parts.append(f"Common interests: {', '.join(common_hobbies[:3])}")
        if participant_interests:
            unique_interests = [i for i in participant_interests if i not in common_hobbies]
            if unique_interests:
                context_parts.append(f"Individual interests: {', '.join(unique_interests[:3])}")
        if recent_topics:
            context_parts.append(f"Recently discussed: {', '.join(recent_topics[:3])}")
        
        context_str = "\n".join(context_parts) if context_parts else "No specific context available"
        
        # Determine suggestion style based on context
        if context == 'icebreaker':
            instruction = "Generate fun, light icebreaker questions that help people get to know each other."
        elif context == 'lull':
            instruction = "Generate engaging conversation starters to revive a quiet conversation. Make them interesting and easy to respond to."
        elif context == 'deep':
            instruction = "Generate deeper, more meaningful conversation topics that encourage thoughtful discussion."
        else:  # general
            instruction = "Generate interesting conversation topics that are relevant to the group's interests."
        
        # Generate suggestions using LLM
        prompt = f"""Generate {limit} conversation topic suggestions for a group chat called "{display_name}".

Context:
{context_str}

{instruction}

Requirements:
- Make topics engaging and easy to respond to
- Relate to their interests when possible
- Keep topics casual and friendly
- Each topic should be 1 short sentence or question

Format: Return one topic per line, no numbering or bullets.

Topic suggestions:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=150,
            temperature=0.8
        )
        
        # Parse suggestions (one per line)
        suggestions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # Remove numbering/bullets if present
            line = line.lstrip('0123456789.-) ').strip()
            if line and len(line) > 10:  # Filter out very short lines
                suggestions.append(line)
        
        # Limit to requested number
        return suggestions[:limit]
        
    except Exception as e:
        print(f"   ⚠️  Error generating topic suggestions: {e}")
        import traceback
        traceback.print_exc()
        return []


def should_suggest_topic(group_chat_id: int) -> bool:
    """
    Determine if a topic suggestion should be sent.
    Checks for conversation lulls or low engagement.
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Check last message time
        last_message = client.table('group_chat_messages')\
            .select('sent_at')\
            .eq('group_chat_id', group_chat_id)\
            .order('sent_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not last_message.data:
            return False
        
        last_msg_time = last_message.data[0].get('sent_at')
        if not last_msg_time:
            return False
        
        last_msg_dt = datetime.fromisoformat(last_msg_time.replace('Z', '+00:00'))
        now = datetime.now(last_msg_dt.tzinfo) if last_msg_dt.tzinfo else datetime.now()
        
        hours_since_last = (now - last_msg_dt).total_seconds() / 3600
        
        # Suggest topic if conversation has been quiet for 2+ hours
        # But not if it's been too long (use reminder system instead)
        return 2 <= hours_since_last <= 12
        
    except Exception as e:
        print(f"   ⚠️  Error checking if topic should be suggested: {e}")
        return False


async def get_contextual_suggestion(group_chat_id: int) -> Optional[str]:
    """
    Get a single contextual topic suggestion based on current conversation state.
    Returns None if no suggestion is needed.
    """
    if not should_suggest_topic(group_chat_id):
        return None
    
    suggestions = await generate_topic_suggestions(group_chat_id, context='lull', limit=1)
    if suggestions:
        return suggestions[0]
    return None

