"""
Group Chat Management
Handles group chat creation, tracking, and AI participation.
"""

from typing import Optional, List, Dict
from embedding_service import get_supabase_client


def get_group_chat_by_chat_id(chat_id: str) -> Optional[Dict]:
    """Get group chat info by Series API chat_id."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.table('group_chats').select('*').eq('chat_id', chat_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting group chat: {e}")
        return None


def create_group_chat_record(chat_id: str, display_name: str, match_id: Optional[int] = None) -> Optional[int]:
    """Create a group chat record in the database. Returns the database ID."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        data = {
            'chat_id': chat_id,
            'display_name': display_name,
            'is_active': True
        }
        if match_id:
            data['match_id'] = match_id
        
        response = client.table('group_chats').insert(data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get('id')
        return None
    except Exception as e:
        print(f"   ⚠️  Error creating group chat record: {e}")
        return None


def add_group_chat_participant(group_chat_id: int, user_id: Optional[str], phone_number: str, is_ai: bool = False) -> bool:
    """Add a participant to a group chat."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        data = {
            'group_chat_id': group_chat_id,
            'phone_number': phone_number,
            'is_ai': is_ai
        }
        if user_id:
            data['user_id'] = user_id
        
        client.table('group_chat_participants').insert(data).execute()
        return True
    except Exception as e:
        print(f"   ⚠️  Error adding participant: {e}")
        return False


def get_group_chat_participants(group_chat_id: int) -> List[Dict]:
    """Get all participants in a group chat."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_participants').select('*').eq('group_chat_id', group_chat_id).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting participants: {e}")
        return []


def get_group_chat_participants_by_chat_id(chat_id: str) -> List[Dict]:
    """Get all participants in a group chat by Series API chat_id."""
    group_chat = get_group_chat_by_chat_id(chat_id)
    if not group_chat:
        return []
    
    return get_group_chat_participants(group_chat.get('id'))


def store_group_chat_message(group_chat_id: int, message_id: str, from_phone: str, from_user_id: Optional[str], text: str, is_from_ai: bool = False) -> bool:
    """Store a group chat message in the database."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        data = {
            'group_chat_id': group_chat_id,
            'message_id': message_id,
            'from_phone': from_phone,
            'text': text,
            'is_from_ai': is_from_ai
        }
        if from_user_id:
            data['from_user_id'] = from_user_id
        
        client.table('group_chat_messages').insert(data).execute()
        return True
    except Exception as e:
        print(f"   ⚠️  Error storing message: {e}")
        return False


def get_group_chat_history(group_chat_id: int, limit: int = 50) -> List[Dict]:
    """Get recent message history for a group chat."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_messages')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .order('sent_at', desc=True)\
            .limit(limit)\
            .execute()
        messages = response.data if response.data else []
        # Reverse to get chronological order
        return list(reversed(messages))
    except Exception as e:
        print(f"   ⚠️  Error getting history: {e}")
        return []


def get_group_chat_profiles(group_chat_id: int) -> List[Dict]:
    """Get profiles of all human participants in a group chat."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # Get participants
        participants = get_group_chat_participants(group_chat_id)
        human_participants = [p for p in participants if not p.get('is_ai')]
        
        if not human_participants:
            return []
        
        # Get profiles
        user_ids = [p.get('user_id') for p in human_participants if p.get('user_id')]
        if not user_ids:
            return []
        
        response = client.table('sessions')\
            .select('user_id, name, school, age, hobbies')\
            .in_('user_id', user_ids)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting profiles: {e}")
        return []


# Analytics functions
def get_group_chat_analytics(group_chat_id: int, period_type: str = 'daily') -> Optional[Dict]:
    """Get analytics for a group chat for a specific period."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        from datetime import datetime, timedelta
        
        if period_type == 'daily':
            period_start = datetime.now() - timedelta(days=1)
        else:  # weekly
            period_start = datetime.now() - timedelta(days=7)
        
        response = client.table('group_chat_analytics')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .eq('period_type', period_type)\
            .gte('period_start', period_start.isoformat())\
            .order('period_start', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting analytics: {e}")
        return None


def get_group_chat_topics(group_chat_id: int, limit: int = 10) -> List[Dict]:
    """Get topics for a group chat, ordered by relevance."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_topics')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .order('relevance_score', desc=True)\
            .order('last_mentioned_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting topics: {e}")
        return []


def get_participant_engagement(group_chat_id: int) -> List[Dict]:
    """Get engagement metrics for all participants."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_participant_engagement')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .order('engagement_score', desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting engagement: {e}")
        return []


def get_group_chat_summaries(group_chat_id: int, summary_type: str = 'daily', limit: int = 5) -> List[Dict]:
    """Get conversation summaries for a group chat."""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_summaries')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .eq('summary_type', summary_type)\
            .order('period_start', desc=True)\
            .limit(limit)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting summaries: {e}")
        return []


def get_group_chat_health_metrics(group_chat_id: int) -> Optional[Dict]:
    """Get health metrics for a group chat."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        gc = client.table('group_chats')\
            .select('health_score, avg_boring_score')\
            .eq('id', group_chat_id)\
            .limit(1)\
            .execute()
        
        if gc.data and len(gc.data) > 0:
            return gc.data[0]
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting health metrics: {e}")
        return None

