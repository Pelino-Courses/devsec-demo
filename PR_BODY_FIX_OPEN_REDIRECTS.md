## Assignment Summary
- Fixed unsafe redirect handling in the authentication workflow by validating `next` targets before redirecting after login, registration, or logout.

## Related Issue
- Closes #370

## Target Assignment Branch
- assignment/fix-open-redirects

## Design Note
- Added a small redirect-validation helper instead of scattering ad hoc redirect checks through the auth views.
- Reused Django's safe redirect utilities so internal navigation still works while external destinations are dropped.

## Security Impact
- Untrusted external redirect targets are no longer honored in auth workflows.
- Legitimate internal `next` navigation is preserved for login and registration.
- Custom protected-route redirects now use Django's `redirect_to_login` helper to keep redirect generation consistent and safe.

## Changes Made
- Added safe redirect validation with `url_has_allowed_host_and_scheme`.
- Updated login, registration, and logout flows to use validated redirect targets.
- Updated custom auth-required decorators to preserve safe internal `next` values.
- Added tests for safe internal redirects, rejected external redirects, and protected-route login redirects.
- Added a short design note at `docs/open-redirect-design.md`.

## Validation
- Ran `python manage.py test -v 1`
- Verified safe internal `next` values still redirect correctly
- Verified external redirect targets fall back to safe internal defaults
- Verified protected routes still send users to login with a safe internal `next`

## AI Assistance Used
- Used Codex for implementation support, test debugging, and PR-body drafting assistance.

## What AI Helped With
- Structuring a small safe-redirect helper around Django's utilities
- Tightening tests around internal and external `next` targets
- Drafting the design note and PR summary

## What I Changed From AI Output
- Kept the implementation narrow and centered on Django's built-in redirect validation utilities.
- Preserved the existing app flow by using safe fallbacks instead of changing unrelated navigation behavior.

## Security Decisions I Made Myself
- Chose Django's allowed-host and scheme validation instead of custom URL parsing.
- Rejected external `next` values by falling back to predictable internal destinations.
- Preserved legitimate internal `next` behavior so the fix improves security without breaking normal navigation.

## Authorship Affirmation
- I understand the submitted code and can explain the redirect risk, the validation logic, and the tests without assistance.

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
