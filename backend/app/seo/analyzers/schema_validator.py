"""
Dristik AI Schema.org & Google Rich Results Validator
Validates JSON-LD entities against official Google Search Rich Result specifications.
Detects missing required fields (syntax errors that block rich snippets) and missing recommended fields.
Supported core types:
- Organization / LocalBusiness / Corporation
- Product / SoftwareApplication
- Article / NewsArticle / BlogPosting
- FAQPage
- BreadcrumbList
"""
import json
from typing import List, Dict, Any, Set
from app.domain.models import PageEvidence, SchemaIssue, SchemaValidationReport
from app.seo.audit.schema_validator import (
    DEPRECATED_SCHEMA_TYPES,
    BRACKET_PLACEHOLDERS,
    BARE_PLACEHOLDER_RE,
)


def _clean_type(stype: Any) -> str:
    if isinstance(stype, str):
        return stype.strip()
    if isinstance(stype, list) and stype:
        return str(stype[0]).strip()
    return ""


def validate_schema_entity(entity: Dict[str, Any], url: str) -> List[SchemaIssue]:
    issues: List[SchemaIssue] = []
    stype = _clean_type(entity.get("@type"))
    if not stype:
        issues.append(SchemaIssue(
            url=url,
            schema_type="Unknown",
            severity="ERROR",
            field="@type",
            message="JSON-LD object is missing the mandatory '@type' property."
        ))
        return issues

    # 0a. Check deprecated schema types
    clean_stype = stype.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
    if clean_stype in DEPRECATED_SCHEMA_TYPES:
        issues.append(SchemaIssue(
            url=url,
            schema_type=stype,
            severity="ERROR",
            field="@type",
            message=f"Schema type '{stype}' is {DEPRECATED_SCHEMA_TYPES[clean_stype]}."
        ))

    # 0b. Check for template placeholder text
    entity_str = json.dumps(entity, ensure_ascii=False)
    for p in BRACKET_PLACEHOLDERS:
        if p.lower() in entity_str.lower():
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="content",
                message=f"Schema contains unreplaced template placeholder '{p}'."
            ))
            break
    for ph in BARE_PLACEHOLDER_RE.findall(entity_str):
        issues.append(SchemaIssue(
            url=url,
            schema_type=stype,
            severity="ERROR",
            field="content",
            message=f"Schema contains unreplaced template placeholder '{ph}'."
        ))
        break

    LOCAL_BUSINESS_TYPES = {
        "LocalBusiness", "Store", "Restaurant", "MedicalBusiness", "Dentist",
        "LegalService", "FinancialService", "AutomotiveBusiness", "RealEstateAgent",
        "Hotel", "LodgingBusiness", "HealthAndBeautyBusiness", "HomeAndConstructionBusiness",
        "ProfessionalService", "ChildCare", "DryCleaningOrLaundry", "EmergencyService",
        "EmploymentAgency", "EntertainmentBusiness", "FoodEstablishment", "GovernmentOffice",
        "Library", "RadioStation", "RecyclingCenter", "SelfStorage", "ShoppingCenter",
        "SportsActivityLocation", "TelevisionStation", "TouristInformationCenter", "TravelAgency"
    }

    # 1. LocalBusiness and specific subtypes
    if stype in LOCAL_BUSINESS_TYPES:
        if not entity.get("name"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="name",
                message=f"Missing required 'name' property for Google {stype} entity."
            ))
        
        # Address validation
        address = entity.get("address")
        if not address:
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="address",
                message=f"Missing required 'address' (PostalAddress) for Google {stype} entity."
            ))
        elif isinstance(address, dict):
            req_address_fields = ["addressLocality", "addressCountry"]
            for af in req_address_fields:
                if not address.get(af):
                    issues.append(SchemaIssue(
                        url=url,
                        schema_type=stype,
                        severity="WARNING",
                        field=f"address.{af}",
                        message=f"Missing '{af}' in PostalAddress for {stype}."
                    ))
            if not (address.get("streetAddress") or address.get("postalCode")):
                issues.append(SchemaIssue(
                    url=url,
                    schema_type=stype,
                    severity="WARNING",
                    field="address.streetAddress",
                    message=f"PostalAddress for {stype} should include streetAddress or postalCode."
                ))
        
        # Telephone
        if not entity.get("telephone"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="telephone",
                message=f"Missing recommended 'telephone' for Google {stype} local entity."
            ))

        # Geo Coordinates
        geo = entity.get("geo")
        if not geo:
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="geo",
                message=f"Missing recommended 'geo' (GeoCoordinates: latitude, longitude) for {stype} map entity."
            ))
        elif isinstance(geo, dict):
            if "latitude" not in geo or "longitude" not in geo:
                issues.append(SchemaIssue(
                    url=url,
                    schema_type=stype,
                    severity="ERROR",
                    field="geo.coordinates",
                    message=f"GeoCoordinates for {stype} must specify both 'latitude' and 'longitude'."
                ))

        # Opening Hours
        if not (entity.get("openingHours") or entity.get("openingHoursSpecification")):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="openingHours",
                message=f"Missing recommended 'openingHours' or 'openingHoursSpecification' for {stype}."
            ))

        # URL
        if not entity.get("url"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="url",
                message=f"Missing recommended 'url' property for Google {stype} entity."
            ))

        # Logo or image
        if not (entity.get("image") or entity.get("logo")):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="image",
                message=f"Missing recommended 'image' or 'logo' for {stype} visual card."
            ))

    # 1b. Organization / Corporation
    elif stype in ("Organization", "Corporation"):
        if not entity.get("name"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="name",
                message=f"Missing required 'name' property for Google {stype} entity."
            ))
        if not entity.get("url"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="url",
                message=f"Missing required 'url' property for Google {stype} entity."
            ))
        if not entity.get("logo"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="logo",
                message="Missing recommended 'logo' property for brand knowledge graph card."
            ))
        if not entity.get("sameAs"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="sameAs",
                message="Missing recommended 'sameAs' social profiles (LinkedIn, X, Wikipedia)."
            ))

    # 2. Product / SoftwareApplication
    elif stype in ("Product", "SoftwareApplication"):
        if not entity.get("name"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="name",
                message=f"Missing required 'name' property on {stype}."
            ))
        has_offers = bool(entity.get("offers"))
        has_rating = bool(entity.get("aggregateRating") or entity.get("review"))
        if not has_offers and not has_rating:
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="offers / aggregateRating",
                message="Google Rich Results require either 'offers' (pricing/availability) or 'aggregateRating'/'review'."
            ))
        if not entity.get("image"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="image",
                message="Missing recommended 'image' property on Product schema."
            ))
        if not entity.get("description"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="description",
                message="Missing recommended 'description' property on Product schema."
            ))

    # 3. Article / BlogPosting / NewsArticle
    elif stype in ("Article", "BlogPosting", "NewsArticle"):
        if not entity.get("headline"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="headline",
                message="Missing required 'headline' property for Article rich snippet."
            ))
        if not entity.get("image"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="image",
                message="Missing required 'image' property for Google Article rich result."
            ))
        if not entity.get("datePublished"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="ERROR",
                field="datePublished",
                message="Missing required 'datePublished' property for Article rich snippet."
            ))
        if not entity.get("author"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="author",
                message="Missing recommended 'author' property (Person or Organization)."
            ))
        if not entity.get("publisher"):
            issues.append(SchemaIssue(
                url=url,
                schema_type=stype,
                severity="WARNING",
                field="publisher",
                message="Missing recommended 'publisher' entity with logo."
            ))

    # 4. FAQPage
    elif stype == "FAQPage":
        main_entity = entity.get("mainEntity")
        if not main_entity or not isinstance(main_entity, list):
            issues.append(SchemaIssue(
                url=url,
                schema_type="FAQPage",
                severity="ERROR",
                field="mainEntity",
                message="FAQPage must declare a 'mainEntity' list containing Question items."
            ))
        else:
            for idx, q in enumerate(main_entity):
                if isinstance(q, dict):
                    if not q.get("name"):
                        issues.append(SchemaIssue(
                            url=url,
                            schema_type="FAQPage",
                            severity="ERROR",
                            field=f"mainEntity[{idx}].name",
                            message=f"Question #{idx+1} is missing the question text in 'name'."
                        ))
                    ans = q.get("acceptedAnswer")
                    if not ans or not isinstance(ans, dict) or not ans.get("text"):
                        issues.append(SchemaIssue(
                            url=url,
                            schema_type="FAQPage",
                            severity="ERROR",
                            field=f"mainEntity[{idx}].acceptedAnswer.text",
                            message=f"Question #{idx+1} is missing 'acceptedAnswer' with answer 'text'."
                        ))

    # 5. BreadcrumbList
    elif stype == "BreadcrumbList":
        elements = entity.get("itemListElement")
        if not elements or not isinstance(elements, list):
            issues.append(SchemaIssue(
                url=url,
                schema_type="BreadcrumbList",
                severity="ERROR",
                field="itemListElement",
                message="BreadcrumbList requires an 'itemListElement' list of ListItem entities."
            ))
        else:
            for idx, item in enumerate(elements):
                if isinstance(item, dict):
                    if item.get("position") is None:
                        issues.append(SchemaIssue(
                            url=url,
                            schema_type="BreadcrumbList",
                            severity="ERROR",
                            field=f"itemListElement[{idx}].position",
                            message=f"Breadcrumb #{idx+1} is missing mandatory 'position' integer."
                        ))
                    if not item.get("name"):
                        issues.append(SchemaIssue(
                            url=url,
                            schema_type="BreadcrumbList",
                            severity="ERROR",
                            field=f"itemListElement[{idx}].name",
                            message=f"Breadcrumb #{idx+1} is missing mandatory 'name'."
                        ))

    return issues


def analyze_schema_rich_results(pages: List[PageEvidence]) -> SchemaValidationReport:
    """
    Performs full Google Rich Results validation across all crawled pages.
    """
    total_pages_with_schema = 0
    all_issues: List[SchemaIssue] = []
    detected_types: Set[str] = set()
    total_entities = 0
    entities_with_errors = 0
    entities_with_warnings = 0

    for page in pages:
        schemas = page.raw_schema or []
        if not schemas and page.schema_types:
            total_pages_with_schema += 1
            for t in page.schema_types:
                detected_types.add(t)
            continue

        if schemas:
            total_pages_with_schema += 1

        for root_item in schemas:
            if not isinstance(root_item, dict):
                continue

            # Flatten @graph items if present
            candidates = [root_item]
            if "@graph" in root_item and isinstance(root_item["@graph"], list):
                candidates.extend([g for g in root_item["@graph"] if isinstance(g, dict)])

            for entity in candidates:
                stype = _clean_type(entity.get("@type"))
                if stype:
                    detected_types.add(stype)
                total_entities += 1

                entity_issues = validate_schema_entity(entity, page.url)
                if entity_issues:
                    all_issues.extend(entity_issues)
                    has_err = any(iss.severity == "ERROR" for iss in entity_issues)
                    has_warn = any(iss.severity == "WARNING" for iss in entity_issues)
                    if has_err:
                        entities_with_errors += 1
                    if has_warn:
                        entities_with_warnings += 1

    valid_entities = max(0, total_entities - entities_with_errors)

    if total_entities == 0:
        summary = "No JSON-LD structured data entities were detected across crawled pages."
    elif entities_with_errors == 0:
        summary = (
            f"No blocking rich-result errors on {total_entities} entities. "
            f"{entities_with_warnings} recommended fields are absent. "
            "Rich-result syntax is not an entity-graph quality score."
        )
    else:
        summary = (
            f"Audited {total_entities} schema entities across {total_pages_with_schema} pages. "
            f"Found {entities_with_errors} entity syntax error(s) and {entities_with_warnings} warning(s). "
            "Rich-result syntax is not an entity-graph quality score."
        )

    return SchemaValidationReport(
        total_pages_with_schema=total_pages_with_schema,
        total_entities_detected=total_entities,
        valid_entities_count=valid_entities,
        entities_with_errors_count=entities_with_errors,
        entities_with_warnings_count=entities_with_warnings,
        detected_types=sorted(detected_types),
        issues=all_issues,
        summary=summary,
    )
