# Design Note: Security Architecture for MUNYABUGINGO

This document outlines the multi-layered security architecture implemented to protect the MUNYABUGINGO platform against common OWASP vulnerabilities and ensure robust auditing.

## 1. Authentication and Brute Force Protection
- **Layer**: `SecureLoginView` (subclass of Django's `LoginView`)
- **Mechanism**: IP-based rate limiting via Django's `cache` framework.
- **Controls**: Max 5 failed attempts within 5 minutes results in a 15-minute lockout for the originating IP.
- **Impact**: Mitigates credential stuffing and brute force attacks.

## 2. Insecure Direct Object Reference (IDOR) Prevention
- **Layer**: View-level authorization checks.
- **Mechanism**: Explicit ownership checks in `profile_detail` view using `profile.user == request.user`.
- **RBAC Integration**: Administrative users with the `can_view_admin_dashboard` permission have a legitimate override for help-desk support workflows.
- **Impact**: Protects private user profile data from unauthorized access.

## 3. Cross-Site Request Forgery (CSRF) Protection
- **Layer**: Middleware and context-aware headers.
- **Mechanism**: Hardened logout (POST-only) and AJAX "Like" API integration.
- **Implementation**: The "Like" feature securely retrieves the `csrftoken` from cookies and passes it via the `X-CSRFToken` header for all state-changing asynchronous requests.
- **Impact**: Prevents session abduction and unauthorized state changes from third-party sites.

## 4. Cross-Site Scripting (XSS) Mitigation
- **Layer**: Context-aware output encoding.
- **Mechanism**: 
    - **HTML**: Relies on standard Django auto-escaping for `bio` and `location` fields.
    - **JavaScript**: Explicit use of the `|escapejs` filter for all content rendered inside `<script>` blocks (e.g., toast messages).
- **Impact**: Eliminates both stored and reflected XSS vectors.

## 5. Open Redirect Protection
- **Layer**: Centralized redirect utility (`get_safe_redirect_url`).
- **Mechanism**: All authentication views (login, register, profile) validate the `next` parameter against the current host and a defined allow-list.
- **Impact**: Protects users against phishing attacks that weaponize the app's redirection logic.

## 6. Security Audit Logging
- **Layer**: Centralized auditing utility and Django signals.
- **Mechanism**: Logs all critical authentication lifecycle events (registrations, logins, lockouts, profile updates, password changes).
- **Privacy**: Automatically masks or excludes sensitive PII (like full email addresses or raw IPs in certain contexts) to adhere to internal data retention policies while maintaining non-repudiation.
- **Impact**: Provides a transparent audit trail for security investigations.
