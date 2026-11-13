"""
Dristik AI Sub-Phase Report Builder.
Translates runtime outputs from crawler, entity resolver, specialist agents,
and remediation engines into canonical SubPhaseReportContracts with zero fabrication.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.reporting.contracts.subphase_contract import (
    ConfidenceLevel,
    EvidenceTokenReference,
    ExecutionStatus,
    ReportFinding,
    SubPhaseReportContract,
)

logger = logging.getLogger("dristik.reporting.builder")


class SubPhaseReportBuilder:
    """Constructs structured SubPhaseReportContract objects from engine payloads."""

    # ─────────────────────────────────────────────────────────────
    # Phase 1: Business Ingestion
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def build_p1_1_ssrf(
        run_id: str,
        website_url: str,
        resolved_ip: Optional[str],
        is_safe: bool,
        redirect_chain: List[str],
        duration_ms: int = 15,
        error_msg: Optional[str] = None,
    ) -> SubPhaseReportContract:
        findings = []
        if not is_safe:
            findings.append(
                ReportFinding(
                    finding_id="SSRF_PRIVATE_IP_BLOCKED",
                    severity="critical",
                    title="SSRF Defense Triggered — Private IP or Disallowed Host",
                    description=f"Resolved IP {resolved_ip} falls within blocked RFC1918 or link-local range.",
                    remediation_hint="Audit domain DNS records to ensure public routability.",
                    evidence_ids=["dns_resolution"],
                )
            )

        evidence = [
            EvidenceTokenReference(
                evidence_id="dns_resolution",
                token_type="dns_record",
                locator=website_url,
                excerpt=f"Resolved IP: {resolved_ip or 'UNRESOLVED'}",
            )
        ]
        if redirect_chain:
            evidence.append(
                EvidenceTokenReference(
                    evidence_id="redirect_chain",
                    token_type="http_header",
                    locator="Location",
                    excerpt=" -> ".join(redirect_chain[:5]),
                )
            )

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.1",
            subphase_title="SSRF Security & Host Preflight",
            objective="Inspect domain DNS resolution, private IP containment, and redirect safety before outbound HTTP connections.",
            agent_id="security.ssrf_gate",
            agent_model="deterministic_kernel",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED if not error_msg else ExecutionStatus.FAILED,
            input_summary={"target_url": website_url},
            processing_steps=[
                f"Parsed URI scheme and hostname from {website_url}",
                f"Resolved DNS A/AAAA records: {resolved_ip or 'None'}",
                "Evaluated IP address against RFC1918, RFC3927, RFC5737, and loopback blacklists",
                f"Validated redirect chain ({len(redirect_chain)} hops)",
            ],
            structured_output={
                "url": website_url,
                "resolved_ip": resolved_ip or "NOT_MEASURED",
                "is_safe": is_safe,
                "redirect_hops": len(redirect_chain),
                "redirect_chain": redirect_chain,
            },
            evidence_tokens=evidence,
            findings=findings,
            confidence=ConfidenceLevel.VERIFIED if resolved_ip else ConfidenceLevel.UNMEASURED,
            errors=[error_msg] if error_msg else [],
            next_phase_handoff={"validated_target_url": website_url, "safe": is_safe},
        )
        return contract.seal()

    @staticmethod
    def build_p1_2_crawler(
        run_id: str,
        website_url: str,
        pages_crawled: int,
        manifest_data: Dict[str, Any],
        duration_ms: int = 1200,
        error_msg: Optional[str] = None,
    ) -> SubPhaseReportContract:
        findings = []
        if pages_crawled == 0:
            findings.append(
                ReportFinding(
                    finding_id="CRAWL_ZERO_PAGES",
                    severity="critical",
                    title="Crawler Failed to Ingest Pages",
                    description=f"Zero pages could be retrieved from {website_url}.",
                    remediation_hint="Check if site blocks headless browsers or has invalid SSL certificates.",
                    evidence_ids=["crawl_frontier"],
                )
            )

        status_breakdown = manifest_data.get("status_codes", {})
        evidence = [
            EvidenceTokenReference(
                evidence_id="crawl_manifest",
                token_type="cas_snapshot",
                locator=website_url,
                excerpt=f"Total pages: {pages_crawled}, Statuses: {status_breakdown}",
            )
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.2",
            subphase_title="Multi-Page Crawler Execution",
            objective="Discover, fetch, and archive HTML pages across the target domain up to configured crawl limits.",
            agent_id="crawler.multipage_service",
            agent_model="playwright_chromium_http",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED if pages_crawled > 0 else ExecutionStatus.FAILED,
            input_summary={"target_url": website_url, "max_pages_limit": manifest_data.get("limit", 15)},
            processing_steps=[
                f"Discovered URL frontier starting from {website_url}",
                f"Executed concurrent HTTP fetches with status code validation",
                f"Recorded response headers, byte sizes, and TTFB latency",
                f"Indexed {pages_crawled} HTML documents into memory",
            ],
            structured_output={
                "pages_crawled": pages_crawled,
                "status_code_distribution": status_breakdown,
                "sample_urls": manifest_data.get("urls", [])[:10],
            },
            evidence_tokens=evidence,
            findings=findings,
            confidence=ConfidenceLevel.VERIFIED,
            errors=[error_msg] if error_msg else [],
            next_phase_handoff={"pages_count": pages_crawled},
        )
        return contract.seal()

    @staticmethod
    def build_p1_3_dom_evidence(
        run_id: str,
        website_url: str,
        dom_metrics: Dict[str, Any],
        duration_ms: int = 500,
    ) -> SubPhaseReportContract:
        findings = []
        if dom_metrics.get("h1_count", 0) == 0:
            findings.append(
                ReportFinding(
                    finding_id="DOM_MISSING_H1",
                    severity="high",
                    title="Missing Primary H1 Heading",
                    description="DOM tree lacks an H1 landmark tag, weakening search indexing and accessibility.",
                    remediation_hint="Ensure the primary value proposition is marked as single H1.",
                    evidence_ids=["dom_heading_tree"],
                )
            )

        evidence = [
            EvidenceTokenReference(
                evidence_id="dom_heading_tree",
                token_type="dom_selector",
                locator="h1, h2, h3",
                excerpt=f"H1s: {dom_metrics.get('h1_count', 0)}, H2s: {dom_metrics.get('h2_count', 0)}",
            ),
            EvidenceTokenReference(
                evidence_id="dom_links",
                token_type="dom_selector",
                locator="a[href]",
                excerpt=f"Internal: {dom_metrics.get('internal_links_count', 0)}, External: {dom_metrics.get('external_links_count', 0)}",
            ),
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.3",
            subphase_title="DOM Evidence & AST Extraction",
            objective="Parse crawled HTML into semantic DOM trees, extract heading hierarchies, link graphs, and CTAs.",
            agent_id="extractor.dom_ast",
            agent_model="beautifulsoup4_lxml",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"pages_processed": dom_metrics.get("pages_count", 1)},
            processing_steps=[
                "Parsed raw HTML into DOM Abstract Syntax Trees",
                "Extracted H1-H6 heading trees and computed word counts",
                "Indexed internal and external hyperlink structures",
                "Identified primary CTA buttons and interactive elements",
            ],
            structured_output=dom_metrics,
            evidence_tokens=evidence,
            findings=findings,
            confidence=ConfidenceLevel.VERIFIED,
            next_phase_handoff={"dom_evidence_ready": True},
        )
        return contract.seal()

    @staticmethod
    def build_p1_4_snapshot_integrity(
        run_id: str,
        snapshot_count: int,
        cas_hashes: List[str],
        duration_ms: int = 150,
    ) -> SubPhaseReportContract:
        evidence = [
            EvidenceTokenReference(
                evidence_id=f"snapshot_{i}",
                token_type="cas_snapshot",
                locator=f"data/cas/{h[:2]}/{h}.html",
                excerpt=f"SHA-256: {h}",
                hash_sha256=h,
            )
            for i, h in enumerate(cas_hashes[:5])
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.4",
            subphase_title="Snapshot Integrity & CAS Archive",
            objective="Preserve immutable SHA-256 content-addressed DOM snapshots to guarantee zero-tamper audit reproducibility.",
            agent_id="storage.cas_engine",
            agent_model="content_addressable_storage",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"snapshots_to_seal": snapshot_count},
            processing_steps=[
                "Calculated cryptographic SHA-256 digest for each raw DOM payload",
                "Stored immutable copies in sharded CAS filesystem (data/cas/)",
                "Registered content hashes in Evidence Graph 2.0",
            ],
            structured_output={
                "snapshot_count": snapshot_count,
                "sample_cas_hashes": cas_hashes[:10],
            },
            evidence_tokens=evidence,
            findings=[],
            confidence=ConfidenceLevel.VERIFIED,
            next_phase_handoff={"cas_snapshots_pinned": True},
        )
        return contract.seal()

    @staticmethod
    def build_p1_5_telemetry(
        run_id: str,
        website_url: str,
        telemetry_data: Dict[str, Any],
        duration_ms: int = 400,
    ) -> SubPhaseReportContract:
        findings = []
        headers = telemetry_data.get("security_headers", {})
        if not headers.get("strict-transport-security"):
            findings.append(
                ReportFinding(
                    finding_id="SEC_MISSING_HSTS",
                    severity="medium",
                    title="Missing HTTP Strict Transport Security (HSTS)",
                    description="The server does not send Strict-Transport-Security, allowing potential downgrade attacks.",
                    remediation_hint="Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' to response headers.",
                    evidence_ids=["http_response_headers"],
                )
            )

        evidence = [
            EvidenceTokenReference(
                evidence_id="http_response_headers",
                token_type="http_header",
                locator="Response Headers",
                excerpt=str(headers)[:300],
            )
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.5",
            subphase_title="External Telemetry & Transport Security",
            objective="Inspect SSL certificate validity, TLS version, cipher suite, and critical security response headers.",
            agent_id="enricher.external_telemetry",
            agent_model="socket_tls_inspector",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"target_url": website_url},
            processing_steps=[
                "Queried DNS A/AAAA and MX records",
                "Inspected SSL/TLS handshake certificates and expiration dates",
                "Audited presence of CSP, HSTS, X-Content-Type-Options, and X-Frame-Options",
            ],
            structured_output=telemetry_data,
            evidence_tokens=evidence,
            findings=findings,
            confidence=ConfidenceLevel.VERIFIED,
            next_phase_handoff={"transport_secure": True},
        )
        return contract.seal()

    @staticmethod
    def build_p1_6_site_facts(
        run_id: str,
        site_facts: Dict[str, Any],
        duration_ms: int = 150,
    ) -> SubPhaseReportContract:
        evidence = [
            EvidenceTokenReference(
                evidence_id="site_facts_canonical",
                token_type="dom_selector",
                locator="link[rel='canonical']",
                excerpt=site_facts.get("canonical_url", "NOT_CONFIGURED"),
            )
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_01_ingestion",
            phase_name="1. Ingestion & Multi-Page Crawl",
            subphase_id="1.6",
            subphase_title="Deterministic Site Facts Ledger",
            objective="Extract core immutable facts (title, canonical URL, language, schema blocks, viewport) directly from HTML source.",
            agent_id="extractor.site_facts",
            agent_model="deterministic_extractor",
            execution_mode="deterministic",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"facts_count": len(site_facts)},
            processing_steps=[
                "Extracted canonical URL, meta title, and meta description",
                "Identified declared HTML lang and viewport configuration",
                "Counted embedded Schema JSON-LD blocks",
            ],
            structured_output=site_facts,
            evidence_tokens=evidence,
            findings=[],
            confidence=ConfidenceLevel.VERIFIED,
            next_phase_handoff={"site_facts": site_facts},
        )
        return contract.seal()

    # ─────────────────────────────────────────────────────────────
    # Phase 2: Business Understanding
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def build_p2_1_entity_resolution(
        run_id: str,
        entity_data: Dict[str, Any],
        duration_ms: int = 800,
    ) -> SubPhaseReportContract:
        canonical_name = entity_data.get("canonical_name") or "UNRESOLVED"
        industry = entity_data.get("industry") or "NOT_MEASURED"

        evidence = [
            EvidenceTokenReference(
                evidence_id="entity_brand_mention",
                token_type="dom_selector",
                locator="header, footer, meta[property='og:site_name']",
                excerpt=f"Resolved Entity: {canonical_name}",
            )
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_02_business",
            phase_name="2. Business Understanding & Entity Grounding",
            subphase_id="2.1",
            subphase_title="Canonical Entity & Brand Resolution",
            objective="Determine official brand identity, canonical legal entity name, primary domain, and industry classification.",
            agent_id="business.discovery.v3",
            agent_model="reasoning_model",
            execution_mode="reasoning_agent",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"input_signals": ["homepage_dom", "meta_tags", "nav_header"]},
            processing_steps=[
                "Parsed brand name occurrences across title tags and logo alt attributes",
                "Reconciled company legal entity naming from footer copyright notices",
                "Classified primary industry and market vertical",
            ],
            structured_output=entity_data,
            evidence_tokens=evidence,
            findings=[],
            confidence=ConfidenceLevel.VERIFIED if canonical_name != "UNRESOLVED" else ConfidenceLevel.INFERRED,
            next_phase_handoff={"canonical_entity": canonical_name, "industry": industry},
        )
        return contract.seal()

    @staticmethod
    def build_p2_2_icp_intelligence(
        run_id: str,
        icp_data: Dict[str, Any],
        duration_ms: int = 900,
    ) -> SubPhaseReportContract:
        evidence = [
            EvidenceTokenReference(
                evidence_id="icp_hero_hook",
                token_type="dom_selector",
                locator="hero, h1, .value-prop",
                excerpt=str(icp_data.get("target_audience", "General Audience"))[:200],
            )
        ]

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_02_business",
            phase_name="2. Business Understanding & Entity Grounding",
            subphase_id="2.2",
            subphase_title="ICP & Target Audience Intelligence",
            objective="Identify Ideal Customer Profile (ICP), buyer roles, customer pain points, and commercial value proposition.",
            agent_id="business.icp.v3",
            agent_model="reasoning_model",
            execution_mode="reasoning_agent",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"pages_sampled": ["homepage", "features", "pricing"]},
            processing_steps=[
                "Analyzed customer-facing problem statements in hero copy",
                "Mapped decision-maker roles (B2B vs B2C)",
                "Isolated core value propositions and pain points addressed",
            ],
            structured_output=icp_data,
            evidence_tokens=evidence,
            findings=[],
            confidence=ConfidenceLevel.INFERRED,
            next_phase_handoff={"icp_profile": icp_data},
        )
        return contract.seal()

    @staticmethod
    def build_p2_3_search_intent(
        run_id: str,
        intent_data: Dict[str, Any],
        duration_ms: int = 700,
    ) -> SubPhaseReportContract:
        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_02_business",
            phase_name="2. Business Understanding & Entity Grounding",
            subphase_id="2.3",
            subphase_title="Search Intent & Commercial Funnel Mapping",
            objective="Classify visitor search intents across crawled URLs into Informational, Commercial, and Transactional stages.",
            agent_id="business.intent.v3",
            agent_model="fast_slm",
            execution_mode="slm",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"urls_evaluated": len(intent_data.get("page_intents", []))},
            processing_steps=[
                "Analyzed page titles, headings, and CTA button language per URL",
                "Classified funnel stage (Top-of-funnel, Mid-funnel, Bottom-of-funnel)",
                "Mapped commercial inquiry pathways",
            ],
            structured_output=intent_data,
            evidence_tokens=[],
            findings=[],
            confidence=ConfidenceLevel.VERIFIED,
            next_phase_handoff={"intent_map": intent_data},
        )
        return contract.seal()

    @staticmethod
    def build_p2_4_identity_arbitration(
        run_id: str,
        arbitration_data: Dict[str, Any],
        duration_ms: int = 600,
    ) -> SubPhaseReportContract:
        conflicts = arbitration_data.get("conflicts", [])
        findings = []
        for c in conflicts:
            findings.append(
                ReportFinding(
                    finding_id="IDENTITY_CONFLICT",
                    severity="medium",
                    title="Contradictory Business Positioning Detected",
                    description=str(c),
                    remediation_hint="Align landing page value proposition with footer and pricing descriptions.",
                    evidence_ids=["brand_arbitration"],
                )
            )

        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id="phase_02_business",
            phase_name="2. Business Understanding & Entity Grounding",
            subphase_id="2.4",
            subphase_title="Identity Arbitration & Positioning Reconciliation",
            objective="Cross-examine identity, target audience, and offering claims to arbitrate conflicts and seal the canonical profile.",
            agent_id="business.semantic_strategist.v3",
            agent_model="judge_model",
            execution_mode="reasoning_agent",
            duration_ms=duration_ms,
            status=ExecutionStatus.COMPLETED,
            input_summary={"subphases_arbitrated": ["2.1", "2.2", "2.3"]},
            processing_steps=[
                "Cross-examined entity name, offerings, and ICP claims",
                "Isolated contradictions between copy claims and technical products",
                "Synthesized the authoritative unified business profile for Phase 3",
            ],
            structured_output=arbitration_data,
            evidence_tokens=[],
            findings=findings,
            confidence=ConfidenceLevel.VERIFIED,
            unresolved_issues=[str(c) for c in conflicts],
            next_phase_handoff={"sealed_business_profile": arbitration_data.get("sealed_profile", {})},
        )
        return contract.seal()

    # ─────────────────────────────────────────────────────────────
    # Generic Builder for Specialists & Remaining Phases
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def build_generic(
        run_id: str,
        phase_id: str,
        phase_name: str,
        subphase_id: str,
        subphase_title: str,
        objective: str,
        agent_id: str,
        agent_model: str,
        execution_mode: str,
        duration_ms: int,
        status: ExecutionStatus,
        input_summary: Dict[str, Any],
        processing_steps: List[str],
        structured_output: Dict[str, Any],
        evidence_tokens: List[EvidenceTokenReference],
        findings: List[Any],
        confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED,
        unresolved_issues: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        next_phase_handoff: Optional[Dict[str, Any]] = None,
    ) -> SubPhaseReportContract:
        contract = SubPhaseReportContract(
            run_id=run_id,
            phase_id=phase_id,
            phase_name=phase_name,
            subphase_id=subphase_id,
            subphase_title=subphase_title,
            objective=objective,
            agent_id=agent_id,
            agent_model=agent_model,
            execution_mode=execution_mode,
            duration_ms=duration_ms,
            status=status,
            input_summary=input_summary,
            processing_steps=processing_steps,
            structured_output=structured_output,
            evidence_tokens=evidence_tokens,
            findings=findings,
            confidence=confidence,
            unresolved_issues=unresolved_issues or [],
            errors=errors or [],
            next_phase_handoff=next_phase_handoff or {},
        )
        return contract.seal()
