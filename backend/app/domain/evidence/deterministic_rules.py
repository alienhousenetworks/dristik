"""
Dristik AI Layer 2 — Deterministic Finding Engine
Zero-hallucination, deterministic rule execution against Layer 1 Machine Observations.
Every finding is strictly bound to its rule_id, evidence_ids, and confidence="certain".
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.domain.models import Finding, FindingEvidence, GroundedRecommendation, CrawlManifest
from app.domain.enums import Category, Severity, RubricConfidence, EvidenceConfidence, FindingClassification
from app.domain.evidence.store import EvidenceStore
from app.domain.evidence.models import MachineObservation


class DeterministicFindingEngine:
    """
    Executes deterministic rules over Layer 1 Machine Observations to emit
    auditable Layer 2 Findings.
    """

    def __init__(self):
        self._finding_counter = 0

    def _next_finding_id(self) -> str:
        self._finding_counter += 1
        return f"FND_{self._finding_counter:03d}"

    def evaluate(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
    ) -> List[Finding]:
        """
        Evaluate all deterministic rules against store observations.
        Returns list of finalized Layer 2 Finding objects.
        """
        findings: List[Finding] = []

        # Rule 1: TITLE_DUPLICATE_001
        findings.extend(self._check_duplicate_titles(store))

        # Rule 2: TITLE_MISSING_001
        findings.extend(self._check_missing_titles(store))

        # Rule 3: H1_MISSING_001
        findings.extend(self._check_missing_h1(store))

        # Rule 4: H1_MULTIPLE_001
        findings.extend(self._check_multiple_h1(store))

        # Rule 5: META_DESC_MISSING_001
        findings.extend(self._check_missing_meta_description(store))

        # Rule 6: STATUS_4XX_5XX_001
        findings.extend(self._check_http_errors(store))

        # Rule 7: SCHEMA_MISSING_001
        findings.extend(self._check_missing_schema(store))

        # Rule 8: SLOW_TTFB_001
        findings.extend(self._check_slow_ttfb(store))

        return findings

    def _check_duplicate_titles(self, store: EvidenceStore) -> List[Finding]:
        title_obs = store.get_observations_by_attribute("title")
        titles_by_val = defaultdict(list)
        for obs in title_obs:
            val = str(obs.value or "").strip().lower()
            if val and len(val) > 2:
                titles_by_val[val].append(obs)

        findings: List[Finding] = []
        for title_str, obs_list in titles_by_val.items():
            if len(obs_list) > 1:
                ev_ids = [o.evidence_id for o in obs_list]
                urls = [o.url for o in obs_list if o.url]
                fid = self._next_finding_id()
                raw_title = obs_list[0].value
                f = Finding(
                    finding_id=fid,
                    rule_id="TITLE_DUPLICATE_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.ON_PAGE_SEO,
                    severity=Severity.HIGH,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Duplicate Title Tag Across Multiple URLs: '{raw_title}'",
                    description=(
                        f"Deterministic inspection observed {len(obs_list)} pages sharing the exact identical "
                        f"title tag: '{raw_title}'. Duplicate title tags dilute organic search relevance and "
                        f"confuse AI crawler disambiguation across URLs: {', '.join(urls[:3])}."
                    ),
                    recommendation="Assign unique, intent-focused title tags to each distinct page URL.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change=f"Differentiate title tags across {len(obs_list)} URLs so each represents a unique intent.",
                        why="Duplicate titles cause search engines and generative models to conflate page intents.",
                        how_to_change="Update the `<title>` tag in each page template or CMS metadata header.",
                        example=f"<title>{raw_title} | Specific Category or Product Name</title>",
                        target_file="index.html / template",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="title",
                            value=str(o.value),
                            selector="title",
                            source=o.source,
                        )
                        for o in obs_list
                    ],
                )
                findings.append(f)
        return findings

    def _check_missing_titles(self, store: EvidenceStore) -> List[Finding]:
        title_obs = store.get_observations_by_attribute("title")
        findings: List[Finding] = []
        for o in title_obs:
            if not o.value or not str(o.value).strip():
                fid = self._next_finding_id()
                ev_ids = [o.evidence_id]
                f = Finding(
                    finding_id=fid,
                    rule_id="TITLE_MISSING_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.ON_PAGE_SEO,
                    severity=Severity.CRITICAL,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Missing Document Title Tag on {o.url or 'Page'}",
                    description=f"Deterministic HTML inspection revealed that page {o.url} completely lacks a `<title>` tag.",
                    recommendation="Add a descriptive, 50-60 character `<title>` tag inside `<head>`.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change="Insert a primary title tag in the document head.",
                        why="Title tags are required for indexing, search engine display, and AI answer citations.",
                        how_to_change="Add `<title>Brand Name — Primary Service</title>` to `<head>`.",
                        example="<title>Acme Corp — Modern Enterprise Infrastructure</title>",
                        target_file="index.html",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="title",
                            value="MISSING",
                            selector="title",
                            source=o.source,
                        )
                    ],
                )
                findings.append(f)
        return findings

    def _check_missing_h1(self, store: EvidenceStore) -> List[Finding]:
        h1_obs = store.get_observations_by_attribute("h1")
        findings: List[Finding] = []
        for o in h1_obs:
            is_empty = False
            if o.value is None:
                is_empty = True
            elif isinstance(o.value, list) and len(o.value) == 0:
                is_empty = True
            elif isinstance(o.value, str) and not o.value.strip():
                is_empty = True

            if is_empty:
                fid = self._next_finding_id()
                ev_ids = [o.evidence_id]
                f = Finding(
                    finding_id=fid,
                    rule_id="H1_MISSING_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.ON_PAGE_SEO,
                    severity=Severity.HIGH,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Missing Primary <h1> Heading on {o.url or 'Page'}",
                    description=f"Deterministic DOM parser observed zero `<h1>` heading elements on page {o.url}.",
                    recommendation="Add a single semantic `<h1>` element communicating the page's primary value proposition.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change="Add an H1 heading element directly above the main hero section.",
                        why="Search engines and AI crawlers rely on H1 tags to determine core document hierarchy.",
                        how_to_change="Wrap primary hero text in `<h1>` rather than generic `<div>` or `<span>`.",
                        example="<h1>Next-Generation Data Infrastructure for Modern Teams</h1>",
                        target_file="index.html",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="h1",
                            value="MISSING",
                            selector="h1",
                            source=o.source,
                        )
                    ],
                )
                findings.append(f)
        return findings

    def _check_multiple_h1(self, store: EvidenceStore) -> List[Finding]:
        h1_obs = store.get_observations_by_attribute("h1")
        findings: List[Finding] = []
        for o in h1_obs:
            if isinstance(o.value, list) and len(o.value) > 1:
                fid = self._next_finding_id()
                ev_ids = [o.evidence_id]
                f = Finding(
                    finding_id=fid,
                    rule_id="H1_MULTIPLE_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.ON_PAGE_SEO,
                    severity=Severity.MEDIUM,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Multiple ({len(o.value)}) <h1> Headings Found on {o.url or 'Page'}",
                    description=f"Page contains {len(o.value)} separate `<h1>` tags: {', '.join([str(x) for x in o.value[:3]])}.",
                    recommendation="Refactor document structure to preserve exactly one top-level `<h1>`, demoting secondary headings to `<h2>`.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change="Demote secondary <h1> tags to <h2>.",
                        why="A single H1 establishes clear topical hierarchy for search crawlers.",
                        how_to_change="Replace secondary <h1> elements with <h2>.",
                        example="<h2>Secondary Section Heading</h2>",
                        target_file="index.html",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="h1",
                            value=str(o.value),
                            selector="h1",
                            source=o.source,
                        )
                    ],
                )
                findings.append(f)
        return findings

    def _check_missing_meta_description(self, store: EvidenceStore) -> List[Finding]:
        desc_obs = store.get_observations_by_attribute("meta_description")
        findings: List[Finding] = []
        for o in desc_obs:
            if not o.value or not str(o.value).strip():
                fid = self._next_finding_id()
                ev_ids = [o.evidence_id]
                f = Finding(
                    finding_id=fid,
                    rule_id="META_DESC_MISSING_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.ON_PAGE_SEO,
                    severity=Severity.MEDIUM,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Missing Meta Description on {o.url or 'Page'}",
                    description=f"Page {o.url} has no `<meta name='description'>` tag.",
                    recommendation="Add a concise, 140-160 character meta description summarizing the page value.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change="Add a meta description tag in the head.",
                        why="Meta descriptions control click-through rate in search results.",
                        how_to_change="Add `<meta name='description' content='...'>` in `<head>`.",
                        example='<meta name="description" content="Explore enterprise solutions designed for speed and reliability.">',
                        target_file="index.html",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="meta_description",
                            value="MISSING",
                            selector='meta[name="description"]',
                            source=o.source,
                        )
                    ],
                )
                findings.append(f)
        return findings

    def _check_http_errors(self, store: EvidenceStore) -> List[Finding]:
        status_obs = store.get_observations_by_attribute("status_code")
        findings: List[Finding] = []
        for o in status_obs:
            try:
                code = int(o.value)
                if code >= 400:
                    fid = self._next_finding_id()
                    ev_ids = [o.evidence_id]
                    f = Finding(
                        finding_id=fid,
                        rule_id="STATUS_4XX_5XX_001",
                        evidence_ids=ev_ids,
                        evidence_refs=ev_ids,
                        category=Category.TECHNICAL_SEO,
                        severity=Severity.CRITICAL if code >= 500 else Severity.HIGH,
                        classification=FindingClassification.VERIFIED_DEFECT,
                        confidence=1.0,
                        confidence_label=EvidenceConfidence.CONFIRMED,
                        confidence_rubric=RubricConfidence.VERIFIED,
                        title=f"HTTP {code} Error Status Recorded on {o.url}",
                        description=f"Server returned HTTP status {code} when requested at {o.url}.",
                        recommendation="Resolve broken URL endpoint, configure proper 301 redirect, or repair origin service.",
                        grounded_recommendation=GroundedRecommendation(
                            recommendation_id=f"REC_{fid}",
                            underlying_finding_id=fid,
                            underlying_evidence_ids=ev_ids,
                            what_to_change=f"Fix endpoint {o.url} to return HTTP 200 or 301.",
                            why="Error responses prevent indexation and waste crawler budget.",
                            how_to_change="Check web server routing or server-side application logs.",
                            example="Redirect 301 /old-url /new-url",
                            target_file="server.conf / .htaccess",
                        ),
                        evidence=[
                            FindingEvidence(
                                evidence_id=o.evidence_id,
                                url=o.url,
                                element="status_code",
                                value=str(code),
                                selector="http_status",
                                source=o.source,
                            )
                        ],
                    )
                    findings.append(f)
            except (ValueError, TypeError):
                pass
        return findings

    def _check_missing_schema(self, store: EvidenceStore) -> List[Finding]:
        schema_obs = store.get_observations_by_attribute("schema_types")
        findings: List[Finding] = []
        for o in schema_obs:
            is_empty = False
            if not o.value:
                is_empty = True
            elif isinstance(o.value, list) and len(o.value) == 0:
                is_empty = True

            if is_empty:
                fid = self._next_finding_id()
                ev_ids = [o.evidence_id]
                f = Finding(
                    finding_id=fid,
                    rule_id="SCHEMA_MISSING_001",
                    evidence_ids=ev_ids,
                    evidence_refs=ev_ids,
                    category=Category.SCHEMA,
                    severity=Severity.HIGH,
                    classification=FindingClassification.VERIFIED_DEFECT,
                    confidence=1.0,
                    confidence_label=EvidenceConfidence.CONFIRMED,
                    confidence_rubric=RubricConfidence.VERIFIED,
                    title=f"Missing Structured Data (Schema.org) on {o.url or 'Page'}",
                    description=f"No JSON-LD or Microdata structured data detected on page {o.url}.",
                    recommendation="Add Organization or WebSite JSON-LD schema with canonical entity metadata.",
                    grounded_recommendation=GroundedRecommendation(
                        recommendation_id=f"REC_{fid}",
                        underlying_finding_id=fid,
                        underlying_evidence_ids=ev_ids,
                        what_to_change="Deploy valid Schema.org JSON-LD in the document head.",
                        why="Structured data enables rich snippet generation and accurate AI engine knowledge graph entity extraction.",
                        how_to_change="Embed `<script type='application/ld+json'>` defining the entity.",
                        example='<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Acme"}</script>',
                        target_file="index.html",
                    ),
                    evidence=[
                        FindingEvidence(
                            evidence_id=o.evidence_id,
                            url=o.url,
                            element="schema_types",
                            value="MISSING",
                            selector='script[type="application/ld+json"]',
                            source=o.source,
                        )
                    ],
                )
                findings.append(f)
        return findings

    def _check_slow_ttfb(self, store: EvidenceStore) -> List[Finding]:
        ttfb_obs = store.get_observations_by_attribute("ttfb_ms")
        findings: List[Finding] = []
        for o in ttfb_obs:
            try:
                ttfb_val = float(o.value)
                if ttfb_val > 1200.0:
                    fid = self._next_finding_id()
                    ev_ids = [o.evidence_id]
                    f = Finding(
                        finding_id=fid,
                        rule_id="SLOW_TTFB_001",
                        evidence_ids=ev_ids,
                        evidence_refs=ev_ids,
                        category=Category.TECHNICAL_SEO,
                        severity=Severity.HIGH,
                        classification=FindingClassification.VERIFIED_DEFECT,
                        confidence=1.0,
                        confidence_label=EvidenceConfidence.CONFIRMED,
                        confidence_rubric=RubricConfidence.VERIFIED,
                        title=f"Excessive Server Response Time (TTFB: {ttfb_val:.0f}ms) on {o.url or 'Page'}",
                        description=f"Measured server Time-to-First-Byte was {ttfb_val:.0f}ms, exceeding Google's 800ms recommended threshold.",
                        recommendation="Enable edge caching (CDN) or optimize backend database queries to bring TTFB below 600ms.",
                        grounded_recommendation=GroundedRecommendation(
                            recommendation_id=f"REC_{fid}",
                            underlying_finding_id=fid,
                            underlying_evidence_ids=ev_ids,
                            what_to_change="Optimize origin latency or configure edge cache headers.",
                            why="Slow initial byte delivery impairs Core Web Vitals and increases crawl budget exhaustion.",
                            how_to_change="Deploy Cloudflare or fast origin caching headers.",
                            example="Cache-Control: public, max-age=3600, s-maxage=86400",
                            target_file="nginx.conf / edge CDN",
                        ),
                        evidence=[
                            FindingEvidence(
                                evidence_id=o.evidence_id,
                                url=o.url,
                                element="ttfb_ms",
                                value=f"{ttfb_val:.0f}ms",
                                selector="network_ttfb",
                                source=o.source,
                            )
                        ],
                    )
                    findings.append(f)
            except (ValueError, TypeError):
                pass
        return findings
