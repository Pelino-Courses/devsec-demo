import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Profile


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.home_url = reverse('home')
        self.username = 'testuser'
        self.password = 'TestPass123!'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_home_page_status_code(self):
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/home.html')

    def test_registration_flow(self):
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!'
        })
        response = self.client.post(self.register_url, {
            'username': 'newuser2',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser2').exists())

    def test_login_flow(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_flow(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_profile_protected_access(self):
        profile_url = reverse('profile', kwargs={'username': self.username})
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/profile.html')

    def test_idor_prevention_on_profile_view(self):
        User.objects.create_user(username='hacker_user', password='TestPass123!')
        self.client.login(username=self.username, password=self.password)
        hacker_profile_url = reverse('profile', kwargs={'username': 'hacker_user'})
        response = self.client.get(hacker_profile_url)
        self.assertEqual(response.status_code, 404)

    def test_idor_prevention_on_profile_update(self):
        target_user = User.objects.create_user(username='target_user', password='TestPass123!')
        target_user.profile.bio = "Original Bio"
        target_user.profile.save()

        self.client.login(username=self.username, password=self.password)
        update_url = reverse('update_profile', kwargs={'username': 'target_user'})
        response = self.client.post(update_url, {'bio': 'Hacked Bio'})
        self.assertEqual(response.status_code, 404)

        target_user.refresh_from_db()
        self.assertEqual(target_user.profile.bio, "Original Bio")

    def test_instructor_dashboard_anonymous_access(self):
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_instructor_dashboard_standard_user_access(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_dashboard_privileged_user_access(self):
        privileged_user = User.objects.create_user(username='instructor1', password='TestPass123!')
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename='view_instructor_dashboard')
        privileged_user.user_permissions.add(perm)

        self.client.login(username='instructor1', password='TestPass123!')
        url = reverse('instructor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shema/instructor_dashboard.html')


class StoredXSSTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'victim'
        self.password = 'VictimPass123!'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.profile_url = reverse('profile', kwargs={'username': self.username})
        self.update_url = reverse('update_profile', kwargs={'username': self.username})

    def test_stored_xss_prevention_in_bio(self):
        malicious_bio = "<script>alert('XSS')</script><b>BoldProof</b>"
        self.client.login(username=self.username, password=self.password)

        update_response = self.client.post(self.update_url, {'bio': malicious_bio})
        self.assertEqual(update_response.status_code, 302)

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        self.assertContains(response, "&lt;b&gt;BoldProof&lt;/b&gt;")
        self.assertNotContains(response, "<b>BoldProof</b>")
        self.assertNotContains(response, "<script>alert")

    def test_bio_xss_payload_is_escaped_in_profile_view(self):
        self.user.profile.bio = '<script>alert("XSS")</script>'
        self.user.profile.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>alert("XSS")</script>', response.content.decode())
        self.assertIn('&lt;script&gt;', response.content.decode())

    def test_profile_auto_created_for_new_user(self):
        new_user = User.objects.create_user(username='newprofileuser', password='TestPass123!')
        self.assertTrue(Profile.objects.filter(user=new_user).exists())

    def test_admin_bio_preview_is_plain_text(self):
        self.user.profile.bio = '<script>alert("XSS")</script>'
        self.user.profile.save()
        profile = Profile.objects.get(user=self.user)
        from shema.admin import ProfileAdmin
        from django.contrib.admin.sites import AdminSite
        from django.utils.safestring import SafeData
        ma = ProfileAdmin(Profile, AdminSite())
        preview = ma.bio_preview(profile)
        self.assertNotIsInstance(preview, SafeData)


class FileUploadSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='uploader', password='TestPass123!')
        self.other = User.objects.create_user(username='attacker', password='TestPass123!')
        self.avatar_url = reverse('upload_avatar', kwargs={'username': 'uploader'})
        self.doc_url = reverse('upload_document', kwargs={'username': 'uploader'})
        self.profile_url = reverse('profile', kwargs={'username': 'uploader'})
        self.client.login(username='uploader', password='TestPass123!')

    # --- valid uploads ---

    def test_valid_png_avatar_accepted(self):
        png = SimpleUploadedFile(
            'avatar.png',
            b'\x89PNG\r\n\x1a\n' + b'\x00' * 20,
            content_type='image/png',
        )
        response = self.client.post(self.avatar_url, {'avatar': png})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar.name)

    def test_valid_pdf_document_accepted(self):
        pdf = SimpleUploadedFile(
            'doc.pdf',
            b'%PDF-1.4 test content',
            content_type='application/pdf',
        )
        response = self.client.post(self.doc_url, {'document': pdf})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.document.name)

    def test_valid_txt_document_accepted(self):
        txt = SimpleUploadedFile('notes.txt', b'hello world', content_type='text/plain')
        response = self.client.post(self.doc_url, {'document': txt})
        self.assertRedirects(response, self.profile_url)

    # --- dangerous types rejected ---

    def test_php_file_rejected_as_avatar(self):
        f = SimpleUploadedFile('shell.php', b'<?php system($_GET["cmd"]); ?>', content_type='application/x-php')
        response = self.client.post(self.avatar_url, {'avatar': f})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    def test_exe_file_rejected_as_document(self):
        f = SimpleUploadedFile('malware.exe', b'MZ\x90\x00malware', content_type='application/octet-stream')
        response = self.client.post(self.doc_url, {'document': f})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.document)

    def test_html_file_rejected_as_document(self):
        f = SimpleUploadedFile('page.html', b'<html><script>alert(1)</script></html>', content_type='text/html')
        response = self.client.post(self.doc_url, {'document': f})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.document)

    # --- magic bytes mismatch rejected ---

    def test_php_disguised_as_png_rejected(self):
        f = SimpleUploadedFile('evil.png', b'<?php system($_GET["cmd"]); ?>', content_type='image/png')
        response = self.client.post(self.avatar_url, {'avatar': f})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    def test_exe_disguised_as_pdf_rejected(self):
        f = SimpleUploadedFile('evil.pdf', b'MZ\x90\x00this is not a pdf', content_type='application/pdf')
        response = self.client.post(self.doc_url, {'document': f})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.document)

    # --- size limit enforced ---

    def test_oversized_avatar_rejected(self):
        big = SimpleUploadedFile('big.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * (3 * 1024 * 1024), content_type='image/png')
        response = self.client.post(self.avatar_url, {'avatar': big})
        self.assertRedirects(response, self.profile_url)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    # --- access control ---

    def test_attacker_cannot_upload_to_other_profile(self):
        self.client.logout()
        self.client.login(username='attacker', password='TestPass123!')
        png = SimpleUploadedFile('avatar.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 20, content_type='image/png')
        response = self.client.post(self.avatar_url, {'avatar': png})
        self.assertEqual(response.status_code, 404)

    def test_serve_view_rejects_other_user(self):
        png = SimpleUploadedFile('avatar.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 20, content_type='image/png')
        self.client.post(self.avatar_url, {'avatar': png})
        self.client.logout()
        self.client.login(username='attacker', password='TestPass123!')
        serve_url = reverse('serve_upload', kwargs={'username': 'uploader', 'filetype': 'avatar'})
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_view_allows_owner(self):
        png = SimpleUploadedFile('avatar.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 20, content_type='image/png')
        self.client.post(self.avatar_url, {'avatar': png})
        self.user.profile.refresh_from_db()
        serve_url = reverse('serve_upload', kwargs={'username': 'uploader', 'filetype': 'avatar'})
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_upload_redirects_to_login(self):
        self.client.logout()
        png = SimpleUploadedFile('avatar.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 20, content_type='image/png')
        response = self.client.post(self.avatar_url, {'avatar': png})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
