# Retrieval Wiring

## Architecture

```text
Authenticated user
  -> get_workspace_context()
  -> organization.id (personal-... or org-...)
  -> POST /api/retrieval/search
  -> retrieval.search.search(query, tenant_id)
  -> retrieval.indexer.load_tenant_index(tenant_id)
       -> corpus_integrity/bns/**/*.md
       -> corpus_integrity/bnss/**/*.md
       -> corpus_integrity/bsa/**/*.md
          fetched_with=jsonl_fallback
          provenance_verified=false
       -> corpus_integrity/egazette/**/*.md|html
       -> corpus_integrity/prs/**/*.md|html
          fetched_with=needs_human_action or robots_blocked
          provenance_verified=false
       -> app/storage/vault/{tenant_id}/**/*.pdf|md|txt
          fetched_with=live_upload
          provenance_verified=true
  -> top chunks with provenance badge metadata
```

## Tenant Isolation

Retrieval never accepts `tenant_id` from the browser. The route uses the same
workspace dependency as Vault and reads `workspace["organization"]["id"]`.
The indexer only walks `app/storage/vault/{tenant_id}` for that id. Files in
`default_tenant`, another `personal-...` workspace, or another `org-...`
workspace are not included in the active tenant index.

The BNS, BNSS, and BSA fallback files are public statutory corpus and are
included for each tenant search, but they are always marked:

```text
fetched_with=jsonl_fallback
provenance_verified=false
```

That flag is deliberate: India Code live browser verification was blocked, so
the UI must show the red fallback badge and must not imply live verification.

eGazette and PRS evidence records are indexed as manual-action evidence until
`app/ingestion/browser_check_egazette.py` or
`app/ingestion/browser_check_prs.py` refreshes the HTML/PNG proof and a human
reviewer verifies provenance. They should display as yellow
`needs_human_action` badges, not verified legal authority.

## Human Review Loop

```text
eCourts browser check detects CAPTCHA
  -> create [Human Action Required] task in active org
  -> GET /api/vault/ops/human-review-pending
  -> UI opens eCourts/evidence
  -> operator uploads public judgment PDF
  -> POST /api/vault/ops/human-review/{task_id}/resolve
       -> save app/storage/vault/{tenant_id}/ecourts/{case}.pdf
       -> create Vault document
       -> mark task done
       -> write ingestion_log.jsonl
       -> re-index tenant files
```

No CAPTCHA solving, robots bypassing, or unverifiable provenance promotion is
performed. Human-uploaded PDFs are searchable as `live_upload`; source review
still remains a legal/compliance responsibility outside the automated crawler.
