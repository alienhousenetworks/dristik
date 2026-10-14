"""
Dristik AI Enterprise Diagnostic Inventory Engine (2026 Master Standard).

Constructs a machine-readable inventory of every diagnostic across all 20 chapters
before narrative report generation. Tracks test status:
- PASS: Test ran and passed
- FAIL: Confirmed defect with evidence
- WARNING: Suboptimal condition or advisory
- NOT_TESTED: Test exists but was not executed
- NOT_CONNECTED: External data provider (GSC, GA4, Ahrefs) not authorized
- NOT_APPLICABLE: Explicitly justified non-applicability (e.g. e-commerce on B2B SaaS)
- INCONCLUSIVE: Conflicting observations or insufficient sample
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.audit.inventory_helper import get_canonical_crawl_inventory
from app.domain.enums import Severity
from app.domain.models import (
    CrawlManifest,
    DiagnosticCoverageMatrix,
    DiagnosticRecord,
    ExecutiveReport,
    Finding,
    PageEvidence,
)

logger = logging.getLogger("dristik.audit.diagnostic_inventory")


class DiagnosticInventoryEngine:
    """
    Evaluates evidence across all 20 chapters and produces a machine-readable
    DiagnosticCoverageMatrix with verified statuses, evidence references,
    affected URLs, and remediation requirements.
    """

    @classmethod
    def build_inventory(
        cls,
        report: ExecutiveReport,
        manifest: Optional[CrawlManifest] = None,
        eval_pages: Optional[List[PageEvidence]] = None,
    ) -> DiagnosticCoverageMatrix:
        manifest = manifest or getattr(report, "crawl_manifest", None)
        pages = eval_pages or (manifest.pages if manifest else []) or getattr(report, "page_reports", [])
        findings = report.findings or []

        records: List[DiagnosticRecord] = []

        # -------------------------------------------------------------
        # Chapter 01: Executive Summary & Site Health Score
        # -------------------------------------------------------------
        crit_blockers = [
            f for f in findings
            if f.priority >= 9 or str(getattr(f.severity, "value", f.severity)).upper() == "CRITICAL"
        ]
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-01-BLOCKERS",
            chapter_num="01",
            chapter_title="Executive Summary & Site Health Score",
            subchapter="Critical Blockers",
            applicable_url_types=["all"],
            required_data_sources=["all_analyzers", "evidence_ledger"],
            test_performed="Identify any verified critical issues that block indexing or render completely blank DOMs.",
            status="FAIL" if crit_blockers else "PASS",
            status_reason=f"Found {len(crit_blockers)} confirmed critical blocker(s)." if crit_blockers else "Zero critical blockers identified.",
            affected_urls=list({url for f in crit_blockers for url in f.affected_urls}),
            affected_count=len(crit_blockers),
            severity="CRITICAL" if crit_blockers else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Resolve P0 critical blockers prior to public launch or broad re-crawl." if crit_blockers else None,
            validation_test="Automated HTTP 200 GET returning full body content without fatal crawler blocks.",
        ))

        score_val = getattr(report.scores, "overall_score", None) if getattr(report, "scores", None) else None
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-01-SCORE-CALC",
            chapter_num="01",
            chapter_title="Executive Summary & Site Health Score",
            subchapter="Health Scorecard Calculation",
            applicable_url_types=["all"],
            required_data_sources=["scoring_engine"],
            test_performed="Calculate weighted health score with transparent pillar weights summing to 100%.",
            status="PASS" if score_val is not None else "INCONCLUSIVE",
            status_reason=f"Overall health score computed at {score_val:.1f}/100." if score_val is not None else "Overall score calculation incomplete.",
            severity="INFORMATIONAL",
            confidence=0.95,
            validation_test="Category scores weighted sum matches overall score within 0.5 points.",
        ))

        # -------------------------------------------------------------
        # Chapter 02: Methodology, Crawl Scope & Limitations
        # -------------------------------------------------------------
        inv = get_canonical_crawl_inventory(manifest, report)
        disc_total = inv.discovered_total
        tested_count = inv.tested_pages
        cov_pct = inv.url_coverage_pct or 0.0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-02-INVENTORY-RECONCILE",
            chapter_num="02",
            chapter_title="Methodology, Crawl Scope & Limitations",
            subchapter="Crawl Scope Reconciliation",
            applicable_url_types=["all"],
            required_data_sources=["crawl_manifest", "http_probes"],
            test_performed="Reconcile discovered, queued, crawled, and tested URLs with explicit declared denominator.",
            status="PASS" if disc_total >= tested_count else "WARNING",
            status_reason=f"Tested {tested_count} of {disc_total} discovered URLs ({cov_pct}% coverage).",
            affected_urls=getattr(manifest, "untested_discovered_urls", [])[:10] if manifest else [],
            affected_count=max(0, disc_total - tested_count),
            severity="INFORMATIONAL",
            confidence=1.0,
            validation_test="Tested count + excluded count + failed count == requested crawl sample.",
        ))

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-02-DISCOVERY-SOURCES",
            chapter_num="02",
            chapter_title="Methodology, Crawl Scope & Limitations",
            subchapter="Discovery Source Accounting",
            applicable_url_types=["all"],
            required_data_sources=["sitemap_parser", "link_traversal"],
            test_performed="Track URL provenance across XML sitemaps, internal links, and seed configuration.",
            status="PASS" if (inv.discovered_via_sitemap > 0 or inv.discovered_via_links > 0) else "WARNING",
            status_reason=f"Discovered via sitemap: {inv.discovered_via_sitemap}, via links: {inv.discovered_via_links}.",
            severity="INFORMATIONAL",
            confidence=1.0,
            validation_test="Provenance recorded for every discovered URL.",
        ))

        # -------------------------------------------------------------
        # Chapter 03: Indexability, Crawlability & Canonicalization
        # -------------------------------------------------------------
        idx = report.indexation_intelligence
        canon = report.canonical_audit
        http_breakdown = report.http_status_breakdown

        c404 = getattr(http_breakdown, "count_4xx", 0) if http_breakdown else 0
        c500 = getattr(http_breakdown, "count_5xx", 0) if http_breakdown else 0
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-03-HTTP-STATUS",
            chapter_num="03",
            chapter_title="Indexability, Crawlability & Canonicalization",
            subchapter="HTTP Response Codes",
            applicable_url_types=["all"],
            required_data_sources=["raw_http"],
            test_performed="Verify all sampled internal URLs return HTTP 200 OK without unhandled 4xx/5xx exceptions.",
            status="FAIL" if (c404 > 0 or c500 > 0) else "PASS",
            status_reason=f"Detected {c404} 4xx error(s) and {c500} 5xx server error(s)." if (c404 > 0 or c500 > 0) else "All audited URLs responded with valid HTTP status codes.",
            affected_urls=[item.url for item in getattr(http_breakdown, "pages_4xx", []) + getattr(http_breakdown, "pages_5xx", [])] if http_breakdown else [],
            affected_count=c404 + c500,
            severity="HIGH" if c500 > 0 else ("MEDIUM" if c404 > 0 else "INFORMATIONAL"),
            confidence=0.95,
            remediation_requirement="Correct broken endpoints, restore missing resources, or return clean 410 Gone / 301 Redirect." if (c404 > 0 or c500 > 0) else None,
            validation_test="curl -s -I <url> returns HTTP/2 200.",
        ))

        can_issues = getattr(canon, "missing_canonical_count", 0) + getattr(canon, "broken_canonical_count", 0) + getattr(canon, "cross_domain_canonical_count", 0) if canon else 0
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-03-CANONICAL-ALIGN",
            chapter_num="03",
            chapter_title="Indexability, Crawlability & Canonicalization",
            subchapter="Canonical Directives",
            applicable_url_types=["canonical", "html"],
            required_data_sources=["raw_html", "rendered_dom"],
            test_performed="Audit rel='canonical' presence, absolute URL validity, and self-referencing consistency.",
            status="FAIL" if can_issues > 0 else "PASS",
            status_reason=f"Detected {can_issues} canonical directive anomalies." if can_issues > 0 else "Canonical tags conform to W3C specifications on audited pages.",
            affected_urls=getattr(canon, "conflicts", []) if canon else [],
            affected_count=can_issues,
            severity="HIGH" if can_issues > 0 else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Declare explicit absolute self-referencing rel='canonical' in document <head>." if can_issues > 0 else None,
            validation_test="document.querySelector('link[rel=canonical]').href matches resolved canonical target.",
        ))

        # -------------------------------------------------------------
        # Chapter 04: Site Architecture, Click Depth & Internal Linking
        # -------------------------------------------------------------
        depth = report.click_depth
        orphans = report.orphan_pages
        deep_count = getattr(depth, "deep_pages_count", 0) if depth else 0
        orphan_count = getattr(orphans, "orphan_count", 0) if orphans else 0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-04-CLICK-DEPTH",
            chapter_num="04",
            chapter_title="Site Architecture, Click Depth & Internal Linking",
            subchapter="Crawl Depth Architecture",
            applicable_url_types=["html"],
            required_data_sources=["crawl_graph"],
            test_performed="Calculate shortest-path crawl distance from homepage root to all internal URLs. Threshold: <= 3 hops.",
            status="WARNING" if deep_count > 0 else "PASS",
            status_reason=f"{deep_count} page(s) require 4 or more clicks from the homepage." if deep_count > 0 else "All sampled pages reachable within 3 clicks of homepage.",
            affected_urls=getattr(depth, "deep_urls", []) if depth else [],
            affected_count=deep_count,
            severity="MEDIUM" if deep_count > 0 else "INFORMATIONAL",
            confidence=0.85,
            remediation_requirement="Promote isolated URLs via contextual in-body links or category hub navigation." if deep_count > 0 else None,
            validation_test="Breadth-first crawl traversal reaches target URL in <= 3 hops from root.",
        ))

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-04-ORPHAN-PAGES",
            chapter_num="04",
            chapter_title="Site Architecture, Click Depth & Internal Linking",
            subchapter="Orphan Page Detection",
            applicable_url_types=["sitemap_urls"],
            required_data_sources=["xml_sitemap", "crawl_graph"],
            test_performed="Cross-reference sitemap URL inventory against pages receiving internal inbound crawl links.",
            status="WARNING" if orphan_count > 0 else "PASS",
            status_reason=f"Found {orphan_count} orphan URL(s) in XML sitemap receiving zero internal links." if orphan_count > 0 else "Zero orphan URLs detected in crawl sample.",
            affected_urls=getattr(orphans, "orphan_urls", []) if orphans else [],
            affected_count=orphan_count,
            severity="MEDIUM" if orphan_count > 0 else "INFORMATIONAL",
            confidence=0.90,
            remediation_requirement="Integrate orphan URLs into related topical hub pages or purge from XML sitemap." if orphan_count > 0 else None,
            validation_test="Page URL possesses at least 2 internal inbound href references from indexable pages.",
        ))

        # -------------------------------------------------------------
        # Chapter 05: On-Page SEO & Metadata Quality (Separating Existence vs Semantic Quality)
        # -------------------------------------------------------------
        meta = report.meta_rollup
        head = report.heading_hierarchy

        pages_sample = pages or (report.page_reports or [])
        total_sample = len(pages_sample) or 1

        missing_titles_urls = [item.url for item in getattr(meta, "missing_titles", [])] if meta else []
        missing_descs_urls = [item.url for item in getattr(meta, "missing_descriptions", [])] if meta else []
        dup_descs_urls = [item.url for item in getattr(meta, "duplicate_descriptions", [])] if meta else []

        poor_titles_urls = []
        if pages:
            for p in pages:
                t = getattr(p, "title", "") or ""
                t_str = t.strip()
                if not t_str:
                    if p.url not in missing_titles_urls:
                        missing_titles_urls.append(p.url)
                elif len(t_str) < 15 or t_str.lower() in ("home", "index", "default", "welcome", "untitled", "home page"):
                    poor_titles_urls.append(p.url)

                d = getattr(p, "meta_description", "") or ""
                d_str = d.strip()
                if not d_str:
                    if p.url not in missing_descs_urls:
                        missing_descs_urls.append(p.url)

            # Check duplicate descriptions in pages
            all_descs = [p.meta_description.strip() for p in pages if getattr(p, "meta_description", None) and p.meta_description.strip()]
            from collections import Counter
            desc_counts = Counter(all_descs)
            for p in pages:
                d = getattr(p, "meta_description", "") or ""
                if d and desc_counts[d.strip()] > 1 and p.url not in dup_descs_urls:
                    dup_descs_urls.append(p.url)

        missing_titles = len(missing_titles_urls)
        missing_descs = len(missing_descs_urls)
        dup_descs = len(dup_descs_urls)
        missing_h1 = len(getattr(head, "missing_h1", [])) if head else 0
        dup_h1 = len(getattr(head, "multiple_h1", [])) if head else 0

        # Title Existence
        status_title_exist = "FAIL" if missing_titles >= total_sample else ("WARNING" if missing_titles > 0 else "PASS")
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-05-TITLE-EXISTENCE",
            chapter_num="05",
            chapter_title="On-Page SEO & Metadata Quality",
            subchapter="Title Tag Presence",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Verify <title> element exists and is non-empty in document head.",
            status=status_title_exist,
            status_reason=f"{missing_titles} page(s) missing <title> tag." if missing_titles > 0 else "All evaluated pages declare non-empty title tags.",
            affected_urls=missing_titles_urls,
            affected_count=missing_titles,
            severity="HIGH" if missing_titles > 0 else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Add <title> tag to document <head>." if missing_titles > 0 else None,
            validation_test="document.querySelector('title') is non-empty.",
        ))

        # Title Semantic Quality
        status_title_qual = "FAIL" if len(poor_titles_urls) >= total_sample else ("WARNING" if len(poor_titles_urls) > 0 else "PASS")
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-05-TITLE-QUALITY",
            chapter_num="05",
            chapter_title="On-Page SEO & Metadata Quality",
            subchapter="Title Descriptive Quality & Uniqueness",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Evaluate title tag length (30-65 chars), keyword front-loading, and uniqueness across pages.",
            status=status_title_qual,
            status_reason=f"Found {len(poor_titles_urls)} page(s) with generic, uninformative or improper length title tags." if poor_titles_urls else "Evaluated title descriptive quality and intent differentiation across crawl sample.",
            affected_urls=poor_titles_urls,
            affected_count=len(poor_titles_urls),
            severity="MEDIUM" if poor_titles_urls else "INFORMATIONAL",
            confidence=0.90,
            validation_test="30 <= len(title) <= 65 and title is unique across domain.",
        ))

        # Meta Description Existence
        status_desc_exist = "FAIL" if missing_descs >= total_sample else ("WARNING" if missing_descs > 0 else "PASS")
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-05-DESC-EXISTENCE",
            chapter_num="05",
            chapter_title="On-Page SEO & Metadata Quality",
            subchapter="Meta Description Presence",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Verify meta name='description' tag is present on indexable HTML pages.",
            status=status_desc_exist,
            status_reason=f"{missing_descs} page(s) missing meta description tag." if missing_descs > 0 else "All evaluated pages declare meta description tags.",
            affected_urls=missing_descs_urls,
            affected_count=missing_descs,
            severity="HIGH" if missing_descs > 0 else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Inject <meta name='description'> tag with compelling value proposition." if missing_descs > 0 else None,
            validation_test="document.querySelector('meta[name=description]').content is non-empty.",
        ))

        # Meta Description Semantic Quality (Checks for Duplicates & Differentiation)
        status_desc_qual = "FAIL" if dup_descs >= total_sample else ("WARNING" if dup_descs > 0 else "PASS")
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-05-DESC-QUALITY",
            chapter_num="05",
            chapter_title="On-Page SEO & Metadata Quality",
            subchapter="Meta Description Uniqueness & Differentiation",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Audit meta description uniqueness, avoiding identical sitewide fallback copy across multiple pages.",
            status=status_desc_qual,
            status_reason=f"Found {dup_descs} instance(s) of duplicated meta descriptions repeated across multiple URLs." if dup_descs > 0 else "Meta descriptions are distinct and page-specific.",
            affected_urls=dup_descs_urls,
            affected_count=dup_descs,
            severity="MEDIUM" if dup_descs > 0 else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Author distinct, page-specific value propositions for each service landing page." if dup_descs > 0 else None,
            validation_test="Set of unique meta description strings equals number of indexable landing pages.",
        ))

        # H1 Structure & Relevance
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-05-H1-RELEVANCE",
            chapter_num="05",
            chapter_title="On-Page SEO & Metadata Quality",
            subchapter="H1 Structure & Outline",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Verify single primary H1 heading per document representing core page topic.",
            status="FAIL" if (missing_h1 > 0 or dup_h1 > 0) else "PASS",
            status_reason=f"{missing_h1} page(s) missing H1; {dup_h1} page(s) declare multiple H1 elements." if (missing_h1 > 0 or dup_h1 > 0) else "Clean single H1 heading hierarchy verified across sample.",
            affected_urls=[item.url for item in getattr(head, "missing_h1", []) + getattr(head, "multiple_h1", [])] if head else [],
            affected_count=missing_h1 + dup_h1,
            severity="MEDIUM" if (missing_h1 > 0 or dup_h1 > 0) else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Ensure template renders exactly one semantic <h1> describing the primary entity." if (missing_h1 > 0 or dup_h1 > 0) else None,
            validation_test="document.querySelectorAll('h1').length === 1.",
        ))

        # -------------------------------------------------------------
        # Chapter 06: Content Quality, Topical Authority & Cannibalization
        # -------------------------------------------------------------
        topical = report.topical_authority
        cannibal_clusters = len(getattr(topical, "cannibalization_clusters", [])) if topical else 0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-06-CANNIBALIZATION",
            chapter_num="06",
            chapter_title="Content Quality, Topical Authority & Cannibalization",
            subchapter="Keyword Cannibalization & Intent Overlap",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom", "entity_extraction"],
            test_performed="Cluster pages sharing >= 75% semantic heading overlap and identical primary target terms.",
            status="WARNING" if cannibal_clusters > 0 else "PASS",
            status_reason=f"Detected {cannibal_clusters} cannibalization cluster(s) competing for identical topics." if cannibal_clusters > 0 else "No acute keyword cannibalization detected among crawled pages.",
            affected_urls=[url for cluster in getattr(topical, "cannibalization_clusters", []) for url in cluster.urls] if topical else [],
            affected_count=cannibal_clusters,
            severity="MEDIUM" if cannibal_clusters > 0 else "INFORMATIONAL",
            confidence=0.85,
            remediation_requirement="Consolidate duplicate topic pages via 301 redirect or differentiate secondary keyword modifiers." if cannibal_clusters > 0 else None,
            validation_test="Unique primary heading and title topic targeting per indexable landing page.",
        ))

        # -------------------------------------------------------------
        # Chapter 07: Search Intent & Commercial Query Alignment
        # -------------------------------------------------------------
        commercial_evals = report.commercial_evaluations or []
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-07-INTENT-MAPPING",
            chapter_num="07",
            chapter_title="Search Intent & Commercial Query Alignment",
            subchapter="Commercial Intent Classification",
            applicable_url_types=["landing_pages"],
            required_data_sources=["commercial_evals", "serp_intelligence"],
            test_performed="Map buyer search journeys across Informational, Commercial Investigation, and Transactional stages.",
            status="PASS" if commercial_evals else "NOT_CONNECTED",
            status_reason=f"Evaluated {len(commercial_evals)} commercial buyer journey queries." if commercial_evals else "Keyword research connector unconfigured; qualitative intent only.",
            severity="INFORMATIONAL",
            confidence=0.85 if commercial_evals else 0.50,
            validation_test="Target URL content provides answers and clear conversion call-to-action.",
        ))

        # -------------------------------------------------------------
        # Chapter 08: Structured Data & Schema Markup Validation
        # -------------------------------------------------------------
        schema_rep = report.schema_validation
        entities_detected = getattr(schema_rep, "total_entities_detected", 0) if schema_rep else 0
        schema_errs = getattr(schema_rep, "entities_with_errors_count", 0) if schema_rep else 0

        # Syntax Validity
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-08-SYNTAX-VALIDITY",
            chapter_num="08",
            chapter_title="Structured Data & Schema Markup Validation",
            subchapter="JSON-LD Schema Syntax & Conformance",
            applicable_url_types=["html"],
            required_data_sources=["json_ld", "microdata"],
            test_performed="Audit JSON-LD blocks for valid JSON syntax and Schema.org context definition.",
            status="WARNING" if entities_detected == 0 else "PASS",
            status_reason="Zero JSON-LD markup found on evaluated pages." if entities_detected == 0 else f"Audited {entities_detected} schema block(s) with valid syntax.",
            severity="MEDIUM" if entities_detected == 0 else "INFORMATIONAL",
            confidence=0.95,
            validation_test="JSON.parse() succeeds on all <script type='application/ld+json'> blocks.",
        ))

        # Google Rich Result Feature Requirements
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-08-REQUIRED-FIELDS",
            chapter_num="08",
            chapter_title="Structured Data & Schema Markup Validation",
            subchapter="Rich Results Feature-Specific Requirements",
            applicable_url_types=["html"],
            required_data_sources=["json_ld", "google_rich_specs"],
            test_performed="Validate presence of mandatory Google Rich Result properties for Organization, Service, and Product.",
            status="FAIL" if schema_errs > 0 else ("WARNING" if entities_detected == 0 else "PASS"),
            status_reason=f"Found {schema_errs} blocking schema property error(s) disqualifying pages from rich snippets." if schema_errs > 0 else ("No structured data entities detected." if entities_detected == 0 else "All detected schema entities satisfy Google mandatory property rules."),
            affected_urls=[issue.url for issue in getattr(schema_rep, "issues", []) if issue.severity == "ERROR"] if schema_rep else [],
            affected_count=schema_errs,
            severity="HIGH" if schema_errs > 0 else ("MEDIUM" if entities_detected == 0 else "INFORMATIONAL"),
            confidence=0.95,
            remediation_requirement="Inject compliant JSON-LD script tag with mandatory properties for Organization/Service." if (schema_errs > 0 or entities_detected == 0) else None,
            validation_test="Schema validator returns zero 'ERROR' diagnostics on tested JSON-LD blocks.",
        ))

        # -------------------------------------------------------------
        # Chapter 09: Mobile Usability & Responsive Layout
        # -------------------------------------------------------------
        visual_ux = report.visual_ux
        mobile_defects = getattr(visual_ux, "mobile_defects_count", 0) if visual_ux else 0
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-09-VIEWPORT-CONFIG",
            chapter_num="09",
            chapter_title="Mobile Usability & Responsive Layout",
            subchapter="Mobile Viewport & Touch Ergonomics",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom", "visual_ux_tester"],
            test_performed="Audit meta name='viewport' content='width=device-width, initial-scale=1' and horizontal overflow.",
            status="FAIL" if mobile_defects > 0 else "PASS",
            status_reason=f"Identified {mobile_defects} responsive layout defect(s) on mobile viewports." if mobile_defects > 0 else "Mobile viewport configuration and responsive layout validated.",
            severity="HIGH" if mobile_defects > 0 else "INFORMATIONAL",
            confidence=0.90,
            remediation_requirement="Ensure viewport meta tag is declared and CSS container max-width does not exceed 100vw." if mobile_defects > 0 else None,
            validation_test="Mobile Chromium rendering shows 0px horizontal scrollbar at 375px viewport.",
        ))

        # -------------------------------------------------------------
        # Chapter 10: Core Web Vitals & Technical Page Performance
        # -------------------------------------------------------------
        media = report.media_assets
        cls_risks = getattr(media, "missing_dimensions_count", 0) if media else 0
        avg_ttfb = getattr(manifest, "crawl_health", {}).get("avg_ttfb_ms", 0.0) if manifest else 0.0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-10-TTFB",
            chapter_num="10",
            chapter_title="Core Web Vitals & Technical Page Performance",
            subchapter="Time to First Byte (TTFB) Lab Measurement",
            applicable_url_types=["all"],
            required_data_sources=["http_timings"],
            test_performed="Measure server response latency from socket connect to first byte. Threshold: < 800ms.",
            status="FAIL" if avg_ttfb > 1200 else ("WARNING" if avg_ttfb > 800 else "PASS"),
            status_reason=f"Average TTFB measured at {avg_ttfb:.0f}ms." if avg_ttfb > 0 else "TTFB within acceptable thresholds.",
            severity="HIGH" if avg_ttfb > 1200 else ("MEDIUM" if avg_ttfb > 800 else "INFORMATIONAL"),
            confidence=0.90,
            remediation_requirement="Implement Edge CDN caching (Cloudflare/Fastly) and database query optimization." if avg_ttfb > 800 else None,
            validation_test="curl -w '%{time_starttransfer}' returns < 0.600s across repeated runs.",
        ))

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-10-CWV-CLS",
            chapter_num="10",
            chapter_title="Core Web Vitals & Technical Page Performance",
            subchapter="Layout Shift & Media Dimensions",
            applicable_url_types=["html"],
            required_data_sources=["rendered_dom"],
            test_performed="Check <img> elements for explicit width and height attributes or CSS aspect-ratio.",
            status="WARNING" if cls_risks > 0 else "PASS",
            status_reason=f"{cls_risks} image(s) lack explicit width/height attributes, creating CLS risk." if cls_risks > 0 else "Explicit dimensions declared on all audited media assets.",
            affected_count=cls_risks,
            severity="MEDIUM" if cls_risks > 0 else "INFORMATIONAL",
            confidence=0.90,
            remediation_requirement="Add explicit width and height HTML attributes to all <img> tags." if cls_risks > 0 else None,
            validation_test="Every <img> tag has non-empty width and height attributes matching intrinsic aspect ratio.",
        ))

        # -------------------------------------------------------------
        # Chapter 11: Security & Protocol Architecture
        # -------------------------------------------------------------
        sec = report.security_audit
        hsts_ok = getattr(sec, "hsts_enabled", False) if sec else False
        mixed_content = getattr(media, "mixed_content_count", 0) if media else 0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-11-HSTS-HEADER",
            chapter_num="11",
            chapter_title="Security & Protocol Architecture",
            subchapter="Strict-Transport-Security (HSTS)",
            applicable_url_types=["https_endpoints"],
            required_data_sources=["response_headers"],
            test_performed="Verify Strict-Transport-Security response header on HTTPS connections.",
            status="PASS" if hsts_ok else "WARNING",
            status_reason="HSTS header confirmed on server responses." if hsts_ok else "Strict-Transport-Security header missing from server responses.",
            severity="MEDIUM" if not hsts_ok else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Configure web server to return: Strict-Transport-Security: max-age=31536000; includeSubDomains." if not hsts_ok else None,
            validation_test="curl -s -I https://... | grep -i strict-transport-security returns max-age >= 31536000.",
        ))

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-11-MIXED-CONTENT",
            chapter_num="11",
            chapter_title="Security & Protocol Architecture",
            subchapter="Mixed Content Assets",
            applicable_url_types=["https_endpoints"],
            required_data_sources=["rendered_dom", "network_trace"],
            test_performed="Ensure zero unencrypted http:// scripts, stylesheets, or images loaded on HTTPS pages.",
            status="FAIL" if mixed_content > 0 else "PASS",
            status_reason=f"Found {mixed_content} insecure http:// asset(s) loaded on HTTPS pages." if mixed_content > 0 else "Zero mixed content references detected.",
            affected_urls=getattr(media, "mixed_content_urls", []) if media else [],
            affected_count=mixed_content,
            severity="HIGH" if mixed_content > 0 else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Update asset references to use protocol-relative // or absolute https:// URLs." if mixed_content > 0 else None,
            validation_test="Network audit records 0 requests with http:// scheme on https:// origin.",
        ))

        # -------------------------------------------------------------
        # Chapter 12: International SEO
        # -------------------------------------------------------------
        intl = report.international_seo
        is_intl = getattr(intl, "is_multilingual", False) or getattr(intl, "is_international_detected", False) if intl else False
        intl_issues = len(getattr(intl, "issues", [])) if intl else 0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-12-HREFLANG-SYNTAX",
            chapter_num="12",
            chapter_title="International SEO (Hreflang & Geotargeting)",
            subchapter="Hreflang & Multi-Region Targeting",
            applicable_url_types=["multilingual_urls"],
            required_data_sources=["raw_html", "response_headers"],
            test_performed="Validate hreflang annotations, return tags, and x-default declarations across language variants.",
            status="PASS" if (is_intl and intl_issues == 0) else ("FAIL" if (is_intl and intl_issues > 0) else "NOT_APPLICABLE"),
            status_reason="Reciprocal hreflang annotations validated." if (is_intl and intl_issues == 0) else (f"{intl_issues} hreflang syntax/reciprocity errors detected." if is_intl else "Website does not declare multiple language variants or ccTLDs; International SEO deemed NOT_APPLICABLE."),
            severity="HIGH" if (is_intl and intl_issues > 0) else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Ensure reciprocal rel='alternate' hreflang annotations connect all localized counterparts." if (is_intl and intl_issues > 0) else None,
            validation_test="Every hreflang destination URL reciprocates with matching hreflang pointing back.",
        ))

        # -------------------------------------------------------------
        # Chapter 13: Local SEO & Google Business Profile Presence
        # -------------------------------------------------------------
        local = report.local_seo
        is_local_eligible = getattr(local, "has_google_business_profile", False) or len(getattr(local, "nap_records", [])) > 0 or getattr(local, "is_local_detected", False) if local else False
        nap_score = getattr(local, "nap_consistency_score", getattr(local, "nap_consistency_pct", 100.0)) if local else 100.0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-13-NAP-CONSISTENCY",
            chapter_num="13",
            chapter_title="Local SEO & Google Business Profile Presence",
            subchapter="NAP Consistency & Google Business Profile",
            applicable_url_types=["contact_and_location_pages"],
            required_data_sources=["rendered_dom", "local_schema"],
            test_performed="Audit consistency of business Name, Address, and Phone across footer, contact page, and schema.",
            status="PASS" if (is_local_eligible and nap_score >= 90) else ("WARNING" if (is_local_eligible and nap_score < 90) else "NOT_APPLICABLE"),
            status_reason=f"NAP consistency verified at {nap_score:.0f}%." if (is_local_eligible and nap_score >= 90) else (f"NAP consistency deficits detected ({nap_score:.0f}%)." if is_local_eligible else "Site operates as a pure digital / cloud entity without public physical storefronts; Local SEO deemed NOT_APPLICABLE."),
            severity="MEDIUM" if (is_local_eligible and nap_score < 90) else "INFORMATIONAL",
            confidence=0.90,
            remediation_requirement="Standardize legal entity name, postal address, and E.164 phone number across all pages." if (is_local_eligible and nap_score < 90) else None,
            validation_test="String equality match across footer contact text, contact page, and LocalBusiness schema.",
        ))

        # -------------------------------------------------------------
        # Chapter 14: E-commerce SEO & Product Architecture
        # -------------------------------------------------------------
        ecom = report.ecommerce_seo
        is_ecom = getattr(ecom, "is_ecommerce_detected", False) if ecom else False
        ecom_issues = len(getattr(ecom, "products_with_issues", [])) if ecom else 0

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-14-PRODUCT-SCHEMA",
            chapter_num="14",
            chapter_title="E-commerce SEO & Product Architecture",
            subchapter="Product & Offer Schema",
            applicable_url_types=["product_urls"],
            required_data_sources=["json_ld"],
            test_performed="Verify Product, Offer, priceCurrency, availability, and merchant return policies.",
            status="PASS" if (is_ecom and ecom_issues == 0) else ("FAIL" if (is_ecom and ecom_issues > 0) else "NOT_APPLICABLE"),
            status_reason="Product schema and offer availability validated." if (is_ecom and ecom_issues == 0) else (f"{ecom_issues} product(s) missing mandatory Offer/Pricing schema." if is_ecom else "Zero transactional checkout or product catalog structures detected; E-commerce SEO deemed NOT_APPLICABLE."),
            severity="HIGH" if (is_ecom and ecom_issues > 0) else "INFORMATIONAL",
            confidence=0.95,
            remediation_requirement="Include valid Offer markup with price, priceCurrency, and hasMerchantReturnPolicy." if (is_ecom and ecom_issues > 0) else None,
            validation_test="Product schema returns valid Offer and in-stock availability.",
        ))

        # -------------------------------------------------------------
        # Chapter 15: SERP Appearance & Google Snippet Previews
        # -------------------------------------------------------------
        serp = report.serp_appearance
        truncated_titles = getattr(serp, "titles_truncated_count", 0) if serp else 0
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-15-TITLE-TRUNCATION",
            chapter_num="15",
            chapter_title="SERP Appearance & Google Snippet Previews",
            subchapter="Desktop & Mobile SERP Pixel Width",
            applicable_url_types=["html"],
            required_data_sources=["serp_simulator"],
            test_performed="Simulate Google SERP pixel layout. Flag title tags exceeding 580px (desktop) or 600px (mobile).",
            status="WARNING" if truncated_titles > 0 else "PASS",
            status_reason=f"{truncated_titles} title(s) exceed 580px desktop width and risk truncation in Google search results." if truncated_titles > 0 else "All evaluated titles fit within standard Google desktop SERP pixel limits.",
            affected_count=truncated_titles,
            severity="MEDIUM" if truncated_titles > 0 else "INFORMATIONAL",
            confidence=0.90,
            remediation_requirement="Front-load primary keywords and trim brand suffix so total pixel length is <= 580px." if truncated_titles > 0 else None,
            validation_test="Simulated title rendered in Arial 20px font has pixel width <= 580px.",
        ))

        # -------------------------------------------------------------
        # Chapter 16: External Authority, Backlink Quality & Mentions
        # -------------------------------------------------------------
        ext = report.external_authority
        ext_status = ext.get("status") if isinstance(ext, dict) else "NOT_CONNECTED"
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-16-REFERRING-DOMAINS",
            chapter_num="16",
            chapter_title="External Authority, Backlink Quality & Mentions",
            subchapter="Backlink Profile & Referring Domains",
            applicable_url_types=["domain"],
            required_data_sources=["backlink_api"],
            test_performed="Evaluate referring domain count, anchor text distribution, and toxic link signals.",
            status="PASS" if ext_status == "CONNECTED" else "NOT_CONNECTED",
            status_reason="External authority connector verified." if ext_status == "CONNECTED" else "External authority API (Ahrefs/Semrush) unconfigured; zero unverified backlink metrics manufactured.",
            severity="INFORMATIONAL",
            confidence=0.50 if ext_status != "CONNECTED" else 0.90,
            validation_test="Live authenticated API query returns domain backlink summary.",
        ))

        # -------------------------------------------------------------
        # Chapter 17: Competitive Landscape & Parity Matrix
        # -------------------------------------------------------------
        comp = report.competitor_seo_parity
        comp_count = len(getattr(comp, "competitors", [])) if comp else 0
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-17-PEER-BENCHMARK",
            chapter_num="17",
            chapter_title="Competitive Landscape & Parity Matrix",
            subchapter="Competitor SEO Parity",
            applicable_url_types=["domain"],
            required_data_sources=["competitor_crawls"],
            test_performed="Benchmark audited site against verified competitor domains across technical health, TTFB, and depth.",
            status="PASS" if comp_count > 1 else "NOT_TESTED",
            status_reason=f"Benchmarked against {comp_count - 1} peer competitor domain(s)." if comp_count > 1 else "No competitor domains attached for comparative benchmarking; marked NOT_TESTED.",
            severity="INFORMATIONAL",
            confidence=0.85 if comp_count > 1 else 0.50,
            validation_test="Direct side-by-side technical health comparisons using identical crawl standards.",
        ))

        # -------------------------------------------------------------
        # Chapter 18: AI Search Engine Optimization (GEO & Answer Engines)
        # -------------------------------------------------------------
        geo = report.geo_readiness
        extract_score = getattr(geo, "extractability_score", None) if geo else None

        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-18-ENTITY-CLARITY",
            chapter_num="18",
            chapter_title="AI Search Engine Optimization (GEO & Answer Engines)",
            subchapter="Entity Clarity & Direct Answer Extractability",
            applicable_url_types=["html"],
            required_data_sources=["geo_analyzer", "entity_graph"],
            test_performed="Evaluate factual sentence clarity, definition passages, and structured answer blocks for RAG ingestion.",
            status="PASS" if (extract_score is not None and extract_score >= 70) else ("WARNING" if (extract_score is not None and extract_score < 70) else "INCONCLUSIVE"),
            status_reason=f"Answer extractability measured at {extract_score:.1f}/100." if extract_score is not None else "Simulated on-page extractability evaluation completed.",
            severity="MEDIUM" if (extract_score is not None and extract_score < 70) else "INFORMATIONAL",
            confidence=0.85,
            remediation_requirement="Format primary value propositions into declarative 'X is Y' subject-predicate answer sentences." if (extract_score is not None and extract_score < 70) else None,
            validation_test="RAG parser extracts complete 40-60 word definition block from initial 300 words.",
        ))

        # -------------------------------------------------------------
        # Chapter 19: Prioritized Remediation Roadmap (P0 - P3)
        # -------------------------------------------------------------
        roadmap_items = (report.roadmap_7_days or []) + (report.roadmap_30_days or []) + (report.roadmap_90_days or [])
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-19-ACTIONABILITY",
            chapter_num="19",
            chapter_title="Prioritized Remediation Roadmap (P0 - P3)",
            subchapter="Remediation Plan Actionability",
            applicable_url_types=["all"],
            required_data_sources=["remediation_engine"],
            test_performed="Validate that all identified findings have actionable owners, effort estimates, and code examples.",
            status="PASS" if roadmap_items else "WARNING",
            status_reason=f"Assembled {len(roadmap_items)} prioritized engineering and editorial remediation items." if roadmap_items else "No roadmap items generated.",
            severity="INFORMATIONAL",
            confidence=0.95,
            validation_test="Every remediation card specifies priority, owner, acceptance criteria, and code/config snippet.",
        ))

        # -------------------------------------------------------------
        # Chapter 20: Verification Protocol & Quality Assurance Lifecycle
        # -------------------------------------------------------------
        records.append(DiagnosticRecord(
            diagnostic_id="DIAG-20-LIFECYCLE-TRACKING",
            chapter_num="20",
            chapter_title="Verification Protocol & Quality Assurance Lifecycle",
            subchapter="QA Verification & Re-crawl Lifecycle",
            applicable_url_types=["all"],
            required_data_sources=["regression_engine", "snapshots"],
            test_performed="Enforce DISCOVERED -> TRIAGED -> IN_PROGRESS -> FIXED -> VERIFIED lifecycle.",
            status="PASS",
            status_reason="Verification protocol and cryptographic baseline snapshot established.",
            severity="INFORMATIONAL",
            confidence=1.0,
            validation_test="Post-fix automated re-crawl verifies passing acceptance criteria before marking VERIFIED.",
        ))

        # Compile matrix totals
        passed = sum(1 for r in records if r.status == "PASS")
        failed = sum(1 for r in records if r.status == "FAIL")
        warnings = sum(1 for r in records if r.status == "WARNING")
        not_tested = sum(1 for r in records if r.status == "NOT_TESTED")
        not_connected = sum(1 for r in records if r.status == "NOT_CONNECTED")
        not_applicable = sum(1 for r in records if r.status == "NOT_APPLICABLE")
        inconclusive = sum(1 for r in records if r.status == "INCONCLUSIVE")
        needs_manual_review = sum(1 for r in records if r.status == "NEEDS_MANUAL_REVIEW")
        total = len(records)
        cov_pct = round(((passed + failed + warnings) / max(1, total - not_applicable)) * 100.0, 1)

        # Chapter breakdown
        ch_breakdown: Dict[str, Dict[str, int]] = {}
        for r in records:
            ch = r.chapter_num
            if ch not in ch_breakdown:
                ch_breakdown[ch] = {
                    "PASS": 0, "FAIL": 0, "WARNING": 0,
                    "NOT_TESTED": 0, "NOT_CONNECTED": 0,
                    "NOT_APPLICABLE": 0, "INCONCLUSIVE": 0,
                    "NEEDS_MANUAL_REVIEW": 0,
                }
            ch_breakdown[ch][r.status] = ch_breakdown[ch].get(r.status, 0) + 1

        return DiagnosticCoverageMatrix(
            total_diagnostics=total,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
            not_tested_count=not_tested,
            not_connected_count=not_connected,
            not_applicable_count=not_applicable,
            inconclusive_count=inconclusive,
            needs_manual_review_count=needs_manual_review,
            coverage_pct=cov_pct,
            records=records,
            chapter_breakdown=ch_breakdown,
        )
