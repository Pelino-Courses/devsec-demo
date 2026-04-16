"""
Tests for CSRF protection in the Aline UAS application.

Ensures that state-changing operations (like logout) are protected against CSRF
and do not allow insecure Method handling (e.g., GET for logout).
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from aline.models import UserProfile

@override_settings(MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])
class CsrfProtectionTestCase(TestCase):
    """Test cases for CSRF protection across state-changing views."""

    def setUp(self):
        self.client = Client(enforce_csrf=True)
        self.logout_url = reverse('aline:logout')
        self.login_url = reverse('aline:login')
        self.dashboard_url = reverse('aline:dashboard')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='csrf_user',
            password='SecurePass123!'
        )
        UserProfile.objects.create(user=self.user, student_id='CSRF001')

    def test_logout_via_get_is_forbidden(self):
        """
        Verify that hitting the logout URL via GET does NOT log the user out.
        This is to prevent simple 1-click CSRF logout attacks.
        """
        self.client.login(username='csrf_user', password='SecurePass123!')
        
        # Verify user is logged in
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        
        # Attempt logout via GET
        response = self.client.get(self.logout_url)
        
        # The expected behavior after fix is that GET either fails (405) 
        # or redirects without logging out.
        # But most importantly, the user should REMAIN logged in.
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_via_post_without_csrf_is_forbidden(self):
        """
        Verify that hitting the logout URL via POST without a CSRF token fails.
        """
        self.client.login(username='csrf_user', password='SecurePass123!')
        
        # Access a page to get a CSRF cookie (some Django versions/configurations require this)
        self.client.get(reverse('aline:home'))
        
        # Attempt logout via POST without token in POST data
        response = self.client.post(self.logout_url)
        
        # CSRF failures in Django return 403 Forbidden
        self.assertEqual(response.status_code, 403)
        
        # Verify user is STILL logged in
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_via_post_with_csrf_works(self):
        """
        Verify that hitting the logout URL via POST with a valid CSRF token works.
        """
        self.client.login(username='csrf_user', password='SecurePass123!')
        
        # To send a valid CSRF token in tests with enforce_csrf=True, 
        # we need to get the token from the cookie
        self.client.get(reverse('aline:home'))
        csrf_token = self.client.cookies['csrftoken'].value
        
        response = self.client.post(self.logout_url, {'csrfmiddlewaretoken': csrf_token}, follow=True)
        
        # User should be logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertRedirects(response, reverse('aline:home'))

    def test_profile_update_via_post_without_csrf_is_forbidden(self):
        """
        Verify that hitting the profile update URL via POST without a CSRF token fails.
        """
        self.client.login(username='csrf_user', password='SecurePass123!')
        self.client.get(reverse('aline:home'))
        
        profile_url = reverse('aline:profile')
        data = {
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'Name'
        }
        
        response = self.client.post(profile_url, data)
        self.assertEqual(response.status_code, 403)
