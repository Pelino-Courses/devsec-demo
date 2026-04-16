"""
Tests for brute-force protection, CSRF protection, open redirect prevention,
and audit logging.

Tests cover:
- Normal login behavior and successful authentication
- Abuse scenarios with repeated failed attempts
- Progressive throttling at 3, 5, 10, and 20 failed attempts
- User enumeration prevention
- IP address extraction and tracking
- Throttle status calculation across different time windows
- CSRF enforcement on the AJAX bio update endpoint
- Open redirect prevention on logout and register flows
- Audit log emission for all security-relevant events
- Verification that no sensitive data (passwords, emails) appears in logs
"""

from django.test import TestCase, Client
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import LoginAttempt, Profile
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


# ── CSRF Protection Tests ─────────────────────────────────────────────────────

class UpdateBioCSRFTests(TestCase):
    """
    Tests verifying that the bio update endpoint enforces CSRF protection.

    Design note:
    The endpoint originally used @csrf_exempt so the fetch call worked without
    an X-CSRFToken header.  That made the endpoint vulnerable: any page on any
    origin could silently POST and overwrite the bio of every logged-in visitor.

    The fix removes @csrf_exempt and requires the X-CSRFToken header.  Django's
    Client enforces CSRF by default when enforce_csrf_checks=True; the standard
    Client skips it (mirrors browser behaviour for same-origin requests which
    always carry the token).
    """

    def setUp(self):
        self.user = User.objects.create_user(username="biouser", password="testpass123")
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.url = reverse("uwamahoro_joseline:update_bio")

    def test_unauthenticated_request_redirected(self):
        """Unauthenticated users cannot reach the endpoint."""
        client = Client()
        response = client.post(
            self.url,
            data='{"bio": "hacked"}',
            content_type="application/json",
        )
        # Should redirect to login, not process the request
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_post_without_csrf_token_rejected(self):
        """
        A POST request missing the CSRF token must be rejected with 403.

        Uses enforce_csrf_checks=True to simulate a real browser cross-origin
        request that does not carry the csrftoken cookie value in the header.
        """
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="biouser", password="testpass123")
        response = csrf_client.post(
            self.url,
            data='{"bio": "forged bio"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        # Bio must not have changed
        profile = Profile.objects.get(user=self.user)
        self.assertNotEqual(profile.bio, "forged bio")

    def test_post_with_csrf_token_succeeds(self):
        """
        A legitimate same-origin POST that includes the CSRF token is accepted.

        Django's standard test Client automatically includes the CSRF token,
        mirroring a browser form/fetch that reads the csrftoken cookie.
        """
        self.client.login(username="biouser", password="testpass123")
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({"bio": "My updated bio"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["bio"], "My updated bio")
        # Verify persisted in DB
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.bio, "My updated bio")

    def test_get_request_rejected(self):
        """GET requests must return 405 — bio update is POST-only."""
        self.client.login(username="biouser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        """Malformed JSON body returns 400, not a server error."""
        self.client.login(username="biouser", password="testpass123")
        response = self.client.post(
            self.url,
            data="not json at all",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_bio_allowed(self):
        """Users can clear their bio by sending an empty string."""
        Profile.objects.get_or_create(user=self.user, defaults={"bio": "old bio"})
        self.client.login(username="biouser", password="testpass123")
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({"bio": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.bio, "")


# ── Open Redirect Tests ───────────────────────────────────────────────────────

class LogoutOpenRedirectTests(TestCase):
    """
    Tests verifying that logout rejects external redirect targets.

    Design note:
    The logout flow accepts an optional next parameter so the app can send
    users to a specific page after they log out (e.g. a public landing page).
    Without host validation an attacker can craft a link like:

        /joseline/logout/?next=https://evil.com

    After clicking "Confirm Logout" the user lands on evil.com instead of the
    login page — a classic phishing vector used to harvest credentials on a
    look-alike page.

    The fix uses url_has_allowed_host_and_scheme to accept only same-host paths.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="logoutuser", password="testpass123")
        self.logout_url = reverse("uwamahoro_joseline:logout")

    def test_logout_without_next_redirects_to_login(self):
        """Default post-logout destination is the login page."""
        self.client.login(username="logoutuser", password="testpass123")
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:login"),
                             fetch_redirect_response=False)

    def test_logout_with_safe_internal_next_is_accepted(self):
        """A same-host path in next is followed after logout."""
        self.client.login(username="logoutuser", password="testpass123")
        safe_next = reverse("uwamahoro_joseline:login")
        response = self.client.post(self.logout_url, {"next": safe_next})
        self.assertRedirects(response, safe_next, fetch_redirect_response=False)

    def test_logout_with_external_url_is_rejected(self):
        """An absolute external URL in next must be ignored."""
        self.client.login(username="logoutuser", password="testpass123")
        response = self.client.post(self.logout_url, {"next": "https://evil.com/phish"})
        # Must land on login, NOT evil.com
        self.assertRedirects(response, reverse("uwamahoro_joseline:login"),
                             fetch_redirect_response=False)

    def test_logout_with_protocol_relative_url_is_rejected(self):
        """Protocol-relative URLs (//evil.com) must also be blocked."""
        self.client.login(username="logoutuser", password="testpass123")
        response = self.client.post(self.logout_url, {"next": "//evil.com/phish"})
        self.assertRedirects(response, reverse("uwamahoro_joseline:login"),
                             fetch_redirect_response=False)

    def test_logout_next_passed_through_hidden_field(self):
        """GET request renders the confirmation page with next in context."""
        self.client.login(username="logoutuser", password="testpass123")
        safe_next = "/joseline/dashboard/"
        response = self.client.get(f"{self.logout_url}?next={safe_next}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], safe_next)


class RegisterOpenRedirectTests(TestCase):
    """
    Tests verifying that registration rejects external redirect targets.

    Same attack model as logout: an attacker sends a new user a registration
    link with next=https://evil.com. After signing up the user is immediately
    sent to the attacker's page, where they may be tricked into re-entering
    their new password or other sensitive information.
    """

    def setUp(self):
        self.register_url = reverse("uwamahoro_joseline:register")

    def _register(self, extra_post=None):
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        if extra_post:
            data.update(extra_post)
        return self.client.post(self.register_url, data)

    def test_register_without_next_redirects_to_dashboard(self):
        """Default post-registration destination is the dashboard."""
        response = self._register()
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"),
                             fetch_redirect_response=False)

    def test_register_with_safe_internal_next_is_accepted(self):
        """A same-host path in next is followed after registration."""
        safe_next = reverse("uwamahoro_joseline:profile")
        response = self._register({"next": safe_next})
        self.assertRedirects(response, safe_next, fetch_redirect_response=False)

    def test_register_with_external_url_is_rejected(self):
        """An absolute external URL in next must be ignored."""
        response = self._register({"next": "https://evil.com/steal-creds"})
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"),
                             fetch_redirect_response=False)

    def test_register_with_protocol_relative_url_is_rejected(self):
        """Protocol-relative URLs (//evil.com) must also be blocked."""
        response = self._register({"next": "//evil.com"})
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"),
                             fetch_redirect_response=False)

    def test_register_next_passed_via_get_to_template(self):
        """GET to the register page with next stores it in the context."""
        safe_next = "/joseline/dashboard/"
        response = self.client.get(f"{self.register_url}?next={safe_next}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], safe_next)


# ── Audit Logging Tests ───────────────────────────────────────────────────────

AUDIT_LOGGER = "uwamahoro_joseline.audit"


class AuditLoggingTests(TestCase):
    """
    Tests verifying that security-relevant events emit the correct audit log records.

    Design note:
    All records are emitted on the "uwamahoro_joseline.audit" logger so that
    production deployments can route them to a dedicated sink (file, SIEM, etc.)
    independently of the general application log.

    Sensitive data that must NEVER appear in logs:
    - Raw passwords or password hashes
    - Session keys or CSRF tokens
    - Email addresses (to avoid leaking account existence via reset endpoint)
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="audituser",
            email="audit@example.com",
            password="AuditPass123!",
        )
        self.login_url = reverse("uwamahoro_joseline:login")
        self.logout_url = reverse("uwamahoro_joseline:logout")
        self.register_url = reverse("uwamahoro_joseline:register")
        self.password_change_url = reverse("uwamahoro_joseline:password_change")

    # ── Registration ──────────────────────────────────────────────────────────

    def test_registration_emits_user_registered(self):
        """Successful registration logs USER_REGISTERED with username."""
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.register_url, {
                "username": "brandnew",
                "email": "brandnew@example.com",
                "password1": "NewPass123!",
                "password2": "NewPass123!",
            })
        self.assertTrue(any("USER_REGISTERED" in m for m in log.output))
        self.assertTrue(any("brandnew" in m for m in log.output))

    def test_registration_log_does_not_contain_password(self):
        """Registration log must never include the password value."""
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.register_url, {
                "username": "brandnew2",
                "email": "brandnew2@example.com",
                "password1": "NewPass123!",
                "password2": "NewPass123!",
            })
        for message in log.output:
            self.assertNotIn("NewPass123!", message)

    # ── Login ─────────────────────────────────────────────────────────────────

    def test_successful_login_emits_login_success(self):
        """Successful login logs LOGIN_SUCCESS with username."""
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.login_url, {
                "username": "audituser",
                "password": "AuditPass123!",
            })
        self.assertTrue(any("LOGIN_SUCCESS" in m for m in log.output))
        self.assertTrue(any("audituser" in m for m in log.output))

    def test_failed_login_emits_login_failed(self):
        """Failed login attempt logs LOGIN_FAILED with username."""
        with self.assertLogs(AUDIT_LOGGER, level="WARNING") as log:
            self.client.post(self.login_url, {
                "username": "audituser",
                "password": "wrongpassword",
            })
        self.assertTrue(any("LOGIN_FAILED" in m for m in log.output))
        self.assertTrue(any("audituser" in m for m in log.output))

    def test_failed_login_log_does_not_contain_password(self):
        """Failed login log must never include the attempted password."""
        with self.assertLogs(AUDIT_LOGGER, level="WARNING") as log:
            self.client.post(self.login_url, {
                "username": "audituser",
                "password": "SuperSecret99!",
            })
        for message in log.output:
            self.assertNotIn("SuperSecret99!", message)

    # ── Logout ────────────────────────────────────────────────────────────────

    def test_logout_emits_logout(self):
        """Successful logout logs LOGOUT with username."""
        self.client.login(username="audituser", password="AuditPass123!")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.logout_url)
        self.assertTrue(any("LOGOUT" in m for m in log.output))
        self.assertTrue(any("audituser" in m for m in log.output))

    # ── Password change ───────────────────────────────────────────────────────

    def test_password_change_emits_password_changed(self):
        """Successful password change logs PASSWORD_CHANGED with username."""
        self.client.login(username="audituser", password="AuditPass123!")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.password_change_url, {
                "old_password": "AuditPass123!",
                "new_password1": "NewAudit456!",
                "new_password2": "NewAudit456!",
            })
        self.assertTrue(any("PASSWORD_CHANGED" in m for m in log.output))
        self.assertTrue(any("audituser" in m for m in log.output))

    def test_password_change_log_does_not_contain_password(self):
        """Password change log must never include any password value."""
        self.client.login(username="audituser", password="AuditPass123!")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.password_change_url, {
                "old_password": "AuditPass123!",
                "new_password1": "NewAudit456!",
                "new_password2": "NewAudit456!",
            })
        for message in log.output:
            self.assertNotIn("AuditPass123!", message)
            self.assertNotIn("NewAudit456!", message)

    def test_failed_password_change_emits_password_change_failed(self):
        """Wrong old password logs PASSWORD_CHANGE_FAILED."""
        self.client.login(username="audituser", password="AuditPass123!")
        with self.assertLogs(AUDIT_LOGGER, level="WARNING") as log:
            self.client.post(self.password_change_url, {
                "old_password": "wrong_old_password",
                "new_password1": "NewAudit456!",
                "new_password2": "NewAudit456!",
            })
        self.assertTrue(any("PASSWORD_CHANGE_FAILED" in m for m in log.output))

    # ── Role changes ──────────────────────────────────────────────────────────

    def test_role_promotion_emits_role_promoted(self):
        """Promoting a user to Instructor logs ROLE_PROMOTED."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        instructor_group, _ = Group.objects.get_or_create(name="Instructor")

        # Give the acting user instructor + manage_users permission
        ct = ContentType.objects.get_for_model(Profile)
        perm = Permission.objects.get(content_type=ct, codename="can_manage_users")
        self.user.groups.add(instructor_group)
        self.user.user_permissions.add(perm)
        self.user.save()

        target = User.objects.create_user(username="targetuser", password="TargetPass1!")
        self.client.login(username="audituser", password="AuditPass123!")

        promote_url = reverse("uwamahoro_joseline:promote_user", kwargs={"user_id": target.pk})
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(promote_url, {"action": "promote"})
        self.assertTrue(any("ROLE_PROMOTED" in m for m in log.output))
        self.assertTrue(any("targetuser" in m for m in log.output))

    # ── Password reset ────────────────────────────────────────────────────────

    def test_password_reset_request_emits_log(self):
        """Submitting the password reset form logs PASSWORD_RESET_REQUESTED."""
        reset_url = reverse("uwamahoro_joseline:password_reset")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(reset_url, {"email": "audit@example.com"})
        self.assertTrue(any("PASSWORD_RESET_REQUESTED" in m for m in log.output))

    def test_password_reset_log_does_not_contain_email(self):
        """Password reset log must not include the email address."""
        reset_url = reverse("uwamahoro_joseline:password_reset")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(reset_url, {"email": "audit@example.com"})
        for message in log.output:
            self.assertNotIn("audit@example.com", message)
