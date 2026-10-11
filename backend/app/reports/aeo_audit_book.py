"""AEO section document as a 55-section evidence book.

Each checklist line is a result from the sealed report. Content readiness,
technical eligibility, observed answer visibility, and business outcomes stay
separate. A missing source is not a zero and not a pass. On-page structure
is not live answer visibility.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_INDEX_PATH = Path(__file__).with_name("aeo_audit_index.json")

_LABEL = {
    "ISSUE_SAMPLE": "Sample verified · issue",
    "CLEAN_SAMPLE": "Sample verified · no issue",
    "VERIFIED": "Verified",
    "INFERRED": "Inferred",
    "DATA_UNAVAILABLE": "Data unavailable",
    "NOT_TESTED": "Not tested",
    "NOT_APPLICABLE": "Not applicable",
}
_CLASS = {
    "ISSUE_SAMPLE": "issue",
    "CLEAN_SAMPLE": "clean",
    "VERIFIED": "measured",
    "INFERRED": "inferred",
    "DATA_UNAVAILABLE": "gap",
    "NOT_TESTED": "untested",
    "NOT_APPLICABLE": "na",
}
_NOTE_PHRASES = (
    "which is a good",
    "which are clear",
    "relatively fast",
    "successful request",
    "good start",
    "good summary",
    "clear and direct",
    "indicates a successful",
)
_SEPARATION = (
    "Content readiness describes the source. Observed answer visibility is a documented engine result. "
    "Business impact is measured separately. These three are not combined into one AEO grade."
)
_LIMIT = (
    " Validation: review the updated page against the stored question and rerun that question under the same documented conditions. "
    "Success metrics are answer completeness, factual accuracy, and, when a live run exists, mention rate and citation rate. "
    "Limitation: a clearer page does not guarantee that an answer engine will select or cite it."
)
_INTENT_RULES = (
    ("definition", ("what is", "define", "definition", "meaning of")),
    ("explanatory", ("why ", "explain", "how does")),
    ("how-to", ("how to", "how do i", "step")),
    ("troubleshooting", ("error", "not working", "troubleshoot", "fix ")),
    ("comparison", (" vs ", "versus", "compare", "alternative", "difference")),
    ("best", ("best ", "top ")),
    ("recommendation", ("recommend", "should i", "which product")),
    ("pricing", ("price", "pricing", "cost", "fee")),
    ("eligibility", ("eligib", "qualif", "who can")),
    ("location", ("where ", "location", "near me", "available in")),
    ("transactional", ("buy", "sign up", "order", "book ", "subscribe")),
    ("navigational", ("login", "official site", "contact")),
    ("opinion", ("review", "worth", "opinion")),
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _pct(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _has(label: str, *needles: str) -> bool:
    low = label.lower()
    return any(needle in low for needle in needles)


def _join(items: Sequence[str], limit: int = 6) -> str:
    rows = [str(item).strip() for item in items if str(item).strip()]
    if not rows:
        return "none recorded"
    shown = rows[:limit]
    extra = len(rows) - len(shown)
    text = "; ".join(shown)
    if extra:
        text += f" (+{extra} more)"
    return text


def _clip(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class _Question:
    def __init__(self, qid: str, text: str, status: str, intent: str, url: str, gap: str, source: str, facet: str) -> None:
        self.qid = qid
        self.text = text
        self.status = status
        self.intent = intent
        self.url = url
        self.gap = gap
        self.source = source
        self.facet = facet


def _question_status(raw: Any, is_answerable: Any) -> str:
    status = str(raw or "").upper()
    if status in {"ANSWERABLE", "SUPPORTED"}:
        if is_answerable is False:
            return "UNANSWERABLE"
        return "ANSWERABLE"
    if status == "PARTIAL":
        return "PARTIAL"
    if status in {"UNANSWERABLE", "UNSUPPORTED", "MISSING", "BLIND"}:
        return "UNANSWERABLE"
    if status in {"CONFLICTING", "CONFLICT"}:
        return "CONFLICTING"
    if is_answerable is True:
        return "ANSWERABLE"
    if is_answerable is False:
        return "UNANSWERABLE"
    return "UNASSESSED"


def _intent_bucket(text: str) -> str:
    low = f" {text.lower()} "
    for name, needles in _INTENT_RULES:
        if any(needle in low for needle in needles):
            return name
    return "unclassified"


class _Facts:
    def __init__(self, report: Any) -> None:
        self.report = report
        self.domain = str(_get(report, "domain", "") or "this site")
        self.generated_at = str(_get(report, "generated_at", "") or "the audit run")
        manifest = _get(report, "crawl_manifest")
        pages = list(_get(manifest, "pages", None) or [])
        if not pages:
            pages = list(_get(report, "page_reports", None) or [])
        self.pages = pages
        self.manifest = manifest
        self.crawled = len(pages)
        discovered = _num(_get(manifest, "total_pages_discovered"))
        self.discovered = int(discovered) if discovered else 0
        self.sample = self._sample_sentence()
        self.profile = _get(report, "business_profile")
        self.geo = _get(report, "geo_readiness")
        self.questions, self.question_source = self._load_questions()
        self.assessed = len(self.questions)
        self.usable = sum(1 for item in self.questions if item.status == "ANSWERABLE")
        self.partial = sum(1 for item in self.questions if item.status == "PARTIAL")
        self.unanswered = sum(1 for item in self.questions if item.status == "UNANSWERABLE")
        self.conflicting = sum(1 for item in self.questions if item.status == "CONFLICTING")
        self.card = _get(report, "ai_visibility_scorecard")
        self.runs = int(_num(_get(self.card, "successful_runs")) or 0) if self.card is not None else 0
        self.engines = [str(item) for item in (_get(self.card, "engines_queried", None) or []) if str(item).strip()]
        self.surfaces = [str(item) for item in (_get(self.card, "surfaces_not_queried", None) or []) if str(item).strip()]
        if self.card is not None and not self.surfaces:
            self.surfaces = ["Google AI Overviews", "Google AI Mode", "Bing Copilot"]
        self.kind = str(_get(self.card, "measurement_kind", "") or "")
        self.records = list(_get(self.card, "observatory_records", None) or []) if self.card is not None else []
        self.rates = {
            "mention": _num(_get(self.card, "mention_rate_pct")) if self.runs > 0 else None,
            "citation": _num(_get(self.card, "citation_rate_pct")) if self.runs > 0 else None,
            "citation_accuracy": _num(_get(self.card, "citation_accuracy_pct")) if self.runs > 0 else None,
            "entity_accuracy": _num(_get(self.card, "entity_accuracy_pct")) if self.runs > 0 else None,
            "competitor": _num(_get(self.card, "competitor_visibility_pct")) if self.runs > 0 else None,
            "hallucination": _num(_get(self.card, "hallucination_rate_pct")) if self.runs > 0 else None,
        }
        matrix = _get(report, "per_engine_geo")
        self.matrix = matrix
        self.simulation = str(_get(matrix, "measurement_mode", "") or "")
        gain = _get(matrix, "information_gain")
        self.info_gain = _num(_get(gain, "score")) if gain is not None else None
        bots = _get(matrix, "ai_bot_directives")
        self.robots_measured = bool(_get(bots, "robots_measured")) if bots is not None else False
        self.bots = bots if self.robots_measured else None
        self.extractability = _num(_get(self.geo, "extractability_score"))
        self.schema_types = self._schema_types()
        cross = _get(self.geo, "schema_crosscheck") or {}
        self.cross = cross if isinstance(cross, dict) else {}
        entity = _get(self.geo, "entity_consistency") or {}
        self.entity = entity if isinstance(entity, dict) else {}
        claims = _get(self.geo, "claims_analysis") or {}
        self.claims = claims if isinstance(claims, dict) else {}
        passages = _get(self.geo, "citation_passages") or {}
        self.passages = passages if isinstance(passages, dict) else {}
        self.contradictions = list(_get(report, "contradictions", None) or [])
        bake = _get(report, "competitor_bakeoff")
        evaluations = list(_get(bake, "evaluations", None) or []) if bake is not None else []
        self.bakeoff = bake if evaluations else None
        self.bake_items = evaluations
        performance = _get(report, "google_performance") or {}
        if not isinstance(performance, dict):
            performance = {}
        search = performance.get("search_console")
        analytics = performance.get("analytics")
        self.search = search if isinstance(search, dict) else {}
        self.analytics = analytics if isinstance(analytics, dict) else {}
        self.gsc_state = str(self.search.get("state") or "NOT_CONNECTED")
        self.ga4_state = str(self.analytics.get("state") or "NOT_CONNECTED")
        self.findings = list(_get(report, "findings", None) or [])
        intl = _get(report, "international_seo")
        self.intl = intl
        schema_validation = _get(report, "schema_validation")
        self.schema_validation = schema_validation if _schema_validation_ran(schema_validation) else None

    def _sample_sentence(self) -> str:
        if self.crawled == 0:
            return "No page was crawled on this run. Dristik uses a representative sample."
        if self.discovered and self.discovered > self.crawled:
            return (
                f"Representative sample: {self.crawled} crawled page(s) of {self.discovered} discovered URLs. "
                "This is not every URL on the site."
            )
        return f"Representative sample: {self.crawled} crawled page(s). This is not every URL on the site."

    def _load_questions(self) -> Tuple[List[_Question], str]:
        sandbox = list(_get(self.report, "dynamic_sandbox_evaluations", None) or [])
        if sandbox:
            return [self._from_sandbox(item) for item in sandbox], "the on-page answer sandbox"
        geo_questions = list(_get(self.geo, "questions", None) or [])
        if geo_questions:
            return [self._from_geo(item) for item in geo_questions], "the stored geo question list"
        graph = _get(self.geo, "question_graph_50") or {}
        if isinstance(graph, dict):
            rows = list(graph.get("questions") or [])
            if rows:
                return [self._from_geo(item) for item in rows], "the stored question graph"
            counts = [
                int(_num(graph.get(name)) or 0)
                for name in ("supported_count", "partial_count", "unsupported_count", "conflicting_count")
            ]
            if sum(counts) > 0:
                return [], "the question-graph counters"
        return [], ""

    def _from_sandbox(self, item: Any) -> _Question:
        text = str(_get(item, "generated_question", "") or "")
        intent = _intent_bucket(f"{text} {_get(item, 'buyer_intent', '')} {_get(item, 'facet', '')}")
        gap = _clip(_get(item, "gap_analysis", "") or "")
        aspects = _get(item, "missing_aspects", None) or []
        if aspects and not gap:
            gap = "Missing aspects: " + _join([str(aspect) for aspect in aspects], 4)
        return _Question(
            str(_get(item, "question_id", "") or ""),
            text,
            _question_status(_get(item, "answerability_status"), _get(item, "is_answerable")),
            intent,
            str(_get(item, "evidence_url", "") or _get(item, "target_update_page", "") or ""),
            gap,
            "sandbox",
            str(_get(item, "facet", "") or ""),
        )

    def _from_geo(self, item: Any) -> _Question:
        if isinstance(item, dict):
            text = str(item.get("question") or item.get("generated_question") or "")
            status = _question_status(item.get("status") or item.get("answerability_status"), item.get("is_answerable"))
            url = str(item.get("evidence_url") or "")
            gap = _clip(item.get("why") or item.get("gap_analysis") or "")
            facet = str(item.get("category") or item.get("facet") or "")
            qid = str(item.get("question_key") or item.get("question_id") or "")
        else:
            text = str(_get(item, "question", "") or "")
            status = _question_status(_get(item, "status"), None)
            url = str(_get(item, "evidence_url", "") or "")
            gap = _clip(_get(item, "why", "") or "")
            facet = str(_get(item, "category", "") or "")
            qid = str(_get(item, "question_key", "") or "")
        return _Question(qid, text, status, _intent_bucket(f"{text} {facet}"), url, gap, "geo", facet)

    def _schema_types(self) -> List[str]:
        found: List[str] = []
        for name in list(_get(self.geo, "schema_types", None) or []):
            if str(name) not in found:
                found.append(str(name))
        for page in self.pages:
            for name in list(_get(page, "schema_types", None) or []):
                if str(name) not in found:
                    found.append(str(name))
        return found

    def profile_value(self, name: str) -> str:
        value = _get(self.profile, name, None)
        if value is None or value == "" or value == []:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value if str(item).strip())
        return str(value).strip()

    def where(self, status: str) -> List[_Question]:
        return [item for item in self.questions if item.status == status]

    def quotes(self, rows: Sequence[_Question], limit: int = 3) -> str:
        shown = []
        for item in list(rows)[:limit]:
            bits = [f"“{item.text or item.qid}” ({item.status}"]
            if item.url:
                bits.append(f", {item.url}")
            if item.gap:
                bits.append(f"; {_clip(item.gap, 140)}")
            bits.append(")")
            shown.append("".join(bits))
        if not shown:
            return "No question text was retained for this line."
        extra = len(rows) - len(shown)
        text = " ".join(shown)
        if extra > 0:
            text += f" {extra} more stay in the stored set."
        return text

    def coverage_sentence(self) -> str:
        if self.assessed == 0:
            if self.question_source == "the question-graph counters":
                return (
                    "Question-graph counters were stored without the question texts, so this book does not "
                    "treat that object as a usable denominator."
                )
            return (
                "No question was assessed on this run. Question coverage has no denominator. "
                "A missing question set is not zero coverage."
            )
        return (
            f"Question coverage is {self.usable} of {self.assessed} assessed questions with a usable answer "
            f"(status ANSWERABLE). Partial: {self.partial}. Unanswered: {self.unanswered}. "
            f"Conflicting: {self.conflicting}. The denominator is {self.question_source}. "
            "A completed evaluation is not, by itself, an answered question. "
            "This ratio is content readiness, not live visibility."
        )

    def live_sentence(self) -> str:
        if self.card is None:
            return (
                "No live answer-engine scorecard was stored. "
                "Google AI Overviews, Google AI Mode, and Bing Copilot stay unqueried unless a run names them. "
                "An on-page writing exercise is not a live query."
            )
        if self.runs <= 0:
            missing = _join(self.surfaces, 6)
            return (
                "No successful live answer-engine run is stored, so mention rate, citation rate, "
                "recommendation rate, and citation share stay unmeasured. A missing rate is not zero. "
                f"Surfaces left unqueried: {missing}. "
                "ChatGPT, Perplexity, Gemini, and Claude API answers are not those consumer surfaces."
            )
        engines = _join(self.engines, 8) if self.engines else "the stored engine list is empty"
        surfaces = _join(self.surfaces, 6)
        kind = self.kind or "unspecified"
        return (
            f"{self.runs} successful live run(s). Measurement kind: {kind}. Engines queried: {engines}. "
            f"Not queried: {surfaces}. "
            "An API answer can differ from the consumer product. "
            "These runs are not universal visibility across users, locations, or sessions."
        )

    def rate(self, key: str, label: str, formula: str) -> Tuple[str, str]:
        value = self.rates.get(key)
        if self.card is None or self.runs <= 0 or value is None:
            state = "NOT_TESTED" if self.card is None or self.runs <= 0 else "DATA_UNAVAILABLE"
            if self.card is not None and self.runs > 0 and value is None:
                state = "DATA_UNAVAILABLE"
            elif self.card is None or self.runs <= 0:
                state = "NOT_TESTED"
            return (
                state,
                f"{label} was not measured. {formula} {self.live_sentence()} "
                "A missing rate is not zero and not a pass.",
            )
        return (
            "VERIFIED",
            f"{label} is {_pct(value)}% on this run. {formula} "
            f"The denominator is the {self.runs} valid successful response(s). "
            "One response can mention several brands and cite several sources; those outcomes are not mutually exclusive. "
            f"{self.live_sentence()}",
        )

    def recommendation(self) -> Tuple[str, str]:
        mention = self.rates.get("mention")
        mention_bit = (
            f"Mention rate on this run is {_pct(mention)}%, and a mention is not a recommendation."
            if mention is not None
            else "Mention rate was not measured either, and it would still not be a recommendation rate."
        )
        state = "NOT_TESTED" if self.card is None or self.runs <= 0 else "DATA_UNAVAILABLE"
        return (
            state,
            "Brand recommendation rate was not measured. The stored scorecard has mention and citation fields, "
            f"not a recommendation flag. {mention_bit} {self.live_sentence()}",
        )

    def profile_line(self, label: str, *names: str) -> Tuple[str, str]:
        found = [(name, self.profile_value(name)) for name in names]
        filled = [f"{name}: {value}" for name, value in found if value]
        if not filled:
            return (
                "DATA_UNAVAILABLE",
                f"{label} is not in the stored business profile. An empty profile field is not a confirmed absence of the fact.",
            )
        status = str(_get(self.profile, "evidence_status", "") or "unspecified")
        return (
            "INFERRED",
            f"The stored business profile records {'; '.join(filled)}. Profile evidence status: {status}. "
            "This is the audit's business context, not a description returned by an answer engine.",
        )

    def gap_examples(self) -> str:
        rows = self.where("UNANSWERABLE") + self.where("CONFLICTING") + self.where("PARTIAL")
        if not rows:
            if self.assessed:
                return "Every assessed question has a usable answer in the stored set."
            return "There is no assessed question to rank."
        return self.quotes(rows, 4)

    def intent_count(self, bucket: str) -> int:
        return sum(1 for item in self.questions if item.intent == bucket)

    def pages_with(self, predicate) -> List[str]:
        found = []
        for page in self.pages:
            url = str(_get(page, "url", "") or "")
            if url and predicate(page):
                found.append(url)
        return found

    def response_times(self) -> List[float]:
        times = []
        for page in self.pages:
            value = _num(_get(page, "ttfb_ms"))
            if value and value > 0:
                times.append(value)
        return times

    def ttfb_sentence(self) -> str:
        times = self.response_times()
        if not times:
            return "Crawl response time was not recorded. Response time is not a Core Web Vital."
        shown = ", ".join(f"{value:g} ms" for value in times[:5])
        return (
            f"Crawl response time on the sample: {shown}. "
            "This is server response timing, not Largest Contentful Paint, and not a field Core Web Vital."
        )

    def field_cwv(self) -> Optional[str]:
        rows = []
        for page in self.pages:
            field = _get(page, "field_performance")
            if not field or not _get(field, "has_field_data"):
                continue
            bits = [str(_get(page, "url", "") or "page")]
            for label, key in (("LCP", "p75_lcp_ms"), ("INP", "p75_inp_ms"), ("CLS", "p75_cls")):
                value = _num(_get(field, key))
                if value is not None:
                    bits.append(f"{label} p75 {value:g}")
            rows.append(" ".join(bits))
        if not rows:
            return None
        return "Field Core Web Vitals were stored. " + _join(rows, 3)

    def lab_lcp(self) -> Optional[str]:
        rows = []
        for page in self.pages:
            lab = _get(page, "lab_performance")
            version = str(_get(lab, "lighthouse_audit_version", "") or "")
            lcp = _num(_get(lab, "lcp_ms"))
            if version and lcp is not None:
                rows.append(f"{_get(page, 'url', 'page')} LCP {lcp:g} ms (Lighthouse {version})")
        if not rows:
            return None
        return "Lab Largest Contentful Paint was stored. " + _join(rows, 3) + " Lab data is not field CrUX data."

    def indexable_sentence(self) -> str:
        if not self.pages:
            return "No crawled page is available, so indexability was not judged."
        blocked = []
        for page in self.pages:
            robots = str(_get(page, "robots_meta", "") or "").lower()
            header = str(_get(page, "x_robots_tag", "") or "").lower()
            if _get(page, "is_indexable") is False or "noindex" in robots or "noindex" in header:
                blocked.append(str(_get(page, "url", "") or "page"))
        if blocked:
            return f"{len(blocked)} crawled page(s) are marked non-indexable: {_join(blocked, 4)}."
        return f"All {self.crawled} crawled page(s) are marked indexable in the crawl record. This is the sample, not the whole site."

    def robots_sentence(self) -> Tuple[str, str]:
        if self.manifest is None or self.crawled == 0:
            return ("NOT_TESTED", "robots.txt was not checked because no crawl manifest with pages was stored.")
        if _get(self.manifest, "robots_txt_found"):
            return ("CLEAN_SAMPLE", "robots.txt was found during the crawl. Bot-specific allow or deny still requires a measured robots parse.")
        return ("ISSUE_SAMPLE", "robots.txt was not found in the crawl. Answer engines that fetch this host have no robots file in the stored evidence.")

    def sitemap_sentence(self) -> Tuple[str, str]:
        if self.manifest is None or self.crawled == 0:
            return ("NOT_TESTED", "No crawl manifest was stored, so sitemap coverage was not checked.")
        if _get(self.manifest, "sitemap_found"):
            url = str(_get(self.manifest, "sitemap_url", "") or "the recorded sitemap")
            return ("CLEAN_SAMPLE", f"An XML sitemap was recorded at {url}.")
        return ("ISSUE_SAMPLE", "No XML sitemap was recorded for this crawl.")

    def schema_sentence(self) -> str:
        if not self.schema_types:
            if self.crawled == 0:
                return "Structured data was not inspected because no page was crawled."
            return (
                "No schema type was recorded on the crawled pages. "
                "Schema can clarify entities. It does not make an answer engine select or cite a page."
            )
        quality = _num(self.cross.get("quality_score")) if self.cross else None
        quality_bit = f" Schema cross-check quality is {_pct(quality)} of 100 stated properties." if quality is not None else ""
        return (
            f"Schema types in the sample: {_join(self.schema_types, 8)}.{quality_bit} "
            "Presence of a type, including FAQPage, does not guarantee a rich result or a citation."
        )

    def entity_sentence(self) -> Tuple[str, str]:
        surfaces = int(_num(self.entity.get("surfaces_analyzed_count")) or 0) if self.entity else 0
        if surfaces <= 0:
            return (
                "NOT_TESTED",
                "Cross-page entity consistency was not measured. A brand name in the profile is not that test.",
            )
        score = _num(self.entity.get("overall_consistency_score"))
        risk = str(self.entity.get("fragmentation_risk") or "unspecified")
        brand = str(self.entity.get("canonical_brand") or "unspecified")
        discrepancies = list(self.entity.get("discrepancies") or [])
        score_bit = f"{_pct(score)} / 100" if score is not None else "unspecified"
        state = "ISSUE_SAMPLE" if discrepancies else "CLEAN_SAMPLE"
        detail = f"{len(discrepancies)} discrepancy record(s)." if discrepancies else "No discrepancy record was stored."
        return (
            state,
            f"Entity consistency across {surfaces} surface(s) is {score_bit}, risk {risk}, canonical brand “{brand}”. {detail} "
            "This is source consistency, not a live answer about the brand.",
        )

    def claims_sentence(self) -> Tuple[str, str]:
        total = int(_num(self.claims.get("total_claims_extracted")) or 0) if self.claims else 0
        if total <= 0:
            return ("NOT_TESTED", "No claim inventory was extracted from the crawled pages.")
        citable = int(_num(self.claims.get("citable_claims_count")) or 0)
        fluff = int(_num(self.claims.get("fluff_claims_count")) or 0)
        verifiability = _num(self.claims.get("aggregate_verifiability_score"))
        bit = f" Aggregate verifiability is {_pct(verifiability)} / 100." if verifiability is not None else ""
        state = "ISSUE_SAMPLE" if fluff else "CLEAN_SAMPLE"
        return (
            state,
            f"The claim extract found {total} claim(s), {citable} marked citable and {fluff} marked fluff.{bit} "
            "These are on-page claims. They are not answer-engine citations.",
        )

    def passage_sentence(self) -> Tuple[str, str]:
        scanned = int(_num(self.passages.get("total_passages_scanned")) or 0) if self.passages else 0
        if scanned <= 0:
            return ("NOT_TESTED", "No passage extractability scan was stored.")
        ready = _num(self.passages.get("citation_readiness_score"))
        high = int(_num(self.passages.get("highly_citable_count")) or 0)
        weak = int(_num(self.passages.get("weak_count")) or 0)
        score_bit = f" The on-page citation-readiness figure is {_pct(ready)} / 100." if ready is not None else ""
        return (
            "INFERRED",
            f"{scanned} passage(s) were scanned, {high} marked highly citable and {weak} marked weak.{score_bit} "
            "That figure is extractability of the source. It is not a live citation rate.",
        )

    def gsc_sentence(self) -> Tuple[str, str]:
        if self.gsc_state != "MEASURED":
            return (
                "DATA_UNAVAILABLE",
                f"Search Console state is {self.gsc_state}. Question queries, clicks, and impressions were not read. "
                "A disconnected connector is not zero clicks.",
            )
        return (
            "VERIFIED",
            "Search Console is MEASURED for this report. Clicks are not conversions, and query rows are not an answer-engine test.",
        )

    def ga4_sentence(self) -> Tuple[str, str]:
        if self.ga4_state != "MEASURED":
            return (
                "DATA_UNAVAILABLE",
                f"GA4 state is {self.ga4_state}. Sessions, landing pages, and key events were not read. "
                "A missing key-event field is not zero conversions. Search Console clicks are not conversions.",
            )
        key_events = self.analytics.get("key_events")
        if key_events is None:
            return (
                "DATA_UNAVAILABLE",
                "GA4 is connected, and the key_events field is absent. Absent is not zero. Revenue was not attributed.",
            )
        return (
            "VERIFIED",
            f"GA4 key events are {key_events}. This is a key-event count, not revenue, and not an AI-referral conversion rate.",
        )

    def bakeoff_sentence(self) -> str:
        if self.bakeoff is None:
            return "No competitor answer comparison with stored evaluations was attached."
        domain = str(_get(self.bakeoff, "competitor_domain", "") or "the named competitor")
        return (
            f"On-page bake-off versus {domain}: target wins {_get(self.bakeoff, 'target_wins', 0)}, "
            f"competitor wins {_get(self.bakeoff, 'competitor_wins', 0)}, ties {_get(self.bakeoff, 'ties', 0)}, "
            f"across {len(self.bake_items)} evaluation(s). This is a stored comparison of answers, not a live citation share."
        )

    def contradiction_sentence(self) -> str:
        if not self.contradictions:
            return "No contradiction record was stored."
        shown = []
        for item in self.contradictions[:3]:
            shown.append(_clip(f"{_get(item, 'contradiction_type', 'conflict')}: {_get(item, 'reason', '')}", 160))
        return f"{len(self.contradictions)} contradiction record(s). {_join(shown, 3)}"

    def languages(self) -> List[str]:
        found = []
        for page in self.pages:
            lang = str(_get(page, "html_lang", "") or "").strip()
            if lang and lang not in found:
                found.append(lang)
            for code in list(_get(page, "hreflang_tags", None) or []):
                if str(code) not in found:
                    found.append(str(code))
        return found

    def fix_for(self, item: _Question) -> str:
        if item.gap:
            return f"Add a fact-checked answer for “{_clip(item.text, 80)}”. Stored gap: {_clip(item.gap, 160)}."
        return f"Add a fact-checked answer, with conditions and a source, for “{_clip(item.text, 80)}”."


def _schema_validation_ran(obj: Any) -> bool:
    if obj is None:
        return False
    if int(_num(_get(obj, "total_entities_detected")) or 0) > 0:
        return True
    if int(_num(_get(obj, "total_pages_with_schema")) or 0) > 0:
        return True
    if list(_get(obj, "issues", None) or []):
        return True
    return bool(str(_get(obj, "summary", "") or "").strip())


def _is_note(finding: Any) -> bool:
    severity = str(_get(finding, "severity", "") or "").upper()
    if severity in {"INFO", "INFORMATIONAL"}:
        return True
    blob = f"{_get(finding, 'title', '')} {_get(finding, 'description', '')}".lower()
    return any(phrase in blob for phrase in _NOTE_PHRASES)


def _is_guessing(finding: Any) -> bool:
    return str(_get(finding, "confidence_rubric", "") or "").upper() == "GUESSING"


def _is_defect(finding: Any) -> bool:
    return not _is_note(finding) and not _is_guessing(finding)


def _public_description(finding: Any) -> str:
    desc = str(_get(finding, "description", "") or "")
    if "SINGLE_SOURCE_UNVERIFIED" in desc or desc.lower().startswith("single_source"):
        return "Observed in the crawled HTML. A second evidence source was not attached, so confidence stays medium."
    desc = re.sub(r"\bext_[A-Za-z0-9_]+\b", "", desc)
    desc = desc.replace("SINGLE_SOURCE_UNVERIFIED", "")
    return re.sub(r"\s+", " ", desc).strip()


def _public_recommendation(finding: Any) -> str:
    rec = str(_get(finding, "suggested_fix", "") or _get(finding, "recommendation", "") or "")
    if not rec.strip() or "implement recommended architectural fix" in rec.lower():
        return "No specific change was written for this finding."
    return rec.strip()


def _issue(facts: _Facts, scope: str, why: str, fix: str) -> str:
    return f"Scope: {scope}. Why it matters: {why} Recommended fix: {fix}{_LIMIT}"


def _unt(label: str, because: str) -> Tuple[str, str]:
    return ("NOT_TESTED", f"{label} was not tested. {because}")


def _gap(label: str, because: str) -> Tuple[str, str]:
    return ("DATA_UNAVAILABLE", f"{label} is data unavailable. {because}")


def _need_questions(facts: _Facts, label: str) -> Optional[Tuple[str, str]]:
    if facts.assessed:
        return None
    return _unt(label, facts.coverage_sentence() + " " + _SEPARATION)


def _s01(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "overall"):
        code = "ISSUE_SAMPLE" if facts.assessed and facts.usable < facts.assessed else ("NOT_TESTED" if facts.assessed == 0 else "CLEAN_SAMPLE")
        return (code, f"{facts.coverage_sentence()} {facts.live_sentence()} {facts.sample} {_SEPARATION}")
    if _has(label, "brand presence"):
        return facts.rate("mention", "Brand mention rate", "Mentions divided by valid responses.")
    if _has(label, "tested versus") or _has(label, "questions tested"):
        return (
            "VERIFIED" if facts.assessed else "NOT_TESTED",
            facts.coverage_sentence() + " Questions outside this stored set were not tested.",
        )
    if _has(label, "recommend"):
        return facts.recommendation()
    if _has(label, "cite the brand"):
        return facts.rate("citation", "Citation rate", "Responses with at least one qualifying citation to the brand domain, divided by valid responses.")
    if _has(label, "competitors instead") or _has(label, "cite competitors"):
        return facts.rate("competitor", "Competitor visibility", "This is the stored competitor-visibility field, not citation share.")
    if _has(label, "missing and inaccurate") or _has(label, "inaccurate"):
        if facts.conflicting or facts.contradictions:
            return (
                "ISSUE_SAMPLE",
                f"{facts.conflicting} assessed question(s) are conflicting. {facts.contradiction_sentence()} {facts.gap_examples()} "
                + _issue(facts, "the stored conflicting questions", "An answer engine can repeat the conflict.", "Resolve the conflicting statements on the cited pages."),
            )
        if facts.unanswered or facts.partial:
            return ("ISSUE_SAMPLE", f"Missing answers in the assessed set. {facts.gap_examples()}")
        if facts.assessed:
            return ("CLEAN_SAMPLE", facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    if _has(label, "highest-priority") or _has(label, "coverage gap"):
        if facts.assessed and (facts.unanswered or facts.partial or facts.conflicting):
            return ("ISSUE_SAMPLE", "Priority gaps are the unanswered, partial, and conflicting questions. " + facts.gap_examples())
        if facts.assessed:
            return ("CLEAN_SAMPLE", "No coverage gap is stored inside the assessed set. " + facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    if _has(label, "commercial"):
        profile = facts.profile_line("Commercial context", "business_model", "value_proposition", "primary_cta")
        return (profile[0] if facts.assessed == 0 else "INFERRED", profile[1] + " " + facts.coverage_sentence() + " No revenue figure is inferred from these gaps.")
    if _has(label, "30/60/90") or _has(label, "action plan"):
        return _unt(
            label,
            "No 30/60/90 calendar is invented. The work queue is the stored gap list: " + facts.gap_examples(),
        )
    return ("INFERRED", facts.coverage_sentence() + " " + facts.live_sentence())


def _s02(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "question coverage"):
        if facts.assessed == 0:
            return _unt(label, facts.coverage_sentence())
        state = "CLEAN_SAMPLE" if facts.usable == facts.assessed else "ISSUE_SAMPLE"
        return (state, "Formula: relevant questions with a usable, verified answer ÷ relevant questions assessed. " + facts.coverage_sentence())
    if _has(label, "completeness"):
        if facts.assessed == 0:
            return _unt(label, "Answer completeness needs assessed questions and required elements. Neither weighted element list was stored.")
        return (
            "INFERRED",
            "A weighted required-element score was not stored. What is stored: "
            f"{facts.usable} of {facts.assessed} are complete enough to be ANSWERABLE, {facts.partial} are partial, "
            f"and a partial answer does not satisfy the completeness formula. {facts.gap_examples()}",
        )
    if _has(label, "clarity") or _has(label, "extractability"):
        code, text = facts.passage_sentence()
        if facts.extractability is not None:
            return (
                "INFERRED",
                f"On-page extractability is {_pct(facts.extractability)} / 100. {text} {_SEPARATION}",
            )
        return code, text + " " + _SEPARATION
    if _has(label, "factual accuracy"):
        if facts.rates.get("entity_accuracy") is not None:
            return facts.rate("entity_accuracy", "Live entity accuracy", "Verified correct brand claims in live responses ÷ brand claims assessed in those responses.")
        return facts.claims_sentence()
    if _has(label, "source attribution") or _has(label, "citation quality"):
        if facts.rates.get("citation_accuracy") is not None:
            return facts.rate(
                "citation_accuracy",
                "Citation accuracy",
                "Verified relevant and correctly attributed citations ÷ citations assessed.",
            )
        return (
            "NOT_TESTED",
            "Citation accuracy stays blank until a span check on a live citation is stored. Passage extractability does not fill this score.",
        )
    if _has(label, "entity consistency"):
        return facts.entity_sentence()
    if _has(label, "accessibility") or _has(label, "answer-source"):
        robots = facts.robots_sentence()
        return (robots[0] if facts.crawled else "NOT_TESTED", f"{facts.sample} {facts.indexable_sentence()} {robots[1]}")
    if _has(label, "structured data"):
        if facts.crawled == 0 and not facts.schema_types:
            return _unt(label, facts.schema_sentence())
        state = "CLEAN_SAMPLE" if facts.schema_types else "ISSUE_SAMPLE"
        return (state, facts.schema_sentence())
    if _has(label, "search answer appearance"):
        return _unt(label, "Featured snippets, People Also Ask, and other search-answer boxes were not collected. " + facts.live_sentence())
    if _has(label, "live answer visibility"):
        return facts.rate("mention", "Live mention rate", "Valid tested responses mentioning the brand ÷ valid responses. This is not a recommendation rate.")
    if _has(label, "citation coverage"):
        return facts.rate("citation", "Citation rate", "Valid responses containing at least one qualifying citation to the brand domain ÷ valid responses.")
    if _has(label, "competitive answer share"):
        cite = facts.rates.get("citation")
        comp = facts.rates.get("competitor")
        if cite is None and comp is None:
            return (
                "NOT_TESTED",
                "Citation share was not calculated. It needs qualifying citations to the brand and to all tracked domains. "
                + facts.bakeoff_sentence() + " " + facts.live_sentence(),
            )
        return (
            "DATA_UNAVAILABLE",
            "Competitor visibility may be stored, and citation share still needs a denominator of qualifying citations to all tracked domains. "
            "Those inputs were not both stored. " + facts.live_sentence(),
        )
    if _has(label, "confidence") or _has(label, "data coverage"):
        return (
            "INFERRED",
            f"{facts.sample} {facts.coverage_sentence()} {facts.live_sentence()} "
            f"Search Console: {facts.gsc_state}. GA4: {facts.ga4_state}. {_SEPARATION}",
        )
    return ("INFERRED", facts.coverage_sentence() + " " + _SEPARATION)


def _s03(facts: _Facts, label: str) -> Tuple[str, str]:
    mapping = (
        (("business model", "core offering"), ("business_model", "industry", "niche")),
        (("products",), ("products", "services")),
        (("persona", "audience"), ("target_audience",)),
        (("countries", "languages", "regions"), ("geography",)),
        (("positioning", "differentiation"), ("value_proposition",)),
        (("pricing", "availability", "eligibility"), ("primary_cta",)),
        (("brand facts", "approved claims"), ("business_name", "value_proposition")),
    )
    for keys, names in mapping:
        if _has(label, *keys):
            return facts.profile_line(label, *names)
    if _has(label, "high-value customer") or _has(label, "buyer journey") or _has(label, "support and troubleshooting"):
        blocked = _need_questions(facts, label)
        if blocked:
            return blocked
        return ("INFERRED", f"{facts.assessed} questions were generated for this business from {facts.question_source}. {facts.coverage_sentence()}")
    if _has(label, "high-risk"):
        return (
            "ISSUE_SAMPLE" if facts.contradictions or facts.conflicting else "NOT_TESTED",
            facts.contradiction_sentence() + " " + facts.claims_sentence()[1] + " No extra high-risk claim was inferred.",
        )
    if _has(label, "platform") or _has(label, "surface"):
        sim = facts.simulation or "not attached"
        return (
            "INFERRED",
            f"{facts.live_sentence()} The on-page engine matrix mode is {sim}. "
            "SIMULATION_ONLY is a writing exercise, not a query of ChatGPT, Perplexity, Gemini, Copilot, or Google AI Overviews.",
        )
    return facts.profile_line(label, "business_name", "industry")


def _s04(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "no useful answer"):
        if facts.unanswered:
            return ("ISSUE_SAMPLE", f"{facts.unanswered} assessed question(s) have no usable answer. {facts.quotes(facts.where('UNANSWERABLE'), 3)} " + _issue(facts, "those questions", "The source cannot satisfy them.", facts.fix_for(facts.where('UNANSWERABLE')[0])))
        if facts.assessed:
            return ("CLEAN_SAMPLE", "No assessed question is unanswered. " + facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    if _has(label, "incorrect") or _has(label, "outdated"):
        if facts.conflicting or facts.contradictions:
            return ("ISSUE_SAMPLE", facts.contradiction_sentence() + " " + facts.quotes(facts.where("CONFLICTING"), 2))
        return _unt(label, "No conflicting answer and no contradiction record were stored. Age of a statistic was not dated.")
    if _has(label, "recommendation"):
        return facts.recommendation()
    if _has(label, "competitors repeatedly"):
        text = facts.bakeoff_sentence() + " " + facts.live_sentence()
        if facts.bakeoff is None and facts.rates.get("competitor") is None:
            return _unt(label, text)
        return ("INFERRED", text)
    if _has(label, "unsupported"):
        return facts.claims_sentence()
    if _has(label, "contradict"):
        if facts.contradictions or facts.conflicting:
            return ("ISSUE_SAMPLE", facts.contradiction_sentence())
        return ("NOT_TESTED", facts.contradiction_sentence() + " An empty contradiction list is not a completed consistency audit.")
    if _has(label, "specification") or _has(label, "evidence for factual"):
        return facts.claims_sentence()
    if _has(label, "unavailable") or _has(label, "inaccessible"):
        return facts.robots_sentence() if facts.crawled else _unt(label, facts.sample)
    if _has(label, "pricing") or _has(label, "policy"):
        priced = [item for item in facts.questions if item.intent == "pricing"]
        if not priced:
            return _unt(label, "No pricing question was in the assessed set, and no price date was checked. Stale pricing is not assumed.")
        bad = [item for item in priced if item.status != "ANSWERABLE"]
        if bad:
            return ("ISSUE_SAMPLE", f"{len(bad)} of {len(priced)} pricing question(s) lack a usable answer. {facts.quotes(bad, 2)}")
        return ("CLEAN_SAMPLE", f"All {len(priced)} assessed pricing question(s) have a usable answer. Currency freshness was not separately dated.")
    if _has(label, "misleading") or _has(label, "generated"):
        return facts.rate("hallucination", "Hallucination rate", "This rate counts inaccurate generated answers in the live runs. It is blank when those runs do not exist.")
    if _has(label, "sensitive") or _has(label, "regulated"):
        return _unt(label, "No regulated-claim review was run. Industry text in the profile is not that review.")
    return _unt(label, facts.coverage_sentence())


def _s05(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.bakeoff is None and facts.rates.get("competitor") is None:
        return _unt(label, facts.bakeoff_sentence() + " " + facts.live_sentence() + " Competitor names are not invented.")
    if _has(label, "opportunity"):
        gaps = facts.where("UNANSWERABLE") + facts.where("PARTIAL")
        return ("INFERRED", facts.bakeoff_sentence() + " Brand-relevant gaps: " + facts.quotes(gaps, 3))
    return ("INFERRED", facts.bakeoff_sentence() + " " + facts.live_sentence())


def _s06(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "time to impact") or _has(label, "effort") or _has(label, "confidence in the recommendation"):
        return _unt(label, "Effort, confidence intervals, and time to impact are not estimated. " + facts.gap_examples())
    if _has(label, "search demand"):
        return facts.gsc_sentence()
    if facts.assessed == 0:
        return _unt(label, facts.coverage_sentence())
    return (
        "INFERRED",
        "Priority follows unanswered, then conflicting, then partial questions. Search demand is separate. "
        + facts.gsc_sentence()[1] + " " + facts.gap_examples() + " No traffic or revenue forecast is attached.",
    )


def _s07(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "search console"):
        return facts.gsc_sentence()
    if _has(label, "collection date") or _has(label, "source and collection"):
        source = facts.question_source or "no question source"
        return ("INFERRED", f"Question source: {source}. Report timestamp: {facts.generated_at}. Autocomplete, People Also Ask, and forums were not given their own collection dates.")
    if _has(label, "live answer"):
        return ("VERIFIED" if facts.runs > 0 else "NOT_TESTED", facts.live_sentence() + " The assessed question inventory is " + (facts.question_source or "not stored") + ".")
    if _has(label, "competitor question"):
        if facts.bake_items:
            return ("INFERRED", facts.bakeoff_sentence())
        return _unt(label, facts.bakeoff_sentence())
    if _has(label, "sandbox") or _has(label, "relevant search") or _has(label, "discovered from"):
        blocked = _need_questions(facts, label)
        return blocked or ("INFERRED", facts.coverage_sentence())
    return _unt(
        label,
        "This source was not collected. The assessed set, when present, is "
        + (facts.question_source or "absent")
        + ". That set is not People Also Ask, autocomplete, a support desk, or a forum export. "
        + facts.coverage_sentence(),
    )


def _s08(facts: _Facts, label: str) -> Tuple[str, str]:
    blocked = _need_questions(facts, label)
    if blocked:
        return blocked
    bucket = "unclassified"
    for name, _needles in _INTENT_RULES:
        if name.split("-")[0] in label.lower() or name in label.lower():
            bucket = name
            break
    if _has(label, "definition"):
        bucket = "definition"
    elif _has(label, "explanatory"):
        bucket = "explanatory"
    elif _has(label, "how-to") or _has(label, "how to"):
        bucket = "how-to"
    elif _has(label, "troubleshoot"):
        bucket = "troubleshooting"
    elif _has(label, "comparison"):
        bucket = "comparison"
    elif _has(label, "best-product") or _has(label, "best-service") or _has(label, "best"):
        bucket = "best"
    elif _has(label, "recommendation"):
        bucket = "recommendation"
    elif _has(label, "pricing"):
        bucket = "pricing"
    elif _has(label, "eligibility") or _has(label, "qualification"):
        bucket = "eligibility"
    elif _has(label, "location") or _has(label, "availability"):
        bucket = "location"
    elif _has(label, "transactional"):
        bucket = "transactional"
    elif _has(label, "navigational"):
        bucket = "navigational"
    elif _has(label, "opinion") or _has(label, "evaluation"):
        bucket = "opinion"
    elif _has(label, "follow-up") or _has(label, "clarification"):
        return _unt(label, "Follow-up turns were not stored. The assessed set is single questions. " + facts.coverage_sentence())
    count = facts.intent_count(bucket)
    rows = [item for item in facts.questions if item.intent == bucket]
    return (
        "INFERRED",
        f"{count} of {facts.assessed} assessed questions match “{bucket}” by wording. "
        "This is a classification of the stored set, not proof of customer demand. "
        + facts.quotes(rows, 2),
    )


def _s09(facts: _Facts, label: str) -> Tuple[str, str]:
    blocked = _need_questions(facts, label)
    if blocked and not _has(label, "geographic"):
        return blocked
    groups: Dict[str, List[_Question]] = {}
    for item in facts.questions:
        groups.setdefault(item.facet or item.intent or "ungrouped", []).append(item)
    if _has(label, "geographic") or _has(label, "language cluster"):
        langs = facts.languages()
        return ("INFERRED" if langs or facts.profile_value("geography") else "NOT_TESTED", f"Languages in the sample: {_join(langs, 6)}. Geography on the profile: {facts.profile_value('geography') or 'not stored'}.")
    if _has(label, "unanswered"):
        empty = [name for name, rows in groups.items() if rows and all(row.status != "ANSWERABLE" for row in rows)]
        if not facts.assessed:
            return _unt(label, facts.coverage_sentence())
        if empty:
            return ("ISSUE_SAMPLE", "Facets with no usable answer: " + _join(empty, 8))
        return ("CLEAN_SAMPLE", "Every stored facet has at least one usable answer.")
    names = [f"{name} ({len(rows)})" for name, rows in list(groups.items())[:8]]
    return (
        "INFERRED",
        f"{len(groups)} group(s) by stored facet or intent, not by an embedding model. {_join(names, 8)} "
        "Duplicate wording was counted inside those groups.",
    )


def _s10(facts: _Facts, label: str) -> Tuple[str, str]:
    blocked = _need_questions(facts, label)
    if blocked:
        return blocked
    with_url = [item for item in facts.questions if item.url]
    without = [item for item in facts.questions if not item.url]
    if _has(label, "no appropriate") or _has(label, "gap"):
        if without:
            return ("ISSUE_SAMPLE", f"{len(without)} of {facts.assessed} assessed questions have no evidence URL. {facts.quotes(without, 3)}")
        return ("CLEAN_SAMPLE", f"All {facts.assessed} assessed questions have an evidence URL.")
    if _has(label, "multiple pages") or _has(label, "consolidation"):
        return ("INFERRED", f"{len(with_url)} questions point at an evidence URL. Shared URLs are visible in the question table. Pages are not merged from this count alone.")
    if without and _has(label, "existing page", "destination", "mapping"):
        return ("ISSUE_SAMPLE", f"{len(with_url)} questions map to a URL and {len(without)} do not. {facts.quotes(without, 2)}")
    return ("INFERRED", f"{len(with_url)} of {facts.assessed} questions have an evidence or target URL. {facts.quotes(with_url or facts.questions, 3)}")


def _s11(facts: _Facts, label: str) -> Tuple[str, str]:
    blocked = _need_questions(facts, label)
    if blocked:
        return blocked
    weak = facts.where("UNANSWERABLE") + facts.where("PARTIAL") + facts.where("CONFLICTING")
    if _has(label, "explicitly") or _has(label, "without requiring") or _has(label, "correct and complete") or _has(label, "actual user intent"):
        if weak:
            return ("ISSUE_SAMPLE", facts.coverage_sentence() + " " + facts.quotes(weak, 3) + _issue(facts, "the named questions and their evidence URLs", "A reader or an answer engine has to infer the answer.", facts.fix_for(weak[0])))
        return ("CLEAN_SAMPLE", facts.coverage_sentence())
    if _has(label, "consistent"):
        if facts.contradictions or facts.conflicting:
            return ("ISSUE_SAMPLE", facts.contradiction_sentence())
        return ("NOT_TESTED", "No contradiction record is stored. That is not a completed consistency audit. " + facts.contradiction_sentence())
    if _has(label, "conditions") or _has(label, "limitations") or _has(label, "terms"):
        return ("INFERRED", "Conditions and limitations are only what the stored gaps say. " + facts.gap_examples())
    if _has(label, "next useful"):
        ctas = []
        for page in facts.pages:
            ctas.extend(str(item) for item in list(_get(page, "ctas", None) or [])[:2])
        if ctas:
            return ("INFERRED", "Calls to action observed on crawled pages: " + _join(ctas, 5) + ". A call to action is not proof the answer itself is complete.")
        return _unt(label, "No call to action was stored on the crawled pages.")
    if _has(label, "facts from opinions"):
        return facts.claims_sentence()
    return ("INFERRED", facts.coverage_sentence() + " Directness of the opening sentence was not separately scored.")


def _s12(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "core answer"):
        return _s11(facts, "Does the page answer the question explicitly?")
    blocked = _need_questions(facts, label)
    if blocked and facts.crawled == 0:
        return blocked
    if _has(label, "evidence") or _has(label, "references"):
        return facts.claims_sentence()
    if _has(label, "missing information"):
        if facts.partial or facts.unanswered:
            return ("ISSUE_SAMPLE", facts.gap_examples())
        if facts.assessed:
            return ("CLEAN_SAMPLE", "No partial or unanswered question is stored. " + facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    return (
        "INFERRED",
        f"{label} was not scored as its own weighted element. "
        f"The stored substitute is answer status. {facts.coverage_sentence()} "
        "A keyword missed in a representative sample is not a sitewide absence.",
    )


def _s13(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "initial"):
        return _s02(facts, "Question coverage score")
    if _has(label, "follow-up") or _has(label, "clarification") or _has(label, "multi-step") or _has(label, "multi-turn") or _has(label, "context-dependent"):
        return _unt(label, "Multi-turn conversations were not run. Single stored questions do not prove a journey.")
    if _has(label, "purchase") or _has(label, "conversion") or _has(label, "next step"):
        count = facts.intent_count("transactional")
        if facts.assessed == 0:
            return _unt(label, facts.coverage_sentence())
        return ("INFERRED", f"{count} assessed question(s) read as transactional by wording. {facts.ga4_sentence()[1]}")
    if _has(label, "decision"):
        count = facts.intent_count("comparison") + facts.intent_count("recommendation") + facts.intent_count("pricing")
        if facts.assessed == 0:
            return _unt(label, facts.coverage_sentence())
        return ("INFERRED", f"{count} assessed question(s) are comparison, recommendation, or pricing by wording. Demand for them was not measured.")
    return _unt(label, "This journey step was not executed as a conversation. " + facts.coverage_sentence())


def _s14(facts: _Facts, label: str) -> Tuple[str, str]:
    faq = any(name.lower() == "faqpage" for name in facts.schema_types)
    if _has(label, "schema") or _has(label, "rich result") or _has(label, "eligibility"):
        if faq:
            return (
                "INFERRED",
                "FAQPage is present in the sample. That does not establish rich-result eligibility, and it does not mean an answer engine will cite the page. "
                + facts.schema_sentence(),
            )
        if facts.crawled == 0:
            return _unt(label, facts.schema_sentence())
        return ("INFERRED", "FAQPage was not recorded. " + facts.schema_sentence())
    if _has(label, "redundant") or _has(label, "duplication"):
        texts = [item.text.strip().lower() for item in facts.questions if item.text.strip()]
        dupes = len(texts) - len(set(texts))
        if facts.assessed == 0:
            return _unt(label, facts.coverage_sentence())
        if dupes:
            return ("ISSUE_SAMPLE", f"{dupes} duplicate question text(s) inside the assessed set.")
        return ("CLEAN_SAMPLE", "No duplicate question text inside the assessed set. Duplication across unfetched pages was not checked.")
    if _has(label, "accuracy") or _has(label, "genuine") or _has(label, "wording"):
        return _s11(facts, "Does the page answer the question explicitly?")
    return ("INFERRED" if facts.assessed or facts.crawled else "NOT_TESTED", facts.schema_sentence() + " " + facts.coverage_sentence())


def _s15(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "search demand"):
        return facts.gsc_sentence()
    if _has(label, "competitor"):
        return _s05(facts, label)
    if _has(label, "inaccurate"):
        return _s04(facts, "Incorrect or outdated answers")
    if _has(label, "weak"):
        rows = facts.where("PARTIAL")
        if rows:
            return ("ISSUE_SAMPLE", f"{len(rows)} partial answer(s). {facts.quotes(rows, 3)}")
        if facts.assessed:
            return ("CLEAN_SAMPLE", "No partial answer is stored. " + facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    if _has(label, "unanswered") or _has(label, "high-value") or _has(label, "brand relevance") or _has(label, "recommended question"):
        if facts.unanswered or facts.partial or facts.conflicting:
            return ("ISSUE_SAMPLE", "Coverage gaps, with business value left unmeasured: " + facts.gap_examples())
        if facts.assessed:
            return ("CLEAN_SAMPLE", facts.coverage_sentence())
        return _unt(label, facts.coverage_sentence())
    if _has(label, "conversion"):
        return _s13(facts, "Purchase or conversion next steps")
    if _has(label, "high-risk"):
        return _s04(facts, "Incorrect or outdated answers")
    if _has(label, "low-value") or _has(label, "redundant"):
        return _s14(facts, "Redundant FAQ detection")
    return _unt(label, facts.coverage_sentence())


def _heading_sentence(facts: _Facts) -> str:
    if not facts.pages:
        return "No crawled page, so heading structure was not read."
    bits = []
    for page in facts.pages[:5]:
        h1 = list(_get(page, "h1", None) or [])
        h2 = list(_get(page, "h2", None) or [])
        bits.append(f"{_get(page, 'url', 'page')}: H1 {_join([str(item) for item in h1], 2)}; H2 count {len(h2)}")
    return "Heading sample: " + _join(bits, 4)


def _s16(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.crawled == 0 and facts.assessed == 0:
        return _unt(label, facts.sample)
    if _has(label, "heading") or _has(label, "h2") or _has(label, "h3") or _has(label, "question-oriented"):
        return ("INFERRED", _heading_sentence(facts) + " A heading that is not a question can still introduce an answer. The sample is not the whole site.")
    if _has(label, "opening") or _has(label, "summary and detail"):
        return ("INFERRED", "Whether the first paragraph states the answer was not separately scored. " + facts.coverage_sentence())
    if _has(label, "table"):
        return _unt(label, "Comparison tables were not extracted as their own objects. " + facts.schema_sentence())
    if _has(label, "list") or _has(label, "step-by-step"):
        how = [item for item in facts.questions if item.intent == "how-to"]
        if how:
            return ("INFERRED", f"{len(how)} how-to question(s) are in the assessed set. {facts.quotes(how, 2)} Step markup was not extracted.")
        return _unt(label, "No how-to question is in the assessed set, and ordered lists were not extracted.")
    if _has(label, "terminology"):
        return facts.entity_sentence()
    return ("INFERRED", _heading_sentence(facts) + " " + facts.coverage_sentence())


def _s17(facts: _Facts, label: str) -> Tuple[str, str]:
    code, text = facts.passage_sentence()
    if _has(label, "pronoun") or _has(label, "abbreviation") or _has(label, "units") or _has(label, "fragment"):
        return _unt(label, "That linguistic check was not run. " + text)
    return code, text + " " + facts.coverage_sentence()


def _s18(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "contradict"):
        if facts.contradictions or facts.conflicting:
            return ("ISSUE_SAMPLE", facts.contradiction_sentence() + " " + facts.quotes(facts.where("CONFLICTING"), 2))
        if facts.assessed == 0 and not facts.claims:
            return ("NOT_TESTED", facts.contradiction_sentence() + " An empty list is not a completed cross-page fact check.")
        return ("INFERRED", "No assessed question is marked CONFLICTING. " + facts.contradiction_sentence())
    if _has(label, "outdated") or _has(label, "dates") or _has(label, "figures"):
        return _unt(label, "Statistic dates were not checked. A missing date check is not a finding that the figure is wrong.")
    code, text = facts.claims_sentence()
    if code == "NOT_TESTED" and (facts.conflicting or facts.contradictions):
        return ("ISSUE_SAMPLE", facts.contradiction_sentence())
    return code, text


def _s19(facts: _Facts, label: str) -> Tuple[str, str]:
    people = [name for name in facts.schema_types if name.lower() in {"person", "author"}]
    if _has(label, "author") or _has(label, "expertise"):
        if people:
            return ("INFERRED", "Person or author schema is in the sample: " + _join(people, 4) + ". Schema is not proof of first-hand expertise.")
        return _unt(label, "No Person or author identity was recorded. " + facts.schema_sentence())
    if _has(label, "original research") or _has(label, "testing") or _has(label, "case stud") or _has(label, "screenshot") or _has(label, "first-hand"):
        if facts.info_gain is not None:
            return ("INFERRED", f"The on-page information-gain figure is {_pct(facts.info_gain)} / 100. It is not a live citation result and not a research certificate.")
        return _unt(label, "First-hand evidence, original research, and screenshots were not inventoried.")
    return facts.claims_sentence()


def _s20(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "structured data") and facts.schema_types:
        return ("INFERRED", facts.schema_sentence() + " Date properties inside the JSON-LD were not separately validated.")
    return _unt(label, "Publication dates, offer expiry, and policy change dates were not compared with a current source. Freshness is not assumed from the crawl time. " + facts.sample)


def _s21(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.info_gain is None:
        return _unt(label, "Information gain was not measured. Repetition versus competitors is not assumed, and no uniqueness score is invented.")
    return (
        "INFERRED",
        f"On-page information gain is {_pct(facts.info_gain)} / 100. "
        "That figure is a writing-exercise signal. It is not proof of proprietary research and not a citation rate.",
    )


def _s22(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "brand name") or _has(label, "organization") or _has(label, "alias"):
        entity = facts.entity_sentence()
        profile = facts.profile_line(label, "business_name")
        return (entity[0] if entity[0] != "NOT_TESTED" else profile[0], entity[1] + " " + profile[1])
    if _has(label, "product") or _has(label, "service") or _has(label, "terminology") or _has(label, "category"):
        return facts.profile_line(label, "products", "services", "industry")
    if _has(label, "founder") or _has(label, "author"):
        return _s19(facts, "Author identity")
    if _has(label, "acronym"):
        return _unt(label, "Acronym expansion was not scanned.")
    if _has(label, "conflict") or _has(label, "ambiguous"):
        return facts.entity_sentence()
    return facts.entity_sentence()


def _s23(facts: _Facts, label: str) -> Tuple[str, str]:
    rows = [item for item in facts.questions if item.intent in {"comparison", "best", "recommendation"}]
    if not rows and _has(label, "disclosure") or _has(label, "conflict of interest"):
        return _unt(label, "Conflicts of interest and paid-placement disclosures were not reviewed.")
    if not rows:
        return _unt(label, "No comparison, best-of, or recommendation question is in the assessed set. " + facts.bakeoff_sentence())
    bad = [item for item in rows if item.status != "ANSWERABLE"]
    if bad and not _has(label, "disclosure"):
        return ("ISSUE_SAMPLE", f"{len(bad)} of {len(rows)} comparison-style questions lack a usable answer. {facts.quotes(bad, 2)} " + facts.bakeoff_sentence())
    if _has(label, "disclosure") or _has(label, "conflict of interest"):
        return _unt(label, "The comparison questions were assessed for answerability only. Disclosure language was not reviewed. " + facts.quotes(rows, 2))
    return ("CLEAN_SAMPLE", f"All {len(rows)} comparison-style questions in the assessed set have a usable answer. {facts.quotes(rows, 2)}")


def _s24(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "correction history") or _has(label, "version"):
        return ("INFERRED", f"This document is the audit dated {facts.generated_at}. A content version-control history for the site was not read.")
    return _unt(label, "Editorial workflow, fact-check ownership, and AI-assisted review policy were not collected from the site. This audit does not invent an editorial board.")


def _bot_access(facts: _Facts) -> Tuple[str, str]:
    if facts.robots_measured:
        bots = facts.bots
        return (
            "VERIFIED",
            "Robots was parsed for AI crawlers. "
            f"GPTBot allowed: {_get(bots, 'gptbot_allowed')}. "
            f"PerplexityBot allowed: {_get(bots, 'perplexitybot_allowed')}. "
            f"ClaudeBot allowed: {_get(bots, 'claudebot_allowed')}. "
            f"Google-Extended allowed: {_get(bots, 'google_extended_allowed')}. "
            "An unmeasured robots file is not treated as allowed.",
        )
    return _gap(
        "Crawler-specific access",
        "AI crawler allow or deny was not measured. A missing parse is not allowed. " + facts.robots_sentence()[1],
    )


def _s25(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "crawler-specific"):
        return _bot_access(facts)
    if _has(label, "robots"):
        return facts.robots_sentence()
    if _has(label, "http") or _has(label, "status") or _has(label, "important page"):
        if not facts.pages:
            return _unt(label, facts.sample)
        codes = [f"{_get(page, 'url', 'page')} HTTP {_get(page, 'status_code', 'unspecified')}" for page in facts.pages[:5]]
        bad = [page for page in facts.pages if int(_num(_get(page, "status_code")) or 0) >= 400]
        state = "ISSUE_SAMPLE" if bad else "CLEAN_SAMPLE"
        return (state, _join(codes, 5) + f". Non-success pages in the sample: {len(bad)}.")
    if _has(label, "authentication") or _has(label, "rate limit") or _has(label, "firewall") or _has(label, "region") or _has(label, "browser and crawler"):
        return _unt(label, "That access comparison was not run. " + facts.sample)
    if facts.crawled == 0:
        return _unt(label, facts.sample)
    return ("INFERRED", facts.sample + " " + facts.indexable_sentence())


def _s26(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "search console"):
        return facts.gsc_sentence()
    if _has(label, "versus actual answer"):
        return ("NOT_TESTED", facts.indexable_sentence() + " " + facts.live_sentence() + " Indexable HTML was not compared with a live answer appearance.")
    if facts.crawled == 0:
        return _unt(label, facts.sample)
    if _has(label, "canonical"):
        missing = facts.pages_with(lambda page: not str(_get(page, "canonical_url", "") or "").strip())
        if missing:
            return ("ISSUE_SAMPLE", f"{len(missing)} crawled page(s) have no canonical URL. {_join(missing, 4)}")
        return ("CLEAN_SAMPLE", "Every crawled page has a canonical URL in the crawl record.")
    if _has(label, "noindex") or _has(label, "robots meta") or _has(label, "x-robots") or _has(label, "indexable") or _has(label, "missing from the index"):
        blocked = facts.pages_with(lambda page: "noindex" in str(_get(page, "robots_meta", "") or "").lower() or _get(page, "is_indexable") is False)
        if blocked:
            return ("ISSUE_SAMPLE", facts.indexable_sentence())
        return ("CLEAN_SAMPLE", facts.indexable_sentence())
    return ("INFERRED", facts.indexable_sentence() + " Search Console index coverage is separate. " + facts.gsc_sentence()[1])


def _s27(facts: _Facts, label: str) -> Tuple[str, str]:
    if not facts.pages:
        return _unt(label, facts.sample)
    modes = [f"{_get(page, 'url', 'page')} {_get(page, 'render_mode', 'unspecified')}" for page in facts.pages[:5]]
    if _has(label, "hydration") or _has(label, "lazy") or _has(label, "accordion") or _has(label, "hidden") or _has(label, "mobile"):
        return _unt(label, "That render failure mode was not tested. Stored render modes: " + _join(modes, 4))
    if _has(label, "structured data"):
        return ("INFERRED", facts.schema_sentence())
    return ("INFERRED", "Stored render modes: " + _join(modes, 4) + ". A static render mode is the crawl's record, not a second browser session.")


def _s28(facts: _Facts, label: str) -> Tuple[str, str]:
    if not facts.pages and facts.manifest is None:
        return _unt(label, facts.sample)
    if _has(label, "orphan"):
        orphans = list(_get(facts.manifest, "orphan_urls", None) or [])
        if facts.manifest is None:
            return _unt(label, "No crawl manifest, so orphan URLs were not listed.")
        if orphans:
            return ("ISSUE_SAMPLE", f"{len(orphans)} orphan URL(s) recorded. {_join([str(item) for item in orphans], 4)}")
        return ("CLEAN_SAMPLE", "The crawl manifest records no orphan URL. The sample can still miss links outside the fetched pages.")
    if _has(label, "broken") or _has(label, "redirect"):
        return _unt(label, "A full broken-link crawl was not attached. HTTP status of fetched pages is in the technical appendix.")
    total_links = 0
    for page in facts.pages:
        total_links += len(list(_get(page, "internal_links", None) or []))
    return ("INFERRED", f"Internal links recorded on crawled pages: {total_links}. {facts.sample} Click depth and anchor quality were not given a separate scored audit in this chapter.")


def _s29(facts: _Facts, label: str) -> Tuple[str, str]:
    wanted = ""
    for name in ("Organization", "Person", "Article", "BlogPosting", "BreadcrumbList", "Product", "Offer", "LocalBusiness", "VideoObject", "FAQ"):
        if name.lower() in label.lower():
            wanted = name
            break
    if wanted:
        present = [name for name in facts.schema_types if wanted.lower() in name.lower()]
        if present:
            return ("INFERRED", f"{wanted} appears in the sample as {_join(present, 4)}. " + facts.schema_sentence())
        if facts.crawled == 0 and not facts.schema_types:
            return _unt(label, facts.schema_sentence())
        return ("INFERRED", f"{wanted} was not recorded in the sample. That absence is the sample, not a rich-result failure. " + facts.schema_sentence())
    if _has(label, "invalid") or _has(label, "duplicate") or _has(label, "misleading"):
        if facts.schema_validation is None:
            conflicts = list(facts.cross.get("conflicts") or [])
            if conflicts:
                return ("ISSUE_SAMPLE", f"{len(conflicts)} schema conflict(s) in the cross-check. " + facts.schema_sentence())
            return _unt(label, "Schema syntax validation was not stored. " + facts.schema_sentence())
        errors = int(_num(_get(facts.schema_validation, "entities_with_errors_count")) or 0)
        state = "ISSUE_SAMPLE" if errors else "CLEAN_SAMPLE"
        return (state, f"Schema validation errors: {errors}. {_get(facts.schema_validation, 'summary', '')} " + facts.schema_sentence())
    if _has(label, "eligibility") or _has(label, "limitation") or _has(label, "does not guarantee"):
        return ("INFERRED", facts.schema_sentence())
    if facts.schema_types:
        return ("INFERRED", facts.schema_sentence())
    if facts.crawled:
        return ("ISSUE_SAMPLE", facts.schema_sentence())
    return _unt(label, facts.schema_sentence())


def _s30(facts: _Facts, label: str) -> Tuple[str, str]:
    if not facts.pages:
        return _unt(label, facts.sample)
    if _has(label, "title"):
        titles = [f"{_get(page, 'url', 'page')}: {_clip(_get(page, 'title', '') or 'missing title', 80)}" for page in facts.pages[:4]]
        missing = [page for page in facts.pages if not str(_get(page, "title", "") or "").strip()]
        state = "ISSUE_SAMPLE" if missing else "CLEAN_SAMPLE"
        return (state, _join(titles, 4))
    if _has(label, "heading"):
        return ("INFERRED", _heading_sentence(facts))
    if _has(label, "table") or _has(label, "landmark") or _has(label, "accessible name") or _has(label, "machine-readable date"):
        return _unt(label, "That HTML structure check was not extracted. " + _heading_sentence(facts))
    return ("INFERRED", _heading_sentence(facts) + " " + facts.sample)


def _s31(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "core web") or _has(label, "largest contentful") or _has(label, "layout stability"):
        field = facts.field_cwv()
        lab = facts.lab_lcp()
        if field:
            return ("VERIFIED", field + " " + facts.ttfb_sentence())
        if lab and _has(label, "largest contentful", "core web"):
            return ("VERIFIED", lab + " " + facts.ttfb_sentence())
        return _unt(label, "Field Core Web Vitals were not measured, and no Lighthouse version with LCP was stored. " + facts.ttfb_sentence())
    if _has(label, "latency") or _has(label, "resource") or _has(label, "performance of documentation"):
        if not facts.pages:
            return _unt(label, facts.ttfb_sentence())
        return ("INFERRED", facts.ttfb_sentence())
    if _has(label, "accessibility") or _has(label, "readability"):
        missing_alt = sum(int(_num(_get(page, "images_without_alt")) or 0) for page in facts.pages)
        if facts.crawled == 0:
            return _unt(label, "No page was crawled. Automated screening is not a WCAG certificate.")
        state = "ISSUE_SAMPLE" if missing_alt else "CLEAN_SAMPLE"
        return (state, f"Images without alt text in the sample: {missing_alt}. This is an automated screen, not a WCAG certificate, and not an answer-engine score.")
    if _has(label, "mobile") or _has(label, "interstitial") or _has(label, "navigation clarity"):
        return _unt(label, "That experience check was not run. " + facts.sample)
    return _unt(label, facts.ttfb_sentence())


def _s32(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "sitemap"):
        return facts.sitemap_sentence()
    if _has(label, "canonical"):
        return _s26(facts, "Canonical URL correctness")
    if _has(label, "international") or _has(label, "hreflang"):
        return _s39(facts, "hreflang and canonical consistency")
    if _has(label, "pagination") or _has(label, "versioned documentation") or _has(label, "migration"):
        return _unt(label, "That URL-architecture check was not run. " + facts.sample)
    if not facts.pages:
        return _unt(label, facts.sample)
    urls = [str(_get(page, "url", "") or "") for page in facts.pages[:5]]
    return ("INFERRED", "Fetched URLs: " + _join(urls, 5) + ". " + facts.sample)


def _platform_absent(facts: _Facts, label: str, surface: str) -> Tuple[str, str]:
    return _unt(
        label,
        f"{surface} was not queried on this run. {facts.live_sentence()} "
        "The on-page matrix does not stand in for this surface. "
        + (f"Matrix mode: {facts.simulation}. " if facts.simulation else ""),
    )


def _s33(facts: _Facts, label: str) -> Tuple[str, str]:
    return _platform_absent(facts, label, "Featured snippets")


def _s34(facts: _Facts, label: str) -> Tuple[str, str]:
    return _platform_absent(facts, label, "People Also Ask")


def _s35(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "ai overview") or _has(label, "ai mode") or _has(label, "featured"):
        return _platform_absent(facts, label, "Google AI Overviews, AI Mode, and featured snippets")
    named = {item.lower() for item in facts.engines}
    if facts.runs > 0 and any("google" in item for item in named):
        return ("VERIFIED", "A queried engine name contains Google. " + facts.live_sentence() + " Confirm the row before calling it AI Overviews or AI Mode.")
    return _platform_absent(facts, label, "Google answer surfaces")


def _s36(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.simulation == "SIMULATION_ONLY" and facts.runs <= 0:
        return (
            "NOT_TESTED",
            f"{label} was not a live query. The per-engine matrix is SIMULATION_ONLY, an on-page writing exercise. "
            + facts.live_sentence(),
        )
    if facts.runs <= 0:
        return _platform_absent(facts, label, "ChatGPT, Perplexity, Gemini, Copilot, and Claude consumer surfaces")
    return (
        "VERIFIED" if _has(label, "coverage", "mention", "citation", "search-enabled", "difference") else "INFERRED",
        facts.live_sentence() + " Recommendation context was not a separate field. " + facts.recommendation()[1],
    )


def _s37(facts: _Facts, label: str) -> Tuple[str, str]:
    return _unt(label, "Voice assistants were not queried. No spoken-answer selection is assumed, and brand pronunciation was not tested.")


def _s38(facts: _Facts, label: str) -> Tuple[str, str]:
    docs = facts.pages_with(lambda page: any(token in str(_get(page, "url", "") or "").lower() for token in ("/help", "/docs", "/support", "/faq", "knowledge")))
    if _has(label, "public versus private"):
        return _unt(label, "Authenticated help content was not compared with public pages. " + facts.sample)
    if docs:
        return ("INFERRED", f"URLs in the sample that look like help or docs: {_join(docs, 4)}. Completeness of those articles was not separately scored. {facts.coverage_sentence()}")
    if facts.crawled == 0:
        return _unt(label, facts.sample)
    return ("INFERRED", "No help, docs, support, or FAQ URL was in the crawled sample. " + facts.sample + " " + facts.coverage_sentence())


def _s39(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.intl is not None and not _get(facts.intl, "is_multilingual"):
        if _has(label, "hreflang") or _has(label, "translation") or _has(label, "localized") or _has(label, "regional") or _has(label, "country-specific") or _has(label, "currency"):
            return (
                "NOT_APPLICABLE",
                "The international audit records this site as not multilingual. hreflang and regional-price checks do not apply. "
                + str(_get(facts.intl, "summary", "") or ""),
            )
    langs = facts.languages()
    if _has(label, "hreflang") or _has(label, "canonical"):
        if facts.intl is not None and _get(facts.intl, "is_multilingual"):
            issues = list(_get(facts.intl, "issues", None) or [])
            state = "ISSUE_SAMPLE" if issues else "CLEAN_SAMPLE"
            return (state, f"Multilingual sample. Locales: {_join([str(item) for item in (_get(facts.intl, 'locales_detected', None) or [])], 6)}. hreflang issues: {len(issues)}.")
        if len(langs) <= 1:
            return ("NOT_APPLICABLE", f"One or no language was recorded ({_join(langs, 3)}). hreflang is not required by this sample alone.")
        return ("INFERRED", "Languages observed: " + _join(langs, 6) + ". Return-tag health was not stored on the page records.")
    if not langs and facts.crawled == 0:
        return _unt(label, "No page language was crawled.")
    return ("INFERRED", f"Languages in the sample: {_join(langs, 6) or 'none recorded'}. Translation quality was not reviewed by a person. {facts.profile_line('Market', 'geography')[1]}")


def _s40(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "confidence interval"):
        return _unt(label, "No confidence interval is calculated. Repeated runs, when stored, are still not universal visibility.")
    if facts.runs <= 0:
        return _unt(label, "A live benchmark was not stored. " + facts.coverage_sentence() + " " + facts.live_sentence())
    repeats = _get(facts.card, "repeats", None)
    failed = _get(facts.card, "failed_runs", None)
    return (
        "VERIFIED",
        f"Successful runs: {facts.runs}. Failed runs: {failed if failed is not None else 'not stored'}. "
        f"Repeats recorded: {repeats if repeats is not None else 'not stored'}. "
        f"Raw response retention is limited to what the scorecard stored. {facts.live_sentence()}",
    )


def _s41(facts: _Facts, label: str) -> Tuple[str, str]:
    return facts.claims_sentence()


def _s42(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.runs <= 0:
        return _unt(label, "Citation URLs were not captured because no successful live run is stored. " + facts.live_sentence())
    if facts.rates.get("citation") is None:
        return _gap(label, "A live run exists and the citation rate field is empty. Empty is not zero citations. " + facts.live_sentence())
    if _has(label, "share"):
        return _s02(facts, "Competitive answer share")
    return facts.rate("citation", "Citation rate", "At least one qualifying citation to the brand domain ÷ valid responses. Individual cited URLs were not retained as an inventory unless present on the observatory row.")


def _s43(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "knowledge panel"):
        return _unt(label, "Knowledge panel presence was not queried.")
    if _has(label, "conflict") or _has(label, "ambiguous") or _has(label, "duplicate"):
        return facts.entity_sentence()
    entity = facts.entity_sentence()
    if entity[0] != "NOT_TESTED":
        return entity
    return facts.profile_line(label, "business_name", "products", "services", "geography")


def _s44(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "recommended") or _has(label, "superlative") or _has(label, "positive") or _has(label, "framing"):
        return facts.recommendation()
    if _has(label, "mentioned") or _has(label, "omitted"):
        return facts.rate("mention", "Brand mention rate", "Valid responses mentioning the brand ÷ valid responses.")
    if _has(label, "pricing"):
        return _s04(facts, "Stale pricing and policy information")
    if _has(label, "comparison"):
        return _s23(facts, "Product comparison criteria")
    if facts.runs > 0 and facts.rates.get("entity_accuracy") is not None:
        return facts.rate("entity_accuracy", "Live entity accuracy", "Correct brand claims in live responses ÷ claims assessed there.")
    return ("NOT_TESTED", "How a live answer described the brand was not stored. " + facts.live_sentence() + " " + facts.profile_line(label, "value_proposition")[1])


def _s45(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "human verification") or _has(label, "correction prior"):
        rows = facts.where("CONFLICTING")
        if rows or facts.contradictions:
            return ("ISSUE_SAMPLE", "Human review is required for the stored conflicts. " + facts.contradiction_sentence() + " " + facts.quotes(rows, 2))
        return _unt(label, "No conflicting answer was stored, so no correction queue was opened. " + facts.live_sentence())
    if facts.rates.get("hallucination") is not None:
        return facts.rate("hallucination", "Hallucination rate", "Inaccurate generated answers ÷ valid live responses. One rate does not name which sentence was wrong.")
    if facts.conflicting or facts.contradictions:
        return ("ISSUE_SAMPLE", "On-page conflicts are stored. They are not, by themselves, a live hallucination. " + facts.contradiction_sentence())
    return _unt(label, "No live hallucination judgment and no on-page conflict were stored. Incorrect features, prices, and affiliations are not invented.")


def _s46(facts: _Facts, label: str) -> Tuple[str, str]:
    return _unt(label, "Third-party reviews, directories, and independent articles were not collected. " + facts.live_sentence())


def _s47(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.bakeoff is None and facts.rates.get("competitor") is None:
        return _unt(label, facts.bakeoff_sentence() + " Defensible opportunities are the unanswered questions, without a competitor citation attached. " + facts.gap_examples())
    return ("INFERRED", facts.bakeoff_sentence() + " " + facts.gap_examples() + " " + facts.live_sentence())


def _s48(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "search console") or _has(label, "question performance"):
        return facts.gsc_sentence()
    if _has(label, "referral") or _has(label, "ai referral") or _has(label, "engine"):
        return _gap(label, "AI referral sessions were not identified. GA4, when connected, is not automatically an answer-engine referral report. " + facts.ga4_sentence()[1])
    if _has(label, "organic") or _has(label, "landing") or _has(label, "visitor") or _has(label, "branded search") or _has(label, "before-and-after") or _has(label, "traffic quality"):
        if facts.ga4_state == "MEASURED":
            return facts.ga4_sentence()
        return facts.ga4_sentence()
    return facts.ga4_sentence()


def _s49(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "revenue"):
        return _gap(label, "Revenue was not attributed. GA4 key events are not revenue. " + facts.ga4_sentence()[1])
    if _has(label, "ai referral"):
        return _gap(label, "AI referral conversions were not measured. " + facts.ga4_sentence()[1])
    return facts.ga4_sentence()


def _s50(facts: _Facts, label: str) -> Tuple[str, str]:
    return _unt(
        label,
        "No forecast is produced. Demand, addressable audience, citation opportunity, effort, cost, "
        "conversion assumptions, time to impact, and upside scenarios are not estimated. "
        "A visibility gap is not a traffic or revenue forecast. " + facts.coverage_sentence(),
    )


def _s51(facts: _Facts, label: str) -> Tuple[str, str]:
    if facts.assessed == 0 and facts.crawled == 0:
        return _unt(label, facts.sample + " " + facts.coverage_sentence())
    target = next((item for item in facts.questions if item.status != "ANSWERABLE" and item.url), None)
    if target is None and facts.questions:
        target = facts.questions[0]
    page = target.url if target else (str(_get(facts.pages[0], "url", "") or "") if facts.pages else "no URL")
    if _has(label, "success") or _has(label, "validation"):
        return ("INFERRED", f"Validation page: {page}. Rerun the stored questions after the edit. {facts.live_sentence()} No improvement is claimed now.")
    if _has(label, "structured"):
        return ("INFERRED", facts.schema_sentence() + f" Page in scope: {page}.")
    if _has(label, "technical"):
        return facts.robots_sentence()
    if target and target.status != "ANSWERABLE" and _has(label, "missing", "recommended", "quality", "questions", "evidence", "review"):
        return ("ISSUE_SAMPLE", f"Page in scope: {page}. " + facts.fix_for(target) + _issue(facts, page, "The stored question does not have a usable answer.", facts.fix_for(target)))
    return ("INFERRED", f"Page in scope: {page}. {facts.coverage_sentence()} {facts.schema_sentence()}")


def _s52(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "owner") or _has(label, "effort") or _has(label, "completion status"):
        return _unt(label, "Owners, effort, and completion status were not assigned. The question rows below are the register.")
    if _has(label, "retest"):
        return ("INFERRED", "Retest condition: the same question text, the same engine list, and a new timestamp. " + facts.live_sentence())
    if facts.assessed == 0:
        return _unt(label, facts.coverage_sentence())
    return ("INFERRED", f"The register has {facts.assessed} question row(s) from {facts.question_source}. {facts.coverage_sentence()} {facts.quotes(facts.questions, 2)}")


def _s53(facts: _Facts, label: str) -> Tuple[str, str]:
    return _unt(label, "No before-and-after implementation was stored, so nothing is marked improved. " + facts.coverage_sentence() + " " + facts.live_sentence())


def _s54(facts: _Facts, label: str) -> Tuple[str, str]:
    return _unt(
        label,
        "No monitoring schedule was armed. A later run can compare question status, live mention rate, and live citation rate only when those values are stored again. "
        + facts.coverage_sentence() + " " + facts.live_sentence(),
    )


def _s55(facts: _Facts, label: str) -> Tuple[str, str]:
    if _has(label, "sampling") or _has(label, "scope"):
        return ("INFERRED", facts.sample + " The sample is not exhaustive sitewide coverage.")
    if _has(label, "engine selection") or _has(label, "model") or _has(label, "platform version") or _has(label, "test environment"):
        return ("INFERRED", facts.live_sentence())
    if _has(label, "scoring") or _has(label, "confidence") or _has(label, "uncertainty") or _has(label, "missing-data"):
        return ("INFERRED", "Rates keep their denominators. A missing input stays unmeasured. " + _SEPARATION + " " + facts.coverage_sentence())
    if _has(label, "privacy") or _has(label, "retention") or _has(label, "version history") or _has(label, "change log") or _has(label, "reproduc"):
        return ("INFERRED", f"This render uses the sealed report timestamped {facts.generated_at}. Raw engine bodies are retained only when the scorecard stored them.")
    if _has(label, "human review"):
        return ("INFERRED", "Conflicting and unsupported claims need a person. " + facts.contradiction_sentence())
    return ("INFERRED", _SEPARATION + " " + facts.sample + " " + facts.live_sentence())


def _appendix(facts: _Facts, number: str, label: str) -> Tuple[str, str]:
    if number == "A":
        if _has(label, "domain"):
            return ("VERIFIED", f"Audited domain: {facts.domain}.")
        if _has(label, "business"):
            return facts.profile_line(label, "business_name", "business_model", "industry")
        if _has(label, "product"):
            return facts.profile_line(label, "products", "services")
        if _has(label, "market"):
            return facts.profile_line(label, "geography")
        if _has(label, "language"):
            return ("INFERRED", "Languages observed: " + (_join(facts.languages(), 6) if facts.languages() else "none recorded."))
        if _has(label, "platform"):
            return ("INFERRED", facts.live_sentence())
        return ("INFERRED", facts.sample + " Exclusions: surfaces and connectors named as not tested in the chapters above.")
    if number == "B":
        if facts.assessed == 0:
            return _unt(label, facts.coverage_sentence())
        if _has(label, "source"):
            return ("INFERRED", f"Source: {facts.question_source}.")
        if _has(label, "intent"):
            return ("INFERRED", "Intent is a wording classification of the stored questions, shown in section 08.")
        if _has(label, "priority"):
            return ("INFERRED", "Priority is unanswered, then conflicting, then partial. Demand is not a priority weight. " + facts.gsc_sentence()[1])
        if _has(label, "date"):
            return ("INFERRED", f"Collection timestamp on the report: {facts.generated_at}.")
        return ("INFERRED", facts.coverage_sentence())
    if number == "C":
        return _s10(facts, label)
    if number == "D":
        return _s12(facts, label if label != "Evaluated answers" else "Core answer presence")
    if number == "E":
        return _s40(facts, label)
    if number == "F":
        return _s42(facts, label)
    if number == "G":
        if _has(label, "price") or _has(label, "polic"):
            return _s04(facts, "Stale pricing and policy information")
        if _has(label, "claim") or _has(label, "source"):
            return facts.claims_sentence()
        return facts.profile_line(label, "business_name", "products", "services")
    if number == "H":
        return _s47(facts, label)
    if number == "I":
        if _has(label, "crawl") or _has(label, "http"):
            return _s25(facts, "HTTP response status")
        if _has(label, "render"):
            return _s27(facts, "Raw HTML versus rendered DOM")
        if _has(label, "index"):
            return _s26(facts, "Indexable answer pages")
        return _s29(facts, "Structured data eligibility and limitations")
    if number == "J":
        if _has(label, "owner") or _has(label, "status"):
            return _s52(facts, "Owner and estimated effort")
        return _s51(facts, "Recommended content changes")
    if number == "K":
        if _has(label, "weight"):
            return ("INFERRED", "The four dimensions are not weighted into one AEO grade. " + _SEPARATION)
        if _has(label, "exclusion"):
            return ("INFERRED", "Excluded from rates: failed runs, unqueried surfaces, simulated writing exercises, and missing connectors. A missing value is not zero.")
        if _has(label, "confidence"):
            return ("INFERRED", "Five repeated answers are not universal visibility. No confidence interval is printed unless it was stored, and none was stored here. " + facts.live_sentence())
        if _has(label, "denominator"):
            return ("INFERRED", "Question coverage uses assessed questions. Mention, recommendation, and citation rates use valid responses. Citation share uses qualifying citations to all tracked domains. A response may both mention and cite.")
        return (
            "INFERRED",
            "Question coverage = usable verified answers ÷ assessed questions. "
            "Answer completeness = weighted required elements satisfied ÷ required elements assessed, and that weight list was not stored. "
            "Brand mention rate = responses mentioning the brand ÷ valid responses. "
            "Brand recommendation rate = responses recommending the brand ÷ valid responses, and that flag was not stored. "
            "Citation rate = responses with a qualifying brand-domain citation ÷ valid responses. "
            "Citation share = brand citations ÷ citations to all tracked domains. "
            "Citation accuracy = verified relevant citations ÷ citations assessed. "
            "Brand fact accuracy = verified correct brand claims ÷ brand claims assessed. "
            "Benchmark coverage = completed valid tests ÷ planned tests. "
            "AI referral conversion rate = attributed conversions ÷ eligible AI referral sessions. "
            + _SEPARATION,
        )
    if number == "L":
        if _has(label, "revenue"):
            return _s49(facts, "Revenue attribution")
        if _has(label, "conversion"):
            return _s49(facts, "Conversions from answer pages")
        if _has(label, "referral"):
            return _s48(facts, "Referral traffic from answer platforms")
        if _has(label, "limitation") or _has(label, "attribution"):
            return ("INFERRED", "Clicks are not conversions. Key events are not revenue. AI referrals were not separated. " + facts.ga4_sentence()[1])
        return _s48(facts, "Organic search traffic to answer pages")
    if number == "M":
        if _has(label, "date"):
            return ("INFERRED", f"Report timestamp: {facts.generated_at}.")
        if _has(label, "provenance") or _has(label, "verification"):
            return ("INFERRED", "Evidence states used in this book: verified, sample verified (issue or no issue), inferred, not tested, data unavailable, not applicable. " + _SEPARATION)
        ids = [str(_get(item, "finding_id", "") or "") for item in facts.findings if _get(item, "finding_id")]
        if ids and _has(label, "evidence id"):
            return ("INFERRED", "Finding ids stored on the report: " + _join(ids, 8))
        return ("INFERRED", f"Findings stored: {len(facts.findings)}. Question rows stored: {facts.assessed}. Live runs: {facts.runs}.")
    if number == "N":
        if _has(label, "engine"):
            return ("INFERRED", facts.live_sentence())
        if _has(label, "integration"):
            return ("INFERRED", f"Search Console: {facts.gsc_state}. GA4: {facts.ga4_state}. Neither missing connector is a zero.")
        if _has(label, "sample"):
            return ("INFERRED", facts.sample)
        return ("INFERRED", facts.gap_examples() + " " + facts.coverage_sentence())
    if _has(label, "scoring interpretation"):
        return ("INFERRED", "Sample verified · issue means the checked sample contains the gap. Sample verified · no issue means that check was clean in the sample. Verified is a connected or live measurement. A chapter with no test is not a pass. " + _SEPARATION)
    if _has(label, "metric"):
        return _appendix(facts, "K", "Metric definitions")
    return (
        "INFERRED",
        "AEO asks whether a source can satisfy a question and be used in an answer. "
        "SEO asks whether the site can be discovered and perform in search. "
        "GEO asks how a brand is represented in generative answers. "
        "CRO asks whether visitors take a valuable action. "
        "A page can rank and still fail a question. A good answer can exist and still not be cited. "
        + _SEPARATION,
    )


_HANDLERS = {
    "01": _s01,
    "02": _s02,
    "03": _s03,
    "04": _s04,
    "05": _s05,
    "06": _s06,
    "07": _s07,
    "08": _s08,
    "09": _s09,
    "10": _s10,
    "11": _s11,
    "12": _s12,
    "13": _s13,
    "14": _s14,
    "15": _s15,
    "16": _s16,
    "17": _s17,
    "18": _s18,
    "19": _s19,
    "20": _s20,
    "21": _s21,
    "22": _s22,
    "23": _s23,
    "24": _s24,
    "25": _s25,
    "26": _s26,
    "27": _s27,
    "28": _s28,
    "29": _s29,
    "30": _s30,
    "31": _s31,
    "32": _s32,
    "33": _s33,
    "34": _s34,
    "35": _s35,
    "36": _s36,
    "37": _s37,
    "38": _s38,
    "39": _s39,
    "40": _s40,
    "41": _s41,
    "42": _s42,
    "43": _s43,
    "44": _s44,
    "45": _s45,
    "46": _s46,
    "47": _s47,
    "48": _s48,
    "49": _s49,
    "50": _s50,
    "51": _s51,
    "52": _s52,
    "53": _s53,
    "54": _s54,
    "55": _s55,
}


def _line(facts: _Facts, number: str, label: str) -> Tuple[str, str]:
    if number in _HANDLERS:
        return _HANDLERS[number](facts, label)
    return _appendix(facts, number, label)


def _chapter_status(codes: Sequence[str]) -> str:
    if any(code == "ISSUE_SAMPLE" for code in codes):
        return "ISSUE_SAMPLE"
    if any(code == "VERIFIED" for code in codes):
        return "VERIFIED"
    if any(code == "CLEAN_SAMPLE" for code in codes):
        return "CLEAN_SAMPLE"
    if any(code == "INFERRED" for code in codes):
        return "INFERRED"
    if any(code == "DATA_UNAVAILABLE" for code in codes):
        return "DATA_UNAVAILABLE"
    if any(code == "NOT_TESTED" for code in codes):
        return "NOT_TESTED"
    return "NOT_APPLICABLE"


def _blurb(facts: _Facts, number: str) -> str:
    if number in {"01", "02", "11", "12", "15"}:
        return facts.coverage_sentence() + " " + _SEPARATION
    if number in {"33", "34", "35", "36", "37", "40", "42", "44", "45"}:
        return facts.live_sentence()
    if number in {"48", "49", "50", "L"}:
        return facts.ga4_sentence()[1] + " No forecast is produced."
    if number in {"25", "26", "27", "31", "32", "I"}:
        return facts.sample + " " + facts.ttfb_sentence()
    return facts.sample + " " + facts.coverage_sentence()


def _question_table(facts: _Facts) -> str:
    if not facts.questions:
        return ""
    rows = []
    for item in facts.questions[:30]:
        rows.append(
            "<tr>"
            f"<td>{_esc(item.qid)}</td>"
            f"<td>{_esc(item.status)}</td>"
            f"<td>{_esc(item.intent)}</td>"
            f"<td>{_esc(_clip(item.text, 160))}</td>"
            f"<td>{_esc(item.url or '—')}</td>"
            "</tr>"
        )
    extra = ""
    if len(facts.questions) > 30:
        extra = f"<p>{len(facts.questions) - 30} further questions remain in the stored set.</p>"
    return (
        "<table><thead><tr><th>ID</th><th>Status</th><th>Intent</th><th>Question</th><th>Evidence URL</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>{extra}"
    )


def _page_table(facts: _Facts) -> str:
    if not facts.pages:
        return ""
    rows = []
    for page in facts.pages[:20]:
        types = ", ".join(str(item) for item in list(_get(page, "schema_types", None) or [])[:4]) or "—"
        ttfb = _num(_get(page, "ttfb_ms"))
        timing = f"{ttfb:g} ms response" if ttfb and ttfb > 0 else "response time not recorded"
        rows.append(
            "<tr>"
            f"<td>{_esc(_get(page, 'url', ''))}</td>"
            f"<td>{_esc(_get(page, 'status_code', ''))}</td>"
            f"<td>{_esc('indexable' if _get(page, 'is_indexable', True) else 'not indexable')}</td>"
            f"<td>{_esc(types)}</td>"
            f"<td>{_esc(timing)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>URL</th><th>HTTP</th><th>Indexability</th><th>Schema</th><th>Response time</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _dimension_table(facts: _Facts) -> str:
    readiness = facts.coverage_sentence()
    technical = facts.sample + " " + facts.indexable_sentence()
    visibility = facts.live_sentence()
    business = facts.ga4_sentence()[1]
    rows = "".join(
        f"<tr><td>{_esc(name)}</td><td>{_esc(text)}</td></tr>"
        for name, text in (
            ("A. Content readiness", readiness),
            ("B. Technical eligibility", technical),
            ("C. Observed answer visibility", visibility),
            ("D. Business outcomes", business),
        )
    )
    return f"<table><thead><tr><th>Dimension</th><th>This run</th></tr></thead><tbody>{rows}</tbody></table>"


def _section_for_finding(finding: Any) -> str:
    text = f"{_get(finding, 'title', '')} {_get(finding, 'description', '')} {_get(finding, 'category', '')}".lower()
    if "people also ask" in text or " paa" in text:
        return "34"
    if "featured snippet" in text:
        return "33"
    if any(token in text for token in ("chatgpt", "perplexity", "gemini", "copilot", "claude", "ai overview")):
        return "36"
    if "hallucination" in text or "incorrect" in text:
        return "45"
    if "citation" in text:
        return "42"
    if "faq" in text:
        return "14"
    if "hreflang" in text:
        return "39"
    if "robots.txt" in text or "robots txt" in text:
        return "25"
    if "canonical" in text or "noindex" in text:
        return "26"
    if "schema" in text or "json-ld" in text or "json ld" in text:
        return "29"
    category = str(_get(finding, "category", "") or "").upper()
    if "SCHEMA" in category:
        return "29"
    if category == "AEO" or "ANSWER" in category:
        return "11"
    if "GEO" in category:
        return "17"
    if "AI_SEARCH" in category or "AI SEARCH" in category:
        return "36"
    return "52"


def _tokens(value: str) -> set:
    stop = {"and", "or", "the", "a", "an", "of", "to", "for", "in", "on", "with", "from"}
    found = set()
    for token in re.findall(r"[a-z0-9]+", value.lower()):
        if token in stop or len(token) < 4:
            continue
        found.add(token)
    return found


def _assign(findings: Sequence[Any], checks: Sequence[str]) -> Dict[str, List[Any]]:
    assigned: Dict[str, List[Any]] = {check: [] for check in checks}
    if not checks:
        return assigned
    for finding in findings:
        blob = _tokens(f"{_get(finding, 'title', '')} {_get(finding, 'description', '')}")
        best = checks[0]
        best_score = 0
        for check in checks:
            score = len(blob & _tokens(check))
            if score > best_score:
                best = check
                best_score = score
        assigned[best].append(finding)
    return assigned


def _finding_card(finding: Any) -> str:
    title = _esc(_get(finding, "title", "") or "Finding")
    severity = _esc(str(_get(finding, "severity", "") or ""))
    description = _esc(_public_description(finding))
    recommendation = _esc(_public_recommendation(finding))
    return (
        f"<p><strong>{title}</strong> ({severity}). {description} "
        f"Change: {recommendation}</p>"
    )


def aeo_cover_figure(report: Any) -> Optional[int]:
    """Schema quality or on-page extractability. Never a live visibility rate."""
    geo = _get(report, "geo_readiness")
    cross = _get(geo, "schema_crosscheck") or {}
    if isinstance(cross, dict):
        quality = _num(cross.get("quality_score"))
        if quality is not None:
            return int(round(quality))
    extractability = _num(_get(geo, "extractability_score"))
    if extractability is not None:
        return int(round(extractability))
    return None


def render_aeo_audit_book(report: Any) -> str:
    """Render sections 01–55 and appendices A–O from stored evidence only."""
    payload = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    facts = _Facts(report)
    grouped: Dict[str, List[Any]] = {}
    for finding in facts.findings:
        grouped.setdefault(_section_for_finding(finding), []).append(finding)
    part_titles = {part["id"]: part["title"] for part in payload["parts"]}
    toc = ["<h2>Complete AEO audit</h2>", "<nav class=\"toc\"><ol>"]
    blocks = [
        "<p>"
        + _esc(facts.sample)
        + " Every section and every checklist line below is a result. "
        "A missing source is not a zero and not a pass. "
        + _esc(_SEPARATION)
        + "</p>"
    ]
    for part in payload["parts"]:
        owned = [section for section in payload["sections"] if section["part"] == part["id"]]
        if not owned:
            continue
        blocks.append(f"<h3>Part {_esc(part['id'])} — {_esc(part['title'])}</h3>")
        for section in owned:
            number = section["number"]
            toc.append(f"<li><a href=\"#aeo-{_esc(number)}\"><span>{_esc(number)}</span> {_esc(section['title'])}</a></li>")
            checks_html = []
            codes = []
            assigned = _assign(grouped.get(number, []), section["checks"])
            for check in section["checks"]:
                code, result = _line(facts, number, check)
                cards = assigned.get(check, [])
                if any(_is_defect(item) for item in cards):
                    code = "ISSUE_SAMPLE"
                    result = result + " Recorded finding on this line."
                codes.append(code)
                checks_html.append(
                    "<article class=\"check "
                    + _CLASS.get(code, "untested")
                    + "\">"
                    + f"<h5>{_esc(check)}</h5>"
                    + f"<p class=\"status\">{_esc(_LABEL.get(code, 'Not tested'))}</p>"
                    + f"<p>{_esc(result)}</p>"
                    + "".join(_finding_card(item) for item in cards)
                    + "</article>"
                )
            status = _chapter_status(codes)
            extra = ""
            if number == "02":
                extra = _dimension_table(facts)
            elif number in {"52", "B", "C"}:
                extra = _question_table(facts)
            elif number == "I":
                extra = _page_table(facts)
            blocks.append(
                f"<section class=\"seo-section\" id=\"aeo-{_esc(number)}\">"
                f"<p class=\"part-label\">Part {_esc(section['part'])} — {_esc(part_titles.get(section['part'], ''))}</p>"
                f"<h4>{_esc(number)}. {_esc(section['title'])}</h4>"
                f"<p class=\"status\">{_esc(_LABEL.get(status, 'Not tested'))}</p>"
                f"<p>{_esc(_blurb(facts, number))}</p>"
                f"{extra}"
                f"{''.join(checks_html)}"
                "</section>"
            )
    toc.append("</ol></nav>")
    return "\n".join([toc[0], blocks[0], *toc[1:], *blocks[1:]])
