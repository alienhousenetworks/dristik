"""Phase 3 Gate: AI 5-Point Enrichment, Evidence Verification & Leaked-Token Stripping."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.domain.enums import Category, Severity
from app.domain.models import Finding, FindingEvidence
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.reports.narrative_validator import strip_leaked_tokens, verify_finding_ai_blocks
from app.reports.pdf_evidence_blocks import render_ai_analysis_card


def test_ai_enrichment_populates_five_point_blocks_and_caps_fix_prompt():
    finding = Finding(
        finding_id="FND_TITLE_001",
        rule_id="TITLE_LENGTH_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Product page title is 'kwikpass'",
        affected_urls=["https://perforacare.com/products/lemon-mint-probiotic-rinse"],
        evidence_ids=["EV_021"],
        evidence_refs=["EV_021"],
        evidence=[
            FindingEvidence(
                evidence_id="EV_021",
                url="https://perforacare.com/products/lemon-mint-probiotic-rinse",
                element="title",
                value="kwikpass",
                snippet="<title>kwikpass</title>",
            )
        ],
    )

    long_prompt = " ".join(["word"] * 85)
    router = SimpleNamespace(
        generate_structured=AsyncMock(
            return_value={
                "analyses": [
                    {
                        "finding_id": "FND_TITLE_001",
                        "ai_understanding": "The title is likely overwritten by the Kwikpass app (EV_021).",
                        "ai_analysis": "Irrelevant SERP titles reduce CTR. Rankings impact is unknown without GSC. Confidence: high on defect.",
                        "fix_prompt": long_prompt,
                        "detailed_diagnosis": "Observed <title>kwikpass</title> on product page (EV_021).",
                        "why_it_matters": "Hurts organic CTR for product searches.",
                        "recommendation": "Set SEO title to '{product.title} | Perfora'.",
                        "validation_criteria": "Rendered HTML contains one <title> between 25-65 chars.",
                    }
                ]
            }
        )
    )

    orch = AnalysisOrchestrator()
    count = asyncio.run(
        orch._enrich_findings_with_ai(
            findings=[finding],
            model_router=router,
            business_profile=SimpleNamespace(business_name="Perfora", industry="Oral Care", value_proposition="Clean oral care"),
            site_facts={},
            website_url="https://perforacare.com",
        )
    )
    assert count == 1
    assert "Kwikpass" in (finding.ai_understanding or "")
    assert "CTR" in (finding.ai_analysis or "")
    assert len((finding.fix_prompt or "").split()) <= 60
    assert finding.connector_effect is not None
    assert finding.connector_effect["needs_connector"] == "Search Console"


def test_verifier_enforces_evidence_ids_strips_tokens_and_guards_connector_off():
    f = {
        "finding_id": "F1",
        "evidence_ids": ["EV_021"],
        "ai_understanding": "Title is kwikpass [[chapter_ref:seo:ch_1]] [].",
        "ai_analysis": "Impact confirmed on revenue for yourdomain.com.",
        "fix_prompt": "Fix title on product page for Verified Brand Name.",
        "connector_effect": {"resolves_issue": "PARTIAL", "needs_connector": "Search Console", "why": "Needs GSC."},
    }
    res = verify_finding_ai_blocks(f, valid_evidence_ids={"EV_021"})
    assert res["verified_state"] == "VERIFIED"
    assert "[[chapter_ref" not in f["ai_understanding"]
    assert "[]" not in f["ai_understanding"]
    assert "yourdomain.com" not in f["ai_analysis"]
    assert "impact confirmed" not in f["ai_analysis"].lower()
    assert "Verified Brand Name" not in f["fix_prompt"]

    # Uncited finding fails verification
    uncited = {"finding_id": "F2", "evidence_ids": [], "ai_understanding": "x", "ai_analysis": "y", "fix_prompt": "z"}
    res2 = verify_finding_ai_blocks(uncited, valid_evidence_ids={"EV_021"})
    assert res2["verified_state"] == "UNVERIFIED"
    assert "missing_evidence_id" in res2["issues"]


def test_epistemic_basis_unknown_suppressed_in_pdf_narrative_block():
    html = render_ai_analysis_card(
        {
            "executive_takeaway": "Clear summary.",
            "epistemic_labels": ["UNKNOWN", "DIRECT_OBSERVATION"],
        },
        narrative_mode="ai_full",
    )
    assert "Epistemic Basis:</strong> <span" in html
    assert ">UNKNOWN<" not in html
    assert "DIRECT_OBSERVATION" in html
    assert strip_leaked_tokens("Epistemic Basis: UNKNOWN clean") == "clean"
