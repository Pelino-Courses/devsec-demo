from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class PasswordResetTestCase(TestCase):
    """Test cases for secure password reset functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123'
        )

    def test_password_reset_request_form_renders(self):
        """Test that password reset request form renders correctly."""
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_form.html')
        self.assertContains(response, 'Password Reset')
        self.assertContains(response, 'Enter your email')

    def test_password_reset_request_successful(self):
        """Test successful password reset request."""
        response = self.client.post(reverse('password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to done page
        self.assertRedirects(response, reverse('password_reset_done'))

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, 'Reset your DevSec Demo password')
        self.assertIn('test@example.com', email.to)
        self.assertIn('reset the password for your account at devsec demo', email.body.lower())
        self.assertIn('/reset/', email.body)

    def test_password_reset_request_nonexistent_email(self):
        """Test password reset request with non-existent email."""
        response = self.client.post(reverse('password_reset'), {
            'email': 'nonexistent@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('password_reset_done'))

        # The response stays the same to avoid enumeration, but Django does
        # not send a reset email for unknown accounts.
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_done_page_renders(self):
        """Test that password reset done page renders correctly."""
        response = self.client.get(reverse('password_reset_done'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_done.html')

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirm with invalid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('password_reset_confirm',
                                         kwargs={'uidb64': uid, 'token': 'invalid-token'}))
        self.assertEqual(response.status_code, 200)
        # Should show invalid link message
        self.assertContains(response, 'invalid or has expired')

    def test_password_reset_confirm_valid_token(self):
        """Test password reset confirm with valid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')

    def test_password_reset_confirm_post_valid(self):
        """Test completing password reset with valid data."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        confirm_url = response.request['PATH_INFO']

        response = self.client.post(confirm_url, {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('password_reset_complete'))

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

    def test_password_reset_confirm_post_mismatched_passwords(self):
        """Test password reset with mismatched passwords."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        confirm_url = response.request['PATH_INFO']

        response = self.client.post(confirm_url, {
            'new_password1': 'newpassword123',
            'new_password2': 'differentpassword'
        })
        self.assertEqual(response.status_code, 200)
        # Should stay on same page with error
        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')
        self.assertContains(response, 'didn’t match')

    def test_password_reset_confirm_post_weak_password(self):
        """Test password reset with weak password."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        confirm_url = response.request['PATH_INFO']

        response = self.client.post(confirm_url, {
            'new_password1': '123',
            'new_password2': '123'
        })
        self.assertEqual(response.status_code, 200)
        # Should stay on same page with validation error
        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')
        self.assertContains(response, 'too short')

    def test_password_reset_complete_page_renders(self):
        """Test that password reset complete page renders correctly."""
        response = self.client.get(reverse('password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_complete.html')

    def test_password_reset_token_expiration_simulation(self):
        """Test that password reset tokens work within expected timeframe."""
        # This is a basic test - in production, tokens expire after a configurable time
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # Token should be valid immediately
        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_email_content_security(self):
        """Test that password reset email doesn't leak sensitive information."""
        self.client.post(reverse('password_reset'), {
            'email': 'test@example.com'
        })

        email = mail.outbox[0]
        # Email should not contain the prior password and should include safe instructions.
        self.assertNotIn('oldpassword123', email.body)
        self.assertIn('/reset/', email.body.lower())
        self.assertIn('ignore this message', email.body.lower())

    def test_password_reset_form_validation(self):
        """Test password reset form validation."""
        # Test empty email
        response = self.client.post(reverse('password_reset'), {
            'email': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required')

        # Test invalid email format
        response = self.client.post(reverse('password_reset'), {
            'email': 'invalid-email'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid')

    def test_password_reset_workflow_end_to_end(self):
        """Test complete password reset workflow."""
        # 1. Request reset
        response = self.client.post(reverse('password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)

        # 2. Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # 4. Visit reset link
        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # 5. Complete reset
        confirm_url = response.request['PATH_INFO']
        response = self.client.post(confirm_url, {
            'new_password1': 'brandnewpassword123',
            'new_password2': 'brandnewpassword123'
        })
        self.assertEqual(response.status_code, 302)

        # 6. Verify completion page
        response = self.client.get(reverse('password_reset_complete'))
        self.assertEqual(response.status_code, 200)

        # 7. Verify password change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brandnewpassword123'))
        self.assertFalse(self.user.check_password('oldpassword123'))
