"""
Dristik AI Deterministic Scoring Engine
Calculates mathematically weighted 0-100 scores from verified observations and intent-adaptive weights.
"""
from typing import List, Dict, Optional, Any
from app.domain.models import Finding, CategoryScore, OverallScoreResult, BusinessProfile
from app.domain.enums import Category, Severity, BusinessIntent
from app.scoring.weights import compute_intent_adjusted_weights


def _diminishing_deduction(severity: Severity, occurrence_index: int) -> float:
    """First finding of a severity hits hardest; repeats add less so marks stay calibrated."""
    tables = {
        Severity.CRITICAL: (25.0, 12.0, 8.0, 5.0),
        Severity.HIGH: (15.0, 9.0, 6.0, 4.0),
        Severity.MEDIUM: (8.0, 5.0, 3.0, 2.0),
        Severity.LOW: (3.0, 2.0, 1.0, 1.0),
        Severity.INFO: (0.0, 0.0, 0.0, 0.0),
    }
    steps = tables.get(severity, (3.0, 2.0, 1.0, 1.0))
    if occurrence_index < len(steps):
        return steps[occurrence_index]
    return steps[-1]


def _get_category_formula_breakdown(
    cat: Category,
    raw_score: float,
    deductions: Optional[List[Dict[str, Any]]] = None,
    is_provisional_neutral: bool = False
) -> List[Dict[str, Any]]:
    rubrics = {
        Category.GEO: [
            ("Entity clarity & canonical definition", 20.0, "MEASURED_DOM", ["entity", "identity", "canonical", "organization"]),
            ("Direct buyer question answerability", 20.0, "MEASURED_DOM", ["answer", "question", "direct", "extract"]),
            ("Structured data & Schema grounding", 15.0, "MEASURED_DOM", ["schema", "json-ld", "structured", "microdata"]),
            ("Commercial question coverage", 15.0, "MEASURED_DOM", ["commercial", "pricing", "icp", "coverage"]),
            ("Citation-ready passage density", 15.0, "MEASURED_DOM", ["citation", "passage", "snippet", "paragraph"]),
            ("Semantic consistency & bot access", 15.0, "MEASURED_DOM", ["llms.txt", "bot", "crawler", "robots", "access"]),
        ],
        Category.CONTENT: [
            ("Topic depth & service capability coverage", 25.0, "MEASURED_DOM", ["depth", "word", "thin", "coverage", "service"]),
            ("Readability & scan-friendly syntax", 25.0, "MEASURED_DOM", ["readability", "flesch", "scan", "syntax", "grammar"]),
            ("Value proposition & heading clarity", 25.0, "MEASURED_DOM", ["heading", "h1", "value proposition", "clarity", "title"]),
            ("Semantic hierarchy & outline structure", 25.0, "MEASURED_DOM", ["hierarchy", "outline", "h2", "h3", "structure"]),
        ],
        Category.TECHNICAL_SEO: [
            ("Crawl accessibility, robots.txt & sitemap hygiene", 25.0, "MEASURED_DOM", ["robots", "sitemap", "crawl", "index"]),
            ("HTTPS security & protocol transport", 25.0, "MEASURED_TRANSPORT", ["https", "ssl", "tls", "security", "transport"]),
            ("TTFB & response latency", 25.0, "MEASURED_PERFORMANCE", ["ttfb", "latency", "speed", "performance", "response", "load"]),
            ("Canonical DOM & link hygiene", 25.0, "MEASURED_DOM", ["canonical", "link", "broken", "redirect", "href"]),
        ],
        Category.SCHEMA: [
            ("Entity Organization graph definition", 30.0, "MEASURED_DOM", ["organization", "entity", "sameas", "graph"]),
            ("WebSite & navigation breadcrumb markup", 25.0, "MEASURED_DOM", ["website", "breadcrumb", "navigation", "sitelinks"]),
            ("Structured Q&A & FAQ content grounding (GEO/AEO extractability)", 25.0, "MEASURED_DOM", ["faq", "q&a", "question", "answer"]),
            ("DOM text cross-grounding consistency", 20.0, "MEASURED_DOM", ["cross-grounding", "consistency", "mismatch", "conflict"]),
        ],
        Category.UX_CONVERSION: [
            ("5-second value proposition clarity", 25.0, "MEASURED_DOM", ["value prop", "5-second", "clarity", "hero"]),
            ("Primary call-to-action prominence", 25.0, "MEASURED_DOM", ["cta", "button", "call to action", "prominence"]),
            ("Form friction & interaction ease", 25.0, "MEASURED_DOM", ["form", "input", "field", "friction", "submit"]),
            ("Viewport & responsive mobile layout", 25.0, "MEASURED_DOM", ["mobile", "viewport", "responsive", "layout"]),
        ],
        Category.TRUST_AUTHORITY: [
            ("Social proof, testimonials & client logos", 30.0, "MEASURED_DOM", ["testimonial", "logo", "proof", "review", "client"]),
            ("Security, compliance & privacy transparency", 25.0, "MEASURED_DOM", ["security", "compliance", "privacy", "gdpr", "soc2"]),
            ("Corporate origin & verified contact", 25.0, "MEASURED_DOM", ["contact", "address", "phone", "email", "origin", "about"]),
            ("Claim verifiability without hyperbole", 20.0, "MEASURED_DOM", ["claim", "hyperbole", "verifiability", "guarantee"]),
        ],
        Category.ON_PAGE_SEO: [
            ("Title tag length & unique keywords", 25.0, "MEASURED_DOM", ["title", "tag"]),
            ("Meta description compellingness & bounds", 25.0, "MEASURED_DOM", ["description", "meta"]),
            ("Single H1 & heading tag hierarchy", 25.0, "MEASURED_DOM", ["h1", "heading"]),
            ("OpenGraph & social preview meta", 25.0, "MEASURED_DOM", ["opengraph", "og:", "social", "twitter"]),
        ],
        Category.AI_SEARCH: [
            ("Citability index & definition blocks", 30.0, "MEASURED_DOM", ["citability", "definition", "block"]),
            ("Brand identity resolution in answer engines", 25.0, "SIMULATION_HEURISTIC", ["identity", "brand", "resolution", "model"]),
            ("Competitive displacement resistance", 25.0, "SIMULATION_HEURISTIC", ["displacement", "competitor", "alternative", "moat"]),
            ("Structured commercial Q&A coverage", 20.0, "MEASURED_DOM", ["commercial", "q&a", "coverage", "pricing"]),
        ],
    }
    specs = rubrics.get(cat, [
        ("Core structural compliance", 50.0, "MEASURED_DOM", ["core", "compliance"]),
        ("Best practice execution", 50.0, "MEASURED_DOM", ["best practice"]),
    ])

    if is_provisional_neutral:
        return [
            {
                "component": item[0],
                "points_earned": round(item[1] * 0.5, 1),
                "points_possible": item[1],
                "provenance": "PROVISIONAL_BASELINE",
                "status": "PROVISIONAL_NEUTRAL"
            }
            for item in specs
        ]

    # Map deductions directly to matching components
    component_deductions = {item[0]: 0.0 for item in specs}
    unmatched_deductions = 0.0

    if deductions:
        for d in deductions:
            pts = float(d.get("points_lost", 0.0))
            text = f"{d.get('title', '')} {d.get('finding_id', '')}".lower()
            matched = False
            for item in specs:
                label = item[0]
                kw_list = item[3] if len(item) > 3 else []
                if any(kw in text for kw in kw_list):
                    component_deductions[label] += pts
                    matched = True
                    break
            if not matched:
                unmatched_deductions += pts

    # Distribute unmatched deductions across components proportionally
    total_possible = sum(item[1] for item in specs) or 100.0
    breakdown = []
    earned_so_far = 0.0

    for idx, item in enumerate(specs):
        label = item[0]
        possible = item[1]
        provenance = item[2] if len(item) > 2 else "MEASURED_DOM"
        comp_ded = component_deductions.get(label, 0.0) + (unmatched_deductions * (possible / total_possible))
        earned = max(0.0, round(possible - comp_ded, 1))

        if idx == len(specs) - 1 and deductions:
            # Adjust final to match raw_score accurately if within reasonable bound
            diff = round(raw_score - (earned_so_far + earned), 1)
            if abs(diff) <= possible * 0.5:
                earned = max(0.0, min(possible, round(earned + diff, 1)))

        earned_so_far += earned
        breakdown.append({
            "component": label,
            "points_earned": earned,
            "points_possible": possible,
            "provenance": provenance,
            "status": "PASS" if earned >= possible * 0.75 else ("DEFICIT" if earned < possible * 0.4 else "PARTIAL")
        })
    return breakdown


class ScoringEngine:
    def calculate_scores(
        self,
        findings: List[Finding],
        business_profile: BusinessProfile,
        has_schema: bool = True,
        is_https: bool = True,
        readability: float = 65.0
    ) -> OverallScoreResult:
        intent = business_profile.primary_intent if business_profile else BusinessIntent.LEAD_GENERATION
        weights = compute_intent_adjusted_weights(intent)

        category_deductions: Dict[Category, float] = {cat: 0.0 for cat in weights.keys()}
        category_deduction_items: Dict[Category, List[Dict[str, Any]]] = {cat: [] for cat in weights.keys()}
        category_strengths: Dict[Category, List[str]] = {cat: [] for cat in weights.keys()}
        category_weaknesses: Dict[Category, List[str]] = {cat: [] for cat in weights.keys()}
        severity_counts: Dict[Category, Dict[Severity, int]] = {
            cat: {s: 0 for s in Severity} for cat in weights.keys()
        }

        from app.domain.enums import RubricConfidence, EvidenceClass
        from app.cognition.finding_registry import _canonical_id
        from app.scoring.calibration import calibrate_finding, deduction_scales

        seen_root_causes: Dict[str, Category] = {}

        for f in findings:
            rubric = getattr(f, "confidence_rubric", None)
            # Gate: hypotheses and low-confidence findings do NOT reduce category scores.
            # This uses the canonical affects_score property which covers all v1 and v2 values.
            if rubric is not None and not rubric.affects_score:
                continue
            if getattr(f, "held_from_executive", False) and not getattr(f, "adversarial_reviewed", False):
                continue
            cat = f.category
            if cat not in category_deductions:
                continue

            # Root-cause deduplication:
            # When multiple findings stem from the exact same structural root cause
            # (e.g. root_h1_identity_slogan_mismatch spanning Content, On-Page SEO, GEO, and Schema),
            # the primary category absorbs the primary deduction, while downstream categories
            # take a discounted marginal penalty (50%) to prevent duplicate penalties.
            cid = _canonical_id(f)
            is_secondary_downstream = (cid in seen_root_causes and seen_root_causes[cid] != cat)
            if cid not in seen_root_causes:
                seen_root_causes[cid] = cat

            calibrate_finding(f)
            calibrated = f.calibrated_impact
            idx = severity_counts[cat][f.severity]
            base_points = _diminishing_deduction(f.severity, idx)
            if is_secondary_downstream:
                base_points = round(base_points * 0.5, 1)
            business_scale, confidence_scale = deduction_scales(calibrated)
            points_lost = round(base_points * business_scale * confidence_scale, 1)

            category_deductions[cat] += points_lost
            severity_counts[cat][f.severity] = idx + 1
            category_weaknesses[cat].append(f.title)
            category_deduction_items[cat].append({
                "finding_id": f.finding_id,
                "title": f.title + (" (Downstream Consequence)" if is_secondary_downstream else ""),
                "severity": f.severity.value,
                "technical_severity": calibrated.technical_severity.value if calibrated else f.severity.value,
                "business_impact": calibrated.business_impact_label if calibrated else "Medium",
                "confidence_band": calibrated.confidence_band.value if calibrated else "MEDIUM",
                "blocking": bool(calibrated.is_blocking) if calibrated else False,
                "confidence": rubric.customer_label if (rubric and hasattr(rubric, "customer_label")) else "Unknown",
                "points_lost": round(points_lost, 1),
                "is_downstream_consequence": is_secondary_downstream,
                "why_it_matters": getattr(f, "why_it_matters", None) or f.title
            })

        # Site-fact calibration only when the audit actually produced findings,
        # so an empty finding list remains a perfect 100 (unit-test invariant).
        if findings:
            if not has_schema and not category_weaknesses.get(Category.SCHEMA):
                category_deductions[Category.SCHEMA] += 8.0
                category_weaknesses[Category.SCHEMA].append("No Schema.org types recorded in the crawl sample.")
                category_deduction_items[Category.SCHEMA].append({
                    "finding_id": "fact_schema_missing",
                    "title": "No Schema.org types recorded in crawl sample",
                    "severity": "HIGH",
                    "points_lost": 8.0,
                    "why_it_matters": "Search and answer engines cannot resolve structured corporate entity data."
                })
            if not is_https and not category_weaknesses.get(Category.TECHNICAL_SEO):
                category_deductions[Category.TECHNICAL_SEO] += 15.0
                category_weaknesses[Category.TECHNICAL_SEO].append("Homepage was not served over HTTPS.")
                category_deduction_items[Category.TECHNICAL_SEO].append({
                    "finding_id": "fact_https_missing",
                    "title": "Homepage not served over HTTPS",
                    "severity": "CRITICAL",
                    "points_lost": 15.0,
                    "why_it_matters": "Insecure HTTP connection triggers browser warnings and search engine penalties."
                })
            if readability < 50:
                category_deductions[Category.CONTENT] += 6.0
                category_weaknesses[Category.CONTENT].append(
                    f"Measured readability {readability:.0f} is hard for a first-time buyer to scan."
                )
                category_deduction_items[Category.CONTENT].append({
                    "finding_id": "fact_readability_low",
                    "title": f"Measured readability {readability:.0f} is difficult to scan",
                    "severity": "MEDIUM",
                    "points_lost": 6.0,
                    "why_it_matters": "High reading difficulty increases bounce rates and reduces direct quotation."
                })
            elif readability >= 80 and not category_weaknesses.get(Category.CONTENT):
                category_strengths[Category.CONTENT].append(
                    f"Measured readability {readability:.0f} is clear enough for a first-pass buyer scan."
                )

        cat_scores: Dict[str, CategoryScore] = {}
        total_weighted = 0.0

        total_findings = len(findings)
        findings_with_ev = sum(1 for f in findings if f.evidence_refs)
        evidence_cov = round(findings_with_ev / max(1, total_findings), 2) if total_findings > 0 else 0.0

        # Evidence quality: fraction of findings backed by OBSERVED or EXTERNALLY_VERIFIED evidence.
        # This is a stronger signal than mere coverage (having any evidence_refs).
        high_quality_ev = sum(
            1 for f in findings
            if getattr(f, "evidence_class", None) in (
                EvidenceClass.OBSERVED, EvidenceClass.EXTERNALLY_VERIFIED
            )
        )
        evidence_quality = round(high_quality_ev / max(1, total_findings), 2) if total_findings > 0 else 0.0

        # Overall confidence: blend coverage and quality — quality matters more.
        overall_conf = round(
            min(0.95, 0.40 + (0.30 * evidence_cov) + (0.25 * evidence_quality)),
            2
        ) if total_findings > 0 else 0.0

        for cat, weight in weights.items():
            raw_score = max(20.0, min(100.0, 100.0 - category_deductions[cat]))
            n_issues = len(category_weaknesses[cat])

            is_provisional = False
            if not category_weaknesses[cat]:
                has_positive_proof = bool(category_strengths.get(cat))
                effective_findings = [f for f in findings if getattr(f, "confidence_rubric", None) is None or getattr(f, "confidence_rubric").affects_score]
                if effective_findings and not has_positive_proof:
                    # Absence of evidence is not proof of excellence: Cap at Provisional Neutral (50)
                    raw_score = 50.0
                    is_provisional = True
                    category_strengths[cat].append(
                        f"Provisional neutral baseline for {cat.value.replace('_', ' ').title()}."
                    )
                    summary = (
                        f"50/100 (Provisional Neutral). Insufficient direct signals in crawl sample to verify excellence; "
                        f"capped at neutral baseline pending extended crawl or live connector integration."
                    )
                else:
                    if effective_findings:
                        raw_score = min(95.0, raw_score)
                    category_strengths[cat].append(
                        f"No defects recorded in the crawled sample for {cat.value.replace('_', ' ').title()}."
                    )
                    summary = (
                        f"{raw_score:.0f}/100. Verified compliant execution with zero defects recorded in the crawl sample."
                    )
            else:
                items = category_deduction_items[cat]
                top_item = max(items, key=lambda item: item.get("points_lost", 0)) if items else None
                if top_item:
                    blocking_word = "yes" if top_item.get("blocking") else "no"
                    summary = (
                        f"{raw_score:.0f}/100 from {n_issues} verified finding{'s' if n_issues != 1 else ''}. "
                        f"Largest deduction: {top_item['title']} "
                        f"(technical {top_item.get('technical_severity')}, "
                        f"business {top_item.get('business_impact')}, "
                        f"confidence {top_item.get('confidence_band')}, "
                        f"blocking {blocking_word})."
                    )
                else:
                    top = category_weaknesses[cat][0]
                    summary = (
                        f"{raw_score:.0f}/100 from {n_issues} verified finding{'s' if n_issues != 1 else ''}. "
                        f"Largest deduction: {top}."
                    )

            cat_findings = [f for f in findings if f.category == cat]
            cat_ev_count = sum(1 for f in cat_findings if f.evidence_refs)
            cat_hq_count = sum(
                1 for f in cat_findings
                if getattr(f, "evidence_class", None) in (
                    EvidenceClass.OBSERVED, EvidenceClass.EXTERNALLY_VERIFIED
                )
            )
            cat_ev_ratio = (cat_ev_count / len(cat_findings)) if cat_findings else 0.5
            cat_hq_ratio = (cat_hq_count / len(cat_findings)) if cat_findings else 0.0
            cat_confidence = round(
                min(0.95, 0.40 + 0.30 * cat_ev_ratio + 0.25 * cat_hq_ratio), 2
            ) if cat_findings else 0.50

            formula_breakdown = _get_category_formula_breakdown(
                cat,
                raw_score,
                deductions=category_deduction_items.get(cat, []),
                is_provisional_neutral=is_provisional
            )

            c_score = CategoryScore(
                category=cat,
                score=round(raw_score, 1),
                confidence=cat_confidence,
                weight=round(weight, 3),
                weighted_score=round(raw_score * weight, 2),
                strengths=category_strengths[cat][:3],
                weaknesses=category_weaknesses[cat][:4],
                summary=summary,
                deductions=category_deduction_items[cat],
                formula_breakdown=formula_breakdown
            )
            cat_scores[cat.value] = c_score
            total_weighted += raw_score * weight

        math_derivation = []
        for cat, weight in weights.items():
            raw = cat_scores[cat.value].score
            w_pct = round(weight * 100.0, 1)
            contribution = round(raw * weight, 2)
            math_derivation.append({
                "category": cat.value,
                "category_label": cat.value.replace("_", " ").title(),
                "raw_score": raw,
                "weight_pct": w_pct,
                "weight": round(weight, 3),
                "weighted_points": contribution
            })

        overall_score = round(max(0.0, min(100.0, sum(row["weighted_points"] for row in math_derivation))), 1)

        if overall_score >= 93:
            grade = "A+"
            health = "Exceptional"
        elif overall_score >= 85:
            grade = "A"
            health = "Excellent"
        elif overall_score >= 75:
            grade = "B"
            health = "Good"
        elif overall_score >= 65:
            grade = "C"
            health = "Moderate"
        elif overall_score >= 50:
            grade = "D"
            health = "Needs Attention"
        else:
            grade = "F"
            health = "Low readiness"

        return OverallScoreResult(
            overall_score=overall_score,
            overall_confidence=overall_conf,
            evidence_coverage=evidence_cov,
            grade=grade,
            health_label=health,
            category_scores=cat_scores,
            intent_adjusted_weights={k.value: round(v, 3) for k, v in weights.items()},
            mathematical_derivation=math_derivation
        )

    def calculate_honest_scores(
        self,
        findings: List[Finding],
        business_profile: BusinessProfile,
        commercial_evals: Optional[List[Any]] = None,
        has_schema: bool = True,
        is_https: bool = True,
        readability: float = 65.0,
        geo_readiness: Optional[Any] = None,
        live_citation_score: Optional[float] = None,
    ):
        """
        Calculates the 3 Honest Scores (Human, Google, AI Citation) grounded strictly in verified findings and evidence IDs.
        No invented CAC or vanity metrics.
        """
        from app.domain.models import HonestScores

        human_deductions = 0.0
        human_issues: List[str] = []
        google_deductions = 0.0
        google_issues: List[str] = []
        ai_deductions = 0.0
        ai_issues: List[str] = []
        evidence_refs: List[str] = []
        human_counts = {s: 0 for s in Severity}
        google_counts = {s: 0 for s in Severity}
        ai_counts = {s: 0 for s in Severity}

        from app.domain.enums import SourceIntegrityLabel, ConfidenceBand, RubricConfidence, AiVisibilityStatus

        for f in findings:
            evidence_refs.extend(f.evidence_refs)
            # Gating: if finding is hypothesis / low-confidence, cap severity at MEDIUM
            effective_sev = f.severity
            conf_val = getattr(f, "confidence", 0.85)
            rubric = getattr(f, "confidence_rubric", None)
            is_unverified = (
                getattr(f, "source_integrity_label", None) == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
                or (rubric is not None and rubric.is_hypothesis)
                or getattr(f, "confidence_band", None) == ConfidenceBand.LOW
                or (isinstance(conf_val, (int, float)) and conf_val < 0.6)
            )
            if is_unverified and effective_sev in (Severity.CRITICAL, Severity.HIGH):
                effective_sev = Severity.MEDIUM

            if f.category in (Category.UX_CONVERSION, Category.CONTENT):
                human_deductions += _diminishing_deduction(effective_sev, human_counts[effective_sev])
                human_counts[effective_sev] += 1
                human_issues.append(f.title)
            elif f.category in (Category.TECHNICAL_SEO, Category.ON_PAGE_SEO, Category.SCHEMA):
                google_deductions += _diminishing_deduction(effective_sev, google_counts[effective_sev])
                google_counts[effective_sev] += 1
                google_issues.append(f.title)
            elif f.category in (Category.GEO, Category.AI_SEARCH, Category.COMPETITIVE, Category.TRUST_AUTHORITY):
                ai_deductions += _diminishing_deduction(effective_sev, ai_counts[effective_sev])
                ai_counts[effective_sev] += 1
                ai_issues.append(f.title)

        if findings:
            if readability < 50:
                human_deductions += 6.0
            if not is_https:
                google_deductions += 10.0
            if not has_schema:
                google_deductions += 6.0

        human_score = max(15.0, min(100.0, 100.0 - human_deductions))
        google_score = max(15.0, min(100.0, 100.0 - google_deductions))

        # Decouple AI Readiness (on-page extractability) from AI Visibility (live engine citations)
        ai_readiness_base = max(15.0, min(100.0, 100.0 - ai_deductions))
        if geo_readiness is not None and getattr(geo_readiness, "questions_total", 0) > 0:
            support_ratio = getattr(geo_readiness, "questions_supported", 0) / geo_readiness.questions_total
            ai_readiness_score = round(ai_readiness_base * 0.6 + (support_ratio * 100.0) * 0.4, 1)
        elif commercial_evals:
            valid_comm = [getattr(c, "before_score", None) for c in commercial_evals if getattr(c, "before_score", None) is not None]
            if valid_comm:
                avg_comm = sum(valid_comm) / len(valid_comm)
                ai_readiness_score = round(ai_readiness_base * 0.5 + (avg_comm * 10.0) * 0.5, 1)
            else:
                ai_readiness_score = round(ai_readiness_base, 1)
        else:
            ai_readiness_score = round(ai_readiness_base, 1)

        # Visibility stays null unless a live engine snapshot was actually measured.
        # ai_citation_score is that live number only. On-page readiness is ai_readiness_score.
        if live_citation_score is None:
            ai_visibility_score = None
            ai_visibility_status = "NOT_MEASURED"
            live_ai_citation_score = None
            ai_citation_alias = None
            ai_citation_status = "not_measured"
        else:
            ai_visibility_score = round(float(live_citation_score), 1)
            ai_visibility_status = "MEASURED"
            live_ai_citation_score = ai_visibility_score
            ai_citation_alias = ai_visibility_score
            ai_citation_status = "measured"

        overall = round((human_score * 0.35 + google_score * 0.35 + ai_readiness_score * 0.30), 1)

        if overall >= 90:
            band = "Category Benchmark"
        elif overall >= 75:
            band = "Citation Ready"
        elif overall >= 50:
            band = "Fragile Presence"
        else:
            band = "Low readiness"

        if human_issues:
            human_summary = (
                f"Human score {human_score:.0f}/100. {len(human_issues)} friction point(s) on clarity or conversion. "
                f"Primary: {human_issues[0]}."
            )
        else:
            human_summary = "Human score 100/100 in the crawl sample: no recorded 5-second or CTA defects."

        if google_issues:
            google_summary = (
                f"Google score {google_score:.0f}/100. {len(google_issues)} technical or on-page bottleneck(s). "
                f"Primary: {google_issues[0]}."
            )
        else:
            google_summary = "Google score 100/100 in the crawl sample: no recorded crawl, index, or schema defects."

        if ai_visibility_score is None:
            visibility_clause = "AI Visibility: NOT MEASURED (live answer-engine citations were not run for this seal)."
        else:
            visibility_clause = f"AI Visibility: {ai_visibility_score:.0f}/100 from a live engine measurement, separate from on-page readiness."
        if geo_readiness is not None:
            ai_summary = (
                f"AI Readiness: {ai_readiness_score:.0f}/100 ({geo_readiness.headline}). "
                f"{visibility_clause} {geo_readiness.visibility_message}"
            )
        else:
            ai_summary = (
                f"AI Readiness: {ai_readiness_score:.0f}/100 based on on-page entity extractability. "
                f"{visibility_clause}"
            )

        unique_ev = sorted(list(set(evidence_refs)))[:12]

        return HonestScores(
            human_score=round(human_score, 1),
            google_score=round(google_score, 1),
            ai_readiness_score=ai_readiness_score,
            ai_visibility_score=ai_visibility_score,
            ai_visibility_status=ai_visibility_status,
            ai_citation_score=ai_citation_alias,
            on_page_proxy_score=ai_readiness_score,
            live_ai_citation_score=live_ai_citation_score,
            overall_score=overall,
            score_band=band,
            human_summary=human_summary,
            google_summary=google_summary,
            ai_citation_summary=ai_summary,
            evidence_refs=unique_ev,
            status="AVAILABLE",
            ai_citation_status=ai_citation_status,
        )
