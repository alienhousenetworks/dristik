"""
Dristik KIE — Phase 2: Website Knowledge Graph
Builds the relational entity graph from extracted claims and page classifications.
Connects: Company → offers → Service, Product → integrates_with → Technology,
Company → claims_certification → Compliance, Company → serves → Industry, etc.

Also includes the Contradiction Engine: detects cross-page knowledge conflicts
(ICP size, pricing inconsistencies, headcount drift, feature deprecations).
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.domain.models import PageEvidence
from app.intelligence.knowledge.primitives import (
    AtomicClaim,
    ContradictionItem,
    EntityNode,
    EntityRelationship,
    KieClaimType,
    KieEvidenceState,
    KnowledgeSourceTier,
    PageKnowledgeClassification,
    PageRole,
)
from app.intelligence.knowledge.claim_extractor import AtomicClaimExtractor
from app.intelligence.knowledge.page_classifier import PageKnowledgeClassifier


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Graph Model
# ─────────────────────────────────────────────────────────────────────────────

class WebsiteKnowledgeGraph:
    """
    First-party website knowledge graph built from crawled DOM.
    Nodes = Entities (Company, Product, Service, Technology, Certification, Location)
    Edges = Relationships (offers, integrates_with, serves, claims_certification, located_at)

    Provides the authoritative knowledge source for the KIE Query Planner and
    Grounded Answer Simulator. External/third-party knowledge is tracked separately.
    """

    def __init__(self, brand: str, domain: str):
        self.brand = brand
        self.domain = domain
        self.entities: Dict[str, EntityNode] = {}
        self.relationships: List[EntityRelationship] = []
        self.claims: List[AtomicClaim] = []
        self.page_classifications: List[PageKnowledgeClassification] = []
        self.contradictions: List[ContradictionItem] = []
        self._root_entity_id = self._add_entity(brand, "Organization")

    # ── Build ────────────────────────────────────────────────────────────────

    def build_from_pages(self, pages: List[PageEvidence]) -> "WebsiteKnowledgeGraph":
        """
        Full pipeline: classify pages → extract claims → build entity/rel graph
        → run contradiction engine.
        """
        self.page_classifications = PageKnowledgeClassifier.classify_all(pages)
        extractor = AtomicClaimExtractor(brand=self.brand)
        self.claims = extractor.extract_from_pages(pages)
        self._build_entity_graph()
        self._run_contradiction_engine()
        return self

    # ── Entity & Relationship Helpers ────────────────────────────────────────

    def _add_entity(self, name: str, category: str) -> str:
        eid = f"ENT_{uuid.uuid4().hex[:8].upper()}"
        self.entities[eid] = EntityNode(
            entity_id=eid,
            name=name,
            category=category,
            knowledge_tier=KnowledgeSourceTier.FIRST_PARTY,
        )
        return eid

    def _find_or_create_entity(self, name: str, category: str) -> str:
        name_l = name.lower()
        for eid, node in self.entities.items():
            if node.name.lower() == name_l and node.category == category:
                return eid
        return self._add_entity(name, category)

    def _add_relationship(
        self,
        source_id: str,
        target_id: str,
        predicate: str,
        provenance_url: Optional[str] = None,
    ) -> None:
        self.relationships.append(EntityRelationship(
            relationship_id=f"REL_{uuid.uuid4().hex[:8].upper()}",
            source_entity_id=source_id,
            target_entity_id=target_id,
            predicate=predicate,
            provenance_url=provenance_url,
        ))

    # ── Graph Construction from Claims ───────────────────────────────────────

    _TECH_PATTERNS = re.compile(
        r"\b(react|vue|angular|django|flask|fastapi|node\.?js|python|typescript|"
        r"kubernetes|docker|aws|gcp|azure|postgres|mysql|mongodb|redis|"
        r"elasticsearch|graphql|rest api|webhooks?|stripe|sendgrid|zapier|"
        r"okta|auth0|salesforce|hubspot|segment|amplitude)\b",
        re.IGNORECASE,
    )
    _CERT_PATTERNS = re.compile(
        r"\b(soc\s*2(?:\s+type\s*ii?)?|iso\s*27001|hipaa|gdpr|ccpa|pci[- ]dss|"
        r"fedramp|aicpa|csa\s+star)\b",
        re.IGNORECASE,
    )
    _SERVICE_PATTERNS = re.compile(
        r"\b([A-Z][a-zA-Z\s]{3,40}(?:Development|Services?|Consulting|"
        r"Integration|Platform|Solution|Analytics|Automation|Management))\b"
    )
    _INDUSTRY_PATTERNS = re.compile(
        r"\b(fintech|healthtech|edtech|proptech|legaltech|insurtech|"
        r"saas|b2b|b2c|healthcare|finance|banking|insurance|"
        r"retail|ecommerce|logistics|manufacturing|real estate|"
        r"education|government|energy|media)\b",
        re.IGNORECASE,
    )

    def _build_entity_graph(self) -> None:
        seen_tech: set = set()
        seen_certs: set = set()
        seen_industries: set = set()
        seen_services: set = set()

        for claim in self.claims:
            combined = f"{claim.predicate} {claim.object}".lower()
            url = claim.evidence.url if claim.evidence else None

            # Technologies / integrations
            for m in self._TECH_PATTERNS.finditer(combined):
                tech_name = m.group(0).strip()
                if tech_name.lower() not in seen_tech:
                    seen_tech.add(tech_name.lower())
                    tech_id = self._find_or_create_entity(tech_name, "Technology")
                    self._add_relationship(
                        self._root_entity_id, tech_id, "uses_technology", url
                    )

            # Certifications
            for m in self._CERT_PATTERNS.finditer(combined):
                cert_name = m.group(0).strip().upper()
                if cert_name not in seen_certs:
                    seen_certs.add(cert_name)
                    cert_id = self._find_or_create_entity(cert_name, "Certification")
                    self._add_relationship(
                        self._root_entity_id, cert_id, "claims_certification", url
                    )

            # Industries served
            for m in self._INDUSTRY_PATTERNS.finditer(combined):
                ind = m.group(0).lower()
                if ind not in seen_industries:
                    seen_industries.add(ind)
                    ind_id = self._find_or_create_entity(ind.title(), "Industry")
                    self._add_relationship(
                        self._root_entity_id, ind_id, "serves_industry", url
                    )

            # Named services
            if claim.claim_type in (KieClaimType.CAPABILITY, KieClaimType.FACT):
                for m in self._SERVICE_PATTERNS.finditer(claim.object):
                    svc_name = m.group(0).strip()[:60]
                    if svc_name.lower() not in seen_services and len(svc_name) < 50:
                        seen_services.add(svc_name.lower())
                        svc_id = self._find_or_create_entity(svc_name, "Service")
                        self._add_relationship(
                            self._root_entity_id, svc_id, "offers", url
                        )

    # ── Contradiction Engine ──────────────────────────────────────────────────

    _ICP_SIZE_PATTERN = re.compile(
        r"(\d{1,6})\+?\s*(?:employees?|team\s+members?|people|staff|headcount)",
        re.IGNORECASE,
    )
    _PRICING_AMOUNT_PATTERN = re.compile(
        r"(?:starting|from|begins?\s+at|as\s+low\s+as)?\s*[\$€£₹]?\s*(\d[\d,]*)",
        re.IGNORECASE,
    )
    _EMPLOYEE_COUNT_PATTERN = re.compile(
        r"(\d{1,5})\+?\s*(?:employees?|team\s+members?|people)",
        re.IGNORECASE,
    )

    def _run_contradiction_engine(self) -> None:
        """
        Scans extracted claims across pages to detect:
        1. ICP / target headcount inconsistency
        2. Pricing-start discrepancy
        3. Employee count drift
        """
        url_to_claims: Dict[str, List[AtomicClaim]] = defaultdict(list)
        for c in self.claims:
            if c.evidence:
                url_to_claims[c.evidence.url].append(c)

        # Gather per-page signals
        per_page_sizes: List[Tuple[str, int]] = []
        per_page_pricing: List[Tuple[str, int]] = []
        per_page_employee: List[Tuple[str, int]] = []

        for url, page_claims in url_to_claims.items():
            full_text = " ".join(c.object for c in page_claims)

            for m in self._ICP_SIZE_PATTERN.finditer(full_text):
                per_page_sizes.append((url, int(m.group(1))))

            for m in self._PRICING_AMOUNT_PATTERN.finditer(full_text):
                num = int(m.group(1).replace(",", ""))
                if 1 < num < 1_000_000:
                    per_page_pricing.append((url, num))

            for m in self._EMPLOYEE_COUNT_PATTERN.finditer(full_text):
                per_page_employee.append((url, int(m.group(1))))

        # ICP size inconsistency
        if len(per_page_sizes) >= 2:
            min_url, min_val = min(per_page_sizes, key=lambda x: x[1])
            max_url, max_val = max(per_page_sizes, key=lambda x: x[1])
            if max_val / max(1, min_val) > 3:
                self.contradictions.append(ContradictionItem(
                    contradiction_id=f"CONTR_{uuid.uuid4().hex[:6].upper()}",
                    topic="ICP Headcount / Target Size",
                    claim_a_text=f"Target company size stated as {min_val}+ employees",
                    claim_b_text=f"Target company size stated as {max_val}+ employees",
                    source_url_a=min_url,
                    source_url_b=max_url,
                    severity="MODERATE",
                    explanation=(
                        f"ICP targeting inconsistency: one page implies companies of {min_val}+ employees, "
                        f"while another implies {max_val}+. AI answer engines may report conflicting audience signals."
                    ),
                ))

        # Pricing start discrepancy (>3x spread)
        if len(per_page_pricing) >= 2:
            min_url, min_p = min(per_page_pricing, key=lambda x: x[1])
            max_url, max_p = max(per_page_pricing, key=lambda x: x[1])
            if min_p > 0 and max_p / min_p > 5 and min_url != max_url:
                self.contradictions.append(ContradictionItem(
                    contradiction_id=f"CONTR_{uuid.uuid4().hex[:6].upper()}",
                    topic="Pricing Start Discrepancy",
                    claim_a_text=f"Starting price mentioned as {min_p}",
                    claim_b_text=f"Starting price mentioned as {max_p}",
                    source_url_a=min_url,
                    source_url_b=max_url,
                    severity="CRITICAL",
                    explanation=(
                        f"Pricing signals conflict: {min_url} implies starting at {min_p}, "
                        f"while {max_url} implies {max_p}. "
                        f"This creates commercial confusion for buyers and may trigger AI hallucination."
                    ),
                ))

        # Employee count drift
        if len(per_page_employee) >= 2:
            min_url, min_e = min(per_page_employee, key=lambda x: x[1])
            max_url, max_e = max(per_page_employee, key=lambda x: x[1])
            if max_e / max(1, min_e) > 2 and min_url != max_url:
                self.contradictions.append(ContradictionItem(
                    contradiction_id=f"CONTR_{uuid.uuid4().hex[:6].upper()}",
                    topic="Organization Size / Headcount Drift",
                    claim_a_text=f"Company described as {min_e} employees",
                    claim_b_text=f"Company described as {max_e} employees",
                    source_url_a=min_url,
                    source_url_b=max_url,
                    severity="LOW",
                    explanation=(
                        f"Organization size stated as {min_e} on one page and {max_e} on another. "
                        f"External directories or AI may combine these into a contradictory entity profile."
                    ),
                ))

    # ── Query Interface ───────────────────────────────────────────────────────

    def get_claims_for_facet(self, facet_keywords: List[str]) -> List[AtomicClaim]:
        """Return claims relevant to a given query facet by keyword overlap."""
        results = []
        kws = [k.lower() for k in facet_keywords]
        for c in self.claims:
            combined = f"{c.predicate} {c.object}".lower()
            if any(k in combined for k in kws):
                results.append(c)
        return results

    def get_entities_by_category(self, category: str) -> List[EntityNode]:
        return [n for n in self.entities.values() if n.category == category]

    def get_relationships_for_entity(self, entity_id: str) -> List[EntityRelationship]:
        return [r for r in self.relationships if r.source_entity_id == entity_id]

    def summary(self) -> Dict:
        return {
            "brand": self.brand,
            "domain": self.domain,
            "total_pages_classified": len(self.page_classifications),
            "total_claims_extracted": len(self.claims),
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "total_contradictions": len(self.contradictions),
            "entity_categories": dict(
                (cat, sum(1 for n in self.entities.values() if n.category == cat))
                for cat in set(n.category for n in self.entities.values())
            ),
        }
