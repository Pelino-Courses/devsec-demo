## Assignment Summary
- Hardened the Django login flow against brute-force abuse with a cache-backed throttle and cooldown response.

## Related Issue
- Closes #36

## Target Assignment Branch
- assignment/harden-login-bruteforce

## Design Note
- Reused the existing Django login flow and wrapped it with a small, auditable throttle instead of adding a complex custom lockout system.
- Chose a hybrid throttle that tracks both account-level failures and IP-level failure bursts so the app can slow focused guessing and broader credential spraying.

## Security Impact
- Repeated failed login attempts now trigger a temporary cooldown response.
- The throttle applies to both repeated guesses against one account and repeated guesses from one IP across many usernames.
- The login error flow still avoids revealing whether a username exists.

## Changes Made
- Added cache-backed login throttle helpers in `justin/security.py`.
- Updated the login view to block requests during cooldown windows and to clear counters after successful authentication.
- Added cooldown messaging to the login template.
- Added tests for successful login, account lockout, IP-based lockout, and counter reset after success.
- Added a short design note at `docs/login-bruteforce-design.md`.

## Validation
- Ran `python manage.py test -v 1`
- Verified repeated failed login attempts return a protective cooldown response
- Verified successful login still works and clears prior failed-attempt counters

## AI Assistance Used
- Used Codex for implementation support, test debugging, and PR-body drafting assistance.

## What AI Helped With
- Structuring a simple Django cache-based throttling approach
- Tightening the brute-force abuse tests around account and IP failure cases
- Drafting the design note and PR summary

## What I Changed From AI Output
- Kept the throttle small and settings-driven instead of introducing a heavier custom middleware or database-backed lockout table.
- Preserved generic invalid-login messaging for normal failures and only showed a cooldown message after the threshold was reached.

## Security Decisions I Made Myself
- Chose a temporary cooldown over a permanent lockout to balance brute-force resistance with usability.
- Used both account and IP tracking so the control handles focused password guessing and multi-username spraying.
- Cleared throttle state after successful authentication so legitimate users can recover cleanly after earlier mistakes.

## Authorship Affirmation
- I understand the submitted code and can explain the abuse model, the throttle design, and the validation steps without assistance.

## Checklist
- [x] I linked the related issue
- [x] I linked exactly one assignment issue in the Related Issue section
- [x] I started from the active assignment branch for this task
- [x] My pull request targets the exact assignment branch named in the linked issue
- [x] I included a short design note and meaningful validation details
- [x] I disclosed any AI assistance used for this submission
- [x] I can explain the key code paths, security decisions, and tests in this PR
- [x] I tested the change locally
- [x] I updated any directly related documentation or configuration, or none was required
