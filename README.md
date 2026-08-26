# Nyaya Darshana

Source-grounded Indian legal intelligence for statutory research, transition analysis, and private PDF work.

Nyaya Darshana retrieves relevant statutory provisions before generation, separates substantive, procedural, and evidence-law timelines, and checks material legal claims against the retrieved evidence. It is a research-support product, not a substitute for professional legal advice.

## What is implemented

- Authenticated, persistent legal consultations with source cards and verification status.
- Transition-aware analysis across the IPC/BNS, CrPC/BNSS, and IEA/BSA commencement boundaries.
- A claim-verification firewall that blocks or corrects unsupported material assertions.
- A tenant-isolated Knowledge Vault for PDF upload, classification, metadata search, and cached summaries.
- Email/password authentication, optional Google OAuth, quota reporting, and optional Razorpay access activation.
- Production health/readiness checks, explicit CORS policy, secret validation, persistent SQLite storage, and a non-root Docker image.

The repository also contains research and experimental training material. No fine-tuned production model is claimed unless its weights and evaluation results are independently verified.

## Run locally

Use Python 3.11 or newer. There is no root-level `app.py`; start the product with `run.py` or Uvicorn.

```powershell
cd "D:\Gyana Darshan"
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API documentation is available at `/docs`, the liveness check at `/health`, and the readiness check at `/ready`.

At minimum, configure these values in `.env` for live generated answers:

```dotenv
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key
NYAYA_JWT_SECRET=generate-a-unique-secret-with-at-least-32-characters
```

Tesseract is optional and is used only when OCR is available for scanned PDFs.

## Architecture

| Layer | Responsibility |
|---|---|
| `app/static/index.html` | Responsive public site and authenticated workspace |
| `api/auth` | Accounts, JWT sessions, quotas, and optional Google OAuth |
| `api/conversations` | Persistent consultations, evidence records, and ownership checks |
| `retrieval` | Deterministic statutory retrieval and transition routing |
| `verification` | Claim grounding and answer enforcement |
| `app/routers/vault.py` | Tenant-isolated PDF upload, metadata search, summaries, and deletion |
| `corpus_integrity` | Runtime statutory text and cross-mapping data |
| `database` / `app/database.py` | SQLite persistence for identity, conversations, evidence, billing, and Vault metadata |

The consultation engine uses the compact statutory corpus in `corpus_integrity`; it does not require FAISS, PyTorch, or sentence-transformers at runtime. The PDF classifier is retained as a separate local processing module.

## Tests and release checks

```powershell
python scripts/release_preflight.py --repository-only
python -m compileall -q app api database retrieval verification scripts tests
python -m pytest -q tests app/test_app_endpoints.py
```

GitHub Actions runs the same release gates on pull requests and pushes to `main`.

## Production deployment

`render.yaml` deploys the checked-in Dockerfile and attaches a 5 GB persistent disk at `/var/data`. A Render plan that supports persistent disks is required if conversations and uploads must survive restarts.

The Render Blueprint generates `NYAYA_API_KEY` and `NYAYA_JWT_SECRET`. Supply these values during deployment:

- `NVIDIA_API_KEY`: required for live generated legal answers.
- `ALLOWED_ORIGINS`: one or more explicit HTTPS origins, comma-separated.

Optional integrations are configured directly in the production environment:

- Google sign-in requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and an HTTPS `GOOGLE_REDIRECT_URI` ending in `/api/auth/google/callback`.
- Razorpay requires both `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. Leave both unset to disable checkout.

Production startup fails closed when required secrets are absent, origins are insecure, or an optional integration is only partially configured. The container runs as an unprivileged user and checks `/health` automatically.

## Product truth

Nyaya Darshana presents retrieved sources, corpus versions, and verification results. It does not expose private chain-of-thought, invent customer activity, or imply that a procedural defect automatically determines innocence or acquittal without supporting authority.

## License

Application code and project-specific legal datasets are proprietary. Third-party models and source materials remain subject to their respective licences and terms.
