import asyncio
import os
from cartesia import AsyncCartesia

# Use the key provided by the user
API_KEY = "sk_car_zop62es5DGFLKJK3pmZXK8"

async def test_cartesia():
    print(f"Testing Cartesia API with key: {API_KEY[:5]}...")
    
    client = AsyncCartesia(api_key=API_KEY)
    text = "Hello! This is a test of the Cartesia voice generator."
    
    try:
        print("   Generating speech...")
        # Model: sonic-english
        # Voice: Standard American Man (694f9389-aac1-45b6-b726-9d9369183238)
        
        output_file = "test_cartesia.wav"
        
        with open(output_file, "wb") as f:
            async for chunk in client.tts.bytes(
                model_id="sonic-english",
                transcript=text,
                voice={"mode": "id", "id": "694f9389-aac1-45b6-b726-9d9369183238"},
                output_format={
                    "container": "wav",
                    "sample_rate": 44100,
                    "encoding": "pcm_s16le",
                },
            ):
                f.write(chunk)
                
        print(f"   ✅ Success! Saved {output_file}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cartesia())
