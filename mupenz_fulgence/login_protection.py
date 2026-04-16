"""
mupenz_fulgence.login_protection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Cache-based brute-force protection for the login endpoint.

Strategy: per-username account lockout
──────────────────────────────────────
Track consecutive failed login attempts per normalized username.
After LOGIN_MAX_ATTEMPTS failures within LOGIN_ATTEMPT_WINDOW seconds,
the account is locked for LOGIN_LOCKOUT_DURATION seconds.
A successful login clears the counter and any active lockout immediately.

Design decisions
────────────────
Per-username (not per-IP)
    IP-based blocking is trivially bypassed with rotating proxies and
    botnets, and punishes innocent users sharing a NAT gateway.
    Username-based lockout is targeted: only the attacked account is
    affected, and behaviour is identical for real and fictitious usernames
    — preserving the anti-enumeration property.

Cache (not database)
    Failure counters are ephemeral; they should expire automatically without
    cron jobs or cleanup tasks.  The cache TTL *is* the expiry mechanism.
    No migrations are needed.  All Django backends (LocMemCache, Redis,
    Memcached) support the add() + incr() pattern used here.

Short lockout (not permanent)
    Permanent lockout requires admin intervention and frustrates legitimate
    users who simply forgot their password.  A 15-minute window stops
    automated tools (which need thousands of attempts) while barely
    inconveniencing humans.  Users can always request a password reset.

Configurable via settings
    LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_DURATION, and LOGIN_ATTEMPT_WINDOW
    can all be overridden per environment without code changes.
"""
from django.conf import settings
from django.core.cache import cache

#: Maximum consecutive failures before the account is locked.
MAX_ATTEMPTS: int = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)

#: Seconds the account remains locked once the threshold is reached.
LOCKOUT_DURATION: int = getattr(settings, 'LOGIN_LOCKOUT_DURATION', 900)  # 15 min

#: Rolling window (seconds) over which consecutive failures are counted.
#: Failures older than this window no longer count toward the threshold.
ATTEMPT_WINDOW: int = getattr(settings, 'LOGIN_ATTEMPT_WINDOW', 900)  # 15 min

# Cache key namespaces — prefix avoids collision with other cache consumers.
_ATTEMPTS_NS = 'mf:login:attempts:'
_LOCKED_NS   = 'mf:login:locked:'


# ── Internal helpers ───────────────────────────────────────────────────────────

def _attempts_key(username: str) -> str:
    """Normalise username and return the cache key for the failure counter."""
    return _ATTEMPTS_NS + username.lower().strip()


def _locked_key(username: str) -> str:
    """Normalise username and return the cache key for the lockout flag."""
    return _LOCKED_NS + username.lower().strip()


# ── Public API ─────────────────────────────────────────────────────────────────

def is_locked_out(username: str) -> bool:
    """
    Return True if the account is currently under an active lockout penalty.
    Returns False for empty usernames to avoid false positives on blank POSTs.
    """
    if not username:
        return False
    return bool(cache.get(_locked_key(username)))


def get_failure_count(username: str) -> int:
    """Return the number of consecutive failures currently on record."""
    if not username:
        return 0
    return cache.get(_attempts_key(username), 0)


def record_failure(username: str) -> int:
    """
    Increment the failure counter for *username*.
    Locks the account if the counter reaches MAX_ATTEMPTS.
    Returns the updated failure count.

    Implementation note — add() + incr() pattern:
      cache.add(key, 0, ttl)   sets the key only when absent, starting the
                                rolling window on the very first failure.
      cache.incr(key)           atomically increments the existing key.
    Both operations are atomic in Redis, Memcached, and LocMemCache, so
    this pattern is safe under concurrent requests.
    """
    if not username:
        return 0
    key = _attempts_key(username)
    # Start the rolling window on first failure; subsequent calls preserve TTL.
    cache.add(key, 0, ATTEMPT_WINDOW)
    count = cache.incr(key)
    if count >= MAX_ATTEMPTS:
        cache.set(_locked_key(username), True, LOCKOUT_DURATION)
    return count


def reset_failures(username: str) -> None:
    """
    Clear the failure counter and any active lockout for *username*.
    Must be called on every successful authentication so that a user who
    previously triggered near-lockout starts fresh after signing in.
    """
    if not username:
        return
    cache.delete(_attempts_key(username))
    cache.delete(_locked_key(username))


def attempts_before_lockout(username: str) -> int:
    """
    Return how many more failed attempts are allowed before lockout.
    Useful for showing a pre-lockout warning in the UI.
    """
    return max(0, MAX_ATTEMPTS - get_failure_count(username))
