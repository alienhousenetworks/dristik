"""
Citation-Ready Passage Detector & Rewriter.
Layer 1 Extractability: What Dristik can prove deterministically from the website itself.

Scans content paragraphs across all crawled pages and evaluates whether they are
ready for external AI retrieval citation (Perplexity, ChatGPT Search, Gemini, Claude).

Evaluates 4 core criteria (25 pts each = 100 max):
1. Length & Standalone Clarity: 35–75 words; self-contained without dangling pronouns.
2. Explicit Subject Attribution: Explicitly names the entity rather than vague pronouns ("We build...").
3. Informational Gain & Density: Contains concrete facts, named technologies, or quantifiable metrics.
4. Factuality vs Fluff: Deducts for empty marketing adjectives ("cutting-edge", "game-changing").

Produces drop-in rewrite recommendations for partially citable or weak blocks.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence

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


class CitationPassageAnalysisResult(BaseModel):
    total_passages_scanned: int
    highly_citable_count: int
    partially_citable_count: int
    weak_count: int
    citation_readiness_score: float  # 0 to 100
    passages: List[CitationPassage] = Field(default_factory=list)
    rewrite_recommendations: List[CitationRewriteItem] = Field(default_factory=list)
    summary: str = ""


class CitationPassageAnalyzer:
    """
    Scans paragraphs across crawled pages and detects citation suitability.
    """

    def __init__(self, brand_name: str = ""):
        self.brand_name = brand_name

    def _extract_paragraphs(self, pages: List[PageEvidence]) -> List[Tuple[str, str]]:
        """Extracts candidate paragraphs (URL, text) from page body text."""
        candidates = []
        for p in pages:
            body = p.body_text or ""
            # Split by double newline or block-like separators
            blocks = re.split(r"\n\s*\n|\r\n\s*\r\n", body)
            for b in blocks:
                cleaned = re.sub(r"\s+", " ", b).strip()
                words = cleaned.split()
                # Candidate passage should have between 12 and 120 words
                if 12 <= len(words) <= 120:
                    candidates.append((p.url or "", cleaned))
        return candidates

    def _score_passage(
        self,
        text: str,
        brand: str
    ) -> Tuple[float, float, float, float, PassageTier, str, List[str], List[str]]:
        words = text.split()
        word_count = len(words)
        low = text.lower()
        first_15_words = " ".join(words[:15]).lower()

        # 1. Standalone Clarity (0 - 25)
        # Optimal word count is 35-75 words. Deduct for dangling anaphora.
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
        # Does it name the brand in the first 15 words?
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

        total = clarity + attribution + info_gain + factuality
        total = max(10.0, min(100.0, total))

        if total >= 75.0:
            tier: PassageTier = "HIGHLY_CITABLE"
        elif total >= 50.0:
            tier = "PARTIALLY_CITABLE"
        else:
            tier = "WEAK"

        return clarity, attribution, info_gain, factuality, tier, detected_subj, fluff_found, factual_anchors

    def _to_third_person(self, verb: str) -> str:
        word = verb.lower()
        irregular = {
            "are": "is", "is": "is", "have": "has", "has": "has",
            "do": "does", "focus": "focuses",
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
            return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        return norm(left) == norm(right)

    def _generate_rewrite(
        self,
        text: str,
        brand: str,
        fluff_found: List[str],
        detected_subj: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Edit only pronouns and empty marketing words already in the sentence.
        Return nothing when the sentence would stay the same.
        """
        brand_name = (brand or "").strip()
        if not brand_name:
            return None, None
        rewritten = re.sub(r"\s+", " ", text).strip()
        changes: List[str] = []

        for fl in fluff_found:
            cleaned = re.sub(rf"\b{re.escape(fl)}\b", "", rewritten, flags=re.I)
            cleaned = re.sub(r"\s{2,}", " ", cleaned)
            cleaned = re.sub(r"\s+([,.;])", r"\1", cleaned).strip()
            if not self._same_text(cleaned, rewritten):
                rewritten = cleaned
                changes.append(f"removed \"{fl}\"")

        opening = re.match(
            r"^We\s+((?:[A-Za-z]+(?:,\s*|\s+and\s+))*[A-Za-z]+)\b(.*)$",
            rewritten,
            flags=re.I,
        )
        if opening and opening.group(1).lower() not in {"are", "is"}:
            rewritten = f"{brand_name} {self._conjugate_phrase(opening.group(1))}{opening.group(2)}"
            changes.append("replaced opening \"We\" with the company name")
        else:
            are_match = re.match(r"^We\s+are\s+(?:an?\s+)?(.*)$", rewritten, flags=re.I)
            if are_match:
                rewritten = f"{brand_name} is {are_match.group(1).strip()}"
                changes.append("replaced \"We are\" with the company name")

        without_our = re.sub(r"\b[Oo]ur\b", f"{brand_name}'s", rewritten)
        if not self._same_text(without_our, rewritten):
            rewritten = without_our
            changes.append("replaced \"our\" with the company name")

        def _we_verb(match: re.Match) -> str:
            return f"{brand_name} {self._to_third_person(match.group(1))}"

        without_we = re.sub(r"\b[Ww]e\s+([A-Za-z]+)\b", _we_verb, rewritten)
        if not self._same_text(without_we, rewritten):
            rewritten = without_we
            changes.append("replaced remaining \"we\" with the company name")

        slogan = re.match(
            r"^(?:Boost|Grow|Discover|Unlock|Transform)\b.+?\bwith\s+(.+?)\.?$",
            rewritten,
            flags=re.I,
        )
        if slogan:
            offer = re.sub(r"\b(your|you)\b", "", slogan.group(1), flags=re.I)
            offer = re.sub(r"\s{2,}", " ", offer).strip(" .")
            if offer:
                rewritten = f"{brand_name} offers {offer}."
                changes.append("turned the second-person slogan into a statement of the offer")

        if brand_name.lower() not in rewritten.lower() and "?" not in rewritten and not re.match(r"^[\d(]", rewritten):
            body = rewritten[0].lower() + rewritten[1:] if rewritten else rewritten
            rewritten = f"{brand_name} offers {body}"
            changes.append("named the company as the subject of an unnamed offer")

        rewritten = re.sub(r"\s{2,}", " ", rewritten).strip()
        if not changes or self._same_text(rewritten, text):
            return None, None
        return rewritten, "Changed the crawled sentence: " + "; ".join(changes) + "."

    def analyze(
        self,
        pages: List[PageEvidence],
        brand_name: str = ""
    ) -> CitationPassageAnalysisResult:
        brand = brand_name or self.brand_name or "The Company"
        paragraphs = self._extract_paragraphs(pages)

        passages: List[CitationPassage] = []
        rewrites: List[CitationRewriteItem] = []

        passage_idx = 1
        for url, raw_text in paragraphs:
            clarity, attribution, info_gain, factuality, tier, detected_subj, fluff_found, factual_anchors = self._score_passage(raw_text, brand)
            total = clarity + attribution + info_gain + factuality

            pid = f"PASS-{passage_idx:03d}"
            passage_idx += 1

            needs_rewrite = (tier in ["PARTIALLY_CITABLE", "WEAK"]) or (detected_subj == "generic_we") or (len(fluff_found) > 0)
            rec_text = None
            rec_why = None

            if needs_rewrite:
                rec_text, rec_why = self._generate_rewrite(raw_text, brand, fluff_found, detected_subj)
                if rec_text and rec_why:
                    rescored = sum(self._score_passage(rec_text, brand)[:4])
                    rewrites.append(CitationRewriteItem(
                        passage_id=pid,
                        source_url=url,
                        current_passage=raw_text[:280],
                        recommended_rewrite=rec_text[:280],
                        why=rec_why,
                        estimated_score_improvement=f"{total:.0f} → {min(100, round(rescored)):.0f}/100",
                    ))
                else:
                    rec_text, rec_why = None, None
                    needs_rewrite = False

            passages.append(CitationPassage(
                passage_id=pid,
                source_url=url,
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

        summary = (
            f"Scanned {len(passages)} passages across crawled pages. "
            f"{highly_citable} are highly citation-ready ({round(highly_citable/len(passages)*100)}%), "
            f"{partially_citable} partially citation-ready, and {weak} weak or fluff-heavy. "
            f"Generated {len(rewrites)} high-impact passage rewrites to boost AI search quotation."
        )

        return CitationPassageAnalysisResult(
            total_passages_scanned=len(passages),
            highly_citable_count=highly_citable,
            partially_citable_count=partially_citable,
            weak_count=weak,
            citation_readiness_score=round(avg_score, 1),
            passages=passages,
            rewrite_recommendations=rewrites,
            summary=summary,
        )


passage_analyzer = CitationPassageAnalyzer()
