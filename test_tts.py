import asyncio
import os
import traceback
from huggingface_hub import AsyncInferenceClient
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv('HF_TOKEN')
print(f"HF_TOKEN: {HF_TOKEN[:5] if HF_TOKEN else 'None'}...")

async def test_pipeline():
    text = "Hello, this is a test of the voice generation pipeline."
    print(f"1. Testing TTS generation for: '{text}' using AsyncClient (Standard)")
    model = "espnet/kan-bayashi_ljspeech_vits"
    
    from huggingface_hub import AsyncInferenceClient
    client = AsyncInferenceClient(token=HF_TOKEN)
    
    try:
        print(f"   Calling {model}...")
        # Try the helper again, maybe this model has a mapping
        response = await client.text_to_speech(text, model=model)
        
        # Audio extraction
        audio_bytes = None
        if isinstance(response, bytes):
            audio_bytes = response
        elif hasattr(response, 'content'):
            audio_bytes = response.content
        elif hasattr(response, 'audio'):
            audio_bytes = response.audio
        else:
            audio_bytes = bytes(response)
        
        print(f"   ✅ TTS success! Got {len(audio_bytes)} bytes.")
        
        # Save WAV
        wav_file = "test_tts.wav"
        with open(wav_file, "wb") as f:
            f.write(audio_bytes)
        print(f"   Saved {wav_file}")
        
        # Test 2: Convert to M4A
        print("2. Testing M4A conversion...")
        m4a_file = "test_tts.m4a"
        
        import subprocess
        cmd = [
            'ffmpeg', '-y', 
            '-i', wav_file,
            '-c:a', 'aac', 
            '-b:a', '48k',
            m4a_file
        ]
        print(f"   Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(m4a_file):
            size = os.path.getsize(m4a_file)
            print(f"   ✅ M4A conversion success! File size: {size} bytes")
        else:
            print("   ❌ M4A file missing after ffmpeg.")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
