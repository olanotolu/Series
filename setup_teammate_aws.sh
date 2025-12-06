#!/bin/bash

# Setup AWS Access for Teammate
# This script helps you create an IAM user and grant access to Series project resources

set -e

echo "🚀 Setting Up AWS Access for Teammate"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured."
    echo "   Please run: aws configure"
    exit 1
fi

echo "✅ AWS CLI found and configured"
echo ""

# Get configuration
read -p "Enter teammate's username (e.g., series-teammate): " USERNAME
read -p "Enter S3 bucket name (default: series-audio-files): " BUCKET_NAME
BUCKET_NAME=${BUCKET_NAME:-series-audio-files}

read -p "Enter AWS region (default: us-east-1): " REGION
REGION=${REGION:-us-east-1}

echo ""
echo "📋 Configuration:"
echo "   Username: $USERNAME"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   Region: $REGION"
echo ""

read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

# Get account ID
echo "🔍 Getting AWS account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   Account ID: $ACCOUNT_ID"
echo ""

# Create IAM user
echo "👤 Creating IAM user: $USERNAME..."
if aws iam get-user --user-name "$USERNAME" &> /dev/null; then
    echo "   ⚠️  User already exists, skipping creation"
else
    aws iam create-user --user-name "$USERNAME"
    echo "   ✅ User created"
fi
echo ""

# Create policy document
echo "📝 Creating IAM policy..."
POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::$BUCKET_NAME",
                "arn:aws:s3:::$BUCKET_NAME/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation"
            ],
            "Resource": "*"
        }
    ]
}
EOF
)

POLICY_NAME="SeriesAudioAccess-$USERNAME"

# Check if policy exists
if aws iam get-policy --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" &> /dev/null; then
    echo "   ⚠️  Policy already exists, updating..."
    # Create new policy version
    echo "$POLICY_DOC" > /tmp/policy.json
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" \
        --policy-document file:///tmp/policy.json \
        --set-as-default
    rm /tmp/policy.json
    echo "   ✅ Policy updated"
else
    # Create new policy
    echo "$POLICY_DOC" > /tmp/policy.json
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/policy.json
    rm /tmp/policy.json
    echo "   ✅ Policy created"
fi
echo ""

# Attach policy to user
echo "🔗 Attaching policy to user..."
aws iam attach-user-policy \
    --user-name "$USERNAME" \
    --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
echo "   ✅ Policy attached"
echo ""

# Create access keys
echo "🔑 Creating access keys..."
KEY_OUTPUT=$(aws iam create-access-key --user-name "$USERNAME")
ACCESS_KEY_ID=$(echo "$KEY_OUTPUT" | grep -o '"AccessKeyId": "[^"]*' | cut -d'"' -f4)
SECRET_ACCESS_KEY=$(echo "$KEY_OUTPUT" | grep -o '"SecretAccessKey": "[^"]*' | cut -d'"' -f4)

echo ""
echo "✅ Setup Complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Share these credentials with your teammate (use encrypted channel!):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID"
echo "AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY"
echo "AWS_REGION=$REGION"
echo "S3_AUDIO_BUCKET=$BUCKET_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Teammate should add these to their .env file:"
echo ""
echo "   AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID"
echo "   AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY"
echo "   AWS_REGION=$REGION"
echo "   S3_AUDIO_BUCKET=$BUCKET_NAME"
echo "   USE_S3_STORAGE=true"
echo ""
echo "⚠️  IMPORTANT: Save these credentials securely. The secret key won't be shown again!"
echo ""

