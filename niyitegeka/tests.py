from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile, LoginAttempt


class RegistrationTest(TestCase):

    def test_register_page_loads(self):
        response = self.client.get(reverse('niyitegeka:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_success(self):
        self.client.post(reverse('niyitegeka:register'), {
            'username': 'peter',
            'email': 'peter@example.com',
            'password1': 'Secure@1234',
            'password2': 'Secure@1234',
        })
        self.assertEqual(User.objects.filter(username='peter').count(), 1)

    def test_register_password_mismatch(self):
        self.client.post(reverse('niyitegeka:register'), {
            'username': 'peter2',
            'email': 'peter2@example.com',
            'password1': 'Secure@1234',
            'password2': 'WrongPassword',
        })
        self.assertEqual(User.objects.filter(username='peter2').count(), 0)


class LoginTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('niyitegeka:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'Secure@1234',
        })
        self.assertRedirects(response, reverse('niyitegeka:dashboard'))

    def test_login_wrong_password(self):
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)


class ProtectedPageTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/dashboard/'
        )

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/profile/'
        )


class LogoutTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_logout_redirects(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:logout'))
        self.assertRedirects(response, reverse('niyitegeka:login'))


class ProfileTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user)
        self.client.login(username='peter', password='Secure@1234')

    def test_profile_page_loads(self):
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        response = self.client.post(reverse('niyitegeka:profile'), {
            'bio': 'I am peter.',
            'phone': '0781234567',
        })
        self.assertRedirects(response, reverse('niyitegeka:profile'))
        updated = Profile.objects.get(user=self.user)
        self.assertEqual(updated.bio, 'I am peter.')


class RoleBasedAccessTest(TestCase):

    def setUp(self):
        self.normal_user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        self.staff_user = User.objects.create_user(
            username='staffpeter',
            password='Secure@1234',
            is_staff=True
        )

    def test_staff_dashboard_requires_login(self):
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/staff/'
        )

    def test_normal_user_cannot_access_staff_dashboard(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/staff/'
        )

    def test_staff_user_can_access_staff_dashboard(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_shows_user_list(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertContains(response, 'peter')

    def test_staff_link_visible_to_staff(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertContains(response, '/auth/staff/')

    def test_staff_link_hidden_from_normal_user(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertNotContains(response, '/auth/staff/')


class IDORPreventionTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        self.user2 = User.objects.create_user(
            username='paul',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user1)
        Profile.objects.create(user=self.user2)

    def test_user_can_view_own_profile_detail(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_profile_detail(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['paul'])
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_any_profile_detail(self):
        staff = User.objects.create_user(
            username='staffpeter',
            password='Secure@1234',
            is_staff=True
        )
        Profile.objects.create(user=staff)
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['paul'])
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_view_profile_detail(self):
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/profile/peter/'
        )


class PasswordResetTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            email='peter@example.com',
            password='Secure@1234'
        )

    def test_password_reset_page_loads(self):
        response = self.client.get(
            reverse('niyitegeka:passwordreset')
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_done_page_loads(self):
        response = self.client.get(
            reverse('niyitegeka:passwordresetdone')
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_complete_page_loads(self):
        response = self.client.get(
            reverse('niyitegeka:passwordresetcomplete')
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_request_valid_email(self):
        response = self.client.post(
            reverse('niyitegeka:passwordreset'),
            {'email': 'peter@example.com'}
        )
        self.assertRedirects(
            response,
            '/auth/password-reset/done/'
        )

    def test_password_reset_request_invalid_email(self):
        response = self.client.post(
            reverse('niyitegeka:passwordreset'),
            {'email': 'notexist@example.com'}
        )
        self.assertRedirects(
            response,
            '/auth/password-reset/done/'
        )


class BruteForceProtectionTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_successful_login_resets_attempts(self):
        self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'wrongpassword',
        })
        self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'Secure@1234',
        })
        attempt = LoginAttempt.objects.get(username='peter')
        self.assertEqual(attempt.attempts, 0)

    def test_failed_login_increments_attempts(self):
        self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'wrongpassword',
        })
        attempt = LoginAttempt.objects.get(username='peter')
        self.assertEqual(attempt.attempts, 1)

    def test_account_locked_after_five_attempts(self):
        for i in range(5):
            self.client.post(reverse('niyitegeka:login'), {
                'username': 'peter',
                'password': 'wrongpassword',
            })
        attempt = LoginAttempt.objects.get(username='peter')
        self.assertTrue(attempt.is_locked())

    def test_locked_account_cannot_login(self):
        LoginAttempt.objects.create(
            username='peter',
            attempts=5,
            locked_until=timezone.now() + timezone.timedelta(minutes=10)
        )
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'Secure@1234',
        })
        self.assertEqual(response.status_code, 200)

    def test_expired_lock_allows_login(self):
        LoginAttempt.objects.create(
            username='peter',
            attempts=5,
            locked_until=timezone.now() - timezone.timedelta(minutes=1)
        )
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'Secure@1234',
        })
        self.assertRedirects(response, reverse('niyitegeka:dashboard'))


class CSRFProtectionTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user)

    def test_updatebio_requires_login(self):
        response = self.client.post(
            reverse('niyitegeka:updatebio'),
            {'bio': 'test bio'}
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/update-bio/'
        )

    def test_updatebio_with_login_and_csrf(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.post(
            reverse('niyitegeka:updatebio'),
            {'bio': 'new bio'},
        )
        self.assertEqual(response.status_code, 200)

    def test_updatebio_updates_correctly(self):
        self.client.login(username='peter', password='Secure@1234')
        self.client.post(
            reverse('niyitegeka:updatebio'),
            {'bio': 'updated bio'},
        )
        updated = Profile.objects.get(user=self.user)
        self.assertEqual(updated.bio, 'updated bio')

    def test_updatebio_rejects_get_request(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:updatebio')
        )
        self.assertEqual(response.status_code, 400)

    def test_profile_form_csrf_protected(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertContains(response, 'csrfmiddlewaretoken')


class OpenRedirectTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_safe_internal_redirect_works(self):
        response = self.client.post(
            '/auth/login/?next=/auth/dashboard/',
            {
                'username': 'peter',
                'password': 'Secure@1234',
                'next': '/auth/dashboard/'
            }
        )
        self.assertRedirects(response, '/auth/dashboard/')

    def test_external_redirect_blocked(self):
        response = self.client.post(
            '/auth/login/?next=https://malicious.com',
            {
                'username': 'peter',
                'password': 'Secure@1234',
                'next': 'https://malicious.com'
            }
        )
        self.assertRedirects(response, '/auth/dashboard/')

    def test_protocol_relative_redirect_blocked(self):
        response = self.client.post(
            '/auth/login/',
            {
                'username': 'peter',
                'password': 'Secure@1234',
                'next': '//malicious.com'
            }
        )
        self.assertRedirects(response, '/auth/dashboard/')

    def test_no_next_redirects_to_dashboard(self):
        response = self.client.post(
            '/auth/login/',
            {
                'username': 'peter',
                'password': 'Secure@1234',
            }
        )
        self.assertRedirects(response, '/auth/dashboard/')

    def test_empty_next_redirects_to_dashboard(self):
        response = self.client.post(
            '/auth/login/',
            {
                'username': 'peter',
                'password': 'Secure@1234',
                'next': ''
            }
        )
        self.assertRedirects(response, '/auth/dashboard/')


class AuditLoggingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='newpeter',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user)

    def test_login_success_is_logged(self):
        with self.assertLogs('niyitegeka.audit', level='INFO') as cm:
            self.client.post(reverse('niyitegeka:login'), {
                'username': 'newpeter',
                'password': 'Secure@1234',
            })
        self.assertTrue(
            any('LOGIN_SUCCESS' in line for line in cm.output)
        )

    def test_login_failure_is_logged(self):
        with self.assertLogs('niyitegeka.audit', level='WARNING') as cm:
            self.client.post(reverse('niyitegeka:login'), {
                'username': 'newpeter',
                'password': 'wrongpassword',
            })
        self.assertTrue(
            any('LOGIN_FAILURE' in line for line in cm.output)
        )

    def test_logout_is_logged(self):
        self.client.login(username='newpeter', password='Secure@1234')
        with self.assertLogs('niyitegeka.audit', level='INFO') as cm:
            self.client.get(reverse('niyitegeka:logout'))
        self.assertTrue(
            any('LOGOUT' in line for line in cm.output)
        )

    def test_registration_is_logged(self):
        with self.assertLogs('niyitegeka.audit', level='INFO') as cm:
            self.client.post(reverse('niyitegeka:register'), {
                'username': 'brandnewpeter',
                'email': 'brandnewpeter@example.com',
                'password1': 'Secure@1234',
                'password2': 'Secure@1234',
            })
        self.assertTrue(
            any('REGISTRATION' in line for line in cm.output)
        )

    def test_password_change_is_logged(self):
        self.client.login(username='newpeter', password='Secure@1234')
        with self.assertLogs('niyitegeka.audit', level='INFO') as cm:
            self.client.post(reverse('niyitegeka:passwordchange'), {
                'old_password': 'Secure@1234',
                'new_password1': 'NewSecure@1234',
                'new_password2': 'NewSecure@1234',
            })
        self.assertTrue(
            any('PASSWORD_CHANGE' in line for line in cm.output)
        )

    def test_raw_password_not_in_logs(self):
        with self.assertLogs('niyitegeka.audit', level='INFO') as cm:
            self.client.post(reverse('niyitegeka:login'), {
                'username': 'newpeter',
                'password': 'Secure@1234',
            })
        log_output = ' '.join(cm.output)
        self.assertNotIn('Secure@1234', log_output)


class StoredXSSTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(username='peter', password='Secure@1234')

    def test_xss_payload_not_executed_in_profile(self):
        self.client.post(reverse('niyitegeka:profile'), {
            'bio': '<script>alert("xss")</script>',
            'phone': '0781234567',
        })
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertNotContains(response, '<script>alert("xss")</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_normal_bio_renders_correctly(self):
        self.client.post(reverse('niyitegeka:profile'), {
            'bio': 'I am peter a CS student.',
            'phone': '0781234567',
        })
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertContains(response, 'I am peter a CS student.')

    def test_html_tags_escaped_in_bio(self):
        self.client.post(reverse('niyitegeka:profile'), {
            'bio': '<b>bold text</b>',
            'phone': '0781234567',
        })
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertNotContains(response, '<b>bold text</b>')
        self.assertContains(response, '&lt;b&gt;')

    def test_xss_payload_not_executed_in_profile_form(self):
        self.client.post(reverse('niyitegeka:profile'), {
            'bio': '<script>alert("xss")</script>',
            'phone': '0781234567',
        })
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertNotContains(
            response,
            '<script>alert("xss")</script>'
        )


class FileUploadTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user)
        self.client.login(username='peter', password='Secure@1234')

    def test_avatar_upload_page_loads(self):
        from django.test import Client
        c = Client()
        c.login(username='peter', password='Secure@1234')
        response = c.get('/auth/avatar-upload/')
        assert response.status_code == 200

    def test_document_upload_page_loads(self):
        from django.test import Client
        c = Client()
        c.login(username='peter', password='Secure@1234')
        response = c.get('/auth/document-upload/')
        assert response.status_code == 200
