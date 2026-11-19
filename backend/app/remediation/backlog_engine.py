"""
Canonical Remediation Backlog Engine — Phase 8.1 (10/10 Transformation)

Automatically ingests audit findings and generates structured remediation tasks
containing all 14 required canonical fields:
1. Finding ID
2. Root cause
3. Affected URLs
4. Affected templates
5. Recommended action
6. Business impact
7. Technical severity
8. Confidence
9. Estimated effort
10. Dependencies
11. Required permissions
12. Owner
13. Status
14. Verification criteria
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.domain.canonical_audit_model import CanonicalFinding
from app.domain.models import Finding
from app.remediation.models import RemediationTaskRecord, TaskStatus

logger = logging.getLogger("dristik.remediation.backlog")

# Deterministic effort and permission heuristics based on root cause / category
CATEGORY_PERMISSION_MAP: Dict[str, List[str]] = {
    "TECHNICAL_SEO": ["SERVER_CONFIG_WRITE", "ROBOTS_TXT_WRITE"],
    "ON_PAGE_SEO": ["THEME_WRITE", "METADATA_WRITE"],
    "GEO": ["SCHEMA_WRITE", "ROBOTS_TXT_WRITE", "LLMS_TXT_WRITE"],
    "AI_SEARCH": ["SCHEMA_WRITE", "LLMS_TXT_WRITE"],
    "AEO": ["FAQ_WRITE", "CONTENT_WRITE", "SCHEMA_WRITE"],
    "CRO": ["THEME_WRITE", "CTA_WRITE", "LAYOUT_WRITE"],
    "UX_CONVERSION": ["THEME_WRITE", "LAYOUT_WRITE"],
    "TRUST_AUTHORITY": ["CONTENT_WRITE", "SECURITY_HEADER_WRITE"],
}

CATEGORY_OWNER_MAP: Dict[str, str] = {
    "TECHNICAL_SEO": "DevOps / Web Engineering",
    "ON_PAGE_SEO": "Frontend Engineering",
    "GEO": "AI Search Engineer",
    "AI_SEARCH": "AI Search Engineer",
    "AEO": "Content & Knowledge Engineer",
    "CRO": "Growth / UX Engineer",
    "UX_CONVERSION": "Growth / UX Engineer",
    "TRUST_AUTHORITY": "Product / Legal",
}


class CanonicalBacklogEngine:
    """
    Transforms audit findings into a fully-specified 14-field remediation backlog.
    """

    @staticmethod
    def infer_template(url: str) -> str:
        path = urlparse(url).path.lower().strip("/")
        if not path:
            return "HOMEPAGE"
        if any(seg in path for seg in ["product", "item"]):
            return "PRODUCT_DETAIL"
        if any(seg in path for seg in ["category", "collection"]):
            return "CATEGORY_LISTING"
        if any(seg in path for seg in ["blog", "article"]):
            return "BLOG_POST"
        if any(seg in path for seg in ["pricing"]):
            return "PRICING_PAGE"
        return "GENERAL_PAGE"

    def create_task_from_finding(
        self,
        finding: Any,
        task_id: Optional[str] = None,
    ) -> RemediationTaskRecord:
        # Extract fields flexibly whether pydantic Finding, CanonicalFinding, or dict
        f_id = getattr(finding, "finding_id", None) or getattr(finding, "id", "F_UNKNOWN")
        title = getattr(finding, "title", "Unspecified Defect")
        description = getattr(finding, "description", "")
        rec_action = (
            getattr(finding, "recommendation_text", None)
            or getattr(finding, "recommended_action", None)
            or f"Remediate {title}"
        )
        cat_str = str(getattr(finding, "category", "TECHNICAL_SEO")).upper().split(".")[-1]
        sev_str = str(getattr(finding, "severity", "MEDIUM")).upper().split(".")[-1]
        impact_str = (
            getattr(finding, "business_impact", None)
            or f"Negatively affects {cat_str.lower().replace('_', ' ')} efficiency and search discoverability."
        )

        urls = getattr(finding, "affected_urls", []) or []
        templates = list(set(self.infer_template(u) for u in urls)) if urls else ["HOMEPAGE"]

        # Root cause extraction
        root_cause = getattr(finding, "root_cause_key", None)
        if not root_cause:
            root_cause = getattr(finding, "root_cause", None)
        if not root_cause:
            root_cause = f"Defective {cat_str} configuration or missing markup: {title}"
        else:
            root_cause = str(root_cause)

        # Effort calculation based on severity
        if sev_str == "CRITICAL":
            effort = "HIGH"
        elif sev_str == "HIGH":
            effort = "MEDIUM"
        else:
            effort = "LOW"

        # Dependencies
        deps = []
        if cat_str in ["AEO", "GEO"]:
            deps.append("BUSINESS_PROFILE_CONFIRMED")
        if "REDIRECT" in title.upper() or "ROBOTS" in title.upper():
            deps.append("STAGING_ENVIRONMENT_PROVISIONED")

        perms = CATEGORY_PERMISSION_MAP.get(cat_str, ["THEME_WRITE"])
        owner = CATEGORY_OWNER_MAP.get(cat_str, "Engineering")

        # Machine-verifiable criteria
        verification_criteria = (
            f"Confirm via post-fix crawl that {title} is no longer observed and returns valid HTTP status."
        )

        t_id = task_id or f"TASK_{f_id.replace('F_', '')}"

        return RemediationTaskRecord(
            task_id=t_id,
            finding_id=f_id,
            root_cause=root_cause,
            affected_urls=urls,
            affected_templates=templates,
            recommended_action=rec_action,
            business_impact=impact_str,
            technical_severity=sev_str,
            confidence=0.95,
            estimated_effort=effort,
            dependencies=deps,
            required_permissions=perms,
            owner=owner,
            status=TaskStatus.DETECTED,
            verification_criteria=verification_criteria,
        )

    def generate_backlog(self, findings: List[Any]) -> List[RemediationTaskRecord]:
        tasks: List[RemediationTaskRecord] = []
        seen_keys = set()
        for idx, f in enumerate(findings):
            task = self.create_task_from_finding(f, task_id=f"TASK_{idx + 1:03d}")
            # Deduplicate tasks with identical root causes and URLs
            dedup_key = (task.root_cause, tuple(sorted(task.affected_urls)))
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                tasks.append(task)
        return tasks


canonical_backlog_engine = CanonicalBacklogEngine()
