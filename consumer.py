#!/usr/bin/env python3
"""
Series Hackathon - Kafka Consumer with Audio Support

Listens to Kafka events and handles:
- Text messages
- Voice memos (OPUS audio)
- Typing indicators
"""

from kafka import KafkaConsumer
import json
import requests
import time
import os
import base64
import shutil
from datetime import datetime
from dotenv import load_dotenv
from opus_to_wav import opus_to_wav

# Hugging Face Inference API (much faster than loading models locally)
try:
    from huggingface_hub import InferenceClient
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

# Initialize Kafka consumer
# Using a unique consumer group to avoid offset issues
UNIQUE_GROUP = f"{CONSUMER_GROUP}-{int(time.time())}"  # Fresh group each restart

consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=[BOOTSTRAP_SERVERS],
    group_id=UNIQUE_GROUP,  # Fresh group = see all new messages
    client_id=CLIENT_ID,
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username=KAFKA_SASL_USERNAME,
    sasl_plain_password=KAFKA_SASL_PASSWORD,
    auto_offset_reset='latest',  # Only get messages sent AFTER consumer starts
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    # No consumer_timeout_ms = wait forever for messages
)

headers = {"Authorization": f"Bearer {API_KEY}"}

# Initialize Hugging Face Inference API client
HF_TOKEN = os.getenv('HF_TOKEN', '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')
hf_client = None

def init_hf_client():
    """Initialize Hugging Face Inference API client."""
    global hf_client
    
    if not HF_AVAILABLE:
        print("⚠️  Hugging Face Inference API not available. Using echo mode.")
        return False
    
    if hf_client is not None:
        return True  # Already initialized
    
    try:
        print("🤖 Initializing Hugging Face Inference API client...")
        hf_client = InferenceClient(token=HF_TOKEN)
        print("✅ Hugging Face Inference API client initialized!")
        return True
    except Exception as e:
        print(f"❌ Error initializing HF client: {e}")
        import traceback
        traceback.print_exc()
        return False

def transcribe_audio(filename: str) -> str:
    """
    Transcribes audio using Hugging Face Inference API (Whisper).
    """
    global hf_client
    
    if not HF_AVAILABLE or hf_client is None:
        if not init_hf_client():
            return None
    
    try:
        print(f"   🎤 Transcribing audio: {filename}...")
        response = hf_client.automatic_speech_recognition(
            filename,
            model="openai/whisper-large-v3-turbo"
        )
        transcript = response.text
        print(f"   ✅ Transcript: {transcript[:100]}...")
        return transcript
    except Exception as e:
        print(f"   ⚠️  Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_llm_response(text: str) -> str:
    """Get response from LLM using Hugging Face Inference API."""
    global hf_client
    
    # Initialize client if not already done
    if hf_client is None:
        if not init_hf_client():
            return f"You said: {text}"  # Fallback to echo
    
    try:
        print(f"   🤖 Getting LLM response via Inference API...")
        
        # Construct messages for chat completion
        messages = [
            {"role": "user", "content": text}
        ]
        
        # Use Meta-Llama-3-8B-Instruct (reliable and fast via API)
        response = hf_client.chat_completion(
            messages=messages,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            max_tokens=512
        )
        
        reply = response.choices[0].message.content.strip()
        
        if not reply or len(reply) < 3:
            return f"I understand you said: {text}. How can I help?"
        
        return reply
        
    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        import traceback
        traceback.print_exc()
        return f"You said: {text}"  # Fallback to echo


def send_text(chat_id: str, text: str):
    """Send a text message via Series API."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    payload = {"message": {"text": text}}
    
    print(f"\n📤 OUTGOING MESSAGE:")
    print(f"   Chat ID: {chat_id}")
    print(f"   Text: {text}")
    
    try:
        r = requests.post(url, json=payload, headers=headers)
        response = r.json()
        
        if r.status_code in [200, 201]:
            message_id = response.get('data', {}).get('id', 'N/A')
            print(f"   ✅ Message ID: {message_id}")
            print(f"   Status: {r.status_code} - Success")
        else:
            print(f"   ⚠️  Status: {r.status_code}")
            print(f"   Response: {response}")
        
        return response
    except Exception as e:
        print(f"   ❌ Error sending: {e}")
        raise


def send_audio(chat_id: str, audio_file_path: str):
    """Send an audio message (voice memo) via Series API."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    
    # Read audio file and encode to base64
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    import base64
    audio_base64 = base64.b64encode(audio_data).decode('ascii')
    
    # Determine format from file extension
    if audio_file_path.endswith('.opus'):
        format_type = 'opus'
    elif audio_file_path.endswith('.wav'):
        format_type = 'wav'
    else:
        format_type = 'opus'  # default
    
    payload = {
        "message": {
            "audio": {
                "format": format_type,
                "sample_rate": 16000,
                "channels": 1,
                "data": audio_base64
            }
        }
    }
    
    r = requests.post(url, json=payload, headers=headers)
    print(f"✅ Sent audio: {audio_file_path}")
    return r.json()


def start_typing(chat_id: str):
    """Send typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/start_typing"
    try:
        r = requests.post(url, headers=headers)
        if r.status_code in [200, 201]:  # Both are success codes
            print(f"   ⌨️  Typing indicator: ON")
        else:
            print(f"   ⚠️  Typing indicator failed: {r.status_code}")
    except Exception as e:
        print(f"   ⚠️  Typing indicator error: {e}")


def stop_typing(chat_id: str):
    """Stop typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/stop_typing"
    try:
        r = requests.delete(url, headers=headers)
        if r.status_code in [200, 201, 204]:  # All are success codes
            print(f"   ⌨️  Typing indicator: OFF")
        else:
            print(f"   ⚠️  Stop typing failed: {r.status_code}")
    except Exception as e:
        print(f"   ⚠️  Stop typing error: {e}")


def process_audio_message(event_data: dict):
    """
    Process incoming voice memo (OPUS audio).
    Saves audio files and converts OPUS to WAV for STT processing.
    Handles both base64 data and URL-based audio.
    """
    chat_id = event_data.get("chat_id")
    sender = event_data.get("from_phone", "Unknown")
    message_id = event_data.get("id", "N/A")
    sent_at = event_data.get("sent_at", "N/A")
    audio_data = event_data.get("audio", {})
    base64_opus = audio_data.get("data")
    audio_url = audio_data.get("url")
    
    print(f"\n📥 INCOMING VOICE MEMO:")
    print(f"   From: {sender}")
    print(f"   Chat ID: {chat_id}")
    print(f"   Message ID: {message_id}")
    print(f"   Sent At: {sent_at}")
    print(f"   Audio format: {audio_data.get('format', 'N/A')}")
    print(f"   Sample rate: {audio_data.get('sample_rate', 'N/A')} Hz")
    print(f"   ────────────────────────────────────────────")
    
    # If no base64 data, try to download from URL
    if not base64_opus and audio_url:
        print(f"   📥 Downloading audio from URL: {audio_url[:50]}...")
        try:
            # Download audio file
            response = requests.get(audio_url, headers=headers, timeout=30)
            if response.status_code == 200:
                opus_data = response.content
                # Encode to base64 for processing
                base64_opus = base64.b64encode(opus_data).decode('ascii')
                print(f"   ✅ Downloaded {len(opus_data):,} bytes")
            else:
                print(f"   ❌ Failed to download: {response.status_code}")
                send_text(chat_id, "Sorry, couldn't download the voice memo.")
                return
        except Exception as e:
            print(f"   ❌ Error downloading audio: {e}")
            send_text(chat_id, "Sorry, couldn't download the voice memo.")
            return
    
    if not base64_opus:
        print("   ⚠️  No audio data in message (no data or url)")
        print(f"   Audio data keys: {list(audio_data.keys())}")
        return
    
    try:
        # Create audio_files directory if it doesn't exist
        audio_dir = "audio_files"
        os.makedirs(audio_dir, exist_ok=True)
        
        # Decode base64 OPUS data
        opus_data = base64.b64decode(base64_opus)
        opus_size = len(opus_data)
        print(f"   📦 Received OPUS data: {opus_size:,} bytes ({opus_size/1024:.2f} KB)")
        
        # Create filename with timestamp and message ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sender = sender.replace("+", "").replace("-", "")
        opus_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.opus"
        
        # Save OPUS file
        with open(opus_filename, 'wb') as f:
            f.write(opus_data)
        print(f"   💾 Saved OPUS file: {opus_filename}")
        print(f"   📁 File size: {os.path.getsize(opus_filename):,} bytes")
        
        # Convert OPUS to WAV for processing
        print("   🎤 Converting OPUS → WAV...")
        wav_file = opus_to_wav(base64_opus)
        wav_size = os.path.getsize(wav_file) if os.path.exists(wav_file) else 0
        print(f"   ✅ Converted to WAV: {wav_file} ({wav_size:,} bytes)")
        
        # Also save WAV file for easier playback
        wav_filename = f"{audio_dir}/voice_memo_{safe_sender}_{timestamp}_{message_id}.wav"
        if os.path.exists(wav_file):
            shutil.copy2(wav_file, wav_filename)
            print(f"   💾 Saved WAV file: {wav_filename}")
        
        # Transcribe audio using Hugging Face Inference API
        print(f"   🎤 Transcribing voice memo...")
        transcript = transcribe_audio(wav_filename)
        
        if transcript:
            print(f"   📝 Transcript: {transcript}")
            
            # Get LLM response to the transcription
            print(f"   🤖 Getting LLM response to transcription...")
            start_typing(chat_id)
            time.sleep(0.3)
            
            try:
                llm_reply = get_llm_response(transcript)
                print(f"   💬 LLM Response: {llm_reply[:100]}...")
                send_text(chat_id, llm_reply)
            except Exception as e:
                print(f"   ⚠️  LLM error: {e}")
                send_text(chat_id, f"🎤 I heard: {transcript}")
            
            stop_typing(chat_id)
        else:
            # Acknowledge receipt if transcription failed
            print(f"   ⚠️  Transcription failed, sending acknowledgment...")
            send_text(chat_id, f"🎤 Got your voice memo! Saved as {os.path.basename(opus_filename)}")
        
        # Cleanup temporary WAV (keep the saved one)
        if os.path.exists(wav_file) and wav_file != wav_filename:
            os.unlink(wav_file)
            
    except Exception as e:
        print(f"   ❌ Error processing audio: {e}")
        import traceback
        traceback.print_exc()
        send_text(chat_id, "Sorry, couldn't process that voice memo.")


def process_text_message(event_data: dict):
    """Process incoming text message."""
    chat_id = event_data.get("chat_id")
    text = event_data.get("text", "")
    sender = event_data.get("from_phone", "")
    message_id = event_data.get("id", "N/A")
    sent_at = event_data.get("sent_at", "N/A")
    
    print(f"\n📥 INCOMING MESSAGE:")
    print(f"   From: {sender}")
    print(f"   Chat ID: {chat_id}")
    print(f"   Message ID: {message_id}")
    print(f"   Sent At: {sent_at}")
    print(f"   Text: {text}")
    print(f"   ────────────────────────────────────────────")
    
    # Get LLM response
    print(f"   🤖 Getting LLM response...")
    start_typing(chat_id)
    time.sleep(0.3)  # Human-like delay
    
    try:
        reply = get_llm_response(text)
        print(f"   💬 LLM Response: {reply[:100]}...")
    except Exception as e:
        print(f"   ⚠️  LLM error, using fallback: {e}")
        reply = f"You said: {text}"  # Fallback
    
    send_text(chat_id, reply)
    stop_typing(chat_id)
    print(f"   ✅ Response sent successfully")


print("🚀 Series Hackathon Consumer Started")
print(f"📡 Listening on topic: {TOPIC_NAME}")
print(f"👥 Consumer Group: {UNIQUE_GROUP}")
print(f"🆔 Client ID: {CLIENT_ID}")
print("=" * 60)
print("💡 Consumer is ready! Send a message from your phone to +16463769330")
print("💡 Or test with: python producer.py 'Test message'")
print("=" * 60)

message_count = 0

try:
    for msg in consumer:
        message_count += 1
        event = msg.value
        
        # Show event header
        event_type = event.get("event_type")
        data = event.get("data", {})
        created_at = event.get("created_at", "N/A")
        
        print(f"\n{'='*60}")
        print(f"📨 EVENT #{message_count} - {event_type.upper()}")
        print(f"{'='*60}")
        print(f"⏰ Time: {created_at}")
        print(f"📊 Kafka: Partition {msg.partition}, Offset {msg.offset}")
        print(f"{'='*60}")
        
        if event_type == "message.received":
            # Debug: Show all keys in data
            print(f"🔍 DEBUG: Data keys: {list(data.keys())}")
            
            # Check if it's audio or text
            # Audio can be in data directly, nested, or in attachments
            has_audio = False
            audio_data_to_process = None
            
            # Check multiple possible locations for audio
            if "audio" in data:
                has_audio = True
                audio_data_to_process = data
                print("   ✅ Found audio in data.audio")
            elif isinstance(data.get("message"), dict) and "audio" in data.get("message", {}):
                has_audio = True
                audio_data_to_process = data.copy()
                audio_data_to_process["audio"] = data["message"]["audio"]
                print("   ✅ Found audio in data.message.audio")
            elif isinstance(data.get("attachments"), list) and len(data.get("attachments", [])) > 0:
                # Check if audio is in attachments array
                print(f"   🔍 Checking {len(data['attachments'])} attachment(s)...")
                for i, att in enumerate(data.get("attachments", [])):
                    print(f"      Attachment {i+1}: {type(att)}, keys: {list(att.keys()) if isinstance(att, dict) else 'not a dict'}")
                    if isinstance(att, dict):
                        # Check various ways audio might be represented
                        is_audio = (
                            att.get("type") == "audio" or 
                            att.get("mime_type", "").startswith("audio/") or
                            att.get("filename", "").endswith((".opus", ".wav", ".m4a", ".aac", ".mp3"))
                        )
                        
                        if is_audio:
                            has_audio = True
                            audio_data_to_process = data.copy()
                            # Map attachment to audio structure (include URL for downloading)
                            audio_data_to_process["audio"] = {
                                "format": att.get("format", "opus"),
                                "sample_rate": att.get("sample_rate", 16000),
                                "channels": att.get("channels", 1),
                                "data": att.get("data") or att.get("content") or att.get("base64_data"),
                                "url": att.get("url")  # Include URL for downloading
                            }
                            print(f"   ✅ Found audio in data.attachments[{i}]")
                            if att.get("url"):
                                print(f"      Audio URL: {att['url'][:60]}...")
                            break
                        elif "data" in att or "content" in att or "base64_data" in att:
                            # Might be audio even without explicit type
                            has_audio = True
                            audio_data_to_process = data.copy()
                            audio_data_to_process["audio"] = {
                                "format": att.get("format", "opus"),
                                "sample_rate": att.get("sample_rate", 16000),
                                "channels": att.get("channels", 1),
                                "data": att.get("data") or att.get("content") or att.get("base64_data"),
                                "url": att.get("url")
                            }
                            print(f"   ✅ Found audio-like data in data.attachments[{i}]")
                            break
            
            if has_audio and audio_data_to_process:
                print("🎤 Audio message detected")
                process_audio_message(audio_data_to_process)
            elif "text" in data and data.get("text"):
                process_text_message(data)
            else:
                print("⚠️  Unknown message format - showing full structure:")
                print(f"   Full data: {json.dumps(data, indent=2)}")
        
        elif event_type == "typing_indicator.received":
            chat_id = data.get("chat_id", "N/A")
            display = data.get("display", False)
            print(f"\n⌨️  TYPING INDICATOR:")
            print(f"   Chat ID: {chat_id}")
            print(f"   Status: {'User is typing...' if display else 'Stopped'}")
            print(f"{'='*60}")
        
        elif event_type == "typing_indicator.removed":
            chat_id = data.get("chat_id", "N/A")
            print(f"\n⌨️  TYPING INDICATOR REMOVED:")
            print(f"   Chat ID: {chat_id}")
            print(f"   Status: User stopped typing")
            print(f"{'='*60}")
        
        else:
            print(f"\nℹ️  OTHER EVENT: {event_type}")
            print(f"   Full event: {json.dumps(event, indent=2)}")
            print(f"{'='*60}")
        
        # Summary line
        print(f"✅ Event #{message_count} processed successfully")
        print(f"{'='*60}\n")

except KeyboardInterrupt:
    print(f"\n\n🛑 Consumer stopped")
    print(f"📊 Total messages processed: {message_count}")
except Exception as e:
    print(f"\n❌ Error in consumer loop: {e}")
    import traceback
    traceback.print_exc()
finally:
    consumer.close()
    print("👋 Consumer closed")

