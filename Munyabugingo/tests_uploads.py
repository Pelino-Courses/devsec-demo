from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Document
import os

class FileUploadSecurityTests(TestCase):
    """Test suite for secure file upload handling and access control"""

    def setUp(self):
        self.user_a = User.objects.create_user(username='usera', password='password123')
        self.user_b = User.objects.create_user(username='userb', password='password123')
        self.client_a = Client()
        self.client_b = Client()
        self.client_a.login(username='usera', password='password123')
        self.client_b.login(username='userb', password='password123')

    def test_upload_allowed_file(self):
        """Test that a valid PDF can be uploaded"""
        pdf_content = b'%PDF-1.4 test content'
        pdf_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        
        response = self.client_a.post(reverse('Munyabugingo:upload_document'), {
            'title': 'My Secret Report',
            'description': 'Description',
            'file': pdf_file
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Document.objects.filter(title='My Secret Report').exists())

    def test_upload_dangerous_file_rejection(self):
        """Test that dangerous file extensions are rejected"""
        dangerous_content = b'<?php phpinfo(); ?>'
        dangerous_file = SimpleUploadedFile("shell.php", dangerous_content, content_type="application/x-php")
        
        response = self.client_a.post(reverse('Munyabugingo:upload_document'), {
            'title': 'Hack attempt',
            'file': dangerous_file
        })
        
        # Should stay on page with errors
        self.assertEqual(response.status_code, 200)
        self.assertIn('Unsupported file extension. Allowed: .pdf, .txt, .doc, .docx', response.content.decode())

    def test_upload_large_file_rejection(self):
        """Test that files exceeding the 5MB limit are rejected"""
        # Create a "large" file (e.g., 6MB)
        large_content = b'0' * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile("large.pdf", large_content, content_type="application/pdf")
        
        response = self.client_a.post(reverse('Munyabugingo:upload_document'), {
            'title': 'Large File',
            'file': large_file
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('File size exceeds the limit of 5MB.', response.content.decode())

    def test_idor_document_download_prevention(self):
        """Test that User B cannot download User A's private document (IDOR check)"""
        # User A uploads a document
        pdf_content = b'secret content'
        pdf_file = SimpleUploadedFile("private.pdf", pdf_content, content_type="application/pdf")
        doc_a = Document.objects.create(user=self.user_a, title='Private Doc', file=pdf_file)
        
        # User B tries to download it
        download_url = reverse('Munyabugingo:download_document', args=[doc_a.pk])
        response = self.client_b.get(download_url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_admin_bypass_for_support(self):
        """Test that an admin user can download user documents (Legit override)"""
        # Create admin with permission
        admin_user = User.objects.create_superuser(username='admin', password='password123', email='admin@test.com')
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from .models import Profile
        
        ct = ContentType.objects.get_for_model(Profile)
        perm = Permission.objects.get(codename='can_view_admin_dashboard', content_type=ct)
        admin_user.user_permissions.add(perm)
        
        self.client.login(username='admin', password='password123')
        
        # User A's document
        pdf_file = SimpleUploadedFile("admin_check.pdf", b'content', content_type="application/pdf")
        doc_a = Document.objects.create(user=self.user_a, title='Admin Review', file=pdf_file)
        
        download_url = reverse('Munyabugingo:download_document', args=[doc_a.pk])
        response = self.client.get(download_url)
        
        # Should be allowed (200 OK or FileResponse)
        self.assertEqual(response.status_code, 200)
