from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from .models import UserProfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

class UASAuthTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        
        self.user_a = User.objects.create_user(username='testuser_a', password='testpassword', email='usera@example.com')
        self.user_b = User.objects.create_user(username='testuser_b', password='testpassword', email='userb@example.com')
        self.instructor = User.objects.create_user(username='instructor', password='testpassword')
        
        UserProfile.objects.get_or_create(user=self.user_a)
        UserProfile.objects.get_or_create(user=self.user_b)
        UserProfile.objects.get_or_create(user=self.instructor)

        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.protected_url = reverse('protected_view')
        self.dashboard_url = reverse('instructor_dashboard')

    def test_login_success(self):
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'testpassword'})
        self.assertRedirects(response, reverse('profile'))

    def test_login_failure(self):
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    def test_protected_view_redirects_unauthenticated(self):
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 302)

    def test_protected_view_allows_authenticated(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_forbids_standard_user(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allows_instructor(self):
        perm = Permission.objects.get(codename='can_view_dashboard')
        self.instructor.user_permissions.add(perm)
        self.client.login(username='instructor', password='testpassword')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, self.login_url)

    # ----------------------------------------
    # IDOR TESTS
    # ----------------------------------------
    def test_idor_prevented_forbidden_access(self):
        self.client.login(username='testuser_a', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_b.id])
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 403)
        
    def test_idor_allowed_self_access(self):
        self.client.login(username='testuser_a', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_a.id])
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)

    def test_idor_override_instructor_access(self):
        perm = Permission.objects.get(codename='can_view_dashboard')
        self.instructor.user_permissions.add(perm)
        self.client.login(username='instructor', password='testpassword')
        update_url = reverse('update_profile', args=[self.user_b.id])
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)

    # ----------------------------------------
    # PASSWORD RESET ENUMERATION TESTS
    # ----------------------------------------
    def test_password_reset_valid_address(self):
        reset_url = reverse('password_reset')
        response = self.client.post(reset_url, {'email': 'usera@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))

    def test_password_reset_invalid_address_anti_enumeration(self):
        reset_url = reverse('password_reset')
        response = self.client.post(reset_url, {'email': 'doesnotexist@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))

    # ----------------------------------------
    # LOGIN BRUTE-FORCE PROTECTION TESTS
    # ----------------------------------------
    def test_brute_force_lockout(self):
        """Test that exactly 5 failed logins triggers a 429 restriction"""
        for i in range(5):
            response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
            self.assertEqual(response.status_code, 200) 
            
        # 6th attempt should hit the 429 natively
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 429)

    def test_brute_force_lockout_clears_on_success(self):
        """Test that successfully logging in resets the cache counter preventing lockout"""
        for i in range(4):
            self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
            
        # 5th attempt success
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'testpassword'})
        self.assertRedirects(response, reverse('profile'))
        
        # Logout
        self.client.post(self.logout_url)
        
        # Follow up failure does not trigger 429
        response = self.client.post(self.login_url, {'username': 'testuser_a', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    # ----------------------------------------
    # CSRF (AJAX LOGIC) PREVENTION TESTS
    # ----------------------------------------
    def test_ajax_csrf_block_missing_token(self):
        """Test malicious connection attempts explicitly missing the tokens catch 403 natively"""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser_a', password='testpassword')
        
        response = csrf_client.post(reverse('ping_status'))
        self.assertEqual(response.status_code, 403)

    def test_ajax_csrf_passes_with_token(self):
        """Test legitimate mapped UI workflow logic inherently passes via native Django processing"""
        from django.middleware.csrf import get_token
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser_a', password='testpassword')
        
        # Grab simulated organic token natively
        request = csrf_client.get(reverse('profile')).wsgi_request
        token = get_token(request)
        
        response = csrf_client.post(
            reverse('ping_status'),
            HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

    # ----------------------------------------
    # OPEN REDIRECT PREVENTION TESTS
    # ----------------------------------------
    def test_login_open_redirect_blocked(self):
        """Test malicious external URLs passed to login are securely dropped!"""
        response = self.client.post(self.login_url, {
            'username': 'testuser_a',
            'password': 'testpassword',
            'next': 'http://evil.com/phishing/'
        })
        # If open redirect was allowed, it would redirect to http://evil.com
        # Since it natively overrides with url_has_allowed_host_and_scheme, it defaults recursively
        self.assertRedirects(response, reverse('profile'))

    def test_login_internal_redirect_allowed(self):
        """Test legitimate internal URI trajectories resolve organically seamlessly"""
        response = self.client.post(self.login_url, {
            'username': 'testuser_a',
            'password': 'testpassword',
            'next': '/alpha/protected/'
        })
        self.assertRedirects(response, '/alpha/protected/')

    # ----------------------------------------
    # AUDIT OBSERVABILITY TESTS
    # ----------------------------------------
    def test_audit_logs_login_success(self):
        with self.assertLogs('security.audit', level='INFO') as cm:
            self.client.post(self.login_url, {
                'username': 'testuser_a',
                'password': 'testpassword'
            })
        self.assertTrue(any("AUDIT_EVENT: [LOGIN_SUCCESS]" in log for log in cm.output))
        self.assertTrue(any("testuser_a" in log for log in cm.output))

    def test_audit_logs_login_failed(self):
        with self.assertLogs('security.audit', level='WARNING') as cm:
            self.client.post(self.login_url, {
                'username': 'testuser_a',
                'password': 'wrongpassword'
            })
        self.assertTrue(any("AUDIT_EVENT: [LOGIN_FAILED]" in log for log in cm.output))
        self.assertTrue(any("testuser_a" in log for log in cm.output))
        self.assertFalse(any("wrongpassword" in log for log in cm.output))  # Verifies credentials dropped

    def test_audit_logs_logout(self):
        self.client.login(username='testuser_a', password='testpassword')
        with self.assertLogs('security.audit', level='INFO') as cm:
            self.client.post(reverse('logout'))
        self.assertTrue(any("AUDIT_EVENT: [LOGOUT]" in log for log in cm.output))
        self.assertTrue(any("testuser_a" in log for log in cm.output))

    # ----------------------------------------
    # STORED XSS PREVENTION TESTS
    # ----------------------------------------
    def test_stored_xss_mitigated_on_bio(self):
        """Test malicious Javascript arrays submitted natively into bios extract safely escaped organically."""
        self.user_a.userprofile.bio = "<script>alert('xss_test_payload')</script>"
        self.user_a.userprofile.save()
        self.client.login(username='testuser_a', password='testpassword')
        response = self.client.get(reverse('profile'))
        
        # Verify specific dangerous string outputs are escaped correctly natively bounding operations
        self.assertNotContains(response, "<script>alert('xss_test_payload')</script>")
        self.assertContains(response, "&lt;script&gt;alert(&#x27;xss_test_payload&#x27;)&lt;/script&gt;")

    # ----------------------------------------
    # SECURE UPLOAD TESTS
    # ----------------------------------------
    def test_upload_valid_png_file(self):
        """Test magic byte validations flawlessly resolve correctly formulated PNG arrays."""
        self.client.login(username='testuser_a', password='testpassword')
        valid_png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\x01\x02\x03\x04\x05'
        file_obj = SimpleUploadedFile("avatar.png", valid_png_content, content_type="image/png")
        
        response = self.client.post(reverse('update_profile', args=[self.user_a.id]), {
            'bio': 'testing avatar',
            'avatar': file_obj
        })
        self.assertRedirects(response, reverse('profile'))
        self.user_a.userprofile.refresh_from_db()
        self.assertTrue(self.user_a.userprofile.avatar)

    def test_upload_invalid_script_spoofed(self):
        """Test python scripts generically masked with valid extensions explicitly crash mapping securely limits."""
        self.client.login(username='testuser_a', password='testpassword')
        hostile_content = b'import os; os.system("rm -rf /")'
        file_obj = SimpleUploadedFile("avatar.png", hostile_content, content_type="image/png")
        
        response = self.client.post(reverse('update_profile', args=[self.user_a.id]), {
            'bio': 'testing bad avatar',
            'avatar': file_obj
        })
        # Fails validation explicitly tracking boundary outputs
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'File type is not supported')
        
    def test_download_authorization_matrix(self):
        """Test only specific bound owners and instructors mathematically map download objects!"""
        # Upload dynamically
        self.client.login(username='testuser_a', password='testpassword')
        valid_pdf_content = b'%PDF-1.4\n1 0 obj'
        file_obj = SimpleUploadedFile("doc.pdf", valid_pdf_content, content_type="application/pdf")
        self.client.post(reverse('update_profile', args=[self.user_a.id]), {'document': file_obj})
        
        # Test download authorized implicitly
        response = self.client.get(reverse('download_document', args=[self.user_a.userprofile.id, 'document']))
        self.assertEqual(response.status_code, 200)
        
        # Test IDOR bounds preventing 'testuser_b' from touching 'testuser_a' docs!
        self.client.login(username='testuser_b', password='testpassword')
        response_b = self.client.get(reverse('download_document', args=[self.user_a.userprofile.id, 'document']))
        self.assertEqual(response_b.status_code, 403)

    # ----------------------------------------
    # INFRASTRUCTURE HARDEST ASSERTS
    # ----------------------------------------
    def test_production_security_settings(self):
        """Test cryptographic parameters physically render effectively mapping constraints natively!"""
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertTrue(settings.SECURE_HSTS_PRELOAD)
        self.assertTrue(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)
