from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail


class PasswordResetFlowTests(TestCase):
    """Test suite for the secure password reset workflow."""

    def setUp(self):
        """Set up test user with email."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='OldPass123!'
        )

    def test_password_reset_page_loads(self):
        """Test that the password reset form page loads successfully."""
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset Your Password')

    def test_valid_email_sends_reset_token(self):
        """Test that submitting a valid email sends a reset email with a secure token."""
        response = self.client.post(reverse('password_reset'), {
            'email': 'testuser@example.com'
        })
        # Should redirect to password_reset_done
        self.assertEqual(response.status_code, 302)
        # One email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('testuser@example.com', mail.outbox[0].to)

    def test_invalid_email_does_not_leak_info(self):
        """Test that submitting an unregistered email does NOT reveal whether
        the account exists. The response should behave identically to a valid request.
        This prevents user enumeration attacks."""
        response = self.client.post(reverse('password_reset'), {
            'email': 'nonexistent@example.com'
        })
        # Should still redirect to password_reset_done (same behavior)
        self.assertEqual(response.status_code, 302)
        # No email should be sent since the account does not exist
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_done_page_loads(self):
        """Test that the password_reset_done page loads with a generic message."""
        response = self.client.get(reverse('password_reset_done'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'If an account exists')

    def test_valid_token_allows_password_change(self):
        """Test that a valid reset token allows the user to change their password."""
        # Request a password reset
        self.client.post(reverse('password_reset'), {
            'email': 'testuser@example.com'
        })
        # Extract the token and uid from the email body
        email_body = mail.outbox[0].body
        # Find the reset URL in the email
        import re
        reset_url_match = re.search(r'/accounts/reset/([^/]+)/([^/]+)/', email_body)
        self.assertIsNotNone(reset_url_match, 'Reset URL not found in email')

        uid = reset_url_match.group(1)
        token = reset_url_match.group(2)

        # Visit the reset confirmation page
        response = self.client.get(
            reverse('password_reset_confirm', args=[uid, token]),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Submit the new password (Django redirects with set-password token)
        # After GET, Django replaces token with 'set-password' in the URL
        reset_confirm_url = reverse('password_reset_confirm', args=[uid, 'set-password'])
        response = self.client.post(reset_confirm_url, {
            'new_password1': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!',
        })
        self.assertEqual(response.status_code, 302)

        # Verify the user can now log in with the new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass456!'))

    def test_invalid_token_rejected(self):
        """Test that an invalid or expired token is properly rejected."""
        response = self.client.get(
            reverse('password_reset_confirm', args=['invaliduid', 'invalid-token'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid')

    def test_password_reset_complete_page(self):
        """Test that the password reset complete page loads."""
        response = self.client.get(reverse('password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'successfully changed')
