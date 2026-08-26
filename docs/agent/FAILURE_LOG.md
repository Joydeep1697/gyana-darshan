# Agent Failure Log

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
