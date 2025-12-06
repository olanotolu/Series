"""
Conversation Summarizer
Generates daily/weekly conversation summaries for group chats.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from embedding_service import get_supabase_client
from dotenv import load_dotenv

load_dotenv()

# Hugging Face for LLM-based summarization
try:
    from huggingface_hub import AsyncInferenceClient
    HF_TOKEN = os.getenv('HF_TOKEN', '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')
    hf_client = None
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Hugging Face not available for summarization")


async def init_hf_client():
    """Initialize Hugging Face client for LLM summarization."""
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


async def generate_summary(group_chat_id: int, summary_type: str = 'daily') -> Optional[Dict]:
    """
    Generate a conversation summary for a group chat.
    
    Args:
        group_chat_id: Internal database ID of the group chat
        summary_type: 'daily' or 'weekly'
    
    Returns:
        Dict with summary_text, key_topics, participant_contributions
    """
    if not await init_hf_client():
        return None
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get group chat info
        group_chat = client.table('group_chats').select('*').eq('id', group_chat_id).limit(1).execute()
        if not group_chat.data:
            return None
        
        group_chat_info = group_chat.data[0]
        display_name = group_chat_info.get('display_name', 'Group Chat')
        
        # Calculate time range
        if summary_type == 'daily':
            period_start = datetime.now() - timedelta(days=1)
            period_end = datetime.now()
        else:  # weekly
            period_start = datetime.now() - timedelta(days=7)
            period_end = datetime.now()
        
        # Get messages in period
        messages = client.table('group_chat_messages')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .gte('sent_at', period_start.isoformat())\
            .lt('sent_at', period_end.isoformat())\
            .order('sent_at', desc=False)\
            .execute()
        
        if not messages.data or len(messages.data) == 0:
            return None
        
        # Get participant profiles
        participants = client.table('group_chat_participants')\
            .select('user_id, phone_number')\
            .eq('group_chat_id', group_chat_id)\
            .eq('is_ai', False)\
            .execute()
        
        participant_map = {}
        if participants.data:
            user_ids = [p.get('user_id') for p in participants.data if p.get('user_id')]
            if user_ids:
                profiles = client.table('sessions')\
                    .select('user_id, name')\
                    .in_('user_id', user_ids)\
                    .execute()
                if profiles.data:
                    for p in profiles.data:
                        participant_map[p.get('user_id')] = p.get('name', 'Someone')
        
        # Format messages for LLM
        conversation_text = ""
        participant_contributions = {}
        
        for msg in messages.data:
            if msg.get('is_from_ai'):
                continue
            
            user_id = msg.get('from_user_id')
            name = participant_map.get(user_id, 'Someone')
            text = msg.get('text', '')
            
            if text:
                conversation_text += f"{name}: {text}\n"
                
                # Track contributions
                if user_id:
                    if user_id not in participant_contributions:
                        participant_contributions[user_id] = {'name': name, 'message_count': 0}
                    participant_contributions[user_id]['message_count'] += 1
        
        if not conversation_text.strip():
            return None
        
        # Get key topics
        topics = client.table('group_chat_topics')\
            .select('topic_text, mention_count')\
            .eq('group_chat_id', group_chat_id)\
            .gte('last_mentioned_at', period_start.isoformat())\
            .order('mention_count', desc=True)\
            .limit(5)\
            .execute()
        
        key_topics = [t.get('topic_text') for t in (topics.data or [])]
        
        # Generate summary using LLM
        prompt = f"""Summarize this {summary_type} conversation from a group chat called "{display_name}".

Key topics discussed: {', '.join(key_topics) if key_topics else 'Various topics'}

Conversation:
{conversation_text[:2000]}  # Limit to avoid token limits

Create a friendly, engaging summary (2-3 sentences) that:
1. Highlights the main topics discussed
2. Mentions who participated actively
3. Captures the overall vibe/energy of the conversation

Summary:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=200,
            temperature=0.7
        )
        
        summary_text = response.strip()
        
        # Format participant contributions
        contributions_dict = {}
        for user_id, data in participant_contributions.items():
            contributions_dict[user_id] = f"{data['name']} sent {data['message_count']} message(s)"
        
        # Store summary in database
        summary_data = {
            'group_chat_id': group_chat_id,
            'summary_type': summary_type,
            'summary_text': summary_text,
            'key_topics': key_topics,
            'participant_contributions': contributions_dict,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat()
        }
        
        client.table('group_chat_summaries').insert(summary_data).execute()
        
        # Update last_summary_at
        client.table('group_chats')\
            .update({'last_summary_at': datetime.now().isoformat()})\
            .eq('id', group_chat_id)\
            .execute()
        
        return {
            'summary_text': summary_text,
            'key_topics': key_topics,
            'participant_contributions': contributions_dict,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat()
        }
        
    except Exception as e:
        print(f"   ⚠️  Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_latest_summary(group_chat_id: int, summary_type: str = 'daily') -> Optional[Dict]:
    """Get the latest summary for a group chat."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.table('group_chat_summaries')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .eq('summary_type', summary_type)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting summary: {e}")
        return None


def should_generate_summary(group_chat_id: int, summary_type: str = 'daily') -> bool:
    """Check if a summary should be generated (hasn't been generated recently)."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Check last summary time
        group_chat = client.table('group_chats')\
            .select('last_summary_at')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        if not group_chat.data:
            return True
        
        last_summary = group_chat.data[0].get('last_summary_at')
        if not last_summary:
            return True
        
        last_summary_dt = datetime.fromisoformat(last_summary.replace('Z', '+00:00'))
        now = datetime.now(last_summary_dt.tzinfo) if last_summary_dt.tzinfo else datetime.now()
        
        if summary_type == 'daily':
            # Generate if last summary was more than 20 hours ago
            return (now - last_summary_dt).total_seconds() > 20 * 3600
        else:  # weekly
            # Generate if last summary was more than 6 days ago
            return (now - last_summary_dt).total_seconds() > 6 * 24 * 3600
        
    except Exception as e:
        print(f"   ⚠️  Error checking summary: {e}")
        return False

