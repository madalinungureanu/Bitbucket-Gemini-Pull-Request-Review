#!/usr/bin/env python3
"""Debug script to simulate webhook processing"""

import json
import sys
import traceback
from webhook_handler import handle_webhook_payload

# Sample webhook payload for testing
test_payload = {
    "pullrequest": {
        "id": 1234,
        "title": "Test PR for debugging",
        "state": "OPEN",
        "updated_on": "2025-07-22T14:30:00.000000+00:00",
        "links": {
            "diff": {"href": "https://api.bitbucket.org/2.0/repositories/test/repo/pullrequests/1234/diff"},
            "comments": {"href": "https://api.bitbucket.org/2.0/repositories/test/repo/pullrequests/1234/comments"}
        }
    }
}

def debug_webhook():
    print("🔍 Debug: Testing webhook handler...")
    
    try:
        result = handle_webhook_payload(test_payload)
        print(f"✓ Webhook processed successfully")
        print(f"Result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Error in webhook handler: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = debug_webhook()
    sys.exit(0 if success else 1)