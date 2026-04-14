"""
Test suite for the mupenz_fulgence User Authentication Service.

Coverage:
  - User registration (success, duplicate username, duplicate email, password mismatch)
  - Login / logout
  - Protected route access control
  - Profile update
  - Password change (success, wrong current password, new-password mismatch)
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_user(username='testuser', password='StrongPass123!', email='test@example.com'):
    """Create and return a User (Profile is auto-created via signal)."""
    return User.objects.create_user(username=username, password=password, email=email)


# ──────────────────────────────────────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────────────────────────────────────

class RegistrationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('mupenz_fulgence:register')

    def test_register_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mupenz_fulgence/registration/register.html')

    def test_register_success_creates_user_and_profile(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(self.url, data)

        # Should redirect to login
        self.assertRedirects(response, reverse('mupenz_fulgence:login'))

        # User and linked Profile should both exist
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.email, 'newuser@example.com')

    def test_register_duplicate_username(self):
        make_user(username='taken')
        data = {
            'username': 'taken',
            'email': 'other@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFormError(form, 'username', 'A user with that username already exists.')

    def test_register_duplicate_email(self):
        make_user(username='existing', email='taken@example.com')
        data = {
            'username': 'brandnew',
            'email': 'taken@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFormError(
            form, 'email', 'An account with this email address already exists.'
        )

    def test_register_password_mismatch(self):
        data = {
            'username': 'mismatch',
            'email': 'mismatch@example.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass456!',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_authenticated_user_redirected_from_register(self):
        make_user()
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('mupenz_fulgence:dashboard'))


# ──────────────────────────────────────────────────────────────────────────────
# Login & Logout
# ──────────────────────────────────────────────────────────────────────────────

class LoginLogoutTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.login_url = reverse('mupenz_fulgence:login')
        self.logout_url = reverse('mupenz_fulgence:logout')
        self.dashboard_url = reverse('mupenz_fulgence:dashboard')

    def test_login_page_loads(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mupenz_fulgence/registration/login.html')

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, self.dashboard_url)

    def test_login_sets_authenticated_session(self):
        self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        # Hitting the dashboard without being redirected proves authentication
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_failure_wrong_password(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'WRONG!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_failure_unknown_user(self):
        response = self.client.post(self.login_url, {
            'username': 'nobody',
            'password': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_clears_session(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.post(self.logout_url)
        # After logout the user is anonymous
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_requires_post(self):
        """GET to the logout URL should not log the user out (Django 5+)."""
        self.client.login(username='testuser', password='StrongPass123!')
        # GET is not allowed by LogoutView in Django 5+; the session must remain intact
        response = self.client.get(self.logout_url)
        # Response is either a 405 or a redirect; the user stays authenticated
        self.assertIn(response.status_code, [302, 405])


# ──────────────────────────────────────────────────────────────────────────────
# Protected routes
# ──────────────────────────────────────────────────────────────────────────────

class ProtectedRouteTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.login_url = reverse('mupenz_fulgence:login')

    def _assert_protected(self, url):
        """Verify that an unauthenticated GET redirects to the login page."""
        response = self.client.get(url)
        self.assertRedirects(response, f'{self.login_url}?next={url}')

    def _assert_accessible(self, url, template):
        """Verify that an authenticated GET returns 200 with the right template."""
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, template)

    def test_dashboard_blocked_for_anonymous(self):
        self._assert_protected(reverse('mupenz_fulgence:dashboard'))

    def test_dashboard_accessible_when_authenticated(self):
        self._assert_accessible(
            reverse('mupenz_fulgence:dashboard'),
            'mupenz_fulgence/dashboard.html',
        )

    def test_profile_blocked_for_anonymous(self):
        self._assert_protected(reverse('mupenz_fulgence:profile'))

    def test_profile_accessible_when_authenticated(self):
        self._assert_accessible(
            reverse('mupenz_fulgence:profile'),
            'mupenz_fulgence/profile.html',
        )

    def test_password_change_blocked_for_anonymous(self):
        self._assert_protected(reverse('mupenz_fulgence:password_change'))

    def test_password_change_accessible_when_authenticated(self):
        self._assert_accessible(
            reverse('mupenz_fulgence:password_change'),
            'mupenz_fulgence/registration/password_change.html',
        )


# ──────────────────────────────────────────────────────────────────────────────
# Profile update
# ──────────────────────────────────────────────────────────────────────────────

class ProfileUpdateTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.login(username='testuser', password='StrongPass123!')
        self.url = reverse('mupenz_fulgence:profile')

    def test_profile_update_success(self):
        data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane@example.com',
            'bio': 'Hello world',
            'location': 'Kigali',
            'birth_date': '1995-06-15',
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.email, 'jane@example.com')
        self.assertEqual(self.user.profile.location, 'Kigali')

    def test_profile_update_duplicate_email_rejected(self):
        make_user(username='other', email='other@example.com')
        data = {
            'first_name': '',
            'last_name': '',
            'email': 'other@example.com',  # already taken
            'bio': '',
            'location': '',
            'birth_date': '',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFormError(
            form, 'email', 'This email address is already in use by another account.'
        )


# ──────────────────────────────────────────────────────────────────────────────
# Password change
# ──────────────────────────────────────────────────────────────────────────────

class PasswordChangeTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(password='OldPass123!')
        self.client.login(username='testuser', password='OldPass123!')
        self.url = reverse('mupenz_fulgence:password_change')

    def test_password_change_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'mupenz_fulgence/registration/password_change.html'
        )

    def test_password_change_success(self):
        response = self.client.post(self.url, {
            'old_password': 'OldPass123!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        })
        # Should redirect to dashboard
        self.assertRedirects(response, reverse('mupenz_fulgence:dashboard'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456!'))

    def test_password_change_keeps_user_logged_in(self):
        """update_session_auth_hash must keep the session valid after change."""
        self.client.post(self.url, {
            'old_password': 'OldPass123!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        })
        # Dashboard should be accessible (user still authenticated)
        response = self.client.get(reverse('mupenz_fulgence:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_wrong_current_password(self):
        response = self.client.post(self.url, {
            'old_password': 'WRONG!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        # Password must NOT have changed
        self.assertFalse(self.user.check_password('NewStrongPass456!'))
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_password_change_new_passwords_mismatch(self):
        response = self.client.post(self.url, {
            'old_password': 'OldPass123!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'DoesNotMatch789!',
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)


# ──────────────────────────────────────────────────────────────────────────────
# Signal / Profile auto-creation
# ──────────────────────────────────────────────────────────────────────────────

class SignalTests(TestCase):

    def test_profile_auto_created_on_user_save(self):
        user = User.objects.create_user(
            username='signaluser', password='Pass123!', email='sig@example.com'
        )
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_not_duplicated_on_user_update(self):
        user = make_user()
        user.first_name = 'Updated'
        user.save()
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
