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

# Global objects
headers = {"Authorization": f"Bearer {API_KEY}"}
hf_client = None


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


async def transcribe_audio(filename: str) -> str:
    """Transcribes audio using Hugging Face Inference API (Whisper)."""
    global hf_client
    
    if not HF_AVAILABLE or hf_client is None:
        if not await init_hf_client():
            return None
    
    try:
        print(f"   🎤 Transcribing audio: {filename}...")
        # Since ASR might involve file reading internally in the client, 
        # but the client is async, we can await it.
        # Note: InferenceClient.automatic_speech_recognition supports filenames
        response = await hf_client.automatic_speech_recognition(
            filename,
            model="openai/whisper-large-v3-turbo"
        )
        
        # Determine if response is object or dict based on version
        transcript = response.text if hasattr(response, 'text') else response.get('text')
        
        print(f"   ✅ Transcript: {transcript[:100]}...")
        return transcript
    except Exception as e:
        print(f"   ⚠️  Transcription error: {e}")
        traceback.print_exc()
        return None


async def get_llm_response(text: str) -> str:
    """Get response from LLM using Hugging Face Inference API."""
    global hf_client
    
    if hf_client is None:
        if not await init_hf_client():
            return f"You said: {text}"
    
    try:
        print(f"   🤖 Getting LLM response via Async Inference API...")
        
        system_prompt = """You are a friendly, helpful friend chatting on Series.so, a social network platform. 
You're having a casual conversation with someone you know. Be warm, engaging, and natural in your responses.
Keep responses concise (1-3 sentences typically), use casual language, and show genuine interest in the conversation.
You can use emojis occasionally to add personality, but don't overdo it. Be yourself - friendly, supportive, and authentic."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        # Use Meta-Llama-3.2-3B-Instruct (reliable and fast via API)
        response = await hf_client.chat_completion(
            messages=messages,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_tokens=512
        )
        
        reply = response.choices[0].message.content.strip()
        
        if not reply or len(reply) < 3:
            return f"I understand you said: {text}. How can I help?"
        
        return reply
        
    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        traceback.print_exc()
        return f"You said: {text}"


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
        
        # Offload CPU-intensive decoding/writing to thread pool
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sender = sender.replace("+", "").replace("-", "")
        opus_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.opus"
        
        loop = asyncio.get_event_loop()
        
        def save_and_convert():
            opus_bytes = base64.b64decode(base64_opus)
            with open(opus_filename, 'wb') as f:
                f.write(opus_bytes)
            return opus_to_wav(base64_opus)

        print("   🎤 Converting OPUS → WAV (in background)...")
        wav_file = await loop.run_in_executor(None, save_and_convert)
        
        # Save a copy with nice name
        wav_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.wav"
        if os.path.exists(wav_file):
            shutil.copy2(wav_file, wav_filename)
        
        # Transcribe
        print(f"   🎤 Transcribing...")
        transcript = await transcribe_audio(wav_filename)
        
        if transcript:
            print(f"   📝 Transcript: {transcript}")
            
            # Start typing
            await start_typing(session, chat_id)
            await asyncio.sleep(0.3)
            
            try:
                llm_reply = await get_llm_response(transcript)
                print(f"   💬 LLM Response: {llm_reply[:100]}...")
                await send_text(session, chat_id, llm_reply)
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
    """Process incoming text message."""
    chat_id = event_data.get("chat_id")
    text = event_data.get("text", "")
    sender = event_data.get("from_phone", "")
    
    print(f"\n📥 INCOMING MESSAGE from {sender}: {text}")
    
    await start_typing(session, chat_id)
    await asyncio.sleep(0.3)
    
    try:
        reply = await get_llm_response(text)
        print(f"   💬 LLM Response: {reply[:100]}...")
    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        reply = f"You said: {text}"
    
    await send_text(session, chat_id, reply)
    await stop_typing(session, chat_id)


async def consume():
    """Main consumer loop."""
    print("🚀 Starting AIOKafka Consumer...")
    
    # Create SSL context
    import ssl
    ssl_context = ssl.create_default_context()
    
    # Initialize Kafka Consumer
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
        enable_auto_commit=False
    )

    await consumer.start()
    print("✅ Kafka Consumer started!")
    
    # Seek to end to skip old messages
    try:
        print("⏩ Seeking to end of partitions...")
        # AIOKafka needs explicit assignment usually, but start() handles subscription
        # We need to wait a bit for assignment or force it
        dummy_poll = await consumer.getmany(timeout_ms=3000, max_records=1) 
        
        parts = consumer.assignment()
        if parts:
            for partition in parts:
                await consumer.seek_to_end(partition)
                print(f"   📍 Partition {partition.partition}: Seeked to end")
            await consumer.commit()
            print("   ✅ Committed end offsets")
        else:
            print("   ⚠️  No partitions assigned yet. Will process from latest.")
    except Exception as e:
        print(f"   ⚠️  Error during seek: {e}")

    # Shared aiohttp session
    async with aiohttp.ClientSession() as session:
        try:
            print("🔄 Waiting for messages...")
            async for msg in consumer:
                try:
                    event = json.loads(msg.value.decode('utf-8'))
                    
                    # Log basics
                    event_type = event.get("event_type")
                    event_id = event.get("event_id") or "N/A"
                    print(f"\n📨 EVENT: {event_type} | ID: {event_id} | Offset: {msg.offset}")

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
                            await process_audio_message(session, audio_data_to_process)
                        elif "text" in data:
                            await process_text_message(session, data)
                    
                    elif event_type == "typing_indicator.received":
                        print(f"   ⌨️  User is typing...")
                    
                    # Commit offset
                    await consumer.commit()
                    
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    traceback.print_exc()
                    # Commit anyway to avoid getting stuck on bad message
                    await consumer.commit()
                    
        finally:
            print("👋 Stopping consumer...")
            await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
