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

## Public Git Credential Exposure

Treat any real credential committed to a public repository, including a deleted file or older commit, as compromised.

1. Preserve evidence without copying secret values into tickets, chat, logs, or new commits.
2. Rotate the affected provider keys first. For payment keys, rotate the full live key pair and review provider transaction logs before restoring service.
3. Replace deployment, CI, and local operational secret-store values with the rotated keys.
4. Run the repository preflight and a secret scan against the current tree before rewriting history.
5. Rewrite public git history with `git filter-repo` or an equivalent reviewed tool, removing the secret-bearing file paths and commit-message fragments.
6. Force-push only after rotation is complete, all collaborators are warned, and protected-branch requirements are temporarily handled by the repository owner.
7. Invalidate forks, caches, deployment artifacts, and local clones where possible; assume bots may already have copied the original commits.
8. Record the incident timeline, rotated key IDs, transaction-log review result, force-push commit, and follow-up controls. Do not record secret values.
