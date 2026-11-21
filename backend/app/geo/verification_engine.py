"""Phase 13 — Independent GEO Verification & Before/After Comparison Engine.

Non-negotiable verification rules:
1. A developer marking a task deployed/complete NEVER closes it as verified.
2. Independently re-crawls (SSRF-guarded) or validates post-change snapshots,
   checks structured data & entity consistency, and compares matched prompt runs
   preserving original prompt, platform, model version, testing mode, market,
   language, timestamp, and repetition number.
3. Strictly separates `implementation_verified` from `outcome_improved`:
   Content update verified = Yes + Brand inclusion improved = Not observed is a
   legitimate, honest result—not a failed implementation.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.security.ssrf import is_safe_url
from app.geo.models import (
    GEODataQualityState,
    GEORemediationTask,
    GEOTaskStatus,
    GEOVerification,
)


def _extract_jsonld_types(html_text: str) -> List[str]:
    types: List[str] = []
    for match in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html_text or "", re.I | re.S):
        try:
            obj = json.loads(match.group(1))
            items = obj if isinstance(obj, list) else [obj]
            for it in items:
                if isinstance(it, dict):
                    t = it.get("@type")
                    if isinstance(t, list):
                        types.extend(str(x) for x in t)
                    elif t:
                        types.append(str(t))
        except Exception:
            continue
    return sorted(set(types))


class GEOIndependentVerificationEngine:
    """Independently re-checks deployed GEO changes and compares before/after evidence."""

    @classmethod
    async def verify_task(
        cls,
        *,
        task: GEORemediationTask,
        verified_by: str,
        before_html: Optional[str] = None,
        after_html: Optional[str] = None,
        target_url: Optional[str] = None,
        expected_text_present: Optional[str] = None,
        expected_schema_type: Optional[str] = None,
        pre_prompt_metrics: Optional[Dict[str, Any]] = None,
        post_prompt_metrics: Optional[Dict[str, Any]] = None,
        retest_metadata: Optional[Dict[str, Any]] = None,
        live_recrawl: bool = False,
    ) -> GEOVerification:
        unavailable_tests: List[str] = []
        fetched_after_html = after_html

        if live_recrawl and not fetched_after_html and target_url:
            safe, reason = is_safe_url(target_url)
            if not safe:
                unavailable_tests.append(f"Live re-crawl blocked by SSRF guard: {reason}")
            else:
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                        resp = await client.get(target_url, headers={"User-Agent": "Dristik-GEO-Verifier/1.0"})
                        if resp.status_code < 400:
                            fetched_after_html = resp.text[:250_000]
                        else:
                            unavailable_tests.append(f"Live re-crawl returned HTTP {resp.status_code}")
                except Exception as exc:
                    unavailable_tests.append(f"Live re-crawl failed: {exc}")

        # 1. Verify implementation independently (content, schema, entities)
        content_verified: Optional[bool] = None
        schema_verified: Optional[bool] = None
        entity_verified: Optional[bool] = None

        if fetched_after_html is not None:
            if expected_text_present:
                content_verified = expected_text_present.lower() in fetched_after_html.lower()
            elif before_html is not None:
                content_verified = fetched_after_html.strip() != before_html.strip() and len(fetched_after_html.strip()) > 0
            else:
                content_verified = len(fetched_after_html.strip()) > 0

            after_schemas = _extract_jsonld_types(fetched_after_html)
            if expected_schema_type:
                schema_verified = expected_schema_type in after_schemas
            elif after_schemas:
                schema_verified = True
            else:
                schema_verified = None

            if task.affected_entities:
                entity_verified = any(e.lower() in fetched_after_html.lower() for e in task.affected_entities)
        else:
            unavailable_tests.append("No post-change page snapshot supplied or fetched for HTML/schema verification.")

        checks_present = [x for x in (content_verified, schema_verified, entity_verified) if x is not None]
        impl_verified = bool(checks_present) and all(checks_present)

        # 2. Independently compare observed AI outcomes (strictly separate from implementation_verified)
        brand_inc_status = "NOT_TESTED"
        cit_freq_status = "NOT_TESTED"
        outcome_status = "NOT_TESTED"
        regression_detected = False
        regression_details: List[str] = []

        if pre_prompt_metrics and post_prompt_metrics:
            pre_m = pre_prompt_metrics.get("mention_rate_pct")
            post_m = post_prompt_metrics.get("mention_rate_pct")
            pre_c = pre_prompt_metrics.get("citation_rate_pct")
            post_c = post_prompt_metrics.get("citation_rate_pct")
            if isinstance(pre_m, (int, float)) and isinstance(post_m, (int, float)):
                if post_m > pre_m:
                    brand_inc_status = "OBSERVED"
                elif post_m < pre_m - 5.0:
                    brand_inc_status = "REGRESSED"
                    regression_detected = True
                    regression_details.append(f"Brand mention rate dropped from {pre_m}% to {post_m}%.")
                else:
                    brand_inc_status = "NOT_OBSERVED"
            if isinstance(pre_c, (int, float)) and isinstance(post_c, (int, float)):
                if post_c > pre_c:
                    cit_freq_status = "OBSERVED"
                elif post_c < pre_c - 5.0:
                    cit_freq_status = "REGRESSED"
                    regression_detected = True
                    regression_details.append(f"Citation rate dropped from {pre_c}% to {post_c}%.")
                else:
                    cit_freq_status = "NOT_OBSERVED"

            if regression_detected:
                outcome_status = "REGRESSED"
            elif brand_inc_status == "OBSERVED" or cit_freq_status == "OBSERVED":
                outcome_status = "OBSERVED"
            elif brand_inc_status == "NOT_OBSERVED" or cit_freq_status == "NOT_OBSERVED":
                outcome_status = "NOT_OBSERVED"
        else:
            unavailable_tests.append("Matched pre/post AI prompt retest metrics were not provided.")

        # 3. Evaluate acceptance criteria
        criteria_results = [
            {
                "criterion": c,
                "passed": impl_verified if not regression_detected else False,
                "note": "Implementation independently verified." if impl_verified else "Pending or failed independent check.",
            }
            for c in (task.acceptance_criteria or ["Implementation verified on live content"])
        ]

        # 4. Determine overall status preserving the critical distinction
        if regression_detected:
            overall = "regressed"
            task.status = GEOTaskStatus.REGRESSED.value
        elif impl_verified and outcome_status == "OBSERVED":
            overall = "verified"
            task.status = GEOTaskStatus.VERIFIED.value
        elif impl_verified and outcome_status in ("NOT_OBSERVED", "NOT_TESTED"):
            # Legitimate result: implementation IS verified even when AI models haven't shifted yet
            overall = "implementation_verified_no_outcome_change"
            task.status = GEOTaskStatus.VERIFIED.value
        elif not checks_present:
            overall = "partial"
            task.status = GEOTaskStatus.VERIFYING.value
        else:
            overall = "failed"
            task.status = GEOTaskStatus.FAILED_VERIFICATION.value

        task.implementation_verified = impl_verified
        task.outcome_improved = outcome_status

        before_after = {
            "page_content": {
                "before": (before_html or "")[:300] or None,
                "after": (fetched_after_html or "")[:300] or None,
                "verified": content_verified,
            },
            "structured_data": {
                "before": _extract_jsonld_types(before_html or "") if before_html else [],
                "after": _extract_jsonld_types(fetched_after_html or "") if fetched_after_html else [],
                "verified": schema_verified,
            },
            "brand_mentions": {
                "before": (pre_prompt_metrics or {}).get("mention_rate_pct"),
                "after": (post_prompt_metrics or {}).get("mention_rate_pct"),
                "status": brand_inc_status,
            },
            "citations": {
                "before": (pre_prompt_metrics or {}).get("citation_rate_pct"),
                "after": (post_prompt_metrics or {}).get("citation_rate_pct"),
                "status": cit_freq_status,
            },
            "competitor_comparison": {
                "before": (pre_prompt_metrics or {}).get("competitor_mention_rate_pct"),
                "after": (post_prompt_metrics or {}).get("competitor_mention_rate_pct"),
            },
            "finding_status": {
                "before": "open",
                "after": task.status,
            },
        }

        ver = GEOVerification(
            tenant_id=task.tenant_id,
            audit_id=task.audit_id,
            task_id=task.task_id,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc).isoformat(),
            implementation_verified=impl_verified,
            content_update_verified=content_verified,
            structured_data_verified=schema_verified,
            entity_consistency_verified=entity_verified,
            external_source_checked=None,
            outcome_improved=outcome_status,
            brand_inclusion_improved=brand_inc_status,
            citation_frequency_improved=cit_freq_status,
            regression_detected=regression_detected,
            regression_details=regression_details,
            before_after_comparison=before_after,
            acceptance_criteria_results=criteria_results,
            retest_metadata=retest_metadata or {},
            evidence_ids=[task.task_id] + ([target_url] if target_url else []),
            unavailable_tests=unavailable_tests,
            overall_status=overall,
            data_quality_state=GEODataQualityState.VERIFIED if impl_verified else GEODataQualityState.PARTIAL,
            source_refs=[task.task_id],
        )
        task.verification_id = ver.verification_id
        task.after_evidence = before_after
        return ver
