"""
Tests for brute-force protection on the login flow.

Ensures that repeated failed login attempts trigger a lockout and that
successful logins reset the attempt counter.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import UserProfile


class BruteForceTestCase(TestCase):
    """Test cases for brute-force attack prevention."""

    def setUp(self):
        """Set up a test user and clear cache."""
        self.client = Client()
        self.username = 'target_user'
        self.password = 'StrongPass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='target@example.com'
        )
        UserProfile.objects.create(user=self.user, student_id='STU789')
        cache.clear()

    def test_normal_login_works(self):
        """Verify that a legitimate login attempt works on the first try."""
        response = self.client.post(reverse('aline:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.assertRedirects(response, reverse('aline:dashboard'))

    def test_lockout_after_max_attempts(self):
        """Verify that 5 failed attempts trigger a lockout."""
        # 5 failed attempts
        for _ in range(5):
            response = self.client.post(reverse('aline:login'), {
                'username': self.username,
                'password': 'wrongpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid username/email or password.')

        # 6th attempt (even with CORRECT password) should be blocked
        response = self.client.post(reverse('aline:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts.')
        
        # Verify the user is NOT logged in
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_reset_on_successful_login(self):
        """Verify that a successful login resets the failure counter."""
        # 3 failed attempts
        for _ in range(3):
            self.client.post(reverse('aline:login'), {
                'username': self.username,
                'password': 'wrongpassword'
            })
        
        # Successful login
        response = self.client.post(reverse('aline:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302)
        
        # 3 more failed attempts (should NOT trigger lockout because counter was reset)
        for _ in range(3):
            response = self.client.post(reverse('aline:login'), {
                'username': self.username,
                'password': 'wrongpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid username/email or password.')

    def test_lockout_by_ip(self):
        """Verify that brute-forcing multiple accounts from one IP triggers lockout."""
        # Brute force 5 different (non-existent) accounts from the same IP
        for i in range(5):
            self.client.post(reverse('aline:login'), {
                'username': f'unknown_{i}',
                'password': 'wrongpassword'
            })
        
        # 6th attempt with a VALID user from same IP should be blocked
        response = self.client.post(reverse('aline:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts.')

    def test_lockout_isolation_by_username(self):
        """Verify that locking out one user doesn't affect another from a different IP."""
        # Lockout 'target_user' using one IP (simulated via client)
        # Note: Client() keeps track of session but IP is Meta.REMOTE_ADDR. 
        # In a test, it's usually 127.0.0.1.
        
        for _ in range(5):
            self.client.post(reverse('aline:login'), {
                'username': self.username,
                'password': 'wrongpassword'
            })
        
        # Another user from the SAME IP should also be locked out (because we track both)
        # But for this test, let's verify another user IS blocked if they share the IP.
        user2_username = 'other_user'
        User.objects.create_user(username=user2_username, password='Pass123!', email='other@example.com')
        
        response = self.client.post(reverse('aline:login'), {
            'username': user2_username,
            'password': 'Pass123!'
        })
        self.assertContains(response, 'Too many failed login attempts.')
        
        # Now simulate a DIFFERENT IP (using REMOTE_ADDR override)
        response = self.client.post(reverse('aline:login'), {
            'username': user2_username,
            'password': 'Pass123!'
        }, REMOTE_ADDR='192.168.1.1')
        
        # Should NOT be locked out from a different IP for a different user
        self.assertEqual(response.status_code, 302)
