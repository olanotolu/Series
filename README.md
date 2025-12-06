# Series Hackathon - iMessage Bot

A Kafka-based consumer that receives and processes iMessage text and voice memos via the Series API.

## 🎯 Milestone: Audio & Text Processing

✅ **Working Features:**
- Receive text messages from iMessage
- Receive voice memos (audio) from iMessage
- Download audio files from URLs
- Save audio files (OPUS and WAV formats)
- Send responses back to users
- Detailed logging for all events

## 📁 Project Structure

```
Series/
├── consumer.py          # Main Kafka consumer (receives messages)
├── producer.py          # Test producer (send test messages)
├── opus_to_wav.py      # Audio conversion utility
├── requirements.txt     # Python dependencies
├── .env                 # API credentials (not in git)
├── audio_files/         # Saved voice memos
│   ├── *.opus          # Original OPUS format
│   └── *.wav           # Converted WAV format
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` file with your Series API credentials:
```
API_KEY=your_api_key
KAFKA_BOOTSTRAP_SERVERS=your_kafka_server
KAFKA_TOPIC_NAME=your_topic
# ... (see Series dashboard for full list)
```

### 3. Run Consumer
```bash
python consumer.py
```

### 4. Send Messages
- **Text**: Send SMS/iMessage to `+16463769330`
- **Voice Memo**: Send voice memo via iMessage to `+16463769330`

## 📝 How It Works

1. **Phone → Series**: User sends message/voice memo to Series number
2. **Series → Kafka**: Series publishes event to Kafka topic
3. **Kafka → Consumer**: Consumer receives event
4. **Processing**:
   - Text messages: Echo back with "You said: {text}"
   - Voice memos: Download, save as OPUS/WAV, send confirmation
5. **Consumer → Series API**: Send response back
6. **Series → Phone**: Response delivered to user

## 🎤 Voice Memo Processing

When a voice memo is received:
- Audio is detected in `attachments` array
- Audio file is downloaded from URL
- Saved as `.opus` (original) and `.wav` (playback)
- Files stored in `audio_files/` directory
- User receives confirmation message

## 📊 Logging

The consumer provides detailed logging:
- Event headers (type, time, Kafka partition/offset)
- Incoming messages (sender, text, IDs)
- Outgoing messages (status, message IDs)
- Audio processing (download, conversion, file sizes)
- Typing indicators

## 🔧 Testing

### Test Text Message
```bash
python producer.py "Hello, this is a test!"
```

### Test Voice Memo
Send a voice memo from your iPhone to `+16463769330`

## 📦 Dependencies

- `kafka-python` - Kafka consumer/producer
- `requests` - HTTP requests to Series API
- `python-dotenv` - Environment variable management
- `pydub` - Audio processing
- `ffmpeg` - Audio conversion (system dependency)

## 🎯 Next Steps

- [ ] Add LLM integration for intelligent responses
- [ ] Add speech-to-text (STT) for voice memos
- [ ] Add text-to-speech (TTS) for audio responses
- [ ] Add conversation context/memory
- [ ] Add multi-user support

## 📞 Series API

- **Base URL**: `https://hackathon.series.so`
- **Phone Number**: `+16463769330`
- **Documentation**: See Series dashboard

---

**Status**: ✅ Audio & Text Processing Complete
