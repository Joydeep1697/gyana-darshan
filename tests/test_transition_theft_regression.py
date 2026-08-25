"""Regression coverage for the 29 June 2024 composite-theft failure."""

from app.source_presenter import extract_citation_keys, format_cited_evidence
from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from retrieval.legal_reasoning import (
    build_reasoning_plan,
    citation_is_grounded,
    deterministic_grounded_answer,
)
from retrieval.transition_context import analyze_transition
from verification.claim_firewall import LegalVerificationFirewall


POST_COMMENCEMENT_CASE = (
    "A theft allegedly occurred on 29 June 2024. The FIR was registered electronically "
    "on 3 July 2024 at a police station in another district. The accused has already spent "
    "12 days in police custody. Police searched his home without videography and seized "
    "laptop files, CCTV footage and WhatsApp messages. Which substantive and procedural "
    "law applies, how much additional police custody is available, how are the electronic "
    "records authenticated, and do the procedural or evidentiary defects establish "
    "innocence or automatic acquittal?"
)


def _keys(pack):
    return {
        (item.get("short_name"), str(item.get("section", "")).split("(")[0])
        for item in pack["retrieved_sections"]
    }


def test_three_transition_axes_are_classified_independently():
    timeline = analyze_transition(POST_COMMENCEMENT_CASE)

    assert timeline.offence_date.isoformat() == "2024-06-29"
    assert timeline.procedure_start_date.isoformat() == "2024-07-03"
    assert timeline.procedure_regime == "BNSS"
    assert timeline.evidence_regime == "BSA"


def test_retrieval_uses_ipc_theft_and_current_procedure_without_bns_303():
    retriever = AuthoritativeLegalRetriever()
    pack = retriever.retrieve_evidence_pack(POST_COMMENCEMENT_CASE, top_k=4)
    keys = _keys(pack)

    assert {
        ("IPC", "378"), ("IPC", "379"), ("BNS", "358"),
        ("BNSS", "531"), ("BNSS", "173"), ("BNSS", "187"), ("BNSS", "105"),
        ("BSA", "170"), ("BSA", "62"), ("BSA", "63"),
    }.issubset(keys)
    assert ("BNS", "303") not in keys
    assert ("CRPC", "167") not in keys
    assert ("IEA", "65B") not in keys


def test_audited_answer_has_no_presumed_law_and_qualifies_custody_arithmetic():
    retriever = AuthoritativeLegalRetriever()
    pack = retriever.retrieve_evidence_pack(POST_COMMENCEMENT_CASE, top_k=4)
    answer = deterministic_grounded_answer(
        POST_COMMENCEMENT_CASE, retriever.format_evidence_context(pack)
    )

    assert answer is not None
    lowered = answer.lower()
    assert "ipc sections 378 and 379" in lowered
    assert "bns section 358" in lowered
    assert "bsa section 170" in lowered
    assert "if the earlier 12 police-custody days were validly authorised" in lowered
    assert "no more than 3 aggregate days remain" in lowered
    assert "automatic acquittal" in lowered
    assert "do not state" in lowered
    for forbidden in (
        "typical legal construct", "typical legal framework", "legal systems typically",
        "presumed 15-day", "logically", "inferred from the context",
    ):
        assert forbidden not in lowered


def test_firewall_replaces_speculative_custody_reasoning_with_audited_answer():
    retriever = AuthoritativeLegalRetriever()
    pack = retriever.retrieve_evidence_pack(POST_COMMENCEMENT_CASE, top_k=4)
    unsafe = (
        "Under a typical legal framework and a presumed 15-day cap, logically only "
        "3 more days of police custody are available."
    )

    passed, answer, claims = LegalVerificationFirewall().verify_and_enforce(unsafe, pack)

    assert passed is False
    assert any(item["type"] == "UNSUPPORTED_LEGAL_INFERENCE" for item in claims)
    assert "IPC sections 378 and 379" in answer
    assert "validly authorised" in answer


def test_pending_pre_commencement_matter_uses_crpc_and_iea_branch():
    query = (
        "A theft occurred on 29 June 2024 and the investigation was already pending "
        "immediately before 1 July 2024. Police have already used 12 days of police "
        "custody, searched the premises, and seized WhatsApp messages. Which law applies?"
    )
    retriever = AuthoritativeLegalRetriever()
    pack = retriever.retrieve_evidence_pack(query, top_k=4)
    plan = build_reasoning_plan(query)
    keys = _keys(pack)

    assert plan.procedure_regime == "CRPC"
    assert plan.evidence_regime == "IEA"
    assert ("CRPC", "167") in keys
    assert ("IEA", "65B") in keys
    assert ("BNSS", "187") not in keys
    assert ("BSA", "63") not in keys

    candidate = (
        "Because the investigation was pending immediately before commencement, "
        "IEA section 65B applies to the computer output, subject to BSA section 170."
    )
    passed, _, claims = LegalVerificationFirewall().verify_and_enforce(candidate, pack)
    assert passed is True
    assert not claims


def test_source_cards_are_cited_unique_clean_and_not_mid_word_truncations():
    retriever = AuthoritativeLegalRetriever()
    pack = retriever.retrieve_evidence_pack(POST_COMMENCEMENT_CASE, top_k=4)
    answer = deterministic_grounded_answer(
        POST_COMMENCEMENT_CASE, retriever.format_evidence_context(pack)
    )
    sources = format_cited_evidence(answer, pack)
    keys = [(source["statute"], source["section"]) for source in sources]

    assert len(keys) == len(set(keys))
    assert ("BSA", "61") not in keys  # retrieved but not cited in the final answer
    assert ("BSA", "62") in keys
    assert all(source["heading"] != "Statutory provision" for source in sources)
    assert all(not source["heading"].startswith("(") for source in sources)
    assert all(not source["text_snippet"].endswith("...") for source in sources)


def test_grounding_checks_only_retrieved_statutory_material():
    context = (
        "VERIFIED LEGAL ISSUES AND REQUIRED ANALYSIS:\n"
        "- unsupported planner instruction: BNSS section 999.\n"
        "AUTHORITATIVE STATUTORY MATERIAL:\n"
        "- BNSS section 173: Information in cognizable cases."
    )

    assert citation_is_grounded("BNSS", "173", context)
    assert not citation_is_grounded("BNSS", "999", context)


def test_source_parser_handles_plural_prefix_and_postfix_citations():
    answer = "IPC sections 378 and 379 apply; sections 62 and 63 of the BSA govern proof."

    assert extract_citation_keys(answer) == [
        ("IPC", "378"), ("IPC", "379"), ("BSA", "62"), ("BSA", "63")
    ]
