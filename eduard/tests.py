import io
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core import mail
from eduard.views import _is_safe_url
from .models import LoginAttempt, UserProfile

from django.core.files.uploadedfile import SimpleUploadedFile

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
        self.client.get(reverse('eduard:logout'))
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
        self.client.get(reverse('eduard:logout'))
        self.assertNotIn(
            '_auth_user_id',
            self.client.session,
            msg='GET request must not log the user out',
        )



class OpenRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='redirectuser',
            password='TestPass123!',
        )
        self.login_url = reverse('eduard:login')

    def _login_with_next(self, next_url):
        """Helper to POST a login with a next parameter."""
        return self.client.post(
            f'{self.login_url}?next={next_url}',
            {
                'username': 'redirectuser',
                'password': 'TestPass123!',
                'next': next_url,
            },
        )

    def test_safe_internal_redirect_is_allowed(self):
        """A relative internal path must be followed after login."""
        response = self._login_with_next('/profile/')
        self.assertRedirects(
            response,
            '/profile/',
            fetch_redirect_response=False,
        )

    def test_external_redirect_is_rejected(self):
        """
        An absolute URL pointing to an external host must be rejected.
        The user must land on the dashboard instead of the external site.
        """
        response = self._login_with_next('https://evil.com')
        self.assertRedirects(
            response,
            reverse('eduard:dashboard'),
            fetch_redirect_response=False,
        )

    def test_external_redirect_with_double_slash_is_rejected(self):
        """
        //evil.com is a protocol-relative URL that browsers treat as
        an external redirect. It must be rejected.
        """
        response = self._login_with_next('//evil.com')
        self.assertRedirects(
            response,
            reverse('eduard:dashboard'),
            fetch_redirect_response=False,
        )

    def test_javascript_scheme_is_rejected(self):
        """
        javascript:// URLs must be rejected to prevent XSS via redirect.
        """
        response = self._login_with_next('javascript://alert(1)')
        self.assertRedirects(
            response,
            reverse('eduard:dashboard'),
            fetch_redirect_response=False,
        )

    def test_empty_next_falls_back_to_dashboard(self):
        """An empty next parameter must redirect to the dashboard."""
        response = self._login_with_next('')
        self.assertRedirects(
            response,
            reverse('eduard:dashboard'),
            fetch_redirect_response=False,
        )

    def test_missing_next_falls_back_to_dashboard(self):
        """No next parameter must redirect to the dashboard."""
        response = self.client.post(self.login_url, {
            'username': 'redirectuser',
            'password': 'TestPass123!',
        })
        self.assertRedirects(
            response,
            reverse('eduard:dashboard'),
            fetch_redirect_response=False,
        )

    def test_is_safe_url_accepts_relative_path(self):
        """Unit test the helper directly with a safe relative path."""
        request = self.client.get('/').wsgi_request
        self.assertTrue(_is_safe_url('/profile/', request))

    def test_is_safe_url_rejects_external_host(self):
        """Unit test the helper directly with an external host."""
        request = self.client.get('/').wsgi_request
        self.assertFalse(_is_safe_url('https://evil.com', request))

    def test_is_safe_url_rejects_none(self):
        """Unit test the helper directly with None input."""
        request = self.client.get('/').wsgi_request
        self.assertFalse(_is_safe_url(None, request))


class AuditLoggingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='audituser',
            email='audit@example.com',
            password='TestPass123!',
        )

    def test_registration_is_logged(self):
        with self.assertLogs('eduard.audit', level='INFO') as log:
            self.client.post(reverse('eduard:register'), {
                'username': 'newaudituser',
                'email': 'new@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
        self.assertTrue(
            any('event=registration' in m and 'newaudituser' in m for m in log.output)
        )

    def test_login_success_is_logged(self):
        with self.assertLogs('eduard.audit', level='INFO') as log:
            self.client.post(reverse('eduard:login'), {
                'username': 'audituser',
                'password': 'TestPass123!',
            })
        self.assertTrue(
            any('event=login' in m and 'status=success' in m for m in log.output)
        )

    def test_login_failure_is_logged(self):
        with self.assertLogs('eduard.audit', level='WARNING') as log:
            self.client.post(reverse('eduard:login'), {
                'username': 'audituser',
                'password': 'WrongPass!',
            })
        self.assertTrue(
            any('event=login' in m and 'status=failure' in m for m in log.output)
        )

    def test_logout_is_logged(self):
        self.client.login(username='audituser', password='TestPass123!')
        with self.assertLogs('eduard.audit', level='INFO') as log:
            self.client.post(reverse('eduard:logout'))
        self.assertTrue(
            any('event=logout' in m and 'audituser' in m for m in log.output)
        )

    def test_password_change_is_logged(self):
        self.client.login(username='audituser', password='TestPass123!')
        with self.assertLogs('eduard.audit', level='INFO') as log:
            self.client.post(reverse('eduard:change_password'), {
                'old_password': 'TestPass123!',
                'new_password1': 'NewPass456!',
                'new_password2': 'NewPass456!',
            })
        self.assertTrue(
            any('event=password_change' in m for m in log.output)
        )

    def test_password_never_appears_in_logs(self):
        with self.assertLogs('eduard.audit', level='INFO') as log:
            self.client.post(reverse('eduard:register'), {
                'username': 'logcheckuser',
                'email': 'logcheck@example.com',
                'password1': 'SuperSecret999!',
                'password2': 'SuperSecret999!',
            })
        for entry in log.output:
            self.assertNotIn('SuperSecret999!', entry)

    def test_account_lockout_is_logged(self):
        for _ in range(5):
            self.client.post(reverse('eduard:login'), {
                'username': 'audituser',
                'password': 'WrongPass!',
            })
        with self.assertLogs('eduard.audit', level='WARNING') as log:
            self.client.post(reverse('eduard:login'), {
                'username': 'audituser',
                'password': 'TestPass123!',
            })
        self.assertTrue(
            any('event=login' in m and 'status=locked' in m for m in log.output)
        )

def test_password_reset_request_is_logged(self):
    with self.assertLogs('eduard.audit', level='INFO') as log:
        self.client.post(reverse('eduard:password_reset'), {
            'email': 'audit@example.com',
        })
    self.assertTrue(
        any('event=password_reset_request' in m for m in log.output)
    )




class StoredXSSTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='xssuser',
            password='TestPass123!',
        )
        self.client.login(username='xssuser', password='TestPass123!')
        self.profile_url = reverse('eduard:profile')

    def test_bio_saves_and_displays_plain_text(self):
        self.client.post(self.profile_url, {'bio': 'Hello I am Eduard'})
        response = self.client.get(self.profile_url)
        self.assertContains(response, 'Hello I am Eduard')

    def test_script_tag_in_bio_is_escaped_not_executed(self):
        """
        A script tag stored in the bio must appear as escaped text
        in the HTML source, never as a live script element.
        Django's auto-escaping converts < to &lt; and > to &gt;
        so the browser displays the tag as text rather than executing it.
        """
        payload = '<script>alert("xss")</script>'
        self.client.post(self.profile_url, {'bio': payload})
        response = self.client.get(self.profile_url)
        content = response.content.decode()
        self.assertNotIn('<script>alert("xss")</script>', content)
        self.assertIn('&lt;script&gt;', content)

    def test_html_tags_in_bio_are_escaped(self):
        """HTML tags must be rendered as visible text, not as markup."""
        self.client.post(self.profile_url, {'bio': '<b>bold</b>'})
        response = self.client.get(self.profile_url)
        content = response.content.decode()
        self.assertNotIn('<b>bold</b>', content)
        self.assertIn('&lt;b&gt;', content)

    def test_javascript_url_in_bio_is_escaped(self):
        """javascript: URLs stored in bio must be escaped as HTML entities."""
        self.client.post(
            self.profile_url,
            {'bio': '<a href="javascript:alert(1)">click</a>'},
        )
        response = self.client.get(self.profile_url)
        content = response.content.decode()
        self.assertNotIn('<a href="javascript:alert(1)">click</a>', content)
        self.assertIn('&lt;a href=&quot;javascript:alert(1)&quot;&gt;', content)
    def test_bio_max_length_enforced(self):
        """Bio must not accept more than 500 characters."""
        response = self.client.post(
            self.profile_url,
            {'bio': 'A' * 501},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.get(user=self.user).bio == 'A' * 501)

    def test_safe_filter_not_used_in_bio_template(self):
        """
        Confirm the template does not use the |safe filter on the bio
        field, which would disable Django's auto-escaping and reintroduce
        the XSS risk.
        """
        with open('eduard/templates/eduard/profile.html', encoding='utf-8') as f:
            template_source = f.read()
        self.assertNotIn('bio|safe', template_source)
        self.assertNotIn('bio | safe', template_source)



class FileUploadSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='uploaduser',
            password='TestPass123!',
        )
        self.client.login(username='uploaduser', password='TestPass123!')
        self.profile_url = reverse('eduard:profile')

    def _make_jpeg(self, size=100):
        """Create a minimal valid JPEG file in memory."""
        from PIL import Image
        img = Image.new('RGB', (size, size), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return buf

    def _make_png(self):
        """Create a minimal valid PNG file in memory."""
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='blue')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def test_valid_jpeg_upload_accepted(self):
        buf = self._make_jpeg()
        upload = SimpleUploadedFile('avatar.jpg', buf.read(), content_type='image/jpeg')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)

    def test_valid_png_upload_accepted(self):
        buf = self._make_png()
        upload = SimpleUploadedFile('avatar.png', buf.read(), content_type='image/png')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)

    def test_php_file_with_image_extension_rejected(self):
        """
        A PHP file renamed to .jpg must be rejected.
        Django's ImageField validates file content before our custom
        validator runs, so the error comes from Django's image check.
        """
        php_content = b'<?php echo shell_exec($_GET["cmd"]); ?>'
        upload = SimpleUploadedFile('evil.jpg', php_content, content_type='image/jpeg')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid image')

    def test_executable_extension_rejected(self):
        """A .exe file must be rejected at the extension check."""
        buf = self._make_jpeg()
        upload = SimpleUploadedFile('evil.exe', buf.read(), content_type='image/jpeg')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not allowed')

    def test_oversized_file_rejected(self):
        """A file over 2MB must be rejected."""
        from PIL import Image
        import io
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        large_content = buf.getvalue() + b'A' * (3 * 1024 * 1024)
        upload = SimpleUploadedFile('big.jpg', large_content, content_type='image/jpeg')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'File too large')

    def test_html_file_disguised_as_image_rejected(self):
        """An HTML file with image extension must be rejected."""
        html_content = b'<html><script>alert(1)</script></html>'
        upload = SimpleUploadedFile('evil.png', html_content, content_type='image/png')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid image')
    def test_upload_requires_login(self):
        self.client.logout()
        buf = self._make_jpeg()
        upload = SimpleUploadedFile('avatar.jpg', buf.read(), content_type='image/jpeg')
        response = self.client.post(self.profile_url, {
            'bio': 'Hello',
            'avatar': upload,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_safe_filename_discards_original_name(self):
        """
        Uploaded filenames must be replaced with random UUIDs to
        prevent path traversal and filename-based attacks.
        """
        from .validators import safe_filename
        result = safe_filename('../../etc/passwd.jpg')
        self.assertNotIn('..', result)
        self.assertNotIn('passwd', result)
        self.assertTrue(result.endswith('.jpg'))

    def test_max_upload_size_setting_exists(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, 'MAX_UPLOAD_SIZE'))
        self.assertLessEqual(settings.MAX_UPLOAD_SIZE, 5 * 1024 * 1024)



class SecuritySettingsTests(TestCase):
    def test_secret_key_is_set(self):
        """SECRET_KEY must never be None or empty."""
        from django.conf import settings
        self.assertTrue(bool(settings.SECRET_KEY))

    def test_debug_is_boolean(self):
        """DEBUG must be a real boolean not a string."""
        from django.conf import settings
        self.assertIsInstance(settings.DEBUG, bool)

    def test_allowed_hosts_is_not_empty(self):
        """ALLOWED_HOSTS must have at least one entry."""
        from django.conf import settings
        self.assertTrue(len(settings.ALLOWED_HOSTS) > 0)

    def test_session_cookie_httponly(self):
        from django.conf import settings
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_session_cookie_samesite(self):
        from django.conf import settings
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')

    def test_csrf_cookie_samesite(self):
        from django.conf import settings
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Lax')

    def test_content_type_nosniff(self):
        from django.conf import settings
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_x_frame_options_is_deny(self):
        from django.conf import settings
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')

    def test_csrf_middleware_present(self):
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

    def test_security_middleware_present(self):
        from django.conf import settings
        self.assertIn(
            'django.middleware.security.SecurityMiddleware',
            settings.MIDDLEWARE,
        )

    def test_password_validators_configured(self):
        from django.conf import settings
        self.assertTrue(len(settings.AUTH_PASSWORD_VALIDATORS) >= 4)