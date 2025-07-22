#!/usr/bin/env python3
"""Test script to verify Gemini API connectivity and functionality"""

import os
import sys
from google import genai
from google.genai import types

# Test Gemini API
def test_gemini_api():
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return False
    
    print(f"✓ API key found: {api_key[:8]}...")
    
    try:
        # Initialize client
        client = genai.Client(api_key=api_key)
        print("✓ Client initialized successfully")
        
        # Test simple query
        test_prompt = "Hello, can you respond with 'Gemini API is working'?"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=test_prompt
        )
        
        print(f"✓ API response received: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Full traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Gemini API connection...")
    success = test_gemini_api()
    sys.exit(0 if success else 1)