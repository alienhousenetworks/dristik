"""
Dristik AI GEO Real-Time Competitor Displacement Sentinel & Alerting Engine.
Tracks rank drops, citation losses, and competitor conquesting across historical snapshot runs.
Generates structured displacement alert feeds and severity-scored triage items.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DisplacementAlert(BaseModel):
    alert_id: str
    timestamp: str
    engine_id: str
    engine_name: str
    query_id: str
    query_text: str
    category: str
    previous_rank: Optional[int] = None
    new_rank: Optional[int] = None
    displaced_by_competitors: List[str] = Field(default_factory=list)
    citation_lost_urls: List[str] = Field(default_factory=list)
    severity: str = "MAJOR"  # CRITICAL | MAJOR | MINOR | OPPORTUNITY
    impact_summary: str
    recommended_patch: str


class DisplacementAnalysisResult(BaseModel):
    target_domain: str
    brand_name: str
    total_queries_compared: int
    net_displacement_score: int  # Positive means gains, negative means net losses
    displacements_suffered: int
    conquests_achieved: int
    critical_alerts: List[DisplacementAlert] = Field(default_factory=list)
    all_alerts: List[DisplacementAlert] = Field(default_factory=list)


class DisplacementSentinel:
    """
    Compares two evaluated query run sets (e.g. Baseline vs Current) to isolate
    displacement events where competitors stole visibility or citations.
    """

    def detect_displacements(
        self,
        baseline_evaluations: List[Any],
        current_evaluations: List[Any],
        target_brand: str,
        target_domain: str,
        competitors: Optional[List[str]] = None
    ) -> DisplacementAnalysisResult:
        brand_clean = target_brand.strip().lower()
        comps_original = [c.strip() for c in (competitors or []) if c and c.strip()]

        # Map by (query_id, engine_id)
        base_map: Dict[str, Any] = {}
        for r in baseline_evaluations:
            key = f"{getattr(r, 'query_id', '')}::{getattr(r, 'engine_id', '')}"
            base_map[key] = r

        curr_map: Dict[str, Any] = {}
        for r in current_evaluations:
            key = f"{getattr(r, 'query_id', '')}::{getattr(r, 'engine_id', '')}"
            curr_map[key] = r

        common_keys = set(base_map.keys()).intersection(set(curr_map.keys()))
        alerts: List[DisplacementAlert] = []
        losses = 0
        gains = 0

        now_str = datetime.now(timezone.utc).isoformat()

        for key in common_keys:
            base_run = base_map[key]
            curr_run = curr_map[key]

            base_pos = getattr(base_run, "mention_position", None)
            curr_pos = getattr(curr_run, "mention_position", None)
            base_cited = getattr(base_run, "was_first_party_cited", False)
            curr_cited = getattr(curr_run, "was_first_party_cited", False)

            q_text = getattr(curr_run, "query_text", "")
            q_id = getattr(curr_run, "query_id", "")
            eng_id = getattr(curr_run, "engine_id", "generic")
            eng_name = getattr(curr_run, "engine_name", eng_id.capitalize())
            cat = getattr(curr_run, "category", "general")

            # Check who is mentioned in curr_run
            curr_text = (getattr(curr_run, "raw_response", "") or "").lower()
            rivals_present = [c for c in comps_original if c.lower() in curr_text]

            # Case A: We dropped rank or lost mention entirely
            is_loss = False
            severity = "MINOR"
            impact = ""
            action = ""

            if base_pos is not None and (curr_pos is None or curr_pos > base_pos):
                is_loss = True
                losses += 1
                if base_pos == 1:
                    severity = "CRITICAL"
                    impact = f"Lost Rank #1 position on {eng_name} to {', '.join(rivals_present) or 'rivals'}."
                    action = "Deploy inverted-pyramid 50-word answer block to reclaim top recommendation."
                elif base_pos <= 3:
                    severity = "MAJOR"
                    impact = f"Fell from top-3 recommendation (Rank {base_pos}) to Rank {curr_pos or 'Unmentioned'}."
                    action = "Update Schema.org FAQ markup and citation proof points."
                else:
                    severity = "MINOR"
                    impact = f"Minor position drop from Rank {base_pos} to Rank {curr_pos or 'unranked'}."
                    action = "Monitor query performance on subsequent pulse runs."

            elif base_cited and not curr_cited:
                is_loss = True
                losses += 1
                severity = "MAJOR"
                impact = f"First-party citation URL was dropped by {eng_name}."
                action = f"Inspect crawler logs for {eng_id} bot blockages and refresh /llms.txt."

            # Case B: Conquest (We gained rank over competitors)
            elif curr_pos is not None and (base_pos is None or curr_pos < base_pos):
                gains += 1
                # Opportunity / Conquest notice
                alerts.append(DisplacementAlert(
                    alert_id=f"CONQ-{uuid.uuid4().hex[:6]}",
                    timestamp=now_str,
                    engine_id=eng_id,
                    engine_name=eng_name,
                    query_id=q_id,
                    query_text=q_text,
                    category=cat,
                    previous_rank=base_pos,
                    new_rank=curr_pos,
                    displaced_by_competitors=[],
                    citation_lost_urls=[],
                    severity="OPPORTUNITY",
                    impact_summary=f"Conquest: Brand advanced from Rank {base_pos or 'Unmentioned'} to Rank {curr_pos} on {eng_name}!",
                    recommended_action="Anchor this victory with additional Schema.org entity definitions."
                ))
                continue

            if is_loss:
                alerts.append(DisplacementAlert(
                    alert_id=f"DISP-{uuid.uuid4().hex[:6]}",
                    timestamp=now_str,
                    engine_id=eng_id,
                    engine_name=eng_name,
                    query_id=q_id,
                    query_text=q_text,
                    category=cat,
                    previous_rank=base_pos,
                    new_rank=curr_pos,
                    displaced_by_competitors=rivals_present,
                    citation_lost_urls=getattr(base_run, "citations", [])[:2],
                    severity=severity,
                    impact_summary=impact,
                    recommended_patch=action
                ))

        critical_list = [a for a in alerts if a.severity in ("CRITICAL", "MAJOR")]

        return DisplacementAnalysisResult(
            target_domain=target_domain,
            brand_name=target_brand,
            total_queries_compared=len(common_keys),
            net_displacement_score=gains - losses,
            displacements_suffered=losses,
            conquests_achieved=gains,
            critical_alerts=critical_list,
            all_alerts=alerts
        )


displacement_sentinel = DisplacementSentinel()
