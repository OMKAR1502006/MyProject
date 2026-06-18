"""
Verify Gemini API connection by initializing the client and sending a simple 'Hello' prompt.
Run from project root: python scripts/test_gemini.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

# Initialize Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgroSathiDjango.settings')
import django
django.setup()

from agro.services.chat import _gemini_key, _call_gemini

def main():
    print("=== Gemini API Connection Test ===")
    
    # 1. Validate key exists
    api_key = _gemini_key()
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is not set in your .env file or environment.")
        print("Please add GEMINI_API_KEY=YOUR_KEY to the .env file.")
        sys.exit(1)
        
    print(f"[OK] GEMINI_API_KEY found (length: {len(api_key)})")
    
    # 2. Validate client initialization and request execution
    system_prompt = "You are a helpful assistant. Keep your response extremely brief."
    test_message = "Hello"
    
    print(f"Sending test prompt: '{test_message}'...")
    try:
        reply = _call_gemini(
            message=test_message,
            system_prompt=system_prompt,
            history=[]
        )
        print("\n[SUCCESS] Received response from Gemini API:")
        print(f"Response: '{reply}'\n")
        print("[OK] Gemini integration is fully functional!")
    except Exception as exc:
        print("\n[ERROR] Gemini API request failed!")
        print(f"Error details: {exc}")
        print("Please check your API key, internet connection, and billing status on Google AI Studio.")
        sys.exit(1)

if __name__ == '__main__':
    main()
