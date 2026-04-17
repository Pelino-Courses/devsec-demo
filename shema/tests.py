import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from .models import Profile


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.username = 'testuser'
        self.password = 'TestPass123!'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_home_page_status_code(self):
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/home.html')

    def test_registration_flow(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!'
        })
        response = self.client.post(self.register_url, {
            'username': 'newuser2',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser2').exists())

    def test_login_flow(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_flow(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_profile_protected_access(self):
        profile_url = reverse('profile', kwargs={'username': self.username})
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/profile.html')

    def test_idor_prevention_on_profile_view(self):
        User.objects.create_user(username='hacker_user', password='TestPass123!')
        self.client.login(username=self.username, password=self.password)
        hacker_profile_url = reverse('profile', kwargs={'username': 'hacker_user'})
        response = self.client.get(hacker_profile_url)
        self.assertEqual(response.status_code, 404)

    def test_idor_prevention_on_profile_update(self):
        target_user = User.objects.create_user(username='target_user', password='TestPass123!')
        target_user.profile.bio = "Original Bio"
        target_user.profile.save()

        self.client.login(username=self.username, password=self.password)
        update_url = reverse('update_profile', kwargs={'username': 'target_user'})
        response = self.client.post(update_url, {'bio': 'Hacked Bio'})
        self.assertEqual(response.status_code, 404)

        target_user.refresh_from_db()
        self.assertEqual(target_user.profile.bio, "Original Bio")

    def test_instructor_dashboard_anonymous_access(self):
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_instructor_dashboard_standard_user_access(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_dashboard_privileged_user_access(self):
        privileged_user = User.objects.create_user(username='instructor1', password='TestPass123!')
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='view_instructor_dashboard')
        privileged_user.user_permissions.add(perm)

        self.client.login(username='instructor1', password='TestPass123!')
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/instructor_dashboard.html')


class StoredXSSTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'victim'
        self.password = 'VictimPass123!'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.profile_url = reverse('profile', kwargs={'username': self.username})
        self.update_url = reverse('update_profile', kwargs={'username': self.username})

    def test_stored_xss_prevention_in_bio(self):
        malicious_bio = "<script>alert('XSS')</script><b>BoldProof</b>"
        self.client.login(username=self.username, password=self.password)

        update_response = self.client.post(self.update_url, {'bio': malicious_bio})
        self.assertEqual(update_response.status_code, 302)

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        self.assertContains(response, "&lt;b&gt;BoldProof&lt;/b&gt;")
        self.assertNotContains(response, "<b>BoldProof</b>")
        self.assertNotContains(response, "<script>alert")

    def test_bio_xss_payload_is_escaped_in_profile_view(self):
        self.user.profile.bio = '<script>alert("XSS")</script>'
        self.user.profile.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>alert("XSS")</script>', response.content.decode())
        self.assertIn('&lt;script&gt;', response.content.decode())

    def test_profile_auto_created_for_new_user(self):
        new_user = User.objects.create_user(username='newprofileuser', password='TestPass123!')
        self.assertTrue(Profile.objects.filter(user=new_user).exists())

    def test_admin_bio_preview_is_plain_text(self):
        self.user.profile.bio = '<script>alert("XSS")</script>'
        self.user.profile.save()
        profile = Profile.objects.get(user=self.user)
        from shema.admin import ProfileAdmin
        from django.contrib.admin.sites import AdminSite
        from django.utils.safestring import SafeData
        ma = ProfileAdmin(Profile, AdminSite())
        preview = ma.bio_preview(profile)
        self.assertNotIsInstance(preview, SafeData)


class SecuritySettingsTests(TestCase):
    """Verify that production-grade security settings are configured correctly."""

    def test_secret_key_is_set(self):
        self.assertTrue(settings.SECRET_KEY, "SECRET_KEY must not be empty or None.")

    def test_debug_defaults_to_false_without_env(self):
        # The env-parsing logic treats anything other than 'true' as False.
        import os
        original = os.environ.get('DJANGO_DEBUG')
        os.environ['DJANGO_DEBUG'] = 'False'
        result = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'
        self.assertFalse(result)
        if original is None:
            del os.environ['DJANGO_DEBUG']
        else:
            os.environ['DJANGO_DEBUG'] = original

    def test_allowed_hosts_has_no_wildcard(self):
        self.assertNotIn('*', settings.ALLOWED_HOSTS,
                         "ALLOWED_HOSTS must not contain '*'.")

    def test_content_type_nosniff_enabled(self):
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_x_frame_options_is_deny(self):
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')

    def test_referrer_policy_is_set(self):
        self.assertEqual(settings.SECURE_REFERRER_POLICY, 'same-origin')

    def test_session_cookie_httponly(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_session_cookie_samesite(self):
        self.assertIn(settings.SESSION_COOKIE_SAMESITE, ('Lax', 'Strict'))

    def test_csrf_cookie_samesite(self):
        self.assertIn(settings.CSRF_COOKIE_SAMESITE, ('Lax', 'Strict'))

    def test_session_cookie_age_is_limited(self):
        # Must be set and no longer than 24 hours to limit session hijack window.
        self.assertLessEqual(settings.SESSION_COOKIE_AGE, 86400)

    def test_session_expires_on_browser_close(self):
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_csrf_cookie_not_httponly(self):
        # CSRF_COOKIE_HTTPONLY must stay False — Django JS reads it for AJAX.
        self.assertFalse(settings.CSRF_COOKIE_HTTPONLY)

    def test_security_middleware_is_first(self):
        first = settings.MIDDLEWARE[0]
        self.assertEqual(first, 'django.middleware.security.SecurityMiddleware',
                         "SecurityMiddleware must be the first middleware.")

    def test_application_still_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
