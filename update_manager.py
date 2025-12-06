#!/usr/bin/env python3
"""
Update Manager - Handle user updates (like Instagram Notes)

Allows users to post updates and view updates from their network.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from embedding_service import get_supabase_client


def post_update(user_id: str, update_text: str) -> bool:
    """
    Post a new update. Replaces existing active update for the user.
    
    Args:
        user_id: User ID (phone number)
        update_text: Update text (max 500 chars)
    
    Returns:
        True if successful, False otherwise
    """
    if not update_text or len(update_text.strip()) < 3:
        print(f"   ⚠️  Update text too short")
        return False
    
    # Limit update text length
    update_text = update_text.strip()[:500]
    
    client = get_supabase_client()
    if not client:
        print(f"   ⚠️  Supabase client not available")
        return False
    
    try:
        # IMPORTANT: Each user can only have ONE active update at a time
        # Deactivate ALL existing active updates for this user before creating new one
        deactivate_result = client.table('user_updates')\
            .update({'is_active': False})\
            .eq('user_id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        if deactivate_result.data:
            print(f"   🔄 Deactivated {len(deactivate_result.data)} existing update(s) for {user_id}")
        
        # Create new update (expires in 48 hours)
        expires_at = (datetime.utcnow() + timedelta(hours=48)).isoformat()
        
        data = {
            'user_id': user_id,
            'update_text': update_text,
            'is_active': True,
            'expires_at': expires_at,
            'view_count': 0
        }
        
        result = client.table('user_updates').insert(data).execute()
        
        if result.data:
            print(f"   ✅ Update posted for {user_id} (replaced previous update)")
            return True
        else:
            print(f"   ⚠️  Failed to post update")
            return False
            
    except Exception as e:
        print(f"   ⚠️  Error posting update: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_updates_feed(limit: int = 20, exclude_user_id: Optional[str] = None) -> List[Dict]:
    """
    Get feed of all active updates, ordered by newest first.
    
    Args:
        limit: Maximum number of updates to return
        exclude_user_id: Optional user ID to exclude from results
    
    Returns:
        List of update dictionaries with user info
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # Get active updates (each user should only have one active update)
        query = client.table('user_updates')\
            .select('id, user_id, update_text, created_at, view_count')\
            .eq('is_active', True)\
            .order('created_at', desc=True)\
            .limit(limit * 2)  # Get more to filter duplicates
        
        if exclude_user_id:
            query = query.neq('user_id', exclude_user_id)
        
        result = query.execute()
        
        if not result.data:
            return []
        
        # Ensure only one update per user (get the most recent one)
        # Since post_update deactivates old ones, this is a safeguard
        seen_users = {}
        unique_updates = []
        for update in result.data:
            user_id = update['user_id']
            if user_id not in seen_users:
                seen_users[user_id] = True
                unique_updates.append(update)
                if len(unique_updates) >= limit:
                    break
        
        # Get user names for each update
        user_ids = list(set([u['user_id'] for u in unique_updates]))
        
        users_result = client.table('sessions')\
            .select('user_id, name')\
            .in_('user_id', user_ids)\
            .execute()
        
        user_map = {u['user_id']: u.get('name', 'Unknown') for u in (users_result.data or [])}
        
        # Enrich updates with user names
        enriched_updates = []
        for update in unique_updates:
            user_id = update['user_id']
            user_name = user_map.get(user_id, 'Unknown')
            
            enriched_updates.append({
                'id': update['id'],
                'user_id': user_id,
                'user_name': user_name,
                'update_text': update['update_text'],
                'created_at': update['created_at'],
                'view_count': update.get('view_count', 0)
            })
        
        return enriched_updates
        
    except Exception as e:
        print(f"   ⚠️  Error getting updates feed: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_updates_feed(updates: List[Dict]) -> str:
    """
    Format updates list into readable feed message.
    
    Args:
        updates: List of update dictionaries
    
    Returns:
        Formatted string message
    """
    if not updates:
        return "No updates in your network right now. Be the first to post one!"
    
    lines = ["📢 Updates from your network:\n"]
    
    for update in updates:
        user_name = update.get('user_name', 'Unknown')
        update_text = update.get('update_text', '')
        created_at = update.get('created_at', '')
        
        # Format time ago
        time_ago = format_time_ago(created_at)
        
        lines.append(f"• {user_name}: {update_text} ({time_ago})")
    
    lines.append("\nType /update <your message> to share your own update!")
    
    return "\n".join(lines)


def format_time_ago(timestamp_str: str) -> str:
    """
    Format timestamp as 'X hours ago' etc.
    
    Args:
        timestamp_str: ISO format timestamp string
    
    Returns:
        Formatted time string
    """
    if not timestamp_str:
        return "just now"
    
    try:
        # Parse timestamp
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        
        # Handle timezone-aware datetime
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)
        else:
            now = datetime.utcnow()
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago" if minutes == 1 else f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago" if hours == 1 else f"{hours}h ago"
        elif diff.total_seconds() < 604800:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago" if days == 1 else f"{days}d ago"
        else:
            weeks = int(diff.total_seconds() / 604800)
            return f"{weeks}w ago" if weeks == 1 else f"{weeks}w ago"
            
    except Exception as e:
        print(f"   ⚠️  Error formatting time: {e}")
        return "recently"


def get_user_updates(user_id: str) -> List[Dict]:
    """
    Get user's own updates.
    
    Args:
        user_id: User ID
    
    Returns:
        List of user's updates
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        result = client.table('user_updates')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"   ⚠️  Error getting user updates: {e}")
        return []


def expire_old_updates():
    """
    Mark old updates as inactive (expired).
    Should be called periodically (e.g., daily cron job).
    """
    client = get_supabase_client()
    if not client:
        return
    
    try:
        # Update expired updates
        result = client.table('user_updates')\
            .update({'is_active': False})\
            .eq('is_active', True)\
            .lt('expires_at', datetime.utcnow().isoformat())\
            .execute()
        
        if result.data:
            print(f"   ✅ Expired {len(result.data)} old updates")
            
    except Exception as e:
        print(f"   ⚠️  Error expiring updates: {e}")

