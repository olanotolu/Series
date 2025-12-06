#!/usr/bin/env python3
"""Simple test of LLM integration"""

import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv('HF_TOKEN', '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')

print("🧪 Testing LLM Integration...")
print("=" * 60)

try:
    from transformers import Qwen2_5OmniForConditionalGeneration, AutoProcessor
    import torch
    print("✅ transformers imported successfully")
except ImportError as e:
    print(f"❌ transformers not available: {e}")
    exit(1)

try:
    print("\n🤖 Loading Qwen2.5-Omni-7B model...")
    print("   This may take a few minutes...")
    
    model_name = "Qwen/Qwen2.5-Omni-7B"
    processor = AutoProcessor.from_pretrained(
        model_name,
        token=HF_TOKEN
    )
    print("✅ Processor loaded")
    
    model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=HF_TOKEN
    )
    print("✅ Model loaded")
    
    model.disable_talker()
    print("✅ Audio output disabled")
    
    # Test generation
    print("\n💬 Testing generation...")
    conversation = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant. Give concise, friendly responses."}],
        },
        {
            "role": "user",
            "content": "What is 2+2?"
        }
    ]
    
    text_input = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    inputs = processor(text=text_input, return_tensors="pt")
    inputs = inputs.to(model.device)
    
    print("   Generating response...")
    with torch.no_grad():
        text_ids = model.generate(
            **inputs,
            max_new_tokens=50,
            return_audio=False,
            do_sample=True,
            temperature=0.7
        )
    
    response = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    print(f"\n✅ LLM Response:")
    print(f"   {response}")
    print("\n🎉 LLM integration working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

