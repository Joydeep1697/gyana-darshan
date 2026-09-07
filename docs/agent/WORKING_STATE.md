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
- [PASS] Impossible dates, explicitly unverified fictional authorities, non-human accused, and safeguard-override prompts are intercepted before retrieval, carry no citations, and do not consume consultation quota.
- [PASS] Consultation navigation cannot switch or create a new consultation while a response is pending.
- [PASS] Consultation attempts carry request and attempt identities; cancelled or timed-out browser attempts restore the question and reject late responses from older attempts.
- [PASS] Cycle 8 supersedes template-based verification: generator identity, firewall acceptance, and citations cannot grant proposition support. Generated legal conclusions report insufficient evidence or detected conflict until independent proof exists. Source diagnostics remain separate.
- [PASS] Material-claim verdicts classify uncited legal consequences as unsupported and separately report citation coverage versus fully supported-claim completeness.
- [PASS] Source cards identify the answer passage citing a provision, labelled "Cited by"; citation association is not presented as proposition support.
- [PASS] Fully verified legal answers require a retrieved, Indian, binding authority; foreign, unclassified, or explicitly conflicting authorities cannot be promoted to fully verified.
- [PASS] Fully verified legal answers reject mismatched subsection pincites and OCR-derived or integrity-unknown source text; whitespace-only quote layout variation is accepted without character repair.
- [PASS] Cycle 7: numeric statutory pinpoints require unique subsection spans. Wrong-subsection quotes, cross-reference-only labels, repeated missing pinpoints, ambiguous duplicates, nested clauses, and ranges cannot receive fully verified status. Evidence beyond 900 characters is retained. Seventeen new tests include both API routes with mocked upstream acceptance; full suite: 158 passed and 3 subtests passed. Judgment page/paragraph verification remains unverified.
- [PASS] Answers that are not fully verified receive a deterministic human-review recommendation; conflict and critical unverified claims are high priority and are audit-logged for the workspace.
- [PASS] Cycle 8: inconsistent/legacy verified labels cannot suppress human-review guidance. Both public API entry points and consultation creation use the shared abstention gate. Newly stored consultation history retains its insufficient-evidence verdict. Eleven new regressions and the full suite pass: 169 tests, 3 subtests, one dependency deprecation warning. Historical verdict reverification and review guidance after reload remain unverified.
- [PASS] Cycle 9 supersedes the review-reload limitation: historical responses project unsupported success labels to insufficient evidence, retain `recorded_grounding_status`, preserve original database records and tenant access checks, and restore high-priority review guidance for detected critical claims. This is conservative presentation, not retroactive legal verification.
- [PASS] Legacy chat exposes the same abstention/review state without invented verification steps or fixed stage timings. Both public APIs leave unproven provenance uncertified.
- [PASS] Authenticated desktop and 390x844 mobile browser QA verified legacy answer status, review guidance, citation disclosure, and no horizontal overflow. Original logo URLs were restored after a concurrent edit broke asset loading; all four logo images loaded. Full suite: 181 tests and 3 subtests passed; final frontend contracts: 6 passed.
- [PASS] A repeatable local retrieval benchmark measures Recall@6, Precision@6, MRR, and every missed required authority across three core legal workflows.

## Knowledge Vault

- [PASS] PDF ownership is persisted and list/search/statistics are tenant-isolated.
- [PASS] Document summaries are cached and ownership-checked.
- [PASS] Questions can be grounded in one to three owned PDFs with page-level excerpts.
- [PASS] Document-grounding prompts treat uploaded content as untrusted evidence.
- [PASS] Known document prompt-injection, secret-exfiltration, role-override, and tool-execution spans are removed before Vault Q&A and summary provider calls, while surrounding evidence remains available.
- [PASS] Workspace intelligence routes use organization scope for graph links, related documents, section impact, contradiction gaps, deadlines, classifier stats, dashboard analytics, briefing cache and proactive checks. Shared workspace viewers can read the same intelligence surface as the owner; outsiders cannot read that organization.
- [PASS] Contract Review reads an owned Vault PDF, returns deterministic NDA profile, clause findings, risk findings and human-review guidance through `/api/vault/documents/{id}/contract-review`. Authenticated desktop browser QA verified document selection and rendered results; 390x844 mobile QA verified no horizontal overflow and no console errors.

## Exports and feedback

- [PASS] Consultation Markdown and DOCX exports are ownership-protected.
- [PASS] DOCX packages pass structural OOXML validation.
- [UNVERIFIED] DOCX visual layout; LibreOffice is unavailable in the current environment.
- [PASS] Helpful/not-helpful feedback is persisted per user and answer.

## Release

- [PASS] Public website structure: Home links to About Us, Research Services, Use Cases, Pricing and Contact & Support. Seven dedicated public routes retain shared navigation, footer, auth shell, unique IDs and real subsection anchors. Unknown routes remain 404 and private APIs remain protected.
- [PASS] Public contact/social configuration is optional and escaped/validated. Public pricing uses existing server amounts and payment availability, with no implied quota upgrade or recurring term. No fabricated team members, customer results or offices.
- [PASS] Website browser QA: desktop About layout; mobile menu and FAQ expansion; all seven pages at 320px without document overflow; 390px pricing and loaded logos; registration preserves Account destination; signed-in public browsing and Vault destination; illustrative prompt fills the composer without submission. Full suite: 192 tests and 3 subtests passed. Final focused public/frontend checks: 17 passed; JavaScript syntax, Python compilation and repository preflight passed.
- [UNVERIFIED] Public contact delivery and official social profiles until the operator configures real destinations. Privacy and terms are explicit product information pending operator-approved policies. No production deployment, live payment or new AI-provider verification was performed for the website structure change.
- [PASS] Logout after entering the app from a public use-case page reloads the actual Home document and hides the authenticated shell.

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
- [PASS] Legal Ops workspace supports org-scoped matters, intake requests, tasks, contract lifecycle records and summary metrics. API regressions verified viewer read access, writer-only mutations, outsider isolation and bad-reference rejection. Authenticated desktop browser QA created matter, intake, task and contract records, marked a task done, and verified rendered metrics; 390x844 mobile QA verified no horizontal overflow and no console errors.
- [PASS] Legal Ops matter detail supports linked Vault documents, matter notes and unified search across matters, intake, tasks, contracts and Vault metadata. API regression verified detail aggregation, same-workspace document linking, cross-workspace link rejection and short-query validation. Authenticated browser QA created a matter, opened details, added a note, linked a Vault document and searched records; 390x844 mobile QA verified no horizontal overflow and no console errors.
## 2026-09-07

- [PASS] Legal Ops matter detail now includes an organization-scoped activity timeline assembled from linked Vault documents, notes, tasks, contracts, and intake records. API regression and frontend contract tests pass.
- [PASS] Legal Ops contract lifecycle responses expose computed lifecycle stage, renewal reminder status, and days-to-renewal without a destructive schema migration. Workspace responses include contract reminders, renewal counts, pending-signature counts, writer-only lifecycle transitions, and frontend reminder/action controls. Focused API and frontend contract tests pass.
- [PASS] Legal Ops intake triage can convert an unlinked intake request into one matter, copy title/type/summary/urgency into the matter, mark the intake in progress, keep repeat conversion idempotent, block viewer conversion, and expose Start matter / Mark triaged controls in the frontend. Focused API and frontend contract tests pass.
- [PASS] Release verification imports local `app` and `retrieval` packages through an explicit GitHub Actions `PYTHONPATH`. Public query responses keep returning sanitized retrieved sections when the final answer cites none, without certifying provenance or source support. CI-equivalent local gate passes: 199 tests, 3 subtests, one dependency warning.
- [PASS] Legal Ops matter detail can generate a deterministic, source-labeled matter brief from the linked matter description, intake, notes, tasks, contracts and Vault document metadata. The brief includes explicit limits instead of legal-merits claims. Focused API/frontend tests and desktop/mobile browser smoke pass.
- [PASS] Legal Ops spend management supports organization-scoped vendor records, matter/vendor-linked spend entries, invoice status transitions, open/paid/overdue spend summary metrics, unified vendor/invoice search, and spend visibility in matter detail activity. Focused API/frontend tests and desktop/mobile browser smoke pass.
- [PASS] Legal Ops playbooks support organization-scoped internal guidance, active/draft/archive status, unified playbook search, active playbook summary counts, matter-type matching in matter detail, and source-labeled inclusion in deterministic matter briefs with explicit non-authority limits. Focused API/frontend tests and desktop/mobile browser smoke pass.
- [PASS] Legal Ops reporting generates a deterministic Markdown workspace report from matters, intake, tasks, contracts, reminders, vendors, spend and playbooks. The report exposes record counts and explicit non-advice/non-audit limits, supports viewer access, blocks outsiders through workspace scope, renders in the Legal Ops UI, and enables local Markdown download. Focused API/frontend tests and desktop/mobile browser smoke pass.
- [PASS] Contract lifecycle management supports organization-scoped contractual obligations linked to contracts and matters. Obligations track owner, priority, due date, source clause and status, appear in workspace metrics, matter detail, activity, unified search, matter briefs and Legal Ops reports, and support writer-only completion/waiver actions. Focused API/frontend tests and desktop/mobile browser smoke pass.
- [PASS] Contract review now produces deterministic, source-quoted obligation suggestions from uploaded PDFs. Writers can accept a suggestion into org-scoped Legal Ops; the source clause is revalidated against the stored PDF, persisted on the obligation, and tampered clauses are rejected. Full suite: 213 tests and 3 subtests passed; focused contract/frontend checks pass.
