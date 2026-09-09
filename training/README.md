# Nyaya Darshana Training Workspace

This directory keeps reusable training and dataset-audit source code only. Generated datasets, model adapters, notebooks, reports, and benchmark outputs are intentionally excluded from the product repository.

Training work must follow these rules:

- Keep legal datasets and model artifacts in private storage, not Git.
- Run dataset fact audits and split-leakage checks before any training job.
- Compare a fine-tuned adapter against the current retrieval-grounded baseline before considering it for use.
- Do not connect an adapter to production unless it passes the legal gates and the result is externally reviewed under `docs/operations/LEGAL_VALIDATION_PROTOCOL.md`.
- Do not publish training accuracy as a product claim without a preserved external reviewer ledger.

The runtime application does not require these training artifacts. Nyaya Darshana's production legal answers continue to use the configured provider, deterministic retrieval, claim checks, and human-review guidance.
