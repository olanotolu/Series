#!/bin/bash
# Quick deployment script for Series consumer

set -e

echo "🚀 Deploying Series Consumer..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Make sure to set environment variables in Shipyard dashboard.${NC}"
else
    echo -e "${GREEN}✅ Found .env file${NC}"
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -t series-consumer:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Test the image locally (optional)
read -p "Test the image locally? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧪 Testing Docker image..."
    if [ -f .env ]; then
        docker run --env-file .env --rm series-consumer:latest &
        TEST_PID=$!
        sleep 5
        kill $TEST_PID 2>/dev/null || true
        echo -e "${GREEN}✅ Test completed${NC}"
    else
        echo -e "${YELLOW}⚠️  Skipping test (no .env file)${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Ready to deploy!${NC}"
echo ""
echo "Next steps:"
echo "1. Push to your Git repository"
echo "2. Connect repository to Shipyard"
echo "3. Set environment variables in Shipyard dashboard"
echo "4. Deploy using shipyard.yaml configuration"
echo ""
echo "Or push to Docker registry:"
echo "  docker tag series-consumer:latest your-registry/series-consumer:latest"
echo "  docker push your-registry/series-consumer:latest"

