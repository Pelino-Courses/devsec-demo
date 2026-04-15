from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile, LoginHistory, PasswordChangeHistory


class RegistrationTests(TestCase):
    """Test user registration functionality"""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('antoine:register')
    
    def test_register_page_loads(self):
        """Test that registration page loads successfully"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/register.html')
    
    def test_register_with_valid_data(self):
        """Test registration with valid data"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_register_password_mismatch(self):
        """Test registration fails with mismatched passwords"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'securepassword123',
            'password2': 'differentpassword',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username"""
        User.objects.create_user('testuser', 'test@example.com', 'password123')
        
        data = {
            'username': 'testuser',
            'email': 'newuser@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
    
    def test_register_duplicate_email(self):
        """Test registration fails with duplicate email"""
        User.objects.create_user('testuser', 'test@example.com', 'password123')
        
        data = {
            'username': 'newuser',
            'email': 'test@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
    
    def test_register_creates_profile(self):
        """Test that user profile is created on registration"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
        }
        self.client.post(self.register_url, data)
        user = User.objects.get(username='testuser')
        self.assertTrue(hasattr(user, 'antoine_profile'))


class LoginTests(TestCase):
    """Test user login functionality"""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('antoine:login')
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'securepassword123'
        )
        UserProfile.objects.create(user=self.user)
    
    def test_login_page_loads(self):
        """Test that login page loads successfully"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/login.html')
    
    def test_login_with_valid_credentials(self):
        """Test login with valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'securepassword123',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_with_invalid_password(self):
        """Test login fails with invalid password"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
    
    def test_login_with_nonexistent_user(self):
        """Test login fails with nonexistent user"""
        data = {
            'username': 'nonexistent',
            'password': 'anypassword',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
    
    def test_login_creates_login_history(self):
        """Test that successful login creates LoginHistory record"""
        data = {
            'username': 'testuser',
            'password': 'securepassword123',
        }
        self.client.post(self.login_url, data)
        
        login_history = LoginHistory.objects.filter(user=self.user, success=True)
        self.assertTrue(login_history.exists())
    
    def test_failed_login_creates_history(self):
        """Test that failed login creates LoginHistory record"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword',
        }
        self.client.post(self.login_url, data)
        
        login_history = LoginHistory.objects.filter(user=self.user, success=False)
        self.assertTrue(login_history.exists())


class LogoutTests(TestCase):
    """Test user logout functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'securepassword123'
        )
        UserProfile.objects.create(user=self.user)
        self.logout_url = reverse('antoine:logout')
    
    def test_logout_requires_authentication(self):
        """Test that logout redirects unauthenticated users"""
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
    
    def test_logout_removes_session(self):
        """Test that logout removes user session"""
        self.client.login(username='testuser', password='securepassword123')
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)


class DashboardTests(TestCase):
    """Test dashboard functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'securepassword123'
        )
        UserProfile.objects.create(user=self.user)
        self.dashboard_url = reverse('antoine:dashboard')
    
    def test_dashboard_requires_authentication(self):
        """Test that dashboard redirects unauthenticated users"""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for authenticated users"""
        self.client.login(username='testuser', password='securepassword123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/dashboard.html')


class ProfileTests(TestCase):
    """Test profile functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'securepassword123'
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.profile_url = reverse('antoine:profile')
    
    def test_profile_requires_authentication(self):
        """Test that profile page redirects unauthenticated users"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
    
    def test_profile_loads_for_authenticated_user(self):
        """Test that profile page loads for authenticated users"""
        self.client.login(username='testuser', password='securepassword123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/profile.html')
    
    def test_profile_update(self):
        """Test updating user profile"""
        self.client.login(username='testuser', password='securepassword123')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'newemail@example.com',
            'bio': 'Test bio',
            'phone_number': '1234567890',
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.email, 'newemail@example.com')


class PasswordChangeTests(TestCase):
    """Test password change functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'oldpassword123'
        )
        UserProfile.objects.create(user=self.user)
        self.change_password_url = reverse('antoine:change_password')
    
    def test_change_password_requires_authentication(self):
        """Test that change password page redirects unauthenticated users"""
        response = self.client.get(self.change_password_url)
        self.assertEqual(response.status_code, 302)
    
    def test_change_password_loads(self):
        """Test that change password page loads for authenticated users"""
        self.client.login(username='testuser', password='oldpassword123')
        response = self.client.get(self.change_password_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/change_password.html')
    
    def test_change_password_with_valid_data(self):
        """Test changing password with valid data"""
        self.client.login(username='testuser', password='oldpassword123')
        data = {
            'old_password': 'oldpassword123',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456',
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify new password works
        self.client.logout()
        login = self.client.login(username='testuser', password='newpassword456')
        self.assertTrue(login)
    
    def test_change_password_with_wrong_old_password(self):
        """Test changing password fails with wrong old password"""
        self.client.login(username='testuser', password='oldpassword123')
        data = {
            'old_password': 'wrongpassword',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456',
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 200)
    
    def test_change_password_creates_history(self):
        """Test that password change creates PasswordChangeHistory record"""
        self.client.login(username='testuser', password='oldpassword123')
        data = {
            'old_password': 'oldpassword123',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456',
        }
        self.client.post(self.change_password_url, data)
        
        history = PasswordChangeHistory.objects.filter(user=self.user)
        self.assertTrue(history.exists())


class LoginHistoryTests(TestCase):
    """Test login history functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'securepassword123'
        )
        UserProfile.objects.create(user=self.user)
        self.login_history_url = reverse('antoine:login_history')
    
    def test_login_history_requires_authentication(self):
        """Test that login history page redirects unauthenticated users"""
        response = self.client.get(self.login_history_url)
        self.assertEqual(response.status_code, 302)
    
    def test_login_history_loads(self):
        """Test that login history page loads for authenticated users"""
        self.client.login(username='testuser', password='securepassword123')
        response = self.client.get(self.login_history_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'antoine/login_history.html')

