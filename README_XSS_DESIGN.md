# Security Design Note: Stored XSS Mitigation

## Vulnerability Overview
Stored Cross-Site Scripting (XSS) occurs when an application receives data from a user and stores it in a database, which is later rendered on a page for other users (or the same user) without proper validation or escaping. If rendered as raw HTML, malicious scripts can execute in the victim's browser.

## Mitigation Strategy
This application employs **Context-Aware Output Encoding** to mitigate Stored XSS risk in user-controlled fields such as the **User Bio**.

### 1. Default HTML Escaping
All user-controlled content is rendered using Django's template engine which, by default, escapes all HTML characters.
- `<` becomes `&lt;`
- `>` becomes `&gt;`
- `'` becomes `&#x27;`
- `"` becomes `&quot;`

Example of secure rendering in `profile.html`:
```html
<div class="detail-value">
    {{ profile_user.profile.bio }}
</div>
```

### 2. Avoiding Unsafe Shortcuts
The application explicitly avoids using the following unsafe rendering mechanisms for user content:
- `|safe` template filter
- `mark_safe()` in Python views
- `{% autoescape off %}` blocks

### 3. Verification
Automated security tests in `shema/tests.py` (`StoredXSSTests`) verify that malicious payloads like `<script>alert('XSS')</script>` are neutralized correctly when rendered.

## Authorship Disclosure
This security hardening was implemented with the assistance of the Antigravity AI agent. The student has reviewed and verified the escaping behavior and the associated test suite.
