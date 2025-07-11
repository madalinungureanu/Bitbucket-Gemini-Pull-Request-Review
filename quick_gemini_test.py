#!/usr/bin/env python3
"""Quick test to show Gemini response for WordPress code"""

import os
from google import genai
from google.genai import types

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Simple WordPress code snippet for analysis
code_snippet = '''
function process_user_data() {
    $input = $_POST['data'];
    echo "Processing: " . $input;
    update_option('user_setting', $input);
}
'''

prompt = f"""
You are a WordPress security expert. Analyze this PHP code for security issues:

{code_snippet}

Provide a brief security analysis focusing on:
1. Input validation issues
2. XSS vulnerabilities 
3. Data sanitization problems
4. WordPress best practices violations

Keep response under 500 words.
"""

try:
    print("🔍 Analyzing WordPress code with Gemini AI...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    analysis = response.text or "No response received"
    print("\n🤖 GEMINI AI ANALYSIS:")
    print("=" * 60)
    print(analysis)
    print("=" * 60)
    print(f"✅ Analysis complete ({len(analysis)} characters)")
    
except Exception as e:
    print(f"❌ Error: {e}")