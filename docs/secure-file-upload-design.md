# Secure File Upload Handling - Design Document

## Executive Summary

This document outlines the security controls implemented for avatar and document file uploads in the devsec-demo learning platform. The implementation addresses OWASP security risks related to file uploads, including arbitrary file upload, MIME type spoofing, and unauthorized access to uploaded content.

## Security Objectives

1. **Prevent Arbitrary File Upload**: Block execution of dangerous file types (executables, scripts, etc.)
2. **Mitigate MIME Type Spoofing**: Validate actual file content, not just extension/content-type header
3. **Enforce Size Limits**: Prevent disk space exhaustion attacks
4. **Control Access**: Restrict download access to authorized users only
5. **Safe Storage**: Store uploads outside web root with secure naming

## Implementation Details

### 1. File Upload Validation Strategy

#### Avatar Upload Validation
- **Allowed Extensions**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` only
- **File Size Limit**: 5MB maximum
- **MIME Type Validation**: 
  - Check file magic bytes (binary signature) in addition to extension
  - Support for: JPEG, PNG, GIF, WebP signatures
  - Reject if extension doesn't match detected format

- **Magic Byte Validation**:
  ```
  JPEG: 0xFF 0xD8 0xFF
  PNG:  0x89 0x50 0x4E 0x47 (8950 4E47)
  GIF:  0x47 0x49 0x46 0x38 (GIF8)
  WebP: 0x52 0x49 0x46 0x46 + contain "WEBP"
  ```

#### Document Upload Validation
- **Allowed Extensions**: `.pdf`, `.doc`, `.docx`, `.txt`, `.pptx`, `.xlsx`
- **File Size Limit**: 10MB maximum
- **MIME Type Validation**:
  - PDF: `0x25 0x50 0x44 0x46` (%PDF)
  - Office 97-2003 (OLE): `0xD0 0xCF 0x11 0xE0`
  - Office Open XML: `0x50 0x4B 0x03 0x04` (PK..)
  - Plain text: UTF-8 decodable content

### 2. Attack Vectors Mitigated

#### Vector 1: Executable File Upload
**Attack**: User uploads executable (.exe, .sh, .bat, .ps1) disguised as image
**Mitigation**: 
- File extension whitelist enforces safe types
- Magic byte validation detects actual file type regardless of claimed extension
- Example: File named `malware.jpg` with PE header (0x4D 0x5A = "MZ") is rejected

#### Vector 2: Script Injection via Archives
**Attack**: User uploads ZIP containing executable, or disguised DOCX (which is ZIP)
**Mitigation**:
- Office Open XML files (.docx, .xlsx) are allowed (legitimate documents)
- ZIP archive extension not allowed directly
- All uploads stored outside web root and served through Django view with access control

#### Vector 3: MIME Type Spoofing
**Attack**: User renames `.exe` to `.jpg` with fake Content-Type header
**Mitigation**:
- Magic bytes validation in Django form (validate_avatar_file, validate_document_file)
- Both form field AND model field validators applied
- File content header inspection bypasses client-side metadata

#### Vector 4: Disk Space Exhaustion
**Attack**: User uploads many large files to exhaust storage
**Mitigation**:
- Per-file size limits (5MB avatar, 10MB document)
- No authentication bypass - all uploads require login
- Database records all uploads for quota enforcement (future enhancement)

#### Vector 5: Unauthorized Access
**Attack**: User directly accesses another user's uploaded files
**Mitigation**:
- Downloads routed through `download_document` view with access control
- Access check: request.user == document.user or request.user.is_staff
- Non-HTML file types served as attachment (not inline)

### 3. Implementation Components

#### Models Layer (`justin/models.py`)
```python
class Profile(models.Model):
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        validators=[validate_avatar_file],
    )

class Document(models.Model):
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[validate_document_file],
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
```

**Key Features**:
- Upload directories use date-based structure for organization
- Validators applied at model level for database integrity
- User foreign key ensures ownership tracking

#### Validators (`justin/models.py`)
```python
def validate_avatar_file(file):
    # 1. Check file size
    # 2. Check extension whitelist
    # 3. Check magic bytes
    
def validate_document_file(file):
    # 1. Check file size
    # 2. Check extension whitelist
    # 3. Check magic bytes
```

#### Forms Layer (`justin/forms.py`)
```python
class ProfileForm(forms.ModelForm):
    def clean_avatar(self):
        # Re-validate avatar (also done at model level)
        validate_avatar_file(avatar)
        
class DocumentUploadForm(forms.ModelForm):
    def clean_file(self):
        # Re-validate document file
        validate_document_file(file)
```

**Defense in Depth**: Validation happens at both form and model layers to ensure security even if one layer is bypassed.

#### Views Layer (`justin/views.py`)
```python
@login_required
def download_document(request, doc_id):
    # Access control check
    if not (is_owner or is_staff):
        return HttpResponseForbidden()
    
    # Serve file through Django (not direct web server access)
    return FileResponse(document.file.open('rb'))
```

**Key Security Features**:
- @login_required decorator enforces authentication
- Explicit access control check prevents unauthorized downloads
- FileResponse serves through Django (can log, audit, check permissions)
- Filename sanitization in response header

### 4. Storage Configuration

#### Upload Directory Structure
```
media/
  avatars/
    2025/04/17/          # Date-based organization
      user123_avatar.jpg
  documents/
    2025/04/17/
      research_paper.pdf
```

**Rationale**:
- Outside web root (MEDIA_ROOT, not STATIC_ROOT)
- Not directly accessible via web server
- Date-based subdirectories prevent unbounded directory sizes
- Filenames generated by Django, not user-supplied

#### Django Settings (in devsec_demo/settings.py)
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Optional: Disable directory listing
MEDIA_UPLOAD_PERMISSIONS = 0o644
```

### 5. Access Control Model

#### Avatar Access
- **View**: Any authenticated user can view their own avatar
- **Edit**: Only profile owner can upload/change avatar
- **Delete**: Only profile owner can delete

#### Document Access
- **Upload**: Only authenticated users can upload
- **View List**: Owner sees all their documents
- **Download**: 
  - **Owner**: Can always download
  - **Staff/Admin**: Can download any document (for moderation)
  - **Others**: Access denied
- **Delete**: Owner or admin only

### 6. Testing Strategy

#### Test Coverage
1. **Valid File Acceptance**
   - Test legitimate PNG, JPEG, PDF uploads
   - Verify files stored with correct content

2. **Invalid Type Rejection**
   - Test executable files (.exe, .sh, .bat)
   - Test non-whitelisted extensions
   - Test archive files

3. **MIME Type Spoofing**
   - Test .exe with PE header named as .jpg
   - Test mismatched magic bytes
   - Test fake content-type headers

4. **Size Limit Enforcement**
   - Test files at limit boundaries
   - Test oversized files rejection

5. **Access Control**
   - Test owner can download own documents
   - Test other users cannot download
   - Test staff can download any document
   - Test non-authenticated access denied

### 7. Security Assumptions & Limitations

#### Current Implementation Assumes:
- Django DEBUG=False in production
- Web server does NOT serve MEDIA_URL directly (uses X-Sendfile or equivalent)
- Database security maintained
- Operating system file permissions properly configured

#### Known Limitations:
- Magic byte validation is heuristic (determined by file signature)
- Office documents can contain macros (not scanned)
- Large file uploads can consume temporary disk space
- No file content scanning for malware

#### Recommended Enhancements:
1. Implement virus scanning (ClamAV integration)
2. Add document upload quotas per user
3. Audit log all file operations
4. Implement content security policy headers
5. Add rate limiting on uploads
6. Use CDN with restricted origin for downloads

### 8. AI Authorship Disclosure

This secure file upload implementation was developed with AI assistance (GitHub Copilot) to ensure:
- Comprehensive security control implementation
- Consistent validation across multiple layers
- Test coverage for common attack vectors
- Clear documentation of security rationale

The security design follows OWASP guidelines and Django best practices for file upload handling.

## References

- OWASP: Unrestricted File Upload
  https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
  
- Django: File Uploads
  https://docs.djangoproject.com/en/stable/ref/models/fields/#filefield
  
- Magic Numbers (File Signatures)
  https://en.wikipedia.org/wiki/List_of_file_signatures
  
- Django Security
  https://docs.djangoproject.com/en/stable/topics/security/
