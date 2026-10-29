"""Bounded public grader.

The grader fetches the homepage, robots.txt, sitemap.xml, and llms.txt.
It reports what those responses contained. It does not invent a GEO score,
AI citations, domain age, or monthly visits. Live AI visibility is a separate
measurement and is listed under checks that were not run.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.core.security.ssrf import is_safe_url
from app.connectors.authority.traffic_estimator import DomainTrafficSummary, estimate_domain_traffic


_HOST = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_MAX_BYTES = 1_500_000
_TIMEOUT = 4.0
_USER_AGENT = "Mozilla/5.0 (compatible; DristikGrader/3.0; +https://dristik.ai/grader)"
_CHECKS_NOT_RUN = [
    "Live AI visibility across answer engines",
    "Multi-page crawl beyond the homepage and three root files",
    "Core Web Vitals and Chrome UX Report",
    "Search Console and GA4",
    "Backlinks and referring domains",
    "WHOIS domain age",
    "Full audit findings, patches, and verification",
]


class PublicFindingPreview(BaseModel):
    evidence_id: str
    title: str
    category: str
    severity: str
    description: str
    suggested_fix: str
    source_url: str
    confidence: str = "observed"


class InspectedPage(BaseModel):
    url: str
    http_status: Optional[int] = None
    bytes_read: int = 0
    error: Optional[str] = None


class MetricProvenance(BaseModel):
    metric: str
    value: Any = None
    source: str
    observed_at: str
    scope: str
    method: str = "public_grader.v3"
    confidence: str


class PublicGradeResult(BaseModel):
    domain: str
    canonical_url: Optional[str] = None
    analyzed_at: str
    assessment_kind: str = "preliminary_technical_readiness"
    coverage_note: str = (
        "This is a bounded preliminary assessment of the homepage and three root files. "
        "It is not a complete GEO score and it is not a live AI visibility measurement."
    )
    execution_budget_seconds: float = _TIMEOUT
    geo_score: Optional[int] = None
    score_kind: str = "preliminary_readiness_not_live_geo"
    grade: Optional[str] = None
    grade_label: str = "Not measured"
    next_grade_target: Optional[str] = None
    ai_crawler_access_score: Optional[int] = None
    machine_readability_score: Optional[int] = None
    structured_data_score: Optional[int] = None
    content_citability_score: Optional[int] = None
    trust_eeat_score: Optional[int] = None
    title_text: Optional[str] = None
    title_length: Optional[int] = None
    title_status: Optional[str] = None
    description_text: Optional[str] = None
    description_length: Optional[int] = None
    description_status: Optional[str] = None
    domain_creation_date: Optional[str] = None
    domain_expiration_date: Optional[str] = None
    domain_age_years: Optional[float] = None
    has_favicon: Optional[bool] = None
    has_ssr: Optional[bool] = None
    html_contained_text: Optional[bool] = None
    google_analytics_detected: Optional[bool] = None
    google_adsense_detected: Optional[bool] = None
    has_robots_txt: Optional[bool] = None
    has_sitemap_xml: Optional[bool] = None
    has_llms_txt: Optional[bool] = None
    word_count: Optional[int] = None
    lang: Optional[str] = None
    h1_count: Optional[int] = None
    heading_jumps_count: Optional[int] = None
    total_images: Optional[int] = None
    images_without_alt: Optional[int] = None
    images_without_title: Optional[int] = None
    total_links: Optional[int] = None
    internal_links: Optional[int] = None
    external_links: Optional[int] = None
    dofollow_links: Optional[int] = None
    nofollow_links: Optional[int] = None
    ai_citations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    traffic_summary: DomainTrafficSummary
    top_findings: list[PublicFindingPreview] = Field(default_factory=list)
    locked_findings_count: int = 0
    pages_inspected: list[InspectedPage] = Field(default_factory=list)
    checks_run: list[str] = Field(default_factory=list)
    checks_not_run: list[str] = Field(default_factory=lambda: list(_CHECKS_NOT_RUN))
    provenance: list[MetricProvenance] = Field(default_factory=list)
    fetch_error: Optional[str] = None
    share_path: Optional[str] = None
    full_audit_path: str = "/#/"
    conversion_note: str = "Get the evidence for what to fix next, then use Dristik to manage and verify the work."


class _Fetch:
    url: str
    status: Optional[int]
    text: str
    error: Optional[str]
    truncated: bool

    def __init__(self, url: str, status: Optional[int] = None, text: str = "", error: Optional[str] = None, truncated: bool = False):
        self.url = url
        self.status = status
        self.text = text
        self.error = error
        self.truncated = truncated


def normalize_public_domain(raw_domain: str) -> str:
    clean = re.sub(r"^https?://", "", raw_domain.strip().lower())
    clean = clean.split("/")[0].split("?")[0].split("#")[0]
    if "@" in clean or not clean:
        raise ValueError("Enter a public domain, without a username or password.")
    host = clean.split(":")[0]
    if not _HOST.match(host):
        try:
            host = host.encode("idna").decode("ascii")
        except Exception as exc:
            raise ValueError("Enter a public domain such as example.com.") from exc
        if not _HOST.match(host):
            raise ValueError("Enter a public domain such as example.com.")
    return host


def _grade_letter(score: Optional[int]) -> tuple[Optional[str], str, Optional[str]]:
    if score is None:
        return None, "Not measured", None
    if score >= 90:
        letter, label, nxt = "A", "Strong preliminary readiness", None
    elif score >= 75:
        letter, label, nxt = "B", "Preliminary readiness", "A is 90 or above on this bounded check set"
    elif score >= 50:
        letter, label, nxt = "C", "Partial preliminary readiness", "B is 75 or above on this bounded check set"
    else:
        letter, label, nxt = "D", "Weak preliminary readiness", "C is 50 or above on this bounded check set"
    return letter, label, nxt


def _ratio(passed: int, total: int) -> Optional[int]:
    if total <= 0:
        return None
    return round(100 * passed / total)


async def _fetch(client: httpx.AsyncClient, url: str) -> _Fetch:
    current = url
    for _hop in range(4):
        safe, reason = is_safe_url(current)
        if not safe:
            return _Fetch(url=current, error=reason)
        try:
            async with client.stream("GET", current, follow_redirects=False, headers={"User-Agent": _USER_AGENT}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return _Fetch(url=str(response.url), status=response.status_code, error="Redirect without a location")
                    current = urljoin(str(response.url), location)
                    continue
                chunks: list[bytes] = []
                total = 0
                truncated = False
                async for chunk in response.aiter_bytes():
                    if total >= _MAX_BYTES:
                        truncated = True
                        break
                    room = _MAX_BYTES - total
                    chunks.append(chunk[:room])
                    total += len(chunks[-1])
                    if len(chunk) > room:
                        truncated = True
                        break
                text = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                return _Fetch(url=str(response.url), status=response.status_code, text=text, truncated=truncated)
        except Exception as exc:
            return _Fetch(url=current, error=type(exc).__name__)
    return _Fetch(url=current, error="Too many redirects")


def _robots_disallows_all(text: str) -> bool:
    agent_star = False
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            agent_star = value == "*"
        elif key == "disallow" and agent_star and value == "/":
            return True
    return False


def _not_measured_citations(observed_at: str) -> dict[str, dict[str, Any]]:
    limitation = "The public grader does not query AI engines. A missing measurement is not a citation count of zero."
    return {
        engine: {
            "citations": None,
            "cited_pages": None,
            "status": "not_measured",
            "growth": None,
            "observed_at": observed_at,
            "limitation": limitation,
        }
        for engine in ("google_ai_overview", "chatgpt", "perplexity", "gemini", "copilot")
    }


async def run_public_grade(raw_domain: str, client: Optional[httpx.AsyncClient] = None) -> PublicGradeResult:
    domain = normalize_public_domain(raw_domain)
    observed_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    homepage = f"https://{domain}/"
    safe, reason = is_safe_url(homepage)
    if not safe:
        raise ValueError(reason)

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        home = await _fetch(client, homepage)
        robots = await _fetch(client, f"https://{domain}/robots.txt")
        sitemap = await _fetch(client, f"https://{domain}/sitemap.xml")
        llms = await _fetch(client, f"https://{domain}/llms.txt")
    finally:
        if owns_client:
            await client.aclose()

    pages = [
        InspectedPage(url=item.url, http_status=item.status, bytes_read=len(item.text.encode("utf-8", errors="replace")), error=item.error)
        for item in (home, robots, sitemap, llms)
    ]
    findings: list[PublicFindingPreview] = []
    checks_run: list[str] = []
    provenance: list[MetricProvenance] = []

    def add_finding(evidence_id: str, title: str, category: str, severity: str, description: str, fix: str, source_url: str) -> None:
        findings.append(PublicFindingPreview(
            evidence_id=evidence_id,
            title=title,
            category=category,
            severity=severity,
            description=description,
            suggested_fix=fix,
            source_url=source_url,
        ))

    def provenance_for(metric: str, value: Any, source: str, confidence: str = "observed") -> None:
        provenance.append(MetricProvenance(
            metric=metric,
            value=value,
            source=source,
            observed_at=observed_at,
            scope="homepage" if source == home.url else "root_file",
            confidence=confidence,
        ))

    title_text = None
    title_length = None
    title_status = None
    desc_text = None
    desc_length = None
    desc_status = None
    canonical_url = None
    has_favicon = None
    html_contained_text = None
    ga_detected = None
    adsense_detected = None
    word_count = None
    lang = None
    h1_count = None
    heading_jumps = None
    total_imgs = None
    missing_alt = None
    missing_title = None
    total_links = None
    internal_links = None
    external_links = None
    dofollow_links = None
    nofollow_links = None
    readability_parts: list[bool] = []
    structure_parts: list[bool] = []
    content_parts: list[bool] = []
    trust_parts: list[bool] = []

    if home.error or home.status is None:
        add_finding(
            "ev_home_unreachable",
            "Homepage could not be fetched",
            "Fetch",
            "HIGH",
            home.error or "The homepage request did not return a response.",
            "Confirm the domain resolves to a public HTTPS site and run the grader again.",
            homepage,
        )
    else:
        checks_run.append("homepage_http")
        provenance_for("http_status", home.status, home.url)
        if home.status != 200:
            add_finding(
                "ev_home_status",
                f"Homepage returned HTTP {home.status}",
                "Fetch",
                "HIGH",
                f"GET {home.url} returned {home.status}.",
                "Serve the public homepage with HTTP 200 over HTTPS.",
                home.url,
            )
        soup = BeautifulSoup(home.text or "", "html.parser")
        if soup.title and soup.title.string:
            title_text = soup.title.string.strip()
        title_length = len(title_text or "")
        if title_text:
            title_status = "optimal" if 45 <= title_length <= 65 else ("short" if title_length < 45 else "long")
        else:
            title_status = "missing"
            add_finding(
                "ev_title_missing",
                "Homepage title is missing",
                "Machine readability",
                "HIGH",
                "The fetched HTML has no title text.",
                "Add a unique title that names the page.",
                home.url,
            )
        checks_run.append("title")
        provenance_for("title", title_text, home.url)
        readability_parts.append(bool(title_text) and title_status == "optimal")

        meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_desc and meta_desc.get("content"):
            desc_text = str(meta_desc.get("content")).strip()
        desc_length = len(desc_text or "")
        if desc_text:
            desc_status = "optimal" if 130 <= desc_length <= 165 else ("short" if desc_length < 130 else "long")
        else:
            desc_status = "missing"
            add_finding(
                "ev_description_missing",
                "Meta description is missing",
                "Machine readability",
                "MEDIUM",
                "The fetched homepage has no meta description.",
                "Add a meta description written from the page's actual offer.",
                home.url,
            )
        checks_run.append("meta_description")
        provenance_for("meta_description", desc_text, home.url)
        readability_parts.append(bool(desc_text))

        canonical = soup.find("link", rel=lambda value: value and "canonical" in str(value).lower())
        if canonical and canonical.get("href"):
            canonical_url = str(canonical.get("href"))
        else:
            add_finding(
                "ev_canonical_missing",
                "Canonical link is missing",
                "Machine readability",
                "MEDIUM",
                "The fetched homepage has no rel=canonical link.",
                "Add a canonical link to the preferred homepage URL.",
                home.url,
            )
        checks_run.append("canonical")
        provenance_for("canonical", canonical_url, home.url)
        readability_parts.append(bool(canonical_url))

        robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        robots_content = str(robots_meta.get("content") or "").lower() if robots_meta else ""
        if "noindex" in robots_content:
            add_finding(
                "ev_noindex",
                "Homepage meta robots contains noindex",
                "Crawler access",
                "HIGH",
                f"The robots meta content is '{robots_content}'.",
                "Remove noindex from the public homepage if it should be indexed.",
                home.url,
            )
        checks_run.append("meta_robots")

        has_favicon = bool(soup.find("link", rel=re.compile(r"icon", re.I)))
        text_content = soup.get_text(separator=" ", strip=True)
        words = [word for word in text_content.split() if len(word) > 1]
        word_count = len(words)
        html_contained_text = word_count > 0
        lang = None
        if soup.html and soup.html.get("lang"):
            lang = str(soup.html.get("lang"))[:12]
        h1_nodes = soup.find_all("h1")
        h1_count = len(h1_nodes)
        if h1_count == 0:
            add_finding(
                "ev_h1_missing",
                "Homepage has no H1",
                "Content readiness",
                "MEDIUM",
                "The fetched HTML contains zero h1 elements.",
                "Add one H1 that states the page topic.",
                home.url,
            )
        elif h1_count > 1:
            add_finding(
                "ev_h1_multiple",
                f"Homepage has {h1_count} H1 elements",
                "Content readiness",
                "LOW",
                "More than one h1 was present in the fetched HTML.",
                "Keep a single H1 on the homepage.",
                home.url,
            )
        levels = [int(tag.name[1]) for tag in soup.find_all(re.compile(r"^h[1-6]$"))]
        jumps = 0
        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                jumps += 1
        heading_jumps = jumps
        checks_run.extend(["h1", "heading_order", "visible_text"])
        provenance_for("h1_count", h1_count, home.url)
        provenance_for("word_count", word_count, home.url)
        content_parts.append(h1_count == 1)
        content_parts.append(word_count >= 200)

        images = soup.find_all("img")
        total_imgs = len(images)
        missing_alt = len([img for img in images if not str(img.get("alt") or "").strip()])
        missing_title = len([img for img in images if not str(img.get("title") or "").strip()])
        if missing_alt:
            add_finding(
                "ev_img_alt",
                f"{missing_alt} homepage images have no alt text",
                "Content readiness",
                "MEDIUM" if missing_alt >= 3 else "LOW",
                f"{missing_alt} of {total_imgs} img elements in the fetched HTML have an empty alt attribute.",
                "Add alt text for informative images. Leave alt empty only for decorative images.",
                home.url,
            )
        checks_run.append("image_alt")
        provenance_for("images_without_alt", missing_alt, home.url)

        links = soup.find_all("a", href=True)
        total_links = len(links)
        internal_links = 0
        external_links = 0
        nofollow_links = 0
        for link in links:
            href = str(link.get("href"))
            rel = " ".join(link.get("rel") or []).lower() if isinstance(link.get("rel"), list) else str(link.get("rel") or "").lower()
            if "nofollow" in rel:
                nofollow_links += 1
            if href.startswith("/") or domain in href:
                internal_links += 1
            elif href.startswith("http"):
                external_links += 1
        dofollow_links = total_links - nofollow_links
        checks_run.append("links")

        schemas = []
        for script in soup.find_all("script"):
            script_type = str(script.get("type") or "").lower()
            if "ld+json" not in script_type:
                continue
            raw_json = script.string or script.get_text() or ""
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                add_finding(
                    "ev_jsonld_invalid",
                    "A JSON-LD block could not be parsed",
                    "Structured data",
                    "MEDIUM",
                    "The homepage contains a script of type application/ld+json that is not valid JSON.",
                    "Correct the JSON-LD so it parses.",
                    home.url,
                )
                continue
            blocks = parsed if isinstance(parsed, list) else [parsed]
            for block in blocks:
                if isinstance(block, dict) and block.get("@type"):
                    kind = block.get("@type")
                    schemas.extend(kind if isinstance(kind, list) else [str(kind)])
        if not schemas:
            add_finding(
                "ev_jsonld_missing",
                "No JSON-LD types were found on the homepage",
                "Structured data",
                "MEDIUM",
                "The fetched homepage has no parseable JSON-LD @type.",
                "Add JSON-LD that matches the visible organization or page type.",
                home.url,
            )
        checks_run.append("json_ld")
        provenance_for("json_ld_types", schemas, home.url)
        structure_parts.append(bool(schemas))

        html_lower = home.text.lower()
        ga_detected = any(token in html_lower for token in ("googletagmanager", "gtag(", "analytics.js", "google-analytics.com"))
        adsense_detected = "adsbygoogle" in html_lower
        trust_parts.append(home.url.startswith("https://"))
        trust_parts.append("noindex" not in robots_content)
        checks_run.append("analytics_marker")

    has_robots = None
    has_sitemap = None
    has_llms = None
    crawler_parts: list[bool] = []
    if robots.error is None and robots.status is not None:
        checks_run.append("robots_txt")
        has_robots = robots.status == 200 and len(robots.text.strip()) > 0
        provenance_for("robots_txt", has_robots, robots.url)
        if not has_robots:
            add_finding(
                "ev_robots_missing",
                "robots.txt was not found",
                "Crawler access",
                "MEDIUM",
                f"GET {robots.url} returned HTTP {robots.status}.",
                "Publish a robots.txt that allows the public pages you want crawled.",
                robots.url,
            )
        elif _robots_disallows_all(robots.text):
            add_finding(
                "ev_robots_disallow",
                "robots.txt disallows the whole site",
                "Crawler access",
                "HIGH",
                "The fetched robots.txt contains User-agent: * and Disallow: /.",
                "Remove the sitewide disallow if the public site should be crawled.",
                robots.url,
            )
            crawler_parts.append(False)
        else:
            crawler_parts.append(True)
        if has_robots and "sitemap:" not in robots.text.lower() and (sitemap.status != 200):
            add_finding(
                "ev_sitemap_missing",
                "No sitemap was found at /sitemap.xml or in robots.txt",
                "Crawler access",
                "MEDIUM",
                "robots.txt does not declare a Sitemap, and GET /sitemap.xml did not return 200.",
                "Publish a sitemap and declare it in robots.txt.",
                robots.url,
            )
    if sitemap.error is None and sitemap.status is not None:
        checks_run.append("sitemap_xml")
        has_sitemap = sitemap.status == 200 and ("<urlset" in sitemap.text.lower() or "<sitemapindex" in sitemap.text.lower())
        provenance_for("sitemap_xml", has_sitemap, sitemap.url)
        crawler_parts.append(bool(has_sitemap))
        if not has_sitemap and not any(item.evidence_id == "ev_sitemap_missing" for item in findings):
            add_finding(
                "ev_sitemap_missing",
                "sitemap.xml did not return a sitemap document",
                "Crawler access",
                "MEDIUM",
                f"GET {sitemap.url} returned HTTP {sitemap.status}.",
                "Publish an XML sitemap at /sitemap.xml or declare another sitemap in robots.txt.",
                sitemap.url,
            )
    if llms.error is None and llms.status is not None:
        checks_run.append("llms_txt")
        has_llms = llms.status == 200 and len(llms.text.strip()) > 0
        provenance_for("llms_txt", has_llms, llms.url)

    severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    findings.sort(key=lambda item: severity_order.get(item.severity, 0), reverse=True)
    shown = findings[:3]
    hidden = max(0, len(findings) - len(shown))

    component_scores = {
        "ai_crawler_access_score": _ratio(sum(1 for item in crawler_parts if item), len(crawler_parts)),
        "machine_readability_score": _ratio(sum(1 for item in readability_parts if item), len(readability_parts)),
        "structured_data_score": _ratio(sum(1 for item in structure_parts if item), len(structure_parts)),
        "content_citability_score": _ratio(sum(1 for item in content_parts if item), len(content_parts)),
        "trust_eeat_score": _ratio(sum(1 for item in trust_parts if item), len(trust_parts)),
    }
    measured_components = [score for score in component_scores.values() if score is not None]
    readiness = round(sum(measured_components) / len(measured_components)) if measured_components else None
    letter, label, nxt = _grade_letter(readiness)
    for metric, value in component_scores.items():
        if value is not None:
            provenance_for(metric, value, home.url if home.status else homepage, "observed")
    if readiness is not None:
        provenance_for("preliminary_readiness", readiness, homepage, "observed")

    fetch_error = home.error if home.error else None
    coverage_note = PublicGradeResult.model_fields["coverage_note"].default
    if any(item.truncated for item in (home, robots, sitemap, llms)):
        coverage_note = f"{coverage_note} A response larger than {_MAX_BYTES} bytes was truncated before parsing."
    return PublicGradeResult(
        domain=domain,
        canonical_url=canonical_url,
        analyzed_at=observed_at,
        geo_score=readiness,
        grade=letter,
        grade_label=label,
        next_grade_target=nxt,
        title_text=title_text,
        title_length=title_length,
        title_status=title_status,
        description_text=desc_text,
        description_length=desc_length,
        description_status=desc_status,
        has_favicon=has_favicon,
        has_ssr=None,
        html_contained_text=html_contained_text,
        google_analytics_detected=ga_detected,
        google_adsense_detected=adsense_detected,
        has_robots_txt=has_robots,
        has_sitemap_xml=has_sitemap,
        has_llms_txt=has_llms,
        word_count=word_count,
        lang=lang,
        h1_count=h1_count,
        heading_jumps_count=heading_jumps,
        total_images=total_imgs,
        images_without_alt=missing_alt,
        images_without_title=missing_title,
        total_links=total_links,
        internal_links=internal_links,
        external_links=external_links,
        dofollow_links=dofollow_links,
        nofollow_links=nofollow_links,
        ai_citations=_not_measured_citations(observed_at),
        traffic_summary=estimate_domain_traffic(domain),
        top_findings=shown,
        locked_findings_count=hidden,
        pages_inspected=pages,
        checks_run=checks_run,
        provenance=provenance,
        fetch_error=fetch_error,
        coverage_note=coverage_note,
        share_path=f"/api/v1/public/grade/{domain}",
        **component_scores,
    )
