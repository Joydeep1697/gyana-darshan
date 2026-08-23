# NYAYA DARSHAN — PRODUCTION RELEASE CHECKLIST

**Release Version**: 2.0.0  
**Target Environment**: Production (Render.com / Containerized VPS)  
**Date**: 2026-08-21  

---

## 1. Pre-Deployment Configuration Verification

- [x] **Secrets Removed from Source Control**: `.env` is listed in `.gitignore` and removed from git index.
- [x] **Sample Configuration Scrubbed**: `.env.example` contains only sanitized placeholder values.
- [x] **Docker Build Sanitized**: `.dockerignore` prevents `.env`, test code, and dev scratch files from being copied.
- [x] **Hot-Reload Disabled**: `run.py` checks `RELOAD_ON_CHANGE=1` before enabling reload (disabled by default in production).
- [x] **Uvicorn Start Command Configured**: `render.yaml` sets `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`.
- [x] **Health Check Sanitized**: `/health` endpoints return clean status, loaded section count, and no misleading benchmark claims.
- [x] **CORS Configuration Verified**: Startup warning is logged if `ALLOWED_ORIGINS` is missing or wildcard in production.

---

## 2. Environment Variables Required on Production Host

The following environment variables **must** be populated in the production dashboard (e.g. Render Environment Settings / Docker Compose):

| Variable | Description | Example / Required Format | Mandatory? |
|---|---|---|:---:|
| `HOST` | Bind host address | `0.0.0.0` | Yes |
| `PORT` | Bind port number | `8000` | Yes |
| `LLM_PROVIDER` | Active LLM inference provider | `nvidia` | Yes |
| `NVIDIA_API_KEY` | NVIDIA Cloud NIM API key | `nvapi-...` | Yes (if `LLM_PROVIDER=nvidia`) |
| `NVIDIA_LLM_MODEL` | Statutory reasoning model | `nvidia/llama-3.3-nemotron-super-49b-v1` | Yes |
| `NYAYA_API_KEY` | Master API Key for endpoint auth | Strong random string (≥ 32 chars) | Yes (for protected API) |
| `NYAYA_JWT_SECRET` | Session token signing secret | Unique random string (≥ 32 chars) | Yes |
| `ALLOWED_ORIGINS` | Comma-delimited CORS origins | `https://nyayadarshana.com,https://app.nyayadarshana.com` | Yes |
| `RAZORPAY_KEY_ID` | Payment gateway Key ID | `rzp_live_...` or `rzp_test_...` | Optional (Billing) |
| `RAZORPAY_KEY_SECRET` | Payment gateway Key Secret | Razorpay secret string | Optional (Billing) |

---

## 3. Post-Deployment Verification Smoke Steps

Immediately after container deployment:

1. **Verify Health Endpoint**:
   ```bash
   curl -s http://<host>:8000/health | grep '"status":"HEALTHY"'
   ```
2. **Verify Database Initialization**:
   Confirm that tables `users`, `conversations`, `messages`, `vault_documents` exist and SQLite is operating in WAL mode.
3. **Verify Grounded Retrieval API**:
   ```bash
   curl -s -X POST http://<host>:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <your configured NYAYA_API_KEY>" \
     -d '{"query": "Convert IPC 302 to BNS", "top_k": 3}' | grep '103(1)'
   ```
4. **Verify Path Exposure Sanitization**:
   Confirm response contains 0 internal drive paths or system trace tokens.
5. **Verify Rate Limiting Headers**:
   Confirm response headers include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
