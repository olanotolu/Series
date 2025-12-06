#!/usr/bin/env python3
"""
Series Hackathon - Agent REST API Interface

Helper functions for sending messages, reactions, and managing chats.
"""

import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL', 'https://api.series.so')
SENDER_NUMBER = os.getenv('SENDER_NUMBER')

headers = {"Authorization": f"Bearer {API_KEY}"}


def create_chat(to_phone: str, send_from: str = SENDER_NUMBER, text: str = "Hello! 👋"):
    """Create a new chat and send initial message."""
    url = f"{BASE_URL}/api/chats"
    payload = {
        "send_from": send_from,
        "chat": {"phone_numbers": [to_phone]},
        "message": {"text": text}
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def send_message(chat_id: str, text: str):
    """Send a text message to a chat."""
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    payload = {"message": {"text": text}}
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def send_audio_message(chat_id: str, audio_file_path: str):
    """Send an audio message (voice memo) to a chat."""
    from audio_to_opus import convert_to_opus
    import tempfile
    import os
    
    # Convert audio to Opus format
    temp_opus = tempfile.NamedTemporaryFile(suffix='.opus', delete=False)
    temp_opus_path = temp_opus.name
    temp_opus.close()
    
    # Use audio_to_opus to convert
    # For now, we'll read the file and encode it
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    import base64
    audio_base64 = base64.b64encode(audio_data).decode('ascii')
    
    url = f"{BASE_URL}/api/chats/{chat_id}/chat_messages"
    payload = {
        "message": {
            "audio": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "bitrate": "32k",
                "data": audio_base64
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def react(message_id: str, reaction: str = "love"):
    """Add a reaction to a message."""
    url = f"{BASE_URL}/api/chat_messages/{message_id}/reactions"
    payload = {"operation": "add", "type": reaction}
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def start_typing(chat_id: str):
    """Start typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/start_typing"
    response = requests.post(url, headers=headers)
    return response.json()


def stop_typing(chat_id: str):
    """Stop typing indicator."""
    url = f"{BASE_URL}/api/chats/{chat_id}/stop_typing"
    response = requests.delete(url, headers=headers)
    return response.json()


def edit_message(message_id: str, new_text: str):
    """Edit a sent message."""
    url = f"{BASE_URL}/api/chat_messages/{message_id}"
    payload = {"message": {"text": new_text}}
    response = requests.patch(url, json=payload, headers=headers)
    return response.json()


if __name__ == '__main__':
    # Test example
    print("🧪 Testing Series API...")
    
    # Create a test chat (replace with your phone number)
    # result = create_chat("+13474591567", text="Hello from Series bot! 🚀")
    # print("Chat created:", result)

