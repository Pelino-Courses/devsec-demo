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


class IDORTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='StrongPass123!'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='StrongPass123!'
        )
        self.client.login(username='user1', password='StrongPass123!')

    def test_user_can_access_own_profile(self):
        response = self.client.get(
            reverse('jeanclaudeirumva:profile_detail',
                    kwargs={'user_id': self.user1.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_other_profile(self):
        response = self.client.get(
            reverse('jeanclaudeirumva:profile_detail',
                    kwargs={'user_id': self.user2.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_access_profile(self):
        self.client.logout()
        response = self.client.get(
            reverse('jeanclaudeirumva:profile_detail',
                    kwargs={'user_id': self.user1.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_profile_view_always_shows_own_profile(self):
        response = self.client.get(reverse('jeanclaudeirumva:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user1')

    def test_password_change_only_affects_own_account(self):
        response = self.client.post(
            reverse('jeanclaudeirumva:password_change'), {
                'old_password': 'StrongPass123!',
                'new_password1': 'NewStrongPass123!',
                'new_password2': 'NewStrongPass123!',
            }
        )
        self.assertRedirects(response, reverse('jeanclaudeirumva:dashboard'))
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password('NewStrongPass123!'))
        self.user2.refresh_from_db()
        self.assertTrue(self.user2.check_password('StrongPass123!'))

    def test_nonexistent_user_profile_returns_404(self):
        response = self.client.get(
            reverse('jeanclaudeirumva:profile_detail',
                    kwargs={'user_id': 99999})
        )
        self.assertEqual(response.status_code, 404)


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