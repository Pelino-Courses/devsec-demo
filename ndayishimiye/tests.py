from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User


@override_settings(
    AXES_ENABLED=True,
    AXES_FAILURE_LIMIT=5,
    AXES_COOLOFF_TIME=1,
)
class UASTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
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
        self.client.force_login(self.user)
        response = self.client.get(reverse('ndayishimiye:logout'))
        self.assertRedirects(response, reverse('ndayishimiye:login'))

    def test_home_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:home'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_requires_login(self):
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_cannot_access_staff_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_staff_user_can_access_staff_dashboard(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('ndayishimiye:staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_access_profile(self):
        self.client.logout()
        response = self.client.get(reverse('ndayishimiye:profile'))
        self.assertEqual(response.status_code, 302)

    def test_user_can_view_own_profile_by_id(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.user.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_profile_by_id(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('ndayishimiye:profile_by_id',
                    kwargs={'user_id': self.other_user.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_can_view_any_profile_by_id(self):
        self.client.force_login(self.staff_user)
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

    def test_password_reset_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:password_reset'))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_done_page_loads(self):
        response = self.client.get(reverse('ndayishimiye:password_reset_done'))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_with_valid_email(self):
        response = self.client.post(reverse('ndayishimiye:password_reset'), {
            'email': 'testuser@example.com'
        })
        self.assertEqual(response.status_code, 302)

    def test_password_reset_with_invalid_email(self):
        response = self.client.post(reverse('ndayishimiye:password_reset'), {
            'email': 'nonexistent@example.com'
        })
        self.assertEqual(response.status_code, 302)

    def test_password_reset_complete_page_loads(self):
        response = self.client.get(
            reverse('ndayishimiye:password_reset_complete')
        )
        self.assertEqual(response.status_code, 200)

    def test_login_lockout_after_too_many_attempts(self):
        for i in range(5):
            self.client.post(reverse('ndayishimiye:login'), {
                'username': 'testuser',
                'password': 'WrongPassword!'
            })
        response = self.client.post(reverse('ndayishimiye:login'), {
            'username': 'testuser',
            'password': 'WrongPassword!'
        })
        self.assertIn(response.status_code, [403, 429])

    def test_successful_login_not_blocked(self):
        response = self.client.post(reverse('ndayishimiye:login'), {
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('ndayishimiye:profile'))

    def test_profile_update_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse('ndayishimiye:profile_update'),
            {'email': 'newemail@example.com'}
        )
        self.assertEqual(response.status_code, 403)

    def test_profile_update_works_with_csrf(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('ndayishimiye:profile_update'),
            {'email': 'newemail@example.com'}
        )
        self.assertRedirects(response, reverse('ndayishimiye:profile'))

    def test_register_post_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse('ndayishimiye:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        self.assertEqual(response.status_code, 403)

    def test_login_post_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse('ndayishimiye:login'), {
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 403)
