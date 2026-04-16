# CSRF Misuse Design Note

The unsafe behavior in this app was the logout flow. Logging out changes
session state, but the original implementation allowed it through a simple GET
request linked directly from navigation. Because GET requests do not carry CSRF
tokens, another site could trigger logout for an authenticated user.

This fix restores Django's standard CSRF pattern:

- logout is now POST-only
- each logout control is rendered as a form with `{% csrf_token %}`
- tests enforce that GET is rejected, POST without a token fails, and POST with
  a valid token succeeds

This keeps normal logout behavior working for legitimate users while making the
state-changing request follow Django's built-in CSRF protection model.
