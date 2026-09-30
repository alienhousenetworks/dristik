import pytest
from app.domain.models import Claim, BusinessProfile, Finding
from app.domain.enums import Category, Severity, FindingClassification
from app.cognition.causal import CausalReasoningEngine, CausalBottleneck


def test_causal_bottleneck_synthesis_multi_source():
    engine = CausalReasoningEngine()
    profile = BusinessProfile(
        business_name="Acme SecOps",
        niche="Cloud Security",
        target_audience="Security Engineers",
        business_model="B2B SaaS"
    )

    claims = [
        Claim(id="clm_1", agent_id="agent_1", category=Category.GEO, statement="Advanced enterprise-grade protection for cloud environments"),
        Claim(id="clm_2", agent_id="agent_2", category=Category.UX_CONVERSION, statement="Book a demo to see pricing and plans"),
    ]

    findings = [
        Finding(
            finding_id="f_icp_1",
            category=Category.GEO,
            severity=Severity.HIGH,
            classification=FindingClassification.VERIFIED_DEFECT,
            title="Entity Definition Ambiguity in Hero Section",
            description="The site does not clearly state who the product is built for.",
            recommendation="Clarify ICP in hero fold.",
        ),
        Finding(
            finding_id="f_perf_1",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            classification=FindingClassification.VERIFIED_DEFECT,
            title="Initial Server Response TTFB Exceeds 2500ms",
            description="Measured TTFB of 3120ms severely delays page rendering.",
            recommendation="Deploy CDN caching.",
        ),
        Finding(
            finding_id="f_schema_1",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            classification=FindingClassification.VERIFIED_DEFECT,
            title="Missing Schema.org Organization Graph",
            description="No JSON-LD structured data detected on homepage.",
            recommendation="Add Organization JSON-LD markup.",
        ),
    ]

    summary = {
        "avg_ttfb_ms": 3120.0,
        "missing_h1_count": 0,
    }

    class MockAiEval:
        def __init__(self, was_cited, engine, query):
            self.was_cited = was_cited
            self.engine = engine
            self.query = query

    ai_search_evals = [
        MockAiEval(False, "perplexity", "best cloud secops tools"),
        MockAiEval(False, "chatgpt", "acme security pricing"),
    ]

    chains = engine.analyze_root_causes(
        claims=claims,
        business_profile=profile,
        findings=findings,
        ai_search_evaluations=ai_search_evals,
        crawl_summary=summary,
    )

    assert len(chains) >= 2
    # Verify entity ambiguity chain
    entity_chain = next((c for c in chains if "entity" in c.bottleneck_id), None)
    assert entity_chain is not None
    assert "insufficiently explicit" in entity_chain.inferred_root_cause.lower()
    assert "solutions" in entity_chain.prescribed_remediation.lower()
    assert entity_chain.expected_mechanism != ""
    assert entity_chain.verification_step != ""
    assert entity_chain.projected_outcome != ""
    assert "f_icp_1" in entity_chain.contributing_finding_ids

    # Verify server latency chain
    latency_chain = next((c for c in chains if "latency" in c.bottleneck_id), None)
    assert latency_chain is not None
    assert "3120" in latency_chain.observed_symptoms[0]
    assert "cdn" in latency_chain.prescribed_remediation.lower()
    assert "f_perf_1" in latency_chain.contributing_finding_ids
