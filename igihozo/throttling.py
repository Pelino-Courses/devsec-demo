import time

from django.conf import settings
from django.core.cache import cache


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _normalized_username(username):
    return (username or "").strip().lower()


def _account_key(username):
    return f"igihozo:login-throttle:account:{_normalized_username(username)}"


def _ip_key(client_ip):
    return f"igihozo:login-throttle:ip:{client_ip or 'unknown'}"


def _default_state():
    return {"count": 0, "blocked_until": 0}


def _remaining_seconds(blocked_until):
    return max(1, int(blocked_until - time.time()))


def _read_state(cache_key):
    return cache.get(cache_key, _default_state())


def _write_state(cache_key, state):
    cache.set(cache_key, state, timeout=settings.LOGIN_THROTTLE_WINDOW_SECONDS)


def _register_failure_for_key(cache_key, limit):
    state = _read_state(cache_key)
    state["count"] += 1
    if state["count"] >= limit:
        state["blocked_until"] = time.time() + settings.LOGIN_THROTTLE_WINDOW_SECONDS
    _write_state(cache_key, state)
    return state


def get_login_throttle_state(username, client_ip):
    account_state = _read_state(_account_key(username))
    ip_state = _read_state(_ip_key(client_ip))
    blocked_until = max(account_state["blocked_until"], ip_state["blocked_until"])
    return {
        "account": account_state,
        "ip": ip_state,
        "is_blocked": blocked_until > time.time(),
        "remaining_seconds": _remaining_seconds(blocked_until) if blocked_until > time.time() else 0,
    }


def register_failed_login(username, client_ip):
    normalized_username = _normalized_username(username)
    if normalized_username:
        _register_failure_for_key(
            _account_key(normalized_username),
            settings.LOGIN_THROTTLE_ACCOUNT_LIMIT,
        )
    _register_failure_for_key(_ip_key(client_ip), settings.LOGIN_THROTTLE_IP_LIMIT)


def clear_login_throttle(username, client_ip):
    normalized_username = _normalized_username(username)
    if normalized_username:
        cache.delete(_account_key(normalized_username))
    cache.delete(_ip_key(client_ip))
