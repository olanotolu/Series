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

async def generate_speech(text: str, output_file: str, language: str = "en"):
    """Generate speech using Cartesia API with proper accents for each language.
    Supports multiple languages: English (en), Hindi (hi), French (fr), and more.
    Uses voice localization to ensure native accents."""
    init_client()
    
    # Language-specific voice configuration with proper accents
    # Cartesia's localization feature ensures native pronunciation and accents
    language_configs = {
        "en": {
            "model_id": "sonic-english",  # Fastest, optimized for English
            "voice_id": "694f9389-aac1-45b6-b726-9d9369183238",  # Standard American Man
            "localize": None  # English is default
        },
        "fr": {
            "model_id": "sonic-multilingual",  # Supports French
            "voice_id": "694f9389-aac1-45b6-b726-9d9369183238",  # Base voice
            "localize": "fr-FR"  # French accent (France)
        },
        "hi": {
            "model_id": "sonic-multilingual",  # Supports Hindi
            "voice_id": "694f9389-aac1-45b6-b726-9d9369183238",  # Base voice
            "localize": "hi-IN"  # Hindi accent (India)
        }
    }
    
    # Get config for language, default to English if not found
    config = language_configs.get(language, language_configs["en"])
    model_id = config["model_id"]
    voice_id = config["voice_id"]
    localize = config.get("localize") 

    try:
        lang_names = {"en": "English", "hi": "Hindi", "fr": "French"}
        lang_name = lang_names.get(language, language.upper())
        accent_info = f"with {localize} accent" if localize else "with native accent"
        print(f"   Generating speech with Cartesia ({model_id}, {lang_name} {accent_info})...")
        
        # Build voice configuration with localization for proper accents
        voice_config = {"mode": "id", "id": voice_id}
        if localize:
            # Use localization to ensure proper accent (French accent for French, Hindi accent for Hindi)
            voice_config["localize"] = localize
        
        # Open file for writing
        with open(output_file, "wb") as f:
            # Stream bytes with localized voice for proper accents
            async for chunk in client.tts.bytes(
                model_id=model_id,
                transcript=text,
                voice=voice_config,
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
