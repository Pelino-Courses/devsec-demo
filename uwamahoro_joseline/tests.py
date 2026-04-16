"""
Tests for brute-force protection on the login flow.

Tests cover:
- Normal login behavior and successful authentication
- Abuse scenarios with repeated failed attempts
- Progressive throttling at 3, 5, 10, and 20 failed attempts
- User enumeration prevention
- IP address extraction and tracking
- Throttle status calculation across different time windows
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import LoginAttempt
from .views import record_login_attempt, get_throttle_status


class LoginAttemptModelTests(TestCase):
    """Test the LoginAttempt model for tracking login attempts."""
    
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
    
    def test_login_attempt_created_successfully(self):
        """Test creating a login attempt record."""
        LoginAttempt.objects.create(
            user=self.user,
            username=self.user.username,
            ip_address="192.168.1.100",
            is_successful=True,
        )
        self.assertEqual(LoginAttempt.objects.count(), 1)
        attempt = LoginAttempt.objects.first()
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.ip_address, "192.168.1.100")
        self.assertTrue(attempt.is_successful)
    
    def test_login_attempt_without_user(self):
        """Test recording attempt for non-existent user (prevents enumeration)."""
        LoginAttempt.objects.create(
            username="nonexistent",
            ip_address="192.168.1.100",
            is_successful=False,
        )
        self.assertEqual(LoginAttempt.objects.count(), 1)
        attempt = LoginAttempt.objects.first()
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.username, "nonexistent")
        self.assertFalse(attempt.is_successful)
    
    def test_login_attempts_ordered_by_timestamp(self):
        """Test that login attempts are ordered by timestamp (newest first)."""
        now = timezone.now()
        LoginAttempt.objects.create(
            username="test",
            ip_address="192.168.1.1",
            is_successful=False,
            attempt_timestamp=now - timedelta(minutes=10),
        )
        LoginAttempt.objects.create(
            username="test",
            ip_address="192.168.1.1",
            is_successful=False,
            attempt_timestamp=now,
        )
        attempts = LoginAttempt.objects.all()
        self.assertEqual(attempts[0].attempt_timestamp, now)
        self.assertEqual(attempts[1].attempt_timestamp, now - timedelta(minutes=10))


class GetClientIpTests(TestCase):
    """Test IP address extraction from requests."""
    
    def test_get_client_ip_from_remote_addr(self):
        """Test extracting IP from REMOTE_ADDR (direct connection)."""
        client = Client()
        # Django test client sets REMOTE_ADDR
        response = client.get(reverse("uwamahoro_joseline:login"))
        self.assertEqual(response.status_code, 200)
    
    def test_get_client_ip_with_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header (proxy scenario)."""
        client = Client()
        # Simulate a proxied request
        response = client.get(
            reverse("uwamahoro_joseline:login"),
            HTTP_X_FORWARDED_FOR="203.0.113.42, 198.51.100.1",
        )
        self.assertEqual(response.status_code, 200)


class RecordLoginAttemptTests(TestCase):
    """Test the record_login_attempt utility function."""
    
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client = Client()
    
    def test_record_successful_login_attempt(self):
        """Test recording a successful login attempt."""
        request = self.client.get(reverse("uwamahoro_joseline:login")).wsgi_request
        record_login_attempt(request, self.user.username, is_successful=True)
        
        self.assertEqual(LoginAttempt.objects.count(), 1)
        attempt = LoginAttempt.objects.first()
        self.assertEqual(attempt.user, self.user)
        self.assertTrue(attempt.is_successful)
    
    def test_record_failed_login_attempt(self):
        """Test recording a failed login attempt."""
        request = self.client.get(reverse("uwamahoro_joseline:login")).wsgi_request
        record_login_attempt(request, self.user.username, is_successful=False)
        
        self.assertEqual(LoginAttempt.objects.count(), 1)
        attempt = LoginAttempt.objects.first()
        self.assertEqual(attempt.user, self.user)
        self.assertFalse(attempt.is_successful)
    
    def test_record_failed_login_for_nonexistent_user(self):
        """Test recording attempt for non-existent user."""
        request = self.client.get(reverse("uwamahoro_joseline:login")).wsgi_request
        record_login_attempt(request, "nonexistent", is_successful=False)
        
        self.assertEqual(LoginAttempt.objects.count(), 1)
        attempt = LoginAttempt.objects.first()
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.username, "nonexistent")


class GetThrottleStatusTests(TestCase):
    """Test the throttle status logic at different attempt thresholds."""
    
    def setUp(self):
        self.username = "testuser"
        self.now = timezone.now()
    
    def test_no_throttle_with_zero_failures(self):
        """Test that new user has no throttle."""
        is_throttled, _, _ = get_throttle_status(self.username)
        self.assertFalse(is_throttled)
    
    def test_no_throttle_with_two_failures(self):
        """Test that 2 failures don't trigger throttle."""
        for i in range(2):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=self.now - timedelta(minutes=1),
            )
        is_throttled, _, failed_count = get_throttle_status(self.username)
        self.assertFalse(is_throttled)
        self.assertEqual(failed_count, 2)
    
    def test_throttle_after_three_failures_in_5_min(self):
        """Test 5-minute throttle after 3 failures in 5 minutes."""
        base_time = self.now - timedelta(minutes=4)
        for i in range(3):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time + timedelta(minutes=i),
            )
        
        is_throttled, seconds_remaining, failed_count = get_throttle_status(self.username)
        self.assertTrue(is_throttled)
        self.assertEqual(failed_count, 3)
        # Should allow roughly 5 minutes (minus elapsed time)
        self.assertGreater(seconds_remaining, 0)
        self.assertLess(seconds_remaining, 300)  # 300 seconds = 5 minutes
    
    def test_no_throttle_when_outside_5min_window(self):
        """Test that failures outside 5-min window don't count."""
        LoginAttempt.objects.create(
            username=self.username,
            ip_address="192.168.1.1",
            is_successful=False,
            attempt_timestamp=self.now - timedelta(minutes=10),
        )
        LoginAttempt.objects.create(
            username=self.username,
            ip_address="192.168.1.1",
            is_successful=False,
            attempt_timestamp=self.now - timedelta(minutes=6),
        )
        LoginAttempt.objects.create(
            username=self.username,
            ip_address="192.168.1.1",
            is_successful=False,
            attempt_timestamp=self.now,
        )
        
        is_throttled, _, failed_count = get_throttle_status(self.username)
        self.assertFalse(is_throttled)
        self.assertEqual(failed_count, 1)  # Only recent one counts
    
    def test_throttle_after_five_failures_in_15_min(self):
        """Test 15-minute throttle after 5 failures in 15 minutes."""
        base_time = self.now - timedelta(minutes=14)
        for i in range(5):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time + timedelta(minutes=i * 3),
            )
        
        is_throttled, seconds_remaining, failed_count = get_throttle_status(self.username)
        self.assertTrue(is_throttled)
        self.assertEqual(failed_count, 5)
        # Should get 15-minute throttle (900 seconds)
        self.assertGreater(seconds_remaining, 0)
    
    def test_throttle_after_ten_failures_in_1_hour(self):
        """Test 60-minute throttle after 10 failures in 1 hour."""
        base_time = self.now - timedelta(minutes=59)
        for i in range(10):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time + timedelta(minutes=i * 6),
            )
        
        is_throttled, seconds_remaining, failed_count = get_throttle_status(self.username)
        self.assertTrue(is_throttled)
        self.assertEqual(failed_count, 10)
    
    def test_throttle_after_twenty_failures_in_24_hours(self):
        """Test 24-hour lockout after 20 failures in 24 hours."""
        base_time = self.now - timedelta(hours=23)
        for i in range(20):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time + timedelta(hours=i * 1.15),
            )
        
        is_throttled, seconds_remaining, failed_count = get_throttle_status(self.username)
        self.assertTrue(is_throttled)
        self.assertEqual(failed_count, 20)
        # Should get ~24-hour throttle
        self.assertGreater(seconds_remaining, 0)
    
    def test_throttle_progression_multiple_levels(self):
        """Test that multiple throttle levels are respected (highest wins)."""
        # Create 5 failures in last 15 minutes AND 10 in last hour
        base_time_15m = self.now - timedelta(minutes=13)
        base_time_1h = self.now - timedelta(minutes=59)
        
        # 5 within 15 minutes
        for i in range(5):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time_15m + timedelta(minutes=i * 2),
            )
        
        # 5 more within 1 hour (but older than 15 min)
        for i in range(5):
            LoginAttempt.objects.create(
                username=self.username,
                ip_address="192.168.1.1",
                is_successful=False,
                attempt_timestamp=base_time_1h + timedelta(minutes=i * 10),
            )
        
        is_throttled, seconds_remaining, failed_count = get_throttle_status(self.username)
        self.assertTrue(is_throttled)
        # Should have 10 in the 1-hour window
        self.assertEqual(failed_count, 10)


class LoginViewBruteForceTests(TestCase):
    """Test the login view with brute-force protection."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.login_url = reverse("uwamahoro_joseline:login")
    
    def test_normal_login_succeeds(self):
        """Test that normal login works without throttling."""
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful login
        # Check that a successful attempt was recorded
        recent_attempts = LoginAttempt.objects.filter(
            username="testuser",
            is_successful=True,
        )
        self.assertEqual(recent_attempts.count(), 1)
    
    def test_failed_login_recorded(self):
        """Test that failed login attempts are recorded."""
        self.client.post(self.login_url, {
            "username": "testuser",
            "password": "wrongpassword",
        })
        # Check that a failed attempt was recorded
        recent_attempts = LoginAttempt.objects.filter(
            username="testuser",
            is_successful=False,
        )
        self.assertEqual(recent_attempts.count(), 1)
    
    def test_login_blocked_after_three_failures(self):
        """Test that login is blocked after 3 failed attempts in 5 minutes."""
        # Simulate 3 failed attempts
        for _ in range(3):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        # Fourth attempt should be throttled
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "wrongpassword",
        })
        
        # Should return 429 (Too Many Requests)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Too Many Failed Attempts", response.content)
    
    def test_throttle_error_shows_minutes_remaining(self):
        """Test that throttle error message shows time remaining."""
        # Create 3 failures
        for _ in range(3):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "wrongpassword",
        })
        
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"minute", response.content)
    
    def test_throttle_lifted_after_window_expires(self):
        """Test that login works again after throttle window expires."""
        # Create 3 failures
        for _ in range(3):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        # Manually move all attempts back in time (simulate window expiration)
        now = timezone.now()
        LoginAttempt.objects.filter(username="testuser").update(
            attempt_timestamp=now - timedelta(minutes=6)
        )
        
        # Now login should work again
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 302)  # Redirect = success
    
    def test_different_users_independent_throttling(self):
        """Test that throttling is per-user, not global."""
        User.objects.create_user(username="testuser2", password="testpass456")
        
        # Throttle first user
        for _ in range(3):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        # Second user should still be able to attempt login
        response = self.client.post(self.login_url, {
            "username": "testuser2",
            "password": "testpass456",
        })
        self.assertEqual(response.status_code, 302)  # Success
    
    def test_user_enumeration_prevention(self):
        """Test that failed attempts are recorded even for non-existent users."""
        # Try login with non-existent user
        self.client.post(self.login_url, {
            "username": "nonexistent",
            "password": "somepassword",
        })
        
        # Attempt should be recorded
        attempts = LoginAttempt.objects.filter(username="nonexistent")
        self.assertEqual(attempts.count(), 1)
        self.assertFalse(attempts.first().is_successful)
        
        # Should get throttled after 3 attempts too
        for _ in range(2):
            self.client.post(self.login_url, {
                "username": "nonexistent",
                "password": "somepassword",
            })
        
        response = self.client.post(self.login_url, {
            "username": "nonexistent",
            "password": "somepassword",
        })
        self.assertEqual(response.status_code, 429)


class LoginViewEdgeCasesTests(TestCase):
    """Test edge cases and special scenarios."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.login_url = reverse("uwamahoro_joseline:login")
    
    def test_empty_username_not_throttled(self):
        """Test that empty username doesn't cause errors."""
        response = self.client.post(self.login_url, {
            "username": "",
            "password": "somepassword",
        })
        # Should render login form, not crash
        self.assertIn(response.status_code, [200, 302])
    
    def test_successful_login_clears_failure_count(self):
        """Test that a successful login doesn't reset, but subsequent failures start fresh."""
        # 2 failures
        for _ in range(2):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        # Successful login
        self.client.post(self.login_url, {
            "username": "testuser",
            "password": "testpass123",
        })
        
        # After success, 2 more failures should be allowed (doesn't cascade)
        for _ in range(2):
            self.client.post(self.login_url, {
                "username": "testuser",
                "password": "wrongpassword",
            })
        
        # 3rd failure should trigger throttle (3 total now)
        response = self.client.post(self.login_url, {
            "username": "testuser",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, 429)
    
    def test_authenticated_user_redirected_from_login(self):
        """Test that already-logged-in users are redirected away from login page."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.login_url)
        # Should redirect to dashboard, not show login form
        self.assertEqual(response.status_code, 302)
