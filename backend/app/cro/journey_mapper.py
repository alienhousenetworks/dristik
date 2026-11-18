"""
Website Journey Mapping Engine for CRO (Phase 6.2).

Constructs the visual conversion journey graph:
Entry Point -> Navigation & Discovery -> Product/Service Evaluation -> Cart/Form Action -> Conversion

Executes 10 Sub-phases:
1. Identify page entry points.
2. Detect primary navigation.
3. Extract clickable CTAs.
4. Identify conversion destinations.
5. Map forms and checkout steps.
6. Identify dead ends (pages with no forward paths).
7. Detect confusing navigation loops (cyclic A -> B -> A without action).
8. Record broken journeys (broken links, unhandled routes).
9. Identify secondary conversion paths.
10. Generate journey-level findings.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence, Finding, FindingEvidence, EvidenceRef
from app.domain.enums import Category, Severity, EvidenceClass


class JourneyNode(BaseModel):
    url: str
    path: str
    stage: str = "DISCOVERY" # "ENTRY", "DISCOVERY", "EVALUATION", "ACTION", "CONVERSION", "DEAD_END"
    title: str = ""
    is_entry_point: bool = False
    is_conversion_destination: bool = False
    is_dead_end: bool = False
    outgoing_cta_links: List[str] = Field(default_factory=list)
    outgoing_nav_links: List[str] = Field(default_factory=list)
    forms_present: int = 0
    primary_ctas: List[str] = Field(default_factory=list)


class JourneyEdge(BaseModel):
    source_url: str
    target_url: str
    interaction_type: str # "PRIMARY_CTA", "SECONDARY_CTA", "NAV_LINK", "FORM_SUBMIT"
    label: str = ""
    is_broken: bool = False
    is_loop: bool = False


class JourneyGraphResult(BaseModel):
    domain: str
    entry_points: List[str] = Field(default_factory=list)
    primary_nav_links: List[str] = Field(default_factory=list)
    conversion_destinations: List[str] = Field(default_factory=list)
    dead_ends: List[str] = Field(default_factory=list)
    navigation_loops: List[List[str]] = Field(default_factory=list)
    broken_journeys: List[Dict[str, str]] = Field(default_factory=list)
    secondary_paths: List[Dict[str, str]] = Field(default_factory=list)
    nodes: Dict[str, JourneyNode] = Field(default_factory=dict)
    edges: List[JourneyEdge] = Field(default_factory=list)
    stages_summary: Dict[str, int] = Field(default_factory=dict)
    journey_findings: List[Finding] = Field(default_factory=list)


class JourneyMapper:
    """Extracts, maps, and analyzes multi-step conversion journeys across crawled pages."""

    ENTRY_PATTERNS = re.compile(r"^https?://[^/]+/?$|/(landing|lp|welcome|start|campaign)", re.I)
    CONVERSION_PATTERNS = re.compile(r"/(cart|checkout|book|demo|contact|thank-you|success|confirmed|order|pricing|signup|register)", re.I)
    SECONDARY_PATTERNS = re.compile(r"/(newsletter|subscribe|resources|whitepaper|case-studies|blog|faq|about|docs)", re.I)

    @classmethod
    def map_journey(
        cls,
        pages: List[PageEvidence],
        raw_html_map: Optional[Dict[str, str]] = None,
        domain: str = "",
    ) -> JourneyGraphResult:
        raw_html_map = raw_html_map or {}
        nodes: Dict[str, JourneyNode] = {}
        all_links_map: Dict[str, Set[str]] = {}
        cta_map: Dict[str, List[Tuple[str, str]]] = {} # source_url -> [(target_url, cta_text)]
        primary_nav_set: Set[str] = set()

        # Phase 6.2.1 - 6.2.5: Extract node attributes, navigation, and CTAs
        for idx, page in enumerate(pages or []):
            url = page.url or f"page_{idx}"
            parsed = urlparse(url)
            path = parsed.path or "/"
            html = raw_html_map.get(url) or getattr(page, "raw_html", None) or ""
            soup = BeautifulSoup(html, "html.parser") if html else None

            # 1. Identify Entry Points
            is_entry = (idx == 0) or bool(cls.ENTRY_PATTERNS.search(url))

            # 2. Detect Primary Navigation
            nav_links = cls._extract_nav_links(soup, url)
            primary_nav_set.update(nav_links)

            # 3. Extract Clickable CTAs
            ctas_with_targets = cls._extract_ctas(soup, url, page)
            cta_map[url] = ctas_with_targets
            cta_texts = [txt for _, txt in ctas_with_targets]
            cta_targets = [tgt for tgt, _ in ctas_with_targets if tgt]

            # 4. Identify Conversion Destinations
            is_conv = bool(cls.CONVERSION_PATTERNS.search(url)) or getattr(page, "forms_count", 0) > 0

            # 5. Map Stage
            stage = cls._determine_stage(url, path, is_entry, is_conv, bool(cta_targets))

            node = JourneyNode(
                url=url,
                path=path,
                stage=stage,
                title=getattr(page, "title", "") or "",
                is_entry_point=is_entry,
                is_conversion_destination=is_conv,
                is_dead_end=False, # evaluated below
                outgoing_cta_links=cta_targets,
                outgoing_nav_links=list(nav_links),
                forms_present=getattr(page, "forms_count", 0),
                primary_ctas=cta_texts,
            )
            nodes[url] = node
            all_links_map[url] = set(cta_targets).union(nav_links)

        # 6. Identify Dead Ends (pages with 0 forward outgoing links/CTAs)
        dead_ends: List[str] = []
        for url, node in nodes.items():
            if not node.outgoing_cta_links and not node.outgoing_nav_links:
                node.is_dead_end = True
                node.stage = "DEAD_END"
                dead_ends.append(url)

        # 7. Detect Confusing Navigation Loops (A -> B -> A cycles without action)
        navigation_loops: List[List[str]] = []
        visited_pairs: Set[Tuple[str, str]] = set()
        for u1, targets in all_links_map.items():
            for u2 in targets:
                if u2 in all_links_map and u1 in all_links_map[u2] and u1 != u2:
                    pair = tuple(sorted([u1, u2]))
                    if pair not in visited_pairs:
                        visited_pairs.add(pair)
                        node1 = nodes.get(u1)
                        node2 = nodes.get(u2)
                        if (not node1 or not node1.is_conversion_destination) and (not node2 or not node2.is_conversion_destination):
                            navigation_loops.append([u1, u2])

        # 8. Record Broken Journeys (links to 404s or malformed anchors)
        known_urls = set(nodes.keys())
        broken_journeys: List[Dict[str, str]] = []
        for u, targets in all_links_map.items():
            for tgt in targets:
                if tgt.startswith("http") and urlparse(tgt).netloc == urlparse(u).netloc:
                    if tgt not in known_urls and "#" in tgt and tgt.split("#")[0] in known_urls:
                        # Malformed or missing anchor fragment
                        broken_journeys.append({
                            "source": u,
                            "target": tgt,
                            "reason": "Missing or unverified anchor ID in destination DOM",
                        })

        # 9. Identify Secondary Conversion Paths
        secondary_paths: List[Dict[str, str]] = []
        for u, node in nodes.items():
            for cta_tgt, cta_txt in cta_map.get(u, []):
                if cls.SECONDARY_PATTERNS.search(cta_tgt) or any(w in cta_txt.lower() for w in ("newsletter", "whitepaper", "guide", "download", "subscribe")):
                    secondary_paths.append({
                        "source": u,
                        "destination": cta_tgt,
                        "cta": cta_txt,
                        "type": "MICRO_CONVERSION",
                    })

        # Build Edges
        edges: List[JourneyEdge] = []
        for src, ctas in cta_map.items():
            for tgt, txt in ctas:
                if tgt:
                    is_loop = any(set([src, tgt]) == set(lp) for lp in navigation_loops)
                    edges.append(JourneyEdge(
                        source_url=src,
                        target_url=tgt,
                        interaction_type="PRIMARY_CTA",
                        label=txt,
                        is_broken=False,
                        is_loop=is_loop,
                    ))

        # 10. Generate Journey-Level Findings
        findings = cls._generate_journey_findings(dead_ends, navigation_loops, broken_journeys, nodes, domain)

        # Stage distribution
        stages_summary: Dict[str, int] = {}
        for n in nodes.values():
            stages_summary[n.stage] = stages_summary.get(n.stage, 0) + 1

        return JourneyGraphResult(
            domain=domain,
            entry_points=[n.url for n in nodes.values() if n.is_entry_point],
            primary_nav_links=list(primary_nav_set),
            conversion_destinations=[n.url for n in nodes.values() if n.is_conversion_destination],
            dead_ends=dead_ends,
            navigation_loops=navigation_loops,
            broken_journeys=broken_journeys,
            secondary_paths=secondary_paths,
            nodes=nodes,
            edges=edges,
            stages_summary=stages_summary,
            journey_findings=findings,
        )

    @classmethod
    def _extract_nav_links(cls, soup: Optional[BeautifulSoup], base_url: str) -> Set[str]:
        links = set()
        if not soup:
            return links
        for nav in soup.find_all(["nav", "header"]):
            for a in nav.find_all("a", href=True):
                href = a.get("href", "").strip()
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    full = urljoin(base_url, href)
                    links.add(full)
        return links

    @classmethod
    def _extract_ctas(cls, soup: Optional[BeautifulSoup], base_url: str, page: PageEvidence) -> List[Tuple[str, str]]:
        ctas = []
        if soup:
            for el in soup.find_all(["button", "a"]):
                txt = el.get_text(strip=True)
                classes = " ".join(el.get("class") or []).lower()
                href = el.get("href", "").strip() if el.name == "a" else ""
                is_cta_candidate = (
                    el.name == "button"
                    or "btn" in classes
                    or "button" in classes
                    or "cta" in classes
                    or any(k in txt.lower() for k in ("get started", "start", "buy", "order", "book", "demo", "pricing", "sign up", "contact"))
                )
                if is_cta_candidate and txt and len(txt) < 45:
                    target = urljoin(base_url, href) if href and not href.startswith(("#", "javascript:")) else ""
                    ctas.append((target, txt))
        if not ctas:
            for c in getattr(page, "ctas", None) or []:
                ctas.append(("", str(c).strip()))
        return ctas

    @classmethod
    def _determine_stage(cls, url: str, path: str, is_entry: bool, is_conv: bool, has_ctas: bool) -> str:
        if is_conv:
            return "CONVERSION"
        if is_entry:
            return "ENTRY"
        p_low = path.lower()
        if any(d in p_low for d in ("/product", "/service", "/feature", "/solution", "/compare", "/case-stud")):
            return "EVALUATION"
        if any(c in p_low for c in ("/shop", "/category", "/catalog", "/explore", "/collection")):
            return "DISCOVERY"
        return "DISCOVERY" if has_ctas else "ACTION"

    @classmethod
    def _generate_journey_findings(
        cls,
        dead_ends: List[str],
        loops: List[List[str]],
        broken: List[Dict[str, str]],
        nodes: Dict[str, JourneyNode],
        domain: str,
    ) -> List[Finding]:
        findings: List[Finding] = []

        if dead_ends:
            findings.append(Finding(
                finding_id="CRO-JOURNEY-001",
                title=f"Conversion Journey Dead End on {len(dead_ends)} Page(s)",
                description=f"Identified {len(dead_ends)} page(s) with no forward conversion CTAs or outbound navigational links, causing visitor abandonment.",
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                impact=3,
                effort=1,
                priority=1,
                recommendation="Introduce a persistent primary CTA and contextual secondary pathway on all terminal pages.",
                why_it_matters="When a visitor reaches a page with zero next steps, bounce and exit rates escalate, terminating the conversion funnel prematurely.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="JOURNEY_GRAPH",
                epistemic_level="Algorithmic graph traversal",
            ))

        if loops:
            findings.append(Finding(
                finding_id="CRO-JOURNEY-002",
                title=f"Cyclic Navigation Loop Detected ({len(loops)} Occurrence(s))",
                description=f"Visitors encounter circular navigational loops between pages ({', '.join(f'{urlparse(l[0]).path} <-> {urlparse(l[1]).path}' for l in loops[:3])}) without advancing toward conversion.",
                category=Category.UX_CONVERSION,
                severity=Severity.MEDIUM,
                impact=2,
                effort=1,
                priority=2,
                recommendation="Break circular reciprocal links with a distinguished primary conversion button and progressive breadcrumbs.",
                why_it_matters="Navigational loops disorient prospective buyers and increase cognitive load.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="JOURNEY_GRAPH",
                epistemic_level="Graph cycle detection",
            ))

        return findings


journey_mapper = JourneyMapper()
