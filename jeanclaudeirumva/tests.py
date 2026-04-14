from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_valid_user(self):
        response = self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='Pass123!')
        response = self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')

    def test_register_duplicate_email(self):
        User.objects.create_user(username='user1', email='same@example.com', password='Pass123!')
        response = self.client.post(reverse('jeanclaudeirumva:register'), {
            'username': 'user2',
            'email': 'same@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already registered')


class LoginTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('jeanclaudeirumva:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials(self):
        response = self.client.post(reverse('jeanclaudeirumva:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('jeanclaudeirumva:login'), {
            'username': 'testuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')


class RedirectSafetyTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )

    def test_safe_internal_redirect_after_login(self):
        response = self.client.post(
            reverse('jeanclaudeirumva:login') + '?next=/auth/profile/',
            {
                'username': 'testuser',
                'password': 'StrongPass123!',
                'next': '/auth/profile/',
            }
        )
        self.assertRedirects(response, '/auth/profile/')

    def test_unsafe_external_redirect_rejected(self):
        response = self.client.post(
            reverse('jeanclaudeirumva:login'),
            {
                'username': 'testuser',
                'password': 'StrongPass123!',
                'next': 'https://evil.com',
            }
        )
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_unsafe_redirect_with_double_slash_rejected(self):
        response = self.client.post(
            reverse('jeanclaudeirumva:login'),
            {
                'username': 'testuser',
                'password': 'StrongPass123!',
                'next': '//evil.com',
            }
        )
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))

    def test_login_without_next_redirects_to_dashboard(self):
        response = self.client.post(reverse('jeanclaudeirumva:login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))


class ProtectedPagesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('jeanclaudeirumva:dashboard'))
        self.assertRedirects(response, '/auth/login/?next=/auth/dashboard/')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertRedirects(response, '/auth/login/?next=/auth/profile/')

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('jeanclaudeirumva:dashboard'))
        self.assertEqual(response.status_code, 200)


class LogoutTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='StrongPass123!'
        )
        self.client.login(username='testuser', password='StrongPass123!')

    def test_logout_requires_post(self):
        response = self.client.get(reverse('jeanclaudeirumva:logout'))
        self.assertEqual(response.status_code, 200)

    def test_logout_success(self):
        response = self.client.post(reverse('jeanclaudeirumva:logout'))
        self.assertRedirects(response, reverse('jeanclaudeirumva:login'))