# Deployment Options for Shipyard

## Option 1: Git Integration (Easiest - Recommended) ✅

Shipyard can build directly from your Git repository. No Docker registry needed!

**Steps:**
1. Push your code to GitHub/GitLab
2. In Shipyard dashboard:
   - Create new application
   - Connect your Git repository
   - Shipyard will auto-detect `Dockerfile`
   - Add environment variables
   - Deploy!

**Advantages:**
- ✅ No Docker registry needed
- ✅ Automatic builds on git push
- ✅ Easy to update (just push code)
- ✅ Free (if using GitHub/GitLab)

## Option 2: Docker Hub (If you want registry)

If you want to use Docker Hub:

```bash
# 1. Login to Docker Hub
docker login

# 2. Tag with your Docker Hub username
docker tag series-consumer:latest YOUR_DOCKERHUB_USERNAME/series-consumer:latest

# 3. Push
docker push YOUR_DOCKERHUB_USERNAME/series-consumer:latest

# 4. In Shipyard, deploy from Docker Hub registry
```

## Option 3: GitHub Container Registry (ghcr.io)

```bash
# 1. Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 2. Tag
docker tag series-consumer:latest ghcr.io/YOUR_GITHUB_USERNAME/series-consumer:latest

# 3. Push
docker push ghcr.io/YOUR_GITHUB_USERNAME/series-consumer:latest
```

## Option 4: AWS ECR (If using AWS)

```bash
# 1. Get login command from AWS
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 2. Create repository (if doesn't exist)
aws ecr create-repository --repository-name series-consumer --region us-east-1

# 3. Tag
docker tag series-consumer:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/series-consumer:latest

# 4. Push
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/series-consumer:latest
```

## Recommendation

**Use Option 1 (Git Integration)** - It's the simplest and Shipyard handles everything automatically!

