"""Catalog of the enterprise SEO specialists.

The catalog is the contract. A run does not call a model for a check that
the deterministic engines can decide, and it does not call a specialist
whose source data is missing.
"""

from __future__ import annotations

from app.seo.enterprise.contracts import SEOAgentContract
from app.seo.enterprise.policy import SHARED_POLICY_VERSION

_INPUT = "seo.agent.input.v1"
_OUTPUT = "seo.agent.output.v1"
_POLICY = [SHARED_POLICY_VERSION]


def _agent(
    agent_id: str,
    purpose: str,
    group: str,
    chapters: list[int],
    permissions: list[str],
    evidence: list[str],
    mode: str,
    dependencies: list[str],
    prompt: str,
    timeout: int = 60,
) -> SEOAgentContract:
    return SEOAgentContract(
        agent_id=agent_id,
        version="1.0.0",
        purpose=purpose,
        group=group,  # type: ignore[arg-type]
        chapters=chapters,
        input_schema_version=_INPUT,
        output_schema_version=_OUTPUT,
        data_permissions=permissions,
        evidence_requirements=evidence,
        policy_requirements=list(_POLICY),
        timeout_seconds=timeout,
        max_retries=1,
        failure_mode="unavailable",
        execution_mode=mode,  # type: ignore[arg-type]
        dependencies=dependencies,
        dedicated_prompt=prompt.strip(),
    )


AGENT_CATALOG: tuple[SEOAgentContract, ...] = (
    _agent(
        "seo.crawlability.v1",
        "Inspect robots.txt, crawl access, and discoverability for the configured crawler.",
        "technical",
        [3, 7],
        ["crawl.robots", "crawl.sitemap_discovery"],
        ["robots_response"],
        "deterministic",
        [],
        """
        You are responsible for robots.txt, crawl access, resource blocking, crawl traps, and discoverability.
        Inspect the actual robots response and directives for the configured crawler and relevant user-agent groups.
        Distinguish crawling restrictions from indexation controls. Detect rules that may block important resources
        or URL classes, but never assume a blocked URL is deindexed. Identify conflicting rules, syntax errors,
        inaccessible robots files, and unnecessary crawl spaces. For each confirmed defect, list affected URL
        patterns, matching rules, representative URLs, and evidence. Recommend the smallest safe change and
        specify regression tests for intended allow/disallow behavior.
        """,
    ),
    _agent(
        "seo.indexability.v1",
        "Determine technical indexing eligibility from status, robots, and canonical signals.",
        "technical",
        [4],
        ["crawl.pages", "crawl.robots", "search_console.index"],
        ["http_response", "robots_directive", "canonical_tag"],
        "deterministic",
        ["seo.crawlability.v1", "seo.http_redirects.v1"],
        """
        Determine whether URLs are technically eligible for indexing by examining HTTP status, robots directives,
        canonical tags, X-Robots-Tag, and relevant response headers. Detect contradictory signals, accidental
        noindex directives, canonical chains, conflicting canonicals, and noncanonical internal-link targets.
        Compare URL-level observations with Search Console indexing data only when supplied. Explain that
        eligibility does not prove actual indexing. Recommend URL-specific or template-level fixes, identify
        accidental deindexation risks, and define tests for canonical consistency and indexability after deployment.
        """,
    ),
    _agent(
        "seo.http_redirects.v1",
        "Analyze observed status codes, redirect hops, and broken internal destinations.",
        "technical",
        [5],
        ["crawl.http"],
        ["http_response", "redirect_chain"],
        "deterministic",
        [],
        """
        Analyze observed status codes, redirect destinations, loops, chains, soft-404 candidates, broken internal
        links, intermittent failures, and hostname or protocol inconsistencies. Follow redirects only within the
        approved crawl policy. Preserve each hop and timestamp. Do not infer a soft 404 solely from a 200 response.
        Recommend relevant final destinations and safe redirect rules, including loop prevention, query-string
        behavior, and rollback. Verify status, hop count, destination relevance, and internal-link updates after remediation.
        """,
    ),
    _agent(
        "seo.sitemaps.v1",
        "Compare sitemap entries with the crawled URL inventory when both exist.",
        "technical",
        [7],
        ["crawl.sitemap", "crawl.pages"],
        ["sitemap_xml", "url_inventory"],
        "deterministic",
        ["seo.indexability.v1"],
        """
        Inspect sitemap indexes, child sitemaps, XML validity, URL status, indexability, canonical consistency,
        timestamps, and URL coverage. Compare sitemap entries against discovered URLs and report the exact
        denominators. Detect stale, redirected, noncanonical, or erroneous entries. Check applicable sitemap
        protocol limits. Do not treat sitemap omission alone as proof of a ranking problem. Recommend corrections
        to generation logic, segmentation, and publication. Define validation tests that compare generated sitemap
        entries with the eligible canonical URL inventory.
        """,
    ),
    _agent(
        "seo.site_architecture.v1",
        "Describe observed URL hierarchy, normalization, and parameters.",
        "technical",
        [6],
        ["crawl.urls", "crawl.graph"],
        ["url_inventory", "link_graph"],
        "deterministic",
        ["seo.crawl_graph.v1"],
        """
        Model the supplied URL hierarchy, directory patterns, parameters, hostnames, click depth, and page
        relationships. Identify inconsistent URL normalization, unnecessary duplicate variants, excessive nesting
        where it obstructs navigation, and structurally disconnected sections. Evaluate the purpose and
        discoverability of each URL class. Do not recommend URL changes merely to make URLs shorter. Prefer
        low-risk internal-link and normalization corrections over migrations when suitable. Provide a proposed
        architecture, mapping requirements for any URL change, and tests that prevent duplicate URL generation.
        """,
    ),
    _agent(
        "seo.rendering_js.v1",
        "Compare raw HTML with the rendered DOM when both snapshots were stored.",
        "technical",
        [8],
        ["crawl.raw_html", "crawl.rendered_dom"],
        ["raw_html", "rendered_dom"],
        "deterministic",
        [],
        """
        Compare raw HTTP HTML with browser-rendered DOM using paired snapshots. Check whether main content,
        anchors, metadata, canonical tags, robots directives, and structured data survive rendering and hydration.
        Identify JavaScript exceptions and failed resource requests from recorded browser telemetry. Separate an
        empty initial HTML response from an actual search-engine accessibility defect. Recommend server rendering,
        prerendering, or hydration fixes only where justified. Define raw-versus-rendered parity tests and verify
        route behavior after deployment.
        """,
    ),
    _agent(
        "seo.international.v1",
        "Validate hreflang only when a locale implementation was observed.",
        "technical",
        [9],
        ["crawl.hreflang"],
        ["hreflang", "html_lang"],
        "deterministic",
        [],
        """
        Validate hreflang syntax, supported language-region values, reciprocal references, x-default behavior,
        canonical alignment, locale destinations, and HTML language declarations. Compare actual rendered
        alternate links and sitemap alternates where available. Distinguish missing optional localization features
        from broken implementations. Detect cross-locale conflicts and inappropriate canonical consolidation.
        Recommend a locale relationship graph and tests for reciprocal mappings, valid targets, and locale-specific
        URL correctness. Do not infer a site's target country from its domain alone.
        """,
    ),
    _agent(
        "seo.performance.v1",
        "Report field and lab performance separately. Do not invent field Core Web Vitals.",
        "technical",
        [18, 19],
        ["performance.field", "performance.lab"],
        ["field_crux", "lab_trace"],
        "deterministic",
        [],
        """
        Analyze LCP, INP, CLS, TTFB, resource loading, JavaScript execution, image delivery, caching, and
        mobile/desktop differences. Label field measurements, lab measurements, and unmeasured estimates
        separately. Apply current documented thresholds and the correct measurement window. Attribute a cause
        only when trace or resource evidence supports it. Rank bottlenecks by measured impact and affected
        templates. Produce a prioritized performance plan with before-and-after acceptance criteria. Never invent
        field Core Web Vitals from a single synthetic test.
        """,
    ),
    _agent(
        "seo.mobile_parity.v1",
        "Compare mobile and desktop output only when both were collected.",
        "technical",
        [19],
        ["crawl.mobile", "crawl.desktop"],
        ["mobile_snapshot", "desktop_snapshot"],
        "deterministic",
        ["seo.rendering_js.v1"],
        """
        Compare mobile and desktop page content, metadata, canonical directives, links, resources, and rendering.
        Inspect viewport behavior, responsive layout, navigation accessibility, and mobile performance. Distinguish
        genuine content or discoverability discrepancies from harmless responsive presentation differences.
        Identify templates and URLs where mobile output loses important information. Recommend responsive
        implementation corrections and provide device-specific browser tests. Do not use generic mobile design
        preferences as automatic SEO violations.
        """,
    ),
    _agent(
        "seo.https_security.v1",
        "Inspect HTTPS consistency and crawl-relevant access. Separate security defects from ranking claims.",
        "technical",
        [24],
        ["crawl.tls", "crawl.headers"],
        ["tls_certificate", "response_headers"],
        "deterministic",
        [],
        """
        Inspect TLS validity, HTTPS consistency, mixed content, insecure resource requests, staging exposure, and
        crawl-relevant access barriers using authorized evidence. Separate security defects from direct SEO issues.
        Do not claim every missing security header harms rankings. Never probe beyond the approved scope. Recommend
        precise configuration changes and safe deployment order. Provide verification steps for certificates, HTTPS
        redirects, resource integrity, and intended public versus private access.
        """,
    ),
    _agent(
        "seo.crawl_graph.v1",
        "Build the internal link graph from the measured crawl, not from an assumed full site.",
        "technical",
        [3, 6, 15],
        ["crawl.links"],
        ["link_graph"],
        "deterministic",
        [],
        """
        Build a directed graph from observed internal links, discovered URLs, redirect edges, and crawl paths.
        Identify orphan candidates, disconnected clusters, excessive click depth, links to broken destinations,
        and important pages with weak discovery paths. State whether the graph represents a complete crawl or a
        sample. An apparent orphan is confirmed only relative to the measured discovery sources and crawl scope.
        Recommend relevant contextual links, navigation corrections, and graph-level acceptance tests.
        """,
    ),
    _agent(
        "seo.migration.v1",
        "Evaluate a migration only when an approved before/after baseline was supplied.",
        "technical",
        [25],
        ["migration.baseline", "crawl.http"],
        ["url_mapping", "before_after_crawl"],
        "gated",
        ["seo.http_redirects.v1", "seo.historical_trends.v1"],
        """
        Evaluate old-to-new URL mappings, redirects, canonical changes, sitemap changes, internal links, and
        before/after crawl evidence for migrations. Detect missing mappings, irrelevant redirect targets, redirect
        loops, and lost indexable destinations. Separate expected changes from regressions using an approved
        baseline. Produce a migration risk register, launch acceptance checklist, rollback triggers, and
        post-launch verification plan. Do not declare a migration successful from HTTP status checks alone.
        """,
    ),
    _agent(
        "seo.title_tags.v1",
        "Evaluate extracted titles. Treat length as a diagnostic, not a ranking threshold.",
        "onpage",
        [10],
        ["crawl.titles"],
        ["title_element"],
        "deterministic",
        [],
        """
        Evaluate title existence, uniqueness, topic alignment, intent, brand conventions, template boilerplate,
        and duplication across observed URLs. Use page content and query data when available to assess relevance.
        Treat character and pixel lengths as diagnostics, not universal ranking thresholds. Distinguish technical
        defects from editorial opportunities. Propose specific revised titles and template logic, explain
        trade-offs, and define tests for uniqueness, output escaping, and page-type coverage.
        """,
    ),
    _agent(
        "seo.meta_descriptions.v1",
        "Evaluate extracted meta descriptions without claiming a ranking benefit.",
        "onpage",
        [11],
        ["crawl.meta"],
        ["meta_description"],
        "deterministic",
        [],
        """
        Analyze meta descriptions for missing values, duplication, boilerplate, misleading claims, and alignment
        with the page's purpose. When query and SERP observations exist, evaluate whether proposed snippets
        address the observed intent. Produce useful descriptions without keyword stuffing or unsupported promises.
        Explain that search engines may generate alternate snippets and that meta descriptions are not a guaranteed
        ranking boost. Supply page-specific revisions, scalable template rules, and quality validation tests.
        """,
    ),
    _agent(
        "seo.headings_semantics.v1",
        "Inspect heading structure. Do not treat multiple H1 elements as a ranking violation.",
        "onpage",
        [12],
        ["crawl.headings"],
        ["heading_outline"],
        "deterministic",
        [],
        """
        Inspect H1–H6 structure, topic clarity, duplicate headings, semantic elements, and template-generated
        heading patterns. Evaluate whether the document structure communicates the page's actual purpose. Do not
        automatically flag multiple H1 elements as a ranking violation. Identify missing context, generic headings,
        or misleading hierarchy only where useful. Recommend precise heading and HTML changes while preserving
        accessible semantics. Verify rendered output and page-template consistency.
        """,
    ),
    _agent(
        "seo.content_quality.v1",
        "Report measured text properties. Do not equate word count with quality.",
        "onpage",
        [13],
        ["crawl.text"],
        ["extracted_text"],
        "interpretive",
        ["seo.page_type.v1"],
        """
        Evaluate the supplied page content for relevance, completeness, originality, factual support, freshness,
        readability, and satisfaction of the intended search task. Distinguish measured textual properties from
        editorial judgment. Do not equate word count with quality or recommend adding filler. Identify missing
        information with concrete examples, cite supporting page evidence, and propose a content brief or revision
        plan. Flag claims needing subject-matter review. Preserve accurate content and avoid rewriting merely for
        keyword density.
        """,
        timeout=120,
    ),
    _agent(
        "seo.image_media.v1",
        "Inspect collected image markup. Do not infer image content from filenames.",
        "onpage",
        [14],
        ["crawl.images"],
        ["image_element"],
        "deterministic",
        [],
        """
        Inspect image URLs, alt attributes, filenames, dimensions, responsive delivery, lazy loading, formats, and
        media discoverability. Distinguish decorative images from informative images and do not infer image content
        from filenames alone. Use actual image inspection only when authorized. Identify layout shifts, oversized
        assets, and broken resources from evidence. Recommend appropriate alt text, media metadata, responsive
        markup, and compression without changing meaning. Provide resource-level and template-level verification tests.
        """,
    ),
    _agent(
        "seo.internal_links.v1",
        "Evaluate internal links and anchors inside the measured graph.",
        "onpage",
        [15],
        ["crawl.links"],
        ["link_graph", "anchor_text"],
        "deterministic",
        ["seo.crawl_graph.v1"],
        """
        Evaluate internal links, anchor descriptions, relevance, destination status, redirects, click depth, and
        contextual relationships. Identify generic anchors or missed linking opportunities only when a clearer
        alternative is genuinely useful. Do not prescribe exact-match keyword anchors indiscriminately. Recommend
        source page, destination page, suggested anchor, and contextual placement for each opportunity. Include
        graph evidence, avoid redundant links, and define tests for link integrity and discoverability.
        """,
    ),
    _agent(
        "seo.structured_data.v1",
        "Validate structured data that was present. Do not require optional schema on every site.",
        "onpage",
        [16],
        ["crawl.schema"],
        ["structured_data"],
        "deterministic",
        [],
        """
        Parse structured data and validate syntax, schema types, property usage, entity relationships,
        visible-content consistency, and feature-specific eligibility where applicable. Separate vocabulary
        validity from search-engine rich-result eligibility and actual display. Do not mark optional schema as
        mandatory for every site. Recommend exact JSON-LD changes grounded in the page content and current
        supported rules. Include parser, schema validator, and relevant rich-result test requirements. Never
        fabricate organization details, reviews, prices, or ratings.
        """,
    ),
    _agent(
        "seo.page_type.v1",
        "Classify observed URLs. Do not force every page into an e-commerce model.",
        "onpage",
        [17],
        ["crawl.pages", "business.profile"],
        ["url_pattern", "dom_features"],
        "deterministic",
        [],
        """
        Classify URLs into verified or uncertain page types using URL patterns, DOM features, templates, and
        supplied business context. Apply conditional checks for service pages, articles, products, documentation,
        directories, jobs, and other supported page classes. Do not force all pages into an e-commerce model.
        Identify template-wide defects, inappropriate checks, and missing page-type coverage. Return the
        classification rationale and applicable check set. Recommend fixes at the correct template layer where possible.
        """,
    ),
    _agent(
        "seo.keyword_mapping.v1",
        "Map supplied queries to landing pages. Do not invent search volume.",
        "intelligence",
        [21],
        ["search.queries"],
        ["query_rows"],
        "gated",
        [],
        """
        Map supplied queries to relevant landing pages using intent, page content, geography, and business context.
        Identify unserved query groups, overlapping targets, and topic gaps supported by the supplied data. Do not
        invent search volumes or claim a keyword is valuable without demand evidence. Separate measured
        opportunities from strategic hypotheses. Return target URL, query group, intent, supporting evidence,
        recommended action, and confidence. Preserve existing high-performing pages unless evidence supports a change.
        """,
    ),
    _agent(
        "seo.search_console.v1",
        "Analyze authorized Search Console rows. Do not treat average position as a precise rank.",
        "intelligence",
        [22],
        ["search_console.performance"],
        ["search_console_rows"],
        "gated",
        [],
        """
        Analyze authorized Search Console data by query, page, date, country, device, and search type. Identify
        statistically or operationally meaningful changes in clicks, impressions, CTR, and average position. Account
        for date ranges, data delays, anonymized queries, and aggregation limits. Do not treat average position as
        a precise per-query rank or infer causality from correlation. Return the comparison baseline, metric deltas,
        evidence window, plausible explanations, and further tests needed.
        """,
    ),
    _agent(
        "seo.backlinks.v1",
        "Analyze an authorized backlink export. Do not invent links or recommend disavowal.",
        "intelligence",
        [20],
        ["backlinks.provider"],
        ["backlink_export"],
        "gated",
        [],
        """
        Analyze authorized backlink provider data, including referring domains, target URLs, link attributes,
        new/lost links, anchors, and available provenance. Distinguish a provider's classification from proven
        manipulation. Report provider, extraction time, coverage, and limitations. Identify broken high-value
        destinations and reasonable reclamation opportunities. Never fabricate links, domain authority metrics, or
        penalties. Do not recommend disavowal without rigorous evidence, specialist review, and explicit approval.
        """,
    ),
    _agent(
        "seo.competitor_benchmark.v1",
        "Compare verified search competitors using supplied evidence only.",
        "intelligence",
        [23],
        ["competitors.serp", "competitors.crawl"],
        ["serp_rows", "competitor_crawl"],
        "gated",
        [],
        """
        Compare the client with verified search competitors using supplied SERPs, query-to-URL data, crawl
        observations, and authorized backlink data. Distinguish actual search competitors from business competitors.
        Identify content, architecture, and ranking opportunities without assuming competitor performance metrics.
        Preserve manually designated competitors while reporting uncertain automated discoveries separately. Return
        the comparison methodology, evidence, opportunity, limitations, and actionable next step.
        """,
    ),
    _agent(
        "seo.organic_analytics.v1",
        "Analyze authorized analytics. Do not treat a missing connector as zero sessions.",
        "intelligence",
        [22],
        ["analytics.ga4"],
        ["analytics_rows"],
        "gated",
        [],
        """
        Analyze authorized GA4, CRM, and revenue data for organic landing-page sessions, engaged visits,
        conversions, and revenue where available. Document channel definitions, attribution model, conversion
        definitions, reporting window, and data completeness. Separate observed attribution from causal impact.
        Never claim SEO revenue caused by a fix without suitable experimental or comparative evidence. Recommend
        instrumentation and reporting corrections when data cannot support a conclusion.
        """,
    ),
    _agent(
        "seo.historical_trends.v1",
        "Compare historical snapshots when a baseline exists. Do not invent history.",
        "intelligence",
        [22, 25],
        ["history.snapshots"],
        ["prior_crawl", "prior_performance"],
        "gated",
        [],
        """
        Compare historical crawl snapshots, URL inventories, query performance, redirects, and deployments to
        identify technical regressions or meaningful changes. Normalize comparisons for scope and sampling
        differences. Flag missing baselines and non-comparable date ranges. Distinguish temporal correlation from
        confirmed root cause. Produce a timeline, evidence-backed regression hypotheses, recovery checks, and
        rollback triggers. Do not invent historical performance when snapshots are absent.
        """,
    ),
    _agent(
        "seo.standards_policy.v1",
        "Label each rule as mandatory, conditional, recommended, or heuristic. Do not rewrite scores.",
        "intelligence",
        list(range(3, 27)),
        ["policy.registry"],
        ["rule_version"],
        "deterministic",
        [
            "seo.crawlability.v1",
            "seo.indexability.v1",
            "seo.http_redirects.v1",
            "seo.sitemaps.v1",
            "seo.site_architecture.v1",
            "seo.rendering_js.v1",
            "seo.international.v1",
            "seo.performance.v1",
            "seo.mobile_parity.v1",
            "seo.https_security.v1",
            "seo.crawl_graph.v1",
            "seo.migration.v1",
            "seo.title_tags.v1",
            "seo.meta_descriptions.v1",
            "seo.headings_semantics.v1",
            "seo.content_quality.v1",
            "seo.image_media.v1",
            "seo.internal_links.v1",
            "seo.structured_data.v1",
            "seo.page_type.v1",
        ],
        """
        Validate proposed findings against Dristik's versioned SEO rules and current approved technical references
        supplied by the policy registry. Determine whether a rule is mandatory, conditional, recommended, or
        heuristic. Resolve exceptions based on page type and implementation context. Flag obsolete guidance,
        unsupported ranking claims, and rules that overstate search-engine requirements. Return the applicable
        rule version, rationale, exceptions, and recommended policy correction. Do not silently rewrite the scoring methodology.
        """,
    ),
    _agent(
        "seo.root_cause.v1",
        "Group related findings. Do not merge unrelated issues that share a symptom.",
        "assurance",
        [27],
        ["findings.validated"],
        ["finding_records"],
        "deterministic",
        ["seo.evidence_adjudicator.v1"],
        """
        Group related findings into candidate root causes, such as a faulty CMS template, shared routing logic, or
        inconsistent deployment configuration. Use shared evidence, affected templates, and reproducible patterns.
        Label causes as confirmed, strongly supported, plausible, or unknown. Do not merge unrelated findings simply
        because they share a symptom. Identify the smallest likely repair point, affected URL set, dependencies,
        and tests required to validate the diagnosis.
        """,
    ),
    _agent(
        "seo.remediation_engineer.v1",
        "Draft implementation steps for open findings. Illustrative code is not a deployed patch.",
        "assurance",
        [27],
        ["findings.approved_or_open", "stack.detected"],
        ["finding_records"],
        "interpretive",
        ["seo.roadmap.v1"],
        """
        Convert approved findings into actionable implementation instructions. Identify the affected file, component,
        template, CMS field, server rule, or configuration only when its location is known or explicitly marked as
        an example. Supply current behavior, intended behavior, exact code or configuration, prerequisites, and
        safe implementation steps. Include alternatives for unsupported stacks. Never present illustrative code as
        a patch already applied. Flag destructive changes and request required authorization.
        """,
        timeout=120,
    ),
    _agent(
        "seo.regression_tests.v1",
        "Write acceptance checks. Do not claim a test passed unless an execution result exists.",
        "assurance",
        [27],
        ["findings.remediation"],
        ["acceptance_criteria"],
        "deterministic",
        ["seo.remediation_engineer.v1"],
        """
        Translate each proposed remediation into testable acceptance criteria. Generate relevant unit, integration,
        HTTP, browser, sitemap, metadata, structured-data, and crawl regression tests. Include negative tests and
        edge cases, such as redirect loops and unintended noindex. Use the repository's actual language and
        framework when supplied; otherwise label code as illustrative. Identify risky assumptions, test coverage
        gaps, and rollback checks. Do not claim tests passed unless execution results are provided.
        """,
    ),
    _agent(
        "seo.evidence_adjudicator.v1",
        "Reject findings that lack evidence, over-generalize a sample, or contradict the record.",
        "assurance",
        list(range(1, 29)),
        ["evidence.ledger", "findings.proposed"],
        ["evidence_record"],
        "deterministic",
        [
            "seo.standards_policy.v1",
            "seo.keyword_mapping.v1",
            "seo.search_console.v1",
            "seo.backlinks.v1",
            "seo.competitor_benchmark.v1",
            "seo.organic_analytics.v1",
            "seo.historical_trends.v1",
        ],
        """
        Validate that each proposed finding has traceable evidence, correct scope, a reproducible rule, and a
        defensible conclusion. Detect stale snapshots, missing references, contradictory observations, duplicate
        issues, unsupported claims, and sample-to-site overgeneralization. Downgrade confidence or reject findings
        when evidence is insufficient. Preserve rejected findings and adjudication reasons in the audit history.
        Never invent evidence or repair a missing evidence record with a generated explanation.
        """,
    ),
    _agent(
        "seo.roadmap.v1",
        "Sequence validated findings. Do not invent traffic or revenue to justify priority.",
        "assurance",
        [28],
        ["findings.adjudicated"],
        ["finding_records"],
        "deterministic",
        ["seo.root_cause.v1", "seo.coverage_scoring.v1"],
        """
        Prioritize validated findings using deterministic severity, scope, confidence, business relevance,
        implementation effort, dependencies, and risk. Explain each priority in plain language. Do not manufacture
        traffic or revenue estimates to inflate impact. Separate urgent blockers from high-value improvements and
        optional enhancements. Produce sequenced 7/30/60/90-day work packages, suggested ownership, dependencies,
        and verification milestones. Leave numeric score calculation to the central policy engine.
        """,
    ),
    _agent(
        "seo.coverage_scoring.v1",
        "Report coverage and interpret scores the scoring service already stored.",
        "assurance",
        [1, 2, 28],
        ["scores.sealed", "coverage.ledger"],
        ["score_record", "coverage_record"],
        "deterministic",
        ["seo.evidence_adjudicator.v1"],
        """
        Inspect the completeness of audit coverage and interpret scores already computed by the deterministic
        scoring service. Report eligible checks, executed checks, evidence-backed outcomes, unavailable checks,
        and sampling coverage. Never invent a score or treat untested checks as passes. Identify domain or
        template coverage gaps and sensitivity to missing data. Recommend score disclosure and coverage gates
        that prevent misleading site-wide ratings.
        """,
    ),
    _agent(
        "seo.report_editor.v1",
        "Assemble the report from validated records. Do not fill gaps with invented metrics.",
        "assurance",
        list(range(1, 29)),
        ["findings.adjudicated", "coverage.ledger"],
        ["finding_records", "evidence_record"],
        "interpretive",
        ["seo.roadmap.v1"],
        """
        Convert validated audit records into a clear, complete report for executives, SEO specialists, engineers,
        and content owners. Preserve finding IDs, severity, evidence, confidence, affected scope, remediation,
        and unresolved limitations. Explain technical language in plain English without losing accuracy. Ensure
        every included finding has the required sections and every claimed fix has the correct status. Do not
        fabricate recommendations, success metrics, or missing content to make the report look complete.
        """,
        timeout=120,
    ),
    _agent(
        "seo.fix_verification.v1",
        "Compare a fresh crawl with the original finding. A deployment is not an SEO outcome.",
        "assurance",
        [27, 28],
        ["verification.rescan"],
        ["before_snapshot", "after_snapshot"],
        "deterministic",
        ["seo.regression_tests.v1"],
        """
        Compare pre-fix and post-fix evidence using the same relevant test conditions wherever possible. Verify
        the original condition, intended behavior, related regressions, and remaining scope. Return VERIFIED,
        PARTIALLY_VERIFIED, FAILED, or NOT_VERIFIABLE with evidence references. A code commit or successful
        deployment is not proof of an SEO outcome. Search indexing and ranking changes require separate
        observations and sufficient time. Keep the issue open when the live condition remains unresolved or
        evidence is inadequate.
        """,
    ),
)

_BASE_CATALOG: tuple[SEOAgentContract, ...] = AGENT_CATALOG


def _compose(base: tuple[SEOAgentContract, ...]) -> tuple[SEOAgentContract, ...]:
    from app.seo.enterprise.ai_catalog import AI_AGENTS, ROADMAP_REVIEW_DEPENDENCIES

    rows = []
    for agent in base:
        if agent.agent_id == "seo.roadmap.v1":
            dependencies = list(agent.dependencies)
            for dependency in ROADMAP_REVIEW_DEPENDENCIES:
                if dependency not in dependencies:
                    dependencies.append(dependency)
            rows.append(agent.model_copy(update={"dependencies": dependencies}))
        else:
            rows.append(agent)
    return tuple(rows) + AI_AGENTS


AGENT_CATALOG = _compose(_BASE_CATALOG)
AGENT_BY_ID = {agent.agent_id: agent for agent in AGENT_CATALOG}


def execution_order(catalog: tuple[SEOAgentContract, ...] = AGENT_CATALOG) -> list[str]:
    """Return a deterministic order that respects dependencies."""
    ids = [agent.agent_id for agent in catalog]
    known = set(ids)
    deps = {}
    for agent in catalog:
        missing = [dep for dep in agent.dependencies if dep not in known]
        if missing:
            raise ValueError(f"{agent.agent_id} depends on unknown agents: {missing}")
        deps[agent.agent_id] = list(agent.dependencies)
    order: list[str] = []
    remaining = set(ids)
    while remaining:
        ready = [agent_id for agent_id in ids if agent_id in remaining and all(dep in order for dep in deps[agent_id])]
        if not ready:
            raise ValueError("Enterprise SEO agent graph has a cycle")
        order.extend(ready)
        remaining.difference_update(ready)
    return order
