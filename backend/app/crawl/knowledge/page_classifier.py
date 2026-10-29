"""
Dristik KIE — Phase 1: Page Knowledge Classifier
Classifies every crawled page into a PageRole and knowledge domains.
Provides the foundation for intent-aware retrieval routing in the Query Planner.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from app.domain.models import PageEvidence
from app.crawl.knowledge.primitives import (
    PageRole,
    PageKnowledgeClassification,
    KnowledgeSourceTier,
)


# ─────────────────────────────────────────────────────────────────────────────
# URL-Path Signal Catalog
# ─────────────────────────────────────────────────────────────────────────────

_URL_ROLE_SIGNALS: List[tuple[list[str], PageRole]] = [
    # Ordered by specificity — first match wins
    (["pricing", "plans", "packages", "subscription", "billing", "tiers", "cost"], PageRole.PRICING),
    (["security", "compliance", "trust", "gdpr", "hipaa", "soc2", "soc-2", "privacy"], PageRole.SECURITY),
    (["case-study", "case_study", "customer-story", "success-story", "client-story", "portfolio"], PageRole.CASE_STUDY),
    (["documentation", "docs", "api", "developer", "sdk", "reference", "guide"], PageRole.DOCUMENTATION),
    (["faq", "frequently-asked", "questions", "help-center"], PageRole.FAQ),
    (["careers", "jobs", "join-us", "hiring", "team", "culture"], PageRole.CAREERS),
    (["contact", "contact-us", "reach-us", "get-in-touch", "support", "talk"], PageRole.CONTACT),
    (["about", "about-us", "our-story", "who-we-are", "mission", "vision", "company"], PageRole.ABOUT),
    (["product", "platform", "solution", "feature", "capabilities"], PageRole.PRODUCT),
    (["service", "services", "offering", "solutions", "consulting", "agency"], PageRole.SERVICES),
    (["blog", "news", "articles", "insights", "post", "resources", "thought-leadership"], PageRole.BLOG),
    (["terms", "tos", "legal", "refund", "cookie", "disclaimer", "policy"], PageRole.LEGAL),
]

_TITLE_ROLE_SIGNALS: List[tuple[list[str], PageRole]] = [
    (["pricing", "price", "plan", "subscription", "cost per", "packages"], PageRole.PRICING),
    (["security", "compliance", "soc 2", "iso 27001", "gdpr", "privacy policy", "data protection"], PageRole.SECURITY),
    (["case study", "customer story", "success story", "client", "how they", "portfolio"], PageRole.CASE_STUDY),
    (["documentation", "api reference", "developer guide", "getting started"], PageRole.DOCUMENTATION),
    (["faq", "frequently asked", "help center", "support"], PageRole.FAQ),
    (["careers", "join our team", "we're hiring", "culture", "life at"], PageRole.CAREERS),
    (["contact", "get in touch", "talk to us", "schedule a demo"], PageRole.CONTACT),
    (["about us", "our story", "who we are", "mission", "vision", "the team"], PageRole.ABOUT),
    (["features", "product", "platform", "solution", "how it works"], PageRole.PRODUCT),
    (["services", "offerings", "consulting", "what we do"], PageRole.SERVICES),
    (["blog", "news", "insights", "articles", "updates"], PageRole.BLOG),
    (["terms of service", "terms and conditions", "legal notice", "cookie policy"], PageRole.LEGAL),
]


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Domain Catalog
# ─────────────────────────────────────────────────────────────────────────────

_DOMAIN_SIGNALS: List[tuple[str, list[str]]] = [
    ("pricing_transparency",    ["pricing", "price", "$", "€", "£", "₹", "/mo", "per month", "per user", "plan", "tier"]),
    ("compliance_security",     ["soc 2", "iso 27001", "hipaa", "gdpr", "ccpa", "pci-dss", "aes-256", "tls 1.3", "penetration"]),
    ("technical_architecture",  ["api", "rest", "graphql", "webhook", "sdk", "kubernetes", "docker", "microservice", "aws", "gcp", "azure"]),
    ("integrations",            ["integrat", "connect", "native support", "plugin", "zapier", "slack", "salesforce", "hubspot"]),
    ("icp_targeting",           ["enterprise", "startup", "smb", "b2b", "small business", "team of", "employees", "headcount"]),
    ("customer_proof",          ["customer", "case study", "client", "testimonial", "review", "roi", "result", "outcome"]),
    ("competitive_positioning", ["vs ", "versus", "alternative", "compare", "competitor", "unlike", "unlike other"]),
    ("purchasing_path",         ["get started", "book a demo", "free trial", "schedule", "contact sales", "buy now", "sign up"]),
    ("onboarding_support",      ["onboarding", "implementation", "setup", "support", "sla", "customer success", "dedicated"]),
    ("product_capabilities",    ["feature", "capability", "workflow", "automat", "dashboard", "report", "analytic"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Classifier
# ─────────────────────────────────────────────────────────────────────────────

class PageKnowledgeClassifier:
    """
    Classifies crawled pages into PageRole and KIE knowledge domains.
    Used by the Query Planner to route retrieval strategy per question intent.
    """

    @classmethod
    def classify(cls, page: PageEvidence) -> PageKnowledgeClassification:
        url = page.url or ""
        title = (page.title or "").lower()
        body = (page.body_text or "").lower()
        full_text = f"{title} {body[:3000]}"

        page_role = cls._resolve_role(url, title)
        knowledge_domains = cls._extract_domains(full_text)
        primary_entities = cls._extract_primary_entities(page, title, body)

        return PageKnowledgeClassification(
            url=url,
            title=page.title,
            page_role=page_role,
            knowledge_domains=knowledge_domains,
            primary_entities=primary_entities,
            confidence=0.9 if page_role != PageRole.UNKNOWN else 0.5,
        )

    @classmethod
    def classify_all(cls, pages: List[PageEvidence]) -> List[PageKnowledgeClassification]:
        return [cls.classify(p) for p in pages]

    @classmethod
    def _resolve_role(cls, url: str, title: str) -> PageRole:
        path = urlparse(url).path.lower().strip("/")
        path_segments = re.split(r"[/\-_]", path)

        # 1. URL path signals (highest specificity)
        for keywords, role in _URL_ROLE_SIGNALS:
            for segment in path_segments:
                if any(kw in segment for kw in keywords):
                    return role

        # 2. Title signals
        for keywords, role in _TITLE_ROLE_SIGNALS:
            if any(kw in title for kw in keywords):
                return role

        # 3. Root path → homepage
        if not path or path in {"", "/", "index.html", "index.htm"}:
            return PageRole.HOMEPAGE

        return PageRole.UNKNOWN

    @classmethod
    def _extract_domains(cls, text: str) -> List[str]:
        domains: List[str] = []
        for domain, signals in _DOMAIN_SIGNALS:
            if any(sig in text for sig in signals):
                domains.append(domain)
        return domains

    @classmethod
    def _extract_primary_entities(
        cls, page: PageEvidence, title: str, body: str
    ) -> List[str]:
        entities: List[str] = []
        # Extract from h1/h2 headings
        for heading in (page.h1 or []) + (page.h2 or []):
            h = heading.strip()
            if 3 < len(h) < 80:
                entities.append(h)
        # Extract capitalised noun phrases from title
        for match in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", page.title or ""):
            if match not in entities:
                entities.append(match)
        return entities[:10]
