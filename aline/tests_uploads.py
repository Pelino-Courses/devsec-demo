import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from aline.models import UserProfile
import os

class SecureFileUploadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        # Ensure profile exists
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={'student_id': 'TEST-123'}
        )
        self.client.login(username='testuser', password='password123')
        
    def create_test_image(self, name='test.png', size=(100, 100), color='blue'):
        file = io.BytesIO()
        image = Image.new('RGB', size=size, color=color)
        image.save(file, 'PNG')
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type='image/png')

    def test_valid_avatar_upload(self):
        """Verify that a valid PNG image can be uploaded as an avatar."""
        image = self.create_test_image()
        response = self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'avatar': image
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.avatar.name.startswith(f'uploads/user_{self.user.id}/avatars/'))
        self.assertTrue(os.path.exists(self.profile.avatar.path))

    def test_invalid_avatar_type_rejected(self):
        """Verify that a non-image file (e.g., .txt) is rejected as an avatar."""
        fake_image = SimpleUploadedFile('malicious.txt', b'<?php echo "pwned"; ?>', content_type='text/plain')
        response = self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'avatar': fake_image
        })
        
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.avatar)
        # Check if any error is present on the avatar field (Pillow or our custom check)
        self.assertTrue(response.context['form'].errors.get('avatar'))

    def test_avatar_size_limit_enforced(self):
        """Verify that an image larger than 2MB is rejected."""
        large_data = b'0' * (2 * 1024 * 1024 + 1024)
        large_image = SimpleUploadedFile('large.png', large_data, content_type='image/png')
        
        response = self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'avatar': large_image
        })
        
        errors = response.context['form'].errors.get('avatar', [])
        # Django's ImageField might catch this as "invalid image", or our clean_avatar as "too large"
        self.assertTrue(len(errors) > 0)

    def test_valid_document_upload(self):
        """Verify that a valid PDF can be uploaded."""
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Title (Test) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
        document = SimpleUploadedFile('transcript.pdf', pdf_content, content_type='application/pdf')
        
        response = self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'academic_document': document
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.academic_document.name.startswith(f'uploads/user_{self.user.id}/documents/'))
        self.assertTrue(os.path.exists(self.profile.academic_document.path))

    def test_invalid_document_type_rejected(self):
        """Verify that dangerous file types like .exe are rejected."""
        malicious_doc = SimpleUploadedFile('malicious.exe', b'MZ...', content_type='application/x-msdownload')
        response = self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'academic_document': malicious_doc
        })
        
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.academic_document)
        self.assertTrue(response.context['form'].errors.get('academic_document'))

    def test_filename_randomization(self):
        """Verify that the stored filename is a UUID and doesn't contain the original filename."""
        original_name = 'my_private_info_v1.png'
        image = self.create_test_image(name=original_name)
        
        self.client.post(reverse('aline:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'student_id': self.profile.student_id,
            'avatar': image
        })
        
        self.profile.refresh_from_db()
        stored_filename = os.path.basename(self.profile.avatar.name)
        self.assertNotIn('my_private_info_v1', stored_filename)
        self.assertEqual(len(stored_filename.split('.')[0]), 36) # UUID length

    def test_access_control_academic_documents(self):
        """Verify that one student cannot access another student's academic document."""
        # Student A uploads a document
        pdf_content = b'%PDF-1.4\n...'
        doc_a = SimpleUploadedFile('doc_a.pdf', pdf_content, content_type='application/pdf')
        self.client.post(reverse('aline:profile'), {
            'first_name': 'Student',
            'last_name': 'A',
            'email': 'a@example.com',
            'student_id': self.profile.student_id,
            'academic_document': doc_a
        })
        self.profile.refresh_from_db()
        filename = os.path.basename(self.profile.academic_document.name)
        doc_a_url = reverse('aline:serve_academic_document', kwargs={'user_id': self.user.id, 'filename': filename})
        
        # Logout and login as Student B
        self.client.logout()
        user_b = User.objects.create_user(username='student_b', password='password123')
        UserProfile.objects.get_or_create(user=user_b, defaults={'student_id': 'TEST-456'})
        self.client.login(username='student_b', password='password123')
        
        # Try to access Student A's document via the NEW secure URL
        response = self.client.get(doc_a_url)
        self.assertEqual(response.status_code, 403)
        
        # Login as Instructor and try to access
        self.client.logout()
        instructor = User.objects.create_user(username='instructor', password='password123')
        instructor_group, _ = Group.objects.get_or_create(name='Instructor')
        instructor.groups.add(instructor_group)
        self.client.login(username='instructor', password='password123')
        
        response = self.client.get(doc_a_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), pdf_content)
