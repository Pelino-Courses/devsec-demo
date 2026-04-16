# Create your tests here.
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class IDORProtectionTests(TestCase):
    """Test suite for Indirect Object Reference (IDOR) vulnerability prevention."""

    def setUp(self):
        """Set up test users and profiles."""
        self.client = Client()
        
        # Create regular user 1
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.profile1 = UserProfile.objects.create(user=self.user1, role='viewer')
        
        # Create regular user 2
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.profile2 = UserProfile.objects.create(user=self.user2, role='viewer')
        
        # Create admin user
        self.admin_user = User.objects.create_user(username='admin', password='pass123')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, role='admin')

    def test_user_can_view_own_profile_by_id(self):
        """Test that a user can view their own profile."""
        self.client.login(username='user1', password='pass123')
        response = self.client.get(reverse('profile_by_id', args=[self.user1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.profile1.user.username, response.content.decode())

    def test_user_cannot_view_other_user_profile(self):
        """Test IDOR protection: User cannot view another user's profile."""
        self.client.login(username='user1', password='pass123')
        response = self.client.get(reverse('profile_by_id', args=[self.user2.id]))
        # Should redirect to home due to permission denied
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/', response.url)

    def test_admin_can_view_any_profile(self):
        """Test that admin user CAN view any profile."""
        self.client.login(username='admin', password='pass123')
        response = self.client.get(reverse('profile_by_id', args=[self.user1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.profile1.user.username, response.content.decode())

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse('profile_by_id', args=[self.user1.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login', response.url)

    def test_nonexistent_user_profile_returns_error(self):
        """Test that accessing a nonexistent user profile shows appropriate message."""
        self.client.login(username='user1', password='pass123')
        response = self.client.get(reverse('profile_by_id', args=[9999]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/', response.url)
