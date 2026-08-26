# Access and Security Operations

## Workspace roles

- `OWNER`: permanent organization owner; manages members, policy, and all workspace content.
- `ADMIN`: manages non-owner members, retention policy, audit records, and content.
- `MEMBER`: creates and changes workspace content.
- `VIEWER`: reads and exports workspace content but cannot mutate it.

Clients select a workspace using the `X-Organization-ID` header. Omitting it selects the account's private workspace. Every server-side resource lookup remains scoped to a verified membership; UI hiding is never treated as authorization.

Adding a member requires an existing verified account. Owner roles cannot be assigned or removed through the member endpoints, preventing accidental orphaning or ownership escalation.

## Production access

Use individual accounts, MFA where supported, least privilege, and time-bound elevation. Review organization audit events and infrastructure access quarterly. Revoke access immediately during offboarding.

Secrets belong only in the deployment secret store. Query text remains excluded from logs by default. Backups contain customer data and require encryption, restricted access, retention, and restoration auditing.

## Known boundary

SQLite plus a single persistent disk is suitable for controlled early deployments, not horizontal multi-region operation. Before enterprise scale, migrate both application databases and job coordination to managed transactional services with tested migrations, point-in-time recovery, encryption controls, and per-tenant observability.
