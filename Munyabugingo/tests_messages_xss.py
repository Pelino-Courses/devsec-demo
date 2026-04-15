from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages

class MessagesXSSTest(TestCase):
    def test_message_escaping_in_js(self):
        """
        Test that a message containing special JS characters or script tags
        does not cause XSS in the showToast call in base.html.
        """
        # Create a malicious message
        malicious_msg = 'test"); alert("XSS"); ("'
        
        # We need a view that adds this message. Let's use a mock view or check existing ones.
        # Actually, we can just trigger a view and use the messages framework.
        # But wait, we want to see the RENDERED output.
        
        # Let's use the login view with a malicious username if it's reflected in messages?
        # No, views.py uses hardcoded strings for login errors.
        
        # How about the profile update view?
        # views.py: messages.success(request, 'Your profile has been updated!')
        
        # Okay, let's create a temporary test view that adds a malicious message
        # Or just use a template rendering test.
        from django.template import Template, Context
        from django.http import HttpRequest
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        request = HttpRequest()
        setattr(request, '_messages', FallbackStorage(request))
        messages.success(request, malicious_msg)
        
        # Render base.html with these messages
        # Wait, base.html depends on many things.
        
        # Simpler: check if "{{ message }}" in base.html is wrapped in |escapejs
        with open('Munyabugingo/templates/olivier/base.html', 'r') as f:
            content = f.read()
            self.assertIn('showToast("{{ message|escapejs }}', content, 
                         "Messages in script tags must use |escapejs to prevent XSS!")
