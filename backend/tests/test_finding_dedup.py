"""
Unit Tests for Finding Deduplicator & Root Cause Clustering
Verifies that redundant observations are merged into canonical root cause findings
and total defect counts match the sum of severity breakdown segments exactly (resolving 43 vs 42).
"""
from app.domain.models import Finding, FindingEvidence
from app.domain.enums import Severity, Category, FindingClassification, ImpactLevel, ConfidenceBand
from app.remediation.deduplicator import FindingDeduplicator


def test_deduplicator_clusters_redundant_homepage_findings():
    raw_findings = [
        Finding(
            finding_id="f1",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="Homepage lacks clear value proposition",
            description="The hero text does not communicate the business purpose.",
            recommendation="Rewrite value proposition.",
            evidence=[FindingEvidence(url="https://acme.com/", snippet="Welcome to our platform")]
        ),
        Finding(
            finding_id="f2",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="H1 not descriptive",
            description="H1 contains generic text.",
            recommendation="Change H1 to include core niche.",
            evidence=[FindingEvidence(url="https://acme.com/", snippet="<h1>Solutions</h1>")]
        ),
        Finding(
            finding_id="f3",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="Homepage lacks prominent CTA",
            description="No primary button above the fold.",
            recommendation="Add a clear demo CTA.",
            evidence=[FindingEvidence(url="https://acme.com/", snippet="<a href='/contact'>Click here</a>")]
        ),
        Finding(
            finding_id="f4",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Missing HSTS Header",
            description="Strict-Transport-Security header is not sent.",
            recommendation="Enable HSTS.",
            evidence=[FindingEvidence(url="https://acme.com/", snippet="Strict-Transport-Security: None")]
        ),
        Finding(
            finding_id="f5",
            category=Category.TECHNICAL_SEO,
            severity=Severity.INFO,
            title="Verified Crawl Sample: 5 pages",
            description="Only 5 pages were crawled during this sample.",
            recommendation="Widen crawl if full estate analysis requested.",
        )
    ]

    deduped = FindingDeduplicator.deduplicate(raw_findings)

    # 3 homepage positioning findings should be merged into 1 root cause finding
    # Plus 1 HSTS finding, Plus 1 Crawl Scope finding -> Total 3 findings
    assert len(deduped) == 3

    # Check the clustered root cause finding
    root_hp = next(f for f in deduped if f.root_cause_id == "RC_HOMEPAGE_POSITIONING")
    assert root_hp is not None
    assert len(root_hp.sub_observations) == 3
    assert "Homepage lacks clear value proposition" in root_hp.sub_observations
    assert "H1 not descriptive" in root_hp.sub_observations
    assert "Homepage lacks prominent CTA" in root_hp.sub_observations
    assert len(root_hp.evidence) >= 3

    # Check Crawl Scope is classified as AUDIT_SCOPE_LIMITATION
    scope_f = next(f for f in deduped if f.classification == FindingClassification.AUDIT_SCOPE_LIMITATION)
    assert scope_f.severity == Severity.INFO

    hsts = next(f for f in deduped if f.root_cause_id == "RC_SECURITY_HEADERS")
    assert hsts.calibrated_impact is not None
    assert hsts.calibrated_impact.technical_severity == Severity.HIGH
    assert hsts.calibrated_impact.business_impact == ImpactLevel.MEDIUM
    assert hsts.calibrated_impact.confidence_band == ConfidenceBand.HIGH
    assert hsts.calibrated_impact.is_blocking is False
    assert hsts.calibrated_impact.blocks == []

    # Check mathematical invariant
    sev_counts, total = FindingDeduplicator.get_severity_breakdown(deduped)
    assert total == len(deduped)
    assert total == sum(sev_counts.values())


def test_user_reported_seven_homepage_positioning_findings_cluster_into_one_root_cause():
    """
    Directly tests the 7 redundant findings reported by the user:
    - unclear value proposition
    - homepage lacks clear value proposition
    - H1 not descriptive
    - primary H1 not clear description/value proposition
    - homepage lacks prominent CTA
    - CTA ambiguous
    - homepage positioning unclear
    All 7 must collapse into exactly 1 canonical Root Cause Finding with 7 sub-observations.
    """
    raw_findings = [
        Finding(
            finding_id="f101",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="unclear value proposition",
            description="Hero copy fails to explain core value proposition to visitors.",
            recommendation="Clarify hero value proposition.",
            evidence=[FindingEvidence(url="https://target.com/", selector="div.hero", snippet="Next-generation cloud scale.")]
        ),
        Finding(
            finding_id="f102",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="homepage lacks clear value proposition",
            description="Above-the-fold copy lacks direct statement of value proposition.",
            recommendation="State core transformation promise.",
            evidence=[FindingEvidence(url="https://target.com/", selector="div.hero-sub", snippet="We do things differently.")]
        ),
        Finding(
            finding_id="f103",
            category=Category.ON_PAGE_SEO,
            severity=Severity.HIGH,
            title="H1 not descriptive",
            description="Primary H1 does not contain business service keywords.",
            recommendation="Rewrite H1.",
            evidence=[FindingEvidence(url="https://target.com/", selector="h1", snippet="<h1>Empowering Enterprises</h1>")]
        ),
        Finding(
            finding_id="f104",
            category=Category.ON_PAGE_SEO,
            severity=Severity.HIGH,
            title="primary H1 not clear description/value proposition",
            description="H1 tag is a marketing slogan rather than clear value proposition.",
            recommendation="Replace slogan with clear description.",
            evidence=[FindingEvidence(url="https://target.com/", selector="h1", snippet="<h1>Beyond Boundaries</h1>")]
        ),
        Finding(
            finding_id="f105",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="homepage lacks prominent CTA",
            description="No primary button with high visual contrast above 600px viewport fold.",
            recommendation="Add high-contrast CTA.",
            evidence=[FindingEvidence(url="https://target.com/", selector="a.btn", snippet="<a class='btn'>Learn More</a>")]
        ),
        Finding(
            finding_id="f106",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="CTA ambiguous",
            description="Action copy 'Learn More' is ambiguous and lacks value trigger.",
            recommendation="Make CTA explicit.",
            evidence=[FindingEvidence(url="https://target.com/", selector="a.btn", snippet="<a class='btn'>Click Here</a>")]
        ),
        Finding(
            finding_id="f107",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH,
            title="homepage positioning unclear",
            description="Target audience / ICP and positioning are not explicitly stated.",
            recommendation="Declare target ICP.",
            evidence=[FindingEvidence(url="https://target.com/", selector="p.subhead", snippet="Built for teams.")]
        ),
    ]

    deduped = FindingDeduplicator.deduplicate(raw_findings)

    # All 7 must collapse into exactly 1 canonical root cause finding
    assert len(deduped) == 1
    root = deduped[0]
    assert root.root_cause_id == "RC_HOMEPAGE_POSITIONING"
    assert root.title == "Homepage Value Proposition & Conversion Positioning Ambiguity"
    assert root.severity == Severity.HIGH
    assert root.classification == FindingClassification.VERIFIED_DEFECT

    # Check that all 7 sub-observations are captured
    assert len(root.sub_observations) == 7
    expected_titles = [
        "unclear value proposition",
        "homepage lacks clear value proposition",
        "H1 not descriptive",
        "primary H1 not clear description/value proposition",
        "homepage lacks prominent CTA",
        "CTA ambiguous",
        "homepage positioning unclear",
    ]
    for t in expected_titles:
        assert t in root.sub_observations

    # Check detailed observations have typed attributes
    assert len(root.detailed_observations) == 7
    obs_map = {obs.observation_id: obs for obs in root.detailed_observations}
    assert "f103" in obs_map
    assert obs_map["f103"].selector == "h1"
    assert "Empowering Enterprises" in obs_map["f103"].snippet

    # Check evidence consolidation
    assert len(root.evidence) >= 5

    # Check mathematical invariant
    counts, total = FindingDeduplicator.get_severity_breakdown(deduped)
    assert total == 1
    assert counts[Severity.HIGH.value] == 1


def test_mathematical_consistency_across_simulated_audit_pipeline():
    """
    Simulates a 43-finding scenario:
    - 7 redundant homepage positioning findings
    - 3 security header findings (HSTS, CSP, X-Frame-Options)
    - 2 missing alt text findings
    - 1 crawl scope limitation
    - 30 distinct technical & content findings
    Total raw = 43 findings.
    After canonical deduplication:
    - 7 homepage positioning -> 1 root cause
    - 3 security headers -> 1 root cause
    - 2 missing alt text -> 1 root cause
    - 1 crawl scope -> 1 root cause
    - 30 distinct -> 30
    Total deduplicated = 34 findings.
    Total defects strictly equals sum of donut segments and len(report.findings).
    """
    raw_findings = []
    # 7 homepage positioning findings
    for i in range(7):
        raw_findings.append(
            Finding(
                finding_id=f"hp_{i}",
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                title=f"unclear value proposition {i}" if i == 0 else (
                    "H1 not descriptive" if i == 1 else f"homepage positioning unclear {i}"
                ),
                description="Positioning issue",
                recommendation="Improve positioning.",
                evidence=[FindingEvidence(url="https://site.com/", selector="h1", snippet="Headline")]
            )
        )

    # 3 security header findings
    for h in ["HSTS missing", "Content-Security-Policy missing", "X-Frame-Options missing"]:
        raw_findings.append(
            Finding(
                finding_id=f"sec_{h[:4]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=h,
                description="Security header not present",
                recommendation=f"Configure {h}.",
                evidence=[FindingEvidence(url="https://site.com/", snippet=h)]
            )
        )

    # 2 image accessibility findings
    for a in ["missing alt text on hero", "images lack alt attributes"]:
        raw_findings.append(
            Finding(
                finding_id=f"img_{a[:4]}",
                category=Category.ON_PAGE_SEO,
                severity=Severity.MEDIUM,
                title=a,
                description="Image missing alt",
                recommendation="Add alt tags.",
                evidence=[FindingEvidence(url="https://site.com/", selector="img", snippet="<img src='logo.png'>")]
            )
        )

    # 1 crawl scope limitation
    raw_findings.append(
        Finding(
            finding_id="scope_1",
            category=Category.TECHNICAL_SEO,
            severity=Severity.INFO,
            title="Verified crawl sample: only 5 pages",
            description="5 pages crawled",
            recommendation="Widen crawl scope.",
        )
    )

    # 30 distinct findings
    for i in range(30):
        raw_findings.append(
            Finding(
                finding_id=f"distinct_{i}",
                category=Category.CONTENT if i % 2 == 0 else Category.TECHNICAL_SEO,
                severity=Severity.LOW if i % 3 == 0 else Severity.MEDIUM,
                title=f"Unique Audited Defect #{i:02d} on Architecture Surface",
                description=f"Detailed defect description {i}",
                recommendation=f"Remediate defect {i}.",
                evidence=[FindingEvidence(url=f"https://site.com/p{i}", snippet=f"Snippet {i}")]
            )
        )

    # Total raw count must be 7 + 3 + 2 + 1 + 30 = 43 findings
    assert len(raw_findings) == 43

    # Deduplicate via canonical engine
    deduped = FindingDeduplicator.deduplicate(raw_findings)

    # Expected:
    # 7 homepage -> 1
    # 3 security -> 1
    # 2 alt -> 1
    # 1 scope -> 1
    # 30 distinct -> 30
    # Total = 34
    assert len(deduped) == 34

    # Mathematical invariant check:
    sev_counts, total_defects = FindingDeduplicator.get_severity_breakdown(deduped)
    assert total_defects == len(deduped)
    assert total_defects == sum(sev_counts.values())

    # Check Visual Intelligence Donut chart simulation
    from app.intelligence.monitoring.visual_intelligence import visual_intelligence_engine
    from app.domain.models import BusinessProfile, OverallScoreResult
    from app.domain.enums import BusinessIntent

    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        health_label="Good",
        category_scores={},
        overall_confidence=0.9
    )
    profile = BusinessProfile(
        company_name="Test Enterprise",
        primary_intent=BusinessIntent.LEAD_GENERATION
    )
    intel = visual_intelligence_engine.synthesize_visual_intelligence(
        domain="site.com",
        business_profile=profile,
        scores=scores,
        manifest=None,
        findings=deduped,
    )

    donut_chart = next((c for c in intel.charts if c.id == "chart_defect_donut"), None)
    assert donut_chart is not None
    # Donut total must strictly equal len(deduped)
    assert donut_chart.data["total"] == len(deduped)
    # Sum of segment counts must strictly equal donut total
    segment_sum = sum(s["count"] for s in donut_chart.data["segments"])
    assert segment_sum == len(deduped)
    assert segment_sum == total_defects
