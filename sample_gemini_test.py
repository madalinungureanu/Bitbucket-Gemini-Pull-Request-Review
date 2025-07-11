#!/usr/bin/env python3
"""
Simple test script to show Gemini AI response for WordPress code analysis
"""

import os
import sys
sys.path.append('.')

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

def main():
    print("Testing Gemini AI WordPress Code Analysis")
    print("=" * 50)
    print("Sample WordPress code diff:")
    print(sample_diff)
    print("=" * 50)
    print("Gemini AI Analysis:")
    print("=" * 50)
    
    try:
        analysis = analyze_code_with_gemini(sample_diff)
        print(analysis)
        
        # Save to file for easy viewing
        with open('latest_gemini_response.txt', 'w') as f:
            f.write("GEMINI AI WORDPRESS CODE ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            f.write("Sample Code Diff:\n")
            f.write(sample_diff)
            f.write("\n\n" + "=" * 50 + "\n")
            f.write("Analysis Result:\n")
            f.write("=" * 50 + "\n\n")
            f.write(analysis)
        
        print(f"\n✅ Analysis complete! Response saved to 'latest_gemini_response.txt'")
        print(f"📊 Response length: {len(analysis)} characters")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()