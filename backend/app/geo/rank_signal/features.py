"""
Rank Signal 15-Signal Feature Catalog (S00-S14), detectors, code transforms,
passage chunking, and pre-judge pair validation guardrails.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Literal, Optional, Tuple

CATALOG_VERSION = 2

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_YEAR_RE = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?(?:19|20)\d{2}\b",
    re.I,
)

NUMBER_WITH_UNIT_RE = re.compile(
    r"[$€£¥₹]\s?\d|\b\d[\d,.]*\s?(?:%|percent\b|per ?cent\b|x\b|times\b|million\b|billion\b|"
    r"thousand\b|k\b|bn\b|kg\b|g\b|lbs?\b|oz\b|km\b|miles?\b|minutes?\b|mins?\b|hours?\b|hrs?\b|"
    r"days?\b|weeks?\b|months?\b|years?\b|seconds?\b|ms\b|[kmgt]b\b|usd\b|eur\b|inr\b|users?\b|customers?\b)",
    re.I,
)

ATTRIBUTION_RE = re.compile(
    r"(?:[Aa]ccording to|[Aa]s reported by|[Rr]eported by|[Dd]ata from|[Rr]esearch (?:by|from)|"
    r"(?:[Ss]tudy|[Ss]urvey|[Rr]eport|[Aa]nalysis) (?:by|from)|[Pp]ublished by)\s+(?:the |a |an )?[A-Z0-9]"
)

HEDGES_RE = re.compile(
    r"\b(?:may(?!\s+\d)|might|possibly|perhaps|probably|likely|arguably|potentially|"
    r"seemingly|appears to|seems to|could be|tends to)\b",
    re.I,
)

SUPERLATIVES = (
    "best-in-class", "world-class", "unbeatable", "unparalleled", "unmatched",
    "revolutionary", "game-changing", "cutting-edge", "industry-leading", "ultimate",
    "incredible", "amazing", "outstanding", "exceptional", "the best",
    "number one", "top-rated", "must-have", "premier", "second to none",
)

LOWERCASE_OK = frozenset(
    "the a an this that these those it its there most many some all each every "
    "our we you your if when while in on for with to by at as after before since although because".split()
)

STOP_WORDS = frozenset(
    "the a an and or for of to in on is are was were be what which how why who when where with by from at as".split()
)

ECHO_RE = re.compile(
    r"(smallest edit|word-for-word|\"with\"|\"without\"|\bpassage [ab]\b|^\s*(?:here is|here's|sure[,!]))",
    re.I,
)


@dataclass
class SignalContext:
    keyword: str
    now: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.now is None:
            self.now = datetime.now(timezone.utc)


@dataclass(frozen=True)
class SignalChecks:
    detector: bool = True
    length_ratio: Tuple[float, float] = (0.85, 1.18)
    similarity: Optional[float] = 0.80
    single_sentence_edit: bool = False


@dataclass(frozen=True)
class SignalDef:
    id: str
    name: str
    build: Literal["code", "llm"]
    add_only: bool
    detector_kind: Literal["none", "llm", "pair", "code"]
    feature: str
    checks: SignalChecks
    expected: Literal["+", "-", "?"]
    detect: Optional[Callable[[str, SignalContext], bool]] = None
    transform: Optional[Callable[[str, SignalContext], Optional[str]]] = None
    skip: Optional[Callable[[str, SignalContext], bool]] = None
    note: str = ""


@dataclass(frozen=True)
class Passage:
    hash: str
    origin: str  # "target" | "competitor"
    url: str
    text: str


def word_tokens(text: str) -> List[str]:
    return [w.replace("’", "'") for w in re.findall(r"[a-z0-9]+(?:['’][a-z]+)*", text.lower())]


def count_words(text: str) -> int:
    return len(text.split())


def normalize_for_hash(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def query_terms(keyword: str) -> List[str]:
    return [w for w in word_tokens(keyword) if len(w) > 2 and w not in STOP_WORDS]


def word_similarity(a: str, b: str) -> float:
    x = word_tokens(a)
    y = word_tokens(b)
    mx = max(len(x), len(y))
    if mx == 0:
        return 1.0
    prev = list(range(len(y) + 1))
    for i, xi in enumerate(x, 1):
        cur = [i]
        for j, yj in enumerate(y, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (0 if xi == yj else 1)))
        prev = cur
    return 1.0 - (prev[-1] / mx)


def is_list_shaped(text: str) -> bool:
    return len([l for l in text.splitlines() if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\S", l)]) >= 2


def _first_line(text: str) -> str:
    return text.lstrip().split("\n", 1)[0]


def _question_from_keyword(keyword: str) -> str:
    k = re.sub(r"[?.!]+$", "", keyword.strip())
    if not k:
        return "What is this?"
    cap = k[0].upper() + k[1:]
    if re.match(r"^(?:what|how|why|which|who|when|where|is|are|can|does|do|should|will)\b", k, re.I):
        return f"{cap}?"
    if re.match(r"^(?:best|top|cheapest|most|fastest|easiest|leading)\b", k, re.I):
        return f"What is the {k}?"
    return f"What is {k}?"


# ── Detectors ────────────────────────────────────────────────────────────────

def has_number(text: str) -> bool:
    return bool(NUMBER_WITH_UNIT_RE.search(text))


def has_attribution(text: str) -> bool:
    return bool(ATTRIBUTION_RE.search(text))


def has_first_person(text: str) -> bool:
    return bool(re.search(r"\b(?:we|our)\b", text, re.I) or re.search(r"\bI\b", text))


def hedge_count(text: str) -> int:
    return len(HEDGES_RE.findall(text))


def has_superlative(text: str, keyword: str) -> bool:
    q_set = set(query_terms(keyword))
    for sup in SUPERLATIVES:
        if any(w in q_set for w in word_tokens(sup)):
            continue
        if re.search(rf"(?<![\w]){re.escape(sup)}(?![\w])", text, re.I):
            return True
    return False


def has_definition(text: str, keyword: str) -> bool:
    kw = r"\s+".join(re.escape(p) for p in keyword.strip().split())
    if not kw:
        return False
    return bool(re.search(rf"(?<!\w){kw}s?\s+(?:is|are|refers to|means)\s+(?:a|an|the)\b", text, re.I))


def has_exact_query(text: str, keyword: str) -> bool:
    norm_t = " " + re.sub(r"[^\w]+", " ", text.lower()).strip() + " "
    norm_k = " " + re.sub(r"[^\w]+", " ", keyword.lower()).strip() + " "
    return norm_k.strip() != "" and norm_k in norm_t


def has_bullet_list(text: str) -> bool:
    return len([l for l in text.splitlines() if re.match(r"^\s*-\s+\S", l)]) >= 2


def has_freshness_clause(text: str) -> bool:
    return bool(re.match(r"^\s*As of [A-Z][a-z]+ \d{4},", text))


def has_question_heading(text: str) -> bool:
    return bool(re.match(r"^#{1,6}\s+.+\?\s*$", _first_line(text).strip()))


def has_bold_query_term(text: str, keyword: str) -> bool:
    terms = query_terms(keyword)
    for m in re.finditer(r"\*\*([^*]+)\*\*", text):
        chunk = m.group(1)
        if any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", chunk, re.I) for t in terms):
            return True
    return False


# ── Deterministic Code Transforms ($0 LLM rewrite cost) ──────────────────────

def to_bullet_list(text: str) -> Optional[str]:
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return None
    return "\n".join(f"- {s}" for s in sentences)


def add_freshness_clause(text: str, now: datetime) -> Optional[str]:
    body = text.lstrip()
    if re.match(r"^(?:[-*+]|\d+[.)])\s", body):
        return None
    m = re.match(r"^[A-Za-z']+", body)
    first_word = m.group(0) if m else ""
    lead = (body[0].lower() + body[1:]) if (first_word.lower() in LOWERCASE_OK and body) else body
    return f"As of {MONTHS[now.month - 1]} {now.year}, {lead}"


def add_question_heading(text: str, keyword: str) -> str:
    return f"## {_question_from_keyword(keyword)}\n\n{text.lstrip()}"


def bold_query_terms(text: str, keyword: str) -> Optional[str]:
    out = text
    for term in query_terms(keyword):
        out = re.sub(rf"(?<!\w)({re.escape(term)})(?!\w)", r"**\1**", out, flags=re.I)
    if out == text:
        return None
    return re.sub(r"\*\*([ \t]+)\*\*", r"\1", out)


# ── Frozen 15-Signal Catalog ─────────────────────────────────────────────────

DEFAULT_CHECKS = SignalChecks()

FEATURE_CATALOG: List[SignalDef] = [
    SignalDef(
        id="S00",
        name="Placebo: one sentence paraphrased",
        build="llm",
        add_only=True,
        detector_kind="none",
        feature="one existing sentence reworded with identical facts, meaning, and length",
        checks=SignalChecks(detector=False, length_ratio=(0.90, 1.10), similarity=0.80, single_sentence_edit=True),
        expected="?",
        note="Calibration: measures judge reaction to being edited at all.",
    ),
    SignalDef(
        id="S01",
        name="Leads with a direct answer",
        build="llm",
        add_only=False,
        detector_kind="llm",
        feature="the passage opens with a sentence that directly answers the query",
        checks=SignalChecks(detector=False),
        expected="+",
    ),
    SignalDef(
        id="S02",
        name="Contains a specific number or statistic",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, _c: has_number(t),
        feature='at least one specific number with a unit or percentage (e.g. "42%", "15 minutes", "$9.99")',
        checks=DEFAULT_CHECKS,
        expected="+",
    ),
    SignalDef(
        id="S03",
        name="Names the entity explicitly",
        build="llm",
        add_only=False,
        detector_kind="llm",
        feature="the subject entity is named explicitly instead of using a pronoun (it, they, this)",
        checks=SignalChecks(detector=False),
        expected="+",
    ),
    SignalDef(
        id="S04",
        name="Cites a named source",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, _c: has_attribution(t),
        feature='a claim attributed to a named source with "according to ..." or similar attribution',
        checks=DEFAULT_CHECKS,
        expected="+",
    ),
    SignalDef(
        id="S05",
        name="List format",
        build="code",
        add_only=True,
        detector_kind="code",
        detect=lambda t, _c: has_bullet_list(t),
        transform=lambda t, _c: to_bullet_list(t),
        skip=lambda t, _c: is_list_shaped(t),
        feature='the sentences formatted as "- " bullet points',
        checks=SignalChecks(detector=True, length_ratio=(0.85, 1.18), similarity=None),
        expected="+",
    ),
    SignalDef(
        id="S06",
        name='Freshness clause ("As of Month YYYY")',
        build="code",
        add_only=True,
        detector_kind="code",
        detect=lambda t, _c: has_freshness_clause(t),
        transform=lambda t, c: add_freshness_clause(t, c.now),
        skip=lambda t, _c: bool(MONTH_YEAR_RE.search(t)),
        feature='a leading "As of {Month YYYY}," freshness clause',
        checks=DEFAULT_CHECKS,
        expected="+",
    ),
    SignalDef(
        id="S07",
        name="First-person experience",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, _c: has_first_person(t),
        feature='a first-person experience statement such as "We tested ..." or "In our experience ..."',
        checks=DEFAULT_CHECKS,
        expected="?",
    ),
    SignalDef(
        id="S08",
        name="Hedging language",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, _c: hedge_count(t) >= 2,
        feature="hedging language (may, might, possibly, perhaps) used at least twice",
        checks=DEFAULT_CHECKS,
        expected="-",
    ),
    SignalDef(
        id="S09",
        name="Promotional superlatives",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, c: has_superlative(t, c.keyword),
        feature='promotional superlatives such as "best-in-class", "unbeatable" or "world-class"',
        checks=DEFAULT_CHECKS,
        expected="-",
    ),
    SignalDef(
        id="S10",
        name="Definition sentence",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, c: has_definition(t, c.keyword),
        feature='a definition sentence of the form "{keyword} is a ..."',
        checks=DEFAULT_CHECKS,
        expected="+",
    ),
    SignalDef(
        id="S11",
        name="Exact query phrase present",
        build="llm",
        add_only=False,
        detector_kind="code",
        detect=lambda t, c: has_exact_query(t, c.keyword),
        feature='the exact query phrase "{keyword}"',
        checks=DEFAULT_CHECKS,
        expected="?",
    ),
    SignalDef(
        id="S12",
        name="Question heading from the query",
        build="code",
        add_only=True,
        detector_kind="code",
        detect=lambda t, _c: has_question_heading(t),
        transform=lambda t, c: add_question_heading(t, c.keyword),
        skip=lambda t, _c: bool(re.match(r"^#{1,6}\s", _first_line(t).strip())),
        feature='a leading "## {Question}?" heading built from the query',
        checks=DEFAULT_CHECKS,
        expected="?",
    ),
    SignalDef(
        id="S13",
        name="Bold query terms",
        build="code",
        add_only=True,
        detector_kind="code",
        detect=lambda t, c: has_bold_query_term(t, c.keyword),
        transform=lambda t, c: bold_query_terms(t, c.keyword),
        skip=lambda t, _c: bool(re.search(r"\*\*[^*]+\*\*|__[^_]+__", t)),
        feature="the query terms in **bold**",
        checks=DEFAULT_CHECKS,
        expected="?",
    ),
    SignalDef(
        id="S14",
        name="Concise (about 40% shorter)",
        build="llm",
        add_only=True,
        detector_kind="pair",
        feature="the same passage about 40% shorter, keeping every fact and dropping filler",
        checks=SignalChecks(detector=False, length_ratio=(0.50, 0.75), similarity=None),
        expected="?",
    ),
]

# Run cheap code-built signals first (zero rewrite cost), then S00 placebo, then LLM signals.
RUN_ORDER: List[str] = (
    [s.id for s in FEATURE_CATALOG if s.build == "code"]
    + ["S00"]
    + [s.id for s in FEATURE_CATALOG if s.build == "llm" and s.id != "S00"]
)


def get_signal(signal_id: str) -> Optional[SignalDef]:
    sid = (signal_id or "").strip().upper()
    return next((s for s in FEATURE_CATALOG if s.id == sid), None)


def is_eligible(signal: SignalDef, text: str, ctx: SignalContext) -> bool:
    if signal.build != "code":
        return True
    if signal.skip and signal.skip(text, ctx):
        return False
    if signal.detect and signal.detect(text, ctx):
        return False
    return signal.transform is not None and signal.transform(text, ctx) is not None


def check_pair(signal: SignalDef, with_text: str, without_text: str, ctx: SignalContext) -> Tuple[bool, str]:
    w = (with_text or "").strip()
    wo = (without_text or "").strip()
    if not w or not wo:
        return False, "empty side"
    if ECHO_RE.search(w) or ECHO_RE.search(wo):
        return False, "echoes instructions"
    if normalize_for_hash(w) == normalize_for_hash(wo):
        return False, "identical sides"
    if signal.build == "llm" and word_tokens(w) == word_tokens(wo):
        return False, "identical words"

    if signal.checks.single_sentence_edit:
        sa = split_sentences(w)
        sb = split_sentences(wo)
        changed = sum(1 for i, s in enumerate(sa) if word_tokens(s) != word_tokens(sb[i] if i < len(sb) else ""))
        if len(sa) != len(sb) or changed != 1:
            return False, f"{changed} sentences changed"

    if signal.checks.detector and signal.detect:
        if not signal.detect(w, ctx):
            return False, "feature missing from with"
        if signal.detect(wo, ctx):
            return False, "feature present in without"

    ratio = count_words(w) / max(1, count_words(wo))
    lo, hi = signal.checks.length_ratio
    if ratio < lo or ratio > hi:
        return False, f"length ratio {ratio:.2f}"

    if signal.checks.similarity is not None:
        sim = word_similarity(w, wo)
        if sim < signal.checks.similarity:
            return False, f"similarity {sim:.2f}"

    return True, "ok"


def extract_passages(
    texts: List[Tuple[str, str, str]],
    *,
    keyword: str = "",
    min_words: int = 35,
    max_words: int = 120,
    limit: int = 60,
) -> List[Passage]:
    """Chunk (origin, url, plain_text) tuples into deduplicated, query-ranked passages."""
    seen: set[str] = set()
    raw_passages: List[Passage] = []
    for origin, url, body in texts:
        sentences = split_sentences(re.sub(r"\s+", " ", body or "").strip())
        buf: List[str] = []
        wc = 0
        for s in sentences:
            sw = count_words(s)
            if wc + sw > max_words and buf:
                chunk = " ".join(buf)
                if count_words(chunk) >= min_words:
                    h = hashlib.sha256(normalize_for_hash(chunk).encode("utf-8")).hexdigest()[:16]
                    if h not in seen:
                        seen.add(h)
                        raw_passages.append(Passage(hash=h, origin=origin, url=url, text=chunk))
                buf = [s]
                wc = sw
            else:
                buf.append(s)
                wc += sw
        if buf:
            chunk = " ".join(buf)
            if count_words(chunk) >= min_words:
                h = hashlib.sha256(normalize_for_hash(chunk).encode("utf-8")).hexdigest()[:16]
                if h not in seen:
                    seen.add(h)
                    raw_passages.append(Passage(hash=h, origin=origin, url=url, text=chunk))

    q_terms = set(query_terms(keyword))
    if q_terms:
        raw_passages.sort(
            key=lambda p: (sum(1 for t in q_terms if t in set(word_tokens(p.text))), p.origin == "target"),
            reverse=True,
        )
    return raw_passages[:limit]
