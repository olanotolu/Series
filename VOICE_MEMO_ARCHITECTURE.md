# 🎤 Voice Memo Architecture - Complete Pipeline

## The Full Flow: From OPUS to Voice Response

```
User sends Voice Memo
    ↓
Series API (iMessage)
    ↓
Kafka Event (with base64 OPUS or URL)
    ↓
Python Consumer (consumer.py)
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Receive & Download                                 │
│  ─────────────────────────────────────────────────────────── │
│  • Get base64 OPUS data OR audio URL                        │
│  • If URL: Download OPUS file from Series API               │
│  • Decode base64 → OPUS bytes                               │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Store OPUS (Original Format)                        │
│  ─────────────────────────────────────────────────────────── │
│  Option A: AWS S3 (Production)                              │
│  • Upload OPUS to S3: s3://bucket/voice_memo_*.opus        │
│  • Keep original for archival                                │
│                                                              │
│  Option B: Local Storage (Development)                      │
│  • Save to: audio_files/voice_memo_*.opus                   │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Convert OPUS → WAV                                 │
│  ─────────────────────────────────────────────────────────── │
│  File: opus_to_wav.py                                        │
│                                                              │
│  1. Decode base64 OPUS → binary OPUS data                    │
│  2. Write to temp file: /tmp/voice_*.opus                   │
│  3. Use ffmpeg to convert:                                   │
│     ffmpeg -i input.opus                                     │
│          -ar 16000    # 16kHz sample rate (optimal for STT) │
│          -ac 1        # Mono channel                        │
│          -f wav       # WAV format                          │
│          output.wav                                          │
│  4. Cleanup temp OPUS file                                  │
│                                                              │
│  Why WAV?                                                    │
│  • Whisper (STT) requires uncompressed audio                 │
│  • 16kHz mono is optimal for speech recognition             │
│  • WAV is universal format for audio processing              │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Store WAV                                           │
│  ─────────────────────────────────────────────────────────── │
│  Option A: AWS S3 (Production)                              │
│  • Upload WAV to S3: s3://bucket/voice_memo_*.wav           │
│  • Download back to temp file for Whisper (needs local)     │
│                                                              │
│  Option B: Local Storage (Development)                      │
│  • Save to: audio_files/voice_memo_*.wav                    │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Transcribe WAV → Text (Speech-to-Text)             │
│  ─────────────────────────────────────────────────────────── │
│  Service: Hugging Face Inference API                        │
│  Model: openai/whisper-large-v3-turbo                       │
│                                                              │
│  Process:                                                    │
│  1. Read WAV file from disk                                 │
│  2. Send to Hugging Face Whisper API                         │
│  3. Whisper returns:                                         │
│     • Transcript text                                        │
│     • Detected language (auto-detected)                     │
│  4. Language detection (fallback): langdetect library       │
│                                                              │
│  Output:                                                     │
│  • transcript: "Hey, how are you doing?"                    │
│  • detected_language: "en"                                  │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Process Text (Same as Text Messages)               │
│  ─────────────────────────────────────────────────────────── │
│  • Get conversation history from Supabase                   │
│  • Get behavioral context                                   │
│  • Send to LLM (Hugging Face Llama-3.2-3B-Instruct)         │
│  • Generate AI response text                                │
│                                                              │
│  Example:                                                    │
│  Transcript: "Hey, how are you doing?"                      │
│  → LLM Response: "I'm doing great! How about you?"         │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Convert Text → Speech (Text-to-Speech)            │
│  ─────────────────────────────────────────────────────────── │
│  Service: ElevenLabs or Cartesia                            │
│                                                              │
│  Process:                                                    │
│  1. Send response text + language to TTS API                │
│  2. Receive WAV audio file                                  │
│  3. Store WAV (S3 or local)                                │
│                                                              │
│  Output: WAV file with AI voice saying the response         │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: Convert WAV → M4A (AAC)                           │
│  ─────────────────────────────────────────────────────────── │
│  Why M4A?                                                    │
│  • iMessage voice memos use M4A format                      │
│  • AAC codec (compressed, smaller file size)                 │
│  • Better compatibility with iOS                             │
│                                                              │
│  Process:                                                    │
│  1. Use ffmpeg to convert:                                  │
│     ffmpeg -i input.wav                                      │
│          -c:a aac        # AAC codec                        │
│          -b:a 64k       # 64kbps bitrate                    │
│          output.m4a                                         │
│  2. Upload M4A to S3 (if using S3)                          │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 9: Send Voice Response                                │
│  ─────────────────────────────────────────────────────────── │
│  • Send M4A file via Series API                             │
│  • Include text transcript (required by API)                │
│  • User receives voice memo response                        │
│                                                              │
│  Rule: Voice memo in → Voice memo out (ALWAYS)              │
│  • Never send text response to voice memo                   │
│  • Always respond with voice                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Details

### Audio Format Conversions

**OPUS → WAV:**
- **Tool:** ffmpeg
- **Settings:** 16kHz, mono
- **Why:** Optimal for speech recognition
- **File:** `opus_to_wav.py`

**WAV → M4A:**
- **Tool:** ffmpeg
- **Codec:** AAC (Advanced Audio Coding)
- **Bitrate:** 64kbps
- **Why:** iMessage voice memo format
- **File:** `wav_to_m4a()` function in `consumer.py`

### Storage Strategy

**Production (S3):**
```
S3 Bucket: series-audio-files/
├── voice_memo_{user}_{timestamp}_{id}.opus  (Original)
├── voice_memo_{user}_{timestamp}_{id}.wav   (For STT)
└── tts_response_{timestamp}.m4a            (Response)
```

**Development (Local):**
```
audio_files/
├── voice_memo_{user}_{timestamp}_{id}.opus
├── voice_memo_{user}_{timestamp}_{id}.wav
└── tts_response_{timestamp}.m4a
```

### Why Each Format?

| Format | Purpose | Why |
|--------|---------|-----|
| **OPUS** | Original from iMessage | Compressed, efficient, native iOS format |
| **WAV** | Speech-to-Text processing | Uncompressed, Whisper requires it, 16kHz optimal |
| **M4A (AAC)** | Voice response | iMessage voice memo format, compressed |

---

## The Complete Pipeline (Step-by-Step)

### 1. **Receive Voice Memo**
```
Kafka Event:
{
  "event": "message.received",
  "audio": {
    "data": "base64_opus_string...",  # OR
    "url": "https://api.series.so/audio/..."
  }
}
```

### 2. **Download (if URL)**
```python
opus_data = await download_file(session, audio_url)
base64_opus = base64.b64encode(opus_data).decode('ascii')
```

### 3. **Store OPUS (Original)**
```python
# S3 or local
opus_s3_key = f"voice_memo_{user}_{timestamp}_{id}.opus"
upload_to_s3(bucket, opus_s3_key, opus_bytes, 'audio/ogg')
```

### 4. **Convert OPUS → WAV**
```python
# opus_to_wav.py
ffmpeg -i temp.opus -ar 16000 -ac 1 -f wav output.wav
```

### 5. **Store WAV**
```python
wav_s3_key = f"voice_memo_{user}_{timestamp}_{id}.wav"
upload_to_s3(bucket, wav_s3_key, wav_data, 'audio/wav')
```

### 6. **Transcribe WAV → Text**
```python
# Hugging Face Whisper
transcript, language = await transcribe_audio(wav_filename)
# Returns: ("Hey, how are you?", "en")
```

### 7. **Get LLM Response**
```python
# Same as text messages
llm_reply = await get_llm_response(transcript, history, language)
# Returns: "I'm doing great! How about you?"
```

### 8. **Text → Speech (TTS)**
```python
# ElevenLabs or Cartesia
tts_wav = await text_to_speech(llm_reply, language="en")
# Returns: WAV file path
```

### 9. **Convert WAV → M4A**
```python
# For iMessage voice memo format
m4a_file = wav_to_m4a(tts_wav)
# Returns: M4A file path
```

### 10. **Send Voice Response**
```python
# Series API
await send_audio(session, chat_id, m4a_file, text=llm_reply)
# User receives voice memo response
```

---

## Key Technologies

### Audio Processing
- **ffmpeg** - Format conversion (OPUS↔WAV↔M4A)
- **pydub** - Audio manipulation library

### Speech-to-Text
- **Hugging Face Whisper** - `openai/whisper-large-v3-turbo`
- **Auto language detection**
- **Multilingual support** (English, Hindi, French, etc.)

### Text-to-Speech
- **ElevenLabs** - High-quality voice synthesis
- **Cartesia** - Alternative TTS provider
- **Language-specific voices**

### Storage
- **AWS S3** - Production audio storage
- **Local filesystem** - Development fallback

---

## Error Handling & Fallbacks

### If OPUS Download Fails
→ Send text: "Sorry, couldn't download the voice memo."

### If OPUS → WAV Conversion Fails
→ Send text: "Sorry, couldn't process that voice memo."

### If Transcription Fails
→ Use fallback message: "Hey! I got your voice memo! Thanks for sending it."
→ Still generate voice response (voice in → voice out)

### If TTS Fails
→ Retry with simpler message: "Got your voice memo!"
→ If still fails, send text (last resort)

### If M4A Conversion Fails
→ Try sending WAV directly
→ If that fails, send text (last resort)

---

## Performance Optimizations

1. **Async Processing** - All I/O operations are async
2. **CPU-Bound Executor** - Audio conversion runs in separate thread
3. **S3 Storage** - Scalable, no local disk limits
4. **Temp File Cleanup** - Automatic cleanup after processing
5. **Parallel Operations** - Download, convert, and upload can overlap

---

## The Magic: Voice Memo In → Voice Memo Out

**Key Rule:** If user sends voice memo, AI ALWAYS responds with voice memo.

**Why?**
- Natural conversation flow
- Maintains communication medium
- Better user experience
- Feels more human

**Implementation:**
- Never sends text response to voice memo
- Always generates TTS and sends as M4A
- Even on errors, tries to send voice error message

---

## Architecture Diagram

```
┌─────────────┐
│   iMessage  │
│  Voice Memo │
└──────┬──────┘
       │ OPUS (base64 or URL)
       ↓
┌─────────────────┐
│   Series API    │
└──────┬──────────┘
       │ Kafka Event
       ↓
┌─────────────────┐
│  Kafka Queue   │
└──────┬──────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│     Python Consumer (consumer.py)        │
│  ─────────────────────────────────────  │
│                                          │
│  1. Download OPUS                        │
│  2. Store OPUS (S3/local)                │
│  3. Convert OPUS → WAV (ffmpeg)         │
│  4. Store WAV (S3/local)                 │
│  5. Transcribe WAV → Text (Whisper)      │
│  6. Get LLM Response (Hugging Face)      │
│  7. Convert Text → Speech (ElevenLabs)   │
│  8. Convert WAV → M4A (ffmpeg)          │
│  9. Send M4A via Series API              │
└─────────────────────────────────────────┘
       │
       ↓
┌─────────────┐
│   iMessage  │
│ Voice Reply │
└─────────────┘
```

---

## File Sizes & Performance

**Typical Sizes:**
- OPUS (original): ~50-200 KB (compressed)
- WAV (for STT): ~500 KB - 2 MB (uncompressed)
- M4A (response): ~100-400 KB (compressed AAC)

**Processing Time:**
- OPUS → WAV: ~100-500ms
- Transcription: ~1-3 seconds (depends on length)
- TTS: ~1-2 seconds
- WAV → M4A: ~100-300ms
- **Total:** ~3-6 seconds end-to-end

---

## Why This Architecture?

1. **Preserve Original** - Keep OPUS for archival
2. **Optimize for STT** - WAV at 16kHz mono is optimal for Whisper
3. **Compatible Response** - M4A works perfectly with iMessage
4. **Scalable Storage** - S3 handles unlimited audio files
5. **Error Resilient** - Multiple fallbacks at each step

---

**This is a production-grade audio processing pipeline built in 24 hours.** 🚀
