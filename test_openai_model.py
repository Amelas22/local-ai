import asyncio
import os
from openai import AsyncOpenAI

async def test_model():
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    models = [
        'gpt-4.1-mini-2025-04-14',
        'gpt-4o-mini',
        'gpt-4o-mini-2024-07-18',
        'gpt-3.5-turbo'
    ]
    
    for model in models:
        try:
            print(f"Testing model: {model}")
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            print(f"✓ Model {model} works!")
            return model
        except Exception as e:
            print(f"✗ Model {model} failed: {str(e)}")
    
    return None

if __name__ == "__main__":
    working_model = asyncio.run(test_model())
    if working_model:
        print(f"\nWorking model found: {working_model}")
    else:
        print("\nNo working model found!")