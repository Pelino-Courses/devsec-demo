from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission

class UASAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.instructor = User.objects.create_user(username='instructor', password='testpassword')
        
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.protected_url = reverse('protected_view')
        self.dashboard_url = reverse('instructor_dashboard')

    def test_login_success(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'testpassword'})
        self.assertRedirects(response, reverse('profile'))

    def test_login_failure(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    def test_protected_view_redirects_unauthenticated(self):
        response = self.client.get(self.protected_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.protected_url}")

    def test_protected_view_allows_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        # Anonymous users should hit a 302 login redirect as setup by Django's generic intercept
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.dashboard_url}")

    def test_dashboard_forbids_standard_user(self):
        self.client.login(username='testuser', password='testpassword')
        # Standard users without perms hit a 403 Forbidden
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allows_instructor(self):
        # Assign permission to instructor to grant them privileged access
        perm = Permission.objects.get(codename='can_view_dashboard')
        self.instructor.user_permissions.add(perm)

        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, self.login_url)
