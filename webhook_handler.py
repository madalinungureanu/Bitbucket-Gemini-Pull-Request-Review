import os
import requests
import logging
import threading
import json
import time
from google import genai
from google.genai import types

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---
# Get credentials from environment variables
BITBUCKET_EMAIL = os.environ.get("BITBUCKET_EMAIL")
BITBUCKET_API_TOKEN = os.environ.get("BITBUCKET_API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")



def get_pr_diff(diff_url: str) -> str:
    """Fetches the diff of a pull request from its diff URL."""
    try:
        if not BITBUCKET_EMAIL or not BITBUCKET_API_TOKEN:
            logger.error("Bitbucket credentials not configured")
            return None
            
        response = requests.get(
            diff_url,
            auth=(BITBUCKET_EMAIL, BITBUCKET_API_TOKEN),
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Successfully fetched diff from: {diff_url}")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching PR diff: {e}")
        return None

def analyze_code_with_gemini(diff: str) -> str:
    """Sends the code diff to Gemini for analysis with a WordPress-specific prompt."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        return "Error: Gemini API not configured"
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        prompt = f"""
You are an expert WordPress developer and senior code reviewer.
Your task is to analyze the following code diff from a pull request.

Please provide feedback on the following aspects:
1. **WordPress Coding Standards**: Does the code adhere to the official WordPress coding standards?
2. **Security Vulnerabilities**: Look for common WordPress security issues (missing nonces, improper sanitization/escaping, SQL injection, XSS vulnerabilities).
3. **Performance**: Are there any obvious performance bottlenecks?
4. **Best Practices**: Suggest improvements based on modern WordPress development best practices.
5. **Bugs**: Identify any potential logical errors or bugs.

Format your review clearly using Markdown. If there are no issues, simply state that the code looks good.

Here is the code diff:
```diff
{diff}
```
"""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text or "No analysis available"
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return "An error occurred while analyzing the code with Gemini."

def post_comment_to_bitbucket(comments_url: str, comment: str):
    """Posts a comment to the Bitbucket pull request."""
    if not BITBUCKET_EMAIL or not BITBUCKET_API_TOKEN:
        logger.error("Bitbucket credentials not configured")
        return
        
    payload = {"content": {"raw": comment}}
    try:
        response = requests.post(
            comments_url,
            json=payload,
            auth=(BITBUCKET_EMAIL, BITBUCKET_API_TOKEN),
            timeout=30
        )
        response.raise_for_status()
        logger.info("Successfully posted comment to Bitbucket.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error posting comment to Bitbucket: {e}")

# --- New additions for async handling ---
# Lock for thread-safe access to the recent events file
file_lock = threading.Lock()
RECENT_EVENTS_FILE = 'recent_events.json'
MAX_RECENT_EVENTS = 100

def is_event_processed(event_id: str) -> bool:
    """Checks if an event has already been processed."""
    with file_lock:
        try:
            with open(RECENT_EVENTS_FILE, 'r') as f:
                recent_events = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            recent_events = []

        if event_id in recent_events:
            logger.info(f"Event {event_id} has already been processed. Skipping.")
            return True
        return False

def mark_event_as_processed(event_id: str):
    """Marks an event as processed."""
    with file_lock:
        try:
            with open(RECENT_EVENTS_FILE, 'r') as f:
                recent_events = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            recent_events = []

        recent_events.insert(0, event_id)
        # Keep the list at a manageable size
        recent_events = recent_events[:MAX_RECENT_EVENTS]

        with open(RECENT_EVENTS_FILE, 'w') as f:
            json.dump(recent_events, f, indent=4)

def process_webhook_in_background(app, payload: dict):
    with app.app_context():
    """This function runs in a background thread to handle the webhook logic."""
    try:
        # Check if PR is open
        if payload.get('pullrequest', {}).get('state') != 'OPEN':
            logger.info("PR is not open, skipping review.")
            return

        # Get required URLs
        pr_links = payload.get('pullrequest', {}).get('links', {})
        diff_url = pr_links.get('diff', {}).get('href')
        comments_url = pr_links.get('comments', {}).get('href')

        if not diff_url or not comments_url:
            logger.error("Missing required URLs in webhook payload")
            return

        pr_title = payload.get('pullrequest', {}).get('title', 'Unknown PR')
        logger.info(f"Processing PR in background: {pr_title}")

        # 1. Get the diff
        diff_text = get_pr_diff(diff_url)
        if not diff_text:
            logger.error("Failed to fetch PR diff")
            return

        # 2. Analyze with Gemini
        review_comment = analyze_code_with_gemini(diff_text)
        logger.info(f"Gemini analysis complete, response length: {len(review_comment)} characters")

        # 3. Post the comment back to Bitbucket
        post_comment_to_bitbucket(comments_url, review_comment)

    except Exception as e:
        logger.error(f"Error processing webhook in background: {e}")


def handle_webhook_payload(payload: dict, app):
    """
    Main handler for the Bitbucket webhook payload.
    This function now handles webhook de-duplication and acknowledges
    the request immediately by starting the actual processing in a
    background thread.
    """
    try:
        pr = payload.get('pullrequest', {})
        pr_id = pr.get('id')
        # Using the source commit hash to uniquely identify the PR state
        commit_hash = pr.get('source', {}).get('commit', {}).get('hash')

        if not pr_id or not commit_hash:
            logger.error("Could not determine PR ID or commit hash from payload.")
            return "Could not determine PR ID or commit hash from payload."

        event_id = f"pr:{pr_id}-commit:{commit_hash}"

        if is_event_processed(event_id):
            logger.info(f"Duplicate event {event_id} received. Skipping.")
            return "Duplicate event received. Skipping."

        mark_event_as_processed(event_id)

        # Run the actual processing in a background thread
        thread = threading.Thread(target=process_webhook_in_background, args=(app, payload))
        thread.start()

        logger.info(f"Webhook for event {event_id} received and accepted for background processing.")
        return "Webhook received and accepted for background processing."

    except Exception as e:
        logger.error(f"Error handling webhook payload: {e}")
        # Return a generic error to avoid causing webhook retries for handler errors.
        return "An internal error occurred while processing the webhook."
