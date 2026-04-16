# Pull Request: Task #42 - Apply Production-Grade Django Security Settings

## Summary
This PR applies comprehensive production-grade security settings to the Django application, hardening the configuration to prevent common web vulnerabilities and enforce defense-in-depth security principles.

## Related Issue
Closes #42: Apply Production-Grade Django Security Settings

## Target Branch
`assignment/harden-django-security-settings`

## Changes Made

### 1. devsec_demo/settings.py
Enhanced Django configuration with production-safe defaults and comprehensive security headers.

**Key Changes:**

#### Environment-Based Configuration
- Added `_is_development_mode()` helper function to check `DJANGO_ENV` variable
  - Defaults to production mode if not set
  - Development mode when `DJANGO_ENV='development'` or `DJANGO_ENV='dev'`
- This approach allows safe configuration of all security settings without environment-specific files

#### SECRET_KEY Management
- **Before**: Used insecure default in development
- **After**: 
  - In development: Falls back to insecure default only if `DJANGO_ENV='development'`
  - In production: Requires `DJANGO_SECRET_KEY` environment variable
  - Raises `ValueError` if missing in production to prevent deployment with exposed key
- **Security Impact**: Prevents accidental exposure of Django secret key in production

#### DEBUG Setting
- **Before**: Had to manually change for production
- **After**: Automatically defaults to `False` for production safety
- Only enabled when `DJANGO_ENV='development'`
- **Security Impact**: Prevents information disclosure via debug pages and error messages

#### ALLOWED_HOSTS Configuration
- **Before**: Empty by default
- **After**: Still empty by default, but can be set via `DJANGO_ALLOWED_HOSTS` environment variable
- Requires explicit configuration in production to prevent Host header attacks
- **Security Impact**: Prevents Host header injection and cache poisoning attacks

#### HTTPS and Transport Security (Production Only)
```python
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 year HSTS expiration
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```
- **Security Impact**: 
  - Forces encrypted communication
  - Prevents downgrade attacks via HSTS
  - Enables HSTS preload for maximum protection

#### Cookie Security (Always Enabled)
```python
SESSION_COOKIE_HTTPONLY = True  # JavaScript cannot access session cookies
CSRF_COOKIE_HTTPONLY = True  # JavaScript cannot access CSRF tokens
SESSION_COOKIE_SAMESITE = 'Strict'  # Cookie sent only in same-site requests
CSRF_COOKIE_SAMESITE = 'Strict'  # CSRF token sent only in same-site requests
```
- **Security Impact**:
  - HttpOnly prevents XSS-based session hijacking
  - SameSite=Strict prevents CSRF attacks across domains

#### Clickjacking Protection
```python
X_FRAME_OPTIONS = 'DENY'  # Prevent framing in any context
```
- **Security Impact**: Prevents clickjacking attacks where page is embedded in iframe

#### Content Security Policy
```python
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),  # Only same-origin content by default
    'script-src': ("'self'",),   # Only same-origin scripts
    'style-src': ("'self'", "'unsafe-inline'"),  # Inline styles allowed (common in Django templates)
    'img-src': ("'self'", 'data:'),  # Images from same-origin or data URIs
}
```
- **Security Impact**: 
  - Restricts where content can be loaded from
  - Prevents injected scripts from executing
  - Limits XSS attack surface

#### XSS Filter
```python
SECURE_BROWSER_XSS_FILTER = True
```
- **Security Impact**: Enables browser's built-in XSS protection filter

#### Password Validation (Already Configured)
- 4 password validators enforce strong password requirements:
  1. UserAttributeSimilarityValidator: Prevents passwords too similar to user info
  2. MinimumLengthValidator: Enforces minimum password length
  3. CommonPasswordValidator: Rejects common weak passwords
  4. NumericPasswordValidator: Rejects all-numeric passwords
- **Security Impact**: Reduces risk of weak password compromise

### 2. Created tests/test_django_security_settings.py
New test suite with 12 comprehensive tests validating security configuration:

#### Tests Included
- `test_secret_key_is_set_in_production`: Ensures SECRET_KEY is properly configured
- `test_debug_is_false_in_production`: Validates DEBUG=False for production
- `test_allowed_hosts_is_configured`: Confirms ALLOWED_HOSTS is set as list
- `test_session_cookie_is_httponly`: Verifies SESSION_COOKIE_HTTPONLY=True
- `test_csrf_cookie_is_httponly`: Verifies CSRF_COOKIE_HTTPONLY=True
- `test_session_cookie_samesite_is_strict`: Validates SESSION_COOKIE_SAMESITE='Strict'
- `test_csrf_cookie_samesite_is_strict`: Validates CSRF_COOKIE_SAMESITE='Strict'
- `test_x_frame_options_set`: Confirms X_FRAME_OPTIONS='DENY'
- `test_xss_filter_enabled`: Validates SECURE_BROWSER_XSS_FILTER=True
- `test_csp_is_configured`: Confirms CSP dictionary exists and is configured
- `test_ssl_redirect_in_production`: Verifies SECURE_SSL_REDIRECT setting exists
- `test_password_validators_configured`: Ensures 4+ password validators configured

**Test Results**: ✅ All 12 tests pass (0.016s)

### 3. Created .env.example
Documentation file showing required environment variables:
```
DJANGO_ENV=production                    # Control dev vs production mode
DJANGO_SECRET_KEY=your-secret-key-here   # REQUIRED in production
DJANGO_ALLOWED_HOSTS=                    # Space-separated list of allowed domains
```

### 4. Updated .env
Development configuration with safe defaults:
```
DJANGO_ENV=development
DJANGO_SECRET_KEY=django-insecure-dev-key-unsafe-for-production
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]
```

## Security Design Decisions

### Why DJANGO_ENV Instead of Separate Settings Files
- **Single source of truth**: One settings.py instead of multiple environment-specific files
- **Consistency**: Development behavior clearly marked and easily testable
- **Reliability**: No file selection logic that could fail in production
- **Auditability**: All configuration is explicit in code

### Why SECRET_KEY Has No Production Default
- **Security principle**: "Fail secure" - crashes are better than running with exposed secrets
- **Detection**: Immediate indication if deployment is misconfigured
- **Prevention**: Prevents accidental deployment with development secret key

### Why DEBUG Defaults to False
- **Defense in depth**: Production safety by default
- **Error handling**: Forces proper error handling and logging setup
- **Information leakage**: Debug pages expose sensitive configuration and stack traces

### Why ALLOWED_HOSTS Is Enforced
- **Host header attacks**: Prevents cache poisoning and request forgery via Host header manipulation
- **Modern requirement**: Essential with reverse proxies and load balancers
- **Explicit configuration**: No "just works" behavior that could be insecure

### Why SameSite=Strict Not Lax
- **Strict security**: No cookies sent even in top-level navigation from external sites
- **CSRF prevention**: Comprehensive protection against cross-site request forgery
- **Compatible**: Supported by all modern browsers

### Why HSTS Is Set to 1 Year
- **Standard duration**: 31536000 seconds (1 year) is industry standard
- **Sufficient period**: Long enough to provide sustained protection
- **HSTS preload**: Allows inclusion in browser preload lists for additional protection
- **Renewal**: Updated with each deployment to maintain protection

## Validation

### Test Coverage
- 12 new security validation tests
- All existing 29 uwase05 tests still pass (no regressions)
- Total: 41 tests passing

### Production Deployment Checklist
Before deploying to production, ensure:
- [ ] `DJANGO_ENV=production` is set
- [ ] `DJANGO_SECRET_KEY` is set to a strong random value (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] `DJANGO_ALLOWED_HOSTS` is set to your domain(s) (e.g., `example.com www.example.com`)
- [ ] HTTPS certificate is configured at the reverse proxy/load balancer
- [ ] All security settings tests pass: `python manage.py test tests.test_django_security_settings`

## Migration Path

### For Existing Deployments
If updating existing deployments:
1. Back up current settings and environment variables
2. Add required environment variables:
   ```bash
   export DJANGO_ENV=production
   export DJANGO_SECRET_KEY=<your-strong-secret-key>
   export DJANGO_ALLOWED_HOSTS=your.domain.com
   ```
3. Restart Django application
4. Verify all tests pass
5. Monitor logs for any security warnings

### For New Deployments
1. Set environment variables before first startup
2. All security settings will be automatically applied
3. Run `python manage.py test` to validate configuration

## Security Improvements Summary

| Vulnerability | Before | After | Mechanism |
|---------------|--------|-------|-----------|
| DEBUG information leakage | Possible | Prevented | DEBUG=False in production |
| Session hijacking via XSS | Vulnerable | Protected | SESSION_COOKIE_HTTPONLY |
| CSRF attacks | Vulnerable | Protected | CSRF_COOKIE_SAMESITE=Strict |
| Clickjacking | Vulnerable | Protected | X_FRAME_OPTIONS=DENY |
| Injected scripts | Partially protected | Better protected | CSP policy |
| Unencrypted transport | Possible | Enforced | SECURE_SSL_REDIRECT |
| Downgrade attacks | Possible | Prevented | SECURE_HSTS |
| Weak passwords | Possible | Limited | Password validators |
| Secret key exposure | Possible | Prevented | Required env var |

## AI Assistance Disclosure

This PR was developed with AI assistance from GitHub Copilot. The following elements were refined with AI guidance:
- Django security settings configuration best practices
- HSTS duration and preload settings selection
- CSP policy balancing security with functionality
- Test design for validating security settings
- Documentation of security decisions

The implementation reflects industry security standards and Django's official security recommendations.

## Testing Instructions

### Run Security Settings Tests
```bash
cd devsec-demo
python manage.py test tests.test_django_security_settings -v 2
```

### Run All Tests (including existing functionality)
```bash
python manage.py test -v 2
```

### Test in Development Mode
```bash
export DJANGO_ENV=development
python manage.py runserver
# App should start normally with DEBUG=True
```

### Test in Production Mode (with required env vars)
```bash
export DJANGO_ENV=production
export DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
export DJANGO_ALLOWED_HOSTS=localhost
python manage.py runserver
# App should start normally with DEBUG=False
```

### Test Production Mode Without DJANGO_SECRET_KEY (should fail)
```bash
export DJANGO_ENV=production
unset DJANGO_SECRET_KEY
python manage.py runserver
# Should raise ValueError about missing SECRET_KEY
```

## Deployment Notes

### Environment Variables Required
- `DJANGO_ENV`: Set to 'production' for production deployments
- `DJANGO_SECRET_KEY`: Strong random value (minimum 50 characters recommended)
- `DJANGO_ALLOWED_HOSTS`: Space-separated list of domains (e.g., 'example.com www.example.com')

### Reverse Proxy Configuration
For production with HTTPS via reverse proxy:
1. Set `DJANGO_ENV=production` in Django environment
2. Configure reverse proxy to:
   - Terminate HTTPS connections
   - Forward `X-Forwarded-Proto: https` header
   - Forward `X-Forwarded-For` header for real IP
3. Django will trust these headers and redirect accordingly

### Monitoring & Logging
After deployment, monitor for:
- 400 Bad Request errors (often indicate host header attacks being blocked)
- 302 redirects to HTTPS (should decrease after initial deployment)
- HSTS header in responses (should include `max-age=31536000`)

## Files Modified
- `devsec_demo/settings.py`: Added security configuration and helpers
- `tests/test_django_security_settings.py`: New test suite (created)
- `.env.example`: New documentation file (created)
- `.env`: Updated with development configuration

## Related Documentation
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security/)

## Sign-off
✅ All tests passing
✅ No regressions in existing functionality
✅ Security hardening complete for production deployment
✅ Environment configuration documented
✅ Ready for production use with proper environment setup
