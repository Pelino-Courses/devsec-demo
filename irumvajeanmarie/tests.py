from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from datetime import timedelta
from .models import Profile, LoginAttempt, AccountLockout, UserDocument


class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('irumvajeanmarie:register'))
        self.assertEqual(response.status_code, 200)

    def test_user_can_register(self):
        response = self.client.post(reverse('irumvajeanmarie:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(User.objects.filter(username='testuser').count(), 1)
        self.assertRedirects(response, reverse('irumvajeanmarie:login'))

    def test_profile_created_with_student_role(self):
        self.client.post(reverse('irumvajeanmarie:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        user = User.objects.get(username='testuser')
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, Profile.ROLE_STUDENT)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username='existing', email='same@example.com', password='pass123')
        response = self.client.post(reverse('irumvajeanmarie:register'), {
            'username': 'newuser',
            'email': 'same@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This email is already registered.')


class LoginTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_login_page_loads(self):
        response = self.client.get(reverse('irumvajeanmarie:login'))
        self.assertEqual(response.status_code, 200)

    def test_user_can_login(self):
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))

    def test_invalid_login_rejected(self):
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')


class ProtectedViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('irumvajeanmarie:dashboard'))
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/dashboard/'
        )

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('irumvajeanmarie:profile'))
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/profile/'
        )

    def test_logout_redirects_to_login(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:logout'))
        self.assertRedirects(response, reverse('irumvajeanmarie:login'))


class PasswordChangeTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)
        self.client.login(username='testuser', password='StrongPass123!')

    def test_password_change_page_loads(self):
        response = self.client.get(reverse('irumvajeanmarie:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_succeeds(self):
        response = self.client.post(reverse('irumvajeanmarie:password_change'), {
            'old_password': 'StrongPass123!',
            'new_password1': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))


class RBACTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student', email='student@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.student, role=Profile.ROLE_STUDENT)

        self.instructor = User.objects.create_user(
            username='instructor', email='instructor@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.instructor, role=Profile.ROLE_INSTRUCTOR)

        self.admin = User.objects.create_user(
            username='adminuser', email='admin@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.admin, role=Profile.ROLE_ADMIN)

    def test_student_cannot_access_instructor_panel(self):
        self.client.login(username='student', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:instructor_panel'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_instructor_panel(self):
        self.client.login(username='instructor', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:instructor_panel'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_instructor_panel(self):
        self.client.login(username='adminuser', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:instructor_panel'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_admin_panel(self):
        self.client.login(username='student', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:admin_panel'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_cannot_access_admin_panel(self):
        self.client.login(username='instructor', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:admin_panel'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_panel(self):
        self.client.login(username='adminuser', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:admin_panel'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_access_instructor_panel(self):
        response = self.client.get(reverse('irumvajeanmarie:instructor_panel'))
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/instructor/'
        )

    def test_anonymous_cannot_access_admin_panel(self):
        response = self.client.get(reverse('irumvajeanmarie:admin_panel'))
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/admin-panel/'
        )


class IDORTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1', email='user1@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.user1, role=Profile.ROLE_STUDENT)

        self.user2 = User.objects.create_user(
            username='user2', email='user2@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.user2, role=Profile.ROLE_STUDENT)

        self.instructor = User.objects.create_user(
            username='instructor', email='instructor@example.com', password='StrongPass123!')
        Profile.objects.create(user=self.instructor, role=Profile.ROLE_INSTRUCTOR)

    def test_user_can_view_own_profile(self):
        self.client.login(username='user1', password='StrongPass123!')
        response = self.client.get(
            reverse('irumvajeanmarie:view_profile', kwargs={'username': 'user1'})
        )
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_view_other_profile(self):
        self.client.login(username='user1', password='StrongPass123!')
        response = self.client.get(
            reverse('irumvajeanmarie:view_profile', kwargs={'username': 'user2'})
        )
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_view_any_profile(self):
        self.client.login(username='instructor', password='StrongPass123!')
        response = self.client.get(
            reverse('irumvajeanmarie:view_profile', kwargs={'username': 'user1'})
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_view_profile(self):
        response = self.client.get(
            reverse('irumvajeanmarie:view_profile', kwargs={'username': 'user1'})
        )
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/profile/user1/'
        )

    def test_profile_edit_always_uses_own_profile(self):
        self.client.login(username='user1', password='StrongPass123!')
        response = self.client.post(reverse('irumvajeanmarie:profile'), {
            'bio': 'My updated bio',
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:profile'))
        profile = Profile.objects.get(user=self.user1)
        self.assertEqual(profile.bio, 'My updated bio')


class PasswordResetTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_password_reset_page_loads(self):
        response = self.client.get(reverse('irumvajeanmarie:password_reset'))
        self.assertEqual(response.status_code, 200)

    def test_valid_email_submission_succeeds(self):
        response = self.client.post(reverse('irumvajeanmarie:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:password_reset_done'))

    def test_invalid_email_submission_succeeds(self):
        response = self.client.post(reverse('irumvajeanmarie:password_reset'), {
            'email': 'nonexistent@example.com'
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:password_reset_done'))

    def test_reset_confirm_page_loads_with_valid_token(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.get(
            reverse('irumvajeanmarie:password_reset_confirm',
                    kwargs={'uidb64': uidb64, 'token': token}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)


class BruteForceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_normal_login_works_and_records_attempt(self):
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!'
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))
        self.assertTrue(LoginAttempt.objects.filter(username='testuser', was_successful=True).exists())

    def test_failed_login_records_attempt(self):
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'WrongPassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(LoginAttempt.objects.filter(username='testuser', was_successful=False).exists())

    def test_account_lockout_after_five_failures(self):
        for _ in range(5):
            self.client.post(reverse('irumvajeanmarie:login'), {
                'username': 'testuser',
                'password': 'WrongPassword123!'
            })
        self.assertTrue(AccountLockout.objects.filter(username='testuser').exists())

    def test_locked_account_cannot_login_with_correct_password(self):
        AccountLockout.objects.create(
            username='testuser',
            locked_until=timezone.now() + timedelta(minutes=15)
        )
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account is locked')

    def test_lockout_expires(self):
        AccountLockout.objects.create(
            username='testuser',
            locked_until=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!'
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))
        self.assertFalse(AccountLockout.objects.filter(username='testuser').exists())


class CSRFHandlingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_contact_page_loads(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('irumvajeanmarie:contact_page'))
        self.assertEqual(response.status_code, 200)

    def test_post_with_valid_csrf_token_succeeds(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser', password='StrongPass123!')
        resp = csrf_client.get(reverse('irumvajeanmarie:contact_page'))
        csrftoken = resp.cookies['csrftoken'].value
        response = csrf_client.post(
            reverse('irumvajeanmarie:contact'),
            data={'message': 'Valid message'},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrftoken
        )
        self.assertEqual(response.status_code, 200)

    def test_post_without_csrf_token_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser', password='StrongPass123!')
        response = csrf_client.post(
            reverse('irumvajeanmarie:contact'),
            data={'message': 'Hacker message'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_redirects(self):
        response = self.client.post(reverse('irumvajeanmarie:contact'), {'message': 'Hi'})
        self.assertRedirects(response, '/irumvajeanmarie/login/?next=/irumvajeanmarie/contact/')


class SafeRedirectTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_login_with_safe_internal_next_parameter_redirects_correctly(self):
        response = self.client.post(
            f"{reverse('irumvajeanmarie:login')}?next=/irumvajeanmarie/dashboard/",
            {'username': 'testuser', 'password': 'StrongPass123!'}
        )
        self.assertRedirects(response, '/irumvajeanmarie/dashboard/', fetch_redirect_response=False)

    def test_login_with_external_next_parameter_falls_back_to_dashboard(self):
        response = self.client.post(
            f"{reverse('irumvajeanmarie:login')}?next=http://evil.com",
            {'username': 'testuser', 'password': 'StrongPass123!'}
        )
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))

    def test_login_with_protocol_relative_next_parameter_falls_back_to_dashboard(self):
        response = self.client.post(
            f"{reverse('irumvajeanmarie:login')}?next=//evil.com",
            {'username': 'testuser', 'password': 'StrongPass123!'}
        )
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))

    def test_normal_login_without_next_parameter_redirects_to_dashboard(self):
        response = self.client.post(reverse('irumvajeanmarie:login'), {
            'username': 'testuser', 'password': 'StrongPass123!'
        })
        self.assertRedirects(response, reverse('irumvajeanmarie:dashboard'))

    def test_logout_with_unsafe_next_parameter_falls_back(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(
            f"{reverse('irumvajeanmarie:logout')}?next=http://evil.com"
        )
        self.assertRedirects(response, reverse('irumvajeanmarie:login'), fetch_redirect_response=False)


class AuditLogTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)

    def test_registration_logs_event(self):
        with self.assertLogs('irumvajeanmarie.audit', level='INFO') as cm:
            self.client.post(reverse('irumvajeanmarie:register'), {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
        self.assertTrue(any('User registration: username=newuser, email=new@example.com' in log for log in cm.output))

    def test_login_success_logs_event(self):
        with self.assertLogs('irumvajeanmarie.audit', level='INFO') as cm:
            self.client.post(reverse('irumvajeanmarie:login'), {
                'username': 'testuser',
                'password': 'StrongPass123!',
            })
        self.assertTrue(any('Login success: username=testuser' in log for log in cm.output))

    def test_login_failure_logs_event(self):
        with self.assertLogs('irumvajeanmarie.audit', level='WARNING') as cm:
            self.client.post(reverse('irumvajeanmarie:login'), {
                'username': 'testuser',
                'password': 'WrongPass123!',
            })
        self.assertTrue(any('Login failure: username=testuser' in log for log in cm.output))
        self.assertTrue(any('reason=Invalid credentials' in log for log in cm.output))

    def test_logout_logs_event(self):
        self.client.login(username='testuser', password='StrongPass123!')
        with self.assertLogs('irumvajeanmarie.audit', level='INFO') as cm:
            self.client.get(reverse('irumvajeanmarie:logout'))
        self.assertTrue(any('Logout: username=testuser' in log for log in cm.output))


class StoredXSSTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)
        self.client.login(username='testuser', password='StrongPass123!')

    def test_bio_with_script_tag_is_escaped(self):
        self.client.post(reverse('irumvajeanmarie:profile'), {
            'bio': '<script>alert("XSS")</script>',
        })
        response = self.client.get(reverse('irumvajeanmarie:profile'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert("XSS")</script>')

    def test_bio_with_html_tags_is_escaped(self):
        self.client.post(reverse('irumvajeanmarie:profile'), {
            'bio': '<b>bold</b><img src=x onerror=alert(1)>',
        })
        response = self.client.get(reverse('irumvajeanmarie:profile'))
        self.assertContains(response, '&lt;b&gt;')
        self.assertNotContains(response, '<b>bold</b>')

    def test_username_display_is_escaped(self):
        response = self.client.get(reverse('irumvajeanmarie:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_legitimate_bio_renders_correctly(self):
        self.client.post(reverse('irumvajeanmarie:profile'), {
            'bio': 'I am a student at UR.',
        })
        response = self.client.get(reverse('irumvajeanmarie:profile'))
        self.assertContains(response, 'I am a student at UR.')


class AvatarUploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='uploader', email='uploader@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)
        self.client.login(username='uploader', password='StrongPass123!')
        self.url = reverse('irumvajeanmarie:upload_avatar')

    def _make_gif(self, name='avatar.gif'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Minimal valid GIF89a
        gif_content = (
            b'GIF89a\x01\x00\x01\x00\x00\xff\x00,'
            b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        return SimpleUploadedFile(name, gif_content, content_type='image/gif')

    def test_avatar_upload_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_avatar_upload_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/upload/avatar/'
        )

    def test_valid_image_upload_accepted(self):
        gif_file = self._make_gif()
        response = self.client.post(self.url, {'avatar': gif_file})
        self.assertRedirects(response, self.url)
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(bool(profile.avatar))

    def test_invalid_file_type_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        php_file = SimpleUploadedFile('shell.php', b'<?php echo 1; ?>', 'application/x-php')
        response = self.client.post(self.url, {'avatar': php_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid image')

    def test_file_too_large_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        large_content = b'A' * (2 * 1024 * 1024 + 1)
        large_file = SimpleUploadedFile('big.gif', large_content, 'image/gif')
        response = self.client.post(self.url, {'avatar': large_file})
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=self.user)
        self.assertFalse(bool(profile.avatar))


class DocumentUploadTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='docuser', email='docuser@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.user, role=Profile.ROLE_STUDENT)
        self.client.login(username='docuser', password='StrongPass123!')
        self.upload_url = reverse('irumvajeanmarie:upload_document')

    def _make_file(self, name, content=b'%PDF-1.4 sample', content_type='application/pdf'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_document_upload_page_loads(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 200)

    def test_document_upload_requires_login(self):
        self.client.logout()
        response = self.client.get(self.upload_url)
        self.assertRedirects(
            response,
            '/irumvajeanmarie/login/?next=/irumvajeanmarie/upload/document/'
        )

    def test_valid_document_upload_accepted(self):
        pdf_file = self._make_file('report.pdf')
        response = self.client.post(self.upload_url, {'document': pdf_file})
        self.assertRedirects(response, self.upload_url)
        self.assertTrue(
            UserDocument.objects.filter(user=self.user, original_filename='report.pdf').exists()
        )

    def test_invalid_document_type_rejected(self):
        exe_file = self._make_file('malware.exe', b'MZ\x90\x00', 'application/octet-stream')
        response = self.client.post(self.upload_url, {'document': exe_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not allowed')
        self.assertFalse(UserDocument.objects.filter(user=self.user).exists())

    def test_document_too_large_rejected(self):
        large_content = b'A' * (5 * 1024 * 1024 + 1)
        large_file = self._make_file('giant.txt', large_content, 'text/plain')
        response = self.client.post(self.upload_url, {'document': large_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'too large')
        self.assertFalse(UserDocument.objects.filter(user=self.user).exists())


class DocumentDeletionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='StrongPass123!'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='StrongPass123!'
        )
        Profile.objects.create(user=self.owner, role=Profile.ROLE_STUDENT)
        Profile.objects.create(user=self.other, role=Profile.ROLE_STUDENT)
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('doc.txt', b'hello', content_type='text/plain')
        self.doc = UserDocument.objects.create(
            user=self.owner,
            file=f,
            original_filename='doc.txt',
        )
        self.delete_url = reverse(
            'irumvajeanmarie:delete_document',
            kwargs={'document_id': self.doc.pk}
        )

    def test_owner_can_delete_document(self):
        self.client.login(username='owner', password='StrongPass123!')
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, reverse('irumvajeanmarie:upload_document'))
        self.assertFalse(UserDocument.objects.filter(pk=self.doc.pk).exists())

    def test_non_owner_delete_returns_403(self):
        self.client.login(username='other', password='StrongPass123!')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(UserDocument.objects.filter(pk=self.doc.pk).exists())

    def test_delete_requires_login(self):
        response = self.client.post(self.delete_url)
        self.assertRedirects(
            response,
            f'/irumvajeanmarie/login/?next=/irumvajeanmarie/upload/document/{self.doc.pk}/delete/'
        )