"""
Schema ↔ Visible Content Consistency Engine.
Layer 1 Extractability: What Dristik can prove deterministically from the website itself.

Compares Schema.org JSON-LD structured data against visible DOM text:
- Does Organization.name match the DOM H1 / visible brand?
- Do Service / Product names exist as visible headings on pages?
- Are sameAs social profile URLs actually linked in the header/footer?
- Does FAQPage structured data match visible on-page FAQ copy?
- Does pricing in Schema (offers.price) match visible pricing text?

Stated-property grounding is verified values divided by values the schema actually states.
It is not an entity-graph quality score. Absent properties are scored by entity_graph.py.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence

PropertyStatus = Literal["VERIFIED", "UNMATCHED", "CONTRADICTED", "PARTIAL"]


class SchemaPropertyCheck(BaseModel):
    schema_type: str
    property_name: str
    schema_value: str
    status: PropertyStatus
    dom_evidence_url: Optional[str] = None
    dom_snippet: Optional[str] = None
    explanation: str
    remediation: Optional[str] = None


class SchemaCrosscheckResult(BaseModel):
    grounding_score: Optional[float] = None  # stated properties only; null when nothing was stated
    total_properties_checked: int
    verified_count: int
    partial_count: int
    unmatched_count: int
    contradicted_count: int
    entity_completeness_pct: float  # 0 to 100
    detected_schemas: List[str] = Field(default_factory=list)
    missing_recommended_schemas: List[str] = Field(default_factory=list)
    checks: List[SchemaPropertyCheck] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""


class SchemaContentCrosschecker:
    """
    Validates semantic consistency between machine-readable Schema.org and human-visible HTML.
    """

    def __init__(self):
        self.recommended_schemas = {"Organization", "WebSite", "SoftwareApplication", "Product", "Service", "FAQPage"}

    def _flatten_schemas(self, pages: List[PageEvidence]) -> List[Tuple[str, Dict[str, Any]]]:
        """Extracts (page_url, schema_dict) pairs from all pages."""
        flattened = []
        for p in pages:
            url = p.url or ""
            raw = p.raw_schema or []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                # Handle @graph
                if "@graph" in item and isinstance(item["@graph"], list):
                    for sub in item["@graph"]:
                        if isinstance(sub, dict):
                            flattened.append((url, sub))
                else:
                    flattened.append((url, item))
        return flattened

    def crosscheck(
        self,
        pages: List[PageEvidence],
        brand_name: str = ""
    ) -> SchemaCrosscheckResult:
        if not pages:
            return SchemaCrosscheckResult(
                grounding_score=None,
                total_properties_checked=0,
                verified_count=0,
                partial_count=0,
                unmatched_count=0,
                contradicted_count=0,
                entity_completeness_pct=0.0,
                summary="No crawl pages provided for Schema cross-checking.",
            )

        flattened = self._flatten_schemas(pages)
        detected_types: Set[str] = set()

        for p in pages:
            detected_types.update(p.schema_types or [])
        for _, s in flattened:
            stype = s.get("@type")
            if isinstance(stype, str):
                detected_types.add(stype)
            elif isinstance(stype, list):
                detected_types.update(stype)

        # Build corpus of all headings, body text, and links
        all_headings = [h.lower() for p in pages for h in ((p.h1 or []) + (p.h2 or []) + (p.h3 or []))]
        all_links = {l.lower().strip() for p in pages for l in ((p.external_links or []) + (p.internal_links or []))}
        all_body = " ".join([(p.body_text or "").lower() for p in pages])

        checks: List[SchemaPropertyCheck] = []
        discrepancies: List[str] = []
        recommendations: List[str] = []

        if not flattened:
            # Zero schema detected
            missing = sorted(list(self.recommended_schemas))
            return SchemaCrosscheckResult(
                grounding_score=None,
                total_properties_checked=0,
                verified_count=0,
                partial_count=0,
                unmatched_count=0,
                contradicted_count=0,
                entity_completeness_pct=0.0,
                detected_schemas=[],
                missing_recommended_schemas=missing,
                checks=[],
                discrepancies=["No Schema.org JSON-LD detected across crawled pages."],
                recommendations=["Deploy structured JSON-LD (Organization, WebSite, Service/Product) on the homepage."],
                summary="No Schema.org JSON-LD in the crawled sample. Stated-property grounding was not measured.",
            )

        for url, sch in flattened:
            stype = str(sch.get("@type", "Thing"))

            # 1. Check Name
            if "name" in sch:
                val = str(sch["name"]).strip()
                val_low = val.lower()
                # Check if name is in any heading or body
                in_headings = any(val_low in h for h in all_headings)
                in_body = val_low in all_body

                if in_headings or in_body:
                    checks.append(SchemaPropertyCheck(
                        schema_type=stype,
                        property_name="name",
                        schema_value=val,
                        status="VERIFIED",
                        dom_evidence_url=url,
                        dom_snippet=f"'{val}' matches visible on-page content.",
                        explanation=f"Schema {stype}.name ('{val}') is verified in visible DOM text."
                    ))
                else:
                    discrepancies.append(f"{stype}.name ('{val}') is absent from visible on-page text.")
                    checks.append(SchemaPropertyCheck(
                        schema_type=stype,
                        property_name="name",
                        schema_value=val,
                        status="UNMATCHED",
                        dom_evidence_url=url,
                        explanation=f"Schema {stype}.name ('{val}') does not appear in visible HTML copy.",
                        remediation=f"Ensure brand name '{val}' is prominently displayed in the H1 or hero section."
                    ))

            if isinstance(sch.get("description"), str) and str(sch.get("description")).strip():
                desc = str(sch["description"]).strip()
                desc_low = desc.lower()
                needle = desc_low if len(desc_low) <= 80 else desc_low[:80]
                if needle in all_body:
                    checks.append(SchemaPropertyCheck(
                        schema_type=stype,
                        property_name="description",
                        schema_value=desc[:180],
                        status="VERIFIED",
                        dom_evidence_url=url,
                        dom_snippet=desc[:120],
                        explanation=f"Schema {stype}.description is visible in the page copy."
                    ))
                else:
                    discrepancies.append(f"{stype}.description is not visible in the page copy.")
                    checks.append(SchemaPropertyCheck(
                        schema_type=stype,
                        property_name="description",
                        schema_value=desc[:180],
                        status="UNMATCHED",
                        dom_evidence_url=url,
                        explanation=f"Schema {stype}.description does not appear in visible HTML copy.",
                        remediation="Use the same description in the visible page and in JSON-LD."
                    ))

            # 2. Check sameAs (Social / External profiles)
            if "sameAs" in sch:
                sameas_val = sch["sameAs"]
                targets = sameas_val if isinstance(sameas_val, list) else [sameas_val]
                for target_url in targets:
                    t_str = str(target_url).strip()
                    t_low = t_str.lower()
                    matched = any(t_low in l or l in t_low for l in all_links) or (t_low in all_body)

                    if matched:
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="sameAs",
                            schema_value=t_str,
                            status="VERIFIED",
                            dom_evidence_url=url,
                            dom_snippet=t_str,
                            explanation=f"sameAs URL '{t_str}' is verified in visible page outbound links."
                        ))
                    else:
                        discrepancies.append(f"sameAs profile '{t_str}' is in Schema but not linked anywhere on visible pages.")
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="sameAs",
                            schema_value=t_str,
                            status="UNMATCHED",
                            dom_evidence_url=url,
                            explanation=f"sameAs link '{t_str}' is not present in visible header, footer, or body links.",
                            remediation=f"Add a visible social icon or outbound link to '{t_str}' in the site footer."
                        ))

            # 3. Check Service / Product Names against headings
            if stype in ["Service", "Product", "SoftwareApplication"]:
                s_name = str(sch.get("name", "")).strip()
                if s_name:
                    s_low = s_name.lower()
                    heading_match = any(s_low in h for h in all_headings)
                    if heading_match:
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="offering_heading",
                            schema_value=s_name,
                            status="VERIFIED",
                            dom_evidence_url=url,
                            dom_snippet=f"'{s_name}' confirmed as a visible heading.",
                            explanation=f"Schema {stype} '{s_name}' exists as an H1/H2 heading in the visible DOM."
                        ))
                    else:
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="offering_heading",
                            schema_value=s_name,
                            status="PARTIAL",
                            dom_evidence_url=url,
                            explanation=f"Schema {stype} '{s_name}' is declared in JSON-LD but missing from visible H2/H3 headings.",
                            remediation=f"Add an explicit H2/H3 heading on service pages for '{s_name}'."
                        ))

            # 4. Check FAQPage questions
            if stype == "FAQPage" and "mainEntity" in sch:
                faq_items = sch["mainEntity"] if isinstance(sch["mainEntity"], list) else [sch["mainEntity"]]
                for item in faq_items:
                    if isinstance(item, dict) and "name" in item:
                        q_name = str(item["name"]).strip()
                        q_low = q_name.lower()
                        # Check if question appears in body or headings
                        q_matched = any(q_low in h for h in all_headings) or (q_low[:40] in all_body)
                        if q_matched:
                            checks.append(SchemaPropertyCheck(
                                schema_type="FAQPage",
                                property_name="faq_question",
                                schema_value=q_name[:80],
                                status="VERIFIED",
                                dom_evidence_url=url,
                                dom_snippet=q_name[:80],
                                explanation="FAQ question in JSON-LD is verified in visible DOM text."
                            ))
                        else:
                            discrepancies.append(f"FAQPage question '{q_name[:60]}...' exists in Schema but is missing from visible DOM.")
                            checks.append(SchemaPropertyCheck(
                                schema_type="FAQPage",
                                property_name="faq_question",
                                schema_value=q_name[:80],
                                status="UNMATCHED",
                                dom_evidence_url=url,
                                explanation="Hidden FAQ markup detected: Question is in JSON-LD but not rendered for human readers.",
                                remediation="Render the FAQ accordion visibly in the page body to prevent search engine penalty."
                            ))

            # 5. Check Pricing in Offers
            if "offers" in sch and isinstance(sch["offers"], dict):
                price_val = str(sch["offers"].get("price", "")).strip()
                if price_val:
                    in_body_price = price_val in all_body
                    if in_body_price:
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="offers.price",
                            schema_value=price_val,
                            status="VERIFIED",
                            dom_evidence_url=url,
                            dom_snippet=f"Price {price_val} confirmed on page.",
                            explanation=f"Schema price '{price_val}' matches visible pricing copy."
                        ))
                    else:
                        discrepancies.append(f"Schema price '{price_val}' does not match visible pricing on page.")
                        checks.append(SchemaPropertyCheck(
                            schema_type=stype,
                            property_name="offers.price",
                            schema_value=price_val,
                            status="PARTIAL",
                            dom_evidence_url=url,
                            explanation=f"Schema states price is '{price_val}', but this figure was not found in visible text.",
                            remediation="Align Schema offers.price with current pricing tables on the pricing page."
                        ))

        # Check completeness of recommended schemas
        missing_recommended = [r for r in self.recommended_schemas if r not in detected_types]
        entity_completeness = round(((len(self.recommended_schemas) - len(missing_recommended)) / len(self.recommended_schemas)) * 100.0, 1)

        total_checked = len(checks)
        verified = sum(1 for c in checks if c.status == "VERIFIED")
        partial = sum(1 for c in checks if c.status == "PARTIAL")
        unmatched = sum(1 for c in checks if c.status == "UNMATCHED")
        contradicted = sum(1 for c in checks if c.status == "CONTRADICTED")

        # Grounding covers stated values only. A thin schema that matches the page is not quality.
        if total_checked > 0:
            grounding_score: Optional[float] = round(((verified * 1.0 + partial * 0.5) / total_checked) * 100.0, 1)
            summary = (
                f"Stated-property grounding is {grounding_score:.0f}/100 "
                f"({verified} of {total_checked} stated properties). "
                "This is not an entity-graph quality score."
            )
        else:
            grounding_score = None
            summary = "No stated schema properties were available to ground against the page."

        if discrepancies:
            recommendations.append(f"Resolve {len(discrepancies)} Schema to HTML discrepancies so stated values match the page.")
        if "Organization" not in detected_types:
            recommendations.append("State Organization name, url, logo, description, and sameAs in JSON-LD.")
        if "FAQPage" not in detected_types:
            recommendations.append(
                "Add FAQPage only when the page shows the questions. "
                "The value is extractability for answer engines."
            )

        return SchemaCrosscheckResult(
            grounding_score=grounding_score,
            total_properties_checked=total_checked,
            verified_count=verified,
            partial_count=partial,
            unmatched_count=unmatched,
            contradicted_count=contradicted,
            entity_completeness_pct=entity_completeness,
            detected_schemas=sorted(list(detected_types)),
            missing_recommended_schemas=missing_recommended,
            checks=checks,
            discrepancies=discrepancies[:8],
            recommendations=recommendations[:5],
            summary=summary,
        )


schema_crosschecker = SchemaContentCrosschecker()
