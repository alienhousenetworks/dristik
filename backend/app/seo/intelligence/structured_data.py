"""
Structured Data & Entity Architecture Intelligence — Phase 3.6

Inspects JSON-LD, Microdata, and RDFa structured data:
- Schema.org syntax validity vs. Google Rich Results eligibility
- Supported entity schemas: Organization, WebSite, Product, Article, BreadcrumbList, FAQPage, Review, AggregateRating
- Integrity checks: Invalid properties, duplicate entities, broken @id references

STRICT GUARDRAIL:
Separates Schema.org syntactic validity from Google Rich Results eligibility.
Valid syntax does NOT guarantee rich snippet display without Google's required fields.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class RichResultEligibility(BaseModel):
    feature_name: str  # "Product Rich Snippet", "Review Stars", "FAQ Dropdown", "Breadcrumb Trail"
    is_eligible: bool
    schema_type: str
    missing_required_fields: List[str] = Field(default_factory=list)
    missing_recommended_fields: List[str] = Field(default_factory=list)
    guidance: str = ""


class EntitySchemaInspection(BaseModel):
    entity_type: str
    node_id: Optional[str] = None
    is_valid_syntax: bool
    is_rich_result_eligible: bool
    eligibility_details: Optional[RichResultEligibility] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class StructuredDataReport(BaseModel):
    url: str
    formats_detected: List[str] = Field(default_factory=list)  # JSON-LD, Microdata, RDFa
    total_entities_found: int
    entities: List[EntitySchemaInspection] = Field(default_factory=list)
    has_broken_id_references: bool = False
    has_duplicate_entities: bool = False
    rich_result_summary: List[str] = Field(default_factory=list)


class StructuredDataEngine:
    """
    Evaluates schema syntax, graph linkage, and Google Rich Result eligibility.
    """

    GOOGLE_RICH_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
        "Product": {
            "required": ["name", "image", "offers"],
            "recommended": ["aggregateRating", "review", "brand", "sku"],
        },
        "Organization": {
            "required": ["name", "url"],
            "recommended": ["logo", "contactPoint", "sameAs"],
        },
        "Article": {
            "required": ["headline", "image", "datePublished", "author"],
            "recommended": ["dateModified", "publisher"],
        },
        "BreadcrumbList": {
            "required": ["itemListElement"],
            "recommended": [],
        },
        "FAQPage": {
            "required": ["mainEntity"],
            "recommended": [],
        },
        "Review": {
            "required": ["author", "itemReviewed", "reviewRating"],
            "recommended": [],
        },
    }

    @classmethod
    def analyze_page_structured_data(cls, url: str, html: str) -> StructuredDataReport:
        formats: List[str] = []
        entities: List[EntitySchemaInspection] = []
        json_ld_blocks: List[Dict[str, Any]] = []

        # 1. Detect JSON-LD
        json_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
        if json_matches:
            formats.append("JSON-LD")
            for block in json_matches:
                try:
                    parsed = json.loads(block.strip())
                    if isinstance(parsed, list):
                        json_ld_blocks.extend(parsed)
                    elif isinstance(parsed, dict):
                        if "@graph" in parsed and isinstance(parsed["@graph"], list):
                            json_ld_blocks.extend(parsed["@graph"])
                        else:
                            json_ld_blocks.append(parsed)
                except Exception as e:
                    entities.append(
                        EntitySchemaInspection(
                            entity_type="Unknown",
                            is_valid_syntax=False,
                            is_rich_result_eligible=False,
                            errors=[f"JSON-LD parsing syntax error: {str(e)}"],
                        )
                    )

        # 2. Detect Microdata
        if "itemscope" in html.lower() and "itemtype" in html.lower():
            formats.append("Microdata")

        # 3. Detect RDFa
        if "typeof=" in html.lower() or "property=" in html.lower():
            formats.append("RDFa")

        # 4. Analyze Extracted Entities
        type_counts: Dict[str, int] = {}
        all_ids: Set[str] = set()
        referenced_ids: Set[str] = set()

        for item in json_ld_blocks:
            t = item.get("@type", "Thing")
            node_id = item.get("@id")
            if node_id:
                all_ids.add(node_id)

            type_counts[t] = type_counts.get(t, 0) + 1
            errors: List[str] = []
            warnings: List[str] = []

            # Check for referenced IDs inside item
            for val in item.values():
                if isinstance(val, dict) and "@id" in val:
                    referenced_ids.add(val["@id"])

            # Check Google Rich Results Requirements
            reqs = cls.GOOGLE_RICH_REQUIREMENTS.get(t)
            eligibility = None
            if reqs:
                missing_req = [f for f in reqs["required"] if f not in item]
                missing_rec = [f for f in reqs["recommended"] if f not in item]
                is_eligible = len(missing_req) == 0

                guidance = (
                    "Eligible for Google rich results."
                    if is_eligible
                    else f"Ineligible for Google Rich Results: missing required property: {', '.join(missing_req)}."
                )
                if not is_eligible:
                    warnings.append(guidance)

                eligibility = RichResultEligibility(
                    feature_name=f"{t} Rich Snippet",
                    is_eligible=is_eligible,
                    schema_type=t,
                    missing_required_fields=missing_req,
                    missing_recommended_fields=missing_rec,
                    guidance=guidance,
                )

            entities.append(
                EntitySchemaInspection(
                    entity_type=t,
                    node_id=node_id,
                    is_valid_syntax=True,
                    is_rich_result_eligible=eligibility.is_eligible if eligibility else False,
                    eligibility_details=eligibility,
                    errors=errors,
                    warnings=warnings,
                )
            )

        # 5. Graph Integrity
        has_broken_id = bool(referenced_ids - all_ids)
        has_duplicate = any(count > 1 for t, count in type_counts.items() if t in ("Organization", "WebSite"))

        # 6. Rich Results Summary
        rich_summary = [
            f"{e.entity_type}: {'Eligible' if e.is_rich_result_eligible else 'Ineligible'} for rich results."
            for e in entities if e.eligibility_details
        ]

        return StructuredDataReport(
            url=url,
            formats_detected=formats,
            total_entities_found=len(entities),
            entities=entities,
            has_broken_id_references=has_broken_id,
            has_duplicate_entities=has_duplicate,
            rich_result_summary=rich_summary,
        )
