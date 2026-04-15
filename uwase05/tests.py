from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


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

    def test_login_and_dashboard_access(self):
        login_success = self.client.login(username='tester', password='StrongPass123')
        self.assertTrue(login_success)

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

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
