# NYAYA DARSHANA / GYANA — PRODUCTION ROLLBACK PROCEDURE

**Protocol**: Production Incident Recovery & Rapid Rollback  
**Version**: 2.0.0  
**Date**: 2026-08-21  

---

## 1. Rollback Triggers

Initiate immediate rollback if any of the following conditions occur post-deployment:

1. **Safety Violation**: Any incident of false legal citation or statutory hallucination in production queries.
2. **Crash Loop / Startup Failure**: Unhandled startup exception or health check failing for > 60 seconds.
3. **Data Leakage**: Detection of server filesystem paths or unredacted traces in API JSON payloads.
4. **Latency Degradation**: P95 latency on `/api/v1/query` exceeding 500ms under nominal traffic (< 50 req/min).
5. **Corpus Integrity Failure**: `/health` reporting fewer than 1,200 active statutory sections.

---

## 2. Fast Rollback Execution (Render.com Platform)

1. Open the [Render Dashboard](https://dashboard.render.com).
2. Navigate to **Services** -> **gyana-darshan** -> **Events / Deploys**.
3. Locate the previous stable build commit (`Phase 8.2G / Phase 7 Production Approved`).
4. Click **Rollback to this deploy**.
5. Verify application restoration by polling:
   ```bash
   curl -f http://<app-domain>/health
   ```

---

## 3. Container / Git VPS Rollback Execution

If deployed via standard Docker / Git container:

```bash
# 1. Stop current container
docker stop gyana-darshan-app

# 2. Checkout previous tagged release or commit
git fetch --tags
git checkout tags/v1.9.0-prod  # or previous stable SHA

# 3. Rebuild and restart container
docker build -t gyana-darshan:rollback .
docker run -d --name gyana-darshan-app -p 8000:8000 --env-file .env gyana-darshan:rollback

# 4. Confirm health
curl -f http://localhost:8000/health
```

---

## 4. Post-Rollback Diagnostics

1. Pull incident audit logs:
   ```bash
   tail -n 200 logs/nyaya_api_audit.jsonl > rollback_incident_audit.jsonl
   ```
2. Export server error logs from uvicorn/container output.
3. Notify the Principal Legal AI Architect with the incident timestamp and failing query payloads.
