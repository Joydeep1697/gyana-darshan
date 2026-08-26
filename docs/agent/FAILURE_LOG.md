# Agent Failure Log

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
