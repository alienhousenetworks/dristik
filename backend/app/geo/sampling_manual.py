"""
Consumer AI / Manual Sampling, Provenance Grading & Persistent Human Overrides.

Adapted from GeoLook's MIT-licensed `scripts/sample.py` into Dristik's enterprise
GEO evidence model:
- Strict session provenance grading (`sandbox`/`incognito`/`clean_profile` -> Grade A;
  `personal` -> Grade D `needs_review`)
- Cross-script CJK/Latin boundary alias matching + sentence-level negation guard
- Brand-in-question quarantine (branded probes never inflate unprompted visibility)
- Brand-proximity negative-cue window (`-80/+160` chars) routing to human review
- Markdown manual sampling sheet export & import + browser capture import
- Immutable `automated_result` preserved alongside persistent `manual_override`
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field


SESSION_MODES: Dict[str, Tuple[str, str]] = {
    "sandbox": ("Disposable clean browser sandbox (no cookies/history)", "A_VERIFIED_CLEAN"),
    "incognito": ("Incognito / logged-out session", "A_VERIFIED_CLEAN"),
    "clean_profile": ("Dedicated clean sampling profile (personalization disabled)", "A_VERIFIED_CLEAN"),
    "personal": ("Personal everyday account (personalization risk — review required)", "D_NEEDS_REVIEW"),
}

_LATIN_RE = re.compile(r"[A-Za-z0-9]")
_NEG_RE = re.compile(r"\b(?:not|isn't|aren't|never|avoid)\b|不是|并非|不属于|不同于", re.I)
_SENT_END = ".!?\n。！？"
_URL_RE = re.compile(r"https?://[^\s\)\]\"'，。；]+")
_NEG_CUES = re.compile(
    r"\b(?:not recommended|avoid|scam|complaints?|lawsuit|shut ?down|worse than|downsides?|overpriced)\b|"
    r"不推荐|避雷|缺点|劣势|投诉|差评|跑路|骗局|不靠谱|慎用|翻车",
    re.I,
)


class ManualSampleAnalysis(BaseModel):
    brand_mentioned: bool = False
    brand_rank: int = 0
    candidates: List[str] = Field(default_factory=list)
    competitors_mentioned: List[str] = Field(default_factory=list)
    cited_domains: List[str] = Field(default_factory=list)
    own_domain_cited: Optional[bool] = None  # None when off-site-only (no website)
    answer_chars: int = 0
    needs_review: bool = False
    negative_cues: List[str] = Field(default_factory=list)


class ManualOverrideRecord(BaseModel):
    brand_mentioned: Optional[bool] = None
    brand_rank: Optional[int] = None
    competitors_mentioned: Optional[List[str]] = None
    evidence_grade: Optional[str] = None
    reviewer_id: str
    review_note: str = ""
    reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConsumerAISample(BaseModel):
    sample_id: str = Field(default_factory=lambda: f"smp_{uuid.uuid4().hex[:12]}")
    tenant_id: str = "default"
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    platform: str
    surface: str = "consumer_ui"  # consumer_ui | manual_sheet | api
    execution_method: str = "manual"  # manual | browser_extension | api
    session_mode: str = "incognito"
    session_label: str = SESSION_MODES["incognito"][0]
    evidence_grade: str = SESSION_MODES["incognito"][1]
    market: str = "global"
    locale: str = "en-US"
    question_id: str
    question_text: str
    brand_in_question: bool = False
    answer_text: str
    citations: List[Dict[str, str]] = Field(default_factory=list)
    automated_result: ManualSampleAnalysis
    manual_override: Optional[ManualOverrideRecord] = None
    needs_review: bool = False

    def effective_analysis(self) -> ManualSampleAnalysis:
        """Return automated analysis overlaid with any persistent human override."""
        base = self.automated_result.model_copy(deep=True)
        if self.manual_override:
            ov = self.manual_override
            if ov.brand_mentioned is not None:
                base.brand_mentioned = ov.brand_mentioned
            if ov.brand_rank is not None:
                base.brand_rank = ov.brand_rank
            if ov.competitors_mentioned is not None:
                base.competitors_mentioned = list(ov.competitors_mentioned)
        return base


def alias_spans(text: str, alias: str) -> List[Tuple[int, int]]:
    """Cross-script boundary matcher: guards Latin-to-Latin continuation without breaking CJK adjacency."""
    if not alias:
        return []
    left = r"(?<![A-Za-z0-9])" if _LATIN_RE.match(alias[0]) else ""
    right = r"(?![A-Za-z0-9])" if _LATIN_RE.match(alias[-1]) else ""
    flags = re.I if (left or right) else 0
    return [m.span() for m in re.finditer(left + re.escape(alias) + right, text, flags)]


def _sentence_at(text: str, pos: int) -> str:
    start = max([text.rfind(c, 0, pos) for c in _SENT_END] + [-1]) + 1
    ends = [text.find(c, pos) + 1 for c in _SENT_END if text.find(c, pos) != -1]
    return text[start: min(ends) if ends else len(text)]


def entity_hit(text: str, aliases: Sequence[str]) -> Tuple[int, bool]:
    """Return `(first_valid_position_or_-1, had_negated_hit_needing_review)`."""
    hits = sorted((s, e) for a in aliases if a for s, e in alias_spans(text, a))
    valid: List[int] = []
    negated = False
    for s, _ in hits:
        if _NEG_RE.search(_sentence_at(text, s)):
            negated = True
        else:
            valid.append(s)
    return (min(valid) if valid else -1), negated


def brand_in_question(
    question_text: str,
    brand_name: str,
    brand_aliases: Sequence[str] = (),
    own_domain: str = "",
) -> bool:
    """True when the prompt itself names the brand (must be quarantined from unprompted visibility)."""
    q_low = (question_text or "").lower()
    own = (urlparse(own_domain).netloc or own_domain).lower().removeprefix("www.")
    if own and own in q_low:
        return True
    for name in [brand_name, *brand_aliases]:
        if name and name.lower() in q_low:
            return True
    return False


def analyze_manual_answer(
    *,
    answer_text: str,
    brand_name: str,
    brand_aliases: Sequence[str] = (),
    competitors: Optional[Dict[str, List[str]]] = None,
    own_domain: str = "",
    citations: Optional[Sequence[Dict[str, str]]] = None,
) -> ManualSampleAnalysis:
    """Parse brand mention, ordinal rank, competitors, citations, and negative-cue review flags."""
    entity_aliases: Dict[str, List[str]] = {brand_name: [brand_name, *list(brand_aliases)]}
    for cname, caliases in (competitors or {}).items():
        if cname and cname != brand_name:
            entity_aliases[cname] = [cname, *list(caliases or [])]

    positions: Dict[str, int] = {}
    needs_review = False
    for name, aliases in entity_aliases.items():
        pos, negated = entity_hit(answer_text, aliases)
        positions[name] = pos
        needs_review = needs_review or negated

    present = {n: p >= 0 for n, p in positions.items()}
    ordered = [n for n, p in sorted(positions.items(), key=lambda x: x[1]) if p >= 0]

    urls = list(_URL_RE.findall(answer_text))
    for c in citations or []:
        if c.get("url"):
            urls.append(str(c["url"]))

    domains: List[str] = []
    for u in urls:
        try:
            host = urlparse(u).netloc.lower().removeprefix("www.")
            if host:
                domains.append(host)
        except Exception:
            continue

    own_clean = (urlparse(own_domain).netloc or own_domain).lower().removeprefix("www.") if own_domain else ""
    own_cited: Optional[bool] = (
        any(d == own_clean or d.endswith("." + own_clean) for d in domains)
        if own_clean
        else None
    )

    neg_found: set[str] = set()
    if present.get(brand_name):
        for a in entity_aliases[brand_name]:
            for s, e in alias_spans(answer_text, a):
                window = answer_text[max(0, s - 80): e + 160]
                for m in _NEG_CUES.finditer(window):
                    neg_found.add(m.group(0).lower())

    return ManualSampleAnalysis(
        brand_mentioned=present.get(brand_name, False),
        brand_rank=(ordered.index(brand_name) + 1) if brand_name in ordered else 0,
        candidates=ordered,
        competitors_mentioned=[n for n in entity_aliases if n != brand_name and present.get(n)],
        cited_domains=sorted(set(domains)),
        own_domain_cited=own_cited,
        answer_chars=len(answer_text),
        needs_review=needs_review or bool(neg_found),
        negative_cues=sorted(neg_found),
    )


def apply_manual_override(
    sample: ConsumerAISample,
    *,
    reviewer_id: str,
    brand_mentioned: Optional[bool] = None,
    brand_rank: Optional[int] = None,
    competitors_mentioned: Optional[List[str]] = None,
    evidence_grade: Optional[str] = None,
    review_note: str = "",
) -> ConsumerAISample:
    """Attach a persistent human override without mutating `automated_result`."""
    sample.manual_override = ManualOverrideRecord(
        brand_mentioned=brand_mentioned,
        brand_rank=brand_rank,
        competitors_mentioned=competitors_mentioned,
        evidence_grade=evidence_grade,
        reviewer_id=reviewer_id,
        review_note=review_note[:500],
    )
    if evidence_grade:
        sample.evidence_grade = evidence_grade
    sample.needs_review = False
    return sample


def export_sampling_sheet(
    *,
    brand_name: str,
    platforms: Sequence[str],
    questions: Sequence[Dict[str, str]],
) -> str:
    """Export a clean Markdown manual sampling sheet with strict hygiene rules."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# {brand_name} — Manual AI Answer Sampling Sheet ({today})",
        "",
        "Hygiene rules (Grade A evidence): use clean sandbox or incognito, start a fresh chat per question, paste the full answer + citation URLs, and include answers that do NOT mention the brand.",
        "",
    ]
    for plat in platforms:
        lines.extend([f"## platform: {plat}", ""])
        for q in questions:
            qid = q.get("id", "q001")
            qtext = q.get("text", "")
            lines.extend([f"### {qid} · {qtext}", "", "```answer", "", "```", ""])
    return "\n".join(lines)


def import_sampling_sheet(
    sheet_markdown: str,
    *,
    tenant_id: str,
    brand_name: str,
    brand_aliases: Sequence[str] = (),
    competitors: Optional[Dict[str, List[str]]] = None,
    own_domain: str = "",
    session_mode: str = "incognito",
    market: str = "global",
) -> List[ConsumerAISample]:
    """Parse a filled Markdown sampling sheet into provenance-tagged `ConsumerAISample` records."""
    sm = session_mode if session_mode in SESSION_MODES else "incognito"
    sm_label, grade = SESSION_MODES[sm]
    samples: List[ConsumerAISample] = []

    blocks = re.split(r"(?m)^##\s+platform:\s*(\S+)\s*$", sheet_markdown or "")
    for i in range(1, len(blocks), 2):
        plat = blocks[i].strip()
        body = blocks[i + 1]
        for m in re.finditer(r"(?ms)^###\s+(\S+)\s*[·-]\s*(.+?)\n(.*?)```answer\n(.*?)```", body):
            qid, qtext, _, answer = m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4).strip()
            if not answer:
                continue
            analysis = analyze_manual_answer(
                answer_text=answer,
                brand_name=brand_name,
                brand_aliases=brand_aliases,
                competitors=competitors,
                own_domain=own_domain,
            )
            samples.append(
                ConsumerAISample(
                    tenant_id=tenant_id,
                    platform=plat,
                    surface="consumer_ui",
                    execution_method="manual",
                    session_mode=sm,
                    session_label=sm_label,
                    evidence_grade=grade,
                    market=market,
                    question_id=qid,
                    question_text=qtext,
                    brand_in_question=brand_in_question(qtext, brand_name, brand_aliases, own_domain),
                    answer_text=answer[:20000],
                    automated_result=analysis,
                    needs_review=analysis.needs_review or (sm == "personal"),
                )
            )
    return samples


def aggregate_manual_samples(samples: Sequence[ConsumerAISample]) -> Dict[str, Any]:
    """Aggregate consumer/manual samples per `(platform, surface)` keeping probes quarantined."""
    grouped: Dict[Tuple[str, str], List[ConsumerAISample]] = {}
    for s in samples:
        grouped.setdefault((s.platform, s.surface), []).append(s)

    by_platform: Dict[str, Dict[str, Any]] = {}
    for (plat, surface), rows in grouped.items():
        probes = [r for r in rows if r.brand_in_question]
        unprompted = [r for r in rows if not r.brand_in_question]
        n = len(unprompted)
        eff = [r.effective_analysis() for r in unprompted]
        mentioned = [a for a in eff if a.brand_mentioned]
        ranks = [a.brand_rank for a in mentioned if a.brand_rank > 0]
        own_cites = [a.own_domain_cited for a in eff if a.own_domain_cited is not None]

        comp_counts: Dict[str, int] = {}
        dom_counts: Dict[str, int] = {}
        for a in eff:
            for c in a.competitors_mentioned:
                comp_counts[c] = comp_counts.get(c, 0) + 1
            for d in a.cited_domains:
                dom_counts[d] = dom_counts.get(d, 0) + 1

        key = f"{plat}:{surface}"
        by_platform[key] = {
            "platform": plat,
            "surface": surface,
            "unprompted_samples": n,
            "mention_rate": round(len(mentioned) / n, 3) if n else None,
            "top1_rate": round(sum(1 for a in mentioned if a.brand_rank == 1) / n, 3) if n else None,
            "top3_rate": round(sum(1 for a in mentioned if 1 <= a.brand_rank <= 3) / n, 3) if n else None,
            "avg_rank": round(sum(ranks) / len(ranks), 2) if ranks else None,
            "own_domain_cite_rate": round(sum(1 for x in own_cites if x) / len(own_cites), 3) if own_cites else None,
            "competitor_mentions": dict(sorted(comp_counts.items(), key=lambda x: -x[1])),
            "top_cited_domains": dict(sorted(dom_counts.items(), key=lambda x: -x[1])[:15]),
            "needs_review_count": sum(1 for r in rows if r.needs_review),
            "manual_override_count": sum(1 for r in rows if r.manual_override is not None),
            "brand_probe": {
                "samples": len(probes),
                "recognized_rate": (
                    round(sum(1 for r in probes if r.effective_analysis().brand_mentioned) / len(probes), 3)
                    if probes
                    else None
                ),
            },
        }
    return {
        "total_samples": len(samples),
        "by_platform_surface": by_platform,
    }
