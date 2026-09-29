"""Attach an external-authority report to a finished crawl audit.

Reading the report never calls a provider. A failure here returns a
coverage placeholder and does not change the crawl findings.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.domain.models import Finding

logger = logging.getLogger("app.external_authority")


def build_audit_attachment(
    *,
    project_id: str,
    domain: str,
    period_days: int = 28,
    pages: Optional[List[Any]] = None,
    evidence_store: Any = None,
) -> Dict[str, Any]:
    try:
        from app.external_authority.evidence_bridge import record_evidence, to_domain_findings
        from app.external_authority.service import get_service

        report = get_service().report(
            project_id,
            domain,
            period_days,
            crawl_observations=observations_from_pages(pages),
        )
        record_evidence(evidence_store, report.get("findings") or [])
        return {
            "report": report,
            "domain_findings": to_domain_findings(report.get("findings") or []),
        }
    except Exception as exc:
        logger.info("external authority report unavailable: %s", type(exc).__name__)
        return {"report": _unavailable(type(exc).__name__), "domain_findings": []}


def observations_from_pages(pages: Optional[List[Any]]) -> Dict[str, Any]:
    schema_types: List[str] = []
    same_as: List[str] = []
    publisher_name = None
    for page in pages or []:
        for item in getattr(page, "schema_types", None) or []:
            text = str(item)
            if text and text not in schema_types:
                schema_types.append(text)
        blobs = list(getattr(page, "structured_data", None) or [])
        blobs.extend(getattr(page, "raw_schema", None) or [])
        for blob in blobs:
            _walk_schema(blob, schema_types, same_as)
            if publisher_name is None and isinstance(blob, dict):
                publisher = blob.get("publisher") or blob.get("name")
                if isinstance(publisher, dict):
                    publisher_name = publisher.get("name")
                elif isinstance(publisher, str) and blob.get("@type") in {"Organization", "LocalBusiness"}:
                    publisher_name = publisher
    return {
        "schema_types": schema_types,
        "same_as": same_as,
        "publisher_name": publisher_name,
    }


def _walk_schema(node: Any, schema_types: List[str], same_as: List[str], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(node, list):
        for item in node:
            _walk_schema(item, schema_types, same_as, depth + 1)
        return
    if not isinstance(node, dict):
        return
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    for item in kinds:
        if item and str(item) not in schema_types:
            schema_types.append(str(item))
    links = node.get("sameAs") or []
    if isinstance(links, str):
        links = [links]
    for link in links:
        if isinstance(link, str) and link not in same_as:
            same_as.append(link)
    for value in node.values():
        if isinstance(value, (dict, list)):
            _walk_schema(value, schema_types, same_as, depth + 1)


def _unavailable(error_type: str) -> Dict[str, Any]:
    return {
        "title": "External Authority & Entity Intelligence",
        "universal_authority_score": None,
        "score_note": "Dristik does not calculate a universal authority score.",
        "coverage": [],
        "findings": [],
        "pillars": {},
        "sections": {},
        "data_sources": [{"source": "Website Crawl", "state": "INCLUDED", "detail": "Crawl evidence is independent of external providers."}],
        "notes": [
            "External authority was not attached. The crawl audit is unchanged.",
            error_type,
        ],
        "error": error_type,
    }


def measured_findings(findings: List[Finding]) -> List[Finding]:
    return [item for item in findings if not item.held_from_executive]
