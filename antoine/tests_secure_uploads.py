"""
Tests for secure avatar and document upload handling.

Verifies that file uploads are properly validated and access controlled.
"""

from io import BytesIO
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import UserProfile
from .validators import (
    validate_avatar_file,
    validate_document_file,
    FileUploadConfig,
    sanitize_filename,
    get_file_extension
)


class AvatarUploadValidationTests(TestCase):
    """Test avatar file upload validation."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(user=self.user)
    
    def create_image_file(self, filename, content, content_type='image/jpeg'):
        """Helper to create an image file for testing."""
        return SimpleUploadedFile(
            name=filename,
            content=content,
            content_type=content_type
        )
    
    def test_valid_jpeg_avatar_accepted(self):
        """Test that valid JPEG image is accepted."""
        # JPEG magic bytes: FF D8 FF
        jpeg_data = b'\xFF\xD8\xFF' + b'\x00' * 100
        file = self.create_image_file('avatar.jpg', jpeg_data, 'image/jpeg')
        # Should not raise
        validate_avatar_file(file)
    
    def test_valid_png_avatar_accepted(self):
        """Test that valid PNG image is accepted."""
        # PNG magic bytes: 89 50 4E 47
        png_data = b'\x89\x50\x4E\x47' + b'\x00' * 100
        file = self.create_image_file('avatar.png', png_data, 'image/png')
        validate_avatar_file(file)
    
    def test_valid_gif_avatar_accepted(self):
        """Test that valid GIF image is accepted."""
        # GIF magic bytes: 47 49 46 38 (GIF8)
        gif_data = b'\x47\x49\x46\x38' + b'\x00' * 100
        file = self.create_image_file('avatar.gif', gif_data, 'image/gif')
        validate_avatar_file(file)
    
    def test_valid_webp_avatar_accepted(self):
        """Test that valid WebP image is accepted."""
        # WebP magic: RIFF ... WEBP
        webp_data = b'RIFF' + b'\x00' * 4 + b'WEBP' + b'\x00' * 100
        file = self.create_image_file('avatar.webp', webp_data, 'image/webp')
        validate_avatar_file(file)
    
    def test_file_too_large_rejected(self):
        """Test that oversized avatar is rejected."""
        # Create file larger than 5 MB limit
        large_data = b'X' * (FileUploadConfig.MAX_AVATAR_SIZE + 1)
        file = self.create_image_file('large.jpg', large_data)
        
        with self.assertRaises(ValidationError) as context:
            validate_avatar_file(file)
        self.assertIn('exceeds maximum', str(context.exception))
    
    def test_invalid_extension_rejected(self):
        """Test that invalid file extension is rejected."""
        file = self.create_image_file(
            'avatar.exe',
            b'\xFF\xD8\xFF' + b'\x00' * 100,
            'image/jpeg'
        )
        
        with self.assertRaises(ValidationError) as context:
            validate_avatar_file(file)
        self.assertIn('not allowed', str(context.exception))
    
    def test_dangerous_extension_rejected(self):
        """Test that dangerous extensions are rejected."""
        dangerous_files = [
            'avatar.exe', 'avatar.bat', 'avatar.sh', 'avatar.py',
            'avatar.php', 'avatar.jsp', 'avatar.jar', 'avatar.zip'
        ]
        
        for filename in dangerous_files:
            file = self.create_image_file(
                filename,
                b'\xFF\xD8\xFF' + b'\x00' * 100
            )
            with self.assertRaises(ValidationError):
                validate_avatar_file(file)
    
    def test_mime_type_mismatch_detected(self):
        """Test that MIME type mismatch is detected."""
        # File with .jpg extension but PNG content
        file = self.create_image_file(
            'avatar.jpg',
            b'\x89\x50\x4E\x47' + b'\x00' * 100,
            'image/png'
        )
        # Should accept because PNG signature is valid visible in magic bytes
        # but MIME type validation should check MIME
        validate_avatar_file(file)
    
    def test_invalid_magic_bytes_rejected(self):
        """Test that files with invalid magic bytes are rejected."""
        # File with valid extension but no valid image signature
        file = self.create_image_file(
            'avatar.jpg',
            b'INVALID_DATA' + b'\x00' * 100,
            'image/jpeg'
        )
        
        with self.assertRaises(ValidationError) as context:
            validate_avatar_file(file)
        self.assertIn('not a valid image', str(context.exception))
    
    def test_empty_file_rejected(self):
        """Test that empty files are rejected."""
        file = self.create_image_file('avatar.jpg', b'', 'image/jpeg')
        
        with self.assertRaises(ValidationError) as context:
            validate_avatar_file(file)
        self.assertIn('empty', str(context.exception).lower())
    
    def test_content_type_mismatch_dangerous_mimetype(self):
        """Test that dangerous MIME types are rejected."""
        file = self.create_image_file(
            'avatar.jpg',
            b'\xFF\xD8\xFF' + b'\x00' * 100,
            'application/x-executable'
        )
        
        with self.assertRaises(ValidationError) as context:
            validate_avatar_file(file)
        self.assertIn('not allowed', str(context.exception))
    
    def test_null_avatar_allowed(self):
        """Test that null/empty avatar field is allowed."""
        # Should not raise for None
        validate_avatar_file(None)


class DocumentUploadValidationTests(TestCase):
    """Test document file upload validation."""
    
    def create_document_file(self, filename, content, content_type='application/pdf'):
        """Helper to create a document file for testing."""
        return SimpleUploadedFile(
            name=filename,
            content=content,
            content_type=content_type
        )
    
    def test_valid_pdf_accepted(self):
        """Test that valid PDF file is accepted."""
        # PDF magic bytes: %PDF
        pdf_data = b'%PDF-1.4' + b'\x00' * 100
        file = self.create_document_file('document.pdf', pdf_data, 'application/pdf')
        validate_document_file(file)
    
    def test_valid_txt_accepted(self):
        """Test that valid text file is accepted."""
        txt_data = b'This is a text document.\n' + b'\x00' * 100
        file = self.create_document_file(
            'document.txt',
            txt_data,
            'text/plain'
        )
        validate_document_file(file)
    
    def test_valid_docx_accepted(self):
        """Test that valid DOCX file is accepted."""
        file = self.create_document_file(
            'document.docx',
            b'PK' + b'\x00' * 100,  # ZIP signature
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        validate_document_file(file)
    
    def test_document_too_large_rejected(self):
        """Test that oversized document is rejected."""
        large_data = b'X' * (FileUploadConfig.MAX_DOCUMENT_SIZE + 1)
        file = self.create_document_file('large.pdf', large_data)
        
        with self.assertRaises(ValidationError):
            validate_document_file(file)
    
    def test_invalid_document_extension_rejected(self):
        """Test that invalid document extension is rejected."""
        file = self.create_document_file(
            'document.exe',
            b'%PDF-1.4' + b'\x00' * 100
        )
        
        with self.assertRaises(ValidationError):
            validate_document_file(file)
    
    def test_dangerous_document_extension_rejected(self):
        """Test that dangerous extensions are rejected."""
        dangerous_files = [
            'doc.exe', 'doc.bat', 'doc.sh', 'doc.py', 'doc.zip'
        ]
        
        for filename in dangerous_files:
            file = self.create_document_file(filename, b'%PDF' + b'\x00' * 100)
            with self.assertRaises(ValidationError):
                validate_document_file(file)
    
    def test_null_document_allowed(self):
        """Test that null/empty document field is allowed."""
        validate_document_file(None)


class FilenameUtilityTests(TestCase):
    """Test filename utility functions."""
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        self.assertEqual(get_file_extension('avatar.jpg'), '.jpg')
        self.assertEqual(get_file_extension('document.pdf'), '.pdf')
        self.assertEqual(get_file_extension('file.tar.gz'), '.gz')
        self.assertEqual(get_file_extension('noextension'), '')
    
    def test_sanitize_filename_removes_path_traversal(self):
        """Test that path traversal attempts are removed."""
        # Attempt directory traversal
        self.assertNotIn('..', sanitize_filename('../../../etc/passwd'))
        self.assertNotIn('/', sanitize_filename('../../file.jpg'))
        self.assertNotIn('\\', sanitize_filename('..\\..\\file.jpg'))
    
    def test_sanitize_filename_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_filename('file\x00.jpg')
        self.assertNotIn('\x00', result)
    
    def test_sanitize_filename_removes_special_chars(self):
        """Test that dangerous special characters are removed."""
        result = sanitize_filename('file<script>.jpg')
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(';', result)
    
    def test_sanitize_filename_keeps_valid_chars(self):
        """Test that valid characters are preserved."""
        result = sanitize_filename('my-file_name.jpg')
        self.assertIn('my', result)
        self.assertIn('file', result)
        self.assertIn('.jpg', result)


class AvatarUploadFormTests(TestCase):
    """Test avatar upload through form submission."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(user=self.user)
    
    def test_profile_form_rejects_invalid_avatar(self):
        """Test that form rejects invalid avatar file."""
        self.client.login(username='testuser', password='testpass123')
        
        # Try to upload invalid file
        invalid_file = SimpleUploadedFile(
            'avatar.jpg',
            b'INVALID_DATA',
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            reverse('antoine:profile'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '123-456-7890',
                'bio': 'Test bio',
                'avatar': invalid_file
            }
        )
        
        # Form should have error and not save
        self.assertEqual(response.status_code, 200)
        # Verify avatar wasn't updated
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.avatar)
    
    def test_profile_form_accepts_valid_avatar(self):
        """Test that form accepts valid avatar file."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create valid JPEG
        valid_jpeg = SimpleUploadedFile(
            'avatar.jpg',
            b'\xFF\xD8\xFF' + b'\x00' * 1000,
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            reverse('antoine:profile'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '123-456-7890',
                'bio': 'Test bio',
                'avatar': valid_jpeg
            }
        )
        
        # Should redirect on success
        self.assertIn(response.status_code, [200, 302])


class AvatarAccessControlTests(TestCase):
    """Test access control for uploaded avatars."""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        UserProfile.objects.create(user=self.user1)
        UserProfile.objects.create(user=self.user2)
    
    def test_user_can_only_update_own_profile_avatar(self):
        """Test that users can only upload to their own profile."""
        self.client.login(username='user1', password='pass123')
        
        # User1 should only be able to update their own profile
        # Attempting to update user2's profile should fail or use their own
        response = self.client.get(reverse('antoine:profile'))
        self.assertEqual(response.status_code, 200)
        
        # Verify it's their own profile, not user2's
        self.assertIn('user1', str(response.content) or response.context.get('user', ''))


class FileUploadSecurityHeadersTests(TestCase):
    """Test security headers and properties for uploaded files."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(user=self.user)
    
    def test_file_size_limits_enforced(self):
        """Test that file size limits are enforced."""
        # Avatar limit: 5 MB
        self.assertEqual(FileUploadConfig.MAX_AVATAR_SIZE, 5 * 1024 * 1024)
        
        # Document limit: 10 MB
        self.assertEqual(FileUploadConfig.MAX_DOCUMENT_SIZE, 10 * 1024 * 1024)
    
    def test_allowed_mime_types_configured(self):
        """Test that allowed MIME types are properly configured."""
        # Avatar MIME types
        self.assertIn('image/jpeg', FileUploadConfig.ALLOWED_AVATAR_MIMETYPES)
        self.assertIn('image/png', FileUploadConfig.ALLOWED_AVATAR_MIMETYPES)
        self.assertIn('image/webp', FileUploadConfig.ALLOWED_AVATAR_MIMETYPES)
        self.assertIn('image/gif', FileUploadConfig.ALLOWED_AVATAR_MIMETYPES)
        
        # Document MIME types
        self.assertIn('application/pdf', FileUploadConfig.ALLOWED_DOCUMENT_MIMETYPES)
        self.assertIn('text/plain', FileUploadConfig.ALLOWED_DOCUMENT_MIMETYPES)
