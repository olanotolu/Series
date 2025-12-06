# 🚀 Next Steps - Series Deployment Checklist

## ✅ What's Done

- [x] Fixed schema issues (created `fix_schema_issues.sql`)
- [x] Created deployment files (Dockerfile, shipyard.yaml, DEPLOYMENT.md)
- [x] Fixed contextual fallback system for LLM responses
- [x] Fixed Kafka offset checking bug
- [x] Created health check script

## 📋 Pre-Deployment Checklist

### 1. **Fix Supabase Schema** ⚠️ IMPORTANT

Run the schema fix script in Supabase:

1. Go to Supabase Dashboard → SQL Editor
2. Open `migrations/fix_schema_issues.sql`
3. Copy and paste the entire script
4. Run it
5. Verify success message: "Schema fixes applied successfully! ✅"

**This adds:**
- UNIQUE constraints (prevents duplicate data)
- Missing `last_activity_at` column
- Health score function
- Performance indexes

### 2. **Verify Environment Variables**

Make sure you have all these set (in `.env` or Shipyard dashboard):

```bash
# Required for deployment
KAFKA_BOOTSTRAP_SERVERS=...
KAFKA_TOPIC_NAME=...
KAFKA_GROUP_ID=...
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
HF_TOKEN=...
ELEVENLABS_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_AUDIO_BUCKET=...
SERIES_API_URL=...
SERIES_API_KEY=...
SENDER_NUMBER=...
```

### 3. **Test Docker Build Locally** (Optional but Recommended)

```bash
# Build the image
docker build -t series-consumer:latest .

# Test run (if you have .env file)
docker run --env-file .env series-consumer:latest
```

This verifies:
- ✅ Dockerfile works
- ✅ All dependencies install
- ✅ Application starts correctly

### 4. **Deploy to Shipyard**

**Option A: Git Integration (Recommended)**
1. Push your code to GitHub/GitLab
2. Connect repository to Shipyard
3. Shipyard will auto-detect `Dockerfile`
4. Add environment variables in Shipyard dashboard
5. Deploy!

**Option B: Docker Registry**
```bash
# Tag and push
docker tag series-consumer:latest your-registry/series-consumer:latest
docker push your-registry/series-consumer:latest

# Then deploy from registry in Shipyard
```

### 5. **Verify Deployment**

After deployment, check:

- [ ] **Logs** - Should see "✅ Kafka Consumer started!"
- [ ] **Health checks** - Should pass (runs every 30s)
- [ ] **Test message** - Send a test message and verify processing
- [ ] **Supabase** - Verify messages are being stored
- [ ] **S3** - Verify audio files are being uploaded

## 🎯 Quick Start Commands

```bash
# 1. Fix schema (run in Supabase SQL Editor)
# Open: migrations/fix_schema_issues.sql

# 2. Test Docker build locally
./deploy.sh

# 3. Deploy to Shipyard
# Follow DEPLOYMENT.md guide
```

## 📚 Documentation

- **Deployment Guide**: `DEPLOYMENT.md`
- **Schema Review**: `SCHEMA_REVIEW.md`
- **Schema Fix Script**: `migrations/fix_schema_issues.sql`
- **Shipyard Config**: `shipyard.yaml`

## 🐛 Troubleshooting

If something goes wrong:

1. **Check logs** in Shipyard dashboard
2. **Verify environment variables** are set correctly
3. **Check Supabase** - ensure schema fixes ran
4. **Check Kafka** - ensure connection is accessible
5. **Review** `DEPLOYMENT.md` troubleshooting section

## 🎉 You're Ready!

Once you've:
1. ✅ Fixed the schema
2. ✅ Set environment variables
3. ✅ Deployed to Shipyard
4. ✅ Verified it's working

**You're live!** 🚀

---

**Need help?** Check the documentation files or review the error logs in Shipyard.

