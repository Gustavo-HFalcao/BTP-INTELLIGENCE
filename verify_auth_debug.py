
import sys
import os
from openai import OpenAI
import httpx

# Config
KEY_SK = "sk-RkswUuLAZlphrur4HJIbwV0elSjm9NI6jLuSNStFZuHaCY2Q"
KEY_AK = "ak-f8a8qq93k3wi11gkopji"
BASE_URL = "https://api.moonshot.cn/v1"

def test_client(api_key, name="Default"):
    print(f"\n--- Testing with {name} ---")
    print(f"Key: {api_key[:10]}...")
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    try:
        response = client.chat.completions.create(
             model="moonshot-v1-8k",
             messages=[{"role": "user", "content": "Hello"}],
             temperature=0.1
        )
        print("SUCCESS!")
        print(response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

def test_custom_header():
    print(f"\n--- Testing with Extra Headers (ID) ---")
    # Using httpx directly to debug headers
    headers = {
        "Authorization": f"Bearer {KEY_SK}",
        "X-App-ID": KEY_AK,
        "X-Access-Key": KEY_AK,
        "Moonshot-App-ID": KEY_AK
    }
    json_data = {
        "model": "moonshot-v1-8k",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    try:
        r = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=json_data)
        print(f"Status: {r.status_code}")
        print(r.text)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    # 1. Try SK with CN endpoint
    if test_client(KEY_SK, "Secret Key (sk-) @ .cn"):
        pass

    # 1b. Try SK with AI endpoint (Global) - Test Models
    global_url = "https://api.moonshot.ai/v1"
    print(f"\n--- Testing with Secret Key (sk-) @ {global_url} ---")
    client = OpenAI(api_key=KEY_SK, base_url=global_url)
    
    models_to_test = ["kimi-k2-turbo-preview", "kimi-latest", "moonshot-v1-auto"]
    
    for model in models_to_test:
        print(f"\nTesting model: {model}...")
        try:
            response = client.chat.completions.create(
                 model=model,
                 messages=[{"role": "user", "content": "Hello"}],
                 temperature=0.1
            )
            print("SUCCESS!")
            print(response.choices[0].message.content)
            break
        except Exception as e:
            print(f"Failed: {e}")

    # 2. Try AK (Just in case)
    if test_client(KEY_AK, "Access Key (ak-)"):
        pass

