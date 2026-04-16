# Login Brute-Force Protection Design Note

This implementation adds a small cache-backed throttle around the login view.
It uses a hybrid strategy:

- per-account throttling slows repeated guessing against one username
- per-IP throttling slows broad guessing against many usernames from one source

Security and usability choices:

- The limits are intentionally simple and configurable in settings so the
  behavior is easy to audit and test.
- The response uses a temporary cooldown rather than a permanent lockout, which
  reduces support burden for legitimate users who mistype a password.
- Successful authentication clears the cached throttle state for that account
  and IP so a legitimate user is not trapped after recovering from a few failed
  attempts.
- The UI shows a clear cooldown message without exposing whether the username
  exists.
