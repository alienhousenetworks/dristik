"""
Dristik AI Answer Diff System.
Audits live AI answer engine responses against the first-party Entity Truth Graph.
Extracts factual claims from LLM responses, reconciles them with verified canonical facts,
and computes claim-level verification:
- Verified claims (Supported)
- Hallucinated claims (Unverified / No first-party source)
- Contradictory claims (Directly violates Entity Truth Graph)
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from app.domain.models import CanonicalEntityFact, AiClaimRecord


ClaimVerificationStatus = Literal["VERIFIED", "UNVERIFIED", "CONTRADICTION"]


class ExtractedEngineClaim(BaseModel):
    claim_id: str
    prompt_id: str
    engine: str
    attribute: str               # pricing, capabilities, founded, headquarters, compliance, customer_type
    statement: str
    status: ClaimVerificationStatus
    grounding_fact: Optional[str] = None
    contradiction_detail: Optional[str] = None
    confidence: float = 0.85


class AiAnswerDiffReport(BaseModel):
    target_domain: str
    brand_name: str
    total_claims: int = 0
    verified_claims: int = 0
    unverified_claims: int = 0
    contradictions: int = 0
    fact_precision: float = 1.0       # verified / total_claims
    fact_recall: float = 0.8          # canonical facts cited / total canonical facts
    contradiction_rate: float = 0.0   # contradictions / total_claims
    hallucination_rate: float = 0.0   # unverified / total_claims
    claims: List[ExtractedEngineClaim] = Field(default_factory=list)
    executive_summary: str = ""


class AiAnswerDiffEngine:
    """
    Compares live AI engine responses against the canonical Entity Truth Graph.
    """

    def analyze_response(
        self,
        prompt_id: str,
        engine_name: str,
        raw_response: str,
        canonical_facts: List[CanonicalEntityFact],
        brand_name: str,
    ) -> List[ExtractedEngineClaim]:
        extracted: List[ExtractedEngineClaim] = []
        if not raw_response or raw_response.startswith("API Error") or raw_response.startswith("Request failed"):
            return extracted

        brand_low = brand_name.lower().strip()
        resp_low = raw_response.lower()

        # Build lookup of canonical facts by attribute
        facts_by_attr: Dict[str, List[CanonicalEntityFact]] = {}
        for f in canonical_facts:
            facts_by_attr.setdefault(f.attribute.lower(), []).append(f)

        # 1. Check Pricing claims
        pricing_matches = re.findall(
            r"(?:costs?|priced? at|plans? start(?:ing)? at|tiers? range from|subscription of)\s+([^\.\n;]+)",
            raw_response,
            re.I
        )
        for p_match in pricing_matches:
            stmt = p_match.strip()[:140]
            cid = f"claim_{uuid.uuid4().hex[:8]}"
            can_pricing = facts_by_attr.get("price") or facts_by_attr.get("pricing") or []
            if not can_pricing:
                extracted.append(ExtractedEngineClaim(
                    claim_id=cid,
                    prompt_id=prompt_id,
                    engine=engine_name,
                    attribute="pricing",
                    statement=f"Model claims pricing: '{stmt}'",
                    status="UNVERIFIED",
                    grounding_fact=None,
                    contradiction_detail="No public pricing published on first-party website; model stated ungrounded commercial terms."
                ))
            else:
                canon_val = can_pricing[0].value.lower()
                if any(num in canon_val for num in re.findall(r"\d+", stmt)):
                    extracted.append(ExtractedEngineClaim(
                        claim_id=cid,
                        prompt_id=prompt_id,
                        engine=engine_name,
                        attribute="pricing",
                        statement=f"Model claims pricing: '{stmt}'",
                        status="VERIFIED",
                        grounding_fact=f"Matches canonical pricing: {can_pricing[0].value}",
                    ))
                else:
                    extracted.append(ExtractedEngineClaim(
                        claim_id=cid,
                        prompt_id=prompt_id,
                        engine=engine_name,
                        attribute="pricing",
                        statement=f"Model claims pricing: '{stmt}'",
                        status="CONTRADICTION",
                        grounding_fact=f"First-party source publishes: {can_pricing[0].value}",
                        contradiction_detail=f"Model claims '{stmt}', which directly contradicts verified pricing '{can_pricing[0].value}'."
                    ))

        # 2. Check Foundation / Establishment year
        founded_match = re.search(r"(?:founded|established|started)\s+(?:in\s+)?([12][0-9]{3})", raw_response, re.I)
        if founded_match:
            year_claimed = founded_match.group(1)
            cid = f"claim_{uuid.uuid4().hex[:8]}"
            can_founded = facts_by_attr.get("foundingdate") or facts_by_attr.get("founded") or []
            if can_founded:
                canon_year = re.search(r"[12][0-9]{3}", can_founded[0].value)
                if canon_year and canon_year.group(0) == year_claimed:
                    extracted.append(ExtractedEngineClaim(
                        claim_id=cid,
                        prompt_id=prompt_id,
                        engine=engine_name,
                        attribute="founded",
                        statement=f"Founded in {year_claimed}",
                        status="VERIFIED",
                        grounding_fact=f"Matches verified schema/DOM year: {can_founded[0].value}",
                    ))
                elif canon_year:
                    extracted.append(ExtractedEngineClaim(
                        claim_id=cid,
                        prompt_id=prompt_id,
                        engine=engine_name,
                        attribute="founded",
                        statement=f"Founded in {year_claimed}",
                        status="CONTRADICTION",
                        grounding_fact=f"Actual verified year is {canon_year.group(0)}",
                        contradiction_detail=f"Model hallucinates founded year as {year_claimed}, but website verifies {canon_year.group(0)}."
                    ))
            else:
                extracted.append(ExtractedEngineClaim(
                    claim_id=cid,
                    prompt_id=prompt_id,
                    engine=engine_name,
                    attribute="founded",
                    statement=f"Founded in {year_claimed}",
                    status="UNVERIFIED",
                    contradiction_detail="Founding year unverified in first-party evidence."
                ))

        # 3. Check Core Capabilities / Services stated
        for fact in canonical_facts:
            if fact.attribute in ("name", "url"):
                continue
            val_snippet = fact.value.lower()
            if len(val_snippet) > 4 and val_snippet in resp_low:
                extracted.append(ExtractedEngineClaim(
                    claim_id=f"claim_{uuid.uuid4().hex[:8]}",
                    prompt_id=prompt_id,
                    engine=engine_name,
                    attribute=fact.attribute,
                    statement=f"Model states verified fact: '{fact.attribute}: {fact.value[:60]}'",
                    status="VERIFIED",
                    grounding_fact=f"Grounded in {fact.source_type} ({fact.source_url or 'site'})"
                ))

        return extracted

    def build_diff_report(
        self,
        evaluations: List[Any],
        canonical_facts: List[CanonicalEntityFact],
        target_domain: str,
        brand_name: str,
    ) -> AiAnswerDiffReport:
        all_claims: List[ExtractedEngineClaim] = []

        for eval_item in evaluations:
            p_id = getattr(eval_item, "query_id", "Q-01")
            eng = getattr(eval_item, "engine_name", "AI Engine")
            raw = getattr(eval_item, "raw_response_text", "") or getattr(eval_item, "raw_response", "") or ""

            claims = self.analyze_response(
                prompt_id=p_id,
                engine_name=eng,
                raw_response=raw,
                canonical_facts=canonical_facts,
                brand_name=brand_name,
            )
            all_claims.extend(claims)

        tot = len(all_claims)
        ver = sum(1 for c in all_claims if c.status == "VERIFIED")
        unv = sum(1 for c in all_claims if c.status == "UNVERIFIED")
        con = sum(1 for c in all_claims if c.status == "CONTRADICTION")

        prec = round(ver / max(1, tot), 2) if tot else 1.0
        rec = round(min(1.0, ver / max(1, len(canonical_facts))), 2) if canonical_facts else 0.8
        con_rate = round(con / max(1, tot), 2) if tot else 0.0
        hall_rate = round(unv / max(1, tot), 2) if tot else 0.0

        summary = (
            f"{ver}/{tot} claims verified against Entity Truth Graph ({prec*100:.0f}% precision). "
            f"{con} contradiction(s), {unv} unverified claim(s)."
            if tot else "No extractable commercial claims found in response sample."
        )

        return AiAnswerDiffReport(
            target_domain=target_domain,
            brand_name=brand_name,
            total_claims=tot,
            verified_claims=ver,
            unverified_claims=unv,
            contradictions=con,
            fact_precision=prec,
            fact_recall=rec,
            contradiction_rate=con_rate,
            hallucination_rate=hall_rate,
            claims=all_claims,
            executive_summary=summary,
        )


ai_answer_diff_engine = AiAnswerDiffEngine()
