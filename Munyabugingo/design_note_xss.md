# Design Note: Mitigating Stored and Reflected XSS

## What is the XSS Risk?
Cross-Site Scripting (XSS) is a security vulnerability where an attacker injects malicious scripts into content that is then delivered to other users.
- **Stored XSS**: Occurs when malicious input is saved in the database (e.g., in a user's `bio`) and later rendered on a page viewed by others.
- **Reflected XSS**: Occurs when malicious input is immediately "reflected" back to the user in a response (e.g., in an error message or a toast notification).

In the context of the user profile, `bio` fields and arbitrary text inputs are primary targets for stored XSS. A malicious actor could provide `<script>alert('XSS')</script>` as their biography. If other authenticated users visited this attacker's profile page, the code would execute within the victim's session.

## Mitigation Strategy

### 1. Robust Output Encoding (HTML)
To mitigate stored XSS in profile content, we enforce strict output encoding whenever user-controlled content is rendered in templates.
- **Framework Defaults**: We rely explicitly on Django's default auto-escaping features (`{{ profile.bio }}`). By avoiding templates tags like `|safe` or `{% autoescape off %}`, Django automatically converts special HTML characters into innocuous HTML entities (e.g., `<` into `&lt;`).
- **Validation**: Our `tests_xss.py` suite explicitly asserts that malicious payloads in profile records are rendered as escaped entities rather than raw script tags.

### 2. Context-Aware Encoding (JavaScript)
A common "gotcha" in web security is rendering data inside `<script>` blocks. Standard HTML auto-escaping is often insufficient because JavaScript has different syntax rules.
- **The Vulnerability**: Using `showToast("{{ message }}", ...)` is dangerous because a message containing a double quote could break out of the string literal and execute arbitrary JS.
- **The Fix**: We use the `|escapejs` filter for any data rendered inside a JavaScript block. This context-aware encoding ensures that all characters are safe for use in JavaScript string literals (e.g., `"` is escaped to `\u0022`).

By combining framework-default auto-escaping for HTML with context-aware `|escapejs` for JavaScript, we provide a defense-in-depth posture against XSS while preserving a seamless user experience.
