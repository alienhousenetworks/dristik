"""
Dristik AI Schema & Structured Data Analyzer
Extracts and validates JSON-LD and Microdata entities (Organization, Product, FAQ, Article).
"""
import json
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore

def analyze_schema_markup(soup: BeautifulSoup, url: str, evidence_store: EvidenceStore) -> Dict[str, Any]:
    raw_schema: List[Dict[str, Any]] = []
    schema_types: List[str] = []
    
    # 1. JSON-LD scripts
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        try:
            content = script.string
            if content:
                data = json.loads(content)
                if isinstance(data, list):
                    raw_schema.extend(data)
                elif isinstance(data, dict):
                    raw_schema.append(data)
        except Exception:
            continue
            
    # Extract @type hierarchy
    for item in raw_schema:
        stype = item.get("@type")
        if isinstance(stype, str):
            schema_types.append(stype)
        elif isinstance(stype, list):
            schema_types.extend([str(t) for t in stype])
            
        if "@graph" in item and isinstance(item["@graph"], list):
            for sub in item["@graph"]:
                gstype = sub.get("@type")
                if isinstance(gstype, str):
                    schema_types.append(gstype)
                elif isinstance(gstype, list):
                    schema_types.extend([str(t) for t in gstype])
                    
    schema_types = list(set(schema_types))
    
    # Register deterministic evidence
    if schema_types:
        evidence_store.add_evidence(
            source_type="schema",
            analyzer="schema_analyzer",
            url=url,
            selector="script[type='application/ld+json']",
            text=f"Detected Schema.org Entity Types: {', '.join(schema_types)}",
            value={
                "schema_types": schema_types,
                "raw_schema_count": len(raw_schema),
                "has_organization": "Organization" in schema_types or "Corporation" in schema_types,
                "has_product_or_service": any(t in schema_types for t in ["Product", "SoftwareApplication", "Service"]),
                "has_faq": "FAQPage" in schema_types
            }
        )
    else:
        evidence_store.add_evidence(
            source_type="schema",
            analyzer="schema_analyzer",
            url=url,
            selector="script[type='application/ld+json']",
            text="No JSON-LD structured data detected on page",
            value={"error": "missing_json_ld", "schema_types": []}
        )
        
    return {
        "schema_types": schema_types,
        "raw_schema": raw_schema,
        "has_schema": len(schema_types) > 0
    }
