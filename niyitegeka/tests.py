from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile


class RegistrationTest(TestCase):

    def test_register_page_loads(self):
        response = self.client.get(reverse('niyitegeka:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_success(self):
        self.client.post(reverse('niyitegeka:register'), {
            'username': 'peter',
            'email': 'peter@example.com',
            'password1': 'Secure@1234',
            'password2': 'Secure@1234',
        })
        self.assertEqual(User.objects.filter(username='peter').count(), 1)

    def test_register_password_mismatch(self):
        self.client.post(reverse('niyitegeka:register'), {
            'username': 'peter2',
            'email': 'peter2@example.com',
            'password1': 'Secure@1234',
            'password2': 'WrongPassword',
        })
        self.assertEqual(User.objects.filter(username='peter2').count(), 0)


class LoginTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('niyitegeka:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'Secure@1234',
        })
        self.assertRedirects(response, reverse('niyitegeka:dashboard'))

    def test_login_wrong_password(self):
        response = self.client.post(reverse('niyitegeka:login'), {
            'username': 'peter',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)


class ProtectedPageTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/dashboard/'
        )

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/profile/'
        )


class LogoutTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )

    def test_logout_redirects(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:logout'))
        self.assertRedirects(response, reverse('niyitegeka:login'))


class ProfileTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user)
        self.client.login(username='peter', password='Secure@1234')

    def test_profile_page_loads(self):
        response = self.client.get(reverse('niyitegeka:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        response = self.client.post(reverse('niyitegeka:profile'), {
            'bio': 'I am peter.',
            'phone': '0781234567',
        })
        self.assertRedirects(response, reverse('niyitegeka:profile'))
        updated = Profile.objects.get(user=self.user)
        self.assertEqual(updated.bio, 'I am peter.')


class RoleBasedAccessTest(TestCase):

    def setUp(self):
        self.normal_user = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        self.staff_user = User.objects.create_user(
            username='staffpeter',
            password='Secure@1234',
            is_staff=True
        )

    def test_staff_dashboard_requires_login(self):
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/staff/'
        )

    def test_normal_user_cannot_access_staff_dashboard(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/staff/'
        )

    def test_staff_user_can_access_staff_dashboard(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_shows_user_list(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:staffdashboard'))
        self.assertContains(response, 'peter')

    def test_staff_link_visible_to_staff(self):
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertContains(response, '/auth/staff/')

    def test_staff_link_hidden_from_normal_user(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(reverse('niyitegeka:dashboard'))
        self.assertNotContains(response, '/auth/staff/')


class IDORPreventionTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='peter',
            password='Secure@1234'
        )
        self.user2 = User.objects.create_user(
            username='paul',
            password='Secure@1234'
        )
        Profile.objects.create(user=self.user1)
        Profile.objects.create(user=self.user2)

    def test_user_can_view_own_profile_detail(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_profile_detail(self):
        self.client.login(username='peter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['paul'])
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_any_profile_detail(self):
        staff = User.objects.create_user(
            username='staffpeter',
            password='Secure@1234',
            is_staff=True
        )
        Profile.objects.create(user=staff)
        self.client.login(username='staffpeter', password='Secure@1234')
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['paul'])
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_view_profile_detail(self):
        response = self.client.get(
            reverse('niyitegeka:profiledetail', args=['peter'])
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=/auth/profile/peter/'
        )
