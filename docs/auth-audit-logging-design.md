# Authentication Audit Logging Design Note

This implementation adds app-level audit logging for security-relevant auth and
privilege events. The goal is to support review and incident analysis without
logging secrets.

Events logged:

- registration
- login success and failure
- logout
- password reset request
- password reset completion
- password changes
- role changes, including blocked or invalid attempts

Privacy and logging choices:

- raw passwords are never logged
- logs record usernames, user IDs, outcomes, and a client IP for correlation
- role-change logs include the old and new role values
- password reset request logs record whether an account existed internally, but
  that information is not shown to the user
