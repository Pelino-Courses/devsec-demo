from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core import mail
from django.utils import timezone
from tresor.models import LoginAttempt, MAX_ATTEMPTS, LOCKOUT_MINUTES


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('tresor:register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'tresor@test.com',
            'password1': 'Securepass123!',
            'password2': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))
        self.assertTrue(User.objects.filter(username='tresortest').exists())

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'tresor@test.com',
            'password1': 'Securepass123!',
            'password2': 'DifferentPass!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='tresortest').exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='tresortest', password='Pass123!')
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'other@test.com',
            'password1': 'Securepass123!',
            'password2': 'Securepass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='tresortest').count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('tresor:login'))
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        response = self.client.post(reverse('tresor:login'), {
            'username': 'tresortest',
            'password': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse('tresor:login'), {
            'username': 'tresortest',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout(self):
        self.client.login(username='tresortest', password='Securepass123!')
        response = self.client.post(reverse('tresor:logout'))
        self.assertRedirects(response, reverse('tresor:login'))


class ProtectedPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertRedirects(response, f"/tresor/login/?next={reverse('tresor:dashboard')}")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('tresor:profile'))
        self.assertRedirects(response, f"/tresor/login/?next={reverse('tresor:profile')}")

    def test_authenticated_user_accesses_dashboard(self):
        self.client.login(username='tresortest', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )
        self.client.login(username='tresortest', password='Securepass123!')

    def test_password_change_page_loads(self):
        response = self.client.get(reverse('tresor:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_successful_password_change(self):
        response = self.client.post(reverse('tresor:password_change'), {
            'old_password': 'Securepass123!',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        })
        self.assertRedirects(response, reverse('tresor:password_change_done'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecure456!'))

    def test_wrong_old_password_rejected(self):
        response = self.client.post(reverse('tresor:password_change'), {
            'old_password': 'wrongpassword',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Securepass123!'))


class RBACTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student1', password='Securepass123!'
        )
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor.groups.add(self.instructor_group)

    def test_anonymous_cannot_access_instructor_dashboard(self):
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_instructor_dashboard(self):
        self.client.login(username='student1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_instructor_dashboard(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_access_instructor_dashboard(self):
        staff = User.objects.create_user(
            username='staffuser', password='Securepass123!', is_staff=True
        )
        self.client.login(username='staffuser', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_instructor_badge(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertContains(response, 'Instructor')

    def test_dashboard_shows_student_badge(self):
        self.client.login(username='student1', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertContains(response, 'Student')

    def test_instructor_sees_all_users(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertContains(response, 'student1')


class IDORProfileViewTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', password='Securepass123!'
        )
        self.user_b = User.objects.create_user(
            username='userb', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor.groups.add(self.instructor_group)

    def test_user_can_view_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'userb'}))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_view_profile(self):
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_profile_returns_404(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'nobody'}))
        self.assertEqual(response.status_code, 404)

    def test_instructor_can_view_any_profile(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)


class IDORProfileEditTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', password='Securepass123!'
        )
        self.user_b = User.objects.create_user(
            username='userb', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor.groups.add(self.instructor_group)

    def test_user_can_edit_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_edit_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'userb'}))
        self.assertEqual(response.status_code, 403)

    def test_instructor_cannot_edit_other_users_profile(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_edit_profile(self):
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 302)

    def test_post_edit_saves_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.post(
            reverse('tresor:profile_edit', kwargs={'username': 'usera'}),
            {'bio': 'My updated bio', 'first_name': 'User', 'last_name': 'A', 'email': 'usera@test.com'},
        )
        self.assertRedirects(response, reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.user_a.profile.refresh_from_db()
        self.assertEqual(self.user_a.profile.bio, 'My updated bio')

    def test_post_cannot_edit_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.post(
            reverse('tresor:profile_edit', kwargs={'username': 'userb'}),
            {'bio': 'Injected bio', 'first_name': 'Hacked', 'last_name': 'B', 'email': 'b@test.com'},
        )
        self.assertEqual(response.status_code, 403)
        self.user_b.profile.refresh_from_db()
        self.assertNotEqual(self.user_b.profile.bio, 'Injected bio')


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetuser',
            email='resetuser@test.com',
            password='Securepass123!',
        )

    def test_reset_request_page_loads(self):
        response = self.client.get(reverse('tresor:password_reset'))
        self.assertEqual(response.status_code, 200)

    def test_reset_sent_page_loads(self):
        response = self.client.get(reverse('tresor:password_reset_done'))
        self.assertEqual(response.status_code, 200)

    def test_valid_email_sends_reset_email(self):
        response = self.client.post(reverse('tresor:password_reset'), {
            'email': 'resetuser@test.com',
        })
        self.assertRedirects(response, reverse('tresor:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

    def test_nonexistent_email_does_not_send_email(self):
        response = self.client.post(reverse('tresor:password_reset'), {
            'email': 'nobody@test.com',
        })
        self.assertRedirects(response, reverse('tresor:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_nonexistent_email_gives_same_response_as_valid(self):
        valid_response = self.client.post(reverse('tresor:password_reset'), {
            'email': 'resetuser@test.com',
        })
        self.client.get('/')
        invalid_response = self.client.post(reverse('tresor:password_reset'), {
            'email': 'nobody@test.com',
        })
        self.assertEqual(valid_response.status_code, invalid_response.status_code)
        self.assertEqual(valid_response['Location'], invalid_response['Location'])

    def test_valid_token_confirms_reset_page(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.get(
            reverse('tresor:password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set a new password')

    def test_invalid_token_shows_error(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse('tresor:password_reset_confirm', kwargs={'uidb64': uid, 'token': 'invalid-token'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid or has expired')

    def test_successful_reset_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.client.get(
            reverse('tresor:password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
            follow=True,
        )
        confirm_url = reverse('tresor:password_reset_confirm', kwargs={'uidb64': uid, 'token': 'set-password'})
        response = self.client.post(confirm_url, {
            'new_password1': 'NewSecure789!',
            'new_password2': 'NewSecure789!',
        })
        self.assertRedirects(response, reverse('tresor:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecure789!'))

    def test_reset_complete_page_loads(self):
        response = self.client.get(reverse('tresor:password_reset_complete'))
        self.assertEqual(response.status_code, 200)


class BruteForceProtectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='targetuser', password='Securepass123!'
        )
        self.login_url = reverse('tresor:login')

    def _fail_login(self, times=1):
        for _ in range(times):
            self.client.post(self.login_url, {
                'username': 'targetuser',
                'password': 'wrongpassword',
            })

    def test_single_failed_attempt_allowed(self):
        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_attempts_are_recorded(self):
        self._fail_login(3)
        attempt = LoginAttempt.objects.get(username='targetuser')
        self.assertEqual(attempt.attempts, 3)

    def test_account_locked_after_max_attempts(self):
        self._fail_login(MAX_ATTEMPTS)
        attempt = LoginAttempt.objects.get(username='targetuser')
        self.assertTrue(attempt.is_locked())

    def test_locked_account_cannot_login_with_correct_password(self):
        self._fail_login(MAX_ATTEMPTS)
        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'Securepass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_lockout_message_shown(self):
        self._fail_login(MAX_ATTEMPTS)
        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'Securepass123!',
        })
        self.assertContains(response, 'Too many failed attempts')

    def test_successful_login_resets_attempts(self):
        self._fail_login(3)
        self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'Securepass123!',
        })
        attempt = LoginAttempt.objects.get(username='targetuser')
        self.assertEqual(attempt.attempts, 0)
        self.assertIsNone(attempt.locked_until)

    def test_lockout_expires_after_timeout(self):
        self._fail_login(MAX_ATTEMPTS)
        attempt = LoginAttempt.objects.get(username='targetuser')
        attempt.locked_until = timezone.now() - timezone.timedelta(minutes=1)
        attempt.save()

        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))

    def test_normal_login_unaffected(self):
        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))


class StoredXSSTests(TestCase):
    def setUp(self):
        self.attacker = User.objects.create_user('attacker', password='Securepass123!')
        self.viewer = User.objects.create_user('viewer', password='Securepass123!')
        instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.viewer.groups.add(instructor_group)

    def _get_profile(self, username):
        self.client.login(username='viewer', password='Securepass123!')
        return self.client.get(reverse('tresor:profile_view', kwargs={'username': username}))

    def test_script_tag_in_bio_is_escaped(self):
        self.attacker.profile.bio = '<script>alert("xss")</script>'
        self.attacker.profile.save()
        response = self._get_profile('attacker')
        self.assertNotIn(b'<script>alert("xss")</script>', response.content)
        self.assertIn(b'&lt;script&gt;', response.content)

    def test_img_onerror_in_bio_is_escaped(self):
        self.attacker.profile.bio = '<img src=x onerror=alert(1)>'
        self.attacker.profile.save()
        response = self._get_profile('attacker')
        self.assertNotIn(b'<img src=x onerror=alert(1)>', response.content)
        self.assertIn(b'&lt;img', response.content)

    def test_anchor_href_javascript_in_bio_is_escaped(self):
        self.attacker.profile.bio = '<a href="javascript:alert(1)">click</a>'
        self.attacker.profile.save()
        response = self._get_profile('attacker')
        self.assertNotIn(b'href="javascript:', response.content)
        self.assertIn(b'&lt;a', response.content)

    def test_plain_bio_text_renders_correctly(self):
        self.attacker.profile.bio = 'Hello, I am a student.'
        self.attacker.profile.save()
        response = self._get_profile('attacker')
        self.assertIn(b'Hello, I am a student.', response.content)

    def test_own_profile_bio_is_escaped(self):
        self.attacker.profile.bio = '<script>steal(document.cookie)</script>'
        self.attacker.profile.save()
        self.client.login(username='attacker', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'attacker'}))
        self.assertNotIn(b'<script>', response.content)
        self.assertIn(b'&lt;script&gt;', response.content)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
