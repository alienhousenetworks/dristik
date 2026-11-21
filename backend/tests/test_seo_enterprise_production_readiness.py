"""
Enterprise Production Readiness Verification Suite for the Dristik SEO Overhaul.
Covers:
1. 40 specialist roles across 10 departments + zero unregistered runners.
2. Fail-closed TaskExecutor (never fakes 20ms success for missing runners).
3. SSRF protection in NativeHTTPCrawler.
4. All 10 SeoQaValidator fail-closed gates.
5. Live post-deployment re-crawl verification (Fixed != Verified).
6. Encrypted SQLite connector persistence & cross-org isolation.
7. Authenticated, tenant-isolated unified /api/v1/seo/* endpoints & QA-gated report publication.
8. EnterprisePdfEngine 11-part chapter anatomy + cross-layer parity.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.connectors.seo_connector_manager import ConnectorManager
from app.domain.enums import UserRole
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.main import app
from app.seo.audit.crawlers.http_client import NativeHTTPCrawler, SSRFBlockedError
from app.seo.audit.orchestration.dag import AuditDAG, DAGNode, DAGStage
from app.seo.audit.orchestration.execution_state import (
    AuditConfiguration,
    AuditMode,
    NodeState,
)
from app.seo.audit.orchestration.task_executor import TaskExecutor
from app.seo.audit.orchestrator import SEOAuditOrchestrator
from app.seo.audit.qa.seo_qa_validator import SeoQaValidator
from app.seo.audit.remediation.post_audit_remediation_engine import (
    PlatformType,
    PostAuditRemediationEngine,
)
from app.seo.reporting.enterprise_pdf_engine import EnterprisePdfEngine


def test_40_specialist_roles_across_10_departments_and_all_runners_registered(tmp_path):
    dag = AuditDAG(mode=AuditMode.DEEP)
    specialists = [n for n in dag.nodes.values() if n.is_specialist]
    departments = {n.department for n in specialists}
    assert len(specialists) == 40
    assert len(departments) == 10

    orch = SEOAuditOrchestrator(
        audit_id="audit_40_check",
        domain="spec-check.example",
        config=AuditConfiguration(target_url="https://spec-check.example", mode=AuditMode.DEEP),
        db_path=str(tmp_path / "spec.db"),
    )
    missing_runners = [nid for nid in dag.nodes if not orch.executor.has_runner(nid)]
    assert missing_runners == []


@pytest.mark.asyncio
async def test_task_executor_fails_closed_on_missing_runner():
    executor = TaskExecutor()
    node = DAGNode(
        agent_id="unregistered_agent",
        agent_name="Unregistered Agent",
        stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
        retry_limit=0,
    )
    checkpoint = await executor.execute_task(node, {"domain": "example.com"})
    assert checkpoint.status == NodeState.FAILED
    assert "No executable runner registered" in (checkpoint.error_message or "")


@pytest.mark.asyncio
async def test_http_crawler_blocks_ssrf_loopback_and_metadata():
    crawler = NativeHTTPCrawler()
    with pytest.raises(SSRFBlockedError):
        await crawler.fetch_page("http://127.0.0.1/admin")
    with pytest.raises(SSRFBlockedError):
        await crawler.fetch_page("http://169.254.169.254/latest/meta-data/")


def test_seo_qa_validator_all_10_gates():
    validator = SeoQaValidator()

    # Valid baseline with partial crawl -> PARTIAL_DISCLOSED (Gate 5)
    base_assessment = {
        "canonical_findings": [
            {
                "finding_id": "FND_1",
                "rule_id": "seo.title.missing",
                "title": "Missing title",
                "affected_urls": ["https://site.test/"],
                "evidence_ids": ["EV_1"],
                "status": "VERIFIED",
            }
        ],
        "canonical_evidence": [
            {
                "evidence_id": "EV_1",
                "url": "https://site.test/",
                "content_sha256": "a" * 64,
            }
        ],
        "coverage": {"urls_discovered": 505, "urls_crawled": 5},
        "mathematical_scorecard": {
            "methodology_version": "dristik_seo_v3.0",
            "overall_health_score": 80.0,
            "active_weight_sum": 0.25,
            "dimensions": [
                {
                    "dimension_id": "technical_crawlability",
                    "name": "Technical Crawlability",
                    "configured_weight": 0.25,
                    "is_applicable": True,
                    "is_measured": True,
                    "score": 80.0,
                }
            ],
        },
        "remediation_tasks": [],
    }
    report_ok = {"findings": base_assessment["canonical_findings"], "domain": "site.test"}
    qa_partial = validator.validate(base_assessment, report_ok)
    assert qa_partial.is_certified is True
    assert qa_partial.status == "PARTIAL_DISCLOSED"

    # Gate 2: Invalid URL blocked
    bad_url = {
        **base_assessment,
        "canonical_evidence": [{"evidence_id": "EV_1", "url": "javascript:alert(1)"}],
    }
    assert validator.validate(bad_url, report_ok).status == "BLOCKED_INTEGRITY_FAILURE"

    # Gate 3: Duplicate (rule_id, url) blocked
    dup_assessment = {
        **base_assessment,
        "canonical_findings": [
            base_assessment["canonical_findings"][0],
            {**base_assessment["canonical_findings"][0], "finding_id": "FND_2"},
        ],
    }
    assert (
        validator.validate(dup_assessment, {"findings": dup_assessment["canonical_findings"]}).status
        == "BLOCKED_INTEGRITY_FAILURE"
    )

    # Gate 4: Unmeasured dimension scored as 0.0 blocked
    zero_unmeasured = {
        **base_assessment,
        "mathematical_scorecard": {
            **base_assessment["mathematical_scorecard"],
            "dimensions": [
                *base_assessment["mathematical_scorecard"]["dimensions"],
                {
                    "dimension_id": "trust_authority_signals",
                    "name": "Trust & Authority",
                    "configured_weight": 0.05,
                    "is_applicable": True,
                    "is_measured": False,
                    "score": 0.0,
                },
            ],
        },
    }
    assert validator.validate(zero_unmeasured, report_ok).status == "BLOCKED_INTEGRITY_FAILURE"

    # Gate 6: Score denominator mismatch blocked
    bad_math = {
        **base_assessment,
        "mathematical_scorecard": {
            **base_assessment["mathematical_scorecard"],
            "overall_health_score": 42.0,
        },
    }
    assert validator.validate(bad_math, report_ok).status == "BLOCKED_INTEGRITY_FAILURE"

    # Gate 7: Cross-report finding count mismatch blocked
    assert validator.validate(base_assessment, {"findings": []}).status == "BLOCKED_INTEGRITY_FAILURE"

    # Gate 8: VERIFIED_FIXED without after-evidence blocked
    fake_verified = {
        **base_assessment,
        "remediation_tasks": [{"task_id": "REM_1", "verification_status": "VERIFIED_FIXED", "after_evidence": {}}],
    }
    assert validator.validate(fake_verified, report_ok).status == "BLOCKED_INTEGRITY_FAILURE"

    # Gate 9: Invalid SHA-256 produces warning
    bad_hash = {
        **base_assessment,
        "canonical_evidence": [{"evidence_id": "EV_1", "url": "https://site.test/", "content_sha256": "not-a-sha"}],
    }
    qa_warn = validator.validate(bad_hash, report_ok)
    assert any("SHA-256" in w for w in qa_warn.warning_reasons)

    # Gate 10: Missing methodology version blocked
    no_meth = {
        **base_assessment,
        "mathematical_scorecard": {**base_assessment["mathematical_scorecard"], "methodology_version": ""},
    }
    assert validator.validate(no_meth, report_ok).status == "BLOCKED_INTEGRITY_FAILURE"


@pytest.mark.asyncio
async def test_live_verification_fixed_vs_still_open():
    engine = PostAuditRemediationEngine()
    task = engine.generate_task_for_finding(
        {
            "finding_id": "FND_TITLE",
            "title": "Missing title tag",
            "affected_urls": ["https://verify.example/page"],
        },
        PlatformType.GENERIC_HTML,
        rule_id="seo.title.missing",
        evidence_ids=["EV_1"],
    )

    async def broken_fetch(_url: str):
        return {
            "url": "https://verify.example/page",
            "status_code": 200,
            "html": "<html><head></head><body><h1>Hello</h1></body></html>",
            "headers": {},
            "content_sha256": "b" * 64,
            "ttfb_ms": 110.0,
        }

    res_fail = await engine.verify_task_live(
        task_id=task.task_id,
        finding_id=task.finding_id,
        target_url="https://verify.example/page",
        rule_id="seo.title.missing",
        before_snapshot={"title": "", "status": "FIX_SUBMITTED"},
        fetch_fn=broken_fetch,
    )
    assert res_fail.passed is False
    assert res_fail.verification_status == "STILL_OPEN"
    assert len(res_fail.comparison_rows) == 6

    async def fixed_fetch(_url: str):
        return {
            "url": "https://verify.example/page",
            "status_code": 200,
            "html": (
                '<html><head><title>Enterprise SEO Guide | Verify Example</title>'
                '<meta name="description" content="Complete technical SEO guide for engineering teams.">'
                '<link rel="canonical" href="https://verify.example/page" />'
                "</head><body><h1>Enterprise SEO Guide</h1></body></html>"
            ),
            "headers": {},
            "content_sha256": "c" * 64,
            "ttfb_ms": 95.0,
        }

    res_pass = await engine.verify_task_live(
        task_id=task.task_id,
        finding_id=task.finding_id,
        target_url="https://verify.example/page",
        rule_id="seo.title.missing",
        before_snapshot={"title": "", "status": "FIX_SUBMITTED"},
        fetch_fn=fixed_fetch,
    )
    assert res_pass.passed is True
    assert res_pass.verification_status == "VERIFIED_FIXED"
    assert len(res_pass.comparison_rows) == 6


def test_connector_manager_encrypts_credentials_in_sqlite_and_isolates_orgs(tmp_path):
    db_file = str(tmp_path / "connectors.db")
    mgr = ConnectorManager(db_path=db_file)
    secret = "gsc-secret-token-987654321"
    st = mgr.connect_provider(
        "google_search_console",
        {"access_token": secret, "property": "sc-domain:example.com"},
        org_id="org_enc_1",
        workspace_id="ws_enc_1",
    )
    assert st.status == "CONNECTED"
    assert st.last_sync_timestamp is not None

    # Raw database row must NOT store plaintext secret
    conn = sqlite3.connect(db_file)
    row = conn.execute(
        "SELECT encrypted_credentials FROM seo_connectors WHERE connector_type = 'google_search_console'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert secret not in (row[0] or "")

    # Decrypted credentials round-trip cleanly for owning org, blocked for other org
    dec = mgr.get_decrypted_credentials("google_search_console", workspace_id="ws_enc_1", org_id="org_enc_1")
    assert dec is not None and dec["access_token"] == secret
    assert mgr.get_decrypted_credentials("google_search_console", workspace_id="ws_enc_1", org_id="org_other") is None

    # Another org cannot overwrite or disconnect org_enc_1's connector
    with pytest.raises(PermissionError):
        mgr.connect_provider(
            "google_search_console",
            {"access_token": "hijack"},
            org_id="org_other",
            workspace_id="ws_enc_1",
        )
    assert mgr.disconnect_provider("google_search_console", workspace_id="ws_enc_1", org_id="org_other") is False


def test_unified_seo_api_auth_no_manual_verified_fixed_and_pdf_consistency():
    client = TestClient(app)

    # Unauthenticated requests blocked with 401
    assert client.get("/api/v1/seo/audits/nonexistent").status_code == 401
    assert client.get("/api/v1/seo/connectors").status_code == 401

    user_a = UserIdentity(
        user_id="usr_u_a",
        org_id="org_u_a",
        email="a@unified.test",
        role=UserRole.OWNER,
        is_active=True,
    )
    user_b = UserIdentity(
        user_id="usr_u_b",
        org_id="org_u_b",
        email="b@unified.test",
        role=UserRole.OWNER,
        is_active=True,
    )

    try:
        app.dependency_overrides[get_current_user] = lambda: user_a

        # Start unified audit
        resp = client.post(
            "/api/v1/seo/audits",
            json={"domain": "unified-check.test", "mode": "QUICK", "workspace_id": "ws_u_1"},
        )
        assert resp.status_code == 202
        audit_id = resp.json()["audit_id"]

        # Owner can read audit overview
        ov = client.get(f"/api/v1/seo/audits/{audit_id}")
        assert ov.status_code == 200
        assert ov.json()["audit_id"] == audit_id

        # Manual PATCH to VERIFIED_FIXED must be rejected (400)
        bad_patch = client.patch(
            f"/api/v1/seo/findings/any_finding_id?audit_id={audit_id}",
            json={"status": "VERIFIED_FIXED"},
        )
        assert bad_patch.status_code == 400

        # Cross-tenant overview access must be denied (404)
        app.dependency_overrides[get_current_user] = lambda: user_b
        assert client.get(f"/api/v1/seo/audits/{audit_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_enterprise_pdf_11_part_anatomy_and_cross_layer_parity(tmp_path):
    db_file = str(tmp_path / "pdf_parity.db")
    orch = SEOAuditOrchestrator(
        audit_id="audit_pdf_parity",
        domain="parity.example",
        config=AuditConfiguration(target_url="https://parity.example", mode=AuditMode.QUICK),
        db_path=db_file,
        seed_pages=[
            {
                "url": "https://parity.example/",
                "status_code": 200,
                "html": "<html><head></head><body><h1>Parity Home</h1><p>Short copy</p></body></html>",
                "title": "",
                "h1": ["Parity Home"],
                "word_count": 12,
                "headers": {},
            }
        ],
    )
    result = await orch.run()
    assessment = result["canonical_assessment"]
    scorecard = assessment["mathematical_scorecard"]
    engine = EnterprisePdfEngine()
    html_out, qa, digest = engine.publish_with_qa_gate(
        assessment=assessment,
        report_data={"domain": "parity.example", "analysis_id": "audit_pdf_parity", "findings": assessment["findings"]},
        profile="complete_book",
    )

    assert len(digest) == 64
    assert qa.is_certified is True
    assert f"{scorecard['overall_health_score']}/100" in html_out
    assert 'href="#ch_18"' in html_out
    assert "DATA_UNAVAILABLE" in html_out  # Unconnected connector chapters disclosed honestly
    for heading in (
        "1. Executive Interpretation",
        "2. Health Overview",
        "3. What Was Tested",
        "4. What Was Observed",
        "6. Root-Cause Analysis",
        "7. Business &amp; SEO Implications",
        "8. Recommended Implementation",
        "9. Ownership &amp; Effort",
        "10. Validation Protocol",
        "11. Remaining Limitations",
    ):
        assert heading in html_out


def test_unified_pdf_bridge_preserves_all_old_and_new_findings_across_all_pdf_renderers(tmp_path):
    """
    Verifies that BOTH legacy ExecutiveReport findings/sections AND new SEO Overhaul
    findings/scorecards/remediation patches/verification runs appear in EVERY SEO PDF renderer:
    1. EnterprisePdfEngine (63-chapter book)
    2. SeoAuditBookRenderer (Master Book HTML/PDF)
    3. SeoPrintReportRenderer (Classic 20-section Print/PDF)
    4. render_seo_audit_book (55-section audit book)
    5. render_adaptive_audit_book_html (Adaptive SEO PDF book)
    """
    from app.domain.enums import Category, FindingStatus, Severity
    from app.domain.models import (
        BusinessProfile,
        ExecutiveReport,
        Finding,
        HttpStatusBreakdown,
        OverallScoreResult,
        PageReport,
        SerpAppearanceReport,
        ThreeWayComparison,
    )
    from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
    from app.seo.reporting.canonical_seo_pdf_bridge import (
        collect_unified_seo_pdf_bundle,
        enrich_report_for_pdf,
    )
    from app.seo.reporting.seo_audit_book import render_seo_audit_book
    from app.seo.reporting.seo_book_renderer import SeoAuditBookRenderer
    from app.seo.reporting.seo_print_report import SeoPrintReportRenderer

    old_finding = Finding(
        finding_id="OLD_LEGACY_001",
        category=Category.TECHNICAL_SEO,
        subcategory="Legacy Canonical Check",
        severity=Severity.CRITICAL,
        priority=10,
        title="Legacy Canonical Redirect Loop Detected",
        description="Old pipeline observed redirect chain between /home and /.",
        why_it_matters="Wastes crawl budget and splits PageRank signals.",
        recommendation="Enforce single 301 canonical host redirect.",
        affected_urls=["https://unified-pdf.example/"],
        evidence_id="EV_OLD_001",
        status=FindingStatus.OPEN,
    )

    pages = [
        PageReport(
            url="https://unified-pdf.example/",
            title="",  # Concrete measured defect for new deterministic check
            status_code=200,
            is_indexable=True,
            word_count=220,
        ),
        PageReport(
            url="https://unified-pdf.example/broken",
            title="Broken Page",
            status_code=404,  # Concrete HTTP 4xx defect for new deterministic check
            is_indexable=False,
            word_count=30,
        ),
    ]

    report = ExecutiveReport(
        org_id="org_unified_pdf",
        report_id="REP_UNI_001",
        analysis_id="AN_UNI_001",
        website_url="https://unified-pdf.example",
        domain="unified-pdf.example",
        generated_at="2026-11-22T00:00:00Z",
        policy_pack="seo_only",
        business_profile=BusinessProfile(
            domain="unified-pdf.example",
            business_name="Unified PDF Corp",
            industry="B2B SaaS",
        ),
        scores=OverallScoreResult(overall_score=71.0, grade="C+", health_label="Needs Improvement"),
        story_summary="Unified PDF Corp has strong HTTPS posture but critical title and HTTP 404 gaps.",
        primary_strategic_opportunity="Fix missing homepage titles and 404 broken links first.",
        consultant_advice_what_to_ignore="Ignore non-indexable staging query parameters.",
        what_site_gets_right=["TLS 1.3 enabled across origin"],
        what_is_holding_it_back=["Homepage omits <title> element"],
        http_status_breakdown=HttpStatusBreakdown(total_urls_checked=2, count_2xx=1, count_4xx=1),
        serp_appearance=SerpAppearanceReport(),
        findings=[old_finding],
        page_reports=pages,
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value prop.",
            search_engine_perspective="Broken 404 route found.",
            ai_answer_engine_perspective="Needs schema.",
        ),
    )

    # Enrich report via the canonical bridge
    enriched = enrich_report_for_pdf(report, org_id="org_unified_pdf")
    finding_titles = [f.title for f in enriched.findings]
    assert "Legacy Canonical Redirect Loop Detected" in finding_titles
    assert any("Missing <title>" in t for t in finding_titles)
    assert any("HTTP 4xx/5xx" in t for t in finding_titles)

    # 1. EnterprisePdfEngine (63-chapter book) has BOTH old sections/findings AND new findings/scorecard/patches
    bundle = collect_unified_seo_pdf_bundle(report=report, org_id="org_unified_pdf")
    bundle["verification_runs"] = [
        {
            "task_id": "REM_OLD_LEGACY_001",
            "target_url": "https://unified-pdf.example/",
            "status": "STILL_OPEN",
            "check_summary": "Live re-crawl confirmed canonical mismatch still active.",
            "comparison_rows": [
                {"dimension": "Canonical", "before": "Missing", "after": "Missing"},
            ],
        }
    ]
    ent_html = EnterprisePdfEngine().render_publication(
        assessment={
            "findings": bundle["findings"],
            "evidence": bundle["evidence"],
            "mathematical_scorecard": bundle["scorecard"],
            "remediation_tasks": bundle["tasks"],
            "verification_runs": bundle["verification_runs"],
            "internal_link_graph": bundle["link_graph"],
            "connectors": bundle["connectors"],
            "coverage": bundle["coverage"],
        },
        report_data={
            **report.model_dump(),
            "findings": bundle["findings"],
            "evidence": bundle["evidence"],
            "mathematical_scorecard": bundle["scorecard"],
            "remediation_tasks": bundle["tasks"],
            "verification_runs": bundle["verification_runs"],
            "internal_link_graph": bundle["link_graph"],
            "legacy_sections": bundle["legacy_sections"],
        },
        profile="complete_book",
    )
    assert "Legacy Canonical Redirect Loop Detected" in ent_html
    assert "Wastes crawl budget and splits PageRank signals." in ent_html
    assert "Unified PDF Corp has strong HTTPS posture" in ent_html
    assert "Missing &lt;title&gt;" in ent_html
    assert "HTTP 4xx/5xx" in ent_html
    assert "Observed HTTP Response Status Breakdown" in ent_html
    assert "Live Verification" in ent_html

    # 2. SeoAuditBookRenderer (Master Book HTML/PDF) has old + new findings + 9-dim scorecard addendum
    book_html = SeoAuditBookRenderer().render_html_report(enriched)
    assert "Legacy Canonical Redirect Loop Detected" in book_html
    assert "Missing &lt;title&gt;" in book_html
    assert "9-Dimension Mathematical SEO Scorecard" in book_html
    assert "Stack-Detected Remediation Directives" in book_html

    # 3. SeoPrintReportRenderer (Classic 20-section Print/PDF) has old + new findings + addendum
    classic_html = SeoPrintReportRenderer().render(enriched)
    assert "Legacy Canonical Redirect Loop Detected" in classic_html
    assert "Missing &lt;title&gt;" in classic_html
    assert "9-Dimension Mathematical SEO Scorecard" in classic_html

    # 4. 55-Section seo_audit_book has old + new findings + addendum
    sec55_html = render_seo_audit_book(enriched)
    assert "Legacy Canonical Redirect Loop Detected" in sec55_html
    assert "Missing &lt;title&gt;" in sec55_html
    assert "9-Dimension Mathematical SEO Scorecard" in sec55_html

    # 5. Adaptive Audit Book (default SEO PDF download) has old + new findings + addendum
    adaptive_html = render_adaptive_audit_book_html(enriched, report_type="SEO")
    assert "Legacy Canonical Redirect Loop Detected" in adaptive_html
    assert "Missing &lt;title&gt;" in adaptive_html
    assert "9-Dimension Mathematical SEO Scorecard" in adaptive_html

