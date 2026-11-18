"""
Structured Value Proposition Model & Intelligence Engine (Phase 6.3).

Evaluates whether a new visitor can immediately answer the 6 Core Buyer Questions:
1. What is being sold?
2. Who is it for?
3. What problem does it solve?
4. Why is it different?
5. Why should I trust it?
6. What should I do next?

Inspects 10 dimensions with transparent criteria:
1. Headline clarity
2. Brand identification
3. Product/service clarity
4. Target audience
5. Primary benefit
6. Differentiation
7. Supporting proof
8. Offer visibility
9. Price transparency
10. Risk reversal

Notice: Transparent criteria used rather than treating a 5-second comprehension heuristic as a measured conversion result.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence, Finding, FindingEvidence, EvidenceRef
from app.domain.enums import Category, Severity, EvidenceClass


class BuyerQuestionAnswer(BaseModel):
    question_number: int
    question: str
    answered: bool
    confidence_score: float # 0.0 to 100.0
    detected_statement: Optional[str] = None
    evaluation_criteria: str
    observed_gap: Optional[str] = None


class ValuePropDimension(BaseModel):
    id: str
    name: str
    score: float # 0.0 to 100.0
    status: str # "STRONG", "ADEQUATE", "DEFICIENT", "UNMEASURED"
    evidence_snippet: Optional[str] = None
    observation: str


class ValuePropIntelligenceResult(BaseModel):
    hero_headline: str = ""
    hero_subhead: str = ""
    brand_name: str = ""
    overall_value_prop_score: float = 70.0
    buyer_questions: List[BuyerQuestionAnswer] = Field(default_factory=list)
    dimensions: List[ValuePropDimension] = Field(default_factory=list)
    transparent_criteria_disclosure: str = (
        "Evaluated via structured deterministic NLP and semantic pattern extraction across above-the-fold hero DOM. "
        "This heuristic analysis is transparent criteria and not a substitute for measured customer conversion data."
    )
    defects: List[Dict[str, Any]] = Field(default_factory=list)


class ValuePropAnalyzer:
    """Analyzes hero messaging, value proposition clarity, and commercial offer transparency."""

    @classmethod
    def analyze(
        cls,
        pages: List[PageEvidence],
        raw_html_map: Optional[Dict[str, str]] = None,
        business_profile: Optional[Any] = None,
    ) -> ValuePropIntelligenceResult:
        raw_html_map = raw_html_map or {}
        first_page = pages[0] if pages else None
        html = ""
        url = ""
        if first_page:
            url = getattr(first_page, "url", "")
            html = raw_html_map.get(url) or getattr(first_page, "raw_html", "") or ""

        soup = BeautifulSoup(html, "html.parser") if html else None

        # 1. Extract Hero Elements
        hero_h1 = cls._extract_h1(soup, first_page)
        hero_subhead = cls._extract_subhead(soup)
        brand = cls._extract_brand(soup, url, business_profile)

        # Full hero and page text corpus
        hero_corpus = f"{hero_h1} {hero_subhead}".strip()
        body_sample = (getattr(first_page, "body_text", "") or "")[:2000] if first_page else ""
        soup_text = soup.get_text(" ", strip=True) if soup else ""
        combined_text = f"{hero_corpus} {body_sample} {soup_text}".strip()

        # 2. Evaluate the 6 Core Buyer Questions
        q1 = cls._eval_q1_what_is_sold(hero_h1, hero_corpus, soup)
        q2 = cls._eval_q2_who_is_it_for(hero_corpus, body_sample)
        q3 = cls._eval_q3_what_problem(hero_corpus, body_sample)
        q4 = cls._eval_q4_why_different(hero_corpus, body_sample)
        q5 = cls._eval_q5_why_trust(soup, combined_text)
        q6 = cls._eval_q6_what_next(soup, first_page)

        buyer_questions = [q1, q2, q3, q4, q5, q6]

        # 3. Evaluate 10 Value Prop Dimensions
        dimensions = cls._evaluate_10_dimensions(
            hero_h1=hero_h1,
            hero_subhead=hero_subhead,
            brand=brand,
            hero_corpus=hero_corpus,
            combined_text=combined_text,
            soup=soup,
            buyer_questions=buyer_questions,
        )

        # 4. Overall Score
        overall_score = round(sum(d.score for d in dimensions) / len(dimensions), 1)

        # 5. Extract Defects
        defects = []
        for q in buyer_questions:
            if not q.answered:
                defects.append({
                    "type": "UNANSWERED_BUYER_QUESTION",
                    "question": q.question,
                    "gap": q.observed_gap,
                    "severity": "HIGH" if q.question_number in (1, 3, 6) else "MEDIUM",
                })

        return ValuePropIntelligenceResult(
            hero_headline=hero_h1,
            hero_subhead=hero_subhead,
            brand_name=brand,
            overall_value_prop_score=overall_score,
            buyer_questions=buyer_questions,
            dimensions=dimensions,
            defects=defects,
        )

    @classmethod
    def _extract_h1(cls, soup: Optional[BeautifulSoup], page: Optional[PageEvidence]) -> str:
        if soup:
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                return h1.get_text(strip=True)
        if page:
            h1s = getattr(page, "h1_tags", None) or getattr(page, "h1", None) or []
            if h1s:
                return str(h1s[0]).strip()
            if getattr(page, "title", None):
                return str(page.title).split("|")[0].split("-")[0].strip()
        return "Untitled Proposition"

    @classmethod
    def _extract_subhead(cls, soup: Optional[BeautifulSoup]) -> str:
        if not soup:
            return ""
        # Check paragraph following h1 or hero subtitle class
        hero = soup.find(class_=re.compile(r"hero|masthead|banner", re.I))
        if hero:
            p = hero.find("p")
            if p and p.get_text(strip=True):
                return p.get_text(strip=True)[:250]
        h1 = soup.find("h1")
        if h1:
            nxt = h1.find_next_sibling(["p", "h2"])
            if nxt and nxt.get_text(strip=True):
                return nxt.get_text(strip=True)[:250]
        return ""

    @classmethod
    def _extract_brand(cls, soup: Optional[BeautifulSoup], url: str, profile: Optional[Any]) -> str:
        if profile and getattr(profile, "brand_name", None):
            return str(profile.brand_name)
        if soup:
            meta_brand = soup.find("meta", property="og:site_name")
            if meta_brand and meta_brand.get("content"):
                return meta_brand.get("content").strip()
        # Fallback to domain root
        netloc = url.split("//")[-1].split("/")[0].replace("www.", "")
        return netloc.split(".")[0].title()

    @classmethod
    def _eval_q1_what_is_sold(cls, h1: str, corpus: str, soup: Optional[BeautifulSoup]) -> BuyerQuestionAnswer:
        # What is being sold? Looks for product nouns, software, platform, service, API, tool, etc.
        patterns = re.compile(r"\b(software|platform|tool|app|service|solution|api|dashboard|engine|generator|agency|system|course|product|kit)\b", re.I)
        match = patterns.search(corpus)
        answered = bool(match) or len(h1.split()) >= 4
        return BuyerQuestionAnswer(
            question_number=1,
            question="What is being sold?",
            answered=answered,
            confidence_score=90.0 if match else (70.0 if answered else 35.0),
            detected_statement=f"Detected product descriptor: '{match.group(0)}'" if match else (h1 if answered else None),
            evaluation_criteria="Explicit noun phrase or product categorization in hero heading or subhead.",
            observed_gap="Hero messaging relies on abstract marketing slogans without stating the tangible product/offering." if not match else None,
        )

    @classmethod
    def _eval_q2_who_is_it_for(cls, corpus: str, body: str) -> BuyerQuestionAnswer:
        # Who is it for? Audience qualifiers: for [adjective]? [teams|enterprises|developers|...]
        audience_patterns = re.compile(
            r"\b(for\s+([a-zA-Z-]+\s+)?(teams|developers|marketers|enterprises|businesses|startups|retailers|agencies|creators|designers|engineers|founders|users|buyers))\b",
            re.I,
        )
        match = audience_patterns.search(corpus) or audience_patterns.search(body[:500])
        answered = bool(match)
        return BuyerQuestionAnswer(
            question_number=2,
            question="Who is it for?",
            answered=answered,
            confidence_score=92.0 if match else 40.0,
            detected_statement=match.group(0) if match else None,
            evaluation_criteria="Explicit customer role, vertical, or segment qualifiers ('for engineering teams', 'for retailers').",
            observed_gap="No explicit target audience defined; visitors must guess whether the product is tailored for them." if not answered else None,
        )

    @classmethod
    def _eval_q3_what_problem(cls, corpus: str, body: str) -> BuyerQuestionAnswer:
        # What problem does it solve? Verbs like automate, scale, eliminate, reduce, prevent, protect, fix
        problem_patterns = re.compile(r"\b(automate|scale|eliminate|reduce|stop|prevent|cut|accelerate|boost|simplify|grow|streamline|fix)\b", re.I)
        match = problem_patterns.search(corpus) or problem_patterns.search(body[:500])
        answered = bool(match)
        return BuyerQuestionAnswer(
            question_number=3,
            question="What problem does it solve?",
            answered=answered,
            confidence_score=88.0 if match else 45.0,
            detected_statement=f"Outcome verb identified: '{match.group(0)}'" if match else None,
            evaluation_criteria="Identifiable friction reduction, automation verb, or commercial outcome proposition.",
            observed_gap="Hero copy lacks clear problem/solution causality or quantifiable business benefit." if not answered else None,
        )

    @classmethod
    def _eval_q4_why_different(cls, corpus: str, body: str) -> BuyerQuestionAnswer:
        diff_patterns = re.compile(r"\b(unlike|only|first|fastest|without|smarter|built-in|all-in-one|zero-configuration|patented)\b", re.I)
        match = diff_patterns.search(corpus) or diff_patterns.search(body[:600])
        answered = bool(match)
        return BuyerQuestionAnswer(
            question_number=4,
            question="Why is it different?",
            answered=answered,
            confidence_score=85.0 if match else 40.0,
            detected_statement=match.group(0) if match else None,
            evaluation_criteria="Contrastive claims, unique value propositions, or comparison statements against category defaults.",
            observed_gap="Proposition sounds generic; lacks clear differentiation from market competitors." if not answered else None,
        )

    @classmethod
    def _eval_q5_why_trust(cls, soup: Optional[BeautifulSoup], combined: str) -> BuyerQuestionAnswer:
        trust_badge = soup.find(class_=re.compile(r"testimonial|review|rating|client|logo|trust|soc2|certified|proof", re.I)) if soup else None
        quant_claim = re.search(r"\b(\d+%\s+(faster|more|reduction|lift|growth)|\$\d+|\d+,\d+\s+users|\bSOC\s?2\b|ISO\s?27001|guarantee)\b", combined, re.I)
        answered = bool(trust_badge or quant_claim)
        return BuyerQuestionAnswer(
            question_number=5,
            question="Why should I trust it?",
            answered=answered,
            confidence_score=95.0 if (trust_badge and quant_claim) else (80.0 if answered else 30.0),
            detected_statement=quant_claim.group(0) if quant_claim else ("Social proof / trust badges detected in page structure" if trust_badge else None),
            evaluation_criteria="Quantified performance claims, recognized client logos, security certifications, or risk reversals.",
            observed_gap="Absence of social proof, client validation, or certifications on the initial viewport." if not answered else None,
        )

    @classmethod
    def _eval_q6_what_next(cls, soup: Optional[BeautifulSoup], page: Optional[PageEvidence]) -> BuyerQuestionAnswer:
        cta_candidates = []
        if soup:
            for b in soup.find_all(["button", "a"]):
                txt = b.get_text(strip=True)
                if txt and any(k in txt.lower() for k in ("get started", "start", "try", "book", "buy", "sign up", "contact", "order", "schedule")):
                    cta_candidates.append(txt)
        if not cta_candidates and page:
            cta_candidates = getattr(page, "ctas", []) or []

        answered = len(cta_candidates) > 0
        return BuyerQuestionAnswer(
            question_number=6,
            question="What should I do next?",
            answered=answered,
            confidence_score=95.0 if answered else 20.0,
            detected_statement=f"Clear conversion action: '{cta_candidates[0]}'" if answered else None,
            evaluation_criteria="Unambiguous, action-oriented primary call to action above the fold.",
            observed_gap="No dominant primary CTA directing the visitor to take immediate next step." if not answered else None,
        )

    @classmethod
    def _evaluate_10_dimensions(
        cls,
        hero_h1: str,
        hero_subhead: str,
        brand: str,
        hero_corpus: str,
        combined_text: str,
        soup: Optional[BeautifulSoup],
        buyer_questions: List[BuyerQuestionAnswer],
    ) -> List[ValuePropDimension]:
        dims = []

        # 1. Headline clarity
        h1_len = len(hero_h1.split())
        h1_score = 90.0 if 5 <= h1_len <= 12 else (70.0 if 3 <= h1_len <= 16 else 50.0)
        dims.append(ValuePropDimension(
            id="headline_clarity",
            name="Headline Clarity",
            score=h1_score,
            status="STRONG" if h1_score >= 80 else ("ADEQUATE" if h1_score >= 65 else "DEFICIENT"),
            evidence_snippet=hero_h1,
            observation=f"Headline contains {h1_len} words, optimal cognitive load is 5–12 words.",
        ))

        # 2. Brand identification
        brand_score = 90.0 if brand and len(brand) > 1 else 50.0
        dims.append(ValuePropDimension(
            id="brand_id",
            name="Brand Identification",
            score=brand_score,
            status="STRONG" if brand_score >= 80 else "DEFICIENT",
            evidence_snippet=brand,
            observation=f"Entity name '{brand}' established in title or header metadata.",
        ))

        # 3. Product / Service clarity
        q1 = buyer_questions[0]
        dims.append(ValuePropDimension(
            id="product_clarity",
            name="Product/Service Clarity",
            score=q1.confidence_score,
            status="STRONG" if q1.answered else "DEFICIENT",
            evidence_snippet=q1.detected_statement,
            observation=q1.evaluation_criteria,
        ))

        # 4. Target audience
        q2 = buyer_questions[1]
        dims.append(ValuePropDimension(
            id="target_audience",
            name="Target Audience Definition",
            score=q2.confidence_score,
            status="STRONG" if q2.answered else "DEFICIENT",
            evidence_snippet=q2.detected_statement,
            observation=q2.evaluation_criteria,
        ))

        # 5. Primary benefit
        q3 = buyer_questions[2]
        dims.append(ValuePropDimension(
            id="primary_benefit",
            name="Primary Benefit Articulation",
            score=q3.confidence_score,
            status="STRONG" if q3.answered else "DEFICIENT",
            evidence_snippet=q3.detected_statement,
            observation=q3.evaluation_criteria,
        ))

        # 6. Differentiation
        q4 = buyer_questions[3]
        dims.append(ValuePropDimension(
            id="differentiation",
            name="Differentiation & Uniqueness",
            score=q4.confidence_score,
            status="STRONG" if q4.answered else "DEFICIENT",
            evidence_snippet=q4.detected_statement,
            observation=q4.evaluation_criteria,
        ))

        # 7. Supporting proof
        q5 = buyer_questions[4]
        dims.append(ValuePropDimension(
            id="supporting_proof",
            name="Supporting Proof & Evidence",
            score=q5.confidence_score,
            status="STRONG" if q5.answered else "DEFICIENT",
            evidence_snippet=q5.detected_statement,
            observation=q5.evaluation_criteria,
        ))

        # 8. Offer visibility
        offer_found = bool(re.search(r"\b(free\s+trial|discount|demo|guarantee|money-back|instant\s+access|plan)\b", combined_text, re.I))
        dims.append(ValuePropDimension(
            id="offer_visibility",
            name="Commercial Offer Visibility",
            score=88.0 if offer_found else 55.0,
            status="STRONG" if offer_found else "ADEQUATE",
            evidence_snippet="Commercial incentive / terms detected" if offer_found else "Standard offer",
            observation="Presence of free trial, demo, or guarantee incentives in hero/primary copy.",
        ))

        # 9. Price transparency
        price_found = bool(re.search(r"(\$|€|£|₹|\bper\s+month|\/mo|\bpricing\b)", combined_text, re.I))
        dims.append(ValuePropDimension(
            id="price_transparency",
            name="Price Transparency",
            score=85.0 if price_found else 50.0,
            status="STRONG" if price_found else "DEFICIENT",
            evidence_snippet="Price or pricing link present" if price_found else "No pricing indicators detected",
            observation="Immediate visibility of pricing information or link to clear tier structure.",
        ))

        # 10. Risk reversal
        guarantee_found = bool(re.search(r"\b(no\s+credit\s+card|cancel\s+anytime|money-back|guarantee|free\s+trial|soc\s?2|gdpr)\b", combined_text, re.I))
        dims.append(ValuePropDimension(
            id="risk_reversal",
            name="Risk Reversal & Friction Reducers",
            score=90.0 if guarantee_found else 50.0,
            status="STRONG" if guarantee_found else "DEFICIENT",
            evidence_snippet="Risk-reversal microcopy detected" if guarantee_found else "Missing risk-reversal microcopy",
            observation="Mitigation of buyer hesitation via 'no credit card required', trial, or warranty statements.",
        ))

        return dims


value_prop_analyzer = ValuePropAnalyzer()
