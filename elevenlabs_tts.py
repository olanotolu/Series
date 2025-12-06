import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ElevenLabs API Key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_80eea64bd38929b50385f058305aa47f2df7e3fde0679fe7")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Language-specific voice IDs (using default voices that work well for each language)
# You can customize these with your preferred voice IDs from ElevenLabs
LANGUAGE_VOICES = {
    "en": "21m00Tcm4TlvDq8ikWAM",  # Rachel - English (default)
    "hi": "pNInz6obpgDQGcFmaJgB",  # Adam - Multilingual (works well for Hindi)
    "fr": "EXAVITQu4vr4xnSDxMaL",  # Bella - Multilingual (works well for French)
}

# Model selection based on language
# eleven_flash_v2_5: Ultra-fast (~75ms), supports 32 languages including en, hi, fr
# eleven_multilingual_v2: Higher quality, supports 29 languages including en, hi, fr
LANGUAGE_MODELS = {
    "en": "eleven_flash_v2_5",  # Fast for English
    "hi": "eleven_flash_v2_5",  # Fast for Hindi
    "fr": "eleven_flash_v2_5",  # Fast for French
}


async def generate_speech(text: str, output_file: str, language: str = "en"):
    """Generate speech using ElevenLabs API with proper accents for each language.
    Supports multiple languages: English (en), Hindi (hi), French (fr), and more.
    Uses language-specific voices to ensure native accents."""
    
    # Get voice ID and model for language
    voice_id = LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["en"])
    model_id = LANGUAGE_MODELS.get(language, LANGUAGE_MODELS["en"])
    
    lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
    lang_name = lang_names.get(language, language.upper())
    
    print(f"   Generating speech with ElevenLabs ({model_id}, {lang_name})...")
    
    try:
        # ElevenLabs API endpoint
        url = f"{ELEVENLABS_API_URL}/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        # Make async HTTP request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"   ❌ ElevenLabs API error {response.status}: {error_text}")
                    return None
                
                # Read audio data
                audio_data = await response.read()
                
                # Save to file (ElevenLabs returns MP3, but we'll save as WAV for compatibility)
                # Actually, let's save as MP3 first, then we can convert if needed
                mp3_file = output_file.replace('.wav', '.mp3')
                with open(mp3_file, 'wb') as f:
                    f.write(audio_data)
                
                print(f"   ✅ ElevenLabs TTS generated ({len(audio_data)} bytes, {lang_name})")
                
                # Convert MP3 to WAV using ffmpeg if needed
                if output_file.endswith('.wav'):
                    import subprocess
                    try:
                        subprocess.run([
                            'ffmpeg', '-y', '-i', mp3_file,
                            '-ar', '44100',  # Sample rate
                            '-ac', '1',      # Mono
                            output_file
                        ], check=True, capture_output=True)
                        os.remove(mp3_file)  # Clean up MP3
                        print(f"   ✅ Converted MP3 → WAV: {output_file}")
                    except subprocess.CalledProcessError as e:
                        print(f"   ⚠️  MP3→WAV conversion failed, using MP3: {e.stderr.decode() if e.stderr else str(e)}")
                        return mp3_file
                
                return output_file
                
    except Exception as e:
        print(f"   ❌ ElevenLabs TTS error: {e}")
        import traceback
        traceback.print_exc()
        return None

