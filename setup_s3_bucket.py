#!/usr/bin/env python3
"""
Setup S3 Bucket for Audio Storage

Creates S3 bucket and configures it for audio file storage.
Run this once to set up the infrastructure.
"""

import os
import sys
from dotenv import load_dotenv
from aws_audio_storage import create_s3_bucket, check_s3_bucket_exists, get_s3_client

load_dotenv()

def setup_s3_bucket():
    """Create and configure S3 bucket for audio storage."""
    bucket_name = os.getenv('S3_AUDIO_BUCKET', 'series-audio-files')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    print(f"🚀 Setting up S3 bucket: {bucket_name}")
    print(f"   Region: {region}")
    
    # Check if bucket exists
    if check_s3_bucket_exists(bucket_name):
        print(f"✅ Bucket '{bucket_name}' already exists and is accessible")
        return True
    
    # Create bucket
    print(f"📦 Creating S3 bucket: {bucket_name}...")
    if create_s3_bucket(bucket_name, region):
        print(f"✅ S3 bucket '{bucket_name}' created successfully!")
        print(f"\n📝 Next steps:")
        print(f"   1. Bucket is ready to use")
        print(f"   2. Set USE_S3_STORAGE=true in .env to enable S3 storage")
        print(f"   3. Run your consumer - audio files will be stored in S3")
        return True
    else:
        print(f"❌ Failed to create S3 bucket")
        return False


if __name__ == '__main__':
    try:
        success = setup_s3_bucket()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

