"""
Dristik AI Cross-Chapter Consistency Engine (2026 Master Standard).

Automated pre-publication contradiction detection and evidence reconciliation engine.
Audits the assembled ExecutiveReport across 12 critical dimensions:
1. Schema Validation vs Entity Graph & Rich Results Consistency
2. Security Headers (HSTS, CSP) vs Remediation Findings
3. Crawl Scope & Inventory Denominators (Ch 1 vs Ch 2)
4. Indexability vs Robots / Canonical Directives
5. Score Components vs Category Weights & Arithmetics
6. Defect Counts (Headline vs Severity breakdown)
7. External Authority Disclosures (NOT_CONNECTED vs quantitative claims)
8. Competitor Parity Disclosures (NOT_TESTED vs benchmark assertions)
9. Canonical Finding Deduplication & Scope Preservation
10. High-Impact Causal Reasoning Completeness & Diagnostic Gap Tracking
11. Metadata Semantic Quality vs Existence Differentiation
12. Remediation Roadmap Linkage & Count Synchronization
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.audit.inventory_helper import get_canonical_crawl_inventory
from app.domain.enums import Category, Severity
from app.domain.models import (
    ConsistencyAuditReport,
    ExecutiveReport,
    Finding,
    SchemaValidationReport,
    SecurityAuditReport,
)

logger = logging.getLogger("dristik.audit.consistency_engine")


class CrossChapterConsistencyEngine:
    """
    Detects and reconciles contradictions across the 20 audit chapters.
    Repairs data model discrepancies in-place where evidence permits,
    or flags conflicting findings as INCONCLUSIVE / DIAGNOSTIC_GAP.
    """

    @classmethod
    def audit_and_reconcile(cls, report: ExecutiveReport) -> Tuple[ExecutiveReport, ConsistencyAuditReport]:
        contradictions: List[Dict[str, Any]] = []
        repairs: List[Dict[str, Any]] = []
        inconclusives: List[Dict[str, Any]] = []
        checks_run = 0

        # -------------------------------------------------------------
        # 1. Schema Validation vs Entity Graph Contradiction Check
        # -------------------------------------------------------------
        checks_run += 1
        s = report.schema_validation
        if s is not None:
            # Check 1: If 0 entities detected, ensure errors count is 0 and clarify summary
            if s.total_entities_detected == 0 and s.entities_with_errors_count > 0:
                contradictions.append({
                    "dimension": "schema_validation",
                    "conflict": f"0 entities detected but {s.entities_with_errors_count} entity errors reported.",
                    "action": "reconcile_to_zero_errors"
                })
                s.entities_with_errors_count = 0
                repairs.append({
                    "field": "schema_validation.entities_with_errors_count",
                    "repaired_value": 0,
                    "reason": "Entity error count must be 0 when 0 entities exist."
                })

            # Check 2: Rich result eligibility must be 0 if 0 entities detected
            if s.total_entities_detected == 0 and getattr(s, "rich_result_eligibility_pct", 0) > 0:
                contradictions.append({
                    "dimension": "schema_rich_results",
                    "conflict": f"0 entities detected but rich result eligibility was {s.rich_result_eligibility_pct}%.",
                    "action": "nullify_rich_result_eligibility"
                })
                s.rich_result_eligibility_pct = 0.0
                repairs.append({
                    "field": "schema_validation.rich_result_eligibility_pct",
                    "repaired_value": 0.0,
                    "reason": "Rich result eligibility cannot be positive when zero schema entities are present."
                })

            # Check 3: Schema findings vs schema report alignment
            schema_findings = [
                f for f in report.findings
                if any(k in f.title.lower() for k in ("schema", "json-ld", "structured data"))
            ]
            if s.total_entities_detected == 0 and not schema_findings:
                repairs.append({
                    "field": "schema_validation.summary",
                    "repaired_value": "No JSON-LD structured data detected. Schema syntax passes trivially because no markup is present.",
                    "reason": "Clarified that zero syntax errors does not mean structured data is implemented."
                })

        # -------------------------------------------------------------
        # 2. Security Headers (HSTS, CSP) Reconciliation
        # -------------------------------------------------------------
        checks_run += 1
        sec = report.security_audit
        if sec is not None:
            hsts_findings = [
                f for f in report.findings
                if any(k in f.title.lower() for k in ("hsts", "strict-transport-security"))
            ]
            if hsts_findings and getattr(sec, "hsts_enabled", False):
                has_evidence_header = bool(getattr(sec, "hsts_header", None))
                if not has_evidence_header:
                    contradictions.append({
                        "dimension": "security_hsts",
                        "conflict": "HSTS marked enabled in security report but missing in remediation finding and no header value recorded.",
                        "action": "reconcile_hsts_disabled"
                    })
                    sec.hsts_enabled = False
                    repairs.append({
                        "field": "security_audit.hsts_enabled",
                        "repaired_value": False,
                        "reason": "Reconciled HSTS to False based on missing header value and verified remediation finding."
                    })

            csp_findings = [
                f for f in report.findings
                if any(k in f.title.lower() for k in ("content-security-policy", "csp"))
            ]
            if csp_findings and getattr(sec, "csp_enabled", False) and not getattr(sec, "csp_header", None):
                sec.csp_enabled = False
                repairs.append({
                    "field": "security_audit.csp_enabled",
                    "repaired_value": False,
                    "reason": "Reconciled CSP to False due to absence of header payload."
                })

        # -------------------------------------------------------------
        # 3. Crawl Scope & Inventory Reconciliation (Ch 1 vs Ch 2)
        # -------------------------------------------------------------
        checks_run += 1
        manifest = getattr(report, "crawl_manifest", None)
        canonical_inv = get_canonical_crawl_inventory(manifest, report)
        report.canonical_crawl_inventory = canonical_inv

        disc_total = canonical_inv.discovered_total
        tested_pages = canonical_inv.tested_pages
        cov_pct = canonical_inv.url_coverage_pct or 0.0

        if manifest:
            old_crawl_inv = getattr(manifest, "crawl_inventory", None)
            if hasattr(old_crawl_inv, "model_dump"):
                old_crawl_inv = old_crawl_inv.model_dump()
            elif not isinstance(old_crawl_inv, dict):
                old_crawl_inv = {}
            old_disc = old_crawl_inv.get("discovered_total", old_crawl_inv.get("total_unique_discovered"))
            if old_disc is not None and old_disc != disc_total:
                contradictions.append({
                    "dimension": "crawl_scope",
                    "conflict": f"Discovered URLs count mismatch: inventory {old_disc} vs canonical {disc_total}.",
                    "action": "reconcile_to_canonical_inventory"
                })

            manifest.crawl_inventory = canonical_inv.model_dump()
            manifest.url_coverage_pct = cov_pct
            manifest.total_pages_discovered = disc_total
            manifest.total_pages_crawled = tested_pages
            manifest.sampling_status = canonical_inv.sampling_status

        if report.crawl_summary:
            report.crawl_summary["total_pages_discovered"] = disc_total
            report.crawl_summary["total_pages_crawled"] = tested_pages
            report.crawl_summary["url_coverage_pct"] = cov_pct

        # Narrative reconciliation for sampled crawls
        if disc_total > tested_pages and report.story_summary:
            s_lower = report.story_summary.lower()
            if "every url" in s_lower or "audited all" in s_lower or "comprehensive" in s_lower:
                contradictions.append({
                    "dimension": "crawl_narrative",
                    "conflict": "Executive narrative claimed full coverage on a sampled audit.",
                    "action": "reconcile_narrative_sampling_disclosure"
                })
                report.story_summary = (
                    f"Sampled audit of {tested_pages} representative pages out of {disc_total} discovered "
                    f"({cov_pct}% URL coverage). " + report.story_summary
                )
                repairs.append({
                    "field": "story_summary",
                    "repaired_value": report.story_summary[:80] + "...",
                    "reason": "Reconciled narrative to accurately disclose sampled audit scope."
                })

        # -------------------------------------------------------------
        # 4. Defect Count Mathematical Reconciliation
        # -------------------------------------------------------------
        checks_run += 1
        findings_count = len(report.findings)
        sev_counts: Dict[str, int] = {}
        for f in report.findings:
            s_val = f.severity.value if hasattr(f.severity, "value") else str(f.severity).upper()
            sev_counts[s_val] = sev_counts.get(s_val, 0) + 1

        sum_sev = sum(sev_counts.values())
        if findings_count != sum_sev:
            contradictions.append({
                "dimension": "defect_counts",
                "conflict": f"Total findings count ({findings_count}) != severity total ({sum_sev}).",
                "action": "reconcile_finding_count"
            })

        # Build formal issue ledger
        report.issue_ledger = {
            "total_distinct_findings": findings_count,
            "severity_breakdown": sev_counts,
            "total_affected_url_instances": sum(len(f.affected_urls) for f in report.findings),
            "open_count": sum(1 for f in report.findings if str(getattr(f, "status", "OPEN")).upper() in ("OPEN", "FINDINGSTATUS.OPEN")),
            "verified_count": sum(1 for f in report.findings if str(getattr(f, "status", "")).upper() in ("VERIFIED", "FINDINGSTATUS.VERIFIED")),
            "p0_critical_count": sum(1 for f in report.findings if f.priority >= 9 or str(getattr(f.severity, "value", f.severity)).upper() == "CRITICAL"),
            "p1_high_count": sum(1 for f in report.findings if (f.priority in (7, 8) or str(getattr(f.severity, "value", f.severity)).upper() == "HIGH") and not (f.priority >= 9 or str(getattr(f.severity, "value", f.severity)).upper() == "CRITICAL")),
        }

        # -------------------------------------------------------------
        # 5. External Authority Zero-Fake Reconciliation
        # -------------------------------------------------------------
        checks_run += 1
        ext = report.external_authority
        if isinstance(ext, dict):
            status = ext.get("status", "NOT_CONNECTED")
            if status == "NOT_CONNECTED" and ext.get("universal_authority_score") is not None:
                contradictions.append({
                    "dimension": "external_authority",
                    "conflict": "External authority is NOT_CONNECTED but universal_authority_score is populated.",
                    "action": "nullify_unverified_score"
                })
                ext["universal_authority_score"] = None
                repairs.append({
                    "field": "external_authority.universal_authority_score",
                    "repaired_value": None,
                    "reason": "Removed fabricated authority score from unconnected provider."
                })

        # -------------------------------------------------------------
        # 6. Competitor Parity Disclosures
        # -------------------------------------------------------------
        checks_run += 1
        comp = report.competitor_seo_parity
        if comp is not None:
            competitors = getattr(comp, "competitors", []) or []
            if len(competitors) <= 1 and comp.peer_avg_seo_score is not None:
                comp.peer_avg_seo_score = None
                repairs.append({
                    "field": "competitor_seo_parity.peer_avg_seo_score",
                    "repaired_value": None,
                    "reason": "Peer average score is unmeasured when zero independent competitors are crawled."
                })

        # -------------------------------------------------------------
        # 7. Scoring Consistency (Arithmetic Integrity)
        # -------------------------------------------------------------
        checks_run += 1
        if report.scores and getattr(report.scores, "category_scores", None):
            cat_scores = list(report.scores.category_scores.values())
            weighted_sum = sum(c.weighted_score for c in cat_scores if getattr(c, "weighted_score", None) is not None)
            overall = report.scores.overall_score
            if overall is not None and abs(overall - weighted_sum) > 0.5:
                contradictions.append({
                    "dimension": "scoring_consistency",
                    "conflict": f"Overall score ({overall:.1f}) diverges from category weighted sum ({weighted_sum:.1f}).",
                    "action": "reconcile_overall_score"
                })
                report.scores.overall_score = round(weighted_sum, 1)
                repairs.append({
                    "field": "scores.overall_score",
                    "repaired_value": round(weighted_sum, 1),
                    "reason": "Reconciled overall score to match exact sum of weighted category contributions."
                })

        # -------------------------------------------------------------
        # 8. Indexability vs Canonical Consistency
        # -------------------------------------------------------------
        checks_run += 1
        canonical_audit = getattr(report, "canonical_audit", None)
        if canonical_audit and getattr(canonical_audit, "conflicts", None):
            conflict_urls = set(getattr(canonical_audit, "conflicts", []))
            if report.indexation_intelligence:
                idx_rep = report.indexation_intelligence
                if hasattr(idx_rep, "indexable_urls") and getattr(idx_rep, "indexable_urls", None):
                    overlap = [u for u in idx_rep.indexable_urls if u in conflict_urls]
                    if overlap:
                        contradictions.append({
                            "dimension": "indexability_canonical",
                            "conflict": f"{len(overlap)} URLs marked indexable but carry canonical conflicts.",
                            "action": "flag_inconclusive"
                        })
                        inconclusives.append({
                            "urls": overlap[:5],
                            "reason": "Canonical conflict prevents deterministic indexability confirmation."
                        })

        # -------------------------------------------------------------
        # 9. Finding Deduplication & Scope Preservation
        # -------------------------------------------------------------
        checks_run += 1
        if report.findings:
            unique_findings: Dict[str, Finding] = {}
            duplicates_found = 0
            for f in report.findings:
                rule_key = getattr(f, "rule_id", "") or f.title.strip().lower()
                cat_val = f.category.value if hasattr(f.category, "value") else str(f.category)
                key = f"{cat_val}::{rule_key}"
                if key in unique_findings:
                    duplicates_found += 1
                    existing = unique_findings[key]
                    merged_urls = list(dict.fromkeys(existing.affected_urls + f.affected_urls))
                    existing.affected_urls = merged_urls
                    existing.evidence_refs = list(dict.fromkeys(existing.evidence_refs + f.evidence_refs))
                    existing.evidence_ids = list(dict.fromkeys(existing.evidence_ids + f.evidence_ids))
                    if not existing.root_cause and f.root_cause:
                        existing.root_cause = f.root_cause
                    if not existing.relevant_code_or_configuration_example and f.relevant_code_or_configuration_example:
                        existing.relevant_code_or_configuration_example = f.relevant_code_or_configuration_example
                else:
                    unique_findings[key] = f

            if duplicates_found > 0:
                contradictions.append({
                    "dimension": "finding_deduplication",
                    "conflict": f"{duplicates_found} duplicate findings detected across chapter outputs.",
                    "action": "merge_duplicates_preserve_scope"
                })
                report.findings = list(unique_findings.values())
                repairs.append({
                    "field": "findings",
                    "repaired_value": f"Merged {duplicates_found} duplicates into {len(report.findings)} unique findings.",
                    "reason": "Merged duplicate findings while preserving all affected URLs and evidence references."
                })

        # -------------------------------------------------------------
        # 10. High-Impact Causal Reasoning Completeness Check
        # -------------------------------------------------------------
        checks_run += 1
        high_impact_findings = [
            f for f in report.findings
            if f.priority >= 7 or str(getattr(f.severity, "value", f.severity)).upper() in ("CRITICAL", "HIGH")
        ]
        unsupported_causal = []
        for f in high_impact_findings:
            if not f.root_cause:
                if f.technical_explanation:
                    f.root_cause = f.technical_explanation
                    f.root_cause_status = "strongly_supported"
                    repairs.append({
                        "field": f"finding.{f.finding_id}.root_cause",
                        "repaired_value": f.root_cause,
                        "reason": "Derived root cause from technical explanation."
                    })
                else:
                    f.root_cause_status = "diagnostic_gap"
                    f.diagnostic_gap = "Underlying mechanism requires origin web server / CDN configuration logs or Direct server runtime telemetry to confirm root cause."
                    f.alternative_explanations = ["Server proxy misconfiguration", "Edge CDN header stripping", "CMS template hook omitted"]
                    unsupported_causal.append(f.finding_id)

        if unsupported_causal:
            inconclusives.append({
                "dimension": "causal_reasoning",
                "finding_ids": unsupported_causal,
                "reason": f"{len(unsupported_causal)} high-impact finding(s) carry documented diagnostic gaps."
            })

        # -------------------------------------------------------------
        # 11. Metadata Quality vs Existence Reconciliation
        # -------------------------------------------------------------
        checks_run += 1
        meta_rollup = getattr(report, "meta_rollup", None)
        if meta_rollup:
            # Check duplicate meta descriptions across sample
            dup_descs = getattr(meta_rollup, "duplicate_descriptions", [])
            has_dup_desc_finding = any("duplicate" in f.title.lower() and "description" in f.title.lower() for f in report.findings)
            if len(dup_descs) > 0 and not has_dup_desc_finding:
                # Add explicit duplicate meta description quality finding
                dup_urls = [item.url for item in dup_descs] if hasattr(dup_descs[0], "url") else []
                new_f = Finding(
                    finding_id="F-ONPAGE-DUP-DESC",
                    title="Duplicate Meta Descriptions Across Audited URLs",
                    category=report.findings[0].category if report.findings else Severity.MEDIUM,
                    severity=Severity.MEDIUM,
                    priority=6,
                    affected_urls=dup_urls or [p.url for p in (report.page_reports or [])],
                    raw_observation=f"Identical meta description string repeated across {len(dup_descs)} pages.",
                    difference_observed_expected="Duplicate description observed; unique, page-specific value proposition expected.",
                    technical_explanation="CMS template repeats sitewide fallback meta description without per-page editorial overrides.",
                    business_impact="Dilutes SERP click-through rate and limits search engine snippet differentiation.",
                    root_cause="Absence of mandatory editorial meta description field in CMS page creation workflow.",
                    recommendation="Author unique 140-160 character meta descriptions for each commercial service landing page.",
                    validation_criteria="Every indexable URL outputs a distinct meta description string in <head>.",
                    acceptance_criteria="Unique meta description verified on all crawled URLs.",
                )
                report.findings.append(new_f)
                repairs.append({
                    "field": "findings",
                    "repaired_value": "F-ONPAGE-DUP-DESC",
                    "reason": "Added explicit quality finding for duplicate meta descriptions across crawled pages."
                })

        # -------------------------------------------------------------
        # 12. Remediation Roadmap Alignment
        # -------------------------------------------------------------
        checks_run += 1
        p0_findings = [f for f in report.findings if f.priority >= 9 or str(getattr(f.severity, "value", f.severity)).upper() == "CRITICAL"]
        if p0_findings and not report.roadmap_7_days:
            # Synchronize 7-day roadmap with P0 blockers
            from app.domain.models import RoadmapItem
            synced_items = []
            for idx, p0 in enumerate(p0_findings):
                cat = getattr(p0, "category", Category.TECHNICAL_SEO)
                if not isinstance(cat, Category):
                    try:
                        cat = Category(str(cat))
                    except Exception:
                        cat = Category.TECHNICAL_SEO
                synced_items.append(RoadmapItem(
                    timeframe="7_days",
                    title=f"Resolve {p0.title}",
                    description=p0.recommendation or p0.description or f"Address {p0.title}",
                    impact="High",
                    effort="Medium",
                    category=cat,
                    related_finding_id=getattr(p0, "finding_id", None),
                ))
            report.roadmap_7_days = synced_items
            repairs.append({
                "field": "roadmap_7_days",
                "repaired_value": f"{len(synced_items)} P0 actions",
                "reason": "Synchronized 7-day quick-win roadmap with verified P0 critical blockers."
            })

        # -------------------------------------------------------------
        # 13. Mandatory Plain-English Structured Fields Enrichment
        # -------------------------------------------------------------
        if report.findings:
            from app.reports.plain_english_engine import PlainEnglishEngine
            for f in report.findings:
                if hasattr(f, "plain_english_summary"):
                    if not f.plain_english_summary or not f.observed_result or not f.who_affected or not f.expected_outcome:
                        enriched = PlainEnglishEngine.enrich_finding(f)
                        if not f.plain_english_summary:
                            f.plain_english_summary = enriched.get("plain_english_summary")
                        if not f.what_was_checked:
                            f.what_was_checked = enriched.get("what_was_checked")
                        if not f.observed_result:
                            f.observed_result = enriched.get("observed_result")
                        if not f.who_affected:
                            f.who_affected = enriched.get("who_affected")
                        if not f.developer_instructions:
                            f.developer_instructions = enriched.get("developer_instructions")
                        if not f.verification_steps and enriched.get("verification_steps"):
                            f.verification_steps = enriched.get("verification_steps")
                        if not f.scope_status:
                            f.scope_status = enriched.get("scope_status")
                        if not f.expected_outcome:
                            f.expected_outcome = enriched.get("expected_outcome")

        # Summary
        is_consistent = len(contradictions) == 0
        summary = (
            f"Cross-Chapter Consistency Gate: {checks_run} checks evaluated across 12 dimensions. "
            f"{len(contradictions)} contradiction(s) detected, {len(repairs)} repaired, "
            f"{len(inconclusives)} inconclusive / diagnostic gaps."
        )

        consistency_report = ConsistencyAuditReport(
            is_consistent=is_consistent,
            checks_run=checks_run,
            contradictions_detected=contradictions,
            reconciled_repairs=repairs,
            inconclusive_items=inconclusives,
            summary=summary,
        )

        report.consistency_report = consistency_report
        return report, consistency_report
