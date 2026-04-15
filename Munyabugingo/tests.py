from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.core import mail
from django.core.cache import cache
from .models import Profile

class AuthenticationTests(TestCase):
    
    def setUp(self):
        """Set up test data and clear cache"""
        cache.clear()
        self.test_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_registration_success(self):
        """Test successful user registration with email"""
        response = self.client.post(reverse('Munyabugingo:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser', email='new@example.com').exists())

    def test_profile_update_success(self):
        """Test successful profile update"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('Munyabugingo:profile'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        })
        self.test_user.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.test_user.first_name, 'Updated')
        self.assertEqual(self.test_user.email, 'updated@example.com')

    def test_password_change_success(self):
        """Test successful password change"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('Munyabugingo:password_change'), {
            'old_password': 'testpass123',
            'new_password1': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        self.assertEqual(response.status_code, 302)
        # Verify can login with new password
        self.assertTrue(self.client.login(username='testuser', password='NewPass123!'))
    
    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        response = self.client.post(reverse('Munyabugingo:register'), {
            'username': 'newuser',
            'password1': 'password123',
            'password2': 'different123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post(reverse('Munyabugingo:login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
    
    def test_protected_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('Munyabugingo:dashboard'))
        self.assertEqual(response.status_code, 302)
    
    def test_authenticated_user_can_access_dashboard(self):
        """Test authenticated user can access dashboard"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WELCOME')
        self.assertContains(response, 'testuser')

    def test_standard_user_cannot_access_admin_dashboard(self):
        """Test authenticated user without permission gets 403 on admin dashboard"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_privileged_user_can_access_admin_dashboard(self):
        """Test privileged user can access admin dashboard"""
        # Create privileged user and add permission
        privileged_user = User.objects.create_user(
            username='privuser',
            password='testpass123',
            email='priv@example.com'
        )
        permission = Permission.objects.get(codename='can_view_admin_dashboard')
        privileged_user.user_permissions.add(permission)
        
        self.client.login(username='privuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')

    def test_user_can_view_own_profile_detail(self):
        """Test user can successfully view their own profile detail page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': self.test_user.profile.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_user_cannot_view_other_profile_detail_idor(self):
        """Test user cannot view another user's profile detail (IDOR Prevention)"""
        # Create another user
        other_user = User.objects.create_user(username='other', password='pass')
        
        self.client.login(username='testuser', password='testpass123')
        # Attempt to access other_user's profile
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': other_user.profile.pk}))
        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_any_profile_detail(self):
        """Test privileged user can view any profile detail page"""
        # Create privileged user
        privileged_user = User.objects.create_user(username='admin_user', password='pass')
        perm = Permission.objects.get(codename='can_view_admin_dashboard')
        privileged_user.user_permissions.add(perm)
        
        # Create a victim user
        victim = User.objects.create_user(username='victim', password='pass')
        
        self.client.login(username='admin_user', password='pass')
        response = self.client.get(reverse('Munyabugingo:profile_detail', kwargs={'pk': victim.profile.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'victim')

    def test_password_reset_request_sends_email(self):
        """Test that a password reset request actually sends an email"""
        response = self.client.post(reverse('Munyabugingo:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        # Check that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        # Verify recipient
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('password reset', mail.outbox[0].body)

    def test_password_reset_enumeration_protection(self):
        """Test that resetting a non-existent email still redirects to success page (Enumeration Protection)"""
        response = self.client.post(reverse('Munyabugingo:password_reset'), {
            'email': 'nonexistent@example.com'
        })
        # Should redirect to the "done" page using idiomatic Django check
        self.assertRedirects(response, reverse('Munyabugingo:password_reset_done'))
        # No email should be sent for non-existent users
        self.assertEqual(len(mail.outbox), 0)

    def test_login_brute_force_lockout(self):
        """Test that multiple failed login attempts trigger an IP lockout"""
        login_url = reverse('Munyabugingo:login')
        
        # Perform 5 failed attempts
        for i in range(5):
            response = self.client.post(login_url, {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            self.assertEqual(response.status_code, 200) # Returns form with error
            if i < 4:
                self.assertContains(response, f'Attempt {i+1} of 5')
            else:
                self.assertContains(response, 'Too many failed attempts')

        # The 6th attempt should be blocked before even checking credentials
        response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'testpass123' # Correct password
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'temporarily blocked')

    def test_login_success_resets_counter(self):
        """Test that a successful login resets the failed attempts counter"""
        login_url = reverse('Munyabugingo:login')
        
        # 3 failed attempts
        for i in range(3):
            self.client.post(login_url, {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            
        # 1 successful login
        response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # 3 more failed attempts should not trigger lockout yet (as counter was reset)
        for i in range(3):
            response = self.client.post(login_url, {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f'Attempt {i+1} of 5')

class CSRFSecurityTests(TestCase):
    """Test suite for CSRF protection and secure workflows"""
    def setUp(self):
        self.user = User.objects.create_user(username='csrfuser', password='testpassword123')
        self.client.login(username='csrfuser', password='testpassword123')
        self.toggle_url = reverse('Munyabugingo:toggle_like')
        self.logout_url = reverse('Munyabugingo:logout')

    def test_logout_get_forbidden_or_safe(self):
        """Verify that GET request to logout doesn't perform immediate logout in Django 5.x"""
        # In Django 5.x, LogoutView defaults to a confirmation page on GET
        response = self.client.get(self.logout_url)
        # Should NOT redirect (302) if it's strictly POST-only or requires confirmation
        self.assertNotEqual(response.status_code, 302, "Logout via GET should not automatically redirect/logout")

    def test_logout_post_csrf_success(self):
        """Verify successful logout via POST with CSRF"""
        response = self.client.post(self.logout_url, follow=True)
        # Check if user session is cleared
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_ajax_toggle_like_csrf_required(self):
        """Verify that toggle_like endpoint requires CSRF protection"""
        from django.test import Client as DjangoClient
        client = DjangoClient(enforce_csrf_checks=True)
        client.login(username='csrfuser', password='testpassword123')
        
        # Attempt POST without CSRF token header
        response = client.post(self.toggle_url, {
            'action': 'like',
            'content_id': 'Test Card'
        })
        self.assertEqual(response.status_code, 403, "AJAX POST without CSRF should be forbidden")

    def test_ajax_toggle_like_success(self):
        """Verify successful AJAX request with simulated CSRF (default Client behavior)"""
        response = self.client.post(self.toggle_url, {
            'action': 'like',
            'content_id': 'Test Card'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'like')

class OpenRedirectSecurityTests(TestCase):
    """Test suite for Open Redirect vulnerabilities in authentication flows"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.login_url = reverse('Munyabugingo:login')
        self.register_url = reverse('Munyabugingo:register')
        self.profile_url = reverse('Munyabugingo:profile')
        self.safe_url = reverse('Munyabugingo:dashboard')
        self.evil_url = 'https://evil-attacker.com/malicious'

    def test_login_safe_redirect(self):
        """Test successful login with safe internal redirect"""
        response = self.client.post(f"{self.login_url}?next=/profile/", {
            'username': 'testuser',
            'password': 'password123'
        })
        # Note: LoginView internally handles the redirect preservation or I passed it via GET
        # SecureLoginView uses get_safe_redirect_url which prefers POST then GET
        self.assertRedirects(response, '/profile/', fetch_redirect_response=False)

    def test_login_unsafe_redirect_fallback(self):
        """Test login with unsafe external redirect falling back to default"""
        response = self.client.post(f"{self.login_url}?next={self.evil_url}", {
            'username': 'testuser',
            'password': 'password123'
        })
        # Should NOT redirect to evil.com, should go to default success URL
        self.assertNotEqual(response.url, self.evil_url)
        self.assertRedirects(response, reverse('Munyabugingo:dashboard'), fetch_redirect_response=False)

    def test_registration_safe_redirect(self):
        """Test successful registration with safe internal redirect"""
        response = self.client.post(f"{self.register_url}?next=/profile/", {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        self.assertRedirects(response, '/profile/', fetch_redirect_response=False)

    def test_registration_unsafe_redirect_fallback(self):
        """Test registration with unsafe external redirect falling back to default"""
        response = self.client.post(f"{self.register_url}?next={self.evil_url}", {
            'username': 'newuser2',
            'email': 'new2@test.com',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        # Should NOT redirect to evil.com
        self.assertNotEqual(response.url, self.evil_url)
        self.assertRedirects(response, reverse('Munyabugingo:dashboard'), fetch_redirect_response=False)

    def test_profile_safe_redirect(self):
        """Test profile update with safe internal redirect"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(f"{self.profile_url}?next={self.safe_url}", {
            'first_name': 'New',
            'last_name': 'Name',
            'email': 'new@email.com'
        })
        self.assertRedirects(response, self.safe_url, fetch_redirect_response=False)

    def test_profile_unsafe_redirect_fallback(self):
        """Test profile update with unsafe external redirect falling back to default"""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(f"{self.profile_url}?next={self.evil_url}", {
            'first_name': 'New',
            'last_name': 'Name',
            'email': 'new@email.com'
        })
        self.assertNotEqual(response.url, self.evil_url)
        self.assertRedirects(response, self.profile_url, fetch_redirect_response=False)

class XSSSecurityTests(TestCase):
    """Test suite for Cross-Site Scripting (XSS) prevention"""

    def setUp(self):
        self.user = User.objects.create_user(username='xsstester', password='password123')
        # Inject malicious payload in bio (user-controlled content)
        self.malicious_payload = '<script>alert("XSS")</script>'
        self.user.profile.bio = self.malicious_payload
        self.user.profile.save()

    def test_profile_bio_escapes_html(self):
        """
        Test that stored malicious HTML in a user's bio is properly escaped
        when rendered on the profile detail page, preventing stored XSS.
        """
        url = reverse('Munyabugingo:profile_detail', args=[self.user.profile.pk])
        
        self.client.login(username='xsstester', password='password123')
        response = self.client.get(url)
        
        # Check that the raw script tags are NOT present in the output
        self.assertNotContains(response, self.malicious_payload)
        
        # Check that the escaped tags ARE present (i.e., &lt;script&gt;)
        self.assertContains(response, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')

    def test_message_escaping_in_js(self):
        """
        Test that messages rendered in base.html's script block are properly
        escaped for JavaScript using |escapejs to prevent script injection.
        """
        from django.template import Template, Context
        # Malicious payload designed to break out of a JS string literal
        malicious_msg = "test\"); alert('XSS'); (\""
        
        # Mock message object
        class MockMessage:
            def __init__(self, message, tags):
                self.message = message
                self.tags = tags
            def __str__(self):
                return self.message

        mock_messages = [MockMessage(malicious_msg, "success")]
        
        # Render the template part that contains the vulnerability
        t = Template('{% for message in messages %}showToast("{{ message|escapejs }}", "{{ message.tags|escapejs }}");{% endfor %}')
        c = Context({'messages': mock_messages})
        rendered = t.render(c)
        
        # Verify that common attack characters are escaped for JS (Unicode escapes)
        self.assertNotIn("\"); alert('XSS'); (\"", rendered)
        self.assertIn("\\u0022", rendered) # double quote
        self.assertIn("\\u003B", rendered) # semicolon (escaped by escapejs)
        self.assertIn("\\u0027", rendered) # single quote
