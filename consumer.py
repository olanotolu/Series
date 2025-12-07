#!/usr/bin/env python3
"""
Series Hackathon - Async Kafka Consumer with Audio Support

Listens to Kafka events effectively using aiokafka and asyncio.
Handles:
- Text messages
- Voice memos (OPUS audio)
- Typing indicators
"""

import asyncio
import json
import os
import time
import base64
import shutil
import random
import traceback
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports that need them
load_dotenv()

# Async libraries
import aiohttp
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaError

# Reuse existing utilities (will be run in executor if blocking)
from opus_to_wav import opus_to_wav
from dlq_handler import send_to_dlq, classify_error, is_recoverable_error
from onboarding_flow import (
    get_onboarding_greeting, get_question, get_next_state,
    validate_answer, get_completion_message, format_profile_summary,
    extract_value
)
from embedding_service import generate_user_embedding, store_embedding
from user_matching import find_matches, get_match_profiles, format_match_message, calculate_common_hobbies

# Session Manager (Supabase) - optional
try:
    from session_manager_supabase import SessionManager as SessionManagerClass
    session_manager = SessionManagerClass()
    SESSION_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Supabase session manager not available: {e}")
    print("   Continuing without session history (conversation context will be limited)")
    SESSION_MANAGER_AVAILABLE = False
    # Create a dummy session manager
    class DummySessionManager:
        def get_history(self, sender): return []
        def add_message(self, sender, role, content): pass
        def clear_history(self, sender): pass
        def analyze_behavior(self, sender): return ""
    session_manager = DummySessionManager()

# AWS S3 Storage
try:
    from aws_audio_storage import (
        upload_to_s3, download_from_s3, download_from_s3_bytes,
        generate_s3_key, check_s3_bucket_exists
    )
    AWS_S3_AVAILABLE = True
except ImportError as e:
    AWS_S3_AVAILABLE = False
    print(f"⚠️  AWS S3 integration error: {e}")

# Initialize Session Manager (Supabase)
session_manager = SessionManagerClass()

# Hugging Face Async Client
try:
    from huggingface_hub import AsyncInferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  huggingface_hub not installed. Install with: pip install huggingface_hub")

# Environment variables already loaded above

# Series API credentials
API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL', 'https://hackathon.series.so')
SENDER_NUMBER = os.getenv('SENDER_NUMBER')

# Kafka credentials
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
TOPIC_NAME = os.getenv('KAFKA_TOPIC_NAME')
CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP')
CLIENT_ID = os.getenv('KAFKA_CLIENT_ID')
KAFKA_SASL_USERNAME = os.getenv('KAFKA_SASL_USERNAME')
KAFKA_SASL_PASSWORD = os.getenv('KAFKA_SASL_PASSWORD')

# Hugging Face Token
HF_TOKEN = os.getenv('HF_TOKEN', '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')

# AWS S3 Configuration
USE_S3_STORAGE = os.getenv('USE_S3_STORAGE', 'true').lower() == 'true'
S3_AUDIO_BUCKET = os.getenv('S3_AUDIO_BUCKET', 'series-audio-files')

# Language Detection
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("⚠️  langdetect not installed. Install with: pip install langdetect")

# ElevenLabs TTS
try:
    from elevenlabs_tts import generate_speech as elevenlabs_generate_speech
    ELEVENLABS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  ElevenLabs integration error: {e}")
    ELEVENLABS_AVAILABLE = False

# Global objects
headers = {"Authorization": f"Bearer {API_KEY}"}
hf_client = None

# Dedicated ThreadPoolExecutor for CPU/IO bound tasks
from concurrent.futures import ThreadPoolExecutor
CPU_BOUND_EXECUTOR = ThreadPoolExecutor(max_workers=20)


async def init_hf_client():
    """Initialize Hugging Face Async Inference API client."""
    global hf_client
    
    if not HF_AVAILABLE:
        print("⚠️  Hugging Face Inference API not available. Using echo mode.")
        return False
    
    if hf_client is not None:
        return True
    
    try:
        print("🤖 Initializing Hugging Face Async Inference API client...")
        print(f"   🔑 Using HF token: {HF_TOKEN[:20]}..." if HF_TOKEN and len(HF_TOKEN) > 20 else f"   🔑 HF token length: {len(HF_TOKEN) if HF_TOKEN else 0}")
        hf_client = AsyncInferenceClient(token=HF_TOKEN)
        
        # Test the client with a simple call to verify it works
        print("   🧪 Testing HF client with a simple request...")
        try:
            # This is just to verify the client works - we'll catch any errors
            test_response = await hf_client.chat_completion(
                messages=[{"role": "user", "content": "Say hello"}],
                model="meta-llama/Llama-3.2-3B-Instruct",
                max_tokens=10
            )
            print(f"   ✅ HF client test successful! Response type: {type(test_response)}")
        except Exception as test_error:
            print(f"   ⚠️  HF client test failed: {test_error}")
            print(f"   ⚠️  This might indicate an API issue, but continuing anyway...")
        
        print("✅ Hugging Face Async Inference API client initialized!")
        return True
    except Exception as e:
        print(f"❌ Error initializing HF client: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        traceback.print_exc()
        return False


async def detect_language(text: str) -> str:
    """Detect language of text using langdetect (Google's algorithm)."""
    
    if not text or len(text.strip()) < 3:
        return "en"
        
    loop = asyncio.get_event_loop()
    
    def _detect_safe():
        if not LANGDETECT_AVAILABLE:
            return "en"
        try:
            return detect(text)
        except LangDetectException:
            return "en"
        except Exception as e:
            print(f"   ⚠️  Language detection error: {e}")
            return "en"

    # Run CPU-bound detection in thread pool
    lang = await loop.run_in_executor(CPU_BOUND_EXECUTOR, _detect_safe)
    return lang


async def transcribe_audio(filename: str, language: str = None) -> tuple:
    """Transcribes audio using Hugging Face Inference API (Whisper).
    Returns (transcript, detected_language)"""
    global hf_client
    
    if not HF_AVAILABLE or hf_client is None:
        if not await init_hf_client():
            return None, None
    
    try:
        print(f"   🎤 Transcribing audio: {filename}...")
        # Whisper automatically detects language, but we can specify it
        # For multilingual support, let Whisper auto-detect
        response = await hf_client.automatic_speech_recognition(
            filename,
            model="openai/whisper-large-v3-turbo"
        )
        
        # Determine if response is object or dict based on version
        transcript = response.text if hasattr(response, 'text') else response.get('text')
        
        # Detect language from transcript
        detected_lang = await detect_language(transcript)
        lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
        print(f"   ✅ Transcript ({lang_names.get(detected_lang, 'Unknown')}): {transcript[:100]}...")
        return transcript, detected_lang
    except Exception as e:
        print(f"   ⚠️  Transcription error: {e}")
        traceback.print_exc()
        return None, None


def _generate_contextual_fallback(text: str, history: list = None, language: str = "en", is_error: bool = False) -> str:
    """Generate a contextual fallback response based on user's message and conversation history.
    This provides varied, appropriate responses when the LLM fails."""
    text_lower = text.lower().strip()
    
    # Check conversation history for context
    last_user_msg = None
    if history:
        # Find last user message (not AI)
        for msg in reversed(history):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_msg = msg.get("content", "").lower()
                break
    
    # Pattern matching for common greetings
    greetings = ["hi", "hey", "hello", "sup", "what's up", "howdy"]
    if any(text_lower.startswith(g) or text_lower == g for g in greetings):
        responses = {
            "en": ["Hey there! 👋", "Hi! What's up?", "Hello! How can I help?", "Hey! Good to hear from you."],
            "hi": ["नमस्ते! 👋", "हैलो! क्या हाल है?", "नमस्कार! कैसे हो?"],
            "fr": ["Salut! 👋", "Bonjour! Comment ça va?", "Salut! Quoi de neuf?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Questions about how they are
    if any(word in text_lower for word in ["how are you", "how are u", "hbu", "how's it going", "how r u"]):
        responses = {
            "en": ["I'm doing well, thanks for asking! How about you?", "Pretty good! What's new with you?", "All good here! How are things on your end?"],
            "hi": ["मैं ठीक हूँ, पूछने के लिए धन्यवाद! आप कैसे हैं?", "बहुत अच्छा! आपके साथ क्या नया है?"],
            "fr": ["Je vais bien, merci de demander! Et toi?", "Plutôt bien! Quoi de neuf avec toi?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Questions
    if text_lower.endswith("?") or any(word in text_lower for word in ["what", "when", "where", "why", "how", "who"]):
        responses = {
            "en": ["That's a good question! Let me think about that...", "Hmm, interesting question. What do you think?", "I'm not entirely sure, but what's your take on it?"],
            "hi": ["यह एक अच्छा सवाल है! मुझे इसके बारे में सोचने दो...", "हम्म, दिलचस्प सवाल। आप क्या सोचते हैं?"],
            "fr": ["C'est une bonne question! Laisse-moi réfléchir...", "Hmm, question intéressante. Qu'est-ce que tu en penses?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Short responses (yes, no, ok, etc.)
    short_responses = ["yes", "yeah", "yep", "no", "nope", "ok", "okay", "sure", "cool", "nice", "good"]
    if text_lower in short_responses or len(text_lower) <= 3:
        responses = {
            "en": ["Got it! What else is on your mind?", "Cool! Tell me more.", "Nice! What's next?", "Alright! What's up?"],
            "hi": ["समझ गया! और क्या है?", "ठीक है! और बताओ।", "अच्छा! आगे क्या?"],
            "fr": ["Compris! Quoi d'autre?", "Cool! Dis-moi en plus.", "Bien! Et ensuite?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Statements or longer messages - acknowledge and engage
    if len(text_lower) > 10:
        # Try to extract key topics
        common_words = ["work", "school", "job", "class", "homework", "project", "meeting", "weekend", "plans", "today", "tomorrow"]
        found_topic = None
        for word in common_words:
            if word in text_lower:
                found_topic = word
                break
        
        if found_topic:
            topic_responses = {
                "work": {"en": "Work stuff, huh? How's that going?", "hi": "काम की बातें, है ना? कैसा चल रहा है?", "fr": "Des trucs de boulot, hein? Comment ça se passe?"},
                "school": {"en": "School! How are classes going?", "hi": "स्कूल! कक्षाएं कैसी चल रही हैं?", "fr": "L'école! Comment se passent les cours?"},
                "job": {"en": "Job stuff! What's happening there?", "hi": "नौकरी की बातें! वहाँ क्या हो रहा है?", "fr": "Des trucs de boulot! Qu'est-ce qui se passe là-bas?"},
                "weekend": {"en": "Weekend plans! What are you up to?", "hi": "सप्ताहांत की योजनाएं! आप क्या कर रहे हैं?", "fr": "Des plans de week-end! Qu'est-ce que tu fais?"},
                "plans": {"en": "Plans! What are you thinking?", "hi": "योजनाएं! आप क्या सोच रहे हैं?", "fr": "Des plans! À quoi tu penses?"}
            }
            if found_topic in topic_responses:
                return topic_responses[found_topic].get(language, topic_responses[found_topic]["en"])
        
        # Generic acknowledgment for longer messages
        responses = {
            "en": ["That's interesting! Tell me more about that.", "I see! What's your take on it?", "Gotcha! How do you feel about that?", "Interesting point! What else is on your mind?"],
            "hi": ["यह दिलचस्प है! मुझे इसके बारे में और बताओ।", "समझ गया! आप इसके बारे में क्या सोचते हैं?", "ठीक है! आप इसके बारे में कैसा महसूस करते हैं?"],
            "fr": ["C'est intéressant! Dis-moi en plus.", "Je vois! Qu'est-ce que tu en penses?", "Compris! Comment tu te sens à ce sujet?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Error fallback (when LLM completely fails)
    if is_error:
        responses = {
            "en": ["Sorry, I'm having a bit of trouble right now. Can you try rephrasing that?", "Oops! Having some technical difficulties. What were you saying?", "Hmm, something's not working right. Can you say that again?"],
            "hi": ["माफ करें, मुझे अभी थोड़ी परेशानी हो रही है। क्या आप इसे फिर से कह सकते हैं?", "ओह! कुछ तकनीकी समस्याएं हो रही हैं। आप क्या कह रहे थे?"],
            "fr": ["Désolé, j'ai un petit problème en ce moment. Peux-tu reformuler?", "Oups! Quelques difficultés techniques. Qu'est-ce que tu disais?"]
        }
        import random
        return random.choice(responses.get(language, responses["en"]))
    
    # Default fallback
    responses = {
        "en": ["Got it! What's on your mind?", "I hear you! What else?", "Interesting! Tell me more.", "Cool! What's next?"],
        "hi": ["समझ गया! आप क्या सोच रहे हैं?", "सुन रहा हूँ! और क्या?", "दिलचस्प! और बताओ।"],
        "fr": ["Compris! Qu'est-ce qui te passe par la tête?", "Je t'entends! Quoi d'autre?", "Intéressant! Dis-moi en plus."]
    }
    import random
    return random.choice(responses.get(language, responses["en"]))


async def get_llm_response(text: str, history: list = None, language: str = "en", behavior_context: str = "", profile: dict = None, group_context: dict = None) -> str:
    """Get response from LLM using Hugging Face Inference API.
    Responds in the detected language (English, Hindi, or French).
    Uses user profile for personalized responses.
    Supports group chat context for multi-user conversations."""
    global hf_client
    
    if hf_client is None:
        if not await init_hf_client():
            print(f"   ❌ HF client initialization failed, using contextual fallback")
            return _generate_contextual_fallback(text, history, language, is_error=True)
    
    try:
        print(f"   🤖 Getting LLM response via Async Inference API...")
        
        # Multilingual system prompt - responds in the same language as the user
        lang_instructions = {
            "en": "You MUST respond ONLY in English. Do not use French, Hindi, or any other language. Use English words and phrases only.",
            "hi": "You MUST respond ONLY in Hindi (Devanagari script). Do not use English, French, or any other language. Use Hindi words and phrases only.",
            "fr": "You MUST respond ONLY in French. Do not use English, Hindi, or any other language. Use French words and phrases only."
        }
        
        lang_instruction = lang_instructions.get(language, lang_instructions["en"])
        lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
        lang_name = lang_names.get(language, "English")
        
        # Build profile section
        profile_section = ""
        if profile:
            profile_parts = []
            if profile.get("name"):
                profile_parts.append(f"Name: {profile['name']}")
            if profile.get("school"):
                profile_parts.append(f"School: {profile['school']}")
            if profile.get("age"):
                profile_parts.append(f"Age: {profile['age']}")
            if profile.get("hobbies"):
                profile_parts.append(f"Hobbies: {profile['hobbies']}")
            
            if profile_parts:
                profile_section = f"""
USER PROFILE:
{chr(10).join(profile_parts)}

Use this information to personalize your responses. Reference their name, school, or hobbies naturally in conversation. For example, if they mention their hobby, show interest. If they're in school, you can ask about classes or activities."""
        
        # Build group chat context section
        group_section = ""
        if group_context and group_context.get("is_group_chat"):
            participants = group_context.get("participants", [])
            recent_messages = group_context.get("recent_messages", [])
            display_name = group_context.get("display_name", "Group Chat")
            engagement_insights = group_context.get("engagement_insights", {})
            recent_topics = group_context.get("recent_topics", [])
            health_metrics = group_context.get("health_metrics", {})
            common_hobbies = group_context.get("common_hobbies", [])
            
            participant_info = []
            for p in participants:
                parts = []
                if p.get("name"):
                    parts.append(p["name"])
                if p.get("school"):
                    parts.append(f"({p['school']})")
                if p.get("age"):
                    parts.append(f"age {p['age']}")
                if parts:
                    participant_info.append(" ".join(parts))
            
            # Build engagement awareness section
            engagement_section = ""
            if engagement_insights:
                active = engagement_insights.get("active_participants", [])
                quiet = engagement_insights.get("quiet_participants", [])
                is_balanced = engagement_insights.get("is_balanced", True)
                needs_engagement = engagement_insights.get("needs_engagement", False)
                
                engagement_section = "\nENGAGEMENT AWARENESS:\n"
                if active:
                    active_names = [p.get("name", "Someone") for p in active if p.get("name")]
                    if active_names:
                        engagement_section += f"- Active participants: {', '.join(active_names[:3])}\n"
                if quiet and needs_engagement:
                    quiet_names = [p.get("name", "Someone") for p in quiet if p.get("name")]
                    if quiet_names:
                        engagement_section += f"- Quiet participants (needs engagement): {', '.join(quiet_names[:3])}\n"
                        engagement_section += "  → Proactively ask them questions or reference their interests to include them.\n"
                if not is_balanced:
                    engagement_section += "- Participation is unbalanced. Try to get everyone involved equally.\n"
            
            # Build topics section
            topics_section = ""
            if recent_topics:
                topics_section = f"\nRECENT TOPICS DISCUSSED:\n"
                topics_section += f"- {', '.join(recent_topics[:5])}\n"
                topics_section += "→ Reference these topics naturally to maintain conversation continuity.\n"
            
            # Build health/sentiment section
            health_section = ""
            if health_metrics:
                health_score = health_metrics.get("health_score", 0.5)
                avg_boring = health_metrics.get("avg_boring_score", 5.0)
                
                health_section = "\nCONVERSATION HEALTH:\n"
                if health_score < 0.4:
                    health_section += "- Conversation health is low. Be more engaging and proactive.\n"
                if avg_boring >= 4.0:
                    health_section += "- Conversation has been a bit dry. Suggest interesting topics or ask engaging questions.\n"
            
            # Build common interests section
            interests_section = ""
            if common_hobbies:
                interests_section = f"\nCOMMON INTERESTS:\n"
                interests_section += f"- {', '.join(common_hobbies[:5])}\n"
                interests_section += "→ Use these shared interests to facilitate conversation and find common ground.\n"
            
            group_section = f"""
GROUP CHAT CONTEXT:
You are in a group chat called "{display_name}" with {len(participants)} other people.
Participants: {', '.join(participant_info) if participant_info else 'Multiple users'}
{interests_section}
{engagement_section}
{topics_section}
{health_section}
IMPORTANT GROUP CHAT RULES:
1. You matched these people because they share common interests. Help facilitate conversation between them.
2. Keep your responses brief and engaging - you're part of a group conversation, not a one-on-one.
3. Reference what others have said when relevant. Show you're paying attention to the whole conversation.
4. Encourage interaction between the participants. Ask questions that involve everyone.
5. Be friendly and inclusive. Make sure everyone feels included in the conversation.
6. If someone asks a question, you can answer, but also try to get others involved.
7. If someone is quiet, proactively engage them with questions related to their interests.
8. Maintain topic continuity by referencing recent topics naturally.
9. If conversation feels dry, suggest new topics or ask engaging questions.
10. Balance participation - make sure everyone has a chance to contribute.

Recent conversation context:
"""
            # Add last few messages for context
            for msg in recent_messages[-5:]:  # Last 5 messages
                from_phone = msg.get("from_phone", "Unknown")
                msg_text = msg.get("text", "")
                is_ai = msg.get("is_from_ai", False)
                if not is_ai and msg_text:
                    # Find participant name
                    participant_name = "Someone"
                    for p in participants:
                        if p.get("user_id") == msg.get("from_user_id"):
                            participant_name = p.get("name", "Someone")
                            break
                    group_section += f"- {participant_name}: {msg_text}\n"
        
        system_prompt = f"""You are a friendly, helpful friend chatting on Series.so, a social network platform. 
You're having a casual conversation with someone you know.
{profile_section}
{group_section}
CRITICAL LANGUAGE RULE: The user is speaking in {lang_name}. {lang_instruction}
You MUST match their language exactly. If they say "Hi" in English, you respond in English. If they say "Bonjour" in French, you respond in French. If they say "नमस्ते" in Hindi, you respond in Hindi.

CONTEXT ABOUT USER STATE ({behavior_context}):
Use this context to adjust your tone. 
- If they are returning after a long silence, welcome them back warmly.
- If they are messaging rapidly (high urgency), be concise and responsive.
- If it's a normal flow, be relaxed.

Keep responses concise (1-3 sentences typically), use casual language, and show genuine interest in the conversation.
You can use emojis occasionally to add personality, but don't overdo it. Be yourself - friendly, supportive, and authentic."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history if provided
        if history:
            messages.extend(history)
            
        # Add current message with language context
        # Format: "[Language: English] User message" to reinforce language matching
        user_message = f"[Language: {lang_name}] {text}"
        messages.append({"role": "user", "content": user_message})
        
        # Use Meta-Llama-3.2-3B-Instruct (reliable and fast via API, supports multilingual)
        try:
            response = await hf_client.chat_completion(
                messages=messages,
                model="meta-llama/Llama-3.2-3B-Instruct",
                max_tokens=512
            )
            
            # Debug: Log response structure
            print(f"   🔍 DEBUG: Response type: {type(response)}")
            if hasattr(response, '__dict__'):
                print(f"   🔍 DEBUG: Response attributes: {list(response.__dict__.keys())}")
            
            # Handle different response structures
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message'):
                    reply = response.choices[0].message.content.strip()
                elif hasattr(response.choices[0], 'text'):
                    reply = response.choices[0].text.strip()
                else:
                    # Try dict access
                    reply = response.choices[0].get('message', {}).get('content', '').strip() if isinstance(response.choices[0], dict) else str(response.choices[0]).strip()
            elif isinstance(response, dict):
                # Response is a dict
                if 'choices' in response and len(response['choices']) > 0:
                    choice = response['choices'][0]
                    if isinstance(choice, dict):
                        reply = choice.get('message', {}).get('content', '').strip()
                    else:
                        reply = str(choice).strip()
                elif 'text' in response:
                    reply = response['text'].strip()
                else:
                    print(f"   ⚠️  Unexpected response structure: {list(response.keys())}")
                    reply = ""
            else:
                # Try to extract text directly
                reply = str(response).strip()
                print(f"   ⚠️  Unexpected response type, using string conversion")
            
            print(f"   🔍 DEBUG: Extracted reply: '{reply[:100]}...' (length: {len(reply)})")
            
        except Exception as api_error:
            print(f"   ❌ Hugging Face API error: {api_error}")
            print(f"   ❌ Error type: {type(api_error).__name__}")
            import traceback
            traceback.print_exc()
            reply = ""
        
        if not reply or len(reply) < 3:
            print(f"   ⚠️  Empty or too short reply, using contextual fallback")
            # Generate contextual fallback based on user's message
            contextual_fallback = _generate_contextual_fallback(text, history, language)
            return contextual_fallback
        
        # Validate language match - if LLM responded in wrong language, use fallback
        detected_reply_lang = await detect_language(reply)
        if detected_reply_lang != language and language != "en":
            # If expected non-English but got different language, use fallback
            print(f"   ⚠️  Language mismatch: Expected {language}, got {detected_reply_lang}. Using fallback.")
            fallbacks = {
                "en": f"Hey! {text} - that's interesting! What's on your mind?",
                "hi": f"हाँ, {text} - यह दिलचस्प है! आप क्या सोच रहे हैं?",
                "fr": f"Salut! {text} - c'est intéressant! Qu'est-ce qui te passe par la tête?"
            }
            return fallbacks.get(language, reply)
        
        return reply
        
    except Exception as e:
        print(f"   ❌ LLM error: {e}")
        print(f"   ❌ Error type: {type(e).__name__}")
        traceback.print_exc()
        # Use contextual fallback based on user's message
        contextual_fallback = _generate_contextual_fallback(text, history, language, is_error=True)
        return contextual_fallback


async def text_to_speech(text: str, language: str = "en", output_file: str = None) -> str:
    """Convert text to speech using ElevenLabs API. Stores in S3 if enabled."""
    
    if not ELEVENLABS_AVAILABLE:
        print("   ❌ ElevenLabs TTS not available")
        return None
    
    try:
        lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
        lang_name = lang_names.get(language, language.upper())
        print(f"   🔊 Generating Speech (ElevenLabs, {lang_name}): {text[:50]}...")
        
        # Determine storage method
        use_s3 = USE_S3_STORAGE and AWS_S3_AVAILABLE
        
        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if output_file is None:
            if use_s3:
                # For S3, we'll use a temp file first, then upload
                output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            else:
                os.makedirs("audio_files", exist_ok=True)
                output_file = f"audio_files/tts_response_{timestamp}.wav"
        
        # Call ElevenLabs with language parameter for multilingual support
        result_file = await elevenlabs_generate_speech(text, output_file, language=language)
        
        if result_file and os.path.exists(result_file):
            if use_s3:
                # Upload to S3
                loop = asyncio.get_event_loop()
                
                def upload_tts_to_s3():
                    with open(result_file, 'rb') as f:
                        wav_data = f.read()
                    
                    s3_key = f"tts_response_{timestamp}.wav"
                    upload_success = upload_to_s3(S3_AUDIO_BUCKET, s3_key, wav_data, 'audio/wav')
                    
                    # Cleanup local temp file
                    os.unlink(result_file)
                    
                    if upload_success:
                        return f"s3://{S3_AUDIO_BUCKET}/{s3_key}"
                    return None
                
                s3_path = await loop.run_in_executor(CPU_BOUND_EXECUTOR, upload_tts_to_s3)
                if s3_path:
                    print(f"   ✅ TTS audio uploaded to S3: {s3_path}")
                    return s3_path
                else:
                    print(f"   ⚠️  S3 upload failed, using local file")
                    return result_file
            else:
                print(f"   ✅ TTS audio saved locally: {result_file}")
                return result_file
        else:
            print(f"   ❌ TTS failed (no file created)")
            return None
            
    except Exception as e:
        print(f"   ⚠️  TTS error: {e}")
        traceback.print_exc()
        return None


def wav_to_opus(wav_file: str, opus_file: str = None) -> str:
    """Convert WAV file to OPUS format using ffmpeg."""
    if opus_file is None:
        opus_file = wav_file.replace('.wav', '.opus')
    
    try:
        import subprocess
        subprocess.run([
            'ffmpeg', '-y', '-i', wav_file,
            '-ar', '16000',  # Sample rate
            '-ac', '1',      # Mono
            '-b:a', '32k',   # Bitrate
            opus_file
        ], check=True, capture_output=True)
        
        print(f"   ✅ Converted WAV → OPUS: {opus_file}")
        return opus_file
    except Exception as e:
        print(f"   ⚠️  Error converting to OPUS: {e}")
        return None


async def send_text(session: aiohttp.ClientSession, chat_id: str, text: str):
    """Send a text message via Series API."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    payload = {"message": {"text": text}}
    
    print(f"\n📤 OUTGOING MESSAGE:")
    print(f"   Chat ID: {chat_id}")
    print(f"   Text: {text}")
    
    try:
        async with session.post(url, json=payload, headers=headers, timeout=30) as r:
            if r.status not in [200, 201]:
                error_msg = f"Series API returned {r.status}"
                print(f"   ⚠️  Status: {r.status}")
                try:
                    resp_json = await r.json()
                    print(f"   Response: {resp_json}")
                except:
                    resp_text = await r.text()
                    print(f"   Response: {resp_text}")
                r.raise_for_status()
            
            response = await r.json()
            message_id = response.get('data', {}).get('id', 'N/A')
            print(f"   ✅ Message ID: {message_id}")
            print(f"   Status: {r.status} - Success")
            return response
    except Exception as e:
        print(f"   ❌ Error sending message: {e}")
        raise


async def send_audio(session: aiohttp.ClientSession, chat_id: str, audio_file_path: str, text: str = "🎤 Voice message"):
    """Send an audio message (voice memo) via Series API.
    The text parameter is required by the API and will be displayed alongside the audio.
    Supports both local file paths and S3 paths (s3://bucket/key)."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    
    # Read audio file and encode to base64 (run in executor)
    loop = asyncio.get_event_loop()
    
    def read_and_encode():
        # Handle S3 path
        if audio_file_path.startswith('s3://'):
            bucket, key = audio_file_path.replace('s3://', '').split('/', 1)
            audio_data = download_from_s3_bytes(bucket, key)
            if not audio_data:
                raise Exception(f"Failed to download audio from S3: {audio_file_path}")
        else:
            # Local file
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
        return base64.b64encode(audio_data).decode('ascii')
    
    audio_base64 = await loop.run_in_executor(CPU_BOUND_EXECUTOR, read_and_encode)
    
    # Determine format - M4A is the target for voice memos
    if audio_file_path.startswith('s3://'):
        filename = audio_file_path.split('/')[-1]
    else:
        filename = os.path.basename(audio_file_path)
    if audio_file_path.endswith('.m4a'):
        mime_type = 'audio/m4a'
    elif audio_file_path.endswith('.opus'):
        mime_type = 'audio/ogg' # Opus usually sent as OGG container
    elif audio_file_path.endswith('.wav'):
        mime_type = 'audio/wav'
    else:
        mime_type = 'application/octet-stream'
    
    # Payload Structure for Voice Memo (M4A)
    # Text is required by API (cannot be empty string)
    payload = {
        "message": {
            "text": text,  # Required field - shows transcript/response text
            "attachments": [
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "data_base64": audio_base64
                }
            ]
        }
    }
    
    print(f"\n📤 OUTGOING VOICE MEMO ({mime_type}):")
    print(f"   Chat ID: {chat_id}")
    print(f"   File: {filename}")
    
    try:
        async with session.post(url, json=payload, headers=headers, timeout=30) as r:
            if r.status not in [200, 201]:
                error_msg = f"Series API returned {r.status}"
                print(f"   ⚠️  Status: {r.status}")
                try:
                    resp_json = await r.json()
                    print(f"   Response: {resp_json}")
                except:
                    resp_text = await r.text()
                    print(f"   Response: {resp_text}")
                r.raise_for_status()
            
            response = await r.json()
            message_id = response.get('data', {}).get('id', 'N/A')
            print(f"   ✅ Message ID: {message_id}")
            print(f"   Status: {r.status} - Success")
            return response
    except Exception as e:
        print(f"   ❌ Error sending audio: {e}")
        raise


async def start_typing(session: aiohttp.ClientSession, chat_id: str):
    """Send typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/start_typing"
    try:
        async with session.post(url, headers=headers) as r:
            if r.status in [200, 201]:
                print(f"   ⌨️  Typing indicator: ON")
            else:
                print(f"   ⚠️  Typing indicator failed: {r.status}")
    except Exception as e:
        print(f"   ⚠️  Typing indicator error: {e}")


async def stop_typing(session: aiohttp.ClientSession, chat_id: str):
    """Stop typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/stop_typing"
    try:
        async with session.delete(url, headers=headers) as r:
            if r.status in [200, 201, 204]:
                print(f"   ⌨️  Typing indicator: OFF")
            else:
                print(f"   ⚠️  Stop typing failed: {r.status}")
    except Exception as e:
        print(f"   ⚠️  Stop typing error: {e}")


async def create_group_chat(session: aiohttp.ClientSession, user_phone: str, match_phone: str, user_name: str, match_name: str, common_hobbies: list) -> str:
    """
    Create a group chat with user, match, and AI.
    
    Args:
        session: aiohttp session
        user_phone: Current user's phone number
        match_phone: Matched user's phone number
        user_name: Current user's name
        match_name: Matched user's name
        common_hobbies: List of common hobbies
    
    Returns:
        Chat ID if successful, None otherwise
    """
    url = f"{BASE_URL}/api/chats"
    
    # Format display name: "User & Match"
    display_name = f"{user_name} & {match_name}"
    
    # Format common hobbies for intro message
    if common_hobbies:
        if len(common_hobbies) == 1:
            hobbies_str = common_hobbies[0]
        elif len(common_hobbies) == 2:
            hobbies_str = f"{common_hobbies[0]} and {common_hobbies[1]}"
        else:
            hobbies_str = ", ".join(common_hobbies[:-1]) + f", and {common_hobbies[-1]}"
    else:
        hobbies_str = "similar interests"
    
    # Create intro message
    intro_message = f"Hey! I matched you two because you both love {hobbies_str}. Say hi!"
    
    # Payload for group chat creation
    # Note: AI is NOT included as participant (causes 403 error)
    # AI will still receive messages if it's subscribed to the chat via Series API
    payload = {
        "send_from": SENDER_NUMBER,
        "chat": {
            "display_name": display_name,
            "phone_numbers": [user_phone, match_phone]  # Only the two matched users
        },
        "message": {
            "text": intro_message
        }
    }
    
    print(f"\n📤 CREATING GROUP CHAT:")
    print(f"   Display Name: {display_name}")
    print(f"   Participants: {user_phone}, {match_phone}")
    print(f"   Sending from: {SENDER_NUMBER} (AI - will receive messages via API)")
    print(f"   Intro Message: {intro_message}")
    
    try:
        async with session.post(url, json=payload, headers=headers, timeout=30) as r:
            if r.status not in [200, 201]:
                error_msg = f"Series API returned {r.status}"
                print(f"   ⚠️  Status: {r.status}")
                try:
                    resp_json = await r.json()
                    print(f"   Response: {resp_json}")
                except:
                    resp_text = await r.text()
                    print(f"   Response: {resp_text}")
                return None
            
            response = await r.json()
            chat_id = response.get('data', {}).get('id')
            if chat_id:
                print(f"   ✅ Group chat created! Chat ID: {chat_id}")
                
                # Store group chat in database
                try:
                    from group_chat_manager import (
                        create_group_chat_record,
                        add_group_chat_participant
                    )
                    
                    # Create group chat record
                    group_chat_db_id = create_group_chat_record(str(chat_id), display_name)
                    
                    if group_chat_db_id:
                        # Add participants (AI not included since it's not a participant)
                        add_group_chat_participant(group_chat_db_id, user_phone, user_phone, is_ai=False)
                        add_group_chat_participant(group_chat_db_id, match_phone, match_phone, is_ai=False)
                        # Note: AI is not a participant, but can still send/receive messages via API
                        print(f"   ✅ Group chat stored in database (ID: {group_chat_db_id})")
                    else:
                        print(f"   ⚠️  Failed to store group chat in database")
                except Exception as e:
                    print(f"   ⚠️  Error storing group chat: {e}")
                    import traceback
                    traceback.print_exc()
                
                return str(chat_id)
            else:
                print(f"   ⚠️  No chat ID in response: {response}")
                return None
    except Exception as e:
        print(f"   ❌ Error creating group chat: {e}")
        traceback.print_exc()
        return None


async def download_file(session: aiohttp.ClientSession, url: str) -> bytes:
    """Download a file from a URL."""
    async with session.get(url, headers=headers, timeout=30) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise Exception(f"Failed to download: {response.status}")


def wav_to_m4a(wav_file: str, m4a_file: str = None) -> str:
    """Convert WAV file to M4A (AAC) format using ffmpeg. Supports S3 paths."""
    use_s3 = USE_S3_STORAGE and AWS_S3_AVAILABLE and wav_file.startswith('s3://')
    
    try:
        import subprocess
        
        # Handle S3 input
        if use_s3:
            # Download from S3 to temp file
            bucket, key = wav_file.replace('s3://', '').split('/', 1)
            temp_wav = download_from_s3(bucket, key)
            if not temp_wav:
                return None
            wav_file = temp_wav
        
        # Generate output path
        if m4a_file is None:
            if use_s3:
                # Use temp file, will upload to S3
                m4a_file = tempfile.NamedTemporaryFile(suffix='.m4a', delete=False).name
            else:
                m4a_file = wav_file.replace('.wav', '.m4a')
        
        # Convert using ffmpeg
        result = subprocess.run([
            'ffmpeg', '-y', 
            '-i', wav_file,
            '-c:a', 'aac', 
            '-b:a', '48k',
            m4a_file
        ], check=True, capture_output=True)
        
        if os.path.exists(m4a_file):
            if use_s3:
                # Upload to S3
                with open(m4a_file, 'rb') as f:
                    m4a_data = f.read()
                
                # Generate S3 key from original WAV key
                bucket, wav_key = wav_file.replace('s3://', '').split('/', 1) if wav_file.startswith('s3://') else (S3_AUDIO_BUCKET, '')
                m4a_key = wav_key.replace('.wav', '.m4a') if wav_key else f"tts_response_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.m4a"
                
                upload_success = upload_to_s3(bucket, m4a_key, m4a_data, 'audio/m4a')
                
                # Cleanup temp files
                os.unlink(m4a_file)
                if wav_file != temp_wav:
                    try:
                        os.unlink(temp_wav)
                    except:
                        pass
                
                if upload_success:
                    s3_path = f"s3://{bucket}/{m4a_key}"
                    print(f"   ✅ Converted WAV → M4A and uploaded to S3: {s3_path}")
                    return s3_path
                else:
                    print(f"   ⚠️  S3 upload failed")
                    return None
            else:
                print(f"   ✅ Converted WAV → M4A: {m4a_file}")
                return m4a_file
        else:
            print(f"   ⚠️  M4A file not created")
            return None
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Error converting to M4A: {e.stderr.decode() if e.stderr else str(e)}")
        return None
    except Exception as e:
        print(f"   ⚠️  Error converting to M4A: {e}")
        return None


async def process_audio_message(session: aiohttp.ClientSession, event_data: dict):
    """Process incoming voice memo."""
    chat_id = event_data.get("chat_id")
    sender = event_data.get("from_phone", "Unknown")
    message_id = event_data.get("id", "N/A")
    audio_data = event_data.get("audio", {})
    base64_opus = audio_data.get("data")
    audio_url = audio_data.get("url")
    
    print(f"\n📥 INCOMING VOICE MEMO from {sender}")
    
    # Download if needed
    if not base64_opus and audio_url:
        print(f"   📥 Downloading audio from URL: {audio_url[:50]}...")
        try:
            opus_data = await download_file(session, audio_url)
            base64_opus = base64.b64encode(opus_data).decode('ascii')
            print(f"   ✅ Downloaded {len(opus_data):,} bytes")
        except Exception as e:
            print(f"   ❌ Error downloading audio: {e}")
            await send_text(session, chat_id, "Sorry, couldn't download the voice memo.")
            return

    if not base64_opus:
        print("   ⚠️  No audio data provided")
        return

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sender = sender.replace("+", "").replace("-", "")
        
        # Determine storage method (S3 or local)
        use_s3 = USE_S3_STORAGE and AWS_S3_AVAILABLE
        
        if use_s3:
            # Verify S3 bucket exists
            loop = asyncio.get_event_loop()
            bucket_exists = await loop.run_in_executor(
                CPU_BOUND_EXECUTOR, 
                check_s3_bucket_exists, 
                S3_AUDIO_BUCKET
            )
            if not bucket_exists:
                print(f"   ⚠️  S3 bucket '{S3_AUDIO_BUCKET}' not accessible, falling back to local storage")
                use_s3 = False
        
        loop = asyncio.get_event_loop()
        
        if use_s3:
            # STEP 1: Upload OPUS to S3
            print(f"   💾 STEP 1: Uploading OPUS to S3...")
            opus_bytes = base64.b64decode(base64_opus)
            opus_s3_key = generate_s3_key("voice_memo", sender, timestamp, message_id, "opus")
            
            upload_success = await loop.run_in_executor(
                CPU_BOUND_EXECUTOR,
                upload_to_s3,
                S3_AUDIO_BUCKET,
                opus_s3_key,
                opus_bytes,
                'audio/ogg'
            )
            
            if upload_success:
                print(f"   ✅ STEP 1 COMPLETE: OPUS uploaded to S3 ({len(opus_bytes)} bytes)")
            else:
                print(f"   ⚠️  S3 upload failed, falling back to local")
                use_s3 = False
        
        if not use_s3:
            # Fallback to local storage
            audio_dir = "audio_files"
            os.makedirs(audio_dir, exist_ok=True)
            opus_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.opus"
            
            def save_local():
                opus_bytes = base64.b64decode(base64_opus)
                with open(opus_filename, 'wb') as f:
                    f.write(opus_bytes)
                print(f"   ✅ STEP 1 COMPLETE: OPUS saved locally ({len(opus_bytes)} bytes)")
                return opus_to_wav(base64_opus)
            
            wav_file = await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_local)
            wav_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.wav"
            if os.path.exists(wav_file):
                shutil.copy2(wav_file, wav_filename)
                print(f"   ✅ STEP 2-4 COMPLETE: WAV saved locally: {wav_filename}")
        else:
            # STEP 2-4: Convert OPUS → WAV (using local temp file, then upload to S3)
            print(f"   🎵 STEP 2-4: Converting OPUS → WAV...")
            
            def convert_and_upload():
                # Convert using local temp file
                wav_temp = opus_to_wav(base64_opus)
                if not wav_temp or not os.path.exists(wav_temp):
                    return None
                
                # Read WAV data
                with open(wav_temp, 'rb') as f:
                    wav_data = f.read()
                
                # Upload to S3
                wav_s3_key = generate_s3_key("voice_memo", sender, timestamp, message_id, "wav")
                upload_success = upload_to_s3(S3_AUDIO_BUCKET, wav_s3_key, wav_data, 'audio/wav')
                
                # Cleanup temp file
                os.unlink(wav_temp)
                
                if upload_success:
                    return wav_s3_key
                return None
            
            wav_s3_key = await loop.run_in_executor(CPU_BOUND_EXECUTOR, convert_and_upload)
            
            if wav_s3_key:
                print(f"   ✅ STEP 2-4 COMPLETE: WAV uploaded to S3: {wav_s3_key}")
                # Download to temp file for Whisper (needs local file)
                wav_filename = await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    download_from_s3,
                    S3_AUDIO_BUCKET,
                    wav_s3_key
                )
            else:
                print(f"   ⚠️  WAV conversion/upload failed")
                wav_filename = None
        
        # Transcribe (with language detection)
        if not wav_filename:
            print("   ⚠️  No WAV file available for transcription")
            await send_text(session, chat_id, "Sorry, couldn't process that voice memo.")
            return
        
        print(f"   🎤 STEP 5: Transcribing WAV → Text (Whisper)...")
        transcript, detected_language = await transcribe_audio(wav_filename)
        
        # Cleanup temp WAV file if it was downloaded from S3
        if use_s3 and wav_filename and os.path.exists(wav_filename) and '/tmp' in wav_filename:
            try:
                os.unlink(wav_filename)
            except:
                pass
        
        # Start typing
        await start_typing(session, chat_id)
        
        # Get user history and behavioral context
        loop = asyncio.get_event_loop()
        history = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_history, sender)
        behavior_context = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.analyze_behavior, sender)
        
        print(f"   🧠 Behavioral Context: {behavior_context}")
        
        # If transcription failed, use a fallback message but still send voice response
        if not transcript:
            print(f"   ⚠️  Transcription failed, using fallback message for voice response")
            transcript = "voice memo"  # Placeholder for context
            detected_language = "en"  # Default to English
            # Use a friendly fallback message
            fallback_messages = {
                "en": "Hey! I got your voice memo! Thanks for sending it.",
                "hi": "नमस्ते! मुझे आपका वॉइस मेमो मिला! भेजने के लिए धन्यवाद।",
                "fr": "Salut! J'ai reçu ton message vocal! Merci de l'avoir envoyé."
            }
            llm_reply = fallback_messages.get(detected_language, fallback_messages["en"])
        else:
            lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
            lang_name = lang_names.get(detected_language, "Unknown")
            print(f"   ✅ STEP 5 COMPLETE: Transcript ({lang_names.get(detected_language, 'Unknown')}): {transcript}")
            
            try:
                if not transcript:
                    transcript = "(Audio)"
                
                # Detect language of transcript for multilingual routing
                if transcript and transcript != "(Audio)":
                    detected_language = await detect_language(transcript)
                else:
                    detected_language = "en"  # Default to English if no transcript
                    
                lang_name = {"en": "English", "hi": "Hindi", "fr": "French"}.get(detected_language, "English")
                    
                # Get LLM response (Text) with behavior context
                print(f"   🤖 STEP 6: Getting LLM response from transcript ({lang_name})...")
                llm_reply = await get_llm_response(transcript, history, language=detected_language or "en", behavior_context=behavior_context)
                print(f"   ✅ STEP 6 COMPLETE: LLM Response ({lang_name}): {llm_reply[:100]}...")
                
            except Exception as e:
                print(f"   ⚠️  LLM error: {e}")
                # Use fallback message
                fallback_messages = {
                    "en": f"I heard your voice memo! Thanks for sending it.",
                    "hi": f"मैंने आपका वॉइस मेमो सुना! भेजने के लिए धन्यवाद।",
                    "fr": f"J'ai entendu ton message vocal! Merci de l'avoir envoyé."
                }
                llm_reply = fallback_messages.get(detected_language or "en", fallback_messages["en"])
        
        # SEND VOICE RESPONSE: Voice memo in → Voice memo out (ALWAYS)
        # Convert response text to speech, then send as audio
        print(f"   🔊 STEP 7: Converting response text → Speech (TTS, {detected_language or 'en'})...")
        tts_wav = await text_to_speech(llm_reply, language=detected_language or "en")
        
        if tts_wav and (os.path.exists(tts_wav) or tts_wav.startswith('s3://')):
            print(f"   ✅ STEP 7 COMPLETE: TTS WAV ready: {tts_wav}")
            
            # Convert WAV to M4A (AAC) for iMessage voice memo
            print(f"   🎵 STEP 8: Converting TTS WAV → M4A (AAC)...")
            loop = asyncio.get_event_loop()
            m4a_file = await loop.run_in_executor(
                CPU_BOUND_EXECUTOR, 
                wav_to_m4a, 
                tts_wav
            )
            
            if m4a_file and (os.path.exists(m4a_file) or m4a_file.startswith('s3://')):
                print(f"   ✅ STEP 8 COMPLETE: M4A file ready: {m4a_file}")
                # Send voice response (with text transcript for API requirement)
                print(f"   📤 STEP 9: Sending VOICE response (voice memo in → voice memo out)...")
                await send_audio(session, chat_id, m4a_file, text=llm_reply)
                print(f"   ✅ STEP 9 COMPLETE: Voice response sent!")
            else:
                # Retry: Try sending WAV directly if M4A conversion fails
                print(f"   ⚠️  M4A conversion failed, trying to send WAV directly...")
                try:
                    await send_audio(session, chat_id, tts_wav, text=llm_reply)
                    print(f"   ✅ Voice response sent as WAV!")
                except Exception as e:
                    # Retry TTS generation if audio send fails
                    print(f"   ⚠️  Audio send failed, retrying TTS generation...")
                    try:
                        # Retry with a simpler message
                        retry_tts = await text_to_speech("Got your voice memo!", language=detected_language or "en")
                        if retry_tts:
                            retry_m4a = await loop.run_in_executor(CPU_BOUND_EXECUTOR, wav_to_m4a, retry_tts)
                            if retry_m4a:
                                await send_audio(session, chat_id, retry_m4a, text="Got your voice memo!")
                                print(f"   ✅ Voice response sent after retry!")
                            else:
                                print(f"   ❌ All audio attempts failed - voice memo cannot be sent")
                        else:
                            print(f"   ❌ TTS retry failed - voice memo cannot be sent")
                    except Exception as retry_error:
                        print(f"   ❌ All voice response attempts failed: {retry_error}")
        else:
            # Retry TTS generation once
            print(f"   ⚠️  TTS failed, retrying once...")
            try:
                retry_tts = await text_to_speech("Got your voice memo!", language=detected_language or "en")
                if retry_tts:
                    retry_m4a = await loop.run_in_executor(CPU_BOUND_EXECUTOR, wav_to_m4a, retry_tts)
                    if retry_m4a:
                        await send_audio(session, chat_id, retry_m4a, text="Got your voice memo!")
                        print(f"   ✅ Voice response sent after retry!")
                    else:
                        print(f"   ❌ All audio attempts failed - voice memo cannot be sent")
                else:
                    print(f"   ❌ TTS retry failed - voice memo cannot be sent")
            except Exception as retry_error:
                print(f"   ❌ All voice response attempts failed: {retry_error}")
        
        # Save context (run in executor) - only if we have a real transcript
        if transcript and transcript != "voice memo":
            def save_context():
                session_manager.add_message(sender, "user", transcript)
                session_manager.add_message(sender, "assistant", llm_reply)
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_context)
        
        await stop_typing(session, chat_id)
        
        # Cleanup temp files (if local and not the final wav_filename)
        if not use_s3 and 'wav_file' in locals() and os.path.exists(wav_file) and wav_file != wav_filename:
            try:
                os.unlink(wav_file)
            except:
                pass

    except Exception as e:
        print(f"   ❌ Error processing audio: {e}")
        traceback.print_exc()
        # Try to send a voice response even on error (voice in → voice out)
        try:
            error_loop = asyncio.get_event_loop()
            error_tts = await text_to_speech("Sorry, couldn't process that voice memo.", language="en")
            if error_tts:
                error_m4a = await error_loop.run_in_executor(CPU_BOUND_EXECUTOR, wav_to_m4a, error_tts)
                if error_m4a:
                    await send_audio(session, chat_id, error_m4a, text="Sorry, couldn't process that voice memo.")
                    print(f"   ✅ Error voice response sent")
                else:
                    print(f"   ❌ Could not send error voice response")
            else:
                print(f"   ❌ Could not generate error voice response")
        except Exception as voice_error:
            print(f"   ❌ Could not send voice error response: {voice_error}")
            # Do NOT send text - voice in must only respond with voice


async def process_text_message(session: aiohttp.ClientSession, event_data: dict):
    """Process incoming text message with multilingual support.
    Text in → Text out (always sends text, never audio)."""
    chat_id = event_data.get("chat_id")
    text = event_data.get("text", "")
    sender = event_data.get("from_phone", "")
    message_id = event_data.get("id", "")
    
    print(f"\n📥 INCOMING TEXT MESSAGE from {sender}: {text}")

    loop = asyncio.get_event_loop()
    
    # Check if this is a group chat
    # Method 1: Check database (for chats created by our system)
    # Method 2: Check chat_handles (for manually created chats)
    is_group_chat = False
    group_chat_info = None
    chat_handles = event_data.get("chat_handles", [])
    
    # Detect group chat by number of participants (chat_handles)
    # Group chat = more than 1 participant (excluding AI)
    if isinstance(chat_handles, list):
        # Count unique participants (excluding AI)
        unique_participants = set()
        for handle in chat_handles:
            phone = None
            if isinstance(handle, str):
                phone = handle
            elif isinstance(handle, dict):
                phone = handle.get('phone_number') or handle.get('phone')
            
            if phone and phone != SENDER_NUMBER:
                unique_participants.add(phone)
        
        if len(unique_participants) > 1:
            is_group_chat = True
            print(f"   👥 Group chat detected: {len(unique_participants)} participants (via chat_handles)")
    
    # Also check database
    try:
        from group_chat_manager import get_group_chat_by_chat_id, store_group_chat_message, get_group_chat_profiles, get_group_chat_history
        
        group_chat_info = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_group_chat_by_chat_id, str(chat_id))
        if group_chat_info:
            is_group_chat = True
            print(f"   👥 Group chat detected in DB: {group_chat_info.get('display_name')}")
            
            # Store message in group chat history
            if message_id:
                # Get user_id from sender phone
                user_id = None
                try:
                    profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
                    if profile:
                        user_id = profile.get('user_id') or sender
                except:
                    user_id = sender
                
                await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    store_group_chat_message,
                    group_chat_info.get('id'),
                    message_id,
                    sender,
                    user_id,
                    text,
                    False  # is_from_ai
                )
                
                # Analyze message: sentiment, topics, boring score, engagement
                try:
                    from group_chat_intelligence import analyze_message
                    analysis = await analyze_message(
                        group_chat_info.get('id'),
                        message_id,
                        text,
                        user_id,
                        sender
                    )
                    print(f"   📊 Message analysis: sentiment={analysis.get('sentiment_score', 0):.2f}, boring={analysis.get('boring_score', 5):.1f}, health={analysis.get('health_score', 0.5):.2f}")
                    
                    # Check if replacement should be offered (boring score >= 4)
                    avg_boring = analysis.get('avg_boring_score', 5.0)
                    print(f"   📊 Average boring score: {avg_boring:.1f} (threshold: 4.0)")
                    if avg_boring >= 4.0:
                        print(f"   ⚠️  Boring score {avg_boring:.1f} >= 4.0 - checking for replacement offers...")
                        try:
                            from match_replacement import check_and_offer_replacements
                            offers = await check_and_offer_replacements(group_chat_info.get('id'))
                            print(f"   💬 Found {len(offers)} replacement offer(s)")
                            for offer in offers:
                                if offer.get('phone_number') and offer.get('message'):
                                    # Send private message to user offering replacement
                                    # Note: This would need to be sent to the user's direct chat, not group chat
                                    print(f"   💬 Replacement offer ready for {offer.get('phone_number')}: {offer.get('message')[:50]}...")
                        except Exception as e:
                            print(f"   ⚠️  Error checking replacement offers: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # Check if topic suggestion should be sent
                    from topic_suggester import should_suggest_topic, get_contextual_suggestion
                    if should_suggest_topic(group_chat_info.get('id')):
                        suggestion = await get_contextual_suggestion(group_chat_info.get('id'))
                        if suggestion:
                            print(f"   💡 Topic suggestion ready: {suggestion}")
                            # Could send this as a proactive message
                except Exception as e:
                    print(f"   ⚠️  Error analyzing message: {e}")
                    import traceback
                    traceback.print_exc()
        elif is_group_chat and not group_chat_info:
            # Group chat exists but not in DB - create record for tracking
            print(f"   📝 Group chat not in DB, creating record...")
            try:
                from group_chat_manager import create_group_chat_record, add_group_chat_participant
                
                # Extract display name from chat_handles or use default
                display_name = f"Group Chat {chat_id[:8]}"
                if chat_handles and len(chat_handles) >= 2:
                    # Try to get names from profiles
                    names = []
                    for handle in chat_handles[:2]:  # First 2 participants
                        if handle.get('phone_number'):
                            profile = await loop.run_in_executor(
                                CPU_BOUND_EXECUTOR,
                                session_manager.get_profile,
                                handle.get('phone_number')
                            )
                            if profile and profile.get('name'):
                                names.append(profile.get('name'))
                    if len(names) >= 2:
                        display_name = f"{names[0]} & {names[1]}"
                
                group_chat_db_id = await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    create_group_chat_record,
                    str(chat_id),
                    display_name
                )
                
                if group_chat_db_id:
                    # Add participants
                    for handle in chat_handles:
                        phone = handle.get('phone_number') or handle.get('phone')
                        if phone:
                            is_ai = (phone == SENDER_NUMBER)
                            await loop.run_in_executor(
                                CPU_BOUND_EXECUTOR,
                                add_group_chat_participant,
                                group_chat_db_id,
                                phone if not is_ai else None,
                                phone,
                                is_ai
                            )
                    
                    # Reload group_chat_info
                    group_chat_info = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        get_group_chat_by_chat_id,
                        str(chat_id)
                    )
                    print(f"   ✅ Group chat record created (ID: {group_chat_db_id})")
            except Exception as e:
                print(f"   ⚠️  Error creating group chat record: {e}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"   ⚠️  Error checking group chat: {e}")
        import traceback
        traceback.print_exc()
    
    # Skip if message is from AI (prevent feedback loop)
    if sender == SENDER_NUMBER:
        print(f"   ⚠️  Ignoring message from AI (feedback loop prevention)")
        return
    
    # Check onboarding status
    is_complete = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.is_onboarding_complete, sender)
    onboarding_state = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_onboarding_state, sender)
    
    print(f"   🔍 Onboarding check: complete={is_complete}, state={onboarding_state}")
    
    # Enhanced /reset command with confirmation
    if text.strip().lower() == "/reset":
        print(f"   🔄 /reset command received for {sender}...")
        
        # Get profile data
        profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
        
        # Format profile summary
        profile_summary = format_profile_summary(profile)
        reset_message = f"{profile_summary}\n\n⚠️ Are you sure you want to reset? This will delete all your data.\n\nReply YES to confirm, or anything else to cancel."
        
        await send_text(session, chat_id, reset_message)
        
        # Set state to reset_confirmation
        await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, "reset_confirmation")
        print("   ✅ Reset confirmation prompt sent.")
        return
    
    # /retry command - retry matching to find a new match
    if text.strip().lower() == "/retry":
        print(f"   🔄 /retry command received for {sender}...")
        await start_typing(session, chat_id)
        
        # Get previous match ID before clearing it
        previous_match_id = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_pending_match, sender)
        
        # Clear previous match
        await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
        
        # Get user profile
        profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
        
        if profile:
            # Find new matches (exclude previous match if possible)
            print(f"   🔍 Finding new matches...")
            matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, find_matches, sender, 5)  # Get top 5 to find a different one
            
            if matches:
                # Get enriched match data
                enriched_matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_match_profiles, matches)
                
                if enriched_matches:
                    # Find first match that's different from previous
                    top_match = None
                    for match in enriched_matches:
                        if match.get('user_id') != previous_match_id:
                            top_match = match
                            break
                    
                    # If all matches are the same, just use the first one
                    if not top_match:
                        top_match = enriched_matches[0]
                    
                    match_score = top_match.get('score', 0.0)
                    
                    # Calculate common hobbies
                    current_hobbies = profile.get('hobbies', '')
                    matched_hobbies = top_match.get('hobbies', '')
                    common = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        calculate_common_hobbies,
                        current_hobbies,
                        matched_hobbies
                    )
                    
                    # Format match message
                    match_msg = format_match_message(top_match, match_score, common)
                    
                    # Send new match message
                    await send_text(session, chat_id, f"🔍 Found you a new match!\n\n{match_msg}")
                    
                    # Store new match info and set state to match_confirmation
                    match_user_id = top_match.get('user_id')
                    if match_user_id:
                        def store_match_info():
                            session_manager.set_pending_match(sender, match_user_id)
                            session_manager.set_onboarding_state(sender, "match_confirmation")
                        await loop.run_in_executor(CPU_BOUND_EXECUTOR, store_match_info)
                        print(f"   ✅ New match found: {top_match.get('name')} (score: {match_score:.2%}) - waiting for confirmation")
                    else:
                        print(f"   ✅ New match found: {top_match.get('name')} (score: {match_score:.2%})")
                else:
                    await send_text(session, chat_id, "Sorry, I couldn't find any other matches right now. Try again later!")
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
            else:
                await send_text(session, chat_id, "Sorry, I couldn't find any other matches right now. Try again later!")
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
        else:
            await send_text(session, chat_id, "Sorry, couldn't retrieve your profile. Please complete onboarding first.")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
        
        await stop_typing(session, chat_id)
        print("   ✅ Retry matching complete.")
        return
    
    # /update command - post or view updates
    if text.strip().lower().startswith("/update"):
        print(f"   📢 /update command received for {sender}...")
        
        # Extract update text (everything after "/update")
        update_text = text[7:].strip()  # Remove "/update" prefix
        
        if not update_text:
            # No text provided - show updates feed
            print(f"   📖 Showing updates feed...")
            from update_manager import get_updates_feed, format_updates_feed
            
            updates = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_updates_feed, 20, sender)
            feed_message = format_updates_feed(updates)
            
            await send_text(session, chat_id, feed_message)
            print("   ✅ Updates feed sent.")
            return
        else:
            # Post new update
            print(f"   📝 Posting update: {update_text[:50]}...")
            from update_manager import post_update
            
            success = await loop.run_in_executor(CPU_BOUND_EXECUTOR, post_update, sender, update_text)
            
            if success:
                await send_text(session, chat_id, "✅ Update posted! People in your network will see this.")
                print("   ✅ Update posted successfully.")
            else:
                await send_text(session, chat_id, "❌ Failed to post update. Please try again later.")
                print("   ⚠️  Failed to post update.")
            return
    
    # Natural language detection for update queries
    # Check if user is asking about updates (before normal conversation flow)
    text_lower = text.strip().lower()
    update_keywords = [
        "what's the latest update",
        "what are the latest updates",
        "show me updates",
        "show updates",
        "latest update",
        "what updates",
        "any updates",
        "recent updates",
        "what's new",
        "whats new",
        "show me what's new",
        "what's happening",
        "whats happening",
        "what are people up to",
        "what's going on"
    ]
    
    is_update_query = any(keyword in text_lower for keyword in update_keywords)
    
    if is_update_query:
        print(f"   📢 Update query detected: {text[:50]}...")
        from update_manager import get_updates_feed, format_updates_feed
        
        updates = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_updates_feed, 20, sender)
        feed_message = format_updates_feed(updates)
        
        await send_text(session, chat_id, feed_message)
        print("   ✅ Updates feed sent in response to query.")
        return
    
    # Handle reset confirmation
    if onboarding_state == "reset_confirmation":
        if text.strip().upper() == "YES":
            print(f"   ✅ Reset confirmed - wiping data for {sender}...")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_profile, sender)
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_history, sender)
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
            
            # Start onboarding
            greeting = get_onboarding_greeting()
            await send_text(session, chat_id, greeting)
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, "greeting")
            print("   ✅ Reset complete - onboarding restarted.")
            return
        else:
            # Cancel reset
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
            await send_text(session, chat_id, "✅ Reset cancelled. Your data is safe!")
            print("   ✅ Reset cancelled.")
            return
    
    # Handle match retry - user wants to find a different match
    if onboarding_state == "match_retry":
        text_lower = text.strip().lower()
        retry_variations = ["retry matching", "retry match", "find another match", "new match", "different match", "try again", "yes", "yeah", "yea", "sure", "ok", "yep", "okay", "y"]
        
        if any(variant in text_lower for variant in retry_variations):
            print(f"   🔄 Retry matching requested by {sender}...")
            await start_typing(session, chat_id)
            
            # Get previous match ID before clearing it
            previous_match_id = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_pending_match, sender)
            
            # Clear previous match
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
            
            # Get user profile
            profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
            
            if profile:
                # Find new matches (exclude previous match if possible)
                print(f"   🔍 Finding new matches...")
                matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, find_matches, sender, 5)  # Get top 5 to find a different one
                
                if matches:
                    # Get enriched match data
                    enriched_matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_match_profiles, matches)
                    
                    if enriched_matches:
                        # Find first match that's different from previous
                        top_match = None
                        for match in enriched_matches:
                            if match.get('user_id') != previous_match_id:
                                top_match = match
                                break
                        
                        # If all matches are the same, just use the first one
                        if not top_match:
                            top_match = enriched_matches[0]
                        
                        match_score = top_match.get('score', 0.0)
                        
                        # Calculate common hobbies
                        current_hobbies = profile.get('hobbies', '')
                        matched_hobbies = top_match.get('hobbies', '')
                        common = await loop.run_in_executor(
                            CPU_BOUND_EXECUTOR,
                            calculate_common_hobbies,
                            current_hobbies,
                            matched_hobbies
                        )
                        
                        # Format match message
                        match_msg = format_match_message(top_match, match_score, common)
                        
                        # Send new match message
                        await send_text(session, chat_id, f"🔍 Found you a new match!\n\n{match_msg}")
                        
                        # Store new match info and set state to match_confirmation
                        match_user_id = top_match.get('user_id')
                        if match_user_id:
                            def store_match_info():
                                session_manager.set_pending_match(sender, match_user_id)
                                session_manager.set_onboarding_state(sender, "match_confirmation")
                            await loop.run_in_executor(CPU_BOUND_EXECUTOR, store_match_info)
                            print(f"   ✅ New match found: {top_match.get('name')} (score: {match_score:.2%}) - waiting for confirmation")
                        else:
                            print(f"   ✅ New match found: {top_match.get('name')} (score: {match_score:.2%})")
                    else:
                        await send_text(session, chat_id, "Sorry, I couldn't find any other matches right now. Try again later!")
                        await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
                else:
                    await send_text(session, chat_id, "Sorry, I couldn't find any other matches right now. Try again later!")
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
            else:
                await send_text(session, chat_id, "Sorry, couldn't retrieve your profile. Please try again later.")
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
            
            await stop_typing(session, chat_id)
            return
        else:
            # User didn't confirm retry - ask again
            await send_text(session, chat_id, "Would you like me to find you a different match? Reply 'retry matching' or 'yes' to find a new match, or 'no' to cancel.")
            return
    
    # Handle match confirmation - keep asking until user says yes
    if onboarding_state == "match_confirmation":
        # Check for "yes" variations (case-insensitive)
        text_lower = text.strip().lower()
        yes_variations = ["yes", "yeah", "yea", "sure", "ok", "yep", "okay", "y", "sounds good", "let's do it", "go ahead", "let's go", "sounds great"]
        
        if any(text_lower == variant or text_lower.startswith(variant + " ") or text_lower.endswith(" " + variant) for variant in yes_variations):
            # User confirmed - create group chat
            print(f"   ✅ Match confirmed by {sender}...")
            
            # Get pending match info
            match_user_id = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_pending_match, sender)
            
            if not match_user_id:
                await send_text(session, chat_id, "Sorry, I couldn't find the match info. Please try again later.")
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
                return
            
            # Get profiles for both users
            user_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
            match_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, match_user_id)
            
            if not user_profile or not match_profile:
                await send_text(session, chat_id, "Sorry, couldn't retrieve profile information. Please try again later.")
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
                return
            
            # Get common hobbies
            user_hobbies = user_profile.get('hobbies', '')
            match_hobbies = match_profile.get('hobbies', '')
            common = await loop.run_in_executor(
                CPU_BOUND_EXECUTOR,
                calculate_common_hobbies,
                user_hobbies,
                match_hobbies
            )
            
            # Create group chat
            try:
                group_chat_id = await create_group_chat(
                    session,
                    sender,
                    match_user_id,
                    user_profile.get('name', 'User'),
                    match_profile.get('name', 'Match'),
                    common
                )
                
                if group_chat_id:
                    # Record match in database and link to group chat
                    def record_match():
                        from embedding_service import get_supabase_client
                        from group_chat_manager import get_group_chat_by_chat_id
                        client = get_supabase_client()
                        if client:
                            # Get match score from previous match
                            try:
                                matches = find_matches(sender, 5)  # Get more matches to find the right one
                                match_score = 0.0
                                if matches:
                                    for m in matches:
                                        if m.get('user_id') == match_user_id:
                                            match_score = m.get('score', 0.0)
                                            break
                                
                                # Insert match
                                match_response = client.table('matches').insert({
                                    'user1_id': sender,
                                    'user2_id': match_user_id,
                                    'score': match_score,
                                    'status': 'accepted'
                                }).execute()
                                
                                match_db_id = match_response.data[0].get('id') if match_response.data else None
                                
                                # Link group chat to match
                                if match_db_id:
                                    group_chat_info = get_group_chat_by_chat_id(str(group_chat_id))
                                    if group_chat_info:
                                        client.table('group_chats').update({
                                            'match_id': match_db_id
                                        }).eq('id', group_chat_info.get('id')).execute()
                                        print(f"   ✅ Group chat linked to match")
                                
                                print(f"   ✅ Match recorded in database: {sender} ↔ {match_user_id} (score: {match_score:.2%})")
                            except Exception as e:
                                print(f"   ⚠️  Error recording match: {e}")
                    
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, record_match)
                    
                    # Clear pending match and reset state
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, None)
                    
                    await send_text(session, chat_id, f"✅ Group chat created! Check your messages.")
                    print(f"   ✅ Group chat created successfully: {group_chat_id}")
                else:
                    # Group chat creation failed - offer retry matching
                    await send_text(session, chat_id, "Sorry, couldn't create the group chat. Would you like me to find you a different match? Reply 'retry matching' or 'yes' to find a new match.")
                    # Keep match info and set state to allow retry
                    await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, "match_retry")
            except Exception as e:
                print(f"   ❌ Error creating group chat: {e}")
                traceback.print_exc()
                # Group chat creation failed - offer retry matching
                await send_text(session, chat_id, "Sorry, there was an error creating the group chat. Would you like me to find you a different match? Reply 'retry matching' or 'yes' to find a new match.")
                # Keep match info and set state to allow retry
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, "match_retry")
            return
        else:
            # User said something other than yes - keep asking for confirmation
            print(f"   ⚠️  User response not 'yes': '{text}' - re-asking for match confirmation")
            
            # Get match info to re-display
            match_user_id = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_pending_match, sender)
            
            if match_user_id:
                # Get match profile to re-display
                match_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, match_user_id)
                user_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
                
                if match_profile and user_profile:
                    # Re-format match message
                    matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, find_matches, sender, 5)
                    match_score = 0.0
                    for m in matches:
                        if m.get('user_id') == match_user_id:
                            match_score = m.get('score', 0.0)
                            break
                    
                    user_hobbies = user_profile.get('hobbies', '')
                    match_hobbies = match_profile.get('hobbies', '')
                    common = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        calculate_common_hobbies,
                        user_hobbies,
                        match_hobbies
                    )
                    
                    match_msg = format_match_message(match_profile, match_score, common)
                    
                    # Re-ask for confirmation
                    await send_text(session, chat_id, f"{match_msg}\n\nWould you like to start chatting? Reply YES to confirm.")
                else:
                    await send_text(session, chat_id, "I found someone for you! Would you like to start chatting? Reply YES to confirm.")
            else:
                # Match info lost, re-ask
                await send_text(session, chat_id, "Would you like to start chatting with your match? Reply YES to confirm.")
            
            # Keep state as match_confirmation to continue asking
            print(f"   ✅ Re-asked for match confirmation - state remains 'match_confirmation'")
            return
    
    # Handle onboarding flow
    if not is_complete:
        print(f"   🎯 Entering onboarding flow (complete={is_complete}, state={onboarding_state})")
        await start_typing(session, chat_id)
        
        # If no state, start onboarding
        if not onboarding_state or onboarding_state == "greeting":
            print(f"   🚀 Starting onboarding - sending greeting and first question")
            greeting = get_onboarding_greeting()
            first_question = get_question("name")
            await send_text(session, chat_id, f"{greeting}\n\n{first_question}")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, "name")
            await stop_typing(session, chat_id)
            print(f"   ✅ Onboarding started - state set to 'name'")
            return
        
        # Process onboarding answer
        is_valid, error_msg = validate_answer(onboarding_state, text)
        
        if not is_valid:
            question = get_question(onboarding_state)
            await send_text(session, chat_id, f"❌ {error_msg}\n\n{question}")
            await stop_typing(session, chat_id)
            return
        
        # Extract the actual value from the answer (e.g., "my name is siddharth" -> "siddharth")
        extracted_value = extract_value(onboarding_state, text)
        
        # Save answer
        profile_update = {}
        if onboarding_state == "name":
            profile_update["name"] = extracted_value
        elif onboarding_state == "school":
            profile_update["school"] = extracted_value
        elif onboarding_state == "age":
            profile_update["age"] = int(extracted_value)
        elif onboarding_state == "hobbies":
            profile_update["hobbies"] = extracted_value
        
        # Update profile (wrap in lambda to handle kwargs)
        def update_profile_wrapper():
            session_manager.update_profile(sender, **profile_update)
        await loop.run_in_executor(CPU_BOUND_EXECUTOR, update_profile_wrapper)
        
        # Move to next state
        next_state = get_next_state(onboarding_state)
        
        if next_state == "complete":
            # Clear any existing pending match before starting fresh matching process
            print(f"   🔄 Clearing any existing pending match before starting fresh matching...")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.clear_pending_match, sender)
            
            # Mark onboarding complete (wrap in function to handle kwargs)
            def complete_onboarding():
                session_manager.update_profile(sender, onboarding_complete=True, onboarding_state="complete")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, complete_onboarding)
            profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
            
            # Generate embedding and find match
            print(f"   🧠 Generating personality embedding...")
            embedding = await loop.run_in_executor(CPU_BOUND_EXECUTOR, generate_user_embedding, profile)
            
            if embedding:
                # Store embedding
                def store_embedding_wrapper():
                    store_embedding(sender, embedding)
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, store_embedding_wrapper)
                
                # Find matches
                print(f"   🔍 Finding matches...")
                matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, find_matches, sender, 1)
                
                if matches:
                    # Get enriched match data
                    enriched_matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_match_profiles, matches)
                    
                    if enriched_matches:
                        top_match = enriched_matches[0]
                        match_score = top_match.get('score', 0.0)
                        
                        # Calculate common hobbies
                        current_hobbies = profile.get('hobbies', '')
                        matched_hobbies = top_match.get('hobbies', '')
                        common = await loop.run_in_executor(
                            CPU_BOUND_EXECUTOR,
                            calculate_common_hobbies,
                            current_hobbies,
                            matched_hobbies
                        )
                        
                        # Format match message
                        match_msg = format_match_message(top_match, match_score, common)
                        
                        # Send completion + match message
                        completion_msg = get_completion_message(profile)
                        full_message = f"{completion_msg}\n\n{match_msg}"
                        await send_text(session, chat_id, full_message)
                        
                        # Store match info and set state to match_confirmation
                        match_user_id = top_match.get('user_id')
                        if match_user_id:
                            def store_match_info():
                                session_manager.set_pending_match(sender, match_user_id)
                                session_manager.set_onboarding_state(sender, "match_confirmation")
                            await loop.run_in_executor(CPU_BOUND_EXECUTOR, store_match_info)
                            print(f"   ✅ Match found: {top_match.get('name')} (score: {match_score:.2%}) - waiting for confirmation")
                        else:
                            print(f"   ✅ Match found: {top_match.get('name')} (score: {match_score:.2%})")
                    else:
                        # No enriched matches, just send completion
                        completion_msg = get_completion_message(profile)
                        await send_text(session, chat_id, completion_msg)
                else:
                    # No matches found, just send completion
                    completion_msg = get_completion_message(profile)
                    await send_text(session, chat_id, completion_msg)
            else:
                # Embedding generation failed, just send completion
                completion_msg = get_completion_message(profile)
                await send_text(session, chat_id, completion_msg)
            
            await stop_typing(session, chat_id)
            print(f"   ✅ Onboarding complete! Profile saved: {profile}")
            return
        else:
            # Ask next question
            next_question = get_question(next_state)
            await send_text(session, chat_id, f"Got it! 👍\n\n{next_question}")
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.set_onboarding_state, sender, next_state)
            await stop_typing(session, chat_id)
            return
    
    # Normal conversation flow (onboarding complete)
    print(f"   💬 Onboarding complete - using normal conversation flow")
    
    # Check if user is asking about their match/team/group chat
    text_lower = text.strip().lower()
    match_queries = [
        "do i have a team", "do i have a match", "who is my match", "who is my teammate",
        "show me my team", "show me my match", "what's my team", "what's my match",
        "who did you match me with", "who am i matched with", "tell me about my match",
        "my team", "my match", "my teammate", "have i been matched"
    ]
    
    is_match_query = any(query in text_lower for query in match_queries)
    
    if is_match_query and not is_group_chat:
        # User is asking about their match/team - check database
        print(f"   🔍 User asking about match/team - checking database...")
        await start_typing(session, chat_id)
        
        try:
            # Get user's profile to get user_id
            profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
            user_id = profile.get('user_id') if profile else sender
            
            # Check for pending match
            pending_match_id = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_pending_match, sender)
            
            # Check for active matches in database
            def get_user_matches():
                from embedding_service import get_supabase_client
                client = get_supabase_client()
                if not client:
                    return []
                
                try:
                    # Get matches where user is either user1 or user2
                    result = client.table('matches')\
                        .select('id, user1_id, user2_id, score, status, matched_at')\
                        .or_(f'user1_id.eq.{user_id},user2_id.eq.{user_id}')\
                        .eq('status', 'accepted')\
                        .order('matched_at', desc=True)\
                        .limit(5)\
                        .execute()
                    
                    return result.data if result.data else []
                except Exception as e:
                    print(f"   ⚠️  Error getting matches: {e}")
                    return []
            
            matches = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_user_matches)
            
            # Check for group chats
            def get_user_group_chats():
                from embedding_service import get_supabase_client
                client = get_supabase_client()
                if not client:
                    return []
                
                try:
                    # Get group chats where user is a participant
                    result = client.table('group_chat_participants')\
                        .select('group_chat_id, group_chats!inner(id, display_name, created_at, match_id)')\
                        .eq('user_id', user_id)\
                        .eq('is_ai', False)\
                        .execute()
                    
                    return result.data if result.data else []
                except Exception as e:
                    print(f"   ⚠️  Error getting group chats: {e}")
                    return []
            
            group_chats = await loop.run_in_executor(CPU_BOUND_EXECUTOR, get_user_group_chats)
            
            # Build response
            response_parts = []
            
            if pending_match_id:
                # User has a pending match waiting for confirmation
                match_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, pending_match_id)
                match_name = match_profile.get('name', 'your match') if match_profile else 'your match'
                response_parts.append(f"🔍 You have a pending match with **{match_name}** waiting for your confirmation!")
                response_parts.append(f"Say 'yes' to open the chat with them.")
            elif matches:
                # User has accepted matches
                match_info = []
                for match in matches[:3]:  # Show up to 3 matches
                    other_user_id = match['user2_id'] if match['user1_id'] == user_id else match['user1_id']
                    other_profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, other_user_id)
                    other_name = other_profile.get('name', 'Unknown') if other_profile else 'Unknown'
                    score = match.get('score', 0)
                    match_info.append(f"**{other_name}** (match strength: {score:.0%})")
                
                if match_info:
                    response_parts.append(f"✅ You're matched with:")
                    response_parts.append("\n".join(f"• {info}" for info in match_info))
            elif group_chats:
                # User has group chats
                chat_info = []
                for gc in group_chats[:3]:  # Show up to 3 group chats
                    gc_data = gc.get('group_chats', {}) if isinstance(gc.get('group_chats'), dict) else {}
                    display_name = gc_data.get('display_name', 'Group Chat')
                    chat_info.append(f"**{display_name}**")
                
                if chat_info:
                    response_parts.append(f"💬 You're in these group chats:")
                    response_parts.append("\n".join(f"• {info}" for info in chat_info))
            else:
                # No matches or group chats
                response_parts.append("You don't have an active match or team yet.")
                response_parts.append("Complete onboarding and I'll find you someone great! 🎯")
            
            response = "\n\n".join(response_parts)
            await send_text(session, chat_id, response)
            await stop_typing(session, chat_id)
            
            # Save to history
            def save_context():
                session_manager.add_message(sender, "user", text)
                session_manager.add_message(sender, "assistant", response)
            await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_context)
            
            print(f"   ✅ Match/team query handled")
            return
            
        except Exception as e:
            print(f"   ⚠️  Error handling match query: {e}")
            import traceback
            traceback.print_exc()
            # Fall through to normal conversation flow
    
    # Detect language
    detected_language = await detect_language(text)
    lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
    lang_name = lang_names.get(detected_language, "Unknown")
    print(f"   🌐 Detected language: {lang_name}")
    
    await start_typing(session, chat_id)
    
    # Get user history and profile
    history = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_history, sender)
    behavior_context = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.analyze_behavior, sender)
    profile = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_profile, sender)
    
    print(f"   🧠 Behavioral Context: {behavior_context}")
    
    # If group chat, get group context
    group_context = None
    if is_group_chat:
        try:
            participants = []
            display_name = "Group Chat"
            group_history = []
            
            if group_chat_info:
                # Group chat is in database - get full context
                from group_chat_manager import get_group_chat_profiles, get_group_chat_history
                
                participants = await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    get_group_chat_profiles,
                    group_chat_info.get('id')
                )
                
                group_history = await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    get_group_chat_history,
                    group_chat_info.get('id'),
                    20  # Last 20 messages
                )
                
                display_name = group_chat_info.get('display_name', 'Group Chat')
            else:
                # Group chat not in DB - build context from chat_handles
                display_name = f"Group Chat {chat_id[:8]}"
                
                # Get profiles for participants from chat_handles
                if isinstance(chat_handles, list):
                    seen_phones = set()
                    for handle in chat_handles:
                        phone = None
                        if isinstance(handle, str):
                            phone = handle
                        elif isinstance(handle, dict):
                            phone = handle.get('phone_number') or handle.get('phone')
                        
                        if phone and phone != SENDER_NUMBER and phone not in seen_phones:
                            seen_phones.add(phone)
                            profile = await loop.run_in_executor(
                                CPU_BOUND_EXECUTOR,
                                session_manager.get_profile,
                                phone
                            )
                            if profile:
                                participants.append(profile)
                            else:
                                # Add basic info if no profile
                                participants.append({
                                    "phone": phone,
                                    "name": phone[-4:]  # Last 4 digits as identifier
                                })
                    
                    # Try to create display name from participant names
                    if len(participants) >= 2:
                        names = [p.get('name', '') for p in participants[:2] if p.get('name')]
                        if len(names) >= 2:
                            display_name = f"{names[0]} & {names[1]}"
            
            # Get enhanced group context: engagement, topics, sentiment
            engagement_insights = None
            recent_topics = []
            health_metrics = None
            common_hobbies = []
            
            if group_chat_info:
                try:
                    from group_chat_intelligence import get_engagement_insights, get_recent_topics
                    from group_chat_manager import get_group_chat_health_metrics
                    
                    engagement_insights = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        get_engagement_insights,
                        group_chat_info.get('id')
                    )
                    
                    topics_data = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        get_recent_topics,
                        group_chat_info.get('id'),
                        5
                    )
                    recent_topics = [t.get('topic_text') for t in topics_data if t.get('topic_text')]
                    
                    health_metrics = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR,
                        get_group_chat_health_metrics,
                        group_chat_info.get('id')
                    )
                    
                    # Get common hobbies from group chat
                    common_hobbies = group_chat_info.get('common_hobbies', [])
                    
                    print(f"   📊 Engagement: {len(engagement_insights.get('active_participants', []))} active, {len(engagement_insights.get('quiet_participants', []))} quiet")
                    print(f"   📝 Topics: {len(recent_topics)} recent topics")
                except Exception as e:
                    print(f"   ⚠️  Error getting enhanced context: {e}")
            
            group_context = {
                "is_group_chat": True,
                "display_name": display_name,
                "participants": participants,
                "recent_messages": group_history,
                "engagement_insights": engagement_insights,
                "recent_topics": recent_topics,
                "health_metrics": health_metrics,
                "common_hobbies": common_hobbies
            }
            print(f"   👥 Group context: {len(participants)} participants, {len(group_history)} recent messages")
        except Exception as e:
            print(f"   ⚠️  Error getting group context: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        reply = await get_llm_response(
            text, 
            history, 
            language=detected_language or "en", 
            behavior_context=behavior_context, 
            profile=profile,
            group_context=group_context
        )
        print(f"   💬 LLM Response ({lang_name}): {reply[:100]}...")
        
        # Save context (run in executor)
        def save_context():
            session_manager.add_message(sender, "user", text)
            session_manager.add_message(sender, "assistant", reply)
        await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_context)
        
        # Store AI response in group chat if applicable
        if is_group_chat and group_chat_info and message_id:
            try:
                from group_chat_manager import store_group_chat_message
                await loop.run_in_executor(
                    CPU_BOUND_EXECUTOR,
                    store_group_chat_message,
                    group_chat_info.get('id'),
                    f"ai_{message_id}",  # AI message ID
                    SENDER_NUMBER,
                    None,
                    reply,
                    True  # is_from_ai
                )
            except Exception as e:
                print(f"   ⚠️  Error storing AI message in group chat: {e}")
        
    except Exception as e:
        print(f"   ❌ LLM error in normal conversation: {e}")
        print(f"   ❌ Error type: {type(e).__name__}")
        traceback.print_exc()
        fallbacks = {
            "en": f"Hey! 👋 I'm here! What's up?",
            "hi": f"नमस्ते! 👋 मैं यहाँ हूँ! क्या हो रहा है?",
            "fr": f"Salut! 👋 Je suis là! Qu'est-ce qui se passe?"
        }
        reply = fallbacks.get(detected_language, fallbacks["en"])
    
    # TEXT IN → TEXT OUT: Always send text response for text messages
    print(f"   📤 Sending TEXT response (text in → text out)...")
    await send_text(session, chat_id, reply)
    await stop_typing(session, chat_id)


async def consume():
    """Main consumer loop."""
    print("🚀 Starting AIOKafka Consumer...")
    
    # Create SSL context
    import ssl
    ssl_context = ssl.create_default_context()
    
    # Initialize Kafka Consumer with proper timeouts to prevent rebalancing
    consumer = AIOKafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        client_id=CLIENT_ID,
        security_protocol='SASL_SSL',
        sasl_mechanism='PLAIN',
        sasl_plain_username=KAFKA_SASL_USERNAME,
        sasl_plain_password=KAFKA_SASL_PASSWORD,
        ssl_context=ssl_context,
        auto_offset_reset='latest',
        enable_auto_commit=False,
        session_timeout_ms=30000,  # 30 seconds
        heartbeat_interval_ms=10000,  # 10 seconds - must be < session_timeout_ms/3
        max_poll_interval_ms=300000,  # 5 minutes - max time between polls
        max_poll_records=10  # Process up to 10 messages per poll
    )

    await consumer.start()
    print("✅ Kafka Consumer started!")
    
    # Verify topic access
    try:
        topics = await consumer.list_topics()
        if TOPIC_NAME in topics:
            print(f"✅ Topic '{TOPIC_NAME}' found")
            partitions = topics[TOPIC_NAME]
            print(f"   📊 Topic has {len(partitions)} partition(s)")
        else:
            print(f"⚠️  Topic '{TOPIC_NAME}' not found in available topics")
            print(f"   Available topics: {list(topics.keys())[:10]}")
    except Exception as e:
        print(f"⚠️  Could not list topics: {e}")
    
    # Wait for partition assignment (can take a moment)
    print("⏳ Waiting for partition assignment...")
    await asyncio.sleep(2)  # Give Kafka time to assign partitions
    
    # Get partition information and check for messages
    print("⏩ Checking partition offsets...")
    try:
        partitions = consumer.assignment()
        print(f"   📊 Assigned partitions: {[p.partition for p in partitions] if partitions else 'None'}")
        if partitions:
            # Check committed offsets vs latest offsets
            for partition in partitions:
                # Get committed offset (where we last left off)
                committed = await consumer.committed(partition)
                # Ensure committed_offset is always a valid integer
                if committed is None:
                    committed_offset = -1
                elif isinstance(committed, (int, type(None))):
                    committed_offset = committed if committed is not None else -1
                else:
                    # Handle unexpected type
                    print(f"   ⚠️  Unexpected committed type: {type(committed)}, defaulting to -1")
                    committed_offset = -1
                
                # Get latest offset (end of partition)
                await consumer.seek_to_end(partition)
                latest_offset = await consumer.position(partition)
                
                # Get beginning offset (start of partition)
                await consumer.seek_to_beginning(partition)
                beginning_offset = await consumer.position(partition)
                
                print(f"   📍 Partition {partition.partition}:")
                print(f"      Beginning: {beginning_offset}, Committed: {committed_offset}, Latest: {latest_offset}")
                
                # If there are messages between committed and latest, we should process them
                if latest_offset > committed_offset and committed_offset >= 0:
                    messages_available = latest_offset - committed_offset
                    print(f"      ⚠️  {messages_available} message(s) available between committed and latest!")
                    # Seek to committed position to process those messages
                    # committed_offset is guaranteed to be >= 0 here, so it's safe to use
                    try:
                        await consumer.seek(partition, committed_offset)
                        print(f"      ✅ Seeking to committed offset {committed_offset} to process available messages")
                    except Exception as seek_error:
                        print(f"      ⚠️  Error seeking to {committed_offset}: {seek_error}, positioning at latest")
                        await consumer.seek_to_end(partition)
                elif committed_offset < 0 and latest_offset > beginning_offset:
                    # No committed offset, but there are messages - process from beginning to catch up
                    messages_available = latest_offset - beginning_offset
                    print(f"      ⚠️  No committed offset, but {messages_available} message(s) available!")
                    # Process from beginning to catch up on missed messages
                    await consumer.seek(partition, beginning_offset)
                    print(f"      ✅ Seeking to beginning ({beginning_offset}) to process available messages")
                elif latest_offset > beginning_offset:
                    # No committed offset, but there are messages - process from latest to only get NEW messages
                    await consumer.seek_to_end(partition)
                    print(f"      ✅ No committed offset, positioned at latest ({latest_offset}) for NEW messages only")
                else:
                    # No messages available
                    await consumer.seek_to_end(partition)
                    print(f"      ✅ No messages, positioned at end ({latest_offset})")
            
            # Don't commit yet - let messages be processed first
            print("   ✅ Positioned for message consumption")
        else:
            print("   ⚠️  No partitions assigned yet - waiting...")
            await asyncio.sleep(3)
            partitions = consumer.assignment()
            if partitions:
                print(f"   ✅ Partitions assigned: {[p.partition for p in partitions]}")
                for partition in partitions:
                    committed = await consumer.committed(partition)
                    # Ensure committed_offset is always a valid integer
                    if committed is None:
                        committed_offset = -1
                    elif isinstance(committed, (int, type(None))):
                        committed_offset = committed if committed is not None else -1
                    else:
                        committed_offset = -1
                    
                    await consumer.seek_to_end(partition)
                    latest_offset = await consumer.position(partition)
                    if latest_offset > committed_offset and committed_offset >= 0:
                        try:
                            await consumer.seek(partition, committed_offset)
                            print(f"   📍 Partition {partition.partition}: seeking to committed {committed_offset} (latest: {latest_offset})")
                        except Exception as seek_error:
                            print(f"   ⚠️  Error seeking to {committed_offset}: {seek_error}, positioning at latest")
                            await consumer.seek_to_end(partition)
                            print(f"   📍 Partition {partition.partition}: positioned at latest {latest_offset}")
                    else:
                        await consumer.seek_to_end(partition)
                        print(f"   📍 Partition {partition.partition}: positioned at latest {latest_offset}")
            else:
                print("   ❌ Still no partitions assigned - check Kafka connection")
    except Exception as e:
        print(f"   ⚠️  Error checking offsets: {e}")
        import traceback
        traceback.print_exc()
    
    print("🔄 Waiting for messages...")

    # Shared aiohttp session
    async with aiohttp.ClientSession() as session:
        try:
            print("🔄 Waiting for messages...")
            message_count = 0
            last_heartbeat = time.time()
            
            # Use getmany with timeout to allow heartbeat checks
            while True:
                # Poll for messages with timeout
                try:
                    msg_pack = await consumer.getmany(timeout_ms=1000, max_records=10)
                    if msg_pack:
                        print(f"   📦 Received {sum(len(msgs) for msgs in msg_pack.values())} message(s) from Kafka")
                except Exception as e:
                    print(f"   ⚠️  Error polling messages: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1)
                    continue
                
                if not msg_pack:
                    # No messages - check heartbeat and verify we're not stuck
                    current_time = time.time()
                    if current_time - last_heartbeat > 30:
                        # Check partition positions and offsets for debugging
                        try:
                            partitions = consumer.assignment()
                            if partitions:
                                pos_info = []
                                offset_info = []
                                for p in partitions:
                                    try:
                                        pos = await consumer.position(p)
                                        # Get latest offset
                                        await consumer.seek_to_end(p)
                                        latest = await consumer.position(p)
                                        # Restore position
                                        await consumer.seek(p, pos)
                                        
                                        pos_info.append(f"P{p.partition}:{pos}")
                                        if latest > pos:
                                            offset_info.append(f"P{p.partition}: {latest-pos} msgs ahead ⚠️")
                                            print(f"   ⚠️  WARNING: Partition {p.partition} has {latest-pos} unprocessed message(s)! Current: {pos}, Latest: {latest}")
                                    except Exception as e:
                                        pos_info.append(f"P{p.partition}:?")
                                
                                status = f"Positions: {', '.join(pos_info)}"
                                if offset_info:
                                    status += f" | ⚠️  {', '.join(offset_info)}"
                                print(f"💓 Consumer heartbeat - waiting for messages... (processed {message_count} so far) | {status}")
                            else:
                                print(f"💓 Consumer heartbeat - waiting for messages... (processed {message_count} so far) | No partitions assigned!")
                        except Exception as e:
                            print(f"💓 Consumer heartbeat - waiting for messages... (processed {message_count} so far) | Error checking positions: {e}")
                        last_heartbeat = current_time
                    continue
                
                # Process all messages in the batch
                # Sort messages by partition and offset to ensure order within each partition
                sorted_messages = []
                for topic_partition, messages in msg_pack.items():
                    for msg in messages:
                        sorted_messages.append((topic_partition, msg))
                
                # Sort by partition first, then by offset within partition
                sorted_messages.sort(key=lambda x: (x[0].partition, x[1].offset))
                
                for topic_partition, msg in sorted_messages:
                    message_count += 1
                    try:
                        event = json.loads(msg.value.decode('utf-8'))
                        
                        # Log basics
                        event_type = event.get("event_type")
                        event_id = event.get("event_id") or "N/A"
                        print(f"\n{'='*60}")
                        print(f"📨 EVENT #{message_count}: {event_type} | ID: {event_id} | Offset: {msg.offset} | Partition: {msg.partition}")
                        print(f"{'='*60}")

                        # FILTER: Check for malformed error events (feedback loop prevention)
                        if not event_type:
                            if "llm_response" in event or "error" in event:
                                print("⚠️  IGNORING malformed event (feedback loop)")
                                await consumer.commit()
                                continue
                            # If truly unknown, log and continue
                            print("⚠️  Missing event_type, skipping.")
                            await consumer.commit()
                            continue

                        # Extract data
                        data = event.get("data", {})
                        
                        # DEBUG: Log message structure
                        print(f"   🔍 DEBUG: Message data keys: {list(data.keys())}")
                        if "text" in data:
                            print(f"   🔍 DEBUG: Text content: '{data.get('text', '')[:50]}...'")
                        if "audio" in data:
                            print(f"   🔍 DEBUG: Audio data present")
                        if "attachments" in data:
                            print(f"   🔍 DEBUG: Attachments: {len(data.get('attachments', []))} items")
                        
                        # Determine message type
                        if event_type == "message.received":
                            # Check for audio
                            has_audio = False
                            audio_data_to_process = None
                            
                            # Logic to find audio (same as sync consumer)
                            if "audio" in data:
                                has_audio = True
                                audio_data_to_process = data
                                print(f"   🔍 DEBUG: Found audio in data.audio")
                            elif isinstance(data.get("message"), dict) and "audio" in data.get("message", {}):
                                has_audio = True
                                audio_data_to_process = data.copy()
                                audio_data_to_process["audio"] = data["message"]["audio"]
                                print(f"   🔍 DEBUG: Found audio in data.message.audio")
                            elif isinstance(data.get("attachments"), list):
                                for att in data.get("attachments", []):
                                    if isinstance(att, dict) and (att.get("type") == "audio" or att.get("mime_type", "").startswith("audio/")):
                                        has_audio = True
                                        audio_data_to_process = data.copy()
                                        audio_data_to_process["audio"] = {
                                            "format": att.get("format", "opus"),
                                            "data": att.get("data") or att.get("base64_data"),
                                            "url": att.get("url")
                                        }
                                        print(f"   🔍 DEBUG: Found audio in attachments")
                                        break
                            
                            if has_audio and audio_data_to_process:
                                # Process audio synchronously to ensure commit happens after success
                                print(f"   🎤 Processing as AUDIO message...")
                                try:
                                    await process_audio_message(session, audio_data_to_process)
                                    await consumer.commit()
                                    print(f"   ✅ Offset {msg.offset} committed successfully")
                                except Exception as e:
                                    print(f"   ❌ Error processing audio: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Don't commit on error - will retry
                                    # Re-raise to stop consumer and retry on restart
                                    raise
                            elif "text" in data and data.get("text", "").strip():
                                # Process text synchronously to ensure commit happens after success
                                print(f"   💬 Processing as TEXT message...")
                                print(f"   📝 Text: '{data.get('text', '')[:100]}'")
                                print(f"   📞 From: {data.get('from_phone', 'Unknown')}")
                                print(f"   💬 Chat ID: {data.get('chat_id', 'Unknown')}")
                                try:
                                    await process_text_message(session, data)
                                    await consumer.commit()
                                    print(f"   ✅ Offset {msg.offset} committed successfully")
                                except Exception as e:
                                    print(f"   ❌ Error processing text: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Don't commit on error - will retry
                                    # Re-raise to stop consumer and retry on restart
                                    raise
                            elif "text" in data and not data.get("text", "").strip():
                                # Empty text - might be a voice memo with no transcript
                                print(f"   ⚠️  Empty text field - checking for audio...")
                                if has_audio:
                                    print(f"   🎤 Processing as AUDIO (empty text)...")
                                    try:
                                        await process_audio_message(session, audio_data_to_process or data)
                                        await consumer.commit()
                                        print(f"   ✅ Offset {msg.offset} committed successfully")
                                    except Exception as e:
                                        print(f"   ❌ Error processing audio: {e}")
                                        traceback.print_exc()
                                        raise
                                else:
                                    print(f"   ⚠️  Empty text and no audio - skipping")
                                    await consumer.commit()
                            else:
                                # Unknown message format - log details before skipping
                                print(f"   ⚠️  Unknown message format - data keys: {list(data.keys())}")
                                print(f"   ⚠️  Full data: {json.dumps(data, indent=2)[:500]}...")
                                await consumer.commit()
                            
                        elif event_type == "typing_indicator.received":
                            print(f"   ⌨️  User is typing...")
                            await consumer.commit()
                        
                        else:
                            # Other event types - commit to acknowledge
                            await consumer.commit()
                    
                    except Exception as e:
                            print(f"\n❌ ERROR processing message at offset {msg.offset}: {e}")
                            print(f"   Error Type: {type(e).__name__}")
                            print(f"   Event Type: {event.get('event_type', 'UNKNOWN')}")
                            print(f"   Event ID: {event.get('event_id', 'N/A')}")
                            try:
                                print(f"   Data keys: {list(event.get('data', {}).keys())}")
                            except:
                                pass
                            traceback.print_exc()
                            print(f"{'='*60}\n")
                            # Don't commit on error - will retry on restart
                            # This ensures we don't lose messages
                            # But we should log this so we can debug
                            continue  # Continue to next message instead of stopping
                    
        finally:
            print("👋 Stopping consumer...")
            await consumer.stop()

if __name__ == "__main__":
    # Start health check HTTP server for Shipyard routing
    try:
        from health_server import start_health_server
        health_port = int(os.getenv('HEALTH_PORT', '8080'))
        start_health_server(health_port)
    except Exception as e:
        print(f"⚠️  Could not start health server: {e}")
        # Continue anyway - health server is optional
    
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
