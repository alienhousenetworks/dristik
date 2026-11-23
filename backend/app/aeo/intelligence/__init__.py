"""
Answer Engine Optimization (AEO) Intelligence Package — Phase 5
"""
from typing import Any

from app.aeo.intelligence.question_universe import (
    QuestionUniverseGenerator,
    QuestionUniverseReport,
    BusinessQuestion,
    QuestionIntent,
    FunnelStage,
    BusinessImportance,
    QuestionOriginStream,
)
from app.aeo.intelligence.question_page_graph import (
    QuestionPageGraphEngine,
    QuestionPageGraphReport,
    QuestionPageNode,
    CoverageStatus,
    MappingAnomalyType,
)
from app.aeo.intelligence.answer_completeness import (
    AnswerCompletenessEngine,
    EvaluatedAnswerCompleteness,
    RequiredAnswerElement,
)
from app.aeo.intelligence.passage_extractability import (
    PassageExtractabilityEngine,
    PassageExtractabilityReport,
    ExtractablePassageEvidence,
)
from app.aeo.intelligence.factual_grounding_pipeline import (
    FactualGroundingPipeline,
    FactualGroundingPipelineReport,
    FactualValidationResult,
    CrossPageContradiction,
)
from app.aeo.intelligence.contradiction_detector import (
    ContradictionDetector,
    ContradictionReport,
    FactConflict,
    ConflictSeverity,
)
from app.aeo.intelligence.live_answer_evaluation import (
    LiveAnswerEvaluationEngine,
    LiveAnswerEvaluationReport,
    AeoLiveAnswerTestResult,
)
from app.aeo.intelligence.conversational_voice import (
    ConversationalVoiceEngine,
    ConversationalVoiceReport,
    SpokenAnswerAudit,
)
from app.aeo.intelligence.third_party_credibility import (
    ThirdPartyCredibilityEngine,
    ClaimToSourceGraphReport,
    SupportingSourceNode,
    ClaimToSourceEdge,
)
from app.aeo.intelligence.aeo_scorecard import (
    AeoScorecardEngine,
    AeoScorecardReport,
    AeoDimensionResult,
)
from app.aeo.intelligence.aeo_remediation import (
    AeoRemediationEngine,
    AeoRemediationReport,
    AeoRemediationProposal,
    RemediationTaskStatus,
)

__all__ = [
    "QuestionUniverseGenerator",
    "QuestionUniverseReport",
    "BusinessQuestion",
    "QuestionIntent",
    "FunnelStage",
    "BusinessImportance",
    "QuestionOriginStream",
    "QuestionPageGraphEngine",
    "QuestionPageGraphReport",
    "QuestionPageNode",
    "CoverageStatus",
    "MappingAnomalyType",
    "AnswerCompletenessEngine",
    "EvaluatedAnswerCompleteness",
    "RequiredAnswerElement",
    "PassageExtractabilityEngine",
    "PassageExtractabilityReport",
    "ExtractablePassageEvidence",
    "FactualGroundingPipeline",
    "FactualGroundingPipelineReport",
    "FactualValidationResult",
    "CrossPageContradiction",
    "ContradictionDetector",
    "ContradictionReport",
    "FactConflict",
    "ConflictSeverity",
    "LiveAnswerEvaluationEngine",
    "LiveAnswerEvaluationReport",
    "AeoLiveAnswerTestResult",
    "ConversationalVoiceEngine",
    "ConversationalVoiceReport",
    "SpokenAnswerAudit",
    "ThirdPartyCredibilityEngine",
    "ClaimToSourceGraphReport",
    "SupportingSourceNode",
    "ClaimToSourceEdge",
    "AeoScorecardEngine",
    "AeoScorecardReport",
    "AeoDimensionResult",
    "AeoRemediationEngine",
    "AeoRemediationReport",
    "AeoRemediationProposal",
    "RemediationTaskStatus",
    "run_aeo_intelligence_suite",
    "run_aeo_intelligence_from_report",
]


def _page_to_dict(page: Any) -> dict:
    """Normalize PageEvidence, PageReport, or dict into a uniform text/html record."""
    if isinstance(page, dict):
        return {
            "url": page.get("url", ""),
            "title": page.get("title") or "",
            "body_text": page.get("body_text") or "",
            "html": page.get("rendered_html") or page.get("raw_html") or page.get("body_text") or "",
            "h2": list(page.get("h2") or []),
        }
    url = getattr(page, "url", "") or ""
    title = getattr(page, "title", None) or ""
    body_text = getattr(page, "body_text", None) or ""
    if not body_text:
        parts = [title, getattr(page, "meta_description", None) or ""]
        parts.extend(getattr(page, "h1_tags", None) or getattr(page, "h1", None) or [])
        parts.extend(getattr(page, "h2", None) or [])
        body_text = " ".join(str(p) for p in parts if p).strip()
    html = getattr(page, "rendered_html", None) or getattr(page, "raw_html", None) or body_text
    return {
        "url": url,
        "title": title,
        "body_text": body_text,
        "html": html,
        "h2": list(getattr(page, "h2", None) or []),
    }


def run_aeo_intelligence_suite(
    *,
    domain: str,
    brand_name: str,
    category: str = "",
    pages: list | None = None,
    products: list[str] | None = None,
    faq_items: list[dict] | None = None,
) -> dict:
    """Run the 5 non-redundant AEO intelligence engines on crawled pages.

    Returns a JSON-serializable payload with explicit NOT_MEASURED handling when
    no crawled pages are available.
    """
    normalized = [_page_to_dict(p) for p in (pages or []) if _page_to_dict(p)["url"]]
    if not normalized:
        return {
            "status": "NOT_MEASURED",
            "reason": "No crawled pages were available for AEO intelligence evaluation.",
            "summary": {
                "total_questions": 0,
                "fully_answered_count": 0,
                "partially_answered_count": 0,
                "unanswered_count": 0,
                "competing_pages_count": 0,
                "avg_answer_completeness_pct": None,
                "avg_passage_extractability_score": None,
                "avg_conversational_readiness_score": None,
                "voice_testing_status": "VOICE_SURFACE_UNTESTED",
            },
        }

    # Extract FAQ-style H2 questions from crawled pages if none were explicitly passed
    derived_faqs = list(faq_items or [])
    if not derived_faqs:
        for p in normalized[:10]:
            for h in p["h2"]:
                if isinstance(h, str) and "?" in h:
                    derived_faqs.append({"question": h.strip()})

    universe = QuestionUniverseGenerator.generate_universe(
        domain=domain,
        brand_name=brand_name or domain,
        category=category or "business",
        products=products or None,
        faq_items=derived_faqs or None,
    )

    graph = QuestionPageGraphEngine.build_graph(
        questions=universe.questions,
        crawled_pages=[
            {"url": p["url"], "title": p["title"], "body_text": p["body_text"]}
            for p in normalized
        ],
    )

    url_to_text = {p["url"]: p["body_text"] for p in normalized}
    completeness_results = []
    for node in graph.nodes[:10]:
        if node.target_url and url_to_text.get(node.target_url):
            completeness_results.append(
                AnswerCompletenessEngine.evaluate_passage_completeness(
                    question_id=node.question_id,
                    question_text=node.question_text,
                    target_url=node.target_url,
                    passage_text=url_to_text[node.target_url][:2000],
                )
            )

    extractability_reports = [
        PassageExtractabilityEngine.analyze_page_extractability(
            url=p["url"],
            html=p["html"],
        )
        for p in normalized[:5]
        if p["html"]
    ]

    voice_reports = [
        ConversationalVoiceEngine.audit_conversational_readiness(
            url=p["url"],
            html_or_text=p["html"],
        )
        for p in normalized[:5]
        if p["html"]
    ]

    avg_comp = (
        round(sum(c.completeness_score_pct for c in completeness_results) / len(completeness_results), 1)
        if completeness_results
        else None
    )
    avg_extract = (
        round(sum(e.overall_extractability_score for e in extractability_reports) / len(extractability_reports), 1)
        if extractability_reports
        else None
    )
    avg_voice = (
        round(sum(v.conversational_readiness_score for v in voice_reports) / len(voice_reports), 1)
        if voice_reports
        else None
    )

    return {
        "status": "MEASURED",
        "summary": {
            "total_questions": graph.total_questions,
            "fully_answered_count": graph.fully_answered_count,
            "partially_answered_count": graph.partially_answered_count,
            "unanswered_count": graph.unanswered_count,
            "competing_pages_count": len(graph.competing_pages_detected),
            "avg_answer_completeness_pct": avg_comp,
            "avg_passage_extractability_score": avg_extract,
            "avg_conversational_readiness_score": avg_voice,
            "voice_testing_status": "VOICE_SURFACE_UNTESTED",
        },
        "question_universe": universe.model_dump(mode="json"),
        "question_page_graph": graph.model_dump(mode="json"),
        "answer_completeness": [c.model_dump(mode="json") for c in completeness_results],
        "passage_extractability": [e.model_dump(mode="json") for e in extractability_reports],
        "conversational_voice": [v.model_dump(mode="json") for v in voice_reports],
    }


def run_aeo_intelligence_from_report(report: Any) -> dict:
    """Return precomputed report.aeo_intelligence or compute it on demand from report data."""
    existing = getattr(report, "aeo_intelligence", None)
    if isinstance(existing, dict) and existing:
        return existing
    bp = getattr(report, "business_profile", None)
    manifest = getattr(report, "crawl_manifest", None)
    pages = (getattr(manifest, "pages", None) if manifest else None) or getattr(report, "page_reports", None) or []
    products = list(getattr(bp, "products", None) or []) + list(getattr(bp, "services", None) or [])
    return run_aeo_intelligence_suite(
        domain=getattr(report, "domain", None) or getattr(report, "website_url", "") or "",
        brand_name=(getattr(bp, "business_name", None) if bp else None) or getattr(report, "domain", "") or "",
        category=(getattr(bp, "industry", None) or getattr(bp, "niche", None) or "") if bp else "",
        pages=pages,
        products=products or None,
    )
