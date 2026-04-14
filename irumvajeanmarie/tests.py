from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .models import Profile


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