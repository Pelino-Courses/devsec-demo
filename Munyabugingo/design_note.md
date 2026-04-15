# Audit Logging Design Note

## What is Logged and Why

The audit logging implementation in this django application tracks critical, security-relevant authentication and authorization events to provide strong observability and accountability. The following events are explicitly logged:

- **USER_REGISTRATION**: Logged when a new account is created. This allows administrators to track account provisioning, identify potential botnets or coordinated sign-up abuse, and audit the creation of potentially privileged accounts over time.
- **LOGIN_SUCCESS** & **LOGIN_FAILURE**: Success tracking identifies normal usage patterns and helps pinpoint compromised accounts in the event of an anomaly. Failure tracking is essential for detecting brute-force or credential stuffing attacks. (Lockout states triggered by repeated failures are also logged).
- **LOGOUT**: Proper session termination is explicitly recorded to trace the entire lifecycle of an authenticated session and help distinguish between concurrent sessions and abandoned sessions.
- **PASSWORD_CHANGE**, **PASSWORD_RESET_REQUEST**, & **PASSWORD_RESET_COMPLETE**: Password modification flows are highly sensitive. Logging these actions ensures that account takeovers leveraging the password recovery mechanism are traceable and detectable.
- **PRIVILEGE_UPGRADE** & **PRIVILEGE_DOWNGRADE** (Role / permission changes): Whenever a user’s group association changes (e.g., being added to the `Privileged Users` pool), it is immediately logged. This ensures no hidden escalation of privilege occurs without leaving a paper trail.
- **PROFILE_UPDATE**: Account detail modifications are tracked to deter malicious alteration of profile metadata (like an attacker attempting lateral movement or social engineering).
  
All these incidents include contextual identifiers such as timestamp, a standardized status label (`SUCCESS`, `FAILURE`, or `BLOCKED`), the targeted `user` (or `ANONYMOUS`), the client's `ip`, and sanitized `metadata`. 

## Privacy Decisions and Data Sanitization

To ensure user privacy and adhere to data compliance best practices (e.g., GDPR, CCPA, minimal data retention principles), audit logs *must never* be treated as dumping grounds for raw data.

1. **No Passwords in Logs**: The central `utils.log_audit_event` mechanism implements an explicit filter that strips out any metadata dictionary keys containing the string `password` (case-insensitive) out of bounds. Raw credentials or tokens are fundamentally excluded.
2. **Minimal PII Exposure**: The logger maps the context exclusively to identifiable and necessary technical indices (Username and IP addresses). Deep personal data associated with the user profile remains untouched in the audit trail unless uniquely necessary. 
3. **Dedicated Application-Level Audit Logs**: As opposed to mingling these alerts into raw HTTP or database-level general application logs (noise), they are specifically formatted with an `[AUDIT]` tag and processed uniquely through a configured logging handle (`Munyabugingo.audit`). This fulfills the objective of "not being noisy" while allowing easy shipping to external SIEM/Observability systems.

## Why Observability is Part of Secure Engineering

Observability guarantees that software does not become a “black box” after deployment. In secure software engineering, preventative controls (like authentication systems, MFA, and strong encryption) are critical but ultimately insufficient; determined attackers will inevitably find ways to compromise networks, orchestrate zero-days, or exploit complex logical flaws over time.

- Observability acts as a vital **detective control**. A security team cannot secure an environment they cannot see. Rapid and reliable detection capabilities drastically lower the "Time to Detect" and "Time to Respond." 
- It bridges the crucial gap in **accountability and non-repudiation**, enabling incident responders to retroactively trace how an attacker exploited the system, what blast radius was achieved (e.g. pivoting through an unlocked account), and if the attack remains an active compromise. Without it, verifying the security posture is a purely theoretical exercise.
