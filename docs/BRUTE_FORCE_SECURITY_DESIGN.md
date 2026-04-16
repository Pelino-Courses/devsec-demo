# Brute-Force Protection Security Design

## Overview

This document describes the security design for hardening the login flow against brute-force attacks. The implementation uses **account-based progressive throttling** with multiple time windows to balance **security** (protecting against abuse) with **usability** (allowing legitimate retries and account recovery).

---

## 1. Threat Model: Login Brute-Force Attacks

### Attack Scenarios

**Credential Stuffing**
- Attacker uses lists of compromised username/password pairs from data breaches
- Attempts many login requests in rapid succession
- Goal: Find valid credentials or gain unauthorized access
- Risk: Compromised user accounts, unauthorized data access

**Password Guessing**
- Attacker focuses on one target account
- Tries common passwords or variations (dictionary attacks)
- Goal: Guess the correct password
- Risk: Account takeover for high-value targets

**User Enumeration**
- Attacker attempts logins to discover which usernames exist
- Uses timing differences or error messages to infer results
- Goal: Build list of valid usernames for targeted attacks
- Risk: Enables focused password guessing and social engineering

---

## 2. Defense Mechanisms

### Password Hashing (First Line of Defense)
- Django uses **PBKDF2** with 260,000 iterations by default (computationally expensive)
- Password comparisons use **constant-time** comparison (prevents timing attacks)
- Even if database is compromised, passwords are not directly usable

### Rate Limiting (Second Line of Defense)
- Tracks **failed login attempts** by username in a `LoginAttempt` model
- Checks throttle status **before processing login form**
- Returns **HTTP 429 (Too Many Requests)** when throttled
- Uses **progressive delays** (not immediate permanent lockout)

### User Enumeration Prevention
- **Records attempts for non-existent usernames** (distinguishing real users is harder)
- Uses consistent error messages: "Invalid username or password"
- Prevents attackers from building accurate username lists

---

## 3. Progressive Throttling Strategy

The throttling system uses **nested time windows** with progressive severity:

```
3+ failures in 5min  → 5-minute delay
5+ failures in 15min → 15-minute delay
10+ failures in 1h   → 60-minute delay
20+ failures in 24h  → 24-hour lockout
```

### Why Progressive Throttling?

**Security Benefits:**
- Early throttling (3 attempts) stops most automated attacks immediately
- Higher thresholds prevent legitimate users from getting locked out accidentally
- Escalating delays make large-scale attacks economically unfeasible

**Usability Benefits:**
- Allows ~2 typos before throttle kicks in (realistic for humans)
- Legitimate users can recover via password reset within 24 hours
- No permanent account lockouts (prevents denial-of-service against intended users)

### Implementation Details

**Time Windows (Separate Checks):**
```python
failed_5m = attempts in last 5 minutes
failed_15m = attempts in last 15 minutes
failed_1h = attempts in last 1 hour
failed_24h = attempts in last 24 hours
```

**Throttle Status Logic:**
1. Check if 20+ failures in 24 hours → **24-hour lockout**
2. Else if 10+ failures in 1 hour → **60-minute delay**
3. Else if 5+ failures in 15 minutes → **15-minute delay**
4. Else if 3+ failures in 5 minutes → **5-minute delay**
5. Else → **Allow login attempt**

**Unlock Mechanism:**
- Expires automatically when the oldest failure in the window is more than the window size old
- No manual admin intervention needed
- Time calculated as: `oldest_failure_time + window_duration`

---

## 4. Implementation Details

### `LoginAttempt` Model

```python
class LoginAttempt(models.Model):
    user = ForeignKey(User)              # NULL for non-existent usernames
    username = CharField(max_length=150) # Always set (even if user DNE)
    ip_address = GenericIPAddressField() # For future IP-based throttling
    attempt_timestamp = DateTimeField()  # Auto-set to now()
    is_successful = BooleanField()       # True/False for auth result
```

**Database Indexes:**
- `(username, timestamp)` - Fast lookup of user's attempts in time window
- `(user_id, timestamp)` - Fast lookup for same user across migrations
- `(ip_address, timestamp)` - Ready for IP-based throttling in future

**Design Choice: Not Indexed by IP Alone**
- Currently username-based (account owner wants to protect their account)
- IP-based throttling could also prevent distributed attacks across many accounts
- Could be added later without breaking existing indexes

### Key Functions

**`get_client_ip(request)`**
- Extracts client IP from request
- Handles proxied requests via `X-Forwarded-For` header
- Falls back to `REMOTE_ADDR` for direct connections

**`record_login_attempt(request, username, is_successful=False)`**
- Records attempt with IP and timestamp
- Creates `LoginAttempt` record regardless of user existence
- Called on both successful and failed login attempts

**`get_throttle_status(username)`**
- Checks all four time windows for failed attempts
- Returns: `(is_throttled, seconds_remaining, failed_attempts_count)`
- Used by login view to decide whether to allow attempt

### Login View Integration

```python
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        
        # Check throttle status BEFORE form processing
        is_throttled, seconds_remaining, _ = get_throttle_status(username)
        if is_throttled:
            # Return 429 with user-friendly message
            return render(..., status=429)
        
        # Process login as normal
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            record_login_attempt(request, username, is_successful=True)
            login(request, user)
        else:
            record_login_attempt(request, username, is_successful=False)
```

---

## 5. User Experience & Messaging

### Throttle Error (HTTP 429)

When throttled, users see:
```
⚠️ Too Many Failed Attempts

Too many failed login attempts. Please try again in X minute(s).
Failed attempts: N

If you forgot your password, reset it here.
```

**Design Choices:**
- Shows **minute counter** (friendly, not raw seconds)
- Shows **total attempt count** (helps users understand severity)
- Provides **password reset link** (gives legitimate users an escape hatch)
- Does **not** expose exact throttle threshold (security through obscurity on rules)

### Normal Login Errors

Clear but non-leaky messages:
- ✅ "Invalid username or password" - Same message for all failures
- ❌ Does NOT say "Username does not exist" or "Password wrong"
- ❌ Does NOT use different HTTP status for user vs password failures

---

## 6. Security Properties

### Attacks Mitigated

**Credential Stuffing**
- Throttles after just 3 attempts in 5 minutes (typically automated tools do 10+/sec)
- Effectively stops this attack pattern at the application layer
- Attacker needs to send from different IPs or wait in between attempts

**Password Guessing**
- 24-hour lockout after 20 attempts in 24 hours
- Makes dictionary attacks on specific accounts impractical
- Even with slow attempts (1 per minute), only ~1440 guesses possible per day per account

**User Enumeration**
- Same throttling applies to non-existent users
- Attackers can't distinguish valid/invalid by attempt limits
- Error messages don't leak user existence
- Timing attacks are mitigated by password hashing overhead

### Assumptions & Limitations

**Assumes:**
- Usernames are not sensitive (typically public in social systems)
- Single-database deployment (not considering distributed scenarios)
- Attackers respect HTTP 429 responses (won't use different IPs persistently)
- Session storage/database is trusted

**Does Not Address:**
- **IP-based distributed attacks** - If attacker uses many IPs, each IP can attempt login
  - *Future improvement:* Add IP-based throttling
  - *Alternative:* Use separate rate limiting service (e.g., fail2ban, nginx)
  
- **Account lockout attacks** - Attacker can lock target out by sending bogus attempts
  - *Mitigation:* Not permanent (expires after window) + password reset available
  - *Consideration:* Could add IP-based detection for rapid lockout patterns

- **Timing-based password cracking** - Relies on network latency, not password strength
  - *Achieved by:* PBKDF2 hashing adds 260,000 iterations (~250ms per check)

---

## 7. Testing Strategy

### Test Coverage

**Normal Flow:**
- ✅ Successful login recorded
- ✅ Failed attempts recorded
- ✅ Different users have independent throttle states

**Throttle Activation:**
- ✅ 3+ failures in 5 min → blocked
- ✅ 5+ failures in 15 min → blocked (even if 3/5 are old)
- ✅ 10+ failures in 1 hour → blocked
- ✅ 20+ failures in 24 hours → blocked

**Throttle Release:**
- ✅ Throttle lifted when window expires
- ✅ Successful login after throttle expires

**Edge Cases:**
- ✅ Non-existent user gets throttled like real users
- ✅ Empty username handled gracefully
- ✅ Authenticated users redirected from login

**Enforcement:**
- ✅ Throttle checked BEFORE form validation
- ✅ HTTP 429 status returned
- ✅ Readable error message shown

### Running Tests

```bash
# Run all security tests
python manage.py test uwamahoro_joseline.tests

# Run specific test class
python manage.py test uwamahoro_joseline.tests.LoginViewBruteForceTests

# Run with verbose output
python manage.py test uwamahoro_joseline.tests -v 2

# Run with coverage
coverage run --source='uwamahoro_joseline' manage.py test uwamahoro_joseline.tests
coverage report
```

---

## 8. Configuration & Tuning

### Threshold Configuration

Current thresholds (in `views.py`, `get_throttle_status()`):

```python
# 5-minute delay after 3 failures in 5 minutes
if failed_5m >= 3

# 15-minute delay after 5 failures in 15 minutes
if failed_15m >= 5

# 60-minute delay after 10 failures in 1 hour
if failed_1h >= 10

# 24-hour lockout after 20 failures in 24 hours
if failed_24h >= 20
```

### Tuning for Different Scenarios

**Stricter Security (High-Sensitivity Systems):**
```python
3 failures in 5 min → 10 min delay
4 failures in 15 min → 30 min delay
8 failures in 1 hour → 2 hour delay
15 failures in 24 hours → 24 hour lockout
```

**Looser (More User-Friendly):**
```python
5 failures in 5 min → 5 min delay
8 failures in 15 min → 15 min delay
15 failures in 1 hour → 60 min delay
30 failures in 24 hours → 24 hour lockout
```

### Monitoring

Track login abuse patterns:
```python
# Get failed attempts by username in last 24 hours
from datetime import timedelta
from django.utils import timezone

day_ago = timezone.now() - timedelta(hours=24)
attempts = LoginAttempt.objects.filter(
    is_successful=False,
    attempt_timestamp__gte=day_ago,
).values('username').annotate(
    count=Count('id')
).order_by('-count')[:10]

for attempt in attempts:
    print(f"{attempt['username']}: {attempt['count']} failed attempts")
```

---

## 9. Deployment Checklist

- [x] LoginAttempt model created and migrated
- [x] Utility functions implemented (`get_client_ip`, `record_login_attempt`, `get_throttle_status`)
- [x] Login view updated to check throttle_status before processing
- [x] Login template shows throttle error and recovery options
- [x] Database indexes created for performance
- [x] Comprehensive test suite covering normal + abuse scenarios
- [x] Error messages consistent (no user enumeration)
- [ ] Database query optimization (check EXPLAIN PLAN)
- [ ] Monitoring/alerting set up for attack patterns
- [ ] Documentation reviewed by security team

---

## 10. Future Enhancements

1. **IP-Based Throttling**
   - Add secondary throttle on IP address (prevent distributed attacks)
   - Use `X-Forwarded-For` from reverse proxy (if available)

2. **CAPTCHA Integration**
   - Show CAPTCHA after 1 failed attempt (instead of/alongside throttle)
   - Requires `django-recaptcha` or similar

3. **Notification System**
   - Email user alerts: "Failed login from IP X"
   - Only send if not throttled (prevent spam)

4. **Geo-Blocking**
   - Optional: Allow login only from known IP ranges
   - Harder to implement correctly; requires good geolocation DB

5. **Two-Factor Authentication (2FA)**
   - Best long-term defense against password compromise
   - Can combine with throttling for defense-in-depth

6. **Velocity Checking**
   - Track successful logins from new IPs
   - Alert user or require verification step

---

## 11. References

- [OWASP: Brute Force Attack](https://owasp.org/www-community/attacks/Brute_force_attack)
- [OWASP: Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html#sec5)

---

## Summary

This implementation provides **practical, auditable brute-force protection** that:
- ✅ Stops most automated attacks within seconds
- ✅ Preserves usability for legitimate users
- ✅ Prevents user enumeration
- ✅ Scales to production with database indexing
- ✅ Is easily testable and monitorable
- ✅ Follows Django best practices

The progressive throttling strategy is the key insight: **allow a few retries** (human-friendly), but **escalate quickly** (attacker-hostile).
