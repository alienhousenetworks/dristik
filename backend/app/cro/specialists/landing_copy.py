"""Department D — Landing Page Optimization & Responsible Conversion Copywriting (Phases 9–10).

Evaluates:
- Message match (strictly reported as UNMEASURED when campaign/ad/query context is unavailable)
- Headline, subheadline, value proposition (6-question buyer model), benefits, differentiation,
  objection handling by business model, CTA language, and trust copy
- Generates grounded replacement copy proposals (original -> problem -> proposed -> rationale ->
  supporting facts -> risks) without EVER inventing testimonials, awards, numbers, or guarantees
- Produces clearly labeled Proposed Wireframe recommendations requiring user approval
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.cro.analyzer import PASSIVE_GENERIC_PATTERNS, generate_agentic_cta_rewrite
from app.cro.business_models import MODEL_CONVERSION_BLUEPRINTS
from app.cro.models import (
    CROAgentOutput,
    CRODimensionCheck,
    CROFinding,
    CRORecommendation,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext
from app.cro.value_prop_analyzer import ValuePropAnalyzer
from app.domain.models import PageEvidence


VAGUE_HEADLINE_RE = re.compile(
    r"^(welcome(\s+to)?|home|innovating\s+the\s+future|reimagining|next[- ]gen\s+solutions?|empowering\s+excellence|synergy|digital\s+transformation)\b",
    re.I,
)


def run_department_d(ctx: CROAuditContext) -> CROAgentOutput:
    findings: List[CROFinding] = []
    evidence_ids: List[str] = []
    limitations: List[str] = []

    landing_pages = [p for p in ctx.pages if p.page_type.value in ("homepage", "landing_page")] or ctx.pages[:1]
    page_ev = [
        PageEvidence(
            url=p.url,
            status_code=p.http_status or 200,
            title=p.title or "",
            h1=[p.h1] if p.h1 else [],
            raw_html=ctx.raw_html_map.get(p.url, ""),
            word_count=p.word_count,
        )
        for p in landing_pages
    ]
    vp_res = ValuePropAnalyzer.analyze(page_ev, ctx.raw_html_map, ctx.profile)
    primary_page = landing_pages[0] if landing_pages else None
    if primary_page:
        evidence_ids.append(primary_page.page_id)

    # Message match evaluation (strictly UNMEASURED if no campaign/ad/search context)
    campaign = ctx.campaign_context or {}
    has_campaign = bool(campaign.get("ad_headline") or campaign.get("search_query") or campaign.get("referral_context"))
    if has_campaign and primary_page:
        src_terms = set(
            re.findall(
                r"[a-z0-9]{4,}",
                f"{campaign.get('ad_headline', '')} {campaign.get('search_query', '')} {campaign.get('referral_context', '')}".lower(),
            )
        )
        lp_terms = set(re.findall(r"[a-z0-9]{4,}", f"{primary_page.h1 or ''} {primary_page.subheadline or ''} {primary_page.title or ''}".lower()))
        overlap = len(src_terms.intersection(lp_terms)) / max(1, len(src_terms))
        message_match = {
            "status": "measured",
            "overlap_ratio": round(overlap, 2),
            "source_context": campaign,
            "landing_headline": primary_page.h1,
            "verdict": "aligned" if overlap >= 0.4 else "weak_message_match",
        }
        ctx.dimension_checks.append(
            CRODimensionCheck(
                check_id="dept_d_message_match",
                dimension_id="landing_page_match",
                label="Acquisition-to-landing-page message match",
                weight=1.5,
                result=round(min(1.0, overlap * 1.5), 2),
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                evidence_ids=evidence_ids,
            )
        )
    else:
        message_match = {
            "status": "unmeasured",
            "overlap_ratio": None,
            "reason": "No campaign, ad headline, search query, or referral context was provided. Message match is reported as unmeasured rather than assumed poor.",
        }
        limitations.append("Campaign/search acquisition context unavailable; landing-page message match is unmeasured.")
        ctx.dimension_checks.append(
            CRODimensionCheck(
                check_id="dept_d_message_match",
                dimension_id="landing_page_match",
                label="Acquisition-to-landing-page message match",
                weight=1.5,
                result=None,
                executed=False,
                source_type=EvidenceSourceType.ANALYTICS_OBSERVATION,
                note="Excluded without penalty until campaign/query context is connected.",
            )
        )

    # Evaluate headline & value proposition clarity
    h1_text = vp_res.hero_headline or (primary_page.h1 if primary_page else "") or ""
    subhead_text = vp_res.hero_subhead or (primary_page.subheadline if primary_page else "") or ""
    is_vague_h1 = bool(not h1_text or len(h1_text.split()) < 3 or VAGUE_HEADLINE_RE.search(h1_text))
    unanswered_qs = [q for q in vp_res.buyer_questions if not q.answered]

    # Objection coverage against business model blueprint
    blueprint = MODEL_CONVERSION_BLUEPRINTS[ctx.profile.business_type]
    full_text = " ".join((ctx.raw_html_map.get(p.url, "") for p in ctx.pages)).lower()
    unanswered_objections: List[str] = []
    objection_probes = {
        "pricing": r"(\$|€|£|₹|pricing|plans|fee|cost|tuition)",
        "cancel": r"(cancel|refund|return|guarantee|money-back)",
        "security": r"(soc\s?2|iso\s?27001|gdpr|ssl|encrypted|hipaa|privacy)",
        "shipping": r"(shipping|delivery|dispatch)",
        "how_it_works": r"(how\s+it\s+works|step\s+1|onboarding|implementation|timeline)",
        "support": r"(support|faq|help|contact)",
    }
    for obj in blueprint["objections"]:
        obj_l = obj.lower()
        matched = False
        for key, pat in objection_probes.items():
            if any(tok in obj_l for tok in key.split("_")) and re.search(pat, full_text, re.I):
                matched = True
                break
        if not matched:
            unanswered_objections.append(obj)

    # Check weak/passive CTA copy across landing pages
    passive_ctas = [
        e for e in ctx.elements
        if e.element_category == "cta"
        and e.text
        and any(re.search(pat, e.text.strip().lower()) for pat in PASSIVE_GENERIC_PATTERNS)
    ]

    lp_score_norm = max(0.2, min(1.0, (vp_res.overall_value_prop_score or 65.0) / 100.0))
    copy_score_norm = max(
        0.2,
        1.0
        - (0.30 if is_vague_h1 else 0.0)
        - (0.08 * len(unanswered_qs))
        - (0.15 if passive_ctas else 0.0),
    )

    ctx.dimension_checks.extend(
        [
            CRODimensionCheck(
                check_id="dept_d_landing_structure",
                dimension_id="landing_page_match",
                label="Landing page 6-question comprehension & page structure",
                weight=2.0,
                result=round(lp_score_norm, 2),
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                evidence_ids=evidence_ids,
            ),
            CRODimensionCheck(
                check_id="dept_d_copy_clarity",
                dimension_id="copywriting_value_prop",
                label="Headline specificity, benefit clarity, CTA language & objection handling",
                weight=2.5,
                result=round(copy_score_norm, 2),
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                evidence_ids=evidence_ids,
            ),
        ]
    )

    # Responsible copywriting proposal (grounded strictly in observed facts — zero invented proof/numbers)
    offering_fact = (
        ", ".join(ctx.profile.products_and_services[:2])
        if ctx.profile.products_and_services
        else (ctx.profile.business_name or ctx.domain)
    )
    audience_fact = ctx.profile.target_customers if ctx.profile.target_customers not in (None, "", "unknown") else "your target customers"
    action_fact = ctx.profile.primary_conversion if ctx.profile.primary_conversion != "unknown" else "Get started"

    proposed_headlines = [
        f"{offering_fact}: Clear Outcome for {audience_fact}" if audience_fact != "your target customers" else f"{offering_fact} — Built to Deliver Your Core Outcome",
        f"Simplify {offering_fact} Without Unnecessary Friction",
    ]
    proposed_subhead = (
        f"Explain clearly what {offering_fact} delivers, who it serves, and what happens immediately after visitors click '{action_fact}'."
    )
    proposed_cta = (
        generate_agentic_cta_rewrite(passive_ctas[0].text, ctx.profile)
        if passive_ctas
        else (action_fact if len(action_fact) <= 32 else "Start Your Request")
    )

    copy_proposals: List[Dict[str, Any]] = [
        {
            "proposal_id": f"copy_hero_{ctx.audit_id[-6:]}",
            "page_url": primary_page.url if primary_page else ctx.target_url,
            "section": "hero_headline",
            "original_copy": h1_text or "(Missing H1 headline)",
            "identified_problem": (
                "Hero headline is vague or fails to communicate product category, target audience, and concrete outcome."
                if (is_vague_h1 or len(unanswered_qs) >= 2)
                else "Headline can be tested for sharper specificity and customer-outcome framing."
            ),
            "recommended_copy": proposed_headlines[0],
            "alternatives": proposed_headlines,
            "reason_for_change": "Clarifies what is offered and for whom within the initial viewport without relying on unverified claims.",
            "supporting_source_facts": [
                f"Observed H1: '{h1_text or 'None'}'",
                f"Business model: {ctx.profile.business_type.value}",
                f"Unanswered buyer questions: {len(unanswered_qs)} of 6",
            ],
            "target_audience": audience_fact,
            "intended_conversion_objective": ctx.profile.primary_conversion,
            "risks_and_assumptions": [
                "Heuristic copy proposal — requires brand review, user approval, and controlled A/B testing before assuming uplift.",
                "Contains zero invented customer counts, awards, testimonials, or performance guarantees.",
            ],
            "requires_user_approval": True,
            "approval_status": "pending",
        },
        {
            "proposal_id": f"copy_subhead_{ctx.audit_id[-6:]}",
            "page_url": primary_page.url if primary_page else ctx.target_url,
            "section": "hero_subheadline",
            "original_copy": subhead_text or "(Missing hero subheadline)",
            "identified_problem": "Subheadline lacks clear explanation of how the offer works and next-step expectation." if not subhead_text else "Opportunity to address key pre-conversion objections directly beneath H1.",
            "recommended_copy": proposed_subhead,
            "alternatives": [proposed_subhead],
            "reason_for_change": "Supports headline comprehension and reduces pre-click uncertainty.",
            "supporting_source_facts": [f"Observed subhead: '{subhead_text or 'None'}'"],
            "target_audience": audience_fact,
            "intended_conversion_objective": ctx.profile.primary_conversion,
            "risks_and_assumptions": ["User approval required prior to production copy update."],
            "requires_user_approval": True,
            "approval_status": "pending",
        },
        {
            "proposal_id": f"copy_cta_{ctx.audit_id[-6:]}",
            "page_url": passive_ctas[0].url if passive_ctas else (primary_page.url if primary_page else ctx.target_url),
            "section": "primary_cta",
            "original_copy": passive_ctas[0].text if passive_ctas else (primary_page.primary_cta if primary_page and primary_page.primary_cta else "(No primary CTA)"),
            "identified_problem": "Generic passive CTA text ('Submit'/'Learn more'/'Click here') does not state the specific outcome of clicking." if passive_ctas else "Align CTA copy directly to the primary conversion objective.",
            "recommended_copy": proposed_cta,
            "alternatives": [proposed_cta, action_fact],
            "reason_for_change": "Descriptive action language reduces hesitation by clarifying the exact next step.",
            "supporting_source_facts": [f"Passive CTAs observed: {len(passive_ctas)}"],
            "target_audience": audience_fact,
            "intended_conversion_objective": ctx.profile.primary_conversion,
            "risks_and_assumptions": ["Ensure CTA language matches the actual landing destination and offer."],
            "requires_user_approval": True,
            "approval_status": "pending",
        },
    ]

    if is_vague_h1 or len(unanswered_qs) >= 3:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-LP-VP-{ctx.audit_id[-6:]}-01",
                category="landing_page_optimization",
                subcategory="value_proposition_clarity",
                department="D",
                agent_id="cro_value_proposition",
                title=f"Unclear Value Proposition & Headline ({len(unanswered_qs)} of 6 Buyer Questions Unanswered)",
                description=(
                    f"Hero headline ('{h1_text or 'missing'}') leaves {len(unanswered_qs)} core buyer question(s) unanswered: "
                    f"{', '.join(q.question for q in unanswered_qs[:4])}. This is an expert heuristic assessment requiring validation."
                ),
                root_cause="Above-the-fold messaging uses abstract or incomplete copy instead of concrete category, audience, and outcome framing.",
                affected_urls=[p.url for p in landing_pages[:5]],
                evidence_ids=evidence_ids,
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.HIGH if (is_vague_h1 or len(unanswered_qs) >= 4) else CROSeverity.MEDIUM,
                confidence=0.8,
                recommendation="Rewrite the hero headline and subheadline to state what is offered, who it serves, the primary problem solved, and the immediate next step.",
                implementation_instructions="Review and approve the grounded copy alternatives in the Landing Page & Copywriting Workspace, then test via A/B experiment.",
                owner_role="Marketing / Copywriting",
                effort="low",
                priority_score=80.0,
                acceptance_criteria=[
                    "Hero H1 and subheadline clearly communicate offering, audience, and outcome.",
                    "Approved copy passes brand review with zero fabricated claims.",
                    "Paired with one visually distinct primary CTA.",
                ],
            )
        )

    if passive_ctas:
        samples = list(dict.fromkeys(f"'{c.text}' ({c.url})" for c in passive_ctas[:5]))
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-COPY-CTA-{ctx.audit_id[-6:]}-01",
                category="copywriting_optimization",
                subcategory="passive_cta_copy",
                department="D",
                agent_id="cro_cta_copy",
                title=f"Weak / Passive CTA Language Detected ({len(passive_ctas)} Element(s))",
                description=(
                    f"Found {len(passive_ctas)} generic passive CTA label(s): {', '.join(samples)}. "
                    "Generic copy fails to set clear expectations for what happens after clicking (heuristic assessment)."
                ),
                root_cause="Buttons reuse generic default labels ('Submit', 'Learn more', 'Click here') instead of outcome-specific microcopy.",
                affected_urls=list(dict.fromkeys(c.url for c in passive_ctas))[:10],
                affected_elements=[c.element_id for c in passive_ctas[:10]],
                evidence_ids=[c.element_id for c in passive_ctas[:5]],
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.MEDIUM,
                confidence=0.85,
                recommendation=f"Replace passive button labels with action-specific copy matching the destination offer (e.g., '{proposed_cta}').",
                implementation_instructions="Approve updated CTA microcopy per page and update button text while preserving accessible names and tracking attributes.",
                owner_role="Marketing / Frontend",
                effort="low",
                priority_score=74.0,
                acceptance_criteria=[
                    "Zero primary conversion buttons use generic 'Submit', 'Click here', or 'Learn more' copy.",
                    "CTA wording accurately reflects the destination action.",
                ],
            )
        )

    if len(unanswered_objections) >= 2:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-COPY-OBJ-{ctx.audit_id[-6:]}-01",
                category="copywriting_optimization",
                subcategory="objection_handling",
                department="D",
                agent_id="cro_objection_handling",
                title=f"Key Buyer Objections Unaddressed ({len(unanswered_objections)} Topic(s))",
                description=f"Audited pages lacked clear coverage of core {ctx.profile.business_type.value} buyer objections: {', '.join(unanswered_objections)}.",
                root_cause="Missing objection-handling sections (FAQ, transparent terms, implementation/delivery details) near conversion points.",
                affected_urls=[p.url for p in landing_pages[:5]],
                evidence_ids=evidence_ids,
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.MEDIUM,
                confidence=0.75,
                recommendation="Add factual, concise objection-handling copy and FAQs addressing pricing, process, policies, and support adjacent to primary CTAs.",
                implementation_instructions="Publish factual FAQ and policy blocks validated by product/legal teams.",
                owner_role="Marketing / Product",
                effort="medium",
                priority_score=65.0,
                acceptance_criteria=["Each primary model objection is answered clearly on the landing or pricing/product page."],
            )
        )

    proposed_wireframe = {
        "is_recommendation_only": True,
        "disclosure": "Proposed wireframe is a structural recommendation for review and testing, not a live implementation.",
        "recommended_section_order": [
            {"order": 1, "section": "Focused Header", "purpose": "Brand identity + <=7 links + 1 primary CTA"},
            {"order": 2, "section": "Above-the-Fold Hero", "purpose": "Specific H1 outcome + explanatory subhead + single primary CTA + factual reassurance"},
            {"order": 3, "section": "Verifiable Proof Strip", "purpose": "Attributable client logos, reviews, or factual credentials (only verified assets)"},
            {"order": 4, "section": "Problem-to-Benefit Breakdown", "purpose": "Scannable outcomes mapped to visitor intent"},
            {"order": 5, "section": "How It Works / Offer & Pricing Clarity", "purpose": "Step-by-step process and transparent pricing/terms"},
            {"order": 6, "section": "Objection Handling & FAQ", "purpose": f"Directly answer: {', '.join(blueprint['objections'][:4])}"},
            {"order": 7, "section": "Focused Conversion Block & Trust Footer", "purpose": "Clear form or checkout CTA with privacy/refund/terms links"},
        ],
    }

    ctx.artifacts["landing_copy_workspace"] = {
        "scorecard": {
            "overall_value_prop_score": vp_res.overall_value_prop_score,
            "buyer_questions": [q.model_dump() for q in vp_res.buyer_questions],
            "dimensions": [d.model_dump() for d in vp_res.dimensions],
        },
        "message_match": message_match,
        "unanswered_objections": unanswered_objections,
        "copy_proposals": copy_proposals,
        "proposed_wireframe": proposed_wireframe,
        "roles_executed": [
            "cro_landing_page",
            "cro_message_match",
            "cro_headline",
            "cro_value_proposition",
            "cro_benefit_clarity",
            "cro_objection_handling",
            "cro_copywriting",
            "cro_cta_copy",
            "cro_trust_copy",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_d_landing_copy",
        department="D",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=evidence_ids,
        confidence=0.8,
        limitations=limitations,
        artifacts=ctx.artifacts["landing_copy_workspace"],
    )
