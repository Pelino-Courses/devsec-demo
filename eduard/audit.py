"""
Audit logging for security-relevant authentication events.

Design principles:
- Every log entry includes a timestamp (from the logging framework),
  event type, username, and IP address for traceability
- Raw passwords, tokens, and session keys are NEVER logged
- Log levels follow severity: INFO for normal events, WARNING for
  suspicious events such as failed logins and lockouts
- A dedicated 'eduard.audit' logger keeps audit events separate from
  Django's own logging so they can be routed independently in production
"""
import logging

audit_log = logging.getLogger('eduard.audit')


def _get_ip(request):
    """
    Extract the client IP address from the request.
    Checks X-Forwarded-For first for requests behind a proxy,
    falls back to REMOTE_ADDR for direct connections.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def log_registration(request, username):
    """Log a successful user registration."""
    audit_log.info(
        'event=registration status=success username=%s ip=%s',
        username,
        _get_ip(request),
    )


def log_login_success(request, username):
    """Log a successful login."""
    audit_log.info(
        'event=login status=success username=%s ip=%s',
        username,
        _get_ip(request),
    )


def log_login_failure(request, username, attempts):
    """Log a failed login attempt with the current attempt count."""
    audit_log.warning(
        'event=login status=failure username=%s ip=%s attempts=%d',
        username,
        _get_ip(request),
        attempts,
    )


def log_account_locked(request, username):
    """Log when an account is locked due to too many failures."""
    audit_log.warning(
        'event=login status=locked username=%s ip=%s',
        username,
        _get_ip(request),
    )


def log_logout(request, username):
    """Log a successful logout."""
    audit_log.info(
        'event=logout status=success username=%s ip=%s',
        username,
        _get_ip(request),
    )


def log_password_change(request, username):
    """Log a successful password change. The new password is never logged."""
    audit_log.info(
        'event=password_change status=success username=%s ip=%s',
        username,
        _get_ip(request),
    )


def log_password_reset_request(request, email):
    """
    Log a password reset request.
    Only the email is logged, not whether an account exists for it,
    to avoid leaking account existence information in logs.
    """
    audit_log.info(
        'event=password_reset_request email=%s ip=%s',
        email,
        _get_ip(request),
    )