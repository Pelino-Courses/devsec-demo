from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core import mail
from .models import LoginAttempt


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('eduard:register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(reverse('eduard:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('eduard:dashboard'))
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username='existing', email='dupe@example.com', password='pass')
        response = self.client.post(reverse('eduard:register'), {
            'username': 'newuser',
            'email': 'dupe@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'A user with this email already exists.')

    def test_password_mismatch_rejected(self):
        response = self.client.post(reverse('eduard:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'WrongPass999!',
        })
        self.assertEqual(response.status_code, 200)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loginuser', password='TestPass123!')

    def test_login_page_loads(self):
        response = self.client.get(reverse('eduard:login'))
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        response = self.client.post(reverse('eduard:login'), {
            'username': 'loginuser',
            'password': 'TestPass123!',
        })
        self.assertRedirects(response, reverse('eduard:dashboard'))

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse('eduard:login'), {
            'username': 'loginuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='loginuser', password='TestPass123!')
        response = self.client.post(reverse('eduard:logout'))
        self.assertRedirects(response, reverse('eduard:login'))


class ProtectedViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='authuser', password='TestPass123!')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('eduard:dashboard'))
        self.assertRedirects(response, f"{reverse('eduard:login')}?next={reverse('eduard:dashboard')}")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('eduard:profile'))
        self.assertRedirects(response, f"{reverse('eduard:login')}?next={reverse('eduard:profile')}")

    def test_authenticated_user_sees_dashboard(self):
        self.client.login(username='authuser', password='TestPass123!')
        response = self.client.get(reverse('eduard:dashboard'))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='passuser', password='OldPass123!')
        self.client.login(username='passuser', password='OldPass123!')

    def test_change_password_success(self):
        response = self.client.post(reverse('eduard:change_password'), {
            'old_password': 'OldPass123!',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertRedirects(response, reverse('eduard:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))



class InstructorAccessTests(TestCase):
    def setUp(self):
        self.instructor_group, _ = Group.objects.get_or_create(name='Instructor')
        self.normal_user = User.objects.create_user(
            username='normal', password='TestPass123!'
        )
        self.instructor_user = User.objects.create_user(
            username='instructor', password='TestPass123!'
        )
        self.instructor_user.groups.add(self.instructor_group)
        self.staff_user = User.objects.create_user(
            username='staffuser', password='TestPass123!', is_staff=True
        )

    def test_anonymous_redirected_from_instructor_page(self):
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_gets_403_on_instructor_page(self):
        self.client.login(username='normal', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_instructor_page(self):
        self.client.login(username='instructor', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_instructor_page(self):
        self.client.login(username='staffuser', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_instructor_page_shows_user_list(self):
        self.client.login(username='instructor', password='TestPass123!')
        response = self.client.get(reverse('eduard:instructor_dashboard'))
        self.assertContains(response, 'normal')


class ProfileIDORTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', password='TestPass123!'
        )
        self.user_b = User.objects.create_user(
            username='userb', password='TestPass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='Instructor')
        self.instructor = User.objects.create_user(
            username='instrtest', password='TestPass123!'
        )
        self.instructor.groups.add(self.instructor_group)

    def test_user_can_view_own_profile(self):
        self.client.login(username='usera', password='TestPass123!')
        response = self.client.get(reverse('eduard:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'usera')

    def test_normal_user_cannot_access_profile_by_id(self):
        """
        Normal users must not be able to look up other profiles by ID.
        Attempting profile_by_id as a normal user must return 403.
        """
        self.client.login(username='usera', password='TestPass123!')
        response = self.client.get(
            reverse('eduard:profile_by_id', args=[self.user_b.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_own_profile_by_id(self):
        """
        Even accessing your own profile via the ID URL is blocked for
        normal users — they must use /profile/ only.
        """
        self.client.login(username='usera', password='TestPass123!')
        response = self.client.get(
            reverse('eduard:profile_by_id', args=[self.user_a.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_profile_by_id(self):
        self.client.login(username='instrtest', password='TestPass123!')
        response = self.client.get(
            reverse('eduard:profile_by_id', args=[self.user_a.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'usera')

    def test_anonymous_user_cannot_access_profile_by_id(self):
        response = self.client.get(
            reverse('eduard:profile_by_id', args=[self.user_a.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_profile_by_id_nonexistent_user_returns_404(self):
        """
        Looking up a non-existent user ID must return 404, not a
        server error — and must not leak whether the user exists.
        """
        self.client.login(username='instrtest', password='TestPass123!')
        response = self.client.get(
            reverse('eduard:profile_by_id', args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_change_password_uses_session_not_url(self):
        """
        Password change must always operate on the session user,
        never on a URL parameter — no IDOR vector exists here.
        """
        self.client.login(username='usera', password='TestPass123!')
        response = self.client.post(reverse('eduard:change_password'), {
            'old_password': 'TestPass123!',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        })
        self.assertRedirects(response, reverse('eduard:profile'))
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password('NewSecure456!'))
        self.user_b.refresh_from_db()
        self.assertTrue(self.user_b.check_password('TestPass123!'))



class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='OldPass123!',
        )

    def test_reset_request_page_loads(self):
        response = self.client.get(reverse('eduard:password_reset'))
        self.assertEqual(response.status_code, 200)

    def test_reset_request_with_valid_email_sends_mail(self):
        response = self.client.post(reverse('eduard:password_reset'), {
            'email': 'reset@example.com',
        })
        self.assertRedirects(
            response,
            reverse('eduard:password_reset_done'),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_request_with_unknown_email_does_not_leak(self):
        """
        Submitting an email that has no account must still redirect to
        the done page - not an error - to prevent user enumeration.
        """
        response = self.client.post(reverse('eduard:password_reset'), {
            'email': 'nobody@example.com',
        })
        self.assertRedirects(
            response,
            reverse('eduard:password_reset_done'),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_done_page_loads(self):
        response = self.client.get(reverse('eduard:password_reset_done'))
        self.assertEqual(response.status_code, 200)

    def test_reset_confirm_invalid_token_shows_error(self):
        response = self.client.get(
            reverse('eduard:password_reset_confirm', kwargs={
                'uidb64': 'invalid',
                'token': 'invalid-token',
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid or expired')

    def test_reset_complete_page_loads(self):
        response = self.client.get(reverse('eduard:password_reset_complete'))
        self.assertEqual(response.status_code, 200)



class BruteForceProtectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bruteuser',
            password='CorrectPass123!',
        )
        self.login_url = reverse('eduard:login')

    def _fail_login(self, n):
        """Helper to submit n failed login attempts."""
        for _ in range(n):
            self.client.post(self.login_url, {
                'username': 'bruteuser',
                'password': 'WrongPassword!',
            })

    def test_successful_login_works_normally(self):
        response = self.client.post(self.login_url, {
            'username': 'bruteuser',
            'password': 'CorrectPass123!',
        })
        self.assertRedirects(response, reverse('eduard:dashboard'))

    def test_failed_attempts_are_tracked(self):
        self._fail_login(3)
        attempt = LoginAttempt.objects.get(username='bruteuser')
        self.assertEqual(attempt.failed_attempts, 3)
        self.assertFalse(attempt.is_locked())

    def test_account_locked_after_five_failures(self):
        self._fail_login(5)
        attempt = LoginAttempt.objects.get(username='bruteuser')
        self.assertTrue(attempt.is_locked())

    def test_locked_account_cannot_login_with_correct_password(self):
        self._fail_login(5)
        response = self.client.post(self.login_url, {
            'username': 'bruteuser',
            'password': 'CorrectPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_lockout_message_shown_to_user(self):
        self._fail_login(5)
        response = self.client.post(self.login_url, {
            'username': 'bruteuser',
            'password': 'CorrectPass123!',
        })
        self.assertContains(response, 'locked')

    def test_successful_login_clears_failed_attempts(self):
        self._fail_login(3)
        self.client.post(self.login_url, {
            'username': 'bruteuser',
            'password': 'CorrectPass123!',
        })
        attempt = LoginAttempt.objects.get(username='bruteuser')
        self.assertEqual(attempt.failed_attempts, 0)
        self.assertIsNone(attempt.locked_until)

    def test_unknown_username_does_not_crash(self):
        response = self.client.post(self.login_url, {
            'username': 'nonexistentuser',
            'password': 'SomePass123!',
        })
        self.assertEqual(response.status_code, 200)

    def test_warning_message_shows_remaining_attempts(self):
        self._fail_login(3)
        response = self.client.post(self.login_url, {
            'username': 'bruteuser',
            'password': 'WrongPassword!',
        })
        self.assertContains(response, 'remaining')



class CSRFProtectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='csrfuser',
            password='TestPass123!',
        )
        self.client.login(username='csrfuser', password='TestPass123!')
        self.url = reverse('eduard:update_display_name')

    def test_update_display_name_with_valid_csrf(self):
        """
        A legitimate AJAX POST with the CSRF token must succeed.
        The Django test client includes CSRF tokens automatically.
        """
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({'display_name': 'Eduard Test'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Eduard Test')

    def test_update_display_name_requires_login(self):
        self.client.logout()
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({'display_name': 'Hacker'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)

    def test_update_display_name_rejects_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_update_display_name_rejects_invalid_json(self):
        response = self.client.post(
            self.url,
            data='not json at all',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_update_display_name_rejects_too_long(self):
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({'display_name': 'A' * 51}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_csrf_middleware_is_active(self):
        """
        Verify CsrfViewMiddleware is present in settings - if it were
        removed or the endpoint used @csrf_exempt, CSRF protection
        would be gone entirely.
        """
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

        
def test_logout_requires_post(self):
        """
        Logout must only work via POST, not GET. A GET-based logout
        would be vulnerable to CSRF via a simple link or image tag.
        """
        response = self.client.get(reverse('eduard:logout'))
        # User must still be logged in after a GET request to logout
        self.assertIn(
            '_auth_user_id',
            self.client.session,
            msg='GET request must not log the user out',
        )
        """
        Logout must only work via POST, not GET. A GET-based logout
        would be vulnerable to CSRF via a simple link or image tag.
        """
        response = self.client.get(reverse('eduard:logout'))
        self.assertNotIn(
            '_auth_user_id',
            self.client.session,
            msg='GET request must not log the user out',
        )