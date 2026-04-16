from .models import AuditLog

def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def record_audit_log(event_type, request, user=None, username_attempted='', details=''):
    """
    Utility to record security-relevant events in the persistent AuditLog.
    """
    AuditLog.objects.create(
        user=user,
        event_type=event_type,
        username_attempted=username_attempted,
        ip_address=get_client_ip(request),
        details=details
    )
