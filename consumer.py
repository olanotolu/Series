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
from datetime import datetime
from dotenv import load_dotenv

# Async libraries
import aiohttp
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaError

# Reuse existing utilities (will be run in executor if blocking)
from opus_to_wav import opus_to_wav
from dlq_handler import send_to_dlq, classify_error, is_recoverable_error
from session_manager import SessionManager

# Initialize Session Manager
session_manager = SessionManager()

# Hugging Face Async Client
try:
    from huggingface_hub import AsyncInferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  huggingface_hub not installed. Install with: pip install huggingface_hub")

# Load environment variables
load_dotenv()

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

# Language Detection
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    print("⚠️  langdetect not installed. Install with: pip install langdetect")

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
        hf_client = AsyncInferenceClient(token=HF_TOKEN)
        print("✅ Hugging Face Async Inference API client initialized!")
        return True
    except Exception as e:
        print(f"❌ Error initializing HF client: {e}")
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


async def get_llm_response(text: str, history: list = None, language: str = "en") -> str:
    """Get response from LLM using Hugging Face Inference API.
    Responds in the detected language (English, Hindi, or French)."""
    global hf_client
    
    if hf_client is None:
        if not await init_hf_client():
            return f"You said: {text}"
    
    try:
        print(f"   🤖 Getting LLM response via Async Inference API...")
        
        # Multilingual system prompt - responds in the same language as the user
        lang_instructions = {
            "en": "Respond in English. Be warm, engaging, and natural.",
            "hi": "Respond in Hindi (Devanagari script). Be warm, engaging, and natural. Use Hindi naturally and conversationally.",
            "fr": "Respond in French. Be warm, engaging, and natural. Use French naturally and conversationally."
        }
        
        lang_instruction = lang_instructions.get(language, lang_instructions["en"])
        
        system_prompt = f"""You are a friendly, helpful friend chatting on Series.so, a social network platform. 
You're having a casual conversation with someone you know. {lang_instruction}
Keep responses concise (1-3 sentences typically), use casual language, and show genuine interest in the conversation.
You can use emojis occasionally to add personality, but don't overdo it. Be yourself - friendly, supportive, and authentic.
IMPORTANT: Always respond in the same language the user is using. If they write in Hindi, respond in Hindi. If they write in French, respond in French."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history if provided
        if history:
            messages.extend(history)
            
        # Add current message
        messages.append({"role": "user", "content": text})
        
        # Use Meta-Llama-3.2-3B-Instruct (reliable and fast via API, supports multilingual)
        response = await hf_client.chat_completion(
            messages=messages,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_tokens=512
        )
        
        reply = response.choices[0].message.content.strip()
        
        if not reply or len(reply) < 3:
            fallbacks = {
                "en": f"I understand you said: {text}. How can I help?",
                "hi": f"मैं समझ गया: {text}. मैं कैसे मदद कर सकता हूं?",
                "fr": f"Je comprends: {text}. Comment puis-je vous aider?"
            }
            return fallbacks.get(language, fallbacks["en"])
        
        return reply
        
    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        traceback.print_exc()
        return f"You said: {text}"


async def text_to_speech(text: str, language: str = "en", output_file: str = None) -> str:
    """Convert text to speech using Hugging Face Inference API (TTS).
    Supports English, Hindi, and French."""
    global hf_client
    
    if not HF_AVAILABLE or hf_client is None:
        if not await init_hf_client():
            return None
    
    try:
        lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
        print(f"   🔊 Converting text to speech ({lang_names.get(language, 'Unknown')}): {text[:50]}...")
        
        # Language-specific TTS models
        tts_models_by_lang = {
            "en": [
                "microsoft/speecht5_tts",  # Good for English
                "facebook/mms-tts",        # Multilingual, works well for English
                "espnet/kan-bayashi_ljspeech_vits"
            ],
            "hi": [
                "facebook/mms-tts",        # Supports Hindi
                "microsoft/speecht5_tts"   # Fallback
            ],
            "fr": [
                "facebook/mms-tts",        # Supports French
                "microsoft/speecht5_tts"   # Fallback
            ]
        }
        
        # Get models for this language, with fallback to English models
        models_to_try = tts_models_by_lang.get(language, tts_models_by_lang["en"])
        if language != "en":
            models_to_try.extend(tts_models_by_lang["en"])  # Add English as fallback
        
        audio_bytes = None
        for model in models_to_try:
            try:
                response = await hf_client.text_to_speech(
                    text,
                    model=model
                )
                
                # Extract audio bytes from response
                if hasattr(response, 'content'):
                    audio_bytes = response.content
                elif isinstance(response, bytes):
                    audio_bytes = response
                elif hasattr(response, 'audio'):
                    audio_bytes = response.audio
                else:
                    # Try to convert to bytes
                    audio_bytes = bytes(response)
                
                if audio_bytes:
                    print(f"   ✅ TTS generated using {model} ({lang_names.get(language, 'Unknown')})")
                    break
            except Exception as e:
                print(f"   ⚠️  TTS model {model} failed: {e}")
                continue
        
        if not audio_bytes:
            print(f"   ❌ All TTS models failed for {lang_names.get(language, 'Unknown')}")
            return None
        
        # Save audio to file
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_file = f"audio_files/tts_response_{timestamp}.wav"
        
        os.makedirs("audio_files", exist_ok=True)
        
        # Write audio bytes to file
        with open(output_file, 'wb') as f:
            f.write(audio_bytes)
        
        print(f"   ✅ TTS audio saved: {output_file} ({len(audio_bytes)} bytes)")
        return output_file
        
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


async def send_audio(session: aiohttp.ClientSession, chat_id: str, audio_file_path: str):
    """Send an audio message (voice memo) via Series API."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    
    # Read audio file and encode to base64 (run in executor)
    loop = asyncio.get_event_loop()
    
    def read_and_encode():
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        return base64.b64encode(audio_data).decode('ascii')
    
    audio_base64 = await loop.run_in_executor(CPU_BOUND_EXECUTOR, read_and_encode)
    
    # Determine format - M4A is the target for voice memos
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
    payload = {
        "message": {
            "text": "",
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


async def download_file(session: aiohttp.ClientSession, url: str) -> bytes:
    """Download a file from a URL."""
    async with session.get(url, headers=headers, timeout=30) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise Exception(f"Failed to download: {response.status}")


def wav_to_m4a(wav_file: str, m4a_file: str = None) -> str:
    """Convert WAV file to M4A (AAC) format using ffmpeg."""
    if m4a_file is None:
        m4a_file = wav_file.replace('.wav', '.m4a')
    
    try:
        import subprocess
        # ffmpeg -y -i input.wav -c:a aac -b:a 48k output.m4a
        result = subprocess.run([
            'ffmpeg', '-y', 
            '-i', wav_file,
            '-c:a', 'aac', 
            '-b:a', '48k',
            m4a_file
        ], check=True, capture_output=True)
        
        if os.path.exists(m4a_file):
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
        audio_dir = "audio_files"
        os.makedirs(audio_dir, exist_ok=True)
        
        # STEP 1: Save OPUS file
        print(f"   💾 STEP 1: Saving OPUS file...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sender = sender.replace("+", "").replace("-", "")
        opus_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.opus"
        
        loop = asyncio.get_event_loop()
        
        def save_and_convert():
            opus_bytes = base64.b64decode(base64_opus)
            with open(opus_filename, 'wb') as f:
                f.write(opus_bytes)
            print(f"   ✅ STEP 1 COMPLETE: OPUS saved ({len(opus_bytes)} bytes)")
            return opus_to_wav(base64_opus)

        # STEP 2-4: Convert OPUS → WAV
        print(f"   🎵 STEP 2-4: Converting OPUS → WAV...")
        wav_file = await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_and_convert)
        
        # Save a copy with nice name
        wav_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.wav"
        if os.path.exists(wav_file):
            shutil.copy2(wav_file, wav_filename)
            print(f"   ✅ STEP 2-4 COMPLETE: WAV saved: {wav_filename}")
        
        # Transcribe (with language detection)
        print(f"   🎤 STEP 5: Transcribing WAV → Text (Whisper)...")
        transcript, detected_language = await transcribe_audio(wav_filename)
        
        if transcript:
            lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
            lang_name = lang_names.get(detected_language, "Unknown")
            print(f"   ✅ STEP 5 COMPLETE: Transcript ({lang_name}): {transcript}")
            
            # Start typing
            await start_typing(session, chat_id)
            
            # Get user history (run in executor)
            loop = asyncio.get_event_loop()
            history = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_history, sender)
            
            try:
                print(f"   🤖 STEP 6: Getting LLM response from transcript ({lang_name})...")
                llm_reply = await get_llm_response(transcript, history, language=detected_language or "en")
                print(f"   ✅ STEP 6 COMPLETE: LLM Response ({lang_name}): {llm_reply[:100]}...")
                
                # SEND VOICE RESPONSE: Convert LLM text to speech, then send as audio
                print(f"   🔊 STEP 7: Converting LLM text → Speech (TTS, {lang_name})...")
                tts_wav = await text_to_speech(llm_reply, language=detected_language or "en")
                
                if tts_wav and os.path.exists(tts_wav):
                    print(f"   ✅ STEP 7 COMPLETE: TTS WAV saved: {tts_wav}")
                    
                    # Convert WAV to M4A (AAC) for iMessage voice memo
                    print(f"   🎵 STEP 8: Converting TTS WAV → M4A (AAC)...")
                    loop = asyncio.get_event_loop()
                    m4a_file = await loop.run_in_executor(
                        CPU_BOUND_EXECUTOR, 
                        wav_to_m4a, 
                        tts_wav
                    )
                    
                    if m4a_file and os.path.exists(m4a_file):
                        print(f"   ✅ STEP 8 COMPLETE: M4A file ready: {m4a_file}")
                        # Send voice response
                        print(f"   📤 STEP 9: Sending voice response to phone...")
                        await send_audio(session, chat_id, m4a_file)
                        print(f"   ✅ STEP 9 COMPLETE: Voice response sent!")
                    else:
                        # Fallback to text if M4A conversion fails
                        print(f"   ⚠️  M4A conversion failed, sending text instead")
                        await send_text(session, chat_id, llm_reply)
                else:
                    # Fallback to text if TTS fails
                    print(f"   ⚠️  TTS failed, sending text instead")
                    await send_text(session, chat_id, llm_reply)
                
                # Save context (run in executor)
                def save_context():
                    session_manager.add_message(sender, "user", transcript)
                    session_manager.add_message(sender, "assistant", llm_reply)
                await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_context)
                
            except Exception as e:
                print(f"   ⚠️  LLM error: {e}")
                await send_text(session, chat_id, f"🎤 I heard: {transcript}")
            
            await stop_typing(session, chat_id)
        else:
            await send_text(session, chat_id, f"🎤 Got your voice memo! Saved as {os.path.basename(opus_filename)}")
        
        # Cleanup temp file
        if os.path.exists(wav_file) and wav_file != wav_filename:
            os.unlink(wav_file)

    except Exception as e:
        print(f"   ❌ Error processing audio: {e}")
        traceback.print_exc()
        await send_text(session, chat_id, "Sorry, couldn't process that voice memo.")


async def process_text_message(session: aiohttp.ClientSession, event_data: dict):
    """Process incoming text message with multilingual support."""
    chat_id = event_data.get("chat_id")
    text = event_data.get("text", "")
    sender = event_data.get("from_phone", "")
    
    print(f"\n📥 INCOMING MESSAGE from {sender}: {text}")
    
    # Detect language
    detected_language = await detect_language(text)
    lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
    lang_name = lang_names.get(detected_language, "Unknown")
    print(f"   🌐 Detected language: {lang_name}")
    
    await start_typing(session, chat_id)
    
    # Get user history (run in executor)
    loop = asyncio.get_event_loop()
    history = await loop.run_in_executor(CPU_BOUND_EXECUTOR, session_manager.get_history, sender)
    
    try:
        reply = await get_llm_response(text, history, language=detected_language)
        print(f"   💬 LLM Response ({lang_name}): {reply[:100]}...")
        
        # Save context (run in executor)
        def save_context():
            session_manager.add_message(sender, "user", text)
            session_manager.add_message(sender, "assistant", reply)
        await loop.run_in_executor(CPU_BOUND_EXECUTOR, save_context)
        
    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        fallbacks = {
            "en": f"You said: {text}",
            "hi": f"आपने कहा: {text}",
            "fr": f"Vous avez dit: {text}"
        }
        reply = fallbacks.get(detected_language, fallbacks["en"])
    
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
    
    # Seek to end of all partitions to only process NEW messages
    print("⏩ Seeking to end of all partitions (ONLY NEW MESSAGES)...")
    try:
        partitions = consumer.assignment()
        if partitions:
            for partition in partitions:
                await consumer.seek_to_end(partition)
                end_offset = await consumer.position(partition)
                print(f"   📍 Partition {partition.partition}: positioned at offset {end_offset} (end)")
            await consumer.commit()
            print("   ✅ Committed end position - will only process NEW messages")
        else:
            print("   ⚠️  No partitions assigned yet")
    except Exception as e:
        print(f"   ⚠️  Error seeking to end: {e}")
    
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
                msg_pack = await consumer.getmany(timeout_ms=1000, max_records=10)
                
                if not msg_pack:
                    # No messages - check heartbeat
                    current_time = time.time()
                    if current_time - last_heartbeat > 30:
                        print(f"💓 Consumer heartbeat - waiting for messages... (processed {message_count} so far)")
                        last_heartbeat = current_time
                    continue
                
                # Process all messages in the batch
                for topic_partition, messages in msg_pack.items():
                    for msg in messages:
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
                            
                            # Determine message type
                            if event_type == "message.received":
                                # Check for audio
                                has_audio = False
                                audio_data_to_process = None
                                
                                # Logic to find audio (same as sync consumer)
                                if "audio" in data:
                                    has_audio = True
                                    audio_data_to_process = data
                                elif isinstance(data.get("message"), dict) and "audio" in data.get("message", {}):
                                    has_audio = True
                                    audio_data_to_process = data.copy()
                                    audio_data_to_process["audio"] = data["message"]["audio"]
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
                                            break
                                
                                if has_audio and audio_data_to_process:
                                    # Process audio synchronously to ensure commit happens after success
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
                                elif "text" in data:
                                    # Process text synchronously to ensure commit happens after success
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
                                else:
                                    # Unknown message format - commit to skip
                                    print("⚠️  Unknown message format")
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
                            traceback.print_exc()
                            print(f"{'='*60}\n")
                            # Don't commit on error - will retry on restart
                            # This ensures we don't lose messages
                    
        finally:
            print("👋 Stopping consumer...")
            await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
