# Series Tech Stack - Fast Summary

## The Flow: From Audio to Everything

```
User's Phone
    ↓
Series API (iMessage/SMS)
    ↓
Kafka (Message Queue)
    ↓
Python Consumer (consumer.py)
    ↓
    ├─→ Audio Processing
    │   ├─→ Download OPUS file
    │   ├─→ Convert to WAV (Lambda/ffmpeg)
    │   ├─→ Transcribe (Hugging Face Whisper)
    │   └─→ Store in S3
    │
    ├─→ Text Processing
    │   ├─→ Detect language
    │   ├─→ Check commands (/update, /reset)
    │   ├─→ Onboarding flow
    │   └─→ Normal conversation
    │
    └─→ AI Response
        ├─→ Get LLM response (Hugging Face)
        ├─→ Generate TTS audio (ElevenLabs/Cartesia)
        └─→ Send back via Series API
```

---

## The Stack (Bottom to Top)

### 1. **Storage Layer**
```
Supabase (PostgreSQL)
├── sessions              # User profiles
├── user_embeddings      # Personality vectors (pgvector)
├── matches              # User connections
├── group_chats          # Chat metadata
├── group_chat_messages  # Messages + analytics
└── user_updates         # Instagram Notes-style updates

AWS S3
└── audio_files/         # Voice memos (OPUS, WAV, M4A)
```

### 2. **Message Queue**
```
Kafka (aiokafka)
├── Receives events from Series API
├── Partitions for scalability
└── Offset tracking for reliability
```

### 3. **Processing Layer**
```
Python Consumer (consumer.py)
├── Async/await for concurrency
├── Handles thousands of messages
└── Routes to appropriate handlers
```

### 4. **Intelligence Layer**
```
AI Services
├── OpenAI
│   └── text-embedding-3-large (personality vectors)
│
├── Hugging Face
│   ├── Llama-3.2-3B-Instruct (conversations)
│   ├── Whisper (speech-to-text)
│   └── Sentiment/Topic analysis
│
└── ElevenLabs/Cartesia
    └── Text-to-speech (TTS)
```

### 5. **Matching Engine**
```
user_matching.py
├── Generate personality embedding
├── Search similar vectors (cosine similarity)
├── Calculate match scores
└── Format match messages
```

### 6. **Group Chat Intelligence**
```
group_chat_intelligence.py
├── analyze_boring_score()      # 1-10 score
├── analyze_sentiment()          # -1 to 1
├── extract_topics()            # What you're talking about
├── update_engagement()         # Who's active/quiet
└── calculate_health_score()    # Overall conversation quality
```

### 7. **Frontend**
```
Next.js (sisi-nextjs/)
├── React components
├── Supabase API routes
├── D3.js (ready for graphs)
└── Framer Motion (animations)
```

---

## Data Flow Examples

### Example 1: User Sends Text Message

```
1. User: "Hi"
   ↓
2. Series API → Kafka event
   ↓
3. consumer.py receives event
   ↓
4. process_text_message()
   ├─→ Check onboarding status
   ├─→ Get user profile from Supabase
   ├─→ Detect language
   └─→ Get LLM response (Hugging Face)
   ↓
5. Send response via Series API
   ↓
6. User receives: "Hey! How's it going?"
```

### Example 2: User Posts Update

```
1. User: "/update I got a job"
   ↓
2. consumer.py detects /update command
   ↓
3. update_manager.py
   ├─→ Deactivate old update (if exists)
   ├─→ Create new update in Supabase
   └─→ Set expiration (48 hours)
   ↓
4. Response: "✅ Update posted!"
```

### Example 3: Personality Matching

```
1. User completes onboarding
   ↓
2. embedding_service.py
   ├─→ Generate embedding (OpenAI)
   └─→ Store in user_embeddings table
   ↓
3. user_matching.py
   ├─→ Search similar vectors (pgvector)
   ├─→ Calculate match scores
   └─→ Format match message
   ↓
4. Send match: "I found someone who feels weirdly close to you..."
```

### Example 4: Group Chat Intelligence

```
1. User sends message in group chat
   ↓
2. group_chat_intelligence.py
   ├─→ analyze_boring_score() → 8.0
   ├─→ analyze_sentiment() → -0.5
   ├─→ extract_topics() → ["basketball", "workout"]
   └─→ update_engagement() → Track participation
   ↓
3. Check avg_boring_score → 6.0
   ↓
4. If ≥ 4.0:
   └─→ match_replacement.py
       └─→ Offer better match privately
```

---

## Key Technologies

### Backend
- **Python 3.13** - Async/await for concurrency
- **Kafka (aiokafka)** - Message streaming
- **Supabase** - PostgreSQL database
- **OpenAI** - Personality embeddings
- **Hugging Face** - LLM, STT, analysis
- **AWS S3** - Audio storage
- **Lambda** - Audio conversion

### Frontend
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **Framer Motion** - Animations
- **D3.js** - Graph visualization
- **Tailwind CSS** - Styling

### Database
- **PostgreSQL** - Main database
- **pgvector** - Vector similarity search
- **Row Level Security** - Privacy protection

---

## Performance

- **< 100ms** - Average response time
- **Real-time** - Message processing
- **Async** - Handles thousands of conversations
- **Scalable** - Kafka partitions for load distribution

---

## The Magic

**It's not just code. It's intelligence.**

Every message is analyzed. Every conversation is understood. Every match is meaningful.

Because we don't just process data. We understand people.

