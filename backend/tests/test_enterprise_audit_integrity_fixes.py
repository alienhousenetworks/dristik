"""Focused regression tests for enterprise audit integrity fixes."""
from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cro.engine import build_cro_intelligence
from app.domain.enums import Severity, VerificationStatus
from app.reports.adaptive_audit_book import _build_ch_aeo, _render_geo_dimension_cards
from app.reports.publication_status import (
    STATUS_AI_EVIDENCE_VERIFIED,
    STATUS_INFERRED,
    STATUS_PENDING_VERIFICATION,
    STATUS_RULE_VERIFIED,
    classify_finding_status,
    render_verification_standard_banner,
    summarize_publication_verification,
)
from app.reports.publishing_engine import (
    ChapterSpec,
    PartSpec,
    PdfPaginationResolver,
    PdfQualityAssurance,
    PublicationDocument,
    PublicationHtmlRenderer,
    PublicationMetadata,
)
from app.reports.snapshot_provenance import (
    format_audit_execution_metadata,
    render_snapshot_provenance_bar,
)
from app.workers.critic_worker import CognitiveCriticWorker


def test_geo_8_dimension_cards_resolve_canonical_keys():
    geo = SimpleNamespace(
        dimension_scores={
            "entity_clarity": SimpleNamespace(score=100.0, band="high", is_measured=True, summary="Clear brand entity."),
            "answerability": SimpleNamespace(score=42.3, band="medium", is_measured=True, summary="3/6 buyer questions."),
            "content_extractability": SimpleNamespace(score=78.7, band="high", is_measured=True, summary="Strong H2/H3 structure."),
            "structured_data_quality": SimpleNamespace(score=43.2, band="medium", is_measured=True, summary="JSON-LD partial."),
            "citation_readiness": SimpleNamespace(score=59.2, band="medium", is_measured=True, summary="4 citable passages."),
            "retrieval_accessibility": SimpleNamespace(score=100.0, band="high", is_measured=True, summary="All AI bots allowed."),
            "factual_grounding": SimpleNamespace(score=20.0, band="low", is_measured=True, summary="Price conflict observed."),
            "ai_engine_visibility": SimpleNamespace(score=None, band="unmeasured", is_measured=False, summary="Connector required."),
        },
        dimensions=[],
    )
    html = _render_geo_dimension_cards(geo)
    assert "59/100 · MEDIUM" in html
    assert "43/100 · MEDIUM" in html
    assert "100/100 · HIGH" in html
    assert "20/100 · LOW" in html
    assert "42/100 · MEDIUM" in html
    assert "79/100 · HIGH" in html
    # Only the unmeasured live AI engine visibility dimension should say NOT MEASURED
    assert html.count("NOT MEASURED") == 1


def test_publication_verification_standard_never_falsely_certifies():
    findings = [
        SimpleNamespace(verification_status=VerificationStatus.VERIFIED, adversarial_reviewed=True, evidence_refs=["ev1"], verification_notes="[AI Review: CONFIRMED] ok"),
        SimpleNamespace(verification_status=VerificationStatus.VERIFIED, adversarial_reviewed=False, evidence_refs=["ev2"], verification_notes=""),
        SimpleNamespace(verification_status=VerificationStatus.PENDING_VERIFICATION, adversarial_reviewed=False, evidence_refs=["ev3"], verification_notes="Not evaluated in critic pass; remains pending verification."),
        SimpleNamespace(verification_status=VerificationStatus.INFERRED, adversarial_reviewed=False, evidence_refs=[], verification_notes=""),
    ]
    assert classify_finding_status(findings[0]) == STATUS_AI_EVIDENCE_VERIFIED
    assert classify_finding_status(findings[1]) == STATUS_RULE_VERIFIED
    assert classify_finding_status(findings[2]) == STATUS_PENDING_VERIFICATION
    assert classify_finding_status(findings[3]) == STATUS_INFERRED

    summary = summarize_publication_verification(findings)
    assert summary.is_fully_ai_verified is False
    assert summary.counts[STATUS_AI_EVIDENCE_VERIFIED] == 1
    assert summary.counts[STATUS_RULE_VERIFIED] == 1
    assert summary.counts[STATUS_PENDING_VERIFICATION] == 1
    assert summary.counts[STATUS_INFERRED] == 1

    banner = render_verification_standard_banner(findings, narrative_mode="deterministic_fallback")
    assert "Mixed Verification" in banner
    assert "deterministic_fallback" in banner


def test_snapshot_provenance_reconciles_specialist_vs_executive_counts():
    report = SimpleNamespace(
        domain="perforacare.com",
        analysis_id="run_ceabb2bbd8",
        generated_at="2026-11-22T05:24:00Z",
        scores=SimpleNamespace(overall_score=53.6, overall_grade="D", category_scores={"TECHNICAL_SEO": SimpleNamespace(score=86.9, status="PARTIAL")}),
        findings=[SimpleNamespace(category="TECHNICAL_SEO", title=f"f{i}") for i in range(17)],
        crawl_manifest=SimpleNamespace(pages=[object()] * 5, total_pages_discovered=503),
    )
    snap = format_audit_execution_metadata(report, use_cache=False)
    bar = render_snapshot_provenance_bar(snap, section_key="cro", section_label="CRO", section_score=67.6, section_findings_count=30)
    assert "30 CRO specialist findings · 17 unified executive findings" in bar
    assert "30 in CRO (17 total" not in bar


def test_aeo_chapter_surfaces_not_measured_reason():
    report = SimpleNamespace(
        ai_visibility_scorecard=SimpleNamespace(
            status="NOT_MEASURED",
            successful_runs=0,
            not_measured_reason="No successful engine responses from OpenRouter.",
        ),
        findings=[],
    )
    html = _build_ch_aeo(report, {})
    assert "No successful engine responses from OpenRouter." in html


def test_toc_pagination_skips_cover_and_toc_pages(monkeypatch):
    # Simulate a 6-page PDF where page 1=Cover, page 2-3=TOC containing chapter titles,
    # and pages 4, 5, 6 are the actual chapter starts with [[chapter_ref:...]] markers.
    fake_pages = [
        "DRISTIK COVER perforacare.com",
        "TABLE OF CONTENTS 01. Executive Brief p. 4 02. Technical SEO p. 5",
        "TABLE OF CONTENTS (cont.) 03. Generative Engine Optimization p. 6",
        "[[chapter_ref:ch_brief:ch_01]] Chapter 01 Executive Brief body",
        "[[chapter_ref:ch_seo:ch_02]] Chapter 02 Technical SEO body",
        "[[chapter_ref:ch_geo:ch_03]] Chapter 03 Generative Engine Optimization body",
    ]

    class _FakePage:
        def __init__(self, txt):
            self._txt = txt

        def extract_text(self):
            return self._txt

    class _FakeReader:
        def __init__(self, _buf):
            self.pages = [_FakePage(t) for t in fake_pages]
            self.metadata = SimpleNamespace(title="Dristik Audit")

    import app.reports.publishing_engine as pe

    monkeypatch.setattr(pe, "pypdf", SimpleNamespace(PdfReader=_FakeReader))
    chapters = [
        ChapterSpec(id="ch_brief", num="01", part_id="p1", part_title="P1", title="Executive Brief", desc="Brief", html_content="<p>a</p>"),
        ChapterSpec(id="ch_seo", num="02", part_id="p1", part_title="P1", title="Technical SEO", desc="SEO", html_content="<p>b</p>"),
        ChapterSpec(id="ch_geo", num="03", part_id="p1", part_title="P1", title="Generative Engine Optimization", desc="GEO", html_content="<p>c</p>"),
    ]
    resolved = PdfPaginationResolver.resolve_physical_pages(b"%PDF-1.4 " + b"0" * 200, chapters, starting_body_page=4)
    assert resolved == {"ch_brief": 4, "ch_seo": 5, "ch_geo": 6}

    doc = PublicationDocument(
        metadata=PublicationMetadata(family="COMPLETE", title="Audit", subtitle="Sub", domain="perforacare.com", brand_name="Perfora", audit_date="2026-11-22", report_ref="RUN_CEABB2BB", classification="CONF", purpose="Test", score_display="53.6", grade="D"),
        parts=[PartSpec(id="p1", num="I", title="Part I", chapters=chapters)],
        toc_pages=2,
        starting_body_page=4,
    )
    rendered_html = PublicationHtmlRenderer.render(doc, resolved_pages=resolved)
    assert "font-size:1pt" in rendered_html
    assert "font-size: 0pt" not in rendered_html

    # QA gate rejects chapters stuck on TOC page 3
    bad_qa = PdfQualityAssurance.validate(b"%PDF-1.4 " + b"0" * 200, doc, {"ch_brief": 3, "ch_seo": 3, "ch_geo": 3})
    assert "check_toc_page_numbers_accurate" in bad_qa.failed_checks


def test_critic_worker_retries_omitted_claims_and_normalizes_ids():
    claims = [
        SimpleNamespace(id="CLM_001", statement="Missing H1", severity=Severity.HIGH, evidence_refs=["ev1"], agent_id="seo", verification_status=VerificationStatus.PROVISIONAL, verification_notes=""),
        SimpleNamespace(id="CLM_002", statement="Broken canonical", severity=Severity.HIGH, evidence_refs=["ev2"], agent_id="seo", verification_status=VerificationStatus.PROVISIONAL, verification_notes=""),
    ]
    blackboard = SimpleNamespace(
        claim_registry=SimpleNamespace(get_all=lambda: claims, register_contradiction=lambda **kw: kw),
        evidence_store=SimpleNamespace(get_all=lambda: [SimpleNamespace(id="ev1"), SimpleNamespace(id="ev2")]),
        log_step=lambda *a, **k: None,
    )
    # First call omits CLM_002 and returns lowercase clm_001; retry call evaluates CLM_002
    router = SimpleNamespace(
        generate_structured=AsyncMock(
            side_effect=[
                {"results": [{"claim_id": "clm_001 ", "decision": "supported", "rationale": "Confirmed by ev1"}]},
                {"results": [{"claim_id": "CLM_002", "decision": "supported", "rationale": "Confirmed by ev2"}]},
            ]
        )
    )
    worker = CognitiveCriticWorker("critic_1", router)
    out = asyncio.run(worker.execute_task("critic", blackboard))
    assert out["pending_claims_count"] == 0
    assert out["critic_coverage_pct"] == 100.0
    assert all(c.verification_status == VerificationStatus.VERIFIED for c in claims)


def test_cro_intelligence_reflects_executed_browser_tests():
    intel = build_cro_intelligence(
        pages=[SimpleNamespace(url="https://perforacare.com/", title="Perfora", body_text="Oral care", h1=["Oral care"])],
        discovered_urls=503,
        browser_tests={"rendered_pages": 1, "interaction_tests_executed": 4, "journey_execution_status": "EXECUTED_SAFE_MODE"},
    )
    assert intel.coverage["rendered_dom_status"] == "RENDERED_DOM_VERIFIED_FOR_SAMPLE"
    assert intel.coverage["rendered_pages"] == 1
    assert intel.coverage["journey_execution_status"] == "EXECUTED_SAFE_MODE"
    assert intel.coverage["interaction_tests_executed"] == 4
