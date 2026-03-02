
import sys
import os

# Add project root to path
sys.path.append("c:/Users/Gustavo/bomtempo-dashboard")

from bomtempo.core.ai_client import ai_client

def test_api():
    print("Testing Kimi AI API...")
    try:
        response = ai_client.query([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, clear the path!"}
        ])
        print(f"Response: {response}")
        if response and "error" not in response.lower():
            print("SUCCESS: API connected.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_api()
