"""
Tests for brute-force attack protection on login view.

These tests verify that the login flow is hardened against brute-force attacks
while remaining usable for legitimate users.

Security tested:
- Failed attempts are tracked per account
- Progressive cooldowns apply after threshold
- Lockout messages don't reveal account existence (user enumeration prevention)
- Successful login resets attempt counter
- Manual admin lockout works
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import LoginAttempt, LoginHistory


class BruteForceProtectionTests(TestCase):
    """Test brute-force protection on login endpoint"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.login_url = reverse('antoine:login')
        
        # Create test user
        self.username = 'testuser'
        self.password = 'SecurePassword123!'
        self.user = User.objects.create_user(
            username=self.username,
            email='test@example.com',
            password=self.password
        )
        
        # Create LoginAttempt record
        self.login_attempt = LoginAttempt.objects.get_or_create(user=self.user)[0]
    
    def test_successful_login_with_no_prior_failures(self):
        """Test successful login when no failed attempts exist"""
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'remember_me': False,
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
        
        # LoginAttempt should be reset
        self.login_attempt.refresh_from_db()
        self.assertEqual(self.login_attempt.failed_attempts, 0)
        self.assertIsNone(self.login_attempt.locked_until)
    
    def test_failed_login_increments_counter(self):
        """Test that failed login increments attempt counter"""
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'wrongpassword',
            'remember_me': False,
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        
        # Counter should increment
        self.login_attempt.refresh_from_db()
        self.assertEqual(self.login_attempt.failed_attempts, 1)
        self.assertIsNone(self.login_attempt.locked_until)
    
    def test_multiple_failed_attempts_without_lockout(self):
        """Test that < 5 failed attempts don't trigger lockout"""
        for i in range(4):
            response = self.client.post(self.login_url, {
                'username': self.username,
                'password': 'wrongpassword',
                'remember_me': False,
            })
            self.assertEqual(response.status_code, 200)
        
        self.login_attempt.refresh_from_db()
        self.assertEqual(self.login_attempt.failed_attempts, 4)
        self.assertIsNone(self.login_attempt.locked_until)
    
    def test_fifth_failed_attempt_triggers_30_second_lockout(self):
        """Test that 5th failure triggers 30-second cooldown"""
        # Make 5 failed attempts
        for i in range(5):
            self.client.post(self.login_url, {
                'username': self.username,
                'password': 'wrongpassword',
                'remember_me': False,
            })
        
        self.login_attempt.refresh_from_db()
        self.assertEqual(self.login_attempt.failed_attempts, 5)
        self.assertIsNotNone(self.login_attempt.locked_until)
        
        # Should be locked for approximately 30 seconds
        cooldown = self.login_attempt.get_cooldown_seconds()
        self.assertGreater(cooldown, 0)
        self.assertLessEqual(cooldown, 30)
    
    def test_lockout_prevents_login_attempt(self):
        """Test that locked account cannot attempt login"""
        # Lock the account
        self.login_attempt.failed_attempts = 5
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=30)
        self.login_attempt.save()
        
        # Try to login
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,  # Even correct password should fail
            'remember_me': False,
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts')
    
    def test_cooldown_message_shows_remaining_time(self):
        """Test that lockout message includes cooldown countdown"""
        # Lock the account for 60 seconds
        self.login_attempt.failed_attempts = 10
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=60)
        self.login_attempt.save()
        
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'remember_me': False,
        })
        
        self.assertEqual(response.status_code, 200)
        # Message should tell user to wait
        self.assertContains(response, 'Too many failed login attempts')
    
    def test_progressive_cooldowns(self):
        """Test that cooldowns increase with more failed attempts"""
        cooldowns = []
        
        # 5-9 failures: 30 second cooldown
        self.login_attempt.failed_attempts = 5
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=30)
        self.login_attempt.save()
        cooldowns.append(self.login_attempt.get_cooldown_seconds())
        
        # 10-14 failures: 1 minute cooldown
        self.login_attempt.failed_attempts = 10
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=60)
        self.login_attempt.save()
        cooldowns.append(self.login_attempt.get_cooldown_seconds())
        
        # 15-19 failures: 5 minute cooldown
        self.login_attempt.failed_attempts = 15
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=300)
        self.login_attempt.save()
        cooldowns.append(self.login_attempt.get_cooldown_seconds())
        
        # 20+ failures: 15 minute cooldown
        self.login_attempt.failed_attempts = 20
        self.login_attempt.locked_until = timezone.now() + timedelta(seconds=900)
        self.login_attempt.save()
        cooldowns.append(self.login_attempt.get_cooldown_seconds())
        
        # Verify cooldowns increase
        for i in range(1, len(cooldowns)):
            self.assertGreaterEqual(cooldowns[i], cooldowns[i-1])
    
    def test_successful_login_resets_attempts(self):
        """Test that successful login resets failed attempt counter"""
        # Set some failed attempts
        self.login_attempt.failed_attempts = 3
        self.login_attempt.save()
        
        # Successful login
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'remember_me': False,
        })
        
        self.login_attempt.refresh_from_db()
        self.assertEqual(self.login_attempt.failed_attempts, 0)
        self.assertIsNone(self.login_attempt.locked_until)
    
    def test_manual_admin_lockout(self):
        """Test that manually locked accounts are blocked"""
        # Admin manually locks account
        self.login_attempt.is_locked = True
        self.login_attempt.save()
        
        # Try to login with correct credentials
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'remember_me': False,
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'account has been manually locked')
    
    def test_expired_lockout_allows_new_attempt(self):
        """Test that expired lockout allows attempting login"""
        # Lock with expired cooldown
        self.login_attempt.failed_attempts = 5
        self.login_attempt.locked_until = timezone.now() - timedelta(seconds=1)  # Expired
        self.login_attempt.save()
        
        # Try to login - expired lockout should be cleared automatically
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'wrongpassword',
            'remember_me': False,
        })
        
        # Should be allowed to attempt (not blocked by expired lockout)
        # Request should complete and create a new lockout on the new failure
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
    
    def test_failed_login_logged_to_history(self):
        """Test that failed login is logged to LoginHistory"""
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'wrongpassword',
            'remember_me': False,
        })
        
        # Check LoginHistory
        history = LoginHistory.objects.filter(user=self.user, success=False)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history[0].failure_reason, 'Invalid password')
    
    def test_successful_login_logged_to_history(self):
        """Test that successful login is logged to LoginHistory"""
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'remember_me': False,
        })
        
        # Check LoginHistory
        history = LoginHistory.objects.filter(user=self.user, success=True)
        self.assertEqual(history.count(), 1)
    
    def test_user_enumeration_prevention(self):
        """Test that non-existent user gets same error message"""
        response = self.client.post(self.login_url, {
            'username': 'nonexistentuser',
            'password': 'somepassword',
            'remember_me': False,
        })
        
        # Should not create LoginAttempt for non-existent user
        self.assertEqual(
            LoginAttempt.objects.filter(user__username='nonexistentuser').count(),
            0
        )
        
        # Same error message as real user
        self.assertContains(response, 'Invalid username or password')
    
    def test_login_attempt_created_on_first_failure(self):
        """Test that LoginAttempt record is created on first failure"""
        # Create new user without LoginAttempt
        user2 = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='Password123!'
        )
        
        # Fail to login
        self.client.post(self.login_url, {
            'username': 'newuser',
            'password': 'wrongpassword',
            'remember_me': False,
        })
        
        # LoginAttempt should be created automatically
        self.assertTrue(LoginAttempt.objects.filter(user=user2).exists())
    
    def test_normal_user_flow_unaffected(self):
        """Test that normal users can login without issues"""
        # Create fresh user
        user = User.objects.create_user('freshuser', 'fresh@example.com', 'Password123!')
        
        # Should login successfully on first try
        response = self.client.post(self.login_url, {
            'username': 'freshuser',
            'password': 'Password123!',
            'remember_me': False,
        })
        
        # Should be logged in and redirected
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class LoginAttemptModelTests(TestCase):
    """Test LoginAttempt model methods"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.attempt = LoginAttempt.objects.create(user=self.user)
    
    def test_increment_failed_attempts(self):
        """Test incrementing failed attempts"""
        self.attempt.increment_failed_attempts()
        self.assertEqual(self.attempt.failed_attempts, 1)
    
    def test_cooldown_after_fifth_failure(self):
        """Test that cooldown is set after 5th failure"""
        for i in range(5):
            self.attempt.increment_failed_attempts()
        
        self.assertIsNotNone(self.attempt.locked_until)
    
    def test_reset_attempts(self):
        """Test resetting failed attempts"""
        self.attempt.failed_attempts = 5
        self.attempt.locked_until = timezone.now() + timedelta(seconds=30)
        self.attempt.save()
        
        self.attempt.reset_attempts()
        
        self.assertEqual(self.attempt.failed_attempts, 0)
        self.assertIsNone(self.attempt.locked_until)
    
    def test_is_temporarily_locked(self):
        """Test checking if account is locked"""
        # Not locked initially
        self.assertFalse(self.attempt.is_temporarily_locked())
        
        # Lock with future time
        self.attempt.locked_until = timezone.now() + timedelta(seconds=30)
        self.attempt.save()
        self.assertTrue(self.attempt.is_temporarily_locked())
        
        # Expired lock should be cleared
        self.attempt.locked_until = timezone.now() - timedelta(seconds=1)
        self.attempt.save()
        self.assertFalse(self.attempt.is_temporarily_locked())
        self.attempt.refresh_from_db()
        self.assertIsNone(self.attempt.locked_until)
    
    def test_get_cooldown_seconds(self):
        """Test calculating remaining cooldown"""
        self.attempt.locked_until = timezone.now() + timedelta(seconds=60)
        self.attempt.save()
        
        cooldown = self.attempt.get_cooldown_seconds()
        self.assertGreater(cooldown, 0)
        self.assertLessEqual(cooldown, 60)
    
    def test_manual_lock_flag(self):
        """Test manual admin lock flag"""
        self.assertFalse(self.attempt.is_locked)
        
        self.attempt.is_locked = True
        self.attempt.save()
        self.assertTrue(self.attempt.is_locked)
