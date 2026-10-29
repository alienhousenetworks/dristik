"""
Topical Authority & Content Quality Analyzer for Dristik
Evaluates semantic entities, outline depth, non-commodity information gain,
first-party evidence, original data points, expert bylines, unsupported claims,
content cannibalization, and search intent alignment.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from app.domain.enums import Category, EvidenceClass, RubricConfidence, Severity
from app.domain.models import (
    CannibalizationCluster,
    Finding,
    FindingEvidence,
    PageContentAuthority,
    PageEvidence,
    TopicalAuthorityAuditReport,
)


def _tokenize_ngrams(text: str, n: int = 3) -> Set[str]:
    """Tokenize clean words into n-grams for similarity comparison."""
    words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text or "")]
    if len(words) < n:
        return set(words)
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return float(intersection) / float(union) if union > 0 else 0.0


def analyze_topical_authority(
    pages: Sequence[PageEvidence],
    target_domain: str = "",
) -> Tuple[TopicalAuthorityAuditReport, List[Finding]]:
    """
    Audits content depth, topical authority, information gain,
    claims without evidence, and cannibalization across crawled pages.
    """
    if not pages:
        return TopicalAuthorityAuditReport(
            status="THIN_COMMODITY",
            summary="No pages available for content authority analysis.",
        ), []

    page_authorities: List[PageContentAuthority] = []
    findings: List[Finding] = []
    total_data_points = 0
    total_unbacked_claims = 0
    pages_with_expert = 0
    total_info_gain = 0.0
    intent_counts: Dict[str, int] = {}
    ngram_maps: Dict[str, Set[str]] = {}

    for p in pages:
        ca = p.content_authority or {}
        w_cnt = p.word_count or ca.get("word_count", 0)
        entities = ca.get("topical_entities") or []
        ig_score = float(ca.get("information_gain_score") or 50.0)
        orig_data = int(ca.get("original_data_points") or 0)
        evidence_markers = ca.get("first_party_evidence_markers") or []
        experts = ca.get("expert_signals") or []
        unbacked = ca.get("unbacked_claims") or []
        intent = ca.get("search_intent") or "INFORMATIONAL"

        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        total_data_points += orig_data
        total_unbacked_claims += len(unbacked)
        total_info_gain += ig_score
        if experts:
            pages_with_expert += 1

        # Check intent mismatch
        intent_mismatch = False
        intent_notes = ""
        p_text_low = (p.body_text or "").lower()
        if intent == "COMMERCIAL" and not any(k in p_text_low for k in ["pricing", "cost", "comparison", "feature"]):
            intent_mismatch = True
            intent_notes = "Commercial intent target page lacks structured pricing or feature comparison table."
        elif intent == "TRANSACTIONAL" and not p.ctas:
            intent_mismatch = True
            intent_notes = "Transactional page lacks prominent call-to-action button above the fold."

        pca = PageContentAuthority(
            url=p.url,
            word_count=w_cnt,
            topical_entities=entities,
            information_gain_score=ig_score,
            original_data_points=orig_data,
            first_party_evidence_markers=evidence_markers,
            expert_signals=experts,
            unbacked_claims=unbacked,
            search_intent=intent,
            intent_mismatch=intent_mismatch,
            intent_notes=intent_notes,
        )
        page_authorities.append(pca)

        # Store n-grams for cannibalization check
        ngram_maps[p.url] = _tokenize_ngrams(p.body_text or "", n=3)

    # 1. Detect Content Cannibalization & Near-Duplicates
    cannibalization_clusters: List[CannibalizationCluster] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for i in range(len(pages)):
        for j in range(i + 1, len(pages)):
            p1 = pages[i]
            p2 = pages[j]
            pair_key = (p1.url, p2.url)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            sim = _jaccard_similarity(ngram_maps.get(p1.url, set()), ngram_maps.get(p2.url, set()))
            # Heading overlap
            h1_p1 = set(h.lower().strip() for h in (p1.h1 or []))
            h1_p2 = set(h.lower().strip() for h in (p2.h1 or []))
            shared_h1 = list(h1_p1 & h1_p2)

            # High similarity (> 0.40 on 3-grams) or identical H1 means cannibalization risk
            if sim > 0.40 or (shared_h1 and sim > 0.25):
                topic = shared_h1[0] if shared_h1 else (p1.title or "Target Topic")
                cluster_id = f"cannibalization_{len(cannibalization_clusters) + 1}"
                cannibalization_clusters.append(
                    CannibalizationCluster(
                        cluster_id=cluster_id,
                        primary_topic=topic,
                        urls=[p1.url, p2.url],
                        similarity_score=round(sim, 2),
                        shared_headings=shared_h1,
                        recommendation="Consolidate near-duplicate URLs into a single comprehensive authoritative guide or assign distinct search intents.",
                    )
                )

    # 2. Aggregate Metrics
    n_pages = max(1, len(pages))
    avg_ig = round(total_info_gain / n_pages, 1)
    evidence_density = round(float(total_data_points) / float(n_pages), 1)

    # Topical Coverage Score (combining entities, outline, and information gain)
    unique_entities = set(e.lower() for pa in page_authorities for e in pa.topical_entities)
    outline_depth = sum(len(p.h2 or []) for p in pages)
    coverage_score = min(100.0, 30.0 + len(unique_entities) * 3.5 + min(30.0, outline_depth * 2.0))
    coverage_score = round(coverage_score, 1)

    # Status Determination
    if avg_ig >= 70.0 and total_unbacked_claims == 0 and not cannibalization_clusters:
        status = "PASS"
        summary = (
            f"High topical authority with superior Information Gain ({avg_ig}/100). "
            f"Content is substantiated by {total_data_points} empirical data points and distinct search intent across pages."
        )
    elif avg_ig < 45.0 or total_unbacked_claims >= 5 or len(cannibalization_clusters) >= 2:
        status = "THIN_COMMODITY"
        summary = (
            f"Low Information Gain ({avg_ig}/100) and commodity content risk. "
            f"Detected {total_unbacked_claims} unsupported superlative claims and {len(cannibalization_clusters)} cannibalization cluster(s)."
        )
    else:
        status = "NEEDS_IMPROVEMENT"
        summary = (
            f"Moderate topical authority ({coverage_score}/100) with room to deepen first-party evidence "
            f"and resolve {len(cannibalization_clusters)} content cannibalization cluster(s)."
        )

    # 3. Generate Findings
    home_url = pages[0].url if pages else f"https://{target_domain}"

    # Finding 1: Unbacked claims
    if total_unbacked_claims > 0:
        pages_with_unbacked = [pa for pa in page_authorities if pa.unbacked_claims]
        example_claims = pages_with_unbacked[0].unbacked_claims if pages_with_unbacked else []
        findings.append(
            Finding(
                finding_id="content_unbacked_superlative_claims",
                title=f"Unsupported Superlative Claims Detected ({total_unbacked_claims} occurrences)",
                description=(
                    f"The crawler identified {total_unbacked_claims} instances of superlative marketing claims "
                    f"(such as '{', '.join(example_claims[:3])}') lacking proximal numerical data, customer citations, or empirical proof. "
                    "Modern Google helpful content and AI-search evaluation penalize unsubstantiated buzzwords in favor of verifiable evidence."
                ),
                category=Category.CONTENT,
                severity=Severity.HIGH if total_unbacked_claims > 3 else Severity.MEDIUM,
                confidence=0.92,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_content_authority",
                        detail=f"Detected superlatives: {', '.join(example_claims)}",
                        url=pages_with_unbacked[0].url if pages_with_unbacked else home_url,
                    )
                ],
                recommendation=(
                    "Substantiate superlative claims with specific first-party metrics, customer case study statistics, "
                    "or third-party industry benchmarks."
                ),
            )
        )

    # Finding 2: Content Cannibalization
    if cannibalization_clusters:
        first_cluster = cannibalization_clusters[0]
        findings.append(
            Finding(
                finding_id="content_cannibalization_clusters",
                title=f"Content Cannibalization & Near-Duplicate Pages ({len(cannibalization_clusters)} clusters)",
                description=(
                    f"Identified {len(cannibalization_clusters)} content cannibalization cluster(s) with high 3-gram text similarity "
                    f"(e.g. {first_cluster.urls[0]} and {first_cluster.urls[1]} share {int(first_cluster.similarity_score * 100)}% identical phrasing). "
                    "Competing internal pages dilute keyword equity and confuse search engine indexing."
                ),
                category=Category.CONTENT,
                severity=Severity.HIGH,
                confidence=0.95,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_cannibalization_detector",
                        detail=f"Overlapping URLs: {', '.join(first_cluster.urls)}",
                        url=first_cluster.urls[0],
                    )
                ],
                recommendation=(
                    "Merge competing near-duplicate pages into a single pillar page, redirect the weaker URL with a 301, "
                    "or differentiate each page's primary search intent and H1 outline."
                ),
            )
        )

    # Finding 3: Low Information Gain / Commodity content
    if avg_ig < 50.0 and total_data_points < 3:
        findings.append(
            Finding(
                finding_id="content_low_information_gain",
                title="Low Information Gain: Commodity Content Lacks First-Party Evidence",
                description=(
                    "The crawled pages exhibit low Information Gain scores (averaging below 50/100) with virtually zero original data points, "
                    "case studies, proprietary benchmarks, or data tables. Under Google's AI-search guidance, commoditized generic copy "
                    "lacks the citation-worthiness required to earn top organic and generative search rankings."
                ),
                category=Category.CONTENT,
                severity=Severity.HIGH,
                confidence=0.90,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_information_gain_scorer",
                        detail=f"Average Information Gain: {avg_ig}/100 across {len(pages)} crawled page(s).",
                        url=home_url,
                    )
                ],
                recommendation=(
                    "Incorporate unique first-party data: publish proprietary benchmark reports, customer ROI metrics, "
                    "concrete case studies with quantifiable outcomes, and structured comparison tables."
                ),
            )
        )

    # Finding 4: Search Intent Mismatches
    intent_mismatches = [pa for pa in page_authorities if pa.intent_mismatch]
    if intent_mismatches:
        findings.append(
            Finding(
                finding_id="content_search_intent_mismatch",
                title=f"Search Intent Mismatch on Key Landing Pages ({len(intent_mismatches)} pages)",
                description=(
                    f"Found {len(intent_mismatches)} page(s) where page copy fails search intent expectations. "
                    f"Example: {intent_mismatches[0].url} targets commercial/transactional queries but {intent_mismatches[0].intent_notes}"
                ),
                category=Category.CONTENT,
                severity=Severity.MEDIUM,
                confidence=0.88,
                rubric_confidence=RubricConfidence.VERIFIED,
                evidence_class=EvidenceClass.OBSERVED,
                evidence=[
                    FindingEvidence(
                        source="crawler_intent_classifier",
                        detail=intent_mismatches[0].intent_notes,
                        url=intent_mismatches[0].url,
                    )
                ],
                recommendation=(
                    "Align page content with buyer intent: ensure commercial pages include pricing and feature grids, "
                    "and ensure high-intent transactional pages feature clear, unencumbered CTA actions."
                ),
            )
        )

    report = TopicalAuthorityAuditReport(
        status=status,
        topical_coverage_score=coverage_score,
        avg_information_gain=avg_ig,
        total_original_data_points=total_data_points,
        first_party_evidence_density=evidence_density,
        pages_with_expert_signals=pages_with_expert,
        unbacked_claims_total=total_unbacked_claims,
        cannibalization_clusters=cannibalization_clusters,
        search_intent_distribution=intent_counts,
        pages=page_authorities,
        summary=summary,
    )

    return report, findings
