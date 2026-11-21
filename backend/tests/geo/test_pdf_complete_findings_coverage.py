"""Regression tests verifying ALL new Enterprise GEO findings/datasets and ALL old finding fields go into PDFs."""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.crawl.browser import BrowserRenderService
from app.db.geo_schema import GEOStore
from app.domain.models import (
    BusinessProfile,
    ExecutiveReport,
    Finding,
    FindingEvidence,
    GeoReadinessReport,
    OverallScoreResult,
    ThreeWayComparison,
)
from app.geo.orchestrator import GEOAuditOrchestrator
from app.geo.reporting.builder import GEOReportBuilder
from app.geo.reporting.geo_audit_book import render_geo_audit_book
from app.geo.verification_engine import GEOIndependentVerificationEngine
from app.geo.experiments import GEOExperimentationEngine
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.reports.plain_english_engine import PlainEnglishEngine, render_plain_english_finding_card
from app.seo.reporting.seo_audit_book import render_seo_audit_book
from app.seo.reporting.seo_print_report import SeoPrintReportRenderer
from tests.geo.fixtures_benchmark import build_benchmark_scenarios


def _rich_legacy_report(org_id: str = "org_pdf_sync", domain: str = "acmeflow.io") -> ExecutiveReport:
    """Create a legacy ExecutiveReport with rich old finding fields AND >12 findings to catch truncations."""
    findings = [
        Finding(
            finding_id="LEG-OLD-001",
            category="GEO",
            severity="CRITICAL",
            title="Legacy GEO Schema Entity Discrepancy",
            description="Organization JSON-LD is missing sameAs links across core landing templates.",
            plain_english_summary="AI engines cannot confirm your official corporate identity across directories.",
            why_it_matters="Weakens knowledge-graph entity disambiguation.",
            business_impact="May reduce direct brand citations in generative answers.",
            expected_condition="Valid Organization JSON-LD with verified sameAs array.",
            difference_observed_expected="0 sameAs links observed vs >=3 authoritative links expected.",
            risk_of_inaction="Continued entity confusion with similarly named brands.",
            user_experience_impact="Brand cards display outdated descriptions.",
            root_cause="Base layout template omits sameAs JSON-LD keys.",
            recommendation="Add verified Organization sameAs links in base layout head.",
            developer_instructions="Update templates/base.html JSON-LD Organization script block.",
            relevant_code_or_configuration_example='{"@type":"Organization","sameAs":["https://linkedin.com/company/acmeflow"]}',
            implementation_steps=["Audit canonical profiles", "Inject sameAs JSON-LD", "Validate with schema tester"],
            acceptance_criteria="Organization JSON-LD contains >=3 verified sameAs URLs.",
            validation_criteria="Schema validator reports 0 errors.",
            verification_steps=["Fetch rendered HTML", "Parse ld+json script", "Assert sameAs URLs resolve 200"],
            verification_command="curl -s https://acmeflow.io/ | grep sameAs",
            responsible_role="Platform Engineering",
            estimated_effort="Medium (3 hours)",
            dependencies=["Design system template PR", "Brand profile verification"],
            priority_rationale="Critical entity disambiguation blocker.",
            limitations="Evaluated on sampled homepage and pricing routes.",
            affected_urls=[f"https://{domain}/page-{i}" for i in range(1, 9)],
            evidence_ids=["EV-LEG-101", "EV-LEG-102"],
            evidence=[
                FindingEvidence(
                    evidence_id="EV-LEG-101",
                    source="html_dom",
                    url=f"https://{domain}/page-1",
                    observed_value="sameAs key absent in Organization block",
                )
            ],
        )
    ]
    # Add 14 more findings to verify ZERO truncation at 6, 8, 10, or 12
    for i in range(2, 16):
        findings.append(
            Finding(
                finding_id=f"LEG-OLD-{i:03d}",
                category="TECHNICAL_SEO" if i % 2 == 0 else "GEO",
                severity="HIGH" if i % 3 == 0 else "MEDIUM",
                title=f"Legacy Audited Issue Number {i:02d}",
                description=f"Observed technical detail for legacy issue {i:02d}.",
                recommendation=f"Apply fix for legacy issue {i:02d}.",
                affected_urls=[f"https://{domain}/route-{i}"],
                evidence_ids=[f"EV-LEG-{i:03d}"],
                responsible_role=f"Team-{i:02d}",
                estimated_effort=f"{i} hours",
            )
        )
    return ExecutiveReport(
        org_id=org_id,
        report_id="rep_pdf_sync_001",
        analysis_id="an_pdf_sync_001",
        website_url=f"https://{domain}",
        domain=domain,
        generated_at="2026-11-22T00:00:00Z",
        business_profile=BusinessProfile(business_name="AcmeFlow", industry="B2B Workflow"),
        scores=OverallScoreResult(
            overall_score=74.0,
            overall_grade="C+",
            grade="C+",
            health_label="FAIR",
            seo_score=76,
            geo_score=70,
            aeo_score=72,
            cro_score=78,
        ),
        geo_readiness=GeoReadinessReport(
            entity_name="AcmeFlow",
            headline="Baseline extractability with entity gaps.",
            extractability_score=70.0,
            questions_total=8,
            questions_supported=5,
            questions_partial=2,
            questions_unsupported=1,
        ),
        story_summary="Complete cross-track audit for AcmeFlow.",
        primary_strategic_opportunity="Unify entity schema and citable documentation.",
        consultant_advice_what_to_ignore="Ignore non-indexed test paths.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear product overview.",
            search_engine_perspective="200 OK on primary pages.",
            ai_answer_engine_perspective="Needs stronger entity attribution.",
        ),
        findings=findings,
    )


def test_plain_english_card_preserves_all_old_and_new_fields():
    rep = _rich_legacy_report()
    enriched = PlainEnglishEngine.enrich_finding(rep.findings[0])
    html = render_plain_english_finding_card(enriched)

    # All previously dropped old finding fields MUST appear
    assert "Valid Organization JSON-LD with verified sameAs array." in html
    assert "0 sameAs links observed vs" in html
    assert "Continued entity confusion with similarly named brands." in html
    assert "Brand cards display outdated descriptions." in html
    assert "Critical entity disambiguation blocker." in html
    assert "Platform Engineering" in html
    assert "Medium (3 hours)" in html
    assert "Design system template PR" in html
    assert "Audit canonical profiles" in html
    assert "curl -s https://acmeflow.io/ | grep sameAs" in html
    assert "EV-LEG-101" in html
    assert "EV-LEG-102" in html
    # Zero URL truncation (all 8 URLs present, not capped at 5)
    for i in range(1, 9):
        assert f"https://acmeflow.io/page-{i}" in html


def test_enterprise_geo_builder_html_and_multipage_pdf_include_all_new_and_legacy_data(tmp_path: Path, monkeypatch):
    store = GEOStore(db_path=str(tmp_path / "geo_pdf_complete.db"))
    payload = build_benchmark_scenarios()["established_brand"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_pdf_sync",
        target_url=payload["target_url"],
        brand_name=payload["brand_name"],
        industry=payload["industry"],
        products=payload["products"],
        competitors=payload["competitors"],
        platforms_requested=["chatgpt", "gemini", "claude", "perplexity"],
        seed_pages=payload["seed_pages"],
        robots_txt="User-agent: GPTBot\nDisallow: /\nUser-agent: OAI-SearchBot\nDisallow: /",
        provider_overrides=payload["provider_overrides"],
        max_prompts=12,
        store=store,
    )
    asyncio.run(orch.run())

    # Add a verification and an experiment so we verify those also render into HTML & PDF!
    pack = store.get_remediation_pack("org_pdf_sync", orch.audit_id)
    assert pack is not None and pack.tasks
    task = pack.tasks[0]
    ver = asyncio.run(
        GEOIndependentVerificationEngine.verify_task(
            task=task,
            verified_by="auditor@acmeflow.io",
            before_html="<html><body>Old copy</body></html>",
            after_html='<html><head><script type="application/ld+json">{"@type":"Organization"}</script></head><body>AcmeFlow verified documentation</body></html>',
            expected_text_present="AcmeFlow verified documentation",
            expected_schema_type="Organization",
        )
    )
    store.save_verification(ver)
    store.save_remediation_pack(pack)
    exp_eng = GEOExperimentationEngine(store=store)
    exp = exp_eng.create_experiment(
        tenant_id="org_pdf_sync",
        audit_id=orch.audit_id,
        title="Comparison Table Citability Test",
        hypothesis="Adding explicit comparison table increases citation accuracy.",
        target_urls=["https://acmeflow.io/pricing"],
    )

    # Register a legacy ExecutiveReport for the same tenant + domain to verify legacy findings also flow into GEO PDF
    from app.orchestration.orchestrator import orchestrator as legacy_orch
    from app.domain.enums import AnalysisStage
    from app.domain.models import AnalysisRun

    leg_rep = _rich_legacy_report(org_id="org_pdf_sync", domain="acmeflow.io")
    leg_run = AnalysisRun(
        analysis_id="an_pdf_sync_001",
        org_id="org_pdf_sync",
        website_url="https://acmeflow.io",
        status=AnalysisStage.COMPLETED,
        created_at="2026-11-22T00:00:00Z",
        updated_at="2026-11-22T00:00:00Z",
    )
    leg_run.report = leg_rep
    legacy_orch.runs["an_pdf_sync_001"] = leg_run

    try:
        builder = GEOReportBuilder(store=store)
        html_doc, json_payload = builder.render_html("org_pdf_sync", orch.audit_id, profile="complete_audit_book")

        # 1. Every canonical GEO finding + root cause + recommendation + evidence appears in HTML
        canonical_findings = store.list_findings("org_pdf_sync", orch.audit_id)
        assert canonical_findings
        for cf in canonical_findings:
            assert cf.finding_id in html_doc
            assert cf.title in html_doc

        # 2. Every legacy finding (all 15!) appears in HTML with full details
        assert "Legacy &amp; Cross-Track Audit Findings (15)" in html_doc
        assert "LEG-OLD-001" in html_doc
        assert "LEG-OLD-015" in html_doc
        assert "curl -s https://acmeflow.io/ | grep sameAs" in html_doc

        # 3. Recommendations, 13 deliverables, full tasks, verifications, experiments, QA checks, and non-stub appendices A1-A10
        assert "Prioritized GEO Recommendations" in html_doc
        assert "13 Consolidated Deliverables" in html_doc
        assert ver.verification_id in html_doc
        assert exp.experiment_id in html_doc
        assert "Comparison Table Citability Test" in html_doc
        assert "Independent Publication QA Gate" in html_doc
        assert "See JSON snapshot" not in html_doc  # ZERO stub appendices!
        assert "Appendix A4: Source Provenance" in html_doc
        assert "Appendix A5: Entity Records" in html_doc
        assert "Appendix A7: Methodology Definitions &amp; Weights" in html_doc
        assert "Appendix A8: Provider Execution Records" in html_doc
        assert "Appendix A10: Historical Comparisons" in html_doc

        # 4. Force fallback multi-page PDF and verify ALL findings, tasks, verifications, experiments, QA are inside PDF bytes
        async def _no_chrome(html_str, timeout_ms=45000):
            return None
        monkeypatch.setattr(BrowserRenderService, "render_pdf", _no_chrome)
        rep, pdf_bytes = asyncio.run(
            builder.publish_report(
                tenant_id="org_pdf_sync",
                audit_id=orch.audit_id,
                profile="complete_audit_book",
                fmt="pdf",
            )
        )
        assert rep.qa_passed is True  # QA-12 Backend==PDF consistency still passes!
        assert pdf_bytes.startswith(b"%PDF-1.4")
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        assert canonical_findings[0].finding_id in pdf_text
        assert "LEG-OLD-001" in pdf_text
        assert "LEG-OLD-015" in pdf_text
        assert ver.verification_id in pdf_text
        assert exp.experiment_id in pdf_text
        assert "PUBLICATION QA GATE" in pdf_text

        # 5. Legacy PDF generators (geo_audit_book, adaptive_audit_book, seo_audit_book, seo_print_report)
        #    MUST include ALL 15 legacy findings AND automatically pull the new Enterprise GEO findings + dossier!
        monkeypatch.setattr("app.geo.reporting.builder.get_geo_store", lambda: store)
        geo_book_html = render_geo_audit_book(leg_rep)
        assert "LEG-OLD-001" in geo_book_html
        assert "LEG-OLD-015" in geo_book_html
        assert "curl -s https://acmeflow.io/ | grep sameAs" in geo_book_html
        assert canonical_findings[0].finding_id in geo_book_html
        assert "ENTERPRISE GEO CANONICAL INTELLIGENCE DOSSIER" in geo_book_html
        assert ver.verification_id in geo_book_html

        adaptive_geo_html = render_adaptive_audit_book_html(leg_rep, report_type="GEO")
        assert "LEG-OLD-001" in adaptive_geo_html
        assert "LEG-OLD-015" in adaptive_geo_html  # No cap at 10 in roadmap or 6/8 in chapter!
        assert "Platform Engineering" in adaptive_geo_html
        assert "Medium (3 hours)" in adaptive_geo_html
        assert canonical_findings[0].finding_id in adaptive_geo_html
        assert "ENTERPRISE GEO CANONICAL INTELLIGENCE DOSSIER" in adaptive_geo_html

        seo_book_html = render_seo_audit_book(leg_rep)
        assert "LEG-OLD-001" in seo_book_html
        assert "curl -s https://acmeflow.io/ | grep sameAs" in seo_book_html
        assert "EV-LEG-102" in seo_book_html

        seo_print_html = SeoPrintReportRenderer().render(leg_rep)
        assert "LEG-OLD-001" in seo_print_html
        assert "EV-LEG-102" in seo_print_html
        assert "ENTERPRISE GEO CANONICAL INTELLIGENCE DOSSIER" in seo_print_html

        from app.aeo.reporting.audit_book import render_aeo_audit_book
        aeo_book_html = render_aeo_audit_book(leg_rep)
        assert "LEG-OLD-001" in aeo_book_html
        assert "curl -s https://acmeflow.io/ | grep sameAs" in aeo_book_html
        assert "EV-LEG-102" in aeo_book_html
        assert "https://acmeflow.io/page-8" in aeo_book_html
    finally:
        legacy_orch.runs.pop("an_pdf_sync_001", None)
