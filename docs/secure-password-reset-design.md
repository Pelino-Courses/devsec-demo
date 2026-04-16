# Secure Password Reset Design Note

This implementation uses Django's built-in password reset views and token
generator instead of a custom reset-token scheme. That keeps the workflow
aligned with framework defaults for token signing, one-time use behavior, and
password validation.

Security choices in this change:

- The request step always redirects to the same confirmation page, whether or
  not the submitted email exists, to reduce user-enumeration risk.
- Reset emails are sent only for real accounts, which matches Django's default
  behavior and avoids noisy mail generation for unknown addresses.
- The confirmation step relies on Django's reset token handling and built-in
  password validators instead of custom password rules.
- Custom templates provide neutral UX copy and avoid exposing unnecessary
  account details during reset.

Validation covered by tests:

- successful reset request for an existing user
- safe reset request behavior for a nonexistent email
- invalid token handling
- successful password update through the canonical confirm flow
- password mismatch and weak-password validation failures
