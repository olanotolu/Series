import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Load environment variables
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Initialize the client
client = InferenceClient(token=HF_TOKEN)

def transcribe_audio(filename):
    """
    Transcribes audio using Hugging Face Inference API (Whisper).
    """
    print(f"Transcribing {filename}...")
    try:
        # Using the recommended model for ASR
        response = client.automatic_speech_recognition(
            filename,
            model="openai/whisper-large-v3-turbo"
        )
        return response.text
    except Exception as e:
        print(f"Error in ASR: {e}")
        return None

def get_llm_response(text):
    """
    Gets a response from an LLM using Hugging Face Inference API.
    """
    print("Getting LLM response...")
    try:
        # Construct a simple prompt
        messages = [
            {"role": "user", "content": text}
        ]
        
        # Using a reliable chat model
        response = client.chat_completion(
            messages=messages,
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM: {e}")
        return None

def main():
    audio_file = "voice_memo_17169102362_20251205_224037_53464749.wav"
    
    if not os.path.exists(audio_file):
        print(f"File not found: {audio_file}")
        return

    transcription = transcribe_audio(audio_file)
    
    if transcription:
        print("\n--- Transcription ---")
        print(transcription)
        print("---------------------\n")
        
        llm_response = get_llm_response(transcription)
        
        if llm_response:
            print("--- LLM Response ---")
            print(llm_response)
            print("--------------------")
    else:
        print("Failed to transcribe audio.")

if __name__ == "__main__":
    main()
