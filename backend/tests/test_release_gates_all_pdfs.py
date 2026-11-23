"""Phase 4 & 5 Gate: Unified 5-Point Card, 4-Part Chapter Layout, Compression & Release Gates."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.enums import Category, Severity
from app.domain.models import Finding, FindingEvidence
from app.report_finding_registry import normalize_canonical_findings, partition_findings_for_chapter
from app.report_integrity_gate import validate_pdf_release_gates
from app.reports.five_point_card_renderer import (
    compress_evidence_rows,
    render_compressed_evidence_ledger,
    render_five_point_finding_card,
    render_global_methodology_and_connectors_page,
    render_unified_chapter,
)


def _perfora_canonical_findings():
    f1 = Finding(
        finding_id="FND_TITLE_021",
        rule_id="TITLE_LENGTH_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Product page title is 'kwikpass'",
        affected_urls=["https://perforacare.com/products/lemon-mint-probiotic-rinse"],
        evidence_ids=["EV_021"],
        evidence_refs=["EV_021"],
        algo_trace=[
            {"rule_id": "TITLE_RELEVANCE", "input": "html.<title>", "threshold": "contains product/brand", "observed": "kwikpass", "status": "FAIL"},
            {"rule_id": "TITLE_LENGTH", "input": "len(title)", "threshold": "25-65 chars", "observed": "8", "status": "FAIL"},
        ],
        ai_understanding="The page title is likely overwritten by the Kwikpass login app or an empty Shopify SEO title field (EV_021).",
        ai_analysis="Search results will show an irrelevant title, hurting click-through. Ranking impact today is unknown without GSC. Confidence: high on defect, medium on cause.",
        fix_prompt="Shopify store. Product page title renders as 'kwikpass'. Check Kwikpass app title injection and product SEO title. Set SEO title to '{product.title} | Perfora' (25-65 chars) and verify one <title> tag.",
        evidence=[
            FindingEvidence(evidence_id="EV_021", url="https://perforacare.com/products/lemon-mint-probiotic-rinse", element="title", value="kwikpass", source="crawl"),
            FindingEvidence(evidence_id="EV_021", url="https://perforacare.com/products/lemon-mint-probiotic-rinse", element="title", value="kwikpass", source="crawl"),
        ],
    )
    f2 = Finding(
        finding_id="FND_TTFB_001",
        rule_id="TTFB_P1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="Homepage TTFB is 2809ms (> 800ms P1 threshold)",
        affected_urls=["https://perforacare.com/"],
        evidence_ids=["EV_001"],
        evidence_refs=["EV_001"],
        algo_trace=[
            {"rule_id": "TTFB_P1", "input": "http.ttfb_ms", "threshold": "<= 800ms", "observed": "2809ms", "status": "FAIL"},
        ],
        ai_understanding="Homepage origin response took 2809ms during crawl (EV_001), likely due to uncached Liquid rendering or blocking Shopify apps.",
        ai_analysis="Slow TTFB delays LCP and increases bounce risk. Real-user field impact cannot be confirmed without CrUX. Confidence: high on lab measurement.",
        fix_prompt="Profile homepage Shopify theme Liquid render time and third-party app scripts causing 2809ms TTFB. Enable edge caching and confirm TTFB <= 800ms on re-crawl.",
        evidence=[
            FindingEvidence(evidence_id="EV_001", url="https://perforacare.com/", element="ttfb_ms", value="2809ms", source="http"),
        ],
    )
    return normalize_canonical_findings(SimpleNamespace(findings=[f1, f2]), active_connectors=set())


def test_five_point_card_and_evidence_compression():
    findings = _perfora_canonical_findings()
    card_html = render_five_point_finding_card(findings[0])
    for block in (
        "1. Finding:",
        "2. Algorithm Analysis",
        "3. AI Understanding:",
        "4. AI Analysis:",
        "5. Fix Plan (Prompt):",
        "Fix resolves issue:",
        "Search Console",
        "EV_021",
    ):
        assert block in card_html

    # Repeated identical evidence rows collapse to one row with count=2
    compressed = compress_evidence_rows(findings[0].evidence)
    assert len(compressed) == 1
    assert compressed[0]["count"] == 2
    ledger_html = render_compressed_evidence_ledger(findings)
    assert "&times;2" in ledger_html


def test_six_pdfs_pass_all_release_gates():
    findings = _perfora_canonical_findings()
    global_page = render_global_methodology_and_connectors_page(active_connectors=set())
    assert "What Connectors Would Change" in global_page
    assert "PageSpeed/CrUX" in global_page
    assert "Search Console" in global_page

    chapters_spec = [
        ("seo", "SEO Audit"),
        ("geo", "GEO Audit"),
        ("aeo", "AEO Audit"),
        ("cro", "CRO Audit"),
        ("crawl", "Crawl & Performance Audit"),
    ]
    chapter_payloads = []
    master_html_parts = []
    pillar_pdfs = {}

    for ch_id, ch_title in chapters_spec:
        owned, xrefs = partition_findings_for_chapter(findings, ch_id)
        ch_html = render_unified_chapter(
            chapter_id=ch_id,
            chapter_title=ch_title,
            chapter_ai_analysis=f"Grounded chapter AI summary for {ch_title} across perforacare.com.",
            section_analyses=[{"section": "Core Checks", "analysis": "Observed deterministic signals only."}],
            owned_findings=owned,
            cross_ref_findings=xrefs,
            passed_checks=[{"rule_id": "ROBOTS_TXT", "detail": "Reachable HTTP 200"}],
        )
        chapter_payloads.append({"chapter_id": ch_id, "owned_finding_count": len(owned), "html": ch_html})
        master_html_parts.append(ch_html)
        pillar_pdfs[ch_id] = {
            "composite_score": 52.4,
            "finding_count": len(findings),
            "html": ch_html + global_page,
            "page_count": 6,
            "chapters": [{"chapter_id": ch_id, "owned_finding_count": len(owned), "html": ch_html}],
        }

    all_six = {
        "master": {
            "composite_score": 52.4,
            "finding_count": len(findings),
            "html": "".join(master_html_parts) + global_page + render_compressed_evidence_ledger(findings),
            "page_count": 19,
            "chapters": chapter_payloads,
        },
        **pillar_pdfs,
    }
    gate_res = validate_pdf_release_gates(all_six, max_master_pages=22)
    assert gate_res["status"] == "PASS"
    assert len(gate_res["pdfs_checked"]) == 6


def test_release_gates_block_leaks_score_drift_and_page_overflow():
    with pytest.raises(ValueError, match="composite score mismatch"):
        validate_pdf_release_gates({
            "master": {"composite_score": 43.7, "finding_count": 15, "html": "<p>ok</p>", "page_count": 20},
            "seo": {"composite_score": 51.0, "finding_count": 15, "html": "<p>ok</p>", "page_count": 6},
        })

    with pytest.raises(ValueError, match="chapter_ref_leak"):
        validate_pdf_release_gates({
            "master": {"composite_score": 50.0, "finding_count": 2, "html": "[[chapter_ref:seo:ch_01]]", "page_count": 18},
        })

    with pytest.raises(ValueError, match="exceeds budget of 22 pages"):
        validate_pdf_release_gates({
            "master": {"composite_score": 50.0, "finding_count": 2, "html": "<p>clean</p>", "page_count": 57},
        })
