# Agent 2 Baseline — Legal Trust and Consultation Reliability

Recorded: 2026-09-05

## Scope and architecture observed

- Application entrypoint: `run.py` starts the FastAPI application in `app/main.py`.
- Authenticated consultation flow: `api/conversations/router.py`; public evidence flow: `POST /api/v1/query` in `app/main.py`.
- Retrieval: `retrieval/hybrid_retriever.py`, with deterministic transition planning in `retrieval/legal_reasoning.py` and statutory corpus records as evidence.
- Generation: `app/intelligence/legal_generation.py`; post-generation citation allowlisting and targeted contradiction rules: `verification/claim_firewall.py`.
- Citation cards: `app/source_presenter.py`; consultation UI state and rendering: `app/static/index.html`.
- Persistence/quota: conversation repositories and usage records in the consultation router.

## Protected baseline safety behaviour

The current working tree contains uncommitted intake safeguards that reject impossible dates, explicitly fictitious authorities, non-human accused, and safeguard-override prompts before retrieval. The response state is `INPUT_NEEDS_CORRECTION`, it has no citations, is persisted, and does not consume quota. Pending consultation navigation is also blocked in the UI.

## Verification run before Agent 2 changes

| Check | Result |
| --- | --- |
| Focused trust/UI tests | 29 passed (run in the immediately preceding implementation turn) |
| Full suite | 130 passed, 1 failed, 3 subtests passed |
| Compilation | Passed in the immediately preceding implementation turn |
| Repository release preflight | Passed in the immediately preceding implementation turn |
| Browser smoke test | Passed in the immediately preceding implementation turn: non-empty page, no overlay, no console errors |

## Pre-existing baseline failure

`retrieval/experimental/test_experimental_modules.py::test_pipeline` initially failed with `KeyError: 'score'`. Investigation confirmed `branch_score` was the canonical meaningful score and a legacy consumer still required `score`; the retriever now returns a compatibility alias with the same value. The focused regression passes.

## Current grounding weakness

The existing firewall confirms that an answer's cited statute-section pair is present in the retrieved evidence pack, and `legal_reasoning.verify_answer` checks expected issue-section coverage for recognised scenarios. Neither creates a general structured material-claim verdict or proves that each cited provision supports each generated proposition. Therefore a P0 false-grounded risk remains for unrecognised or partially answered multi-issue prompts.

## Baseline release posture

The post-change full suite is green: 137 passed, 1 warning, 3 subtests passed. Do not treat that as a legal-correctness release approval: proposition support for model synthesis, jurisdiction, temporal validity, quote verification, and conflict resolution are not yet independently measured.
