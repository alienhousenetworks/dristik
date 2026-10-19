"""Build an enterprise SEO assessment from a sealed report.

Deterministic checks reuse the current SEO analyzers. Missing connectors stay
unavailable. This module does not calculate a new score. AI specialists load a
versioned prompt and publish a judgment only when a runner returns one that
cites the supplied packet. The default runner does not call a model.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app.seo.enterprise.agents import AGENT_BY_ID, AGENT_CATALOG, execution_order
from app.seo.enterprise.cards import build_finding_card
from app.seo.enterprise.contracts import (
    ChapterCoverage,
    CoverageStatement,
    EnterpriseFinding,
    EnterpriseSeoAssessment,
    EvidenceRecord,
    IntegrationStatus,
    RejectedFinding,
    RoadmapItem,
    SEOAgentResult,
    ScoreDisclosure,
    SubchapterCoverage,
)
from app.seo.enterprise.rules import RULE_BY_ID, evaluate_condition
from app.seo.enterprise.taxonomy import CHAPTERS

_SESSION_KEYS = {"session", "sid", "phpsessid", "jsessionid", "aspsessionid"}
_SEVERITY_WINDOW = {
    "critical": "24h",
    "high": "7d",
    "medium": "30d",
    "low": "60d",
    "info": "90d",
}
_STATUS_RANK = {
    "ISSUE_VERIFIED": 6,
    "INFERRED": 5,
    "MEASURED": 4,
    "NO_ISSUE": 3,
    "DATA_UNAVAILABLE": 2,
    "NOT_APPLICABLE": 1,
    "NOT_TESTED": 0,
}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def _url_of(item: Any) -> str | None:
    if isinstance(item, str) and item.startswith(("http://", "https://")):
        return item
    for key in ("url", "page_url", "source_url", "origin_url"):
        value = _get(item, key)
        if isinstance(value, str) and value:
            return value
    return None


def _urls(items: Any) -> list[str]:
    found: list[str] = []
    for item in _as_list(items):
        url = _url_of(item)
        if url and url not in found:
            found.append(url)
    return found


def _domain_of(report: Any) -> str:
    raw = str(_get(report, "domain") or _get(report, "website_url") or "").strip()
    raw = raw.replace("https://", "").replace("http://", "").split("/")[0]
    return raw or "unknown"


def _parse_robots(text: str) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    errors: list[str] = []
    known = {"user-agent", "allow", "disallow", "sitemap", "crawl-delay"}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"Line {number} has no directive")
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key not in known:
            errors.append(f"Line {number} uses an unrecognized directive")
            continue
        if key == "user-agent":
            current = {"agents": [value.lower()], "rules": []}
            groups.append(current)
            continue
        if key == "sitemap":
            continue
        if current is None:
            errors.append(f"Line {number} appears before a user-agent")
            continue
        if key in {"allow", "disallow"}:
            current["rules"].append((key, value))
    disallow_all = False
    conflict = False
    for group in groups:
        agents = {agent for agent in group["agents"]}
        if agents.isdisjoint({"*", "googlebot"}):
            continue
        seen: dict[str, str] = {}
        for kind, path in group["rules"]:
            if path in seen and seen[path] != kind:
                conflict = True
            seen[path] = kind
        if seen.get("/") == "disallow":
            disallow_all = True
    return {"errors": errors, "disallow_all": disallow_all, "conflict": conflict}


def _detect_stack(pages: list[Any]) -> str | None:
    chunks: list[str] = []
    for page in pages[:8]:
        chunks.append(str(_get(page, "raw_html") or "")[:8000].lower())
        headers = _get(page, "response_headers") or {}
        if isinstance(headers, dict):
            chunks.append(" ".join(f"{key}:{value}" for key, value in headers.items()).lower())
    text = "\n".join(chunks)
    if "wp-content" in text or "wp-includes" in text:
        return "wordpress"
    if "cdn.shopify.com" in text or "shopify.theme" in text:
        return "shopify"
    if "__next_data__" in text or "/_next/static" in text:
        return "nextjs"
    if "csrfmiddlewaretoken" in text:
        return "django"
    return None


def _coerce_pages(raw: Any) -> list[Any]:
    pages = []
    for item in _as_list(raw):
        if isinstance(item, dict):
            if not item.get("url"):
                continue
            try:
                from app.domain.models import PageEvidence

                pages.append(PageEvidence.model_validate(item))
            except Exception:
                pages.append(item)
            continue
        if _get(item, "url"):
            pages.append(item)
    return pages


@dataclass
class _Bundle:
    meta: Any = None
    headings: Any = None
    http: Any = None
    canonical: Any = None
    indexation: Any = None
    media: Any = None
    schema: Any = None
    international: Any = None
    security: Any = None
    redirects: Any = None
    click: Any = None
    orphans: Any = None
    anchors: Any = None
    render_urls: list[str] = field(default_factory=list)
    render_checked: int = 0
    notes: list[str] = field(default_factory=list)


def _hydrate(report: Any, pages: list[Any], sitemap_urls: list[str]) -> _Bundle:
    bundle = _Bundle(
        meta=_get(report, "meta_rollup"),
        headings=_get(report, "heading_hierarchy"),
        http=_get(report, "http_status_breakdown"),
        canonical=_get(report, "canonical_audit"),
        indexation=_get(report, "indexation_intelligence") or _get(_get(report, "crawl_manifest"), "indexation_rollup"),
        media=_get(report, "media_assets"),
        schema=_get(report, "schema_validation"),
        international=_get(report, "international_seo"),
        security=_get(report, "security_audit"),
        redirects=_get(report, "host_and_redirects"),
        click=_get(report, "click_depth"),
        orphans=_get(report, "orphan_pages"),
        anchors=_get(report, "anchor_text_audit"),
    )
    if not pages:
        return bundle
    try:
        if bundle.meta is None:
            from app.seo.analyzers.meta_rollup import analyze_meta_rollup

            bundle.meta = analyze_meta_rollup(pages)
        if bundle.headings is None:
            from app.seo.analyzers.heading_analyzer import analyze_heading_hierarchy

            bundle.headings = analyze_heading_hierarchy(pages)
        if bundle.http is None:
            from app.seo.analyzers.http_status_auditor import analyze_http_statuses

            bundle.http, _unused = analyze_http_statuses(pages)
        if bundle.canonical is None:
            from app.seo.analyzers.canonical_auditor import analyze_canonicals

            bundle.canonical, _unused = analyze_canonicals(pages)
        if bundle.media is None:
            from app.seo.analyzers.media_asset_analyzer import analyze_media_assets

            bundle.media = analyze_media_assets(pages)
        if bundle.schema is None:
            from app.seo.analyzers.schema_validator import analyze_schema_rich_results

            bundle.schema = analyze_schema_rich_results(pages)
        if bundle.international is None:
            from app.seo.analyzers.international_seo_analyzer import analyze_international_seo

            bundle.international, _unused = analyze_international_seo(pages)
        if bundle.click is None or bundle.orphans is None or bundle.anchors is None:
            from app.seo.analyzers.link_depth import analyze_link_depth_and_orphans

            click, orphans, anchors = analyze_link_depth_and_orphans(pages, sitemap_urls or None)
            bundle.click = bundle.click or click
            bundle.orphans = bundle.orphans or orphans
            bundle.anchors = bundle.anchors or anchors
    except Exception as exc:
        bundle.notes.append(f"An existing SEO analyzer could not be reused ({type(exc).__name__}).")

    from app.seo.analyzers.rendering_disparity import analyze_rendering_disparity

    for page in pages:
        if bundle.render_checked >= 8:
            bundle.notes.append("Rendering parity was compared on the first 8 paired snapshots only.")
            break
        raw_html = _get(page, "raw_html")
        rendered_html = _get(page, "rendered_html")
        if not raw_html or not rendered_html:
            continue
        bundle.render_checked += 1
        try:
            disparity, _findings = analyze_rendering_disparity(raw_html, rendered_html, _get(page, "url") or "")
        except Exception:
            continue
        if disparity.get("has_disparity") or disparity.get("has_discrepancy") or disparity.get("client_injected_h1"):
            url = _get(page, "url")
            if isinstance(url, str):
                bundle.render_urls.append(url)
    return bundle


class _Builder:
    def __init__(self, report: Any, ai_runner: Any = None):
        self.report = report
        self.ai_runner = ai_runner
        self.audit_id = str(_get(report, "analysis_id") or _get(report, "report_id") or "unscoped")
        self.domain = _domain_of(report)
        self.generated_at = _get(report, "generated_at")
        manifest = _get(report, "crawl_manifest")
        raw_pages = _as_list(_get(manifest, "pages")) or _as_list(_get(report, "pages"))
        self.pages = _coerce_pages(raw_pages)
        self.discovered = _optional_int(_get(manifest, "total_pages_discovered"))
        self.crawled = _optional_int(_get(manifest, "total_pages_crawled"))
        if self.crawled is None and self.pages:
            self.crawled = len(self.pages)
        self.sampling_status = str(_get(manifest, "sampling_status") or "NOT_RECORDED")
        if self.discovered and self.crawled is not None and self.discovered > self.crawled:
            self.sampling_status = "SAMPLED_AUDIT"
        self.sitemap_urls = [url for url in _as_list(_get(manifest, "sitemap_urls")) if isinstance(url, str)]
        self.robots_found = _get(manifest, "robots_txt_found")
        self.robots_text = _get(manifest, "robots_txt_content")
        self.sitemap_found = _get(manifest, "sitemap_found")
        self.bundle = _hydrate(report, self.pages, self.sitemap_urls)
        self.stack = _detect_stack(self.pages)
        self.sub_status: dict[str, tuple[str, str]] = {}
        self.working: dict[int, list[str]] = {}
        self.limitations: list[str] = list(self.bundle.notes)
        self.evidence: dict[str, EvidenceRecord] = {}
        self.proposed: list[EnterpriseFinding] = []
        self.rejected: list[RejectedFinding] = []
        self.rendered = sum(1 for page in self.pages if _get(page, "rendered_html"))

    def mark(self, subchapter_id: str, status: str, note: str) -> None:
        current = self.sub_status.get(subchapter_id)
        if current and _STATUS_RANK[current[0]] > _STATUS_RANK[status]:
            return
        self.sub_status[subchapter_id] = (status, note)

    def works(self, chapter: int, text: str) -> None:
        self.working.setdefault(chapter, []).append(text)

    def emit(
        self,
        rule_id: str,
        urls: list[str],
        *,
        observed: str,
        expected: str,
        simple: str,
        significance: str,
        source: str,
        eligible: int | None,
        scope: str,
        extra_limitations: list[str] | None = None,
    ) -> None:
        rule = RULE_BY_ID[rule_id]
        clean_urls = [url for url in urls if url][:100]
        if not clean_urls:
            self.rejected.append(RejectedFinding(
                rule_id=rule_id,
                title=rule_id,
                reason="The check matched a count but no URL was stored, so no finding was published.",
            ))
            return
        facts = {rule.expression: True}
        # The expression name is the fact key used by the allowlist wrappers.
        fact_key = _FACT_KEY[rule.expression]
        if not evaluate_condition(rule.expression, {fact_key: True}):
            return
        payload = "|".join([self.audit_id, rule_id, rule.version, source, *sorted(clean_urls)])
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        evidence = EvidenceRecord(
            evidence_id=f"ev_{digest[:16]}",
            content_hash=digest,
            audit_run_id=self.audit_id,
            collected_at=str(self.generated_at) if self.generated_at else None,
            source=source,
            url=clean_urls[0],
            snapshot_type="derived",
            collection_method=source,
            collector="seo.enterprise.v1",
            scope=scope,  # type: ignore[arg-type]
            integrity="derived",
            snapshot_ids=[str(_get(page, "snapshot_id")) for page in self.pages if _get(page, "snapshot_id") and _get(page, "url") in clean_urls],
        )
        self.evidence[evidence.evidence_id] = evidence
        steps, code, risk, tests, owner, effort = _remediation(rule_id, self.stack)
        evaluation_state = "ISSUE_VERIFIED" if rule.issue_type == "defect" else "MEASURED"
        limitations = [
            "The listed URLs are the checked set. This finding does not claim the same condition on every URL of the site.",
        ]
        if self.discovered and self.crawled is not None and self.discovered > self.crawled:
            limitations.append(
                f"The crawl checked {self.crawled} of {self.discovered} discovered URLs."
            )
        if extra_limitations:
            limitations.extend(extra_limitations)
        finding = EnterpriseFinding(
            finding_id=f"f_{digest[:12]}",
            audit_run_id=self.audit_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            rule_class=rule.rule_class,  # type: ignore[arg-type]
            title=_TITLES[rule_id],
            category=_CATEGORIES[rule.chapter],
            chapter=rule.chapter,
            subchapters=list(rule.subchapters),
            severity=rule.severity,  # type: ignore[arg-type]
            issue_type=rule.issue_type,  # type: ignore[arg-type]
            status="open",
            scope=scope,  # type: ignore[arg-type]
            affected_urls=clean_urls,
            affected_count=len(urls),
            eligible_count=eligible,
            evidence_ids=[evidence.evidence_id],
            observed_condition=observed,
            expected_condition=expected,
            simple_explanation=simple,
            seo_significance=significance,
            root_cause_hypothesis=(
                "The same rule matched multiple fetched URLs. A shared template or generator is a plausible cause, and it is not confirmed."
                if len(urls) > 1
                else "The condition is present on the fetched URL. The template or configuration that produced it was not identified."
            ),
            cause_label="plausible" if len(urls) > 1 else "unknown",
            remediation_steps=steps,
            code_examples=code,
            code_is_illustrative=True,
            stack_detected=self.stack,
            acceptance_tests=tests,
            regression_risk=risk,
            confidence=0.9 if rule.issue_type == "defect" else 0.55,
            limitations=limitations,
            owner_role=owner,
            estimated_effort=effort,
            verification_status="NOT_VERIFIABLE",
            observed_at=str(self.generated_at) if self.generated_at else None,
            evaluation_state=evaluation_state,  # type: ignore[arg-type]
            claim_kind="observed",
            business_impact=_IMPACT.get(
                rule_id,
                "The condition can change how this URL is crawled, indexed, or understood. No traffic, ranking, or revenue figure is estimated.",
            ),
            investigation_targets=steps,
            severity_rationale=(
                f"Severity {rule.severity} comes from rule {rule.rule_id} class {rule.rule_class}. "
                "It is not a traffic estimate."
            ),
            confidence_rationale="The condition was read from stored crawl evidence on the listed URLs.",
        )
        self.proposed.append(finding)
        status = "ISSUE_VERIFIED" if rule.issue_type == "defect" else "MEASURED"
        for subchapter_id in rule.subchapters:
            self.mark(subchapter_id, status, observed)

    def finish(self) -> EnterpriseSeoAssessment:
        from app.seo.enterprise.ai_runtime import run_ai_phase
        from app.seo.enterprise.gap import DEFERRED_MODULES

        self._checks()
        ai_results = run_ai_phase(self, phase="analysis", runner=self.ai_runner)
        published = self._adjudicate()
        ai_results.update(run_ai_phase(self, phase="review", findings=published, runner=self.ai_runner))
        published = self._adjudicate()
        chapters = self._chapters(published)
        agents = self._agents(published, ai_results)
        scores = _scores(self.report)
        coverage = self._coverage()
        roadmap = _roadmap(published)
        cards = [build_finding_card(finding) for finding in published]
        limitations = list(self.limitations)
        limitations.append("AEO, GEO, and CRO are separate modules and are not scored here.")
        limitations.append("No post-fix crawl was supplied. This assessment does not implement or verify a fix.")
        limitations.append("AI specialists publish a judgment only when a model completion is grounded in the packet.")
        if any(not card.complete for card in cards):
            limitations.append("One or more finding cards are missing a required section.")
        verified = sum(1 for finding in published if finding.evaluation_state == "ISSUE_VERIFIED")
        inferred = sum(1 for finding in published if finding.evaluation_state == "INFERRED")
        held = sum(1 for result in ai_results.values() if result.status == "unavailable")
        diagnostic = (
            f"SEO analysis only. {verified} verified finding(s) and {inferred} analytical judgment(s) "
            f"were published from the stored evidence. {held} AI specialists loaded a versioned prompt and "
            "did not publish a judgment. GEO, AEO, CRO, competitor benchmarking, content writing, and code "
            "remediation did not run. No traffic, ranking, or revenue figure was estimated."
        )
        return EnterpriseSeoAssessment(
            audit_run_id=self.audit_id,
            domain=self.domain,
            generated_at=str(self.generated_at) if self.generated_at else None,
            report_stage="preliminary",
            coverage=coverage,
            scores=scores,
            chapters=chapters,
            agents=agents,
            execution_order=execution_order(),
            findings=published,
            rejected=self.rejected,
            evidence=list(self.evidence.values()),
            cards=cards,
            roadmap=roadmap,
            limitations=limitations,
            diagnostic_summary=diagnostic,
            deferred_modules=list(DEFERRED_MODULES),
        )

    def _adjudicate(self) -> list[EnterpriseFinding]:
        published: list[EnterpriseFinding] = []
        seen: set[str] = set()
        seen_conditions: set[tuple[str, tuple[str, ...]]] = set()
        evidence_ids = set(self.evidence)
        for finding in self.proposed:
            if finding.finding_id in seen:
                self.rejected.append(RejectedFinding(rule_id=finding.rule_id, title=finding.title, reason="Duplicate finding."))
                continue
            condition = (finding.rule_id, tuple(sorted(finding.affected_urls)))
            if condition in seen_conditions:
                self.rejected.append(RejectedFinding(
                    rule_id=finding.rule_id,
                    title=finding.title,
                    reason="Duplicate finding for the same rule and URL set.",
                ))
                continue
            if finding.scope == "SITE_INFERRED":
                self.rejected.append(RejectedFinding(
                    rule_id=finding.rule_id,
                    title=finding.title,
                    reason="A sample was generalized to the whole site.",
                ))
                continue
            if not finding.evidence_ids or any(item not in evidence_ids for item in finding.evidence_ids):
                self.rejected.append(RejectedFinding(
                    rule_id=finding.rule_id,
                    title=finding.title,
                    reason="The finding has no retrievable evidence record.",
                ))
                continue
            if not finding.affected_urls:
                self.rejected.append(RejectedFinding(
                    rule_id=finding.rule_id,
                    title=finding.title,
                    reason="The finding has no affected URL.",
                ))
                continue
            seen.add(finding.finding_id)
            seen_conditions.add(condition)
            published.append(finding)
        published = _drop_contradictions(published, self.rejected)
        unique: list[RejectedFinding] = []
        seen_rejected: set[tuple[str, str, str]] = set()
        for item in self.rejected:
            key = (item.rule_id, item.title, item.reason)
            if key in seen_rejected:
                continue
            seen_rejected.add(key)
            unique.append(item)
        self.rejected = unique
        return published

    def _checks(self) -> None:
        self._scope_chapters()
        self._robots()
        self._http()
        self._indexability()
        self._sitemap()
        self._architecture()
        self._titles()
        self._headings()
        self._content()
        self._images()
        self._links()
        self._schema()
        self._international()
        self._rendering()
        self._performance()
        self._mobile()
        self._security()
        self._page_types()
        self._integrations()
        self._assurance_chapters()

    def _scope_chapters(self) -> None:
        self.mark("1.1", "MEASURED", "This module does not calculate a score. A sealed category score is shown only when the scoring service stored one.")
        self.mark("1.3", "MEASURED", "Highest-impact items are the published findings from the checked URLs.")
        self.mark("1.4", "MEASURED", "Strengths are limited to checks that ran and found the expected condition.")
        self.mark("1.5", "MEASURED", "The roadmap orders published findings. It does not estimate traffic or revenue.")
        self.mark("1.6", "MEASURED", "Limitations are listed with the coverage statement.")
        self.mark("2.1", "MEASURED", f"Audited host: {self.domain}.")
        self.mark("2.8", "MEASURED", f"Assessment schema seo.enterprise.v1. Audit run {self.audit_id}.")
        self.mark("2.9", "MEASURED", "Untested subchapters stay not tested. They are not passes.")
        if self.crawled is None:
            self.mark("2.4", "NOT_TESTED", "No crawl count was stored.")
        else:
            discovered = f"{self.discovered} discovered" if self.discovered else "the full-site denominator was not stored"
            self.mark("2.4", "MEASURED", f"Crawl status {self.sampling_status}. Checked {self.crawled} URLs; {discovered}.")
        manifest = _get(self.report, "crawl_manifest")
        if manifest is None:
            self.mark("2.3", "NOT_TESTED", "No crawl manifest was stored.")
            self.mark("2.5", "NOT_TESTED", "Robots policy was not stored on the manifest.")
        else:
            via_links = len(_as_list(_get(manifest, "discovered_via_links")))
            via_sitemap = len(_as_list(_get(manifest, "discovered_via_sitemap"))) or len(self.sitemap_urls)
            self.mark("2.3", "MEASURED", f"Discovery sources in the manifest: links {via_links}, sitemap URLs {via_sitemap}.")
        self.mark("2.2", "NOT_TESTED", "The crawler user-agent string was not stored on this report.")
        self.mark("2.6", "NOT_TESTED", "Browser and rendering configuration were not stored as a reproducible profile.")

    def _robots(self) -> None:
        if self.robots_found is None and not self.robots_text:
            self.mark("3.1", "NOT_TESTED", "No robots.txt fetch was stored.")
            return
        robots_url = f"https://{self.domain}/robots.txt" if self.domain != "unknown" else ""
        if self.robots_found is False:
            self.emit(
                "seo.robots.unavailable",
                [robots_url],
                observed="The crawl recorded that robots.txt was not available.",
                expected="A reachable robots.txt whose directives match the intended crawl policy.",
                simple="The site did not return a robots.txt file during the crawl.",
                significance="Crawlers then fall back to their default policy. A missing file does not by itself remove URLs from an index.",
                source="crawl_manifest.robots_txt_found",
                eligible=1,
                scope="PAGE_VERIFIED",
                extra_limitations=["This records the robots fetch, not a deindexation."],
            )
            return
        if not isinstance(self.robots_text, str) or not self.robots_text.strip():
            self.mark("3.1", "NOT_TESTED", "robots.txt was reported present, but the response body was not stored.")
            return
        parsed = _parse_robots(self.robots_text)
        if parsed["errors"]:
            self.emit(
                "seo.robots.syntax",
                [robots_url],
                observed="The stored robots.txt body has directive lines the parser could not accept.",
                expected="User-agent groups with Allow and Disallow directives in a parseable file.",
                simple="The robots file contains lines that do not follow the expected directive syntax.",
                significance="A crawler may ignore a broken line or interpret the group differently from the author's intent.",
                source="crawl_manifest.robots_txt_content",
                eligible=1,
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark("3.1", "NO_ISSUE", "The stored robots.txt body parsed into user-agent groups.")
            self.works(3, "The stored robots.txt body parsed.")
        if parsed["disallow_all"]:
            self.emit(
                "seo.robots.disallow_all",
                [robots_url],
                observed="A * or Googlebot group contains Disallow: /.",
                expected="Disallow rules that block only the paths the site intends to keep out of crawl.",
                simple="The stored robots file tells matching crawlers not to fetch the site.",
                significance="This is a crawl restriction. It is not proof that previously indexed URLs have been removed from the index.",
                source="crawl_manifest.robots_txt_content",
                eligible=1,
                scope="PAGE_VERIFIED",
                extra_limitations=["Do not describe this as a confirmed deindexation."],
            )
        if parsed["conflict"]:
            self.emit(
                "seo.robots.conflict",
                [robots_url],
                observed="The same path is both allowed and disallowed in one matching user-agent group.",
                expected="One outcome per path for each user-agent group.",
                simple="Allow and Disallow disagree for at least one path.",
                significance="Matching crawlers can apply a different path than the one the author expects.",
                source="crawl_manifest.robots_txt_content",
                eligible=1,
                scope="PAGE_VERIFIED",
            )
        elif not parsed["disallow_all"]:
            self.mark("3.2", "NO_ISSUE", "No allow/disallow conflict was found in the * or Googlebot groups.")
        self.mark("3.7", "NOT_TESTED", "Calendar and infinite-space traps were not executed as a separate check.")
        self.mark("3.8", "NOT_TESTED", "Internal nofollow and blocked-resource fetches were not separately measured.")
        self.mark("3.9", "NOT_TESTED", "Search-engine bot responses were not compared with the audit crawler.")

    def _http(self) -> None:
        http = self.bundle.http
        if http is None:
            self.mark("5.1", "NOT_TESTED", "No HTTP status inventory was stored.")
            return
        eligible = _optional_int(_get(http, "total_urls_checked")) or self.crawled
        pages_4xx = _urls(_get(http, "pages_4xx"))
        pages_5xx = _urls(_get(http, "pages_5xx"))
        broken = _urls(_get(http, "broken_links"))
        count_2xx = _optional_int(_get(http, "count_2xx")) or 0
        if pages_4xx:
            self.emit(
                "seo.http.4xx",
                pages_4xx,
                observed=f"{len(pages_4xx)} fetched URLs returned a 4xx status.",
                expected="Internal destinations that people and crawlers still request return a successful final URL.",
                simple="Some checked URLs were not found or were refused.",
                significance="Links and sitemap entries that end on these URLs waste crawl and send people to an error.",
                source="http_status_breakdown.pages_4xx",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        if pages_5xx:
            self.emit(
                "seo.http.5xx",
                pages_5xx,
                observed=f"{len(pages_5xx)} fetched URLs returned a 5xx status.",
                expected="Public URLs return a successful response or a deliberate redirect.",
                simple="The server failed while those URLs were being fetched.",
                significance="A server error can keep a URL out of the index while it persists. One sample does not prove the failure is constant.",
                source="http_status_breakdown.pages_5xx",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        if broken:
            self.emit(
                "seo.http.broken_link",
                broken,
                observed=f"{len(broken)} internal link targets in the crawl were broken.",
                expected="Internal links point at a final URL that returns a successful response.",
                simple="The crawl found links whose destinations failed.",
                significance="Those links do not pass discovery to the intended page.",
                source="http_status_breakdown.broken_links",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        if not pages_4xx and not pages_5xx:
            self.mark("5.1", "NO_ISSUE", f"No 4xx or 5xx URLs were in the {eligible or 'checked'} URL inventory.")
            self.works(5, f"{count_2xx} URLs in the inventory were in the 2xx class.")
        redirects = self.bundle.redirects
        if redirects is None:
            self.mark("5.2", "NOT_TESTED", "Redirect hops were not stored.")
        else:
            if _get(redirects, "has_redirect_loop"):
                self.emit(
                    "seo.http.loop",
                    _redirect_urls(redirects) or [f"https://{self.domain}/"],
                    observed="The host probe recorded a redirect loop.",
                    expected="Each redirect ends on a final URL without returning to an earlier hop.",
                    simple="A request was sent in a circle.",
                    significance="A loop prevents the final page from being fetched.",
                    source="host_and_redirects.has_redirect_loop",
                    eligible=1,
                    scope="PAGE_VERIFIED",
                )
            elif _get(redirects, "has_chain_gt_1_hop"):
                self.emit(
                    "seo.http.chain",
                    _redirect_urls(redirects) or [f"https://{self.domain}/"],
                    observed="The host probe recorded a redirect chain longer than one hop.",
                    expected="Hostname and protocol variants resolve in a single permanent redirect.",
                    simple="Requests pass through more than one redirect before the final URL.",
                    significance="Extra hops add failure points and can waste crawl.",
                    source="host_and_redirects.has_chain_gt_1_hop",
                    eligible=1,
                    scope="PAGE_VERIFIED",
                )
            else:
                self.mark("5.2", "NO_ISSUE", "The stored host probe did not record a loop or a multi-hop chain.")
        self.mark("5.3", "NOT_TESTED", "Temporary versus permanent redirect use was not classified hop by hop.")
        soft_urls = [
            _get(page, "url")
            for page in _as_list(_get(self.bundle.indexation, "pages"))
            if _get(page, "is_soft_404") and _get(page, "url")
        ]
        if soft_urls:
            self.emit(
                "seo.index.soft404",
                [url for url in soft_urls if isinstance(url, str)],
                observed="The indexation record flagged these URLs as soft 404s.",
                expected="A missing page returns an error status, or a real page returns its own content.",
                simple="A stored check says these URLs look like missing pages while still answering successfully.",
                significance="A soft 404 can be treated as an error even though the status is successful. This crawl alone does not confirm how a search engine classifies it.",
                source="indexation_intelligence.pages.is_soft_404",
                eligible=_optional_int(_get(self.bundle.indexation, "total_pages_evaluated")) or self.crawled,
                scope="PAGE_VERIFIED",
                extra_limitations=["A 200 response by itself was not treated as a soft 404."],
            )
        else:
            self.mark("5.4", "NOT_TESTED", "Soft 404s were not inferred from successful responses. No soft-404 flag was stored.")
        self.mark("5.6", "NOT_TESTED", "Asset responses were not inventoried separately from page statuses.")
        self.mark("5.8", "NOT_TESTED", "Redirect destination relevance was not judged.")
        self.mark("5.9", "NOT_TESTED", "Intermittent failures need repeated fetches. One crawl does not show them.")
        self.mark("5.10", "NOT_TESTED", "CDN and edge responses were not compared across locations.")
        insecure = [url for url in _page_url_list(self.pages) if url.startswith("http://")]
        if insecure:
            self.emit(
                "seo.http.https",
                insecure,
                observed="Fetched URLs used http://.",
                expected="Public pages are requested and served on HTTPS.",
                simple="Part of the checked inventory is still on HTTP.",
                significance="People and crawlers can be sent through an extra redirect, or stay on an unsecured URL.",
                source="crawl.pages.url",
                eligible=self.crawled,
                scope="PAGE_VERIFIED",
            )
        elif self.pages:
            self.mark("5.7", "NO_ISSUE", "The fetched page URLs used HTTPS.")

    def _indexability(self) -> None:
        canonical = self.bundle.canonical
        if canonical is None:
            self.mark("4.3", "NOT_TESTED", "Canonical tags were not audited.")
        else:
            eligible = _optional_int(_get(canonical, "total_pages_evaluated")) or self.crawled
            missing = [
                url for url in (
                    _url_of(item) for item in _as_list(_get(canonical, "items"))
                    if str(_get(item, "status") or "") == "missing"
                ) if url
            ]
            conflicts = [
                url for url in (
                    _url_of(item) for item in _as_list(_get(canonical, "items"))
                    if str(_get(item, "status") or "") in {"broken", "multiple", "cross_domain"}
                ) if url
            ]
            if missing:
                self.emit(
                    "seo.canonical.missing",
                    missing,
                    observed="These fetched pages have no canonical URL.",
                    expected="Each indexable URL declares one canonical URL that matches the preferred address.",
                    simple="The page does not say which URL is the preferred one.",
                    significance="Search engines may choose a different URL. A missing canonical is not proof of a ranking loss.",
                    source="canonical_audit.items",
                    eligible=eligible,
                    scope="PAGE_VERIFIED",
                )
            elif (_optional_int(_get(canonical, "missing_canonical_count")) or 0) > 0:
                self.mark("4.3", "MEASURED", "Missing canonicals were counted, but the URL list was not stored, so no finding was published.")
            else:
                self.mark("4.3", "NO_ISSUE", "No missing canonical was recorded in the canonical audit.")
                self.works(4, "Checked pages that were audited for canonicals had a canonical signal.")
            if conflicts:
                self.emit(
                    "seo.canonical.conflict",
                    conflicts,
                    observed="Canonical targets are broken, repeated, or point at another host.",
                    expected="One absolute canonical URL on the preferred host.",
                    simple="The page sends more than one conflicting preferred-URL signal.",
                    significance="Conflicting canonicals make the preferred URL ambiguous.",
                    source="canonical_audit.items",
                    eligible=eligible,
                    scope="PAGE_VERIFIED",
                )
            else:
                self.mark("4.4", "NO_ISSUE", "No broken, repeated, or cross-host canonical was listed.")
        indexation = self.bundle.indexation
        noindex_urls = [
            _get(page, "url")
            for page in _as_list(_get(indexation, "pages"))
            if _get(page, "has_noindex") and _get(page, "url")
        ]
        if not noindex_urls:
            noindex_urls = [
                _get(page, "url")
                for page in self.pages
                if "noindex" in str(_get(page, "robots_meta") or "").lower()
                or "noindex" in str(_get(page, "x_robots_tag") or "").lower()
            ]
        if noindex_urls:
            self.emit(
                "seo.index.noindex",
                [url for url in noindex_urls if isinstance(url, str)],
                observed="These fetched URLs send a noindex directive.",
                expected="URLs that should be eligible for indexing do not send noindex.",
                simple="The page asks crawlers not to index it.",
                significance="A noindex directive can keep a URL out of the index. This crawl does not confirm whether a search engine has dropped it.",
                source="indexation_or_robots_meta",
                eligible=_optional_int(_get(indexation, "total_pages_evaluated")) or self.crawled,
                scope="PAGE_VERIFIED",
                extra_limitations=["Eligibility is not index confirmation."],
            )
        elif indexation is not None or self.pages:
            self.mark("4.1", "NO_ISSUE", "No noindex directive was stored on the checked URLs.")
            self.mark("4.2", "NO_ISSUE", "No conflicting index directive was stored.")
        else:
            self.mark("4.1", "NOT_TESTED", "Robots directives were not stored.")
        gsc_rows = [
            page for page in _as_list(_get(indexation, "pages"))
            if _get(page, "gsc_coverage_state")
        ]
        if gsc_rows:
            self.mark("4.8", "MEASURED", "Search Console coverage states were stored. They were not re-diagnosed as a cause.")
        else:
            self.mark("4.8", "DATA_UNAVAILABLE", "Search Console indexing status was not stored. That absence is not an indexing failure.")
        self.mark("4.5", "MEASURED" if indexation is not None else "NOT_TESTED",
                  "Indexable and non-indexable counts come from the stored indexation rollup." if indexation is not None else "No indexable inventory was stored.")
        self.mark("4.9", "NOT_TESTED", "Index bloat was not calculated beyond duplicate titles and URL variants in this pass.")
        self.mark("4.10", "MEASURED", "Crawl eligibility is not confirmation that a URL is in a search index.")
        self.mark("4.7", "NOT_TESTED", "Status, redirect, and canonical consistency was not joined into one chain check.")

    def _sitemap(self) -> None:
        manifest = _get(self.report, "crawl_manifest")
        if manifest is None and self.sitemap_found is None:
            self.mark("7.1", "NOT_TESTED", "Sitemap discovery was not stored.")
            self.mark("3.3", "NOT_TESTED", "Sitemap discovery was not stored.")
            return
        if self.sitemap_found is False:
            self.emit(
                "seo.sitemap.missing",
                [f"https://{self.domain}/sitemap.xml"] if self.domain != "unknown" else [],
                observed="The crawl did not discover an XML sitemap.",
                expected="A sitemap is published when the site uses one to list canonical URLs.",
                simple="No XML sitemap was found from the stored discovery sources.",
                significance="A missing sitemap is not proof of a ranking problem. Discovery can still happen through links.",
                source="crawl_manifest.sitemap_found",
                eligible=1,
                scope="PAGE_VERIFIED",
                extra_limitations=["Sitemap omission was not treated as a ranking failure."],
            )
        elif self.sitemap_urls:
            self.mark("7.1", "MEASURED", f"{len(self.sitemap_urls)} sitemap URLs were stored. XML schema validation of the file body was not run in this pass.")
            self.mark("3.3", "MEASURED", "Sitemap URLs were present in the manifest.")
            bad = set(_urls(_get(self.bundle.http, "pages_4xx")) + _urls(_get(self.bundle.http, "pages_5xx")) + _urls(_get(self.bundle.http, "pages_3xx")))
            ineligible = [url for url in self.sitemap_urls if url in bad]
            if ineligible:
                self.emit(
                    "seo.sitemap.ineligible",
                    ineligible,
                    observed="Sitemap URLs match fetched URLs whose final status is a redirect or an error.",
                    expected="Sitemap URLs are canonical and return a successful status.",
                    simple="The sitemap lists URLs that the crawl did not fetch as successful final pages.",
                    significance="Search engines may waste crawl on those entries.",
                    source="crawl_manifest.sitemap_urls",
                    eligible=len(self.sitemap_urls),
                    scope="SAMPLE_VERIFIED",
                )
            else:
                self.mark("7.3", "NO_ISSUE", "Stored sitemap URLs did not match the 3xx, 4xx, or 5xx inventory.")
        else:
            self.mark("7.1", "NOT_TESTED", "A sitemap was reported, but its URL list was not stored.")
        for subchapter_id, note in (
            ("7.2", "The sitemap XML body was not validated against the schema."),
            ("7.5", "lastmod values were not compared with page changes."),
            ("7.6", "Sitemap freshness was not measured."),
            ("7.7", "Sitemap size limits were not calculated."),
            ("7.8", "Image and video sitemaps were not checked."),
            ("7.9", "Sitemap segmentation was not reviewed."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)
        self.mark("7.4", "NOT_TESTED", "Sitemap URLs were not fully joined to canonical targets in this pass.")

    def _architecture(self) -> None:
        urls = _page_url_list(self.pages) or self.sitemap_urls
        if not urls:
            self.mark("6.1", "NOT_TESTED", "No URL inventory was stored.")
            return
        self.mark("6.1", "MEASURED", f"{len(urls)} URLs were available for architecture checks.")
        variants = _normalization_variants(urls)
        if variants:
            self.emit(
                "seo.url.variant",
                variants,
                observed="The inventory contains URLs that differ only by trailing slash or letter case.",
                expected="Each document has one normalized URL.",
                simple="The same path is available at more than one spelling.",
                significance="Duplicate URLs can split signals if they are both linked or listed.",
                source="url_inventory",
                eligible=len(urls),
                scope="SAMPLE_VERIFIED",
            )
        else:
            self.mark("6.3", "NO_ISSUE", "No trailing-slash or case duplicates were found in the stored inventory.")
        sessions = [url for url in urls if _has_session_parameter(url)]
        if sessions:
            self.emit(
                "seo.url.session",
                sessions,
                observed="URLs contain a session-like query parameter.",
                expected="Public URLs do not include session identifiers.",
                simple="A parameter such as a session id is part of the URL.",
                significance="Session parameters can create many URLs for the same page.",
                source="url_inventory",
                eligible=len(urls),
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark("6.4", "NO_ISSUE", "No session-like query parameter was found in the stored URLs.")
        depth = self.bundle.click
        if depth is None:
            self.mark("6.6", "NOT_TESTED", "Click depth was not calculated.")
            self.mark("3.5", "NOT_TESTED", "Click depth was not calculated.")
        else:
            deep = _optional_int(_get(depth, "high_depth_warning_count")) or 0
            deep_urls = _as_list((_get(depth, "pages_by_depth") or {}).get("4") if isinstance(_get(depth, "pages_by_depth"), dict) else [])
            deep_urls += _as_list((_get(depth, "pages_by_depth") or {}).get("4+") if isinstance(_get(depth, "pages_by_depth"), dict) else [])
            listed = [url for url in deep_urls if isinstance(url, str)]
            if deep and listed:
                self.emit(
                    "seo.graph.depth",
                    listed,
                    observed=f"{deep} URLs sit four or more clicks from the homepage in the measured graph.",
                    expected="Important URLs are reachable in a small number of clicks within the crawled graph.",
                    simple="Some checked pages take several clicks to reach from the home page.",
                    significance="Deep pages are harder to discover. A sample crawl can exaggerate depth when links were not followed.",
                    source="click_depth.pages_by_depth",
                    eligible=_optional_int(_get(depth, "total_pages_analyzed")) or self.crawled,
                    scope="SAMPLE_VERIFIED",
                    extra_limitations=["Depth is relative to the crawled link graph."],
                )
            else:
                self.mark("6.6", "NO_ISSUE", "The stored click-depth report did not list pages at depth four or more.")
                self.mark("3.5", "NO_ISSUE", "Click depth did not flag a four-click path in the stored report.")
                self.mark("15.8", "NO_ISSUE", "Important-page depth was not flagged in the stored click-depth report.")
        self.mark("6.2", "NOT_TESTED", "URL readability was not scored.")
        self.mark("6.5", "MEASURED", "Directory nesting was inspected only for duplicate spellings and click depth.")
        hosts = {urlsplit(url).netloc.lower() for url in urls if "://" in url}
        self.mark("6.7", "MEASURED", f"Hosts in the stored inventory: {', '.join(sorted(hosts)) or 'none'}.")
        if any("/page/" in url or "page=" in url for url in urls):
            self.mark("6.8", "MEASURED", "Pagination-like URLs were observed. Their indexable combinations were not fully tested.")
        else:
            self.mark("6.8", "NOT_APPLICABLE", "No pagination URL was in the stored inventory.")
        if any(any(token in url for token in ("sort=", "filter=", "color=", "size=")) for url in urls):
            self.mark("6.9", "MEASURED", "Facet-like parameters were observed. Indexable combinations were not enumerated.")
        else:
            self.mark("6.9", "NOT_APPLICABLE", "No facet-like parameter was in the stored inventory.")
        self.mark("6.10", "NOT_TESTED", "Historical URLs were not compared with a migration baseline.")
        self.mark("3.6", "NOT_TESTED", "Faceted crawl-trap handling was not simulated.")

    def _titles(self) -> None:
        meta = self.bundle.meta
        if meta is None:
            self.mark("10.1", "NOT_TESTED", "Titles were not extracted.")
            return
        eligible = _optional_int(_get(meta, "total_pages_evaluated")) or self.crawled
        missing = _urls(_get(meta, "missing_titles"))
        duplicate = _urls(_get(meta, "duplicate_titles"))
        short = _urls(_get(meta, "too_short_titles"))
        long = _urls(_get(meta, "too_long_titles"))
        if missing:
            self.emit(
                "seo.title.missing",
                missing,
                observed="The extracted title is missing or empty.",
                expected="Each indexable page has one non-empty title that describes that page.",
                simple="The page does not provide a title.",
                significance="The site loses control of the title link. Search engines may write their own. This does not by itself prove a ranking loss.",
                source="meta_rollup.missing_titles",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        if duplicate:
            self.emit(
                "seo.title.duplicate",
                duplicate,
                observed="The same non-empty title was extracted on more than one checked URL.",
                expected="Titles are unique where the pages serve different purposes.",
                simple="More than one checked page uses the same title.",
                significance="Duplicate titles make those pages harder to tell apart in search results.",
                source="meta_rollup.duplicate_titles",
                eligible=eligible,
                scope="SAMPLE_VERIFIED",
                extra_limitations=["Uniqueness is relative to the checked URLs, not the whole site."],
            )
        if not missing and not duplicate:
            self.mark("10.1", "NO_ISSUE", "No missing or duplicate title was recorded in the checked pages.")
            self.works(10, "Checked pages had titles, and no duplicate title was recorded.")
        length_urls = []
        for url in short + long:
            if url not in length_urls and url not in missing:
                length_urls.append(url)
        if length_urls:
            self.emit(
                "seo.title.length",
                length_urls,
                observed="Title length falls outside the diagnostic band used by the existing meta rollup.",
                expected="Titles are understandable when shown in a search result. Length is not a ranking threshold.",
                simple="The title is shorter or longer than the diagnostic band.",
                significance="Length can affect truncation. It is not evidence that the page ranks worse.",
                source="meta_rollup.title_length",
                eligible=eligible,
                scope="PAGE_VERIFIED",
                extra_limitations=["Character length was not treated as a ranking rule."],
            )
        else:
            self.mark("10.6", "NO_ISSUE", "No title was outside the diagnostic length band.")
        for subchapter_id, note in (
            ("10.2", "Title relevance to intent was not judged. No query mapping was applied."),
            ("10.3", "Keyword targeting was not scored."),
            ("10.4", "Brand and template conventions were not compared with a style guide."),
            ("10.7", "Template-level title variation was not isolated from page-level titles."),
            ("10.8", "Live search-result title rewrites were not collected."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)
        descriptions = _urls(_get(meta, "missing_descriptions"))
        duplicate_descriptions = _urls(_get(meta, "duplicate_descriptions"))
        if descriptions:
            self.emit(
                "seo.meta.missing",
                descriptions,
                observed="The meta description is missing or empty.",
                expected="Pages that rely on a snippet provide a unique description of the page.",
                simple="The page does not provide a meta description.",
                significance="Search engines may write the snippet themselves. A meta description is not a guaranteed ranking boost.",
                source="meta_rollup.missing_descriptions",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        if duplicate_descriptions:
            self.emit(
                "seo.meta.duplicate",
                duplicate_descriptions,
                observed="The same meta description was extracted on more than one checked URL.",
                expected="Descriptions differ where the pages differ.",
                simple="More than one checked page repeats the same description.",
                significance="A repeated description is a weak snippet. It is not evidence of a ranking penalty.",
                source="meta_rollup.duplicate_descriptions",
                eligible=eligible,
                scope="SAMPLE_VERIFIED",
            )
        if not descriptions and not duplicate_descriptions:
            self.mark("11.1", "NO_ISSUE", "No missing or duplicate meta description was recorded.")
        for subchapter_id, note in (
            ("11.2", "Search-intent alignment was not judged."),
            ("11.3", "Value-proposition quality was not edited by a model."),
            ("11.4", "Keyword stuffing was not classified."),
            ("11.5", "Template generation was not isolated."),
            ("11.6", "Live snippet rewrites were not collected. Meta descriptions are not a ranking boost."),
            ("11.7", "Description quality was not split by page type."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)

    def _headings(self) -> None:
        headings = self.bundle.headings
        if headings is None:
            self.mark("12.1", "NOT_TESTED", "Headings were not extracted.")
            return
        eligible = _optional_int(_get(headings, "total_pages_evaluated")) or self.crawled
        missing = _urls(_get(headings, "missing_h1"))
        multiple = _urls(_get(headings, "multiple_h1"))
        if missing:
            self.emit(
                "seo.heading.missing_h1",
                missing,
                observed="The extracted outline has no H1.",
                expected="The page has a heading that states its subject.",
                simple="The page outline does not name a main heading.",
                significance="The document structure is harder to understand. A missing H1 is not a confirmed ranking loss.",
                source="heading_hierarchy.missing_h1",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark("12.1", "NO_ISSUE", "No missing H1 was recorded.")
            self.works(12, "Checked pages had an H1.")
        if multiple:
            self.emit(
                "seo.heading.multiple_h1",
                multiple,
                observed="More than one H1 was extracted.",
                expected="The outline makes the main subject clear. Multiple H1 elements are not automatically a defect.",
                simple="The page has more than one top-level heading.",
                significance="This is a diagnostic. Multiple H1 elements are not treated as a ranking violation.",
                source="heading_hierarchy.multiple_h1",
                eligible=eligible,
                scope="PAGE_VERIFIED",
                extra_limitations=["Multiple H1 elements were not classified as a ranking failure."],
            )
        violations = _urls(_get(headings, "hierarchy_violations"))
        if violations:
            self.emit(
                "seo.heading.hierarchy",
                violations,
                observed="The stored heading audit recorded a skipped heading level.",
                expected="Heading levels follow the document outline without unexplained skips.",
                simple="The outline jumps over a heading level.",
                significance="A broken outline makes the page harder to scan. It is not a confirmed ranking loss.",
                source="heading_hierarchy.hierarchy_violations",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark("12.2", "NO_ISSUE", "No heading-level skip was listed.")
        for subchapter_id, note in (
            ("12.3", "Generic heading copy was not judged."),
            ("12.4", "Heading relevance to the body was not judged."),
            ("12.5", "Landmark elements were not audited in this pass."),
            ("12.6", "Template-generated heading defects were not isolated."),
            ("12.7", "Accessibility overlap was not certified. This is not a WCAG certificate."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)

    def _content(self) -> None:
        short = [
            _get(page, "url")
            for page in self.pages
            if isinstance(_get(page, "url"), str)
            and isinstance(_get(page, "word_count"), int)
            and 0 <= _get(page, "word_count") < 40
            and (_get(page, "status_code") or 200) == 200
        ]
        if not self.pages:
            self.mark("13.4", "NOT_TESTED", "Page text was not stored.")
        elif short:
            self.emit(
                "seo.content.short_text",
                [url for url in short if isinstance(url, str)],
                observed="Fewer than 40 words were extracted from the page.",
                expected="The page contains the explanation its purpose requires.",
                simple="Very little text was extracted.",
                significance="Word count is not a quality score. A short page can be complete. This flags the measurement only.",
                source="page.word_count",
                eligible=len(self.pages),
                scope="PAGE_VERIFIED",
                extra_limitations=["Word count was not treated as quality, and filler was not recommended."],
            )
        else:
            self.mark("13.4", "MEASURED", "Extracted word counts were inspected. No page under 40 words was flagged. Word count is not a quality score.")
        for subchapter_id, note in (
            ("13.1", "Topical completeness was not judged by a model."),
            ("13.2", "Search-intent satisfaction was not judged."),
            ("13.3", "Originality and information gain were not measured."),
            ("13.5", "Factual freshness was not checked against a source."),
            ("13.6", "Claims were not sent for subject-matter review."),
            ("13.7", "Readability was not used as a ranking score."),
            ("13.8", "Cross-page duplication was not fingerprinted in this pass."),
            ("13.9", "Query cannibalization requires query-level evidence and was not inferred from titles alone."),
            ("13.10", "Page purpose was not judged editorially."),
            ("13.11", "Editorial ownership was not recorded."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)

    def _images(self) -> None:
        media = self.bundle.media
        if media is None:
            self.mark("14.1", "NOT_TESTED", "Image markup was not audited.")
            return
        eligible = _optional_int(_get(media, "total_images_analyzed"))
        missing = _urls(_get(media, "missing_alt_images")) or _urls(_get(media, "flagged_images"))
        missing = [url for url in missing if url]
        if (_optional_int(_get(media, "missing_alt_count")) or 0) > 0 and missing:
            self.emit(
                "seo.image.alt",
                missing,
                observed="Informative images were recorded without alt text.",
                expected="Informative images have alt text. Decorative images are marked as decorative.",
                simple="An image is missing a text alternative.",
                significance="People and some crawlers lose the description of the image. The filename was not treated as the image's meaning.",
                source="media_assets.missing_alt",
                eligible=eligible,
                scope="PAGE_VERIFIED",
            )
        elif (_optional_int(_get(media, "missing_alt_count")) or 0) == 0 and eligible:
            self.mark("14.2", "NO_ISSUE", "The image audit did not record missing alt text.")
            self.works(14, "No missing alt text was recorded in the image audit.")
        else:
            self.mark("14.2", "NOT_TESTED", "Alt text results were not stored with URLs.")
        if (_optional_int(_get(media, "missing_dimensions_count")) or 0) > 0:
            dim_urls = _urls(_get(media, "cls_risk_images")) or missing
            if dim_urls:
                self.emit(
                    "seo.image.dimensions",
                    dim_urls,
                    observed="Images were recorded without width and height.",
                    expected="Images reserve space when layout stability matters.",
                    simple="The image markup does not reserve its display size.",
                    significance="This can contribute to layout movement. It is not a field Cumulative Layout Shift measurement.",
                    source="media_assets.missing_dimensions",
                    eligible=eligible,
                    scope="PAGE_VERIFIED",
                    extra_limitations=["Missing dimensions were not reported as field CLS."],
                )
        else:
            self.mark("14.5", "NO_ISSUE", "The image audit did not record missing dimensions.")
        for subchapter_id, note in (
            ("14.1", "Image URLs were counted only when the media audit stored them."),
            ("14.3", "Filenames were not treated as descriptions of the image."),
            ("14.4", "srcset was not validated."),
            ("14.6", "Compression and modern formats were not scored as a ranking factor."),
            ("14.7", "Lazy-loading behavior was not executed in a browser."),
            ("14.8", "An image sitemap was not required."),
            ("14.9", "Video indexing was not tested."),
            ("14.10", "Media performance was not measured as field Core Web Vitals."),
        ):
            if subchapter_id not in self.sub_status:
                self.mark(subchapter_id, "NOT_TESTED", note)

    def _links(self) -> None:
        orphans = self.bundle.orphans
        sitemap_total = _optional_int(_get(orphans, "total_sitemap_urls")) or len(self.sitemap_urls)
        orphan_urls = _urls(_get(orphans, "orphan_urls")) if orphans is not None else []
        if orphans is None:
            self.mark("15.2", "NOT_TESTED", "Orphan detection did not run.")
            self.mark("3.4", "NOT_TESTED", "Orphan detection did not run.")
        elif sitemap_total <= 0:
            self.mark("15.2", "NOT_TESTED", "Orphans were not confirmed because the sitemap denominator is missing.")
            self.mark("3.4", "NOT_TESTED", "Orphan detection had no sitemap source to compare.")
        elif orphan_urls:
            self.emit(
                "seo.graph.orphan",
                orphan_urls,
                observed="These URLs are in the sitemap and were not reached by an internal link in the measured crawl.",
                expected="Important URLs are linked from at least one crawled page.",
                simple="The sitemap lists URLs that the crawled pages did not link to.",
                significance="They may be hard to discover by links. This is relative to the crawled pages and the sitemap, not proof the URL has no links anywhere.",
                source="orphan_pages.orphan_urls",
                eligible=sitemap_total,
                scope="SAMPLE_VERIFIED",
                extra_limitations=["An orphan here is unconfirmed outside the measured discovery sources."],
            )
        else:
            self.mark("15.2", "NO_ISSUE", "No sitemap URL was left unlinked inside the measured crawl.")
            self.mark("3.4", "NO_ISSUE", "The measured crawl linked every stored sitemap URL.")
        generic = _optional_int(_get(self.bundle.anchors, "generic_anchor_count")) or 0
        generic_urls = []
        for item in _as_list(_get(self.bundle.anchors, "flagged_anchor_instances")):
            url = _url_of(item) or _get(item, "source_url")
            if isinstance(url, str):
                generic_urls.append(url)
        if generic and generic_urls:
            self.emit(
                "seo.link.generic_anchor",
                generic_urls,
                observed=f"{generic} anchors were classified as generic by the existing anchor audit.",
                expected="Anchors describe the destination when a clearer phrase is available.",
                simple="Some links use generic text such as 'click here'.",
                significance="Generic anchors are a writing diagnostic. Exact-match keyword anchors were not prescribed.",
                source="anchor_text_audit.flagged_anchor_instances",
                eligible=_optional_int(_get(self.bundle.anchors, "total_links_analyzed")),
                scope="SAMPLE_VERIFIED",
            )
        elif self.bundle.anchors is not None:
            self.mark("15.3", "NO_ISSUE", "The anchor audit did not flag generic anchors.")
        else:
            self.mark("15.3", "NOT_TESTED", "Anchor text was not audited.")
        for subchapter_id, note in (
            ("15.1", "The link graph is the measured crawl, not a complete site graph."),
            ("15.5", "Links to redirects were not fully joined beyond the HTTP inventory."),
            ("15.6", "Topical relevance of links was not judged."),
            ("15.7", "Navigation, breadcrumb, and footer regions were not separated."),
            ("15.9", "Sitewide link repetition was not counted."),
            ("15.10", "New internal-link opportunities were not invented without a relevance judgment."),
        ):
            if subchapter_id not in self.sub_status:
                self.mark(subchapter_id, "NOT_TESTED", note)
        if "15.4" not in self.sub_status:
            self.mark("15.4", "NOT_TESTED" if self.bundle.http is None else "NO_ISSUE",
                      "Broken internal links follow the HTTP inventory." if self.bundle.http is not None else "Broken links were not inventoried.")

    def _schema(self) -> None:
        schema = self.bundle.schema
        if schema is None:
            self.mark("16.1", "NOT_TESTED", "Structured data was not parsed.")
            return
        errors = [
            item for item in _as_list(_get(schema, "issues"))
            if str(_get(item, "severity") or "").upper() == "ERROR"
        ]
        error_urls = _urls(errors)
        detected = _optional_int(_get(schema, "total_entities_detected")) or 0
        if detected == 0 and not errors:
            self.mark("16.1", "MEASURED", "No structured data was observed. Optional schema was not treated as a defect.")
            self.works(16, "Absence of optional structured data was not scored as a failure.")
        elif error_urls:
            self.emit(
                "seo.schema.error",
                error_urls,
                observed="The schema audit recorded a parse or property error.",
                expected="Present structured data is valid and consistent with the visible page.",
                simple="The markup on the page does not validate.",
                significance="Invalid markup can make a page ineligible for a rich result. Eligibility is not a guarantee the result will show.",
                source="schema_validation.issues",
                eligible=_optional_int(_get(schema, "total_pages_with_schema")) or self.crawled,
                scope="PAGE_VERIFIED",
                extra_limitations=["No review, price, or rating was invented to complete the markup."],
            )
        else:
            self.mark("16.2", "NO_ISSUE", "No schema error was listed.")
            self.works(16, "No schema error was listed for the markup that was present.")
        for subchapter_id, note in (
            ("16.3", "Vocabulary checks are limited to the stored schema audit."),
            ("16.4", "Entity and URL consistency was not re-resolved."),
            ("16.5", "Recommended properties were not promoted to mandatory sitewide requirements."),
            ("16.6", "Contradictory markup was not separately clustered."),
            ("16.7", "Visible-content consistency was not re-read by a model."),
            ("16.8", "Rich-result eligibility was not treated as guaranteed display."),
            ("16.9", "A post-change schema regression was not run."),
        ):
            if subchapter_id not in self.sub_status:
                self.mark(subchapter_id, "NOT_TESTED", note)

    def _international(self) -> None:
        report = self.bundle.international
        if report is None:
            self.mark("9.1", "NOT_TESTED", "Hreflang was not audited.")
            return
        status = str(_get(report, "status") or "").upper()
        multilingual = bool(_get(report, "is_multilingual") or _get(report, "is_international_detected"))
        if status == "NOT_APPLICABLE" or not multilingual:
            for sub in CHAPTERS[8].subchapters:
                self.mark(sub.subchapter_id, "NOT_APPLICABLE", "No multilingual implementation was observed. A missing optional locale feature is not a defect.")
            return
        issues = _as_list(_get(report, "issues"))
        urls = _urls(issues)
        if urls:
            self.emit(
                "seo.hreflang.invalid",
                urls,
                observed="The hreflang audit recorded invalid or non-reciprocal alternates.",
                expected="Each locale URL references its alternates, and those alternates reference it back.",
                simple="The language alternates do not form a consistent set.",
                significance="Broken hreflang can cause the wrong locale to be selected. The site's country was not inferred from the domain.",
                source="international_seo.issues",
                eligible=len(_as_list(_get(report, "matrix"))) or self.crawled,
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark("9.2", "NO_ISSUE", "No hreflang issue was listed for the observed locale implementation.")
        for subchapter_id in ("9.1", "9.4", "9.5", "9.6", "9.7", "9.8", "9.9"):
            if subchapter_id not in self.sub_status:
                self.mark(subchapter_id, "NOT_TESTED", "This locale check was not executed beyond the stored hreflang issue list.")

    def _rendering(self) -> None:
        if self.bundle.render_checked == 0:
            self.mark("8.1", "NOT_TESTED", "No paired raw HTML and rendered DOM snapshots were stored.")
        elif self.bundle.render_urls:
            self.emit(
                "seo.render.parity",
                self.bundle.render_urls,
                observed="Raw HTML and the rendered DOM disagree on a signal the rendering check records.",
                expected="Main content, links, and indexing directives that matter are present in the fetched HTML or survive rendering.",
                simple="The page the server sends and the page after JavaScript do not match.",
                significance="A client-rendered page is not automatically unindexable. The mismatch is limited to the paired snapshots that were compared.",
                source="rendering_disparity",
                eligible=self.bundle.render_checked,
                scope="PAGE_VERIFIED",
                extra_limitations=["Only paired snapshots were compared. An empty first HTML response was not assumed to be an indexing failure."],
            )
        else:
            self.mark("8.1", "NO_ISSUE", f"{self.bundle.render_checked} paired snapshots showed no recorded parity failure.")
            self.works(8, "Paired snapshots that were compared did not record a parity failure.")
        for subchapter_id, note in (
            ("8.2", "Hydration exceptions were not collected as browser telemetry."),
            ("8.3", "A no-JavaScript fetch was not run separately from the raw HTML snapshot."),
            ("8.4", "JavaScript-only links were not inventoried beyond the parity check."),
            ("8.6", "JavaScript console errors were not stored."),
            ("8.7", "Lazy-loaded content was not scrolled into view."),
            ("8.8", "Dynamic metadata was covered only where the parity check compared it."),
            ("8.9", "Route transitions were not browsed."),
            ("8.10", "DOM complexity was not scored as a ranking factor."),
        ):
            if subchapter_id not in self.sub_status:
                self.mark(subchapter_id, "NOT_TESTED", note)

    def _performance(self) -> None:
        field_rows = []
        for page in self.pages:
            field = _get(page, "field_performance")
            if field and _get(field, "has_field_data"):
                field_rows.append((page, field))
        if not field_rows:
            for subchapter_id in ("18.1", "18.2", "18.3", "18.5"):
                self.mark(subchapter_id, "NOT_TESTED", "Field Core Web Vitals were not collected. Response time was not used as LCP, INP, or CLS.")
            self.mark("18.4", "NOT_TESTED", "No field measurement was stored. Response time was not used as LCP, and lab indicators were not promoted to field data.")
        else:
            self.mark("18.4", "MEASURED", "Field rows are labeled separately from lab data.")
            self._field_metric(field_rows, "p75_lcp_ms", 2500, "seo.cwv.lcp", "LCP")
            self._field_metric(field_rows, "p75_inp_ms", 200, "seo.cwv.inp", "INP")
            self._field_metric(field_rows, "p75_cls", 0.1, "seo.cwv.cls", "CLS")
        if any(_get(page, "ttfb_ms") for page in self.pages):
            self.mark("18.10", "MEASURED", "TTFB was stored for at least one URL. It was not reported as LCP.")
        else:
            self.mark("18.10", "NOT_TESTED", "TTFB was not stored.")
        for subchapter_id, note in (
            ("18.6", "Render-blocking resources were not traced."),
            ("18.7", "Main-thread work was not traced."),
            ("18.8", "Image and font loading were not traced as a performance waterfall."),
            ("18.9", "Caching and compression were not measured."),
            ("18.11", "Performance was not grouped by template."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)

    def _field_metric(self, rows: list[tuple[Any, Any]], key: str, threshold: float, rule_id: str, label: str) -> None:
        urls = []
        for page, field in rows:
            value = _get(field, key)
            if isinstance(value, (int, float)) and value > threshold:
                url = _get(page, "url")
                if isinstance(url, str):
                    urls.append(url)
        subchapter = RULE_BY_ID[rule_id].subchapters[0]
        if urls:
            self.emit(
                rule_id,
                urls,
                observed=f"Field {label} is above the documented threshold on the stored CrUX row.",
                expected=f"Field {label} is at or below the current good threshold for the measured origin or URL.",
                simple=f"Real-user {label} is slower or less stable than the current good threshold.",
                significance="This uses the stored field measurement only. It was not estimated from a single server response.",
                source=f"field_performance.{key}",
                eligible=len(rows),
                scope="PAGE_VERIFIED",
            )
        else:
            self.mark(subchapter, "NO_ISSUE", f"Stored field {label} values were within the threshold, or the metric was absent on a row that otherwise had field data.")

    def _mobile(self) -> None:
        self.mark("19.1", "NOT_TESTED", "A separate mobile render was not stored, so content parity was not compared.")
        self.mark("19.2", "NOT_TESTED", "Mobile and desktop metadata were not compared.")
        self.mark("19.3", "NOT_TESTED", "Mobile navigation was not browsed separately.")
        checked = False
        missing_viewport = []
        for page in self.pages:
            raw_html = _get(page, "raw_html")
            if not isinstance(raw_html, str) or "<html" not in raw_html.lower():
                continue
            checked = True
            if not re.search(r"name\s*=\s*['\"]viewport['\"]", raw_html, flags=re.I):
                url = _get(page, "url")
                if isinstance(url, str):
                    missing_viewport.append(url)
        if missing_viewport:
            self.emit(
                "seo.mobile.viewport",
                missing_viewport,
                observed="The stored HTML has no viewport meta element.",
                expected="HTML documents declare a viewport so small screens use the responsive layout.",
                simple="The page does not tell the browser how to size the layout on a phone.",
                significance="Without a viewport, mobile browsers may show a desktop layout. This is not a design preference.",
                source="page.raw_html",
                eligible=self.crawled,
                scope="PAGE_VERIFIED",
            )
        elif checked:
            self.mark("19.4", "NO_ISSUE", "Stored HTML documents included a viewport element.")
        else:
            self.mark("19.4", "NOT_TESTED", "Raw HTML was not stored, so the viewport element was not checked.")
        for subchapter_id, note in (
            ("19.5", "Tap targets were not measured."),
            ("19.6", "Mobile-only network failures were not captured."),
            ("19.7", "Mobile-first crawling was not simulated with a separate bot."),
            ("19.8", "Device-specific performance regressions require field device splits, which were not stored."),
        ):
            self.mark(subchapter_id, "NOT_TESTED", note)

    def _security(self) -> None:
        security = self.bundle.security
        if security is None:
            self.mark("24.4", "NOT_TESTED", "Security headers were not stored.")
        else:
            missing_header = not bool(_get(security, "hsts_enabled"))
            if missing_header:
                self.emit(
                    "seo.security.header",
                    [f"https://{self.domain}/"] if self.domain != "unknown" else [],
                    observed="The stored security audit does not show HSTS.",
                    expected="HTTPS responses include the security headers the deployment standard requires.",
                    simple="A common security header was not observed.",
                    significance="This is a security observation. It is not evidence that rankings, conversions, or citations changed.",
                    source="security_audit.hsts_enabled",
                    eligible=1,
                    scope="PAGE_VERIFIED",
                    extra_limitations=["A missing security header was not described as an SEO ranking loss."],
                )
            self.mark("24.7", "MEASURED", "Security header gaps are reported as security observations, not as confirmed SEO outcomes.")
        mixed = _urls(_get(self.bundle.media, "mixed_content_urls"))
        if mixed:
            self.emit(
                "seo.https.mixed",
                mixed,
                observed="Resources were requested over HTTP from an HTTPS page.",
                expected="Pages load scripts, styles, and images over HTTPS.",
                simple="The page mixes secure and insecure resources.",
                significance="Browsers can block the insecure resource. That can remove content or functionality from the page.",
                source="media_assets.mixed_content_urls",
                eligible=_optional_int(_get(self.bundle.media, "total_images_analyzed")),
                scope="PAGE_VERIFIED",
            )
        elif self.bundle.media is not None:
            self.mark("24.2", "NO_ISSUE", "The media audit did not record mixed content.")
            self.mark("24.3", "NO_ISSUE", "No insecure resource URL was listed.")
        else:
            self.mark("24.2", "NOT_TESTED", "Mixed content was not audited.")
        self.mark("24.1", "NOT_TESTED", "Certificate validity was not probed beyond the stored page URLs.")
        self.mark("24.5", "NOT_TESTED", "Development and staging hosts were not probed.")
        self.mark("24.6", "NOT_TESTED", "Authentication barriers were not tested.")

    def _page_types(self) -> None:
        urls = _page_url_list(self.pages)
        if not urls:
            self.mark("17.1", "NOT_TESTED", "No URLs were available to classify.")
            return
        classes = {
            "17.2": ("/blog", "/news", "/article"),
            "17.3": ("/product", "/shop", "/collection"),
            "17.5": ("/docs", "/documentation", "/help"),
            "17.8": ("/jobs", "/careers"),
            "17.11": ("/page/", "/tag/", "/category"),
        }
        seen: set[str] = set()
        for subchapter_id, tokens in classes.items():
            if any(any(token in url.lower() for token in tokens) for url in urls):
                seen.add(subchapter_id)
                self.mark(subchapter_id, "MEASURED", "URLs matched this class by pattern. The class is uncertain without a template map.")
            else:
                self.mark(subchapter_id, "NOT_APPLICABLE", "No URL of this class was in the checked inventory. That absence is not a defect.")
        self.mark("17.1", "MEASURED", "Remaining URLs were left as unclassified pages. They were not forced into an e-commerce model.")
        for subchapter_id in ("17.4", "17.6", "17.7", "17.9", "17.10", "17.12"):
            self.mark(subchapter_id, "NOT_APPLICABLE" if subchapter_id != "17.12" else "NOT_TESTED",
                      "No sector rule was selected." if subchapter_id == "17.12" else "This page class was not identified in the checked URLs.")

    def _integrations(self) -> None:
        gsc = _channel(_get(_get(self.report, "google_performance"), "search_console"))
        ga4 = _channel(_get(_get(self.report, "google_performance"), "analytics"))
        if gsc == "MEASURED":
            self.mark("1.2", "MEASURED", "Search Console is connected. This pass does not restate its rows as a new causal analysis.")
            self.mark("22.1", "MEASURED", "Search Console rows may be stored. Clicks were not recomputed, and a missing row was not shown as zero.")
            self.mark("22.10", "MEASURED", "Search Console data is subject to delay, anonymization, and aggregation.")
        else:
            self.mark("1.2", "DATA_UNAVAILABLE", "Organic performance data is not connected. The gap is not a traffic failure and not a zero.")
            for subchapter_id in ("22.1", "22.2", "22.3", "22.4", "22.5", "22.6", "22.7", "22.10"):
                self.mark(subchapter_id, "DATA_UNAVAILABLE", "Search Console is not connected. No clicks, impressions, or positions were invented.")
        if ga4 == "MEASURED":
            self.mark("22.8", "MEASURED", "Analytics is connected. Sessions were not treated as revenue.")
            self.mark("22.9", "NOT_TESTED", "Revenue was not measured from key events.")
        else:
            self.mark("22.8", "DATA_UNAVAILABLE", "Analytics is not connected. No sessions were shown as zero.")
            self.mark("22.9", "DATA_UNAVAILABLE", "Revenue attribution is unavailable.")
        if _backlinks_present(self.report):
            self.mark("20.1", "MEASURED", "A backlink inventory was stored. Provider metrics were not renamed as Google metrics.")
        else:
            for subchapter_id in ("20.1", "20.2", "20.3", "20.4", "20.5", "20.6", "20.7", "20.9"):
                self.mark(subchapter_id, "DATA_UNAVAILABLE", "No authorized backlink inventory was stored. Links were not invented.")
            self.mark("20.8", "NOT_APPLICABLE", "Disavow was not recommended. There is no evidence of manipulation in this pass.")
        competitors = _competitor_count(self.report)
        if competitors:
            self.mark("23.1", "MEASURED", "A stored competitor record exists. It was not revalidated as a set of search competitors.")
            self.mark("23.9", "MEASURED", "Competitor coverage is limited to the stored record.")
        else:
            for number in range(1, 10):
                self.mark(f"23.{number}", "DATA_UNAVAILABLE", "No verified search-competitor evidence was stored.")
        for number in range(1, 10):
            if f"21.{number}" not in self.sub_status:
                self.mark(f"21.{number}", "DATA_UNAVAILABLE", "No query inventory was mapped. Search volume was not invented.")
        for number in range(1, 9):
            self.mark(f"25.{number}", "NOT_TESTED", "No approved migration baseline was stored.")
        for number in range(1, 9):
            self.mark(f"26.{number}", "NOT_TESTED", "No governance control was inspected. A missing control was not invented as a defect.")
        self.mark("2.7", "MEASURED", f"Search Console {gsc}. Analytics {ga4}. Backlinks {'stored' if _backlinks_present(self.report) else 'not stored'}.")

    def _assurance_chapters(self) -> None:
        self.mark("27.1", "MEASURED", "Root causes are labeled plausible or unknown. None was confirmed from a template map.")
        self.mark("27.2", "MEASURED", "Fixes stay proposals until a person approves them.")
        self.mark("27.3", "MEASURED", "Implementation notes name a stack only when the crawl identified it. Otherwise they stay illustrative.")
        self.mark("27.4", "MEASURED", "Expected behavior is the rule's expected condition. It has not been observed after a fix.")
        self.mark("27.5", "MEASURED", "Acceptance checks are written. They were not executed.")
        self.mark("27.6", "MEASURED", "No production change was approved or deployed by this assessment.")
        self.mark("27.7", "MEASURED", "Effort labels are planning labels, not measured hours.")
        self.mark("27.8", "MEASURED", "Every published finding is open and NOT_VERIFIABLE.")
        self.mark("28.1", "MEASURED", "Critical items are the published critical findings, if any.")
        self.mark("28.2", "MEASURED", "The 7-day window contains high-severity findings.")
        self.mark("28.3", "MEASURED", "The 30-day window contains medium-severity findings.")
        self.mark("28.4", "MEASURED", "The 60-day window contains low-severity findings.")
        self.mark("28.5", "MEASURED", "The 90-day window contains diagnostics and observations.")
        self.mark("28.6", "MEASURED", "Owners are roles, not named people.")
        self.mark("28.7", "MEASURED", "The verification checkpoint is a fresh crawl of the affected URLs.")
        self.mark("28.8", "MEASURED", "Unresolved findings remain open.")
        self.mark("28.9", "NOT_TESTED", "The next audit date was not scheduled by this module.")

    def _chapters(self, findings: list[EnterpriseFinding]) -> list[ChapterCoverage]:
        by_chapter: dict[int, list[str]] = {}
        for finding in findings:
            by_chapter.setdefault(finding.chapter, []).append(finding.finding_id)
        rows = []
        for chapter in CHAPTERS:
            subs = []
            for sub in chapter.subchapters:
                status, note = self.sub_status.get(sub.subchapter_id, ("NOT_TESTED", "No deterministic check is registered for this subchapter."))
                subs.append(SubchapterCoverage(subchapter_id=sub.subchapter_id, title=sub.title, status=status, note=note))
            status = _rollup_status(subs)
            summary = _chapter_summary(status, chapter.title)
            rows.append(ChapterCoverage(
                chapter=chapter.number,
                title=chapter.title,
                part=chapter.part,
                status=status,
                summary=summary,
                finding_ids=by_chapter.get(chapter.number, []),
                subchapters=subs,
                working=self.working.get(chapter.number, []),
                limitations=[sub.note for sub in subs if sub.status in {"NOT_TESTED", "DATA_UNAVAILABLE"}],
            ))
        return rows

    def _coverage(self) -> CoverageStatement:
        if self.crawled is None:
            statement = "No crawled URL inventory was stored. Checks that need it were not executed."
            known = False
        elif self.discovered and self.discovered > self.crawled:
            statement = (
                f"Checked {self.crawled} of {self.discovered} discovered URLs. "
                "This is a sample. It is not a complete site audit."
            )
            known = True
        elif not self.discovered:
            statement = (
                f"Checked {self.crawled} URLs. The full-site denominator was not discovered, "
                "so coverage is limited to this inventory."
            )
            known = False
        else:
            statement = (
                f"Checked {self.crawled} URLs and discovery reported the same count. "
                "That is the fetched inventory, not proof that every public URL was found."
            )
            known = True
        gsc = _channel(_get(_get(self.report, "google_performance"), "search_console"))
        ga4 = _channel(_get(_get(self.report, "google_performance"), "analytics"))
        return CoverageStatement(
            urls_discovered=self.discovered,
            urls_requested=self.crawled,
            urls_crawled=self.crawled,
            urls_rendered=self.rendered or None,
            discovered_denominator_known=known,
            sampling_status=self.sampling_status,
            statement=statement,
            integrations=[
                IntegrationStatus(name="Search Console", status=gsc, note="Disconnected data is not shown as zero."),
                IntegrationStatus(name="Analytics", status=ga4, note="Sessions are not revenue."),
                IntegrationStatus(
                    name="Backlinks",
                    status="STORED" if _backlinks_present(self.report) else "NOT_CONNECTED",
                    note="No links were invented.",
                ),
            ],
        )

    def _agents(self, findings: list[EnterpriseFinding], ai_results: dict[str, SEOAgentResult] | None = None) -> list[SEOAgentResult]:
        by_rule: dict[str, list[EnterpriseFinding]] = {}
        for finding in findings:
            by_rule.setdefault(finding.rule_id, []).append(finding)
        results = []
        ai_results = ai_results or {}
        for agent in AGENT_CATALOG:
            if agent.agent_id in ai_results:
                result = ai_results[agent.agent_id]
                owned = by_rule.get(agent.agent_id, [])
                results.append(result.model_copy(update={
                    "finding_ids": [finding.finding_id for finding in owned],
                    "evidence_ids": sorted({evidence_id for finding in owned for evidence_id in finding.evidence_ids}),
                }))
                continue
            rule_ids = _AGENT_RULES.get(agent.agent_id, set())
            owned = [finding for rule_id in rule_ids for finding in by_rule.get(rule_id, [])]
            status, error, note, limits = _agent_outcome(agent.agent_id, self, owned)
            if agent.agent_id in {
                "seo.evidence_adjudicator.v1",
                "seo.root_cause.v1",
                "seo.remediation_engineer.v1",
                "seo.regression_tests.v1",
                "seo.roadmap.v1",
                "seo.coverage_scoring.v1",
                "seo.report_editor.v1",
                "seo.fix_verification.v1",
                "seo.standards_policy.v1",
            }:
                owned = findings
            results.append(SEOAgentResult(
                agent_id=agent.agent_id,
                agent_version=agent.version,
                status=status,
                finding_ids=[finding.finding_id for finding in owned],
                evidence_ids=sorted({evidence_id for finding in owned for evidence_id in finding.evidence_ids}),
                coverage_note=note,
                limitations=limits,
                error_code=error,
            ))
        return results


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_url_list(pages: list[Any]) -> list[str]:
    urls = []
    for page in pages:
        url = _get(page, "url")
        if isinstance(url, str) and url not in urls:
            urls.append(url)
    return urls


def _redirect_urls(report: Any) -> list[str]:
    urls = []
    variants = _get(report, "host_variants") or {}
    if isinstance(variants, dict):
        for item in variants.values():
            url = _url_of(item)
            if url:
                urls.append(url)
    return urls


def _normalization_variants(urls: list[str]) -> list[str]:
    groups: dict[tuple[str, str], list[str]] = {}
    for url in urls:
        parts = urlsplit(url)
        path = parts.path or "/"
        key = (parts.netloc.lower(), path.rstrip("/").lower() or "/")
        groups.setdefault(key, [])
        if url not in groups[key]:
            groups[key].append(url)
    variants = []
    for grouped in groups.values():
        if len(grouped) > 1:
            variants.extend(grouped)
    return variants


def _has_session_parameter(url: str) -> bool:
    query = parse_qs(urlsplit(url).query)
    return any(key.lower() in _SESSION_KEYS for key in query)


def _channel(node: Any) -> str:
    if node is None:
        return "NOT_CONNECTED"
    return str(_get(node, "state") or "NOT_CONNECTED")


def _backlinks_present(report: Any) -> bool:
    authority = _get(report, "external_authority")
    if not authority:
        return False
    for key in ("backlinks", "referring_domains", "links"):
        if _as_list(_get(authority, key)):
            return True
    return False


def _competitor_count(report: Any) -> int:
    matrix = _get(report, "competitor_seo_parity")
    competitors = _as_list(_get(matrix, "competitors"))
    return sum(1 for item in competitors if not _get(item, "is_target"))


def _scores(report: Any) -> list[ScoreDisclosure]:
    scores = _get(report, "scores")
    categories = _get(scores, "category_scores") or {}
    version = _get(report, "scoring_rubric_version")
    version_text = str(version) if version else None
    rows = []
    if isinstance(categories, dict):
        for key, label in (("TECHNICAL_SEO", "Technical SEO"), ("ON_PAGE_SEO", "On-page SEO"), ("CONTENT", "Content")):
            row = categories.get(key)
            if row is None:
                continue
            status = str(_get(row, "status") or "").upper()
            raw = _get(row, "score")
            if status in {"NOT_MEASURED", "NOT_TESTED", "NOT_APPLICABLE"} or raw is None:
                rows.append(ScoreDisclosure(
                    category=label,
                    score=None,
                    methodology_version=version_text,
                    status="not_scored",
                    note="The sealed score is absent. It was not replaced with zero or one hundred.",
                ))
                continue
            try:
                number = float(raw)
            except (TypeError, ValueError):
                continue
            rows.append(ScoreDisclosure(
                category=label,
                score=number,
                methodology_version=version_text,
                status="sealed",
                note="Sealed category score from the existing scoring service. Not a grade of the 28 chapters.",
            ))
    if not rows:
        rows.append(ScoreDisclosure(
            category="SEO",
            score=None,
            methodology_version=version_text,
            status="not_scored",
            note="This module does not calculate a score. No sealed SEO category score was stored.",
        ))
    return rows


def _roadmap(findings: list[EnterpriseFinding]) -> list[RoadmapItem]:
    items = []
    for finding in findings:
        if finding.issue_type == "observation":
            window = "90d"
        else:
            window = _SEVERITY_WINDOW[finding.severity]
        items.append(RoadmapItem(
            window=window,  # type: ignore[arg-type]
            finding_id=finding.finding_id,
            title=finding.title,
            owner_role=finding.owner_role,
            estimated_effort=finding.estimated_effort,
            verification="Re-crawl the affected URLs and attach the new snapshot before changing the status.",
        ))
    return items


def _rollup_status(subs: list[SubchapterCoverage]) -> str:
    statuses = {sub.status for sub in subs}
    if statuses == {"NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    if "ISSUE_VERIFIED" in statuses:
        return "ISSUE_VERIFIED"
    executed = statuses & {"NO_ISSUE", "MEASURED", "INFERRED", "ISSUE_VERIFIED"}
    if not executed and "DATA_UNAVAILABLE" in statuses and "NOT_TESTED" not in statuses:
        return "DATA_UNAVAILABLE"
    if not executed:
        return "NOT_TESTED"
    if "NOT_TESTED" in statuses or "DATA_UNAVAILABLE" in statuses or "MEASURED" in statuses or "INFERRED" in statuses:
        return "MEASURED"
    return "NO_ISSUE"


def _chapter_summary(status: str, title: str) -> str:
    if status == "ISSUE_VERIFIED":
        return f"{title} has a validated finding in the checked set."
    if status == "NO_ISSUE":
        return f"The registered checks for {title} found no defect in the checked set. This is not a sitewide certificate."
    if status == "DATA_UNAVAILABLE":
        return f"{title} needs a source that is not connected. The gap is not a failure and not a zero."
    if status == "NOT_APPLICABLE":
        return f"{title} does not apply to the observed site."
    if status == "NOT_TESTED":
        return f"{title} was not executed."
    return f"{title} has measured notes. Untested subchapters are not passes."


def _drop_contradictions(published: list[EnterpriseFinding], rejected: list[RejectedFinding]) -> list[EnterpriseFinding]:
    """Drop a finding that cannot be true on a URL that already has the opposing observation."""
    pairs = (
        ("seo.title.missing", "seo.title.duplicate"),
        ("seo.title.missing", "seo.title.length"),
        ("seo.heading.missing_h1", "seo.heading.multiple_h1"),
        ("seo.canonical.missing", "seo.canonical.conflict"),
    )
    rank = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    by_url: dict[str, dict[str, list[EnterpriseFinding]]] = {}
    for finding in published:
        for url in finding.affected_urls:
            by_url.setdefault(url, {}).setdefault(finding.rule_id, []).append(finding)
    drop: set[str] = set()
    for url, rules in by_url.items():
        for left, right in pairs:
            if left not in rules or right not in rules:
                continue
            loser = right if rank[rules[left][0].severity] >= rank[rules[right][0].severity] else left
            winner = left if loser == right else right
            for finding in rules[loser]:
                if finding.finding_id in drop:
                    continue
                drop.add(finding.finding_id)
                rejected.append(RejectedFinding(
                    rule_id=finding.rule_id,
                    title=finding.title,
                    reason=f"Contradicts {winner} on {url}.",
                ))
    return [finding for finding in published if finding.finding_id not in drop]


def _remediation(rule_id: str, stack: str | None) -> tuple[list[str], list[str], str, list[str], str, str]:
    stack_line = (
        f"The crawl identified a {stack} environment. Inspect the template that renders the affected URL. "
        "No repository path was inspected, so none is named."
        if stack
        else "The implementation environment was not identified. Inspect the template or configuration that rendered the affected URL."
    )
    steps = [
        "Confirm the affected URL still shows the recorded condition on a fresh crawl.",
        stack_line,
        "Inspect the template, route, or configuration that produced the recorded condition. No source file was named because none was inspected.",
        "This note is not a patch. No replacement copy and no configuration diff were generated.",
        "A later verification crawl should store a new snapshot before anyone changes the finding status.",
    ]
    code: list[str] = []
    tests = [
        "The affected URL returns the intended final status.",
        "The recorded condition is gone on a fresh snapshot.",
        "A related template does not gain a duplicate title, a redirect loop, or an accidental noindex.",
        "The finding stays open until that snapshot is stored.",
    ]
    owner = "engineering"
    effort = "template change"
    if rule_id.startswith("seo.content") or rule_id.startswith("seo.title") or rule_id.startswith("seo.meta") or rule_id.startswith("seo.heading"):
        owner = "content"
        effort = "content edit"
    if rule_id.startswith("seo.security") or rule_id.startswith("seo.http") or rule_id.startswith("seo.robots"):
        owner = "engineering"
        effort = "configuration change"
    risk = "A broad template edit can change pages that were not in the sample. Review a page of each affected template before deployment."
    return steps, code, risk, tests, owner, effort


_IMPACT = {
    "seo.canonical.missing": "Search engines may choose a URL the business did not declare. No traffic or ranking loss is estimated.",
    "seo.canonical.conflict": "Conflicting canonical signals can consolidate indexing toward a different URL. The impact depends on the other indexing signals. No traffic figure is estimated.",
    "seo.index.noindex": "A noindex directive can keep the URL out of an index if the crawler honors it. The crawl does not prove the current index state.",
    "seo.robots.disallow_all": "A full disallow can stop crawling. It is not proof that indexed URLs were removed, and it is not a traffic estimate.",
    "seo.title.missing": "The result link can be assembled from other text. No click or ranking change is estimated.",
    "seo.http.5xx": "A server error means the fetched URL did not return a page. No revenue impact is estimated.",
    "seo.http.4xx": "The fetched URL did not return a successful page. No ranking loss is estimated.",
}

_TITLES = {
    "seo.robots.unavailable": "robots.txt was not available",
    "seo.robots.disallow_all": "robots.txt disallows the whole site",
    "seo.robots.syntax": "robots.txt has a syntax problem",
    "seo.robots.conflict": "robots.txt allow and disallow conflict",
    "seo.title.missing": "Missing or empty HTML title",
    "seo.title.duplicate": "Duplicate titles in the checked pages",
    "seo.title.length": "Title length is outside the diagnostic band",
    "seo.meta.missing": "Missing meta description",
    "seo.meta.duplicate": "Duplicate meta descriptions in the checked pages",
    "seo.heading.missing_h1": "Missing H1",
    "seo.heading.multiple_h1": "Multiple H1 elements observed",
    "seo.heading.hierarchy": "Heading level is skipped",
    "seo.http.4xx": "Fetched URLs return a client error",
    "seo.http.5xx": "Fetched URLs return a server error",
    "seo.http.loop": "Redirect loop",
    "seo.http.chain": "Redirect chain is longer than one hop",
    "seo.http.broken_link": "Broken internal link destination",
    "seo.http.https": "Fetched URL is not HTTPS",
    "seo.canonical.missing": "Canonical URL is missing",
    "seo.canonical.conflict": "Canonical signals conflict",
    "seo.index.noindex": "Noindex directive on a fetched URL",
    "seo.index.soft404": "Soft 404 flag on a fetched URL",
    "seo.sitemap.missing": "XML sitemap was not discovered",
    "seo.sitemap.ineligible": "Sitemap lists a non-successful URL",
    "seo.graph.orphan": "Sitemap URL was not linked in the measured crawl",
    "seo.graph.depth": "URL is deep in the measured crawl",
    "seo.url.variant": "URL spelling variants were fetched",
    "seo.url.session": "URL contains a session parameter",
    "seo.render.parity": "Raw HTML and rendered DOM disagree",
    "seo.hreflang.invalid": "Hreflang alternates are inconsistent",
    "seo.image.alt": "Image is missing alt text",
    "seo.image.dimensions": "Image is missing dimensions",
    "seo.https.mixed": "Mixed content resource",
    "seo.schema.error": "Structured data error",
    "seo.security.header": "Security header was not observed",
    "seo.cwv.lcp": "Field LCP is above the threshold",
    "seo.cwv.inp": "Field INP is above the threshold",
    "seo.cwv.cls": "Field CLS is above the threshold",
    "seo.mobile.viewport": "Viewport element is missing",
    "seo.content.short_text": "Extracted text is very short",
    "seo.link.generic_anchor": "Generic anchor text",
}

_CATEGORIES = {
    3: "crawlability",
    4: "indexability",
    5: "http",
    6: "architecture",
    7: "sitemaps",
    8: "rendering",
    9: "international",
    10: "titles",
    11: "snippets",
    12: "headings",
    13: "content",
    14: "media",
    15: "internal_links",
    16: "structured_data",
    18: "performance",
    19: "mobile",
    24: "security",
}

# Map each allowlisted expression to the fact flag its wrapper reads.
_FACT_KEY = {
    "title_element_missing_or_empty": "title_missing",
    "title_duplicated_in_sample": "title_duplicated",
    "title_length_outside_diagnostic_band": "title_length_diagnostic",
    "meta_description_missing": "meta_missing",
    "meta_description_duplicated": "meta_duplicated",
    "meta_length_outside_diagnostic_band": "meta_length_diagnostic",
    "h1_missing": "h1_missing",
    "multiple_h1_observed": "multiple_h1",
    "heading_hierarchy_skip": "heading_hierarchy",
    "http_4xx_observed": "http_4xx",
    "http_5xx_observed": "http_5xx",
    "redirect_loop_observed": "redirect_loop",
    "redirect_chain_observed": "redirect_chain",
    "temporary_redirect_observed": "temporary_redirect",
    "broken_internal_link_observed": "broken_internal",
    "hostname_https_inconsistent": "https_inconsistent",
    "canonical_missing": "canonical_missing",
    "canonical_conflict": "canonical_conflict",
    "noindex_observed": "noindex",
    "soft_404_observed": "soft_404",
    "robots_unavailable": "robots_unavailable",
    "robots_disallow_all": "robots_disallow_all",
    "robots_syntax_error": "robots_syntax",
    "robots_rule_conflict": "robots_conflict",
    "sitemap_not_discovered": "sitemap_missing",
    "sitemap_url_not_eligible": "sitemap_ineligible",
    "orphan_candidate_in_scope": "orphan_candidate",
    "click_depth_high": "click_depth_high",
    "url_normalization_variant": "url_variant",
    "session_parameter_observed": "session_parameter",
    "render_parity_failed": "render_parity",
    "hreflang_invalid": "hreflang_invalid",
    "missing_alt_observed": "missing_alt",
    "image_dimensions_missing": "image_dimensions",
    "mixed_content_observed": "mixed_content",
    "schema_error_observed": "schema_error",
    "security_header_absent": "security_header_absent",
    "field_lcp_above_threshold": "field_lcp",
    "field_inp_above_threshold": "field_inp",
    "field_cls_above_threshold": "field_cls",
    "viewport_missing": "viewport_missing",
    "short_extracted_text": "short_text",
    "generic_anchor_observed": "generic_anchor",
}

_AGENT_RULES = {
    "seo.crawlability.v1": {"seo.robots.unavailable", "seo.robots.disallow_all", "seo.robots.syntax", "seo.robots.conflict"},
    "seo.indexability.v1": {"seo.canonical.missing", "seo.canonical.conflict", "seo.index.noindex"},
    "seo.http_redirects.v1": {"seo.http.4xx", "seo.http.5xx", "seo.http.loop", "seo.http.chain", "seo.http.broken_link", "seo.http.https", "seo.index.soft404"},
    "seo.sitemaps.v1": {"seo.sitemap.missing", "seo.sitemap.ineligible"},
    "seo.site_architecture.v1": {"seo.url.variant", "seo.url.session", "seo.graph.depth"},
    "seo.rendering_js.v1": {"seo.render.parity"},
    "seo.international.v1": {"seo.hreflang.invalid"},
    "seo.performance.v1": {"seo.cwv.lcp", "seo.cwv.inp", "seo.cwv.cls"},
    "seo.mobile_parity.v1": {"seo.mobile.viewport"},
    "seo.https_security.v1": {"seo.security.header", "seo.https.mixed"},
    "seo.crawl_graph.v1": {"seo.graph.orphan", "seo.graph.depth"},
    "seo.title_tags.v1": {"seo.title.missing", "seo.title.duplicate", "seo.title.length"},
    "seo.meta_descriptions.v1": {"seo.meta.missing", "seo.meta.duplicate"},
    "seo.headings_semantics.v1": {"seo.heading.missing_h1", "seo.heading.multiple_h1", "seo.heading.hierarchy"},
    "seo.content_quality.v1": {"seo.content.short_text"},
    "seo.image_media.v1": {"seo.image.alt", "seo.image.dimensions"},
    "seo.internal_links.v1": {"seo.link.generic_anchor", "seo.graph.orphan", "seo.http.broken_link"},
    "seo.structured_data.v1": {"seo.schema.error"},
}


def _agent_outcome(agent_id: str, builder: _Builder, owned: list[EnterpriseFinding]) -> tuple[str, str | None, str, list[str]]:
    from app.seo.enterprise.taxonomy import CHAPTER_BY_NUMBER

    gsc = _channel(_get(_get(builder.report, "google_performance"), "search_console"))
    ga4 = _channel(_get(_get(builder.report, "google_performance"), "analytics"))
    gated = {
        "seo.migration.v1": (False, "NO_BASELINE", "No approved migration baseline was stored."),
        "seo.keyword_mapping.v1": (False, "DATA_UNAVAILABLE", "No query inventory was stored. Search volume was not invented."),
        "seo.search_console.v1": (gsc == "MEASURED", "DATA_UNAVAILABLE", "Search Console is not connected."),
        "seo.backlinks.v1": (_backlinks_present(builder.report), "DATA_UNAVAILABLE", "No authorized backlink inventory was stored."),
        "seo.competitor_benchmark.v1": (_competitor_count(builder.report) > 0, "DATA_UNAVAILABLE", "No competitor evidence was stored."),
        "seo.organic_analytics.v1": (ga4 == "MEASURED", "DATA_UNAVAILABLE", "Analytics is not connected."),
        "seo.historical_trends.v1": (False, "NO_BASELINE", "No historical snapshot was supplied for comparison."),
    }
    if agent_id in gated:
        open_gate, code, note = gated[agent_id]
        if not open_gate:
            return "unavailable", code, note, ["Missing source data was not turned into a negative finding."]
        return "partial", None, "The source is connected. This pass did not recalculate causality or revenue.", [
            "Connected data was not rewritten as a new score.",
        ]
    if agent_id == "seo.fix_verification.v1":
        return "completed", None, "No post-fix crawl was supplied. Every finding stays NOT_VERIFIABLE.", [
            "A deployment would not close these findings.",
        ]
    if agent_id == "seo.report_editor.v1":
        return "completed", None, "Preliminary report assembled from validated records.", [
            "The report is preliminary until a fresh crawl verifies fixes.",
        ]
    if agent_id == "seo.coverage_scoring.v1":
        return "completed", None, "Coverage is reported separately from any sealed category score.", [
            "Untested checks were not counted as passes.",
        ]
    if agent_id == "seo.content_quality.v1":
        if not builder.pages:
            return "unavailable", "NOT_TESTED", "Page text was not stored.", ["Editorial judgment was not run."]
        return "partial", None, "Only measured text properties were recorded. A model did not judge quality.", [
            "Word count was not treated as quality.",
        ]
    if agent_id == "seo.rendering_js.v1" and builder.bundle.render_checked == 0:
        return "unavailable", "NOT_TESTED", "No paired raw and rendered snapshots were stored.", []
    if agent_id == "seo.performance.v1" and not any(_get(_get(page, "field_performance"), "has_field_data") for page in builder.pages):
        return "unavailable", "NOT_TESTED", "Field Core Web Vitals were not collected.", ["TTFB was not converted into LCP."]
    agent = AGENT_BY_ID[agent_id]
    if agent.group != "assurance":
        statuses = [
            builder.sub_status.get(sub.subchapter_id, ("NOT_TESTED", ""))[0]
            for number in agent.chapters
            for sub in CHAPTER_BY_NUMBER[number].subchapters
        ]
        if statuses and all(status == "NOT_APPLICABLE" for status in statuses):
            return "completed", None, "The specialist does not apply to the observed site.", []
        if statuses and all(status == "NOT_TESTED" for status in statuses):
            return "unavailable", "NOT_TESTED", "The source for this specialist was not stored.", [
                "A missing source was not turned into a defect.",
            ]
        if statuses and all(status == "DATA_UNAVAILABLE" for status in statuses):
            return "unavailable", "DATA_UNAVAILABLE", "The source is not connected.", [
                "Missing data was not scored as a failure.",
            ]
    if owned:
        return "completed", None, f"{len(owned)} finding(s) from stored evidence.", []
    return "completed", None, "The registered check ran, or the source was inspected and no defect was published.", [
        "A completed specialist with no finding is not a sitewide pass.",
    ]


def build_enterprise_seo(report: Any, ai_runner: Any = None) -> EnterpriseSeoAssessment:
    """Return the enterprise assessment for a sealed report or a plain mapping.

    ai_runner, when supplied, receives the versioned system prompt. The default
    runner does not call a model and does not invent a judgment.
    """
    return _Builder(report, ai_runner=ai_runner).finish()
