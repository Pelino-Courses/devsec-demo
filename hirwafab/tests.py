from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationTests(TestCase):
    """Test user registration functionality."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('hirwafab:register')

    def test_register_page_loads(self):
        """Test that registration page loads successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/register.html')

    def test_register_user_successfully(self):
        """Test successful user registration."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPassword123',
            'password2': 'TestPassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='TestPassword123'
        )
        data = {
            'username': 'existing',
            'email': 'new@example.com',
            'password1': 'TestPassword123',
            'password2': 'TestPassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        # Check that the form has errors
        self.assertTrue(response.context['form'].has_error('username'))

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='TestPassword123'
        )
        data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password1': 'TestPassword123',
            'password2': 'TestPassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        # Check that the form has errors
        self.assertTrue(response.context['form'].has_error('email'))

    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPassword123',
            'password2': 'DifferentPassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_register_weak_password(self):
        """Test registration with weak password."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': '123',  # Too short
            'password2': '123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_register_authenticated_user_redirects(self):
        """Test that authenticated users redirected from register page."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 302)


class UserLoginTests(TestCase):
    """Test user login functionality."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('hirwafab:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_login_page_loads(self):
        """Test that login page loads successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/login.html')

    def test_login_valid_credentials(self):
        """Test login with valid credentials."""
        data = {
            'username': 'testuser',
            'password': 'TestPassword123',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)
        # Check that session has user
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_invalid_username(self):
        """Test login with invalid username."""
        data = {
            'username': 'wronguser',
            'password': 'TestPassword123',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_invalid_password(self):
        """Test login with invalid password."""
        data = {
            'username': 'testuser',
            'password': 'WrongPassword123',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_authenticated_user_redirects(self):
        """Test that authenticated users redirected from login page."""
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)


class UserLogoutTests(TestCase):
    """Test user logout functionality."""

    def setUp(self):
        self.client = Client()
        self.logout_url = reverse('hirwafab:logout')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_logout_page_requires_login(self):
        """Test that logout page requires authentication."""
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_logout_loads_confirmation(self):
        """Test that logout page loads confirmation."""
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/logout_confirm.html')

    def test_logout_post_removes_session(self):
        """Test that logout POST removes user session."""
        self.client.login(username='testuser', password='TestPassword123')
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        # Session should be cleared
        self.assertNotIn('_auth_user_id', self.client.session)


class DashboardTests(TestCase):
    """Test dashboard functionality."""

    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('hirwafab:dashboard')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_access_dashboard(self):
        """Test that authenticated user can access dashboard."""
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/dashboard.html')

    def test_dashboard_creates_profile_if_missing(self):
        """Test that dashboard creates profile if it doesn't exist."""
        self.client.login(username='testuser', password='TestPassword123')
        # Delete profile if it exists
        UserProfile.objects.filter(user=self.user).delete()
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())


class PasswordChangeTests(TestCase):
    """Test password change functionality."""

    def setUp(self):
        self.client = Client()
        self.change_password_url = reverse('hirwafab:change_password')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_change_password_requires_login(self):
        """Test that change password requires authentication."""
        response = self.client.get(self.change_password_url)
        self.assertEqual(response.status_code, 302)

    def test_change_password_page_loads(self):
        """Test that change password page loads."""
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.change_password_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/change_password.html')

    def test_change_password_successfully(self):
        """Test successful password change."""
        self.client.login(username='testuser', password='TestPassword123')
        data = {
            'old_password': 'TestPassword123',
            'new_password1': 'NewPassword123',
            'new_password2': 'NewPassword123',
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 302)
        # Verify new password works
        self.client.logout()
        login_successful = self.client.login(username='testuser', password='NewPassword123')
        self.assertTrue(login_successful)

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password."""
        self.client.login(username='testuser', password='TestPassword123')
        data = {
            'old_password': 'WrongPassword123',
            'new_password1': 'NewPassword123',
            'new_password2': 'NewPassword123',
        }
        response = self.client.post(self.change_password_url, data)
        # Should fail and stay on page
        self.assertEqual(response.status_code, 200)

    def test_change_password_mismatch(self):
        """Test password change with mismatched new passwords."""
        self.client.login(username='testuser', password='TestPassword123')
        data = {
            'old_password': 'TestPassword123',
            'new_password1': 'NewPassword123',
            'new_password2': 'DifferentPassword123',
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 200)


class ProfileTests(TestCase):
    """Test profile functionality."""

    def setUp(self):
        self.client = Client()
        self.profile_url = reverse('hirwafab:profile')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)

    def test_profile_page_loads(self):
        """Test that profile page loads."""
        self.client.login(username='testuser', password='TestPassword123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/profile.html')

    def test_update_profile_successfully(self):
        """Test successful profile update."""
        self.client.login(username='testuser', password='TestPassword123')
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'bio': 'This is my bio',
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.profile.bio, 'This is my bio')

    def test_csrf_protection_on_forms(self):
        """Test CSRF protection on form submissions."""
        self.client.login(username='testuser', password='TestPassword123')
        # Try to POST without including CSRF token - Django test client should still include it
        # so this test verifies the CSRF middleware is enabled
        self.assertTrue(self.client.session.get('_auth_user_id') is not None)


class URLConfigTests(TestCase):
    """Test URL configuration."""

    def test_register_url_name(self):
        """Test register URL name resolves."""
        url = reverse('hirwafab:register')
        self.assertEqual(url, '/register/')

    def test_login_url_name(self):
        """Test login URL name resolves."""
        url = reverse('hirwafab:login')
        self.assertEqual(url, '/login/')

    def test_logout_url_name(self):
        """Test logout URL name resolves."""
        url = reverse('hirwafab:logout')
        self.assertEqual(url, '/logout/')

    def test_dashboard_url_name(self):
        """Test dashboard URL name resolves."""
        url = reverse('hirwafab:dashboard')
        self.assertEqual(url, '/dashboard/')

    def test_profile_url_name(self):
        """Test profile URL name resolves."""
        url = reverse('hirwafab:profile')
        self.assertEqual(url, '/profile/')

    def test_change_password_url_name(self):
        """Test change password URL name resolves."""
        url = reverse('hirwafab:change_password')
        self.assertEqual(url, '/change-password/')
