"""
Dristik AI Prioritized Roadmap Builder
Structures 7-Day, 30-Day, and 90-Day tactical execution boards.
"""
from typing import List, Dict, Any, Tuple, Optional
from app.domain.models import Finding, RoadmapItem, ExecutiveActionItem, ExecutiveTopActionsPlan, BusinessProfile, OverallScoreResult
from app.domain.enums import Category

def _resolve_owner(category: Any) -> str:
    cat_str = str(getattr(category, "value", category) or "").upper()
    if any(k in cat_str for k in ("TECHNICAL", "CRAWL", "SECURITY", "HOST")):
        return "DevOps / Technical SEO Lead"
    if "SCHEMA" in cat_str:
        return "Full-Stack Engineer"
    if any(k in cat_str for k in ("CONTENT", "E_E_A_T")):
        return "Senior Content Strategist"
    if any(k in cat_str for k in ("GEO", "AEO", "AI_SEARCH")):
        return "AI Visibility & Knowledge Engineer"
    if any(k in cat_str for k in ("UX", "CONVERSION", "CRO")):
        return "Product UX / Frontend Lead"
    if "COMPETITIVE" in cat_str:
        return "Growth Marketing Lead"
    return "Technical Lead"

def _resolve_hours(effort: Any) -> str:
    eff_val = 3
    if isinstance(effort, (int, float)):
        eff_val = int(effort)
    elif str(effort).lower() == "low":
        eff_val = 2
    elif str(effort).lower() == "medium":
        eff_val = 5
    elif str(effort).lower() == "high":
        eff_val = 8
    if eff_val <= 3:
        return "2–4 hours"
    elif eff_val <= 6:
        return "1–2 days"
    return "3–5 days"

def _resolve_verification(f: Finding) -> str:
    if getattr(f, "verification_method", None):
        return str(f.verification_method).strip()
    return f"Re-test affected URLs and verify resolution against automated validation gate (Ref: {f.finding_id})."

class RoadmapBuilder:
    def build_roadmap(self, findings: List[Finding], synthesizer_roadmap: Dict[str, Any]) -> Tuple[List[RoadmapItem], List[RoadmapItem], List[RoadmapItem]]:
        r7: List[RoadmapItem] = []
        r30: List[RoadmapItem] = []
        r90: List[RoadmapItem] = []

        # Sort findings by technical priority and severity
        sev_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        sorted_findings = sorted(
            findings,
            key=lambda x: (
                sev_weights.get(str(getattr(getattr(x, "severity", ""), "value", getattr(x, "severity", ""))).upper(), 0),
                getattr(x, "priority", 0)
            ),
            reverse=True
        )

        seen_finding_ids = set()
        for f in sorted_findings:
            if f.finding_id in seen_finding_ids:
                continue
            seen_finding_ids.add(f.finding_id)

            owner = _resolve_owner(f.category)
            hours = _resolve_hours(f.effort)
            verification = _resolve_verification(f)
            rec_desc = f.recommendation or f.finding or f.title

            if f.priority >= 8 or str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))).upper() in ["CRITICAL", "HIGH"]:
                r7.append(RoadmapItem(
                    timeframe="7_days",
                    title=f.title,
                    description=rec_desc,
                    impact="High",
                    effort="Low" if f.effort <= 4 else "Medium",
                    category=f.category,
                    related_finding_id=f.finding_id,
                    owner_role=owner,
                    estimated_hours=hours,
                    verification_step=verification,
                    priority_badge="P0 Blocker"
                ))
            elif f.priority >= 5 or str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))).upper() == "MEDIUM":
                r30.append(RoadmapItem(
                    timeframe="30_days",
                    title=f.title,
                    description=rec_desc,
                    impact="Medium",
                    effort="Medium",
                    category=f.category,
                    related_finding_id=f.finding_id,
                    owner_role=owner,
                    estimated_hours=hours,
                    verification_step=verification,
                    priority_badge="P1 Sprint Priority"
                ))
            else:
                r90.append(RoadmapItem(
                    timeframe="90_days",
                    title=f.title,
                    description=rec_desc,
                    impact="Medium",
                    effort="High",
                    category=f.category,
                    related_finding_id=f.finding_id,
                    owner_role=owner,
                    estimated_hours=hours,
                    verification_step=verification,
                    priority_badge="P2 Strategic Architecture"
                ))

        # Augment with synthesizer items if lists are sparse
        synth_r7 = synthesizer_roadmap.get("roadmap_7_days", [])
        if len(r7) < 3 and synth_r7:
            for item in synth_r7:
                if isinstance(item, dict) and item.get("title") and item.get("description"):
                    r7.append(RoadmapItem(
                        timeframe="7_days",
                        title=str(item["title"]).strip(),
                        description=str(item["description"]).strip(),
                        impact=item.get("impact", "High"),
                        effort=item.get("effort", "Low"),
                        category=Category.SCHEMA,
                        owner_role="Technical SEO Lead",
                        estimated_hours="2–4 hours",
                        verification_step="Automated retest on schema validation suite.",
                        priority_badge="P0 Blocker"
                    ))

        synth_r30 = synthesizer_roadmap.get("roadmap_30_days", [])
        if len(r30) < 3 and synth_r30:
            for item in synth_r30:
                if isinstance(item, dict) and item.get("title") and item.get("description"):
                    r30.append(RoadmapItem(
                        timeframe="30_days",
                        title=str(item["title"]).strip(),
                        description=str(item["description"]).strip(),
                        impact=item.get("impact", "High"),
                        effort=item.get("effort", "Medium"),
                        category=Category.AI_SEARCH,
                        owner_role="AI Visibility Engineer",
                        estimated_hours="1–2 days",
                        verification_step="Re-query AI Search simulation and verify quotation rate.",
                        priority_badge="P1 Sprint Priority"
                    ))

        synth_r90 = synthesizer_roadmap.get("roadmap_90_days", [])
        if len(r90) < 3 and synth_r90:
            for item in synth_r90:
                if isinstance(item, dict) and item.get("title") and item.get("description"):
                    r90.append(RoadmapItem(
                        timeframe="90_days",
                        title=str(item["title"]).strip(),
                        description=str(item["description"]).strip(),
                        impact=item.get("impact", "High"),
                        effort=item.get("effort", "High"),
                        category=Category.CONTENT,
                        owner_role="Content Strategist",
                        estimated_hours="3–5 days",
                        verification_step="Verify topic depth score and E-E-A-T signals.",
                        priority_badge="P2 Strategic Architecture"
                    ))

        return r7[:8], r30[:8], r90[:8]

    def build_top_10_actions(
        self,
        findings: List[Finding],
        business_profile: Optional[BusinessProfile] = None,
        scores: Optional[OverallScoreResult] = None,
        narrative: Optional[Dict[str, Any]] = None,
        crawl_summary: Optional[Dict[str, Any]] = None,
    ) -> ExecutiveTopActionsPlan:
        """
        Synthesizes a prioritized, defensible Top 10 Actions execution matrix for leadership.
        Format: Priority (P0, P1, P2), Action, Impact, Effort, Expected outcome,
        Estimated engineer-hours, Dependencies flow, and Automated retest criteria.
        """
        # Find related finding references by theme
        findings_map: Dict[str, Finding] = {}
        for f in findings:
            lowered = (f.title + " " + f.finding + " " + (f.description or "")).lower()
            if "h1" in lowered or "positioning" in lowered or "headline" in lowered:
                findings_map.setdefault("positioning", f)
            if "taxonomy" in lowered or "service" in lowered or "entity" in lowered:
                findings_map.setdefault("taxonomy", f)
            if "schema" in lowered or "json-ld" in lowered or "structured data" in lowered:
                findings_map.setdefault("schema", f)
            if "duplicate" in lowered or "canonical" in lowered or "meta" in lowered:
                findings_map.setdefault("duplicate_meta", f)
            if "icp" in lowered or "audience" in lowered or "conversion" in lowered:
                findings_map.setdefault("icp", f)
            if "case study" in lowered or "trust" in lowered or "proof" in lowered or "testimonial" in lowered:
                findings_map.setdefault("trust", f)
            if "sitemap" in lowered or "robots" in lowered or "crawl" in lowered:
                findings_map.setdefault("crawl", f)
            if "answer" in lowered or "faq" in lowered or "question" in lowered or "citation" in lowered:
                findings_map.setdefault("answerability", f)
            if "vitals" in lowered or "ttfb" in lowered or "speed" in lowered or "performance" in lowered:
                findings_map.setdefault("performance", f)
            if "hierarchy" in lowered or "heading" in lowered or "h2" in lowered or "structure" in lowered:
                findings_map.setdefault("hierarchy", f)

        # Standard institutional actions with intent & finding tuning
        actions: List[ExecutiveActionItem] = [
            ExecutiveActionItem(
                rank=1,
                priority="P0",
                action="Define service taxonomy",
                impact="Very High",
                effort="Low",
                expected_outcome="Category clarity & unambiguous entity mapping",
                estimated_engineer_hours=4,
                dependencies=[],
                validation="Automated retest: Taxonomy terms registered in DOM AST and canonical paths",
                category=Category.GEO,
                related_finding_id=findings_map.get("taxonomy", {}).finding_id if findings_map.get("taxonomy") else None,
            ),
            ExecutiveActionItem(
                rank=2,
                priority="P0",
                action="Rewrite homepage positioning",
                impact="Very High",
                effort="Low",
                expected_outcome="Improve visitor comprehension & instant value recognition",
                estimated_engineer_hours=3,
                dependencies=[],
                validation="Automated retest: Homepage H1 & title contain explicit service category",
                category=Category.UX_CONVERSION,
                related_finding_id=findings_map.get("positioning", {}).finding_id if findings_map.get("positioning") else None,
            ),
            ExecutiveActionItem(
                rank=3,
                priority="P1",
                action="Create service schema",
                impact="High",
                effort="Medium",
                expected_outcome="Better entity understanding & AI knowledge graph ingestion",
                estimated_engineer_hours=5,
                dependencies=["Define service taxonomy"],
                validation="Automated retest: Schema Validator verifies valid Service & Organization JSON-LD",
                category=Category.SCHEMA,
                related_finding_id=findings_map.get("schema", {}).finding_id if findings_map.get("schema") else None,
            ),
            ExecutiveActionItem(
                rank=4,
                priority="P1",
                action="Fix metadata duplication",
                impact="High",
                effort="Low",
                expected_outcome="Better page differentiation & clean SERP snippets",
                estimated_engineer_hours=3,
                dependencies=[],
                validation="Automated retest: 100% unique <title> and meta descriptions across crawled URLs",
                category=Category.ON_PAGE_SEO,
                related_finding_id=findings_map.get("duplicate_meta", {}).finding_id if findings_map.get("duplicate_meta") else None,
            ),
            ExecutiveActionItem(
                rank=5,
                priority="P1",
                action="Add ICP landing pages",
                impact="High",
                effort="Medium",
                expected_outcome="Better commercial qualification & dedicated intent routes",
                estimated_engineer_hours=6,
                dependencies=["Define service taxonomy"],
                validation="Automated retest: Target ICP paths return HTTP 200 with >400 words depth",
                category=Category.CONTENT,
                related_finding_id=findings_map.get("icp", {}).finding_id if findings_map.get("icp") else None,
            ),
            ExecutiveActionItem(
                rank=6,
                priority="P1",
                action="Add case studies & proof points",
                impact="High",
                effort="Medium",
                expected_outcome="Trust validation & decision confidence",
                estimated_engineer_hours=5,
                dependencies=["Add ICP landing pages"],
                validation="Automated retest: Social proof elements and quantifiable metrics identified",
                category=Category.TRUST_AUTHORITY,
                related_finding_id=findings_map.get("trust", {}).finding_id if findings_map.get("trust") else None,
            ),
            ExecutiveActionItem(
                rank=7,
                priority="P2",
                action="Configure sitemap & robots directives",
                impact="Medium",
                effort="Low",
                expected_outcome="Crawlability & zero index waste",
                estimated_engineer_hours=2,
                dependencies=[],
                validation="Automated retest: robots.txt allows AI/search bots; sitemap.xml returns 200",
                category=Category.TECHNICAL_SEO,
                related_finding_id=findings_map.get("crawl", {}).finding_id if findings_map.get("crawl") else None,
            ),
            ExecutiveActionItem(
                rank=8,
                priority="P2",
                action="Format structured Q&A for answer engines",
                impact="High",
                effort="Medium",
                expected_outcome="AI Search citation readiness & snippet extraction",
                estimated_engineer_hours=4,
                dependencies=["Define service taxonomy"],
                validation="Automated retest: FAQPage schema or semantic Q&A blocks verified in AST",
                category=Category.AI_SEARCH,
                related_finding_id=findings_map.get("answerability", {}).finding_id if findings_map.get("answerability") else None,
            ),
            ExecutiveActionItem(
                rank=9,
                priority="P2",
                action="Remediate TTFB & Core Web Vitals bottlenecks",
                impact="Medium",
                effort="Medium",
                expected_outcome="Page experience & crawl budget optimization",
                estimated_engineer_hours=4,
                dependencies=[],
                validation="Automated retest: Server response TTFB < 400ms across tested endpoints",
                category=Category.TECHNICAL_SEO,
                related_finding_id=findings_map.get("performance", {}).finding_id if findings_map.get("performance") else None,
            ),
            ExecutiveActionItem(
                rank=10,
                priority="P2",
                action="Standardize semantic heading hierarchy",
                impact="Medium",
                effort="Low",
                expected_outcome="Content scannability & assistive parsing integrity",
                estimated_engineer_hours=2,
                dependencies=[],
                validation="Automated retest: DOM heading tree has single H1 and sequential H2/H3 levels",
                category=Category.ON_PAGE_SEO,
                related_finding_id=findings_map.get("hierarchy", {}).finding_id if findings_map.get("hierarchy") else None,
            ),
        ]

        total_hours = sum(a.estimated_engineer_hours for a in actions)
        dependencies_flow = "Define service taxonomy → Create service schema → Add ICP landing pages → Add case studies"

        return ExecutiveTopActionsPlan(
            actions=actions,
            total_engineer_hours=total_hours,
            dependencies_flow=dependencies_flow,
            validation_mode="automated_retest",
        )
