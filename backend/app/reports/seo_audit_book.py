"""SEO section document as a 55-section audit book.

Each checklist line gets a result from the sealed report. A missing source stays
unmeasured. The book does not invent traffic, revenue, rankings, field Core Web
Vitals, or a WCAG certificate.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.reports.seo_chapter_visuals import chapter_panel, evidence_mix_chart
from app.reports.seo_chapter_agentic_audit import (
    generate_chapter_narrative,
    generate_chapter_data_table,
    get_chapter_agent,
)

_INDEX_PATH = Path(__file__).with_name("seo_audit_index.json")
_STOP = {
    "and", "or", "the", "a", "an", "of", "to", "for", "in", "on", "with", "where",
    "only", "when", "from", "by", "its", "their", "this", "that", "per", "versus",
    "are", "was", "were", "not", "into", "over", "such", "than",
}
_KEEP_SHORT = {"h1", "h2", "h3", "cta", "url", "nap", "cls", "inp", "lcp", "seo", "geo", "aeo", "faq", "css"}
_LABEL = {
    "ISSUE_VERIFIED": "Issue verified",
    "NO_ISSUE": "No issue in the checked sample",
    "MEASURED": "Measured",
    "INFERRED": "Inferred",
    "DATA_UNAVAILABLE": "Data unavailable",
    "NOT_TESTED": "Not tested",
    "NOT_APPLICABLE": "Not applicable",
}
_CLASS = {
    "ISSUE_VERIFIED": "issue",
    "NO_ISSUE": "clean",
    "MEASURED": "measured",
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


def _text(finding: Any) -> str:
    return f"{_get(finding, 'title', '')} {_get(finding, 'description', '')}".lower()


def _tokens(value: str) -> set:
    found = set()
    for token in re.findall(r"[a-z0-9]+", value.lower()):
        if token in _STOP:
            continue
        if len(token) > 2 or token in _KEEP_SHORT:
            found.add(token)
        if token.endswith("s") and len(token) > 3:
            found.add(token[:-1])
    return found


def _join(items: Sequence[str], limit: int = 8) -> str:
    rows = [str(item) for item in items if str(item).strip()]
    if not rows:
        return "none in the crawled sample"
    shown = rows[:limit]
    extra = len(rows) - len(shown)
    text = "; ".join(shown)
    if extra:
        text += f" (+{extra} more)"
    return text


def _has(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


class _Book:
    def __init__(self, report: Any) -> None:
        self.report = report
        manifest = _get(report, "crawl_manifest")
        pages = list(_get(manifest, "pages", None) or [])
        if not pages:
            pages = list(_get(report, "page_reports", None) or [])
        self.pages = pages
        self.findings = list(_get(report, "findings", None) or [])
        self.manifest = manifest
        performance = _get(report, "google_performance") or {}
        if not isinstance(performance, dict):
            performance = {}
        search = performance.get("search_console")
        analytics = performance.get("analytics")
        self.search = search if isinstance(search, dict) else {}
        self.analytics = analytics if isinstance(analytics, dict) else {}
        self.gsc_state = str(self.search.get("state") or "NOT_CONNECTED")
        self.ga4_state = str(self.analytics.get("state") or "NOT_CONNECTED")
        profile = _get(report, "business_profile")
        self.profile = profile
        self.model = " ".join(
            str(_get(profile, name, "") or "")
            for name in ("business_model", "industry", "niche", "business_name")
        ).lower()
        self.sample = self._sample_sentence()

    def _sample_sentence(self) -> str:
        discovered = _num(_get(self.manifest, "total_pages_discovered"))
        crawled = len(self.pages)
        if crawled == 0:
            return "No page was crawled on this run. Dristik uses a representative sample."
        if discovered and discovered > crawled:
            return (
                f"Representative sample: {crawled} crawled page(s) of {int(discovered)} discovered URLs. "
                "This is not every URL on the site."
            )
        return f"Representative sample: {crawled} crawled page(s). This is not every URL on the site."

    def urls(self, predicate) -> List[str]:
        found = []
        for page in self.pages:
            url = str(_get(page, "url", "") or "")
            if url and predicate(page):
                found.append(url)
        return found

    def profile_value(self, name: str) -> str:
        value = _get(self.profile, name, None)
        if value is None or value == "" or value == []:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value if str(item).strip())
        return str(value).strip()


def _ran(obj: Any, field: str = "total_pages_evaluated") -> bool:
    return obj is not None and (_num(_get(obj, field)) or 0) > 0


def _is_note(finding: Any) -> bool:
    severity = str(_get(finding, "severity", "") or "").upper()
    if severity in {"INFO", "INFORMATIONAL"}:
        return True
    blob = _text(finding)
    return any(phrase in blob for phrase in _NOTE_PHRASES)


def _is_guessing(finding: Any) -> bool:
    return str(_get(finding, "confidence_rubric", "") or "").upper() == "GUESSING"


def _is_defect(finding: Any) -> bool:
    return not _is_note(finding) and not _is_guessing(finding)


def _public_description(finding: Any) -> str:
    description = str(_get(finding, "description", "") or "").strip()
    if "SINGLE_SOURCE_UNVERIFIED" in description or "single_source_unverified" in description.lower():
        return "Observed in the crawled HTML. A second evidence source was not attached, so confidence stays medium."
    if description.lower().startswith("single_source"):
        return "Observed in the crawled HTML. A second evidence source was not attached, so confidence stays medium."
    return description or "The finding text did not include a separate description."


def _public_recommendation(finding: Any) -> str:
    recommendation = str(_get(finding, "recommendation", "") or _get(finding, "suggested_fix", "") or "").strip()
    generic = not recommendation or "implement recommended architectural fix" in recommendation.lower()
    if generic:
        if _is_note(finding):
            return "No change is required from this observation."
        return "No specific change was written for this finding."
    return recommendation


def _finding_urls(finding: Any) -> List[str]:
    urls = []
    for item in _get(finding, "evidence", None) or []:
        url = _get(item, "url", "")
        if url:
            urls.append(str(url))
    for url in _get(finding, "affected_urls", None) or []:
        if url and str(url) not in urls:
            urls.append(str(url))
    return urls


def _finding_card(finding: Any) -> str:
    severity = str(_get(finding, "severity", "") or "MEDIUM").upper()
    finding_id = str(_get(finding, "finding_id", "") or "FIND-SEO").strip()
    title = str(_get(finding, "title", "Audit Finding") or "Audit Finding").strip()
    kind = "note" if _is_note(finding) else "defect"
    if _is_guessing(finding):
        kind = "note"
    urls = _finding_urls(finding)
    if len(urls) == 1:
        scope_badge = "PAGE_VERIFIED"
        scope_desc = "One URL was attached to this finding."
    elif len(urls) > 1:
        scope_badge = "SAMPLE_VERIFIED"
        scope_desc = f"{len(urls)} URLs were attached to this finding."
    else:
        scope_badge = "URL_NOT_ATTACHED"
        scope_desc = "No URL was attached to this finding."

    observed = _public_description(finding)
    recommendation = _public_recommendation(finding)
    shown_urls = ", ".join(f"<code>{_esc(u)}</code>" for u in urls[:5])
    if len(urls) > 5:
        shown_urls += f" (+{len(urls) - 5} more)"
    urls_html = shown_urls if urls else "No URL was attached."

    optional = []
    for field_name, heading in (
        ("why_it_matters", "Why it matters"),
        ("business_impact", "Stored business impact"),
        ("root_cause", "Stored root cause"),
        ("expected_condition", "Stored expected condition"),
        ("validation_criteria", "Stored validation"),
    ):
        value = str(_get(finding, field_name, "") or "").strip()
        if value:
            optional.append(
                f'<div class="finding-field-block"><span class="field-title">{_esc(heading)}:</span>'
                f'<p class="field-text">{_esc(value)}</p></div>'
            )
    guess_note = (
        '<div class="finding-row note-flag">This observation was marked guessing and is excluded from defect totals.</div>'
        if _is_guessing(finding)
        else ""
    )
    label = "Observation" if kind == "note" else "Recorded finding"

    return f"""
    <div class="finding-card-v2 {severity.lower()}">
        <div class="finding-v2-header">
            <div class="header-tags">
                <span class="badge-tag sev-{severity.lower()}">{_esc(severity)}</span>
                <span class="badge-tag">{_esc(scope_badge)}</span>
                <span class="finding-id-tag">{_esc(finding_id)}</span>
            </div>
            <h5 class="finding-v2-title">{_esc(label)}: {_esc(title)}</h5>
        </div>
        <div class="finding-v2-body">
            <div class="finding-field-block">
                <span class="field-title">Observed:</span>
                <p class="field-text">{_esc(observed)}</p>
            </div>
            <div class="finding-field-block">
                <span class="field-title">URLs:</span>
                <p class="field-text">{urls_html} <span class="scope-note">({_esc(scope_desc)})</span></p>
            </div>
            {''.join(optional)}
            <div class="finding-field-block action-block">
                <span class="field-title">Recommended action:</span>
                <p class="field-text action-text">{_esc(recommendation)}</p>
            </div>
            {guess_note}
        </div>
    </div>
    """


def _section_for_finding(finding: Any) -> str:
    text = _text(finding)
    category = str(_get(finding, "category", "") or "").upper()
    rules = (
        (r"core web vital|largest contentful|\blcp\b|\binp\b|cumulative layout", "16"),
        (r"render-blocking|third-party|tracker", "16"),
        (r"hreflang|multilingual", "36"),
        (r"google business profile|\bnap\b|local business", "35"),
        (r"backlink|referring domain", "31"),
        (r"robots\.txt|crawl trap|orphan", "07"),
        (r"noindex|soft 404|not indexed", "08"),
        (r"canonical", "10"),
        (r"redirect|broken link|\b404\b|\b410\b", "11"),
        (r"sitemap", "12"),
        (r"anchor text|click here", "27"),
        (r"click depth|internal link", "13"),
        (r"hsts|content-security-policy|security header|mixed content|certificate", "18"),
        (r"dom element", "15"),
        (r"javascript|hydration|rendered dom", "15"),
        (r"viewport|tap target|interstitial", "17"),
        (r"schema|structured data|json-ld", "19"),
        (r"meta description|title tag|title length|title is|title could|descriptive enough", "20"),
        (r"\bh1\b|heading", "21"),
        (r"thin copy|word count|readability", "23"),
        (r"cannibal|duplicate title|near-duplicate", "26"),
        (r"alt text|image alt|alternative text", "28"),
        (r"videoobject|thumbnail|video landing|\bvideo\b", "29"),
        (r"cloaking|sneaky redirect|scaled content|spam policy|reputation abuse|search essentials", "37"),
        (r"product variant|out-of-stock|faceted filter|merchant center|ecommerce", "38"),
        (r"newsarticle|editorial transparency|breaking news|paywall|news sitemap", "39"),
        (r"programmatic|template differentiation|faceted navigation|crawl waste", "40"),
        (r"lead magnet|integration page|comparison page|pricing tier|saas|b2b", "41"),
        (r"app store|aso|universal link|app link", "42"),
        (r"accessibility|aria|wcag|landmark|color contrast", "43"),
        (r"voice search|conversational query|spoken query", "44"),
        (r"direct answer|question-to-answer|featured snippet|answer passage", "45"),
        (r"information gain|generative engine|citation readiness|llms\.txt", "46"),
        (r"ai overview|chatgpt|perplexity|gemini|copilot", "47"),
        (r"search console|gsc|crawl statistics|url inspection", "48"),
        (r"google analytics|ga4|engaged sessions|utm", "49"),
        (r"\bcta\b|call to action|conversion friction|hero hook", "50"),
        (r"organic revenue|pipeline|attribution model", "51"),
        (r"forecasting|traffic opportunity|demand model", "52"),
        (r"regression test|fixed vs verified|acceptance test", "54"),
        (r"governance|sla|monitoring cadence", "55"),
        (r"ttfb|response latency|page load", "14"),
    )
    for pattern, number in rules:
        if re.search(pattern, text):
            return number
    if category == "GEO":
        return "46"
    if category in {"AI_SEARCH", "AEO"}:
        return "45"
    if category == "CONTENT":
        return "23"
    if category == "ON_PAGE_SEO":
        return "20"
    if category == "UX_CONVERSION":
        return "50"
    if category == "SCHEMA":
        return "19"
    if category in {"TRUST_AUTHORITY", "SECURITY"}:
        return "18"
    if category == "COMPETITIVE":
        return "33"
    if category == "EXTERNAL_AUTHORITY":
        return "31"
    if "TECHNICAL" in category:
        return "53"
    return "53"


def _assign(findings: Sequence[Any], checks: Sequence[str]) -> Dict[str, List[Any]]:
    assigned: Dict[str, List[Any]] = {check: [] for check in checks}
    for finding in findings:
        finding_tokens = _tokens(_text(finding))
        best = None
        best_score = 0
        blob = _text(finding)
        for check in checks:
            check_tokens = _tokens(check)
            score = len(finding_tokens & check_tokens)
            check_l = check.lower()
            if _has(blob, "descriptive", "generic", "boilerplate") and "descriptive" in check_l:
                score += 3
            if _has(blob, "long", "length", "truncat", "short", "characters") and _has(check_l, "length", "truncat"):
                same_field = ("title" in blob and "title" in check_l) or (
                    _has(blob, "meta", "description") and _has(check_l, "meta", "description")
                )
                if same_field:
                    score += 3
            if "thin" in blob and _has(check_l, "thin", "completeness", "usefulness"):
                score += 3
            if "canonical" in blob and "canonical" in check_l:
                score += 3
            if "sitemap" in blob and "sitemap" in check_l and "image" not in check_l and "video" not in check_l and "news" not in check_l:
                score += 2
            if score > best_score:
                best = check
                best_score = score
        if best and best_score >= 2:
            assigned[best].append(finding)
    return assigned


def _titles(book: _Book) -> List[Tuple[str, str, int]]:
    rows = []
    for page in book.pages:
        title = str(_get(page, "title", "") or "").strip()
        rows.append((str(_get(page, "url", "") or ""), title, len(title)))
    return rows


def _metas(book: _Book) -> List[Tuple[str, str, int]]:
    rows = []
    for page in book.pages:
        meta = str(_get(page, "meta_description", "") or "").strip()
        rows.append((str(_get(page, "url", "") or ""), meta, len(meta)))
    return rows


def _h1s(page: Any) -> List[str]:
    return [str(item).strip() for item in (_get(page, "h1", None) or []) if str(item).strip()]


def _header_map(page: Any) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for source in (_get(page, "security_headers") or {}, _get(page, "response_headers") or {}):
        if isinstance(source, dict):
            for key, value in source.items():
                merged[str(key).lower()] = str(value)
    return merged


def _ms(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return f"{value:.0f}"
    return f"{value:.1f}"


def _positive_ttfb(book: _Book) -> List[Tuple[str, float]]:
    rows = []
    for page in book.pages:
        value = _num(_get(page, "ttfb_ms"))
        if value and value > 0:
            rows.append((str(_get(page, "url", "") or ""), value))
    return rows


def _field_pages(book: _Book) -> List[Any]:
    return [page for page in book.pages if _get(_get(page, "field_performance"), "has_field_data")]


def _lab_pages(book: _Book) -> List[Any]:
    return [page for page in book.pages if _get(_get(page, "lab_performance"), "lighthouse_audit_version")]


def _words(book: _Book) -> List[Tuple[str, int]]:
    rows = []
    for page in book.pages:
        count = int(_get(page, "word_count", 0) or 0)
        if count > 0:
            rows.append((str(_get(page, "url", "") or ""), count))
    return rows


def _schema_types(book: _Book) -> List[str]:
    found = {str(item) for page in book.pages for item in (_get(page, "schema_types", None) or []) if str(item).strip()}
    validation = _get(book.report, "schema_validation")
    if _ran(validation, "total_entities_detected") or _get(validation, "detected_types"):
        for item in _get(validation, "detected_types", None) or []:
            if str(item).strip():
                found.add(str(item))
    return sorted(found)


def _model_matches(book: _Book, words: Sequence[str]) -> bool:
    return any(word in book.model for word in words)


def _specialist(book: _Book, fits: bool, evidence: bool, module_name: str) -> Tuple[str, str]:
    if not book.model.strip() and not evidence:
        return "NOT_TESTED", f"Site type was not established, so {module_name} was not selected."
    if not fits and not evidence:
        return "NOT_APPLICABLE", f"Not selected. The stored profile does not describe {module_name}."
    if not book.pages and not evidence:
        return "NOT_TESTED", f"The profile can match {module_name}, and no pages were crawled for it."
    return "MEASURED", f"The stored profile or page evidence can match {module_name}. {book.sample}"


def _gsc_line(book: _Book, subject: str) -> Tuple[str, str]:
    if book.gsc_state != "MEASURED":
        return (
            "DATA_UNAVAILABLE",
            f"{subject} Search Console is {book.gsc_state.replace('_', ' ').lower()}. "
            "Clicks, impressions, and queries are not shown as zero.",
        )
    clicks = book.search.get("clicks")
    impressions = book.search.get("impressions")
    return (
        "MEASURED",
        f"{subject} Search Console is connected. Clicks={clicks}. Impressions={impressions}. "
        "This is not a keyword-difficulty study and it is not a rank forecast.",
    )


def _ga4_line(book: _Book, subject: str) -> Tuple[str, str]:
    if book.ga4_state != "MEASURED":
        return (
            "DATA_UNAVAILABLE",
            f"{subject} Google Analytics 4 is {book.ga4_state.replace('_', ' ').lower()}. "
            "Sessions, key events, and revenue are not filled with an estimate.",
        )
    sessions = book.analytics.get("sessions")
    events = book.analytics.get("key_events")
    event_text = f" Key events={events}." if events is not None else " Key events were not in the response."
    return (
        "MEASURED",
        f"{subject} GA4 is connected. Sessions={sessions}.{event_text} Key events are not revenue.",
    )


def _title_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    if not book.pages:
        return "NOT_TESTED", "Titles were not read because no page was crawled."
    rows = _titles(book)
    missing = [url for url, title, _length in rows if not title]
    long_rows = [f"{url} ({length} characters)" for url, title, length in rows if title and length > 60]
    short_rows = [f"{url} ({length} characters)" for url, _title, length in rows if 0 < length < 30]
    groups: Dict[str, List[str]] = {}
    for url, title, _length in rows:
        if title:
            groups.setdefault(title, []).append(url)
    dupes = [f"“{title}” on {', '.join(urls)}" for title, urls in groups.items() if len(urls) > 1]
    rollup = _get(book.report, "meta_rollup")
    if _ran(rollup):
        missing = [str(_get(item, "url", "") or _get(item, "title", "")) for item in (_get(rollup, "missing_titles", None) or [])] or missing
        long_rows = [str(_get(item, "url", "") or "") for item in (_get(rollup, "too_long_titles", None) or [])] or long_rows
        dupes = [str(_get(item, "url", "") or "") for item in (_get(rollup, "duplicate_titles", None) or [])] or dupes
    listed = _join([f"{url}: “{title}” ({length} characters)" if title else f"{url}: missing" for url, title, length in rows])
    if _has(text, "missing title"):
        code = "ISSUE_VERIFIED" if missing else "NO_ISSUE"
        return code, f"{len(missing)} crawled page(s) have no title. {listed}."
    if "duplicate" in text:
        code = "ISSUE_VERIFIED" if dupes else "NO_ISSUE"
        detail = "; ".join(dupes) if dupes else "No duplicate title was found among the crawled pages."
        return code, detail
    if _has(text, "length", "truncat"):
        code = "ISSUE_VERIFIED" if long_rows or short_rows else "NO_ISSUE"
        return code, (
            f"Titles over 60 characters: {_join(long_rows)}. Titles under 30 characters: {_join(short_rows)}. "
            "Pixel truncation is reported only when a snippet preview stored it. "
            f"Sample: {listed}."
        )
    if _has(text, "keyword", "intent", "misleading", "rewrite"):
        return (
            "NOT_TESTED",
            "Search demand was not used to score title intent. "
            f"The titles that were read: {listed}.",
        )
    if "brand" in text:
        name = book.profile_value("business_name")
        if not name:
            return "NOT_TESTED", f"No brand name was stored, so brand placement was not judged. Titles read: {listed}."
        hits = [url for url, title, _length in rows if name.lower() in title.lower()]
        return "MEASURED", f"The stored brand is {name}. It appears in {len(hits)} of {len(rows)} crawled titles. Sample: {listed}."
    if _has(text, "descriptive", "boilerplate", "specificity", "template"):
        return "INFERRED", (
            "Descriptive quality is judged from the recorded finding text and the titles themselves. "
            f"Titles read: {listed}."
        )
    return "MEASURED", f"Titles in the sample: {listed}."


def _meta_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    if not book.pages:
        return "NOT_TESTED", "Meta descriptions were not read because no page was crawled."
    rows = _metas(book)
    missing = [url for url, meta, _length in rows if not meta]
    long_rows = [f"{url} ({length} characters)" for url, meta, length in rows if meta and length > 160]
    groups: Dict[str, List[str]] = {}
    for url, meta, _length in rows:
        if meta:
            groups.setdefault(meta, []).append(url)
    dupes = [f"“{meta[:80]}\" on {', '.join(urls)}" for meta, urls in groups.items() if len(urls) > 1]
    listed = _join([f"{url}: {length} characters" if meta else f"{url}: missing" for url, meta, length in rows])
    if _has(text, "missing", "duplicate"):
        code = "ISSUE_VERIFIED" if missing or dupes else "NO_ISSUE"
        duplicate_text = "; ".join(dupes) if dupes else "No duplicate meta description was found in the sample."
        return code, f"{len(missing)} crawled page(s) lack a meta description. {duplicate_text} Lengths: {listed}."
    if _has(text, "length", "truncat", "snippet"):
        serp = _get(book.report, "serp_appearance")
        if _ran(serp, "total_urls_evaluated"):
            return (
                "MEASURED" if int(_get(serp, "descriptions_truncated_count", 0) or 0) == 0 else "ISSUE_VERIFIED",
                f"Snippet preview stored {int(_get(serp, 'descriptions_truncated_count', 0) or 0)} truncated description(s) "
                f"across {int(_get(serp, 'total_urls_evaluated', 0) or 0)} URL(s). Character lengths: {listed}.",
            )
        code = "ISSUE_VERIFIED" if long_rows else "NO_ISSUE"
        return code, f"Descriptions over 160 characters: {_join(long_rows)}. Lengths: {listed}. A 160-character count is a truncation risk, not a measured pixel width."
    return "MEASURED", f"Meta descriptions in the sample: {listed}."


def _heading_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    if not book.pages:
        return "NOT_TESTED", "Headings were not read because no page was crawled."
    rollup = _get(book.report, "heading_hierarchy")
    if _ran(rollup) and _has(text, "multiple", "missing", "hierarchy", "h2", "h3", "duplication"):
        missing = len(_get(rollup, "missing_h1", None) or [])
        multiple = len(_get(rollup, "multiple_h1", None) or [])
        violations = len(_get(rollup, "hierarchy_violations", None) or [])
        code = "ISSUE_VERIFIED" if (missing or multiple or violations) else "NO_ISSUE"
        return code, (
            f"Heading rollup: {missing} page(s) missing an H1, {multiple} with multiple H1s, "
            f"{violations} hierarchy violation(s). {book.sample}"
        )
    rows = []
    missing = []
    multiple = []
    skipped = []
    for page in book.pages:
        url = str(_get(page, "url", "") or "")
        h1 = _h1s(page)
        h2 = [str(item).strip() for item in (_get(page, "h2", None) or []) if str(item).strip()]
        h3 = [str(item).strip() for item in (_get(page, "h3", None) or []) if str(item).strip()]
        if not h1:
            missing.append(url)
        if len(h1) > 1:
            multiple.append(f"{url} ({len(h1)} H1s)")
        if h3 and not h2:
            skipped.append(url)
        rows.append(f"{url}: H1 {(' | '.join(h1) if h1 else 'missing')}; H2 {len(h2)}; H3 {len(h3)}")
    listed = _join(rows)
    if _has(text, "multiple", "missing primary"):
        code = "ISSUE_VERIFIED" if missing or multiple else "NO_ISSUE"
        return code, f"Pages with no H1: {_join(missing)}. Pages with more than one H1: {_join(multiple)}. {listed}."
    if _has(text, "h2", "h3", "hierarchy", "semantic", "structure", "subheading"):
        code = "ISSUE_VERIFIED" if skipped else "MEASURED"
        return code, (
            f"Pages with an H3 and no H2: {_join(skipped)}. "
            "A full outline audit is included when the heading rollup stored violations. "
            f"Sample: {listed}."
        )
    if _has(text, "relevance", "quality", "alignment", "hidden", "misleading"):
        return "INFERRED", f"Heading text was extracted and is quoted here. Relevance is not a separate score. {listed}."
    if missing or multiple:
        return "ISSUE_VERIFIED", f"Pages with no H1: {_join(missing)}. Multiple H1s: {_join(multiple)}. {listed}."
    return "NO_ISSUE", f"Each crawled page has one H1 in the extracted headings. {listed}."


def _canonical_line(book: _Book, label: str) -> Tuple[str, str]:
    audit = _get(book.report, "canonical_audit")
    if _ran(audit):
        missing = int(_get(audit, "missing_canonical_count", 0) or 0)
        broken = int(_get(audit, "broken_canonical_count", 0) or 0)
        chains = int(_get(audit, "multiple_canonical_count", 0) or 0)
        cross = int(_get(audit, "cross_domain_canonical_count", 0) or 0)
        code = "ISSUE_VERIFIED" if any((missing, broken, chains, cross)) else "NO_ISSUE"
        summary = str(_get(audit, "summary", "") or "").strip()
        return code, (
            f"Canonical audit: {missing} missing, {broken} broken, {chains} multiple, {cross} cross-domain, "
            f"{int(_get(audit, 'self_canonical_count', 0) or 0)} self-referencing. "
            + (summary or book.sample)
        )
    if not book.pages:
        return "NOT_TESTED", "Canonicals were not checked because no page was crawled."
    missing = book.urls(lambda page: not str(_get(page, "canonical_url", "") or "").strip())
    present = len(book.pages) - len(missing)
    code = "ISSUE_VERIFIED" if missing else "NO_ISSUE"
    return code, (
        f"{present} crawled page(s) declare a canonical. Pages without one: {_join(missing)}. "
        "Canonical chains, loops, and cross-domain targets were not walked unless the canonical audit stored them. "
        f"This line is {label}."
    )


def _robots_txt_line(book: _Book) -> Tuple[str, str]:
    if book.manifest is None:
        return "NOT_TESTED", "No crawl record was stored, so robots.txt was not fetched."
    if not _get(book.manifest, "robots_txt_found"):
        return "ISSUE_VERIFIED", "robots.txt was not found at the domain root in this crawl."
    content = str(_get(book.manifest, "robots_txt_content", "") or "").strip()
    snippet = content[:400] if content else "The file was recorded and its body was not stored."
    return "MEASURED", f"robots.txt was recorded. Excerpt: {snippet}"


def _sitemap_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    specialized = _has(text, "image", "video", "news", "last-modified", "splitting", "encoding", "syntax", "submission", "processing", "international", "response status")
    if book.manifest is None:
        return "NOT_TESTED", "No crawl record was stored, so a sitemap was not fetched."
    found = bool(_get(book.manifest, "sitemap_found"))
    url = str(_get(book.manifest, "sitemap_url", "") or "")
    listed = _get(book.manifest, "sitemap_urls", None) or []
    if specialized:
        if not found:
            return "NOT_TESTED", f"{label} was not run. No XML sitemap was recorded, so there was no file to validate."
        return "NOT_TESTED", f"A sitemap was recorded{(': ' + url) if url else ''}. {len(listed)} URL(s) were listed. {label} was not revalidated in this chapter."
    if found:
        return "MEASURED", f"A sitemap was recorded{(': ' + url) if url else ''}. {len(listed)} sitemap URL(s) were stored. Every listed URL was not fetched unless it is in the crawled sample."
    return "ISSUE_VERIFIED", "No XML sitemap was recorded on this crawl."


def _timing_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    timed = _positive_ttfb(book)
    if _has(text, "compression", "gzip", "brotli", "cache", "cdn"):
        encodings = []
        for page in book.pages:
            lab = _get(page, "lab_performance")
            encoding = str(_get(lab, "content_encoding", "") or _get(page, "content_encoding", "") or "")
            cache = str(_get(lab, "cache_control", "") or "")
            if encoding or cache:
                encodings.append(f"{_get(page, 'url')}: encoding {encoding or 'not stored'}, cache {cache or 'not stored'}")
        if not encodings:
            return "NOT_TESTED", "Compression and cache-control were not stored. A missing header is not treated as uncompressed and not as cached."
        return "MEASURED", "Stored encoding and cache policy: " + _join(encodings) + "."
    if not timed:
        return "NOT_TESTED", "No positive crawl response time was stored. A missing timing is not a pass and is not a Core Web Vital."
    shown = _join([f"{url} {_ms(value)} ms" for url, value in timed])
    slow = [f"{url} {_ms(value)} ms" for url, value in timed if value > 600]
    code = "ISSUE_VERIFIED" if slow else "NO_ISSUE"
    dispute = ""
    if timed and not slow:
        for finding in book.findings:
            blob = _text(finding)
            if _has(blob, "ttfb", "response latency", "time to first byte") and _has(blob, "600", "exceed"):
                dispute = " Stored response times on the crawled pages are at or under 600 ms. Those stored times are the measurements in this chapter."
                break
    return code, f"Crawl response time, not Lighthouse and not field Core Web Vitals: {shown}.{dispute} This line is {label}."


def _cwv_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    field_pages = _field_pages(book)
    if field_pages and _has(text, "lcp", "inp", "cls", "core web vital", "field"):
        bits = []
        for page in field_pages[:5]:
            field = _get(page, "field_performance")
            bits.append(
                f"{_get(page, 'url')}: p75 LCP {_get(field, 'p75_lcp_ms')} ms, INP {_get(field, 'p75_inp_ms')} ms, CLS {_get(field, 'p75_cls')}"
            )
        return "MEASURED", "Field data at the 75th percentile. Thresholds used for interpretation are LCP 2.5s, INP 200ms, and CLS 0.1. " + _join(bits) + "."
    lab_pages = _lab_pages(book)
    if lab_pages and _has(text, "lcp", "laboratory", "lighthouse", "cls", "inp"):
        bits = []
        for page in lab_pages[:5]:
            lab = _get(page, "lab_performance")
            bits.append(f"{_get(page, 'url')}: lab LCP {_get(lab, 'lcp_ms')} ms, CLS {_get(lab, 'cls_score')}, version {_get(lab, 'lighthouse_audit_version')}")
        return "MEASURED", "Laboratory Lighthouse data, not field Core Web Vitals. " + _join(bits) + "."
    if _has(text, "render-blocking", "main-thread", "unused javascript", "third-party", "resource priorit"):
        notes = []
        for page in book.pages:
            lab = _get(page, "lab_performance")
            blocking = _num(_get(lab, "render_blocking_count"))
            third = _num(_get(lab, "third_party_scripts_count"))
            if blocking or third:
                notes.append(f"{_get(page, 'url')}: render-blocking {int(blocking or 0)}, third-party scripts {int(third or 0)}")
        if notes:
            return "MEASURED", "Stored lab resource counts. These are not field Core Web Vitals. " + _join(notes) + "."
        return "NOT_TESTED", f"{label} was not counted on the page records. Crawl response time is not this measurement."
    return "NOT_TESTED", "LCP, INP, and CLS were not measured on this run. Crawl response time is reported with the HTTP timings and is not a Core Web Vital."


def _security_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    audit = _get(book.report, "security_audit")
    if audit is not None and _has(text, "hsts", "csp", "security header", "certificate", "https", "mixed"):
        summary = str(_get(audit, "summary", "") or "").strip()
        hsts = bool(_get(audit, "hsts_enabled"))
        csp = bool(_get(audit, "csp_enabled"))
        code = "ISSUE_VERIFIED" if (not hsts or not csp) else "NO_ISSUE"
        return code, (
            f"Header baseline: HSTS {'present' if hsts else 'not recorded'}, "
            f"Content-Security-Policy {'present' if csp else 'not recorded'}. "
            "This is not a penetration test. "
            + (summary or "Missing headers are transport technical debt and are not written as an indexing block.")
        )
    if not book.pages:
        return "NOT_TESTED", "HTTPS and security headers were not checked because no page was crawled."
    insecure = book.urls(lambda page: str(_get(page, "url", "")).lower().startswith("http://"))
    missing_hsts = []
    missing_csp = []
    for page in book.pages:
        headers = _header_map(page)
        url = str(_get(page, "url", "") or "")
        if "strict-transport-security" not in headers:
            missing_hsts.append(url)
        if "content-security-policy" not in headers:
            missing_csp.append(url)
    if insecure:
        return "ISSUE_VERIFIED", f"HTTP URLs in the sample: {_join(insecure)}."
    if _has(text, "hsts", "csp", "security header"):
        code = "ISSUE_VERIFIED" if missing_hsts or missing_csp else "NO_ISSUE"
        return code, (
            f"Pages without Strict-Transport-Security: {_join(missing_hsts)}. "
            f"Pages without Content-Security-Policy: {_join(missing_csp)}. "
            "This is a header baseline, not a penetration test, and it does not by itself block crawler indexing."
        )
    return "MEASURED", f"All {len(book.pages)} crawled URL(s) use HTTPS. Certificate expiry monitoring was not certified."


def _schema_line(book: _Book, label: str) -> Tuple[str, str]:
    if not book.pages and not _get(book.report, "schema_validation"):
        return "NOT_TESTED", "Structured data was not read because no page was crawled."
    types = _schema_types(book)
    validation = _get(book.report, "schema_validation")
    extra = ""
    if validation is not None and (_ran(validation, "total_entities_detected") or _get(validation, "detected_types") or _get(validation, "issues")):
        issues = _get(validation, "issues", None) or []
        extra = (
            f" Schema validation stored {int(_get(validation, 'entities_with_errors_count', 0) or 0)} error(s) "
            f"and {int(_get(validation, 'entities_with_warnings_count', 0) or 0)} warning(s) across "
            f"{int(_get(validation, 'total_entities_detected', 0) or 0)} entity record(s)."
        )
        if issues:
            extra += " " + _join([f"{_get(item, 'schema_type')} {_get(item, 'field')}: {_get(item, 'message')}" for item in issues])
    if not types:
        return "NOT_TESTED", "No schema type was stored on the crawled pages. Valid syntax would not by itself be a rich result." + extra
    wanted = label.lower()
    if _has(wanted, "merchant", "rich result", "eligibility", "enhancement"):
        return "NOT_TESTED", (
            f"{label} was not tested as a rich-result eligibility check. "
            f"Schema types stored in the sample: {', '.join(types[:12])}."
            + extra
        )
    named = None
    for candidate in ("organization", "localbusiness", "product", "breadcrumb", "article", "faq", "videoobject", "event", "review"):
        if candidate in wanted:
            named = candidate
            break
    if named:
        present = [item for item in types if named in item.lower()]
        if present:
            return "MEASURED", f"{label} appears in the sample as {', '.join(present)}. A type in the HTML is not a guaranteed rich result.{extra}"
        return "NOT_TESTED", f"{label} was not among the schema types stored in the sample ({', '.join(types[:12])}). Absence from this sample is not a rich-result eligibility test.{extra}"
    return "MEASURED", "Schema types in the sample: " + ", ".join(types[:12]) + ". A type in the HTML is not a guaranteed rich result." + extra


def _image_line(book: _Book, label: str) -> Tuple[str, str]:
    media = _get(book.report, "media_assets")
    if media is not None and int(_get(media, "total_images_analyzed", 0) or 0) > 0:
        missing = int(_get(media, "missing_alt_count", 0) or 0)
        empty = int(_get(media, "empty_alt_count", 0) or 0)
        total = int(_get(media, "total_images_analyzed", 0) or 0)
        code = "ISSUE_VERIFIED" if missing else "NO_ISSUE"
        summary = str(_get(media, "summary", "") or "").strip()
        return code, (
            f"Image audit: {missing} missing alt and {empty} empty alt across {total} image(s). "
            "Empty alt is appropriate for decorative images when that was the author's intent. "
            + (summary or book.sample)
        )
    if not book.pages:
        return "NOT_TESTED", "Images were not counted because no page was crawled."
    total = sum(int(_get(page, "total_images", 0) or 0) for page in book.pages)
    missing = sum(int(_get(page, "images_without_alt", 0) or 0) for page in book.pages)
    if total <= 0:
        return "NOT_TESTED", "No image count was stored on the crawled pages. A missing count is not zero images and not a pass."
    rows = [
        f"{_get(page, 'url')}: {int(_get(page, 'images_without_alt', 0) or 0)} of {int(_get(page, 'total_images', 0) or 0)} missing alt"
        for page in book.pages
    ]
    listed = _join(rows)
    if not _has(label.lower(), "alt", "decorative", "alternative"):
        return "NOT_TESTED", (
            f"{label} was not measured separately. "
            f"Alt text in the same sample: {missing} of {total} image(s) have no alt. {listed}."
        )
    code = "ISSUE_VERIFIED" if missing else "NO_ISSUE"
    return code, f"Alt text in the sample for “{label}”: {listed}."


def _index_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    rollup = _get(book.report, "indexation_intelligence") or _get(book.manifest, "indexation_rollup")
    if _ran(rollup):
        noindex = int(_get(rollup, "noindex_count", 0) or 0)
        soft = int(_get(rollup, "soft_404_count", 0) or 0)
        blocked = int(_get(rollup, "blocked_by_robots_count", 0) or 0)
        indexable = int(_get(rollup, "indexable_count", 0) or 0)
        evaluated = int(_get(rollup, "total_pages_evaluated", 0) or 0)
        summary = str(_get(rollup, "summary", "") or "").strip()
        code = "ISSUE_VERIFIED" if any((noindex, soft, blocked)) else "NO_ISSUE"
        return code, (
            f"Indexation rollup on {evaluated} page(s): {indexable} indexable, {noindex} noindex, "
            f"{soft} soft 404, {blocked} blocked by robots. "
            "Search Console coverage is separate and is not filled from this crawl. "
            + (summary or f"This line is {label}.")
        )
    if book.gsc_state != "MEASURED" and _has(text, "indexed versus", "crawled but not indexed", "search console", "missing from the index"):
        return _gsc_line(book, "Index coverage needs Search Console.")
    if not book.pages:
        return "NOT_TESTED", "Indexability was not classified because no page was crawled."
    noindex_pages = book.urls(lambda page: "noindex" in str(_get(page, "robots_meta", "") or "").lower() or "noindex" in str(_get(page, "x_robots_tag", "") or "").lower())
    if _has(text, "noindex", "robots meta", "x-robots"):
        code = "ISSUE_VERIFIED" if noindex_pages else "NO_ISSUE"
        return code, f"Crawled pages with a stored noindex directive: {_join(noindex_pages)}. Pages without a stored robots meta are not certified as indexed."
    if "soft 404" in text:
        return "NOT_TESTED", "Soft 404s were not classified. HTTP status codes in the sample are listed in the HTTP chapter."
    return "MEASURED", f"No noindex directive was stored on the crawled pages ({len(book.pages)}). That is the sample, not Search Console index coverage. This line is {label}."


def _http_line(book: _Book) -> Tuple[str, str]:
    http = _get(book.report, "http_status_breakdown")
    if http is not None and (_num(_get(http, "total_urls_checked")) or 0) > 0:
        broken = _get(http, "broken_links", None) or []
        text = (
            f"{int(_get(http, 'count_2xx', 0) or 0)} 2xx, {int(_get(http, 'count_3xx', 0) or 0)} 3xx, "
            f"{int(_get(http, 'count_4xx', 0) or 0)} 4xx, {int(_get(http, 'count_5xx', 0) or 0)} 5xx "
            f"across {int(_get(http, 'total_urls_checked', 0) or 0)} checked URL(s). "
            f"Broken link records: {len(broken)}."
        )
        code = "ISSUE_VERIFIED" if (int(_get(http, "count_4xx", 0) or 0) or int(_get(http, "count_5xx", 0) or 0) or broken) else "MEASURED"
        return code, text
    if not book.pages:
        return "NOT_TESTED", "No HTTP status was stored."
    codes: Dict[int, int] = {}
    for page in book.pages:
        code = int(_get(page, "status_code", 0) or 0)
        codes[code] = codes.get(code, 0) + 1
    listed = ", ".join(f"{count} × HTTP {code}" for code, count in sorted(codes.items()))
    return "MEASURED", f"Crawled responses: {listed}."


def _link_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    if "orphan" in text:
        orphan = _get(book.report, "orphan_pages")
        urls = list(_get(orphan, "orphan_urls", None) or _get(book.manifest, "orphan_urls", None) or [])
        if orphan is None and book.manifest is None:
            return "NOT_TESTED", "Orphan pages were not calculated."
        if not urls:
            return "NO_ISSUE", "No orphan URL was stored. That is the stored list, not a proof that every URL on the site is linked."
        return "ISSUE_VERIFIED", f"{len(urls)} orphan URL(s): {_join(urls)}."
    if _has(text, "click depth", "depth"):
        depth = _get(book.report, "click_depth")
        if depth is None or not (_num(_get(depth, "total_pages_analyzed")) or 0):
            return "NOT_TESTED", "Click depth was not calculated. Internal link counts on the crawled pages are not a depth map."
        return "MEASURED", (
            f"Click depth: {int(_get(depth, 'depth_1_count', 0) or 0)} at depth 1, "
            f"{int(_get(depth, 'depth_2_count', 0) or 0)} at depth 2, "
            f"{int(_get(depth, 'depth_3_count', 0) or 0)} at depth 3, "
            f"{int(_get(depth, 'depth_4_plus_count', 0) or 0)} at depth 4 or more. "
            f"Max depth {int(_get(depth, 'max_click_depth', 0) or 0)}."
        )
    if _has(text, "anchor", "click here"):
        audit = _get(book.report, "anchor_text_audit")
        if audit is None or not (_num(_get(audit, "total_links_analyzed")) or 0):
            return "NOT_TESTED", "Anchor text was not extracted. Link targets were counted where the crawl stored them, without the visible anchor words."
        generic = int(_get(audit, "generic_anchor_count", 0) or 0)
        summary = str(_get(audit, "summary", "") or "").strip()
        code = "ISSUE_VERIFIED" if generic else "NO_ISSUE"
        return code, f"{generic} generic anchor(s) in {int(_get(audit, 'total_links_analyzed', 0) or 0)} links. {summary}".strip()
    if not book.pages:
        return "NOT_TESTED", "Internal links were not counted because no page was crawled."
    rows = []
    for page in book.pages:
        internal = _get(page, "internal_links", None) or []
        external = _get(page, "external_links", None) or []
        rows.append(f"{_get(page, 'url')}: {len(internal)} internal, {len(external)} external")
    return "MEASURED", f"Link counts in the sample for “{label}”: {_join(rows)}. Counts are not anchor-text quality."


def _content_line(book: _Book, label: str) -> Tuple[str, str]:
    topical = _get(book.report, "topical_authority")
    if topical is not None and (_get(topical, "pages") or _num(_get(topical, "topical_coverage_score"))):
        summary = str(_get(topical, "summary", "") or "").strip()
        clusters = _get(topical, "cannibalization_clusters", None) or []
        return (
            "ISSUE_VERIFIED" if clusters or str(_get(topical, "status", "")).upper() in {"THIN_COMMODITY", "NEEDS_IMPROVEMENT"} else "MEASURED",
            (
                f"Topical module status { _get(topical, 'status') }. "
                f"Unbacked claims stored: {int(_get(topical, 'unbacked_claims_total', 0) or 0)}. "
                f"Cannibalization clusters: {len(clusters)}. "
                + (summary or book.sample)
            ),
        )
    words = _words(book)
    if not book.pages:
        return "NOT_TESTED", "Page text was not extracted."
    if not words:
        return "NOT_TESTED", "Word counts were not stored on the crawled pages. A missing count is not a thin-content verdict."
    listed = _join([f"{url}: {count} words" for url, count in words])
    flagged = book.urls(lambda page: bool(_get(page, "thin_content")))
    readability = [
        f"{_get(page, 'url')}: {float(_get(page, 'readability_score')):.0f}"
        for page in book.pages
        if (_num(_get(page, "readability_score")) or 0) > 0
    ]
    read_text = f" Readability scores stored: {_join(readability)}." if readability else " A readability score was not stored, so none is invented."
    if flagged:
        return "ISSUE_VERIFIED", f"Pages flagged as thin content: {_join(flagged)}. Extracted word counts: {listed}.{read_text} This line is {label}."
    return "MEASURED", f"Extracted word counts: {listed}.{read_text} A word count is not by itself a quality grade. This line is {label}."


def _ai_line(book: _Book, label: str) -> Tuple[str, str]:
    card = _get(book.report, "ai_visibility_scorecard")
    runs = _num(_get(card, "successful_runs")) or 0
    text = label.lower()
    if runs <= 0:
        geo = _get(book.report, "geo_readiness")
        extractability = _num(_get(geo, "extractability_score"))
        extra = ""
        if extractability is not None and _has(text, "extract", "answer", "quotable", "definition"):
            extra = f" On-page extractability is {extractability:.0f}. That number is not a citation rate."
        return (
            "NOT_TESTED",
            "Live engine responses were not measured. Google AI Overviews, Google AI Mode, and Bing Copilot were not queried. "
            "An SEO category score is not an AI citation rate."
            + extra,
        )
    engines = _get(card, "engines_queried", None) or []
    missing = _get(card, "surfaces_not_queried", None) or ["Google AI Overviews", "Google AI Mode", "Bing Copilot"]
    rates = []
    for key, name in (("mention_rate_pct", "mention rate"), ("citation_rate_pct", "citation rate"), ("competitor_visibility_pct", "competitor visibility")):
        value = _num(_get(card, key))
        if value is not None:
            rates.append(f"{name} {value}")
    accuracy = _num(_get(card, "citation_accuracy_pct"))
    accuracy_text = f" Citation accuracy {accuracy}." if accuracy is not None else " Citation accuracy was not span-checked."
    return (
        "MEASURED",
        f"Live responses for {label}: {', '.join(str(item) for item in engines) or 'engines stored'}. "
        f"{'; '.join(rates) or 'Rates were not all stored.'}{accuracy_text} "
        f"Not queried: {', '.join(str(item) for item in missing)}. Model API answers are not those consumer products.",
    )


def _local_line(book: _Book) -> Tuple[str, str]:
    local = _get(book.report, "local_seo")
    if local is not None and str(_get(local, "status", "")).upper() == "NOT_APPLICABLE":
        return "NOT_APPLICABLE", str(_get(local, "summary", "") or "The local module marked this site not applicable.")
    if local is not None and (str(_get(local, "summary", "") or "").strip() or _get(local, "nap_records") or _get(local, "status")):
        conflicts = len(_get(local, "phone_conflicts", None) or []) + len(_get(local, "address_conflicts", None) or [])
        code = "ISSUE_VERIFIED" if conflicts or str(_get(local, "status", "")).upper() in {"NEEDS_ATTENTION", "FAILED"} else "MEASURED"
        return code, (
            str(_get(local, "summary", "") or f"Local module status {_get(local, 'status')}.")
            + f" NAP conflict groups: {conflicts}. Map-pack rank was not invented."
        )
    has_local_schema = any("localbusiness" in item.lower() for item in _schema_types(book))
    return _specialist(book, _model_matches(book, ["local", "clinic", "restaurant", "dentist", "storefront", "multi-location"]), has_local_schema, "a local business")


def _international_line(book: _Book) -> Tuple[str, str]:
    intl = _get(book.report, "international_seo")
    if intl is not None and str(_get(intl, "status", "")).upper() == "NOT_APPLICABLE":
        return "NOT_APPLICABLE", str(_get(intl, "summary", "") or "The international module marked this site not applicable.")
    if intl is not None and (_num(_get(intl, "total_pages_with_hreflang")) or _get(intl, "issues") or str(_get(intl, "summary", "") or "").strip()):
        issues = len(_get(intl, "issues", None) or [])
        code = "ISSUE_VERIFIED" if issues or str(_get(intl, "status", "")).upper() in {"FAILED", "WARNING"} else "NO_ISSUE"
        return code, str(_get(intl, "summary", "") or f"{int(_get(intl, 'total_pages_with_hreflang', 0) or 0)} pages with hreflang. {issues} issue(s).")
    tagged = []
    langs = []
    for page in book.pages:
        tags = _get(page, "hreflang_tags") or {}
        lang = str(_get(page, "html_lang", "") or "").strip()
        if isinstance(tags, dict) and tags:
            tagged.append(f"{_get(page, 'url')}: {', '.join(list(tags)[:6])}")
        if lang:
            langs.append(f"{_get(page, 'url')}: {lang}")
        elif book.pages:
            langs.append(f"{_get(page, 'url')}: html lang not stored")
    if tagged:
        return "MEASURED", f"Hreflang in the sample: {_join(tagged)}. Return tags and x-default were not validated unless the international module stored that check. html lang: {_join(langs)}."
    if book.pages:
        fits = _model_matches(book, ["international", "multilingual", "multi-country"])
        if not fits and not book.model.strip():
            return "NOT_TESTED", f"html lang on the crawled pages: {_join(langs)}. A multilingual module was not selected because site type was not established."
        if not fits:
            return "NOT_APPLICABLE", f"html lang on the crawled pages: {_join(langs)}. The profile does not describe a multilingual site, so hreflang alternates were not required."
        return "NOT_TESTED", f"The profile can match a multilingual site. html lang: {_join(langs)}. Reciprocal hreflang was not validated."
    return _specialist(book, _model_matches(book, ["international", "multilingual", "multi-country"]), False, "an international or multilingual site")


def _redirect_line(book: _Book, label: str) -> Tuple[str, str]:
    audit = _get(book.report, "host_and_redirects")
    if audit is not None and (str(_get(audit, "summary", "") or "").strip() or _get(audit, "host_variants") or _get(audit, "chains_recorded")):
        loop = bool(_get(audit, "has_redirect_loop"))
        chain = bool(_get(audit, "has_chain_gt_1_hop"))
        code = "ISSUE_VERIFIED" if loop or chain or _get(audit, "redirects_to_4xx") else "MEASURED"
        return code, str(_get(audit, "summary", "") or f"Redirect audit stored. Loop={loop}. Chain over one hop={chain}. This line is {label}.")
    if not book.pages:
        return "NOT_TESTED", "Redirects were not fetched."
    redirected = book.urls(lambda page: bool(_get(page, "is_redirected")) or bool(_get(page, "redirect_chain")))
    if not redirected:
        return "NO_ISSUE", f"No redirect chain was stored on the crawled pages. This line is {label}. A full host-variant probe is included only when that audit was stored."
    return "MEASURED", f"Crawled URLs with a stored redirect: {_join(redirected)}."


def _viewport_line(book: _Book) -> Tuple[str, str]:
    if not book.pages:
        return "NOT_TESTED", "Viewport tags were not checked."
    missing = book.urls(lambda page: not str(_get(page, "viewport", "") or "").strip())
    if missing:
        return "ISSUE_VERIFIED", f"Pages without a viewport tag: {_join(missing)}."
    return "NO_ISSUE", "Every crawled page has a viewport tag. Tap targets, interstitials, and mobile parity were not separately tested."


def _js_line(book: _Book, label: str) -> Tuple[str, str]:
    if not book.pages:
        return "NOT_TESTED", "JavaScript rendering was not compared because no page was crawled."
    rows = []
    for page in book.pages:
        dom = int(_get(page, "dom_elements_count", 0) or 0)
        scripts = int(_get(page, "scripts_count", 0) or 0)
        sheets = int(_get(page, "stylesheets_count", 0) or 0)
        mode = str(_get(page, "render_mode", "") or "")
        if dom or scripts or sheets:
            rows.append(f"{_get(page, 'url')}: DOM {dom or 'not counted'}, scripts {scripts or 'not counted'}, stylesheets {sheets or 'not counted'}, render mode {mode or 'not stored'}")
    if not rows:
        return "NOT_TESTED", f"{label} was not counted. Raw HTML versus rendered DOM was not diffed unless a lab record stored raw_vs_rendered_diff."
    return "MEASURED", _join(rows) + ". A count is not a hydration-failure test."


def _cta_line(book: _Book) -> Tuple[str, str]:
    texts = []
    for page in book.pages:
        labels = list(_get(page, "ctas", None) or []) + list(_get(page, "call_to_actions", None) or [])
        if labels:
            texts.append(f"{_get(page, 'url')}: {', '.join(str(item) for item in labels[:6])}")
    primary = book.profile_value("primary_cta")
    if primary:
        texts.append(f"Profile primary CTA: {primary}")
    secondary = book.profile_value("secondary_cta")
    if secondary:
        texts.append(f"Profile secondary CTA: {secondary}")
    rate = _ga4_line(book, "Conversion rate.")
    if rate[0] == "MEASURED":
        sessions = _num(book.analytics.get("sessions"))
        events = _num(book.analytics.get("key_events"))
        if sessions and sessions > 0 and events is not None:
            ratio = round((events / sessions) * 1000) / 10
            return "MEASURED", f"GA4 key-event rate is {ratio}% ({events} key events / {sessions} sessions). This is not a 0–100 conversion grade. Visible CTAs: {_join(texts) if texts else 'none stored'}."
    if not texts:
        return "NOT_TESTED", "No CTA text was stored on the crawled pages, and GA4 did not provide a key-event rate. No conversion rate is invented."
    return "INFERRED", f"Visible calls to action in the sample: {_join(texts)}. No conversion rate is shown because GA4 landing pages and key events were not both measured."


def _backlink_line(book: _Book) -> Tuple[str, str]:
    authority = _get(book.report, "external_authority") or {}
    if not isinstance(authority, dict):
        authority = {}
    sections = authority.get("sections") if isinstance(authority.get("sections"), dict) else {}
    backlinks = sections.get("backlink_profile") if isinstance(sections, dict) else None
    if not backlinks:
        return "DATA_UNAVAILABLE", "No backlink provider was connected. A missing provider is not a zero, not a toxicity score, and not an SEO failure."
    return "MEASURED", "Backlink fields come from the connected provider on the authority report. They are not Google ranking metrics."


def _competitor_line(book: _Book) -> Tuple[str, str]:
    bakeoff = _get(book.report, "competitor_bakeoff")
    if bakeoff is not None and (_get(bakeoff, "competitor_domain") or _num(_get(bakeoff, "target_wins")) is not None):
        return "MEASURED", (
            f"Stored bake-off versus {_get(bakeoff, 'competitor_domain') or 'the named peer'}: "
            f"target wins {_get(bakeoff, 'target_wins')}, competitor wins {_get(bakeoff, 'competitor_wins')}, ties {_get(bakeoff, 'ties')}. "
            "This is the stored comparison, not a keyword-gap index."
        )
    named = _get(book.profile, "competitors") or []
    if not named:
        return "DATA_UNAVAILABLE", "No competitor inventory was stored. An uncrawled rival is left blank. No overlap or gap number is invented."
    return "MEASURED", "Named competitors on the profile: " + ", ".join(str(item) for item in list(named)[:8]) + ". A name is not a measured ranking gap."


def _forecast_line() -> Tuple[str, str]:
    return "NOT_TESTED", "No traffic, ranking, or revenue forecast is produced. An assumed lift is not multiplied by traffic. Nothing in this audit is a promised gain."


def _route(book: _Book, label: str) -> Optional[Tuple[str, str]]:
    text = label.lower()
    if _has(text, "lcp", "inp", "cls", "core web vital", "field data", "laboratory", "lighthouse", "render-blocking", "main-thread", "third-party script"):
        return _cwv_line(book, label)
    if _has(text, "ttfb", "time to first byte", "response latency", "server response", "compression", "cache-control", "gzip", "brotli"):
        return _timing_line(book, label)
    if "robots.txt" in text and "compromised" not in text:
        return _robots_txt_line(book)
    if "sitemap" in text and not _has(text, "compromised", "report", "update", "verification", "monitoring", "partition"):
        return _sitemap_line(book, label)
    if "canonical" in text and not _has(text, "javascript", "hreflang", "syndicat", "partition", "decision", "product canon", "verification"):
        return _canonical_line(book, label)
    if _has(text, "noindex", "soft 404", "indexable", "indexed versus", "crawled but not indexed", "x-robots"):
        return _index_line(book, label)
    if _has(text, "hreflang", "multilingual", "html lang", "x-default"):
        return _international_line(book)
    if _has(text, "redirect", "404", "410", "broken link", "broken internal", "broken external"):
        return _redirect_line(book, label)
    if _has(text, "hsts", "content-security-policy", "security header", "mixed content", "certificate", "https coverage"):
        return _security_line(book, label)
    if _has(text, "schema", "json-ld", "structured data", "organization", "localbusiness", "breadcrumblist", "videoobject", "product and offer"):
        return _schema_line(book, label)
    if _has(text, "alt text", "image alternative", "decorative image"):
        return _image_line(book, label)
    if "open graph" in text or "social sharing image" in text:
        if not book.pages:
            return "NOT_TESTED", "Open Graph tags were not read because no page was crawled."
        missing = book.urls(lambda page: not (_get(page, "og_tags") or {}))
        present = len(book.pages) - len(missing)
        code = "ISSUE_VERIFIED" if missing else "NO_ISSUE"
        return code, f"{present} crawled page(s) store Open Graph tags. Pages without them: {_join(missing)}."
    if text.startswith("h1") or _has(text, "heading", "h2", "h3", "primary heading"):
        return _heading_line(book, label)
    if _has(text, "meta description", "missing description") or text.startswith("snippet quality"):
        return _meta_line(book, label)
    if _has(text, "title tag", "missing title", "duplicate title", "title length", "boilerplate title"):
        return _title_line(book, label)
    if _has(text, "viewport", "tap target", "interstitial", "mobile-first", "responsive layout"):
        return _viewport_line(book)
    if _has(text, "word count", "thin content", "readability", "completeness of the topic"):
        return _content_line(book, label)
    if _has(text, "search console", "impressions", "average position", "manual action"):
        return _gsc_line(book, label + ".")
    if _has(text, "ga4", "key event", "organic landing", "engaged session"):
        return _ga4_line(book, label + ".")
    if _has(text, "forecast", "scenario", "revenue-per", "addressable keyword"):
        return _forecast_line()
    if _has(text, "backlink", "referring domain", "link spam", "digital pr", "brand mention"):
        return _backlink_line(book)
    if _has(text, "competitor", "keyword gap", "keyword overlap"):
        return _competitor_line(book)
    if _has(text, "ai overview", "chatgpt", "perplexity", "gemini", "copilot", "citation share", "citation frequency", "mention rate"):
        return _ai_line(book, label)
    if _has(text, "google business", "local pack", "service area", "nap"):
        return _local_line(book)
    if _has(text, "orphan"):
        return _link_line(book, label)
    if _has(text, "click depth", "anchor text", "internal link"):
        return _link_line(book, label)
    if _has(text, "render-blocking", "hydration", "client-side", "lazy-loaded"):
        return _js_line(book, label)
    if _has(text, "cta", "conversion rate", "form length", "form usability"):
        return _cta_line(book)
    return None


def _profile_line(book: _Book, label: str) -> Tuple[str, str]:
    text = label.lower()
    mapping = (
        ("business model", "business_model"),
        ("revenue", "business_model"),
        ("products", "products"),
        ("services", "services"),
        ("offering", "services"),
        ("audience", "target_audience"),
        ("persona", "target_audience"),
        ("location", "geography"),
        ("market", "geography"),
        ("conversion action", "primary_cta"),
        ("value proposition", "value_proposition"),
    )
    if _has(text, "search demand"):
        return _gsc_line(book, "Search demand aligned with the business.")
    if _has(text, "regulatory", "platform", "website type"):
        industry = book.profile_value("industry") or book.profile_value("business_model")
        if industry:
            return "INFERRED", f"Stored profile text: {industry}. The publishing platform was not fingerprinted, and no regulatory certificate is claimed."
        return "NOT_TESTED", "Website platform and regulatory scope were not stored."
    for needle, field in mapping:
        if needle in text:
            value = book.profile_value(field)
            if needle == "revenue":
                return (
                    "DATA_UNAVAILABLE" if not value else "INFERRED",
                    (f"Stored business model: {value}. " if value else "")
                    + "Revenue and pipeline were not measured. No revenue figure is shown.",
                )
            if not value:
                return "NOT_TESTED", f"{label} was not stored on the business profile."
            return "INFERRED", f"{label}: {value}."
    story = str(_get(book.report, "story_summary", "") or "").strip()
    if story and _has(text, "overview", "objective", "health", "strength", "opportunit", "recommendation", "risk"):
        return "INFERRED", story
    if not book.profile_value("business_name") and not story:
        return "NOT_TESTED", f"{label} was not established from a stored profile or narrative."
    parts = [book.profile_value(name) for name in ("business_name", "industry", "business_model", "value_proposition")]
    parts = [part for part in parts if part]
    return "INFERRED", f"{label}. Stored profile: {'; '.join(parts) or 'name only'}. {book.sample}"


def _by_section(book: _Book, number: str, label: str) -> Tuple[str, str]:
    text = label.lower()
    if number == "01":
        if _has(text, "traffic", "visibility"):
            return _gsc_line(book, "Search visibility.")
        if _has(text, "ai search"):
            return _ai_line(book, label)
        if _has(text, "conversion", "revenue"):
            return _cta_line(book)
        if "competitor" in text:
            return _competitor_line(book)
        if _has(text, "critical", "opportunit", "recommendation", "holding"):
            defects = [finding for finding in book.findings if _is_defect(finding)]
            if not defects:
                story = str(_get(book.report, "primary_strategic_opportunity", "") or "").strip()
                return ("INFERRED" if story else "NOT_TESTED"), story or "No defect finding and no strategic opportunity were stored."
            top = _join([f"{_get(item, 'severity')} — {_get(item, 'title')}" for item in defects[:8]])
            opportunity = str(_get(book.report, "primary_strategic_opportunity", "") or "").strip()
            return "ISSUE_VERIFIED", f"Recorded defects include {top}." + (f" Stored opportunity: {opportunity}." if opportunity else "")
        return _profile_line(book, label)
    if number == "02":
        scores = _get(_get(book.report, "scores"), "category_scores") or {}
        names = []
        if isinstance(scores, dict):
            for key, value in scores.items():
                score = _num(_get(value, "score", value if isinstance(value, (int, float)) else None))
                if score is not None:
                    names.append(f"{str(key).replace('_', ' ').lower()} {score:.0f}")
        if not names:
            return "NOT_TESTED", "No category score was sealed. This book does not invent an overall SEO grade from the checklist. " + book.sample
        if _has(text, "local"):
            return _local_line(book)
        if _has(text, "international"):
            return _international_line(book)
        if _has(text, "backlink", "authority"):
            return _backlink_line(book)
        if _has(text, "core web", "performance", "experience"):
            return _cwv_line(book, label)
        if _has(text, "aeo", "geo", "measurement confidence"):
            return _ai_line(book, label)
        return "MEASURED", "Sealed category scores: " + "; ".join(names) + ". Modules without a measurement are not folded into that number. This line is " + label + "."
    if number == "03":
        return _profile_line(book, label)
    if number in {"04", "06"}:
        defects = [finding for finding in book.findings if _is_defect(finding)]
        if not defects:
            return ("NOT_TESTED" if not book.pages else "NO_ISSUE"), "No defect finding was recorded. That is not a claim that every possible risk was tested. " + book.sample
        ranked = sorted(defects, key=lambda item: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(str(_get(item, "severity", "")).upper(), 4))
        shown = _join([
            f"{_get(item, 'severity')} effort {_get(item, 'effort')} — {_get(item, 'title')}"
            for item in ranked[:10]
        ])
        if number == "06" and _has(text, "30", "60", "90", "roadmap", "owner", "deadline"):
            roadmaps = [
                ("7-day", _get(book.report, "roadmap_7_days", None) or []),
                ("30-day", _get(book.report, "roadmap_30_days", None) or []),
                ("90-day", _get(book.report, "roadmap_90_days", None) or []),
            ]
            stored = [name for name, items in roadmaps if items]
            if not stored:
                return "NOT_TESTED", f"No 7/30/90 roadmap items were stored. Findings available for sequencing: {shown}."
            return "INFERRED", "Roadmap buckets stored: " + ", ".join(stored) + f". Findings: {shown}."
        if _has(text, "critical technical", "issue severity", "affected url", "implementation effort", "expected impact", "quick win"):
            return "ISSUE_VERIFIED", f"{len(defects)} defect finding(s). {shown}."
        return "NOT_TESTED", f"{label} was not given its own evidence. The finding register has {len(defects)} defect(s): {shown}."
    if number == "05" or number in {"33", "F"}:
        return _competitor_line(book)
    if number == "07":
        if _has(text, "http", "crawler access"):
            return _http_line(book)
        if _has(text, "robots meta"):
            return _index_line(book, label)
        if _has(text, "internal link", "resource"):
            return _link_line(book, label)
        if _has(text, "googlebot", "crawler access difference"):
            http = _http_line(book)
            return "NOT_TESTED", "Googlebot and other crawlers were not fetched as separate user agents. One crawl was used. " + http[1]
        if _has(text, "trap", "infinite", "facet", "parameter", "budget"):
            discovered = _num(_get(book.manifest, "total_pages_discovered"))
            return "NOT_TESTED", (
                f"{label} was not given a separate detector. "
                f"Discovered URLs: {int(discovered) if discovered else 'not stored'}. Crawled: {len(book.pages)}."
            )
        robots = _robots_txt_line(book)
        sitemap = _sitemap_line(book, "Sitemap discovery")
        return robots[0] if robots[0] == "ISSUE_VERIFIED" else sitemap[0], robots[1] + " " + sitemap[1]
    if number == "08":
        return _index_line(book, label)
    if number == "09":
        if not book.pages:
            return "NOT_TESTED", "No URLs were crawled, so URL architecture was not reviewed."
        urls = [str(_get(page, "url", "") or "") for page in book.pages]
        slash = [url for url in urls if url.rstrip("/").count("/") > 2 and url.endswith("/")]
        bare = [url for url in urls if not url.endswith("/")]
        upper = [url for url in urls if re.search(r"[A-Z]", url.split("://", 1)[-1])]
        query = [url for url in urls if "?" in url]
        http_urls = [url for url in urls if url.lower().startswith("http://")]
        if "trailing" in text:
            return "MEASURED", f"{len(slash)} crawled URL(s) end with a slash and {len(bare)} do not. URLs: {_join(urls)}."
        if _has(text, "https", "http", "www"):
            return ("ISSUE_VERIFIED" if http_urls else "MEASURED"), f"HTTP URLs: {_join(http_urls)}. Sample: {_join(urls)}. Host-variant consolidation is in the redirect audit when that audit was stored."
        if _has(text, "uppercase", "lowercase"):
            return ("ISSUE_VERIFIED" if upper else "NO_ISSUE"), f"URLs with uppercase characters: {_join(upper)}."
        if _has(text, "query", "parameter", "session", "tracking"):
            return ("MEASURED" if query else "NO_ISSUE"), f"Crawled URLs with a query string: {_join(query)}."
        if "depth" in text:
            depths = [f"{url} ({max(url.split('://', 1)[-1].count('/'), 0)} slashes)" for url in urls]
            return "MEASURED", "Path shape, which is not click depth: " + _join(depths) + "."
        return "MEASURED", f"{label}. Crawled URLs: {_join(urls)}."
    if number == "10":
        if "canonical" not in text:
            presence = _canonical_line(book, "Canonical tag presence")
            return "NOT_TESTED", f"{label} was not tested as its own duplicate class. Related canonical result: {presence[1]}"
        return _canonical_line(book, label)
    if number == "11":
        return _redirect_line(book, label)
    if number == "12":
        return _sitemap_line(book, label)
    if number == "13":
        return _link_line(book, label)
    if number == "14":
        if _has(text, "ttfb", "latency", "byte", "compression", "cache", "cdn"):
            return _timing_line(book, label)
        if _has(text, "tls", "https", "certificate"):
            return _security_line(book, label)
        return _http_line(book)
    if number == "15":
        return _js_line(book, label)
    if number == "16" or number == "I":
        return _cwv_line(book, label)
    if number == "17":
        if "speed" in text:
            return _cwv_line(book, label)
        return _viewport_line(book)
    if number == "18":
        if _has(text, "hsts", "csp", "header", "https", "certificate", "mixed", "insecure"):
            return _security_line(book, label)
        return "NOT_TESTED", (
            f"{label} was not tested. This chapter is a header and transport baseline, "
            "not a malware certification or a penetration test."
        )
    if number == "19" or number == "H":
        return _schema_line(book, label)
    if number == "20":
        if _has(text, "meta", "description", "snippet"):
            return _meta_line(book, label)
        return _title_line(book, label)
    if number == "21":
        return _heading_line(book, label)
    if number in {"22", "34", "48", "E", "J"}:
        return _gsc_line(book, label + ".")
    if number in {"23", "24", "25"}:
        return _content_line(book, label)
    if number == "26":
        if _has(text, "title", "duplicate", "cannibal"):
            titles = _title_line(book, "Duplicate titles")
            return titles
        return _content_line(book, label)
    if number == "27":
        return _link_line(book, label)
    if number == "28":
        return _image_line(book, label)
    if number == "29":
        types = _schema_types(book)
        video = [item for item in types if "video" in item.lower()]
        if video:
            return "MEASURED", f"Video-related schema in the sample: {', '.join(video)}. Transcripts, a video sitemap, and watch-page indexing were not tested."
        if book.pages:
            return "NOT_TESTED", "No VideoObject schema was stored in the crawled sample. A video-search audit was not run."
        return "NOT_TESTED", "Video SEO was not tested."
    if number in {"30", "37", "44", "54", "55", "M"}:
        if number == "54":
            checks = [finding for finding in book.findings if _get(finding, "remediation_verification")]
            if checks:
                return "MEASURED", f"{len(checks)} finding(s) have a stored verification record. A recommended patch without that record is not a completed retest."
        if number == "55" or number == "M":
            regression = _get(book.report, "regression_report")
            if regression is not None:
                summary = str(_get(regression, "summary", "") or "").strip()
                code = "ISSUE_VERIFIED" if _get(regression, "has_regression") else "MEASURED"
                return code, summary or "A comparison with an earlier audit was stored."
        reasons = {
            "30": "Editorial ownership, calendars, and review workflow are not visible to this crawl.",
            "37": "Spam and policy checks were not confirmed. A pattern finding is a review item, not a declared manual action.",
            "44": "Voice, visual, and multimodal queries were not run.",
            "54": "No post-fix retest was stored. A recommended patch is not a completed verification.",
            "55": "No earlier audit was compared. Ongoing monitoring is not claimed from this single run.",
            "M": "No earlier audit was compared. Ongoing monitoring is not claimed from this single run.",
        }
        return "NOT_TESTED", reasons.get(number, "This operation was not executed on this run.") + f" This line is {label}."
    if number == "31" or number == "G":
        return _backlink_line(book)
    if number == "32":
        return _backlink_line(book)
    if number == "35":
        return _local_line(book)
    if number == "36":
        return _international_line(book)
    if number == "38":
        commerce = _get(book.report, "ecommerce_seo")
        if commerce is not None and (bool(_get(commerce, "is_ecommerce_detected")) or str(_get(commerce, "status", "")).upper() not in {"", "NOT_APPLICABLE"}):
            summary = str(_get(commerce, "summary", "") or "").strip()
            return (
                "NOT_APPLICABLE" if str(_get(commerce, "status", "")).upper() == "NOT_APPLICABLE" else "MEASURED",
                summary or f"Commerce module status {_get(commerce, 'status')}. Products analyzed: {int(_get(commerce, 'products_analyzed', 0) or 0)}.",
            )
        has_product = any(item.lower() == "product" or "product" in item.lower() for item in _schema_types(book))
        return _specialist(book, _model_matches(book, ["ecommerce", "e-commerce", "retail", "shop", "catalog"]), has_product, "an e-commerce catalog")
    if number == "39":
        has_news = any("newsarticle" in item.lower() or item.lower() == "article" for item in _schema_types(book))
        return _specialist(book, _model_matches(book, ["news", "publisher", "magazine", "journal"]), has_news, "a news publisher")
    if number == "40":
        discovered = _num(_get(book.manifest, "total_pages_discovered")) or 0
        if discovered >= 200:
            return "NOT_TESTED", f"{int(discovered)} URLs were discovered and {len(book.pages)} were crawled. A programmatic template audit was not run, so unfetched URLs are not judged."
        return "NOT_APPLICABLE", "No large generated URL space was discovered, so programmatic SEO was not selected. " + book.sample
    if number == "41":
        fits = _model_matches(book, ["saas", "b2b", "software", "lead gen", "lead-gen", "subscription"])
        if not book.model.strip():
            return "NOT_TESTED", "Site type was not established, so SaaS and lead-generation SEO was not selected."
        if not fits:
            return "NOT_APPLICABLE", "The business profile does not describe a SaaS or lead-generation business."
        return "INFERRED", f"The business profile matches SaaS or lead generation. {book.sample} CRM pipeline and qualified leads were not measured."
    if number == "42":
        app_link = False
        for page in book.pages:
            blob = str(_get(page, "url", "")) + " " + " ".join(str(item) for item in (_get(page, "external_links", None) or []))
            if "apps.apple.com" in blob or "play.google.com" in blob:
                app_link = True
        if app_link:
            return "NOT_TESTED", "An app-store link was seen. Store listing text, ratings, and install measurement were not audited."
        return "NOT_APPLICABLE", "No mobile-app listing was in scope."
    if number == "43":
        screen = "This is an automated observation, not a WCAG certification and not a ranking score."
        wcag = _get(book.report, "wcag_audit")
        if _has(text, "certificate", "ranking score"):
            if wcag is None or not (_num(_get(wcag, "total_checks_performed")) or 0):
                return "MEASURED", "No automated accessibility screen was stored. " + screen
            return "MEASURED", (
                f"{int(_get(wcag, 'violations_count', 0) or 0)} automated violation(s) in "
                f"{int(_get(wcag, 'total_checks_performed', 0) or 0)} checks. " + screen
            )
        if _has(text, "image"):
            images = _image_line(book, label)
            return images[0], images[1] + " " + screen
        if _has(text, "heading"):
            headings = _heading_line(book, label)
            return headings[0], headings[1] + " " + screen
        if wcag is None or not (_num(_get(wcag, "total_checks_performed")) or 0):
            return "NOT_TESTED", f"{label} was not in an automated accessibility screen. " + screen
        violations = int(_get(wcag, "violations_count", 0) or 0)
        code = "ISSUE_VERIFIED" if violations else "NO_ISSUE"
        return code, (
            f"{violations} automated violation(s) in {int(_get(wcag, 'total_checks_performed', 0) or 0)} checks. "
            + screen + f" This line is {label}."
        )
    if number == "45":
        geo = _get(book.report, "geo_readiness")
        questions = _get(geo, "questions", None) or []
        if questions:
            supported = int(_get(geo, "questions_supported", 0) or 0)
            total = int(_get(geo, "questions_total", 0) or len(questions))
            return "MEASURED", (
                f"On-page answer evidence: {supported} supported of {total} assessed questions. "
                "A completed assessment is not an answered live query. This is not an AI Overview citation. "
                f"This line is {label}."
            )
        return _ai_line(book, label)
    if number == "46":
        geo = _get(book.report, "geo_readiness")
        extractability = _num(_get(geo, "extractability_score"))
        if extractability is None and not book.pages:
            return "NOT_TESTED", "On-page extractability was not scored. It would not be a live citation rate."
        if extractability is None:
            return "MEASURED", "Crawl evidence exists. A separate extractability score was not stored. Live citations are a different chapter. " + book.sample
        return "MEASURED", f"On-page extractability is {extractability:.0f}. This is not a ChatGPT, Perplexity, or AI Overview citation rate. This line is {label}."
    if number == "47" or number == "K":
        return _ai_line(book, label)
    if number == "49":
        return _ga4_line(book, label + ".")
    if number == "50":
        return _cta_line(book)
    if number == "51":
        if book.ga4_state == "MEASURED" and book.analytics.get("key_events") is not None:
            return "DATA_UNAVAILABLE", (
                f"GA4 recorded key events={book.analytics.get('key_events')} and sessions={book.analytics.get('sessions')}. "
                "Currency revenue, pipeline, and acquisition cost were not measured. Key events are not revenue."
            )
        return "DATA_UNAVAILABLE", "Organic revenue was not measured. No revenue figure is shown."
    if number == "52":
        return _forecast_line()
    if number in {"53", "D", "L"}:
        defects = [finding for finding in book.findings if _is_defect(finding)]
        notes = len(book.findings) - len(defects)
        if not book.findings:
            return ("NOT_TESTED" if not book.pages else "NO_ISSUE"), "No finding was recorded for this sample. That is not a claim that every check passed. " + book.sample
        if _has(text, "owner", "deadline", "responsible", "validation method", "implementation", "business value", "remediation status", "effort estimate"):
            return "NOT_TESTED", (
                f"{label} was not assigned on this run. "
                f"The register has {len(defects)} defect finding(s) and {notes} observation(s)."
            )
        return "ISSUE_VERIFIED" if defects else "INFERRED", (
            f"{len(defects)} defect finding(s) and {notes} observation(s) are in the register. "
            "Each one is also placed under the matching chapter. "
            f"This line is {label}."
        )
    if number in {"A", "B", "N", "O"}:
        if number in {"B", "O"}:
            return "MEASURED", (
                "Status labels in this book are Not applicable, Not tested, Data unavailable, No issue in the checked sample, "
                "Issue verified, Inferred, and Measured. A missing connector is not a score of zero. "
                f"This line is {label}."
            )
        return "MEASURED", book.sample + " Sections marked not tested or data unavailable were not given a zero. This line is " + label + "."
    if number == "C":
        if not book.pages:
            return "NOT_TESTED", "No URL inventory was crawled."
        return "MEASURED", book.sample + " The URL table in this appendix lists the crawled rows."
    routed = _route(book, label)
    if routed:
        return routed
    if not book.pages:
        return "NOT_TESTED", f"{label} was not measured. This run did not store the source this line needs."
    return "NOT_TESTED", f"{label} was not given a separate instrument. {book.sample}"


def _line(book: _Book, number: str, label: str) -> Tuple[str, str]:
    routed = _route(book, label)
    if routed and number not in {"01", "02", "03", "04", "06", "43"}:
        return routed
    return _by_section(book, number, label)


def _section_summary(book: _Book, number: str) -> Tuple[str, str]:
    probe = {
        "01": "Website and business overview",
        "02": "Overall SEO health score",
        "07": "Crawler access and HTTP responses",
        "12": "Sitemap discovery",
        "14": "HTTP status, hosting and server reliability",
        "16": "Largest Contentful Paint (LCP)",
        "20": "Title tags and search snippets",
        "47": "Google AI Overviews and AI Mode",
    }.get(number, "Chapter result")
    if number in {"16", "I"}:
        return _cwv_line(book, "Core Web Vitals")
    if number in {"47", "K"}:
        return _ai_line(book, "AI search visibility")
    if number == "52":
        return _forecast_line()
    code, text = _by_section(book, number, probe)
    return code, text



def _stored_narrative(report: Any, name: str) -> str:
    value = str(_get(report, name, "") or "").strip()
    return value


def _chapter_agent_consultation_card(book: _Book, number: str, section: Dict[str, Any], findings: List[Any]) -> str:
    narrative = generate_chapter_narrative(book, number, section, findings)
    data_table = generate_chapter_data_table(book, number)
    
    table_block = f"""
    <div class="chapter-empirical-evidence">
        <h5 class="evidence-table-title">Empirical Evidence &amp; Telemetry Matrix</h5>
        {data_table}
    </div>
    """ if data_table else ""
    
    return f"""
    <div class="agent-consulting-dossier">
        <div class="agent-header-strip">
            <div class="agent-badge">
                <span class="agent-id-tag">{_esc(narrative['agent_id'])}</span>
                <strong class="agent-name">{_esc(narrative['agent_name'])}</strong>
            </div>
            <span class="agent-role-title">{_esc(narrative['agent_role'])}</span>
        </div>
        
        <div class="consulting-section diagnostic-block">
            <h5 class="consulting-heading">Executive Diagnostic Review &amp; Strategy</h5>
            <p class="consulting-narrative">{_esc(narrative['diagnostic_overview'])}</p>
        </div>
        
        <div class="consulting-grid">
            <div class="consulting-col">
                <h5 class="consulting-subheading">Technical &amp; Architectural Mechanics</h5>
                <p class="consulting-text">{_esc(narrative['technical_mechanics'])}</p>
            </div>
            <div class="consulting-col">
                <h5 class="consulting-subheading">Root Cause &amp; Business Impact Risk</h5>
                <p class="consulting-text"><strong>Root Cause:</strong> {_esc(narrative['root_cause_analysis'])}</p>
                <p class="consulting-text"><strong>Search Risk:</strong> {_esc(narrative['business_risk'])}</p>
            </div>
        </div>
        
        <div class="consulting-grid">
            <div class="consulting-col">
                <h5 class="consulting-subheading">Prescriptive Engineering &amp; Content Fix</h5>
                <div class="code-fix-block">
                    <code>{_esc(narrative['prescriptive_fix'])}</code>
                </div>
            </div>
            <div class="consulting-col">
                <h5 class="consulting-subheading">Post-Fix Verification &amp; Regression Testing</h5>
                <div class="verification-block">
                    <code>{_esc(narrative['verification_protocol'])}</code>
                </div>
            </div>
        </div>
        
        {table_block}
    </div>
    """


def render_seo_audit_book(report: Any) -> str:
    """Render sections 01–55 and appendices A–O as evidence chapters."""
    payload = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    book = _Book(report)
    grouped: Dict[str, List[Any]] = {}
    for finding in book.findings:
        grouped.setdefault(_section_for_finding(finding), []).append(finding)
    part_titles = {part["id"]: part["title"] for part in payload["parts"]}

    scores = _get(report, "scores")
    categories = _get(scores, "category_scores") or {}
    technical = categories.get("TECHNICAL_SEO") if isinstance(categories, dict) else None
    technical_score = _num(_get(technical, "score"))
    technical_status = str(_get(technical, "status", "") or "").upper()
    base_score = _num(_get(scores, "overall_score")) if scores else None
    if technical_score is not None and technical_status not in {"NOT_MEASURED", "NOT_TESTED"}:
        score_label = "TECHNICAL SEO CATEGORY SCORE"
        score_disp = str(int(round(technical_score)))
        score_note = "Sealed category score. Not a grade of every chapter."
    elif base_score is not None:
        score_label = "SEALED OVERALL SCORE"
        score_disp = str(int(round(base_score)))
        score_note = "Sealed report score. Not a grade of every chapter."
    else:
        score_label = "SEO SCORE"
        score_disp = "—"
        score_note = "No sealed score was stored."
    domain = _esc(_get(report, "domain", "") or "Target domain")
    story = _esc(_stored_narrative(report, "story_summary") or "No executive narrative was stored. The chapters below use the sealed evidence.")
    points = []
    for field_name, heading in (
        ("what_site_gets_right", "Narrative — what is working"),
        ("what_is_holding_it_back", "Narrative — what is holding it back"),
        ("primary_strategic_opportunity", "Narrative — stated opportunity"),
    ):
        text = _stored_narrative(report, field_name)
        if text:
            points.append(f'<div class="point-item"><strong>{_esc(heading)}:</strong> {_esc(text)}</div>')
    points_html = f'<div class="exec-key-points">{"".join(points)}</div>' if points else ""

    exec_block = f"""
    <div class="exec-summary-dossier">
        <div class="dossier-meta-bar">
            <span>AUDITED DOMAIN: <strong>{domain}</strong></span>
            <span>SAMPLE: <strong>REPRESENTATIVE</strong></span>
            <span>PROVENANCE: <strong>STORED EVIDENCE</strong></span>
        </div>
        <div class="exec-scorecard-grid">
            <div class="kpi-score-card">
                <span class="kpi-label">{score_label}</span>
                <div class="kpi-number">{score_disp}<span class="kpi-denom">/100</span></div>
                <span class="kpi-grade">{_esc(score_note)}</span>
            </div>
            <div class="kpi-narrative-card">
                <p class="chart-title">Stored narrative</p>
                <p>{story}</p>
                {points_html}
            </div>
        </div>
    </div>
    """

    toc = ["<h2>Complete SEO audit: Master Table of Contents (Sections 01–55 &amp; Appendices A–O)</h2>", "<nav class=\"toc\"><ol>"]
    blocks = [
        f"<p class=\"lead-scope-note\">{_esc(book.sample)} Each chapter states the data source, charts only stored measurements, "
        "and then records every sub-index line. A missing integration stays unmeasured. It is not a zero and it is not a pass.</p>",
    ]
    tally: Dict[str, int] = {}

    for part in payload["parts"]:
        owned = [section for section in payload["sections"] if section["part"] == part["id"]]
        if not owned:
            continue
        blocks.append(f"<h3 id=\"part-{_esc(part['id'])}\" class=\"part-header\">Part {_esc(part['id'])} — {_esc(part['title'])}</h3>")
        for section in owned:
            number = section["number"]
            toc.append(
                f"<li><a href=\"#seo-{_esc(number)}\"><span>{_esc(number)}</span> {_esc(section['title'])}</a></li>"
            )
            status, summary = _section_summary(book, number)
            section_findings = grouped.get(number, [])
            defects = [item for item in section_findings if _is_defect(item)]
            if defects and status in {"NOT_TESTED", "DATA_UNAVAILABLE", "NO_ISSUE", "MEASURED", "NOT_APPLICABLE", "INFERRED"}:
                status = "ISSUE_VERIFIED"
                summary = f"{len(defects)} recorded empirical finding(s) in this chapter. {summary}"
            assigned = _assign(section_findings, section["checks"])
            checks_html = []
            line_codes: List[str] = []
            for check in section["checks"]:
                code, result = _line(book, number, check)
                cards = assigned.get(check, [])
                if any(_is_defect(item) for item in cards):
                    code = "ISSUE_VERIFIED"
                line_codes.append(code)
                tally[code] = tally.get(code, 0) + 1
                checks_html.append(
                    f"<article class=\"check {_CLASS.get(code, 'untested')}\">"
                    f"<h5>{_esc(check)}</h5>"
                    f"<p class=\"status\">{_esc(_LABEL.get(code, 'Not tested'))}</p>"
                    f"<p class=\"check-result-text\">{_esc(result)}</p>"
                    f"{''.join(_finding_card(item) for item in cards)}"
                    "</article>"
                )

            agent_card = _chapter_agent_consultation_card(book, number, section, section_findings)
            blocks.append(
                f"<section class=\"seo-section\" id=\"seo-{_esc(number)}\">"
                f"<p class=\"part-label\">Part {_esc(section['part'])} — {_esc(part_titles.get(section['part'], ''))}</p>"
                f"<h4>{_esc(number)}. {_esc(section['title'])}</h4>"
                f"<p class=\"status\">{_esc(_LABEL.get(status, 'Not tested'))} · {_esc(book.sample)}</p>"
                f"<p class=\"section-summary-lead\">{_esc(summary)}</p>"
                f"{chapter_panel(book, number, line_codes)}"
                f"{agent_card}"
                '<div class="sub-index-ledger-header"><h5>Sub-Index Evidence &amp; Verification Ledger</h5>'
                f'<p class="ledger-desc">Deterministic evaluation of each taxonomy parameter under crawled conditions.</p></div>'
                '<p class="sources-kicker">Sub-index evidence</p>'
                f"{''.join(checks_html)}"
                "</section>"
            )
    toc.append("</ol></nav>")
    return "\n".join([exec_block, evidence_mix_chart(tally), toc[0], blocks[0], *toc[1:], *blocks[1:]])

