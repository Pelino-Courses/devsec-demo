# Pull Request: Harden Login Flow Against Brute-Force Attacks

## Assignment Summary
Implemented account-based rate limiting and progressive cooldowns to protect the login flow against brute-force attacks. After 5 failed login attempts, users are temporarily locked out with escalating cooldown periods (30s → 1min → 5min → 15min), preventing credential stuffing and password guessing attacks while maintaining usability for legitimate users.

## Related Issue
Closes #36

## Target Assignment Branch
`assignment/harden-login-brute-force`

## Design Note
**Approach**: Implemented account-based (not IP-based) attempt tracking with a `LoginAttempt` model that records failed attempts per user. Chose progressive cooldowns over immediate account lockout to balance security with user experience—legitimate users can still attempt login but face increasing delays after failures.

**Key design decisions**:
- Tracked by **account**, not IP (users on shared networks aren't blocked)
- Progressive delays instead of immediate permanent lockout
- Generic error messages prevent user enumeration
- Cooldowns reset after 24 hours of inactivity
- All attempts logged to `LoginHistory` for audit trail

## Security Impact
Prevents brute-force attacks by:

1. **Blocking password guessing**: After 5 failed attempts, attacker must wait 30+ seconds between tries
2. **Stopping credential stuffing**: Escalating cooldowns make testing multiple passwords impractical
3. **Maintaining usability**: Legitimate users can still login if they remember their password
4. **Preserving privacy**: Generic error messages don't leak whether account exists

## Changes Made
1. Created `LoginAttempt` model with failed attempt tracking and lockout logic
2. Updated `login()` view to check attempt history and enforce cooldowns
3. Added helper functions: `get_client_ip()`, `get_user_agent()`, `is_temporarily_locked()`, `get_cooldown_seconds()`
4. Created migration for new model
5. Updated Django admin to display attempt history
6. Added 21 comprehensive tests covering normal login, abuse cases, and edge cases
7. Updated `PASSWORD_RESET_DOCUMENTATION.md` with security implementation details

## Validation
- ✅ All 21 brute-force protection tests pass
- ✅ All existing tests still pass (no regressions)
- ✅ Manual testing: 5 incorrect attempts → 30s lockout triggered as expected
- ✅ Legitimate login still works immediately with correct credentials
- ✅ Attempt history visible in admin panel
- ✅ Cooldowns properly escalate with each failure tier

## AI Assistance Used
Yes. GitHub Copilot assisted with:
- Code structure and implementation patterns
- Model design and Django ORM syntax
- Test case generation and organization
- Documentation formatting

## What AI Helped With
1. **Model design**: Suggested the `LoginAttempt` model structure with relevant fields
2. **Helper functions**: Provided `get_client_ip()` and `get_user_agent()` implementations
3. **Test framework**: Generated test case templates and assertion patterns
4. **Cooldown logic**: Suggested the tiered approach with progressive delays
5. **Documentation**: Helped structure security documentation

## What I Changed From AI Output
1. **Validation of thresholds**: Manually verified that 5-attempt threshold is appropriate (balance between security and usability)
2. **Error messages**: Modified to use generic messages rather than revealing attempt count
3. **Lockout duration calculations**: Fine-tuned the cooldown formula to match assignment requirements
4. **Test coverage**: Expanded test suite beyond initial suggestions to cover edge cases like:
   - Expired lockouts being cleared
   - Multiple lockouts in succession
   - Attempt count after successful login
5. **Admin integration**: Manually added read-only display of attempt history in admin panel

## Security Decisions I Made Myself
1. **Account-based, not IP-based**: Chose account-based throttling to avoid locking out legitimate users behind shared networks (NAT, corporate proxies)
2. **Progressive delays vs. hard lockout**: Implemented escalating cooldowns rather than permanently locking accounts—security without breaking user experience
3. **24-hour reset window**: Set attempt counter to reset after 24 hours of inactivity to prevent long-term denial of service
4. **Generic error messages**: Ensured error messages don't reveal whether account exists, preventing user enumeration even during brute-force protection
5. **Audit logging**: Required all attempts be logged to `LoginHistory` with IP/user-agent for security analysis

## Authorship Affirmation
I understand the code and can thoroughly explain:
- The `LoginAttempt` model design and how it tracks state
- The cooldown calculation logic and why progressive delays work better than alternatives
- How the login view integrates brute-force checks without disrupting legitimate authentication
- The test strategy and why each test case validates critical security behavior
- The trade-offs made between security and usability

## Checklist
- [x] I linked the related issue (#36)
- [x] I linked exactly one assignment issue in the Related Issue section
- [x] I started from the active assignment branch for this task
- [x] My pull request targets the exact assignment branch named in the linked issue
- [x] I included a short design note and meaningful validation details
- [x] I disclosed AI assistance used for this submission
- [x] I can explain the key code paths, security decisions, and tests in this PR
- [x] I tested the change locally (all 21 tests pass, all existing tests pass)
- [x] I updated related documentation (PASSWORD_RESET_DOCUMENTATION.md)

---

## Implementation Details

### LoginAttempt Model
The model tracks failed login attempts per account with fields for:
- User reference
- Failed attempt count
- Last attempt timestamp
- Manual lockout flag

### Cooldown Tiers
| Failed Attempts | Lockout Duration |
|---|---|
| 1-4 | No restriction |
| 5-9 | 30 seconds |
| 10-14 | 1 minute |
| 15-19 | 5 minutes |
| 20+ | 15 minutes |

### Test Coverage
21 tests covering:
- Normal login with correct credentials
- Failed login attempts and cooldown enforcement
- Progressive cooldown escalation
- Attempt count reset after successful login
- Attempt count reset after 24 hours
- Account lockout scenarios
- Edge cases and state transitions
