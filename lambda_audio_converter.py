#!/usr/bin/env python3
"""
Lambda Function: OPUS to WAV Converter

Converts OPUS audio files stored in S3 to WAV format.
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
    Lambda handler for OPUS to WAV conversion.
    
    Event format:
    {
        "bucket": "series-audio-files",
        "opus_key": "voice_memo_123_20251206_010000_123.opus",
        "output_key": "voice_memo_123_20251206_010000_123.wav" (optional)
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "bucket": "series-audio-files",
            "wav_key": "voice_memo_123_20251206_010000_123.wav",
            "success": true
        }
    }
    """
    try:
        bucket = event.get('bucket')
        opus_key = event.get('opus_key')
        
        if not bucket or not opus_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: bucket, opus_key'
                })
            }
        
        # Generate output key if not provided
        output_key = event.get('output_key')
        if not output_key:
            output_key = opus_key.replace('.opus', '.wav')
        
        print(f"Converting OPUS to WAV: s3://{bucket}/{opus_key}")
        
        # Download OPUS from S3
        opus_data = download_from_s3_bytes(bucket, opus_key)
        if not opus_data:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to download OPUS file from S3'
                })
            }
        
        # Save OPUS to temp file
        with tempfile.NamedTemporaryFile(suffix='.opus', delete=False) as temp_opus:
            temp_opus.write(opus_data)
            temp_opus_path = temp_opus.name
        
        # Convert OPUS to WAV using ffmpeg
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        try:
            subprocess.run([
                '/opt/bin/ffmpeg', '-y',  # ffmpeg in Lambda layer
                '-i', temp_opus_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # mono
                '-f', 'wav',
                temp_wav_path
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Try system ffmpeg as fallback
            subprocess.run([
                'ffmpeg', '-y',
                '-i', temp_opus_path,
                '-ar', '16000',
                '-ac', '1',
                '-f', 'wav',
                temp_wav_path
            ], check=True, capture_output=True)
        
        # Read WAV file
        with open(temp_wav_path, 'rb') as f:
            wav_data = f.read()
        
        # Upload WAV to S3
        success = upload_to_s3(bucket, output_key, wav_data, 'audio/wav')
        
        # Cleanup temp files
        os.unlink(temp_opus_path)
        os.unlink(temp_wav_path)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'bucket': bucket,
                    'wav_key': output_key,
                    'success': True
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to upload WAV to S3'
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

