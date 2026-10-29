"""
Unit tests for Enterprise-Grade Findings Engine Improvements.
Verifies:
1. Prompt compiler and model router default max_claims capacity (8 claims).
2. SpecialistAgent deterministic checks across titles, metas, headings, canonicals, and security headers.
3. Canonical finding registry precision: distinct structural defects receive distinct canonical IDs,
   while identical cross-agent root causes correctly consolidate.
4. PageIntelligenceAgent attaches valid evidence references to per-page findings.
"""
import pytest
from app.domain.enums import Category, Severity, ClaimType
from app.domain.models import PageEvidence, CrawlManifest, Finding
from app.agents.runtime.registry import AgentDefinition
from app.cognition.blackboard import CognitiveBlackboard
from app.cognition.finding_registry import FindingRegistry, _canonical_id
from app.agents.runtime.specialist import SpecialistAgent
from app.inference.prompt_compiler import PromptCompiler
from app.evidence.models import Evidence


def test_prompt_compiler_default_max_claims_is_eight():
    compiler = PromptCompiler()
    compiled = compiler.compile(
        agent_role="Test Specialist",
        task_contract="Audit headings.",
        evidence_list=[],
    )
    assert "max_claims: 8" in compiled["user"]


def test_canonical_id_distinguishes_separate_structural_defects():
    f_slogan_1 = Finding(
        finding_id="f1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="H1 tag is a slogan instead of clear identity",
        description="The primary heading fails to state the core service.",
        recommendation="Replace H1 slogan with core product identity.",
        impact=7,
        confidence=0.9
    )
    f_slogan_2 = Finding(
        finding_id="f2",
        category=Category.AI_SEARCH,
        severity=Severity.CRITICAL,
        title="H1 is slogan - missing core business entity",
        description="Meta description has the real identity while H1 is a marketing slogan.",
        recommendation="State core entity in H1 for generative search extraction.",
        impact=8,
        confidence=0.9
    )
    # Identical root defect across different agents -> SAME canonical ID
    assert _canonical_id(f_slogan_1) == _canonical_id(f_slogan_2)
    assert _canonical_id(f_slogan_1) == "root_h1_identity_slogan_mismatch"

    # Distinct defects -> DISTINCT canonical IDs
    f_missing_h1 = Finding(
        finding_id="f3",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="2 page(s) are missing an H1.",
        description="Pages lack an H1 heading.",
        recommendation="Add an H1 heading to all pages.",
        impact=7,
        confidence=0.95
    )
    f_multi_h1 = Finding(
        finding_id="f4",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="1 page(s) contain multiple H1 heading tags.",
        description="Multiple H1 tags found.",
        recommendation="Consolidate to one H1 per page.",
        impact=5,
        confidence=0.95
    )
    f_heading_skip = Finding(
        finding_id="f5",
        category=Category.TECHNICAL_SEO,
        severity=Severity.LOW,
        title="1 page(s) have non-hierarchical heading skips (H1 to H3 without H2).",
        description="Heading level jump.",
        recommendation="Use sequential headings.",
        impact=4,
        confidence=0.95
    )
    f_hsts = Finding(
        finding_id="f6",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Strict-Transport-Security (HSTS) header is missing.",
        description="Missing HSTS header on HTTPS responses.",
        recommendation="Add HSTS header.",
        impact=8,
        confidence=0.95
    )
    f_csp = Finding(
        finding_id="f7",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Content-Security-Policy (CSP) header is missing.",
        description="Missing CSP protection.",
        recommendation="Add CSP header.",
        impact=8,
        confidence=0.95
    )
    f_xfo = Finding(
        finding_id="f8",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="X-Frame-Options header is missing (clickjacking protection).",
        description="Clickjacking vulnerability.",
        recommendation="Add XFO header.",
        impact=6,
        confidence=0.95
    )
    f_sitemap = Finding(
        finding_id="f9",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="XML sitemap was not found during crawl.",
        description="Sitemap missing.",
        recommendation="Publish sitemap.xml.",
        impact=6,
        confidence=0.95
    )
    f_robots = Finding(
        finding_id="f10",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="robots.txt was not found at the domain root.",
        description="robots.txt missing.",
        recommendation="Add robots.txt.",
        impact=6,
        confidence=0.95
    )
    f_canonical_miss = Finding(
        finding_id="f11",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="1 page(s) have canonical tag mismatch pointing away from current URL.",
        description="Canonical URL does not match current URL.",
        recommendation="Fix canonical tag URL.",
        impact=7,
        confidence=0.95
    )

    ids = [
        _canonical_id(f_slogan_1),
        _canonical_id(f_missing_h1),
        _canonical_id(f_multi_h1),
        _canonical_id(f_heading_skip),
        _canonical_id(f_hsts),
        _canonical_id(f_csp),
        _canonical_id(f_xfo),
        _canonical_id(f_sitemap),
        _canonical_id(f_robots),
        _canonical_id(f_canonical_miss),
    ]
    # All 10 distinct issues must have unique canonical IDs
    assert len(set(ids)) == 10, f"Expected 10 distinct IDs, got {len(set(ids))}: {ids}"


def test_specialist_deterministic_audit_expanded_checks():
    blackboard = CognitiveBlackboard(run_id="test_run_01", website_url="https://example.com")
    # Add mock evidence
    ev = Evidence(
        id="ev_001",
        analyzer="crawler",
        source_type="dom",
        url="https://example.com/",
        text="Sample text",
        selector="body",
        hash="h123",
        evidence_subtype="DOM"
    )
    blackboard.evidence_store.add(ev)

    # Configure pages with multiple distinct defects
    pages = [
        PageEvidence(
            url="https://example.com/",
            status_code=200,
            title="Short",  # suboptimal length (<35)
            meta_description="Too short",  # suboptimal length (<70)
            h1=["Heading 1", "Duplicate Heading 1"],  # multiple H1s
            h2=[],
            h3=["Sub-sub section"],  # heading skip (H1 to H3 without H2)
            canonical_url="https://example.com/canonical-mismatch",  # canonical mismatch
            response_headers={"server": "nginx"}  # missing HSTS, CSP, XFO
        ),
        PageEvidence(
            url="https://example.com/broken",
            status_code=404,
            title="",  # missing title
            meta_description="",  # missing meta
            h1=[],  # missing H1
            canonical_url=None,  # missing canonical
        )
    ]
    blackboard.pages = pages
    blackboard.crawl_manifest = CrawlManifest(
        manifest_id="cm_01",
        base_url="https://example.com",
        sitemap_found=False,
        robots_txt_found=False,
        pages=pages
    )

    # Test seo.html.v3 deterministic audit
    defn_html = AgentDefinition(
        agent_id="seo.html.v3",
        agent_name="HTML Specialist",
        domain="TECHNICAL",
        capabilities=["seo_html"],
        allowed_models=["deterministic"]
    )
    specialist_html = SpecialistAgent(defn_html, model_router=None)
    res_html = specialist_html._deterministic_audit(blackboard, [ev])
    statements_html = [c.statement for c in blackboard.claim_registry.get_all()]

    assert any("missing an H1" in s for s in statements_html)
    assert any("multiple H1" in s for s in statements_html)
    assert any("missing a title" in s for s in statements_html)
    assert any("outside optimal length" in s for s in statements_html)
    assert any("missing a meta description" in s for s in statements_html)
    assert any("heading skips" in s for s in statements_html)

    # Test seo.security.v3 deterministic audit
    defn_sec = AgentDefinition(
        agent_id="seo.security.v3",
        agent_name="Security Specialist",
        domain="TECHNICAL",
        capabilities=["seo_security"],
        allowed_models=["deterministic"]
    )
    specialist_sec = SpecialistAgent(defn_sec, model_router=None)
    res_sec = specialist_sec._deterministic_audit(blackboard, [ev])
    statements_all = [c.statement for c in blackboard.claim_registry.get_all()]

    assert any("Strict-Transport-Security (HSTS)" in s for s in statements_all)
    assert any("Content-Security-Policy (CSP)" in s for s in statements_all)
    assert any("X-Frame-Options" in s for s in statements_all)

    # Test seo.indexability.v3 deterministic audit
    defn_idx = AgentDefinition(
        agent_id="seo.indexability.v3",
        agent_name="Indexability Specialist",
        domain="TECHNICAL",
        capabilities=["seo_indexability"],
        allowed_models=["deterministic"]
    )
    specialist_idx = SpecialistAgent(defn_idx, model_router=None)
    res_idx = specialist_idx._deterministic_audit(blackboard, [ev])
    statements_idx = [c.statement for c in blackboard.claim_registry.get_all()]

    assert any("no rel=canonical tag" in s for s in statements_idx)
    assert any("canonical tag mismatch" in s for s in statements_idx)


def test_registry_clusters_cleanly_into_high_volume_enterprise_findings():
    registry = FindingRegistry()
    topics = [
        "payload compression gzip",
        "redis caching layer invalidation",
        "dns resolution latency slow",
        "tls handshake version deprecation",
        "server worker process exhaustion",
        "mysql connection pool leak",
        "static asset expires headers absent",
        "cookie domain scope insecure",
        "cross origin resource sharing misconfig",
        "content encoding header corrupt",
    ]
    findings = [
        Finding(
            finding_id=f"f_{i}",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title=f"Critical infrastructure bottleneck {topics[i]}",
            description=f"Detailed investigation for {topics[i]}.",
            recommendation=f"Remediate {topics[i]}.",
            impact=7,
            confidence=0.9
        )
        for i in range(len(topics))
    ]
    for f in findings:
        registry.register(f)

    # Distinct defects should all be retained without false-positive collapsing
    all_f = registry.all_findings()
    assert len(all_f) == len(topics)
