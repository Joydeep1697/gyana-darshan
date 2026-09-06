# Agent Failure Log

## Cycle 9 — saved verdicts and alternate presentations bypassed truth-state protections

### Problem
Reloading history lost review guidance and displayed old verified labels. Legacy chat and public provenance fields implied checks that had not occurred.

### Evidence
Ten new baseline checks failed: five saved statuses, four provenance cases across both public entry points, and legacy chat. The browser also showed source-card "Supports" wording and public copy claiming comprehensive material-claim verification.

### Hypothesis
Creation-time verdicts were treated as a complete solution, while history copied stored labels directly, omitted review metadata, and alternate presentation paths independently invented verification claims.

### Attempt
Earlier cycles guarded generated conclusions but retained the existing history schemas, chat response shape, fixed chat-stage timings, unconditional `provenance_verified=True`, and older UI wording.

### Result
Review warnings disappeared after history reload, old unsupported certainty returned, and provenance was certified even with no retrieved source.

### Why it failed
Every read and display boundary must distinguish recorded metadata from currently established support. A completed computation is not proof of legal validity or provenance.

### New information learned
Saved records retain excerpt summaries, not independent proposition/provenance proof. They can be projected conservatively without a data migration or rewriting historical audit values. Existing source associations justify "Cited by", not "Supports".

### Do not repeat
Do not certify historical labels by copying them into current status, drop review guidance during serialization, invent stage timings, or claim source provenance from a populated citation card. Do not overwrite unrelated concurrent page changes when repairing asset URLs.

### Correct resolution
Added conservative historical verdict projection, retained `recorded_grounding_status`, and restored review metadata in historical schemas. Tenant denial and unchanged stored values are tested. Legacy chat uses the shared gate and a measured total duration. Provenance certification remains false pending a verifiable chain. UI guards old/unknown labels, preserves input/clarification states, labels citations honestly, and corrects public capability overclaims.

### Verification
Twelve new checks pass; targeted suite: 29 passed. Full CI-equivalent suite: 181 passed, 3 subtests passed, one dependency deprecation warning. Desktop and 390x844 mobile QA used a separate synthetic database and real sign-in/history requests. Review status and source disclosure remained readable with no mobile horizontal overflow. A concurrent change after the full run replaced static asset references with relative paths; the branding contract failed and server logs confirmed 404s. Restored the six asset references, preserved other visual edits, and reran frontend contracts (6 passed). All four logo assets then loaded. Python compilation, JavaScript syntax, and repository preflight passed. Isolated QA server stopped and viewport reset. No live-provider generation, export rendering, or new restart-persistence certification is claimed.

### Relevant files
- `app/intelligence/grounding_verdict.py`, `app/intelligence/human_review.py`
- `api/conversations/router.py`, `api/conversations/schemas.py`
- `app/routers/chat.py`, `app/models.py`, `app/main.py`, `api/main.py`
- `app/static/index.html`, `tests/test_truth_state_presentation.py`
- `tests/test_frontend_product_contract.py`

## Cycle 8 — generator equality and firewall pass were mistaken for proposition proof

### Problem
A generated conclusion could be labelled fully verified without independent proposition evidence, suppressing human-review guidance.

### Evidence
Five synthetic false claims paired with a real citation and accepted source metadata all received GROUNDED_AND_VERIFIED when the supplied template matched the answer. Their evidence-level proposition verdicts remained INSUFFICIENT_EVIDENCE. All three API callers reproduced false verification with upstream generation/firewall acceptance mocked. Eleven new regression assertions failed before the fix.

### Hypothesis
The verdict trusted deterministic generator equality rather than independent proof; an alternate API entry point trusted firewall success alone. The review recommender trusted the top-level label even when its claims were explicitly unsupported.

### Attempt
Earlier cycles classified exact template output with retrieved citations as audited, while the source verifier intentionally did not establish proposition entailment. Citation coverage was also inferred from claim-support labels or context text instead of retrieved claim/citation records.

### Result
False propositions, including a compound sentence containing a genuine quote, could be promoted to fully supported conclusions. The review guard accepted an inconsistent verified label.

### Why it failed
Generator identity, source identity, quote matching, and firewall acceptance do not establish independent legal proposition proof. Separate entry points had inconsistent trust gates.

### New information learned
No independent entailment verifier currently exists. Safe abstention is necessary across all generated conclusions, including templates. The alternate `api.main` server is covered by existing application tests and must use the same gate.

### Do not repeat
Do not regenerate an answer to verify itself, treat a firewall pass as full grounding, infer proposition support from citation presence, or suppress review from a legacy status string alone.

### Correct resolution
Cycle 8 removed template promotion and redundant regeneration from verifier callers. Claims with retrieved records remain INSUFFICIENT_EVIDENCE; missing citations remain UNSUPPORTED. Citation coverage uses actual claim/citation identity records. Both public API entry points and the consultation route share the fail-closed verdict; human review remains required pending independent proof. New consultation history stores the same insufficient-evidence status. Eleven new tests passed after the first implementation, and 45 targeted grounding/pinpoint/retrieval tests passed. Existing tests that explicitly certified template equality or allowed an unsupported verified label to suppress review were corrected to assert the stronger invariant. No failed implementation retry or destructive rollback occurred.

### Relevant files
- `app/intelligence/grounding_verdict.py`
- `app/intelligence/human_review.py`
- `app/main.py`
- `api/main.py`
- `api/conversations/router.py`
- `tests/test_independent_proposition_gate.py`

### Remaining limits
Independent proposition verification is still absent; this cycle implements safe abstention, not an entailment model. Existing stored verdicts are not retroactively reverified. Review metadata on reloaded history, the legacy chat route's displayed verification claims, and unconditional provenance flags remain queued for a separate truthfulness audit. Final Cycle 8 verification: 169 full-suite tests and 3 subtests passed, one dependency deprecation warning; repository preflight, compilation, and diff checks passed. No live-provider, rendered-browser, restart-persistence, or deployment verification was performed.

## Cycle 7 — previously accepted pinpoint verification allowed false grounding

### Problem
The Cycle 4 verifier could label a wrong statutory pinpoint fully verified.

### Evidence
All 14 existing grounding tests passed. Nine new synthetic attacks received GROUNDED_AND_VERIFIED: quotes from other subsections, postfix/long-name aliases bypassing pinpoint checks, cross-reference-only labels, repeated missing pinpoints, nested nonexistent clauses, and another section's label. Two additional provenance/layout assertions failed.

### Hypothesis
Matching a subsection token anywhere and a quote anywhere in the record was being mistaken for evidence at the cited location.

### Attempt
The earlier implementation used a first-match regex, searched the entire source for subsection numbers and quotes separately, and stored only its first 900 characters.

### Result
The old gate accepted all nine false-pinpoint attacks and could store an excerpt omitting the quote it claimed to verify.

### Why it failed
Section identity, subsection presence, and quote presence are distinct checks. They do not establish a shared evidence location. Repeated citations and supported citation aliases also need complete parsing.

### New information learned
The old absent-subsection test could not detect misattribution to an existing subsection. Original source layout must remain available until span boundaries are resolved.

### Do not repeat
Do not validate a pinpoint from an arbitrary `(n)` occurrence, check only the first citation, search the whole section for a subsection quote, or substitute a fixed prefix for the actual span.

### Correct resolution
Cycle 7 resolves every explicit numeric subsection to a unique source span and checks each quote within every referenced span. Nested clauses, ranges, missing labels, and duplicate labels fail closed. The evidence record retains the resolved span. All 17 new tests and the CI-equivalent full suite pass (158 tests, 3 subtests, one dependency deprecation warning). Both public and authenticated APIs reject full verification when upstream generation/firewall acceptance is mocked. No Cycle 7 implementation retry or destructive rollback was needed; the red baseline intentionally reproduced the old defect.

### Relevant files
- `app/intelligence/grounding_verdict.py`
- `tests/test_pincite_scope.py`
- `.agent/STATE.md`

### Remaining limits
This is a bounded statutory-subsection gate, not independent proposition entailment or judgment page/paragraph verification. Live-provider, rendered-browser, and deployment checks were not run in this cycle.

## Backup snapshots remained locked on Windows

### Problem
The backup round-trip test could not remove its temporary snapshot database on Windows.

### Evidence
Cleanup raised `PermissionError [WinError 32]` for the temporary `product.db` after the SQLite backup completed.

### Hypothesis
The SQLite connection context manager committed transactions but did not close the connection handles.

### Attempt
The first snapshot helper used `with sqlite3.connect(...)` for source and target connections.

### Result
The archive was created, but Windows correctly prevented deletion of the still-open temporary database.

### Why it failed
Python's SQLite connection context protocol manages transactions; it does not guarantee connection closure.

### New information learned
Portable backup tooling must explicitly close every SQLite connection before archiving or cleaning temporary files.

### Do not repeat
Do not rely on the SQLite connection context manager alone for resource closure.

### Correct resolution
Wrap source and target connections with `contextlib.closing` and retain the backup round-trip regression test.

### Relevant files
- `scripts/backup_data.py`
- `tests/test_enterprise_operations.py`

## Organization migration indexed columns before upgrading existing tables

### Problem
Existing databases failed during startup with `sqlite3.OperationalError: no such column: organization_id`.

### Evidence
The organization schema worked conceptually for new tables, but `executescript` reached new indexes while the pre-existing `conversations` and `audit_events` tables still lacked the added column.

### Hypothesis
Backward-compatible column additions were being executed after index creation.

### Attempt
The initial schema placed organization indexes directly in the idempotent base DDL.

### Result
Test collection failed before application startup on the existing development database.

### Why it failed
`CREATE TABLE IF NOT EXISTS` does not upgrade an existing table, so its following index referred to a column that had not yet been migrated.

### New information learned
Indexes involving migrated columns must be created only after explicit column detection and migration.

### Do not repeat
Do not place an index for a newly migrated column in base DDL unless all supported existing schemas already contain that column.

### Correct resolution
Move both organization indexes into `init_db()` after their respective `ALTER TABLE` compatibility checks, and verify old and clean database initialization.

### Relevant files
- `database/models.py`
- `database/connection.py`

## Generic transition query returned electronic-FIR-only advice

### Problem
The consultation example “An offence occurred before 1 July 2024, but the FIR came later” returned only BNSS section 173 electronic-FIR advice and omitted substantive and procedural transition analysis.

### Evidence
The reasoning plan contained only `electronic_fir_registration`; `offence_date` was `None`. A live generation check reproduced the incomplete answer. After the first matcher correction, the existing composite transition regression lost its legitimate electronic-FIR timing analysis.

### Hypothesis
Relative pre-commencement wording was not represented in the timeline model, and the substring `e fir` accidentally matched the end of “the FIR.”

### Attempt
Added an explicit pre-commencement flag and replaced substring matching with a word-boundary regular expression.

### Result
The generic query routed correctly, but the first regular expression did not recognize “FIR was registered electronically,” causing an existing regression test to fail.

### Why it failed
The first expression covered “FIR is registered electronically” but omitted the past-tense “was registered” form.

### New information learned
Electronic-FIR detection must reject cross-word substring matches while preserving tense variants used in real narratives.

### Do not repeat
Do not use raw substring checks such as `"e fir" in query`, and do not narrow the matcher without running the complete transition regression suite.

### Correct resolution
Represent relative pre-commencement allegations explicitly, allow the generic transition template without requiring a theft issue, and use a boundary-aware matcher supporting both “is registered” and “was registered electronically.”

### Relevant files
- `retrieval/transition_context.py`
- `retrieval/legal_reasoning.py`
- `app/intelligence/legal_generation.py`
- `tests/test_transition_theft_regression.py`

## DOCX visual QA unavailable

### Problem
The professional consultation export required render-based visual verification.

### Evidence
The packaged DOCX renderer failed with `FileNotFoundError [WinError 2]` while starting LibreOffice. The generated DOCX remained structurally readable as an OOXML ZIP.

### Hypothesis
LibreOffice or `soffice` is not installed or not present on the executable path.

### Attempt
Generated a representative DOCX and invoked the bundled `render_docx.py` workflow.

### Result
No page PNGs or PDF were generated.

### Why it failed
The external LibreOffice renderer dependency is unavailable in the current environment.

### New information learned
Structural DOCX tests are available locally, but visual export certification requires a machine or CI image with LibreOffice.

### Do not repeat
Do not claim the DOCX export passed visual QA on this environment unless LibreOffice becomes available.

### Correct resolution
Pending: run the same renderer in an environment with LibreOffice and inspect every generated page.

### Relevant files
- `app/exports/legal_memo.py`
- `tests/test_product_workflows.py`

## Grounding verdict helper recursed through itself

### Problem
The first full-suite run after introducing the conservative grounding verdict returned HTTP 500 for both public and authenticated legal-query paths.

### Evidence
`RecursionError` showed `deterministic_answer_for_evidence()` calling itself while the query routes were computing their answer-level verdict.

### Hypothesis
The new helper was intended to wrap the existing deterministic answer generator so routes could identify audited output.

### Attempt
A broad replacement changed the helper body to call its own name instead of `deterministic_grounded_answer`.

### Result
The helper recursed until Python hit its recursion limit; 133 tests passed and 2 query-path tests failed.

### Why it failed
The replacement matched the helper's newly added assignment rather than only the generation call site.

### New information learned
The verdict helper is on both production query paths, so its direct and authenticated integration must be covered together.

### Do not repeat
Do not use an unscoped text replacement when extracting a helper around similarly named functions.

### Correct resolution
Restore the helper's call to `deterministic_grounded_answer`, return its guardrail-enforced output, and call the helper only from generation and verdict assessment. The public and authenticated endpoint regressions pass.

### Relevant files
- `app/intelligence/legal_generation.py`
- `app/main.py`
- `api/conversations/router.py`
- `app/test_app_endpoints.py`
- `tests/test_auth_and_conversations.py`
