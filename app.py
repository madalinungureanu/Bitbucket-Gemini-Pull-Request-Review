import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, copy_context

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Import webhook handler
from webhook_handler import handle_webhook_payload

# Store recent webhook events for display
import json

def load_recent_events():
    """Load recent events from file"""
    try:
        with open('recent_events.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_recent_events(events):
    """Save recent events to file"""
    try:
        with open('recent_events.json', 'w') as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save events: {e}")

# Load existing events on startup
recent_events = load_recent_events()

# Add some sample events if none exist (for demonstration)
if not recent_events:
    recent_events = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': 'OPEN',
            'pr_title': 'Sample: Fix WordPress security issues',
            'pr_id': 'demo-001',
            'status': 'success',
            'gemini_response': 'Demo: This would contain the Gemini AI analysis of WordPress code security improvements and best practices recommendations.'
        },
        {
            'timestamp': (datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': 'OPEN',
            'pr_title': 'Sample: Add proper input sanitization',
            'pr_id': 'demo-002',
            'status': 'success',
            'gemini_response': 'Demo: Analysis would include WordPress coding standards compliance and security vulnerability assessment.'
        }
    ]
    save_recent_events(recent_events)

@app.route('/')
def index():
    """Main dashboard showing recent webhook events"""
    return render_template('index.html', events=recent_events)

@app.route('/webhook', methods=['GET', 'POST'], strict_slashes=False)
@app.route('/webhook/', methods=['GET', 'POST'], strict_slashes=False)
def webhook():
    """Bitbucket webhook endpoint"""
    if request.method == 'GET':
        return jsonify({
            'status': 'webhook_endpoint_active',
            'message': 'Webhook endpoint is ready to receive POST requests',
            'timestamp': datetime.now().isoformat()
        })
    
    # Handle POST requests (actual webhooks)
    try:
        # Log the incoming request for debugging
        logger.debug(f"Webhook received: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Get the webhook payload
        payload = request.get_json()
        
        if not payload:
            logger.error("No JSON payload received")
            return jsonify({'error': 'No JSON payload'}), 400
        
        # Log the event
        event_info = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': payload.get('pullrequest', {}).get('state', 'unknown'),
            'pr_title': payload.get('pullrequest', {}).get('title', 'No title'),
            'pr_id': payload.get('pullrequest', {}).get('id', 'unknown'),
            'status': 'processing',
            'gemini_response': None
        }
        
        # Add to recent events (keep last 10)
        recent_events.insert(0, event_info)
        if len(recent_events) > 10:
            recent_events.pop()
        
        # Save events to file for persistence
        save_recent_events(recent_events)
        
        logger.info(f"Received webhook for PR: {event_info['pr_title']}")
        
        # Process the webhook
        try:
            gemini_response = handle_webhook_payload(payload)
            event_info['status'] = 'success'
            event_info['gemini_response'] = gemini_response
            logger.info("Webhook processed successfully")
        except Exception as e:
            event_info['status'] = 'error'
            event_info['error'] = str(e)
            logger.error(f"Error processing webhook: {e}")
        
        # Update the saved events with final status
        save_recent_events(recent_events)
        
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test():
    """Test endpoint to verify the application is running"""
    return jsonify({
        'status': 'ok',
        'message': 'WordPress Code Review Bot is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    # Check if required environment variables are set
    required_vars = ['BITBUCKET_EMAIL', 'BITBUCKET_API_TOKEN', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        return jsonify({
            'status': 'error',
            'message': f'Missing environment variables: {", ".join(missing_vars)}'
        }), 500
    
    return jsonify({
        'status': 'healthy',
        'message': 'All required environment variables are set'
    })

@app.route('/gemini-responses')
def gemini_responses():
    """Show recent Gemini AI responses"""
    responses = []
    for event in recent_events:
        if event.get('gemini_response'):
            responses.append({
                'timestamp': event['timestamp'],
                'pr_title': event['pr_title'],
                'pr_id': event['pr_id'],
                'response': event['gemini_response']
            })
    return jsonify(responses)

@app.route('/test-gemini')
def test_gemini():
    """Test Gemini AI with a sample WordPress code diff"""
    from webhook_handler import analyze_code_with_gemini
    
    # Sample WordPress code diff for testing
    sample_diff = '''--- a/wp-content/plugins/test-plugin/test-plugin.php
+++ b/wp-content/plugins/test-plugin/test-plugin.php
@@ -10,7 +10,12 @@
 
 function handle_form_submission() {
     if (isset($_POST['submit'])) {
-        $user_input = $_POST['user_data'];
+        $user_input = sanitize_text_field($_POST['user_data']);
+        
+        // Verify nonce for security
+        if (!wp_verify_nonce($_POST['_wpnonce'], 'test_form_nonce')) {
+            wp_die('Security check failed');
+        }
         
         // Process the input
         echo "User said: " . esc_html($user_input);
'''
    
    try:
        logger.info("Testing Gemini AI with sample WordPress code diff")
        analysis = analyze_code_with_gemini(sample_diff)
        logger.info(f"Gemini test analysis complete: {len(analysis)} characters")
        
        return jsonify({
            'status': 'success',
            'sample_diff': sample_diff,
            'gemini_analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Gemini test failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
