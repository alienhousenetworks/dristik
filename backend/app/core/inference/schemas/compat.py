"""
Dristik AI Legacy Adaptation Layer
Maps 70B-hardened qualitative bands and structured outputs into legacy keys
to prevent breaking downstream API consumers, blackboard states, or UI components.
"""
from typing import Dict, Any, List

"""
Dristik AI Legacy Adaptation Layer
Maps 70B-hardened qualitative bands and structured outputs into legacy keys
without fabricating synthetic precision numbers.
"""
from typing import Dict, Any, List, Optional


def legacy_adapt(agent_name: str, new_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapts 70B-hardened output dictionaries to legacy format expected by existing APIs.
    Preserves qualitative bands and leaves unmeasured numeric scores as None.
    """
    if not isinstance(new_obj, dict):
        return {}

    adapted = dict(new_obj)

    if agent_name in ["business", "business_intelligence"]:
        if "five_second_clarity" in adapted and isinstance(adapted["five_second_clarity"], dict):
            band = adapted["five_second_clarity"].get("band", "unknown")
            adapted["five_second_clarity_band"] = band
            # Do not invent a pseudo-precise score from qualitative band
            if "five_second_clarity_score" not in adapted:
                adapted["five_second_clarity_score"] = None
        elif "five_second_clarity_score" not in adapted:
            adapted["five_second_clarity_score"] = None

        # Map cac_impact band to cac_impact_risk text
        if "cac_impact" in adapted and isinstance(adapted["cac_impact"], dict):
            adapted["cac_impact_risk"] = adapted["cac_impact"].get("mechanism") or adapted["cac_impact"].get("band", "moderate")

        # Map motion signals to primary intent if missing
        if "primary_intent" not in adapted:
            motion = adapted.get("monetization_motion") or adapted.get("motion_signals")
            if motion == "self_serve":
                adapted["primary_intent"] = "saas"
            elif motion == "sales_assisted":
                adapted["primary_intent"] = "lead_generation"
            else:
                adapted["primary_intent"] = "lead_generation"

        if "confidence" not in adapted:
            adapted["confidence"] = 0.50

    elif agent_name in ["geo", "geo_analysis"]:
        if "entity_clarity_score" not in adapted:
            adapted["entity_clarity_score"] = None

        if "information_gain_score" not in adapted:
            adapted["information_gain_score"] = None

        if "direct_answer_density_score" not in adapted:
            adapted["direct_answer_density_score"] = None

    elif agent_name in ["ai_search", "ai_search_simulation"]:
        evals = adapted.get("evaluations", [])
        adapted_evals = []
        for ev in evals:
            if isinstance(ev, dict):
                item = dict(ev)
                if "citation_probability" not in item:
                    item["citation_probability"] = None
                if "score" not in item:
                    item["score"] = None
                if "hallucination_vulnerability_risk" not in item:
                    item["hallucination_vulnerability_risk"] = item.get("hallucination_vulnerability", "low").capitalize()
                adapted_evals.append(item)
        adapted["evaluations"] = adapted_evals

        if "aggregate_citation_probability" not in adapted:
            adapted["aggregate_citation_probability"] = None

    elif agent_name in ["synthesizer", "executive_synthesizer"]:
        if "financial_impact_model" in adapted and isinstance(adapted["financial_impact_model"], dict):
            fim = dict(adapted["financial_impact_model"])
            if "estimated_cac_inflation_pct" not in fim:
                fim["estimated_cac_inflation_pct"] = None
            if "organic_pipeline_at_risk_score" not in fim:
                fim["organic_pipeline_at_risk_score"] = fim.get("organic_pipeline_at_risk", "Moderate").capitalize()
            if "conversion_velocity_uplift_potential" not in fim:
                fim["conversion_velocity_uplift_potential"] = fim.get("conversion_velocity_uplift", "Moderate").capitalize()
            adapted["financial_impact_model"] = fim

    elif agent_name in ["strategist"]:
        opps = adapted.get("growth_opportunities", [])
        for opp in opps:
            if isinstance(opp, dict) and "ice_score" in opp and isinstance(opp["ice_score"], dict):
                ice = opp["ice_score"]
                if "composite" not in ice or ice["composite"] is None:
                    i = ice.get("impact")
                    c = ice.get("confidence")
                    e = ice.get("ease")
                    if i is not None and c is not None and e is not None:
                        ice["composite"] = round((i + c + e) / 3.0, 1)
                    else:
                        ice["composite"] = None

    if "claims" in adapted and isinstance(adapted["claims"], list):
        adapted_claims = []
        for c in adapted["claims"]:
            if isinstance(c, dict):
                c_copy = dict(c)
                if "impact" not in c_copy:
                    c_copy["impact"] = None
                if "confidence" not in c_copy:
                    c_copy["confidence"] = 0.50
                adapted_claims.append(c_copy)
        adapted["claims"] = adapted_claims
    elif "claims" not in adapted:
        adapted["claims"] = []

    return adapted

