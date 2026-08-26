# Nyaya Darshana Operations Runbook

This runbook is the operational source of truth. It is written so an engineer other than the founder can deploy, monitor, recover, and support the service.

## Ownership

Assign named primary and backup owners for application operations, security incidents, legal-content releases, billing, and customer support. Never leave production credentials in personal accounts; use the hosting provider's team access and least-privilege roles.

## Daily checks

1. Confirm `/health` returns HTTP 200 and `/ready` is `READY` or an understood AI-only degraded state.
2. As an application administrator, inspect `/api/operations/status` for AI availability, failed Vault documents, storage growth, and recent audit volume.
3. Review provider and hosting error logs without enabling query-text logging.
4. Confirm the most recent automated backup completed and passed validation.

## Deployment

1. Create a tested backup before migrations or releases.
2. Run `python scripts/release_preflight.py --repository-only` and the complete test command from `README.md`.
3. Deploy the immutable commit through the checked-in `Dockerfile` and `render.yaml`.
4. Verify `/health`, `/ready`, login, one private consultation, one source card, and one owned Vault document.
5. Record the commit, operator, time, checks, and any migration result in the change ticket.

Rollback follows [ROLLBACK_PROCEDURE.md](../../ROLLBACK_PROCEDURE.md). Restore data only when forward recovery is impossible.

## Backups and recovery

Create a consistent online snapshot:

```powershell
.venv\Scripts\python.exe scripts\backup_data.py D:\secure-backups\nyaya-2026-08-27.zip
.venv\Scripts\python.exe scripts\restore_data.py D:\secure-backups\nyaya-2026-08-27.zip --validate-only
```

Store backups in encrypted, access-controlled storage outside the application disk. The ZIP itself is not encrypted. Define and test the business RPO and RTO; until that exercise is completed, no recovery-time guarantee is claimed.

To restore, stop every application instance first, take a copy of the current data directory, validate the archive, then run:

```powershell
.venv\Scripts\python.exe scripts\restore_data.py D:\secure-backups\nyaya-2026-08-27.zip --confirm RESTORE_NYAYA_DATA
```

Start one instance, run readiness and user-flow checks, and only then restore normal traffic.

## Retention

Organization owners and administrators set a policy through `PUT /api/organizations/{id}/retention`. A null policy retains data until user deletion. Thirty days is the minimum configured period.

Preview before every enforcement run:

```powershell
.venv\Scripts\python.exe scripts\enforce_retention.py
.venv\Scripts\python.exe scripts\enforce_retention.py --apply
```

Schedule the apply command once daily. Backups have a separate lifecycle and must be expired using the backup-storage policy.

## Legal-content updates

1. Record the authoritative source, publication date, effective date, and checksum.
2. Update structured data and mappings; never edit generated answers to conceal retrieval defects.
3. Run statutory, transition, citation, and adversarial regression suites.
4. Review failures with a qualified legal reviewer where interpretation is involved.
5. Update the internal source version, deploy, and retain the prior release for rollback.

## Customer support

Collect request IDs, timestamps, workspace ID, endpoint, and visible error text. Do not request passwords, tokens, private documents, or full legal narratives through insecure channels. Escalate authorization, data-loss, citation-integrity, and billing issues immediately.

## Offboarding

Remove the operator from hosting, GitHub, provider, domain, payment, monitoring, and backup systems; rotate credentials they could access; revoke application sessions; and transfer open incidents and change records.
