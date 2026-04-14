from django.core.cache import cache


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes in seconds


def get_lockout_key(username):
    return f"login_attempts_{username}"


def get_lockout_time_key(username):
    return f"lockout_time_{username}"


def is_account_locked(username):
    attempts = cache.get(get_lockout_key(username), 0)
    return attempts >= MAX_FAILED_ATTEMPTS


def register_failed_attempt(username):
    key = get_lockout_key(username)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOCKOUT_DURATION)
    return attempts


def reset_failed_attempts(username):
    cache.delete(get_lockout_key(username))


def get_remaining_attempts(username):
    attempts = cache.get(get_lockout_key(username), 0)
    return max(0, MAX_FAILED_ATTEMPTS - attempts)