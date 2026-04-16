import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from .models import LoginAttempt, MAX_FAILED_ATTEMPTS, Profile


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


class PasswordResetFlowTests(TestCase):
	"""Verify the secure password reset workflow.

	Covers: request page, user-enumeration prevention, email delivery,
	token validation, new-password submission, and the completion page.
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username='resetuser',
			email='reset@example.com',
			password=self.password,
		)

	def test_password_reset_request_page_loads(self):
		response = self.client.get(reverse('webwi:password_reset'))
		self.assertEqual(response.status_code, 200)

	def test_password_reset_done_page_loads(self):
		response = self.client.get(reverse('webwi:password_reset_done'))
		self.assertEqual(response.status_code, 200)

	def test_password_reset_request_with_known_email_redirects_to_done(self):
		response = self.client.post(
			reverse('webwi:password_reset'),
			{'email': 'reset@example.com'},
		)
		self.assertRedirects(
			response,
			reverse('webwi:password_reset_done'),
			fetch_redirect_response=False,
		)

	def test_password_reset_request_with_unknown_email_also_redirects_to_done(self):
		"""Unknown email must produce the same redirect as a known one to prevent user enumeration."""
		response = self.client.post(
			reverse('webwi:password_reset'),
			{'email': 'nobody@example.com'},
		)
		self.assertRedirects(
			response,
			reverse('webwi:password_reset_done'),
			fetch_redirect_response=False,
		)

	def test_password_reset_sends_email_for_known_address(self):
		from django.core import mail
		self.client.post(reverse('webwi:password_reset'), {'email': 'reset@example.com'})
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('reset@example.com', mail.outbox[0].to)

	def test_password_reset_does_not_send_email_for_unknown_address(self):
		"""No email must be sent for an address that has no account (silent non-disclosure)."""
		from django.core import mail
		self.client.post(reverse('webwi:password_reset'), {'email': 'nobody@example.com'})
		self.assertEqual(len(mail.outbox), 0)

	def test_password_reset_confirm_with_valid_token_renders_form(self):
		from django.contrib.auth.tokens import default_token_generator
		from django.utils.encoding import force_bytes
		from django.utils.http import urlsafe_base64_encode

		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)
		url = reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
		response = self.client.get(url, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['validlink'])

	def test_password_reset_confirm_with_invalid_token_shows_invalid_link(self):
		from django.utils.encoding import force_bytes
		from django.utils.http import urlsafe_base64_encode

		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		url = reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': 'invalid-token'})
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.context['validlink'])

	def test_password_reset_complete_sets_new_password(self):
		from django.contrib.auth.tokens import default_token_generator
		from django.utils.encoding import force_bytes
		from django.utils.http import urlsafe_base64_encode

		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)

		# First GET stores the token in the session and redirects to the set-password URL
		confirm_url = reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
		self.client.get(confirm_url, follow=True)

		# POST the new password to the session-bound set-password URL
		set_url = reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': 'set-password'})
		response = self.client.post(
			set_url,
			{'new_password1': 'BrandNewSafePass123!', 'new_password2': 'BrandNewSafePass123!'},
			follow=True,
		)
		self.assertRedirects(response, reverse('webwi:password_reset_complete'))
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('BrandNewSafePass123!'))


class BruteForceProtectionTests(TestCase):
	"""Verify that the login view enforces account-level lockout.

	After MAX_FAILED_ATTEMPTS consecutive failures the account is locked
	for LOCKOUT_DURATION; legitimate users are unaffected across accounts.
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username='targetuser',
			email='target@example.com',
			password=self.password,
		)

	def _fail_login(self, username='targetuser', times=1):
		for _ in range(times):
			self.client.post(
				reverse('webwi:login'),
				{'username': username, 'password': 'wrongpassword'},
			)

	def test_normal_login_succeeds(self):
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'targetuser', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	def test_failed_logins_below_threshold_do_not_lock_account(self):
		self._fail_login(times=MAX_FAILED_ATTEMPTS - 1)
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'targetuser', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	def test_account_locked_after_max_failed_attempts(self):
		self._fail_login(times=MAX_FAILED_ATTEMPTS)
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'targetuser', 'password': self.password},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'locked')

	def test_locked_account_cannot_login_with_correct_password(self):
		self._fail_login(times=MAX_FAILED_ATTEMPTS)
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'targetuser', 'password': self.password},
		)
		self.assertNotEqual(response.status_code, 302)

	def test_attempt_counter_resets_on_successful_login(self):
		self._fail_login(times=MAX_FAILED_ATTEMPTS - 1)
		self.client.post(
			reverse('webwi:login'),
			{'username': 'targetuser', 'password': self.password},
		)
		self.assertEqual(LoginAttempt.objects.filter(username='targetuser').count(), 0)

	def test_lockout_does_not_affect_other_accounts(self):
		User.objects.create_user(
			username='innocent',
			email='innocent@example.com',
			password=self.password,
		)
		self._fail_login(username='targetuser', times=MAX_FAILED_ATTEMPTS)
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'innocent', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	def test_each_failed_attempt_is_recorded(self):
		self._fail_login(times=3)
		self.assertEqual(LoginAttempt.objects.filter(username='targetuser').count(), 3)


class CSRFProtectionTests(TestCase):
	"""Verify that the AJAX display-name endpoint enforces CSRF protection.

	The standard Django test client bypasses CSRF by default.  These tests
	use Client(enforce_csrf_checks=True) to exercise the real middleware path,
	confirming that:
	  - Requests without a valid token are rejected (403).
	  - Requests that include the correct X-CSRFToken header succeed.
	  - Unauthenticated requests are rejected regardless of CSRF state.
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username='csrfuser',
			email='csrf@example.com',
			password=self.password,
		)
		self.url = reverse('webwi:quick_display_name_update')

	def _csrf_client(self):
		"""Return a test client that enforces CSRF checks."""
		return Client(enforce_csrf_checks=True)

	def test_post_without_csrf_token_is_rejected(self):
		"""A state-changing request with no CSRF token must return 403."""
		csrf_client = self._csrf_client()
		csrf_client.login(username='csrfuser', password=self.password)
		response = csrf_client.post(
			self.url,
			data=json.dumps({'display_name': 'Hacker'}),
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 403)

	def test_post_with_valid_csrf_token_succeeds(self):
		"""A request that includes the correct X-CSRFToken header is accepted."""
		csrf_client = self._csrf_client()
		csrf_client.login(username='csrfuser', password=self.password)
		# Fetch any page to obtain the CSRF cookie
		csrf_client.get(reverse('webwi:dashboard'))
		csrftoken = csrf_client.cookies['csrftoken'].value
		response = csrf_client.post(
			self.url,
			data=json.dumps({'display_name': 'ValidName'}),
			content_type='application/json',
			HTTP_X_CSRFTOKEN=csrftoken,
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(json.loads(response.content)['display_name'], 'ValidName')

	def test_post_updates_only_the_authenticated_users_display_name(self):
		"""A successful update writes to request.user's profile, not anyone else's."""
		self.client.login(username='csrfuser', password=self.password)
		self.client.post(
			self.url,
			data=json.dumps({'display_name': 'MyName'}),
			content_type='application/json',
		)
		profile = Profile.objects.get(user=self.user)
		self.assertEqual(profile.display_name, 'MyName')

	def test_unauthenticated_request_is_rejected(self):
		"""Anonymous AJAX calls must not be served."""
		response = self.client.post(
			self.url,
			data=json.dumps({'display_name': 'Anon'}),
			content_type='application/json',
		)
		self.assertNotEqual(response.status_code, 200)


class OpenRedirectTests(TestCase):
	"""Verify that redirect targets in login and registration flows are validated.

	Covers both safe internal redirects (allowed) and unsafe external or
	protocol-relative redirects (rejected with fallback to the default URL).
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username='redirectuser',
			email='redirect@example.com',
			password=self.password,
		)

	# --- Login flow ---

	def test_login_with_safe_internal_next_follows_it(self):
		"""A relative internal next URL is allowed after successful login."""
		target = reverse('webwi:profile')
		response = self.client.post(
			reverse('webwi:login') + '?next=' + target,
			{'username': 'redirectuser', 'password': self.password},
		)
		self.assertRedirects(response, target, fetch_redirect_response=False)

	def test_login_with_external_next_falls_back_to_dashboard(self):
		"""An absolute external next URL must be rejected; user lands on dashboard."""
		response = self.client.post(
			reverse('webwi:login') + '?next=https://evil.com/',
			{'username': 'redirectuser', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	def test_login_with_protocol_relative_external_next_is_rejected(self):
		"""A protocol-relative URL pointing off-host must be rejected."""
		response = self.client.post(
			reverse('webwi:login') + '?next=//evil.com/steal',
			{'username': 'redirectuser', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	def test_login_with_no_next_redirects_to_dashboard(self):
		"""Login without a next parameter redirects to the default dashboard."""
		response = self.client.post(
			reverse('webwi:login'),
			{'username': 'redirectuser', 'password': self.password},
		)
		self.assertRedirects(response, reverse('webwi:dashboard'), fetch_redirect_response=False)

	# --- Registration flow ---

	def test_registration_with_safe_internal_next_follows_it(self):
		"""A safe next URL is honoured after successful registration."""
		target = reverse('webwi:login')
		response = self.client.post(
			reverse('webwi:register') + '?next=' + target,
			{
				'username': 'newuser1',
				'email': 'new1@example.com',
				'password1': 'TestPass999!',
				'password2': 'TestPass999!',
			},
		)
		self.assertRedirects(response, target, fetch_redirect_response=False)

	def test_registration_with_external_next_falls_back_to_login(self):
		"""An external next URL after registration must be rejected."""
		response = self.client.post(
			reverse('webwi:register') + '?next=https://evil.com/',
			{
				'username': 'newuser2',
				'email': 'new2@example.com',
				'password1': 'TestPass999!',
				'password2': 'TestPass999!',
			},
		)
		self.assertRedirects(response, reverse('webwi:login'), fetch_redirect_response=False)


class AuditLoggingTests(TestCase):
	"""Verify that security-relevant events are written to the audit log.

	Uses assertLogs('webwi.audit') to intercept log records without
	requiring a real file or SIEM.  Each test also checks that sensitive
	data (passwords, email addresses for reset requests) never appear.
	"""

	def setUp(self):
		self.password = 'SafePass123!'
		self.user = User.objects.create_user(
			username='audituser',
			email='audit@example.com',
			password=self.password,
		)

	def test_registration_is_logged(self):
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(
				reverse('webwi:register'),
				{
					'username': 'newaudituser',
					'email': 'newaudit@example.com',
					'password1': 'TestPass999!',
					'password2': 'TestPass999!',
				},
			)
		combined = ' '.join(cm.output)
		self.assertIn('user_registered', combined)
		self.assertIn('newaudituser', combined)

	def test_login_success_is_logged(self):
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(
				reverse('webwi:login'),
				{'username': 'audituser', 'password': self.password},
			)
		combined = ' '.join(cm.output)
		self.assertIn('login_success', combined)
		self.assertIn('audituser', combined)

	def test_login_failure_is_logged(self):
		with self.assertLogs('webwi.audit', level='WARNING') as cm:
			self.client.post(
				reverse('webwi:login'),
				{'username': 'audituser', 'password': 'wrongpassword'},
			)
		combined = ' '.join(cm.output)
		self.assertIn('login_failure', combined)
		self.assertIn('audituser', combined)

	def test_logout_is_logged(self):
		self.client.login(username='audituser', password=self.password)
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(reverse('webwi:logout'))
		combined = ' '.join(cm.output)
		self.assertIn('logout', combined)
		self.assertIn('audituser', combined)

	def test_password_change_is_logged(self):
		self.client.login(username='audituser', password=self.password)
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(
				reverse('webwi:password_change'),
				{
					'old_password': self.password,
					'new_password1': 'NewSafePass123!',
					'new_password2': 'NewSafePass123!',
				},
			)
		combined = ' '.join(cm.output)
		self.assertIn('password_changed', combined)
		self.assertIn('audituser', combined)

	def test_password_reset_request_is_logged_without_email(self):
		"""Reset request event must be logged but the submitted email must NOT appear."""
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(reverse('webwi:password_reset'), {'email': 'audit@example.com'})
		combined = ' '.join(cm.output)
		self.assertIn('password_reset_requested', combined)
		self.assertNotIn('audit@example.com', combined)

	def test_password_reset_complete_is_logged(self):
		from django.contrib.auth.tokens import default_token_generator
		from django.utils.encoding import force_bytes
		from django.utils.http import urlsafe_base64_encode

		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)
		self.client.get(
			reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),
			follow=True,
		)
		set_url = reverse('webwi:password_reset_confirm', kwargs={'uidb64': uid, 'token': 'set-password'})
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.client.post(
				set_url,
				{'new_password1': 'BrandNewSafe999!', 'new_password2': 'BrandNewSafe999!'},
			)
		self.assertIn('password_reset_complete', ' '.join(cm.output))

	def test_raw_password_never_appears_in_audit_log(self):
		"""The plaintext password must be absent from every audit log entry."""
		with self.assertLogs('webwi.audit', level='DEBUG') as cm:
			self.client.post(
				reverse('webwi:login'),
				{'username': 'audituser', 'password': self.password},
			)
		self.assertNotIn(self.password, ' '.join(cm.output))

	def test_permission_grant_is_logged(self):
		permission = Permission.objects.get(codename='view_user_directory')
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.user.user_permissions.add(permission)
		combined = ' '.join(cm.output)
		self.assertIn('permission_granted', combined)
		self.assertIn('audituser', combined)

	def test_permission_revoke_is_logged(self):
		permission = Permission.objects.get(codename='view_user_directory')
		self.user.user_permissions.add(permission)
		with self.assertLogs('webwi.audit', level='INFO') as cm:
			self.user.user_permissions.remove(permission)
		combined = ' '.join(cm.output)
		self.assertIn('permission_revoked', combined)
		self.assertIn('audituser', combined)
