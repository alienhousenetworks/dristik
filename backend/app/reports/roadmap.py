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
        Synthesizes a prioritized Top 10 Actions execution matrix directly from
        verified audit findings (no fabricated actions when findings are absent).
        """
        sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        sev_to_priority = {"CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2", "LOW": "P3", "INFO": "P3"}
        sev_to_impact = {"CRITICAL": "Very High", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low", "INFO": "Low"}
        effort_hours = {"LOW": 2, "MEDIUM": 4, "HIGH": 8}

        active_findings = [f for f in (findings or []) if not getattr(f, "held_from_executive", False)]
        ordered = sorted(
            active_findings,
            key=lambda f: (
                sev_rank.get(str(getattr(getattr(f, "severity", None), "value", getattr(f, "severity", "MEDIUM"))).upper(), 2),
                str(getattr(f, "finding_id", "")),
            ),
        )[:10]

        actions: List[ExecutiveActionItem] = []
        for idx, f in enumerate(ordered, start=1):
            sev_str = str(getattr(getattr(f, "severity", None), "value", getattr(f, "severity", "MEDIUM"))).upper()
            eff_str = str(getattr(getattr(f, "effort", None), "value", getattr(f, "effort", "MEDIUM"))).upper()
            ver_steps = getattr(f, "verification_steps", None) or []
            validation = ver_steps[0] if ver_steps else f"Retest {getattr(f, 'affected_url', None) or 'affected URLs'} to verify remediation."
            actions.append(
                ExecutiveActionItem(
                    rank=idx,
                    priority=sev_to_priority.get(sev_str, "P2"),
                    action=getattr(f, "recommended_action", None) or getattr(f, "title", None) or f.finding,
                    impact=sev_to_impact.get(sev_str, "Medium"),
                    effort=eff_str.title() if eff_str else "Medium",
                    expected_outcome=getattr(f, "impact_explanation", None) or getattr(f, "description", None) or "Resolves verified audit defect.",
                    estimated_engineer_hours=effort_hours.get(eff_str, 4),
                    dependencies=[],
                    validation=validation,
                    category=getattr(f, "category", Category.TECHNICAL_SEO),
                    related_finding_id=getattr(f, "finding_id", None),
                )
            )

        total_hours = sum(a.estimated_engineer_hours for a in actions)
        dependencies_flow = " → ".join(a.action[:40] for a in actions[:4]) if actions else "No remediation actions required."

        return ExecutiveTopActionsPlan(
            actions=actions,
            total_engineer_hours=total_hours,
            dependencies_flow=dependencies_flow,
            validation_mode="automated_retest",
        )
