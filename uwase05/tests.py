from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from uwase05.models import Profile


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123',
        )
        self.register_url = reverse('uwase05:register')
        self.login_url = reverse('uwase05:login')
        self.dashboard_url = reverse('uwase05:dashboard')
        self.profile_url = reverse('uwase05:profile')
        self.password_change_url = reverse('uwase05:password_change')
        self.password_change_done_url = reverse('uwase05:password_change_done')
        self.password_reset_url = reverse('uwase05:password_reset')
        self.password_reset_done_url = reverse('uwase05:password_reset_done')
        self.password_reset_complete_url = reverse('uwase05:password_reset_complete')
        self.logout_url = reverse('uwase05:logout')
        self.instructor_url = reverse('uwase05:instructor_dashboard')

    def test_register_new_user(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': 'SafePass1234',
                'password2': 'SafePass1234',
            },
        )
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_is_logged(self):
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            self.client.post(
                self.register_url,
                {
                    'username': 'newuser',
                    'email': 'new@example.com',
                    'password1': 'SafePass1234',
                    'password2': 'SafePass1234',
                },
            )
        self.assertTrue(any('event=registration' in message for message in cm.output))
        self.assertTrue(any('username=newuser' in message for message in cm.output))

    def test_login_and_dashboard_access(self):
        login_success = self.client.login(username='tester', password='StrongPass123')
        self.assertTrue(login_success)

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_login_success_is_logged(self):
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            response = self.client.post(
                self.login_url,
                {'username': 'tester', 'password': 'StrongPass123'},
            )
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(any('event=login_success' in message for message in cm.output))
        self.assertTrue(any('username=tester' in message for message in cm.output))

    def test_login_failure_is_logged_without_password(self):
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            self.client.post(
                self.login_url,
                {'username': 'tester', 'password': 'WrongPass123'},
            )
        self.assertTrue(any('event=login_failed' in message for message in cm.output))
        self.assertFalse(any('WrongPass123' in message for message in cm.output))

    def test_login_redirects_to_safe_next_target(self):
        response = self.client.post(
            f'{self.login_url}?next={self.profile_url}',
            {'username': 'tester', 'password': 'StrongPass123'},
        )
        self.assertRedirects(response, self.profile_url)

    def test_login_ignores_external_next_target(self):
        response = self.client.post(
            f'{self.login_url}?next=https://malicious.example.com',
            {'username': 'tester', 'password': 'StrongPass123'},
        )
        self.assertRedirects(response, self.dashboard_url)

    def test_logout_is_logged(self):
        self.client.login(username='tester', password='StrongPass123')
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            self.client.post(self.logout_url)
        self.assertTrue(any('event=logout' in message for message in cm.output))
        self.assertTrue(any('username=tester' in message for message in cm.output))

    def test_password_change_is_logged(self):
        self.client.login(username='tester', password='StrongPass123')
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            response = self.client.post(
                self.password_change_url,
                {
                    'old_password': 'StrongPass123',
                    'new_password1': 'NewStrongPass123',
                    'new_password2': 'NewStrongPass123',
                },
            )
        self.assertRedirects(response, self.password_change_done_url)
        self.assertTrue(any('event=password_changed' in message for message in cm.output))
        self.assertTrue(any('username=tester' in message for message in cm.output))

    def test_group_membership_change_is_logged(self):
        instructor_group, _ = Group.objects.get_or_create(name='instructor')
        with self.assertLogs('uwase05.audit', level='INFO') as cm:
            self.user.groups.add(instructor_group)
        self.assertTrue(any('event=group_added' in message for message in cm.output))
        self.assertTrue(any('username=tester' in message for message in cm.output))

    def test_login_throttles_repeated_failed_attempts(self):
        for attempt in range(1, 6):
            response = self.client.post(
                self.login_url,
                {'username': 'tester', 'password': 'WrongPass123'},
            )
            self.assertEqual(response.status_code, 200)
            if attempt < 5:
                self.assertContains(
                    response,
                    'Please enter a correct username and password.',
                )
            else:
                self.assertContains(
                    response,
                    'Too many failed login attempts. Please try again in 5 minutes.',
                )

        response = self.client.post(
            self.login_url,
            {'username': 'tester', 'password': 'StrongPass123'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Too many failed login attempts. Please try again in 5 minutes.',
        )

    def test_logout_ignores_external_next_target(self):
        self.client.login(username='tester', password='StrongPass123')
        response = self.client.post(
            f'{self.logout_url}?next=https://malicious.example.com'
        )
        self.assertRedirects(response, self.login_url)

    def test_logout_prevents_dashboard_access(self):
        self.client.login(username='tester', password='StrongPass123')
        self.client.logout()
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.dashboard_url}')

    def test_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.profile_url}')

    def test_password_change_requires_authentication(self):
        response = self.client.get(self.password_change_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.password_change_url}')

    def test_password_change_done_requires_authentication(self):
        response = self.client.get(self.password_change_done_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.password_change_done_url}')

    def test_password_reset_request_page_loads(self):
        response = self.client.get(self.password_reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset your password')

    def test_password_reset_request_is_silent_for_unknown_email(self):
        response = self.client.post(self.password_reset_url, {'email': 'unknown@example.com'})
        self.assertRedirects(response, self.password_reset_done_url)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_sends_email_for_valid_user(self):
        response = self.client.post(self.password_reset_url, {'email': 'tester@example.com'})
        self.assertRedirects(response, self.password_reset_done_url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('password reset', mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ['tester@example.com'])

    def test_password_reset_confirm_updates_password(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        reset_confirm_url = reverse(
            'uwase05:password_reset_confirm',
            kwargs={'uidb64': uid, 'token': token},
        )

        response = self.client.get(reset_confirm_url)
        self.assertEqual(response.status_code, 302)

        confirm_url = response['Location']
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            confirm_url,
            {
                'new_password1': 'NewSafePass123',
                'new_password2': 'NewSafePass123',
            },
        )
        self.assertRedirects(response, self.password_reset_complete_url)

        self.user.refresh_from_db()
        self.assertTrue(self.client.login(username='tester', password='NewSafePass123'))

    def test_profile_returns_current_user_profile(self):
        profile = self.user.profile
        profile.bio = 'Tester bio'
        profile.save()

        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='OtherPass123',
        )
        other_profile = other_user.profile
        other_profile.bio = 'Other bio'
        other_profile.save()

        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile'].user, self.user)
        self.assertContains(response, 'Tester bio')
        self.assertNotContains(response, 'Other bio')

    def test_profile_bio_is_escaped_to_prevent_stored_xss(self):
        profile = self.user.profile
        profile.bio = '<script>alert("xss")</script>Malicious content'
        profile.save()

        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;Malicious content')
        self.assertNotContains(response, '<script>alert("xss")</script>')

    def test_standard_user_cannot_access_instructor_area(self):
        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.instructor_url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_group_can_access_instructor_area(self):
        instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.user.groups.add(instructor_group)
        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.instructor_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instructor Area')

    def test_instructor_area_is_denied_to_anonymous_users(self):
        response = self.client.get(self.instructor_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.instructor_url}')

    def test_new_user_is_assigned_student_group(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'standarduser',
                'email': 'student@example.com',
                'password1': 'SafePass1234',
                'password2': 'SafePass1234',
            },
        )
        self.assertRedirects(response, self.login_url)
        new_user = User.objects.get(username='standarduser')
        self.assertTrue(new_user.groups.filter(name='student').exists())
