from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
	def setUp(self):
		self.username = 'student1'
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username=self.username,
			email='student1@example.com',
			password=self.password,
		)

	def test_register_success(self):
		response = self.client.post(
			reverse('webwi:register'),
			{
				'username': 'newstudent',
				'email': 'newstudent@example.com',
				'password1': 'AnotherSafePass123!',
				'password2': 'AnotherSafePass123!',
			},
			follow=True,
		)

		self.assertRedirects(response, reverse('webwi:login'))
		self.assertTrue(User.objects.filter(username='newstudent').exists())

	def test_register_rejects_duplicate_username(self):
		response = self.client.post(
			reverse('webwi:register'),
			{
				'username': self.username,
				'email': 'other@example.com',
				'password1': 'AnotherSafePass123!',
				'password2': 'AnotherSafePass123!',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A user with that username already exists')

	def test_login_and_logout(self):
		login_response = self.client.post(
			reverse('webwi:login'),
			{'username': self.username, 'password': self.password},
			follow=True,
		)

		self.assertRedirects(login_response, reverse('webwi:dashboard'))
		self.assertTrue(login_response.context['user'].is_authenticated)

		logout_response = self.client.post(reverse('webwi:logout'), follow=True)
		self.assertRedirects(logout_response, reverse('webwi:login'))
		self.assertFalse(logout_response.context['user'].is_authenticated)

	def test_protected_pages_require_authentication(self):
		dashboard_response = self.client.get(reverse('webwi:dashboard'))
		self.assertEqual(dashboard_response.status_code, 302)
		self.assertIn(reverse('webwi:login'), dashboard_response['Location'])

		profile_response = self.client.get(reverse('webwi:profile'))
		self.assertEqual(profile_response.status_code, 302)
		self.assertIn(reverse('webwi:login'), profile_response['Location'])

	def test_password_change(self):
		self.client.login(username=self.username, password=self.password)

		change_response = self.client.post(
			reverse('webwi:password_change'),
			{
				'old_password': self.password,
				'new_password1': 'BrandNewSafePass123!',
				'new_password2': 'BrandNewSafePass123!',
			},
		)

		self.assertRedirects(
			change_response,
			reverse('webwi:password_change_done'),
			fetch_redirect_response=False,
		)

		self.client.logout()
		login_again = self.client.post(
			reverse('webwi:login'),
			{'username': self.username, 'password': 'BrandNewSafePass123!'},
		)
		self.assertRedirects(
			login_again,
			reverse('webwi:dashboard'),
			fetch_redirect_response=False,
		)
