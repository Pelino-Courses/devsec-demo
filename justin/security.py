import math
import time

from django.conf import settings
from django.core.cache import cache


THROTTLE_PREFIX = 'login-throttle'


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def normalize_username(username):
    return (username or '').strip().casefold()


def _cache_key(scope, value, suffix):
    return f'{THROTTLE_PREFIX}:{scope}:{value}:{suffix}'


def _window_seconds():
    return getattr(settings, 'LOGIN_THROTTLE_LOCKOUT_SECONDS', 300)


def _record_failure(key):
    failures = cache.get(key, 0) + 1
    cache.set(key, failures, timeout=_window_seconds())
    return failures


def _set_lock(lock_key):
    lock_until = time.time() + _window_seconds()
    cache.set(lock_key, lock_until, timeout=_window_seconds())
    return lock_until


def _lock_state(lock_until, scope):
    if not lock_until:
        return None

    remaining = math.ceil(lock_until - time.time())
    if remaining <= 0:
        return None

    return {
        'locked': True,
        'scope': scope,
        'retry_after': remaining,
    }


def get_login_throttle_state(request, username):
    normalized_username = normalize_username(username)
    client_ip = get_client_ip(request)

    if normalized_username:
        account_state = _lock_state(
            cache.get(_cache_key('account', normalized_username, 'lock')),
            'account',
        )
        if account_state:
            return account_state

    ip_state = _lock_state(
        cache.get(_cache_key('ip', client_ip, 'lock')),
        'ip',
    )
    if ip_state:
        return ip_state

    return {
        'locked': False,
        'scope': None,
        'retry_after': 0,
    }


def register_failed_login(request, username):
    normalized_username = normalize_username(username)
    client_ip = get_client_ip(request)

    account_failures = 0
    if normalized_username:
        account_failures = _record_failure(
            _cache_key('account', normalized_username, 'failures'),
        )
        if account_failures >= getattr(settings, 'LOGIN_THROTTLE_ACCOUNT_FAILURE_LIMIT', 5):
            _set_lock(_cache_key('account', normalized_username, 'lock'))

    ip_failures = _record_failure(_cache_key('ip', client_ip, 'failures'))
    if ip_failures >= getattr(settings, 'LOGIN_THROTTLE_IP_FAILURE_LIMIT', 10):
        _set_lock(_cache_key('ip', client_ip, 'lock'))

    state = get_login_throttle_state(request, username)
    state['account_failures'] = account_failures
    state['ip_failures'] = ip_failures
    return state


def reset_login_throttle(request, username):
    normalized_username = normalize_username(username)
    client_ip = get_client_ip(request)

    keys = [
        _cache_key('ip', client_ip, 'failures'),
        _cache_key('ip', client_ip, 'lock'),
    ]

    if normalized_username:
        keys.extend([
            _cache_key('account', normalized_username, 'failures'),
            _cache_key('account', normalized_username, 'lock'),
        ])

    cache.delete_many(keys)
