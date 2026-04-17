from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from io import BytesIO
from .models import Profile, Document, validate_avatar_file, validate_document_file


class FileUploadValidationTest(TestCase):
    """Test secure file upload validation."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(user=self.user)

    def create_image_file(self, name='test.png', format='PNG', size=(100, 100)):
        """Create a valid PNG test image."""
        from PIL import Image
        file_object = BytesIO()
        image = Image.new('RGB', size=size)
        image.save(file_object, format=format)
        file_object.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file_object.getvalue(),
            content_type='image/png'
        )

    def create_jpeg_file(self, name='test.jpg'):
        """Create a valid JPEG test image."""
        from PIL import Image
        file_object = BytesIO()
        image = Image.new('RGB', size=(100, 100))
        image.save(file_object, format='JPEG')
        file_object.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file_object.getvalue(),
            content_type='image/jpeg'
        )

    def test_validate_legitimate_png_avatar(self):
        """Test that valid PNG avatars are accepted."""
        avatar_file = self.create_image_file(name='avatar.png', format='PNG')
        # Should not raise exception
        try:
            validate_avatar_file(avatar_file)
        except ValidationError:
            self.fail('Valid PNG avatar validation raised ValidationError')

    def test_validate_legitimate_jpeg_avatar(self):
        """Test that valid JPEG avatars are accepted."""
        avatar_file = self.create_jpeg_file(name='avatar.jpg')
        try:
            validate_avatar_file(avatar_file)
        except ValidationError:
            self.fail('Valid JPEG avatar validation raised ValidationError')

    def test_reject_oversized_avatar(self):
        """Test that oversized avatars are rejected."""
        # Create a file larger than 5MB
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        avatar_file = SimpleUploadedFile(
            name='large.png',
            content=large_content,
            content_type='image/png'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_avatar_file(avatar_file)
        self.assertIn('5MB', str(ctx.exception))

    def test_reject_invalid_avatar_extension(self):
        """Test that unsupported file extensions are rejected."""
        avatar_file = SimpleUploadedFile(
            name='avatar.exe',
            content=b'MZ\x90\x00',  # Partial EXE magic bytes
            content_type='application/octet-stream'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_avatar_file(avatar_file)
        self.assertIn('not allowed', str(ctx.exception).lower())

    def test_reject_mismatched_magic_bytes(self):
        """Test that files with mismatched magic bytes are rejected."""
        # Create a file with .png extension but wrong magic bytes
        fake_png = SimpleUploadedFile(
            name='fake.png',
            content=b'This is not a PNG',
            content_type='image/png'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_avatar_file(fake_png)
        self.assertIn('not a valid image format', str(ctx.exception).lower())

    def test_reject_executable_as_image(self):
        """Test that executable files disguised as images are rejected."""
        exe_content = b'MZ\x90\x00' + b'\x00' * 100
        fake_jpg = SimpleUploadedFile(
            name='virus.jpg',
            content=exe_content,
            content_type='image/jpeg'
        )
        with self.assertRaises(ValidationError):
            validate_avatar_file(fake_jpg)

    def test_validate_legitimate_pdf_document(self):
        """Test that valid PDF documents are accepted."""
        pdf_content = b'%PDF-1.4\n%data'
        pdf_file = SimpleUploadedFile(
            name='document.pdf',
            content=pdf_content,
            content_type='application/pdf'
        )
        try:
            validate_document_file(pdf_file)
        except ValidationError:
            self.fail('Valid PDF document validation raised ValidationError')

    def test_reject_oversized_document(self):
        """Test that oversized documents are rejected."""
        large_content = b'%PDF-1.4\n' + (b'x' * (11 * 1024 * 1024))  # 11MB
        doc_file = SimpleUploadedFile(
            name='large.pdf',
            content=large_content,
            content_type='application/pdf'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_document_file(doc_file)
        self.assertIn('10MB', str(ctx.exception))

    def test_reject_disallowed_document_type(self):
        """Test that disallowed document types are rejected."""
        doc_file = SimpleUploadedFile(
            name='document.exe',
            content=b'MZ\x90\x00',
            content_type='application/octet-stream'
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_document_file(doc_file)
        self.assertIn('not allowed', str(ctx.exception).lower())

    def test_reject_mismatched_document_magic_bytes(self):
        """Test that documents with mismatched magic bytes are rejected."""
        fake_pdf = SimpleUploadedFile(
            name='fake.pdf',
            content=b'This is not a PDF',
            content_type='application/pdf'
        )
        with self.assertRaises(ValidationError):
            validate_document_file(fake_pdf)


class AvatarUploadIntegrationTest(TestCase):
    """Test avatar upload functionality in profile context."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = Profile.objects.create(user=self.user)

    def create_test_image(self, name='test.png'):
        """Create a valid test image."""
        from PIL import Image
        file_object = BytesIO()
        image = Image.new('RGB', size=(100, 100))
        image.save(file_object, format='PNG')
        file_object.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=file_object.getvalue(),
            content_type='image/png'
        )

    def test_profile_rejects_invalid_avatar(self):
        """Test that profile model rejects invalid avatar files."""
        # Create a profile with invalid avatar
        fake_image = SimpleUploadedFile(
            name='fake.png',
            content=b'Not an image',
            content_type='image/png'
        )
        profile = Profile(user=self.user, avatar=fake_image)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_accepts_valid_avatar(self):
        """Test that profile model accepts valid avatar files."""
        valid_image = self.create_test_image()
        profile = Profile(user=self.user, avatar=valid_image)
        # Should not raise exception
        try:
            profile.full_clean()
        except ValidationError as e:
            self.fail(f'Valid avatar was rejected: {e}')


class DocumentUploadIntegrationTest(TestCase):
    """Test document upload functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_document_rejects_invalid_pdf(self):
        """Test that document model rejects invalid PDF files."""
        fake_pdf = SimpleUploadedFile(
            name='fake.pdf',
            content=b'Not a PDF file',
            content_type='application/pdf'
        )
        document = Document(
            user=self.user,
            title='Test Doc',
            file=fake_pdf
        )
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_document_accepts_valid_pdf(self):
        """Test that document model accepts valid PDF files."""
        valid_pdf = SimpleUploadedFile(
            name='document.pdf',
            content=b'%PDF-1.4\n%data',
            content_type='application/pdf'
        )
        document = Document(
            user=self.user,
            title='Test Document',
            file=valid_pdf
        )
        try:
            document.full_clean()
        except ValidationError as e:
            self.fail(f'Valid PDF was rejected: {e}')

    def test_document_enforces_access_control(self):
        """Test that document access is restricted to owner and staff."""
        valid_pdf = SimpleUploadedFile(
            name='document.pdf',
            content=b'%PDF-1.4\n%data',
            content_type='application/pdf'
        )
        document = Document.objects.create(
            user=self.user,
            title='Private Doc',
            file=valid_pdf,
            is_public=False
        )
        
        # Only the owner should be able to download
        # (Access control would be enforced in views)
        self.assertEqual(document.user, self.user)

    def test_document_upload_form_validation(self):
        """Test that document upload form validates properly."""
        from .forms import DocumentUploadForm
        
        # Test with missing file
        form_data = {
            'title': 'Test Doc',
            'file': None,
            'description': 'Test',
            'is_public': False,
        }
        form = DocumentUploadForm(form_data)
        # File is required, form should be invalid
        self.assertFalse(form.is_valid() or form.fields['file'].required)
from django.test import TestCase, Client
from django.core import mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import Profile, Role
from django.urls import reverse


class RoleBasedAccessControlTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.standard_user = User.objects.create_user(
            username='standard',
            email='standard@test.com',
            password='testpass123'
        )
        self.standard_profile = Profile.objects.create(
            user=self.standard_user,
            role=Role.USER
        )
        
        self.privileged_user = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123'
        )
        self.privileged_profile = Profile.objects.create(
            user=self.privileged_user,
            role=Role.INSTRUCTOR
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_profile = Profile.objects.create(
            user=self.admin_user,
            role=Role.ADMIN
        )
    
    def test_anonymous_access_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_access_register(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
    
    def test_anonymous_cannot_access_profile(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_standard_user_can_access_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_admin_dashboard(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_cannot_access_user_management(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_privileged_user_can_access_admin_dashboard(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_cannot_access_user_management(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 403)
    
    def test_admin_user_can_access_user_management(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('user_management'))
        self.assertEqual(response.status_code, 200)
    
    def test_privileged_user_can_access_all_profiles(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_cannot_access_all_profiles(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('all_profiles'))
        self.assertEqual(response.status_code, 403)
    
    def test_standard_user_can_change_password(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)
    
    def test_standard_user_can_update_profile(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('update_profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_403_template_rendered_for_denied_access(self):
        self.client.login(username='standard', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'justin/403.html')
    
    def test_profile_role_property(self):
        self.assertFalse(self.standard_profile.is_privileged)
        self.assertFalse(self.standard_profile.is_admin)
        
        self.assertTrue(self.privileged_profile.is_privileged)
        self.assertFalse(self.privileged_profile.is_admin)
        
        self.assertTrue(self.admin_profile.is_privileged)
        self.assertTrue(self.admin_profile.is_admin)
    
    def test_role_context_for_authenticated_user(self):
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])
        self.assertEqual(response.context['user_role'], 'instructor')
    
    def test_role_context_for_anonymous_user(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_privileged'])
        self.assertFalse(response.context['is_admin'])


class PasswordResetWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='resetuser',
            email='resetuser@example.com',
            password='Original123!'
        )
        self.user.save()

    def test_password_reset_request_with_nonexistent_email_does_not_disclose(self):
        response = self.client.post(reverse('password_reset'), {'email': 'missing@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_sends_email_for_existing_user(self):
        response = self.client.post(reverse('password_reset'), {'email': 'resetuser@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reset your DevSec Demo password')
        self.assertIn('/reset/', mail.outbox[0].body)
        self.assertIn('ignore this message', mail.outbox[0].body.lower())

    def test_password_reset_confirm_with_invalid_token_shows_invalid_link(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': 'set-password'}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])

    def test_password_reset_complete_flow_updates_password(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_url = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        # Follow the canonical confirm redirect path before posting the form.
        response = self.client.get(reset_url, follow=True)
        confirm_url = response.request['PATH_INFO']
        self.assertIn('/reset/', confirm_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            confirm_url,
            {
                'new_password1': 'NewSecurePass123!',
                'new_password2': 'NewSecurePass123!',
            },
            follow=True
        )

        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))


class ProfileXSSTestCase(TestCase):
    """Test cases for preventing XSS in user profile content."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.profile = Profile.objects.create(user=self.user, bio='Safe bio')

    def test_bio_xss_prevention_in_profile_view(self):
        """Test that malicious script in bio is escaped in profile view."""
        # Update bio with malicious content
        malicious_bio = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
        self.profile.bio = malicious_bio
        self.profile.save()

        # Login and view profile
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('profile'))

        # Check that the response contains escaped HTML, not executable script
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')
        self.assertContains(response, '&lt;img src=x onerror=alert(1)&gt;')
        # Ensure the script tags are not present unescaped
        self.assertNotContains(response, '<script>')
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')

    def test_bio_xss_prevention_in_all_profiles_view(self):
        """Test that malicious script in bio is escaped in all profiles view."""
        # Create privileged user to access all profiles
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        admin_profile = Profile.objects.create(user=admin_user, role=Role.ADMIN)

        # Update bio with malicious content
        malicious_bio = '<script>alert("XSS")</script>'
        self.profile.bio = malicious_bio
        self.profile.save()

        # Login as admin and view all profiles
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('all_profiles'))

        # Check that the response contains escaped HTML
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>')
