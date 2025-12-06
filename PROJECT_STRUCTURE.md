# Series Project Structure

## Directory Organization

```
Series/
├── README.md                    # Main project documentation
├── TECH_STACK_SUMMARY.md        # Quick tech overview
├── requirements.txt             # Python dependencies
├── requirements_lambda.txt      # Lambda dependencies
├── .gitignore                   # Git ignore rules
│
├── consumer.py                  # Main Kafka consumer (core)
├── onboarding_flow.py          # Onboarding logic
├── embedding_service.py         # OpenAI embeddings
├── user_matching.py             # Personality matching
├── group_chat_manager.py        # Group chat operations
├── group_chat_intelligence.py   # Conversation analysis
├── match_replacement.py         # Better match offers
├── update_manager.py            # User updates system
├── topic_suggester.py           # Topic suggestions
├── conversation_summarizer.py   # Conversation summaries
├── reminder_system.py           # Smart reminders
│
├── session_manager.py           # Local session manager
├── session_manager_supabase.py  # Supabase session manager
│
├── opus_to_wav.py               # Audio conversion
├── audio_to_opus.py             # Audio processing
├── aws_audio_storage.py         # S3 operations
├── elevenlabs_tts.py            # ElevenLabs TTS
├── cartesia_tts.py              # Cartesia TTS
│
├── lambda_audio_converter.py    # Lambda: OPUS to WAV
├── lambda_wav_to_m4a.py        # Lambda: WAV to M4A
├── lambda_deploy.sh             # Lambda deployment script
│
├── producer.py                  # Test producer
├── dlq_handler.py               # Dead letter queue handler
├── main.py                      # Entry point (if needed)
├── agent.py                     # Agent logic
│
├── run_consumer.sh              # Run script
├── setup_s3_bucket.py           # S3 setup
├── setup_teammate_aws.sh        # AWS access setup
│
├── migrations/                  # Database migrations
│   ├── setup_supabase_table.sql
│   ├── migrate_add_profile_columns.sql
│   ├── migrate_add_matching_tables.sql
│   ├── migrate_add_group_chats.sql
│   ├── migrate_group_chat_intelligence.sql
│   ├── migrate_add_user_updates.sql
│   ├── migrate_add_pending_match.sql
│   ├── fix_match_embeddings_rpc.sql
│   ├── match_embeddings.sql
│   └── verify_schema.sql
│
├── tests/                       # Test files
│   ├── test_matching.py
│   ├── test_embedding.py
│   ├── test_supabase_table.py
│   ├── test_cartesia.py
│   ├── test_tts.py
│   └── test_llm_simple.py
│
├── scripts/                     # Utility scripts
│   ├── add_demo_users.py
│   └── fix_demo_embeddings.py
│
├── docs/                        # Documentation
│   ├── README_RUNNING.md
│   ├── README_SISI.md
│   ├── TECH_STACK_SUMMARY.md
│   ├── UPDATE_FEATURE.md
│   ├── MATCHING_SETUP.md
│   ├── LLM_INTEGRATION.md
│   ├── NEXT_STEPS_MATCHING.md
│   ├── SCHEMA_REVIEW_GUIDE.md
│   ├── SCREEN_GUIDE.md
│   ├── QUICK_START.md
│   ├── FIX_RLS_ISSUE.md
│   ├── FIXES_APPLIED.md
│   └── setup_teammate_aws_access.md
│
├── sisi-nextjs/                 # Next.js frontend
│   ├── app/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── README.md
│
└── sisi.html                     # Legacy HTML interface
```

## Core Files (Production)

### Main Application
- `consumer.py` - Main Kafka consumer (2,153 lines)
- `onboarding_flow.py` - Onboarding logic
- `embedding_service.py` - Personality embeddings
- `user_matching.py` - Matching algorithm

### Intelligence Layer
- `group_chat_intelligence.py` - Conversation analysis
- `match_replacement.py` - Better match offers
- `update_manager.py` - User updates
- `topic_suggester.py` - Topic suggestions
- `conversation_summarizer.py` - Summaries
- `reminder_system.py` - Smart reminders

### Infrastructure
- `group_chat_manager.py` - Database operations
- `session_manager_supabase.py` - Session management
- `aws_audio_storage.py` - S3 operations
- `dlq_handler.py` - Error handling

## Database Migrations

Run migrations in order:
1. `setup_supabase_table.sql`
2. `migrate_add_profile_columns.sql`
3. `migrate_add_matching_tables.sql`
4. `migrate_add_group_chats.sql`
5. `migrate_add_pending_match.sql`
6. `migrate_group_chat_intelligence.sql`
7. `migrate_add_user_updates.sql`
8. `fix_match_embeddings_rpc.sql` (if needed)
9. `verify_schema.sql` (verification)

## Testing

Test files are in `tests/` directory:
- `test_matching.py` - Matching tests
- `test_embedding.py` - Embedding tests
- `test_supabase_table.py` - Database tests
- `test_llm_simple.py` - LLM tests

## Documentation

All documentation is in `docs/` except:
- `README.md` - Main project README (root)
- `TECH_STACK_SUMMARY.md` - Quick tech overview (root)

