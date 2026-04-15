from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from uwase05.models import Profile


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
        self.password_change_done_url = reverse('uwase05:password_change_done')
        self.instructor_url = reverse('uwase05:instructor_dashboard')

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

    def test_password_change_done_requires_authentication(self):
        response = self.client.get(self.password_change_done_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.password_change_done_url}')

    def test_profile_returns_current_user_profile(self):
        profile = self.user.profile
        profile.bio = 'Tester bio'
        profile.save()

        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='OtherPass123',
        )
        other_profile = other_user.profile
        other_profile.bio = 'Other bio'
        other_profile.save()

        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile'].user, self.user)
        self.assertContains(response, 'Tester bio')
        self.assertNotContains(response, 'Other bio')

    def test_standard_user_cannot_access_instructor_area(self):
        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.instructor_url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_group_can_access_instructor_area(self):
        instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.user.groups.add(instructor_group)
        self.client.login(username='tester', password='StrongPass123')
        response = self.client.get(self.instructor_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Instructor Area')

    def test_instructor_area_is_denied_to_anonymous_users(self):
        response = self.client.get(self.instructor_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.instructor_url}')

    def test_new_user_is_assigned_student_group(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'standarduser',
                'email': 'student@example.com',
                'password1': 'SafePass1234',
                'password2': 'SafePass1234',
            },
        )
        self.assertRedirects(response, self.login_url)
        new_user = User.objects.get(username='standarduser')
        self.assertTrue(new_user.groups.filter(name='student').exists())
