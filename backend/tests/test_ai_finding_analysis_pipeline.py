"""
Tests for the AI finding analysis pipeline fixes:
1. Stage 7b `_serialize_findings_brief` handles FindingEvidence Pydantic objects without TypeError.
2. `DecisionEngine.synthesize_findings` preserves AI `why_it_matters`/`validation_criteria` and
   does not overwrite `description` with Critic `verification_notes`.
3. `SpecialistAgent._ingest_llm` resolves case-mismatched `evidence_refs` against the evidence store.
4. `AnalysisOrchestrator._enrich_findings_with_ai` enriches ROOT_RC_* and Stage-1 deterministic
   findings via `model_router.generate_structured` while preserving identity and evidence_refs.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import Category, Severity, VerificationStatus
from app.domain.models import Claim, Finding, FindingEvidence
from app.evidence.store import EvidenceStore
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.cognition.decision_engine import DecisionEngine
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.orchestration.runtime.registry import SPECIALIST_AGENTS_V3
from app.orchestration.runtime.specialist import SpecialistAgent
from app.remediation.deduplicator import FindingDeduplicator
from app.reports.ai_report_narrator import _serialize_findings_brief


def test_serialize_findings_brief_handles_pydantic_finding_evidence():
    finding = Finding(
        finding_id="find_001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing meta description on /pages/about",
        description="About page lacks a meta description.",
        recommendation="Add a concise meta description.",
        evidence=[
            FindingEvidence(
                evidence_id="EV_048",
                url="https://perforacare.com/pages/about",
                element="meta[name=description]",
                value="",
                snippet="missing_meta_description",
            )
        ],
        affected_urls=["https://perforacare.com/pages/about"],
    )

    rows = _serialize_findings_brief([finding])
    assert len(rows) == 1
    assert rows[0]["finding_id"] == "find_001"
    assert "EV_048" in rows[0]["observed_evidence"]
    # Must be JSON-serializable end-to-end
    json.dumps(rows)


def test_decision_engine_preserves_ai_why_and_isolates_critic_notes():
    store = EvidenceStore(run_id="run_test")
    ev = store.add_evidence(
        source_type="dom",
        analyzer="crawler",
        url="https://perforacare.com/pages/about",
        selector="meta[name=description]",
        text="missing_meta_description",
        value="missing",
    )

    claim = Claim(
        id="claim_001",
        agent_id="seo.html.v3",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        statement="https://perforacare.com/pages/about lacks a meta description.",
        recommendation="Write a 140-character meta description for Perfora's About page.",
        why_it_matters="Search engines auto-generate weak snippets without a meta description, lowering organic CTR.",
        validation_criteria="Page /pages/about renders a non-empty <meta name='description'> tag.",
        evidence_refs=[ev.id],
        confidence=0.95,
        verification_status=VerificationStatus.VERIFIED,
        verification_notes="ev_001 explicitly records missing meta description; claim is supported.",
    )

    findings = DecisionEngine().synthesize_findings([claim], store)
    assert len(findings) == 1
    f = findings[0]
    assert f.description == claim.statement
    assert "claim is supported" not in f.description
    assert f.verification_notes == claim.verification_notes
    assert f.why_it_matters == claim.why_it_matters
    assert f.validation_criteria == claim.validation_criteria


def test_specialist_ingest_llm_resolves_case_insensitive_evidence_refs():
    bb = CognitiveBlackboard(run_id="run_test", website_url="https://perforacare.com")
    ev = bb.evidence_store.add_evidence(
        source_type="dom",
        analyzer="crawler",
        url="https://perforacare.com",
        selector="title",
        text="Perfora Oral Care",
        value="Perfora Oral Care",
    )
    # Supply opposite-case ID (EV_001 vs canonical ev_001) to mirror mixed-case LLM output
    mismatched_case_id = ev.id.upper() if ev.id.islower() else ev.id.lower()

    defn = SPECIALIST_AGENTS_V3["seo.html.v3"]
    agent = SpecialistAgent(defn, model_router=None)

    raw_llm = {
        "status": "completed",
        "claims": [
            {
                "statement": "Homepage title exceeds 60 characters.",
                "severity": "MEDIUM",
                "confidence": 0.9,
                "recommendation": "Shorten homepage title to under 60 characters.",
                "why_it_matters": "Truncated titles reduce SERP click-through rate.",
                "evidence_refs": [mismatched_case_id],
            }
        ],
    }

    res = agent._ingest_llm(bb, raw_llm, evidence_slice=[])
    assert res["status"] == "completed"
    assert len(res["claims"]) == 1
    assert res["claims"][0]["evidence_refs"] == [ev.id]


def test_deduplicator_preserves_member_ai_why_and_recommendation():
    f1 = Finding(
        finding_id="f1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Multiple H1 tags on product page",
        description="Two H1 tags detected.",
        recommendation="Keep only the product name as H1 on Perfora product pages.",
        why_it_matters="Duplicate H1s dilute Perfora's primary product keyword focus.",
        evidence=[FindingEvidence(evidence_id="EV_010", url="https://perforacare.com/p1", element="h1", value="2")],
        evidence_refs=["EV_010"],
    )
    f2 = Finding(
        finding_id="f2",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Missing H1 on about page",
        description="No H1 detected.",
        recommendation="Implement recommended architectural fix based on evidence.",
        evidence=[FindingEvidence(evidence_id="EV_011", url="https://perforacare.com/about", element="h1", value="0")],
        evidence_refs=["EV_011"],
    )

    deduped = FindingDeduplicator.deduplicate([f1, f2])
    assert len(deduped) == 1
    root = deduped[0]
    assert root.finding_id == "ROOT_RC_HEADING_HIERARCHY"
    assert "Perfora" in (root.why_it_matters or "")
    assert "Perfora" in (root.recommendation or "")


@pytest.mark.asyncio
async def test_orchestrator_enrich_findings_with_ai_enriches_deterministic_and_root_findings():
    root_finding = Finding(
        finding_id="ROOT_RC_HEADING_HIERARCHY",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Document Outline & Heading Hierarchy Fragmentation",
        description="Page heading tags violate sequential order.",
        recommendation="Ensure each page contains one H1.",
        why_it_matters="This canonical defect consolidates 3 related symptoms that collectively impair user experience, trust, and organic discoverability.",
        evidence=[FindingEvidence(evidence_id="EV_010", url="https://perforacare.com/pages/about", element="h1", value="0")],
        evidence_refs=["EV_010"],
        affected_urls=["https://perforacare.com/pages/about"],
    )
    det_finding = Finding(
        finding_id="FINDING-ECOM-001",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
        title="Incomplete Product Schema & Offer Properties",
        description="2 product page(s) lack required Google Merchant fields.",
        recommendation="Enrich Product JSON-LD with Offer objects.",
        evidence=[FindingEvidence(evidence_id="EV_020", url="https://perforacare.com/products/flosser", element="script[type='application/ld+json']", value="missing offers")],
        evidence_refs=["EV_020"],
        affected_urls=["https://perforacare.com/products/flosser"],
    )

    mock_router = SimpleNamespace(
        generate_structured=AsyncMock(
            return_value={
                "analyses": [
                    {
                        "finding_id": "ROOT_RC_HEADING_HIERARCHY",
                        "detailed_diagnosis": "Perfora's About page lacks an H1 while product pages render duplicate H1s.",
                        "why_it_matters": "Weak heading structure reduces topical relevance for Perfora's oral care queries.",
                        "recommendation": "Add a single descriptive H1 on /pages/about and demote secondary product H1s to H2.",
                        "validation_criteria": "Every crawled Perfora URL contains exactly one H1 heading.",
                    },
                    {
                        "finding_id": "FINDING-ECOM-001",
                        "detailed_diagnosis": "Perfora product pages omit Offer price and availability inside Product JSON-LD.",
                        "why_it_matters": "Missing Offer schema disqualifies Perfora SKUs from Google Shopping rich results.",
                        "recommendation": "Inject complete Offer (price, priceCurrency, availability) into Shopify Product JSON-LD.",
                        "validation_criteria": "Product JSON-LD on all product URLs validates with non-empty offers.",
                    },
                ]
            }
        )
    )

    orch = AnalysisOrchestrator.__new__(AnalysisOrchestrator)
    bp = SimpleNamespace(business_name="Perfora", industry="Oral Care D2C", value_proposition="Modern oral care products")

    enriched = await orch._enrich_findings_with_ai(
        findings=[root_finding, det_finding],
        model_router=mock_router,
        business_profile=bp,
        site_facts={"domain": "perforacare.com"},
        website_url="https://perforacare.com",
    )

    assert enriched == 2
    assert "Perfora" in root_finding.description
    assert "Perfora" in (root_finding.why_it_matters or "")
    assert root_finding.agent_id == "ai.finding_analyst"
    assert root_finding.evidence_refs == ["EV_010"]
    assert "Google Shopping" in (det_finding.why_it_matters or "")
    assert det_finding.evidence_refs == ["EV_020"]
