"""
Group Chat Intelligence Module
Handles topic extraction, sentiment analysis, engagement analytics, and health scoring.
"""

import os
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from embedding_service import get_supabase_client
from dotenv import load_dotenv

load_dotenv()

# Hugging Face for LLM-based analysis
try:
    from huggingface_hub import AsyncInferenceClient
    HF_TOKEN = os.getenv('HF_TOKEN', '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')
    hf_client = None
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Hugging Face not available for intelligence analysis")


async def init_hf_client():
    """Initialize Hugging Face client for LLM analysis."""
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


async def extract_topics_from_message(text: str, group_chat_id: int, existing_topics: List[str] = None) -> List[Dict]:
    """
    Extract topics from a message using LLM.
    Returns list of topic dicts with text and relevance_score.
    """
    if not await init_hf_client():
        return []
    
    if not text or len(text.strip()) < 3:
        return []
    
    try:
        existing_topics_str = ", ".join(existing_topics) if existing_topics else "None"
        
        prompt = f"""Analyze this message and extract 1-3 main topics or themes. 
Return only the topics as a comma-separated list, nothing else.

Existing topics in this conversation: {existing_topics_str}

Message: "{text}"

Topics:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=50,
            temperature=0.3
        )
        
        topics_text = response.strip()
        if not topics_text or topics_text.lower() in ['none', 'n/a', '']:
            return []
        
        # Parse topics from response
        topics = [t.strip() for t in topics_text.split(',') if t.strip()]
        
        # Store topics in database
        client = get_supabase_client()
        if client:
            topic_dicts = []
            for topic_text in topics[:3]:  # Limit to 3 topics
                try:
                    # Check if topic already exists
                    existing = client.table('group_chat_topics')\
                        .select('id, mention_count')\
                        .eq('group_chat_id', group_chat_id)\
                        .ilike('topic_text', f'%{topic_text}%')\
                        .limit(1)\
                        .execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Update existing topic
                        topic_id = existing.data[0]['id']
                        mention_count = existing.data[0].get('mention_count', 1) + 1
                        client.table('group_chat_topics')\
                            .update({
                                'last_mentioned_at': datetime.now().isoformat(),
                                'mention_count': mention_count,
                                'relevance_score': min(0.95, 0.5 + (mention_count * 0.1))
                            })\
                            .eq('id', topic_id)\
                            .execute()
                        topic_dicts.append({'id': topic_id, 'text': topic_text, 'relevance_score': min(0.95, 0.5 + (mention_count * 0.1))})
                    else:
                        # Create new topic
                        response = client.table('group_chat_topics').insert({
                            'group_chat_id': group_chat_id,
                            'topic_text': topic_text,
                            'relevance_score': 0.6,
                            'mention_count': 1
                        }).execute()
                        if response.data:
                            topic_dicts.append({
                                'id': response.data[0]['id'],
                                'text': topic_text,
                                'relevance_score': 0.6
                            })
                except Exception as e:
                    print(f"   ⚠️  Error storing topic: {e}")
            
            return topic_dicts
        
        return [{'text': t, 'relevance_score': 0.6} for t in topics[:3]]
        
    except Exception as e:
        print(f"   ⚠️  Error extracting topics: {e}")
        return []


async def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of a message using LLM.
    Returns sentiment score from -1 (negative) to 1 (positive).
    """
    if not await init_hf_client():
        return 0.0
    
    if not text or len(text.strip()) < 3:
        return 0.0
    
    try:
        prompt = f"""Analyze the sentiment of this message. Respond with ONLY a number from -1 to 1:
-1 = very negative
0 = neutral
1 = very positive

Message: "{text}"

Sentiment score:"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=10,
            temperature=0.1
        )
        
        # Try to extract number from response
        import re
        numbers = re.findall(r'-?\d+\.?\d*', response.strip())
        if numbers:
            score = float(numbers[0])
            # Clamp to -1 to 1 range
            return max(-1.0, min(1.0, score))
        
        return 0.0
        
    except Exception as e:
        print(f"   ⚠️  Error analyzing sentiment: {e}")
        return 0.0


async def analyze_boring_score(text: str) -> float:
    """
    Analyze how boring/dry a message is using LLM.
    Returns boring score from 1 (very interesting) to 10 (very boring/dry).
    Lower scores = more interesting, Higher scores = more boring.
    """
    if not await init_hf_client():
        return 5.0  # Default neutral score
    
    if not text or len(text.strip()) < 3:
        return 5.0
    
    try:
        prompt = f"""Rate how boring or dry this message is on a scale of 1 to 10. Respond with ONLY a number:
1 = very interesting, engaging, creative
5 = neutral, average
10 = very boring, dry, uninteresting

Consider: engagement level, creativity, interest, energy, enthusiasm.

Message: "{text}"

Boring score (1-10):"""
        
        response = await hf_client.text_generation(
            prompt=prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=10,
            temperature=0.1
        )
        
        # Try to extract number from response
        import re
        numbers = re.findall(r'\d+\.?\d*', response.strip())
        if numbers:
            score = float(numbers[0])
            # Clamp to 1 to 10 range
            return max(1.0, min(10.0, score))
        
        return 5.0  # Default neutral
        
    except Exception as e:
        print(f"   ⚠️  Error analyzing boring score: {e}")
        return 5.0


def update_avg_boring_score(group_chat_id: int) -> float:
    """
    Calculate and update average boring score for a group chat.
    Returns the average boring score.
    """
    client = get_supabase_client()
    if not client:
        return 5.0
    
    try:
        # Get recent messages (last 50) and calculate average
        response = client.table('group_chat_messages')\
            .select('boring_score')\
            .eq('group_chat_id', group_chat_id)\
            .not_.is_('boring_score', 'null')\
            .order('sent_at', desc=True)\
            .limit(50)\
            .execute()
        
        if response.data and len(response.data) > 0:
            scores = [float(m.get('boring_score', 5.0)) for m in response.data if m.get('boring_score') is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                
                # Update group chat
                client.table('group_chats')\
                    .update({'avg_boring_score': avg_score})\
                    .eq('id', group_chat_id)\
                    .execute()
                
                return avg_score
        
        return 5.0  # Default if no scores
        
    except Exception as e:
        print(f"   ⚠️  Error updating avg boring score: {e}")
        return 5.0


def update_participant_engagement(group_chat_id: int, user_id: Optional[str], phone_number: str, 
                                   message_count_increment: int = 1, response_time_seconds: Optional[float] = None):
    """
    Update participant engagement metrics.
    """
    client = get_supabase_client()
    if not client:
        return
    
    try:
        # Get or create engagement record
        existing = client.table('group_chat_participant_engagement')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .eq('phone_number', phone_number)\
            .limit(1)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing
            current_count = existing.data[0].get('message_count', 0)
            current_avg_response = existing.data[0].get('avg_response_time_seconds')
            
            new_count = current_count + message_count_increment
            
            # Update average response time if provided
            new_avg_response = current_avg_response
            if response_time_seconds is not None:
                if current_avg_response is None:
                    new_avg_response = response_time_seconds
                else:
                    # Weighted average
                    new_avg_response = (current_avg_response * current_count + response_time_seconds) / new_count
            
            # Calculate engagement score (0-1)
            # Based on message count, recency, and response time
            engagement_score = min(1.0, new_count / 50.0)  # Normalize by 50 messages
            
            # Calculate participation balance (0-1)
            # Get total messages in group chat
            total_messages = client.table('group_chat_messages')\
                .select('id', count='exact')\
                .eq('group_chat_id', group_chat_id)\
                .execute()
            
            total_count = total_messages.count if hasattr(total_messages, 'count') else 0
            if total_count > 0:
                participation_balance = new_count / total_count
            else:
                participation_balance = 0.5
            
            client.table('group_chat_participant_engagement')\
                .update({
                    'message_count': new_count,
                    'last_active': datetime.now().isoformat(),
                    'avg_response_time_seconds': new_avg_response,
                    'engagement_score': engagement_score,
                    'participation_balance': participation_balance,
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Create new engagement record
            engagement_score = min(1.0, message_count_increment / 50.0)
            participation_balance = 0.5  # Default for new participant
            
            client.table('group_chat_participant_engagement').insert({
                'group_chat_id': group_chat_id,
                'user_id': user_id,
                'phone_number': phone_number,
                'message_count': message_count_increment,
                'last_active': datetime.now().isoformat(),
                'avg_response_time_seconds': response_time_seconds,
                'engagement_score': engagement_score,
                'participation_balance': participation_balance
            }).execute()
            
    except Exception as e:
        print(f"   ⚠️  Error updating engagement: {e}")


def get_participant_engagement(group_chat_id: int) -> List[Dict]:
    """
    Get engagement metrics for all participants in a group chat.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('group_chat_participant_engagement')\
            .select('*')\
            .eq('group_chat_id', group_chat_id)\
            .order('engagement_score', desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"   ⚠️  Error getting engagement: {e}")
        return []


def get_recent_topics(group_chat_id: int, limit: int = 5) -> List[Dict]:
    """
    Get recent topics for a group chat, ordered by relevance and recency.
    """
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


def calculate_health_score(group_chat_id: int) -> float:
    """
    Calculate and update health score for a group chat.
    Uses the database function if available, otherwise calculates manually.
    """
    client = get_supabase_client()
    if not client:
        return 0.5
    
    try:
        # Call the database function
        result = client.rpc('update_group_chat_health_score', {'p_group_chat_id': group_chat_id}).execute()
        if result.data:
            return float(result.data)
        
        # Fallback: manual calculation
        return 0.5
    except Exception as e:
        print(f"   ⚠️  Error calculating health score: {e}")
        # Fallback: manual calculation
        try:
            # Get recent activity
            recent_messages = client.table('group_chat_messages')\
                .select('id', count='exact')\
                .eq('group_chat_id', group_chat_id)\
                .gt('sent_at', (datetime.now() - timedelta(hours=24)).isoformat())\
                .execute()
            
            activity_score = min(1.0, (recent_messages.count if hasattr(recent_messages, 'count') else 0) / 20.0)
            
            # Get average engagement
            engagement = client.table('group_chat_participant_engagement')\
                .select('engagement_score')\
                .eq('group_chat_id', group_chat_id)\
                .execute()
            
            if engagement.data:
                avg_engagement = sum(e.get('engagement_score', 0.5) for e in engagement.data) / len(engagement.data)
            else:
                avg_engagement = 0.5
            
            health_score = (activity_score * 0.5 + avg_engagement * 0.5)
            
            # Update group chat
            client.table('group_chats')\
                .update({'health_score': health_score})\
                .eq('id', group_chat_id)\
                .execute()
            
            return health_score
        except Exception as e2:
            print(f"   ⚠️  Error in fallback health calculation: {e2}")
            return 0.5


def get_engagement_insights(group_chat_id: int) -> Dict:
    """
    Get insights about participant engagement: who's active, who's quiet, balance.
    """
    engagement_data = get_participant_engagement(group_chat_id)
    
    if not engagement_data:
        return {
            'active_participants': [],
            'quiet_participants': [],
            'is_balanced': True,
            'needs_engagement': False
        }
    
    # Sort by engagement score
    sorted_engagement = sorted(engagement_data, key=lambda x: x.get('engagement_score', 0), reverse=True)
    
    # Identify active (top 50%) and quiet (bottom 50%)
    mid_point = len(sorted_engagement) // 2
    active = sorted_engagement[:mid_point] if mid_point > 0 else sorted_engagement
    quiet = sorted_engagement[mid_point:] if mid_point > 0 else []
    
    # Check if participation is balanced
    if len(sorted_engagement) >= 2:
        scores = [e.get('participation_balance', 0.5) for e in sorted_engagement]
        balance_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores) if scores else 0
        is_balanced = balance_variance < 0.1  # Low variance = balanced
    else:
        is_balanced = True
    
    # Check if engagement is needed (anyone very quiet)
    needs_engagement = any(e.get('engagement_score', 0.5) < 0.3 for e in sorted_engagement)
    
    return {
        'active_participants': active,
        'quiet_participants': quiet,
        'is_balanced': is_balanced,
        'needs_engagement': needs_engagement,
        'total_participants': len(sorted_engagement)
    }


async def analyze_message(group_chat_id: int, message_id: str, text: str, from_user_id: Optional[str], 
                          from_phone: str) -> Dict:
    """
    Analyze a single message: extract topics, analyze sentiment, analyze boring score, update engagement.
    Returns analysis results.
    """
    # Get existing topics for context
    existing_topics = get_recent_topics(group_chat_id, limit=10)
    existing_topic_texts = [t.get('topic_text', '') for t in existing_topics]
    
    # Extract topics
    topics = await extract_topics_from_message(text, group_chat_id, existing_topic_texts)
    topic_ids = [t.get('id') for t in topics if t.get('id')]
    
    # Analyze sentiment
    sentiment_score = await analyze_sentiment(text)
    
    # Analyze boring score
    boring_score = await analyze_boring_score(text)
    
    # Determine engagement level
    if len(text) > 100:
        engagement_level = 'high'
    elif len(text) > 30:
        engagement_level = 'medium'
    else:
        engagement_level = 'low'
    
    # Update message with analysis results
    client = get_supabase_client()
    if client:
        try:
            client.table('group_chat_messages')\
                .update({
                    'sentiment_score': sentiment_score,
                    'topic_ids': topic_ids,
                    'engagement_level': engagement_level,
                    'boring_score': boring_score
                })\
                .eq('message_id', message_id)\
                .execute()
        except Exception as e:
            print(f"   ⚠️  Error updating message analysis: {e}")
    
    # Update participant engagement
    update_participant_engagement(group_chat_id, from_user_id, from_phone, message_count_increment=1)
    
    # Update average boring score for group chat
    avg_boring_score = update_avg_boring_score(group_chat_id)
    
    # Recalculate health score
    health_score = calculate_health_score(group_chat_id)
    
    return {
        'topics': topics,
        'sentiment_score': sentiment_score,
        'boring_score': boring_score,
        'avg_boring_score': avg_boring_score,
        'engagement_level': engagement_level,
        'health_score': health_score
    }

