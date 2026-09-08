"""Static product-quality checks for the zero-build web interface."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "app" / "static" / "index.html"
LOGO = ROOT / "app" / "static" / "logo-scales-v2.png"
FAVICON = ROOT / "app" / "static" / "favicon-scales.png"


class ProductHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {name: value or "" for name, value in attrs}))


def _parsed() -> tuple[str, ProductHTMLParser]:
    source = INDEX.read_text(encoding="utf-8")
    parser = ProductHTMLParser()
    parser.feed(source)
    return source, parser


def test_frontend_has_one_coherent_accessible_document_contract():
    source, parser = _parsed()
    html = next(attrs for tag, attrs in parser.tags if tag == "html")
    ids = [attrs["id"] for _, attrs in parser.tags if attrs.get("id")]
    buttons = [attrs for tag, attrs in parser.tags if tag == "button"]

    assert html.get("lang") == "en"
    assert len(ids) == len(set(ids)), [item for item, count in Counter(ids).items() if count > 1]
    assert all(button.get("type") == "button" or button.get("type") == "submit" for button in buttons)
    # Public and authenticated shells are mutually exclusive; each owns one H1.
    assert source.count("<h1") == 2
    assert 'class="skip-link"' in source
    assert 'aria-live="polite"' in source
    assert "@media(prefers-reduced-motion:reduce)" in source
    assert "@media(max-width:720px)" in source


def test_frontend_loads_without_render_blocking_third_party_assets():
    _, parser = _parsed()
    scripts = [attrs.get("src", "") for tag, attrs in parser.tags if tag == "script"]
    stylesheets = [
        attrs.get("href", "")
        for tag, attrs in parser.tags
        if tag == "link" and attrs.get("rel") == "stylesheet"
    ]
    assert not [src for src in scripts if src.startswith(("http://", "https://"))]
    assert not [href for href in stylesheets if href.startswith(("http://", "https://"))]


def test_frontend_uses_the_approved_scales_brand_assets():
    source, parser = _parsed()
    logo_images = [
        attrs
        for tag, attrs in parser.tags
        if tag == "img" and attrs.get("class") == "brand-logo"
    ]
    icons = [attrs for tag, attrs in parser.tags if tag == "link" and "icon" in attrs.get("rel", "")]

    assert LOGO.is_file() and LOGO.stat().st_size > 0
    assert FAVICON.is_file() and FAVICON.stat().st_size > 0
    assert len(logo_images) == 4
    assert all(image.get("src") == "/static/logo-scales-v2.png" for image in logo_images)
    assert all(image.get("alt") == "" for image in logo_images)
    sidebar_logo = next(image for image in logo_images if image.get("width") == "54")
    assert sidebar_logo.get("height") == "54"
    assert 'class="sidebar-brand-name">Nyaya<br>Darshana</span>' in source
    assert any(icon.get("href") == "/static/favicon-scales.png" for icon in icons)
    assert 'class="mark"' not in source


def test_visible_website_copy_does_not_use_em_dashes():
    source, _ = _parsed()
    assert "—" not in source


def test_frontend_uses_real_product_routes_and_current_response_shapes():
    source, _ = _parsed()
    assert "documents.documents||[]" in source
    assert "method:'POST'" in source
    assert "/api/vault/documents/${encodeURIComponent(doc.id)}/summary" in source
    assert "/api/conversations/${encodeURIComponent(state.activeConversation.id)}/messages" in source
    assert "/api/auth/google/config" in source
    assert "application/pdf,.pdf" in source
    assert "/api/vault/documents/ask" in source
    assert "/api/vault/documents/${encodeURIComponent(selected)}/contract-review" in source
    assert "/api/vault/documents/${encodeURIComponent(docId)}/contract-obligations" in source
    assert 'data-view="contract"' in source
    assert 'id="contractView"' in source
    assert 'id="reviewContractButton"' in source
    assert "Obligation suggestions" in source
    assert "Accept into Legal Ops" in source
    assert "data-obligation-suggestion" in source
    assert "activeContractReviewDocumentId" in source
    assert "Human legal review recommended" in source
    assert 'data-view="ops"' in source
    assert 'id="opsView"' in source
    assert 'id="matterForm"' in source
    assert 'id="intakeForm"' in source
    assert 'id="taskForm"' in source
    assert 'id="contractRecordForm"' in source
    assert 'id="contractEffectiveDate"' in source
    assert 'id="contractExpiryDate"' in source
    assert 'id="obligationForm"' in source
    assert 'id="obligationContractSelect"' in source
    assert 'id="obligationList"' in source
    assert 'id="opsObligationCount"' in source
    assert 'id="opsOverdueObligations"' in source
    assert 'id="playbookForm"' in source
    assert 'id="playbookList"' in source
    assert 'id="playbookTitle"' in source
    assert 'id="playbookBody"' in source
    assert 'id="opsPlaybookCount"' in source
    assert 'id="generateOpsReportButton"' in source
    assert 'id="downloadOpsReportButton"' in source
    assert 'id="opsReportResult"' in source
    assert 'id="vendorForm"' in source
    assert 'id="spendForm"' in source
    assert 'id="vendorList"' in source
    assert 'id="spendList"' in source
    assert 'id="spendMatterSelect"' in source
    assert 'id="spendVendorSelect"' in source
    assert 'id="opsOpenSpend"' in source
    assert 'id="opsPaidSpend"' in source
    assert 'id="opsOverdueInvoices"' in source
    assert 'id="contractReminderList"' in source
    assert 'id="opsRenewalCount"' in source
    assert 'id="opsSignatureCount"' in source
    assert "/api/legal-ops/workspace" in source
    assert "/api/legal-ops/report" in source
    assert "/api/legal-ops/matters" in source
    assert "/api/legal-ops/intake" in source
    assert "/api/legal-ops/intake/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/intake/${encodeURIComponent(id)}/convert" in source
    assert "/api/legal-ops/tasks" in source
    assert "/api/legal-ops/contracts" in source
    assert "/api/legal-ops/contracts/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/obligations" in source
    assert "/api/legal-ops/obligations/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/playbooks" in source
    assert "/api/legal-ops/playbooks/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/vendors" in source
    assert "/api/legal-ops/spend" in source
    assert "/api/legal-ops/spend/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/search?q=" in source
    assert "nyaya-legal-ops-report.md" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(id)}" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/brief" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/notes" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/documents" in source
    assert 'id="opsSearchForm"' in source
    assert 'id="matterDetailPanel"' in source
    assert 'id="matterBriefButton"' in source
    assert 'id="matterBriefResult"' in source
    assert 'id="matterNoteForm"' in source
    assert 'id="matterDocumentForm"' in source
    assert "/feedback" in source
    assert "/export?format=" in source
    assert "Select up to three PDFs" in source
    assert "supporting_claim" in source
    assert 'id="workspaceSelect"' in source
    assert 'id="memberForm"' in source
    assert "X-Organization-ID" in source
    assert "Premise needs correction" in source
    assert "presentationStatus" in source
    assert "Grounded · verified" not in source
    assert "Verified · corrected" not in source
    assert "<b>Supports:</b>" not in source
    assert "<b>Cited by:</b>" in source
    assert "Insufficient evidence" in source
    assert "Evidence status per answer" in source
    assert ">Evidence-grounded<" not in source
    assert "Please wait for the current consultation response" in source
    assert 'id="cancelQuestionButton"' in source
    assert "AbortController" in source
    assert "request_id:request.requestId" in source
    assert "response.request_id!==request.requestId" in source
    assert "TIMED_OUT" in source
    assert "contract_reminders" in source
    assert "open_contract_obligations" in source
    assert "data-contract-status" in source
    assert "data-obligation-status" in source
    assert "data-intake-convert" in source
    assert "data-intake-status" in source
    assert "pending_signature" in source
    assert 'id="matterDraftButton"' in source
    assert 'id="matterDraftMarkdownButton"' in source
    assert 'id="matterDraftDocxButton"' in source
    assert 'id="matterDraftReviewForm"' in source
    assert 'id="matterDraftReviewStatus"' in source
    assert 'id="matterDraftReviewerNote"' in source
    assert "Save review" in source
    assert "updateMatterDraftReview" in source
    assert "review_status" in source
    assert "reviewer_note" in source
    assert 'id="matterPrecedentSearchForm"' in source
    assert 'id="matterPrecedentSearchInput"' in source
    assert 'id="selectedMatterPrecedents"' in source
    assert 'id="matterPrecedentSearchResults"' in source
    assert "Draft precedents" in source
    assert "Add to draft" in source
    assert "Remove from draft" in source
    assert "selectedMatterDraftPrecedents" in source
    assert 'id="opsDeadlineCount"' in source
    assert 'id="matterDeadlineList"' in source
    assert 'id="matterDeadlineWindowFilter"' in source
    assert 'id="matterDeadlineKindFilter"' in source
    assert "filteredMatterDeadlines" in source
    assert "renderDeadlineActions" in source
    assert "data-deadline-clear-kind" in source
    assert "data-deadline-task-kind" in source
    assert "clearMatterDeadline" in source
    assert "createTaskFromMatterDeadline" in source
    assert "/api/legal-ops/deadlines/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/clear" in source
    assert "/api/legal-ops/deadlines/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/task" in source
    assert "Matter deadlines" in source
    assert "Deadline calendar" in source
    assert "detail.deadlines" in source
    assert "matter_deadlines" in source
    assert 'id="taskAssigneeSelect"' in source
    assert "assignee_user_id" in source
    assert "assignee_name" in source
    assert "state.ops?.members" in source
    assert "renderTaskAssigneeOptions" in source
    assert "Matter comment" in source
    assert 'id="matterNoteLinkKind"' in source
    assert 'id="matterNoteLinkSourceId"' in source
    assert "author_name" in source
    assert "link_kind" in source
    assert "link_source_id" in source
    assert "Activity by date" in source
    assert "renderMatterActivity" in source
    assert "actor_name" in source
    assert "data-deadline-note-kind" in source
    assert "prepareDeadlineNote" in source
    assert "bindDeadlineActionButtons" in source
    assert "Add note" in source
    assert '@router.get("/matters/{matter_id}/deadlines"' in Path("app/routers/legal_ops.py").read_text(encoding="utf-8")
    assert "Draft history" in source
    assert "data-matter-draft-id" in source
    assert "data-add-matter-precedent" in source
    assert "data-remove-matter-precedent" in source
    assert "searchMatterDraftPrecedents" in source
    assert "loadMatterDraft" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/draft" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/drafts/${encodeURIComponent(draftId)}" in source
    assert "/api/legal-ops/matters/${encodeURIComponent(detail.id)}/drafts/${encodeURIComponent(draft.id)}" in source
    assert "/draft/export?format=" in source
    assert "&draft_id=${encodeURIComponent(state.activeMatterDraft.id)}" in source
    assert "precedent_ids:state.selectedMatterDraftPrecedents.map(item=>item.id)" in source
    assert 'id="precedentSearchForm"' in source
    assert 'id="precedentSearchResults"' in source
    assert "/api/vault/precedents?q=" in source
    assert "Search indexed judgments" in source
    assert "provenance_status" in source


def test_frontend_does_not_reintroduce_mock_operational_claims_or_reasoning_theatre():
    source, _ = _parsed()
    forbidden = (
        "Mission Control",
        "Active agents",
        "Memory synced",
        "Reasoning Trail",
        "Verification Trail",
        "Dedicated Multi-Agent",
        "DOCX/TXT/HTML/XLSX",
    )
    for phrase in forbidden:
        assert phrase.casefold() not in source.casefold()
    assert not re.search(r"Nyaya Darshan(?!a)", source)
    assert "corpus" not in source.casefold()
