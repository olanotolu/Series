# AI-Powered User Matching Setup Guide

## Overview

The AI-powered user matching system uses OpenAI embeddings and pgvector cosine similarity to match users based on their complete personality profile (not just hobby string matching).

## What Was Implemented

### 1. Database Schema (`setup_supabase_table.sql`)
- ✅ Added pgvector extension
- ✅ Created `user_embeddings` table with vector(1536) column
- ✅ Created `matches` table for tracking matches
- ✅ Added indexes for performance

### 2. PostgreSQL Function (`match_embeddings.sql`)
- ✅ Created `match_embeddings()` function for cosine similarity search
- ✅ Returns top matches with similarity scores

### 3. Embedding Service (`embedding_service.py`)
- ✅ `generate_user_embedding()` - Creates 1536-dim personality vectors using OpenAI
- ✅ `store_embedding()` - Stores embeddings in Supabase
- ✅ `get_user_vector()` - Retrieves user embeddings

### 4. Matching Module (`user_matching.py`)
- ✅ `find_matches()` - Finds compatible users using pgvector
- ✅ `get_match_profiles()` - Enriches matches with profile data
- ✅ `calculate_common_hobbies()` - Finds shared interests
- ✅ `format_match_message()` - Generates Series-style match messages

### 5. Integration (`consumer.py`)
- ✅ After onboarding completes:
  1. Generates personality embedding
  2. Stores embedding in database
  3. Finds top match using cosine similarity
  4. Sends completion message + match message

### 6. Session Manager (`session_manager_supabase.py`)
- ✅ Added `get_all_completed_profiles()` method

### 7. Dependencies
- ✅ Added `openai` to `requirements.txt`
- ✅ Added `OPENAI_API_KEY` placeholder to `.env`

## Setup Steps

### 1. Install Dependencies
```bash
pip install openai
```

### 2. Add OpenAI API Key
Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-...
```

### 3. Run Database Setup Scripts

**In Supabase SQL Editor:**

1. Run `setup_supabase_table.sql` to create:
   - pgvector extension
   - `user_embeddings` table
   - `matches` table

2. Run `match_embeddings.sql` to create the matching function

### 4. Verify Setup

Test the embedding service:
```python
from embedding_service import generate_user_embedding, store_embedding

profile = {
    'name': 'Test User',
    'school': 'Test University',
    'age': '20',
    'hobbies': 'coding, basketball, music'
}

vector = generate_user_embedding(profile)
if vector:
    store_embedding('+1234567890', vector)
    print("✅ Embedding stored successfully!")
```

## How It Works

1. **User completes onboarding** → Profile saved (name, school, age, hobbies)

2. **Embedding generation** → OpenAI creates 1536-dim vector from profile text

3. **Vector storage** → Stored in `user_embeddings` table with pgvector

4. **Match finding** → PostgreSQL function finds closest vectors using cosine similarity

5. **Match message** → Series-style message sent with match details and common hobbies

## Example Match Message

```
Alright—your profile is live. And we already found someone who feels *weirdly close* to you.

**Sarah**, 21, Stanford University.
Match strength: **87%**.

You two share the same energy around: coding, basketball, and music.

Want me to open the chat?
```

## Advantages

- **Semantic Understanding**: Understands "basketball" and "hoops" are similar
- **Personality Matching**: Considers entire profile, not just hobbies
- **Scalable**: Vector search is fast even with millions of users
- **Production-Ready**: Same tech stack as major social apps
- **Accurate**: Cosine similarity > string matching

## Troubleshooting

### "OPENAI_API_KEY not set"
- Add your OpenAI API key to `.env`

### "pgvector extension not found"
- Run `CREATE EXTENSION IF NOT EXISTS vector;` in Supabase SQL Editor

### "match_embeddings function not found"
- Run `match_embeddings.sql` in Supabase SQL Editor

### "No matches found"
- Ensure at least 2 users have completed onboarding
- Check that embeddings were generated and stored
- Verify `user_embeddings` table has data

## Next Steps

1. ✅ Complete setup steps above
2. Test with 2+ users completing onboarding
3. Verify matches are found and messages sent
4. Monitor embedding generation costs (OpenAI API)

