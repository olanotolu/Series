"""
Smart Reminder System
Detects quiet chats and sends personalized reminders with topic suggestions.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from embedding_service import get_supabase_client
from dotenv import load_dotenv

load_dotenv()

# Hugging Face for LLM-based reminder generation
try:
    from huggingface_hub import AsyncInferenceClient
    HF_TOKEN = os.getenv('HF_TOKEN', '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')
    hf_client = None
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Hugging Face not available for reminders")


async def init_hf_client():
    """Initialize Hugging Face client for LLM reminder generation."""
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


def detect_quiet_chats(hours_threshold: int = 24) -> List[Dict]:
    """
    Detect group chats that have been quiet for a specified number of hours.
    
    Args:
        hours_threshold: Number of hours of inactivity to consider "quiet"
    
    Returns:
        List of quiet group chat info
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        cutoff_time = (datetime.now() - timedelta(hours=hours_threshold)).isoformat()
        
        # Get group chats with no recent messages
        # First, get all active group chats
        group_chats = client.table('group_chats')\
            .select('id, chat_id, display_name, last_reminder_sent_at')\
            .eq('is_active', True)\
            .execute()
        
        if not group_chats.data:
            return []
        
        quiet_chats = []
        
        for gc in group_chats.data:
            gc_id = gc.get('id')
            
            # Check last message time
            last_message = client.table('group_chat_messages')\
                .select('sent_at')\
                .eq('group_chat_id', gc_id)\
                .order('sent_at', desc=True)\
                .limit(1)\
                .execute()
            
            if not last_message.data:
                # No messages at all - skip (might be new)
                continue
            
            last_msg_time = last_message.data[0].get('sent_at')
            if not last_msg_time:
                continue
            
            last_msg_dt = datetime.fromisoformat(last_msg_time.replace('Z', '+00:00'))
            now = datetime.now(last_msg_dt.tzinfo) if last_msg_dt.tzinfo else datetime.now()
            
            hours_since_last = (now - last_msg_dt).total_seconds() / 3600
            
            # Check if reminder was sent recently (avoid spam)
            last_reminder = gc.get('last_reminder_sent_at')
            if last_reminder:
                reminder_dt = datetime.fromisoformat(last_reminder.replace('Z', '+00:00'))
                hours_since_reminder = (now - reminder_dt).total_seconds() / 3600
                if hours_since_reminder < 12:  # Don't send reminder if one was sent in last 12 hours
                    continue
            
            if hours_since_last >= hours_threshold:
                quiet_chats.append({
                    'group_chat_id': gc_id,
                    'chat_id': gc.get('chat_id'),
                    'display_name': gc.get('display_name'),
                    'hours_since_last': hours_since_last
                })
        
        return quiet_chats
        
    except Exception as e:
        print(f"   ⚠️  Error detecting quiet chats: {e}")
        import traceback
        traceback.print_exc()
        return []


async def generate_reminder_message(group_chat_id: int, suggested_topics: List[str] = None) -> Optional[str]:
    """
    Generate a personalized reminder message for a quiet group chat.
    
    Args:
        group_chat_id: Internal database ID
        suggested_topics: List of topic suggestions
    
    Returns:
        Reminder message text
    """
    if not await init_hf_client():
        return "Hey! It's been a while since anyone messaged in this group chat. Want to pick up the conversation?"
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get group chat info
        gc = client.table('group_chats').select('*').eq('id', group_chat_id).limit(1).execute()
        if not gc.data:
            return None
        
        gc_info = gc.data[0]
        display_name = gc_info.get('display_name', 'Group Chat')
        common_hobbies = gc_info.get('common_hobbies', [])
        
        # Get participants
        participants = client.table('group_chat_participants')\
            .select('user_id')\
            .eq('group_chat_id', group_chat_id)\
            .eq('is_ai', False)\
            .execute()
        
        user_ids = [p.get('user_id') for p in (participants.data or []) if p.get('user_id')]
        names = []
        if user_ids:
            profiles = client.table('sessions')\
                .select('user_id, name')\
                .in_('user_id', user_ids)\
                .execute()
            if profiles.data:
                names = [p.get('name') for p in profiles.data if p.get('name')]
        
        # Build topic suggestions
        topics_str = ""
        if suggested_topics:
            topics_str = f"Here are some topics you could discuss: {', '.join(suggested_topics[:3])}"
        elif common_hobbies:
            topics_str = f"You both love {', '.join(common_hobbies[:2])}. Maybe talk about that?"
        
        # Generate reminder using LLM
        prompt = f"""Create a friendly, casual reminder message for a quiet group chat.
        
Group chat name: {display_name}
Participants: {', '.join(names) if names else 'friends'}
Common interests: {', '.join(common_hobbies) if common_hobbies else 'various topics'}
Topic suggestions: {topics_str if topics_str else 'None provided'}

Write a brief (1-2 sentences), friendly message that:
1. Acknowledges it's been quiet
2. Encourages conversation
3. Mentions topic suggestions if available

Keep it casual and warm. Don't be pushy.

Reminder message:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=100,
            temperature=0.7
        )
        
        return response.strip()
        
    except Exception as e:
        print(f"   ⚠️  Error generating reminder: {e}")
        return "Hey! It's been a while. Want to pick up the conversation?"


def create_reminder(group_chat_id: int, reminder_type: str, reminder_message: str, 
                    suggested_topics: List[str] = None, scheduled_for: Optional[datetime] = None) -> Optional[int]:
    """
    Create a reminder record in the database.
    
    Returns:
        Reminder ID if successful
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        if scheduled_for is None:
            scheduled_for = datetime.now()
        
        data = {
            'group_chat_id': group_chat_id,
            'reminder_type': reminder_type,
            'reminder_message': reminder_message,
            'status': 'pending',
            'scheduled_for': scheduled_for.isoformat()
        }
        
        if suggested_topics:
            data['suggested_topics'] = suggested_topics
        
        response = client.table('group_chat_reminders').insert(data).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0].get('id')
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error creating reminder: {e}")
        return None


def mark_reminder_sent(reminder_id: int):
    """Mark a reminder as sent."""
    client = get_supabase_client()
    if not client:
        return
    
    try:
        client.table('group_chat_reminders')\
            .update({
                'status': 'sent',
                'sent_at': datetime.now().isoformat()
            })\
            .eq('id', reminder_id)\
            .execute()
        
        # Update group chat last_reminder_sent_at
        reminder = client.table('group_chat_reminders')\
            .select('group_chat_id')\
            .eq('id', reminder_id)\
            .limit(1)\
            .execute()
        
        if reminder.data:
            gc_id = reminder.data[0].get('group_chat_id')
            client.table('group_chats')\
                .update({'last_reminder_sent_at': datetime.now().isoformat()})\
                .eq('id', gc_id)\
                .execute()
            
    except Exception as e:
        print(f"   ⚠️  Error marking reminder sent: {e}")


def get_pending_reminders() -> List[Dict]:
    """Get all pending reminders that are due to be sent."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        now = datetime.now().isoformat()
        
        response = client.table('group_chat_reminders')\
            .select('*, group_chats!inner(chat_id, display_name)')\
            .eq('status', 'pending')\
            .lte('scheduled_for', now)\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"   ⚠️  Error getting pending reminders: {e}")
        return []

