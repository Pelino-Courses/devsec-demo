from django.test import TestCase, Client
from django.test.utils import override_settings
from django.core import mail
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import Profile, Role
from django.urls import reverse


class RoleBasedAccessControlTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.standard_user = User.objects.create_user(
            username='standard',
            email='standard@test.com',
            password='testpass123'
        )
        self.standard_profile = Profile.objects.create(
            user=self.standard_user,
            role=Role.USER
        )
        
        self.privileged_user = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123'
        )
        self.privileged_profile = Profile.objects.create(
            user=self.privileged_user,
            role=Role.INSTRUCTOR
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_profile = Profile.objects.create(
            user=self.admin_user,
            role=Role.ADMIN
        )
    
    def test_anonymous_access_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_access_register(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_cannot_access_profile(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_standard_user_can_access_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_admin_dashboard(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_cannot_access_user_management(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_privileged_user_can_access_admin_dashboard(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_cannot_access_user_management(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_admin_user_can_access_user_management(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_can_access_all_profiles(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_all_profiles(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_can_change_password(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_can_update_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('update_profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_403_template_rendered_for_denied_access(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'justin/403.html')
    
    def test_profile_role_property(self):
        self.assertFalse(self.standard_profile.is_privileged)
        self.assertFalse(self.standard_profile.is_admin)
        
        self.assertTrue(self.privileged_profile.is_privileged)
        self.assertFalse(self.privileged_profile.is_admin)
        
        self.assertTrue(self.admin_profile.is_privileged)
        self.assertTrue(self.admin_profile.is_admin)
    
    def test_role_context_for_authenticated_user(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])
        self.assertEqual(response.context['user_role'], 'instructor')
    
    def test_role_context_for_anonymous_user(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])


class PasswordResetWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='resetuser',
            email='resetuser@example.com',
            password='Original123!'
        )
        self.user.save()

    def test_password_reset_request_with_nonexistent_email_does_not_disclose(self):
        response = self.client.post(reverse('password_reset'), {'email': 'missing@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_sends_email_for_existing_user(self):
        response = self.client.post(reverse('password_reset'), {'email': 'resetuser@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reset your DevSec Demo password')
        self.assertIn('/reset/', mail.outbox[0].body)
        self.assertIn('ignore this message', mail.outbox[0].body.lower())

    def test_password_reset_confirm_with_invalid_token_shows_invalid_link(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': 'set-password'}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])

    def test_password_reset_complete_flow_updates_password(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_url = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        # Follow the canonical confirm redirect path before posting the form.
        response = self.client.get(reset_url, follow=True)
        confirm_url = response.request['PATH_INFO']
        self.assertIn('/reset/', confirm_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            confirm_url,
            {
                'new_password1': 'NewSecurePass123!',
                'new_password2': 'NewSecurePass123!',
            },
            follow=True
        )

        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))


@override_settings(
    LOGIN_THROTTLE_ACCOUNT_FAILURE_LIMIT=3,
    LOGIN_THROTTLE_IP_FAILURE_LIMIT=5,
    LOGIN_THROTTLE_LOCKOUT_SECONDS=60,
)
class LoginBruteForceProtectionTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(REMOTE_ADDR='203.0.113.10')
        self.user = User.objects.create_user(
            username='lockeduser',
            email='locked@example.com',
            password='SecurePass123!',
        )

    def tearDown(self):
        cache.clear()

    def test_valid_login_still_succeeds(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'lockeduser', 'password': 'SecurePass123!'},
        )
        self.assertRedirects(response, reverse('profile'))

    def test_repeated_failed_attempts_trigger_account_lockout(self):
        for _ in range(2):
            response = self.client.post(
                reverse('login'),
                {'username': 'lockeduser', 'password': 'wrong-password'},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid username or password')

        response = self.client.post(
            reverse('login'),
            {'username': 'lockeduser', 'password': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Too many login attempts', status_code=429)
        self.assertContains(response, 'temporarily paused', status_code=429)

    def test_successful_login_clears_failed_attempt_counter(self):
        for _ in range(2):
            self.client.post(
                reverse('login'),
                {'username': 'lockeduser', 'password': 'wrong-password'},
            )

        response = self.client.post(
            reverse('login'),
            {'username': 'lockeduser', 'password': 'SecurePass123!'},
        )
        self.assertRedirects(response, reverse('profile'))

        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {'username': 'lockeduser', 'password': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        self.assertNotContains(response, 'Too many login attempts')

    def test_ip_lockout_blocks_distributed_username_guessing(self):
        for attempt in range(4):
            response = self.client.post(
                reverse('login'),
                {'username': f'unknown{attempt}', 'password': 'wrong-password'},
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('login'),
            {'username': 'someoneelse', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 429)

        blocked_response = self.client.post(
            reverse('login'),
            {'username': 'lockeduser', 'password': 'SecurePass123!'},
        )
        self.assertEqual(blocked_response.status_code, 429)
        self.assertContains(blocked_response, 'Too many login attempts', status_code=429)
