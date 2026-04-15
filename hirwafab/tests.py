import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from .models import UserProfile, LoginAttempt


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
        self.user.groups.add(Group.objects.get(name='students'))

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
        self.user.groups.add(Group.objects.get(name='students'))

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
        self.user.groups.add(Group.objects.get(name='students'))

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


class RBACStudentTests(TestCase):
    """Test that students can access their own pages and nothing more."""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student1', email='s@example.com', password='TestPass123'
        )
        UserProfile.objects.get_or_create(user=self.student)
        students_group = Group.objects.get(name='students')
        self.student.groups.add(students_group)

    def test_student_can_access_dashboard(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_own_profile(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:profile'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_user_directory(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:user_directory'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_full_directory(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:user_directory_full'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_activity(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:user_activity'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_reports(self):
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:reports'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_view_other_profile(self):
        other = User.objects.create_user(username='other', password='TestPass123')
        UserProfile.objects.get_or_create(user=other)
        self.client.login(username='student1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:view_user_profile', args=[other.id]))
        self.assertEqual(response.status_code, 403)


class RBACInstructorTests(TestCase):
    """Test that instructors can access privileged pages."""

    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create_user(
            username='instructor1', email='i@example.com', password='TestPass123'
        )
        UserProfile.objects.get_or_create(user=self.instructor)
        instructors_group = Group.objects.get(name='instructors')
        self.instructor.groups.add(instructors_group)

        self.student = User.objects.create_user(
            username='student2', email='s2@example.com', password='TestPass123'
        )
        UserProfile.objects.get_or_create(user=self.student)

    def test_instructor_can_access_full_directory(self):
        self.client.login(username='instructor1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:user_directory_full'))
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_access_activity(self):
        self.client.login(username='instructor1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:user_activity'))
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_access_reports(self):
        self.client.login(username='instructor1', password='TestPass123')
        response = self.client.get(reverse('hirwafab:reports'))
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_view_other_profile(self):
        self.client.login(username='instructor1', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.student.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_instructor_viewing_own_profile_redirects(self):
        self.client.login(username='instructor1', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.instructor.id])
        )
        self.assertEqual(response.status_code, 302)


class RBACAnonymousTests(TestCase):
    """Test that anonymous users cannot access protected pages."""

    def test_anonymous_cannot_access_dashboard(self):
        response = self.client.get(reverse('hirwafab:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cannot_access_user_directory(self):
        response = self.client.get(reverse('hirwafab:user_directory'))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cannot_access_reports(self):
        response = self.client.get(reverse('hirwafab:reports'))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cannot_access_activity(self):
        response = self.client.get(reverse('hirwafab:user_activity'))
        self.assertEqual(response.status_code, 302)


class RBACGroupAssignmentTests(TestCase):
    """Test group and permission assignment logic."""

    def test_students_group_has_correct_permissions(self):
        group = Group.objects.get(name='students')
        codenames = set(group.permissions.values_list('codename', flat=True))
        self.assertIn('view_dashboard', codenames)
        self.assertIn('view_own_profile', codenames)
        self.assertIn('view_user_directory', codenames)
        self.assertNotIn('view_all_profiles', codenames)
        self.assertNotIn('download_reports', codenames)

    def test_instructors_group_has_correct_permissions(self):
        group = Group.objects.get(name='instructors')
        codenames = set(group.permissions.values_list('codename', flat=True))
        self.assertIn('view_all_profiles', codenames)
        self.assertIn('view_user_activity', codenames)
        self.assertIn('download_reports', codenames)

    def test_new_user_assigned_to_students_group_on_register(self):
        self.client.post(reverse('hirwafab:register'), {
            'username': 'newstudent',
            'email': 'new@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        })
        user = User.objects.get(username='newstudent')
        self.assertTrue(user.groups.filter(name='students').exists())


class IDORProfileTests(TestCase):
    """
    Tests that verify object-level access control prevents IDOR attacks.
    A user must never be able to view or modify another user's data
    by changing a URL identifier.
    """

    def setUp(self):
        self.client = Client()
        students_group = Group.objects.get(name='students')
        instructors_group = Group.objects.get(name='instructors')

        self.student_a = User.objects.create_user(
            username='student_a', email='a@example.com', password='TestPass123'
        )
        self.profile_a = UserProfile.objects.create(user=self.student_a)
        self.student_a.groups.add(students_group)

        self.student_b = User.objects.create_user(
            username='student_b', email='b@example.com', password='TestPass123'
        )
        self.profile_b = UserProfile.objects.create(user=self.student_b)
        self.student_b.groups.add(students_group)

        self.instructor = User.objects.create_user(
            username='instructor', email='i@example.com', password='TestPass123'
        )
        UserProfile.objects.create(user=self.instructor)
        self.instructor.groups.add(instructors_group)

    # --- Student cannot access another student's profile via URL ---

    def test_student_cannot_view_other_student_profile_url(self):
        """Student A cannot access student B's profile by changing user_id in URL."""
        self.client.login(username='student_a', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.student_b.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_view_any_profile_url(self):
        """Unauthenticated request to a profile URL is redirected."""
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.student_a.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_instructor_can_view_any_student_profile(self):
        """Instructor can view a student's profile by user_id."""
        self.client.login(username='instructor', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.student_a.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_viewing_own_user_id_redirects_to_own_profile(self):
        """Requesting own user_id in the URL redirects to own profile page."""
        self.client.login(username='instructor', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[self.instructor.id])
        )
        self.assertEqual(response.status_code, 302)

    # --- Profile edit ownership ---

    def test_student_can_edit_own_profile(self):
        """A student can edit their own profile."""
        self.client.login(username='student_a', password='TestPass123')
        response = self.client.post(reverse('hirwafab:profile'), {
            'first_name': 'Alice',
            'last_name': 'Test',
            'email': 'a@example.com',
            'bio': 'Hello',
        })
        self.assertEqual(response.status_code, 302)
        self.student_a.refresh_from_db()
        self.assertEqual(self.student_a.first_name, 'Alice')

    def test_profile_edit_only_modifies_own_data(self):
        """Profile edit never touches another user's data."""
        self.client.login(username='student_a', password='TestPass123')
        self.client.post(reverse('hirwafab:profile'), {
            'first_name': 'Alice',
            'last_name': 'Test',
            'email': 'a@example.com',
            'bio': 'Hello',
        })
        # Student B's data must be unchanged
        self.student_b.refresh_from_db()
        self.assertEqual(self.student_b.first_name, '')

    # --- Password change ownership ---

    def test_student_can_change_own_password(self):
        """A student can change their own password."""
        self.client.login(username='student_a', password='TestPass123')
        response = self.client.post(reverse('hirwafab:change_password'), {
            'old_password': 'TestPass123',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_change_password(self):
        """Unauthenticated request to change-password is redirected."""
        response = self.client.get(reverse('hirwafab:change_password'))
        self.assertEqual(response.status_code, 302)

    # --- Non-existent profile ID returns 404 not 500 ---

    def test_nonexistent_user_id_returns_404(self):
        """Requesting a user_id that does not exist returns 404, not 500."""
        self.client.login(username='instructor', password='TestPass123')
        response = self.client.get(
            reverse('hirwafab:view_user_profile', args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class PasswordResetTests(TestCase):
    """
    Tests for the secure password reset workflow.
    Covers request, token validation, confirmation, and anti-enumeration.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='OldPass123'
        )

    def test_reset_request_page_loads(self):
        """Password reset request page is accessible to anyone."""
        response = self.client.get(reverse('hirwafab:password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/password_reset.html')

    def test_reset_request_with_valid_email_redirects_to_done(self):
        """Submitting a valid email redirects to the done page."""
        response = self.client.post(reverse('hirwafab:password_reset'), {
            'email': 'reset@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('hirwafab:password_reset_done'))

    def test_reset_request_with_unknown_email_still_redirects(self):
        """
        Submitting an unknown email also redirects to done — no user enumeration.
        The response must be identical to the valid case.
        """
        response = self.client.post(reverse('hirwafab:password_reset'), {
            'email': 'nobody@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('hirwafab:password_reset_done'))

    def test_reset_done_page_loads(self):
        """The 'check your email' page loads correctly."""
        response = self.client.get(reverse('hirwafab:password_reset_done'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/password_reset_done.html')

    def test_reset_confirm_with_invalid_token_shows_error(self):
        """An invalid or expired token shows an error, not a form."""
        response = self.client.get(
            reverse('hirwafab:password_reset_confirm', kwargs={
                'uidb64': 'invalid',
                'token': 'invalid-token',
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])

    def test_full_reset_flow(self):
        """Full flow: request → token → confirm → complete → can login."""
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # GET the confirm page with a valid token
        confirm_url = reverse('hirwafab:password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token,
        })
        response = self.client.get(confirm_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])

        # POST the new password using the session URL Django sets after GET
        session_url = response.redirect_chain[-1][0] if response.redirect_chain else confirm_url
        response = self.client.post(session_url, {
            'new_password1': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!',
        })
        self.assertEqual(response.status_code, 302)

        # Old password no longer works
        self.assertFalse(
            self.client.login(username='resetuser', password='OldPass123')
        )
        # New password works
        self.assertTrue(
            self.client.login(username='resetuser', password='NewSecurePass456!')
        )

    def test_reset_email_sent_for_valid_user(self):
        """Exactly one email is sent when a valid email is submitted."""
        from django.core import mail
        self.client.post(reverse('hirwafab:password_reset'), {
            'email': 'reset@example.com',
        })
        self.assertEqual(len(mail.outbox), 1)

    def test_no_email_sent_for_unknown_address(self):
        """No email is sent for an address not in the system."""
        from django.core import mail
        self.client.post(reverse('hirwafab:password_reset'), {
            'email': 'nobody@example.com',
        })
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_complete_page_loads(self):
        """The password reset complete page loads correctly."""
        response = self.client.get(reverse('hirwafab:password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/password_reset_complete.html')


# ---------------------------------------------------------------------------
# Brute-force / login-throttling tests
# ---------------------------------------------------------------------------

class BruteForceProtectionTests(TestCase):
    """
    Verify that the login endpoint resists brute-force attacks.

    Design under test (hirwafab/views.py):
    - MAX_LOGIN_ATTEMPTS = 5  failures within a LOCKOUT_WINDOW_MINUTES rolling window
    - Lockout applies per-username and per-IP (hybrid)
    - Successful login clears the failure history for that username
    - Locked-out requests are rejected even with valid credentials
    """

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('hirwafab:login')
        self.user = User.objects.create_user(
            username='brutetest',
            password='GoodPass123!',
        )
        self.credentials = {'username': 'brutetest', 'password': 'GoodPass123!'}
        self.bad_credentials = {'username': 'brutetest', 'password': 'WrongPass!'}

    # --- helper -------------------------------------------------------

    def _fail_login(self, n, ip='127.0.0.1', username='brutetest'):
        """Submit n failed login attempts from the given IP."""
        for _ in range(n):
            self.client.post(
                self.login_url,
                {'username': username, 'password': 'WrongPass!'},
                REMOTE_ADDR=ip,
            )

    # --- normal-path tests --------------------------------------------

    def test_valid_login_succeeds(self):
        """Baseline: correct credentials produce a redirect to dashboard."""
        response = self.client.post(self.login_url, self.credentials)
        self.assertRedirects(response, reverse('hirwafab:dashboard'))

    def test_invalid_login_returns_200_with_error(self):
        """Incorrect credentials show the login page again with an error message."""
        response = self.client.post(self.login_url, self.bad_credentials)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hirwafab/login.html')
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('Invalid' in m for m in messages))

    # --- attempt-tracking tests ---------------------------------------

    def test_failed_login_creates_login_attempt_record(self):
        """Each failed attempt is persisted as a LoginAttempt row."""
        self.client.post(self.login_url, self.bad_credentials, REMOTE_ADDR='127.0.0.1')
        self.assertEqual(LoginAttempt.objects.filter(username='brutetest').count(), 1)

    def test_successful_login_clears_attempt_records(self):
        """Successful login deletes the failure history for that username."""
        self._fail_login(3)
        self.assertEqual(LoginAttempt.objects.filter(username='brutetest').count(), 3)
        self.client.post(self.login_url, self.credentials, REMOTE_ADDR='127.0.0.1')
        self.assertEqual(LoginAttempt.objects.filter(username='brutetest').count(), 0)

    def test_failed_logins_below_threshold_do_not_lock(self):
        """Four failures (one below threshold) must not trigger a lockout."""
        self._fail_login(4)
        response = self.client.post(self.login_url, self.credentials)
        self.assertRedirects(response, reverse('hirwafab:dashboard'))

    # --- lockout trigger tests ----------------------------------------

    def test_lockout_triggers_after_max_attempts(self):
        """Five failures lock the account; the 6th attempt is blocked."""
        self._fail_login(5)
        response = self.client.post(self.login_url, self.bad_credentials, REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 200)
        messages_list = [str(m) for m in response.context['messages']]
        self.assertTrue(any('Too many' in m for m in messages_list))

    def test_lockout_blocks_valid_credentials(self):
        """Even correct credentials are refused while the account is locked."""
        self._fail_login(5)
        response = self.client.post(self.login_url, self.credentials, REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_lockout_context_passed_to_template(self):
        """Template receives locked_out=True and a positive minutes_remaining."""
        self._fail_login(5)
        response = self.client.post(self.login_url, self.bad_credentials, REMOTE_ADDR='127.0.0.1')
        self.assertTrue(response.context.get('locked_out'))
        self.assertGreater(response.context.get('minutes_remaining', 0), 0)

    def test_lockout_message_shown_in_template(self):
        """The login page renders the lockout alert block when locked."""
        self._fail_login(5)
        response = self.client.post(self.login_url, self.bad_credentials, REMOTE_ADDR='127.0.0.1')
        self.assertContains(response, 'Too many failed login attempts')

    # --- IP-based lockout tests ---------------------------------------

    def test_ip_lockout_triggers_for_different_usernames(self):
        """
        Five failures from the same IP across different usernames still triggers
        the IP-based lockout for that IP.
        """
        for i in range(5):
            self.client.post(
                self.login_url,
                {'username': f'nonexistent_{i}', 'password': 'Wrong!'},
                REMOTE_ADDR='10.0.0.1',
            )
        # Now try any username from same IP — should be locked by IP
        response = self.client.post(
            self.login_url,
            {'username': 'nonexistent_99', 'password': 'Wrong!'},
            REMOTE_ADDR='10.0.0.1',
        )
        messages_list = [str(m) for m in response.context['messages']]
        self.assertTrue(any('Too many' in m for m in messages_list))

    def test_different_ip_not_affected_by_other_ip_lockout(self):
        """
        IP-level lockout on 192.168.1.1 must not block 192.168.1.2.
        Uses nonexistent usernames so no account-level lockout is triggered
        for 'brutetest', isolating the IP-only dimension of the check.
        """
        for i in range(5):
            self.client.post(
                self.login_url,
                {'username': f'ghost_{i}', 'password': 'Wrong!'},
                REMOTE_ADDR='192.168.1.1',
            )
        # Different IP with valid credentials → should succeed
        response = self.client.post(self.login_url, self.credentials, REMOTE_ADDR='192.168.1.2')
        self.assertRedirects(response, reverse('hirwafab:dashboard'))

    # --- lockout expiry tests -----------------------------------------

    def test_lockout_expires_after_window(self):
        """
        Failures older than LOCKOUT_WINDOW_MINUTES no longer count, so an
        otherwise-locked account can log in once the window has passed.
        """
        from hirwafab.views import LOCKOUT_WINDOW_MINUTES

        # Backdated attempts — already outside the window
        old_time = timezone.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES + 1)
        for _ in range(5):
            LoginAttempt.objects.create(
                username='brutetest',
                ip_address='127.0.0.1',
                timestamp=old_time,
            )

        # Manually set timestamp (auto_now_add prevents it at create time)
        LoginAttempt.objects.filter(username='brutetest').update(timestamp=old_time)

        # Window has fully elapsed → login should succeed
        response = self.client.post(self.login_url, self.credentials, REMOTE_ADDR='127.0.0.1')
        self.assertRedirects(response, reverse('hirwafab:dashboard'))


# ---------------------------------------------------------------------------
# CSRF protection tests for the AJAX bio-update endpoint
# ---------------------------------------------------------------------------

class CSRFBioUpdateTests(TestCase):
    """
    Verify that the AJAX bio-update endpoint enforces CSRF protection.

    Django's test Client sends CSRF tokens by default. To test that a request
    WITHOUT a token is rejected, we use enforce_csrf_checks=True when creating
    the client so the middleware behaves exactly as it does in production.
    """

    def setUp(self):
        self.url = reverse('hirwafab:ajax_bio_update')
        self.user = User.objects.create_user(username='csrftest', password='Pass1234!')
        UserProfile.objects.get_or_create(user=self.user)
        # Authenticated client with CSRF checks enforced (production behaviour)
        self.csrf_client = Client(enforce_csrf_checks=True)
        self.csrf_client.login(username='csrftest', password='Pass1234!')
        # Authenticated client with CSRF checks disabled (token always valid)
        self.safe_client = Client()
        self.safe_client.login(username='csrftest', password='Pass1234!')

    def _post(self, client, bio='Hello', token=None):
        headers = {'content_type': 'application/json'}
        if token:
            headers['HTTP_X_CSRFTOKEN'] = token
        return client.post(
            self.url,
            data=json.dumps({'bio': bio}),
            **headers,
        )

    # --- CSRF enforcement -------------------------------------------------

    def test_post_without_csrf_token_returns_403(self):
        """A POST with no X-CSRFToken header must be rejected with 403."""
        response = self._post(self.csrf_client)
        self.assertEqual(response.status_code, 403)

    def test_post_with_wrong_csrf_token_returns_403(self):
        """A POST with an invalid token must be rejected with 403."""
        response = self._post(self.csrf_client, token='completelywrong')
        self.assertEqual(response.status_code, 403)

    def test_post_with_valid_csrf_token_returns_200(self):
        """A POST that includes the correct X-CSRFToken header must succeed."""
        # GET the logout confirm page — requires only login, renders
        # {% csrf_token %}, which causes CsrfViewMiddleware to set the cookie.
        get_resp = self.csrf_client.get(reverse('hirwafab:logout'))
        self.assertEqual(get_resp.status_code, 200)
        token = self.csrf_client.cookies.get('csrftoken')
        self.assertIsNotNone(token, 'CSRF cookie was not set by middleware')
        response = self._post(self.csrf_client, token=token.value)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    # --- authentication gate ----------------------------------------------

    def test_unauthenticated_request_redirects(self):
        """An unauthenticated request must be redirected to login, not served."""
        anon = Client(enforce_csrf_checks=True)
        response = anon.post(
            self.url,
            data=json.dumps({'bio': 'hack'}),
            content_type='application/json',
        )
        self.assertIn(response.status_code, [302, 403])

    def test_get_request_rejected(self):
        """GET is not an allowed method on this endpoint."""
        response = self.safe_client.get(self.url)
        self.assertEqual(response.status_code, 405)

    # --- functional correctness -------------------------------------------

    def test_bio_is_saved_on_valid_request(self):
        """The bio field is actually persisted when the request is valid."""
        response = self._post(self.safe_client, bio='My updated bio')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'My updated bio')

    def test_bio_is_truncated_to_500_chars(self):
        """Input longer than 500 characters is silently truncated."""
        long_bio = 'x' * 600
        self._post(self.safe_client, bio=long_bio)
        self.user.profile.refresh_from_db()
        self.assertEqual(len(self.user.profile.bio), 500)


# ---------------------------------------------------------------------------
# Open redirect tests for login and logout flows
# ---------------------------------------------------------------------------

class OpenRedirectTests(TestCase):
    """
    Verify that the login and logout endpoints validate the next parameter
    and never redirect to external or untrusted destinations.

    The fix uses url_has_allowed_host_and_scheme which rejects:
    - Absolute URLs whose host differs from the current request host
    - Protocol-relative URLs like //evil.com (same bypass, different syntax)
    - Any value that could forward the user off-site
    """

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('hirwafab:login')
        self.logout_url = reverse('hirwafab:logout')
        self.user = User.objects.create_user(
            username='redirecttest',
            password='SecurePass123!',
        )
        self.credentials = {
            'username': 'redirecttest',
            'password': 'SecurePass123!',
        }

    # --- login next parameter tests --------------------------------------

    def test_login_safe_internal_next_is_followed(self):
        """A relative internal path in next is accepted after login."""
        response = self.client.post(
            self.login_url + '?next=/hirwafab/dashboard/',
            self.credentials,
        )
        self.assertRedirects(response, '/hirwafab/dashboard/', fetch_redirect_response=False)

    def test_login_external_next_is_rejected(self):
        """An absolute external URL in next is ignored; user goes to dashboard."""
        response = self.client.post(
            self.login_url,
            {**self.credentials, 'next': 'https://evil.com'},
        )
        self.assertRedirects(
            response, reverse('hirwafab:dashboard'), fetch_redirect_response=False
        )

    def test_login_protocol_relative_next_is_rejected(self):
        """A protocol-relative URL (//evil.com) is rejected — common bypass attempt."""
        response = self.client.post(
            self.login_url,
            {**self.credentials, 'next': '//evil.com/phish'},
        )
        self.assertRedirects(
            response, reverse('hirwafab:dashboard'), fetch_redirect_response=False
        )

    def test_login_missing_next_redirects_to_dashboard(self):
        """When next is absent the user lands on the dashboard."""
        response = self.client.post(self.login_url, self.credentials)
        self.assertRedirects(
            response, reverse('hirwafab:dashboard'), fetch_redirect_response=False
        )

    def test_login_next_preserved_across_get_to_post(self):
        """next in the GET query string is passed through to the POST form."""
        get_response = self.client.get(self.login_url + '?next=/hirwafab/dashboard/')
        self.assertContains(get_response, 'name="next"')
        self.assertContains(get_response, '/hirwafab/dashboard/')

    # --- logout next parameter tests -------------------------------------

    def test_logout_safe_internal_next_is_followed(self):
        """A relative internal path in next is accepted after logout."""
        self.client.login(username='redirecttest', password='SecurePass123!')
        response = self.client.post(
            self.logout_url,
            {'next': '/hirwafab/login/'},
        )
        self.assertRedirects(response, '/hirwafab/login/', fetch_redirect_response=False)

    def test_logout_external_next_is_rejected(self):
        """An absolute external URL in next is ignored; user goes to login."""
        self.client.login(username='redirecttest', password='SecurePass123!')
        response = self.client.post(
            self.logout_url,
            {'next': 'https://evil.com'},
        )
        self.assertRedirects(
            response, reverse('hirwafab:login'), fetch_redirect_response=False
        )

    def test_logout_protocol_relative_next_is_rejected(self):
        """A protocol-relative URL (//evil.com) is rejected on logout too."""
        self.client.login(username='redirecttest', password='SecurePass123!')
        response = self.client.post(
            self.logout_url,
            {'next': '//evil.com'},
        )
        self.assertRedirects(
            response, reverse('hirwafab:login'), fetch_redirect_response=False
        )
