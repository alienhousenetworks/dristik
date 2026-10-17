"""
Dristik AI First-Class Evidence Taxonomy & Epistemic Hierarchy

Defines explicit evidence classes and modalities to separate:
1. OBSERVED: Directly measured (DOM, HTTP, AST, Headers, Screenshot, Accessibility tree, Schema)
2. EXTERNALLY_VERIFIED: Confirmed through an external source (Search, Business directory, Company profile, Certificate registry, GSC, Analytics)
3. MODEL_INFERRED: LLM interpretation of observed evidence (Semantic synthesis, Entity deduction)
4. HYPOTHESIS: Potential issue requiring verification (Single-source unverified, Working hypothesis)
5. RECOMMENDATION: Proposed remediation (Code patch, Schema fix, Infrastructure directive)
"""
from typing import Dict, Any, List, Optional
from app.domain.enums import EvidenceClass, EvidenceSubtype
from app.domain.models import Finding, FindingEvidence, EvidenceTaxonomyReport


TAXONOMY_SPEC = {
    EvidenceClass.OBSERVED: {
        "label": "OBSERVED",
        "title": "Directly Measured",
        "epistemic_level": "Level 1 · Deterministic Ground Truth",
        "description": "Direct empirical measurement captured from browser runtime, HTTP network transactions, or DOM/AST syntax trees. 100% verifiable via browser DevTools or curl.",
        "badge_color": "emerald",
        "subtypes": [
            {"id": "DOM", "name": "DOM Node Extraction", "description": "Raw HTML element, selector, or attribute directly extracted from crawled markup."},
            {"id": "HTTP", "name": "HTTP Response / Status", "description": "Direct server response headers, status codes (200, 301, 404), or TTFB timings."},
            {"id": "AST", "name": "AST Syntax Tree", "description": "Structured syntax parse of JavaScript bundles, CSS stylesheets, or structured data."},
            {"id": "HEADERS", "name": "Security & Network Headers", "description": "Content-Security-Policy, HSTS, X-Frame-Options, or Cache-Control headers."},
            {"id": "SCREENSHOT", "name": "Visual Render Snapshot", "description": "Pixel-rendered viewport screenshot verifying visual above-the-fold display."},
            {"id": "ACCESSIBILITY_TREE", "name": "Accessibility Tree", "description": "AXTree accessible roles, aria attributes, and contrast ratios."},
            {"id": "SCHEMA", "name": "JSON-LD & Microdata Schema", "description": "Extracted and validated schema.org structured data payloads."},
        ],
    },
    EvidenceClass.EXTERNALLY_VERIFIED: {
        "label": "EXTERNALLY VERIFIED",
        "title": "Confirmed Through External Source",
        "epistemic_level": "Level 2 · Corroborated External Signal",
        "description": "Cross-referenced and validated against external authoritative databases, search engine APIs, or public registries.",
        "badge_color": "blue",
        "subtypes": [
            {"id": "SEARCH", "name": "Live Search Query Result", "description": "Confirmed indexing, ranking snippet, or SERP presence via live search queries."},
            {"id": "BUSINESS_DIRECTORY", "name": "Business Directory / Registries", "description": "Company registration, MCA/SEC records, or verified directory listings."},
            {"id": "COMPANY_PROFILE", "name": "Corporate Profile / Crunchbase / LinkedIn", "description": "Corroborated firmographic data from official public social and market profiles."},
            {"id": "CERTIFICATE_REGISTRY", "name": "Certificate & DNS Registry", "description": "TLS/SSL certificate authority logs, WHOIS registration, and DNS records."},
            {"id": "GSC", "name": "Google Search Console", "description": "Direct first-party search performance, impressions, and index status via GSC API."},
            {"id": "ANALYTICS", "name": "Verified Web Analytics", "description": "GA4, PostHog, or server-side telemetry confirming visitor traffic and bounce rates."},
        ],
    },
    EvidenceClass.MODEL_INFERRED: {
        "label": "MODEL-INFERRED",
        "title": "LLM Interpretation of Observed Evidence",
        "epistemic_level": "Level 3 · Cognitive Model Deduction",
        "description": "Deductive synthesis derived by neural reasoning agents based on measured facts. This represents cognitive analysis, not a raw physical measurement.",
        "badge_color": "purple",
        "subtypes": [
            {"id": "LLM_INTERPRETATION", "name": "Generative Deduction", "description": "LLM qualitative evaluation of value proposition, tone, and positioning."},
            {"id": "SEMANTIC_SYNTHESIS", "name": "Semantic Entity Extraction", "description": "Embedding similarity analysis comparing website claims against market entity graphs."},
            {"id": "COGNITIVE_REASONING", "name": "Market Psychology & Answerability", "description": "Synthesized assessment of how LLM search engines (Perplexity, ChatGPT) parse the content."},
        ],
    },
    EvidenceClass.HYPOTHESIS: {
        "label": "HYPOTHESIS",
        "title": "Potential Issue Requiring Verification",
        "epistemic_level": "Level 4 · Working Hypothesis / Single-Source",
        "description": "Provisional flag or single-observation signal that requires manual developer check or multi-source corroboration before deployment.",
        "badge_color": "amber",
        "subtypes": [
            {"id": "SINGLE_SOURCE_UNVERIFIED", "name": "Single-Source Unverified", "description": "Observed in crawl but uncorroborated by external sources or repeated crawls."},
            {"id": "WORKING_HYPOTHESIS", "name": "Working Hypothesis", "description": "Heuristic suspicion of performance bottleneck or tracking deficit awaiting re-test."},
            {"id": "UNVERIFIED_ANOMALY", "name": "Unverified Behavioral Anomaly", "description": "Unexplained variance in TTFB or rendering requiring deeper server trace."},
        ],
    },
    EvidenceClass.RECOMMENDATION: {
        "label": "RECOMMENDATION",
        "title": "Proposed Remediation",
        "epistemic_level": "Level 5 · Actionable Engineering Intervention",
        "description": "Deterministic code fix, configuration update, or strategic rewrite designed to eliminate an identified defect.",
        "badge_color": "indigo",
        "subtypes": [
            {"id": "CODE_PATCH", "name": "Verified Code Patch", "description": "Drop-in HTML, React, or Astro code replacement addressing verified DOM defect."},
            {"id": "CONFIG_CHANGE", "name": "Server & CDN Config", "description": "Nginx, Cloudflare, or robots.txt configuration modification."},
            {"id": "CONTENT_REWRITE", "name": "Positioning / Copy Rewrite", "description": "High-clarity copywriting replacement improving customer comprehension."},
            {"id": "STRATEGIC_DIRECTIVE", "name": "Architectural Directive", "description": "Roadmap recommendation for leadership or engineering teams."},
        ],
    },
}


def classify_finding(finding: Finding) -> tuple[EvidenceClass, str]:
    """
    Deterministically assigns an EvidenceClass and EvidenceSubtype to a Finding
    based on its empirical evidence, source integrity, and confidence rubric.
    """
    desc = f"{finding.title} {finding.description} {finding.finding}".lower()
    
    # Check for Hypothesis / Single-Source
    if (
        finding.source_integrity_label == "SINGLE_SOURCE_UNVERIFIED"
        or "single-source unverified" in desc
        or "working hypothesis" in desc
        or "hypothesis" in desc
    ):
        return EvidenceClass.HYPOTHESIS, "SINGLE_SOURCE_UNVERIFIED"

    # Check for External Verification
    has_external = any(
        (ev.type == "external_ground_truth" or (ev.evidence_id and ev.evidence_id.startswith("ext_")))
        for ev in (finding.evidence or [])
    ) or finding.source_integrity_label == "CORROBORATED"
    if has_external:
        if "gsc" in desc or "search console" in desc:
            return EvidenceClass.EXTERNALLY_VERIFIED, "GSC"
        if "registry" in desc or "ssl" in desc or "cert" in desc:
            return EvidenceClass.EXTERNALLY_VERIFIED, "CERTIFICATE_REGISTRY"
        return EvidenceClass.EXTERNALLY_VERIFIED, "SEARCH"

    # Check for Directly Observed DOM / Technical Facts
    has_dom_selector = any(bool(ev.selector or ev.element) for ev in (finding.evidence or []))
    is_technical = finding.category.value in ["TECHNICAL_SEO", "SCHEMA"]
    is_observed_keyword = any(
        kw in desc
        for kw in [
            "dom", "h1", "meta description", "robots.txt", "sitemap", "http 200", "404",
            "json-ld", "schema", "viewport", "canonical", "ttfb", "latency", "headers"
        ]
    )

    if has_dom_selector or (is_technical and (finding.evidence or is_observed_keyword)):
        if "schema" in desc or "json-ld" in desc or finding.category.value == "SCHEMA":
            return EvidenceClass.OBSERVED, "SCHEMA"
        if "header" in desc or "status code" in desc or "http" in desc or "ttfb" in desc:
            return EvidenceClass.OBSERVED, "HTTP"
        return EvidenceClass.OBSERVED, "DOM"

    # Pure recommendation without distinct finding context
    if "recommendation" in desc and not finding.evidence:
        return EvidenceClass.RECOMMENDATION, "STRATEGIC_DIRECTIVE"

    # Default to Model Inferred for qualitative / positioning / heuristic claims
    return EvidenceClass.MODEL_INFERRED, "SEMANTIC_SYNTHESIS"


def assign_evidence_scope(finding: Finding, sample_size: int = 0) -> None:
    """
    Sets how far the finding was checked. Does not change evidence_class.
    A header seen on fetched responses is origin-verified, not a full-site scan.
    """
    from app.domain.enums import EvidenceScope

    urls: List[str] = []
    for ev in finding.evidence or []:
        url = getattr(ev, "url", None)
        if url:
            urls.append(str(url))
    unique = list(dict.fromkeys(urls))
    subtype = (finding.evidence_subtype or "").upper()
    blob = f"{finding.title} {finding.description} {finding.finding}".lower()
    sample = sample_size or len(unique)

    if finding.evidence_class == EvidenceClass.EXTERNALLY_VERIFIED:
        finding.evidence_scope = EvidenceScope.EXTERNAL_MEASURED.value
        finding.scope_hit_count = len(unique) or None
        finding.scope_sample_size = sample or None
        return

    header_markers = (
        "content-security-policy", "strict-transport-security", "hsts",
        "x-frame-options", "x-content-type-options", "referrer-policy",
        "permissions-policy", "security header",
    )
    if subtype == "HEADERS" or any(marker in blob for marker in header_markers):
        finding.evidence_scope = EvidenceScope.ORIGIN_VERIFIED.value
        finding.scope_hit_count = len(unique) or 1
        finding.scope_sample_size = max(sample, finding.scope_hit_count)
        return

    if "sitemap" in blob and "index" in blob and finding.evidence_class == EvidenceClass.OBSERVED:
        finding.evidence_scope = EvidenceScope.INDEX_OBSERVED.value
        finding.scope_hit_count = len(unique) or None
        finding.scope_sample_size = sample or None
        return

    if finding.evidence_class in (
        EvidenceClass.MODEL_INFERRED,
        EvidenceClass.HYPOTHESIS,
        EvidenceClass.RECOMMENDATION,
    ):
        finding.evidence_scope = EvidenceScope.SITE_INFERRED.value
        finding.scope_hit_count = len(unique) or None
        finding.scope_sample_size = sample or None
        return

    if len(unique) >= 2:
        finding.evidence_scope = EvidenceScope.SAMPLE_VERIFIED.value
        finding.scope_hit_count = len(unique)
        finding.scope_sample_size = sample
        return

    if len(unique) == 1 or finding.evidence_class == EvidenceClass.OBSERVED:
        finding.evidence_scope = EvidenceScope.PAGE_VERIFIED.value
        finding.scope_hit_count = 1 if unique else None
        finding.scope_sample_size = sample or (1 if unique else None)
        return

    finding.evidence_scope = EvidenceScope.SITE_INFERRED.value


def generate_evidence_taxonomy_report(
    findings: List[Finding],
    evidence_ledger: Optional[Dict[str, Any]] = None,
    sample_size: int = 0,
) -> EvidenceTaxonomyReport:
    """
    Computes summary metrics, counts, and epistemic integrity across all findings and ledger items.
    """
    evidence_ledger = evidence_ledger or {}
    class_counts: Dict[str, int] = {
        EvidenceClass.OBSERVED.value: 0,
        EvidenceClass.EXTERNALLY_VERIFIED.value: 0,
        EvidenceClass.MODEL_INFERRED.value: 0,
        EvidenceClass.HYPOTHESIS.value: 0,
        EvidenceClass.RECOMMENDATION.value: 0,
    }
    subtype_counts: Dict[str, int] = {}

    for f in findings:
        ev_class, ev_subtype = classify_finding(f)
        f.evidence_class = ev_class
        f.evidence_subtype = ev_subtype
        f.epistemic_level = TAXONOMY_SPEC[ev_class]["epistemic_level"]
        assign_evidence_scope(f, sample_size=sample_size)

        class_counts[ev_class.value] = class_counts.get(ev_class.value, 0) + 1
        subtype_counts[ev_subtype] = subtype_counts.get(ev_subtype, 0) + 1

        # Also classify inline evidence items if present
        for ev in (f.evidence or []):
            ev.evidence_class = ev_class
            ev.evidence_subtype = ev_subtype

    total_findings = len(findings)
    observed_verified = (
        class_counts[EvidenceClass.OBSERVED.value] + class_counts[EvidenceClass.EXTERNALLY_VERIFIED.value]
    )
    integrity_score = round((observed_verified / max(1, total_findings)) * 100, 1)

    total_nodes = total_findings + len(evidence_ledger)

    classes_breakdown = []
    for cls_enum, spec in TAXONOMY_SPEC.items():
        count = class_counts.get(cls_enum.value, 0)
        pct = round((count / max(1, total_findings)) * 100, 1)
        classes_breakdown.append({
            "class_id": cls_enum.value,
            "label": spec["label"],
            "title": spec["title"],
            "epistemic_level": spec["epistemic_level"],
            "description": spec["description"],
            "badge_color": spec["badge_color"],
            "count": count,
            "percentage": pct,
            "subtypes": spec["subtypes"],
        })

    return EvidenceTaxonomyReport(
        total_evidence_nodes=total_nodes,
        epistemic_integrity_score=integrity_score,
        class_counts=class_counts,
        subtype_counts=subtype_counts,
        classes_breakdown=classes_breakdown,
        description=(
            f"Dristik Epistemic Taxonomy: {observed_verified}/{total_findings} findings ({integrity_score}%) "
            f"are anchored directly in empirical OBSERVED DOM or EXTERNALLY VERIFIED records."
        ),
    )
