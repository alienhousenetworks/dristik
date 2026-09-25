"""
Deterministic Structured Data & Schema.org Parser
Extracts JSON-LD, Microdata, and validates schema implementation against business entity types.
"""
import json
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

def parse_schema_markup(html_content: str) -> Dict[str, Any]:
    """
    Extracts all JSON-LD blocks and microdata items from HTML content.
    Returns detected schema types, raw structures, and validation flags.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    schema_types = set()
    raw_schemas = []

    # 1. Parse JSON-LD scripts
    json_ld_tags = soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)})
    for tag in json_ld_tags:
        content = tag.string or tag.get_text()
        if not content:
            continue
        try:
            # Clean possible JS comments or trailing commas
            cleaned = content.strip()
            data = json.loads(cleaned)
            
            def extract_types(item):
                if isinstance(item, dict):
                    t = item.get("@type")
                    if t:
                        if isinstance(t, list):
                            for sub_t in t:
                                schema_types.add(str(sub_t))
                        else:
                            schema_types.add(str(t))
                    # Check graph array
                    if "@graph" in item and isinstance(item["@graph"], list):
                        for sub_item in item["@graph"]:
                            extract_types(sub_item)
                    for k, v in item.items():
                        if isinstance(v, (dict, list)):
                            extract_types(v)
                elif isinstance(item, list):
                    for sub in item:
                        extract_types(sub)

            extract_types(data)
            raw_schemas.append(data)
        except Exception:
            # Malformed JSON-LD
            continue

    # 2. Parse Microdata itemtype
    microdata_tags = soup.find_all(attrs={"itemtype": True})
    for tag in microdata_tags:
        itemtype = tag.get("itemtype", "")
        if itemtype:
            # Extract last path segment e.g. https://schema.org/LocalBusiness -> LocalBusiness
            type_name = itemtype.split("/")[-1].split("#")[-1]
            if type_name:
                schema_types.add(type_name)

    types_list = sorted(list(schema_types))

    # Standard check flags
    has_organization = any("Organization" in t or "Corporation" in t for t in types_list)
    has_local_business = any("LocalBusiness" in t or "Store" in t or "Restaurant" in t or "MedicalBusiness" in t for t in types_list)
    has_product = any("Product" in t or "SoftwareApplication" in t for t in types_list)
    has_faq = any("FAQPage" in t for t in types_list)
    has_breadcrumbs = any("BreadcrumbList" in t for t in types_list)
    has_article = any("Article" in t or "BlogPosting" in t or "NewsArticle" in t for t in types_list)
    has_web_site = any("WebSite" in t for t in types_list)
    has_person = any("Person" in t for t in types_list)

    return {
        "schema_types": types_list,
        "raw_schemas": raw_schemas,
        "has_organization": has_organization,
        "has_local_business": has_local_business,
        "has_product": has_product,
        "has_faq": has_faq,
        "has_breadcrumbs": has_breadcrumbs,
        "has_article": has_article,
        "has_web_site": has_web_site,
        "has_person": has_person,
        "total_schemas_found": len(types_list)
    }
