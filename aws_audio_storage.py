#!/usr/bin/env python3
"""
AWS S3 Audio Storage Utilities

Handles all S3 operations for audio file storage:
- Upload audio files to S3
- Download audio files from S3
- Generate S3 URLs
- Delete old files
"""

import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Optional, BinaryIO
import tempfile

# Initialize S3 client (uses default credential chain: AWS CLI, env vars, IAM roles)
s3_client = None

def get_s3_client():
    """Get or create S3 client using default credential chain."""
    global s3_client
    if s3_client is None:
        region = os.getenv('AWS_REGION', 'us-east-1')
        s3_client = boto3.client('s3', region_name=region)
    return s3_client


def generate_s3_key(file_type: str, sender: str, timestamp: str, message_id: str, extension: str) -> str:
    """
    Generate S3 key following the same pattern as local files.
    
    Args:
        file_type: 'voice_memo' or 'tts_response'
        sender: Phone number (sanitized)
        timestamp: Timestamp string
        message_id: Message ID
        extension: File extension (opus, wav, m4a)
    
    Returns:
        S3 key string
    """
    safe_sender = sender.replace("+", "").replace("-", "")
    return f"{file_type}_{safe_sender}_{timestamp}_{message_id}.{extension}"


def upload_to_s3(bucket: str, key: str, data: bytes, content_type: str = None) -> bool:
    """
    Upload audio data to S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        data: Audio file bytes
        content_type: MIME type (e.g., 'audio/opus', 'audio/wav', 'audio/m4a')
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_s3_client()
        
        # Set content type based on extension if not provided
        if content_type is None:
            if key.endswith('.opus'):
                content_type = 'audio/ogg'  # Opus is typically in OGG container
            elif key.endswith('.wav'):
                content_type = 'audio/wav'
            elif key.endswith('.m4a'):
                content_type = 'audio/m4a'
            elif key.endswith('.mp3'):
                content_type = 'audio/mpeg'
            else:
                content_type = 'application/octet-stream'
        
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        
        print(f"   ✅ Uploaded to S3: s3://{bucket}/{key} ({len(data):,} bytes)")
        return True
        
    except ClientError as e:
        print(f"   ❌ S3 upload error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ S3 upload error: {e}")
        return False


def download_from_s3(bucket: str, key: str, local_path: str = None) -> Optional[str]:
    """
    Download audio file from S3 to local temporary file.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Optional local file path (creates temp file if None)
    
    Returns:
        Path to local file, or None if error
    """
    try:
        client = get_s3_client()
        
        if local_path is None:
            # Create temporary file
            suffix = os.path.splitext(key)[1] or '.tmp'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            local_path = temp_file.name
            temp_file.close()
        
        client.download_file(bucket, key, local_path)
        
        print(f"   ✅ Downloaded from S3: s3://{bucket}/{key} → {local_path}")
        return local_path
        
    except ClientError as e:
        print(f"   ❌ S3 download error: {e}")
        return None
    except Exception as e:
        print(f"   ❌ S3 download error: {e}")
        return None


def download_from_s3_bytes(bucket: str, key: str) -> Optional[bytes]:
    """
    Download audio file from S3 as bytes (in-memory).
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        File bytes, or None if error
    """
    try:
        client = get_s3_client()
        response = client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read()
        
        print(f"   ✅ Downloaded from S3 (bytes): s3://{bucket}/{key} ({len(data):,} bytes)")
        return data
        
    except ClientError as e:
        print(f"   ❌ S3 download error: {e}")
        return None
    except Exception as e:
        print(f"   ❌ S3 download error: {e}")
        return None


def get_s3_url(bucket: str, key: str, expires_in: int = 3600) -> Optional[str]:
    """
    Generate presigned URL for S3 object (for temporary access).
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expires_in: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned URL, or None if error
    """
    try:
        client = get_s3_client()
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        return url
        
    except ClientError as e:
        print(f"   ❌ S3 URL generation error: {e}")
        return None
    except Exception as e:
        print(f"   ❌ S3 URL generation error: {e}")
        return None


def delete_from_s3(bucket: str, key: str) -> bool:
    """
    Delete audio file from S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_s3_client()
        client.delete_object(Bucket=bucket, Key=key)
        
        print(f"   ✅ Deleted from S3: s3://{bucket}/{key}")
        return True
        
    except ClientError as e:
        print(f"   ❌ S3 delete error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ S3 delete error: {e}")
        return False


def check_s3_bucket_exists(bucket: str) -> bool:
    """
    Check if S3 bucket exists and is accessible.
    
    Args:
        bucket: S3 bucket name
    
    Returns:
        True if bucket exists and is accessible, False otherwise
    """
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"   ⚠️  S3 bucket '{bucket}' does not exist")
        else:
            print(f"   ⚠️  S3 bucket access error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  S3 bucket check error: {e}")
        return False


def create_s3_bucket(bucket: str, region: str = 'us-east-1') -> bool:
    """
    Create S3 bucket if it doesn't exist.
    
    Args:
        bucket: S3 bucket name
        region: AWS region (default: us-east-1)
    
    Returns:
        True if bucket exists or was created, False otherwise
    """
    try:
        client = get_s3_client()
        
        # Check if bucket exists
        if check_s3_bucket_exists(bucket):
            print(f"   ✅ S3 bucket '{bucket}' already exists")
            return True
        
        # Create bucket
        if region == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            client.create_bucket(Bucket=bucket)
        else:
            client.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        print(f"   ✅ Created S3 bucket: {bucket} in region {region}")
        return True
        
    except ClientError as e:
        print(f"   ❌ S3 bucket creation error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ S3 bucket creation error: {e}")
        return False

