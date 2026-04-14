from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from .models import UserProfile

class UASAuthTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='testuser_a', password='testpassword')
        self.user_b = User.objects.create_user(username='testuser_b', password='testpassword')
        self.instructor = User.objects.create_user(username='instructor', password='testpassword')
        
        # Ensure profiles exist (usually created by signal or in our register view, but for tests we do it manually or assume they exist if register is used)
        # We'll create them explicitly to be safe
        UserProfile.objects.get_or_create(user=self.user_a)
        UserProfile.objects.get_or_create(user=self.user_b)
        UserProfile.objects.get_or_create(user=self.instructor)

        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.protected_url = reverse('protected_view')
        self.dashboard_url = reverse('instructor_dashboard')

    def test_login_success(self):
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'testpassword'})
        self.assertRedirects(response, reverse('profile'))

    def test_login_failure(self):
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    def test_protected_view_redirects_unauthenticated(self):
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 302)

    def test_protected_view_allows_authenticated(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_forbids_standard_user(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allows_instructor(self):
        perm = Permission.objects.get(codename='can_view_dashboard')
        self.instructor.user_permissions.add(perm)
        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, self.login_url)

    # ----------------------------------------
    # IDOR TESTS
    # ----------------------------------------
    
    def test_idor_prevented_forbidden_access(self):
        """User A attempts to access User B's update profile form"""
        self.client.login(username='testuser_a', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_b.id])
        response = self.client.get(update_url)
        # Should be explicitly 403 Forbidden
        self.assertEqual(response.status_code, 403)
        
    def test_idor_allowed_self_access(self):
        """User A accesses their own update profile form"""
        self.client.login(username='testuser_a', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_a.id])
        response = self.client.get(update_url)
        # Should be accessible
        self.assertEqual(response.status_code, 200)

    def test_idor_override_instructor_access(self):
        """Instructor attempts to access User B's update profile form"""
        perm = Permission.objects.get(codename='can_view_dashboard')
        self.instructor.user_permissions.add(perm)
        self.client.login(username='instructor', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_b.id])
        response = self.client.get(update_url)
        # Instructor bypasses object-level block
        self.assertEqual(response.status_code, 200)
