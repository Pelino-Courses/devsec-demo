from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class UASTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!'
        )

    def test_register_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:register'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('ndayishimiye:login'), {
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('ndayishimiye:profile'))

    def test_profile_requires_login(self):
        response = self.client.get(reverse('ndayishimiye:profile'))
        self.assertEqual(response.status_code, 302)

    def test_logout(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('ndayishimiye:logout'))
        self.assertRedirects(response, reverse('ndayishimiye:login'))
        