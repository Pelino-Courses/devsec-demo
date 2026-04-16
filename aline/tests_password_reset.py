"""
Tests for the secure password reset flow.

Ensures that users can safely recover their accounts using Django's built-in
mechanisms, including verification of token security and enumeration prevention.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import UserProfile


class PasswordResetTestCase(TestCase):
    """Test cases for the password reset flow."""

    def setUp(self):
        """Set up a test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        UserProfile.objects.create(user=self.user, student_id='STU456')

    def test_password_reset_request_view(self):
        """Verify the password reset request page loaded correctly."""
        response = self.client.get(reverse('aline:password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Password?')

    def test_password_reset_submission_with_valid_email(self):
        """Test that a valid email triggers a reset email."""
        response = self.client.post(reverse('aline:password_reset'), {
            'email': 'test@example.com'
        })
        # Redirects to password_reset_done
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password reset', mail.outbox[0].subject)
        self.assertIn('test@example.com', mail.outbox[0].to)

    def test_password_reset_enumeration_prevention(self):
        """Test that invalid emails don't leak account existence."""
        response = self.client.post(reverse('aline:password_reset'), {
            'email': 'nonexistent@example.com'
        })
        # Should still redirect to the same "Done" page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('aline:password_reset_done')))
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_view_token_validity(self):
        """Test the confirm view with valid and invalid tokens."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        
        # Valid token (Django redirects to set-password URL after validating token)
        response = self.client.get(reverse('aline:password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        }), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set New Password')

        # Invalid token
        response = self.client.get(reverse('aline:password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': 'invalid-token'
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Link')

    def test_complete_reset_flow(self):
        """Test the full flow from confirms to complete."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        
        # 1. GET the token URL (Django validates token and stores user in session)
        confirm_url = reverse('aline:password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        })
        response = self.client.get(confirm_url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # 2. POST to the same URL (which is now the session-based set-password URL)
        # Note: We must use the last URL in the chain if there was a redirect
        final_url = response.request.get('PATH_INFO')
        
        response = self.client.post(final_url, {
            'new_password1': 'NewSecurePass123!',
            'new_password2': 'NewSecurePass123!'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(res[0].endswith(reverse('aline:password_reset_complete')) for res in response.redirect_chain))
        self.assertContains(response, 'Password Reset Complete')
        
        # 3. Verify login with new password
        login_success = self.client.login(username='testuser', password='NewSecurePass123!')
        self.assertTrue(login_success)
