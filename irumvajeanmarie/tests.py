from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
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

    def test_profile_created_on_register(self):
        self.client.post(reverse('irumvajeanmarie:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        user = User.objects.get(username='testuser')
        self.assertTrue(Profile.objects.filter(user=user).exists())

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
        Profile.objects.create(user=self.user)

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
        Profile.objects.create(user=self.user)

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
        Profile.objects.create(user=self.user)
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