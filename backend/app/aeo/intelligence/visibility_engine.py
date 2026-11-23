"""
Rigorous AEO & GEO AI Visibility Engine + Platform-Specific AI Crawler Matrix.

Enforces enterprise measurement integrity:
1. Never conflates an LLM API response (OpenAI API / Gemini API) with consumer
   search products (ChatGPT Search UI / Google AI Overviews).
2. Explicitly declares execution_method per engine:
   LIVE_WEB_SEARCH | RETRIEVAL_AUGMENTED | MODEL_GENERATION | UNOBSERVABLE.
3. Unsupported or unobservable surfaces stay UNMEASURED (never unofficial scraping).
4. Records exact query, intent_class, locale, device_context, model_version,
   execution_method, timestamp, raw_response, and normalized/validated citations.
5. Supports repeat trials (N runs) to measure volatility and citation persistence.
6. Separates Brand Mention Rate from Linked Citation Rate, Share of Voice,
   Citation Position, Source Diversity, Competitor Overlap, and Answer Accuracy.
7. Distinguishes Training Crawlers, Search Crawlers, and Live Retrieval Fetchers.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import urlsplit
from pydantic import BaseModel, Field

from app.governance.data_reliability import utc_now_iso
from app.seo.intelligence.backlink_intelligence import normalize_canonical_domain

INTENT_CLASSES = ("informational", "commercial", "comparison", "transactional", "local", "brand")

ENGINE_CAPABILITY_REGISTRY: Dict[str, Dict[str, str]] = {
    "perplexity_sonar": {
        "display_name": "Perplexity Sonar API",
        "execution_method": "LIVE_WEB_SEARCH",
        "surface_note": "Official Perplexity API with live web retrieval and native citations.",
    },
    "openai_web_search": {
        "display_name": "OpenAI Responses API (Web Search)",
        "execution_method": "LIVE_WEB_SEARCH",
        "surface_note": "Official OpenAI API with web_search tool. Distinct from consumer ChatGPT UI.",
    },
    "openai_api": {
        "display_name": "OpenAI Model API",
        "execution_method": "MODEL_GENERATION",
        "surface_note": "Parametric model generation only — NOT evidence of consumer ChatGPT Search UI.",
    },
    "gemini_grounded": {
        "display_name": "Gemini API (Google Search Grounding)",
        "execution_method": "RETRIEVAL_AUGMENTED",
        "surface_note": "Official Gemini API with grounding. Distinct from consumer Google AI Overviews.",
    },
    "gemini_api": {
        "display_name": "Gemini Model API",
        "execution_method": "MODEL_GENERATION",
        "surface_note": "Parametric Gemini API — NOT evidence of Google AI Overviews.",
    },
    "claude_api": {
        "display_name": "Anthropic Claude API",
        "execution_method": "MODEL_GENERATION",
        "surface_note": "Official Anthropic Messages API (parametric unless web search tool enabled).",
    },
    "chatgpt_search_consumer_ui": {
        "display_name": "ChatGPT Search (Consumer UI)",
        "execution_method": "UNOBSERVABLE",
        "surface_note": "No official deterministic API; unofficial scraping prohibited. Marked UNMEASURED.",
    },
    "google_ai_overviews_consumer_ui": {
        "display_name": "Google AI Overviews (Consumer SERP)",
        "execution_method": "UNOBSERVABLE",
        "surface_note": "Requires licensed SERP/AIO provider; otherwise explicitly UNMEASURED.",
    },
}

AI_CRAWLER_CATEGORIES: Dict[str, List[Dict[str, str]]] = {
    "training_crawlers": [
        {"bot": "GPTBot", "operator": "OpenAI", "purpose": "Foundation model training"},
        {"bot": "ClaudeBot", "operator": "Anthropic", "purpose": "Foundation model training"},
        {"bot": "Google-Extended", "operator": "Google", "purpose": "Gemini / Vertex training opt-out token"},
        {"bot": "CCBot", "operator": "Common Crawl", "purpose": "Open web training corpus"},
        {"bot": "Meta-ExternalAgent", "operator": "Meta", "purpose": "Model training & indexing"},
        {"bot": "Bytespider", "operator": "ByteDance", "purpose": "Model training"},
    ],
    "search_crawlers": [
        {"bot": "OAI-SearchBot", "operator": "OpenAI", "purpose": "ChatGPT search indexing"},
        {"bot": "PerplexityBot", "operator": "Perplexity", "purpose": "Perplexity answer search index"},
        {"bot": "Bingbot", "operator": "Microsoft", "purpose": "Bing & Copilot search index"},
        {"bot": "Applebot", "operator": "Apple", "purpose": "Apple Search / Siri answers"},
    ],
    "retrieval_fetchers": [
        {"bot": "ChatGPT-User", "operator": "OpenAI", "purpose": "Live user-triggered retrieval"},
        {"bot": "Claude-User", "operator": "Anthropic", "purpose": "Live user-triggered retrieval"},
        {"bot": "Perplexity-User", "operator": "Perplexity", "purpose": "Live user-triggered retrieval"},
    ],
}


class VisibilityQuery(BaseModel):
    query_id: str
    query_text: str
    intent_class: str  # informational | commercial | comparison | transactional | local | brand
    locale: str = "en-US"
    device_context: str = "desktop"


class CitationRecord(BaseModel):
    raw_url: str
    normalized_domain: str
    position: int
    is_first_party: bool
    http_status: Optional[int] = None
    url_valid: bool = True


class EngineExecutionObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:12]}")
    query_id: str
    query_text: str
    intent_class: str
    locale: str = "en-US"
    device_context: str = "desktop"
    engine_id: str
    model_version: str
    execution_method: str  # LIVE_WEB_SEARCH | RETRIEVAL_AUGMENTED | MODEL_GENERATION | UNOBSERVABLE
    trial_number: int = 1
    status: str = "SUCCESS"  # SUCCESS | UNMEASURED | FAILED
    executed_at_utc: str = Field(default_factory=utc_now_iso)
    raw_response: str = ""
    citations: List[CitationRecord] = Field(default_factory=list)
    brand_mentioned: bool = False
    first_party_cited: bool = False
    first_party_citation_position: Optional[int] = None
    competitors_mentioned: List[str] = Field(default_factory=list)
    answer_accurate: Optional[bool] = None
    error_note: Optional[str] = None


class AiVisibilitySummary(BaseModel):
    domain: str
    brand_name: str
    total_queries_defined: int
    valid_executions: int
    unmeasured_engines: List[str] = Field(default_factory=list)
    execution_methods_used: Dict[str, str] = Field(default_factory=dict)
    # Separated core AEO metrics
    citation_rate_pct: Optional[float] = None
    brand_mention_rate_pct: Optional[float] = None
    share_of_voice_pct: Optional[float] = None
    avg_citation_position: Optional[float] = None
    source_diversity_urls: int = 0
    competitor_overlap_pct: Optional[float] = None
    answer_accuracy_pct: Optional[float] = None
    citation_persistence_pct: Optional[float] = None
    volatility_score_pct: Optional[float] = None
    competitor_comparison: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[EngineExecutionObservation] = Field(default_factory=list)
    disclosure: str = (
        "Brand mentions and linked citations are measured separately. "
        "Model API responses are explicitly distinguished from consumer search UIs; unobservable surfaces remain UNMEASURED."
    )


def generate_classified_question_set(
    *,
    brand_name: str,
    category: str,
    products: Sequence[str] = (),
    competitors: Sequence[str] = (),
    locations: Sequence[str] = ("India",),
    target_count: int = 100,
    locale: str = "en-IN",
) -> List[VisibilityQuery]:
    """Generates 100-500 deterministic commercial-intent queries classified across 6 intent buckets."""
    target_count = max(10, min(500, target_count))
    prod_list = list(products) or [category, f"{category} kit", f"{category} starter pack"]
    comp_list = list(competitors) or ["top competitor"]
    loc_list = list(locations) or ["India"]

    templates = [
        ("informational", lambda p, c, l: f"What are the benefits of {p} for daily {category}?"),
        ("informational", lambda p, c, l: f"How does {p} work compared to traditional {category}?"),
        ("commercial", lambda p, c, l: f"Best {p} brands in {l} with clinical or verified reviews"),
        ("commercial", lambda p, c, l: f"Top rated {category} products recommended by experts in {l}"),
        ("comparison", lambda p, c, l: f"{brand_name} {p} vs {c}: which is better?"),
        ("comparison", lambda p, c, l: f"Compare {brand_name} and {c} on price, quality, and features"),
        ("transactional", lambda p, c, l: f"Where to buy {brand_name} {p} online with warranty in {l}?"),
        ("transactional", lambda p, c, l: f"{brand_name} {p} price, offers, and return policy"),
        ("local", lambda p, c, l: f"Is {brand_name} {p} available for delivery in {l}?"),
        ("brand", lambda p, c, l: f"Is {brand_name} trustworthy and what products does {brand_name} make?"),
    ]

    queries: List[VisibilityQuery] = []
    idx = 0
    seen: set[str] = set()
    while len(queries) < target_count:
        intent, fn = templates[idx % len(templates)]
        p = prod_list[(idx // len(templates)) % len(prod_list)]
        c = comp_list[(idx // (len(templates) * len(prod_list))) % len(comp_list)]
        l = loc_list[idx % len(loc_list)]
        text = fn(p, c, l)
        if text in seen:
            text = f"{text} (variant {idx + 1})"
        seen.add(text)
        queries.append(
            VisibilityQuery(
                query_id=f"Q-{len(queries) + 1:03d}",
                query_text=text,
                intent_class=intent,
                locale=locale,
            )
        )
        idx += 1
    return queries


def build_ai_crawler_matrix(robots_txt: Optional[str]) -> Dict[str, Any]:
    """Parses robots.txt into a platform-specific AI crawler matrix separating training, search, and retrieval bots."""
    if robots_txt is None:
        return {
            "robots_measured": False,
            "status": "DATA_UNAVAILABLE",
            "categories": AI_CRAWLER_CATEGORIES,
            "matrix": [],
        }

    # Parse user-agent -> disallow/allow directives
    rules: Dict[str, List[str]] = {}
    current_agents: List[str] = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = [part.strip() for part in line.split(":", 1)]
        kl = k.lower()
        if kl == "user-agent":
            current_agents = [v.lower()]
            rules.setdefault(v.lower(), [])
        elif kl in ("disallow", "allow") and current_agents:
            for ag in current_agents:
                rules.setdefault(ag, []).append(f"{kl}:{v}")

    def _evaluate_bot(bot_name: str) -> str:
        specific = rules.get(bot_name.lower())
        effective = specific if specific is not None else rules.get("*", [])
        if any(r == "disallow:/" for r in effective):
            return "BLOCKED"
        if any(r.startswith("disallow:/") and len(r) > len("disallow:/") for r in effective):
            return "PARTIALLY_RESTRICTED"
        return "ALLOWED"

    matrix: List[Dict[str, str]] = []
    for cat_key, bots in AI_CRAWLER_CATEGORIES.items():
        for b in bots:
            matrix.append({
                "category": cat_key,
                "bot": b["bot"],
                "operator": b["operator"],
                "purpose": b["purpose"],
                "access_status": _evaluate_bot(b["bot"]),
            })

    return {
        "robots_measured": True,
        "status": "MEASURED",
        "matrix": matrix,
        "note": "Training crawlers, search index crawlers, and live user-triggered retrieval fetchers are evaluated separately.",
    }


class RigorousAiVisibilityEngine:
    """Evaluates multi-engine AI visibility with execution-method disclosure, volatility, and URL validation."""

    @staticmethod
    def normalize_and_validate_citations(
        raw_urls: Sequence[str],
        target_domain: str,
        url_validator: Optional[Callable[[str], Optional[int]]] = None,
    ) -> List[CitationRecord]:
        clean_target = normalize_canonical_domain(target_domain)
        records: List[CitationRecord] = []
        seen_urls: set[str] = set()
        for raw in raw_urls:
            u = (raw or "").strip()
            if not u or u in seen_urls:
                continue
            seen_urls.add(u)
            parsed = urlsplit(u)
            valid_syntax = parsed.scheme in ("http", "https") and bool(parsed.hostname)
            norm_dom = normalize_canonical_domain(u) if valid_syntax else ""
            http_status = url_validator(u) if (url_validator and valid_syntax) else None
            is_valid = valid_syntax and (http_status is None or (200 <= http_status < 400))
            records.append(
                CitationRecord(
                    raw_url=u,
                    normalized_domain=norm_dom,
                    position=len(records) + 1,
                    is_first_party=bool(norm_dom and (norm_dom == clean_target or norm_dom.endswith("." + clean_target))),
                    http_status=http_status,
                    url_valid=is_valid,
                )
            )
        return records

    @classmethod
    def evaluate_observations(
        cls,
        *,
        domain: str,
        brand_name: str,
        queries: Sequence[VisibilityQuery],
        raw_executions: Sequence[Dict[str, Any]],
        competitors: Sequence[str] = (),
        verified_facts: Optional[Dict[str, str]] = None,
        url_validator: Optional[Callable[[str], Optional[int]]] = None,
    ) -> AiVisibilitySummary:
        facts = verified_facts or {}
        observations: List[EngineExecutionObservation] = []
        unmeasured_engines: set[str] = set()
        methods_used: Dict[str, str] = {}

        for ex in raw_executions:
            engine_id = str(ex.get("engine_id") or "unknown")
            cap = ENGINE_CAPABILITY_REGISTRY.get(
                engine_id,
                {"execution_method": ex.get("execution_method", "UNOBSERVABLE"), "display_name": engine_id},
            )
            method = str(ex.get("execution_method") or cap["execution_method"]).upper()
            methods_used[engine_id] = method

            if method == "UNOBSERVABLE" or str(ex.get("status", "")).upper() in {"UNMEASURED", "NOT_CONNECTED"}:
                unmeasured_engines.add(engine_id)
                observations.append(
                    EngineExecutionObservation(
                        query_id=str(ex.get("query_id") or "Q-000"),
                        query_text=str(ex.get("query_text") or ""),
                        intent_class=str(ex.get("intent_class") or "commercial"),
                        locale=str(ex.get("locale") or "en-US"),
                        device_context=str(ex.get("device_context") or "desktop"),
                        engine_id=engine_id,
                        model_version=str(ex.get("model_version") or "unmeasured"),
                        execution_method=method,
                        trial_number=int(ex.get("trial_number") or 1),
                        status="UNMEASURED",
                        error_note=cap.get("surface_note", "Engine not observable or not connected."),
                    )
                )
                continue

            resp_text = str(ex.get("raw_response") or "")
            citations = cls.normalize_and_validate_citations(
                ex.get("citations") or [], target_domain=domain, url_validator=url_validator
            )
            fp_cites = [c for c in citations if c.is_first_party and c.url_valid]
            fp_pos = fp_cites[0].position if fp_cites else None
            mentioned = bool(brand_name and re.search(rf"\b{re.escape(brand_name)}\b", resp_text, re.IGNORECASE))
            comps_found = [
                c for c in competitors
                if c and c.lower() != brand_name.lower() and re.search(rf"\b{re.escape(c)}\b", resp_text, re.IGNORECASE)
            ]

            accurate: Optional[bool] = None
            if facts:
                q_low = str(ex.get("query_text") or "").lower()
                matched_keys = [k for k in facts if k.lower() in q_low]
                if matched_keys:
                    accurate = all(facts[k].lower() in resp_text.lower() for k in matched_keys)

            observations.append(
                EngineExecutionObservation(
                    query_id=str(ex.get("query_id") or "Q-000"),
                    query_text=str(ex.get("query_text") or ""),
                    intent_class=str(ex.get("intent_class") or "commercial"),
                    locale=str(ex.get("locale") or "en-US"),
                    device_context=str(ex.get("device_context") or "desktop"),
                    engine_id=engine_id,
                    model_version=str(ex.get("model_version") or "unspecified"),
                    execution_method=method,
                    trial_number=int(ex.get("trial_number") or 1),
                    status="SUCCESS",
                    raw_response=resp_text,
                    citations=citations,
                    brand_mentioned=mentioned,
                    first_party_cited=bool(fp_cites),
                    first_party_citation_position=fp_pos,
                    competitors_mentioned=comps_found,
                    answer_accurate=accurate,
                )
            )

        valid = [o for o in observations if o.status == "SUCCESS"]
        n = len(valid)
        if n == 0:
            return AiVisibilitySummary(
                domain=domain,
                brand_name=brand_name,
                total_queries_defined=len(queries),
                valid_executions=0,
                unmeasured_engines=sorted(unmeasured_engines),
                execution_methods_used=methods_used,
                observations=observations,
            )

        cited_cnt = sum(1 for o in valid if o.first_party_cited)
        mention_cnt = sum(1 for o in valid if o.brand_mentioned)
        overlap_cnt = sum(1 for o in valid if o.brand_mentioned and o.competitors_mentioned)
        positions = [o.first_party_citation_position for o in valid if o.first_party_citation_position is not None]
        distinct_fp_urls = {c.raw_url for o in valid for c in o.citations if c.is_first_party and c.url_valid}
        acc_evals = [o.answer_accurate for o in valid if o.answer_accurate is not None]

        # Competitor Share of Voice on identical executed query set
        comp_counts: Dict[str, int] = {c: 0 for c in competitors}
        for o in valid:
            for c in o.competitors_mentioned:
                comp_counts[c] = comp_counts.get(c, 0) + 1
        total_entity_appearances = mention_cnt + sum(comp_counts.values())
        sov = round((mention_cnt / total_entity_appearances) * 100.0, 1) if total_entity_appearances > 0 else 0.0

        # Repeat-trial volatility & citation persistence across (query_id, engine_id)
        by_qe: Dict[tuple[str, str], List[bool]] = {}
        for o in valid:
            by_qe.setdefault((o.query_id, o.engine_id), []).append(o.first_party_cited)
        multi_trials = [vals for vals in by_qe.values() if len(vals) >= 2]
        if multi_trials:
            volatile_pairs = sum(1 for vals in multi_trials if len(set(vals)) > 1)
            persistent_cited = sum(1 for vals in multi_trials if all(vals))
            volatility = round((volatile_pairs / len(multi_trials)) * 100.0, 1)
            persistence = round((persistent_cited / len(multi_trials)) * 100.0, 1)
        else:
            volatility, persistence = None, None

        return AiVisibilitySummary(
            domain=domain,
            brand_name=brand_name,
            total_queries_defined=len(queries),
            valid_executions=n,
            unmeasured_engines=sorted(unmeasured_engines),
            execution_methods_used=methods_used,
            citation_rate_pct=round((cited_cnt / n) * 100.0, 1),
            brand_mention_rate_pct=round((mention_cnt / n) * 100.0, 1),
            share_of_voice_pct=sov,
            avg_citation_position=round(sum(positions) / len(positions), 2) if positions else None,
            source_diversity_urls=len(distinct_fp_urls),
            competitor_overlap_pct=round((overlap_cnt / n) * 100.0, 1),
            answer_accuracy_pct=round((sum(1 for a in acc_evals if a) / len(acc_evals)) * 100.0, 1) if acc_evals else None,
            citation_persistence_pct=persistence,
            volatility_score_pct=volatility,
            competitor_comparison=[
                {"competitor": c, "appearances": cnt, "appearance_rate_pct": round((cnt / n) * 100.0, 1)}
                for c, cnt in sorted(comp_counts.items(), key=lambda x: -x[1])
            ],
            observations=observations,
        )
