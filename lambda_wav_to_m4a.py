#!/usr/bin/env python3
"""
Lambda Function: WAV to M4A Converter

Converts WAV audio files stored in S3 to M4A (AAC) format.
Requires ffmpeg Lambda layer.
"""

import json
import os
import subprocess
import tempfile
import boto3
from aws_audio_storage import download_from_s3_bytes, upload_to_s3

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda handler for WAV to M4A conversion.
    
    Event format:
    {
        "bucket": "series-audio-files",
        "wav_key": "tts_response_20251206_010000_123.wav",
        "output_key": "tts_response_20251206_010000_123.m4a" (optional)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "bucket": "series-audio-files",
            "m4a_key": "tts_response_20251206_010000_123.m4a",
            "success": true
        }
    }
    """
    try:
        bucket = event.get('bucket')
        wav_key = event.get('wav_key')
        
        if not bucket or not wav_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: bucket, wav_key'
                })
            }
        
        # Generate output key if not provided
        output_key = event.get('output_key')
        if not output_key:
            output_key = wav_key.replace('.wav', '.m4a')
        
        print(f"Converting WAV to M4A: s3://{bucket}/{wav_key}")
        
        # Download WAV from S3
        wav_data = download_from_s3_bytes(bucket, wav_key)
        if not wav_data:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to download WAV file from S3'
                })
            }
        
        # Save WAV to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav.write(wav_data)
            temp_wav_path = temp_wav.name
        
        # Convert WAV to M4A using ffmpeg
        temp_m4a = tempfile.NamedTemporaryFile(suffix='.m4a', delete=False)
        temp_m4a_path = temp_m4a.name
        temp_m4a.close()
        
        try:
            subprocess.run([
                '/opt/bin/ffmpeg', '-y',  # ffmpeg in Lambda layer
                '-i', temp_wav_path,
                '-c:a', 'aac',
                '-b:a', '48k',
                temp_m4a_path
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Try system ffmpeg as fallback
            subprocess.run([
                'ffmpeg', '-y',
                '-i', temp_wav_path,
                '-c:a', 'aac',
                '-b:a', '48k',
                temp_m4a_path
            ], check=True, capture_output=True)
        
        # Read M4A file
        with open(temp_m4a_path, 'rb') as f:
            m4a_data = f.read()
        
        # Upload M4A to S3
        success = upload_to_s3(bucket, output_key, m4a_data, 'audio/m4a')
        
        # Cleanup temp files
        os.unlink(temp_wav_path)
        os.unlink(temp_m4a_path)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'bucket': bucket,
                    'm4a_key': output_key,
                    'success': True
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to upload M4A to S3'
                })
            }
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

