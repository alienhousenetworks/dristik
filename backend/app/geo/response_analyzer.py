"""Phase 6 — Deterministic AI Response Analysis & Brand Visibility Measurement.

Analyzes verbatim AI responses with full provenance:
- Classifies all 8 mention types (`direct_mention`, `entity_mention`, `recommendation`,
  `shortlist_inclusion`, `comparative_inclusion`, `citation_only`, `negative_mention`,
  `incorrect_representation`).
- Strictly separates mentions from recommendations and citations.
- Detects competitor mentions, brand positioning, factual claims, and inaccuracies
  compared against approved `GEOEntity` brand facts.
- Computes cross-repeat variation and Wilson confidence intervals.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from app.geo.metrics import wilson_score_interval
from app.geo.models import (
    GEOAuditScope,
    GEOCitation,
    GEODataQualityState,
    GEOEntity,
    GEOEntityFactStatus,
    GEOMention,
    GEOMentionType,
    GEOPromptRun,
    GEOResponse,
    GEOSourceOwnership,
)
from app.geo.sentiment_engine import NEGATIVE_LEXICON, POSITIVE_LEXICON

RECOMMENDATION_VERBS = (
    r"\b(?:recommend(?:ed|s|ing)?|top\s+(?:choice|pick|option|recommendation)|"
    r"best\s+(?:overall|choice|option|pick|for)|standout\s+(?:choice|option)|"
    r"ideal\s+(?:choice|option|for)|go\s+with|worth\s+choosing)\b"
)
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:avoid|unreliable|scam|poor|outdated|lacks|discontinued|expensive|complaints|"
    r"limited|slow|buggy|negative|not\s+recommended|weakness|drawback)\b",
    re.I,
)
COMPARATIVE_RE = re.compile(r"\b(?:vs\.?|versus|compared\s+to|comparison|whereas|unlike|while)\b", re.I)


def _norm_host(url_or_domain: str) -> str:
    raw = (url_or_domain or "").strip().lower()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw if "://" in raw else f"//{raw}")
        host = (parsed.hostname or "").rstrip(".").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _contains_whole(text: str, term: str) -> bool:
    if not text or not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term.strip())}(?!\w)", text, re.I) is not None


def _extract_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _extract_ordinal_position(text: str, terms: List[str]) -> Optional[int]:
    for line in (text or "").splitlines():
        if not any(_contains_whole(line, t) for t in terms if t):
            continue
        m = re.match(r"^\s*(?:#|\*\*#?)?(\d+)[\.\):\s]", line)
        if m:
            return int(m.group(1))
        m2 = re.search(r"#(\d+)", line)
        if m2:
            return int(m2.group(1))
    return None


def _count_list_items(text: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:\d+[\.\)]|[-*•])\s+\S+", text or ""))


def _sentence_sentiment(sentence: str) -> str:
    low = f" {sentence.lower()} "
    pos = sum(1 for w in POSITIVE_LEXICON if f" {w} " in low)
    neg = sum(1 for w in NEGATIVE_LEXICON if f" {w} " in low) + (1 if NEGATIVE_CONTEXT_RE.search(sentence) else 0)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    if pos > 0 and neg > 0:
        return "mixed"
    return "neutral"


def _detect_inaccuracies(
    brand_sentences: List[str],
    approved_entities: List[GEOEntity],
) -> List[Dict[str, str]]:
    """Detect verifiable factual conflicts between AI response sentences and confirmed brand entities."""
    conflicts: List[Dict[str, str]] = []
    confirmed = [e for e in approved_entities if e.fact_status == GEOEntityFactStatus.CONFIRMED]
    joined = " ".join(brand_sentences)
    joined_low = joined.lower()

    for ent in confirmed:
        attr = ent.attribute.lower()
        val_str = str(ent.value or "").strip()
        if not val_str:
            continue
        # Check founding year conflict
        if "founded" in attr or "founding" in attr:
            yr_expected = re.search(r"\b(19\d\d|20\d\d)\b", val_str)
            yr_found = re.search(r"\bfounded\s+(?:in\s+)?(19\d\d|20\d\d)\b", joined, re.I)
            if yr_expected and yr_found and yr_expected.group(1) != yr_found.group(1):
                conflicts.append({
                    "attribute": ent.attribute,
                    "expected": yr_expected.group(1),
                    "observed_in_ai": yr_found.group(1),
                    "note": f"AI states founded in {yr_found.group(1)}, conflicting with verified fact '{val_str}'.",
                })
        # Check HQ / location conflict
        elif "headquarters" in attr or "location" in attr or "hq" in attr:
            m_hq = re.search(r"\b(?:based|headquartered|located)\s+in\s+([A-Z][A-Za-z\s,]{2,35})", joined)
            if m_hq:
                obs_loc = m_hq.group(1).strip(" .,;")
                if obs_loc.lower() not in val_str.lower() and val_str.lower() not in obs_loc.lower():
                    conflicts.append({
                        "attribute": ent.attribute,
                        "expected": val_str,
                        "observed_in_ai": obs_loc,
                        "note": f"AI states headquarters in '{obs_loc}', conflicting with verified fact '{val_str}'.",
                    })
        # Check discontinued / closed false claim
        elif "status" in attr and "active" in val_str.lower():
            if any(k in joined_low for k in ("discontinued", "shut down", "defunct", "no longer operates")):
                conflicts.append({
                    "attribute": ent.attribute,
                    "expected": val_str,
                    "observed_in_ai": "discontinued/shut down",
                    "note": "AI claims brand is discontinued despite confirmed active status.",
                })
        # Check pricing conflict when confirmed fact says no public pricing or specific currency figure
        elif "pricing" in attr:
            if "no public pricing" in val_str.lower() or "custom enterprise" in val_str.lower():
                m_price = re.search(r"(\$\d+(?:\.\d+)?(?:/mo|/month|/yr)?)", joined)
                if m_price:
                    conflicts.append({
                        "attribute": ent.attribute,
                        "expected": val_str,
                        "observed_in_ai": m_price.group(1),
                        "note": f"AI quotes '{m_price.group(1)}' although verified brand profile lists '{val_str}'.",
                    })
    return conflicts


def analyze_prompt_run_response(
    *,
    run: GEOPromptRun,
    raw_text: str,
    raw_citations: List[str],
    tool_use_metadata: Optional[Dict[str, Any]],
    scope: GEOAuditScope,
    approved_entities: Optional[List[GEOEntity]] = None,
    snapshot_id: Optional[str] = None,
) -> Tuple[GEOResponse, List[GEOMention], List[GEOCitation]]:
    """Deterministically analyze one captured AI response into canonical records."""
    text = (raw_text or "").strip()
    response_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    target_host = _norm_host(scope.domain)
    brand = scope.brand_name.strip()
    aliases = [a.strip() for a in (scope.brand_aliases or []) if a and a.strip()]
    products = [p.strip() for p in (scope.products or []) + (scope.services or []) if p and p.strip()]
    competitors = [c.strip() for c in (scope.competitors or []) if c and c.strip()]
    approved = approved_entities or []

    # 1. Extract and classify citations
    citations_out: List[GEOCitation] = []
    inline_urls = re.findall(r"https?://[^\s\)\],>'\"]+", text)
    ordered_urls = list(dict.fromkeys([str(u).rstrip(".,);]>'\"") for u in list(raw_citations or []) + inline_urls if u]))
    owned_cited = False

    comp_hosts = {_norm_host(c): c for c in competitors if "." in c}
    for idx, url in enumerate(ordered_urls, start=1):
        host = _norm_host(url)
        valid = bool(host and "." in host and url.lower().startswith(("http://", "https://")))
        if not host:
            continue
        is_owned = bool(target_host and (host == target_host or host.endswith("." + target_host)))
        matched_comps = [
            c for c in competitors
            if (_norm_host(c) and (host == _norm_host(c) or host.endswith("." + _norm_host(c))))
            or (c.lower().replace(" ", "") in host.replace("-", ""))
        ]
        if is_owned:
            ownership = GEOSourceOwnership.OWNED
            owned_cited = True
        elif matched_comps:
            ownership = GEOSourceOwnership.COMPETITOR
        else:
            ownership = GEOSourceOwnership.INDEPENDENT

        citations_out.append(
            GEOCitation(
                tenant_id=run.tenant_id,
                audit_id=run.audit_id,
                response_id="",  # populated below once GEOResponse ID exists
                run_id=run.run_id,
                prompt_id=run.prompt_id,
                platform_id=run.platform_id,
                cited_url=url,
                domain=host,
                publisher=host.split(".")[0].capitalize() if host else "",
                source_ownership=ownership,
                citation_position=idx,
                competitors_associated=matched_comps,
                url_valid=valid,
                data_quality_state=GEODataQualityState.OBSERVED if valid else GEODataQualityState.FAILED,
                source_refs=[run.run_id] + ([snapshot_id] if snapshot_id else []),
            )
        )

    # 2. Detect brand / alias / product mentions
    sentences = _extract_sentences(text)
    direct_hit = _contains_whole(text, brand) or (bool(target_host) and _contains_whole(text, target_host))
    alias_hits = [a for a in aliases if _contains_whole(text, a)]
    product_hits = [p for p in products if len(p) >= 4 and _contains_whole(text, p)]
    brand_terms = [t for t in ([brand, target_host] + alias_hits + product_hits) if t]
    brand_sentences = [s for s in sentences if any(_contains_whole(s, t) for t in brand_terms)]

    is_comparative = bool(COMPARATIVE_RE.search(text)) and bool(
        any(_contains_whole(text, c) for c in competitors) or "competitor" in text.lower() or "alternative" in text.lower()
    )
    list_count = _count_list_items(text)
    ordinal_pos = _extract_ordinal_position(text, brand_terms)
    is_shortlisted = bool(brand_sentences) and (list_count >= 2 or ordinal_pos is not None)

    is_recommended = False
    for s in brand_sentences:
        if re.search(RECOMMENDATION_VERBS, s, re.I) and not NEGATIVE_CONTEXT_RE.search(s):
            is_recommended = True
            break
    if not is_recommended and ordinal_pos == 1 and brand_sentences and not NEGATIVE_CONTEXT_RE.search(brand_sentences[0]):
        is_recommended = True

    inaccuracies = _detect_inaccuracies(brand_sentences, approved) if brand_sentences else []
    sentiments = [_sentence_sentiment(s) for s in brand_sentences]
    if not brand_sentences:
        overall_sentiment = "unmentioned"
    elif "negative" in sentiments and "positive" not in sentiments:
        overall_sentiment = "negative"
    elif "negative" in sentiments and "positive" in sentiments:
        overall_sentiment = "mixed"
    elif "positive" in sentiments:
        overall_sentiment = "positive"
    else:
        overall_sentiment = "neutral"

    # Extract concise factual claims about the brand
    extracted_claims = [
        {"sentence": s[:240], "sentiment": _sentence_sentiment(s), "verified_status": "unverified_ai_statement"}
        for s in brand_sentences[:6]
    ]

    positioning = ""
    if is_recommended:
        positioning = "explicitly_recommended"
    elif is_shortlisted:
        positioning = "shortlist_option"
    elif is_comparative and brand_sentences:
        positioning = "comparative_reference"
    elif brand_sentences:
        positioning = "mentioned_without_recommendation"
    elif owned_cited:
        positioning = "cited_source_only"
    else:
        positioning = "not_observed"

    resp = GEOResponse(
        tenant_id=run.tenant_id,
        audit_id=run.audit_id,
        run_id=run.run_id,
        prompt_id=run.prompt_id,
        platform_id=run.platform_id,
        model_version=run.model_version,
        testing_mode=run.testing_mode,
        response_text=text,
        response_hash=response_hash,
        raw_citations=ordered_urls,
        tool_use_metadata=tool_use_metadata or {},
        snapshot_id=snapshot_id,
        extracted_claims=extracted_claims,
        sentiment=overall_sentiment,
        brand_positioning=positioning,
        is_shortlisted=is_shortlisted,
        is_comparative=is_comparative,
        brand_mentioned=bool(direct_hit or alias_hits or product_hits),
        brand_recommended=is_recommended,
        brand_cited=owned_cited,
        inaccurate_claims_count=len(inaccuracies),
        data_quality_state=GEODataQualityState.OBSERVED if text else GEODataQualityState.NOT_OBSERVED,
        source_refs=[run.run_id] + ([snapshot_id] if snapshot_id else []),
    )

    for c in citations_out:
        c.response_id = resp.response_id
        # Attach closest supporting claim sentence if available
        if brand_sentences and c.source_ownership == GEOSourceOwnership.OWNED:
            c.associated_claim = brand_sentences[0][:220]

    # 3. Emit granular GEOMention records covering all 8 mention types
    mentions_out: List[GEOMention] = []
    first_snippet = brand_sentences[0][:220] if brand_sentences else ""

    def _add_mention(
        entity_name: str,
        entity_kind: str,
        is_target: bool,
        m_type: GEOMentionType,
        snippet: str,
        pos: Optional[int] = None,
        sent: str = "neutral",
        inacc: Optional[str] = None,
    ) -> None:
        mentions_out.append(
            GEOMention(
                tenant_id=run.tenant_id,
                audit_id=run.audit_id,
                response_id=resp.response_id,
                run_id=run.run_id,
                prompt_id=run.prompt_id,
                platform_id=run.platform_id,
                entity_name=entity_name,
                entity_kind=entity_kind,
                is_target_brand=is_target,
                mention_type=m_type,
                ordinal_position=pos,
                sentiment=sent,
                context_snippet=snippet,
                inaccuracy_note=inacc,
                data_quality_state=GEODataQualityState.OBSERVED,
                source_refs=[resp.response_id, run.run_id],
            )
        )

    if direct_hit:
        _add_mention(brand, "brand", True, GEOMentionType.DIRECT_MENTION, first_snippet, ordinal_pos, overall_sentiment)
    for alias in alias_hits:
        _add_mention(alias, "brand", True, GEOMentionType.ENTITY_MENTION, first_snippet, ordinal_pos, overall_sentiment)
    for prod in product_hits:
        prod_sent = next((s for s in sentences if _contains_whole(s, prod)), first_snippet)
        _add_mention(prod, "product", True, GEOMentionType.ENTITY_MENTION, prod_sent[:220], ordinal_pos, _sentence_sentiment(prod_sent))
    if is_recommended:
        _add_mention(brand, "brand", True, GEOMentionType.RECOMMENDATION, first_snippet, ordinal_pos, "positive")
    if is_shortlisted:
        _add_mention(brand, "brand", True, GEOMentionType.SHORTLIST_INCLUSION, first_snippet, ordinal_pos, overall_sentiment)
    if is_comparative and brand_sentences:
        _add_mention(brand, "brand", True, GEOMentionType.COMPARATIVE_INCLUSION, first_snippet, ordinal_pos, overall_sentiment)
    if owned_cited and not brand_sentences:
        _add_mention(brand, "brand", True, GEOMentionType.CITATION_ONLY, f"Owned domain {target_host} cited without direct brand mention.", None, "neutral")
    if overall_sentiment == "negative":
        neg_s = next((s for s in brand_sentences if _sentence_sentiment(s) == "negative"), first_snippet)
        _add_mention(brand, "brand", True, GEOMentionType.NEGATIVE_MENTION, neg_s[:220], ordinal_pos, "negative")
    for inc in inaccuracies:
        _add_mention(brand, "brand", True, GEOMentionType.INCORRECT_REPRESENTATION, first_snippet, ordinal_pos, "negative", inc["note"])

    # Competitor mentions
    for comp in competitors:
        comp_name = comp.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        comp_token = comp_name.split(".")[0] if "." in comp_name else comp_name
        if not comp_token:
            continue
        comp_sents = [s for s in sentences if _contains_whole(s, comp_name) or _contains_whole(s, comp_token)]
        if not comp_sents:
            continue
        c_pos = _extract_ordinal_position(text, [comp_name, comp_token])
        c_rec = any(re.search(RECOMMENDATION_VERBS, s, re.I) and not NEGATIVE_CONTEXT_RE.search(s) for s in comp_sents) or c_pos == 1
        c_sent = _sentence_sentiment(comp_sents[0])
        _add_mention(
            comp,
            "competitor",
            False,
            GEOMentionType.RECOMMENDATION if c_rec else GEOMentionType.DIRECT_MENTION,
            comp_sents[0][:220],
            c_pos,
            c_sent,
        )

    return resp, mentions_out, citations_out


def summarize_repeat_variation(
    runs: List[GEOPromptRun],
    responses: List[GEOResponse],
) -> Dict[str, Any]:
    """Compute repeat-run stability, inclusion/recommendation/citation rates, and Wilson CIs."""
    resp_by_run = {r.run_id: r for r in responses}
    ok_runs = [r for r in runs if r.status == GEODataQualityState.OBSERVED and r.run_id in resp_by_run]
    n = len(ok_runs)
    if n == 0:
        return {
            "status": GEODataQualityState.NOT_TESTED.value,
            "sample_size": 0,
            "inclusion_rate_pct": None,
            "recommendation_rate_pct": None,
            "citation_rate_pct": None,
            "response_variation_pct": None,
            "wilson_ci_95": {},
            "note": "No successful prompt executions recorded; observed rates remain unmeasured.",
        }

    mentions = sum(1 for r in ok_runs if resp_by_run[r.run_id].brand_mentioned)
    recs = sum(1 for r in ok_runs if resp_by_run[r.run_id].brand_recommended)
    cites = sum(1 for r in ok_runs if resp_by_run[r.run_id].brand_cited)

    # Measure variation across repeated executions of the same (prompt_id, platform_id)
    grouped: Dict[Tuple[str, str], List[GEOResponse]] = defaultdict(list)
    for r in ok_runs:
        grouped[(r.prompt_id, r.platform_id)].append(resp_by_run[r.run_id])

    repeated_groups = [g for g in grouped.values() if len(g) >= 2]
    variable_groups = 0
    for g in repeated_groups:
        states = {(x.brand_mentioned, x.brand_recommended, x.brand_cited) for x in g}
        if len(states) > 1:
            variable_groups += 1
    variation_pct = round((variable_groups / len(repeated_groups)) * 100.0, 1) if repeated_groups else None

    return {
        "status": GEODataQualityState.OBSERVED.value,
        "sample_size": n,
        "repeated_prompt_platform_pairs": len(repeated_groups),
        "inclusion_rate_pct": round((mentions / n) * 100.0, 1),
        "recommendation_rate_pct": round((recs / n) * 100.0, 1),
        "citation_rate_pct": round((cites / n) * 100.0, 1),
        "response_variation_pct": variation_pct,
        "wilson_ci_95": {
            "inclusion": wilson_score_interval(mentions, n),
            "recommendation": wilson_score_interval(recs, n),
            "citation": wilson_score_interval(cites, n),
        },
        "note": (
            "Observed rates apply strictly to the tested prompt suite, platforms, and timestamps; "
            "they are not universal market share or a guarantee of future AI responses."
        ),
    }
