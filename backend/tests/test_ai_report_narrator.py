"""Stage 7b tests: AI-Narrated 5 PDFs + 5 PPTXs (Executive, SEO, GEO, AEO, CRO).

Verifies all exit-gate & engineering-review invariants:
1. Raw digits outside `{{placeholders}}` trigger retry; remaining bad sentences are removed WHOLE (no broken fragments).
2. Unknown or `held_from_executive` finding IDs are dropped; 100% of cited IDs resolve.
3. `UNKNOWN (Requires GA4)`, `NOT_MEASURED`, and `AI_INTERPRETATION` labels survive verbatim.
4. Narrative Critic runs on a DIFFERENT provider than writer when `CRITIC_PROVIDER_OVERRIDE` is set and drops unsupported items.
5. `REPORT_MIN_BUDGET_USD` protects small sites; Executive PDF -> PPT run FIRST; per-document `narrative_mode` tracks reduced docs individually.
6. Offline / budget-exhausted runs set `narrative_mode="deterministic_fallback"` (never `"ai_full"`).
7. All 5 PDFs + 5 PPTXs + JSON share ONE canonical score; PPTX respects slide/bullet/word limits + speaker notes; `mode='legacy_full'` preserved.
8. `sync_seo_chapter_narratives_map` preserves 100% of `CORE_CHAPTERS` IDs & numeric keys (zero chapter loss).
9. Orchestrator executes Stage 7b strictly after Critic (Stage 5), Synthesizer (Stage 6), and Remediation (Stage 7).
"""
import inspect
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from pptx import Presentation

from app.core.config import settings
from app.core.inference.telemetry import TelemetryTracker
from app.domain.enums import Category, Severity
from app.domain.models import (
    BusinessProfile,
    CrawlManifest,
    ExecutiveReport,
    Finding,
    HonestScores,
    OverallScoreResult,
    PageEvidence,
)
from app.domain.scoring.displayed_score import displayed_composite
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.reports.ai_report_narrator import (
    compute_reporting_budget_cap_usd,
    narrate_all_documents,
    narrate_document,
    sync_seo_chapter_narratives_map,
)
from app.reports.deck.coordinator import generate_executive_pptx_deck, generate_section_pptx_deck
from app.reports.narrative_validator import (
    build_scorecard_vars,
    validate_and_hydrate_bundle,
)
from app.seo.reporting.seo_book_renderer import CORE_CHAPTERS
from app.seo.reporting.seo_report_generator import CompleteSeoReportGenerator


def _sample_report() -> ExecutiveReport:
    pages = [
        PageEvidence(
            url="https://acme.example/",
            title="Acme Cloud — Automated Deployments",
            h1=["Ship Kubernetes Faster"],
            word_count=450,
            status_code=200,
            body_text="Ship Kubernetes Faster with instant rollbacks.",
        ),
        PageEvidence(
            url="https://acme.example/pricing",
            title="Pricing — Acme Cloud",
            h1=["Transparent Plans"],
            word_count=310,
            status_code=200,
            body_text="Plans start with a free sandbox tier.",
        ),
    ]
    findings = [
        Finding(
            finding_id="find_seo_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.CRITICAL,
            title="Missing canonical tag on pricing page",
            description="Canonical link absent on /pricing.",
            affected_urls=["https://acme.example/pricing"],
            recommendation="Add self-referencing canonical tag.",
            priority=9,
        ),
        Finding(
            finding_id="find_geo_01",
            category=Category.GEO,
            severity=Severity.HIGH,
            title="Homepage lacks concise quotable entity definition",
            description="No 50-word factual summary for AI citation engines.",
            affected_urls=["https://acme.example/"],
            recommendation="Add concise definition block.",
            priority=8,
        ),
        Finding(
            finding_id="find_aeo_01",
            category=Category.AI_SEARCH,
            severity=Severity.HIGH,
            title="Pricing FAQ missing structured answers",
            description="Common buyer pricing questions unanswered.",
            affected_urls=["https://acme.example/pricing"],
            recommendation="Publish FAQPage Q&A block.",
            priority=8,
        ),
        Finding(
            finding_id="find_cro_01",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="Hero CTA lacks risk-reversal copy",
            description="No trial or security reassurance adjacent to CTA.",
            affected_urls=["https://acme.example/"],
            recommendation="Add security reassurance beside primary CTA.",
            priority=7,
        ),
        Finding(
            finding_id="find_fp_held",
            category=Category.TECHNICAL_SEO,
            severity=Severity.INFO,
            title="Confirmed false positive ecommerce rule",
            held_from_executive=True,
            affected_urls=["https://acme.example/"],
        ),
    ]
    return ExecutiveReport(
        report_id="rep_s7b",
        analysis_id="run_s7b",
        org_id="org_acme",
        website_url="https://acme.example/",
        domain="acme.example",
        generated_at="2026-11-22",
        business_profile=BusinessProfile(business_name="Acme Cloud", industry="B2B SaaS"),
        scores=OverallScoreResult(overall_score=62.0, grade="D"),
        honest_scores=HonestScores(
            human_score=74.0,
            google_score=68.0,
            ai_readiness_score=65.0,
            ai_visibility_score=None,
        ),
        story_summary="Grounded summary.",
        primary_strategic_opportunity="Unblock indexation and answerability.",
        consultant_advice_what_to_ignore="Low-impact vanity warnings.",
        crawl_manifest=CrawlManifest(domain="acme.example", pages=pages, total_pages=len(pages)),
        findings=findings,
    )


@pytest.mark.asyncio
async def test_raw_number_rejected_retried_and_whole_sentence_removed_no_broken_fragments():
    report = _sample_report()
    sc_vars = build_scorecard_vars(report)
    attempts = {"writer": 0}

    async def _fake_router(**kwargs):
        if kwargs["capability"] == "report_narrative":
            attempts["writer"] += 1
            if attempts["writer"] == 1:
                # Attempt 1 has raw digits ("42%") -> must trigger retry
                return {
                    "executive_summary": "Acme Cloud scores {{score.overall}} and lifts traffic by 42%.",
                    "chapters": [
                        {
                            "chapter_id": "ch_exec_summary",
                            "title": "Executive Posture",
                            "audience": "ceo",
                            "executive_takeaway": "Overall posture is {{score.overall}}.",
                            "body_md": "Fixing canonicals improves crawl clarity. Traffic jumps by 42% in two weeks.",
                            "why_it_matters": "Protects organic acquisition.",
                            "cited_finding_ids": ["find_seo_01"],
                        }
                    ],
                }
            # Attempt 2 STILL has one bad digit sentence alongside a clean sentence -> bad sentence removed WHOLE!
            return {
                "executive_summary": "Acme Cloud scores {{score.overall}} across {{count.pages_crawled}} crawled pages. Revenue increases by $50000.",
                "chapters": [
                    {
                        "chapter_id": "ch_exec_summary",
                        "title": "Executive Posture",
                        "audience": "ceo",
                        "executive_takeaway": "Overall posture is {{score.overall}}.",
                        "body_md": "Fixing canonical tags stabilizes pricing indexation. Conversion improves by 18% immediately. Unresolved {{fake.metric}} dropped.",
                        "why_it_matters": "Protects organic visibility without speculation.",
                        "cited_finding_ids": ["find_seo_01"],
                    }
                ],
            }
        return {"verdicts": [{"item_id": "ch_exec_summary", "decision": "supported", "reason": "ok"}]}

    mock_router = MagicMock()
    mock_router.client = MagicMock(provider="anthropic")
    mock_router.telemetry = TelemetryTracker()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_router)

    bundle = await narrate_document(
        doc_type="executive",
        doc_format="pdf",
        audience="ceo",
        tier="standard",
        findings=[f for f in report.findings if not f.held_from_executive],
        scorecard_vars=sc_vars,
        roadmap_summary={},
        model_router=mock_router,
    )

    assert attempts["writer"] == 2  # Retried once on raw digits
    assert bundle.narrative_mode == "ai_full"
    # Pre-hydration braces MUST NEVER reach user; bad sentences removed WHOLE (no "improves by .")
    assert "{{" not in bundle.executive_summary
    assert "$50000" not in bundle.executive_summary
    assert sc_vars["score.overall"] in bundle.executive_summary
    body = bundle.chapters[0].body_md
    assert "Fixing canonical tags stabilizes pricing indexation." in body
    assert "18%" not in body
    assert "improves by" not in body
    assert "fake.metric" not in body
    assert "[metric not in evidence]" not in body


def test_unknown_and_held_finding_ids_dropped_and_labels_preserved():
    report = _sample_report()
    sc_vars = build_scorecard_vars(report)
    verified_ids = {"find_seo_01", "find_cro_01"}  # excludes find_fp_held & find_ghost_999

    raw_bundle = {
        "executive_summary": (
            "Score is {{score.overall}}. Analytics remain {{label.analytics}} and live visibility is {{score.live_visibility}}. "
            "Strategic prioritization is {{label.ai_interpretation}}."
        ),
        "chapters": [
            {
                "chapter_id": "ch_good",
                "title": "Valid Chapter",
                "body_md": "Pricing page lacks canonicals while conversion impact stays {{label.analytics}}.",
                "cited_finding_ids": ["find_seo_01", "find_fp_held"],
            },
            {
                "chapter_id": "ch_bad_id",
                "title": "Bad Citation Chapter",
                "body_md": "References a hallucinated finding.",
                "cited_finding_ids": ["find_ghost_999"],
            },
        ],
        "slides": [
            {
                "slide_id": "sl_good",
                "title": "Fix Canonical Tag",
                "bullets": [
                    "Add self-referencing canonical tag on pricing page immediately to protect indexation across search engines and AI crawlers",
                    "Analytics conversion rate remains {{label.analytics}}",
                    "Live visibility remains {{score.live_visibility}}",
                    "Priority note is {{label.ai_interpretation}}",
                    "Fifth bullet must be truncated by max_bullets=4",
                ],
                "speaker_notes": "Explain canonical remediation.",
                "cited_finding_ids": ["find_seo_01"],
            },
            {
                "slide_id": "sl_bad",
                "title": "Ghost Slide",
                "bullets": ["Cites nonexistent finding."],
                "speaker_notes": "Should be dropped.",
                "cited_finding_ids": ["find_ghost_999"],
            },
        ],
    }

    hydrated, val_rep = validate_and_hydrate_bundle(
        raw_bundle,
        verified_finding_ids=verified_ids,
        scorecard_vars=sc_vars,
        max_slides=12,
    )

    assert len(hydrated["chapters"]) == 1
    assert hydrated["chapters"][0]["chapter_id"] == "ch_good"
    assert hydrated["chapters"][0]["cited_finding_ids"] == ["find_seo_01"]  # find_fp_held stripped
    assert len(hydrated["slides"]) == 1
    assert hydrated["slides"][0]["slide_id"] == "sl_good"
    assert len(hydrated["slides"][0]["bullets"]) == 4  # capped at 4
    assert len(hydrated["slides"][0]["bullets"][0].split()) <= 15  # capped at 15 words
    assert "UNKNOWN (Requires GA4)" in hydrated["executive_summary"]
    assert "NOT_MEASURED" in hydrated["executive_summary"]
    assert "AI_INTERPRETATION" in hydrated["executive_summary"]
    assert "UNKNOWN (Requires GA4)" in val_rep.preserved_labels_found


@pytest.mark.asyncio
async def test_critic_uses_different_provider_than_writer_and_drops_unsupported(monkeypatch):
    report = _sample_report()
    sc_vars = build_scorecard_vars(report)
    monkeypatch.setattr(settings, "CRITIC_PROVIDER_OVERRIDE", "openai")

    critic_kwargs_captured = {}

    async def _fake_router(**kwargs):
        if kwargs["capability"] == "report_narrative":
            return {
                "executive_summary": "Acme Cloud scores {{score.overall}}.",
                "chapters": [
                    {
                        "chapter_id": "ch_supported",
                        "title": "Canonical Health",
                        "body_md": "Pricing page lacks a canonical tag.",
                        "cited_finding_ids": ["find_seo_01"],
                    },
                    {
                        "chapter_id": "ch_unsupported",
                        "title": "Overstated Claim",
                        "body_md": "Guaranteed top ranking after adding a single tag.",
                        "cited_finding_ids": ["find_seo_01"],
                    },
                ],
            }
        if kwargs["capability"] == "critic":
            critic_kwargs_captured.update(kwargs)
            return {
                "verdicts": [
                    {"item_id": "ch_supported", "decision": "supported", "reason": "Backed by find_seo_01"},
                    {"item_id": "ch_unsupported", "decision": "unsupported", "reason": "Guarantees ranking"},
                ]
            }
        return {"status": "unavailable"}

    mock_router = MagicMock()
    mock_router.client = MagicMock(provider="anthropic")
    mock_router.telemetry = TelemetryTracker()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_router)

    bundle = await narrate_document(
        doc_type="executive",
        doc_format="pdf",
        audience="ceo",
        tier="standard",
        findings=[f for f in report.findings if not f.held_from_executive],
        scorecard_vars=sc_vars,
        roadmap_summary={},
        model_router=mock_router,
    )

    # Critic provider MUST differ from writer provider when CRITIC_PROVIDER_OVERRIDE is set
    assert bundle.writer_provider == "anthropic"
    assert bundle.critic_provider == "openai"
    assert bundle.critic_provider != bundle.writer_provider
    assert critic_kwargs_captured.get("provider_override") == "openai"
    assert critic_kwargs_captured.get("model_tier") == "judge_model"
    # Unsupported chapter MUST be dropped
    assert [c.chapter_id for c in bundle.chapters] == ["ch_supported"]
    assert bundle.critic_summary["dropped_ids"] == ["ch_unsupported"]


@pytest.mark.asyncio
async def test_budget_floor_priority_order_and_per_document_narrative_mode():
    # Small 20-page site: 15% of $1.00 = $0.15, so REPORT_MIN_BUDGET_USD ($0.35) floor applies
    assert compute_reporting_budget_cap_usd(1.00) == pytest.approx(0.35, abs=1e-4)
    # Large site: 15% of $10.00 = $1.50 > floor
    assert compute_reporting_budget_cap_usd(10.00) == pytest.approx(1.50, abs=1e-4)

    report = _sample_report()
    tracker = TelemetryTracker()
    call_order = []

    async def _fake_router(**kwargs):
        cap = kwargs["capability"]
        if cap == "report_narrative":
            role = kwargs["agent_role"]
            call_order.append(role)
            # Simulate Executive PDF ($0.20) + Executive PPT ($0.20) consuming the $0.35 floor
            tracker.telemetry.estimated_cost_usd += 0.20
            if "PPT" in role:
                return {
                    "executive_summary": "Executive summary {{score.overall}}.",
                    "slides": [
                        {
                            "slide_id": "exec_sl_1",
                            "title": "Fix Canonical Tag",
                            "bullets": ["Add self-referencing canonical link on pricing page."],
                            "speaker_notes": "Lead with indexation risk.",
                            "cited_finding_ids": ["find_seo_01"],
                        }
                    ],
                }
            return {
                "executive_summary": "Executive summary {{score.overall}}.",
                "chapters": [
                    {
                        "chapter_id": "ch_exec_summary",
                        "title": "Executive Posture",
                        "body_md": "Pricing page lacks a canonical link tag.",
                        "cited_finding_ids": ["find_seo_01"],
                    }
                ],
            }
        return {"verdicts": [{"item_id": "ch_exec_summary", "decision": "supported", "reason": "ok"}, {"item_id": "exec_sl_1", "decision": "supported", "reason": "ok"}]}

    mock_router = MagicMock()
    mock_router.client = MagicMock(provider="anthropic")
    mock_router.telemetry = tracker
    mock_router.budget_manager = MagicMock(max_budget_usd=1.50)
    mock_router.set_active_stage = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_router)

    doc_narrs, overall_mode, tier = await narrate_all_documents(
        report=report,
        model_router=mock_router,
        audit_budget_usd=1.50,  # cap = $0.35 floor
    )

    assert tier == "standard"
    # Executive PDF and Executive PPT MUST run first!
    assert "EXECUTIVE PDF" in call_order[0]
    assert "EXECUTIVE PPT" in call_order[1]
    # Per-document modes: Executive PDF/PPT succeeded (ai_full), later pillars capped -> reduced!
    assert doc_narrs["executive_pdf"]["narrative_mode"] == "ai_full"
    assert doc_narrs["executive_ppt"]["narrative_mode"] == "ai_full"
    assert doc_narrs["seo_pdf"]["narrative_mode"] == "reduced"
    assert doc_narrs["cro_ppt"]["narrative_mode"] == "reduced"
    assert overall_mode == "reduced"
    assert doc_narrs["_summary"]["per_document_modes"]["executive_pdf"] == "ai_full"
    assert doc_narrs["_summary"]["per_document_modes"]["seo_pdf"] == "reduced"


@pytest.mark.asyncio
async def test_offline_or_budget_exhausted_returns_deterministic_fallback():
    report = _sample_report()
    mock_router = MagicMock()
    mock_router.client = MagicMock(provider="anthropic")
    mock_router.telemetry = TelemetryTracker()
    mock_router.budget_manager = MagicMock(max_budget_usd=2.0)
    mock_router.set_active_stage = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={"status": "budget_exceeded", "claims": []})

    doc_narrs, overall_mode, _ = await narrate_all_documents(report=report, model_router=mock_router)
    assert overall_mode == "deterministic_fallback"
    for k in ("executive_pdf", "executive_ppt", "seo_pdf", "seo_ppt", "geo_pdf", "geo_ppt", "aeo_pdf", "aeo_ppt", "cro_pdf", "cro_ppt"):
        assert doc_narrs[k]["narrative_mode"] == "deterministic_fallback"


@pytest.mark.asyncio
async def test_all_10_documents_score_parity_ppt_limits_speaker_notes_and_legacy_full_mode():
    report = _sample_report()
    canonical = displayed_composite(report)
    assert canonical is not None
    expected_score_str = f"{int(round(canonical))}"

    async def _fake_router(**kwargs):
        if kwargs["capability"] == "report_narrative":
            if "PPT" in kwargs["agent_role"]:
                return {
                    "executive_summary": "Canonical posture is {{score.overall}} across {{count.pages_crawled}} crawled pages.",
                    "slides": [
                        {
                            "slide_id": f"sl_{i:02d}",
                            "title": f"Priority Action {chr(65 + i)}",
                            "kicker": "VERIFIED PRIORITY",
                            "bullets": [
                                "Canonical score stands at {{score.overall}} today.",
                                "Analytics conversion impact stays {{label.analytics}}.",
                            ],
                            "speaker_notes": f"Presenter talking point for slide {chr(65 + i)} citing canonical score {{{{score.overall}}}}.",
                            "cited_finding_ids": ["find_seo_01"],
                        }
                        for i in range(6)
                    ],
                }
            return {
                "executive_summary": "Canonical posture is {{score.overall}} across {{count.pages_crawled}} crawled pages.",
                "chapters": [
                    {
                        "chapter_id": "ch_exec_summary",
                        "title": "Executive Posture",
                        "executive_takeaway": "Composite score stands at {{score.overall}}.",
                        "body_md": "Pricing page lacks canonical metadata while analytics remain {{label.analytics}}.",
                        "why_it_matters": "Protects search indexation clarity.",
                        "cited_finding_ids": ["find_seo_01"],
                    }
                ],
            }
        return {"verdicts": [{"item_id": "ch_exec_summary", "decision": "supported", "reason": "ok"}]}

    mock_router = MagicMock()
    mock_router.client = MagicMock(provider="anthropic")
    mock_router.telemetry = TelemetryTracker()
    mock_router.budget_manager = MagicMock(max_budget_usd=10.0)
    mock_router.set_active_stage = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_router)

    doc_narrs, overall_mode, tier = await narrate_all_documents(report=report, model_router=mock_router)
    report.document_narratives = doc_narrs
    report.narrative_mode = overall_mode
    report.narrative_tier = tier

    assert overall_mode == "ai_full"
    # Verify all 10 keys exist
    expected_keys = {
        "executive_pdf", "seo_pdf", "geo_pdf", "aeo_pdf", "cro_pdf",
        "executive_ppt", "seo_ppt", "geo_ppt", "aeo_ppt", "cro_ppt",
    }
    assert expected_keys.issubset(set(doc_narrs.keys()))

    # 1. JSON report score parity
    json_rep = CompleteSeoReportGenerator().render_json_report(report)
    assert json_rep["health_score"] == canonical

    # 2. All 5 PDF HTMLs render with AI narrative block + canonical score
    for family in ("COMPLETE", "SEO", "GEO", "AEO", "CRO"):
        html_doc = render_adaptive_audit_book_html(report, report_type=family)
        assert expected_score_str in html_doc
        assert "ai-chapter-narrative" in html_doc
        assert "Narrative Mode:" in html_doc

    # 3. Condensed Executive PPTX (<=20 slides, speaker notes embedded, canonical score present)
    exec_bytes, exec_bp = generate_executive_pptx_deck(report, mode="standard")
    assert exec_bp.total_slides <= 20
    prs = Presentation(io.BytesIO(exec_bytes))
    assert len(prs.slides) == exec_bp.total_slides
    all_notes = " ".join(
        (s.notes_slide.notes_text_frame.text if s.has_notes_slide else "")
        for s in prs.slides
    )
    assert f"{expected_score_str}/100" in all_notes

    # 4. Legacy full mode preserved for one release (> condensed count)
    _, legacy_bp = generate_executive_pptx_deck(report, mode="legacy_full")
    assert legacy_bp.total_slides > exec_bp.total_slides

    # 5. All 4 pillar PPTXs compile cleanly within standard tier limits
    for pillar in ("seo", "geo", "aeo", "cro"):
        p_bytes, p_bp = generate_section_pptx_deck(report, pillar, mode="standard")
        assert len(p_bytes) > 1000
        assert p_bp.total_slides <= 20


def test_seo_chapter_narratives_map_preserves_all_core_chapters_parity():
    existing = {}
    for idx, ch in enumerate(CORE_CHAPTERS):
        num = f"{idx + 3:02d}"
        entry = {"executive_summary": f"Baseline {ch['id']}", "why_reader_should_care": "Baseline why"}
        existing[ch["id"]] = entry
        existing[num] = entry

    seo_bundle = {
        "narrative_mode": "ai_full",
        "chapters": [
            {
                "chapter_id": "ch_seo_crawl",
                "title": "Crawl Infrastructure & Indexability",
                "executive_takeaway": "AI crawl summary.",
                "body_md": "AI crawl details.",
                "why_it_matters": "AI crawl business impact.",
                "cited_finding_ids": ["find_seo_01"],
            }
        ],
    }
    merged = sync_seo_chapter_narratives_map(seo_bundle, existing, CORE_CHAPTERS)

    # Zero chapters lost: every CORE_CHAPTERS id and numeric key must still exist!
    for idx, ch in enumerate(CORE_CHAPTERS):
        num = f"{idx + 3:02d}"
        assert ch["id"] in merged
        assert num in merged
        assert merged[ch["id"]].get("executive_summary")


def test_orchestrator_runs_stage7b_after_critic_synthesizer_and_remediation():
    src = inspect.getsource(AnalysisOrchestrator._execute_analysis_pipeline_scoped)
    idx_critic = src.index("worker_critic.execute_task(")
    idx_synth = src.index("worker_synthesizer.execute_task(")
    idx_remed = src.index("AiRemediationSynthesizer(model_router)")
    idx_s7b = src.index("narrate_all_documents(")
    idx_gate = src.index("ValidationGate.enforce_gate(")

    assert idx_critic < idx_synth < idx_remed < idx_s7b < idx_gate
