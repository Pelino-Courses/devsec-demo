"""Audit logging for security-relevant authentication and privilege events.

All helpers write to the 'webwi.audit' logger so log routing is controlled
entirely in settings.LOGGING.

Privacy rules enforced here:
- Raw passwords are never passed to these functions and must never be logged.
- The email address submitted to the password-reset form is intentionally
  omitted from log_password_reset_request to avoid writing PII that could
  aid user-enumeration if logs are ever exposed.
- IP addresses are recorded to support incident investigation.
"""

import logging

logger = logging.getLogger('webwi.audit')


def _ip(request):
    """Return the best available client IP from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def log_registration(request, username):
    logger.info("event=user_registered username=%s ip=%s", username, _ip(request))


def log_login_success(request, username):
    logger.info("event=login_success username=%s ip=%s", username, _ip(request))


def log_login_failure(request, username):
    logger.warning("event=login_failure username=%s ip=%s", username, _ip(request))


def log_logout(request, username):
    logger.info("event=logout username=%s ip=%s", username, _ip(request))


def log_password_change(request, username):
    logger.info("event=password_changed username=%s ip=%s", username, _ip(request))


def log_password_reset_request(request):
    # The submitted email is intentionally excluded — see module docstring.
    logger.info("event=password_reset_requested ip=%s", _ip(request))


def log_password_reset_complete(request, username):
    logger.info("event=password_reset_complete username=%s ip=%s", username, _ip(request))


def log_permission_granted(target_username, permission, actor='system'):
    logger.info(
        "event=permission_granted actor=%s target=%s permission=%s",
        actor, target_username, permission,
    )


def log_permission_revoked(target_username, permission, actor='system'):
    logger.info(
        "event=permission_revoked actor=%s target=%s permission=%s",
        actor, target_username, permission,
    )
