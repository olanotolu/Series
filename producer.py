#!/usr/bin/env python3
"""
Kafka Producer - Send test messages to your team's Kafka topic

Use this to send test messages that your consumer will receive.
"""

from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Kafka Configuration from .env
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
TOPIC_NAME = os.getenv('KAFKA_TOPIC_NAME')
KAFKA_SASL_USERNAME = os.getenv('KAFKA_SASL_USERNAME')
KAFKA_SASL_PASSWORD = os.getenv('KAFKA_SASL_PASSWORD')

# Initialize Producer with reliability settings
# acks='all': Wait for all in-sync replicas to acknowledge
# enable_idempotence=True: Prevent duplicates on retries (exactly-once semantics)
# retries: Unlimited retries with exponential backoff
producer = KafkaProducer(
    bootstrap_servers=[BOOTSTRAP_SERVERS],
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username=KAFKA_SASL_USERNAME,
    sasl_plain_password=KAFKA_SASL_PASSWORD,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Wait for all in-sync replicas
    enable_idempotence=True,  # Prevent duplicates on retries
    retries=2147483647,  # Maximum retries (effectively unlimited)
    max_in_flight_requests_per_connection=1  # Must be 1 for idempotence guarantee
    # Note: compression_type removed - requires additional libraries
)

def send_test_message(text: str = None, audio_file: str = None, event_type: str = "message.received"):
    """Send a test message to Kafka."""
    message = {
        "api_version": "v2",
        "created_at": datetime.now().isoformat(),
        "event_type": event_type,
        "data": {
            "chat_id": "1702918",  # Use your actual chat ID
            "text": text or "",
            "from_phone": "+13474591567",
            "id": f"test_{datetime.now().timestamp()}",
            "is_read": False,
            "sent_at": datetime.now().isoformat(),
            "service": "iMessage",
            "attachments": []
        },
        "event_id": f"test-{datetime.now().timestamp()}"
    }

    if audio_file and os.path.exists(audio_file):
        import base64
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        # Simple detection
        fmt = "opus" if audio_file.endswith(".opus") else "wav"
        
        # If it's a WAV, we should convert to OPUS for realism, but for test we can send check consumer logic
        # Consumer checks: data.audio or attachments.
        # Let's attach as base64
        b64_data = base64.b64encode(audio_data).decode('ascii')
        
        message["data"]["message"] = {
            "audio": {
                "format": fmt,
                "data": b64_data
            }
        }
        print(f"   📎 Added audio: {audio_file} ({len(audio_data)} bytes)")
    
    try:
        future = producer.send(TOPIC_NAME, value=message)
        record_metadata = future.get(timeout=10)
        print(f"✅ Message sent successfully!")
        print(f"   Topic: {record_metadata.topic}")
        print(f"   Partition: {record_metadata.partition}")
        print(f"   Offset: {record_metadata.offset}")
        if text: print(f"   Message: {text}")
        return True
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def send_multiple_messages(messages: list):
    """Send multiple messages in sequence."""
    print(f"📤 Sending {len(messages)} messages...")
    print("=" * 60)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n[{i}/{len(messages)}] Sending: {msg}")
        send_test_message(msg)
        import time
        time.sleep(0.5)  # Small delay between messages
    
    print("\n" + "=" * 60)
    print(f"✅ All {len(messages)} messages sent!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Check if it's an audio file
        arg = sys.argv[1]
        if arg.endswith(('.opus', '.wav', '.m4a')):
            print(f"🎤 Sending audio test: {arg}")
            send_test_message(audio_file=arg)
        else:
            # Send single message from command line
            message = " ".join(sys.argv[1:])
            send_test_message(text=message)
    else:
        # Send multiple test messages
        test_messages = [
            "Hello! This is message 1",
            "This is message 2"
        ]
        send_multiple_messages(test_messages)
    
    producer.close()

