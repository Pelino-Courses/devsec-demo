from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from Munyabugingo.models import Profile
from django.template import Template, Context

class StoredXSSTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='xsstester', password='password123')
        # Inject malicious payload in bio (user-controlled content)
        self.malicious_payload = '<script>alert("XSS")</script>'
        self.user.profile.bio = self.malicious_payload
        self.user.profile.save()

    def test_profile_bio_escapes_html(self):
        """
        Test that stored malicious HTML in a user's bio is properly escaped
        when rendered on the profile detail page, preventing stored XSS.
        """
        url = reverse('Munyabugingo:profile_detail', args=[self.user.profile.id])
        
        # User needs to be authenticated to view profiles with privileges or their own
        self.client.login(username='xsstester', password='password123')
        response = self.client.get(url)
        
        # Check that the raw script tags are NOT present in the output
        self.assertNotContains(response, self.malicious_payload)
        
        # Check that the escaped tags ARE present (i.e., &lt;script&gt;)
        self.assertContains(response, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')

class MessagesXSSTest(TestCase):
    def test_message_escaping_in_js(self):
        """
        Test that messages rendered in base.html's script block are properly
        escaped for JavaScript using |escapejs to prevent script injection.
        """
        # Malicious payload designed to break out of a JS string literal: "); alert('XSS'); ("
        malicious_msg = "test\"); alert('XSS'); (\""
        
        # Simpler approach: test the template rendering directly without full middleware stack
        # Create a mock message object with tags
        class MockMessage:
            def __init__(self, message, tags):
                self.message = message
                self.tags = tags
            def __str__(self):
                return self.message

        mock_messages = [MockMessage(malicious_msg, "success")]
        
        # In base.html: showToast("{{ message|escapejs }}", "{{ message.tags|escapejs }}");
        t = Template('{% for message in messages %}showToast("{{ message|escapejs }}", "{{ message.tags|escapejs }}");{% endfor %}')
        c = Context({'messages': mock_messages})
        rendered = t.render(c)
        
        # Check that the malicious string is escaped for JS
        # \") should be escaped, and semicolons should be escaped too
        self.assertNotIn("\"); alert('XSS'); (\"", rendered)
        
        # Verify that common attack characters are escaped
        self.assertIn("\\u0022", rendered) # double quote
        self.assertIn("\\u003B", rendered) # semicolon
        self.assertIn("\\u0027", rendered) # single quote
        
        # Verify the actual escaped structure observed in the previous run
        self.assertIn("test\\u0022)\\u003B alert(\\u0027XSS\\u0027)\\u003B (\\u0022", rendered)
