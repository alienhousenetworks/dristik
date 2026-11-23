"""
6 Evidence-Linked Behavioral AI Analysis Agents for CRO.

Agents:
1. FrictionDetectionAgent — repeated interaction failures & dead clicks
2. RageClickAgent — repeated unsuccessful clicks on specific selectors
3. FormAbandonmentAgent — field-level drop-off & backend submission failures
4. NavigationAgent — confusing back-and-forth / loop navigation paths
5. MobileUxAgent — mobile-specific friction vs desktop baseline
6. ConversionBehaviourAgent — behavioral differences between converters and non-converters

Every observation MUST store:
- recording_ref (session/recording identifier)
- timestamp_utc
- supporting event_sequence
- explicit denominator (sessions evaluated)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.db.enterprise_intelligence_schema import connect_enterprise_db


class BehavioralObservation(BaseModel):
    agent_name: str
    severity: str  # CRITICAL | HIGH | MEDIUM | INFO
    title: str
    page_url: str
    dom_selector: Optional[str] = None
    recording_ref: str
    timestamp_utc: str
    event_sequence: List[str] = Field(default_factory=list)
    affected_sessions: int = 0
    denominator_sessions: int = 0
    rate_pct: float = 0.0
    recommendation: str


class BehavioralAgentSuite:
    """Runs all 6 evidence-linked CRO behavioral agents over real persisted event telemetry."""

    @classmethod
    def analyze(cls, *, org_id: str, domain: str, db_path: Optional[str] = None) -> Dict[str, Any]:
        conn = connect_enterprise_db(db_path)
        try:
            rows = conn.execute(
                """
                SELECT session_id, visitor_id, event_name, page_url, device_category,
                       dom_selector, form_id, form_field_name, backend_submit_status,
                       is_rage_click, is_dead_click, event_ts_utc
                FROM analytics_events
                WHERE org_id = ? AND domain = ? AND is_bot_or_internal = 0 AND consent_granted = 1
                ORDER BY session_id ASC, event_ts_utc ASC
                """,
                (org_id, domain),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return {
                "status": "NO_BEHAVIORAL_DATA",
                "denominator_sessions": 0,
                "observations": [],
                "agents_executed": [
                    "FrictionDetectionAgent", "RageClickAgent", "FormAbandonmentAgent",
                    "NavigationAgent", "MobileUxAgent", "ConversionBehaviourAgent",
                ],
            }

        sessions: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            sessions.setdefault(r["session_id"], []).append(dict(r))

        denom = len(sessions)
        observations: List[BehavioralObservation] = []

        # 1. RageClickAgent
        rage_by_sel: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        for sid, evs in sessions.items():
            for e in evs:
                if e["is_rage_click"]:
                    rage_by_sel.setdefault((e["page_url"], e["dom_selector"] or "unknown"), []).append(e)
        for (url, sel), hits in rage_by_sel.items():
            aff = len({h["session_id"] for h in hits})
            sample = hits[0]
            observations.append(BehavioralObservation(
                agent_name="RageClickAgent",
                severity="HIGH" if aff / denom >= 0.1 else "MEDIUM",
                title=f"Rage clicks detected on selector '{sel}'",
                page_url=url, dom_selector=sel,
                recording_ref=f"rec:{sample['session_id']}",
                timestamp_utc=sample["event_ts_utc"],
                event_sequence=[e["event_name"] for e in sessions[sample["session_id"]][-5:]],
                affected_sessions=aff, denominator_sessions=denom,
                rate_pct=round((aff / denom) * 100.0, 1),
                recommendation=f"Inspect click handler and hit-area for '{sel}' on {url}.",
            ))

        # 2. FrictionDetectionAgent (dead clicks)
        dead_sessions = [sid for sid, evs in sessions.items() if any(e["is_dead_click"] for e in evs)]
        if dead_sessions:
            sample_sid = dead_sessions[0]
            sample_ev = next(e for e in sessions[sample_sid] if e["is_dead_click"])
            observations.append(BehavioralObservation(
                agent_name="FrictionDetectionAgent",
                severity="MEDIUM",
                title=f"Dead clicks on non-interactive element '{sample_ev['dom_selector'] or 'unknown'}'",
                page_url=sample_ev["page_url"], dom_selector=sample_ev["dom_selector"],
                recording_ref=f"rec:{sample_sid}",
                timestamp_utc=sample_ev["event_ts_utc"],
                event_sequence=[e["event_name"] for e in sessions[sample_sid][-5:]],
                affected_sessions=len(dead_sessions), denominator_sessions=denom,
                rate_pct=round((len(dead_sessions) / denom) * 100.0, 1),
                recommendation="Clarify visual affordances or bind interactive action to elements visitors expect to click.",
            ))

        # 3. FormAbandonmentAgent (including backend submission failure detection)
        form_starts = [sid for sid, evs in sessions.items() if any(e["event_name"] in ("form_start", "form_field_focus") for e in evs)]
        form_success = [
            sid for sid, evs in sessions.items()
            if any(e["event_name"] == "form_submit_result" and (e["backend_submit_status"] or 0) in range(200, 300) for e in evs)
        ]
        abandoned = [sid for sid in form_starts if sid not in form_success]
        if abandoned:
            sample_sid = abandoned[0]
            last_form_ev = [e for e in sessions[sample_sid] if e["form_id"] or e["event_name"].startswith("form_")][-1]
            observations.append(BehavioralObservation(
                agent_name="FormAbandonmentAgent",
                severity="HIGH",
                title=f"Form abandonment observed at field '{last_form_ev['form_field_name'] or 'submit'}'",
                page_url=last_form_ev["page_url"], dom_selector=last_form_ev["form_id"],
                recording_ref=f"rec:{sample_sid}",
                timestamp_utc=last_form_ev["event_ts_utc"],
                event_sequence=[e["event_name"] for e in sessions[sample_sid][-6:]],
                affected_sessions=len(abandoned), denominator_sessions=len(form_starts),
                rate_pct=round((len(abandoned) / len(form_starts)) * 100.0, 1),
                recommendation="Reduce field friction and verify server-side 2xx submission confirmation.",
            ))

        # 4. NavigationAgent (looping / back-and-forth page views >= 4 on same session)
        loop_sids = []
        for sid, evs in sessions.items():
            urls = [e["page_url"] for e in evs if e["event_name"] == "page_view"]
            if len(urls) >= 3 and len(set(urls)) < len(urls):
                loop_sids.append(sid)
        if loop_sids:
            sample_sid = loop_sids[0]
            observations.append(BehavioralObservation(
                agent_name="NavigationAgent",
                severity="MEDIUM",
                title="Repeated back-and-forth navigation loop detected",
                page_url=sessions[sample_sid][0]["page_url"],
                recording_ref=f"rec:{sample_sid}",
                timestamp_utc=sessions[sample_sid][-1]["event_ts_utc"],
                event_sequence=[e["page_url"] for e in sessions[sample_sid] if e["event_name"] == "page_view"][:6],
                affected_sessions=len(loop_sids), denominator_sessions=denom,
                rate_pct=round((len(loop_sids) / denom) * 100.0, 1),
                recommendation="Clarify information architecture and surface pricing/shipping details earlier.",
            ))

        # 5. MobileUxAgent (mobile rage/dead click rate)
        mobile_sids = [sid for sid, evs in sessions.items() if evs[0]["device_category"] == "mobile"]
        mobile_friction = [sid for sid in mobile_sids if any(e["is_rage_click"] or e["is_dead_click"] for e in sessions[sid])]
        if mobile_friction:
            sample_sid = mobile_friction[0]
            observations.append(BehavioralObservation(
                agent_name="MobileUxAgent",
                severity="HIGH",
                title="Mobile-specific interaction friction detected",
                page_url=sessions[sample_sid][0]["page_url"],
                recording_ref=f"rec:{sample_sid}",
                timestamp_utc=sessions[sample_sid][-1]["event_ts_utc"],
                event_sequence=[e["event_name"] for e in sessions[sample_sid][-5:]],
                affected_sessions=len(mobile_friction), denominator_sessions=len(mobile_sids),
                rate_pct=round((len(mobile_friction) / len(mobile_sids)) * 100.0, 1),
                recommendation="Increase mobile tap targets (>=44x44px) and keep primary CTA sticky above the fold.",
            ))

        # 6. ConversionBehaviourAgent (converters vs non-converters)
        conv_sids = [sid for sid, evs in sessions.items() if any(e["event_name"] in ("purchase", "closed_won") for e in evs)]
        non_conv_sids = [sid for sid in sessions if sid not in conv_sids]
        if conv_sids and non_conv_sids:
            avg_ev_conv = round(sum(len(sessions[s]) for s in conv_sids) / len(conv_sids), 1)
            avg_ev_non = round(sum(len(sessions[s]) for s in non_conv_sids) / len(non_conv_sids), 1)
            observations.append(BehavioralObservation(
                agent_name="ConversionBehaviourAgent",
                severity="INFO",
                title=f"Converters average {avg_ev_conv} interactions vs {avg_ev_non} for non-converters",
                page_url=sessions[conv_sids[0]][0]["page_url"],
                recording_ref=f"rec:{conv_sids[0]}",
                timestamp_utc=sessions[conv_sids[0]][-1]["event_ts_utc"],
                event_sequence=[e["event_name"] for e in sessions[conv_sids[0]][:6]],
                affected_sessions=len(conv_sids), denominator_sessions=denom,
                rate_pct=round((len(conv_sids) / denom) * 100.0, 1),
                recommendation="Guide non-converting visitors toward the high-intent actions exhibited by converters.",
            ))

        return {
            "status": "MEASURED",
            "denominator_sessions": denom,
            "observations": [o.model_dump() for o in observations],
            "agents_executed": [
                "FrictionDetectionAgent", "RageClickAgent", "FormAbandonmentAgent",
                "NavigationAgent", "MobileUxAgent", "ConversionBehaviourAgent",
            ],
        }
