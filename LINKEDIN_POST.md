# LinkedIn Post for Series Hackathon

What an intense weekend at the Series HQ in NYC for the 24-hour hackathon! 🚀

Huge thanks to the C-suite and Shipyard for hosting an incredible hackathon experience.

At the dot of time start, me and Siddharth Haveliwala started brainstorming and came up with an idea we called **Sisi** - an AI-powered social matching platform that understands your personality through natural conversation.

## What We Built

**Sisi** is different from traditional dating apps. Instead of matching on keywords or photos, we match on **energy** - understanding who you really are through conversation.

### The Magic:
- **Natural Onboarding**: No forms, no checkboxes. Just chat with our AI like you're talking to a friend. The AI remembers everything and builds a 1536-dimensional personality vector that captures your essence.

- **Energy-Based Matching**: When you say "I love basketball," we don't just match you with other basketball players. We understand you're active, competitive, and enjoy team dynamics - then find people with similar energy, even if they express it differently.

- **Intelligent Group Chats**: Our AI analyzes every message in real-time with a "boring score" system (1-10). When conversations are dying, it proactively suggests topics or offers better matches. No more awkward ghosting - the system helps you find better connections.

- **Full Voice Memo Support**: Users can send voice memos, which get transcribed using Hugging Face Whisper, processed by our AI, and responded to with voice using ElevenLabs/Cartesia TTS. Complete audio pipeline from OPUS → WAV conversion → transcription → AI response → voice reply.

- **Network Updates**: Instagram Notes-style updates that expire after 48 hours, keeping your network connected without constant messaging.

### The Tech Stack:
- **3,700+ lines** of async Python code
- **Kafka** for real-time message processing
- **Supabase** (PostgreSQL + pgvector) for personality embeddings
- **OpenAI** for 1536-dimensional personality vectors
- **Hugging Face** (Llama-3.2-3B-Instruct, Whisper) for LLM and speech-to-text
- **AWS S3 + Lambda** for audio processing
- **Next.js** frontend (SISI interface) with draggable profile cards

### The Result:
An AI that doesn't just connect people - it **understands** them, matches them intelligently, and helps them build real relationships. All with < 100ms response time and real-time conversation analysis.

The future of human connection feels human. 💫

#SeriesHackathon #AI #MachineLearning #SocialMatching #Hackathon #Tech #Innovation
