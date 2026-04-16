from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationTestCase(TestCase):
    """Test cases for user registration functionality."""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('aline:register')
        self.login_url = reverse('aline:login')
    
    def test_register_page_loads(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/register.html')
    
    def test_successful_registration(self):
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
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertEqual(user.profile.student_id, 'STU001')
        self.assertRedirects(response, self.login_url)
    
    def test_registration_with_duplicate_email(self):
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
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_registration_with_duplicate_student_id(self):
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
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_password_mismatch(self):
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'student_id': 'STU003',
            'password1': 'SecurePass123!',
            'password2': 'DifferentPass123!',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())


class UserAuthenticationTestCase(TestCase):
    """Test cases for user login and logout functionality."""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('aline:login')
        self.dashboard_url = reverse('aline:dashboard')
        self.logout_url = reverse('aline:logout')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
    
    def test_login_page_loads(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/login.html')
    
    def test_successful_login_with_username(self):
        data = {'username': 'testuser', 'password': 'TestPass123!'}
        response = self.client.post(self.login_url, data, follow=True)
        self.assertEqual(response.wsgi_request.user.username, 'testuser')
        self.assertRedirects(response, self.dashboard_url)
    
    def test_successful_login_with_email(self):
        data = {'username': 'test@example.com', 'password': 'TestPass123!'}
        response = self.client.post(self.login_url, data, follow=True)
        self.assertEqual(response.wsgi_request.user.username, 'testuser')
    
    def test_invalid_login_credentials(self):
        data = {'username': 'testuser', 'password': 'WrongPassword!'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_nonexistent_user_login(self):
        data = {'username': 'nonexistent', 'password': 'SomePass123!'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.dashboard_url)
    
    def test_logout_functionality(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(self.dashboard_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        response = self.client.post(self.logout_url, follow=True)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class AccessControlTestCase(TestCase):
    """Test cases for access control and authentication decorators."""
    
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('aline:dashboard')
        self.profile_url = reverse('aline:profile')
        self.password_change_url = reverse('aline:password_change')
        self.login_url = reverse('aline:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
    
    def test_dashboard_requires_login(self):
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.dashboard_url}')
    
    def test_profile_requires_login(self):
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.profile_url}')
    
    def test_password_change_requires_login(self):
        response = self.client.get(self.password_change_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.password_change_url}')
    
    def test_authenticated_user_can_access_dashboard(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/dashboard.html')
    
    def test_authenticated_user_can_access_profile(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/profile.html')


class PasswordChangeTestCase(TestCase):
    """Test cases for password change functionality."""
    
    def setUp(self):
        self.client = Client()
        self.password_change_url = reverse('aline:password_change')
        self.profile_url = reverse('aline:profile')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword123!'
        )
        UserProfile.objects.create(user=self.user, student_id='STU001')
        self.client.login(username='testuser', password='OldPassword123!')
    
    def test_password_change_page_loads(self):
        response = self.client.get(self.password_change_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aline/password_change.html')
    
    def test_successful_password_change(self):
        data = {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data, follow=True)
        self.assertRedirects(response, self.profile_url)
        self.client.logout()
        login_result = self.client.login(username='testuser', password='NewPassword123!')
        self.assertTrue(login_result)
    
    def test_password_change_with_wrong_current_password(self):
        data = {
            'old_password': 'WrongPassword!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        }
        response = self.client.post(self.password_change_url, data)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        login_result = self.client.login(username='testuser', password='OldPassword123!')
        self.assertTrue(login_result)
    
    def test_password_change_mismatch(self):
        data = {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'DifferentPassword!',
        }
        response = self.client.post(self.password_change_url, data)
        self.assertEqual(response.status_code, 200)
