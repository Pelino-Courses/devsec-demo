from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse


class UserRegistrationTests(TestCase):
    """Tests for user registration functionality."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('mucyo_aime_maxime:register')

    def test_registration_page_loads(self):
        """Test that registration page loads successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/register.html')

    def test_user_registration_success(self):
        """Test successful user registration."""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_registration_duplicate_username(self):
        """Test registration with duplicate username."""
        User.objects.create_user('testuser', 'test@example.com', 'testpass123')
        data = {
            'username': 'testuser',
            'email': 'newemail@example.com',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='newemail@example.com').exists())

    def test_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        User.objects.create_user('testuser', 'test@example.com', 'testpass123')
        data = {
            'username': 'newuser',
            'email': 'test@example.com',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'TestPassword123!',
            'password2': 'DifferentPassword123!',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())


class UserLoginTests(TestCase):
    """Tests for user login functionality."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('mucyo_aime_maxime:login')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')

    def test_login_page_loads(self):
        """Test that login page loads successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/login.html')

    def test_user_login_success(self):
        """Test successful user login."""
        data = {
            'username': 'testuser',
            'password': 'testpass123',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_redirect_from_login(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)


class UserLogoutTests(TestCase):
    """Tests for user logout functionality."""

    def setUp(self):
        self.client = Client()
        self.logout_url = reverse('mucyo_aime_maxime:logout')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')

    def test_logout_requires_login(self):
        """Test that logout requires authentication."""
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_logout_get_not_allowed(self):
        """Test that logout does not allow GET requests."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_user_logout_success(self):
        """Test successful user logout."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UserProfileTests(TestCase):
    """Tests for user profile functionality."""

    def setUp(self):
        self.client = Client()
        self.profile_url = reverse('mucyo_aime_maxime:profile')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')

    def test_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)

    def test_profile_page_loads(self):
        """Test that profile page loads for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/profile.html')

    def test_profile_update_success(self):
        """Test successful profile update."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'email': 'newemail@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')


class PasswordChangeTests(TestCase):
    """Tests for password change functionality."""

    def setUp(self):
        self.client = Client()
        self.password_change_url = reverse('mucyo_aime_maxime:password_change')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'testpass123')

    def test_password_change_requires_login(self):
        """Test that password change page requires authentication."""
        response = self.client.get(self.password_change_url)
        self.assertEqual(response.status_code, 302)

    def test_password_change_page_loads(self):
        """Test that password change page loads for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.password_change_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/password_change.html')

    def test_password_change_success(self):
        """Test successful password change."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'old_password': 'testpass123',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword123!'))

    def test_password_change_wrong_old_password(self):
        """Test password change with wrong old password."""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'old_password': 'wrongpassword',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data)
        self.assertEqual(response.status_code, 200)


class RoleBasedAccessControlTests(TestCase):
    """Tests for role-based access control and authorization."""

    def setUp(self):
        self.client = Client()
        
        # Create test users with different roles
        self.regular_user = User.objects.create_user(
            'regularuser',
            'regular@example.com',
            'testpass123'
        )
        
        self.staff_user = User.objects.create_user(
            'staffuser',
            'staff@example.com',
            'testpass123'
        )
        
        self.instructor_user = User.objects.create_user(
            'instructoruser',
            'instructor@example.com',
            'testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            'adminuser',
            'admin@example.com',
            'testpass123'
        )
        
        # Create and assign groups
        self.staff_group = Group.objects.create(name='Staff')
        self.instructor_group = Group.objects.create(name='Instructor')
        
        self.staff_user.groups.add(self.staff_group)
        self.instructor_user.groups.add(self.instructor_group)
        
        # Set up URLs
        self.staff_dashboard_url = reverse('mucyo_aime_maxime:staff_dashboard')
        self.instructor_reports_url = reverse('mucyo_aime_maxime:instructor_reports')
        self.profile_url = reverse('mucyo_aime_maxime:profile')

    def test_anonymous_user_cannot_access_staff_dashboard(self):
        """Test that anonymous users are redirected from staff dashboard."""
        response = self.client.get(self.staff_dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_regular_user_cannot_access_staff_dashboard(self):
        """Test that regular authenticated users cannot access staff dashboard."""
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(self.staff_dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/profile/', response.url)

    def test_staff_user_can_access_staff_dashboard(self):
        """Test that staff users can access staff dashboard."""
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(self.staff_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/staff_dashboard.html')

    def test_instructor_cannot_access_staff_dashboard(self):
        """Test that instructor users cannot access staff dashboard."""
        self.client.login(username='instructoruser', password='testpass123')
        response = self.client.get(self.staff_dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_staff_dashboard(self):
        """Test that admin/superuser can access staff dashboard."""
        self.client.login(username='adminuser', password='testpass123')
        response = self.client.get(self.staff_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/staff_dashboard.html')

    def test_anonymous_user_cannot_access_instructor_reports(self):
        """Test that anonymous users are redirected from instructor reports."""
        response = self.client.get(self.instructor_reports_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_regular_user_cannot_access_instructor_reports(self):
        """Test that regular users cannot access instructor reports."""
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(self.instructor_reports_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/profile/', response.url)

    def test_staff_cannot_access_instructor_reports(self):
        """Test that staff users cannot access instructor reports."""
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(self.instructor_reports_url)
        self.assertEqual(response.status_code, 302)

    def test_instructor_can_access_instructor_reports(self):
        """Test that instructor users can access instructor reports."""
        self.client.login(username='instructoruser', password='testpass123')
        response = self.client.get(self.instructor_reports_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/instructor_reports.html')

    def test_admin_can_access_instructor_reports(self):
        """Test that admin/superuser can access instructor reports."""
        self.client.login(username='adminuser', password='testpass123')
        response = self.client.get(self.instructor_reports_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/instructor_reports.html')

    def test_authenticated_user_can_access_profile(self):
        """Test that authenticated users can access their profile."""
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/profile.html')

    def test_anonymous_user_redirected_to_login_for_profile(self):
        """Test that anonymous users are redirected to login for profile."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_staff_user_in_correct_group(self):
        """Test that staff user is in Staff group."""
        self.assertTrue(self.staff_user.groups.filter(name='Staff').exists())

    def test_instructor_user_in_correct_group(self):
        """Test that instructor user is in Instructor group."""
        self.assertTrue(self.instructor_user.groups.filter(name='Instructor').exists())

    def test_regular_user_has_no_privileged_groups(self):
        """Test that regular user is not in any privileged groups."""
        self.assertFalse(self.regular_user.groups.filter(name__in=['Staff', 'Instructor']).exists())


class IDORPreventionTests(TestCase):
    """
    Tests for Insecure Direct Object Reference (IDOR) prevention.
    
    These tests verify that users cannot view or modify data belonging to other users
    by changing URL parameters. Object-level access control is enforced.
    """

    def setUp(self):
        self.client = Client()
        
        # Create multiple users for testing
        self.user1 = User.objects.create_user(
            'user1',
            'user1@example.com',
            'password123'
        )
        
        self.user2 = User.objects.create_user(
            'user2',
            'user2@example.com',
            'password123'
        )
        
        self.superuser = User.objects.create_superuser(
            'admin',
            'admin@example.com',
            'password123'
        )

    def test_user_can_access_own_profile_by_id(self):
        """Test that a user can access their own profile via ID URL."""
        self.client.login(username='user1', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user1.id])
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/profile.html')

    def test_user_cannot_access_other_user_profile_by_id(self):
        """Test that a user cannot access another user's profile via ID URL (IDOR prevention)."""
        self.client.login(username='user1', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user2.id])
        response = self.client.get(profile_url)
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_modify_other_user_profile_by_id(self):
        """Test that a user cannot modify another user's profile via ID URL (IDOR prevention)."""
        self.client.login(username='user1', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user2.id])
        data = {
            'email': 'hacker@example.com',
            'first_name': 'Hacker',
            'last_name': 'User',
        }
        response = self.client.post(profile_url, data)
        # Should return 403 Forbidden and not modify user2's data
        self.assertEqual(response.status_code, 403)
        self.user2.refresh_from_db()
        self.assertNotEqual(self.user2.email, 'hacker@example.com')

    def test_unauthenticated_user_cannot_access_profile_by_id(self):
        """Test that unauthenticated users are redirected when trying to access profile by ID."""
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user1.id])
        response = self.client.get(profile_url)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_nonexistent_user_id_returns_error(self):
        """Test that accessing a nonexistent user ID returns appropriate error."""
        self.client.login(username='user1', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[9999])
        response = self.client.get(profile_url)
        # User is authenticated but user ID doesn't exist
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/profile/', response.url)

    def test_superuser_can_access_any_user_profile(self):
        """Test that superuser can access any user's profile (admin privilege)."""
        self.client.login(username='admin', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user1.id])
        response = self.client.get(profile_url)
        # Superuser should have access
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/profile.html')

    def test_superuser_can_modify_any_user_profile(self):
        """Test that superuser can modify any user's profile."""
        self.client.login(username='admin', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile_detail', args=[self.user1.id])
        data = {
            'email': 'modified@example.com',
            'first_name': 'Modified',
            'last_name': 'User',
        }
        response = self.client.post(profile_url, data)
        # Superuser should be able to modify
        self.assertEqual(response.status_code, 302)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.email, 'modified@example.com')

    def test_user_can_update_own_profile_default_view(self):
        """Test that user can update their own profile using default profile view."""
        self.client.login(username='user1', password='password123')
        profile_url = reverse('mucyo_aime_maxime:profile')
        data = {
            'email': 'newemail@example.com',
            'first_name': 'Updated',
            'last_name': 'User',
        }
        response = self.client.post(profile_url, data)
        # Should succeed and redirect
        self.assertEqual(response.status_code, 302)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.email, 'newemail@example.com')

    def test_user_can_change_own_password(self):
        """Test that user can change their own password."""
        self.client.login(username='user1', password='password123')
        password_change_url = reverse('mucyo_aime_maxime:password_change')
        data = {
            'old_password': 'password123',
            'new_password1': 'NewPassword456!',
            'new_password2': 'NewPassword456!',
        }
        response = self.client.post(password_change_url, data)
        # Should succeed
        self.assertEqual(response.status_code, 302)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password('NewPassword456!'))


from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

class PasswordResetTests(TestCase):
    """
    Tests for secure password reset functionality.
    
    Verifies the multi-step reset flow:
    1. Request reset link (email sent)
    2. Access reset confirm page with token
    3. Successfully change password
    4. Link becomes invalid after use
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'resetuser', 
            'reset@example.com', 
            'InitialPass123!'
        )
        self.reset_url = reverse('mucyo_aime_maxime:password_reset')

    def test_password_reset_page_loads(self):
        """Test that the password reset request page loads."""
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/password_reset_form.html')

    def test_password_reset_request_success(self):
        """
        Test that requesting a password reset sends an email.
        
        Verifies security criteria: users are redirected to a success page
        regardless of whether the email exists (preventing enumeration).
        """
        data = {'email': 'reset@example.com'}
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/password-reset/done/', response.url)
        
        # Verify email was "sent" (to outbox in test environment)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset@example.com', mail.outbox[0].to)

    def test_password_reset_nonexistent_email(self):
        """
        Test that requesting a reset for a nonexistent email still shows success.
        
        This is critical for preventing user enumeration.
        """
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(self.reset_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/password-reset/done/', response.url)
        
        # No email should be sent for nonexistent user
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_page_loads(self):
        """Test that the password reset confirmation page loads with a valid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse('mucyo_aime_maxime:password_reset_confirm', 
                             kwargs={'uidb64': uid, 'token': token})
        
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mucyo_aime_maxime/password_reset_confirm.html')

    def test_password_reset_confirm_success(self):
        """Test successful password reset after following the link."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse('mucyo_aime_maxime:password_reset_confirm', 
                             kwargs={'uidb64': uid, 'token': token})
        
        data = {
            'new_password1': 'NewSecurePass999!',
            'new_password2': 'NewSecurePass999!',
        }
        response = self.client.post(confirm_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/password-reset-complete/', response.url)
        
        # Verify password is changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass999!'))

    def test_password_reset_invalid_token(self):
        """Test that an invalid token does not allow resetting password."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = "invalid-token"
        confirm_url = reverse('mucyo_aime_maxime:password_reset_confirm', 
                             kwargs={'uidb64': uid, 'token': token})
        
        response = self.client.get(confirm_url)
        # Should show the error message in the template (validlink = False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reset link was invalid")


class CSRFPreventionTests(TestCase):
    """Tests for Cross-Site Request Forgery (CSRF) protection."""

    def setUp(self):
        # Client with enforce_csrf=True to test CSRF protection
        self.csrf_client = Client(enforce_csrf=True)
        self.login_url = reverse('mucyo_aime_maxime:login')

    def test_post_request_without_csrf_rejected(self):
        """Test that a POST request without a CSRF token is rejected with 403 Forbidden."""
        data = {
            'username': 'testuser',
            'password': 'testpassword',
        }
        # Attempting POST without token
        response = self.csrf_client.post(self.login_url, data)
        self.assertEqual(response.status_code, 403)

    def test_logout_requires_post(self):
        """Test that logout is only possible via POST (already tested but re-verifying)."""
        logout_url = reverse('mucyo_aime_maxime:logout')
        response = self.client.get(logout_url)
        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)


class OpenRedirectTests(TestCase):
    """Tests for Open Redirect vulnerability prevention."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('mucyo_aime_maxime:login')
        self.logout_url = reverse('mucyo_aime_maxime:logout')
        self.register_url = reverse('mucyo_aime_maxime:register')
        self.user = User.objects.create_user('redirectuser', 'redir@example.com', 'testpass123')

    def test_login_safe_redirect(self):
        """Test that login redirects to a safe internal URL."""
        safe_url = '/auth/profile/'
        response = self.client.post(f"{self.login_url}?next={safe_url}", {
            'username': 'redirectuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, safe_url)

    def test_login_unsafe_redirect(self):
        """Test that login rejects an unsafe external redirect and uses default."""
        unsafe_url = 'http://malicious-site.com'
        response = self.client.post(f"{self.login_url}?next={unsafe_url}", {
            'username': 'redirectuser',
            'password': 'testpass123'
        })
        # Should redirect to default profile instead of malicious site
        self.assertRedirects(response, reverse('mucyo_aime_maxime:profile'))

    def test_logout_safe_redirect(self):
        """Test that logout redirects to a safe internal URL."""
        self.client.login(username='redirectuser', password='testpass123')
        safe_url = reverse('mucyo_aime_maxime:login')
        response = self.client.post(f"{self.logout_url}?next={safe_url}")
        self.assertRedirects(response, safe_url)

    def test_logout_unsafe_redirect(self):
        """Test that logout rejects an unsafe external redirect."""
        self.client.login(username='redirectuser', password='testpass123')
        unsafe_url = 'http://malicious-site.com'
        response = self.client.post(f"{self.logout_url}?next={unsafe_url}")
        # Should redirect to default login
        self.assertRedirects(response, reverse('mucyo_aime_maxime:login'))

    def test_register_safe_redirect(self):
        """Test that registration redirects to a safe internal URL."""
        safe_url = '/auth/profile/'
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
        }
        response = self.client.post(f"{self.register_url}?next={safe_url}", data)
        self.assertRedirects(response, safe_url)

    def test_register_unsafe_redirect(self):
        """Test that registration rejects an unsafe external redirect."""
        unsafe_url = 'http://malicious-site.com'
        data = {
            'username': 'newuser2',
            'email': 'new2@example.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
        }
        response = self.client.post(f"{self.register_url}?next={unsafe_url}", data)
        # Should redirect to default profile
        self.assertRedirects(response, reverse('mucyo_aime_maxime:profile'))


from django.core.cache import cache

class LoginBruteforceTests(TestCase):
    """
    Tests for login authentication hardening against brute-force attacks.
    """

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('mucyo_aime_maxime:login')
        self.user = User.objects.create_user('bruteuser', 'brute@example.com', 'InitialPass123!')
        
        # Clear cache before each test to ensure a clean state
        cache.clear()

    def test_login_successful_under_limit(self):
        """Test successful login after a few failed attempts."""
        # Note: Using views.MAX_LOGIN_ATTEMPTS isn't strictly necessary if hardcoded to 5 based on design
        for _ in range(3):
            response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid username or password")
            
        # 4th attempt is successful
        response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'InitialPass123!'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_lockout_after_max_attempts(self):
        """Test that the account is locked out after MAX_LOGIN_ATTEMPTS."""
        # 5 failed attempts
        for _ in range(5):
            response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
            self.assertEqual(response.status_code, 200)
            
        # At this point, the account should be locked.
        # The 5th attempt might also display the lockout message depending on exactly when it's checked,
        # but let's test the 6th attempt specifically.
        
        # 6th attempt (even with correct password) should fail due to lockout
        response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'InitialPass123!'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed attempts. Please try again in 5 minutes.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_counter_resets_on_success(self):
        """Test that a successful login resets the failed attempt counter."""
        # 3 failed attempts
        for _ in range(3):
            self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
            
        # 1 successful attempt
        self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'InitialPass123!'})
        self.client.logout()
        
        # Now we should safely be able to have 3 more failed attempts without getting locked out.
        # If the counter did not reset, the 2nd attempt here (5th overall) would trigger a lockout.
        for _ in range(3):
            response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
            self.assertContains(response, "Invalid username or password")
            self.assertNotContains(response, "Too many failed attempts")

    def test_lockout_isolation(self):
        """Test that a lockout for one user does not affect another user."""
        other_user = User.objects.create_user('otheruser', 'other@example.com', 'OtherPass123!')
        
        # Lock out bruteuser
        for _ in range(5):
            self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
            
        # Verify bruteuser is locked out
        response = self.client.post(self.login_url, {'username': 'bruteuser', 'password': 'wrongpassword'})
        self.assertContains(response, "Too many failed attempts")
        
        # Verify otheruser can still login perfectly fine
        response = self.client.post(self.login_url, {'username': 'otheruser', 'password': 'OtherPass123!'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

