import os
import requests
import logging
from google import genai
from google.genai import types

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---
# Get credentials from environment variables
BITBUCKET_EMAIL = os.environ.get("BITBUCKET_EMAIL")
BITBUCKET_API_TOKEN = os.environ.get("BITBUCKET_API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini client
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    logger.warning("GEMINI_API_KEY not set")

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
    if not client:
        logger.error("Gemini client not initialized")
        return "Error: Gemini API not configured"
    
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

def handle_webhook_payload(payload: dict):
    """Main handler for the Bitbucket webhook payload."""
    try:
        # Check if PR is open
        if payload.get('pullrequest', {}).get('state') != 'OPEN':
            logger.info("PR is not open, skipping review.")
            return "PR is not open, skipping review."

        # Get required URLs
        pr_links = payload.get('pullrequest', {}).get('links', {})
        diff_url = pr_links.get('diff', {}).get('href')
        comments_url = pr_links.get('comments', {}).get('href')
        
        if not diff_url or not comments_url:
            logger.error("Missing required URLs in webhook payload")
            return "Missing required URLs in webhook payload"
        
        pr_title = payload.get('pullrequest', {}).get('title', 'Unknown PR')
        logger.info(f"Processing PR: {pr_title}")

        # 1. Get the diff
        diff_text = get_pr_diff(diff_url)
        if not diff_text:
            logger.error("Failed to fetch PR diff")
            return "Failed to fetch PR diff"

        # 2. Analyze with Gemini
        review_comment = analyze_code_with_gemini(diff_text)
        logger.info(f"Gemini analysis complete, response length: {len(review_comment)} characters")

        # 3. Post the comment back to Bitbucket
        post_comment_to_bitbucket(comments_url, review_comment)

        # Return the analysis for display
        return review_comment

    except Exception as e:
        logger.error(f"Error handling webhook payload: {e}")
        raise
