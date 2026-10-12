from pathlib import Path

import pytest
from app.reports.section_exports import section_report_generator
from app.agents.deck.coordinator import generate_section_pptx_deck
from app.domain.models import ExecutiveReport, BusinessProfile, OverallScoreResult, ThreeWayComparison, Finding


def _mock_report() -> ExecutiveReport:
    return ExecutiveReport(
        report_id="rep_test_001",
        analysis_id="run_test_001",
        website_url="https://example.com",
        domain="example.com",
        generated_at="2026-10-11T12:00:00Z",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(
            overall_score=75.0,
            overall_grade="B",
            grade="B",
            health_label="FAIR",
            seo_score=78,
            geo_score=70,
            aeo_score=72,
            cro_score=76,
        ),
        story_summary="Comprehensive digital intelligence audit.",
        primary_strategic_opportunity="Optimize structured data.",
        consultant_advice_what_to_ignore="Ignore vanity metrics.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition.",
            search_engine_perspective="Valid crawl structure.",
            ai_answer_engine_perspective="Citable definitions.",
        ),
        findings=[
            Finding(
                finding_id="f_01",
                category="TECHNICAL_SEO",
                severity="HIGH",
                title="Sitemap missing",
                description="XML sitemap was not discovered during crawl.",
                evidence_id="ev_001",
                recommendation="Publish sitemap.xml",
            ),
            Finding(
                finding_id="f_02",
                category="UX_CONVERSION",
                severity="MEDIUM",
                title="CTA above the fold",
                description="Hero fold lacks high-contrast action button.",
                evidence_id="ev_002",
                recommendation="Add CTA button",
            ),
        ],
    )


def test_section_html_generation():
    rep = _mock_report()
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        html = section_report_generator.render_section_html(rep, sec)
        assert html is not None
        assert "example.com" in html
        assert "<html" in html
        assert "</html>" in html


def test_seo_section_pdf_includes_the_full_index():
    html = section_report_generator.render_section_html(_mock_report(), "seo")
    for title in (
        "01. Executive summary",
        "16. Core Web Vitals and page speed",
        "47. AI search visibility and citation intelligence",
        "55. Monitoring, governance and ongoing SEO operations",
        "O. Glossary",
    ):
        assert title in html
    assert "Largest Contentful Paint (LCP)" in html
    assert "Googlebot and other crawler access differences" in html
    assert "Google AI Overviews and AI Mode" in html
    assert "representative sample" in html.lower()
    assert "Complete SEO audit" in html
    assert html.count("<h4>") >= 70
    assert html.count("<article") >= 700
    assert "Sitemap missing" in html
    assert "Publish sitemap.xml" in html
    assert "agent-consulting-dossier" in html
    assert "seo.crawl.v3" in html
    assert "Executive Diagnostic Review &amp; Strategy" in html
    assert "Prescriptive Engineering &amp; Content Fix" in html
    assert "Sub-Index Evidence &amp; Verification Ledger" in html
    assert "CERTIFIED" not in html
    assert "ZERO-FAKE" not in html
    assert "SINGLE_SOURCE_UNVERIFIED" not in html
    crawl = section_report_generator.render_section_html(_mock_report(), "crawl")
    assert "Complete SEO report index" not in crawl
    assert "Complete SEO audit" not in crawl
    frontend_index = Path(__file__).resolve().parents[2] / "frontend/src/report/auditIndex/catalog.json"
    backend_index = Path(__file__).resolve().parents[1] / "app/reports/seo_audit_index.json"
    assert frontend_index.read_text(encoding="utf-8") == backend_index.read_text(encoding="utf-8")


def test_seo_section_pdf_writes_a_result_for_crawled_evidence():
    from app.domain.models import CrawlManifest, PageEvidence

    report = _mock_report()
    report.crawl_manifest = CrawlManifest(
        domain="example.com",
        total_pages_discovered=5,
        pages=[
            PageEvidence(
                url="https://example.com",
                status_code=200,
                title="Example Corp",
                meta_description="A" * 180,
                h1=["BEYOND IMAGINATION"],
                h2=["Cloud"],
                word_count=152,
                canonical_url=None,
                viewport="width=device-width",
                schema_types=["Organization"],
                images_without_alt=2,
                total_images=4,
                ttfb_ms=291.6,
                html_lang="en",
                security_headers={},
            )
        ],
        robots_txt_found=False,
        sitemap_found=False,
    )
    report.findings.append(
        Finding(
            finding_id="f_03",
            category="ON_PAGE_SEO",
            severity="MEDIUM",
            title="Meta description length",
            description="SINGLE_SOURCE_UNVERIFIED: no usable ext_xxx for this claim family. The meta description is too long.",
            evidence_id="ev_003",
            recommendation="Implement recommended architectural fix based on evidence.",
        )
    )
    html = section_report_generator.render_section_html(report, "seo")
    assert "BEYOND IMAGINATION" in html
    assert "Organization" in html
    assert "291" in html
    assert "180 characters" in html
    assert "robots.txt was not found" in html
    assert "No XML sitemap was recorded" in html
    assert "not a Core Web Vital" in html
    assert "SINGLE_SOURCE_UNVERIFIED" not in html
    assert "ext_xxx" not in html
    assert "Implement recommended architectural fix" not in html
    assert "No specific change was written for this finding." in html
    assert "Issue verified" in html
    assert "Not tested" in html
    assert "Data unavailable" in html
    assert html.count('class="chapter-chart"') >= 70
    assert "HTTP status in the crawled sample" in html
    assert "Crawl response time (ms)" in html
    assert "No forecast chart is drawn" in html
    assert "94% Confidence" not in html
    assert "Fast / Responsive" not in html
    assert "Grounding Verified" not in html
    assert "+12%" not in html
    assert "DETERMINISTIC" not in html
    assert "Zero-Fake" not in html
    assert "83.3" not in html
    assert "Lab performance simulated" not in html


def test_aeo_section_pdf_is_an_evidence_book():
    from app.domain.models import (
        AiVisibilityScorecard,
        DynamicSandboxQuestionEvaluation,
        Finding,
    )

    html = section_report_generator.render_section_html(_mock_report(), "aeo")
    for title in (
        "01. Executive summary",
        "36. Conversational AI and answer platforms",
        "50. AEO opportunity and forecasting model",
        "55. Methodology, governance and evidence integrity",
        "O. Glossary",
    ):
        assert title in html
    assert "representative sample" in html.lower()
    assert "Complete AEO audit" in html
    assert html.count("<h4>") >= 70
    assert html.count("<article") >= 700
    assert "CERTIFIED" not in html
    assert "ZERO-FAKE" not in html
    assert "not a zero" in html.lower()
    assert "No forecast is produced" in html
    assert "0 of 0" not in html
    assert "0.30" not in html
    assert "Citation rate is" not in html
    crawl = section_report_generator.render_section_html(_mock_report(), "crawl")
    assert "Complete AEO audit" not in crawl
    frontend_index = Path(__file__).resolve().parents[2] / "frontend/src/report/aeoIndex/catalog.json"
    backend_index = Path(__file__).resolve().parents[1] / "app/reports/aeo_audit_index.json"
    assert frontend_index.read_text(encoding="utf-8") == backend_index.read_text(encoding="utf-8")

    measured = _mock_report()
    measured.dynamic_sandbox_evaluations = [
        DynamicSandboxQuestionEvaluation(
            question_id="Q-001",
            facet="Pricing",
            generated_question="What does Example Corp charge for onboarding?",
            buyer_intent="A buyer comparing price",
            is_answerable=False,
            answerability_status="UNANSWERABLE",
            crawled_answer="The crawled pages do not state a price.",
            evidence_url="https://example.com/pricing",
            gap_analysis="Price is not stated.",
            citability_score=5,
            projected_patch_gain=0.30,
        )
    ]
    measured.ai_visibility_scorecard = AiVisibilityScorecard(
        successful_runs=4,
        engines_queried=["chatgpt"],
        mention_rate_pct=25,
        citation_rate_pct=None,
        surfaces_not_queried=["Google AI Overviews", "Google AI Mode", "Bing Copilot"],
    )
    measured.findings = list(measured.findings) + [
        Finding(
            finding_id="f_aeo",
            category="SCHEMA",
            severity="MEDIUM",
            title="Organization schema incomplete",
            description="SINGLE_SOURCE_UNVERIFIED ext_xxx Organization node lacks a logo.",
            recommendation="Implement recommended architectural fix based on evidence.",
        )
    ]
    audited = section_report_generator.render_section_html(measured, "aeo")
    assert "What does Example Corp charge for onboarding?" in audited
    assert "UNANSWERABLE" in audited
    assert "0 of 1" in audited
    assert "25%" in audited
    assert "Google AI Overviews" in audited
    assert "Brand recommendation rate was not measured" in audited
    assert "0.30" not in audited
    assert "SINGLE_SOURCE_UNVERIFIED" not in audited
    assert "ext_xxx" not in audited
    assert "No specific change was written for this finding." in audited
    assert "not a Core Web Vital" in audited
    assert "Sample verified · issue" in audited


def test_section_pptx_generation():
    rep = _mock_report()
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        pptx_bytes, blueprint = generate_section_pptx_deck(rep, sec)
        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 1000
        assert blueprint.total_slides > 0


def test_section_html_generation_with_category_score_objects():
    from app.domain.models import CategoryScore, Category
    rep = _mock_report()
    rep.scores.category_scores = {
        "TECHNICAL_SEO": CategoryScore(
            category=Category.TECHNICAL_SEO,
            score=82.4,
            summary="Strong technical foundation.",
        ),
        "GEO": CategoryScore(
            category=Category.GEO,
            score=68.0,
            summary="GEO extractability measured.",
        ),
        "UX_CONVERSION": CategoryScore(
            category=Category.UX_CONVERSION,
            score=74.5,
            summary="UX conversion measured.",
        ),
    }
    for sec in ["crawl", "seo", "geo", "aeo", "cro", "competitors"]:
        html = section_report_generator.render_section_html(rep, sec)
        assert html is not None
        assert "example.com" in html
        assert "<html" in html
        assert "</html>" in html

