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
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='OtherPass123!'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='StaffPass123!',
            is_staff=True
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

    def test_home_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:home'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_requires_login(self):
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_cannot_access_staff_dashboard(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_staff_user_can_access_staff_dashboard(self):
        self.client.login(username='staffuser', password='StaffPass123!')
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_access_profile(self):
        self.client.logout()
        response = self.client.get(reverse('ndayishimiye:profile'))
        self.assertEqual(response.status_code, 302)

    def test_user_can_view_own_profile_by_id(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.user.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_profile_by_id(self):
        self.client.login(username='testuser', password='TestPass123!')
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.other_user.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_can_view_any_profile_by_id(self):
        self.client.login(username='staffuser', password='StaffPass123!')
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.user.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_view_profile_by_id(self):
        self.client.logout()
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.user.id})
        )
        self.assertEqual(response.status_code, 302)
