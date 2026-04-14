import logging

logger = logging.getLogger('jeanclaudeirumva.audit')


def log_registration(username):
    """Log successful user registration."""
    logger.info("REGISTRATION username=%s", username)


def log_login_success(username):
    """Log successful login."""
    logger.info("LOGIN_SUCCESS username=%s", username)


def log_login_failure(username):
    """Log failed login attempt."""
    logger.warning("LOGIN_FAILURE username=%s", username)


def log_logout(username):
    """Log user logout."""
    logger.info("LOGOUT username=%s", username)


def log_password_change(username):
    """Log password change - never log the actual password."""
    logger.info("PASSWORD_CHANGE username=%s", username)


def log_password_reset_request(email):
    """Log password reset request - log email domain only to protect privacy."""
    domain = email.split('@')[-1] if '@' in email else 'unknown'
    logger.info("PASSWORD_RESET_REQUEST email_domain=%s", domain)


def log_unauthorized_access(username, resource):
    """Log unauthorized access attempts."""
    logger.warning("UNAUTHORIZED_ACCESS username=%s resource=%s", username, resource)