import os
import asyncio
from cartesia import AsyncCartesia

# Use environment variable or fallback to the key provided by user
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "sk_car_zop62es5DGFLKJK3pmZXK8")

client = None

def init_client():
    global client
    if client is None:
        client = AsyncCartesia(api_key=CARTESIA_API_KEY)

async def generate_speech(text: str, output_file: str):
    """Generate speech using Cartesia API and save to WAV file."""
    init_client()
    
    # Model: sonic-english (fastest, high quality)
    # Voice ID: 694f9389-aac1-45b6-b726-9d9369183238 (Standard American Man)
    model_id = "sonic-english" 
    voice_id = "694f9389-aac1-45b6-b726-9d9369183238" 

    try:
        print(f"   Generating speech with Cartesia ({model_id})...")
        
        # Open file for writing
        with open(output_file, "wb") as f:
            # Stream bytes
            async for chunk in client.tts.bytes(
                model_id=model_id,
                transcript=text,
                voice={"mode": "id", "id": voice_id},
                output_format={
                    "container": "wav",
                    "sample_rate": 44100,
                    "encoding": "pcm_s16le",
                },
            ):
                f.write(chunk)
                
        return output_file
    except Exception as e:
        print(f"   ❌ Cartesia TTS error: {e}")
        return None
