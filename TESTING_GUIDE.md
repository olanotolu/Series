# 🧪 Testing Guide for Shipyard Deployment

## Quick Test Checklist

### 1. **Health Check Endpoint** ✅

Test if the service is running:

```bash
# In browser or terminal:
curl https://series.dev.olanotolu.shipyard.host/health
# OR
curl https://series.dev.olanotolu.shipyard.host/

# Expected response:
{
  "status": "healthy",
  "service": "series-consumer",
  "version": "1.0.0"
}
```

**If this works:** ✅ Your container is running and accessible!

---

### 2. **Check Shipyard Logs** 📊

1. Go to your Shipyard dashboard
2. Navigate to your deployment
3. Click on **"Logs"** tab
4. Look for these success indicators:

```
✅ Health check server started on port 8080
✅ Kafka Consumer started!
✅ Connected to Supabase
🔄 Waiting for messages...
```

**If you see errors:**
- Check environment variables are set correctly
- Verify Kafka connection string
- Check Supabase credentials

---

### 3. **Test via Text Message** 💬

This is the **main way** your system works:

1. **Send a text message** to your `SENDER_NUMBER` (from your deployment config)
   - Example: `+16463769330` (or whatever you configured)

2. **Send a simple message:**
   ```
   Hi
   ```

3. **Expected behavior:**
   - AI should respond with onboarding questions
   - Check Shipyard logs to see message processing
   - Response should come back via text message

4. **Complete onboarding:**
   ```
   Hi
   → AI: "Hey! I'm your AI friend. What's your name?"
   You: "I'm Ola"
   → AI: "Nice to meet you, Ola! Where are you from?"
   You: "UB"
   → AI: "Cool! How old are you?"
   You: "30"
   → AI: "What do you love doing?"
   You: "Basketball, fitness, hiking"
   ```

5. **After onboarding:**
   - AI should generate personality embedding
   - Store in LanceDB (check logs for "✅ Stored embedding in LanceDB")
   - Find matches and send match message

---

### 4. **Test LanceDB Integration** 🚀

After sending a message and completing onboarding:

1. **Check Shipyard logs** for:
   ```
   🧠 Generating embedding for: Ola (UB, 30)
   ✅ Generated 1536-dimensional embedding
   ✅ Stored embedding in Supabase for +1234567890
   ✅ Stored embedding in LanceDB for +1234567890
   🔍 Finding matches...
   ✅ Found X match(es) via LanceDB for +1234567890
   ```

2. **Verify LanceDB is working:**
   - Look for "via LanceDB" in match logs (not "via RPC" or "fallback")
   - Should see fast matching results

---

### 5. **Test Voice Memos** 🎤

1. **Send a voice memo** to your SENDER_NUMBER
2. **Check logs** for:
   ```
   📥 INCOMING VOICE MEMO
   🎵 STEP 1: Downloading OPUS file...
   🎵 STEP 2-4: Converting OPUS → WAV...
   🎤 STEP 5: Transcribing WAV → Text (Whisper)...
   💬 Processing as TEXT message...
   ```

3. **Expected:**
   - Voice memo transcribed
   - AI responds (text or voice)
   - Audio stored in S3

---

### 6. **Test Commands** ⚡

Try these commands:

```
/update I got a new job
→ Should respond: "✅ Update posted!"

/update
→ Should show network updates

/reset
→ Should reset onboarding
```

---

### 7. **Test Group Chat Intelligence** 👥

1. **Create a group chat** with multiple users
2. **Send messages** in the group
3. **Check logs** for:
   ```
   📊 Analyzing message...
   Boring score: 6.0
   Sentiment: 0.5
   Topics: ["basketball", "fitness"]
   ```

4. **If conversation gets boring:**
   - AI should suggest topics
   - Or offer replacement matches

---

## Troubleshooting

### Health Check Returns 404 or Error

**Problem:** Service not running or routing issue

**Solution:**
1. Check Shipyard dashboard - is container running?
2. Check logs for startup errors
3. Verify port 8080 is exposed
4. Check Shipyard routing configuration

---

### No Response to Text Messages

**Problem:** Kafka consumer not receiving messages

**Solution:**
1. Check Kafka connection in logs
2. Verify `KAFKA_BOOTSTRAP_SERVERS` is correct
3. Check `KAFKA_TOPIC_NAME` matches Series API topic
4. Verify `KAFKA_GROUP_ID` is unique
5. Check `SERIES_API_KEY` is valid

---

### Embeddings Not Storing in LanceDB

**Problem:** LanceDB not working

**Solution:**
1. Check logs for "❌ Error storing embedding in LanceDB"
2. Verify `LANCEDB_PATH` environment variable (defaults to `./lancedb_data`)
3. Check disk space in container
4. Look for permission errors

**Note:** LanceDB stores data locally in the container. For production, consider:
- Using persistent volumes
- Or using LanceDB cloud/remote storage

---

### Matches Not Found

**Problem:** Matching not working

**Solution:**
1. Verify user completed onboarding
2. Check if embedding was generated and stored
3. Look for "Found X match(es) via LanceDB" in logs
4. If you see "via Supabase fallback", LanceDB might not be working
5. Check if other users exist in database

---

### Audio Processing Fails

**Problem:** Voice memos not working

**Solution:**
1. Check if ffmpeg is installed (should be in Dockerfile)
2. Verify S3 credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
3. Check S3 bucket exists and is accessible
4. Verify `S3_AUDIO_BUCKET` environment variable

---

## Advanced Testing

### Test Matching Performance

1. **Create multiple test users:**
   ```python
   # Use scripts/add_demo_users.py
   python scripts/add_demo_users.py
   ```

2. **Send messages from different numbers**
3. **Verify matches are found quickly** (should be < 100ms with LanceDB)

---

### Test Scalability

1. **Send multiple messages simultaneously**
2. **Check logs** for concurrent processing
3. **Monitor CPU/Memory** in Shipyard dashboard
4. **Verify no message loss**

---

### Test Error Recovery

1. **Temporarily break a service** (e.g., invalid Supabase key)
2. **Send a message**
3. **Check error handling** in logs
4. **Fix the service**
5. **Verify recovery** and message processing resumes

---

## Success Criteria ✅

Your deployment is working correctly if:

- ✅ Health check returns 200 OK
- ✅ Logs show "Kafka Consumer started!"
- ✅ Text messages receive AI responses
- ✅ Onboarding flow works end-to-end
- ✅ Embeddings stored in LanceDB (check logs)
- ✅ Matches found via LanceDB (not Supabase fallback)
- ✅ Voice memos transcribed and responded to
- ✅ Commands (`/update`, `/reset`) work
- ✅ No errors in logs

---

## Quick Test Script

Save this as `test_deployment.sh`:

```bash
#!/bin/bash

echo "🧪 Testing Series Deployment..."
echo ""

# Test 1: Health Check
echo "1. Testing health endpoint..."
HEALTH=$(curl -s https://series.dev.olanotolu.shipyard.host/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    echo "   Response: $HEALTH"
fi

echo ""
echo "2. Next steps:"
echo "   - Check Shipyard logs for 'Kafka Consumer started!'"
echo "   - Send a text message to your SENDER_NUMBER"
echo "   - Complete onboarding flow"
echo "   - Verify matches are found via LanceDB"
```

Run with: `bash test_deployment.sh`

---

## Need Help?

If something isn't working:

1. **Check Shipyard logs** - Most issues show up here
2. **Verify environment variables** - All required vars must be set
3. **Test health endpoint** - Confirms basic connectivity
4. **Check Series API** - Verify your API key and topic configuration
5. **Review error messages** - They usually point to the issue

---

**Happy Testing! 🚀**
