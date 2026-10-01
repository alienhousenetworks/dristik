"""
Citation-Ready Passage Detector & Rewriter.
Layer 1 Extractability: What Dristik can prove deterministically from the website itself,
augmented with optional LLM Generative Engine Optimization (GEO) synthesis.

Scans content paragraphs across all crawled pages and evaluates whether they are
ready for external AI retrieval citation (Perplexity, ChatGPT Search, Gemini, Claude).

Evaluates 4 core criteria (25 pts each = 100 max):
1. Length & Standalone Clarity: 35–75 words; self-contained without dangling pronouns.
2. Explicit Subject Attribution: Explicitly names the entity rather than vague pronouns ("We build...").
3. Informational Gain & Density: Contains concrete facts, named technologies, or quantifiable metrics.
4. Factuality vs Fluff: Deducts for empty marketing adjectives ("cutting-edge", "game-changing").

Produces drop-in rewrite recommendations for partially citable or weak blocks,
strictly avoiding repetitive prefixes and broken syntax.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.config import settings
from app.domain.models import PageEvidence

logger = logging.getLogger(__name__)

PassageTier = Literal["HIGHLY_CITABLE", "PARTIALLY_CITABLE", "WEAK"]

DANGLING_ANAPHORA = [
    "as mentioned above", "as discussed", "in addition to these",
    "these features", "furthermore we", "additionally we also",
    "our team also does", "as a result of this", "like we said"
]

FLUFF_TERMS = [
    "revolutionize", "revolutionary", "unprecedented", "cutting-edge", "seamless", "seamlessly",
    "next-generation", "next-gen", "unlock growth", "future of business",
    "game-changer", "game-changing", "innovative solutions", "synergy", "synergistic",
    "reimagine", "all-in-one", "world-class", "best-in-class", "supercharge",
    "robust", "state-of-the-art", "paradigm",
]

FACTUAL_INDICATORS = [
    "api", "fastapi", "python", "react", "aws", "cloud", "soc 2", "iso 27001",
    "gdpr", "hipaa", "postgres", "docker", "kubernetes", "%", "$", "sla",
    "b2b", "saas", "enterprise", "startups", "uptime", "latency", "sdk"
]

BOILERPLATE_PATTERNS = [
    re.compile(r"copyright\s*(?:©|\(c\)|&copy;|\d{4})", re.I),
    re.compile(r"all\s+rights\s+reserved", re.I),
    re.compile(r"privacy\s+policy|terms\s+of\s+service|terms\s+of\s+use|cookie\s+settings", re.I),
    re.compile(r"^(?:skip\s+to\s+content|menu|navigation|home\s+about\s+services)", re.I),
]


class CitationPassage(BaseModel):
    passage_id: str
    source_url: str
    raw_text: str
    word_count: int
    standalone_clarity_score: float      # 0 to 25
    subject_attribution_score: float     # 0 to 25
    informational_gain_score: float      # 0 to 25
    factuality_score: float              # 0 to 25
    total_score: float                   # 0 to 100
    readiness_tier: PassageTier
    detected_subject: str = "generic_we" # "canonical_brand", "generic_we", "unnamed"
    fluff_detected: List[str] = Field(default_factory=list)
    factual_anchors: List[str] = Field(default_factory=list)
    keyword_stuffing_detected: bool = False
    keyword_stuffing_penalty: float = 0.0
    statistics_density_score: float = 0.0
    quotation_density_score: float = 0.0
    citation_anchor_score: float = 0.0
    needs_rewrite: bool = False
    rewrite_recommendation: Optional[str] = None
    rewrite_rationale: Optional[str] = None


class CitationRewriteItem(BaseModel):
    passage_id: str
    source_url: str
    current_passage: str
    recommended_rewrite: str
    why: str
    estimated_score_improvement: str
    category: Optional[str] = "Core Offerings"
    primary_geo_lever: str = "FLUENCY_OPTIMIZATION"  # STATISTICS_ADDITION | QUOTATION_ADDITION | CITE_SOURCES | FLUENCY_OPTIMIZATION | SIMPLIFICATION
    provenance_tag: str = "SITE_EXTRACTED"           # CLIENT_SUPPLIED | SITE_EXTRACTED | VERIFIED_THIRD_PARTY | UNVERIFIED_PLACEHOLDER
    provenance_source: Optional[str] = None
    approval_status: str = "DRAFT_PENDING_APPROVAL"  # DRAFT_PENDING_APPROVAL | APPROVED | REJECTED
    keyword_stuffing_detected: bool = False
    keyword_stuffing_penalty: float = 0.0
    improvements: List[str] = Field(default_factory=list)
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    all_source_urls: List[str] = Field(default_factory=list)


class CitationPassageAnalysisResult(BaseModel):
    total_passages_scanned: int
    highly_citable_count: int
    partially_citable_count: int
    weak_count: int
    citation_readiness_score: float  # 0 to 100
    passages: List[CitationPassage] = Field(default_factory=list)
    rewrite_recommendations: List[CitationRewriteItem] = Field(default_factory=list)
    summary: str = ""


def _brand_possessive(brand: str) -> str:
    """Proper English possessive: 'Networks'' vs 'Google's'."""
    b = (brand or "").strip()
    if not b:
        return "The Company's"
    if b.endswith(("s", "S", "z", "Z")):
        return f"{b}'"
    return f"{b}'s"


def _normalize_passage_key(text: str) -> str:
    """Canonical key to deduplicate identical passages across crawled pages."""
    t = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", " ", t).strip()


class CitationPassageAnalyzer:
    """
    Scans paragraphs across crawled pages and detects citation suitability.
    Features cross-page deduplication, grammar-aware fluff removal,
    and LLM-assisted citation enhancement.
    """

    def __init__(self, brand_name: str = ""):
        self.brand_name = brand_name

    def _extract_paragraphs(self, pages: List[PageEvidence]) -> List[Tuple[str, str, List[str]]]:
        """
        Extracts candidate paragraphs (primary_url, text, all_source_urls) from page body text.
        Deduplicates identical text blocks across pages and discards boilerplate.
        """
        # Map: normalized_key -> (primary_url, text, [all_urls])
        seen: Dict[str, Tuple[str, str, List[str]]] = {}

        for p in pages:
            url = p.url or ""
            body = p.body_text or ""
            blocks = re.split(r"\n\s*\n|\r\n\s*\r\n", body)
            for b in blocks:
                cleaned = re.sub(r"\s+", " ", b).strip()
                words = cleaned.split()
                # Candidate passage should have between 12 and 120 words
                if not (12 <= len(words) <= 120):
                    continue

                # Filter boilerplate
                if any(bp.search(cleaned) for bp in BOILERPLATE_PATTERNS):
                    continue

                key = _normalize_passage_key(cleaned)
                if not key or len(key) < 25:
                    continue

                if key in seen:
                    prev_url, prev_text, urls = seen[key]
                    if url and url not in urls:
                        urls.append(url)
                else:
                    seen[key] = (url, cleaned, [url] if url else [])

        # Priority sort: passages discussing core services/products/capabilities first
        def passage_priority(item: Tuple[str, str, List[str]]) -> int:
            txt = item[1].lower()
            score = 0
            if any(term in txt for term in ["service", "platform", "solution", "software", "infrastructure", "ai", "consulting", "engineers", "develops"]):
                score += 10
            if any(term in txt for term in ["we ", "our ", "provide", "delivers", "specializ"]):
                score += 5
            return score

        candidates = list(seen.values())
        candidates.sort(key=passage_priority, reverse=True)
        return candidates

    def _detect_keyword_stuffing(self, text: str, brand: str) -> Tuple[bool, float]:
        """
        Detects repetitive keyword/brand stuffing in passages.
        Aggarwal et al. (KDD 2024) demonstrated keyword stuffing harms visibility (-8% to -10%).
        Emits a 10.0 point penalty deduction if detected.
        """
        words = text.lower().split()
        if len(words) < 8:
            return False, 0.0

        brand_tokens = [t for t in re.findall(r"\b[a-z0-9]+\b", brand.lower()) if len(t) > 2]
        if not brand_tokens:
            return False, 0.0

        for tok in brand_tokens:
            count = sum(1 for w in words if tok in w)
            density = float(count) / float(len(words))
            # Flag if keyword occurs > 3 times in < 45 words or density > 6%
            if (count >= 3 and len(words) <= 45) or density > 0.06:
                return True, 10.0
        return False, 0.0

    def _score_passage(
        self,
        text: str,
        brand: str
    ) -> Tuple[float, float, float, float, PassageTier, str, List[str], List[str], float, float, float, bool, float]:
        words = text.split()
        word_count = len(words)
        low = text.lower()
        first_15_words = " ".join(words[:15]).lower()

        # 1. Standalone Clarity (0 - 25)
        clarity = 15.0
        if 35 <= word_count <= 75:
            clarity += 10.0
        elif 25 <= word_count <= 95:
            clarity += 5.0

        for dang in DANGLING_ANAPHORA:
            if dang in low:
                clarity = max(5.0, clarity - 10.0)
                break

        # 2. Explicit Subject Attribution (0 - 25)
        attribution = 8.0
        detected_subj = "unnamed"
        brand_clean = brand.lower().strip()

        if brand_clean and brand_clean in first_15_words:
            attribution = 25.0
            detected_subj = "canonical_brand"
        elif brand_clean and brand_clean in low:
            attribution = 18.0
            detected_subj = "canonical_brand"
        elif re.search(r"^(?:we\s+|our\s+team|our\s+company)", first_15_words):
            attribution = 10.0
            detected_subj = "generic_we"
        else:
            attribution = 5.0
            detected_subj = "unnamed"

        # 3. Informational Gain & Density (0 - 25)
        info_gain = 8.0
        factual_anchors = []
        for fact in FACTUAL_INDICATORS:
            if re.search(rf"\b{re.escape(fact)}\b", low):
                factual_anchors.append(fact)

        metrics = re.findall(r"(?:\$|€|£|₹|\b\d+[\.,]?\d*%?|\b\d+\+\b)", text)
        factual_anchors.extend(metrics[:2])

        info_gain += min(17.0, len(factual_anchors) * 5.0)

        # 4. Factuality vs Fluff (0 - 25)
        factuality = 22.0
        fluff_found = []
        for fl in FLUFF_TERMS:
            if fl in low:
                fluff_found.append(fl)

        factuality -= min(17.0, len(fluff_found) * 7.0)
        factuality = max(5.0, factuality)

        # Keyword stuffing penalty check (Aggarwal et al., KDD 2024 negative impact finding: -8% to -10%)
        kw_stuffed, kw_penalty = self._detect_keyword_stuffing(text, brand)

        # Statistics density score (0 - 25)
        stat_score = min(25.0, len(metrics) * 10.0 + (5.0 if any(c in text for c in ["%", "$", "€", "₹", "ms", "SLA"]) else 0.0))

        # Quotation density score (0 - 25)
        quotes = re.findall(r'"([^"]{8,})"', text) or re.findall(r"'([^']{8,})'", text)
        quote_score = min(25.0, len(quotes) * 12.5)

        # Citation anchor score (0 - 25)
        anchors = [f for f in factual_anchors if any(t in f.lower() for t in ["soc 2", "iso", "api", "gdpr", "hipaa", "aws", "docker"])]
        anchor_score = min(25.0, len(anchors) * 8.0)

        total = clarity + attribution + info_gain + factuality - kw_penalty
        total = max(10.0, min(100.0, total))

        if total >= 75.0:
            tier: PassageTier = "HIGHLY_CITABLE"
        elif total >= 50.0:
            tier = "PARTIALLY_CITABLE"
        else:
            tier = "WEAK"

        return clarity, attribution, info_gain, factuality, tier, detected_subj, fluff_found, factual_anchors, stat_score, quote_score, anchor_score, kw_stuffed, kw_penalty

    def _to_third_person(self, verb: str) -> str:
        word = verb.lower()
        irregular = {
            "are": "is", "is": "is", "have": "has", "has": "has",
            "do": "does", "focus": "focuses", "deliver": "delivers",
            "build": "builds", "provide": "provides", "offer": "offers",
            "help": "helps", "ensure": "ensures", "enable": "enables",
        }
        if word in irregular:
            return irregular[word]
        if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
            return word[:-1] + "ies"
        if word.endswith(("s", "sh", "ch", "x", "z", "o")):
            return word + "es"
        return word + "s"

    def _conjugate_phrase(self, phrase: str) -> str:
        parts = re.split(r"(\s+and\s+|,\s*)", phrase.strip())
        return "".join(
            self._to_third_person(part) if re.fullmatch(r"[A-Za-z]+", part) else part
            for part in parts
        )

    def _same_text(self, left: str, right: str) -> bool:
        def norm(value: str) -> str:
            return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
        return norm(left) == norm(right)

    def _clean_syntax_and_grammar(self, text: str) -> str:
        """
        Cleans syntax defects after word removals:
        - Commas following verbs ('building, secure' -> 'building secure')
        - Double commas
        - Proper 'a' vs 'an' indefinite articles
        - Punctuation spacing
        """
        cleaned = text

        # 1. Clean dangling commas right after verbs or prepositions
        cleaned = re.sub(
            r"\b(building|delivering|creating|offering|providing|developing|engineering|using|with|for|to)\s*,\s*",
            r"\1 ",
            cleaned,
            flags=re.I
        )

        # 2. Fix multiple commas and spaces before punctuation
        cleaned = re.sub(r",\s*,+", ", ", cleaned)
        cleaned = re.sub(r"\s+([,.;?!])", r"\1", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)

        # 3. Fix coordinate commas (e.g. 'building secure, and scalable' -> 'building secure and scalable')
        cleaned = re.sub(r",\s*and\b", " and", cleaned)

        # 4. Fix indefinite articles: 'a' before vowel sounds (e-commerce, AI, enterprise, electric, intelligent)
        vowel_sound_pattern = r"\b([Aa])\s+((?:[aeioAEIO]|un|ev|ai|api)\b|[a-z0-9-]*e-commerce)"
        cleaned = re.sub(vowel_sound_pattern, r"\1n \2", cleaned, flags=re.I)

        # 5. Fix 'an' before consonant sounds (e.g. 'an cloud' -> 'a cloud', 'an software' -> 'a software')
        cleaned = re.sub(
            r"\b([Aa])n\s+([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ][a-z]+)",
            r"\1 \2",
            cleaned
        )

        return cleaned.strip()

    def _generate_rewrite(
        self,
        text: str,
        brand: str,
        fluff_found: List[str],
        detected_subj: str
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Generates an authoritative, grammatically sound rewrite for a citable passage.
        Returns: (rewritten_text, rationale, improvements_list)
        """
        brand_name = (brand or "").strip()
        if not brand_name:
            return None, None, []

        possessive_brand = _brand_possessive(brand_name)
        rewritten = re.sub(r"\s+", " ", text).strip()
        changes: List[str] = []
        improvements: List[str] = []

        # 1. Clean fluff terms gracefully
        for fl in fluff_found:
            # Pattern matches fluff term with optional trailing comma/conjunction
            cleaned = re.sub(rf"\b{re.escape(fl)}\b", "", rewritten, flags=re.I)
            cleaned = self._clean_syntax_and_grammar(cleaned)
            if not self._same_text(cleaned, rewritten):
                rewritten = cleaned
                changes.append(f"removed empty adjective \"{fl}\"")

        if fluff_found:
            improvements.append("Fluff Elimination")

        # 2. Transform Opening Pronouns ("We", "Our")
        opening = re.match(
            r"^We\s+((?:[A-Za-z]+(?:,\s*|\s+and\s+))*[A-Za-z]+)\b(.*)$",
            rewritten,
            flags=re.I,
        )
        if opening and opening.group(1).lower() not in {"are", "is"}:
            rewritten = f"{brand_name} {self._conjugate_phrase(opening.group(1))}{opening.group(2)}"
            changes.append("established explicit brand attribution in the primary clause")
            improvements.append("Entity Grounding")
        else:
            are_match = re.match(r"^We\s+are\s+(?:an?\s+)?(.*)$", rewritten, flags=re.I)
            if are_match:
                rewritten = f"{brand_name} is {are_match.group(1).strip()}"
                changes.append("anchored entity definition with brand name")
                improvements.append("Entity Grounding")

        # 3. Replace ambiguous possessive "Our"
        without_our = re.sub(r"\b[Oo]ur\b", possessive_brand, rewritten)
        if not self._same_text(without_our, rewritten):
            rewritten = without_our
            changes.append("replaced ambiguous \"our\" with explicit brand ownership")
            if "Entity Grounding" not in improvements:
                improvements.append("Entity Grounding")

        # 4. Replace remaining "we <verb>"
        def _we_verb(match: re.Match) -> str:
            return f"{brand_name} {self._to_third_person(match.group(1))}"

        without_we = re.sub(r"\b[Ww]e\s+([A-Za-z]+)\b", _we_verb, rewritten)
        if not self._same_text(without_we, rewritten):
            rewritten = without_we
            changes.append("converted remaining first-person verbs to third-person attribution")

        # 5. Transform second-person slogans into declarative capabilities
        slogan = re.match(
            r"^(?:Boost|Grow|Discover|Unlock|Transform)\b.+?\bwith\s+(.+?)\.?$",
            rewritten,
            flags=re.I,
        )
        if slogan:
            offer = re.sub(r"\b(your|you)\b", "", slogan.group(1), flags=re.I)
            offer = re.sub(r"\s{2,}", " ", offer).strip(" .")
            if offer:
                rewritten = f"{brand_name} delivers {offer} designed for enterprise scalability and performance."
                changes.append("restructured second-person promotional hook into an authoritative capability statement")
                improvements.append("Declarative Structure")

        # 6. Transform standalone noun phrases (Services, Infrastructure, Architecture)
        if brand_name.lower() not in rewritten.lower() and "?" not in rewritten and not re.match(r"^[\d(]", rewritten):
            rewritten_clean = self._clean_syntax_and_grammar(rewritten)
            low_text = rewritten_clean.lower()
            if low_text.startswith(("custom software", "software development", "web and mobile")):
                rewritten = f"{brand_name} engineers {rewritten_clean[0].lower() + rewritten_clean[1:]}"
            elif low_text.startswith(("secure,", "cloud infrastructure", "cloud solutions")):
                rewritten = f"{brand_name} provides {rewritten_clean[0].lower() + rewritten_clean[1:]}"
            elif low_text.startswith(("design, development", "design and development", "ai engineering", "scalable ai")):
                rewritten = f"{brand_name} delivers end-to-end {rewritten_clean[0].lower() + rewritten_clean[1:]}"
            elif low_text.startswith(("strategic business", "consulting", "hiring", "recruitment", "staffing")):
                rewritten = f"{brand_name} provides {rewritten_clean[0].lower() + rewritten_clean[1:]}"
            else:
                body = rewritten_clean[0].lower() + rewritten_clean[1:] if rewritten_clean else rewritten_clean
                rewritten = f"{brand_name} provides {body}"
            changes.append("anchored standalone service definition with explicit company attribution")
            improvements.append("Entity Grounding")

        # 7. Final syntax and grammar cleanup
        rewritten = self._clean_syntax_and_grammar(rewritten)
        if not rewritten.endswith((".", "!", "?")):
            rewritten += "."

        if not changes or self._same_text(rewritten, text):
            return None, None, []

        rationale = "Transformed crawled copy: " + "; ".join(changes) + "."
        if not improvements:
            improvements.append("Citation Optimization")

        return rewritten, rationale, improvements

    def analyze(
        self,
        pages: List[PageEvidence],
        brand_name: str = ""
    ) -> CitationPassageAnalysisResult:
        brand = brand_name or self.brand_name or "The Company"
        paragraphs = self._extract_paragraphs(pages)

        passages: List[CitationPassage] = []
        raw_rewrites: List[CitationRewriteItem] = []

        passage_idx = 1
        for primary_url, raw_text, all_urls in paragraphs:
            clarity, attribution, info_gain, factuality, tier, detected_subj, fluff_found, factual_anchors, stat_score, quote_score, anchor_score, kw_stuffed, kw_penalty = self._score_passage(raw_text, brand)
            total = clarity + attribution + info_gain + factuality - kw_penalty

            pid = f"PASS-{passage_idx:03d}"
            passage_idx += 1

            needs_rewrite = (tier in ["PARTIALLY_CITABLE", "WEAK"]) or (detected_subj == "generic_we") or (len(fluff_found) > 0) or kw_stuffed
            rec_text = None
            rec_why = None

            if needs_rewrite:
                rec_text, rec_why, improvements = self._generate_rewrite(raw_text, brand, fluff_found, detected_subj)
                if rec_text and rec_why:
                    rescored = sum(self._score_passage(rec_text, brand)[:4])

                    # Determine primary GEO lever
                    primary_lever = "FLUENCY_OPTIMIZATION"
                    if "Fluff Elimination" in improvements:
                        primary_lever = "SIMPLIFICATION"
                    elif stat_score > 10.0:
                        primary_lever = "STATISTICS_ADDITION"
                    elif quote_score > 10.0:
                        primary_lever = "QUOTATION_ADDITION"
                    elif anchor_score > 10.0:
                        primary_lever = "CITE_SOURCES"
                    elif "Entity Grounding" in improvements:
                        primary_lever = "FLUENCY_OPTIMIZATION"

                    # Provenance and zero-hallucination guard
                    prov_tag = "UNVERIFIED_PLACEHOLDER" if "[ADD VERIFIED" in rec_text else "SITE_EXTRACTED"

                    raw_rewrites.append(CitationRewriteItem(
                        passage_id=pid,
                        source_url=primary_url,
                        current_passage=raw_text[:280],
                        recommended_rewrite=rec_text[:280],
                        why=rec_why,
                        estimated_score_improvement=f"{total:.0f} → {min(100, round(rescored)):.0f}/100",
                        improvements=improvements,
                        primary_geo_lever=primary_lever,
                        provenance_tag=prov_tag,
                        provenance_source=primary_url,
                        approval_status="DRAFT_PENDING_APPROVAL",
                        keyword_stuffing_detected=kw_stuffed,
                        keyword_stuffing_penalty=kw_penalty,
                        score_before=round(total, 1),
                        score_after=round(min(100.0, rescored), 1),
                        all_source_urls=all_urls,
                    ))
                else:
                    rec_text, rec_why = None, None
                    needs_rewrite = False

            passages.append(CitationPassage(
                passage_id=pid,
                source_url=primary_url,
                raw_text=raw_text,
                word_count=len(raw_text.split()),
                standalone_clarity_score=round(clarity, 1),
                subject_attribution_score=round(attribution, 1),
                informational_gain_score=round(info_gain, 1),
                factuality_score=round(factuality, 1),
                total_score=round(total, 1),
                readiness_tier=tier,
                detected_subject=detected_subj,
                fluff_detected=fluff_found,
                factual_anchors=factual_anchors,
                keyword_stuffing_detected=kw_stuffed,
                keyword_stuffing_penalty=kw_penalty,
                statistics_density_score=round(stat_score, 1),
                quotation_density_score=round(quote_score, 1),
                citation_anchor_score=round(anchor_score, 1),
                needs_rewrite=needs_rewrite,
                rewrite_recommendation=rec_text,
                rewrite_rationale=rec_why,
            ))

        if not passages:
            return CitationPassageAnalysisResult(
                total_passages_scanned=0,
                highly_citable_count=0,
                partially_citable_count=0,
                weak_count=0,
                citation_readiness_score=40.0,
                passages=[],
                rewrite_recommendations=[],
                summary="No multi-sentence narrative passages detected across crawled pages.",
            )

        highly_citable = sum(1 for p in passages if p.readiness_tier == "HIGHLY_CITABLE")
        partially_citable = sum(1 for p in passages if p.readiness_tier == "PARTIALLY_CITABLE")
        weak = sum(1 for p in passages if p.readiness_tier == "WEAK")
        avg_score = sum(p.total_score for p in passages) / len(passages)

        # Prioritize top 8 highest-impact distinct recommendations
        # Sorted by greatest score delta and informational importance
        raw_rewrites.sort(
            key=lambda r: (
                (r.score_after or 0) - (r.score_before or 0),
                len(r.improvements)
            ),
            reverse=True
        )
        selected_rewrites = raw_rewrites[:8]

        summary = (
            f"Scanned {len(passages)} unique passages across crawled pages. "
            f"{highly_citable} are highly citation-ready ({round(highly_citable/len(passages)*100)}%), "
            f"{partially_citable} partially citation-ready, and {weak} weak or fluff-heavy. "
            f"Generated {len(selected_rewrites)} prioritized high-impact passage rewrites to boost AI search quotation."
        )

        return CitationPassageAnalysisResult(
            total_passages_scanned=len(passages),
            highly_citable_count=highly_citable,
            partially_citable_count=partially_citable,
            weak_count=weak,
            citation_readiness_score=round(avg_score, 1),
            passages=passages,
            rewrite_recommendations=selected_rewrites,
            summary=summary,
        )

    async def enrich_rewrites_with_llm(
        self,
        result: CitationPassageAnalysisResult,
        model_router: Any,
        brand_name: str,
        domain: str,
        profile: Optional[Any] = None,
    ) -> CitationPassageAnalysisResult:
        """
        Uses ModelRouter to elevate the top passage rewrites into publication-grade,
        authoritative GEO citation snippets grounded in verified on-page evidence.
        """
        if not model_router or not getattr(settings, "has_active_llm_key", False):
            return result

        if not result.rewrite_recommendations:
            return result

        # Select top 5 candidate rewrites to enhance with LLM
        targets = result.rewrite_recommendations[:5]
        brand = brand_name or self.brand_name or domain or "The Company"

        industry = getattr(profile, "industry", "") or getattr(profile, "niche", "") or "Technology"
        services = list(getattr(profile, "services", None) or []) or list(getattr(profile, "products", None) or [])
        service_context = ", ".join(services[:5]) if services else "Enterprise software and digital solutions"

        candidates_payload = [
            {
                "passage_id": t.passage_id,
                "current_passage": t.current_passage,
                "context": t.why
            }
            for t in targets
        ]

        task_contract = (
            f"You are a Generative Engine Optimization (GEO) copywriter for '{brand}' ({domain}).\n"
            f"Business Industry: {industry}. Core Services: {service_context}.\n\n"
            "Task: Rewrite the provided weak or fluff-heavy website passages into citation-grade, authoritative paragraphs (35-65 words each).\n"
            "AI search engines (Perplexity, SearchGPT, Gemini, Claude) will directly quote these to answer buyer questions.\n\n"
            "Strict Quality Rules:\n"
            f"1. Name '{brand}' as the authoritative subject with active third-person verbs.\n"
            "2. Ground all claims strictly in facts provided in the current passage and business profile. DO NOT invent fake clients, awards, statistics, or SOC2/ISO certifications unless explicitly stated.\n"
            "3. Eliminate empty consulting buzzwords ('cutting-edge', 'seamless', 'revolutionary', 'game-changing', 'next-gen', 'world-class'). Replace them with concrete operational or technical capabilities.\n"
            "4. Ensure flawless English grammar, natural syntax, and complete standalone clarity.\n"
            "5. The rewrite MUST substantively improve the sentence. Do not just paste the company name on the front of an unchanged sentence.\n"
        )

        rubric = (
            "1. ENTITY CLARITY: Passage explicitly names the brand and defines what it delivers.\n"
            "2. QUOTATION READINESS: Self-contained statement that an AI answer engine can quote verbatim as a factual source.\n"
            "3. ZERO FLUFF: Professional, dense, executive tone without vague marketing superlatives."
        )

        output_schema_desc = (
            "{\n"
            '  "rewrites": [\n'
            '    {\n'
            '      "passage_id": "string",\n'
            '      "recommended_rewrite": "string (35-65 words, authoritative, citable)",\n'
            '      "why": "string (concise explanation of why this rewrite boosts AI search citation)",\n'
            '      "improvements": ["Entity Grounding", "Fluff Eliminated", "High Citation Density"]\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            llm_res = await model_router.generate_structured(
                capability="content_intelligence",
                agent_role="GEO Citation Copywriter. Precision evidence-grounded copy.",
                task_contract=task_contract,
                evidence_list=[],
                rubric=rubric,
                output_schema_desc=output_schema_desc,
                additional_context=f"Candidates to rewrite:\n{candidates_payload}",
                allow_fallback=False,
            )

            if isinstance(llm_res, dict) and "rewrites" in llm_res and isinstance(llm_res["rewrites"], list):
                llm_map = {item.get("passage_id"): item for item in llm_res["rewrites"] if isinstance(item, dict)}

                for rec in result.rewrite_recommendations:
                    pid = rec.passage_id
                    if pid in llm_map:
                        item = llm_map[pid]
                        new_text = (item.get("recommended_rewrite") or "").strip()
                        new_why = (item.get("why") or "").strip()
                        new_improvements = item.get("improvements") or ["Entity Grounding", "Fluff Eliminated", "Citation Optimized"]

                        if new_text and not self._same_text(new_text, rec.current_passage):
                            rescored = sum(self._score_passage(new_text, brand)[:4])
                            rec.recommended_rewrite = new_text
                            rec.why = new_why or rec.why
                            rec.improvements = new_improvements
                            rec.score_after = round(min(100.0, rescored), 1)
                            rec.estimated_score_improvement = f"{rec.score_before:.0f} → {min(100, round(rescored)):.0f}/100"

                logger.info("[CitationPassages] Successfully enriched %d passage rewrites with LLM", len(llm_map))
        except Exception as exc:
            logger.warning("[CitationPassages] LLM enrichment encountered exception, preserving deterministic rewrites: %s", exc)

        return result


passage_analyzer = CitationPassageAnalyzer()
