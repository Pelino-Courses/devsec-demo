from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile

class XSSTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.login(username='testuser', password='password123')
        self.update_url = reverse('update_profile')
        self.profile_url = reverse('profile')

    def test_stored_xss_is_escaped(self):
        """Verify that a malicious script tag is escaped during rendering."""
        # 1. Update bio with a malicious script
        malicious_bio = "<script>alert('XSS')</script><b>Bold Text</b>"
        self.client.post(self.update_url, {'bio': malicious_bio})
        
        # 2. Access the profile page
        response = self.client.get(self.profile_url)
        content = response.content.decode()
        
        # 3. Verify that the script tag is escaped
        # It should show up as &lt;script&gt; and NOT be executable HTML
        self.assertIn("&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;", content)
        # Verify that legitimate HTML (even if safe-looking) is also escaped by default
        self.assertIn("&lt;b&gt;Bold Text&lt;/b&gt;", content)
        
        # Verify it's NOT rendered as raw HTML
        self.assertNotIn("<script>alert('XSS')</script>", content)
        self.assertNotIn("<b>Bold Text</b>", content)

    def test_legitimate_content_renders(self):
        """Ensure normal text renders correctly."""
        normal_bio = "Hello, I am a security-conscious user."
        self.client.post(self.update_url, {'bio': normal_bio})
        
        response = self.client.get(self.profile_url)
        self.assertIn(normal_bio, response.content.decode())
