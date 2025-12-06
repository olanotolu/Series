# 🚀 Quick Shipyard Deployment Guide

## ✅ Pre-Deployment Checklist

- [x] Code committed and pushed to GitHub
- [x] `docker-compose.yml` created
- [x] `Dockerfile` ready
- [x] `shipyard.yaml` configured

## 📋 Step-by-Step Deployment

### Step 1: In Shipyard Dashboard

1. **Click "Load latest commit"** button
   - This will refresh and pick up the new `docker-compose.yml` file
   - The "No Compose file found!" error should disappear

2. **Select the compose file**
   - You should now see `docker-compose.yml` available
   - Select it from the dropdown

3. **Click "Add environment variables"** (should be enabled now)

### Step 2: Add All Environment Variables

Add these variables in Shipyard (one by one):

**Kafka:**
```
KAFKA_BOOTSTRAP_SERVERS=your-kafka-servers
KAFKA_TOPIC_NAME=your-topic-name
KAFKA_GROUP_ID=team-cg-your-group-id
KAFKA_SASL_USERNAME=your-kafka-username
KAFKA_SASL_PASSWORD=your-kafka-password
```

**Supabase:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**Hugging Face:**
```
HF_TOKEN=hf_your-token-here
```

**ElevenLabs:**
```
ELEVENLABS_API_KEY=your-elevenlabs-key
```

**AWS S3:**
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_AUDIO_BUCKET=series-audio-files
```

**Series API:**
```
SERIES_API_URL=https://api.linqapp.com
SERIES_API_KEY=your-api-key
SENDER_NUMBER=+16463769330
```

### Step 3: Deploy!

1. **Review your configuration**
2. **Click "Deploy"** or "Save and Deploy"
3. **Wait for build** - Shipyard will:
   - Pull your code from GitHub
   - Build the Docker image
   - Start the container

### Step 4: Verify Deployment

1. **Check logs** in Shipyard dashboard
   - Look for: `✅ Kafka Consumer started!`
   - Look for: `✅ Connected to Supabase`
   - Look for: `🔄 Waiting for messages...`

2. **Test the system:**
   - Send a test message to your AI number
   - Verify it's processed correctly
   - Check Supabase for stored messages

## 🐛 Troubleshooting

### "No Compose file found!" still showing
- Make sure you clicked "Load latest commit"
- Verify `docker-compose.yml` is in your repository root
- Check that the file was pushed to GitHub

### Build fails
- Check Dockerfile syntax
- Verify all dependencies in `requirements.txt`
- Check build logs for specific errors

### Container starts but crashes
- Check environment variables are all set
- Verify Kafka connection string
- Check Supabase credentials
- Review logs for error messages

### Consumer not receiving messages
- Verify Kafka topic name matches
- Check Kafka group ID is correct
- Ensure Kafka credentials are valid
- Check network connectivity

## 📊 Monitoring

After deployment, monitor:
- **CPU/Memory usage** - Should be stable
- **Logs** - Should show message processing
- **Error rate** - Should be minimal
- **Message processing rate** - Should match incoming messages

## 🔄 Updates

To update after code changes:
1. Commit and push to GitHub
2. In Shipyard: Click "Redeploy" or "Deploy latest"
3. Shipyard will rebuild and restart automatically

## ✅ Success Indicators

You'll know it's working when you see:
- ✅ `Kafka Consumer started!`
- ✅ `Connected to Supabase`
- ✅ `Waiting for messages...`
- ✅ Messages being processed in logs
- ✅ No error messages

---

**Your code is ready! Just follow the steps above in the Shipyard dashboard.** 🚀

