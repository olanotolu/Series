#!/bin/bash
# Lambda Deployment Script
# Packages and deploys Lambda functions for audio conversion

set -e

echo "🚀 Deploying Lambda Functions for Audio Processing"

# Configuration
REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME_OPUS_WAV="series-audio-opus-to-wav"
FUNCTION_NAME_WAV_M4A="series-audio-wav-to-m4a"
S3_BUCKET=${S3_AUDIO_BUCKET:-series-audio-files}
LAYER_NAME="ffmpeg-layer"

# Create deployment package directory
mkdir -p lambda_packages
cd lambda_packages

echo "📦 Creating deployment packages..."

# Package opus_to_wav Lambda
echo "   Packaging ${FUNCTION_NAME_OPUS_WAV}..."
mkdir -p ${FUNCTION_NAME_OPUS_WAV}
cp ../lambda_audio_converter.py ${FUNCTION_NAME_OPUS_WAV}/lambda_function.py
cp ../aws_audio_storage.py ${FUNCTION_NAME_OPUS_WAV}/

# Install dependencies
pip install -r ../requirements_lambda.txt -t ${FUNCTION_NAME_OPUS_WAV}/ --quiet

# Create zip
cd ${FUNCTION_NAME_OPUS_WAV}
zip -r ../${FUNCTION_NAME_OPUS_WAV}.zip . -q
cd ..

# Package wav_to_m4a Lambda
echo "   Packaging ${FUNCTION_NAME_WAV_M4A}..."
mkdir -p ${FUNCTION_NAME_WAV_M4A}
cp ../lambda_wav_to_m4a.py ${FUNCTION_NAME_WAV_M4A}/lambda_function.py
cp ../aws_audio_storage.py ${FUNCTION_NAME_WAV_M4A}/

# Install dependencies
pip install -r ../requirements_lambda.txt -t ${FUNCTION_NAME_WAV_M4A}/ --quiet

# Create zip
cd ${FUNCTION_NAME_WAV_M4A}
zip -r ../${FUNCTION_NAME_WAV_M4A}.zip . -q
cd ..

echo "✅ Packages created:"
echo "   - ${FUNCTION_NAME_OPUS_WAV}.zip"
echo "   - ${FUNCTION_NAME_WAV_M4A}.zip"

echo ""
echo "📝 Next steps:"
echo "   1. Create Lambda functions in AWS Console or using AWS CLI:"
echo "      aws lambda create-function \\"
echo "        --function-name ${FUNCTION_NAME_OPUS_WAV} \\"
echo "        --runtime python3.11 \\"
echo "        --role <IAM_ROLE_ARN> \\"
echo "        --handler lambda_function.lambda_handler \\"
echo "        --zip-file fileb://${FUNCTION_NAME_OPUS_WAV}.zip \\"
echo "        --timeout 300 \\"
echo "        --memory-size 512"
echo ""
echo "   2. Attach ffmpeg layer (search for 'ffmpeg' in AWS Lambda layers)"
echo "   3. Set environment variables:"
echo "      - S3_AUDIO_BUCKET=${S3_BUCKET}"
echo ""
echo "   4. Repeat for ${FUNCTION_NAME_WAV_M4A}"
echo ""
echo "   Or use AWS SAM/Serverless Framework for easier deployment"

cd ..

