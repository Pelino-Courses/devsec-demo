from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import UserProfile
import io
import os
from PIL import Image

class FileUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        UserProfile.objects.get_or_create(user=self.user)
        self.client.login(username='testuser', password='password123')
        self.upload_url = reverse('upload_files')

    def create_dummy_image(self, name='test.png', size=(100, 100)):
        file = io.BytesIO()
        image = Image.new('RGBA', size=size, color=(155, 0, 0))
        image.save(file, 'png')
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type='image/png')

    def test_valid_image_accepted(self):
        """Verify that a legitimate PNG image is accepted and renamed."""
        avatar = self.create_dummy_image()
        response = self.client.post(self.upload_url, {'avatar': avatar})
        self.assertEqual(response.status_code, 302)
        
        self.user.userprofile.refresh_from_db()
        self.assertTrue(self.user.userprofile.avatar.name.startswith('avatars/'))
        # Check that it was renamed to a UUID-like string (8-4-4-4-12 pattern)
        filename = os.path.basename(self.user.userprofile.avatar.name)
        self.assertEqual(len(filename.split('.')[0]), 36) 

    def test_dangerous_file_type_rejected(self):
        """Verify that a PHP file disguised as a document is rejected."""
        document = SimpleUploadedFile("shell.php", b"<?php phpinfo(); ?>", content_type='application/x-php')
        response = self.client.post(self.upload_url, {'document': document})
        
        # Should stay on the same page (200) and show an error message
        self.assertEqual(response.status_code, 200)
        self.user.userprofile.refresh_from_db()
        self.assertFalse(self.user.userprofile.document)

    def test_large_file_rejected(self):
        """Verify that a file exceeding 5MB is rejected."""
        large_content = b"0" * (6 * 1024 * 1024) # 6MB
        document = SimpleUploadedFile("large.pdf", large_content, content_type='application/pdf')
        response = self.client.post(self.upload_url, {'document': document})
        
        self.assertEqual(response.status_code, 200)
        self.user.userprofile.refresh_from_db()
        self.assertFalse(self.user.userprofile.document)
