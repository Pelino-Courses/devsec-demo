from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationTestCase(TestCase):
    """Test cases for user registration functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.register_url = reverse('aline_uwamahoro:register')
        self.login_url = reverse('aline_uwamahoro:login')
    
    def test_register_page_loads(self):
        """Test that registration page loads successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline_uwamahoro/register.html')
    
    def test_successful_registration(self):
        """Test successful user registration."""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'student_id': 'STU001',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        }
        response = self.client.post(self.register_url, data, follow=True)
        
        # User should be created
        self.assertTrue(User.objects.filter(username='testuser').exists())
        
        # Associated UserProfile should be created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.profile.student_id, 'STU001')
        
        # Should redirect to login page
        self.assertRedirects(response, self.login_url)
    
    def test_registration_with_duplicate_email(self):
        """Test registration fails with duplicate email."""
        # Create initial user
        User.objects.create_user(
            username='existing',
            email='duplicate@example.com',
            password='Pass123!'
        )
        
        data = {
            'username': 'newuser',
            'email': 'duplicate@example.com',
            'student_id': 'STU002',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        }
        response = self.client.post(self.register_url, data)
        
        # Should keep user on registration page
        self.assertEqual(response.status_code, 200)
        
        # New user should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_registration_with_duplicate_student_id(self):
        """Test registration fails with duplicate student ID."""
        # Create initial user with profile
        user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='Pass123!'
        )
        UserProfile.objects.create(user=user, student_id='STU001')
        
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'student_id': 'STU001',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        }
        response = self.client.post(self.register_url, data)
        
        # Should keep user on registration page
        self.assertEqual(response.status_code, 200)
        
        # New user should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_password_mismatch(self):
        """Test registration fails when passwords don't match."""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'student_id': 'STU003',
            'password1': 'SecurePass123!',
            'password2': 'DifferentPass123!',
        }
        response = self.client.post(self.register_url, data)
        
        # Should keep user on registration page
        self.assertEqual(response.status_code, 200)
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='testuser').exists())


class UserAuthenticationTestCase(TestCase):
    """Test cases for user login and logout functionality."""
    
    def setUp(self):
        """Set up test client and test user."""
        self.client = Client()
        self.login_url = reverse('aline_uwamahoro:login')
        self.dashboard_url = reverse('aline_uwamahoro:dashboard')
        self.logout_url = reverse('aline_uwamahoro:logout')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
    
    def test_login_page_loads(self):
        """Test that login page loads successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline_uwamahoro/login.html')
    
    def test_successful_login_with_username(self):
        """Test successful login using username."""
        data = {
            'username': 'testuser',
            'password': 'TestPass123!',
        }
        response = self.client.post(self.login_url, data, follow=True)
        
        # Check if user is authenticated in session
        self.assertEqual(response.wsgi_request.user.username, 'testuser')
        
        # Should redirect to dashboard
        self.assertRedirects(response, self.dashboard_url)
    
    def test_successful_login_with_email(self):
        """Test successful login using email address."""
        data = {
            'username': 'test@example.com',
            'password': 'TestPass123!',
        }
        response = self.client.post(self.login_url, data, follow=True)
        
        # Check if user is authenticated
        self.assertEqual(response.wsgi_request.user.username, 'testuser')
    
    def test_invalid_login_credentials(self):
        """Test login fails with invalid password."""
        data = {
            'username': 'testuser',
            'password': 'WrongPassword!',
        }
        response = self.client.post(self.login_url, data)
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_nonexistent_user_login(self):
        """Test login fails for non-existent user."""
        data = {
            'username': 'nonexistent',
            'password': 'SomePass123!',
        }
        response = self.client.post(self.login_url, data)
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_authenticated_user_redirected_from_login(self):
        """Test that logged-in users are redirected from login page."""
        # Login user
        self.client.login(username='testuser', password='TestPass123!')
        
        response = self.client.get(self.login_url)
        
        # Should redirect to dashboard
        self.assertRedirects(response, self.dashboard_url)
    
    def test_logout_functionality(self):
        """Test logout functionality."""
        # Login user
        self.client.login(username='testuser', password='TestPass123!')
        
        # Verify user is logged in
        response = self.client.get(self.dashboard_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        
        # Logout
        response = self.client.get(self.logout_url, follow=True)
        
        # User should be logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class AccessControlTestCase(TestCase):
    """Test cases for access control and authentication decorators."""
    
    def setUp(self):
        """Set up test client and test user."""
        self.client = Client()
        self.dashboard_url = reverse('aline_uwamahoro:dashboard')
        self.profile_url = reverse('aline_uwamahoro:profile')
        self.password_change_url = reverse('aline_uwamahoro:password_change')
        self.login_url = reverse('aline_uwamahoro:login')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
    
    def test_dashboard_requires_login(self):
        """Test that dashboard is only accessible to authenticated users."""
        response = self.client.get(self.dashboard_url)
        
        # Should redirect to login
        self.assertRedirects(response, f'{self.login_url}?next={self.dashboard_url}')
    
    def test_profile_requires_login(self):
        """Test that profile page requires authentication."""
        response = self.client.get(self.profile_url)
        
        # Should redirect to login
        self.assertRedirects(response, f'{self.login_url}?next={self.profile_url}')
    
    def test_password_change_requires_login(self):
        """Test that password change requires authentication."""
        response = self.client.get(self.password_change_url)
        
        # Should redirect to login
        self.assertRedirects(response, f'{self.login_url}?next={self.password_change_url}')
    
    def test_authenticated_user_can_access_dashboard(self):
        """Test that authenticated user can access dashboard."""
        self.client.login(username='testuser', password='TestPass123!')
        
        response = self.client.get(self.dashboard_url)
        
        # Should load successfully
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline_uwamahoro/dashboard.html')
    
    def test_authenticated_user_can_access_profile(self):
        """Test that authenticated user can access profile page."""
        self.client.login(username='testuser', password='TestPass123!')
        
        response = self.client.get(self.profile_url)
        
        # Should load successfully
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline_uwamahoro/profile.html')


class PasswordChangeTestCase(TestCase):
    """Test cases for password change functionality."""
    
    def setUp(self):
        """Set up test client and test user."""
        self.client = Client()
        self.password_change_url = reverse('aline_uwamahoro:password_change')
        self.profile_url = reverse('aline_uwamahoro:profile')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
        
        # Login
        self.client.login(username='testuser', password='OldPassword123!')
    
    def test_password_change_page_loads(self):
        """Test that password change page loads for authenticated user."""
        response = self.client.get(self.password_change_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline_uwamahoro/password_change.html')
    
    def test_successful_password_change(self):
        """Test successful password change."""
        data = {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data, follow=True)
        
        # Should redirect to profile
        self.assertRedirects(response, self.profile_url)
        
        # User should be able to login with new password
        self.client.logout()
        login_result = self.client.login(
            username='testuser',
            password='NewPassword123!'
        )
        self.assertTrue(login_result)
    
    def test_password_change_with_wrong_current_password(self):
        """Test password change fails with wrong current password."""
        data = {
            'old_password': 'WrongPassword!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data)
        
        # Should stay on password change page
        self.assertEqual(response.status_code, 200)
        
        # Old password should still work
        self.client.logout()
        login_result = self.client.login(
            username='testuser',
            password='OldPassword123!'
        )
        self.assertTrue(login_result)
    
    def test_password_change_mismatch(self):
        """Test password change fails when new passwords don't match."""
        data = {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'DifferentPassword!',
        }
        response = self.client.post(self.password_change_url, data)
        
        # Should stay on password change page
        self.assertEqual(response.status_code, 200)


class UserProfileTestCase(TestCase):
    """Test cases for user profile model and functionality."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            student_id='STU001'
        )
    
    def test_user_profile_creation(self):
        """Test that UserProfile is created correctly."""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.student_id, 'STU001')
    
    def test_user_profile_string_representation(self):
        """Test UserProfile string representation."""
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.save()
        
        expected = f"Test User (STU001)"
        self.assertEqual(str(self.profile), expected)
    
    def test_user_profile_get_full_name(self):
        """Test get_full_name method."""
        self.user.first_name = 'John'
        self.user.save()
        
        full_name = self.profile.get_full_name()
        self.assertEqual(full_name, 'John')

