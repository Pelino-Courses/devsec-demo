## Assignment Summary
- Added structured audit logging for authentication and privilege-sensitive events in the UAS.

## Related Issue
- Closes #325

## Target Assignment Branch
- assignment/add-auth-audit-logging

## Design Note
- Added one small reusable audit logger so auth and privilege events can be logged consistently without scattering ad hoc log formatting across the app.
- Wrapped password reset request and confirmation in small auth-view subclasses so reset events are logged cleanly alongside the function-based auth flows.

## Security Impact
- Security-relevant auth events now leave an audit trail for review and debugging.
- The logs include useful context such as actor, target, outcome, and client IP.
- Raw passwords and other secrets are never written to the logs.

## Changes Made
- Added reusable audit logging helpers in `justin/audit.py`.
- Logged registration, login success/failure, logout, password change, password reset request/completion, and role changes.
- Added tests that capture and validate audit log output.
- Added a short design note at `docs/auth-audit-logging-design.md`.

## Validation
- Ran `python manage.py test -v 1`
- Verified login failure logs are emitted without raw passwords
- Verified registration, password reset request, and role changes generate audit records

## AI Assistance Used
- Used Codex for implementation support, test debugging, and PR-body drafting assistance.

## What AI Helped With
- Structuring the reusable audit logger and password-reset logging hooks
- Designing log-capture tests around Django's logging system
- Drafting the design note and PR summary

## What I Changed From AI Output
- Kept the logging focused on security-relevant events instead of broad request logging.
- Chose a minimal structured payload that is useful for review without pulling in sensitive or noisy fields.

## Security Decisions I Made Myself
- Avoided logging raw passwords or form bodies entirely.
- Logged actor, target, outcome, and client IP because those fields support incident review without over-collecting.
- Included blocked or invalid role-change attempts because they are security-relevant, not just successful changes.

## Authorship Affirmation
- I understand the submitted code and can explain what is logged, what is intentionally excluded, and how the validation works without assistance.

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
