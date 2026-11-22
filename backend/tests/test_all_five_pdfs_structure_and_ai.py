"""Regression tests verifying structure, concrete evidence, and AI analysis across all 5 PDFs."""
from __future__ import annotations

from types import SimpleNamespace

from app.cro.engine import build_cro_intelligence
from app.cro.reporting import build_cro_publication_document
from app.domain.enums import Severity, VerificationStatus
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.reports.ai_report_narrator import _serialize_evidence_context, sync_seo_chapter_narratives_map
from app.reports.narrative_validator import inspect_bundle_for_raw_digits
from app.seo.reporting.seo_book_renderer import CORE_CHAPTERS, _build_chapter_analysis


def _sample_report():
    pages = [
        SimpleNamespace(
            url="https://perforacare.com/",
            status_code=200,
            ttfb_ms=420,
            word_count=850,
            title="Perfora — Science-Backed Oral Care",
            h1=["Better Oral Care"],
            h2=["Electric Toothbrushes", "Mouthwash"],
            h3=[],
            schema_types=["Organization", "Product"],
            body_text="Perfora builds clean oral care products including electric toothbrushes and probiotic mouthwash.",
            meta_description="Clean oral care essentials.",
            is_homepage=True,
        ),
        SimpleNamespace(
            url="https://perforacare.com/products/toothbrush",
            status_code=200,
            ttfb_ms=510,
            word_count=620,
            title="Perfora Electric Toothbrush — Smart Sonic Brush",
            h1=["Smart Sonic Toothbrush"],
            h2=["Features", "Pricing"],
            h3=[],
            schema_types=["Product"],
            body_text="Sonic toothbrush priced at ₹1,499 with 2-minute smart timer.",
            meta_description="Sonic toothbrush details.",
            is_homepage=False,
        ),
    ]
    findings = [
        SimpleNamespace(
            finding_id="FINDING-ECOM-001",
            category="SCHEMA",
            severity=Severity.HIGH,
            priority=8,
            title="Incomplete Product JSON-LD on product pages",
            description="Product JSON-LD is missing offers and description fields.",
            recommendation="Add offers, priceCurrency, and description to Product JSON-LD.",
            why_it_matters="Blocks rich shopping snippets and AI product citations.",
            affected_urls=["https://perforacare.com/products/toothbrush"],
            evidence_refs=["ev_schema_1"],
            verification_status=VerificationStatus.VERIFIED,
            adversarial_reviewed=True,
            verification_notes="[AI Review: CONFIRMED] Observed missing offers in Product JSON-LD.",
        ),
        SimpleNamespace(
            finding_id="FINDING-SERP-001",
            category="ON_PAGE_SEO",
            severity=Severity.MEDIUM,
            priority=6,
            title="Title tags exceed 580px on key landing pages",
            description="Homepage and product titles truncate in Google SERP.",
            recommendation="Tighten title tags below 580px.",
            why_it_matters="Reduces organic CTR.",
            affected_urls=["https://perforacare.com/"],
            evidence_refs=["ev_title_1"],
            verification_status=VerificationStatus.VERIFIED,
            adversarial_reviewed=True,
            verification_notes="[AI Review: CONFIRMED] Title width exceeds 580px.",
        ),
    ]
    ai_bundle = lambda doc_type, ch_id, ch_title, txt: {
        "doc_type": doc_type,
        "format": "pdf",
        "audience": "ceo",
        "tier": "standard",
        "narrative_mode": "ai_full",
        "executive_summary": f"Grounded AI executive thesis for {doc_type.upper()} on perforacare.com.",
        "chapters": [
            {
                "chapter_id": ch_id,
                "title": ch_title,
                "audience": "marketer",
                "executive_takeaway": txt,
                "body_md": f"Deep evidence-grounded AI diagnosis referencing FINDING-ECOM-001 on perforacare.com.",
                "why_it_matters": "Directly improves organic visibility and buyer conversion.",
                "cited_finding_ids": ["FINDING-ECOM-001"],
            }
        ],
    }
    return SimpleNamespace(
        domain="perforacare.com",
        website_url="https://perforacare.com",
        analysis_id="run_test_5pdfs",
        generated_at="2026-11-22T10:00:00Z",
        narrative_mode="ai_full",
        narrative_tier="standard",
        business_profile=SimpleNamespace(business_name="Perfora", industry="Oral Care"),
        crawl_manifest=SimpleNamespace(pages=pages, total_pages_discovered=50, robots_txt_found=True, sitemap_found=True),
        page_reports=pages,
        scores=SimpleNamespace(
            overall_score=72.0,
            overall_grade="C",
            seo_score=78.0,
            geo_score=65.0,
            aeo_score=55.0,
            cro_score=68.0,
            category_scores={
                "TECHNICAL_SEO": SimpleNamespace(score=78.0, status="MEASURED", weight=25.0, weighted_score=19.5, category="TECHNICAL_SEO"),
                "GEO": SimpleNamespace(score=65.0, status="MEASURED", weight=25.0, weighted_score=16.25, category="GEO"),
            },
        ),
        geo_readiness=SimpleNamespace(
            extractability_score=65.0,
            dimension_scores={
                "entity_clarity": SimpleNamespace(score=95.0, band="high", is_measured=True, summary="Clear brand."),
                "citation_readiness": SimpleNamespace(score=62.0, band="medium", is_measured=True, summary="Quotable passages found."),
            },
            dimensions=[],
            questions=[],
            citation_passages={},
        ),
        ai_visibility_scorecard=SimpleNamespace(
            status="NOT_MEASURED",
            successful_runs=0,
            not_measured_reason="OpenRouter key not active in test.",
        ),
        findings=findings,
        document_narratives={
            "executive_pdf": ai_bundle("executive", "ch_brief", "Executive Diagnostic Briefing", "AI Executive Takeaway Complete"),
            "seo_pdf": ai_bundle("seo", "ch_seo_schema", "Structured Data & Schema.org Validation", "AI SEO Schema Takeaway"),
            "geo_pdf": ai_bundle("geo", "ch_geo_extractability", "The 8-Dimension Content Extractability Framework", "AI GEO Extractability Takeaway"),
            "aeo_pdf": ai_bundle("aeo", "ch_aeo_questions", "Question Universe & Search Intent Mapping", "AI AEO Questions Takeaway"),
            "cro_pdf": ai_bundle("cro", "ch_cro_value_prop", "Experience quality", "AI CRO Value Prop Takeaway"),
        },
        chapter_narratives={},
        story_summary="Perfora shows strong technical crawlability with schema gaps.",
        what_site_gets_right=["Clean HTTPS and fast homepage TTFB"],
        what_is_holding_it_back=["Incomplete Product JSON-LD"],
        primary_strategic_opportunity="Complete Product JSON-LD offers and tighten title pixel widths.",
    )


def test_narrative_validator_allows_technical_tokens_but_blocks_fabricated_metrics():
    ok_bundle = {
        "executive_summary": "Missing H1 and HTTP 301 redirect chains affect WCAG 2.2 compliance on FINDING-ECOM-001 (above 580px).",
        "chapters": [],
    }
    assert inspect_bundle_for_raw_digits(ok_bundle) == []

    bad_bundle = {
        "executive_summary": "Fixing this will increase revenue by $45,000 and boost traffic by 37%.",
        "chapters": [],
    }
    assert len(inspect_bundle_for_raw_digits(bad_bundle)) >= 2


def test_evidence_context_extracts_real_urls_and_schemas():
    rep = _sample_report()
    ctx = _serialize_evidence_context(rep, "geo")
    assert ctx["domain"] == "perforacare.com"
    assert len(ctx["sampled_pages"]) == 2
    assert "Product" in ctx["sampled_pages"][0]["schema_types"]
    assert ctx["geo_dimensions"]["entity_clarity"] == "high"


def test_complete_geo_and_aeo_pdfs_include_ai_analysis_and_evidence_tables():
    rep = _sample_report()

    complete_html = render_adaptive_audit_book_html(rep, report_type="COMPLETE")
    assert "AI Executive Takeaway Complete" in complete_html
    assert "https://perforacare.com/products/toothbrush" in complete_html
    assert "Observed First-Party Crawl &amp; DOM Evidence Ledger" in complete_html

    geo_html = render_adaptive_audit_book_html(rep, report_type="GEO")
    assert "AI GEO Extractability Takeaway" in geo_html
    assert "Observed Page-Level Extractability &amp; Schema Evidence" in geo_html

    aeo_html = render_adaptive_audit_book_html(rep, report_type="AEO")
    assert "AI AEO Questions Takeaway" in aeo_html
    assert "https://perforacare.com/" in aeo_html


def test_cro_pdf_renders_ai_analysis_evidence_table_and_collapses_unmeasured_sections():
    rep = _sample_report()
    intel = build_cro_intelligence(pages=rep.crawl_manifest.pages, discovered_urls=50)
    doc = build_cro_publication_document(rep, intel)
    all_html = "\n".join(ch.html_content for part in doc.parts for ch in part.chapters)

    assert "CRO AI Executive Diagnosis" in all_html
    assert "Grounded AI executive thesis for CRO on perforacare.com." in all_html
    assert "Observed Landing &amp; Conversion Page Evidence" in all_html
    assert "Collapsed Unmeasured CRO Sections" in all_html


def test_seo_pdf_merges_seo_pdf_ai_narrative_across_chapter_ids():
    rep = _sample_report()
    merged = sync_seo_chapter_narratives_map(rep.document_narratives["seo_pdf"], {}, CORE_CHAPTERS)
    schema_ch = next(c for c in CORE_CHAPTERS if "schema" in c["id"].lower() or "schema" in c["title"].lower())
    assert schema_ch["id"] in merged
    assert merged[schema_ch["id"]]["executive_summary"] == "AI SEO Schema Takeaway"

    interp = _build_chapter_analysis(
        ch=schema_ch,
        ch_num="05",
        report=rep,
        pages=rep.crawl_manifest.pages,
        ch_findings=[],
        has_failed_metrics=False,
    )
    assert "AI SEO Schema Takeaway" in interp["executive_interpretation"]
