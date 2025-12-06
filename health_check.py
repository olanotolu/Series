#!/usr/bin/env python3
"""
Simple health check endpoint for Series consumer.
Can be used by Shipyard or other platforms to verify the service is running.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

def check_health():
    """Check if all required services are accessible."""
    issues = []
    
    # Check environment variables
    required_vars = [
        "KAFKA_BOOTSTRAP_SERVERS",
        "SUPABASE_URL",
        "HF_TOKEN",
        "ELEVENLABS_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "S3_AUDIO_BUCKET"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        issues.append(f"Missing env vars: {', '.join(missing_vars)}")
    
    # Check if ffmpeg is available
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              timeout=2)
        if result.returncode != 0:
            issues.append("ffmpeg not working")
    except Exception as e:
        issues.append(f"ffmpeg check failed: {e}")
    
    # Check Python dependencies
    try:
        import aiohttp
        import aiokafka
        import supabase
        import boto3
        import huggingface_hub
    except ImportError as e:
        issues.append(f"Missing dependency: {e}")
    
    if issues:
        print(f"❌ Health check failed: {'; '.join(issues)}")
        sys.exit(1)
    else:
        print("✅ Health check passed")
        sys.exit(0)

if __name__ == "__main__":
    check_health()

