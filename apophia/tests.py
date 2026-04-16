from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile

class UASAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.profile_url = reverse('profile')
        self.dashboard_url = reverse('dashboard')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Password123!',
            'password_confirm': 'Password123!'
        }

    def test_registration_flow(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'apophia/register.html')

        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'Password123!',
            'password2': 'Password123!'
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        user = User.objects.get(username='newuser')
        self.assertTrue(hasattr(user, 'profile'))

    def test_login_logout_flow(self):
        user = User.objects.create_user(username='testuser', password='Password123!')
        
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'Password123!'
        })
        self.assertRedirects(response, self.profile_url)

        response = self.client.post(self.logout_url) 
        self.assertEqual(response.status_code, 302)

    def test_protected_areas(self):
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.profile_url}")

        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.dashboard_url}")

    def test_profile_update(self):
        user = User.objects.create_user(username='updateuser', password='Password123!')
        self.client.login(username='updateuser', password='Password123!')
        
        response = self.client.post(self.profile_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'bio': 'Test bio',
            'location': 'Test City',
            'birth_date': '1990-01-01'
        })
        self.assertRedirects(response, self.profile_url)
        
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.profile.location, 'Test City')

class RBACAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username='staffadmin', password='Password123!', is_staff=True)
        self.regular_user = User.objects.create_user(username='regularuser', password='Password123!', is_staff=False)
        self.staff_dir_url = reverse('staff_directory')
        self.login_url = reverse('login')

    def test_anonymous_access_staff_directory(self):
        # Anonymous users should be redirected to login
        response = self.client.get(self.staff_dir_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

    def test_regular_user_access_staff_directory(self):
        # Authenticated non-staff users should be denied (redirected to login or shown 302 by user_passes_test)
        self.client.login(username='regularuser', password='Password123!')
        response = self.client.get(self.staff_dir_url)
        self.assertEqual(response.status_code, 302) # user_passes_test redirects by default

    def test_staff_user_access_staff_directory(self):
        # Staff users should have access
        self.client.login(username='staffadmin', password='Password123!')
        response = self.client.get(self.staff_dir_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'apophia/staff_directory.html')
        self.assertContains(response, 'regularuser')
        self.assertContains(response, 'staffadmin')
