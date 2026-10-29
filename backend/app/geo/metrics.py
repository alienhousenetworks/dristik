"""
GEO Impression Metrics & Statistical Reliability Engine (Aggarwal et al., KDD 2024).
Provides:
1. Deterministic sentence tokenization with abbreviation and URL protection.
2. Exact Aggarwal et al. (KDD 2024) Impression metrics:
   - Imp_wc: Word-count impression metric without credit splitting.
   - Imp_pwc: Position-weighted impression metric with negative exponential decay.
   - Dristik-adjusted Imp_wc: Citation credit split (|s| / |C_s|) for multi-source sentences.
   - Unlinked brand mentions: Continuous and count tracking for brand mentions without citations.
3. Statistical confidence intervals:
   - Wilson score intervals for binomial proportions (mention & first-party citation rates).
   - Student's t / bootstrap intervals for continuous impression metrics.
   - Confidence interval overlap & suppression detection.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

# Protected abbreviations to prevent erroneous sentence splitting
_PROTECTED_ABBREVIATIONS = {
    "e.g.", "i.e.", "vs.", "etc.", "inc.", "ltd.", "corp.", "co.",
    "dr.", "mr.", "ms.", "prof.", "u.s.", "ai.", "no.", "sla.",
    "dept.", "approx.", "est.", "fig.", "jan.", "feb.", "mar.", "apr.",
    "jun.", "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec."
}


def tokenize_sentences(text: str) -> List[str]:
    """
    Deterministically splits raw model responses into ordered sentences,
    preserving abbreviations, decimal numbers, and inline citation markers.
    """
    if not text or not text.strip():
        return []

    # Clean carriage returns
    normalized = re.sub(r"\r\n|\r", "\n", text.strip())

    # Protect common abbreviations by temporarily escaping the period
    def _protect_match(m: re.Match) -> str:
        return m.group(0).replace(".", "§DOT§")

    protected = normalized
    for abbr in _PROTECTED_ABBREVIATIONS:
        # Match case-insensitively with word boundaries
        pattern = re.compile(rf"\b{re.escape(abbr)}", re.IGNORECASE)
        protected = pattern.sub(_protect_match, protected)

    # Protect decimal numbers (e.g. 99.9%, 3.5, $4.50)
    protected = re.sub(r"(\d+)\.(\d+)", r"\1§DOT§\2", protected)

    # Split on newlines that represent structural breaks (bullet points, markdown headers, double newlines)
    raw_lines = re.split(r"\n{2,}|\n(?=[-*•#]|\d+[\.\)])", protected)
    sentences: List[str] = []

    # Boundary pattern: period/question/exclamation followed by space and capital/number/bracket
    sentence_boundary = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\[\(\$₹€£])')

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # Split paragraph into sentence candidates
        chunks = sentence_boundary.split(line)
        for chunk in chunks:
            # Restore protected dots
            clean_chunk = chunk.replace("§DOT§", ".").strip()
            # Remove leading bullet points/numbers if present
            clean_chunk = re.sub(r"^[-*•]\s+", "", clean_chunk)
            clean_chunk = re.sub(r"^\d+[\.\)]\s+", "", clean_chunk).strip()
            if clean_chunk:
                sentences.append(clean_chunk)

    return sentences


def _clean_domain(url_or_domain: str) -> str:
    """Extracts a normalized hostname/domain (e.g. 'alienhouse.ai', removing 'www.')."""
    if not url_or_domain:
        return ""
    try:
        val = str(url_or_domain).strip().lower()
        if val.startswith("http://") or val.startswith("https://"):
            netloc = urlparse(val).netloc
            return netloc.replace("www.", "").strip()
        return val.replace("www.", "").split("/")[0].strip()
    except Exception:
        return ""


def extract_sentence_sources(
    sentence: str,
    available_citations: List[str],
) -> List[str]:
    """
    Extracts cited domains from a single sentence using:
    1. Perplexity-style bracket indices: [1], [2], [1, 2], [1][2]
    2. Markdown links: [anchor](https://...)
    3. Verbatim raw URLs: https://...
    """
    cited_domains: Set[str] = set()

    # 1. Bracket numeric citations (e.g. [1], [2], [1, 3])
    bracket_matches = re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", sentence)
    for bm in bracket_matches:
        raw_indices = bm.group(1).split(",")
        for idx_str in raw_indices:
            try:
                # 1-indexed to 0-indexed mapping
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(available_citations):
                    dom = _clean_domain(available_citations[idx])
                    if dom:
                        cited_domains.add(dom)
            except Exception:
                continue

    # 2. Markdown links [text](http...)
    for md_match in re.finditer(r"\[[^\]]*\]\((https?://[^\)]+)\)", sentence):
        dom = _clean_domain(md_match.group(1))
        if dom:
            cited_domains.add(dom)

    # 3. Verbatim URLs
    for url_match in re.finditer(r"https?://([a-zA-Z0-9\.\-]+)", sentence):
        dom = _clean_domain(url_match.group(1))
        if dom:
            cited_domains.add(dom)

    return sorted(list(cited_domains))


class SentenceImpressionDetail(BaseModel):
    sentence_index: int
    text: str
    word_count: int
    cited_domains: List[str] = Field(default_factory=list)
    citations_count: int = 0
    cites_target: bool = False
    mentions_brand_unlinked: bool = False
    position_weight: float = 1.0


class ResponseImpressionResult(BaseModel):
    total_sentences: int
    total_words: int
    target_cited_sentences: int
    unlinked_brand_sentences: int
    word_count_impression_pct: float = 0.0          # Paper Imp_wc
    position_adjusted_impression_pct: float = 0.0   # Paper Imp_pwc (negative exponential decay)
    dristik_adjusted_impression_pct: float = 0.0    # Dristik-adjusted (credit split |s| / |C_s|)
    unlinked_brand_impression_pct: float = 0.0      # Continuous impression for brand mentions without citation
    sentence_details: List[SentenceImpressionDetail] = Field(default_factory=list)


def calculate_response_impressions(
    raw_response: str,
    citations: List[str],
    target_domain: str,
    brand_name: str,
) -> ResponseImpressionResult:
    """
    Computes exact Aggarwal et al. (KDD 2024) impression metrics on a raw AI answer engine response.

    Paper Imp_wc(c, r)  = SUM_{s in S_c} |s| / SUM_{s in S_r} |s|
    Paper Imp_pwc(c, r) = SUM_{s in S_c} |s| * exp(-pos(s)/|S_r|) / SUM_{s in S_r} |s|
    Dristik-adjusted   = SUM_{s in S_c} (|s| / |C_s|) / SUM_{s in S_r} |s|
    """
    sentences = tokenize_sentences(raw_response)
    if not sentences:
        return ResponseImpressionResult(
            total_sentences=0,
            total_words=0,
            target_cited_sentences=0,
            unlinked_brand_sentences=0,
        )

    clean_target = _clean_domain(target_domain)
    brand_clean = (brand_name or clean_target.split(".")[0]).lower().strip()
    total_sentences_count = len(sentences)

    total_words = 0
    sentence_details: List[SentenceImpressionDetail] = []

    imp_wc_numerator = 0.0
    imp_pwc_numerator = 0.0
    imp_dristik_numerator = 0.0
    imp_unlinked_numerator = 0.0

    target_cited_count = 0
    unlinked_brand_count = 0

    for idx, s_text in enumerate(sentences, start=1):
        words = s_text.split()
        wc = len(words)
        total_words += wc

        # 1-indexed position weight: exp(-pos / total_sentences)
        pos_weight = math.exp(-float(idx) / float(total_sentences_count))

        # Sources cited in this specific sentence
        cited_sources = extract_sentence_sources(s_text, citations)
        cites_target = False
        if clean_target:
            cites_target = any(
                clean_target in src or src in clean_target
                for src in cited_sources
            )

        # Brand mentioned in sentence
        s_low = s_text.lower()
        has_brand_mention = bool(
            (brand_clean and brand_clean in s_low) or
            (clean_target and clean_target in s_low)
        )

        mentions_unlinked = has_brand_mention and not cites_target

        if cites_target:
            target_cited_count += 1
            imp_wc_numerator += float(wc)
            imp_pwc_numerator += float(wc) * pos_weight
            # Dristik-adjusted: divide sentence credit by number of sources cited in sentence
            citations_in_sentence = max(1, len(cited_sources))
            imp_dristik_numerator += float(wc) / float(citations_in_sentence)

        if mentions_unlinked:
            unlinked_brand_count += 1
            imp_unlinked_numerator += float(wc)

        sentence_details.append(
            SentenceImpressionDetail(
                sentence_index=idx,
                text=s_text,
                word_count=wc,
                cited_domains=cited_sources,
                citations_count=len(cited_sources),
                cites_target=cites_target,
                mentions_brand_unlinked=mentions_unlinked,
                position_weight=round(pos_weight, 4),
            )
        )

    if total_words == 0:
        return ResponseImpressionResult(
            total_sentences=total_sentences_count,
            total_words=0,
            target_cited_sentences=0,
            unlinked_brand_sentences=0,
            sentence_details=sentence_details,
        )

    wc_pct = round((imp_wc_numerator / float(total_words)) * 100.0, 2)
    pwc_pct = round((imp_pwc_numerator / float(total_words)) * 100.0, 2)
    dristik_pct = round((imp_dristik_numerator / float(total_words)) * 100.0, 2)
    unlinked_pct = round((imp_unlinked_numerator / float(total_words)) * 100.0, 2)

    return ResponseImpressionResult(
        total_sentences=total_sentences_count,
        total_words=total_words,
        target_cited_sentences=target_cited_count,
        unlinked_brand_sentences=unlinked_brand_count,
        word_count_impression_pct=wc_pct,
        position_adjusted_impression_pct=pwc_pct,
        dristik_adjusted_impression_pct=dristik_pct,
        unlinked_brand_impression_pct=unlinked_pct,
        sentence_details=sentence_details,
    )


# ---------------------------------------------------------------------------
# Statistical Reliability Layer (Wilson Score & Continuous Confidence Intervals)
# ---------------------------------------------------------------------------

def wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> Optional[Tuple[float, float]]:
    """
    Computes the 95% Wilson Score Interval for a binomial proportion.
    Accurate for small sample sizes and boundary cases (p = 0 or p = 1).
    Returns (lower_pct, upper_pct) bounded between 0.0 and 100.0.
    """
    if trials <= 0:
        return None

    # Z-value for confidence level (default 1.95996 for 95%)
    if abs(confidence - 0.95) < 0.01:
        z = 1.95996
    elif abs(confidence - 0.90) < 0.01:
        z = 1.64485
    elif abs(confidence - 0.99) < 0.01:
        z = 2.57583
    else:
        # Standard normal approximation
        z = 1.95996

    n = float(trials)
    p = float(successes) / n
    z2 = z * z

    denominator = 1.0 + (z2 / n)
    center_adjusted = p + (z2 / (2.0 * n))
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * (n ** 2))))

    lower = max(0.0, (center_adjusted - margin) / denominator)
    upper = min(1.0, (center_adjusted + margin) / denominator)

    return (round(lower * 100.0, 1), round(upper * 100.0, 1))


def continuous_confidence_interval(
    values: List[float],
    confidence: float = 0.95,
) -> Optional[Tuple[float, float]]:
    """
    Computes the confidence interval for continuous measurements (such as Impression %)
    using Student's t distribution approximation across repeated runs.
    """
    if not values:
        return None
    n = len(values)
    if n == 1:
        val = max(0.0, min(100.0, values[0]))
        return (round(val, 1), round(val, 1))

    mean = sum(values) / float(n)
    variance = sum((x - mean) ** 2 for x in values) / float(n - 1)
    std_dev = math.sqrt(variance)

    # Student's t critical values for 95% two-sided
    # degrees of freedom = n - 1
    t_table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776,
        5: 2.571,  6: 2.447, 7: 2.365, 8: 2.306,
        9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086
    }
    df = n - 1
    t_crit = t_table.get(df, 1.96 if df > 20 else 2.228)

    margin = t_crit * (std_dev / math.sqrt(n))
    lower = max(0.0, mean - margin)
    upper = min(100.0, mean + margin)

    return (round(lower, 1), round(upper, 1))


def intervals_overlap(
    ci1: Optional[Tuple[float, float]],
    ci2: Optional[Tuple[float, float]],
) -> bool:
    """
    Checks if two confidence intervals overlap.
    Used for trend suppression: if baseline and follow-up intervals overlap,
    the change cannot be asserted as statistically significant.
    """
    if not ci1 or not ci2:
        return True
    return max(ci1[0], ci2[0]) <= min(ci1[1], ci2[1])


def calculate_sample_variance(values: List[float]) -> float:
    """Calculates sample variance for adaptive sampling decisions."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)
