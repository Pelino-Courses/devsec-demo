from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import Profile


User = get_user_model()


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

	def test_profile_update_changes_user_and_profile_fields(self):
		self.client.login(username=self.username, password=self.password)

		response = self.client.post(
			reverse('webwi:profile'),
			{
				'first_name': 'Alice',
				'last_name': 'Tester',
				'email': 'alice@example.com',
				'display_name': 'alice-t',
				'bio': 'Security-focused student.',
			},
			follow=True,
		)

		self.assertRedirects(response, reverse('webwi:profile'))

		self.user.refresh_from_db()
		profile = Profile.objects.get(user=self.user)
		self.assertEqual(self.user.first_name, 'Alice')
		self.assertEqual(self.user.last_name, 'Tester')
		self.assertEqual(self.user.email, 'alice@example.com')
		self.assertEqual(profile.display_name, 'alice-t')
		self.assertEqual(profile.bio, 'Security-focused student.')


class RBACTests(TestCase):
	def setUp(self):
		self.password = 'SafePass123!'
		self.standard_user = User.objects.create_user(
			username='standard',
			email='standard@example.com',
			password=self.password,
		)
		self.staff_user = User.objects.create_user(
			username='staffer',
			email='staff@example.com',
			password=self.password,
			is_staff=True,
		)

	def test_anonymous_cannot_access_privileged_directory(self):
		response = self.client.get(reverse('webwi:user_directory'))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('webwi:login'), response['Location'])

	def test_authenticated_standard_user_is_denied_privileged_directory(self):
		self.client.login(username='standard', password=self.password)
		response = self.client.get(reverse('webwi:user_directory'))
		self.assertEqual(response.status_code, 403)

	def test_staff_user_can_access_privileged_directory(self):
		self.client.login(username='staffer', password=self.password)
		response = self.client.get(reverse('webwi:user_directory'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Privileged User Directory')

	def test_permission_granted_user_can_access_privileged_directory(self):
		permission = Permission.objects.get(codename='view_user_directory')
		self.standard_user.user_permissions.add(permission)

		self.client.login(username='standard', password=self.password)
		response = self.client.get(reverse('webwi:user_directory'))
		self.assertEqual(response.status_code, 200)

	def test_users_navigation_visibility_matches_role(self):
		self.client.login(username='standard', password=self.password)
		standard_response = self.client.get(reverse('webwi:dashboard'))
		self.assertNotContains(standard_response, reverse('webwi:user_directory'))

		self.client.logout()
		self.client.login(username='staffer', password=self.password)
		staff_response = self.client.get(reverse('webwi:dashboard'))
		self.assertContains(staff_response, reverse('webwi:user_directory'))


class IDORPreventionTests(TestCase):
	"""Verify that the profile view enforces object-level ownership.

	These tests document the IDOR risk and confirm it is prevented:
	a user must never be able to read or modify another user's profile
	data by supplying a different identifier in the URL, query string,
	or POST body.
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user_a = User.objects.create_user(
			username='user_a',
			email='a@example.com',
			password=self.password,
			first_name='Alice',
		)
		self.user_b = User.objects.create_user(
			username='user_b',
			email='b@example.com',
			password=self.password,
			first_name='Bob',
		)
		Profile.objects.get_or_create(user=self.user_a)
		Profile.objects.get_or_create(user=self.user_b)

	def test_profile_view_returns_only_own_profile(self):
		"""GET /profile/ binds the form to the authenticated user's profile, not another user's."""
		self.client.login(username='user_a', password=self.password)
		response = self.client.get(reverse('webwi:profile'))
		self.assertEqual(response.status_code, 200)
		form = response.context['form']
		self.assertEqual(form.instance.user, self.user_a)
		self.assertNotEqual(form.instance.user, self.user_b)

	def test_profile_update_does_not_modify_another_users_data(self):
		"""POST /profile/ updates only the authenticated user; other accounts are unaffected."""
		self.client.login(username='user_a', password=self.password)
		self.client.post(
			reverse('webwi:profile'),
			{
				'first_name': 'Attacker',
				'last_name': 'Owned',
				'email': 'hacked@example.com',
				'display_name': 'hacked',
				'bio': 'I was here.',
			},
		)
		self.user_b.refresh_from_db()
		self.assertEqual(self.user_b.first_name, 'Bob')
		self.assertNotEqual(self.user_b.email, 'hacked@example.com')

	def test_submitting_another_users_profile_pk_does_not_affect_them(self):
		"""A pk value in POST data cannot retarget an update to another user's profile row."""
		profile_b = Profile.objects.get(user=self.user_b)

		self.client.login(username='user_a', password=self.password)
		self.client.post(
			reverse('webwi:profile'),
			{
				'id': profile_b.pk,
				'first_name': 'Injected',
				'last_name': 'Value',
				'email': 'injected@example.com',
				'display_name': 'injected',
				'bio': 'Injected bio.',
			},
		)

		profile_b.refresh_from_db()
		self.assertNotEqual(profile_b.bio, 'Injected bio.')
		self.user_b.refresh_from_db()
		self.assertNotEqual(self.user_b.email, 'injected@example.com')

	def test_unauthenticated_access_to_profile_is_redirected(self):
		"""Unauthenticated requests to /profile/ are redirected to login, not served."""
		response = self.client.get(reverse('webwi:profile'))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('webwi:login'), response['Location'])
