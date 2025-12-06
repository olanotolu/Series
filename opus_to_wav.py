#!/usr/bin/env python3
"""
OPUS to WAV Converter

Converts OPUS audio (base64) to WAV format for STT processing.
Used for receiving voice memos from iMessage.
"""

import base64
import subprocess
import uuid
import os
import tempfile
from pathlib import Path


def opus_to_wav(base64_opus: str, output_file: str = None) -> str:
    """
    Convert OPUS base64 string to WAV file for STT processing.
    
    Args:
        base64_opus: Base64-encoded OPUS audio data
        output_file: Optional output WAV file path (auto-generated if None)
    
    Returns:
        Path to the WAV file
    """
    # Decode base64
    opus_data = base64.b64decode(base64_opus)
    
    # Create temporary files
    temp_opus = tempfile.NamedTemporaryFile(suffix='.opus', delete=False)
    temp_opus_path = temp_opus.name
    temp_opus.write(opus_data)
    temp_opus.close()
    
    # Generate output path
    if output_file is None:
        output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    
    # Convert OPUS to WAV using ffmpeg
    # 16kHz mono for optimal STT processing
    cmd = [
        'ffmpeg', '-y',
        '-i', temp_opus_path,
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',      # mono
        '-f', 'wav',
        output_file
    ]
    
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )
    
    # Cleanup temp opus file
    os.unlink(temp_opus_path)
    
    return output_file


def opus_to_wav_bytes(base64_opus: str) -> bytes:
    """
    Convert OPUS base64 string to WAV bytes (in-memory).
    
    Args:
        base64_opus: Base64-encoded OPUS audio data
    
    Returns:
        WAV file bytes
    """
    wav_file = opus_to_wav(base64_opus)
    with open(wav_file, 'rb') as f:
        wav_data = f.read()
    os.unlink(wav_file)  # Cleanup
    return wav_data


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: opus_to_wav.py <base64_opus_string> [output.wav]")
        sys.exit(1)
    
    base64_data = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    wav_path = opus_to_wav(base64_data, output)
    print(f"Converted to: {wav_path}")

