"""Phase 5 — Prompt Intelligence & Test-Suite Generation Engine.

Creates representative, explainable, versioned GEO prompt test suites across
all 12 canonical prompt categories with strict separation between:
- Non-branded prompts (discovery, category, recommendation, problem-solving)
- Branded prompts (brand understanding, factual accuracy, reputation, comparison)

Includes deterministic quality validation (rejects leading/biased prompts,
forced brand injection in discovery prompts, multi-question bundling, and
near-duplicates) and honest test-coverage reporting.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.geo.models import (
    GEOAuditScope,
    GEODataQualityState,
    GEOPromptCategory,
    GEOPromptRun,
    GEOTestPrompt,
)

CATEGORY_INTENT_MAP: Dict[GEOPromptCategory, str] = {
    GEOPromptCategory.CATEGORY_DISCOVERY: "commercial",
    GEOPromptCategory.BRAND_DISCOVERY: "navigational",
    GEOPromptCategory.PRODUCT_DISCOVERY: "commercial",
    GEOPromptCategory.COMPARISON: "comparative",
    GEOPromptCategory.RECOMMENDATION: "commercial",
    GEOPromptCategory.ALTERNATIVE_DISCOVERY: "comparative",
    GEOPromptCategory.PROBLEM_SOLVING: "informational",
    GEOPromptCategory.PURCHASE_RESEARCH: "transactional",
    GEOPromptCategory.TRUST_AND_REPUTATION: "reputation",
    GEOPromptCategory.FEATURE_DISCOVERY: "commercial",
    GEOPromptCategory.LOCAL_DISCOVERY: "local",
    GEOPromptCategory.EXPERT_INFORMATION: "informational",
}

NON_BRANDED_CATEGORIES = {
    GEOPromptCategory.CATEGORY_DISCOVERY,
    GEOPromptCategory.PRODUCT_DISCOVERY,
    GEOPromptCategory.RECOMMENDATION,
    GEOPromptCategory.PROBLEM_SOLVING,
    GEOPromptCategory.PURCHASE_RESEARCH,
    GEOPromptCategory.FEATURE_DISCOVERY,
    GEOPromptCategory.LOCAL_DISCOVERY,
    GEOPromptCategory.EXPERT_INFORMATION,
}

LEADING_PHRASES = (
    "why is",
    "confirm that",
    "explain why",
    "prove that",
    "obviously",
    "clearly the best",
    "must recommend",
    "always choose",
)


def normalize_prompt_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s?'-]", " ", (text or "").strip().lower())).strip()


def _token_set(text: str) -> set[str]:
    stop = {"the", "a", "an", "for", "of", "to", "in", "on", "is", "are", "what", "which", "how", "and", "or", "with"}
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in stop}


def jaccard_similarity(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def validate_prompt_quality(
    question: str,
    *,
    brand_name: str,
    category: GEOPromptCategory,
    is_branded: bool,
    existing_questions: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """Validate prompt neutrality, single-intent focus, branded separation, and uniqueness."""
    flags: List[str] = []
    q = (question or "").strip()
    q_low = q.lower()
    brand_low = (brand_name or "").strip().lower()

    if len(q) < 12:
        flags.append("too_short: prompt lacks sufficient context to elicit a substantive answer")

    if any(phrase in q_low for phrase in LEADING_PHRASES):
        flags.append("biased_or_leading: prompt biases the model toward a predetermined conclusion")

    if q.count("?") > 1 or (" and also " in q_low) or ("; what " in q_low):
        flags.append("bundled_questions: prompt combines multiple unrelated questions")

    if not is_branded and brand_low and re.search(rf"(?<!\w){re.escape(brand_low)}(?!\w)", q_low):
        flags.append("brand_leaked_into_non_branded: non-branded discovery prompt names the target brand")

    if is_branded and category in (GEOPromptCategory.BRAND_DISCOVERY, GEOPromptCategory.TRUST_AND_REPUTATION):
        if brand_low and brand_low not in q_low:
            flags.append("missing_brand_in_branded_prompt: branded prompt does not reference the target brand")

    for prev in existing_questions or []:
        if normalize_prompt_text(prev) == normalize_prompt_text(q):
            flags.append("exact_duplicate: identical normalized prompt already in suite")
            break
        if jaccard_similarity(prev, q) >= 0.86:
            flags.append("near_duplicate: superficial wording duplicate of another prompt in suite")
            break

    blocking = [f for f in flags if f.startswith(("too_short", "exact_duplicate", "near_duplicate", "brand_leaked", "biased_or_leading"))]
    return len(blocking) == 0, flags


def generate_prompt_suite(
    scope: GEOAuditScope,
    *,
    audit_id: Optional[str] = None,
    version: int = 1,
) -> List[GEOTestPrompt]:
    """Generate a balanced, deduplicated, quality-checked 12-category GEO prompt suite."""
    brand = scope.brand_name.strip() or scope.domain.split(".")[0].capitalize()
    industry = (scope.industry or "").strip() or "business software"
    products = [p.strip() for p in (scope.products or []) if p and p.strip()]
    services = [s.strip() for s in (scope.services or []) if s and s.strip()]
    offerings = products + services

    def _debrand(label: str) -> str:
        cleaned = re.sub(rf"(?<!\w){re.escape(brand)}(?!\w)", "", label or "", flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—:/")
        return cleaned if len(cleaned) >= 5 else industry

    # Non-branded prompts must never leak the brand name even when product names contain the brand.
    primary_offering = _debrand(offerings[0]) if offerings else industry
    secondary_offering = _debrand(offerings[1]) if len(offerings) > 1 else primary_offering
    raw_primary_product = offerings[0] if offerings else industry
    competitors = [c.strip() for c in (scope.competitors or []) if c and c.strip()]
    primary_comp = competitors[0] if competitors else ""
    secondary_comp = competitors[1] if len(competitors) > 1 else ""
    audience = (scope.target_audience or "").strip() or "buyers"
    markets = scope.markets or ["US"]
    languages = scope.languages or ["en"]
    primary_market = markets[0]
    primary_lang = languages[0]
    platforms = list(scope.platforms_requested or ["chatgpt", "gemini", "claude", "perplexity"])

    # Candidate definitions: (category, is_branded, importance, question, topic, target_product, rationale)
    candidates: List[Tuple[GEOPromptCategory, bool, str, str, str, Optional[str], str]] = [
        # 1. Category discovery (non-branded)
        (
            GEOPromptCategory.CATEGORY_DISCOVERY, False, "critical",
            f"What are the leading {industry} solutions for {audience}?",
            industry, None, "Tests unprompted brand discovery in primary category queries.",
        ),
        (
            GEOPromptCategory.CATEGORY_DISCOVERY, False, "high",
            f"Which companies provide reliable {primary_offering} platforms?",
            primary_offering, primary_offering, "Tests category inclusion around primary offering.",
        ),
        # 2. Brand discovery (branded)
        (
            GEOPromptCategory.BRAND_DISCOVERY, True, "critical",
            f"What does {brand} offer and who is it built for?",
            "brand_identity", None, "Measures factual brand comprehension and positioning.",
        ),
        (
            GEOPromptCategory.BRAND_DISCOVERY, True, "medium",
            f"What are the main products and services offered by {brand}?",
            "brand_portfolio", None, "Checks accuracy of product portfolio attribution.",
        ),
        # 3. Product discovery (non-branded)
        (
            GEOPromptCategory.PRODUCT_DISCOVERY, False, "high",
            f"Which tools solve {primary_offering} needs for {audience}?",
            primary_offering, primary_offering, "Tests product-level discovery without naming the brand.",
        ),
        (
            GEOPromptCategory.PRODUCT_DISCOVERY, False, "medium",
            f"What products are available for {secondary_offering} workflows?",
            secondary_offering, secondary_offering, "Evaluates secondary offering discoverability.",
        ),
        # 4. Comparison (branded + competitor)
        (
            GEOPromptCategory.COMPARISON, True, "critical",
            f"Compare {brand} with {primary_comp} for {industry}."
            if primary_comp else f"How does {brand} compare with other {industry} providers?",
            "head_to_head_comparison", primary_offering, "Measures comparative positioning and factual differentiation.",
        ),
        # 5. Recommendation (non-branded)
        (
            GEOPromptCategory.RECOMMENDATION, False, "critical",
            f"Recommend suitable {industry} providers for {audience} evaluating {primary_offering}.",
            "buyer_recommendation", primary_offering, "Measures explicit shortlist and recommendation share on unbranded intent.",
        ),
        (
            GEOPromptCategory.RECOMMENDATION, False, "high",
            f"Which {primary_offering} providers are worth shortlisting in {primary_market}?",
            "shortlist_recommendation", primary_offering, "Measures regional recommendation inclusion.",
        ),
        # 6. Alternative discovery (competitor-anchored non-target-branded)
        (
            GEOPromptCategory.ALTERNATIVE_DISCOVERY, False, "high",
            f"What are strong alternatives to {primary_comp} for {industry}?"
            if primary_comp else f"What alternatives exist to legacy {industry} tools?",
            "competitor_alternatives", None, "Tests whether target brand surfaces as a rival alternative.",
        ),
        # 7. Problem solving (non-branded)
        (
            GEOPromptCategory.PROBLEM_SOLVING, False, "high",
            f"How should {audience} solve common challenges in {primary_offering}?",
            "problem_solving", primary_offering, "Measures citation and brand inclusion in educational problem-solving answers.",
        ),
        # 8. Purchase research (non-branded + branded)
        (
            GEOPromptCategory.PURCHASE_RESEARCH, False, "high",
            f"What criteria should a buyer evaluate before purchasing a {industry} solution?",
            "buyer_criteria", None, "Tests whether brand content is cited as buying-guide authority.",
        ),
        (
            GEOPromptCategory.PURCHASE_RESEARCH, True, "high",
            f"What should a buyer know about {brand} pricing, onboarding, and limitations?",
            "pricing_and_limits", None, "Tests factual accuracy on pricing and trade-offs.",
        ),
        # 9. Trust and reputation (branded)
        (
            GEOPromptCategory.TRUST_AND_REPUTATION, True, "critical",
            f"Is {brand} reliable and what independent customer reviews or proof exist?",
            "brand_trust", None, "Measures reputation framing, independent citations, and hallucination risk.",
        ),
        # 10. Feature discovery (non-branded)
        (
            GEOPromptCategory.FEATURE_DISCOVERY, False, "medium",
            f"Which {industry} vendors offer documented {primary_offering} capabilities and integrations?",
            "feature_discovery", primary_offering, "Evaluates capability-driven discovery without brand cues.",
        ),
        # 11. Local discovery (non-branded)
        (
            GEOPromptCategory.LOCAL_DISCOVERY, False, "medium",
            f"Which {industry} providers serve customers in {primary_market}?",
            f"local_{primary_market}", None, "Measures geographic visibility for target market.",
        ),
        # 12. Expert information (non-branded)
        (
            GEOPromptCategory.EXPERT_INFORMATION, False, "medium",
            f"Which authoritative sources explain best practices for {industry}?",
            "expert_authority", None, "Measures citation authority in informational expert queries.",
        ),
    ]

    if secondary_comp:
        candidates.append((
            GEOPromptCategory.COMPARISON, True, "medium",
            f"Compare {brand} and {secondary_comp} for {primary_offering}.",
            "secondary_comparison", primary_offering, "Broadens head-to-head competitive coverage.",
        ))

    # Multi-market / multi-language expansions
    for extra_market in markets[1:3]:
        candidates.append((
            GEOPromptCategory.LOCAL_DISCOVERY, False, "medium",
            f"Which {industry} solutions are available for {audience} in {extra_market}?",
            f"local_{extra_market}", None, f"Evaluates visibility in secondary market {extra_market}.",
        ))
    for extra_lang in languages[1:3]:
        candidates.append((
            GEOPromptCategory.CATEGORY_DISCOVERY, False, "medium",
            f"[{extra_lang}] What are the leading {industry} solutions for {audience}?",
            f"multilingual_{extra_lang}", None, f"Evaluates multilingual response consistency ({extra_lang}).",
        ))

    # Additional product-specific discovery prompts when multiple products exist
    for extra_prod in offerings[2:5]:
        generic_prod = _debrand(extra_prod)
        candidates.append((
            GEOPromptCategory.PRODUCT_DISCOVERY, False, "medium",
            f"Which providers offer {generic_prod} capabilities for {audience}?",
            generic_prod, extra_prod, f"Tests discovery visibility for product/service '{extra_prod}'.",
        ))

    accepted: List[GEOTestPrompt] = []
    seen_texts: List[str] = []
    max_n = max(4, min(scope.max_prompts, 200))

    for cat, is_branded, imp, q_text, topic, prod, rationale in candidates:
        if len(accepted) >= max_n:
            break
        ok, flags = validate_prompt_quality(
            q_text,
            brand_name=brand,
            category=cat,
            is_branded=is_branded,
            existing_questions=seen_texts,
        )
        if not ok:
            continue
        lang = primary_lang
        mkt = primary_market
        if topic.startswith("multilingual_"):
            lang = topic.split("_", 1)[1]
        elif topic.startswith("local_"):
            mkt = topic.split("_", 1)[1]
        accepted.append(
            GEOTestPrompt(
                tenant_id=scope.tenant_id,
                audit_id=audit_id,
                question=q_text,
                normalized_question=normalize_prompt_text(q_text),
                category=cat,
                intent=CATEGORY_INTENT_MAP[cat],
                is_branded=is_branded,
                topic=topic,
                target_brand=brand,
                target_product=prod,
                relevant_competitors=competitors,
                market=mkt,
                language=lang,
                importance=imp,
                testing_rationale=rationale,
                version=version,
                applicable_platforms=platforms,
                repetitions=scope.repetitions,
                approval_status="approved",
                quality_flags=flags,
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )
        seen_texts.append(q_text)

    return accepted


def compute_prompt_coverage(
    prompts: List[GEOTestPrompt],
    runs: List[GEOPromptRun],
) -> Dict[str, Any]:
    """Report honest prompt test coverage across platforms, markets, languages, intents, and repeats."""
    approved = [p for p in prompts if p.approval_status == "approved"]
    approved_ids = {p.prompt_id for p in approved}
    branded_total = sum(1 for p in approved if p.is_branded)
    non_branded_total = sum(1 for p in approved if not p.is_branded)

    executed_prompt_ids = {r.prompt_id for r in runs if r.prompt_id in approved_ids}
    succeeded_runs = [r for r in runs if r.status == GEODataQualityState.OBSERVED]
    failed_runs = [r for r in runs if r.status in (GEODataQualityState.FAILED, GEODataQualityState.UNAVAILABLE)]
    succeeded_prompt_ids = {r.prompt_id for r in succeeded_runs if r.prompt_id in approved_ids}

    platforms_seen = sorted({r.platform_id for r in succeeded_runs})
    markets_seen = sorted({p.market for p in approved})
    languages_seen = sorted({p.language for p in approved})
    intents_seen = sorted({p.intent for p in approved})
    categories_seen = sorted({p.category.value for p in approved})
    max_repeat = max((r.repetition_number for r in runs), default=0)

    completion_pct = (
        round((len(succeeded_prompt_ids) / len(approved)) * 100.0, 1) if approved else 0.0
    )

    return {
        "approved_prompts": len(approved),
        "branded_prompts": branded_total,
        "non_branded_prompts": non_branded_total,
        "prompts_executed": len(executed_prompt_ids),
        "prompts_succeeded": len(succeeded_prompt_ids),
        "total_runs_attempted": len(runs),
        "total_runs_succeeded": len(succeeded_runs),
        "total_runs_failed": len(failed_runs),
        "prompt_completion_pct": completion_pct,
        "is_partial_coverage": len(succeeded_prompt_ids) < len(approved),
        "platforms_covered": platforms_seen,
        "markets_covered": markets_seen,
        "languages_covered": languages_seen,
        "intents_covered": intents_seen,
        "categories_covered": categories_seen,
        "repeat_coverage_max": max_repeat,
    }
