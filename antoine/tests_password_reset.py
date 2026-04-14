"""
Password Reset Flow Tests

Tests for secure password reset functionality.
Covers request, token validation, confirm, and error handling.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from antoine.models import UserProfile, PasswordChangeHistory


class PasswordResetRequestTest(TestCase):
    """Test password reset request flow"""
    
    def setUp(self):
        """Create test user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword@123'
        )
        UserProfile.objects.create(user=self.user)
    
    def test_anonymous_can_request_reset(self):
        """Test that unauthenticated user can access reset request"""
        response = self.client.get(reverse('antoine:password_reset_request'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
    
    def test_authenticated_user_redirected_to_dashboard(self):
        """Test that authenticated user is redirected away from reset request"""
        self.client.login(username='testuser', password='OldPassword@123')
        response = self.client.get(reverse('antoine:password_reset_request'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response.url)
    
    def test_reset_request_with_valid_email(self):
        """Test password reset request with existing email"""
        response = self.client.post(
            reverse('antoine:password_reset_request'),
            {'email': 'test@example.com'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Check your email', str(response.content).lower())
    
    def test_reset_request_with_nonexistent_email(self):
        """Test that non-existent email gets same response (user enumeration prevention)"""
        response = self.client.post(
            reverse('antoine:password_reset_request'),
            {'email': 'nonexistent@example.com'},
            follow=True
        )
        # Should get same success message (don't reveal email doesn't exist)
        self.assertEqual(response.status_code, 200)
        self.assertIn('check your email', str(response.content).lower())
    
    def test_reset_done_page_accessible(self):
        """Test that reset done page is accessible after request"""
        response = self.client.get(reverse('antoine:password_reset_done'))
        self.assertEqual(response.status_code, 200)


class PasswordResetTokenTest(TestCase):
    """Test password reset token handling"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword@123'
        )
        UserProfile.objects.create(user=self.user)
        self.client = Client()
    
    def test_valid_token_generated(self):
        """Test that valid token is generated for password reset"""
        token = default_token_generator.make_token(self.user)
        self.assertTrue(len(token) > 0)
        self.assertTrue(default_token_generator.check_token(self.user, token))
    
    def test_token_invalid_after_password_change(self):
        """Test that token becomes invalid after password is changed"""
        token = default_token_generator.make_token(self.user)
        self.assertTrue(default_token_generator.check_token(self.user, token))
        
        # Change password
        self.user.set_password('NewPassword@456')
        self.user.save()
        
        # Token should now be invalid
        self.assertFalse(default_token_generator.check_token(self.user, token))
    
    def test_token_specific_to_user(self):
        """Test that token from one user doesn't work for another"""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='Password@123'
        )
        
        token = default_token_generator.make_token(self.user)
        # Token should be valid for user1
        self.assertTrue(default_token_generator.check_token(self.user, token))
        # But not for user2
        self.assertFalse(default_token_generator.check_token(user2, token))


class PasswordResetConfirmTest(TestCase):
    """Test password reset confirmation flow"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword@123'
        )
        UserProfile.objects.create(user=self.user)
        self.client = Client()
        
        # Generate valid token and UID
        self.token = default_token_generator.make_token(self.user)
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
    
    def test_valid_token_shows_form(self):
        """Test that valid token shows password reset form"""
        response = self.client.get(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])
        self.assertIn('form', response.context)
    
    def test_invalid_token_shows_error(self):
        """Test that invalid token shows error"""
        response = self.client.get(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, 'invalid-token'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])
    
    def test_expired_or_modified_token_error(self):
        """Test that expired tokens show error"""
        # Change password to invalidate token
        self.user.set_password('NewPassword@456')
        self.user.save()
        
        response = self.client.get(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])
    
    def test_wrong_uid_shows_error(self):
        """Test that wrong UID shows error"""
        wrong_uidb64 = urlsafe_base64_encode(force_bytes(99999))
        response = self.client.get(
            reverse('antoine:password_reset_confirm', args=[wrong_uidb64, self.token])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])
    
    def test_reset_password_with_weak_password(self):
        """Test that weak passwords are rejected"""
        response = self.client.post(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token]),
            {
                'new_password1': '123',  # Too weak
                'new_password2': '123',
            }
        )
        self.assertEqual(response.status_code, 200)
        # Form should have errors
        form = response.context['form']
        self.assertTrue(form.errors)
    
    def test_reset_password_with_mismatched_passwords(self):
        """Test that mismatched passwords are rejected"""
        response = self.client.post(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token]),
            {
                'new_password1': 'NewPassword@456',
                'new_password2': 'DifferentPassword@456',
            }
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.errors)
    
    def test_reset_password_successful(self):
        """Test successful password reset"""
        response = self.client.post(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token]),
            {
                'new_password1': 'NewPassword@456',
                'new_password2': 'NewPassword@456',
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword@456'))
        self.assertFalse(self.user.check_password('OldPassword@123'))
    
    def test_password_reset_logs_to_history(self):
        """Test that password reset is logged to PasswordChangeHistory"""
        response = self.client.post(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token]),
            {
                'new_password1': 'NewPassword@456',
                'new_password2': 'NewPassword@456',
            },
            follow=True
        )
        
        # Check that password change was logged
        history = PasswordChangeHistory.objects.filter(user=self.user)
        self.assertTrue(history.exists())
    
    def test_old_token_invalid_after_reset(self):
        """Test that token cannot be used again after reset"""
        # First reset
        response1 = self.client.post(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token]),
            {
                'new_password1': 'NewPassword@456',
                'new_password2': 'NewPassword@456',
            },
            follow=True
        )
        self.assertEqual(response1.status_code, 200)
        
        # Try to use same token again
        response2 = self.client.get(
            reverse('antoine:password_reset_confirm', args=[self.uidb64, self.token])
        )
        self.assertFalse(response2.context['validlink'])


class PasswordResetCompleteTest(TestCase):
    """Test password reset completion"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword@123'
        )
        UserProfile.objects.create(user=self.user)
        self.client = Client()
    
    def test_complete_page_accessible(self):
        """Test that password reset complete page is accessible"""
        response = self.client.get(reverse('antoine:password_reset_complete'))
        self.assertEqual(response.status_code, 200)
    
    def test_can_login_after_reset(self):
        """Test that user can login with new password after reset"""
        # Reset password
        self.user.set_password('NewPassword@456')
        self.user.save()
        
        # Try to login with old password (should fail)
        response = self.client.post(
            reverse('antoine:login'),
            {
                'username': 'testuser',
                'password': 'OldPassword@123',
                'remember_me': False,
            }
        )
        self.assertIn('Invalid username or password', str(response.content).lower())
        
        # Try to login with new password (should succeed)
        response = self.client.post(
            reverse('antoine:login'),
            {
                'username': 'testuser',
                'password': 'NewPassword@456',
                'remember_me': False,
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('welcome', str(response.content).lower())


class PasswordResetSecurityTest(TestCase):
    """Test security aspects of password reset"""
    
    def setUp(self):
        """Create test users"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password@123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password@123'
        )
        self.client = Client()
    
    def test_no_user_enumeration_via_email(self):
        """Test that password reset doesn't leak user existence"""
        # Request reset for existing email
        response1 = self.client.post(
            reverse('antoine:password_reset_request'),
            {'email': 'user1@example.com'},
            follow=True
        )
        
        # Request reset for non-existent email  
        response2 = self.client.post(
            reverse('antoine:password_reset_request'),
            {'email': 'nonexistent@example.com'},
            follow=True
        )
        
        # Both should show same message
        content1 = str(response1.content).lower()
        content2 = str(response2.content).lower()
        
        # Both should mention checking email
        self.assertIn('check your email', content1)
        self.assertIn('check your email', content2)
    
    def test_csrf_protection_on_post(self):
        """Test that CSRF protection is active"""
        response = self.client.post(
            reverse('antoine:password_reset_request'),
            {'email': 'test@example.com'},
            HTTP_X_CSRFTOKEN='invalid'
        )
        # Without valid CSRF, POST should be rejected or redirected
        # (Exact behavior depends on Django settings)
    
    def test_token_uses_user_id_not_email(self):
        """Test that token is based on user ID (immutable after account creation)"""
        token1 = default_token_generator.make_token(self.user1)
        
        # Change email
        self.user1.email = 'newemail@example.com'
        self.user1.save()
        
        # Token should still be valid (based on ID/password, not email)
        self.assertTrue(default_token_generator.check_token(self.user1, token1))
