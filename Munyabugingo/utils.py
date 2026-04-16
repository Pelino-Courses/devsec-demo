import logging
from django.utils.http import url_has_allowed_host_and_scheme

audit_logger = logging.getLogger('Munyabugingo.audit')

def log_audit_event(event_type, user=None, request=None, status='SUCCESS', metadata=None):
    """
    Standardized helper to log security-relevant audit events.
    Captures timestamp (via logger), event type, user, IP, and details.
    IMPORTANT: sensitive data such as passwords is never logged.
    """
    client_ip = 'UNKNOWN'
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR')

    username = user.username if user and user.is_authenticated else 'ANONYMOUS'
    if not user and request and request.user.is_authenticated:
        username = request.user.username

    message = f"[{event_type}] status={status} user={username} ip={client_ip}"
    if metadata:
        # Sanitize metadata - never log passwords or other secrets
        sanitized_metadata = {k: v for k, v in metadata.items() if 'password' not in k.lower()}
        message += f" details={sanitized_metadata}"

    audit_logger.info(message)


def get_safe_redirect_url(request, default_url):
    """
    Safely extract and validate a redirect URL from the request.
    Checks 'next' in POST and then GET parameters.
    Rejects external URLs and unsafe schemes to prevent open redirect attacks.
    """
    redirect_to = request.POST.get('next', request.GET.get('next'))

    # Check if URL is safe: internal and uses allowed schemes
    if redirect_to and url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to

    return default_url
