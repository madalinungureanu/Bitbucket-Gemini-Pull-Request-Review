import os
import requests
import logging
import time
import ssl
from google import genai
from google.genai import types
import httpx
from urllib.parse import unquote, quote

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
            logger.error(f"BITBUCKET_EMAIL exists: {bool(BITBUCKET_EMAIL)}")
            logger.error(
                f"BITBUCKET_API_TOKEN exists: {bool(BITBUCKET_API_TOKEN)}")
            return ""

        # Clean up the URL to handle encoding issues
        logger.info(f"Original diff URL: {diff_url}")
        
        # First decode any URL encoding, then re-encode properly
        # This handles cases where there are unwanted characters like %0D (carriage return)
        try:
            # Decode the URL first
            decoded_url = unquote(diff_url)
            logger.info(f"Decoded URL: {decoded_url}")
            
            # Replace newlines with '..' to form a valid commit range
            cleaned_url = decoded_url.replace('\r\n', '..').replace('\r', '..').replace('\n', '..').strip()
            
            # Re-encode properly if needed (but most of the URL should be fine as-is)
            # We only need to re-encode the parts after the domain that contain special characters
            if '/repositories/' in cleaned_url:
                base_part, path_part = cleaned_url.split('/repositories/', 1)
                # Split path into URL path and query parameters
                if '?' in path_part:
                    url_path, query_params = path_part.split('?', 1)
                else:
                    url_path = path_part
                    query_params = ""
                
                # Only re-encode the repository and path parts that contain special characters
                path_parts = url_path.split('/')
                encoded_parts = []
                for part in path_parts:
                    if ':' in part:
                        # This is likely a branch/commit reference, encode carefully
                        encoded_parts.append(quote(part, safe=':'))
                    else:
                        encoded_parts.append(part)
                
                cleaned_url = base_part + '/repositories/' + '/'.join(encoded_parts)
                if query_params:
                    cleaned_url += '?' + query_params
            
            logger.info(f"Cleaned URL: {cleaned_url}")
            diff_url = cleaned_url
            
        except Exception as url_error:
            logger.warning(f"URL cleaning failed, using original: {url_error}")
            # Fall back to original URL if cleaning fails
            pass

        logger.info(f"Making authenticated request to: {diff_url}")
        logger.info(f"Using email: {BITBUCKET_EMAIL}")

        response = requests.get(diff_url,
                                auth=(BITBUCKET_EMAIL, BITBUCKET_API_TOKEN),
                                timeout=30)

        logger.info(f"Response status: {response.status_code}")

        response.raise_for_status()
        logger.info(f"Successfully fetched diff from: {diff_url}")
        logger.info(f"Diff length: {len(response.text)} characters")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching PR diff: {e}")
        logger.error(
            f"Response status code: {getattr(e.response, 'status_code', 'N/A')}"
        )
        logger.error(f"Response text: {getattr(e.response, 'text', 'N/A')}")
        return ""


def analyze_code_with_gemini(diff: str) -> str:
    """Sends the code diff to Gemini for analysis with a WordPress-specific prompt."""
    if not client:
        logger.error("Gemini client not initialized")
        return "Error: Gemini API not configured"

    # Retry logic for SSL/network issues
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            prompt = f"""
You are an expert WordPress developer and senior code reviewer.
Your task is to analyze the following code diff from a pull request.

Please provide feedback on the following aspects:
1. **Bugs**: Identify any potential logical errors or bugs.
2. **Performance**: Are there any obvious performance bottlenecks?
3. **Best Practices**: Suggest improvements based on modern WordPress development best practices.

Format your review clearly using Markdown. If there are no issues, simply state that the code looks good. Try to be concise and keep your response under 2000 characters.

Here is the code diff:
```diff
{diff}
```
"""

            logger.info(
                f"Attempting Gemini API call (attempt {attempt + 1}/{max_retries})"
            )

            response = client.models.generate_content(model="gemini-2.5-flash",
                                                      contents=prompt)

            logger.info(f"Gemini API call successful on attempt {attempt + 1}")
            return response.text or "No analysis available"

        except (ssl.SSLError, ConnectionError, OSError,
                httpx.RemoteProtocolError, httpx.ReadTimeout,
                httpx.ConnectTimeout, httpx.NetworkError) as e:
            logger.warning(
                f"Network/connection error on attempt {attempt + 1}: {type(e).__name__}: {e}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("All retry attempts failed for Gemini API")
                return f"Network connectivity issue with Gemini API after {max_retries} attempts. Connection error: {str(e)}"

        except Exception as e:
            # Check if this is any other network-related error that we should retry
            error_name = type(e).__name__
            error_str = str(e).lower()

            # Check for common network error patterns
            if any(pattern in error_str for pattern in [
                    'connection', 'timeout', 'network', 'disconnected',
                    'protocol'
            ]):
                logger.warning(
                    f"Potential network error on attempt {attempt + 1}: {error_name}: {e}"
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error("All retry attempts failed for Gemini API")
                    return f"Network connectivity issue with Gemini API after {max_retries} attempts. Error: {str(e)}"

            # If we get here, it's a non-retryable error
            logger.error(f"Non-retryable error calling Gemini API: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Diff length: {len(diff)} characters")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"An error occurred while analyzing the code with Gemini: {str(e)}"


def post_comment_to_bitbucket(comments_url: str, comment: str):
    """Posts a comment to the Bitbucket pull request."""
    if not BITBUCKET_EMAIL or not BITBUCKET_API_TOKEN:
        logger.error("Bitbucket credentials not configured")
        return

    payload = {"content": {"raw": comment}}
    try:
        response = requests.post(comments_url,
                                 json=payload,
                                 auth=(BITBUCKET_EMAIL, BITBUCKET_API_TOKEN),
                                 timeout=30)
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
        logger.info(f"Attempting to fetch diff from: {diff_url}")
        diff_text = get_pr_diff(diff_url)
        if not diff_text:
            error_msg = f"⚠️ **Unable to fetch code changes**\n\nFailed to retrieve the pull request diff from: `{diff_url}`\n\nThis could be due to:\n- API authentication issues\n- Repository access permissions\n- Temporary API unavailability\n\nPlease check the webhook bot configuration and try again."
            logger.error(f"Failed to fetch PR diff from {diff_url}")

            # Still post a helpful error message to the PR
            post_comment_to_bitbucket(comments_url, error_msg)
            return error_msg

        # 2. Analyze with Gemini
        logger.info(
            f"Starting Gemini analysis for diff of {len(diff_text)} characters"
        )
        review_comment = analyze_code_with_gemini(diff_text)

        # Check if Gemini analysis failed
        if review_comment.startswith("An error occurred while analyzing"):
            logger.error("Gemini analysis failed, check detailed logs above")
            # Still post the error as a comment for visibility
            review_comment = f"⚠️ **Code Review Bot Error**\n\n{review_comment}\n\nPlease check the bot logs and try again later."

        logger.info(
            f"Gemini analysis complete, response length: {len(review_comment)} characters"
        )

        # 3. Post the comment back to Bitbucket
        post_comment_to_bitbucket(comments_url, review_comment)

        # Return the analysis for display
        return review_comment

    except Exception as e:
        logger.error(f"Error handling webhook payload: {e}")
        raise
