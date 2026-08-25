"""Regression tests for request-level statutory citation grounding."""

from verification.claim_firewall import LegalVerificationFirewall


def evidence_pack():
    return {
        "query": "What is the punishment for murder?",
        "authoritative_facts": [],
        "retrieved_sections": [
            {
                "short_name": "BNS",
                "section": "103",
                "text": "Whoever commits murder shall be punished in accordance with this section.",
            }
        ],
    }


def test_supported_citation_passes():
    passed, answer, claims = LegalVerificationFirewall().verify_and_enforce(
        "BNS section 103 governs punishment for murder.", evidence_pack()
    )

    assert passed is True
    assert answer == "BNS section 103 governs punishment for murder."
    assert claims == []


def test_supported_subsection_uses_parent_section():
    passed, _, claims = LegalVerificationFirewall().verify_and_enforce(
        "BNS section 103(1) governs the issue.", evidence_pack()
    )

    assert passed is True
    assert claims == []


def test_unsupported_citation_is_blocked_and_evidence_is_returned():
    passed, answer, claims = LegalVerificationFirewall().verify_and_enforce(
        "BNS section 999 creates a mandatory death penalty.", evidence_pack()
    )

    assert passed is False
    assert "BNS section 999" in answer
    assert "not present in the retrieved authoritative evidence" in answer
    assert "BNS section 103" in answer
    assert claims[-1]["type"] == "UNSUPPORTED_STATUTORY_CITATION"


def test_full_statute_name_is_normalized():
    passed, _, claims = LegalVerificationFirewall().verify_and_enforce(
        "Bharatiya Nyaya Sanhita section 404 applies.", evidence_pack()
    )

    assert passed is False
    assert claims[-1]["citations"] == ["BNS section 404"]


def test_every_section_in_a_plural_citation_must_be_grounded():
    passed, answer, claims = LegalVerificationFirewall().verify_and_enforce(
        "BNS sections 103 and 999 govern the issue.", evidence_pack()
    )

    assert passed is False
    assert "BNS section 999" in answer
    assert claims[-1]["citations"] == ["BNS section 999"]


def test_postfix_plural_citation_is_also_grounded():
    passed, _, claims = LegalVerificationFirewall().verify_and_enforce(
        "Sections 103 and 999 of the BNS govern the issue.", evidence_pack()
    )

    assert passed is False
    assert claims[-1]["citations"] == ["BNS section 999"]
