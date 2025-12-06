# Next Steps: AI-Powered Matching System

## ✅ What's Done
- ✅ Database tables created (`user_embeddings`, `matches`)
- ✅ pgvector extension enabled
- ✅ `match_embeddings()` function created
- ✅ Code integrated into `consumer.py`

## 🚀 What's Next

### Step 1: Add OpenAI API Key

1. Get your OpenAI API key from: https://platform.openai.com/api-keys
2. Open `.env` file
3. Add your key:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

### Step 2: Install OpenAI Package

```bash
pip install openai
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Step 3: Test the System

#### Option A: Test with Real Users
1. Start your consumer:
   ```bash
   python consumer.py
   ```

2. Have 2+ users complete onboarding:
   - User 1 completes onboarding → embedding generated
   - User 2 completes onboarding → embedding generated + match found!

#### Option B: Test Embedding Generation Manually

Create a test script `test_embedding.py`:

```python
from embedding_service import generate_user_embedding, store_embedding

# Test profile
profile = {
    'name': 'Test User',
    'school': 'Test University',
    'age': '20',
    'hobbies': 'coding, basketball, music'
}

print("🧠 Generating embedding...")
vector = generate_user_embedding(profile)

if vector:
    print(f"✅ Generated {len(vector)}-dimensional vector")
    print(f"   First 5 values: {vector[:5]}")
    
    # Store it (use a test phone number)
    store_embedding('+1234567890', vector)
    print("✅ Embedding stored!")
else:
    print("❌ Failed to generate embedding")
```

Run it:
```bash
python test_embedding.py
```

### Step 4: Verify Everything Works

After users complete onboarding, check:

1. **Embeddings are generated**: Check Supabase `user_embeddings` table
   ```sql
   SELECT user_id, updated_at FROM user_embeddings;
   ```

2. **Matches are found**: Check Supabase `matches` table
   ```sql
   SELECT user1_id, user2_id, score, matched_at FROM matches ORDER BY matched_at DESC;
   ```

3. **Messages are sent**: Check consumer logs for:
   ```
   🧠 Generating personality embedding...
   ✅ Generated 1536-dimensional embedding
   ✅ Stored embedding for +1234567890
   🔍 Finding matches...
   ✅ Found 1 match(es)
   ✅ Match found: Sarah (score: 87.00%)
   ```

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"
- Make sure you added the key to `.env`
- Restart consumer after adding the key

### "No matches found"
- Need at least 2 users with completed onboarding
- Check that embeddings were generated:
  ```sql
  SELECT COUNT(*) FROM user_embeddings;
  ```

### "pgvector extension not found"
- Already enabled! ✅ (You saw the success message)

### "match_embeddings function not found"
- Already created! ✅ (You saw the success message)

## 📊 How It Works

1. **User completes onboarding** → Profile saved (name, school, age, hobbies)

2. **Embedding generation** → OpenAI creates 1536-dim vector from profile

3. **Vector storage** → Stored in `user_embeddings` table

4. **Match finding** → PostgreSQL function finds closest vectors using cosine similarity

5. **Match message** → Series-style message sent with match details

## 🎯 Expected Flow

```
User: "Hi"
Bot: "Hey! What's your name?"
User: "Sarah"
Bot: "Nice to meet you, Sarah! What school do you go to?"
...
User: "coding, basketball"
Bot: "Perfect! Alright—your profile is live. And we already found someone who feels *weirdly close* to you.

**John**, 21, MIT.
Match strength: **87%**.

You two share the same energy around: coding and basketball.

Want me to open the chat?"
```

## ✅ You're Ready!

Once you:
1. ✅ Add OpenAI API key to `.env`
2. ✅ Install `openai` package
3. ✅ Restart consumer

The matching system will automatically work for all new users completing onboarding!

