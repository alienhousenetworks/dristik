"""Phase 5 tests: Per-page/section AI copywriting with AEO/pillar gaps & tiered model routing,
Frontier AI tech-stack-aware Remediation Pack with anti-fabrication & JSON-LD validation,
dynamic finding-anchored 7/30/90-day + Top-10 Roadmap, and AI Chapter Narratives in orchestrator.
"""
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.crawl.page_intelligence import PageIntelligenceAgent, _observed_sections
from app.domain.enums import Category, Severity
from app.domain.evidence.models import Evidence
from app.domain.models import (
    BusinessProfile,
    DynamicSandboxQuestionEvaluation,
    Finding,
    PageEvidence,
    PageSection,
)
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.remediation.ai_remediation_synthesizer import AiRemediationSynthesizer
from app.reports.roadmap import RoadmapBuilder


@pytest.mark.asyncio
async def test_page_intelligence_uses_real_sections_aeo_gaps_and_no_double_body():
    bb = CognitiveBlackboard(run_id="p5_copy", website_url="https://acme.example/")
    bb.business_profile = BusinessProfile(
        business_name="Acme Cloud",
        industry="B2B SaaS",
        target_audience="Engineering Managers",
        value_proposition="Automated deployment monitoring",
    )
    page = PageEvidence(
        url="https://acme.example/",
        page_type="homepage",
        title="Acme Cloud",
        h1=["Monitor Deployments"],
        word_count=320,
        status_code=200,
        body_text="Monitor Deployments across Kubernetes clusters with instant rollback alerts.",
        ctas=["Start Free Trial"],
        sections=[
            PageSection(
                section_id="sec_hero",
                order=0,
                section_role="hero",
                heading_text="Monitor Deployments",
                heading_level="h1",
                body_text="Monitor Deployments across Kubernetes clusters with instant rollback alerts.",
                word_count=10,
                ctas=["Start Free Trial"],
            ),
        ],
    )
    bb.pages = [page]
    bb.evidence_store.add(
        Evidence(
            id="ev_home_1",
            source_type="page_section",
            analyzer="crawler",
            url=page.url,
            selector="section#sec_hero",
            text=page.body_text,
            content_sha256="c" * 64,
            hash="c" * 64,
        )
    )
    bb.findings = [
        Finding(
            finding_id="f_seo_1",
            category=Category.ON_PAGE_SEO,
            severity=Severity.HIGH,
            title="Homepage title is too short",
            description="Title has only 10 characters.",
            affected_urls=["https://acme.example/"],
        ),
        Finding(
            finding_id="f_fp_1",
            category=Category.TECHNICAL_SEO,
            severity=Severity.INFO,
            title="False positive ecommerce check",
            held_from_executive=True,
            affected_urls=["https://acme.example/"],
        ),
    ]
    bb.dynamic_sandbox_evaluations = [
        DynamicSandboxQuestionEvaluation(
            question_id="Q-001",
            facet="Pricing",
            generated_question="Does Acme Cloud offer a free tier?",
            buyer_intent="Verify entry pricing",
            is_answerable=False,
            answerability_status="EVIDENCE_GAP",
            crawled_answer="Not stated",
            gap_analysis="No pricing tiers published on homepage.",
            recommended_answer="Publish clear tier summary.",
            target_update_page="https://acme.example/",
            citability_score=1,
            projected_patch_gain=0.6,
        )
    ]

    observed = _observed_sections(page)
    assert observed[0]["section_id"] == "sec_hero"
    assert observed[0]["role"] == "hero"

    captured_kwargs = {}

    async def _fake_copy_call(**kwargs):
        captured_kwargs.update(kwargs)
        return {
            "score": 74,
            "seo_score": 70,
            "geo_score": 68,
            "analysis": "Clear hero headline; title tag is too short.",
            "issues": [{"area": "title", "severity": "HIGH", "issue": "Title lacks category keyword", "why_it_matters": "Lowers SERP CTR"}],
            "suggested": {
                "title": "Acme Cloud | Kubernetes Deployment Monitoring",
                "sections": [
                    {
                        "section_id": "sec_hero",
                        "section_name": "Monitor Deployments",
                        "status": "CHANGE_RECOMMENDED",
                        "suggested_copy": "Monitor Kubernetes deployments with instant rollback alerts.",
                    }
                ],
            },
        }

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_copy_call)

    agent = PageIntelligenceAgent(mock_router)
    await agent.run(bb)

    assert mock_router.generate_structured.await_count == 1
    # Verify NO duplicate additional_context body dump!
    assert "additional_context" not in captured_kwargs
    sf = captured_kwargs["site_facts"]
    assert sf["observed_sections"][0]["section_id"] == "sec_hero"
    assert any("Homepage title is too short" in g for g in sf["pillar_audit_gaps"])
    assert not any("False positive" in g for g in sf["pillar_audit_gaps"])
    assert any("Does Acme Cloud offer a free tier?" in q for q in sf["aeo_unanswered_questions"])
    assert captured_kwargs["model_tier"] == "reasoning_model"
    assert len(bb.page_reports) == 1
    assert bb.page_reports[0].copywriting.llm_status == "ok"


@pytest.mark.asyncio
async def test_ai_remediation_synthesizer_validates_stack_jsonld_and_rejects_fabrications():
    pages = [
        PageEvidence(
            url="https://bakery.local/",
            title="Sweet Crumb Bakery",
            word_count=200,
            status_code=200,
            raw_html="<html><head><title>Sweet Crumb Bakery</title></head><body><h1>Artisan Cakes</h1></body></html>",
        )
    ]
    findings = [
        Finding(
            finding_id="f_schema_1",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title="Missing LocalBusiness JSON-LD schema",
            affected_urls=["https://bakery.local/"],
            recommendation="Add LocalBusiness JSON-LD.",
        ),
        Finding(
            finding_id="f_meta_1",
            category=Category.ON_PAGE_SEO,
            severity=Severity.MEDIUM,
            title="Missing meta description",
            affected_urls=["https://bakery.local/"],
            recommendation="Add concise meta description.",
        ),
    ]

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(
        return_value={
            "patches": [
                # Valid JSON-LD patch (with Next.js layout.tsx hallucination -> must be normalized to index.html!)
                {
                    "finding_id": "f_schema_1",
                    "title": "Add LocalBusiness Schema",
                    "category": "SCHEMA",
                    "target_url": "https://bakery.local/",
                    "target_file": "app/layout.tsx",
                    "operation": "INSERT_HEAD",
                    "risk_level": "SAFE_AUTO",
                    "after_snippet": '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Bakery","name":"Sweet Crumb Bakery","url":"https://bakery.local/"}</script>',
                    "explanation": "Adds valid Bakery schema grounded in observed title.",
                },
                # Fabricated LinkedIn URL -> MUST be rejected!
                {
                    "finding_id": "f_meta_1",
                    "title": "Add Social Links",
                    "category": "GEO",
                    "target_url": "https://bakery.local/",
                    "target_file": "index.html",
                    "operation": "INSERT_HEAD",
                    "after_snippet": '<script type="application/ld+json">{"@context":"https://schema.org","sameAs":["https://linkedin.com/company/fake-bakery"]}</script>',
                    "explanation": "Invented social link.",
                },
                # Invalid JSON-LD syntax -> MUST be rejected!
                {
                    "finding_id": "f_schema_1",
                    "title": "Broken JSON-LD",
                    "category": "SCHEMA",
                    "target_url": "https://bakery.local/",
                    "target_file": "index.html",
                    "operation": "INSERT_HEAD",
                    "after_snippet": '<script type="application/ld+json">{broken json</script>',
                    "explanation": "Malformed schema.",
                },
            ]
        }
    )

    synth = AiRemediationSynthesizer(mock_router)
    cp_list, rp_list = await synth.synthesize_patches(
        findings=findings,
        business_profile=BusinessProfile(business_name="Sweet Crumb Bakery", industry="Bakery"),
        website_url="https://bakery.local/",
        pages=pages,
    )

    assert len(cp_list) == 1
    assert len(rp_list) == 1
    assert cp_list[0].target_file == "index.html"  # Non-Next.js site never gets layout.tsx!
    assert rp_list[0].finding_id == "f_schema_1"


@pytest.mark.asyncio
async def test_dynamic_roadmap_has_zero_hardcoded_boilerplate_and_links_real_findings():
    findings = [
        Finding(
            finding_id="f_real_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.CRITICAL,
            title="Product pages blocked by robots.txt",
            recommendation="Remove Disallow: /products/ from robots.txt",
            priority=9,
            effort=2,
        ),
        Finding(
            finding_id="f_real_02",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="Checkout button hidden below fold on mobile",
            recommendation="Add sticky Add-to-Cart bar on product pages.",
            priority=8,
            effort=3,
        ),
    ]

    # Deterministic fallback Top-10 must contain ONLY actions derived from real findings (no 10 boilerplate items!)
    rb = RoadmapBuilder()
    det_plan = rb.build_top_10_actions(findings)
    assert len(det_plan.actions) == 2
    assert {a.related_finding_id for a in det_plan.actions} == {"f_real_01", "f_real_02"}
    assert not any("Define service taxonomy" in a.action for a in det_plan.actions)

    # AI Roadmap synthesis strictly validates related_finding_id against verified findings
    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(
        return_value={
            "roadmap_7_days": [
                {
                    "title": "Unblock /products/ in robots.txt",
                    "description": "Remove disallow rule blocking catalog indexation.",
                    "related_finding_id": "f_real_01",
                    "impact": "High",
                    "effort": "Low",
                    "owner_role": "DevOps",
                    "estimated_hours": "1 hour",
                    "verification_step": "Verify robots.txt returns Allow for /products/",
                },
                {
                    "title": "Bogus unlinked task",
                    "description": "Should be dropped because finding_id does not exist.",
                    "related_finding_id": "f_fake_999",
                },
            ],
            "roadmap_30_days": [],
            "roadmap_90_days": [],
            "top_10_actions": [
                {
                    "priority": "P0",
                    "action": "Unblock /products/ in robots.txt",
                    "related_finding_id": "f_real_01",
                    "impact": "Very High",
                    "effort": "Low",
                    "expected_outcome": "Allows Google and AI crawlers to index product catalog.",
                    "estimated_engineer_hours": 1,
                    "validation": "GET /robots.txt no longer disallows /products/",
                }
            ],
            "dependencies_flow": "Unblock /products/ in robots.txt -> Improve mobile checkout visibility",
        }
    )
    synth = AiRemediationSynthesizer(mock_router)
    res = await synth.synthesize_roadmap(
        findings=findings,
        business_profile=BusinessProfile(business_name="ShopTest"),
        website_url="https://shop.test/",
    )
    assert res is not None
    r7, r30, r90, top10 = res
    assert len(r7) == 1
    assert r7[0].related_finding_id == "f_real_01"
    assert len(top10.actions) == 1
    assert top10.actions[0].related_finding_id == "f_real_01"


def test_orchestrator_uses_ai_chapter_narratives_and_single_pass_ai_remediation():
    src = inspect.getsource(AnalysisOrchestrator._execute_analysis_pipeline_scoped)
    assert "synthesize_chapter_narrative_ai(" in src
    assert "AiRemediationSynthesizer(model_router)" in src
    # Ensure duplicate second build_remediation_plan call was removed
    assert src.count("self.remediation_planner.build_remediation_plan(") == 1
