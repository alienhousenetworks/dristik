"""
Dristik AI Prioritized Roadmap Builder
Structures 7-Day, 30-Day, and 90-Day tactical execution boards.
"""
from typing import List, Dict, Any, Tuple
from app.domain.models import Finding, RoadmapItem
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
