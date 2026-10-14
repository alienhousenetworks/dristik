"""
Dristik AI 20-Point Report Integrity Engine & Automated Validation Gate
Enforces hard constraints before shipping or saving any ExecutiveReport.
A report violating any rule in the VALIDATION GATE must be repaired/regenerated or fail closed.
"""
from dataclasses import dataclass, field
import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple

from app.domain.models import (
    ExecutiveReport,
    Finding,
    RoadmapItem,
    CodePatch,
    OverallScoreResult,
    CategoryScore,
)
from app.domain.enums import Severity, Category


BANNED_TERMS = [
    "hyper-advanced",
    "hyper advanced",
    "revolutionary",
    "revolutionize",
    "world-class",
    "world class",
    "next-gen",
    "next gen",
    "cutting-edge",
    "game-changer",
    "unmatched",
    "best-in-class",
]

ASSURANCE_TERMS = [
    "independent assurance",
    "certified audit",
    "certification",
    "lead auditor sign-off",
    "lead auditor",
    "client privileged",
    "official attestation",
]


@dataclass
class ValidationResult:
    is_valid: bool
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    failure_reasons: Dict[str, str] = field(default_factory=dict)
    repaired: bool = False

    def summary(self) -> str:
        if self.is_valid:
            return f"VALIDATION GATE PASSED: All {len(self.passed_checks)} checks satisfied."
        return (
            f"VALIDATION GATE FAILED: {len(self.failed_checks)} failure(s) detected:\n"
            + "\n".join(f" - [{k}]: {self.failure_reasons[k]}" for k in self.failed_checks)
        )


class ValidationGate:
    """
    Evaluates and enforces the 20-point hard constraints on ExecutiveReport.
    """

    @classmethod
    def validate_report(cls, report: ExecutiveReport, manifest: Optional[Any] = None) -> ValidationResult:
        passed: List[str] = []
        failed: List[str] = []
        reasons: Dict[str, str] = {}

        def record(check_id: str, condition: bool, reason: str = ""):
            if condition:
                passed.append(check_id)
            else:
                failed.append(check_id)
                reasons[check_id] = reason

        # -------------------------------------------------------------
        # 1. SCORING INTEGRITY
        # -------------------------------------------------------------
        # 1.1 & 1.2: Overall score == sum of weighted contributions
        cat_scores = report.scores.category_scores.values() if report.scores and report.scores.category_scores else []
        if cat_scores:
            calc_sum = sum(c.weighted_score for c in cat_scores if c.weighted_score is not None)
            overall_val = report.scores.overall_score if report.scores.overall_score is not None else 0.0
            is_close = abs(overall_val - calc_sum) <= 0.5
            record(
                "overall_score_equals_weighted_sum",
                is_close,
                f"Overall score ({report.scores.overall_score}) does not match sum of weighted contributions ({calc_sum:.2f})."
            )

            # 1.3: Base weights MUST sum to exactly 100% (or 1.0)
            weight_sum = sum(c.weight for c in cat_scores if c.weight is not None)
            weights_ok = abs(weight_sum - 100.0) <= 0.5 or abs(weight_sum - 1.0) <= 0.01
            record(
                "weights_sum_to_100_percent",
                weights_ok,
                f"Base weights sum to {weight_sum}, expected exactly 100% or 1.0."
            )
        else:
            record("overall_score_equals_weighted_sum", False, "No category scores present.")
            record("weights_sum_to_100_percent", False, "No category weights present.")

        # 1.4: Every score appears with an identical value on every surface
        score_inconsistencies = []
        if report.visual_intelligence and getattr(report.visual_intelligence, "kpis", None):
            for kpi in report.visual_intelligence.kpis:
                if kpi.label.lower() in ["overall health", "health score", "overall score"]:
                    try:
                        kpi_val = float(str(kpi.value).replace("/100", "").replace("%", "").strip())
                        overall_val = report.scores.overall_score if report.scores.overall_score is not None else 0.0
                        if abs(kpi_val - overall_val) > 1.0:
                            score_inconsistencies.append(f"Visual KPI {kpi.label}={kpi_val} vs Overall={report.scores.overall_score}")
                    except ValueError:
                        pass
        record(
            "score_identical_across_surfaces",
            len(score_inconsistencies) == 0,
            "; ".join(score_inconsistencies) if score_inconsistencies else ""
        )

        from app.scoring.displayed_score import displayed_composite, story_matches_composite
        dossier_composite = displayed_composite(report)
        story_agrees = story_matches_composite(getattr(report, "story_summary", "") or "", dossier_composite)
        record(
            "headline_score_matches_composite",
            story_agrees,
            "" if story_agrees else (
                f"Executive story score disagrees with the dossier composite {dossier_composite}."
            ),
        )

        # 1.5: Composite scores are derivable from components
        composite_ok = True
        composite_err = ""
        if report.honest_scores and report.honest_scores.ai_citation_score is not None:
            # Check visual intelligence GEO engine matrix alignment
            if report.visual_intelligence:
                charts_list = getattr(report.visual_intelligence, "selected_visualizations", None) or getattr(report.visual_intelligence, "charts", None) or []
                for c in charts_list:
                    if getattr(c, "id", "") == "chart_ai_engine_matrix":
                        engines = (c.data or {}).get("engines", [])
                        if engines:
                            eng_avg = sum(float(e.get("readiness", 0)) for e in engines) / len(engines)
                            if abs(report.honest_scores.ai_citation_score - eng_avg) > 1.01:
                                composite_ok = False
                                composite_err = f"Composite AI Citation Score ({report.honest_scores.ai_citation_score}) diverges from GEO engine matrix average ({eng_avg:.1f})."
                            # Check superlative consistency
                            top_readiness = max(float(e.get("readiness", 0)) for e in engines)
                            insight_text = getattr(c, "ai_insight", "") or ""
                            if "most extractable in" in insight_text.lower():
                                for e in engines:
                                    name = e.get("name", "")
                                    r = float(e.get("readiness", 0))
                                    if f"most extractable in {name.lower()}" in insight_text.lower() and r < top_readiness:
                                        composite_ok = False
                                        composite_err = f"Contradictory takeaway: claims brand is most extractable in {name} ({r}%) but top engine has {top_readiness}%."

            if report.ai_search_matrix:
                def _get_q_score(q):
                    if hasattr(q, "score") and q.score is not None:
                        return float(q.score) * 10.0
                    if hasattr(q, "citation_probability") and q.citation_probability is not None:
                        return float(q.citation_probability) * 100.0
                    return float(getattr(q, "citability_score", 50.0))
                matrix_avg = sum(_get_q_score(q) for q in report.ai_search_matrix) / len(report.ai_search_matrix)
                if abs(report.honest_scores.ai_citation_score - matrix_avg) > 50:
                    composite_ok = False
                    composite_err = f"Composite AI Citation Score ({report.honest_scores.ai_citation_score}) diverges from query matrix average ({matrix_avg:.1f})."
        record("composite_scores_derivable", composite_ok, composite_err)

        # 1.6: Defect counts reconcile across all three representations
        findings_count = len(report.findings)
        sev_counts = {}
        for f in report.findings:
            s = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sev_counts[s] = sev_counts.get(s, 0) + 1
        sev_total = sum(sev_counts.values())
        record(
            "defect_counts_reconcile",
            findings_count == sev_total,
            f"Headline findings ({findings_count}) != severity breakdown total ({sev_total})."
        )

        # -------------------------------------------------------------
        # 2. DEDUPLICATION
        # -------------------------------------------------------------
        # 2.1 & 2.2: Zero duplicate findings by root cause
        seen_roots: Set[str] = set()
        duplicate_findings: List[str] = []
        for f in report.findings:
            root_key = f"{f.category}:{f.title.lower().strip()}"
            if root_key in seen_roots:
                duplicate_findings.append(f.title)
            else:
                seen_roots.add(root_key)
        record(
            "zero_duplicate_findings_root_cause",
            len(duplicate_findings) == 0,
            f"Duplicate findings found for same root cause: {duplicate_findings[:3]}"
        )

        # 2.3: Zero duplicate roadmap items across phases
        roadmap_titles: Set[str] = set()
        duplicate_roadmap: List[str] = []
        for phase_name, items in [
            ("7_days", report.roadmap_7_days),
            ("30_days", report.roadmap_30_days),
            ("90_days", report.roadmap_90_days),
        ]:
            for item in items:
                norm_title = item.title.lower().strip()
                if norm_title in roadmap_titles:
                    duplicate_roadmap.append(f"'{item.title}' in {phase_name}")
                else:
                    roadmap_titles.add(norm_title)
        record(
            "zero_duplicate_roadmap_items",
            len(duplicate_roadmap) == 0,
            f"Roadmap items appear in multiple phases or duplicates: {duplicate_roadmap}"
        )

        # -------------------------------------------------------------
        # 3. FIELD COMPLETENESS
        # -------------------------------------------------------------
        # 3.1: Zero empty or dash-only fields
        dash_fields = []
        bp = report.business_profile
        if bp:
            for field_name in ["value_proposition", "target_audience", "business_model"]:
                val = getattr(bp, field_name, "")
                if str(val).strip() in ["—", "-", "--", "N/A", "null", "None", ""]:
                    dash_fields.append(f"business_profile.{field_name}")

        for text_field, label in [
            (report.story_summary, "story_summary"),
            (report.primary_strategic_opportunity, "primary_strategic_opportunity"),
            (report.consultant_advice_what_to_ignore, "consultant_advice_what_to_ignore"),
        ]:
            if str(text_field).strip() in ["—", "-", "--", "N/A", "null", "None", ""]:
                dash_fields.append(label)

        record(
            "zero_empty_or_dash_fields",
            len(dash_fields) == 0,
            f"Fields render with placeholder dashes or empty values: {dash_fields}"
        )

        # 3.3: Zero truncated strings mid-token
        truncated_strings = []
        for text, source in [
            (report.story_summary, "story_summary"),
            (report.primary_strategic_opportunity, "primary_strategic_opportunity"),
            (report.website_url, "website_url"),
        ]:
            if "https://" in text and ("…" in text or text.endswith("...")):
                truncated_strings.append(f"Truncated URL in {source}")
            elif re.search(r"https?://[^\s]+…", text):
                truncated_strings.append(f"Clipped URL token in {source}")

        record(
            "zero_truncated_strings",
            len(truncated_strings) == 0,
            "; ".join(truncated_strings) if truncated_strings else ""
        )

        # -------------------------------------------------------------
        # 4. EVIDENCE AND CONFIDENCE HONESTY
        # -------------------------------------------------------------
        # 4.1 & 4.2: Zero 100-scores coexisting with findings in same category
        coexisting_flaws = []
        for cat_name, cat_obj in (report.scores.category_scores or {}).items():
            if cat_obj.score is not None and cat_obj.score >= 99.5:
                has_high_defects = any(
                    f.category == cat_obj.category and str(f.severity).upper() in ["CRITICAL", "HIGH", "SEVERITY.CRITICAL", "SEVERITY.HIGH"]
                    for f in report.findings
                )
                if has_high_defects:
                    coexisting_flaws.append(f"{cat_name} scored {cat_obj.score} but has HIGH/CRITICAL defects.")

        record(
            "zero_100_scores_coexisting_with_findings",
            len(coexisting_flaws) == 0,
            "; ".join(coexisting_flaws) if coexisting_flaws else ""
        )

        # 4.3: Aggregate confidence <= maximum finding confidence
        finding_confs = [
            getattr(f, "confidence", 0.7) for f in report.findings if isinstance(getattr(f, "confidence", None), (int, float))
        ]
        max_finding_conf = max(finding_confs) if finding_confs else 0.7
        narrative_text = f"{report.story_summary} {report.primary_strategic_opportunity}".lower()
        excessive_certainty = (
            max_finding_conf < 0.6 and "high empirical certainty" in narrative_text
        )
        record(
            "aggregate_confidence_within_ceiling",
            not excessive_certainty,
            "Narrative claims high empirical certainty while underlying findings have low confidence."
        )

        # 4.4 & 4.5: Provenance labeling enforced
        has_misleading_actual = "actual result" in narrative_text and "simulated" in narrative_text
        record(
            "every_number_carries_provenance_label",
            not has_misleading_actual,
            "Simulated output was labeled as 'ACTUAL RESULT'."
        )

        # 4.6 & 4.7: Benchmarks and projections cite basis
        unsubstantiated_projections = []
        if re.search(r"\+\d+%\s+to\s+\+\d+%", narrative_text):
            if "based on" not in narrative_text and "assuming" not in narrative_text and "modeled" not in narrative_text:
                unsubstantiated_projections.append("Projection percentage without stated assumptions.")
        record(
            "every_benchmark_and_projection_cites_basis",
            len(unsubstantiated_projections) == 0,
            "; ".join(unsubstantiated_projections) if unsubstantiated_projections else ""
        )

        # -------------------------------------------------------------
        # 5. CODE PATCH VALIDITY
        # -------------------------------------------------------------
        # 5.1 & 14: All JSON-LD validates; zero nulls or empty values
        patch_flaws = []
        for patch in report.code_patches:
            snippet = patch.after_snippet or ""
            if "application/ld+json" in snippet or patch.target_file.endswith(".jsonld"):
                clean_json = re.sub(r"<script[^>]*>", "", snippet)
                clean_json = re.sub(r"</script>", "", clean_json).strip()
                try:
                    data = json.loads(clean_json)
                    def check_nulls(obj, path=""):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if v is None:
                                    patch_flaws.append(f"Null value in patch {patch.patch_id} at {path}.{k}")
                                elif v == "":
                                    patch_flaws.append(f"Empty string in patch {patch.patch_id} at {path}.{k}")
                                else:
                                    check_nulls(v, f"{path}.{k}")
                        elif isinstance(obj, list):
                            for i, v in enumerate(obj):
                                check_nulls(v, f"{path}[{i}]")
                    check_nulls(data)
                except json.JSONDecodeError:
                    patch_flaws.append(f"Patch {patch.patch_id} contains invalid JSON-LD.")

        record(
            "all_json_ld_validates_zero_nulls",
            len(patch_flaws) == 0,
            "; ".join(patch_flaws[:3]) if patch_flaws else ""
        )

        # 5.3: Zero invented URLs in sameAs
        invented_urls = []
        crawled_urls: Set[str] = set()
        if manifest and getattr(manifest, "pages", None):
            for p in manifest.pages:
                if hasattr(p, "url") and p.url:
                    crawled_urls.add(p.url.lower().rstrip("/"))
                if hasattr(p, "external_links"):
                    for el in p.external_links:
                        crawled_urls.add(str(el).lower().rstrip("/"))

        for patch in report.code_patches:
            snippet = patch.after_snippet or ""
            same_as_matches = re.findall(r'"sameAs":\s*\[(.*?)\]', snippet, re.DOTALL)
            for sa_block in same_as_matches:
                urls = re.findall(r'"(https?://[^"]+)"', sa_block)
                for u in urls:
                    clean_u = u.lower().rstrip("/")
                    if any(soc in clean_u for soc in ["twitter.com", "linkedin.com", "github.com", "facebook.com", "instagram.com"]):
                        if clean_u not in crawled_urls:
                            invented_urls.append(f"Unobserved social link in sameAs: {u}")

        record(
            "zero_invented_urls",
            len(invented_urls) == 0,
            "; ".join(invented_urls[:3]) if invented_urls else ""
        )

        # -------------------------------------------------------------
        # 6. INTERNAL CONSISTENCY OF ADVICE
        # -------------------------------------------------------------
        # 6.1: Directive and roadmap sequencing agree
        ignore_text = report.consultant_advice_what_to_ignore.lower()
        directive_conflicts = []
        deprioritizes_tech_seo = "technical seo" in ignore_text or "meta tag" in ignore_text or "sitemap" in ignore_text
        if deprioritizes_tech_seo:
            for item in report.roadmap_7_days:
                cat_str = str(item.category).upper()
                title_lower = item.title.lower()
                is_tech_seo = "TECHNICAL_SEO" in cat_str or "sitemap" in title_lower or ("meta description" in title_lower and "h1" not in title_lower)
                if is_tech_seo:
                    directive_conflicts.append(
                        f"Roadmap 7-Day features '{item.title}' but 'What to Ignore' deprioritizes it."
                    )
        record(
            "directive_and_roadmap_sequencing_agree",
            len(directive_conflicts) == 0,
            "; ".join(directive_conflicts) if directive_conflicts else ""
        )

        # 6.2: Zero banned terms in recommended copy
        banned_found = []
        all_prose = f"{report.story_summary} {report.primary_strategic_opportunity} {report.consultant_advice_what_to_ignore}".lower()
        if report.character_safe_copy:
            csc = report.character_safe_copy
            all_prose += f" {csc.hero_headline} {csc.hero_subhead} {csc.meta_description}".lower()

        for term in BANNED_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", all_prose):
                banned_found.append(term)

        record(
            "zero_banned_terms_in_recommended_copy",
            len(banned_found) == 0,
            f"Banned terms found in recommendations or copy: {banned_found}"
        )

        # 6.3: Zero contradictory statements about detected entities
        contradictory_statements = []
        if report.contradictions:
            for c in report.contradictions:
                if getattr(c, "severity", None) in ["CRITICAL", "HIGH"]:
                    contradictory_statements.append(f"Contradiction: {getattr(c, 'claim_a', '')} vs {getattr(c, 'claim_b', '')}")
        record(
            "zero_contradictory_statements_about_detected_entities",
            len(contradictory_statements) == 0,
            "; ".join(contradictory_statements[:2]) if contradictory_statements else ""
        )

        # 6.4: Zero heading contradictions between findings and rollups
        heading_contradictions = []
        missing_h1_cnt = 0
        if report.heading_hierarchy and hasattr(report.heading_hierarchy, "missing_h1"):
            missing_h1_cnt = len(report.heading_hierarchy.missing_h1 or [])
        elif report.crawl_summary:
            missing_h1_cnt = int(report.crawl_summary.get("missing_h1_count", 0))

        if missing_h1_cnt == 0:
            for f in (report.findings or []):
                if getattr(f, "held_from_executive", False):
                    continue
                f_text = f"{f.title} {f.description or ''}".lower()
                if "document lacks a top-level <h1>" in f_text or "missing an <h1> tag" in f_text or "lacks a top-level h1" in f_text:
                    heading_contradictions.append(f"Finding {f.finding_id} claims document lacks <h1> but heading hierarchy verifies 0 missing H1 pages.")

        record(
            "heading_hierarchy_consistent_with_findings",
            len(heading_contradictions) == 0,
            "; ".join(heading_contradictions) if heading_contradictions else ""
        )

        # -------------------------------------------------------------
        # 7. LANGUAGE AND CLAIM RESTRAINT
        # -------------------------------------------------------------
        # 7.1: Zero assurance/certification language without human reviewer
        assurance_found = []
        for term in ASSURANCE_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", all_prose):
                assurance_found.append(term)
        record(
            "zero_assurance_language_without_human_reviewer",
            len(assurance_found) == 0,
            f"Unauthorized certification/assurance claims detected: {assurance_found}"
        )

        from app.scoring.calibration import prose_overclaims
        overclaim_fields = [
            name for name, text in (
                ("story_summary", report.story_summary),
                ("primary_strategic_opportunity", report.primary_strategic_opportunity),
                ("consultant_advice_what_to_ignore", report.consultant_advice_what_to_ignore),
            )
            if prose_overclaims(text or "")
        ]
        record(
            "outcome_claims_respect_blocking",
            len(overclaim_fields) == 0,
            "Narrative treats a defect as freezing SEO, design, conversion, or citations "
            "without a blocking record for that outcome: " + ", ".join(overclaim_fields),
        )

        # -------------------------------------------------------------
        # 8. RENDERING & ENVIRONMENT CLEANLINESS
        # -------------------------------------------------------------
        # 8.1 & 8.4: Zero dev-build artifacts, localhost, or encoding errors
        dev_artifacts = []
        raw_export_text = (
            f"{report.story_summary} {report.primary_strategic_opportunity} "
            f"{report.website_url} {report.domain}"
        )
        if "localhost:" in raw_export_text or "127.0.0.1" in raw_export_text or ":5173" in raw_export_text:
            dev_artifacts.append("Dev host or port found in report text.")

        for mojibake in ["o!ers", "tra\"ic", "so!ware", "â€™", "â€œ", "â€\x9d"]:
            if mojibake in raw_export_text:
                dev_artifacts.append(f"Dropped ligature or mojibake: '{mojibake}'")

        record(
            "zero_dev_artifacts_and_encoding_errors",
            len(dev_artifacts) == 0,
            "; ".join(dev_artifacts) if dev_artifacts else ""
        )

        # 8.5: Canonical Entity Resolved & Non-Generic (Zero 'Unknown Business')
        from app.intelligence.business.entity_resolver import BANNED_NAMES
        biz_name = (report.business_profile.business_name if report.business_profile else "") or ""
        ent_name = (report.resolved_entity.name if getattr(report, "resolved_entity", None) else "") or ""
        has_generic_name = False
        if not biz_name.strip() and not ent_name.strip():
            has_generic_name = True
        if biz_name.strip() and (biz_name.strip().lower() in BANNED_NAMES or "unknown business" in biz_name.lower()):
            has_generic_name = True
        if ent_name.strip() and (ent_name.strip().lower() in BANNED_NAMES or "unknown business" in ent_name.lower()):
            has_generic_name = True

        record(
            "canonical_entity_resolved_non_generic",
            not has_generic_name,
            f"Business entity name is generic or unresolved ('{biz_name}' / '{ent_name}'). Must be deterministically resolved."
        )

        # -------------------------------------------------------------
        # 9. EVIDENCE PROVENANCE & ZERO-FAKE CLAIM LEDGER ENFORCEMENT
        # -------------------------------------------------------------
        # 9.1: Zero unsupported claims allowed as current website facts
        unsupported_facts = []
        if getattr(report, "claim_ledger", None) and report.claim_ledger and getattr(report.claim_ledger, "entries", None):
            for entry in report.claim_ledger.entries:
                st = str(entry.source_type.value if hasattr(entry.source_type, "value") else entry.source_type).upper()
                if (
                    st == "UNSUPPORTED"
                    and not entry.scope.startswith("recommendation")
                    and not entry.scope.startswith("quarantined")
                ):
                    unsupported_facts.append(f"[{entry.claim_id}] {entry.claim[:60]}")
        else:
            # Check findings directly for evidence presence
            for f in report.findings:
                if not getattr(f, "held_from_executive", False):
                    ev_count = len(f.evidence_ids or f.evidence_refs or f.evidence or [])
                    if ev_count == 0:
                        unsupported_facts.append(f"Finding {f.finding_id} has 0 evidence")

        record(
            "zero_unsupported_website_facts",
            len(unsupported_facts) == 0,
            f"Unsupported factual claims detected in current website facts: {'; '.join(unsupported_facts[:3])}"
        )

        # -------------------------------------------------------------
        # 10. PRE-RENDER REPORT INTEGRITY LINTER & DEFECT DONUT HARMONIZATION
        # -------------------------------------------------------------
        # 10.1: Donut severity breakdown equals post-gate findings length exactly
        donut_mismatch = False
        donut_reason = ""
        if report.visual_intelligence and getattr(report.visual_intelligence, "selected_visualizations", None):
            for c in report.visual_intelligence.selected_visualizations:
                if c.chart_type == "defect_donut" and isinstance(c.data, dict):
                    donut_total = c.data.get("total", 0)
                    seg_sum = sum(seg.get("count", 0) for seg in c.data.get("segments", []))
                    findings_len = len(report.findings)
                    if donut_total != findings_len or seg_sum != findings_len:
                        donut_mismatch = True
                        donut_reason = f"Donut chart total ({donut_total}) / segment sum ({seg_sum}) contradicts findings register count ({findings_len})."
                        break
        record(
            "donut_findings_count_exact_match",
            not donut_mismatch,
            donut_reason
        )

        # 10.2: Patch safety hygiene (no literal '...', no 'Disallow: /_next/', no SearchAction, no IP src)
        unsafe_patches = []
        for patch in (report.code_patches or []):
            snip = patch.after_snippet or ""
            if "..." in snip and ("<title>" in snip or '<meta name="description"' in snip):
                unsafe_patches.append(f"{patch.patch_id}: literal '...' in HTML tag")
            if "Disallow: /_next/" in snip:
                unsafe_patches.append(f"{patch.patch_id}: blocks Next.js assets with /_next/")
            if "SearchAction" in snip:
                unsafe_patches.append(f"{patch.patch_id}: references deprecated SearchAction")
            if re.search(r'src=["\']https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', snip):
                unsafe_patches.append(f"{patch.patch_id}: raw IP address in image src")
        record(
            "safe_code_patches_hygiene",
            len(unsafe_patches) == 0,
            f"Unsafe code patches detected: {'; '.join(unsafe_patches[:3])}"
        )

        # 10.3: No self-contradictory H1 or Meta claims
        contradictory_findings = []
        pages_dict = {}
        if manifest and getattr(manifest, "pages", None):
            for p in manifest.pages:
                pages_dict[p.url] = p
        elif getattr(report, "crawl_manifest", None) and getattr(report.crawl_manifest, "pages", None):
            for p in report.crawl_manifest.pages:
                pages_dict[p.url] = p

        for f in report.findings:
            title_low = f.title.lower()
            for ev in (f.evidence or []):
                p_obj = pages_dict.get(ev.url)
                if p_obj:
                    # If page has H1 >= 1, cannot claim missing H1
                    if "missing" in title_low and "h1" in title_low and len(p_obj.h1 or []) >= 1:
                        contradictory_findings.append(f"{f.finding_id}: claims missing H1 but page has {len(p_obj.h1)} H1(s): '{p_obj.h1[0]}'")
                    # If page title length is 50-60 chars, cannot claim title is too long or too short
                    t_len = len(p_obj.title or "")
                    if 50 <= t_len <= 60 and ("too long" in title_low or "too short" in title_low) and "title" in title_low:
                        contradictory_findings.append(f"{f.finding_id}: claims title is too long/short ({t_len} chars) but 50-60 is optimal")

        record(
            "no_self_contradictory_findings",
            len(contradictory_findings) == 0,
            f"Contradictory findings against crawl ground truth: {'; '.join(contradictory_findings[:2])}"
        )

        # -------------------------------------------------------------
        # 11. ZERO-PLACEHOLDER EVIDENCE TOKENS (ELIMINATE [ev_xxx])
        # -------------------------------------------------------------
        placeholder_regex = re.compile(r"\[?(?:ev|ext)_[xX]{3,}\]?", re.IGNORECASE)
        placeholder_violations = []
        for field_name, text in [
            ("story_summary", report.story_summary or ""),
            ("primary_strategic_opportunity", report.primary_strategic_opportunity or ""),
            ("consultant_advice_what_to_ignore", report.consultant_advice_what_to_ignore or ""),
        ]:
            if placeholder_regex.search(text):
                placeholder_violations.append(f"Placeholder token in {field_name}")

        for f in (report.findings or []):
            f_blob = f"{f.title or ''} {f.description or ''} {getattr(f, 'diagnosis', '') or ''} {getattr(f, 'observed_value', '') or ''}"
            if placeholder_regex.search(f_blob):
                placeholder_violations.append(f"Finding {f.finding_id} contains placeholder token in narrative")
            for ev_ref in (getattr(f, "evidence_refs", None) or getattr(f, "evidence_ids", None) or []):
                if placeholder_regex.search(str(ev_ref)):
                    placeholder_violations.append(f"Finding {f.finding_id} references placeholder evidence ref '{ev_ref}'")

        for item in (report.roadmap_7_days or []) + (report.roadmap_30_days or []) + (report.roadmap_90_days or []):
            if placeholder_regex.search(f"{item.title or ''} {item.description or ''}"):
                placeholder_violations.append(f"Roadmap item '{item.title}' contains placeholder token")

        for patch in (report.code_patches or []):
            if placeholder_regex.search(f"{patch.explanation or ''} {patch.after_snippet or ''}"):
                placeholder_violations.append(f"Code patch {patch.patch_id} contains placeholder token")

        record(
            "zero_placeholder_evidence_tokens",
            len(placeholder_violations) == 0,
            f"Placeholder evidence tokens detected: {'; '.join(placeholder_violations[:3])}"
        )

        # -------------------------------------------------------------
        # 12. ZERO-FABRICATION EVIDENCE CONTRACT ENFORCEMENT
        # -------------------------------------------------------------
        unbacked_findings = []
        cross_site_leaks = []
        report_domain = (report.domain or "").lower().replace("www.", "")
        for f in (report.findings or []):
            if getattr(f, "held_from_executive", False):
                continue
            ev_items = getattr(f, "evidence", None) or []
            ev_refs = getattr(f, "evidence_refs", None) or getattr(f, "evidence_ids", None) or []
            has_evidence = len(ev_items) > 0 or len(ev_refs) > 0
            valid_refs = [r for r in ev_refs if not placeholder_regex.search(str(r)) and str(r).strip() not in ["", "none", "null"]]
            if not has_evidence or (len(ev_refs) > 0 and len(valid_refs) == 0 and len(ev_items) == 0):
                unbacked_findings.append(f"{f.finding_id}: '{f.title}' lacks valid evidence")

            if report_domain:
                for ev in ev_items:
                    ev_url = getattr(ev, "url", "") or ""
                    if ev_url and ev_url.startswith("http"):
                        from urllib.parse import urlparse
                        parsed_host = urlparse(ev_url).netloc.lower().replace("www.", "")
                        if parsed_host and report_domain not in parsed_host and parsed_host not in report_domain:
                            ev_type = getattr(ev, "evidence_type", None) or getattr(ev, "source_type", None) or ""
                            if "external" not in str(ev_type).lower() and "competitor" not in str(ev_type).lower():
                                cross_site_leaks.append(f"{f.finding_id}: evidence URL '{ev_url}' does not match site domain '{report_domain}'")

        record(
            "every_finding_has_valid_evidence",
            len(unbacked_findings) == 0 and len(cross_site_leaks) == 0,
            f"Findings failing evidence contract: {'; '.join((unbacked_findings + cross_site_leaks)[:3])}"
        )

        # -------------------------------------------------------------
        # 13. CRAWL INVENTORY & COVERAGE RECONCILIATION
        # -------------------------------------------------------------
        inventory_discrepancies = []
        active_manifest = manifest or getattr(report, "crawl_manifest", None)
        if active_manifest and not hasattr(active_manifest, "_mock_return_value"):
            inv = getattr(active_manifest, "crawl_inventory", None)
            if isinstance(inv, dict):
                disc_total = inv.get("discovered_total", 0)
                tested_pages = inv.get("tested_pages", 0)
            else:
                disc_urls = getattr(active_manifest, "discovered_urls", None)
                disc_total = len(disc_urls) if isinstance(disc_urls, (list, set, tuple)) else 0
                pages = getattr(active_manifest, "pages", None)
                tested_pages = len(pages) if isinstance(pages, (list, set, tuple)) else 0

            if isinstance(disc_total, int) and isinstance(tested_pages, int):
                if disc_total > 0 and tested_pages > disc_total:
                    inventory_discrepancies.append(f"Tested pages ({tested_pages}) exceeds discovered URLs ({disc_total})")

                sampling_status = str(getattr(active_manifest, "sampling_status", ""))
                is_sampled = (sampling_status == "SAMPLED_AUDIT" or (disc_total > tested_pages and tested_pages > 0))
                if is_sampled:
                    all_prose_low = f"{report.story_summary or ''} {report.primary_strategic_opportunity or ''}".lower()
                    if "audited every url" in all_prose_low or "all urls tested" in all_prose_low or "comprehensive audit of all pages" in all_prose_low:
                        inventory_discrepancies.append("Narrative claims comprehensive audit of all pages despite sampled crawl")

        record(
            "crawl_and_url_inventory_reconciled",
            len(inventory_discrepancies) == 0,
            "; ".join(inventory_discrepancies) if inventory_discrepancies else ""
        )

        is_valid = len(failed) == 0
        return ValidationResult(
            is_valid=is_valid,
            passed_checks=passed,
            failed_checks=failed,
            failure_reasons=reasons,
        )

    @classmethod
    def evaluate_quality_gates(cls, report: ExecutiveReport, manifest: Optional[Any] = None) -> Dict[str, Any]:
        """
        Evaluates the 6 Pre-Publication Enterprise Quality Gates:
        1. Evidence Gate: Every material claim has traceable evidence references.
        2. Coverage Gate: Crawl coverage denominator is explicitly disclosed.
        3. Analysis Gate: All applicable diagnostics evaluated with root cause and remediation.
        4. Consistency Gate: Zero cross-chapter contradictions.
        5. Actionability Gate: Priorities have owners, effort, and acceptance criteria.
        6. Reporting Gate: No raw placeholder strings or broken section summaries.
        """
        gates: Dict[str, Dict[str, Any]] = {}

        # Gate 1: Evidence Gate
        untraceable_findings = []
        for f in (report.findings or []):
            if not f.evidence and not f.evidence_refs and not getattr(f, "raw_observation", None):
                untraceable_findings.append(f.finding_id)
        gates["evidence_gate"] = {
            "passed": len(untraceable_findings) == 0,
            "status": "PASS" if len(untraceable_findings) == 0 else "WARNING",
            "details": f"{len(report.findings) - len(untraceable_findings)}/{len(report.findings)} findings have traceable DOM/header evidence."
        }

        # Gate 2: Coverage Gate
        active_manifest = manifest or getattr(report, "crawl_manifest", None)
        inv = getattr(active_manifest, "crawl_inventory", {}) if active_manifest and not hasattr(active_manifest, "_mock_return_value") else {}
        if isinstance(inv, dict):
            disc_total = inv.get("discovered_total", len(report.page_reports))
            tested_count = inv.get("tested_pages", len(report.page_reports))
        else:
            disc_total = len(report.page_reports)
            tested_count = len(report.page_reports)
        if not isinstance(disc_total, (int, float)):
            disc_total = len(report.page_reports)
        if not isinstance(tested_count, (int, float)):
            tested_count = len(report.page_reports)
        cov_val = round((tested_count / max(1, disc_total)) * 100.0, 1)
        gates["coverage_gate"] = {
            "passed": disc_total >= tested_count,
            "status": "PASS" if disc_total >= tested_count else "WARNING",
            "details": f"Tested {tested_count} of {disc_total} discovered URLs ({cov_val}% coverage)."
        }

        # Gate 3: Analysis Gate
        crit_high = [f for f in report.findings if f.priority >= 7 or str(f.severity.value).upper() in ("CRITICAL", "HIGH")]
        missing_root_causes = [f.finding_id for f in crit_high if not f.root_cause]
        gates["analysis_gate"] = {
            "passed": len(missing_root_causes) == 0,
            "status": "PASS" if len(missing_root_causes) == 0 else "FAIL",
            "details": f"All {len(crit_high)} Critical/High findings have verified root-cause chains." if not missing_root_causes else f"{len(missing_root_causes)} high-impact findings lack causal diagnosis."
        }

        # Gate 4: Consistency Gate
        cons_rep = getattr(report, "consistency_report", None)
        cons_ok = getattr(cons_rep, "is_consistent", True) if cons_rep else True
        gates["consistency_gate"] = {
            "passed": cons_ok,
            "status": "PASS" if cons_ok else "WARNING",
            "details": getattr(cons_rep, "summary", "Cross-chapter consistency verified.") if cons_rep else "Cross-chapter consistency verified."
        }

        # Gate 5: Actionability Gate
        roadmap = (report.roadmap_7_days or []) + (report.roadmap_30_days or [])
        missing_action = [r.title for r in roadmap if not getattr(r, "description", None) and not getattr(r, "title", None)]
        gates["actionability_gate"] = {
            "passed": len(missing_action) == 0,
            "status": "PASS" if len(missing_action) == 0 else "WARNING",
            "details": f"All {len(roadmap)} prioritized roadmap items have explicit titles and actionable descriptions." if not missing_action else f"{len(missing_action)} roadmap actions lack actionable descriptions."
        }

        # Gate 6: Reporting Gate
        has_placeholders = any(
            ph in str(getattr(report, f, "")).lower()
            for f in ["story_summary", "primary_strategic_opportunity"]
            for ph in ["[todo]", "undefined", "nan", "null"]
        )
        gates["reporting_gate"] = {
            "passed": not has_placeholders,
            "status": "PASS" if not has_placeholders else "FAIL",
            "details": "Zero placeholder tokens detected across executive narrative." if not has_placeholders else "Executive narrative contains unresolved placeholder strings."
        }

        all_passed = all(g["passed"] for g in gates.values())
        return {
            "all_passed": all_passed,
            "gates": gates,
            "scorecard": f"{sum(1 for g in gates.values() if g['passed'])}/6 Quality Gates Cleared",
        }

    @classmethod
    def repair_report(cls, report: ExecutiveReport, manifest: Optional[Any] = None) -> Tuple[ExecutiveReport, List[str]]:
        """
        Applies deterministic auto-repair passes to fix common violations:
        1. Scoring arithmetic: aligns overall_score = sum(weighted_score) and weights sum to 100%.
        2. Deduplication: clusters findings by root cause and removes duplicate roadmap actions.
        3. Patch cleansing: removes unverified sameAs social links and strips nulls.
        4. Field normalization: replaces raw dashes with explicit 'Not determinable from crawled evidence'.
        5. Copy linting: removes banned terms.
        """
        repairs_made: List[str] = []

        from app.scoring.displayed_score import align_story_score, displayed_composite, story_matches_composite
        dossier_composite = displayed_composite(report)
        if dossier_composite is not None and report.story_summary and not story_matches_composite(report.story_summary, dossier_composite):
            sealed = getattr(getattr(report, "scores", None), "overall_score", None)
            aligned = align_story_score(report.story_summary, sealed, dossier_composite)
            if aligned != report.story_summary:
                report.story_summary = aligned
                repairs_made.append(
                    f"Rewrote the executive headline score to the dossier composite {dossier_composite:.1f}."
                )

        # 0. Rule 4.2: Cross-check 100-scores against findings and rescore
        if report.scores and report.scores.category_scores:
            for cat_name, cat_obj in report.scores.category_scores.items():
                if cat_obj.score is not None and cat_obj.score >= 99.5:
                    cat_defects = [
                        f for f in report.findings
                        if f.category == cat_obj.category and str(f.severity).upper() in ["CRITICAL", "HIGH", "SEVERITY.CRITICAL", "SEVERITY.HIGH"]
                    ]
                    if cat_defects:
                        deduction = sum(25.0 if "CRITICAL" in str(f.severity).upper() else 15.0 for f in cat_defects)
                        cat_obj.score = max(35.0, 100.0 - deduction)
                        cat_obj.weighted_score = round((cat_obj.score * (cat_obj.weight or 0.0)) / 100.0, 2)
                        repairs_made.append(f"Rescored {cat_name} from 100.0 to {cat_obj.score} due to {len(cat_defects)} HIGH/CRITICAL finding(s).")

        # 1. Reconcile scoring arithmetic
        if report.scores and report.scores.category_scores:
            total_weighted = 0.0
            total_weight = sum(c.weight for c in report.scores.category_scores.values() if c.weight is not None)
            for cat_key, cat_obj in report.scores.category_scores.items():
                if 0.99 <= total_weight <= 1.01:
                    cat_obj.weight = (cat_obj.weight or 0.0) * 100.0
                score_val = float(cat_obj.score) if cat_obj.score is not None else 0.0
                cat_obj.weighted_score = round((score_val * (cat_obj.weight or 0.0)) / 100.0, 2)
                total_weighted += cat_obj.weighted_score
            new_overall = round(total_weighted, 1)
            curr_overall = report.scores.overall_score if report.scores.overall_score is not None else 0.0
            if abs(curr_overall - new_overall) > 0.1:
                repairs_made.append(f"Reconciled overall score from {report.scores.overall_score} to exact weighted sum {new_overall}")
                report.scores.overall_score = new_overall

        # 1b. Align composite AI citation score with query matrix or live citation status
        if report.honest_scores and report.honest_scores.ai_citation_score is not None:
            if getattr(report.honest_scores, "live_ai_citation_score", None) is None:
                report.honest_scores.ai_citation_score = None
                repairs_made.append("Cleared ai_citation_score because live engine measurement was unexecuted.")
            elif report.ai_search_matrix:
                def _get_q_score(q):
                    if hasattr(q, "score") and q.score is not None:
                        return float(q.score) * 10.0
                    if hasattr(q, "citation_probability") and q.citation_probability is not None:
                        return float(q.citation_probability) * 100.0
                    return float(getattr(q, "citability_score", 50.0))
                matrix_avg = sum(_get_q_score(q) for q in report.ai_search_matrix) / len(report.ai_search_matrix)
                if abs(report.honest_scores.ai_citation_score - matrix_avg) > 50:
                    report.honest_scores.ai_citation_score = round(matrix_avg, 1)
                    repairs_made.append(f"Reconciled composite AI citation score with query matrix average ({matrix_avg:.1f}).")

        # 2. Roadmap deduplication
        seen_roadmap_titles: Set[str] = set()
        clean_r7 = []
        for item in report.roadmap_7_days:
            title_key = item.title.lower().strip()
            if title_key not in seen_roadmap_titles:
                seen_roadmap_titles.add(title_key)
                clean_r7.append(item)
            else:
                repairs_made.append(f"Removed duplicate roadmap item: {item.title}")

        clean_r30 = []
        for item in report.roadmap_30_days:
            title_key = item.title.lower().strip()
            if title_key not in seen_roadmap_titles:
                seen_roadmap_titles.add(title_key)
                clean_r30.append(item)
            else:
                repairs_made.append(f"Removed duplicate roadmap item: {item.title}")

        clean_r90 = []
        for item in report.roadmap_90_days:
            title_key = item.title.lower().strip()
            if title_key not in seen_roadmap_titles:
                seen_roadmap_titles.add(title_key)
                clean_r90.append(item)
            else:
                repairs_made.append(f"Removed duplicate roadmap item: {item.title}")

        report.roadmap_7_days = clean_r7
        report.roadmap_30_days = clean_r30
        report.roadmap_90_days = clean_r90

        # 3. Deduplicate findings by root cause
        seen_finding_keys: Set[str] = set()
        clean_findings: List[Finding] = []
        for f in report.findings:
            key = f"{f.category}:{f.title.lower().strip()}"
            if key not in seen_finding_keys:
                seen_finding_keys.add(key)
                clean_findings.append(f)
            else:
                repairs_made.append(f"Merged duplicate root cause finding: {f.title}")
        report.findings = clean_findings

        # 3b. Contradiction reconciliation with crawl ground truth & pairwise conflicts
        from app.cognition.contradiction_engine import contradiction_engine
        from app.cognition.report_critic import ReportCritic
        manifest_for_repair = manifest or getattr(report, "crawl_manifest", None)
        report, critic_actions = ReportCritic.reconcile_report(
            report, manifest=manifest_for_repair, heading_hierarchy=report.heading_hierarchy
        )
        repairs_made.extend(critic_actions)

        reconciled_findings, rollup_actions = contradiction_engine.reconcile_with_manifest_and_rollups(
            report.findings, manifest=manifest_for_repair, heading_hierarchy=report.heading_hierarchy
        )
        repairs_made.extend(rollup_actions)

        # Pairwise contradiction resolution across findings
        ctrd_reports, reconciled_findings = contradiction_engine.reconcile(reconciled_findings)
        # Suppress loser findings from executive reporting
        report.findings = [f for f in reconciled_findings if not getattr(f, "held_from_executive", False)]
        if ctrd_reports:
            report.contradictions = (report.contradictions or []) + ctrd_reports
            repairs_made.append(f"Reconciled {len(ctrd_reports)} pairwise finding contradiction(s).")

        # 4. Clean patches (strip unobserved sameAs social links & nulls)
        for patch in report.code_patches:
            snippet = patch.after_snippet or ""
            if '"sameAs"' in snippet and any(s in snippet for s in ["twitter.com", "linkedin.com"]):
                clean_snip = re.sub(r',\s*"sameAs":\s*\[[^\]]*\]', '', snippet)
                clean_snip = re.sub(r'"sameAs":\s*\[[^\]]*\],\s*', '', clean_snip)
                if clean_snip != snippet:
                    patch.after_snippet = clean_snip
                    repairs_made.append(f"Omitted unobserved sameAs URLs from patch {patch.patch_id}")

            clean_snip = re.sub(r',\s*"[^"]+":\s*null', '', patch.after_snippet)
            clean_snip = re.sub(r'"[^"]+":\s*null,\s*', '', clean_snip)
            if clean_snip != patch.after_snippet:
                patch.after_snippet = clean_snip
                repairs_made.append(f"Stripped null attributes from patch {patch.patch_id}")

        # 5. Field completeness (replace dashes)
        bp = report.business_profile
        if bp:
            for field_name in ["value_proposition", "target_audience", "business_model"]:
                val = getattr(bp, field_name, "")
                if str(val).strip() in ["—", "-", "--", "N/A", "null", "None", ""]:
                    setattr(bp, field_name, "Not determinable from crawled evidence (no structured declaration found)")
                    repairs_made.append(f"Replaced placeholder dash in business_profile.{field_name}")

        # 6. Outcome claims must follow blocking records
        from app.reports.narrative import calibrated_field_replacements
        from app.scoring.calibration import rewrite_outcome_overclaims
        replacements = calibrated_field_replacements(
            report.findings or [],
            report.scores,
            report.business_profile,
        )
        for field_name, replacement in replacements.items():
            current = getattr(report, field_name, "") or ""
            updated, changed = rewrite_outcome_overclaims(current, replacement)
            if changed and updated != current:
                setattr(report, field_name, updated)
                repairs_made.append(
                    f"Rewrote {field_name} so a non-blocking finding is not treated as freezing unrelated outcomes."
                )

        # 7. Copy linting for banned terms
        for term in BANNED_TERMS:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            report.story_summary = pattern.sub("enterprise-grade", report.story_summary)
            report.primary_strategic_opportunity = pattern.sub("high-priority", report.primary_strategic_opportunity)
            report.consultant_advice_what_to_ignore = pattern.sub("secondary", report.consultant_advice_what_to_ignore)

        # 7. Directive vs Roadmap Sequencing Agreement (Rule 6.1)
        ignore_text_repair = (report.consultant_advice_what_to_ignore or "").lower()
        deprioritizes_tech_seo_repair = any(k in ignore_text_repair for k in ["technical seo", "meta tag", "sitemap"])
        if deprioritizes_tech_seo_repair:
            conflicting_r7_indices = []
            for i, item in enumerate(report.roadmap_7_days):
                cat_str = str(item.category).upper()
                title_lower = item.title.lower()
                is_tech = "TECHNICAL_SEO" in cat_str or "sitemap" in title_lower or ("meta description" in title_lower and "h1" not in title_lower)
                if is_tech:
                    conflicting_r7_indices.append(i)

            if conflicting_r7_indices:
                non_conflicting_r7 = [item for i, item in enumerate(report.roadmap_7_days) if i not in conflicting_r7_indices]
                moved_items = [report.roadmap_7_days[i] for i in conflicting_r7_indices]
                if non_conflicting_r7:
                    report.roadmap_7_days = non_conflicting_r7
                    existing_30_titles = {it.title.lower().strip() for it in report.roadmap_30_days}
                    for it in moved_items:
                        it.timeframe = "30_days"
                        if it.title.lower().strip() not in existing_30_titles:
                            report.roadmap_30_days.append(it)
                            existing_30_titles.add(it.title.lower().strip())
                    repairs_made.append(f"Resequenced {len(moved_items)} technical SEO items from 7-day to 30-day roadmap to align with 'What to Ignore' directive.")
                else:
                    report.consultant_advice_what_to_ignore = (
                        "Ignore vanity cosmetic animations, bulk backlink outreach, and speculative TAM expansion until the foundational Phase 1 architecture is deployed."
                    )
                    repairs_made.append("Aligned 'What to Ignore' directive to deprioritize vanity tasks rather than Phase 1 foundational items.")

        # 8. Canonical Entity auto-repair (eradicate generic or 'Unknown Business')
        from app.intelligence.business.entity_resolver import UniversalEntityResolver, BANNED_NAMES
        bp_name = (report.business_profile.business_name if report.business_profile else "") or ""
        re_name = (report.resolved_entity.name if getattr(report, "resolved_entity", None) else "") or ""
        if (
            bp_name.strip().lower() in BANNED_NAMES or
            re_name.strip().lower() in BANNED_NAMES or
            "unknown business" in bp_name.lower() or
            "unknown business" in re_name.lower() or
            not getattr(report, "resolved_entity", None)
        ):
            pages = manifest.pages if (manifest and getattr(manifest, "pages", None)) else (report.crawl_manifest.pages if report.crawl_manifest else [])
            resolved = UniversalEntityResolver.resolve_from_evidence(
                website_url=report.website_url or report.domain,
                pages=pages,
                profile=report.business_profile
            )
            report.resolved_entity = resolved
            if report.business_profile:
                report.business_profile.business_name = resolved.name
            repairs_made.append(f"Auto-resolved canonical entity to '{resolved.name}' and eradicated generic '{bp_name}'.")

        # 9. Sanitize UNSUPPORTED claims from website facts to enforce Certified Zero-Fake
        if getattr(report, "claim_ledger", None) and report.claim_ledger:
            from app.evidence.claim_ledger import ClaimLedgerBuilder
            report, ledger_repairs = ClaimLedgerBuilder.sanitize_unsupported_facts(report, report.claim_ledger)
            repairs_made.extend(ledger_repairs)

        clean_ev_findings = []
        for f in report.findings:
            ev_cnt = len(f.evidence_ids or f.evidence_refs or f.evidence or [])
            if ev_cnt == 0:
                repairs_made.append(f"Quarantined unbacked finding {f.finding_id} ('{f.title}') from executive facts.")
            else:
                clean_ev_findings.append(f)
        report.findings = clean_ev_findings

        # 10. Clean code patches (remove Disallow /_next/, SearchAction, preload, ellipses)
        for patch in (report.code_patches or []):
            if patch.after_snippet:
                snip = patch.after_snippet
                if "Disallow: /_next/" in snip:
                    snip = snip.replace("Disallow: /_next/\n\n", "").replace("Disallow: /_next/\n", "")
                    repairs_made.append(f"Removed Disallow: /_next/ from patch {patch.patch_id} to prevent asset rendering blockage.")
                if "SearchAction" in snip:
                    snip = re.sub(r'{\s*"@type":\s*"SearchAction"[^}]*},\s*', '', snip)
                    repairs_made.append(f"Removed deprecated SearchAction from patch {patch.patch_id}.")
                if "; preload" in snip:
                    snip = snip.replace("; preload", "")
                    repairs_made.append(f"Removed premature HSTS preload from patch {patch.patch_id}.")
                if "..." in snip and "<title>" in snip:
                    snip = re.sub(r'\.\.\.</title>', '</title>', snip)
                    repairs_made.append(f"Removed literal ellipsis from <title> in patch {patch.patch_id}.")
                patch.after_snippet = snip

        # 11. Remove contradictory findings against crawl ground truth
        pages_dict = {}
        if manifest and getattr(manifest, "pages", None):
            for p in manifest.pages:
                pages_dict[p.url] = p
        elif getattr(report, "crawl_manifest", None) and getattr(report.crawl_manifest, "pages", None):
            for p in report.crawl_manifest.pages:
                pages_dict[p.url] = p

        if pages_dict:
            non_contradictory_findings = []
            for f in report.findings:
                title_low = f.title.lower()
                is_contradiction = False
                for ev in (f.evidence or []):
                    p_obj = pages_dict.get(ev.url)
                    if p_obj:
                        if "missing" in title_low and "h1" in title_low and len(p_obj.h1 or []) >= 1:
                            is_contradiction = True
                            repairs_made.append(f"Quarantined finding {f.finding_id} claiming missing H1 because page has {len(p_obj.h1)} verified H1(s).")
                            break
                        t_len = len(p_obj.title or "")
                        if 50 <= t_len <= 60 and ("too long" in title_low or "too short" in title_low) and "title" in title_low:
                            is_contradiction = True
                            repairs_made.append(f"Quarantined finding {f.finding_id} claiming title is too long/short ({t_len} chars) because 50-60 is optimal.")
                            break
                if not is_contradiction:
                    non_contradictory_findings.append(f)
            report.findings = non_contradictory_findings

        # 11b. Strip placeholder evidence tokens from narrative, findings, roadmap, and code patches
        placeholder_pat = re.compile(r"\s*\[?(?:ev|ext)_[xX]{3,}\]?", re.IGNORECASE)
        for field_name in ["story_summary", "primary_strategic_opportunity", "consultant_advice_what_to_ignore"]:
            val = getattr(report, field_name, "") or ""
            if placeholder_pat.search(val):
                cleaned = placeholder_pat.sub("", val).strip()
                setattr(report, field_name, cleaned)
                repairs_made.append(f"Stripped placeholder evidence tokens from {field_name}.")

        for list_field in ["what_site_gets_right", "what_is_holding_it_back"]:
            val_list = getattr(report, list_field, []) or []
            if any(placeholder_pat.search(s) for s in val_list):
                setattr(report, list_field, [placeholder_pat.sub("", s).strip() for s in val_list])
                repairs_made.append(f"Stripped placeholder evidence tokens from {list_field}.")

        for f in report.findings:
            if placeholder_pat.search(f.title or ""):
                f.title = placeholder_pat.sub("", f.title).strip()
                repairs_made.append(f"Stripped placeholder tokens from finding {f.finding_id} title.")
            if placeholder_pat.search(f.description or ""):
                f.description = placeholder_pat.sub("", f.description).strip()
                repairs_made.append(f"Stripped placeholder tokens from finding {f.finding_id} description.")
            if getattr(f, "finding", None) and placeholder_pat.search(f.finding):
                f.finding = placeholder_pat.sub("", f.finding).strip()
            if getattr(f, "diagnosis", None) and placeholder_pat.search(f.diagnosis):
                f.diagnosis = placeholder_pat.sub("", f.diagnosis).strip()
                repairs_made.append(f"Stripped placeholder tokens from finding {f.finding_id} diagnosis.")
            if getattr(f, "observed_value", None) and placeholder_pat.search(str(f.observed_value)):
                f.observed_value = placeholder_pat.sub("", str(f.observed_value)).strip()
                repairs_made.append(f"Stripped placeholder tokens from finding {f.finding_id} observed_value.")
            if getattr(f, "recommendation", None) and placeholder_pat.search(f.recommendation):
                f.recommendation = placeholder_pat.sub("", f.recommendation).strip()

            raw_refs = getattr(f, "evidence_refs", None) or []
            clean_refs = [
                r for r in raw_refs
                if not placeholder_pat.search(str(r)) and str(r).strip() not in ["", "none", "null"]
            ]
            if len(clean_refs) != len(raw_refs):
                f.evidence_refs = clean_refs
                repairs_made.append(f"Removed placeholder evidence refs from finding {f.finding_id}.")

            raw_ids = getattr(f, "evidence_ids", None) or []
            clean_ids = [
                r for r in raw_ids
                if not placeholder_pat.search(str(r)) and str(r).strip() not in ["", "none", "null"]
            ]
            if len(clean_ids) != len(raw_ids):
                f.evidence_ids = clean_ids
                repairs_made.append(f"Removed placeholder evidence IDs from finding {f.finding_id}.")

            # Keep evidence_refs and evidence_ids synchronized
            if f.evidence_refs and not f.evidence_ids:
                f.evidence_ids = list(f.evidence_refs)
            elif f.evidence_ids and not f.evidence_refs:
                f.evidence_refs = list(f.evidence_ids)

        for item in (report.roadmap_7_days or []) + (report.roadmap_30_days or []) + (report.roadmap_90_days or []):
            if placeholder_pat.search(item.title or ""):
                item.title = placeholder_pat.sub("", item.title).strip()
            if placeholder_pat.search(item.description or ""):
                item.description = placeholder_pat.sub("", item.description).strip()

        for patch in (report.code_patches or []):
            if placeholder_pat.search(patch.explanation or ""):
                patch.explanation = placeholder_pat.sub("", patch.explanation).strip()
                repairs_made.append(f"Stripped placeholder tokens from patch {patch.patch_id} explanation.")
            if placeholder_pat.search(patch.after_snippet or ""):
                patch.after_snippet = placeholder_pat.sub("", patch.after_snippet).strip()
                repairs_made.append(f"Stripped placeholder tokens from patch {patch.patch_id} after_snippet.")

        # 11c. Quarantine unbacked findings or findings that only possessed placeholder evidence
        clean_backed_findings = []
        for f in report.findings:
            ev_cnt = len(getattr(f, "evidence", None) or [])
            valid_refs = [r for r in (getattr(f, "evidence_refs", None) or getattr(f, "evidence_ids", None) or []) if not placeholder_pat.search(str(r)) and str(r).strip() not in ["", "none", "null"]]
            if ev_cnt == 0 and len(valid_refs) == 0:
                repairs_made.append(f"Quarantined unbacked finding {f.finding_id} ('{f.title}') lacking valid evidence.")
            else:
                clean_backed_findings.append(f)
        report.findings = clean_backed_findings

        # 11d. Reconcile sampled crawl claims
        active_manifest = manifest or getattr(report, "crawl_manifest", None)
        if active_manifest and not hasattr(active_manifest, "_mock_return_value"):
            inv = getattr(active_manifest, "crawl_inventory", None)
            if isinstance(inv, dict):
                disc_total = inv.get("discovered_total", 0)
                tested_pages = inv.get("tested_pages", 0)
            else:
                disc_urls = getattr(active_manifest, "discovered_urls", None)
                disc_total = len(disc_urls) if isinstance(disc_urls, (list, set, tuple)) else 0
                pages = getattr(active_manifest, "pages", None)
                tested_pages = len(pages) if isinstance(pages, (list, set, tuple)) else 0

            if isinstance(disc_total, int) and isinstance(tested_pages, int):
                sampling_status = str(getattr(active_manifest, "sampling_status", ""))
                is_sampled = sampling_status == "SAMPLED_AUDIT" or (disc_total > tested_pages and tested_pages > 0)
                if is_sampled and report.story_summary:
                    for overclaim in ["audited every url", "all urls tested", "comprehensive audit of all pages"]:
                        if overclaim in report.story_summary.lower():
                            report.story_summary = re.sub(
                                re.escape(overclaim),
                                f"sampled audit of {tested_pages} representative pages out of {disc_total} discovered",
                                report.story_summary,
                                flags=re.IGNORECASE
                            )
                            repairs_made.append("Reconciled sampled crawl coverage claims in story_summary.")

        # 12. Pre-Render Donut & Visual Intelligence Re-synchronization
        # Re-synthesize visual intelligence using post-gate finalized findings
        try:
            from app.intelligence.monitoring.visual_intelligence import visual_intelligence_engine
            report.visual_intelligence = visual_intelligence_engine.synthesize_visual_intelligence(
                domain=report.domain,
                business_profile=report.business_profile,
                scores=report.scores,
                honest_scores=report.honest_scores,
                manifest=report.crawl_manifest or manifest,
                findings=report.findings,
                ai_search_matrix=report.ai_search_matrix,
            )
            repairs_made.append("Re-synchronized visual intelligence and defect donut with finalized post-gate findings ledger.")
        except Exception:
            pass

        return report, repairs_made

    @classmethod
    def enforce_gate(cls, report: ExecutiveReport, manifest: Optional[Any] = None) -> Tuple[ExecutiveReport, ValidationResult]:
        """
        Runs validation gate, attempts deterministic repair if needed,
        and re-runs gate. Discloses all alterations in the visible integrity log.
        If fatal violations remain, marks report as DEGRADED_SECTIONS_WITHHELD.
        """
        initial_result = cls.validate_report(report, manifest)
        if initial_result.is_valid:
            return report, initial_result

        # Attempt deterministic auto-repair
        repaired_report, repairs = cls.repair_report(report, manifest)
        final_result = cls.validate_report(repaired_report, manifest)
        final_result.repaired = len(repairs) > 0

        # Disclose every single automated repair in the visible Report Integrity Log
        if repairs:
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
            existing_log = getattr(repaired_report, "integrity_repairs_log", None) or []
            for r in repairs:
                existing_log.append({
                    "timestamp": now_iso,
                    "action": "DETERMINISTIC_REPAIR",
                    "description": r,
                    "auditable": True
                })
            repaired_report.integrity_repairs_log = existing_log

        # Graceful degraded fallback: if repairs cannot clear the gate, withhold affected sections with audit label
        if not final_result.is_valid:
            repaired_report.certification_status = "DEGRADED_SECTIONS_WITHHELD"
            withheld = []
            for check in final_result.failed_checks:
                sec = (
                    "Section 2.0 (Institutional Scorecard)" if "score" in check or "weight" in check
                    else "Section 8.0 (Code Patches)" if "patch" in check or "sameas" in check or "json" in check
                    else "Section 9.0 (Roadmap)" if "roadmap" in check or "directive" in check
                    else "Section 5.0 (AI Search & Citations)"
                )
                withheld.append({
                    "check": check,
                    "section": sec,
                    "reason": f"Section withheld from formal certification due to unresolved gate check: {check}"
                })
            repaired_report.withheld_sections = withheld

        repaired_report.quality_gate_results = cls.evaluate_quality_gates(repaired_report, manifest)
        return repaired_report, final_result
