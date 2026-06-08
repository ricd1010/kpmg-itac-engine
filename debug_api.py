import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

print(f"Testing Key: {api_key[:6]}...")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

try:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=5
    )
    print("✅ API Key is VALID!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ API Key Test FAILED: {str(e)}")
