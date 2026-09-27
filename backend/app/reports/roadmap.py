"""
Dristik AI Prioritized Roadmap Builder
Structures 7-Day, 30-Day, and 90-Day tactical execution boards.
"""
from typing import List, Dict, Any, Tuple, Optional
from app.domain.models import Finding, RoadmapItem, ExecutiveActionItem, ExecutiveTopActionsPlan, BusinessProfile, OverallScoreResult
from app.domain.enums import Category

class RoadmapBuilder:
    def build_roadmap(self, findings: List[Finding], synthesizer_roadmap: Dict[str, Any]) -> Tuple[List[RoadmapItem], List[RoadmapItem], List[RoadmapItem]]:
        r7: List[RoadmapItem] = []
        r30: List[RoadmapItem] = []
        r90: List[RoadmapItem] = []
        
        # 1. First populate from high-priority verified findings
        for f in findings:
            if f.priority >= 8 or f.severity in ["CRITICAL", "HIGH"]:
                r7.append(RoadmapItem(
                    timeframe="7_days",
                    title=f.title,
                    description=f.recommendation,
                    impact="High",
                    effort="Low" if f.effort <= 4 else "Medium",
                    category=f.category,
                    related_finding_id=f.finding_id
                ))
            elif f.priority >= 5 or f.severity == "MEDIUM":
                r30.append(RoadmapItem(
                    timeframe="30_days",
                    title=f.title,
                    description=f.recommendation,
                    impact="Medium",
                    effort="Medium",
                    category=f.category,
                    related_finding_id=f.finding_id
                ))
            else:
                r90.append(RoadmapItem(
                    timeframe="90_days",
                    title=f.title,
                    description=f.recommendation,
                    impact="Medium",
                    effort="High",
                    category=f.category,
                    related_finding_id=f.finding_id
                ))
                
        # 2. Augment with synthesizer items if lists are sparse
        synth_r7 = synthesizer_roadmap.get("roadmap_7_days", [])
        if len(r7) < 2 and synth_r7:
            for item in synth_r7:
                r7.append(RoadmapItem(
                    timeframe="7_days",
                    title=item.get("title", "Quick Win"),
                    description=item.get("description", "Execute immediate high-ROI architectural fix."),
                    impact=item.get("impact", "High"),
                    effort=item.get("effort", "Low"),
                    category=Category.SCHEMA
                ))
                
        synth_r30 = synthesizer_roadmap.get("roadmap_30_days", [])
        if len(r30) < 2 and synth_r30:
            for item in synth_r30:
                r30.append(RoadmapItem(
                    timeframe="30_days",
                    title=item.get("title", "30-Day Milestone"),
                    description=item.get("description", "Implement structured answerability & friction reduction."),
                    impact=item.get("impact", "High"),
                    effort=item.get("effort", "Medium"),
                    category=Category.AI_SEARCH
                ))
                
        synth_r90 = synthesizer_roadmap.get("roadmap_90_days", [])
        if len(r90) < 2 and synth_r90:
            for item in synth_r90:
                r90.append(RoadmapItem(
                    timeframe="90_days",
                    title=item.get("title", "Strategic Initiative"),
                    description=item.get("description", "Build comprehensive topic cluster architecture and authority moat."),
                    impact=item.get("impact", "High"),
                    effort=item.get("effort", "High"),
                    category=Category.CONTENT
                ))
                
        return r7[:5], r30[:5], r90[:5]

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
