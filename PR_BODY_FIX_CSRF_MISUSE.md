## Assignment Summary
- Fixed CSRF misuse in the custom logout workflow by changing it from a GET-triggered state change to a CSRF-protected POST flow.

## Related Issue
- Closes #369

## Target Assignment Branch
- assignment/fix-csrf-misuse

## Design Note
- Reviewed the custom state-changing flows in the UAS and focused on logout because it was mutating session state through a plain GET link.
- Switched logout controls to standard Django POST forms with CSRF tokens instead of adding any custom CSRF workaround.

## Security Impact
- Logout is no longer triggerable by a cross-site GET request.
- State-changing logout requests now require a valid CSRF token.
- The fix uses Django's built-in CSRF protection rather than bypasses or exemptions.

## Changes Made
- Marked the logout view as POST-only.
- Replaced logout links in authenticated templates with CSRF-protected forms.
- Added tests proving GET logout is rejected, POST without a token fails, and valid CSRF-protected POST logout still works.
- Added a short design note at `docs/csrf-misuse-design.md`.

## Validation
- Ran `python manage.py test -v 1`
- Verified logout through GET no longer changes session state
- Verified logout POST without a CSRF token is rejected with `403`
- Verified logout POST with a valid CSRF token succeeds

## AI Assistance Used
- Used Codex for implementation support, test debugging, and PR-body drafting assistance.

## What AI Helped With
- Identifying the most concrete CSRF misuse in the custom UAS workflows
- Structuring the logout CSRF enforcement tests
- Drafting the design note and PR summary

## What I Changed From AI Output
- Kept the fix on Django's standard POST-plus-CSRF pattern instead of introducing custom AJAX token handling where it was not needed.
- Focused the change on the actual unsafe state-changing GET workflow rather than broad unrelated refactors.

## Security Decisions I Made Myself
- Treated logout as a state-changing action that must not be reachable by GET.
- Used Django's default CSRF mechanism rather than exemptions or custom headers-only logic.
- Added enforcement tests so the protection is verified, not just assumed.

## Authorship Affirmation
- I understand the submitted code and can explain the CSRF risk, the logout fix, and the validation steps without assistance.

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
