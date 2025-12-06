# LLM Integration - Qwen2.5-Omni-7B

## Overview

We've integrated [Qwen2.5-Omni-7B](https://huggingface.co/Qwen/Qwen2.5-Omni-7B) from Hugging Face to provide intelligent text responses instead of simple echo.

## Setup

### 1. Install Dependencies
```bash
pip install transformers torch accelerate sentencepiece
```

### 2. Environment Variables
The HF_TOKEN is already added to `.env`:
```
HF_TOKEN=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
```

### 3. Model Loading
- Model loads automatically on first use (lazy loading)
- First load may take a few minutes
- Model is cached after first load
- Audio output is disabled (text-only) to save memory

## How It Works

1. **Text Message Received** → Consumer processes it
2. **LLM Processing** → Qwen2.5-Omni generates intelligent response
3. **Response Sent** → User receives LLM-generated reply

## Features

- ✅ Intelligent text responses (not just echo)
- ✅ Lazy loading (only loads when needed)
- ✅ Fallback to echo if LLM fails
- ✅ Memory efficient (audio output disabled)
- ✅ Error handling with graceful fallback

## Usage

Just run the consumer normally:
```bash
python consumer.py
```

The LLM will automatically:
- Load on first text message
- Generate intelligent responses
- Handle errors gracefully

## Model Details

- **Model**: Qwen2.5-Omni-7B
- **Capabilities**: Text, Audio, Image, Video (we use text-only)
- **Size**: ~11B parameters
- **License**: Apache 2.0
- **Source**: [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-Omni-7B)

## Next Steps

- [ ] Add audio input processing (voice memo → text → LLM)
- [ ] Add conversation memory/context
- [ ] Fine-tune for specific use cases
- [ ] Add streaming responses

