"""Phase 10.2: Website Change Detection Engine.

Detects 12 categories of website changes across consecutive crawls:
- New pages
- Deleted pages
- Changed metadata
- Changed headings
- Changed content
- Changed schema
- Broken links
- Redirect changes
- New scripts
- Changed page templates
- Performance regressions
- Changed robots directives
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from app.monitoring.models import (
    PageChangeRecord,
    WebsiteChangeReport,
    WebsiteChangeType,
    _utcnow,
)


class WebsiteChangeDetector:
    """Compares baseline and current crawl snapshots to identify structural, technical, and content shifts."""

    def __init__(self, performance_regression_threshold: float = 0.25):
        self.perf_threshold = performance_regression_threshold

    def detect_changes(
        self,
        domain: str,
        baseline_crawl_id: str,
        current_crawl_id: str,
        baseline_pages: dict[str, dict[str, Any]],
        current_pages: dict[str, dict[str, Any]],
        baseline_robots_txt: Optional[str] = None,
        current_robots_txt: Optional[str] = None,
    ) -> WebsiteChangeReport:
        baseline_urls = set(baseline_pages.keys())
        current_urls = set(current_pages.keys())

        new_urls = sorted(list(current_urls - baseline_urls))
        deleted_urls = sorted(list(baseline_urls - current_urls))
        common_urls = sorted(list(baseline_urls & current_urls))

        modified_pages: list[PageChangeRecord] = []
        changes_by_type: dict[str, int] = {ct.value: 0 for ct in WebsiteChangeType}
        changes_by_type[WebsiteChangeType.NEW_PAGES.value] = len(new_urls)
        changes_by_type[WebsiteChangeType.DELETED_PAGES.value] = len(deleted_urls)

        # Check global robots.txt change
        robots_txt_changed = False
        if baseline_robots_txt is not None and current_robots_txt is not None:
            if baseline_robots_txt.strip() != current_robots_txt.strip():
                robots_txt_changed = True
                changes_by_type[WebsiteChangeType.CHANGED_ROBOTS_DIRECTIVES.value] += 1

        for url in common_urls:
            b_page = baseline_pages[url]
            c_page = current_pages[url]
            detected_types: list[WebsiteChangeType] = []
            before_snippet: dict[str, Any] = {}
            after_snippet: dict[str, Any] = {}
            severity = "INFO"

            # 1. Metadata changes
            b_meta = b_page.get("metadata", {})
            c_meta = c_page.get("metadata", {})
            meta_diff = self._diff_dict(b_meta, c_meta)
            if meta_diff:
                detected_types.append(WebsiteChangeType.CHANGED_METADATA)
                changes_by_type[WebsiteChangeType.CHANGED_METADATA.value] += 1
                before_snippet["metadata"] = meta_diff["before"]
                after_snippet["metadata"] = meta_diff["after"]

            # 2. Heading changes
            b_headings = b_page.get("headings", {})
            c_headings = c_page.get("headings", {})
            if b_headings != c_headings:
                detected_types.append(WebsiteChangeType.CHANGED_HEADINGS)
                changes_by_type[WebsiteChangeType.CHANGED_HEADINGS.value] += 1
                before_snippet["headings"] = b_headings
                after_snippet["headings"] = c_headings

            # 3. Content changes
            b_text = b_page.get("content_text", "")
            c_text = c_page.get("content_text", "")
            b_hash = b_page.get("content_hash") or hashlib.md5(b_text.encode("utf-8")).hexdigest()
            c_hash = c_page.get("content_hash") or hashlib.md5(c_text.encode("utf-8")).hexdigest()
            if b_hash != c_hash:
                detected_types.append(WebsiteChangeType.CHANGED_CONTENT)
                changes_by_type[WebsiteChangeType.CHANGED_CONTENT.value] += 1
                before_snippet["content_length"] = len(b_text)
                after_snippet["content_length"] = len(c_text)

            # 4. Schema changes
            b_schema = b_page.get("schema", [])
            c_schema = c_page.get("schema", [])
            if b_schema != c_schema:
                detected_types.append(WebsiteChangeType.CHANGED_SCHEMA)
                changes_by_type[WebsiteChangeType.CHANGED_SCHEMA.value] += 1
                before_snippet["schema_count"] = len(b_schema)
                after_snippet["schema_count"] = len(c_schema)

            # 5. Broken links
            b_broken = [lk for lk in b_page.get("links", []) if lk.get("status", 200) >= 400]
            c_broken = [lk for lk in c_page.get("links", []) if lk.get("status", 200) >= 400]
            if len(c_broken) > len(b_broken) or (c_broken and not b_broken):
                detected_types.append(WebsiteChangeType.BROKEN_LINKS)
                changes_by_type[WebsiteChangeType.BROKEN_LINKS.value] += 1
                before_snippet["broken_links"] = len(b_broken)
                after_snippet["broken_links"] = len(c_broken)
                severity = "WARNING" if len(c_broken) < 5 else "CRITICAL"

            # 6. Redirect changes
            b_redir = b_page.get("redirect_url")
            c_redir = c_page.get("redirect_url")
            b_code = b_page.get("status_code", 200)
            c_code = c_page.get("status_code", 200)
            if b_redir != c_redir or (c_code in (301, 302, 307, 308) and b_code == 200):
                detected_types.append(WebsiteChangeType.REDIRECT_CHANGES)
                changes_by_type[WebsiteChangeType.REDIRECT_CHANGES.value] += 1
                before_snippet["redirect"] = {"url": b_redir, "code": b_code}
                after_snippet["redirect"] = {"url": c_redir, "code": c_code}

            # 7. New scripts
            b_scripts = set(b_page.get("scripts", []))
            c_scripts = set(c_page.get("scripts", []))
            if b_scripts != c_scripts:
                detected_types.append(WebsiteChangeType.NEW_SCRIPTS)
                changes_by_type[WebsiteChangeType.NEW_SCRIPTS.value] += 1
                before_snippet["scripts"] = sorted(list(b_scripts))
                after_snippet["scripts"] = sorted(list(c_scripts))

            # 8. Template changes
            b_template = b_page.get("template_fingerprint")
            c_template = c_page.get("template_fingerprint")
            if b_template and c_template and b_template != c_template:
                detected_types.append(WebsiteChangeType.CHANGED_PAGE_TEMPLATES)
                changes_by_type[WebsiteChangeType.CHANGED_PAGE_TEMPLATES.value] += 1
                before_snippet["template"] = b_template
                after_snippet["template"] = c_template

            # 9. Performance regressions
            b_perf = b_page.get("performance", {})
            c_perf = c_page.get("performance", {})
            perf_regressed = self._check_perf_regression(b_perf, c_perf)
            if perf_regressed:
                detected_types.append(WebsiteChangeType.PERFORMANCE_REGRESSIONS)
                changes_by_type[WebsiteChangeType.PERFORMANCE_REGRESSIONS.value] += 1
                before_snippet["performance"] = b_perf
                after_snippet["performance"] = c_perf
                severity = "WARNING"

            # 10. Robots directives changes
            b_rob = b_page.get("robots_directives", [])
            c_rob = c_page.get("robots_directives", [])
            if b_rob != c_rob or (robots_txt_changed and url == f"https://{domain}/"):
                detected_types.append(WebsiteChangeType.CHANGED_ROBOTS_DIRECTIVES)
                changes_by_type[WebsiteChangeType.CHANGED_ROBOTS_DIRECTIVES.value] += 1
                before_snippet["robots_directives"] = b_rob
                after_snippet["robots_directives"] = c_rob
                if "noindex" in [str(r).lower() for r in c_rob] and "noindex" not in [str(r).lower() for r in b_rob]:
                    severity = "CRITICAL"

            if detected_types:
                modified_pages.append(
                    PageChangeRecord(
                        url=url,
                        change_types=detected_types,
                        before_snippet=before_snippet,
                        after_snippet=after_snippet,
                        severity=severity,
                    )
                )

        return WebsiteChangeReport(
            domain=domain,
            baseline_crawl_id=baseline_crawl_id,
            current_crawl_id=current_crawl_id,
            total_pages_scanned=len(current_pages),
            new_pages=new_urls,
            deleted_pages=deleted_urls,
            modified_pages=modified_pages,
            changes_by_type=changes_by_type,
            generated_at=_utcnow(),
        )

    @staticmethod
    def _diff_dict(d1: dict[str, Any], d2: dict[str, Any]) -> Optional[dict[str, Any]]:
        keys = set(d1.keys()) | set(d2.keys())
        diff_before = {}
        diff_after = {}
        for k in keys:
            v1 = d1.get(k)
            v2 = d2.get(k)
            if v1 != v2:
                diff_before[k] = v1
                diff_after[k] = v2
        if diff_before or diff_after:
            return {"before": diff_before, "after": diff_after}
        return None

    def _check_perf_regression(self, b_perf: dict[str, Any], c_perf: dict[str, Any]) -> bool:
        if not b_perf or not c_perf:
            return False
        # Check load_time_ms, ttfb_ms, page_size_kb
        for metric in ("load_time_ms", "ttfb_ms", "page_size_kb"):
            b_val = b_perf.get(metric)
            c_val = c_perf.get(metric)
            if b_val and c_val and b_val > 0:
                rel_increase = (c_val - b_val) / float(b_val)
                if rel_increase >= self.perf_threshold:
                    return True
        return False
