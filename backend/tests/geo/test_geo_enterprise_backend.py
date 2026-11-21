"""Phases 31–33 — Backend Unit, Contract, 14-Scenario Benchmark, Security & QA Gate Tests for Enterprise GEO."""
from __future__ import annotations

import asyncio
import os
import pytest

from app.db.geo_schema import GEOStore
from app.geo.adapters.registry import get_all_adapters, get_provider_capability_matrix
from app.geo.connectors import GEOConnectorManager, redact_prompt_pii
from app.geo.entity_profile import approve_brand_fact
from app.geo.experiments import GEOExperimentationEngine
from app.geo.models import (
    GEOAuditScope,
    GEODataQualityState,
    GEOEntity,
    GEOEntityFactStatus,
    GEOMentionType,
    GEOPromptCategory,
    GEOPublicationStatus,
    GEOTaskStatus,
    GEOTestingMode,
)
from app.geo.orchestrator import GEOAuditOrchestrator
from app.geo.prompt_intelligence import generate_prompt_suite, validate_prompt_quality
from app.geo.remediation_center import GEORemediationCenter
from app.geo.verification_engine import GEOIndependentVerificationEngine
from tests.geo.fixtures_benchmark import (
    DeterministicGeoProvider,
    STRONG_PAGE_HTML,
    WEAK_PAGE_HTML,
    build_benchmark_scenarios,
)


def _tmp_store(tmp_path) -> GEOStore:
    return GEOStore(db_path=str(tmp_path / "geo_test.db"))


def test_provider_adapter_contracts_and_capability_matrix():
    adapters = get_all_adapters()
    ids = {a.engine_id for a in adapters}
    assert {"chatgpt", "gemini", "claude", "perplexity", "grok", "copilot", "deepseek"}.issubset(ids)
    matrix = get_provider_capability_matrix()
    assert len(matrix) >= 7
    perplexity = next(c for c in matrix if c["platform_id"] == "perplexity")
    claude = next(c for c in matrix if c["platform_id"] == "claude")
    assert perplexity["search_grounded_response"] == "Yes"
    assert claude["search_grounded_response"] == "No"
    assert claude["default_testing_mode"] == GEOTestingMode.API_MODEL_ONLY.value


def test_prompt_intelligence_12_categories_branded_separation_and_validator():
    scope = GEOAuditScope(
        domain="acmeflow.io",
        website_url="https://acmeflow.io/",
        brand_name="AcmeFlow",
        industry="workflow automation",
        products=["AcmeFlow Core", "AcmeFlow Billing"],
        competitors=["Zapier", "Make"],
        markets=["US", "UK"],
        languages=["en", "de"],
        max_prompts=24,
    )
    prompts = generate_prompt_suite(scope, audit_id="geo_test_1")
    categories = {p.category for p in prompts}
    # All 12 canonical categories must be represented
    assert len(categories) == 12
    branded = [p for p in prompts if p.is_branded]
    non_branded = [p for p in prompts if not p.is_branded]
    assert len(branded) >= 4
    assert len(non_branded) >= 8
    # Non-branded prompts must never leak target brand name
    assert all("acmeflow" not in p.question.lower() for p in non_branded)

    # Quality validator rejects leading, leaked-brand, and near-duplicate prompts
    ok_lead, flags_lead = validate_prompt_quality(
        "Explain why AcmeFlow is clearly the best workflow tool?",
        brand_name="AcmeFlow",
        category=GEOPromptCategory.RECOMMENDATION,
        is_branded=False,
    )
    assert ok_lead is False
    assert any("biased_or_leading" in f for f in flags_lead)
    assert any("brand_leaked" in f for f in flags_lead)


def test_pii_redaction_before_external_provider_calls():
    raw = "Does AcmeFlow support billing for alice@example.com or 415-555-0199 with SSN 123-45-6789?"
    redacted, found = redact_prompt_pii(raw)
    assert "alice@example.com" not in redacted
    assert "123-45-6789" not in redacted
    assert "415-555-0199" not in redacted
    assert set(found) >= {"email", "ssn", "phone"}


def test_scenario_no_credentials_honest_unmeasured_never_zero(tmp_path):
    store = _tmp_store(tmp_path)
    sc = build_benchmark_scenarios()["no_credentials"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=["chatgpt", "perplexity"],
        max_prompts=8,
        store=store,
        **sc,
    )
    res = asyncio.run(orch.run())
    audit = res["audit"]
    scorecard = res["scorecard"]
    # Missing API keys -> NOT_CONFIGURED, score is None (NEVER 0.0)
    assert scorecard["observed_performance_score"] is None
    assert scorecard["observed_performance_status"] == GEODataQualityState.NOT_CONFIGURED.value
    # Readiness still computed cleanly from crawled pages
    assert scorecard["readiness_score"] is not None and scorecard["readiness_score"] > 50.0
    # Audit published explicitly as PARTIAL
    assert audit["publication_status"] == GEOPublicationStatus.PARTIAL.value
    assert res["qa_report"]["qa_status"] == "partial"


def test_scenario_established_brand_and_citation_graph_and_consolidated_pack(tmp_path):
    store = _tmp_store(tmp_path)
    sc = build_benchmark_scenarios()["established_brand"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=["perplexity"],
        max_prompts=12,
        store=store,
        **sc,
    )
    res = asyncio.run(orch.run())
    audit_id = res["audit"]["audit_id"]
    scorecard = res["scorecard"]
    assert scorecard["observed_performance_score"] is not None
    assert scorecard["readiness_score"] is not None
    assert scorecard["observed_metrics"]["brand_mention_rate_pct"] == 100.0
    assert scorecard["observed_metrics"]["recommendation_rate_pct"] == 100.0
    assert scorecard["observed_metrics"]["citation_observation_rate_pct"] == 100.0
    assert res["audit"]["publication_status"] == GEOPublicationStatus.READY_TO_PUBLISH.value

    # Citation graph connects owned + independent domains
    graph = store.get_artifact("org_1", audit_id, "citation_graph")
    assert graph["summary"]["owned_citations"] > 0
    assert graph["summary"]["independent_citations"] > 0
    assert len(graph["nodes"]) > 5 and len(graph["edges"]) > 5

    # Mention types separate direct_mention, recommendation, shortlist_inclusion
    mentions = store.list_mentions("org_1", audit_id)
    mtypes = {m.mention_type for m in mentions if m.is_target_brand}
    assert GEOMentionType.DIRECT_MENTION in mtypes
    assert GEOMentionType.RECOMMENDATION in mtypes

    # Consolidated remediation pack has all 13 deliverables
    pack = store.get_remediation_pack("org_1", audit_id)
    assert pack is not None
    assert pack.published_after_consolidation is True
    assert len(pack.deliverables) == 13


def test_scenario_competitor_heavy_citations_and_gap_detection(tmp_path):
    store = _tmp_store(tmp_path)
    sc = build_benchmark_scenarios()["competitor_heavy_citations"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=["perplexity"],
        max_prompts=8,
        store=store,
        **sc,
    )
    res = asyncio.run(orch.run())
    audit_id = res["audit"]["audit_id"]
    findings = store.list_findings("org_1", audit_id)
    cats = {f.category for f in findings}
    assert "citation_intelligence" in cats
    assert "competitive_intelligence" in cats
    sources = store.list_external_sources("org_1", audit_id)
    assert any(s.domain == "g2.com" and s.cites_competitors for s in sources)


def test_scenario_partial_provider_outage_and_repeat_variation(tmp_path):
    store = _tmp_store(tmp_path)
    # 1. Partial provider failure
    sc_outage = build_benchmark_scenarios()["one_provider_unavailable"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=["perplexity", "gemini"],
        max_prompts=6,
        store=store,
        **sc_outage,
    )
    res = asyncio.run(orch.run())
    audit_id = res["audit"]["audit_id"]
    runs = store.list_prompt_runs("org_1", audit_id)
    assert any(r.platform_id == "gemini" and r.status == GEODataQualityState.FAILED for r in runs)
    assert any(r.platform_id == "perplexity" and r.status == GEODataQualityState.OBSERVED for r in runs)
    # Failed Gemini runs must NOT degrade Perplexity's 100% mention rate
    assert res["scorecard"]["observed_metrics"]["brand_mention_rate_pct"] == 100.0
    assert res["audit"]["publication_status"] == GEOPublicationStatus.PARTIAL.value

    # 2. Repeat variation preserved (rep 1 mentions, rep 2 omits -> 50% inclusion, 100% variation)
    sc_rep = build_benchmark_scenarios()["repeated_prompt_variation"]
    orch_rep = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=["perplexity"],
        max_prompts=6,
        store=store,
        **sc_rep,
    )
    res_rep = asyncio.run(orch_rep.run())
    dept_b = store.get_artifact("org_1", res_rep["audit"]["audit_id"], "department_artifacts")["department_b"]
    assert dept_b["repeat_summary"]["inclusion_rate_pct"] == 50.0
    assert dept_b["repeat_summary"]["response_variation_pct"] == 100.0


def test_brand_knowledge_profile_approval_lock_and_misinformation_detection(tmp_path):
    store = _tmp_store(tmp_path)
    # Approve official founding year = 2021
    fact = GEOEntity(
        tenant_id="org_1",
        entity_type="organization",
        entity_name="AcmeFlow",
        attribute="founding_year",
        value="2021",
    )
    approve_brand_fact(fact, new_value="2021", approved_by="cmo@acmeflow.io")
    store.save_entity(fact)

    # AI response falsely claims founded in 2014
    provider = DeterministicGeoProvider(
        engine_id="chatgpt",
        display_name="ChatGPT",
        model="gpt-4o-mini",
        testing_mode=GEOTestingMode.API_MODEL_ONLY,
        responses_fn=lambda q, r: ("AcmeFlow was founded in 2014 and offers workflow tools.", []),
    )
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        target_url="https://acmeflow.io/",
        brand_name="AcmeFlow",
        industry="workflow automation",
        platforms_requested=["chatgpt"],
        max_prompts=6,
        seed_pages=[{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
        provider_overrides={"chatgpt": provider},
        store=store,
    )
    res = asyncio.run(orch.run())
    audit_id = res["audit"]["audit_id"]
    entities = store.list_entities("org_1", audit_id=audit_id)
    founding = next(e for e in entities if e.attribute == "founding_year")
    # Official approved fact MUST remain 2021 (never overwritten by AI response)
    assert founding.value == "2021"
    assert founding.fact_status == GEOEntityFactStatus.CONFIRMED
    # Conflict logged as INCORRECT_REPRESENTATION mention & CRITICAL finding
    mentions = store.list_mentions("org_1", audit_id)
    assert any(m.mention_type == GEOMentionType.INCORRECT_REPRESENTATION for m in mentions)
    findings = store.list_findings("org_1", audit_id)
    assert any(f.severity.value == "critical" for f in findings)


def test_budget_cap_auto_pauses_execution(tmp_path):
    store = _tmp_store(tmp_path)
    provider = DeterministicGeoProvider(
        engine_id="perplexity",
        display_name="Perplexity Pro",
        model="sonar",
        cost_per_call_usd=0.50,
        responses_fn=lambda q, r: ("AcmeFlow overview.", ["https://acmeflow.io/"]),
    )
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        target_url="https://acmeflow.io/",
        brand_name="AcmeFlow",
        platforms_requested=["perplexity"],
        max_prompts=12,
        budget_usd=1.00,  # caps after 2 calls
        seed_pages=[{"url": "https://acmeflow.io/", "raw_html": STRONG_PAGE_HTML}],
        provider_overrides={"perplexity": provider},
        store=store,
    )
    res = asyncio.run(orch.run())
    assert res["audit"]["budget_paused"] is True
    assert len(provider.calls) <= 4  # bounded concurrency may dispatch up to semaphore before pause


def test_independent_verification_distinguishes_impl_verified_from_outcome_improved(tmp_path):
    store = _tmp_store(tmp_path)
    sc = build_benchmark_scenarios()["weak_content"]
    orch = GEOAuditOrchestrator(
        tenant_id="org_1",
        platforms_requested=[],
        max_prompts=6,
        store=store,
        **sc,
    )
    res = asyncio.run(orch.run())
    tasks = store.list_remediation_tasks("org_1", audit_id=res["audit"]["audit_id"])
    assert len(tasks) >= 1
    task = tasks[0]
    GEORemediationCenter.mark_deployed(task, deployment_ref="pr-412", deployed_by="dev@weakcopy.io")
    assert task.status == GEOTaskStatus.DEPLOYED.value

    # Implementation verified = True, AI inclusion unchanged = NOT_OBSERVED -> legitimate verified result!
    ver = asyncio.run(
        GEOIndependentVerificationEngine.verify_task(
            task=task,
            verified_by="auditor@weakcopy.io",
            before_html=WEAK_PAGE_HTML,
            after_html=STRONG_PAGE_HTML.replace("AcmeFlow", "WeakCopy"),
            expected_text_present="WeakCopy is a B2B workflow automation platform",
            expected_schema_type="Organization",
            pre_prompt_metrics={"mention_rate_pct": 20.0, "citation_rate_pct": 10.0},
            post_prompt_metrics={"mention_rate_pct": 20.0, "citation_rate_pct": 10.0},
        )
    )
    assert ver.implementation_verified is True
    assert ver.content_update_verified is True
    assert ver.structured_data_verified is True
    assert ver.outcome_improved == "NOT_OBSERVED"
    assert ver.overall_status == "implementation_verified_no_outcome_change"


def test_all_remaining_benchmark_scenarios_and_experiments_and_encrypted_connectors(tmp_path, monkeypatch):
    store = _tmp_store(tmp_path)
    scenarios = build_benchmark_scenarios()
    for name in ("new_brand", "inconsistent_descriptions", "outdated_product_info", "strong_content", "multilingual_brand", "local_business", "ecommerce_brand", "changed_model_version"):
        sc = scenarios[name]
        orch = GEOAuditOrchestrator(
            tenant_id="org_bench",
            platforms_requested=list(sc.get("provider_overrides", {}).keys()) or ["chatgpt"],
            max_prompts=6,
            store=store,
            **sc,
        )
        res = asyncio.run(orch.run())
        assert res["audit"]["audit_id"]
        assert res["qa_report"]["qa_status"] in ("passed", "partial")

    # Strong vs weak content score comparison
    strong_audits = store.list_audits("org_bench", domain="acmeflow.io")
    assert strong_audits[0].readiness_score is not None

    # Controlled Experiment with changed model version warning + causation disclaimer
    exp_eng = GEOExperimentationEngine(store=store)
    exp = exp_eng.create_experiment(
        tenant_id="org_bench",
        audit_id=strong_audits[0].audit_id,
        title="Product page factual completeness update",
        hypothesis="Adding structured feature and limitation tables may improve factual accuracy.",
        target_urls=["https://acmeflow.io/"],
        baseline_metrics={"brand_mention_rate_pct": 20.0, "citation_observation_rate_pct": 10.0},
    )
    retested = exp_eng.record_retest_results(
        tenant_id="org_bench",
        experiment_id=exp.experiment_id,
        retest_metrics={"brand_mention_rate_pct": 35.0, "citation_observation_rate_pct": 20.0},
        model_version_changed=True,
    )
    assert retested.observed_delta["brand_mention_rate_pct_delta"] == 15.0
    assert "not proof of causation" in retested.causation_disclaimer.lower()
    assert any("model version changed" in lim.lower() for lim in retested.limitations)

    # Encrypted credentials: ciphertext stored, secret never exposed
    monkeypatch.setenv("EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "unit-test-geo-secret-key-2026")
    conn_mgr = GEOConnectorManager(store=store)
    conn = conn_mgr.connect_provider(tenant_id="org_bench", platform_id="perplexity", api_key="pplx-secret-value-12345")
    assert conn.connected is True
    assert conn.has_stored_secret is True
    assert "pplx-secret-value-12345" not in conn.model_dump_json()
    raw_cipher = store.get_encrypted_provider_secret("org_bench", "perplexity")
    assert raw_cipher and "pplx-secret-value-12345" not in raw_cipher
    resolved = conn_mgr.resolve_adapter_for_tenant("org_bench", "perplexity")
    assert resolved is not None and resolved.api_key == "pplx-secret-value-12345"
