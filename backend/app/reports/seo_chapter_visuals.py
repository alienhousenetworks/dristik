"""Chapter charts for the SEO audit book.

A bar is a stored count or measurement. A missing connector is named and is
not plotted as zero. Crawl response time is not drawn as a Core Web Vital.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Sequence, Tuple

_STATUS_LABEL = {
    "ISSUE_VERIFIED": "Issue verified",
    "NO_ISSUE": "No issue in sample",
    "MEASURED": "Measured",
    "INFERRED": "Inferred",
    "DATA_UNAVAILABLE": "Data unavailable",
    "NOT_TESTED": "Not tested",
    "NOT_APPLICABLE": "Not applicable",
}
_STATUS_ORDER = (
    "ISSUE_VERIFIED",
    "NO_ISSUE",
    "MEASURED",
    "INFERRED",
    "DATA_UNAVAILABLE",
    "NOT_TESTED",
    "NOT_APPLICABLE",
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


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"


def _svg(title: str, note: str, bars: Sequence[Tuple[str, float]]) -> str:
    rows = [(str(label), float(value)) for label, value in bars if value is not None]
    if not rows:
        return ""
    width = 640
    label_w = 168
    bar_max = 390
    row_h = 26
    height = 28 + row_h * len(rows)
    peak = max(value for _, value in rows) or 1.0
    parts = [
        '<figure class="chapter-chart">',
        f"<figcaption><strong>{_esc(title)}</strong><span>{_esc(note)}</span></figcaption>",
        (
            f'<svg role="img" aria-label="{_esc(title)}" viewBox="0 0 {width} {height}" '
            'width="100%" height="auto">'
        ),
    ]
    for index, (label, value) in enumerate(rows[:14]):
        y = 8 + index * row_h
        width_px = 0.0 if value <= 0 else max(2.0, (value / peak) * bar_max)
        parts.append(
            f'<text x="0" y="{y + 13}">{_esc(label[:32])}</text>'
            f'<rect x="{label_w}" y="{y}" width="{width_px:.1f}" height="16" fill="#0f172a"></rect>'
            f'<text x="{label_w + width_px + 8:.1f}" y="{y + 13}">{_esc(_fmt(value))}</text>'
        )
    parts.append("</svg></figure>")
    return "".join(parts)


def _mix(codes: Sequence[str]) -> str:
    bars = []
    for code in _STATUS_ORDER:
        count = sum(1 for item in codes if item == code)
        if count:
            bars.append((_STATUS_LABEL[code], count))
    return _svg(
        "Sub-index evidence states",
        "How many checklist lines in this chapter landed in each evidence state. This is not a pass rate for URLs that were not fetched.",
        bars,
    )


def evidence_mix_chart(tally: Dict[str, int]) -> str:
    bars = [(_STATUS_LABEL[code], tally.get(code, 0)) for code in _STATUS_ORDER if tally.get(code, 0)]
    return _svg(
        "Evidence state of every checklist line",
        "Counts of line judgments on this run. A not-tested line is not a failure and is not a pass.",
        bars,
    )


def _source(state: str, name: str, detail: str) -> str:
    return (
        f'<li><span class="src">{_esc(state)}</span> '
        f"<strong>{_esc(name)}</strong> — {_esc(detail)}</li>"
    )


def _panel(sources: Sequence[str], charts: Sequence[str], gap: str = "") -> str:
    chart_html = "".join(charts)
    gap_html = f'<p class="chart-gap">{_esc(gap)}</p>' if gap else ""
    if not chart_html and not gap:
        gap = "No measured series is stored for this chapter. A missing series is not plotted as zero."
        gap_html = f'<p class="chart-gap">{_esc(gap)}</p>'
    return (
        '<div class="chapter-panel">'
        '<p class="sources-kicker">Data sources</p>'
        f'<ul class="source-list">{"".join(sources)}</ul>'
        f"{chart_html}{gap_html}"
        "</div>"
    )


def _pages(book: Any) -> List[Any]:
    return list(getattr(book, "pages", None) or [])


def _http_bars(book: Any) -> List[Tuple[str, float]]:
    counts: Dict[str, int] = {}
    for page in _pages(book):
        code = _get(page, "status_code", None)
        if code is None or code == "":
            continue
        key = str(code)
        counts[key] = counts.get(key, 0) + 1
    return [(f"HTTP {code}", count) for code, count in sorted(counts.items())]


def _ttfb_bars(book: Any) -> List[Tuple[str, float]]:
    rows = []
    for page in _pages(book):
        value = _num(_get(page, "ttfb_ms"))
        if value and value > 0:
            url = str(_get(page, "url", "") or "URL")
            rows.append((url.replace("https://", "").replace("http://", "")[:28], value))
    return rows[:8]


def _title_bars(book: Any) -> List[Tuple[str, float]]:
    pages = _pages(book)
    if not pages:
        return []
    missing = short = mid = long = 0
    for page in pages:
        title = str(_get(page, "title", "") or "").strip()
        length = len(title)
        if not title:
            missing += 1
        elif length < 40:
            short += 1
        elif length <= 60:
            mid += 1
        else:
            long += 1
    return [
        ("Title missing", missing),
        ("Title 1–39 characters", short),
        ("Title 40–60 characters", mid),
        ("Title over 60 characters", long),
    ]


def _meta_bars(book: Any) -> List[Tuple[str, float]]:
    pages = _pages(book)
    if not pages:
        return []
    missing = short = mid = long = 0
    for page in pages:
        meta = str(_get(page, "meta_description", "") or "").strip()
        length = len(meta)
        if not meta:
            missing += 1
        elif length < 70:
            short += 1
        elif length <= 160:
            mid += 1
        else:
            long += 1
    return [
        ("Description missing", missing),
        ("Description 1–69 characters", short),
        ("Description 70–160 characters", mid),
        ("Description over 160 characters", long),
    ]


def _h1_bars(book: Any) -> List[Tuple[str, float]]:
    none = one = many = 0
    seen = False
    for page in _pages(book):
        value = _get(page, "h1", None)
        if not isinstance(value, (list, tuple)):
            continue
        seen = True
        count = len([item for item in value if str(item).strip()])
        if count == 0:
            none += 1
        elif count == 1:
            one += 1
        else:
            many += 1
    if not seen:
        return []
    return [("No H1", none), ("One H1", one), ("More than one H1", many)]


def _word_bars(book: Any) -> List[Tuple[str, float]]:
    low = mid = high = 0
    seen = False
    for page in _pages(book):
        count = _num(_get(page, "word_count"))
        if not count or count <= 0:
            continue
        seen = True
        if count < 400:
            low += 1
        elif count < 800:
            mid += 1
        else:
            high += 1
    if not seen:
        return []
    return [("Under 400 words", low), ("400–799 words", mid), ("800 or more words", high)]


def _schema_bars(book: Any) -> List[Tuple[str, float]]:
    counts: Dict[str, int] = {}
    for page in _pages(book):
        for item in _get(page, "schema_types", None) or []:
            name = str(item).strip()
            if name:
                counts[name] = counts.get(name, 0) + 1
    return sorted(((name, count) for name, count in counts.items()), key=lambda row: (-row[1], row[0]))[:10]


def _canonical_bars(book: Any) -> List[Tuple[str, float]]:
    missing = same = other = 0
    if not _pages(book):
        return []
    for page in _pages(book):
        url = str(_get(page, "url", "") or "").rstrip("/")
        canon = str(_get(page, "canonical_url", "") or "").strip().rstrip("/")
        if not canon:
            missing += 1
        elif canon == url:
            same += 1
        else:
            other += 1
    return [("No canonical stored", missing), ("Self-referencing", same), ("Points elsewhere", other)]


def _viewport_bars(book: Any) -> List[Tuple[str, float]]:
    if not _pages(book):
        return []
    present = 0
    absent = 0
    for page in _pages(book):
        if str(_get(page, "viewport", "") or "").strip():
            present += 1
        else:
            absent += 1
    return [("Viewport tag stored", present), ("No viewport tag stored", absent)]


def _image_bars(book: Any) -> List[Tuple[str, float]]:
    total = 0
    missing = 0
    seen = False
    for page in _pages(book):
        images = _num(_get(page, "total_images"))
        without = _num(_get(page, "images_without_alt"))
        if images is None and without is None:
            continue
        seen = True
        total += int(images or 0)
        missing += int(without or 0)
    if not seen or total <= 0:
        return []
    with_alt = max(total - missing, 0)
    return [("Images with alt text", with_alt), ("Images without alt text", missing)]


def _severity_bars(book: Any) -> List[Tuple[str, float]]:
    counts: Dict[str, int] = {}
    for finding in getattr(book, "findings", None) or []:
        severity = str(_get(finding, "severity", "") or "UNSPECIFIED").upper()
        counts[severity] = counts.get(severity, 0) + 1
    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNSPECIFIED"]
    bars = [(name.title(), counts[name]) for name in order if counts.get(name)]
    for name, count in counts.items():
        if name not in order:
            bars.append((name.title(), count))
    return bars


def _score_bars(book: Any) -> List[Tuple[str, float]]:
    scores = _get(getattr(book, "report", None), "scores")
    bars: List[Tuple[str, float]] = []
    overall = _num(_get(scores, "overall_score"))
    if overall is not None:
        bars.append(("Sealed overall", overall))
    categories = _get(scores, "category_scores") or {}
    if isinstance(categories, dict):
        for key, row in categories.items():
            status = str(_get(row, "status", "") or "").upper()
            if status in {"NOT_MEASURED", "NOT_TESTED"}:
                continue
            value = _num(_get(row, "score"))
            if value is None:
                continue
            bars.append((str(key).replace("_", " ").title(), value))
    return bars


def _field_rows(book: Any) -> List[Any]:
    rows = []
    for page in _pages(book):
        field = _get(page, "field_performance")
        if _get(field, "has_field_data") is True:
            rows.append(page)
    return rows


def _lab_rows(book: Any) -> List[Any]:
    rows = []
    for page in _pages(book):
        lab = _get(page, "lab_performance")
        if str(_get(lab, "lighthouse_audit_version", "") or "").strip():
            rows.append(page)
    return rows


def _cwv_charts(book: Any) -> Tuple[List[str], str]:
    charts: List[str] = []
    field_pages = _field_rows(book)
    if field_pages:
        for key, label in (("p75_lcp_ms", "Field p75 LCP ms"), ("p75_inp_ms", "Field p75 INP ms"), ("p75_cls", "Field p75 CLS")):
            bars = []
            for page in field_pages[:8]:
                value = _num(_get(_get(page, "field_performance"), key))
                if value is None:
                    continue
                url = str(_get(page, "url", "") or "URL").replace("https://", "")[:28]
                bars.append((url, value))
            if bars:
                charts.append(_svg(label, "Field data at the 75th percentile. Thresholds used for reading are LCP 2500 ms, INP 200 ms, and CLS 0.1. One URL is not an origin score.", bars))
        return charts, ""
    lab_pages = _lab_rows(book)
    if lab_pages:
        lcp_bars = []
        cls_bars = []
        for page in lab_pages[:8]:
            lab = _get(page, "lab_performance")
            url = str(_get(page, "url", "") or "URL").replace("https://", "")[:28]
            lcp = _num(_get(lab, "lcp_ms"))
            cls = _num(_get(lab, "cls_score"))
            if lcp is not None:
                lcp_bars.append((url, lcp))
            if cls is not None:
                cls_bars.append((url, cls))
        if lcp_bars:
            charts.append(_svg("Laboratory LCP ms", "Lighthouse laboratory data. Not field Core Web Vitals and not a Google certification.", lcp_bars))
        if cls_bars:
            charts.append(_svg("Laboratory CLS", "Lighthouse laboratory data. Not field Core Web Vitals.", cls_bars))
        return charts, ""
    return [], "LCP, INP, and CLS were not measured. Crawl response time is not a Core Web Vital and is not plotted here."


def _ai_charts(book: Any) -> Tuple[List[str], str]:
    card = _get(getattr(book, "report", None), "ai_visibility_scorecard")
    runs = _num(_get(card, "successful_runs")) or 0
    if runs <= 0:
        return [], (
            "Live engine responses were not measured. Google AI Overviews, Google AI Mode, and Bing Copilot stay unqueried "
            "unless a scorecard names them. An SEO score is not a citation rate. No citation chart is drawn."
        )
    bars = []
    for key, label in (
        ("mention_rate_pct", "Mention rate %"),
        ("citation_rate_pct", "Citation rate %"),
        ("competitor_visibility_pct", "Competitor visibility %"),
    ):
        value = _num(_get(card, key))
        if value is not None:
            bars.append((label, value))
    note = "Live model-API responses only. A mention is not a recommendation. A missing rate is omitted, not drawn as zero."
    if not bars:
        return [], "Successful responses were stored, and mention, citation, and competitor rates were not. Those rates are not drawn as zero. " + note
    return [_svg("Live AI response rates", note, bars)], ""


def _gsc_chart(book: Any) -> Tuple[List[str], str]:
    state = str(getattr(book, "gsc_state", "") or "NOT_CONNECTED")
    if state != "MEASURED":
        return [], f"Search Console is {state}. Clicks and impressions are not filled with zero."
    bars = []
    search = getattr(book, "search", None) or {}
    for key, label in (("clicks", "Clicks"), ("impressions", "Impressions")):
        value = _num(search.get(key) if isinstance(search, dict) else None)
        if value is not None:
            bars.append((label, value))
    if not bars:
        return [], "Search Console is connected and did not store clicks or impressions. Nothing is plotted as zero."
    return [_svg("Search Console totals", "Stored property totals. Clicks are not conversions.", bars)], ""


def _ga4_note(book: Any) -> str:
    state = str(getattr(book, "ga4_state", "") or "NOT_CONNECTED")
    if state != "MEASURED":
        return f"Google Analytics 4 is {state}. Sessions and key events are not filled with zero. Key events are not revenue."
    analytics = getattr(book, "analytics", None) or {}
    sessions = _num(analytics.get("sessions") if isinstance(analytics, dict) else None)
    events = _num(analytics.get("key_events") if isinstance(analytics, dict) else None)
    bits = []
    if sessions is not None:
        bits.append(f"sessions { _fmt(sessions) }")
    if events is not None:
        bits.append(f"key events { _fmt(events) }")
    if sessions and sessions > 0 and events is not None:
        rate = round((events / sessions) * 1000) / 10
        bits.append(f"key-event rate {rate}%")
    if not bits:
        return "Google Analytics 4 is marked measured and did not store sessions or key events."
    return "Stored GA4 figures: " + "; ".join(bits) + ". This is not a conversion grade and not revenue."


def _crawl_source(book: Any) -> str:
    sample = str(getattr(book, "sample", "") or "No crawl sample was stored.")
    state = "Measured" if _pages(book) else "Not tested"
    return _source(state, "Crawl sample", sample)


def _connector_source(book: Any, number: str) -> List[str]:
    rows = [_crawl_source(book)]
    if number in {"01", "02", "04", "06", "22", "34", "48", "J"}:
        state = str(getattr(book, "gsc_state", "") or "NOT_CONNECTED")
        rows.append(_source("Measured" if state == "MEASURED" else "Data unavailable", "Google Search Console", state))
    if number in {"49", "50", "51"}:
        state = str(getattr(book, "ga4_state", "") or "NOT_CONNECTED")
        rows.append(_source("Measured" if state == "MEASURED" else "Data unavailable", "Google Analytics 4", state + ". Key events are not revenue."))
    if number in {"16", "I"}:
        if _field_rows(book):
            rows.append(_source("Measured", "Field Core Web Vitals", "CrUX-style field records with has_field_data."))
        elif _lab_rows(book):
            rows.append(_source("Measured", "Laboratory Lighthouse", "Lab records with a Lighthouse version. Not field data."))
        else:
            rows.append(_source("Not tested", "Core Web Vitals", "No field record and no versioned Lighthouse run."))
        rows.append(_source("Not applicable", "Crawl TTFB as LCP", "Response time is kept in the HTTP chapter and is not a Core Web Vital."))
    if number in {"45", "46", "47", "K"}:
        card = _get(getattr(book, "report", None), "ai_visibility_scorecard")
        runs = _num(_get(card, "successful_runs")) or 0
        if runs > 0:
            rows.append(_source("Measured", "Live model APIs", f"{int(runs)} successful response(s). Not consumer AI Overviews unless named."))
        else:
            rows.append(_source("Not tested", "Live AI answers", "No successful engine response on this run."))
    if number in {"31", "G"}:
        rows.append(_source("Data unavailable", "Backlink provider", "A missing provider is not a zero and not a toxicity score."))
    if number == "52":
        rows.append(_source("Not produced", "Forecast model", "No traffic, ranking, or revenue forecast is produced."))
    if number == "43":
        rows.append(_source("Not tested", "Accessibility screen", "Shown only when an automated screen stored a check count. Not a WCAG certificate."))
    return rows


def _topic_charts(book: Any, number: str) -> Tuple[List[str], str]:
    charts: List[str] = []
    gap = ""
    if number in {"07", "08", "11", "14", "C"}:
        http = _http_bars(book)
        if http:
            charts.append(_svg("HTTP status in the crawled sample", "Status codes stored on fetched URLs. A code that did not occur is omitted.", http))
        elif _pages(book):
            gap = "Pages were crawled and no HTTP status code was stored. Status is not assumed to be 200."
    if number == "14":
        timing = _ttfb_bars(book)
        if timing:
            charts.append(_svg("Crawl response time (ms)", "Time to first byte on the crawl response. Not Lighthouse and not a Core Web Vital.", timing))
        elif not gap:
            gap = "No positive crawl response time was stored. A missing timing is not a pass and is not a Core Web Vital."
    if number == "10":
        bars = _canonical_bars(book)
        if bars:
            charts.append(_svg("Canonical signals in the sample", "Counted from stored canonical URLs. Chains and cross-domain targets were not walked unless a canonical audit stored them.", bars))
    if number == "17":
        bars = _viewport_bars(book)
        if bars:
            charts.append(_svg("Viewport tags in the sample", "Presence of a viewport tag. Tap targets, interstitials, and mobile-desktop parity were not tested.", bars))
    if number in {"19", "H"}:
        bars = _schema_bars(book)
        if bars:
            charts.append(_svg("Schema types on crawled pages", "Types found in stored structured data. Valid markup is not a promise of a rich result.", bars))
        elif _pages(book) and not gap:
            gap = "No schema type was stored on the crawled pages. That absence is not a rich-result eligibility score."
    if number == "20":
        titles = _title_bars(book)
        metas = _meta_bars(book)
        if titles:
            charts.append(_svg("Title length in the sample", "Character counts of stored titles. A long title is a truncation risk, not a measured click-through rate.", titles))
        if metas:
            charts.append(_svg("Meta description length in the sample", "Character counts of stored meta descriptions. Search engines may rewrite the snippet.", metas))
    if number == "21":
        bars = _h1_bars(book)
        if bars:
            charts.append(_svg("H1 counts in the sample", "Heading counts from stored HTML. This is not a content-quality grade.", bars))
    if number in {"23", "D"}:
        bars = _word_bars(book)
        if bars:
            charts.append(_svg("Extracted word counts", "Word count is not by itself a quality grade. Pages with no stored count are omitted, not treated as thin.", bars))
        elif _pages(book) and not gap:
            gap = "Word counts were not stored. A missing count is not plotted as thin content."
    if number == "28":
        bars = _image_bars(book)
        if bars:
            charts.append(_svg("Image alt text in the sample", "Counts from stored image totals. Decorative handling was not separately judged.", bars))
    if number in {"01", "04", "53", "L"}:
        bars = _severity_bars(book)
        if bars:
            charts.append(_svg("Recorded findings by severity", "Findings stored on this run. Severity is not a traffic or revenue estimate.", bars))
    if number in {"02", "B"}:
        bars = _score_bars(book)
        if bars:
            charts.append(_svg("Sealed scores that were stored", "Overall and category scores present on the report. Not-measured categories are omitted. This is not a grade of every chapter, and model-default confidence is not plotted.", bars))
        elif not gap:
            gap = "No sealed overall or category score was stored. A missing score is not drawn as zero."
    if number in {"16", "I"}:
        cwv, cwv_gap = _cwv_charts(book)
        charts.extend(cwv)
        gap = gap or cwv_gap
    if number in {"45", "46", "47", "K"}:
        ai, ai_gap = _ai_charts(book)
        charts.extend(ai)
        gap = gap or ai_gap
    if number in {"34", "48", "J"}:
        gsc, gsc_gap = _gsc_chart(book)
        charts.extend(gsc)
        gap = gap or gsc_gap
    if number in {"49", "50", "51"}:
        gap = gap or _ga4_note(book)
    if number == "52":
        gap = "No forecast chart is drawn. No traffic, ranking, or revenue forecast is produced. An assumed lift is not a measurement."
    if number in {"05", "33", "F"}:
        bakeoff = _get(getattr(book, "report", None), "competitor_bakeoff")
        if bakeoff is not None and _get(bakeoff, "competitor_domain"):
            bars = []
            for key, label in (("target_wins", "Target wins"), ("competitor_wins", "Competitor wins"), ("ties", "Ties")):
                value = _num(_get(bakeoff, key))
                if value is not None:
                    bars.append((label, value))
            if bars:
                charts.append(_svg(f"Stored comparison with {_get(bakeoff, 'competitor_domain')}", "The stored bake-off only. Not a keyword-gap index.", bars))
        elif not gap:
            gap = "No competitor comparison was stored. An uncrawled rival is not given a score."
    if number in {"31", "G"} and not gap:
        gap = "No backlink series is plotted. A missing provider is not a zero, not a toxicity score, and not an SEO failure."
    return charts, gap


def _url_table(book: Any) -> str:
    pages = _pages(book)[:12]
    if not pages:
        return ""
    body = []
    for index, page in enumerate(pages, 1):
        title = str(_get(page, "title", "") or "")
        timing = _num(_get(page, "ttfb_ms"))
        shown = f"{_fmt(timing)} ms" if timing and timing > 0 else "not stored"
        code = _get(page, "status_code", None)
        code_shown = "not stored" if code is None or code == "" else str(code)
        body.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td><code>{_esc(_get(page, 'url', ''))}</code></td>"
            f"<td>{_esc(code_shown)}</td>"
            f"<td>{_esc(shown)}</td>"
            f"<td>{_esc(len(title) if title else 'missing')}</td>"
            "</tr>"
        )
    return (
        '<div class="data-table-wrap"><table><thead><tr>'
        "<th>#</th><th>URL</th><th>HTTP</th><th>Crawl response</th><th>Title characters</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
        '<p class="chart-gap">Crawl response time is not a Core Web Vital. The table lists the crawled sample only.</p>'
    )


def chapter_panel(book: Any, number: str, line_statuses: Sequence[str]) -> str:
    """Data-source strip, evidence-state chart, and any stored series for one chapter."""
    sources = _connector_source(book, number)
    charts, gap = _topic_charts(book, number)
    mix = _mix(line_statuses)
    if mix:
        charts = [mix, *charts]
    extra = _url_table(book) if number == "C" else ""
    return _panel(sources, charts, gap) + extra
