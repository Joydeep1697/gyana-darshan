# Nyaya Darshana production release checklist

A release is approved only when every applicable item has current evidence.

## Source and build

- [ ] Confirm `.env`, browser profiles, SQLite databases, private uploads, and excluded download metadata are absent from the release commit and container context.
- [ ] Run `python scripts/release_preflight.py --repository-only` successfully.
- [ ] Install production dependencies and run `pip check`.
- [ ] Require the GitHub Actions **Release verification** workflow to pass for the release commit.
- [ ] Build the Docker image or complete the Render build without bypassing preflight checks.

## Production configuration

- [ ] Set `ENVIRONMENT=production` and `LLM_PROVIDER=nvidia`.
- [ ] Generate independent random values of at least 32 characters for `NYAYA_API_KEY` and `NYAYA_JWT_SECRET`.
- [ ] Store a freshly rotated `NVIDIA_API_KEY` only in the hosting platform secret manager.
- [ ] Set `ALLOWED_ORIGINS` to exact HTTPS frontend origins; wildcards and HTTP are forbidden.
- [ ] Either provide both rotated Razorpay credentials or leave both unset.
- [ ] Provision persistent storage for database, uploads, and logs; Render disks require a paid eligible service.
- [ ] Run `python scripts/release_preflight.py --environment-only` in production.
- [ ] Keep `NYAYA_LOG_QUERY_TEXT=false` unless a reviewed retention policy authorizes logging legal questions.

## Live verification

- [ ] Confirm `/health` succeeds through the public HTTPS deployment.
- [ ] Confirm anonymous or invalid API keys cannot access protected endpoints.
- [ ] Confirm account creation, sign-in, and cross-user authorization controls.
- [ ] Submit a legal question and verify a real NVIDIA-generated response with traceable statutory citations.
- [ ] Upload a valid PDF, reject malformed uploads, and confirm documents survive a service restart.
- [ ] If billing is enabled, complete a Razorpay test-mode payment and verify signature rejection before switching to live keys.
- [ ] Check logs for absence of secrets, raw legal queries, internal paths, and stack traces.
- [ ] Verify domain/TLS, backups, restore procedure, incident ownership, and rollback instructions.

## Approval

Record the deployed commit, workflow URL, deployment URL, verifier, date, and evidence for each live check. Repository checks alone do not establish production readiness.
