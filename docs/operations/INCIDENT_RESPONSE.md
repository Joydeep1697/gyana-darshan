# Incident Response

## Severity

- **SEV-1:** confirmed cross-tenant disclosure, credential compromise, destructive data loss, or total production outage.
- **SEV-2:** sustained AI unavailability, broken authentication, major incorrect-citation regression, or partial data unavailability.
- **SEV-3:** isolated workflow failure with a safe workaround.

## Response

1. Assign an incident lead and open a timestamped incident record.
2. Contain the problem: disable the affected route or integration, revoke compromised access, or roll back the release. Preserve evidence.
3. Use request IDs, organization audit events, hosting logs, provider state, and deployment history. Keep document/query contents redacted unless explicitly required and authorized.
4. Recover using the smallest verified action. Validate tenant isolation, authentication, persistence, and grounding before reopening traffic.
5. Notify affected customers and authorities when contractual or legal obligations require it. Obtain appropriate legal advice; this document does not define notification law.
6. Write a blameless post-incident review with root cause, impact, timeline, corrective actions, owners, and deadlines. Add regression tests.

Never delete logs, rotate away evidence, or restore a database over current state before preserving a forensic copy.
