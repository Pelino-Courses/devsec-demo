# Secure Password Reset Flow: Design Notes and Security Decisions

## Overview

This pull request implements a **secure password reset workflow** using Django's built-in utilities. The implementation prioritizes security, user experience, and prevents common vulnerabilities in password reset flows.

## Security Principles Applied

### 1. **Cryptographically Secure Tokens**

**Instead of:**
- Simple sequential IDs (predictable)
- Weak random numbers
- Timestamps only

**We use:** Django's signed token generator with:
- Cryptographic HMAC-SHA256 signatures
- User PK + timestamp embedded in token
- Tamper detection (catches modified tokens)

```python
# Django generates tokens like: "a1b2c3d4-abcd1234..."
token = default_token_generator.make_token(user)
```

---

### 2. **User Enumeration Prevention**

**The IDOR/Enumeration Problem:**
A site that says "Email not found" reveals which emails are registered → attackers can harvest valid emails.

**Our Solution:**
```
Scenario 1: Valid email   → "Check your email" message
Scenario 2: Invalid email → "Check your email" message (identical)
```

Even though Django internally skips non-existent users, we never tell the requester what happened. This is called a **"no-op" response** for invalid emails.

**Django's Implementation:**
```python
# find_users filters by email but ONLY sends to active users
# No distinction in response between found/not-found
for user in User.objects.filter(email=email).filter(is_active=True):
    send_mail(...)  # Silent if none match
```

**Test Case:**
```python
# Both valid and invalid emails show same success page
def test_password_reset_with_valid_email(self):
    response1 = self.client.post(self.url, {"email": "test@example.com"})
    
def test_password_reset_with_nonexistent_email(self):
    response2 = self.client.post(self.url, {"email": "fake@example.com"})
    
# Both responses are identical
assert response1.status_code == response2.status_code
assert response1.template_name == response2.template_name
```

---

### 3. **Token Expiration**

**Why it matters:**
- If a reset link is leaked or the user's email is compromised, a long expiration window is dangerous
- Each hour the link exists is an opportunity for attackers

**Our Configuration:**
```python
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours (one day)
```

**Django's Token Validation:**
```python
# Tokens include a timestamp
# Validation fails if:
# - Token is tampered with (signature fails)
# - Token is expired (timestamp > timeout)
# - User is inactive
```

**Benefits:**
- Balances UX (24 hrs reasonable for most users) and security
- Default is 3 days; we reduced it for higher security
- Non-configurable per-user; everyone gets same window

---

### 4. **One-Time Use Tokens**

**The Problem:** Some systems allow reusing the same token multiple times.

**Django's Solution:** Tokens are based on:
- User's last_login timestamp
- Password hash
- When password is changed, **all old tokens become invalid** (hash changes)

**Security Flow:**
```
1. User requests reset → Token generated with password_hash_v1
2. User gets email link
3. User clicks link → New password set → password_hash becomes _v2
4. Old token trying to use hash_v1 → FAILS (hash mismatch)
```

**Test Case:**
```python
def test_token_is_one_time_use(self):
    # Use token once successfully
    self.client.post(confirm_url, new_password_data, follow=True)
    
    # Try to reuse same token
    # Django detects password changed, invalidates old token
    response = self.client.post(confirm_url, different_password_data)
    assert "Invalid or Expired Link" in response
```

---

### 5. **Password Validation**

**Weak Password Prevention:**

Django's built-in validators check:
- ✗ Too short (< 8 chars)
- ✗ Too common (matches common passwords list)
- ✗ Matches username or email
- ✓ No obviously personal info
- ✓ Mix of character types encouraged

**Implementation:**
```python
AUTH_PASSWORD_VALIDATORS = [
    'UserAttributeSimilarityValidator',  # No username/email match
    'MinimumLengthValidator',            # >= 8 chars
    'CommonPasswordValidator',           # Not in common list
    'NumericPasswordValidator',          # Not all numbers
]
```

**Test Cases:**
```python
def test_password_reset_with_weak_password(self):
    response = client.post(url, {"new_password1": "123"})
    assert "at least 8 characters" in response
    
def test_password_reset_with_password_same_as_username(self):
    response = client.post(url, {"new_password1": "testuser"})
    assert "too similar to username" in response
```

---

### 6. **Email-Only Reset Channel**

**Why Email?**
- ✓ Controlled by user (recovery method)
- ✓ Out-of-band (can't intercept from app)
- ✓ Auditable (we can log who sent it)

**NOT supported (intentionally):**
- ✗ SMS (costs money, unreliable)
- ✗ Security questions (too easy to guess)
- ✗ Instant web form (user might be at attacker's device)

---

## Attack Scenarios Prevented

| Attack | Django Protection | Our Code | Test |
|--------|------------------|----------|------|
| **Token Prediction** | Signed tokens with randomness | HMAC-SHA256 | N/A |
| **Token Reuse** | Invalidation on password change | Auto on `save()` | `test_token_is_one_time_use` |
| **User Enumeration** | No-op for nonexistent emails | Generic response | `test_nonexistent_email` |
| **Weak Password** | Builtin validators | All enabled | `test_weak_password` |
| **Expired Link** | Timestamp validation | 24-hour window | N/A (tested implicitly) |
| **Admin Override** | None needed | No backdoor codes | N/A |
| **Email Interception** | HTTPS only | App-level setting | Deployment concern |

---

## Email Security Notes

### Template Injection Prevention

```django
{% autoescape off %}
<!-- DO NOT escape token in email, always quote URLs correctly -->
{{ protocol }}://{{ domain }}{% url '...' uidb64=uid token=token %}
{% endautoescape %}
```

### Plaintext Email Risk

Our email includes the reset link in plain text (standard practice):
- Users expect this
- Reset is a time-sensitive action
- Email is already compromised if attacker has access

### SMTP Configuration (Production)

```python
# Development: Console backend (emails print to console)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production: Requires env vars
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
```

---

## Views Architecture

### 1. **SecurePasswordResetView** (GET/POST)
- **Route**: `/password-reset/`
- **Method**: Django's `PasswordResetView`
- **Flow**:
  1. User enters email
  2. Django finds user (silent if none)
  3. Generates token + URL
  4. Sends email (silently skips if user not found)
  5. Redirects to "done" page (always)

### 2. **SecurePasswordResetDoneView** (GET)
- **Route**: `/password-reset/done/`
- **Display**: Generic "check email" message
- **Purpose**: Confirm request was received (prevent user enumeration)

### 3. **SecurePasswordResetConfirmView** (GET/POST)
- **Route**: `/password-reset/<uidb64>/<token>/`
- **GET**: Show form if token valid, error if invalid
- **POST**: Validate password, set new password, redirect to complete
- **Validation**:
  - Token signature (tamper detection)
  - Token timestamp (not expired)
  - User is active
  - New passwords match
  - Password strength

### 4. **SecurePasswordResetCompleteView** (GET)
- **Route**: `/password-reset/complete/`
- **Display**: Success message + link to login
- **Purpose**: Confirm password was changed

---

## URL Patterns

```python
path("password-reset/", SecurePasswordResetView.as_view(), 
     name="password_reset"),
path("password-reset/done/", SecurePasswordResetDoneView.as_view(), 
     name="password_reset_done"),
path("password-reset/<uidb64>/<token>/", SecurePasswordResetConfirmView.as_view(), 
     name="password_reset_confirm"),
path("password-reset/complete/", SecurePasswordResetCompleteView.as_view(), 
     name="password_reset_complete"),
```

---

## Email Templates

### Subject Line
```
Password Reset Request for SecureAuth
```

### Email Body
```
You're receiving this email because you requested a password reset.

Click link below (valid 24 hours): [LINK]

If you didn't request this, ignore—password unchanged.

Security reminder:
- Don't share this link
- Don't forward this email
```

---

## Test Coverage

### Request Flow Tests (6 tests)
- ✓ Page loads for unauthenticated users
- ✓ Valid email request succeeds
- ✓ Invalid email request also succeeds (no enumeration)
- ✓ Invalid email format rejected
- ✓ Unauthenticated users can request
- ✓ Authenticated users can request

### Confirmation Flow Tests (9 tests)
- ✓ Page loads with valid token
- ✓ Invalid token shows error
- ✓ Valid password succeeds
- ✓ Weak password rejected
- ✓ Mismatched passwords rejected
- ✓ Password same as username rejected
- ✓ Token is one-time use
- ✓ Can login with new password
- ✓ Cannot login with old password

**Total: 15 comprehensive security tests**

---

## Why Django Built-Ins?

Instead of custom code:

| Aspect | Custom Code Risk | Django Built-In | Our Choice |
|--------|------------------|-----------------|-----------|
| Token Generation | Weak randomness | HMAC-SHA256 signed | ✓ Django |
| Token Validation | Bypassable logic | Cryptographic verification | ✓ Django |
| User Enumeration | Hard to prevent | Built-in no-op | ✓ Django |
| Password Validation | Weak rules | NIST-aligned validators | ✓ Django |
| Email Sending | SMTP bugs | Abstracted backend | ✓ Django |
| Time Window | Forgotten | Configurable timeout | ✓ Django |

---

## Backward Compatibility

✓ All existing views remain unchanged  
✓ New URLs don't conflict with existing routes  
✓ Existing tests continue to pass  
✓ No database migrations required  
✓ No breaking API changes  

---

## Future Enhancements

Possible improvements (not in scope):
- [ ] Two-factor authentication for recovery
- [ ] SMS backup reset channel
- [ ] Admin password reset endpoint
- [ ] Reset attempt rate limiting
- [ ] Audit logging of all resets
- [ ] IP address verification on reset confirm

---

## Security Checklist

✓ Uses Django's built-in secure token generation  
✓ Prevents user enumeration (same response for all inputs)  
✓ Implements token expiration (24 hours)  
✓ Enforces password strength validation  
✓ Prevents token reuse (invalidated on password change)  
✓ Validates password don't match username/email  
✓ Clear error messages without leaking account info  
✓ Email-only reset channel (secure out-of-band)  
✓ Comprehensive test coverage (15 tests)  
✓ Handles edge cases (nonexistent users, invalid tokens)  

---

**Author's Note:** This implementation demonstrates secure password reset design by leveraging Django's battle-tested utilities rather than reinventing the wheel. All design decisions prioritize security without sacrificing usability.
