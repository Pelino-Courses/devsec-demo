"""
Structured audit logging for security-relevant authentication events.

Logged events: registration, login success/failure/lockout, logout,
password change, password reset requested, password reset complete.

Never logged: passwords, password hashes, session tokens, or any credential.
"""
import logging

_logger = logging.getLogger('apophia.audit')


def _ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def log_registration(request, username):
    _logger.info('event=registration status=success username=%s ip=%s', username, _ip(request))


def log_login_success(request, username):
    _logger.info('event=login status=success username=%s ip=%s', username, _ip(request))


def log_login_failure(request, username):
    _logger.warning('event=login status=failure username=%s ip=%s', username, _ip(request))


def log_login_lockout(request, username):
    _logger.warning('event=login status=locked_out username=%s ip=%s', username, _ip(request))


def log_logout(request, username):
    _logger.info('event=logout username=%s ip=%s', username, _ip(request))


def log_password_change(request, username):
    _logger.info('event=password_change status=success username=%s ip=%s', username, _ip(request))


def log_password_reset_requested(request, email):
    _logger.info('event=password_reset_requested email=%s ip=%s', email, _ip(request))


def log_password_reset_complete(request, username):
    _logger.info('event=password_reset_complete username=%s ip=%s', username, _ip(request))
