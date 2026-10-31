"""
Dristik Finding Deduplication & Root Cause Hierarchy Engine
Transforms flat, redundant rule violations into a structured root-cause hierarchy:
Observation -> Evidence -> Root Cause -> Deduplicated Findings -> Actionable Recommendations.

Guarantees:
1. Strict mathematical consistency: Total findings count strictly matches sum of severity segments.
2. Clustered root causes: Groups redundant defects (e.g. H1 non-descriptive + weak CTA + ambiguous value prop).
3. 5-Category Evidence Classification: Separates VERIFIED_DEFECT, VERIFIED_OPPORTUNITY,
   INSUFFICIENT_DATA, AUDIT_SCOPE_LIMITATION, and ANALYSIS_LIMITATION.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from app.domain.models import Finding, FindingCalibratedImpact, FindingEvidence, SubObservation
from app.domain.enums import Severity, ImpactLevel, FindingClassification, Category


# 12-Cluster Enterprise Root Cause Taxonomy
ROOT_CAUSE_CLUSTERS = [
    {
        "id": "RC_HOMEPAGE_POSITIONING",
        "title": "Homepage Value Proposition & Conversion Positioning Ambiguity",
        "category": Category.UX_CONVERSION,
        "severity": Severity.HIGH,
        "impact": ImpactLevel.HIGH,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "value proposition", "positioning", "h1 not descriptive", "unclear value proposition",
            "cta ambiguous", "prominent cta", "clarity", "icp not explicit", "5-second test",
            "3-second hook", "tagline", "slogan mismatch", "hero text", "hero value proposition",
            "lacks clear value proposition", "primary h1 not clear", "cta weak", "weak cta"
        ],
        "unified_description": "The homepage hero viewport does not establish an immediate commercial value proposition, explicit ICP qualification, or a compelling primary call-to-action.",
        "unified_recommendation": "Deploy a high-clarity hero section with an unambiguous H1 declaring your core solution, explicit ICP qualification copy, and a primary high-contrast CTA.",
    },
    {
        "id": "RC_IMAGE_ACCESSIBILITY",
        "title": "Missing Image Accessibility & Alternative Text Hierarchy",
        "category": Category.ON_PAGE_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.LOW,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "missing alt", "alt attribute", "images lack alt", "image accessibility", "empty alt", "alt text"
        ],
        "unified_description": "Multiple visual assets on crawled pages lack descriptive alt attributes, degrading screen reader accessibility and image search indexing.",
        "unified_recommendation": "Populate concise, contextual alt descriptions for all content images and mark purely decorative background assets with empty alt=''.",
    },
    {
        "id": "RC_SECURITY_HEADERS",
        "title": "HTTP Security Header Hardening & Transport Protection (HSTS & CSP)",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.LOW,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "hsts", "strict-transport-security", "content-security-policy", "csp", "security header",
            "x-frame-options", "x-content-type-options", "clickjacking", "nosniff"
        ],
        "unified_description": "Server response headers lack HSTS and Content-Security-Policy directives. This represents transport security technical debt, though it does not block crawler indexing or buyer access.",
        "unified_recommendation": "Configure Strict-Transport-Security (max-age=31536000; includeSubDomains; preload) and establish a modern Content-Security-Policy at the reverse proxy or CDN layer.",
    },
    {
        "id": "RC_SCHEMA_ENTITY_GRAPH",
        "title": "Incomplete Schema.org Knowledge Graph & Entity Disambiguation",
        "category": Category.SCHEMA,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.HIGH,
        "classification": FindingClassification.VERIFIED_OPPORTUNITY,
        "keywords": [
            "service schema", "faqpage", "breadcrumb", "schema missing", "organization schema",
            "entity graph", "structured data", "json-ld", "sameas", "entity clarity", "unlinked entity"
        ],
        "unified_description": "The site lacks connected Schema.org JSON-LD graphs (Organization, Service, FAQPage, BreadcrumbList), limiting AI search engines' ability to directly cite structured facts.",
        "unified_recommendation": "Embed comprehensive Organization, WebSite, Service, and FAQPage JSON-LD microdata across target landing pages.",
    },
    {
        "id": "RC_HEADING_HIERARCHY",
        "title": "Document Outline & Heading Hierarchy Fragmentation",
        "category": Category.ON_PAGE_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.LOW,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "multiple h1", "duplicate h1", "no h1", "missing h1", "lacks an h1", "heading hierarchy",
            "heading skip", "non-hierarchical heading", "h2 skipped", "h3 skipped"
        ],
        "unified_description": "Page heading tags violate sequential order or contain multiple H1 elements, impairing screen reader navigation and search engine topical extraction.",
        "unified_recommendation": "Ensure each page contains exactly one primary descriptive H1, with subsequent headings arranged strictly in sequential H2 and H3 order.",
    },
    {
        "id": "RC_METADATA_OPTIMIZATION",
        "title": "SERP Metadata & Snippet Architecture Deficit",
        "category": Category.ON_PAGE_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "meta description missing", "no meta description", "missing meta", "meta description short",
            "meta description long", "title tag missing", "no title tag", "title tag optimization",
            "page title short", "page title duplicate", "title tag too short", "meta description length"
        ],
        "unified_description": "Target landing pages feature missing, truncated, or unoptimized page titles and meta descriptions, depressing search engine click-through rates.",
        "unified_recommendation": "A specialist should write a distinct title and meta description from the page's stored offer. A character band is not the fix.",
    },
    {
        "id": "RC_FORM_CONVERSION_FRICTION",
        "title": "Form Accessibility & Conversion Friction Obstacles",
        "category": Category.UX_CONVERSION,
        "severity": Severity.HIGH,
        "impact": ImpactLevel.HIGH,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "form label", "input label", "form accessibility", "missing label on form",
            "captcha friction", "form fields excessive", "submit button ambiguous"
        ],
        "unified_description": "Interactive forms lack explicit associated <label> elements or introduce high-friction verification barriers that suppress lead capture rates.",
        "unified_recommendation": "Attach explicit <label for='...'> tags to all form controls, simplify required fields, and provide immediate client-side validation cues.",
    },
    {
        "id": "RC_HOST_CANONICAL_ARCHITECTURE",
        "title": "Canonical Host Redirection & Indexation Alignment",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.HIGH,
        "impact": ImpactLevel.MEDIUM,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "canonical tag missing", "rel=canonical", "canonical mismatch", "canonical conflict",
            "host redirect", "www redirect", "non-www", "301 redirect hop", "trailing slash redirect"
        ],
        "unified_description": "Inconsistent host routing (HTTP/HTTPS, www/non-www) or missing/conflicting rel='canonical' tags disperse organic link equity across multiple URL variants.",
        "unified_recommendation": "Implement single-hop 301 redirects to the canonical host and inject self-referential canonical tags across all authoritative URLs.",
    },
    {
        "id": "RC_CRAWL_DEPTH_ORPHANS",
        "title": "Information Architecture Depth & Orphan Pages",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.LOW,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "click depth", "crawl depth", "orphan page", "orphan", "inlinks missing", "deep page"
        ],
        "unified_description": "Valuable content pages are buried beyond 3 clicks from the homepage or lack internal inbound links entirely, impeding crawler discovery and indexation.",
        "unified_recommendation": "Rebalance internal navigation menus and contextual breadcrumbs to ensure all critical landing pages are reachable within 2-3 clicks.",
    },
    {
        "id": "RC_AI_CRAWLER_DIRECTIVES",
        "title": "AI Search Bot Access & Indexation Directives",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.HIGH,
        "impact": ImpactLevel.HIGH,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "gptbot", "claudebot", "perplexitybot", "unintended noindex", "robots.txt block",
            "crawler directives", "ai crawler"
        ],
        "unified_description": "Robots.txt directives or robots meta tags inadvertently restrict major generative AI crawlers (GPTBot, ClaudeBot, PerplexityBot) from ingesting commercial content.",
        "unified_recommendation": "Audit robots.txt directives and explicitly permit verified AI user-agents access to public commercial documentation and landing pages.",
    },
    {
        "id": "RC_SERVER_LATENCY",
        "title": "Server Response Latency & TTFB Performance Drag",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "ttfb", "time to first byte", "server latency", "slow response", "core web vitals",
            "latency curve", "uncompressed"
        ],
        "unified_description": "Page response latency (TTFB) exceeds acceptable performance thresholds (>600ms), delaying browser rendering and crawler throughput.",
        "unified_recommendation": "Enable edge caching, configure Gzip/Brotli compression, and optimize backend database queries to bring TTFB below 200ms.",
    },
    {
        "id": "RC_CRAWL_SCOPE_SAMPLING",
        "title": "Crawl Scope Intentional Audit Sampling",
        "category": Category.TECHNICAL_SEO,
        "severity": Severity.INFO,
        "impact": ImpactLevel.INFO,
        "classification": FindingClassification.AUDIT_SCOPE_LIMITATION,
        "keywords": [
            "crawl coverage", "5 pages", "limited crawl", "deep crawl not executed", "sample crawl"
        ],
        "unified_description": "Audit executed under an intentional page-budget limit. Conclusions reflect the verified sample and do not represent site-wide defect claims.",
        "unified_recommendation": "To perform site-wide architecture validation across hundreds of URLs, initiate a full-site crawl program.",
    },
    {
        "id": "RC_WCAG_INTERACTIVE_ACCESSIBILITY",
        "title": "Interactive Element Accessibility & Keyboard Focus Traps (WCAG 2.2 AA)",
        "category": Category.UX_CONVERSION,
        "severity": Severity.HIGH,
        "impact": ImpactLevel.MEDIUM,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "keyboard accessible", "positive tabindex", "focus trap", "aria-hidden", "outline: none",
            "focus visible", "target size", "touch target", "nameless button", "button names",
            "accessible names", "ambiguous link", "skip navigation", "wcag_2_1_1", "wcag_2_4_3",
            "wcag_2_4_4", "wcag_2_4_7", "wcag_2_5_8", "wcag_4_1_2"
        ],
        "unified_description": "Interactive elements lack accessible names, suppress keyboard focus visibility, or present keyboard navigation barriers that violate WCAG 2.2 AA standards.",
        "unified_recommendation": "Ensure all interactive controls have accessible names, maintain visible focus indicators, preserve natural tab order, and meet 24x24px minimum target sizes.",
    },
    {
        "id": "RC_WCAG_CONTRAST_AND_SEMANTICS",
        "title": "Visual Contrast & Semantic Document Structure (WCAG 2.2 AA)",
        "category": Category.ON_PAGE_SEO,
        "severity": Severity.MEDIUM,
        "impact": ImpactLevel.MEDIUM,
        "classification": FindingClassification.VERIFIED_DEFECT,
        "keywords": [
            "color contrast", "low contrast", "contrast ratio", "viewport scaling", "user-scalable",
            "landmark structure", "table headers", "aria misuse", "invalid aria", "modal accessibility",
            "wcag_1_4_3", "wcag_1_4_4", "wcag_1_3_1", "wcag_3_1_1"
        ],
        "unified_description": "Text elements exhibit low color contrast ratios (<4.5:1), lack semantic landmark hierarchy, or restrict assistive zoom scaling.",
        "unified_recommendation": "Elevate text color contrast to at least 4.5:1, deploy semantic landmark regions (<main>, <nav>), and allow unconstrained viewport zoom scaling.",
    },
]


class FindingDeduplicator:
    """
    Deduplicates raw findings into canonical root-cause findings and ensures
    strict mathematical consistency across all report surfaces.
    Observation -> Evidence -> Root Cause -> Deduplicated Findings -> Actionable Recommendations.
    """

    @classmethod
    def deduplicate(cls, raw_findings: List[Finding]) -> List[Finding]:
        if not raw_findings:
            return []

        deduplicated: List[Finding] = []
        cluster_buckets: Dict[str, List[Finding]] = {}
        unclustered: List[Finding] = []

        # Step 1: Assign findings to semantic clusters or unclustered bucket
        for finding in raw_findings:
            matched_cluster_id = None
            title_desc = f"{finding.title} {finding.description} {getattr(finding, 'finding', '')}".lower()

            if (finding.rule_id or "").startswith("entity_graph_"):
                unclustered.append(finding)
                continue

            # Check if this finding is an audit scope limitation (never a defect!)
            if any(k in title_desc for k in ["crawl coverage", "only 5 pages", "sample crawl", "verified crawl sample"]):
                finding.classification = FindingClassification.AUDIT_SCOPE_LIMITATION
                finding.severity = Severity.INFO

            for cluster in ROOT_CAUSE_CLUSTERS:
                if any(kw in title_desc for kw in cluster["keywords"]):
                    matched_cluster_id = cluster["id"]
                    break

            if matched_cluster_id:
                if matched_cluster_id not in cluster_buckets:
                    cluster_buckets[matched_cluster_id] = []
                cluster_buckets[matched_cluster_id].append(finding)
            else:
                unclustered.append(finding)

        # Step 2: Consolidate each cluster into a single canonical root-cause finding
        for cluster_def in ROOT_CAUSE_CLUSTERS:
            c_id = cluster_def["id"]
            if c_id not in cluster_buckets:
                continue

            group = cluster_buckets[c_id]
            # Build detailed sub-observations from all members
            detailed_obs: List[SubObservation] = []
            sub_obs_titles: List[str] = []
            merged_evidence: List[FindingEvidence] = []
            seen_ev_selectors = set()
            surfaces: List[Dict[str, Any]] = []

            for f in group:
                sub_obs_titles.append(f.title)
                primary_ev = f.evidence[0] if (f.evidence and len(f.evidence) > 0) else None
                sel = primary_ev.selector if primary_ev and primary_ev.selector else (primary_ev.element if primary_ev else None)
                snip = (primary_ev.snippet or primary_ev.value) if primary_ev else None
                url = primary_ev.url if primary_ev else None

                detailed_obs.append(
                    SubObservation(
                        observation_id=f.finding_id,
                        title=f.title,
                        description=f.description or getattr(f, "finding", "") or f.title,
                        selector=sel,
                        snippet=snip,
                        url=url,
                        severity=f.severity,
                        category=f.category,
                        evidence_refs=f.evidence_refs or []
                    )
                )

                from app.seo.audit.evidence.compatibility_gate import EvidenceCompatibilityGate

                for ev in (f.evidence or []):
                    if not EvidenceCompatibilityGate.is_evidence_compatible(f.title, str(f.category), ev):
                        continue
                    ev_key = f"{ev.evidence_id or ''}:{ev.url or ''}:{ev.selector or ''}:{ev.value or ''}:{ev.snippet or ''}"
                    if ev_key not in seen_ev_selectors:
                        seen_ev_selectors.add(ev_key)
                        merged_evidence.append(ev)

                for surf in (getattr(f, "surfaces_affected", []) or []):
                    if not any(s.get("surface") == surf.get("surface") and s.get("url") == surf.get("url") for s in surfaces):
                        surfaces.append(surf)

            if len(group) == 1:
                # Single observation matching cluster — preserve identity but standardize
                f = group[0]
                f.root_cause_id = c_id
                f.classification = cluster_def["classification"]
                f.sub_observations = sub_obs_titles
                f.detailed_observations = detailed_obs
                if surfaces:
                    f.surfaces_affected = surfaces
                if not f.calibrated_impact:
                    f.calibrated_impact = FindingCalibratedImpact(
                        technical_severity=f.severity,
                        business_impact=cluster_def["impact"],
                        confidence=f.confidence,
                        is_blocking=False
                    )
                deduplicated.append(f)
            else:
                # Multiple redundant observations merged into canonical root-cause finding
                # Calibrate severity: highest severity among group or cluster default
                severity_ranks = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0}
                max_sev = max((f.severity for f in group), key=lambda s: severity_ranks.get(s, 1), default=cluster_def["severity"])
                best_impact = max((f.impact for f in group if f.impact is not None), default=7)
                best_priority = max((f.priority for f in group if f.priority is not None), default=7)

                capped_evidence = merged_evidence[:8]
                kept_ev_ids = {ev.evidence_id for ev in capped_evidence if getattr(ev, "evidence_id", None)}
                all_ev_ids = {ev.evidence_id for f in group for ev in (f.evidence or []) if getattr(ev, "evidence_id", None)}
                dropped_ev_ids = all_ev_ids - kept_ev_ids
                merged_refs = [
                    ref for ref in dict.fromkeys(ref for f in group for ref in (f.evidence_refs or []))
                    if ref not in dropped_ev_ids
                ]
                canonical_finding = Finding(
                    finding_id=f"ROOT_{c_id}",
                    category=cluster_def["category"],
                    severity=max_sev,
                    classification=cluster_def["classification"],
                    root_cause_id=c_id,
                    sub_observations=sub_obs_titles,
                    detailed_observations=detailed_obs,
                    surfaces_affected=surfaces,
                    title=cluster_def["title"],
                    description=cluster_def["unified_description"],
                    recommendation=cluster_def["unified_recommendation"],
                    evidence=capped_evidence,
                    evidence_refs=merged_refs,
                    confidence=max((f.confidence for f in group), default=0.90),
                    impact=best_impact,
                    priority=best_priority,
                    why_it_matters=f"This canonical defect consolidates {len(group)} related symptoms that collectively impair user experience, trust, and organic discoverability.",
                    validation_criteria=f"Resolve all {len(group)} underlying observations and verify compliance.",
                    calibrated_impact=FindingCalibratedImpact(
                        technical_severity=max_sev,
                        business_impact=cluster_def["impact"],
                        confidence=0.92,
                        is_blocking=False
                    )
                )
                deduplicated.append(canonical_finding)

        # Step 3: Deduplicate remaining unclustered findings by title similarity
        seen_titles: Dict[str, Finding] = {}
        for f in unclustered:
            clean_title = re.sub(r"[^\w\s]", "", f.title.lower()).strip()
            # Normalize common prefixes/suffixes
            clean_title = re.sub(r"^(missing|lacks?|unclear|duplicate|weak)\s+", "", clean_title)

            if clean_title in seen_titles:
                # Subsume into already seen unclustered finding
                existing = seen_titles[clean_title]
                if f.title not in existing.sub_observations:
                    existing.sub_observations.append(f.title)
                from app.seo.audit.evidence.compatibility_gate import EvidenceCompatibilityGate
                comp_evs = [ev for ev in (f.evidence or []) if EvidenceCompatibilityGate.is_evidence_compatible(f.title, str(f.category), ev)]
                primary_ev = comp_evs[0] if comp_evs else None
                existing.detailed_observations.append(
                    SubObservation(
                        observation_id=f.finding_id,
                        title=f.title,
                        description=f.description or getattr(f, "finding", "") or f.title,
                        selector=primary_ev.selector if primary_ev and primary_ev.selector else (primary_ev.element if primary_ev else None),
                        snippet=(primary_ev.snippet or primary_ev.value) if primary_ev else None,
                        url=primary_ev.url if primary_ev else None,
                        severity=f.severity,
                        category=f.category,
                        evidence_refs=f.evidence_refs or []
                    )
                )
                # Combine evidence tokens
                seen_refs = set(existing.evidence_refs)
                for ref in (f.evidence_refs or []):
                    if ref not in seen_refs:
                        existing.evidence_refs.append(ref)
                continue

            # Populate initial self-observation on unclustered finding
            if not f.sub_observations:
                f.sub_observations = [f.title]
            if not f.detailed_observations:
                from app.seo.audit.evidence.compatibility_gate import EvidenceCompatibilityGate
                comp_evs = [ev for ev in (f.evidence or []) if EvidenceCompatibilityGate.is_evidence_compatible(f.title, str(f.category), ev)]
                primary_ev = comp_evs[0] if comp_evs else None
                f.detailed_observations = [
                    SubObservation(
                        observation_id=f.finding_id,
                        title=f.title,
                        description=f.description or getattr(f, "finding", "") or f.title,
                        selector=primary_ev.selector if primary_ev and primary_ev.selector else (primary_ev.element if primary_ev else None),
                        snippet=(primary_ev.snippet or primary_ev.value) if primary_ev else None,
                        url=primary_ev.url if primary_ev else None,
                        severity=f.severity,
                        category=f.category,
                        evidence_refs=f.evidence_refs or []
                    )
                ]

            seen_titles[clean_title] = f
            deduplicated.append(f)

        from app.scoring.calibration import calibrate_finding
        for finding in deduplicated:
            calibrate_finding(finding)

        return deduplicated

    @classmethod
    def get_severity_breakdown(cls, findings: List[Finding]) -> Tuple[Dict[str, int], int]:
        """
        Calculates severity counts strictly from verified defects.
        Guarantees that total_defects == sum(severity_counts.values()) == len(findings).
        """
        counts = {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 0,
            Severity.MEDIUM.value: 0,
            Severity.LOW.value: 0,
            Severity.INFO.value: 0,
        }
        for f in findings:
            sev_key = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            if sev_key in counts:
                counts[sev_key] += 1
            else:
                counts[Severity.INFO.value] += 1

        total = sum(counts.values())
        return counts, total

