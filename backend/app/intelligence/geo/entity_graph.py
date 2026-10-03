"""
Entity graph quality for a representative page sample.

Rich-results syntax answers whether Google would reject a required field.
This module answers whether the identity graph is complete, grounded, and
consistent across JSON-LD, Open Graph, and the visible page.

Completeness uses applicable properties as the denominator. A schema that
states five matching values does not score 100.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.domain.enums import Category, EvidenceClass, RubricConfidence, Severity
from app.domain.models import ContradictionReport, Finding, FindingEvidence, PageEvidence, CanonicalEntityFact
from app.intelligence.business.entity_resolver import BANNED_NAMES
from app.intelligence.geo.schema_crosscheck import (
    SchemaCrosscheckResult,
    SchemaPropertyCheck,
    schema_crosschecker,
)

Applicability = Literal["EXPECTED", "NOT_APPLICABLE"]
PropertyStatus = Literal["PRESENT", "ABSENT", "PLACEHOLDER", "UNGROUNDED", "CONTRADICTED", "PARTIAL"]
TypeStatus = Literal["PRESENT", "ABSENT", "PARTIAL", "NOT_APPLICABLE"]

_ORG_TYPES = {"Organization", "LocalBusiness", "Corporation"}
_ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle"}
_PRODUCT_TYPES = {"Product", "SoftwareApplication"}
_PRESENT = {"PRESENT", "CONTRADICTED", "UNGROUNDED", "PARTIAL"}
_CORE_IDENTITY = {
    ("Organization", "name"),
    ("Organization", "url"),
    ("Organization", "logo"),
    ("Organization", "description"),
    ("Organization", "sameAs"),
    ("WebSite", "name"),
    ("WebSite", "url"),
}
_TEMPLATE_NAMES = {
    "company name",
    "your business",
    "your company name",
    "business name",
    "site name",
    "lorem ipsum",
    "example company",
    "todo",
    "changeme",
    "placeholder",
}
_TITLE_STOP = {
    "welcome",
    "home",
    "homepage",
    "official",
    "official site",
    "blog",
    "contact",
    "about",
    "index",
    "untitled",
    "default",
}
_LEGAL_SUFFIX = re.compile(
    r"\b(incorporated|inc|llc|l l c|ltd|limited|pvt|private|llp|plc|corp|corporation|gmbh|co)\b",
    re.I,
)
_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}\s+"
    r"(?:street|st|road|rd|avenue|ave|boulevard|blvd|lane|ln|drive|dr|way|court|ct)\b",
    re.I,
)
_PRICE_RE = re.compile(r"(?:\$|€|£|₹)\s?\d|\b\d+(?:\.\d{2})?\s?(?:/mo|per month|usd)\b", re.I)
_LEGAL_VISIBLE_RE = re.compile(r"\b(llc|l\.l\.c\.?|ltd|pvt\.?\s*ltd|llp|plc|gmbh)\b", re.I)
_WHY_CONFLICT = (
    "Answer engines can attach the wrong name to this entity. This does not block indexing."
)
_WHY_GAP = (
    "The sampled entity graph leaves applicable identity properties unstated. "
    "Answer engines have less to resolve. This does not block indexing."
)


class GraphProperty(BaseModel):
    schema_type: str
    property_name: str
    applicability: Applicability
    applicability_reason: str
    status: PropertyStatus
    schema_value: Optional[str] = None
    page_url: Optional[str] = None


class IdentityConflict(BaseModel):
    field: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    left_surface: str
    left_value: str
    left_url: Optional[str] = None
    right_surface: str
    right_value: str
    right_url: Optional[str] = None
    explanation: str


class TypeAssessment(BaseModel):
    schema_type: str
    status: TypeStatus
    applicable_properties: int = 0
    present_properties: int = 0
    reason: str = ""


class EntityGraphReport(BaseModel):
    quality_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    grounding_score: Optional[float] = None
    applicable_properties: int = 0
    present_properties: int = 0
    verified_count: int = 0
    partial_count: int = 0
    unmatched_count: int = 0
    contradicted_count: int = 0
    total_properties_checked: int = 0
    entity_completeness_pct: float = 0.0
    detected_schemas: List[str] = Field(default_factory=list)
    missing_recommended_schemas: List[str] = Field(default_factory=list)
    checks: List[SchemaPropertyCheck] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""
    conflicts: List[IdentityConflict] = Field(default_factory=list)
    properties: List[GraphProperty] = Field(default_factory=list)
    canonical_facts: List[CanonicalEntityFact] = Field(default_factory=list)
    not_applicable: List[str] = Field(default_factory=list)
    type_assessments: List[TypeAssessment] = Field(default_factory=list)
    sample_page_count: int = 0


class _NameObs(BaseModel):
    surface: str
    value: str
    url: str
    compare_titles: bool = False


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_as_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("name", "url", "text", "streetAddress", "@id"):
            if value.get(key):
                return _as_text(value.get(key))
    return ""


def _is_placeholder(value: str) -> bool:
    low = (value or "").strip().lower()
    if not low:
        return False
    if low in BANNED_NAMES or low in _TEMPLATE_NAMES:
        return True
    return "lorem ipsum" in low


def _norm_name(value: str) -> str:
    cleaned = _LEGAL_SUFFIX.sub(" ", (value or "").lower())
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _names_agree(left: str, right: str) -> bool:
    a, b = _norm_name(left), _norm_name(right)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.5


def _brand_token(title: str) -> str:
    if not title:
        return ""
    for sep in ("|", "–", "—", "-", ":", "•"):
        if sep in title:
            return title.split(sep)[0].strip()
    return title.strip()


def _title_comparable(token: str) -> bool:
    if _is_placeholder(token):
        return True
    if not token or len(token) > 40 or token.lower() in _TITLE_STOP:
        return False
    words = token.split()
    if not words or len(words) > 3:
        return False
    return all(word[:1].isupper() for word in words)


def _registrable(url_or_host: str) -> str:
    raw = (url_or_host or "").strip()
    if not raw:
        return ""
    host = urlparse(raw if "://" in raw else f"https://{raw}").netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    labels = [part for part in host.split(".") if part]
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "net", "ac", "gov"} and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host


def _host(url: str) -> str:
    host = urlparse(url if "://" in (url or "") else f"https://{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _flatten(pages: Sequence[PageEvidence]) -> List[Tuple[str, Dict[str, Any]]]:
    flat: List[Tuple[str, Dict[str, Any]]] = []
    for page in pages:
        blob = page.raw_schema or page.structured_data or []
        for item in blob:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                for sub in graph:
                    if isinstance(sub, dict):
                        flat.append((page.url or "", sub))
            else:
                flat.append((page.url or "", item))
    return flat


def _types_of(entity: Dict[str, Any]) -> List[str]:
    raw = entity.get("@type")
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _primary_type(entity: Dict[str, Any]) -> str:
    types = _types_of(entity)
    return types[0] if types else ""


def _is_home(page: PageEvidence) -> bool:
    if (page.page_type or "") == "homepage":
        return True
    path = urlparse(page.url or "").path.strip("/").lower()
    return path in {"", "index.html", "home"}


def _path(page: PageEvidence) -> str:
    return urlparse(page.url or "").path.lower()


def _corpus(pages: Sequence[PageEvidence]) -> str:
    parts: List[str] = []
    for page in pages:
        parts.append(page.title or "")
        parts.extend(page.h1 or [])
        parts.extend(page.h2 or [])
        parts.extend(page.h3 or [])
        parts.append(page.body_text or "")
        parts.append(page.meta_description or "")
        parts.extend(page.external_links or [])
        parts.extend(page.internal_links or [])
        parts.append(page.raw_html or "")
    return "\n".join(parts)


def _meta(page: PageEvidence, key: str) -> str:
    og = page.og_tags or {}
    meta = page.meta_tags or {}
    twitter = page.twitter_tags or {}
    return str(og.get(key) or meta.get(key) or twitter.get(key) or "").strip()


def _has_search(pages: Sequence[PageEvidence]) -> bool:
    for page in pages:
        path = _path(page)
        if path.rstrip("/").endswith("/search") or "/search" in path:
            return True
        html = (page.raw_html or "").lower()
        if 'type="search"' in html or "type='search'" in html or 'role="search"' in html:
            return True
        for form in page.forms or []:
            if not isinstance(form, dict):
                continue
            action = str(form.get("action") or form.get("form_action") or "").lower()
            if "search" in action:
                return True
            for inp in form.get("inputs") or []:
                if isinstance(inp, dict) and str(inp.get("type") or "").lower() == "search":
                    return True
    return False


def _visible_faq(pages: Sequence[PageEvidence]) -> bool:
    for page in pages:
        headings = list(page.h1 or []) + list(page.h2 or []) + list(page.h3 or [])
        blob = " ".join(headings + [page.body_text or ""]).lower()
        if re.search(r"\b(faq|frequently asked)\b", blob):
            return True
        if sum(1 for heading in headings if heading.strip().endswith("?")) >= 2:
            return True
    return False


def _page_kind(page: PageEvidence, kinds: Sequence[str]) -> bool:
    blob = f"{page.page_type or ''} {_path(page)}"
    return any(kind in blob for kind in kinds)


def _same_as_values(entity: Dict[str, Any], site_host: str) -> List[str]:
    raw = entity.get("sameAs")
    values = raw if isinstance(raw, list) else [raw] if raw else []
    external: List[str] = []
    for value in values:
        text = _as_text(value)
        if not text:
            continue
        if _host(text) and _host(text) == site_host:
            continue
        external.append(text)
    return external


def _search_action(entity: Dict[str, Any]) -> bool:
    raw = entity.get("potentialAction")
    actions = raw if isinstance(raw, list) else [raw] if raw else []
    for action in actions:
        if isinstance(action, dict) and "SearchAction" in str(action.get("@type") or ""):
            return True
    return False


def _contact_point_text(entity: Dict[str, Any]) -> str:
    raw = entity.get("contactPoint")
    if isinstance(raw, dict):
        bits = [raw.get("telephone"), raw.get("email"), raw.get("contactType"), raw.get("name")]
        return _as_text([bit for bit in bits if bit]) or "contactPoint"
    if isinstance(raw, list) and raw:
        return _contact_point_text({"contactPoint": raw[0]}) if isinstance(raw[0], dict) else "contactPoint"
    return _as_text(raw)


def _contact_value(entity: Dict[str, Any], field: str) -> str:
    direct = _as_text(entity.get(field))
    if direct:
        return direct
    raw = entity.get("contactPoint")
    points = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    for point in points:
        if isinstance(point, dict) and point.get(field):
            return _as_text(point.get(field))
    return ""


def _prop(
    schema_type: str,
    name: str,
    reason: str,
    value: str,
    url: str,
    applicable: bool = True,
) -> GraphProperty:
    if not applicable:
        return GraphProperty(
            schema_type=schema_type,
            property_name=name,
            applicability="NOT_APPLICABLE",
            applicability_reason=reason,
            status="ABSENT",
            page_url=url or None,
        )
    if not value:
        status: PropertyStatus = "ABSENT"
    elif _is_placeholder(value):
        status = "PLACEHOLDER"
    else:
        status = "PRESENT"
    return GraphProperty(
        schema_type=schema_type,
        property_name=name,
        applicability="EXPECTED",
        applicability_reason=reason,
        status=status,
        schema_value=value or None,
        page_url=url or None,
    )


def _first(entities: Sequence[Tuple[str, Dict[str, Any]]], types: set) -> Tuple[str, Dict[str, Any]]:
    for url, entity in entities:
        if _primary_type(entity) in types or any(item in types for item in _types_of(entity)):
            return url, entity
    return "", {}


def _assessment(schema_type: str, props: Sequence[GraphProperty], reason_if_na: str, absent_reason: str) -> TypeAssessment:
    scoped = [item for item in props if item.schema_type == schema_type]
    expected = [item for item in scoped if item.applicability == "EXPECTED"]
    if not expected:
        return TypeAssessment(schema_type=schema_type, status="NOT_APPLICABLE", reason=reason_if_na)
    present = sum(1 for item in expected if item.status in _PRESENT)
    if present == 0:
        status: TypeStatus = "ABSENT"
        reason = absent_reason
    elif present == len(expected):
        status = "PRESENT"
        reason = f"{present} of {len(expected)} applicable properties are present."
    else:
        status = "PARTIAL"
        reason = f"{present} of {len(expected)} applicable properties are present."
    return TypeAssessment(
        schema_type=schema_type,
        status=status,
        applicable_properties=len(expected),
        present_properties=present,
        reason=reason,
    )


def _content_tokens(text: str) -> set:
    stop = {"this", "that", "with", "from", "your", "have", "will", "about", "their", "which"}
    return {word for word in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if word not in stop}


def _descriptions_disagree(left: str, right: str) -> bool:
    if _is_placeholder(left) or _is_placeholder(right):
        return bool(left and right)
    if len(left) <= 40 or len(right) <= 40:
        return False
    a, b = _content_tokens(left), _content_tokens(right)
    if len(a) < 4 or len(b) < 4:
        return False
    return len(a & b) / len(a | b) < 0.15


def _score(props: Sequence[GraphProperty], conflicts: Sequence[IdentityConflict], grounding: Optional[float], has_jsonld: bool) -> Tuple[float, float, float, int, int]:
    expected = [item for item in props if item.applicability == "EXPECTED"]
    applicable = len(expected)
    present = sum(1 for item in expected if item.status in _PRESENT)
    completeness = round((present / applicable) * 100.0, 1) if applicable else 0.0
    consistency = 100.0
    high = [item for item in conflicts if item.severity == "HIGH"]
    medium = [item for item in conflicts if item.severity == "MEDIUM"]
    consistency -= 60.0 * len(high)
    consistency -= 15.0 * len(medium)
    consistency = max(0.0, consistency)
    if not has_jsonld:
        return 0.0, 0.0, 0.0, applicable, present
    grounding_component = grounding if grounding is not None else completeness
    quality = round(0.45 * completeness + 0.20 * grounding_component + 0.35 * consistency, 1)
    if high:
        quality = min(quality, 59.0)
    return quality, completeness, round(consistency, 1), applicable, present


def _headline(
    quality: float,
    present: int,
    applicable: int,
    grounding: Optional[float],
    verified: int,
    stated: int,
    conflicts: Sequence[IdentityConflict],
    has_jsonld: bool,
    page_count: int,
) -> str:
    sample = f"this {page_count}-page sample"
    if not has_jsonld:
        return (
            f"No Schema.org JSON-LD in {sample}. Entity graph quality 0/100. "
            f"{present} of {applicable} applicable properties are present."
        )
    if grounding is None:
        grounded = "Stated-property grounding was not measured because no property values were stated."
    else:
        grounded = f"Stated-property grounding is {grounding:.0f}/100 ({verified} of {stated})."
    conflict = ""
    if conflicts:
        first = conflicts[0]
        conflict = f" {first.left_surface} is '{first.left_value}'; {first.right_surface} is '{first.right_value}'."
    return (
        f"Entity graph quality {quality:.0f}/100 on {sample}. "
        f"{present} of {applicable} applicable properties are present. "
        f"{grounded}{conflict}"
    )


def _build_properties(pages: Sequence[PageEvidence]) -> Tuple[List[GraphProperty], List[TypeAssessment], List[str], bool, str]:
    entities = _flatten(pages)
    has_jsonld = bool(entities)
    site_host = _host(pages[0].url) if pages else ""
    corpus = _corpus(pages)
    links = " ".join(
        (page.raw_html or "") + " " + " ".join(page.external_links or []) + " " + " ".join(page.internal_links or [])
        for page in pages
    ).lower()
    home_url = next((page.url for page in pages if _is_home(page)), pages[0].url if pages else "")

    org_url, org = _first(entities, _ORG_TYPES)
    web_url, website = _first(entities, {"WebSite"})
    service_url, service = _first(entities, {"Service"})
    product_url, product = _first(entities, _PRODUCT_TYPES)
    article_url, article = _first(entities, _ARTICLE_TYPES)
    faq_url, faq = _first(entities, {"FAQPage"})

    phone_visible = "tel:" in links or bool(_PHONE_RE.search(corpus))
    email_visible = "mailto:" in links or bool(_EMAIL_RE.search(corpus))
    address_visible = bool(_ADDRESS_RE.search(corpus)) or bool(re.search(r"\baddress\s*[:\-]\s*\d", corpus, re.I))
    legal_visible = bool(_LEGAL_VISIBLE_RE.search(corpus))
    about_pages = [page for page in pages if _page_kind(page, ("about", "team", "company"))]
    about_blob = " ".join((page.body_text or "") + " " + " ".join(page.h2 or []) for page in about_pages)
    founder_visible = bool(re.search(r"\b(co-)?founders?\b", about_blob, re.I))
    employee_visible = bool(re.search(r"\b(our team|leadership|meet the team)\b", about_blob, re.I))
    price_visible = bool(_PRICE_RE.search(corpus))
    search_visible = _has_search(pages)
    faq_visible = _visible_faq(pages)
    service_visible = bool(service) or any(_page_kind(page, ("service", "solution")) for page in pages)
    product_visible = bool(product) or any(_page_kind(page, ("product", "shop")) for page in pages)
    article_visible = bool(article) or any(_page_kind(page, ("blog", "news", "article")) for page in pages)
    inner_pages = [page for page in pages if not _is_home(page)]

    org_same = _same_as_values(org, site_host) if org else []
    props: List[GraphProperty] = [
        _prop("Organization", "name", "Organization name is always expected on the sample.", _as_text(org.get("name")), org_url),
        _prop("Organization", "url", "Organization url is always expected on the sample.", _as_text(org.get("url")), org_url),
        _prop("Organization", "logo", "Organization logo is always expected on the sample.", _as_text(org.get("logo")), org_url),
        _prop("Organization", "description", "Organization description is always expected on the sample.", _as_text(org.get("description")), org_url),
        _prop(
            "Organization",
            "sameAs",
            "A public site is expected to state external sameAs profiles.",
            ", ".join(org_same),
            org_url,
        ),
        _prop(
            "Organization",
            "legalName",
            "A legal suffix or legalName is visible in the sample." if (legal_visible or org.get("legalName")) else "No legal suffix is visible in the sample.",
            _as_text(org.get("legalName")),
            org_url,
            applicable=bool(legal_visible or org.get("legalName")),
        ),
        _prop(
            "Organization",
            "address",
            "A street address is visible in the sample." if address_visible or org.get("address") else "No street address is visible in the sample.",
            _as_text(org.get("address")),
            org_url,
            applicable=bool(address_visible or org.get("address")),
        ),
        _prop(
            "Organization",
            "telephone",
            "A telephone number is visible in the sample." if phone_visible or _contact_value(org, "telephone") else "No telephone number is visible in the sample.",
            _contact_value(org, "telephone"),
            org_url,
            applicable=bool(phone_visible or _contact_value(org, "telephone")),
        ),
        _prop(
            "Organization",
            "email",
            "An email address is visible in the sample." if email_visible or _contact_value(org, "email") else "No email address is visible in the sample.",
            _contact_value(org, "email"),
            org_url,
            applicable=bool(email_visible or _contact_value(org, "email")),
        ),
        _prop(
            "Organization",
            "contactPoint",
            "Visible phone or email makes contactPoint expected." if (phone_visible or email_visible or org.get("contactPoint")) else "No contact channel is visible in the sample.",
            _contact_point_text(org),
            org_url,
            applicable=bool(phone_visible or email_visible or org.get("contactPoint")),
        ),
        _prop(
            "Organization",
            "founder",
            "An about or team page names a founder." if (founder_visible or org.get("founder")) else "No founder is named in the sample.",
            _as_text(org.get("founder")),
            org_url,
            applicable=bool(founder_visible or org.get("founder")),
        ),
        _prop(
            "Organization",
            "employee",
            "An about or team page names a team." if (employee_visible or org.get("employee")) else "No team is named in the sample.",
            _as_text(org.get("employee")),
            org_url,
            applicable=bool(employee_visible or org.get("employee")),
        ),
        _prop("WebSite", "name", "WebSite name is always expected on the sample.", _as_text(website.get("name")), web_url or home_url),
        _prop("WebSite", "url", "WebSite url is always expected on the sample.", _as_text(website.get("url")), web_url or home_url),
        _prop(
            "WebSite",
            "SearchAction",
            "A site search form is in the sample." if search_visible else "No site search form or /search URL is in the sample.",
            "SearchAction" if website and _search_action(website) else "",
            web_url or home_url,
            applicable=search_visible or bool(website and _search_action(website)),
        ),
    ]

    service_applicable = service_visible
    props.extend([
        _prop("Service", "serviceType", "A service page or Service entity is in the sample." if service_applicable else "No service page or Service entity is in the sample.", _as_text(service.get("serviceType")), service_url, service_applicable),
        _prop("Service", "provider", "A service page or Service entity is in the sample." if service_applicable else "No service page or Service entity is in the sample.", _as_text(service.get("provider")), service_url, service_applicable),
        _prop("Service", "areaServed", "A service page or Service entity is in the sample." if service_applicable else "No service page or Service entity is in the sample.", _as_text(service.get("areaServed")), service_url, service_applicable),
        _prop("Service", "description", "A service page or Service entity is in the sample." if service_applicable else "No service page or Service entity is in the sample.", _as_text(service.get("description")), service_url, service_applicable),
        _prop(
            "Service",
            "offers",
            "A price is visible in the sample." if (service_applicable and (price_visible or service.get("offers"))) else "No service price is visible in the sample.",
            _as_text(service.get("offers")),
            service_url,
            applicable=bool(service_applicable and (price_visible or service.get("offers"))),
        ),
    ])

    product_applicable = product_visible
    props.extend([
        _prop("Product", "name", "A product page or product entity is in the sample." if product_applicable else "No product page or product entity is in the sample.", _as_text(product.get("name")), product_url, product_applicable),
        _prop("Product", "description", "A product page or product entity is in the sample." if product_applicable else "No product page or product entity is in the sample.", _as_text(product.get("description")), product_url, product_applicable),
        _prop("Product", "image", "A product page or product entity is in the sample." if product_applicable else "No product page or product entity is in the sample.", _as_text(product.get("image")), product_url, product_applicable),
        _prop(
            "Product",
            "offers",
            "A price or offer is visible in the sample." if (product_applicable and (price_visible or product.get("offers"))) else "No product price is visible in the sample.",
            _as_text(product.get("offers")),
            product_url,
            applicable=bool(product_applicable and (price_visible or product.get("offers"))),
        ),
    ])

    article_applicable = article_visible
    props.extend([
        _prop("Article", "headline", "A blog or article page is in the sample." if article_applicable else "No blog or article page is in the sample.", _as_text(article.get("headline") or article.get("name")), article_url, article_applicable),
        _prop("Article", "image", "A blog or article page is in the sample." if article_applicable else "No blog or article page is in the sample.", _as_text(article.get("image")), article_url, article_applicable),
        _prop("Article", "datePublished", "A blog or article page is in the sample." if article_applicable else "No blog or article page is in the sample.", _as_text(article.get("datePublished")), article_url, article_applicable),
        _prop("Article", "author", "A blog or article page is in the sample." if article_applicable else "No blog or article page is in the sample.", _as_text(article.get("author")), article_url, article_applicable),
    ])

    crumb_pages = []
    for page in inner_pages:
        found = False
        for url, entity in entities:
            if url == (page.url or "") and "BreadcrumbList" in _types_of(entity):
                elements = entity.get("itemListElement")
                if isinstance(elements, list) and elements:
                    found = True
        crumb_pages.append(found)
    if inner_pages:
        if all(crumb_pages):
            crumb_value, crumb_status = "BreadcrumbList", "PRESENT"
        elif any(crumb_pages):
            crumb_value, crumb_status = "BreadcrumbList", "PARTIAL"
        else:
            crumb_value, crumb_status = "", "ABSENT"
        props.append(GraphProperty(
            schema_type="BreadcrumbList",
            property_name="itemListElement",
            applicability="EXPECTED",
            applicability_reason="Inner pages in the sample are expected to state BreadcrumbList.",
            status=crumb_status,  # type: ignore[arg-type]
            schema_value=crumb_value or None,
            page_url=inner_pages[0].url,
        ))
    else:
        props.append(GraphProperty(
            schema_type="BreadcrumbList",
            property_name="itemListElement",
            applicability="NOT_APPLICABLE",
            applicability_reason="The sample has no page below the homepage.",
            status="ABSENT",
            page_url=home_url,
        ))

    faq_questions = faq.get("mainEntity") if faq else None
    faq_value = _as_text(faq_questions) if isinstance(faq_questions, list) and faq_questions else ""
    props.append(_prop(
        "FAQPage",
        "mainEntity",
        "Visible FAQ copy is in the sample." if (faq_visible or faq) else "No visible FAQ heading or question list is in the sample.",
        faq_value,
        faq_url,
        applicable=bool(faq_visible or faq),
    ))

    assessments = [
        _assessment("Organization", props, "", "No Organization, LocalBusiness, or Corporation entity is in the sample."),
        _assessment("WebSite", [item for item in props if item.property_name != "SearchAction"], "", "No WebSite entity states name and url."),
        _assessment("WebSite", [item for item in props if item.property_name == "SearchAction"], "No site search form or /search URL is in the sample.", "A site search form is in the sample, and WebSite SearchAction is absent."),
        _assessment("Service", props, "No service page or Service entity is in the sample.", "A service page is in the sample, and Service schema is absent."),
        _assessment("Product", props, "No product page or product entity is in the sample.", "A product page is in the sample, and Product schema is absent."),
        _assessment("Article", props, "No blog or article page is in the sample.", "A blog page is in the sample, and Article schema is absent."),
        _assessment("BreadcrumbList", props, "The sample has no page below the homepage.", "Inner pages in the sample have no BreadcrumbList."),
        _assessment("FAQPage", props, "No visible FAQ heading or question list is in the sample.", "Visible questions are in the sample, and FAQPage is absent. The value is extractability for answer engines."),
    ]
    # The second WebSite assessment is SearchAction. Expose it as its own row.
    website_rows = [item for item in assessments if item.schema_type == "WebSite"]
    if len(website_rows) == 2:
        website_rows[1] = website_rows[1].model_copy(update={"schema_type": "SearchAction"})
        assessments = [item for item in assessments if item.schema_type != "WebSite"] + [website_rows[0], website_rows[1]]

    not_applicable = [
        f"{item.schema_type}: {item.reason}"
        for item in assessments
        if item.status == "NOT_APPLICABLE"
    ]
    return props, assessments, not_applicable, has_jsonld, site_host


def _name_observations(pages: Sequence[PageEvidence], entities: Sequence[Tuple[str, Dict[str, Any]]]) -> List[_NameObs]:
    found: List[_NameObs] = []
    for url, entity in entities:
        types = set(_types_of(entity))
        primary = _primary_type(entity)
        if types & _ORG_TYPES or primary in _ORG_TYPES:
            if entity.get("name"):
                found.append(_NameObs(surface="Organization.name", value=_as_text(entity.get("name")), url=url))
            if entity.get("legalName"):
                found.append(_NameObs(surface="Organization.legalName", value=_as_text(entity.get("legalName")), url=url))
        if "WebSite" in types:
            if entity.get("name"):
                found.append(_NameObs(surface="WebSite.name", value=_as_text(entity.get("name")), url=url))
        if "Service" in types and entity.get("provider"):
            found.append(_NameObs(surface="Service.provider", value=_as_text(entity.get("provider")), url=url))
        if types & _PRODUCT_TYPES and entity.get("brand"):
            found.append(_NameObs(surface="Product.brand", value=_as_text(entity.get("brand")), url=url))
    for page in pages:
        og_site = _meta(page, "og:site_name")
        if og_site:
            found.append(_NameObs(surface="og:site_name", value=og_site, url=page.url or ""))
        for surface, raw in (
            ("og:title", _meta(page, "og:title")),
            ("twitter:title", _meta(page, "twitter:title")),
            ("title", page.title or ""),
        ):
            token = _brand_token(raw)
            if token and _title_comparable(token):
                found.append(_NameObs(surface=surface, value=token, url=page.url or "", compare_titles=True))
    return found


def _identity_conflicts(pages: Sequence[PageEvidence]) -> Tuple[List[IdentityConflict], List[str]]:
    entities = _flatten(pages)
    names = _name_observations(pages, entities)
    conflicts: List[IdentityConflict] = []
    notes: List[str] = []
    anchor = next((item for item in names if item.surface == "Organization.name" and not _is_placeholder(item.value)), None)
    if anchor is None:
        anchor = next((item for item in names if item.surface in {"WebSite.name", "Organization.legalName"} and not _is_placeholder(item.value)), None)

    seen = set()
    if anchor:
        for other in names:
            if other.surface == anchor.surface and other.url == anchor.url and other.value == anchor.value:
                continue
            if other.surface == "Organization.legalName" and _names_agree(anchor.value, other.value):
                continue
            if other.compare_titles and not _is_placeholder(other.value) and _names_agree(anchor.value, other.value):
                continue
            if other.compare_titles and not _title_comparable(other.value):
                continue
            if _names_agree(anchor.value, other.value) and not (_is_placeholder(other.value) or _is_placeholder(anchor.value)):
                continue
            if not other.value:
                continue
            key = tuple(sorted((anchor.surface, other.surface, anchor.value.lower(), other.value.lower())))
            if key in seen:
                continue
            seen.add(key)
            conflicts.append(IdentityConflict(
                field="name",
                severity="HIGH",
                left_surface=anchor.surface,
                left_value=anchor.value,
                left_url=anchor.url,
                right_surface=other.surface,
                right_value=other.value,
                right_url=other.url,
                explanation=(
                    f"{anchor.surface} on {anchor.url or 'the sample'} is '{anchor.value}'. "
                    f"{other.surface} on {other.url or 'the sample'} is '{other.value}'."
                ),
            ))

    urls: List[Tuple[str, str, str]] = []
    for url, entity in entities:
        types = set(_types_of(entity))
        if types & _ORG_TYPES and entity.get("url"):
            urls.append(("Organization.url", _as_text(entity.get("url")), url))
        if "WebSite" in types and entity.get("url"):
            urls.append(("WebSite.url", _as_text(entity.get("url")), url))
    for page in pages:
        og_url = _meta(page, "og:url")
        if og_url:
            urls.append(("og:url", og_url, page.url or ""))
        if page.canonical_url:
            urls.append(("canonical", page.canonical_url, page.url or ""))

    domains = [(surface, value, page_url, _registrable(value)) for surface, value, page_url in urls if _registrable(value)]
    distinct = []
    for item in domains:
        if item[3] not in {existing[3] for existing in distinct}:
            distinct.append(item)
    if len(distinct) >= 2:
        left, right = distinct[0], distinct[1]
        conflicts.append(IdentityConflict(
            field="url",
            severity="HIGH",
            left_surface=left[0],
            left_value=left[1],
            left_url=left[2],
            right_surface=right[0],
            right_value=right[1],
            right_url=right[2],
            explanation=(
                f"{left[0]} host {left[3]} does not match {right[0]} host {right[3]}."
            ),
        ))
    elif domains:
        hosts = {_host(item[1]) for item in domains}
        if len(hosts) > 1:
            notes.append("URL hosts differ by www or scheme. That is not a different registered domain.")

    descriptions: List[Tuple[str, str, str]] = []
    for url, entity in entities:
        if set(_types_of(entity)) & _ORG_TYPES and entity.get("description"):
            descriptions.append(("Organization.description", _as_text(entity.get("description")), url))
    for page in pages:
        og_desc = _meta(page, "og:description")
        if og_desc:
            descriptions.append(("og:description", og_desc, page.url or ""))
        if page.meta_description:
            descriptions.append(("meta description", page.meta_description, page.url or ""))
    for index, left in enumerate(descriptions):
        for right in descriptions[index + 1:]:
            if left[0] == right[0]:
                continue
            if _descriptions_disagree(left[1], right[1]):
                conflicts.append(IdentityConflict(
                    field="description",
                    severity="MEDIUM",
                    left_surface=left[0],
                    left_value=left[1][:180],
                    left_url=left[2],
                    right_surface=right[0],
                    right_value=right[1][:180],
                    right_url=right[2],
                    explanation=f"{left[0]} and {right[0]} describe different businesses.",
                ))
                break
        else:
            continue
        break
    return conflicts, notes


def _evidence(url: str, element: str, value: str, snippet: str) -> FindingEvidence:
    return FindingEvidence(
        url=url or None,
        element=element,
        value=value,
        snippet=snippet,
        source="crawl",
        evidence_class=EvidenceClass.OBSERVED,
        evidence_subtype="DOM",
    )


def _findings(report: EntityGraphReport, pages: Sequence[PageEvidence]) -> Tuple[List[Finding], List[ContradictionReport]]:
    findings: List[Finding] = []
    contradictions: List[ContradictionReport] = []
    sample_urls = [page.url for page in pages if page.url]

    for index, conflict in enumerate(report.conflicts):
        if conflict.severity != "HIGH":
            continue
        if conflict.field == "url":
            title = "Organization URL contradicts the page canonical"
        elif conflict.right_surface == "og:site_name" or conflict.left_surface == "og:site_name":
            title = "Organization name contradicts Open Graph site name"
        else:
            title = f"{conflict.left_surface} contradicts {conflict.right_surface}"
        evidence = [
            _evidence(conflict.left_url or "", conflict.left_surface, conflict.left_value, conflict.explanation),
            _evidence(conflict.right_url or "", conflict.right_surface, conflict.right_value, conflict.explanation),
        ]
        finding_id = f"entity_graph_contradiction_{index}"
        findings.append(Finding(
            finding_id=finding_id,
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title=title,
            description=conflict.explanation,
            recommendation=(
                f"Use one entity name. Set {conflict.right_surface} to the same string as {conflict.left_surface}."
            ),
            why_it_matters=_WHY_CONFLICT,
            validation_criteria=(
                f"{conflict.left_surface} and {conflict.right_surface} state the same entity after legal suffixes are ignored."
            ),
            evidence=evidence,
            evidence_refs=["entity_graph"],
            rule_id="entity_graph_contradiction",
            confidence=0.95,
            confidence_rubric=RubricConfidence.VERIFIED,
            evidence_class=EvidenceClass.OBSERVED,
            evidence_subtype="DOM",
            impact=8,
            effort=2,
            priority=8,
            surfaces_affected=[
                {"surface": conflict.left_surface, "url": conflict.left_url or "", "value": conflict.left_value},
                {"surface": conflict.right_surface, "url": conflict.right_url or "", "value": conflict.right_value},
            ],
        ))
        contradictions.append(ContradictionReport(
            id=finding_id,
            contradiction_type="schema_identity_conflict",
            declared_type=conflict.left_surface,
            detected_type=conflict.right_surface,
            confidence=0.95,
            reason=conflict.explanation,
            evidence=evidence,
        ))

    expected = [item for item in report.properties if item.applicability == "EXPECTED"]
    core_absent = [
        item for item in expected
        if (item.schema_type, item.property_name) in _CORE_IDENTITY and item.status in {"ABSENT", "PLACEHOLDER"}
    ]
    if core_absent:
        name_or_url = any(item.property_name in {"name", "url"} and item.schema_type == "Organization" for item in core_absent)
        listed = ", ".join(f"{item.schema_type}.{item.property_name}" for item in core_absent)
        findings.append(Finding(
            finding_id="entity_graph_incomplete",
            category=Category.SCHEMA,
            severity=Severity.HIGH if name_or_url or not report.detected_schemas else Severity.MEDIUM,
            title="Identity properties are incomplete on this sample",
            description=(
                f"{report.present_properties} of {report.applicable_properties} applicable properties are present. "
                f"Absent core properties: {listed}."
            ),
            recommendation="State Organization name, url, logo, description, and sameAs, plus WebSite name and url.",
            why_it_matters=_WHY_GAP,
            validation_criteria="Each always-expected identity property has a non-placeholder value in JSON-LD.",
            evidence=[_evidence(url, "json-ld", "sample page", "Page included in the entity graph sample.") for url in sample_urls[:5]],
            evidence_refs=["entity_graph"],
            rule_id="entity_graph_incomplete",
            confidence=0.95,
            confidence_rubric=RubricConfidence.VERIFIED,
            evidence_class=EvidenceClass.OBSERVED,
            evidence_subtype="DOM",
            impact=6,
            effort=3,
            priority=6,
        ))

    contact_names = {"telephone", "email", "address", "contactPoint"}
    contact_absent = [
        item for item in expected
        if item.schema_type == "Organization" and item.property_name in contact_names and item.status in {"ABSENT", "PLACEHOLDER"}
    ]
    if contact_absent:
        listed = ", ".join(item.property_name for item in contact_absent)
        findings.append(Finding(
            finding_id="entity_graph_contact",
            category=Category.SCHEMA,
            severity=Severity.MEDIUM,
            title="Visible contact details are absent from Organization schema",
            description=f"The sample shows contact details that Organization schema does not state: {listed}.",
            recommendation=f"Add the visible {listed} values to Organization JSON-LD.",
            why_it_matters=_WHY_GAP,
            validation_criteria="Organization schema states each contact value that is visible in the sample.",
            evidence=[_evidence(item.page_url or (sample_urls[0] if sample_urls else ""), item.property_name, item.schema_value or "", item.applicability_reason) for item in contact_absent],
            evidence_refs=["entity_graph"],
            rule_id="entity_graph_contact",
            confidence=0.95,
            confidence_rubric=RubricConfidence.VERIFIED,
            evidence_class=EvidenceClass.OBSERVED,
            evidence_subtype="DOM",
            impact=5,
            effort=2,
            priority=5,
        ))

    conditional = {"Service", "Product", "Article", "BreadcrumbList", "FAQPage", "SearchAction"}
    absent_types = [item for item in report.type_assessments if item.schema_type in conditional and item.status == "ABSENT"]
    if absent_types:
        lines = [f"{item.schema_type}: {item.reason}" for item in absent_types]
        findings.append(Finding(
            finding_id="entity_graph_applicability",
            category=Category.SCHEMA,
            severity=Severity.MEDIUM,
            title="Applicable schema types are absent from this sample",
            description=" ".join(lines),
            recommendation=(
                "Add the schema type only where the sample already shows that entity. "
                "FAQPage is for extractability by answer engines when the questions are visible."
            ),
            why_it_matters=_WHY_GAP,
            validation_criteria="Each schema type the sample justifies is present, and inapplicable types stay unstated.",
            evidence=[_evidence(url, "json-ld", "sample page", "Page included in the entity graph sample.") for url in sample_urls[:5]],
            evidence_refs=["entity_graph"],
            rule_id="entity_graph_applicability",
            confidence=0.9,
            confidence_rubric=RubricConfidence.VERIFIED,
            evidence_class=EvidenceClass.OBSERVED,
            evidence_subtype="DOM",
            impact=5,
            effort=3,
            priority=5,
        ))
    return findings, contradictions


def evaluate_entity_graph(pages: Sequence[PageEvidence], brand_name: str = "") -> Tuple[EntityGraphReport, List[Finding], List[ContradictionReport]]:
    """Score the sample and return findings plus identity contradictions."""
    del brand_name  # The graph is read from the pages. The resolver keeps its own canonical name.
    pages = list(pages or [])
    cross: SchemaCrosscheckResult = schema_crosschecker.crosscheck(pages)
    props, assessments, not_applicable, has_jsonld, _site = _build_properties(pages)
    conflicts, notes = _identity_conflicts(pages)
    quality, completeness, consistency, applicable, present = _score(
        props, conflicts, cross.grounding_score, has_jsonld
    )
    summary = _headline(
        quality,
        present,
        applicable,
        cross.grounding_score,
        cross.verified_count,
        cross.total_properties_checked,
        conflicts,
        has_jsonld,
        len(pages),
    )
    faq_na = any(item.schema_type == "FAQPage" and item.status == "NOT_APPLICABLE" for item in assessments)
    recommendations = [
        item for item in cross.recommendations
        if not (faq_na and "FAQPage" in item)
    ]
    absent_types = [item.schema_type for item in assessments if item.status == "ABSENT"]
    canonical_facts: List[CanonicalEntityFact] = []
    conflict_fields = {c.field for c in conflicts}
    for p in props:
        if p.status in ("PRESENT", "PARTIAL") and p.schema_value:
            has_conf = p.property_name in conflict_fields
            contra = [c.explanation for c in conflicts if c.field == p.property_name]
            canonical_facts.append(CanonicalEntityFact(
                entity_type=p.schema_type,
                attribute=p.property_name,
                value=p.schema_value,
                source_type="SCHEMA",
                source_url=p.page_url,
                verified=not has_conf,
                contradictions=contra
            ))

    report = EntityGraphReport(
        quality_score=quality,
        completeness_score=completeness if has_jsonld else 0.0,
        consistency_score=consistency,
        grounding_score=cross.grounding_score,
        applicable_properties=applicable,
        present_properties=present,
        verified_count=cross.verified_count,
        partial_count=cross.partial_count,
        unmatched_count=cross.unmatched_count,
        contradicted_count=cross.contradicted_count + sum(1 for item in conflicts if item.severity == "HIGH"),
        total_properties_checked=cross.total_properties_checked,
        entity_completeness_pct=completeness if has_jsonld else 0.0,
        detected_schemas=cross.detected_schemas,
        missing_recommended_schemas=absent_types,
        checks=cross.checks,
        discrepancies=(cross.discrepancies + notes)[:8],
        recommendations=recommendations[:5],
        summary=summary,
        conflicts=conflicts,
        properties=props,
        canonical_facts=canonical_facts,
        not_applicable=not_applicable,
        type_assessments=assessments,
        sample_page_count=len(pages),
    )
    findings, contradictions = _findings(report, pages)
    return report, findings, contradictions
