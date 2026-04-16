# Open Redirect Design Note

This change adds validated post-authentication redirect handling for the UAS.
The app now accepts `next` only when it points to a safe local destination.

Security choices in this fix:

- Redirect targets are validated with Django's
  `url_has_allowed_host_and_scheme`.
- External URLs and scheme-relative destinations are rejected and replaced with
  predictable internal defaults.
- Login and registration preserve legitimate internal navigation when a user was
  first sent to an auth page from a protected route.
- Custom privileged/admin decorators now use Django's `redirect_to_login`
  helper so the `next` parameter is generated consistently and safely.
