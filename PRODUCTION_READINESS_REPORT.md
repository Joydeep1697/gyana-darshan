# Nyaya Darshana production readiness report

## Release verdict

**Deployment infrastructure is prepared; production approval remains blocked until real hosting, rotated credentials, CI, and live end-to-end checks succeed.** This report does not certify historical benchmark values, unpublished test counts, provider availability, or payment processing.

Benchmark numbers in this repository are self-reported by project-owned scripts unless a report explicitly cites an external, independent auditor and reproducible validation package.

## Release controls

| Area | Implemented control | Required independent evidence |
| --- | --- | --- |
| Secret management | Secrets excluded from Git/container contexts; Render generates application signing secrets. | Verify the release commit and platform secret configuration. |
| Production startup | Standard-library preflight rejects short secrets, insecure origins, missing NVIDIA credentials, and partial Razorpay configuration. | Run preflight in the real deployed environment. |
| Container hardening | Non-root runtime, HTTP health check, bounded workers, persistent data directories. | Build image and restart with mounted storage. |
| Render deployment | Dynamic port, build/start gates, generated secrets, persistent disk. | Provision an eligible paid Render service. |
| Dependencies | Direct dependencies have lower and upper bounds; CI runs `pip check`. | Retain the successful CI run and review transitive dependencies. |
| Automated verification | GitHub Actions runs statutory, deployment, authentication, authorization, and application regressions. | Confirm workflow passes for the production commit. |
| Privacy | Query-text logging disabled in production configuration by default. | Inspect deployed logs and retention controls. |
| Payments | Billing credentials supplied together; no false payment success. | Verify test-mode payment before live transactions. |

## External launch prerequisites

1. Rotate credentials previously disclosed outside a secret manager.
2. Add the rotated NVIDIA key and exact HTTPS origins to the deployment platform.
3. Provision paid persistent hosting and configure the public domain/TLS.
4. Configure Razorpay only if billing is required and verify signatures in test mode.
5. Complete `RELEASE_CHECKLIST.md` and preserve current evidence.

This report guarantees neither legal accuracy nor completed deployment.
