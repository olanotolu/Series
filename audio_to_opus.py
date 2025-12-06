#!/usr/bin/env python3
"""
Audio to Opus Converter

Converts audio files to Opus format and outputs as JSON with base64-encoded data.
Opus is the best modern codec for JSON - 88% smaller than PCM, 76% smaller than μ-law.
"""

import argparse
import sys
import json
import base64
import subprocess
import tempfile
import os
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub not installed.")
    print("Install with: pip install pydub")
    sys.exit(1)


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_to_opus(input_file: str, output_file: str = None, 
                    sample_rate: int = 16000, bitrate: str = '32k'):
    """
    Convert audio file to Opus format and output as JSON.
    
    Args:
        input_file: Path to input audio file
        output_file: Path to output JSON file (optional, prints to stdout if not provided)
        sample_rate: Target sample rate (default: 16000 Hz for wideband)
        bitrate: Opus bitrate (default: 32k)
    """
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install with: brew install ffmpeg (macOS)", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load audio file
        print(f"Loading: {input_file}", file=sys.stderr)
        audio = AudioSegment.from_file(input_file)
        
        # Convert to target format
        audio = audio.set_frame_rate(sample_rate)
        audio = audio.set_channels(1)  # mono
        audio = audio.set_sample_width(2)  # 16-bit
        
        duration = len(audio) / 1000.0
        
        # Convert to Opus using ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            audio.export(temp_wav_path, format='wav')
        
        with tempfile.NamedTemporaryFile(suffix='.opus', delete=False) as temp_opus:
            temp_opus_path = temp_opus.name
        
        # Convert to Opus
        cmd = [
            'ffmpeg', '-i', temp_wav_path,
            '-c:a', 'libopus',
            '-b:a', bitrate,
            '-ar', str(sample_rate),
            '-ac', '1',
            '-y',
            temp_opus_path
        ]
        
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        # Read Opus data
        with open(temp_opus_path, 'rb') as f:
            opus_data = f.read()
        
        # Cleanup
        os.unlink(temp_wav_path)
        os.unlink(temp_opus_path)
        
        # Encode to base64
        opus_base64 = base64.b64encode(opus_data).decode('ascii')
        
        # Create JSON structure
        json_data = {
            "chat": {
                "phone_numbers": ["+13343284472"]
            },
            "message": {
                "text": "Hello!",
                "audio": {
                    "format": "opus",
                    "sample_rate": sample_rate,
                    "channels": 1,
                    "duration": round(duration, 3),
                    "bitrate": bitrate,
                    "data": opus_base64
                }
            },
            "send_from": "+13175269229"
        }
        
        json_str = json.dumps(json_data, indent=2)
        
        # Output
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_str)
            print(f"Saved: {output_file} ({len(json_str):,} bytes)", file=sys.stderr)
        else:
            print(json_str)
        
        print(f"Opus size: {len(opus_data):,} bytes ({len(opus_data)/1024:.2f} KB)", file=sys.stderr)
        print(f"JSON size: {len(json_str):,} bytes ({len(json_str)/1024:.2f} KB)", file=sys.stderr)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert audio to Opus format and output as JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input_file',
        help='Input audio file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Output JSON file (default: stdout)'
    )
    
    parser.add_argument(
        '-r', '--sample-rate',
        type=int,
        default=16000,
        dest='sample_rate',
        help='Sample rate in Hz (default: 16000)'
    )
    
    parser.add_argument(
        '-b', '--bitrate',
        default='32k',
        help='Opus bitrate (default: 32k)'
    )
    
    args = parser.parse_args()
    
    if not Path(args.input_file).exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    convert_to_opus(args.input_file, args.output_file, args.sample_rate, args.bitrate)


if __name__ == '__main__':
    main()

