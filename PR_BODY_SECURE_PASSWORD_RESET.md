## Assignment Summary
- Implemented a secure password reset workflow for the UAS using Django's built-in password reset views, tokens, and password validation.

## Related Issue
- Closes #35

## Target Assignment Branch
- assignment/secure-password-reset

## Design Note
- Reused Django's built-in password reset request, confirm, done, and complete views instead of introducing a custom token flow.
- Moved the reset templates into a project-level `templates/registration/` directory so Django reliably uses the secure custom UX instead of its built-in fallback templates.

## Security Impact
- Avoids custom reset-token risks by relying on Django's built-in password reset token handling.
- Uses neutral request messaging to reduce user enumeration risk.
- Preserves Django password validation rules during reset confirmation.
- Handles invalid or expired reset links without exposing unnecessary account information.

## Changes Made
- Added the `justin` UAS app with authentication, role-based profile features, and password reset routes.
- Configured Django to load project-level password reset override templates.
- Added custom password reset request, email, confirm, done, and complete templates.
- Added password reset tests for successful resets, invalid tokens, password validation failures, and safe nonexistent-email behavior.
- Added a short design note at `docs/secure-password-reset-design.md`.

## Validation
- Ran `python manage.py test -v 1`
- Verified the password reset templates resolve from `templates/registration/`
- Confirmed the full password reset flow updates the user's password successfully

## AI Assistance Used
- Used Codex for implementation support, test debugging, and PR-body drafting assistance.

## What AI Helped With
- Identifying why Django was ignoring the custom password reset email templates
- Tightening the password reset tests around Django's canonical confirm flow
- Drafting the design note and PR summary

## What I Changed From AI Output
- Kept the implementation on Django's built-in auth views rather than introducing any custom token logic.
- Adjusted the test expectations to match Django's actual secure behavior for unknown email addresses and reset confirmation redirects.

## Security Decisions I Made Myself
- Chose Django's built-in reset flow so token generation, validation, and password policy stay framework-managed.
- Kept the request confirmation message the same for real and missing accounts to avoid leaking account existence.
- Ensured password reset completion still uses Django's password validators instead of weaker custom checks.

## Authorship Affirmation
- I understand the submitted code and can explain the reset flow, token usage, security controls, and validation steps without assistance.

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
