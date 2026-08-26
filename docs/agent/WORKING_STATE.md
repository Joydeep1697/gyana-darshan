# Verified Working State

This file records product behavior only after automated or runtime verification.

## Branding

- [PASS] Scales-of-justice logo appears through local product assets.
- [PASS] Sidebar brand lockup has responsive contract coverage.

## Consultation

- [PASS] Authenticated consultation creation and persistent message history.
- [PASS] Tenant ownership checks for consultation retrieval, export, and feedback.
- [PASS] Pre-commencement conduct is separated from procedural transition routing.
- [PASS] Generic “the FIR came later” wording does not trigger electronic-FIR advice.
- [PASS] Legitimate electronic-FIR narratives retain timing analysis.
- [PASS] Materially missing transition facts can trigger a focused clarification without consuming consultation quota.
- [PASS] Cited source cards can identify the answer claim supported by each provision.

## Knowledge Vault

- [PASS] PDF ownership is persisted and list/search/statistics are tenant-isolated.
- [PASS] Document summaries are cached and ownership-checked.
- [PASS] Questions can be grounded in one to three owned PDFs with page-level excerpts.
- [PASS] Document-grounding prompts treat uploaded content as untrusted evidence.

## Exports and feedback

- [PASS] Consultation Markdown and DOCX exports are ownership-protected.
- [PASS] DOCX packages pass structural OOXML validation.
- [UNVERIFIED] DOCX visual layout; LibreOffice is unavailable in the current environment.
- [PASS] Helpful/not-helpful feedback is persisted per user and answer.

## Release

- [PASS] Frontend product contract tests cover accessible controls and approved branding.
- [PASS] Production preflight, health, authentication, authorization, AI routing, and statutory release checks are automated.

## Enterprise operations

- [PASS] Every account receives a backward-compatible private organization workspace.
- [PASS] Organization consultations and Vault documents are membership-scoped.
- [PASS] OWNER, ADMIN, MEMBER, and read-only VIEWER permissions are server-enforced.
- [PASS] Member, retention, consultation, feedback, upload, deletion, and export actions are auditable.
- [PASS] Retention enforcement defaults to dry-run and validates upload paths before deletion.
- [PASS] Backup archives use online SQLite snapshots, checksums, traversal validation, and guarded restoration.
- [PASS] Account and access UI exposes workspace switching, member review, organization creation, and member invitation.
- [PASS] Organization controls passed authenticated desktop browser QA with no console warnings or errors.
