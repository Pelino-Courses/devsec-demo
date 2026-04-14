
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


class AuditLoggingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='StrongPass123!'
        )

    def test_registration_is_logged(self):
        with self.assertLogs('jeanclaudeirumva.audit', level='INFO') as cm:
            self.client.post(reverse('jeanclaudeirumva:register'), {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
        self.assertTrue(any('REGISTRATION' in msg for msg in cm.output))
        self.assertTrue(any('newuser' in msg for msg in cm.output))

    def test_login_success_is_logged(self):
        with self.assertLogs('jeanclaudeirumva.audit', level='INFO') as cm:
            self.client.post(reverse('jeanclaudeirumva:login'), {
                'username': 'testuser',
                'password': 'StrongPass123!',
            })
        self.assertTrue(any('LOGIN_SUCCESS' in msg for msg in cm.output))
        self.assertTrue(any('testuser' in msg for msg in cm.output))

    def test_login_failure_is_logged(self):
        with self.assertLogs('jeanclaudeirumva.audit', level='WARNING') as cm:
            self.client.post(reverse('jeanclaudeirumva:login'), {
                'username': 'testuser',
                'password': 'WrongPassword!',
            })
        self.assertTrue(any('LOGIN_FAILURE' in msg for msg in cm.output))
        self.assertTrue(any('testuser' in msg for msg in cm.output))

    def test_logout_is_logged(self):
        self.client.login(username='testuser', password='StrongPass123!')
        with self.assertLogs('jeanclaudeirumva.audit', level='INFO') as cm:
            self.client.post(reverse('jeanclaudeirumva:logout'))
        self.assertTrue(any('LOGOUT' in msg for msg in cm.output))
        self.assertTrue(any('testuser' in msg for msg in cm.output))

    def test_password_change_is_logged(self):
        self.client.login(username='testuser', password='StrongPass123!')
        with self.assertLogs('jeanclaudeirumva.audit', level='INFO') as cm:
            self.client.post(reverse('jeanclaudeirumva:password_change'), {
                'old_password': 'StrongPass123!',
                'new_password1': 'NewStrongPass123!',
                'new_password2': 'NewStrongPass123!',
            })
        self.assertTrue(any('PASSWORD_CHANGE' in msg for msg in cm.output))
        self.assertTrue(any('testuser' in msg for msg in cm.output))

    def test_password_never_logged(self):
        with self.assertLogs('jeanclaudeirumva.audit', level='INFO') as cm:
            self.client.post(reverse('jeanclaudeirumva:login'), {
                'username': 'testuser',
                'password': 'StrongPass123!',
            })
        for msg in cm.output:
            self.assertNotIn('StrongPass123!', msg)


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