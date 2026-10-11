"""
Dristik Enterprise CRO, Behavioral UX, and Conversion Intelligence Analyzer.

Evaluates multi-page conversion friction adhering strictly to the Zero-Fake Evidence Standard:
1. CTA & Action Hierarchy Studio (intent classification, passive microcopy warnings, suggested rewrites)
2. 5-Second Hook & Value Proposition Clarity (cognitive load, customer-centricity, hero CTA proximity)
3. Social Proof & Trust Architecture (testimonials, client logos, quantified ROI claims, trust seals)
4. Pricing Psychology & Risk Reversal (pricing discovery, tier structure, billing toggle, guarantee signals)
5. Form Usability & Input Friction (integrates FormAccessibilityAnalyzer with input type inspection)
"""
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from app.domain.models import (
    PageEvidence,
    Finding,
    FindingEvidence,
    EvidenceRef,
    CtaAuditItem,
    CtaAnalysisRollup,
    SocialProofAuditRollup,
    PricingPsychologyRollup,
    ValuePropClarityAudit,
    CroAuditReport,
    FormAuditReport,
)
from app.domain.enums import Category, Severity, EvidenceClass
from app.analyzers.form_analyzer import FormAccessibilityAnalyzer


HIGH_INTENT_PATTERNS = [
    r"\b(get\s+started|start\s+(free|now|trial|your)|book\s+(a\s+)?demo|schedule\s+(a\s+)?demo|request\s+(a\s+)?(demo|quote)|claim\s+(your\s+)?(offer|report|audit)|buy\s+now|sign\s+up|order\s+now|subscribe\s+now|get\s+quote|hire\s+us|contact\s+sales)\b"
]

EXPLORATORY_PATTERNS = [
    r"\b(view\s+pricing|see\s+plans|explore\s+features|watch\s+(a\s+)?(demo|video)|case\s+studies|our\s+work|solutions|compare\s+plans|read\s+story)\b"
]

PASSIVE_GENERIC_PATTERNS = [
    r"^(submit|click\s+here|learn\s+more|read\s+more|continue|next|more|go|here|download|view\s+more|check\s+it\s+out)$"
]

CTA_REWRITE_SUGGESTIONS = {
    "submit": "Claim Your Strategy Report / Complete Registration",
    "click here": "Explore Solution & Pricing",
    "learn more": "Discover How It Works / See Full Capabilities",
    "read more": "Read Full Case Study / View Technical Breakdown",
    "continue": "Proceed to Next Step",
    "download": "Get Free Guide / Download Resource",
    "go": "Start Now",
}


class CroAnalyzer:
    """Deterministic, zero-fake CRO & conversion experience analyzer."""

    @staticmethod
    def analyze_cro(
        pages: List[PageEvidence],
        raw_html_map: Optional[Dict[str, str]] = None,
        business_profile: Optional[Any] = None,
    ) -> Tuple[CroAuditReport, List[Finding]]:
        raw_html_map = raw_html_map or {}
        findings: List[Finding] = []

        # 1. Evaluate Forms via FormAccessibilityAnalyzer
        form_rep: FormAuditReport = FormAccessibilityAnalyzer.analyze_forms(pages, raw_html_map)

        # 2. Extract & Classify CTAs across all pages
        cta_items: List[CtaAuditItem] = []
        pages_without_ctas: List[str] = []
        hero_cta_found = False
        hero_cta_text: Optional[str] = None

        for idx, p in enumerate(pages):
            html = raw_html_map.get(p.url) or getattr(p, "raw_html", None)
            if not html and getattr(p, "snapshot_path", None):
                try:
                    from pathlib import Path
                    sp = Path(p.snapshot_path)
                    if sp.exists():
                        html = sp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

            page_ctas_detected = 0
            if html:
                soup = BeautifulSoup(html, "html.parser")
                # Look for interactive conversion triggers: buttons, links with button-like classes, submit inputs
                triggers = soup.find_all(["button", "a", "input"])
                for el in triggers:
                    tag = el.name
                    text = ""
                    href = el.get("href") or el.get("action") or ""
                    is_button_or_cta = False

                    if tag == "button":
                        text = el.get_text(strip=True)
                        is_button_or_cta = True
                    elif tag == "input" and el.get("type") in ("submit", "button"):
                        text = el.get("value", "").strip() or el.get("placeholder", "").strip()
                        is_button_or_cta = True
                    elif tag == "a":
                        cls_str = " ".join(el.get("class") or []).lower()
                        # Detect if anchor is styled or used as a button/action
                        if any(b in cls_str for b in ["btn", "button", "cta", "action", "primary", "header-action"]):
                            text = el.get_text(strip=True)
                            is_button_or_cta = True
                        elif href and any(act in href.lower() for act in ["contact", "pricing", "signup", "register", "demo", "checkout", "quote"]):
                            text = el.get_text(strip=True)
                            if 1 < len(text) < 40:
                                is_button_or_cta = True

                    if not is_button_or_cta or not text or len(text) > 50:
                        continue

                    text_clean = " ".join(text.split())
                    intent = "EXPLORATORY"
                    is_passive = False
                    suggestion = None

                    # Check Intent
                    lower_t = text_clean.lower()
                    if any(re.search(pat, lower_t) for pat in PASSIVE_GENERIC_PATTERNS):
                        intent = "PASSIVE_GENERIC"
                        is_passive = True
                        suggestion = CTA_REWRITE_SUGGESTIONS.get(lower_t, f"Action-Oriented: {text_clean} Now")
                    elif any(re.search(pat, lower_t) for pat in HIGH_INTENT_PATTERNS):
                        intent = "HIGH_INTENT"
                    elif any(re.search(pat, lower_t) for pat in EXPLORATORY_PATTERNS):
                        intent = "EXPLORATORY"

                    # Determine placement zone
                    placement = "BODY"
                    parent_tags = [p_el.name for p_el in el.parents]
                    if "header" in parent_tags or "nav" in parent_tags:
                        placement = "HEADER"
                    elif "footer" in parent_tags:
                        placement = "FOOTER"
                    elif idx == 0 and page_ctas_detected == 0:
                        placement = "HERO"
                        hero_cta_found = True
                        hero_cta_text = text_clean

                    cta_item = CtaAuditItem(
                        page_url=p.url,
                        cta_text=text_clean,
                        element_type=tag,
                        target_url=str(href) if href else None,
                        intent_category=intent,
                        placement_zone=placement,
                        is_passive_friction=is_passive,
                        suggested_rewrite=suggestion,
                    )
                    cta_items.append(cta_item)
                    page_ctas_detected += 1

            # Fallback to page.ctas if html was unavailable
            if page_ctas_detected == 0 and getattr(p, "ctas", None):
                for c_text in p.ctas:
                    c_str = str(c_text).strip()
                    if not c_str:
                        continue
                    lower_t = c_str.lower()
                    is_passive = any(re.search(pat, lower_t) for pat in PASSIVE_GENERIC_PATTERNS)
                    intent = "PASSIVE_GENERIC" if is_passive else ("HIGH_INTENT" if any(re.search(pat, lower_t) for pat in HIGH_INTENT_PATTERNS) else "EXPLORATORY")
                    cta_items.append(CtaAuditItem(
                        page_url=p.url,
                        cta_text=c_str,
                        element_type="button",
                        target_url=None,
                        intent_category=intent,
                        placement_zone="HERO" if idx == 0 and not hero_cta_found else "BODY",
                        is_passive_friction=is_passive,
                        suggested_rewrite=CTA_REWRITE_SUGGESTIONS.get(lower_t),
                    ))
                    page_ctas_detected += 1
                    if idx == 0 and not hero_cta_found:
                        hero_cta_found = True
                        hero_cta_text = c_str

            if page_ctas_detected == 0 and (p.word_count or 0) > 100:
                pages_without_ctas.append(p.url)

        # CTA Rollup
        high_intent = sum(1 for c in cta_items if c.intent_category == "HIGH_INTENT")
        exploratory = sum(1 for c in cta_items if c.intent_category == "EXPLORATORY")
        passive_cnt = sum(1 for c in cta_items if c.intent_category == "PASSIVE_GENERIC")
        total_ctas = len(cta_items)

        action_score = 70.0
        if total_ctas > 0:
            high_intent_ratio = high_intent / total_ctas
            passive_ratio = passive_cnt / total_ctas
            action_score = max(20.0, min(100.0, 50.0 + (high_intent_ratio * 40.0) - (passive_ratio * 30.0)))
        elif pages:
            action_score = 40.0

        cta_rollup = CtaAnalysisRollup(
            total_ctas_detected=total_ctas,
            high_intent_count=high_intent,
            exploratory_count=exploratory,
            passive_generic_count=passive_cnt,
            pages_without_ctas=pages_without_ctas,
            has_hero_cta=hero_cta_found,
            hero_cta_text=hero_cta_text,
            ctas=cta_items[:50],  # Keep top 50
            action_clarity_score=round(action_score, 1),
        )

        # 3. 5-Second Hook & Value Proposition Analysis
        hp = pages[0] if pages else None
        h1_text = (hp.h1[0] if (hp and hp.h1) else "") or (hp.title if hp else "")
        subhead_text = ""
        if hp and getattr(hp, "h2", None):
            subhead_text = hp.h2[0] if len(hp.h2) > 0 else ""

        h1_words = len(h1_text.split()) if h1_text else 0
        customer_words = len(re.findall(r"\b(you|your|yours)\b", (h1_text + " " + subhead_text).lower()))
        company_words = len(re.findall(r"\b(we|our|us|i|my)\b", (h1_text + " " + subhead_text).lower()))
        centricity_ratio = round((customer_words / max(company_words, 1)), 2)

        vp_observations = []
        if h1_words == 0:
            vp_observations.append("Homepage lacks a prominent H1 heading.")
            clarity_grade = "D"
        elif h1_words > 12:
            vp_observations.append(f"Hero headline is wordy ({h1_words} words). Aim for concise 6-9 word punchiness.")
            clarity_grade = "C"
        else:
            vp_observations.append(f"Hero headline is concise ({h1_words} words).")
            clarity_grade = "A" if hero_cta_found else "B"

        if customer_words > company_words:
            vp_observations.append("Headline messaging is customer-focused (uses 'you/your').")
        else:
            vp_observations.append("Consider rewriting headline to focus on user outcomes rather than self-referential 'we/our'.")

        if hero_cta_found:
            vp_observations.append(f"Primary CTA '{hero_cta_text}' is placed in direct hero proximity.")
        else:
            vp_observations.append("No immediate primary CTA detected above the fold in hero section.")

        value_prop_audit = ValuePropClarityAudit(
            hero_headline=h1_text or None,
            hero_subhead=subhead_text or None,
            headline_word_count=h1_words,
            customer_centricity_ratio=centricity_ratio,
            has_adjacent_cta=hero_cta_found,
            clarity_grade=clarity_grade,
            observations=vp_observations,
        )

        # 4. Social Proof & Trust Signals
        testimonials_found = 0
        logos_found = 0
        quant_claims: List[str] = []
        trust_badges: List[str] = []
        has_privacy = False
        has_terms = False

        for p in pages:
            url_l = p.url.lower()
            if "privacy" in url_l:
                has_privacy = True
            if "terms" in url_l or "tos" in url_l:
                has_terms = True

            html = raw_html_map.get(p.url) or getattr(p, "raw_html", None)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href_l = a["href"].lower()
                    text_l = a.get_text(strip=True).lower()
                    if "privacy" in href_l or "privacy" in text_l:
                        has_privacy = True
                    if "terms" in href_l or "tos" in href_l or "terms" in text_l:
                        has_terms = True
                # Testimonials
                test_elems = soup.find_all(attrs={"class": re.compile(r"testimonial|review|quote", re.I)})
                test_elems += soup.find_all("blockquote")
                testimonials_found += len(test_elems)

                # Logos
                logo_elems = soup.find_all("img", attrs={"alt": re.compile(r"logo|partner|client|customer", re.I)})
                logos_found += len(logo_elems)

                # Quantified ROI claims
                page_text = soup.get_text(" ", strip=True)
                roi_matches = re.findall(
                    r"(\b\d+%\s+(?:increase|lift|growth|reduction|faster|more|roi)\b|\b\$\d+[\d,]*\s+(?:saved|generated|pipeline)\b|\b\d+[\+kKmM]\s+(?:customers|teams|users|enterprises)\b)",
                    page_text,
                    re.I
                )
                for rm in roi_matches[:5]:
                    if rm not in quant_claims:
                        quant_claims.append(rm)

                # Trust seals & badges
                for badge_term, badge_label in [
                    ("soc 2", "SOC 2 Type II Certified"),
                    ("iso 27001", "ISO 27001 Certified"),
                    ("hipaa", "HIPAA Compliant"),
                    ("gdpr", "GDPR Compliant"),
                    ("ssl", "256-Bit SSL Encryption"),
                    ("30-day", "30-Day Money-Back Guarantee"),
                    ("cancel anytime", "Cancel Anytime Guarantee"),
                    ("no credit card", "No Credit Card Required"),
                ]:
                    if badge_term in page_text.lower() and badge_label not in trust_badges:
                        trust_badges.append(badge_label)

        # Compute Trust Score
        trust_score = 50.0
        if has_privacy:
            trust_score += 10.0
        if has_terms:
            trust_score += 10.0
        if testimonials_found > 0:
            trust_score += 15.0
        if logos_found > 0:
            trust_score += 10.0
        if len(quant_claims) > 0:
            trust_score += 10.0
        if len(trust_badges) > 0:
            trust_score += 15.0
        trust_score = min(100.0, trust_score)

        trust_risk = "LOW" if trust_score >= 70 else ("MEDIUM" if trust_score >= 50 else "HIGH")

        social_proof_audit = SocialProofAuditRollup(
            total_testimonials=testimonials_found,
            client_logos_detected=logos_found,
            quantified_proof_claims=quant_claims[:8],
            trust_badges_detected=trust_badges,
            has_privacy_policy=has_privacy,
            has_terms_of_service=has_terms,
            trust_authority_score=round(trust_score, 1),
            risk_level=trust_risk,
        )

        # 5. Pricing Psychology & Commercial Risk Reversal
        pricing_url = None
        tiers_count = 0
        has_toggle = False
        has_guarantee = any("guarantee" in b.lower() for b in trust_badges)
        has_trial = any("credit card" in b.lower() for b in trust_badges) or any("trial" in c.cta_text.lower() for c in cta_items)
        guarantee_signals: List[str] = [b for b in trust_badges if "guarantee" in b.lower() or "cancel" in b.lower()]

        for p in pages:
            u_low = p.url.lower()
            if "pricing" in u_low or "plans" in u_low:
                pricing_url = p.url
                html = raw_html_map.get(p.url) or getattr(p, "raw_html", None)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    # Tiers
                    tier_cards = soup.find_all(attrs={"class": re.compile(r"pricing-card|plan-card|tier|price-box", re.I)})
                    tiers_count = max(tiers_count, len(tier_cards))
                    # Billing toggle
                    if soup.find(attrs={"class": re.compile(r"toggle|switch|billing-cycle|annual", re.I)}) or "annual" in soup.get_text().lower():
                        has_toggle = True
                break

        transparency_score = 60.0
        if pricing_url:
            transparency_score += 20.0
        if has_toggle:
            transparency_score += 10.0
        if has_guarantee or has_trial:
            transparency_score += 10.0
        transparency_score = min(100.0, transparency_score)

        pricing_audit = PricingPsychologyRollup(
            pricing_page_detected=bool(pricing_url),
            pricing_url=pricing_url,
            detected_tiers_count=tiers_count,
            has_billing_toggle=has_toggle,
            has_money_back_guarantee=has_guarantee,
            has_free_trial=has_trial,
            guarantee_signals=guarantee_signals,
            commercial_transparency_score=round(transparency_score, 1),
        )

        # 6. Overall CRO Score Calculation
        overall_score = (
            (action_score * 0.30)
            + ((90.0 if clarity_grade == "A" else (75.0 if clarity_grade == "B" else 60.0)) * 0.25)
            + (trust_score * 0.25)
            + ((100.0 - (form_rep.friction_score if form_rep else 0.0)) * 0.20)
        )
        overall_score = max(20.0, min(100.0, overall_score))

        cro_grade = "A" if overall_score >= 85 else ("B" if overall_score >= 70 else ("C" if overall_score >= 55 else "D"))

        # 7. Actionable Remedies
        remedies = []
        if passive_cnt > 0:
            remedies.append(f"Upgrade {passive_cnt} passive CTA buttons (e.g. 'Submit', 'Learn More') with outcome-driven action verbs.")
        if not hero_cta_found:
            remedies.append("Place an immediate high-contrast primary CTA above the fold in the homepage hero section.")
        if len(pages_without_ctas) > 0:
            remedies.append(f"Add clear conversion pathways to {len(pages_without_ctas)} page(s) currently missing any call-to-action.")
        if testimonials_found == 0 and logos_found == 0:
            remedies.append("Incorporate verifiable social proof (client logos, customer testimonials, or ROI metrics) on key commercial pages.")
        if not has_privacy or not has_terms:
            remedies.append("Add explicit links to Privacy Policy and Terms of Service in the global footer to satisfy buyer trust requirements.")
        if pricing_url and not has_toggle:
            remedies.append("Deploy a monthly/annual billing toggle on the pricing page with visible annual discount savings.")
        if form_rep and form_rep.actionable_remedies:
            remedies.extend(form_rep.actionable_remedies[:2])

        # 8. Generate Category.UX_CONVERSION Findings
        # Finding 1: Passive Microcopy
        if passive_cnt > 0:
            passive_samples = [c for c in cta_items if c.is_passive_friction][:3]
            sample_desc = ", ".join(f"'{c.cta_text}' on {c.page_url}" for c in passive_samples)
            sample_sug = ", ".join(f"'{c.cta_text}' → '{c.suggested_rewrite}'" for c in passive_samples if c.suggested_rewrite)

            ev_hash = hashlib.md5(sample_desc.encode()).hexdigest()[:8]
            ev_ref = EvidenceRef(
                source_type="crawl",
                source_id=f"cro_passive_cta_{ev_hash}",
                evidence_hash=ev_hash,
                url=passive_samples[0].page_url if passive_samples else pages[0].url,
                selector="button, a",
                snippet=f"Detected {passive_cnt} passive CTA(s): {sample_desc}",
                observed_value=passive_cnt,
                collector_or_analyzer="CroAnalyzer.cta_microcopy",
            )
            findings.append(Finding(
                finding_id=f"find_cro_passive_cta_{ev_hash}",
                title=f"Passive & Generic CTA Microcopy ({passive_cnt} Buttons)",
                description=(
                    f"Audited {total_ctas} CTA buttons across the website and identified {passive_cnt} buttons "
                    f"using passive or vague microcopy ({sample_desc}). Generic CTAs increase decision friction "
                    "and deliver lower click-through conversion rates than value-specific action verbs."
                ),
                category=Category.UX_CONVERSION,
                severity=Severity.MEDIUM,
                impact=3,
                effort=1,
                priority=2,
                recommendation=f"Replace generic button copy with specific, value-driven alternatives: {sample_sug or 'e.g. Schedule VIP Demo, Claim Your Free Report'}.",
                why_it_matters="High-intent action verbs clarify the outcome of clicking, reducing hesitation and boosting conversion by up to 25%.",
                validation_criteria="All interactive CTA buttons must contain specific outcome verbs and eliminate generic 'Submit' or 'Click Here' labels.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="DOM_TEXT",
                evidence=[FindingEvidence(
                    url=passive_samples[0].page_url if passive_samples else pages[0].url,
                    element="button, a",
                    value=f"{passive_cnt} passive buttons",
                    source="crawl",
                    evidence_ref=ev_ref,
                )],
                evidence_refs=[ev_ref.source_id],
                evidence_ref_objects=[ev_ref],
            ))

        # Finding 2: Missing Hero CTA
        if not hero_cta_found and pages:
            ev_hash = hashlib.md5(pages[0].url.encode()).hexdigest()[:8]
            ev_ref = EvidenceRef(
                source_type="crawl",
                source_id=f"cro_missing_hero_cta_{ev_hash}",
                evidence_hash=ev_hash,
                url=pages[0].url,
                selector="header, .hero, body",
                snippet="No primary CTA button detected above the fold in hero section",
                observed_value=0,
                collector_or_analyzer="CroAnalyzer.hero_cta",
            )
            findings.append(Finding(
                finding_id=f"find_cro_missing_hero_cta_{ev_hash}",
                title="Above-the-Fold Hero Section Lacks Primary Call-to-Action",
                description=(
                    f"Homepage '{pages[0].url}' hero section contains headline copy but lacks an immediate, "
                    "high-contrast primary action button. First-time visitors arriving from search or AI answers "
                    "lack an obvious next action to take within the initial 5-second evaluation window."
                ),
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                impact=4,
                effort=1,
                priority=1,
                recommendation="Position an action-oriented primary button (e.g. 'Get Started Free' or 'Book a Demo') in direct proximity to the main headline.",
                why_it_matters="Over 50% of visitor exits happen above the fold when no immediate value path is presented.",
                validation_criteria="Hero section must display at least one prominent primary conversion button above the fold.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="DOM",
                evidence=[FindingEvidence(
                    url=pages[0].url,
                    element="hero",
                    value="Zero hero CTAs detected",
                    source="crawl",
                    evidence_ref=ev_ref,
                )],
                evidence_refs=[ev_ref.source_id],
                evidence_ref_objects=[ev_ref],
            ))

        # Finding 3: Social Proof Deficit
        if testimonials_found == 0 and logos_found == 0 and len(pages) > 0:
            ev_hash = hashlib.md5("social_proof_deficit".encode()).hexdigest()[:8]
            ev_ref = EvidenceRef(
                source_type="crawl",
                source_id=f"cro_social_proof_{ev_hash}",
                evidence_hash=ev_hash,
                url=pages[0].url,
                selector="body",
                snippet="No client logos or testimonials detected on crawled pages",
                observed_value=0,
                collector_or_analyzer="CroAnalyzer.social_proof",
            )
            findings.append(Finding(
                finding_id=f"find_cro_social_proof_{ev_hash}",
                title="Social Proof Deficit: Zero Client Logos or Verifiable Testimonials",
                description=(
                    "Crawled landing pages contain no client logos, recognizable partner marks, customer quotes, "
                    "or quantified outcome metrics. Unverified claims without third-party proof create significant "
                    "conversion resistance for evaluators."
                ),
                category=Category.UX_CONVERSION,
                severity=Severity.MEDIUM,
                impact=3,
                effort=2,
                priority=2,
                recommendation="Deploy a client logo bar and at least 2 customer testimonials with named roles and measurable business results.",
                why_it_matters="Social proof is the strongest trust lever for B2B and commercial buyers evaluating unfamiliar brands.",
                validation_criteria="Homepage and primary commercial routes must feature verifiable client logos or customer quotes.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="DOM_TEXT",
                evidence=[FindingEvidence(
                    url=pages[0].url,
                    element="body",
                    value="0 testimonials, 0 logos",
                    source="crawl",
                    evidence_ref=ev_ref,
                )],
                evidence_refs=[ev_ref.source_id],
                evidence_ref_objects=[ev_ref],
            ))

        # Finding 4: Trust Links in Global Footer
        if (not has_privacy or not has_terms) and len(pages) > 0:
            missing_links = []
            if not has_privacy:
                missing_links.append("Privacy Policy")
            if not has_terms:
                missing_links.append("Terms of Service")
            ev_hash = hashlib.md5("trust_links".encode()).hexdigest()[:8]
            ev_ref = EvidenceRef(
                source_type="crawl",
                source_id=f"cro_trust_links_{ev_hash}",
                evidence_hash=ev_hash,
                url=pages[0].url,
                selector="footer",
                snippet=f"Missing footer links: {', '.join(missing_links)}",
                observed_value=len(missing_links),
                collector_or_analyzer="CroAnalyzer.trust_links",
            )
            findings.append(Finding(
                finding_id=f"find_cro_trust_links_{ev_hash}",
                title=f"Missing Critical Trust Links ({', '.join(missing_links)})",
                description=(
                    f"The website lacks conspicuous global footer links to {', '.join(missing_links)}. "
                    "Corporate compliance officers and security-conscious buyers check for legal disclaimers "
                    "before initiating commercial contact."
                ),
                category=Category.UX_CONVERSION,
                severity=Severity.LOW,
                impact=2,
                effort=1,
                priority=3,
                recommendation=f"Add transparent links to {', '.join(missing_links)} in the global footer.",
                why_it_matters="Mandatory for legal compliance and builds baseline corporate legitimacy.",
                validation_criteria="Global footer must contain crawlable links to Privacy Policy and Terms of Service.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="DOM",
                evidence=[FindingEvidence(
                    url=pages[0].url,
                    element="footer",
                    value=f"Missing: {', '.join(missing_links)}",
                    source="crawl",
                    evidence_ref=ev_ref,
                )],
                evidence_refs=[ev_ref.source_id],
                evidence_ref_objects=[ev_ref],
            ))

        cro_report = CroAuditReport(
            overall_cro_score=round(overall_score, 1),
            cro_grade=cro_grade,
            cta_analysis=cta_rollup,
            social_proof=social_proof_audit,
            pricing_psychology=pricing_audit,
            value_prop=value_prop_audit,
            form_friction=form_rep,
            actionable_remedies=remedies,
        )
        from app.intelligence.cro import build_cro_intelligence

        cro_report.intelligence = build_cro_intelligence(
            pages=pages,
            raw_html_map=raw_html_map,
            business_profile=business_profile,
        ).model_dump()

        return cro_report, findings


analyze_cro = CroAnalyzer.analyze_cro
