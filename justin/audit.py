import json
import logging


logger = logging.getLogger('justin.audit')


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _user_snapshot(user):
    if not user:
        return None

    return {
        'id': user.id,
        'username': user.get_username(),
    }


def audit_event(event_type, request=None, actor=None, target=None, outcome='success', **details):
    payload = {
        'event_type': event_type,
        'outcome': outcome,
        'actor': _user_snapshot(actor),
        'target': _user_snapshot(target),
        'ip_address': get_client_ip(request) if request else None,
        'details': details,
    }
    logger.info(json.dumps(payload, sort_keys=True))
