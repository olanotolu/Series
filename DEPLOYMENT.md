# Deployment Guide for Series

This guide will help you deploy the Series consumer to Shipyard (or any containerized platform).

## Prerequisites

1. **Docker** installed locally (for testing)
2. **Shipyard account** (or similar platform)
3. **Environment variables** configured
4. **Database migrations** run on Supabase
5. **AWS S3 bucket** created for audio storage

## Step 1: Prepare Environment Variables

Create a `.env.production` file with all required variables:

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your-kafka-servers
KAFKA_TOPIC_NAME=your-topic-name
KAFKA_GROUP_ID=team-cg-your-group-id

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Hugging Face
HF_TOKEN=hf_your-token-here

# ElevenLabs
ELEVENLABS_API_KEY=your-elevenlabs-key

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_AUDIO_BUCKET=series-audio-files

# Series API
SERIES_API_URL=https://api.linqapp.com
SERIES_API_KEY=your-api-key
SENDER_NUMBER=+1234567890
```

## Step 2: Test Docker Build Locally

```bash
# Build the Docker image
docker build -t series-consumer:latest .

# Test run locally (with .env file)
docker run --env-file .env series-consumer:latest
```

## Step 3: Deploy to Shipyard

### Option A: Using Shipyard Dashboard

1. **Create a new application** in Shipyard
2. **Connect your Git repository** (GitHub/GitLab)
3. **Select Dockerfile** as build method
4. **Add environment variables** from Step 1
5. **Deploy!**

### Option B: Using Shipyard CLI

```bash
# Install Shipyard CLI (if available)
# shipyard login

# Deploy
shipyard deploy --config shipyard.yaml
```

### Option C: Using Docker Registry

```bash
# Tag and push to registry
docker tag series-consumer:latest your-registry/series-consumer:latest
docker push your-registry/series-consumer:latest

# Then deploy from registry in Shipyard dashboard
```

## Step 4: Verify Deployment

1. **Check logs** in Shipyard dashboard
2. **Verify Kafka connection** - should see "✅ Kafka Consumer started!"
3. **Test with a message** - send a test message and verify processing
4. **Check Supabase** - verify messages are being stored
5. **Check S3** - verify audio files are being uploaded

## Step 5: Monitor and Scale

- **Monitor CPU/Memory** usage
- **Check error logs** regularly
- **Scale up** if processing is slow
- **Set up alerts** for failures

## Troubleshooting

### Consumer Not Starting

- Check Kafka connection string
- Verify environment variables are set
- Check network connectivity

### Audio Processing Fails

- Verify ffmpeg is installed (included in Dockerfile)
- Check S3 credentials and bucket permissions
- Verify ElevenLabs API key is valid

### Database Errors

- Run migrations on Supabase
- Verify service role key has proper permissions
- Check RLS policies

### LLM Not Responding

- Verify HF_TOKEN is valid and not expired
- Check API rate limits
- Monitor Hugging Face API status

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] S3 bucket created and accessible
- [ ] Kafka topics created
- [ ] Health checks configured
- [ ] Logging set up
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Backup strategy in place

## Next Steps

1. **Set up CI/CD** - Automate deployments
2. **Add monitoring** - Set up metrics and dashboards
3. **Configure auto-scaling** - Based on message volume
4. **Set up staging environment** - Test before production

## Support

For issues or questions:
- Check logs in Shipyard dashboard
- Review error messages in consumer output
- Verify all environment variables are set correctly

