"""
Dristik AI Wave-0 Deterministic Site Facts Builder
Extracts empirical, verified baseline facts from CrawlManifest and EvidenceStore ($0 inference).
Prevents LLMs from redundantly rediscovering facts Wave-0 already computed.
"""
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from app.domain.models import CrawlManifest, PageEvidence
from app.domain.evidence.store import EvidenceStore


def _extract_schemas_and_sameas(page: PageEvidence) -> tuple[List[str], List[str], List[str]]:
    """Extracts schema @types, sameAs URLs, and FAQ questions from raw_schema and schema_types."""
    detected_schemas = set(page.schema_types or [])
    sameas_urls = set()
    faq_questions = set()

    for item in (page.raw_schema or []):
        if not isinstance(item, dict):
            continue

        # Handle @graph or direct object
        entities = item.get("@graph", [item]) if isinstance(item.get("@graph"), list) else [item]
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            etype = ent.get("@type")
            if isinstance(etype, str):
                detected_schemas.add(etype)
            elif isinstance(etype, list):
                detected_schemas.update([t for t in etype if isinstance(t, str)])

            # sameAs
            sameas = ent.get("sameAs")
            if isinstance(sameas, str):
                sameas_urls.add(sameas)
            elif isinstance(sameas, list):
                for s in sameas:
                    if isinstance(s, str):
                        sameas_urls.add(s)

            # FAQ questions
            if etype == "FAQPage" or "mainEntity" in ent:
                main_entity = ent.get("mainEntity", [])
                if isinstance(main_entity, list):
                    for q in main_entity:
                        if isinstance(q, dict) and "name" in q:
                            faq_questions.add(str(q["name"]))
                        elif isinstance(q, dict) and "text" in q:
                            faq_questions.add(str(q["text"]))

    return list(detected_schemas), list(sameas_urls), list(faq_questions)


def extract_site_facts(
    manifest: CrawlManifest,
    evidence_store: Optional[EvidenceStore] = None
) -> Dict[str, Any]:
    """
    Constructs the canonical Wave-0 site_facts dictionary passed to all downstream agents.
    """
    pages = manifest.pages or []
    homepage: Optional[PageEvidence] = None

    # Find homepage
    for p in pages:
        if p.page_type == "homepage" or urlparse(p.url).path in ["", "/"]:
            homepage = p
            break
    if not homepage and pages:
        homepage = pages[0]

    final_url = homepage.url if homepage else manifest.base_url
    title = (homepage.title or "") if homepage else ""
    meta_desc = (homepage.meta_description or "") if homepage else ""
    h1 = (homepage.h1 or []) if homepage else []
    h2 = (homepage.h2 or [])[:10] if homepage else []

    # Business name candidates
    candidates = set()
    if title:
        for delim in ["|", "-", "—", "•", ":"]:
            if delim in title:
                parts = title.split(delim)
                for part in parts:
                    clean = part.strip()
                    if 2 <= len(clean) <= 40 and not clean.lower().startswith(("http", "home", "welcome")):
                        candidates.add(clean)

    domain = manifest.domain or (urlparse(final_url).netloc.replace("www.", ""))
    if domain:
        domain_name = domain.split(".")[0].capitalize()
        if len(domain_name) >= 2:
            candidates.add(domain_name)

    # Aggregate schemas, sameAs, FAQs, and CTAs across pages
    all_schemas = set()
    all_sameas = set()
    all_faqs = set()
    all_ctas = set()
    visible_pricing_text = set()
    pricing_signals_present = False
    nav_labels = set()

    for p in pages:
        s_list, sa_list, faq_list = _extract_schemas_and_sameas(p)
        all_schemas.update(s_list)
        all_sameas.update(sa_list)
        all_faqs.update(faq_list)

        for cta in (p.ctas or []):
            if cta and len(cta.strip()) < 50:
                all_ctas.add(cta.strip())

        if p.page_type == "pricing":
            pricing_signals_present = True

        # Check body text for pricing signals
        if p.body_text:
            price_matches = re.findall(r'(?:[\$€£¥]\s*\d+(?:[.,]\d+)?(?:\s*/\s*(?:mo|month|yr|year|user))?)', p.body_text)
            for pm in price_matches[:5]:
                visible_pricing_text.add(pm.strip())
            if price_matches:
                pricing_signals_present = True

        # Nav labels
        for link in (p.internal_links or []):
            path = urlparse(link).path.strip("/").split("/")[-1]
            if path and len(path) < 25 and path.isalpha():
                nav_labels.add(path.replace("-", " ").capitalize())

    # Check evidence store for additional footer/copyright/title facts
    if evidence_store:
        all_ev = evidence_store.get_all()
        for ev in all_ev:
            st = (ev.source_type or "").lower()
            text = (ev.text or "").strip()
            if "copyright" in text.lower() or "all rights reserved" in text.lower():
                match = re.search(r'©\s*(?:\d{4}\s*)?([A-Za-z0-9\s,\.\-]+?)(?:\.|\s+All|\s*$)', text)
                if match:
                    holder = match.group(1).strip()
                    if 2 <= len(holder) <= 50:
                        candidates.add(holder)
            if "nav" in st or (ev.selector and "nav" in ev.selector.lower()):
                if 2 <= len(text) <= 30:
                    nav_labels.add(text)

    status_code = homepage.status_code if homepage else 200
    is_https = final_url.lower().startswith("https://")

    return {
        "final_url": final_url,
        "business_name_candidates": sorted(list(candidates))[:8],
        "title": title,
        "meta_description": meta_desc,
        "h1": h1,
        "h2": h2,
        "cta_texts": sorted(list(all_ctas))[:12],
        "schemas_detected": sorted(list(all_schemas)),
        "sameas_urls": sorted(list(all_sameas)),
        "faq_questions": sorted(list(all_faqs))[:10],
        "pricing_signals_present": pricing_signals_present,
        "http": {
            "status": status_code,
            "https": is_https,
            "tls": None
        },
        "visible_pricing_text": sorted(list(visible_pricing_text))[:10],
        "nav_labels": sorted(list(nav_labels))[:15]
    }
