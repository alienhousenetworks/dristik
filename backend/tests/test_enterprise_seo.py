"""Enterprise SEO stays inside the evidence it was given."""

from app.domain.models import PageEvidence
from app.seo.enterprise.agents import AGENT_CATALOG, execution_order
from app.seo.enterprise.assess import build_enterprise_seo
from app.seo.enterprise.contracts import EnterpriseFinding
from app.seo.enterprise.lifecycle import LifecycleError, transition
from app.seo.enterprise.policy import SHARED_POLICY
from app.seo.enterprise.report_html import render_enterprise_appendix
from app.seo.enterprise.rules import UnknownExpression, evaluate_condition
from app.seo.enterprise.taxonomy import CHAPTERS


def _chapter(assessment, number):
    return next(chapter for chapter in assessment.chapters if chapter.chapter == number)


def _sub(chapter, subchapter_id):
    return next(sub for sub in chapter.subchapters if sub.subchapter_id == subchapter_id)


def test_catalog_has_35_specialists_and_an_acyclic_order():
    from app.seo.enterprise.ai_catalog import AI_AGENTS

    ids = [agent.agent_id for agent in AGENT_CATALOG]
    assert len(AI_AGENTS) == 25
    assert len(ids) == 35 + len(AI_AGENTS)
    assert len(set(ids)) == len(ids)
    assert "seo.crawlability.v1" in ids
    assert "seo.fix_verification.v1" in ids
    assert "seo.ai.content_completeness.v1" in ids
    assert "seo.ai.query_page_mapping.v1" not in ids
    assert not any(agent_id.startswith(("aeo.", "geo.", "cro.")) for agent_id in ids)
    order = execution_order()
    assert order[0] in {"seo.crawlability.v1", "seo.http_redirects.v1", "seo.rendering_js.v1"}
    assert order.index("seo.evidence_adjudicator.v1") < order.index("seo.ai.confidence_reviewer.v1")
    assert order.index("seo.ai.confidence_reviewer.v1") < order.index("seo.roadmap.v1")
    assert order.index("seo.roadmap.v1") < order.index("seo.fix_verification.v1")
    for agent in AGENT_CATALOG:
        assert "Do not score AEO, GEO, or CRO." in SHARED_POLICY
        assert len(agent.dedicated_prompt) > 80
        assert agent.policy_requirements == ["seo.specialist.shared.v1"]
        if agent.agent_id.startswith("seo.ai."):
            assert agent.prompt_source == "versioned_file"
            assert agent.prompt_sha256
            assert agent.execution_mode == "interpretive"
        else:
            assert agent.prompt_source == "inline_role"


def test_taxonomy_has_28_chapters():
    assert len(CHAPTERS) == 28
    assert CHAPTERS[0].subchapters[0].subchapter_id == "1.1"
    assert CHAPTERS[-1].number == 28


def test_rule_evaluator_rejects_code():
    try:
        evaluate_condition("__import__('os').system('echo no')", {})
        raised = False
    except UnknownExpression:
        raised = True
    assert raised


def test_lifecycle_blocks_unverified_closure():
    assert transition("open", "in_progress") == "in_progress"
    try:
        transition("open", "verified")
        raised = False
    except LifecycleError:
        raised = True
    assert raised


def test_empty_report_does_not_invent_a_score_or_a_failure():
    assessment = build_enterprise_seo({"analysis_id": "run_empty", "domain": "example.com"})
    assert assessment.scores[0].status == "not_scored"
    assert assessment.scores[0].score is None
    assert assessment.findings == []
    assert "not a complete site audit" not in assessment.coverage.statement.lower() or assessment.coverage.urls_crawled is None
    search = next(agent for agent in assessment.agents if agent.agent_id == "seo.search_console.v1")
    assert search.status == "unavailable"
    assert _chapter(assessment, 22).status == "DATA_UNAVAILABLE"
    assert _chapter(assessment, 18).status == "NOT_TESTED"
    html = render_enterprise_appendix({"analysis_id": "run_empty", "domain": "example.com"})
    assert "Not scored" in html
    assert "{{" not in html
    assert "CERTIFIED" not in html
    assert "84.5" not in html


def test_missing_title_stays_on_the_checked_urls():
    report = {
        "analysis_id": "run_titles",
        "domain": "example.com",
        "generated_at": "2026-10-18T00:00:00Z",
        "crawl_manifest": {
            "sampling_status": "SAMPLED_AUDIT",
            "total_pages_discovered": 100,
            "total_pages_crawled": 2,
            "robots_txt_found": True,
            "robots_txt_content": "User-agent: *\nDisallow:\n",
            "sitemap_found": True,
            "sitemap_urls": ["https://example.com/a"],
        },
        "meta_rollup": {
            "total_pages_evaluated": 2,
            "missing_titles": [{"url": "https://example.com/a", "text": "", "char_length": 0}],
            "duplicate_titles": [],
            "too_short_titles": [{"url": "https://example.com/b", "text": "Hi", "char_length": 2}],
            "too_long_titles": [],
            "missing_descriptions": [],
            "duplicate_descriptions": [],
        },
        "heading_hierarchy": {
            "total_pages_evaluated": 2,
            "missing_h1": [],
            "multiple_h1": [{"url": "https://example.com/b", "headings": ["One", "Two"]}],
            "hierarchy_violations": [],
        },
    }
    first = build_enterprise_seo(report)
    second = build_enterprise_seo(report)
    missing = next(finding for finding in first.findings if finding.rule_id == "seo.title.missing")
    assert missing.affected_urls == ["https://example.com/a"]
    assert missing.affected_count == 1
    assert missing.eligible_count == 2
    assert missing.scope == "PAGE_VERIFIED"
    assert "100" in " ".join(missing.limitations)
    assert missing.evidence_ids
    assert missing.evidence_ids[0] in {item.evidence_id for item in first.evidence}
    assert missing.evaluation_state == "ISSUE_VERIFIED"
    assert missing.claim_kind == "observed"
    assert missing.code_examples == []
    assert missing.investigation_targets
    assert "visits" not in missing.business_impact
    assert "revenue" not in missing.business_impact
    assert missing.verification_status == "NOT_VERIFIABLE"
    assert missing.status == "open"
    length = next(finding for finding in first.findings if finding.rule_id == "seo.title.length")
    assert length.severity == "info"
    assert length.issue_type == "diagnostic"
    multiple = next(finding for finding in first.findings if finding.rule_id == "seo.heading.multiple_h1")
    assert multiple.issue_type == "diagnostic"
    assert "ranking violation" in multiple.seo_significance
    assert [finding.finding_id for finding in first.findings] == [finding.finding_id for finding in second.findings]
    card = next(item for item in first.cards if item.finding_id == missing.finding_id)
    assert card.complete
    assert len(card.sections) == 18
    assert _sub(_chapter(first, 10), "10.2").status == "NOT_TESTED"
    assert _chapter(first, 10).status != "NO_ISSUE"


def test_security_header_is_not_a_ranking_claim():
    assessment = build_enterprise_seo({
        "analysis_id": "run_security",
        "domain": "example.com",
        "security_audit": {"target_domain": "example.com", "hsts_enabled": False, "summary": "HSTS absent"},
    })
    finding = next(item for item in assessment.findings if item.rule_id == "seo.security.header")
    assert finding.issue_type == "observation"
    assert "not evidence" in finding.seo_significance
    assert "ranking" in finding.seo_significance


def test_soft_404_and_field_vitals_are_not_inferred():
    page = PageEvidence(url="https://example.com/", status_code=200, title="Example", ttfb_ms=800, word_count=200)
    assessment = build_enterprise_seo({
        "analysis_id": "run_http",
        "domain": "example.com",
        "crawl_manifest": {
            "total_pages_crawled": 1,
            "total_pages_discovered": 1,
            "pages": [page.model_dump()],
            "robots_txt_found": True,
            "robots_txt_content": "User-agent: *\nAllow: /\n",
            "sitemap_found": True,
            "sitemap_urls": ["https://example.com/"],
        },
    })
    assert not any(finding.rule_id == "seo.index.soft404" for finding in assessment.findings)
    assert not any(finding.rule_id.startswith("seo.cwv.") for finding in assessment.findings)
    assert _sub(_chapter(assessment, 18), "18.1").status == "NOT_TESTED"
    assert "not used as LCP" in _sub(_chapter(assessment, 18), "18.1").note or "not used as LCP" in _sub(_chapter(assessment, 18), "18.4").note


def test_disallow_all_is_a_crawl_block_not_a_deindexation():
    assessment = build_enterprise_seo({
        "analysis_id": "run_robots",
        "domain": "example.com",
        "crawl_manifest": {
            "robots_txt_found": True,
            "robots_txt_content": "User-agent: *\nDisallow: /\n",
            "sitemap_found": False,
        },
    })
    finding = next(item for item in assessment.findings if item.rule_id == "seo.robots.disallow_all")
    assert finding.severity == "critical"
    assert finding.scope == "PAGE_VERIFIED"
    assert "not proof" in finding.seo_significance


def test_international_absence_is_not_a_defect():
    assessment = build_enterprise_seo({
        "analysis_id": "run_locale",
        "domain": "example.com",
        "international_seo": {"status": "NOT_APPLICABLE", "is_multilingual": False, "issues": []},
    })
    assert _chapter(assessment, 9).status == "NOT_APPLICABLE"
    assert not any(finding.chapter == 9 for finding in assessment.findings)


def test_adjudicator_rejects_a_sitewide_leap():
    from app.seo.enterprise.assess import _Builder

    builder = _Builder({"analysis_id": "run_reject", "domain": "example.com"})
    finding = EnterpriseFinding(
        finding_id="f_test",
        audit_run_id="run_reject",
        rule_id="seo.title.missing",
        rule_version="1.0.0",
        rule_class="mandatory",
        title="Missing title",
        category="titles",
        chapter=10,
        subchapters=["10.1"],
        severity="high",
        issue_type="defect",
        scope="SITE_INFERRED",
        affected_urls=["https://example.com/"],
        affected_count=1,
        eligible_count=1,
        evidence_ids=["ev_missing"],
        observed_condition="The title is empty.",
        expected_condition="The title is present.",
        simple_explanation="The page has no title.",
        seo_significance="The title link is uncontrolled.",
        root_cause_hypothesis="Unknown.",
        cause_label="unknown",
        remediation_steps=["Add a title."],
        acceptance_tests=["The fresh snapshot has a title."],
        regression_risk="A template change can affect other pages.",
        confidence=0.9,
    )
    builder.proposed.append(finding)
    assert builder._adjudicate() == []
    assert builder.rejected[0].reason.startswith("A sample was generalized")


def test_verified_fix_requires_a_fresh_snapshot_state():
    assessment = build_enterprise_seo({
        "analysis_id": "run_verify",
        "domain": "example.com",
        "meta_rollup": {
            "total_pages_evaluated": 1,
            "missing_titles": [{"url": "https://example.com/"}],
        },
    })
    verifier = next(agent for agent in assessment.agents if agent.agent_id == "seo.fix_verification.v1")
    assert verifier.status == "completed"
    assert assessment.report_stage == "preliminary"
    assert all(finding.verification_status == "NOT_VERIFIABLE" for finding in assessment.findings)


def test_gap_matrix_reuses_existing_agents_and_defers_other_disciplines():
    from app.seo.enterprise.gap import DEFERRED_MODULES, REUSED, gap_matrix

    matrix = gap_matrix()
    assert matrix["missing_or_duplicated"] == []
    assert "seo.ai.content_completeness.v1" in matrix["implemented_ai"]
    assert "seo.ai.query_page_mapping.v1 -> seo.keyword_mapping.v1" in matrix["reused"]
    assert REUSED["seo.ai.evidence_critic.v1"] == "seo.evidence_adjudicator.v1"
    assert "Content writing" in DEFERRED_MODULES
    assert "Code remediation" in DEFERRED_MODULES
    assert "GEO intelligence" in matrix["deferred"]


def test_default_ai_pass_loads_prompts_and_publishes_no_judgment():
    page = PageEvidence(
        url="https://example.com/guide",
        title="Example guide",
        body_text="Example guide explains the installation steps for the hosted product in one short paragraph.",
        word_count=12,
    )
    assessment = build_enterprise_seo({
        "analysis_id": "run_ai_off",
        "domain": "example.com",
        "crawl_manifest": {"total_pages_crawled": 1, "pages": [page.model_dump()]},
    })
    specialists = [agent for agent in assessment.agents if agent.agent_id.startswith("seo.ai.")]
    assert len(specialists) == 25
    assert all(agent.status == "unavailable" for agent in specialists)
    assert all(agent.prompt_sha256 for agent in specialists)
    assert not any(finding.rule_id.startswith("seo.ai.") for finding in assessment.findings)
    assert "content writing" in assessment.diagnostic_summary
    assert "GEO" in assessment.diagnostic_summary
    html = render_enterprise_appendix({
        "analysis_id": "run_ai_off",
        "domain": "example.com",
        "crawl_manifest": {"total_pages_crawled": 1, "pages": [page.model_dump()]},
    })
    assert "Not executed in this phase" in html
    assert "replacement copy" in html or "No patch was generated" in html


def test_ai_runner_receives_the_versioned_prompt_and_must_cite_evidence():
    import json
    import re

    from app.seo.enterprise.prompt_store import render_system_prompt

    system, _version, digest = render_system_prompt("seo.ai.content_completeness.v1")
    assert digest == next(agent.prompt_sha256 for agent in AGENT_CATALOG if agent.agent_id == "seo.ai.content_completeness.v1")
    assert "You are `seo.ai.content_completeness.v1`" in system
    assert "Do not score AEO, GEO, or CRO." in system
    calls = []

    def runner(prompt: str, user: str, timeout_seconds: int):
        assert timeout_seconds >= 1
        agent_id = re.search(r"You are `([^`]+)`", prompt).group(1)
        calls.append(agent_id)
        assert "Do not generate remediation code or replacement copy." in prompt
        assert SHARED_POLICY in prompt
        packet = json.loads(user)
        assert packet["instruction"]
        if agent_id != "seo.ai.content_completeness.v1":
            return {"agent_id": agent_id, "version": "1.0.0", "status": "completed", "findings": []}
        page = packet["pages"][0]
        return {
            "agent_id": agent_id,
            "version": "1.0.0",
            "status": "completed",
            "findings": [{
                "url": page["url"],
                "evidence_ids": [page["evidence_id"]],
                "observation": "The supplied passage names installation and does not explain the steps.",
                "explanation": "The body is a single sentence, so the steps the title suggests are not in the passage.",
                "why_it_matters": "A reader who reached this page for the installation steps would not find them in the supplied text.",
                "severity": "low",
                "confidence": 0.4,
                "confidence_rationale": "Only one passage was supplied, so the judgment is limited to that passage.",
                "evaluation_state": "INFERRED",
                "claim_kind": "judgment",
                "investigation": ["Inspect the page purpose before treating the short passage as a defect."],
                "verification_criteria": ["A later crawl stores a passage that states the installation steps."],
                "limitations": ["No query log was supplied."],
            }],
        }

    page = PageEvidence(
        url="https://example.com/guide",
        title="Installation guide",
        body_text="Installation guide for the hosted product.",
        word_count=6,
    )
    report = {
        "analysis_id": "run_ai_on",
        "domain": "example.com",
        "crawl_manifest": {"total_pages_crawled": 1, "total_pages_discovered": 1, "pages": [page.model_dump()]},
    }
    assessment = build_enterprise_seo(report, ai_runner=runner)
    assert "seo.ai.content_completeness.v1" in calls
    assert "seo.ai.search_intent.v1" not in calls
    assert "seo.ai.opportunity_analysis.v1" not in calls
    assert "seo.crawlability.v1" not in calls
    finding = next(item for item in assessment.findings if item.rule_id == "seo.ai.content_completeness.v1")
    assert finding.evaluation_state == "INFERRED"
    assert finding.claim_kind == "judgment"
    assert finding.code_examples == []
    assert finding.scope == "PAGE_VERIFIED"
    assert finding.evidence_ids[0] in {item.evidence_id for item in assessment.evidence}
    assert _sub(_chapter(assessment, 13), "13.1").status == "INFERRED"

    def ungrounded(prompt: str, user: str, timeout_seconds: int):
        agent_id = re.search(r"You are `([^`]+)`", prompt).group(1)
        if agent_id != "seo.ai.content_completeness.v1":
            return {"agent_id": agent_id, "version": "1.0.0", "status": "completed", "findings": []}
        packet = json.loads(user)
        return {
            "agent_id": agent_id,
            "version": "1.0.0",
            "status": "completed",
            "findings": [{
                "url": packet["pages"][0]["url"],
                "evidence_ids": ["ev_not_in_packet"],
                "observation": "The supplied passage names installation and does not explain the steps.",
                "explanation": "The body does not contain the steps.",
                "why_it_matters": "The reader would not find the steps in the supplied text.",
                "severity": "low",
                "confidence": 0.4,
                "confidence_rationale": "The cited evidence id is not real and must be rejected.",
                "evaluation_state": "INFERRED",
                "claim_kind": "judgment",
                "investigation": ["Discard this judgment because the evidence id is not in the packet."],
                "verification_criteria": ["The evidence id matches a stored passage hash."],
                "limitations": [],
                "patch": "Add a paragraph here.",
            }],
        }

    rejected = build_enterprise_seo(report, ai_runner=ungrounded)
    assert not any(item.rule_id == "seo.ai.content_completeness.v1" for item in rejected.findings)
    specialist = next(agent for agent in rejected.agents if agent.agent_id == "seo.ai.content_completeness.v1")
    assert specialist.status == "partial"
    assert specialist.error_code == "EVIDENCE_REJECTED"


def test_ai_timeout_does_not_invent_a_finding():
    def runner(prompt: str, user: str, timeout_seconds: int):
        raise TimeoutError()

    page = PageEvidence(url="https://example.com/guide", title="Guide", body_text="A stored passage for the guide page.", word_count=8)
    assessment = build_enterprise_seo({
        "analysis_id": "run_ai_timeout",
        "domain": "example.com",
        "crawl_manifest": {"pages": [page.model_dump()]},
    }, ai_runner=runner)
    specialist = next(agent for agent in assessment.agents if agent.agent_id == "seo.ai.content_completeness.v1")
    assert specialist.status == "unavailable"
    assert specialist.error_code == "TIMEOUT"
    assert not any(finding.rule_id.startswith("seo.ai.") for finding in assessment.findings)


def test_contradictory_title_claims_on_one_url_are_not_both_published():
    from app.seo.enterprise.assess import _Builder

    builder = _Builder({"analysis_id": "run_conflict", "domain": "example.com"})
    evidence = {
        "evidence_id": "ev_title",
        "content_hash": "abc",
        "audit_run_id": "run_conflict",
        "source": "test",
        "url": "https://example.com/a",
        "snapshot_type": "derived",
        "collection_method": "test",
        "collector": "test",
        "scope": "PAGE_VERIFIED",
    }
    from app.seo.enterprise.contracts import EvidenceRecord

    builder.evidence["ev_title"] = EvidenceRecord.model_validate(evidence)

    def finding(rule_id: str, finding_id: str, severity: str, issue_type: str) -> EnterpriseFinding:
        return EnterpriseFinding(
            finding_id=finding_id,
            audit_run_id="run_conflict",
            rule_id=rule_id,
            rule_version="1.0.0",
            rule_class="mandatory",
            title=rule_id,
            category="titles",
            chapter=10,
            subchapters=["10.1"],
            severity=severity,  # type: ignore[arg-type]
            issue_type=issue_type,  # type: ignore[arg-type]
            scope="PAGE_VERIFIED",
            affected_urls=["https://example.com/a"],
            affected_count=1,
            eligible_count=1,
            evidence_ids=["ev_title"],
            observed_condition="Observed on the fetched URL.",
            expected_condition="The title signals agree.",
            simple_explanation="The two claims cannot both be true.",
            seo_significance="Conflicting title claims.",
            root_cause_hypothesis="Unknown.",
            cause_label="unknown",
            remediation_steps=["Inspect the template."],
            acceptance_tests=["A fresh snapshot has one title state."],
            regression_risk="A template edit can affect other pages.",
            confidence=0.9,
        )

    builder.proposed.append(finding("seo.title.missing", "f_missing", "high", "defect"))
    builder.proposed.append(finding("seo.title.length", "f_length", "info", "diagnostic"))
    published = builder._adjudicate()
    assert [item.finding_id for item in published] == ["f_missing"]
    assert any(item.reason.startswith("Contradicts seo.title.missing") for item in builder.rejected)
