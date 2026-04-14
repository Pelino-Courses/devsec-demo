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
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)

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

