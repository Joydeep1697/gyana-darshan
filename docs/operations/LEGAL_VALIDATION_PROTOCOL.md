# Nyaya Darshana Legal Validation Protocol

Nyaya Darshana must not use internal benchmark scores as public legal-accuracy claims. Internal tests are engineering evidence only. A public accuracy, launch, investor, or customer claim requires an external reviewer package completed by qualified legal reviewers who did not author the benchmark, implementation, or expected answers.

## Minimum Reviewer Panel

- At least two qualified Indian legal reviewers.
- One reviewer must validate statutory correctness and citation identity.
- One reviewer must validate practical legal usefulness, missing-fact handling, and overclaim risk.
- Reviewers must record conflicts, abstentions, and uncertain conclusions instead of forcing a pass/fail answer.

## Review Set Requirements

- Use a frozen sample that was not used to tune retrieval rules, prompts, tests, or benchmark expectations.
- Include criminal law transition questions, BNS/BNSS/BSA evidence issues, special-statute interactions, contract review, matter drafting, precedent search, and document-grounded Q&A.
- Include adversarial false-premise questions and incomplete fact patterns.
- Preserve every prompt, retrieved source, generated answer, cited provision, review decision, reviewer note, date, and app commit.

## Legal Quality Criteria

A reviewed answer can pass only when:

- The cited authority exists and matches the statute, section, subsection, and quoted text.
- The answer distinguishes current law from historical law where timing matters.
- The answer separates legal research support from legal advice.
- The answer identifies material missing facts before reaching a conclusion.
- The answer does not claim case outcome certainty without authority and procedural context.
- The answer flags unsupported generated propositions for human review.

## Evidence Ledger

For each reviewed item, record:

- `review_id`
- `reviewer_role`
- `commit_sha`
- `product_area`
- `prompt`
- `expected_issue`
- `retrieved_sources`
- `answer_excerpt`
- `citation_identity_status`
- `proposition_support_status`
- `missing_fact_handling`
- `overclaim_risk`
- `decision`: `pass`, `fail`, or `needs_revision`
- `reviewer_notes`
- `reviewed_at`

## Launch Rule

Nyaya Darshana may describe its legal quality publicly only with the exact externally reviewed scope. Example: "Externally reviewed on 120 Indian statutory research scenarios" is acceptable only after the ledger exists and is preserved. A broad claim such as "96% legally accurate" is not acceptable unless the external package directly supports that scope.
