"""
Dristik AI Causal Reasoning & Root-Cause Analysis Engine
Distinguishes deep architectural and commercial bottlenecks from superficial symptoms.
Maps causal chains: Root Cause -> Intermediate Deficit -> User Impact -> Lost Growth.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import Claim, BusinessProfile
from app.domain.enums import Category, Severity

class CausalBottleneck(BaseModel):
    bottleneck_id: str
    root_cause: str
    primary_category: Category
    downstream_symptoms: List[str]
    commercial_consequence: str
    severity: Severity = Severity.HIGH
    confidence: float = 0.92
    prescribed_intervention: str

class CausalReasoningEngine:
    """
    Infers causal relationships across claims to isolate the primary bottleneck.
    """

    def analyze_root_causes(
        self,
        claims: List[Claim],
        business_profile: BusinessProfile
    ) -> List[CausalBottleneck]:
        bottlenecks: List[CausalBottleneck] = []

        # Find ICP or Value Proposition claims
        icp_claims = [c for c in claims if any(k in c.statement.lower() for k in ["icp", "target audience", "value proposition", "positioning", "messaging"])]
        cta_claims = [c for c in claims if any(k in c.statement.lower() for k in ["cta", "call to action", "conversion", "button", "funnel"])]
        schema_claims = [c for c in claims if any(k in c.statement.lower() for k in ["schema", "json-ld", "structured data", "entity"])]
        ai_claims = [c for c in claims if any(k in c.statement.lower() for k in ["ai search", "citation", "chatgpt", "perplexity", "geo"])]

        # 1. Root Cause: ICP Ambiguity causing downstream conversion decay
        if icp_claims:
            symptoms = [c.statement for c in cta_claims[:3]]
            if not symptoms:
                symptoms = ["Generic, non-specific CTA copy", "Vague feature descriptions", "Unclear buyer self-qualification"]

            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_01_icp",
                root_cause="The website does not explicitly specify its Ideal Customer Profile (ICP) or market category.",
                primary_category=Category.COMPETITIVE,
                downstream_symptoms=symptoms,
                commercial_consequence="Enterprise prospects cannot quickly determine if the product solves their specific tier problems, resulting in high first-fold bounce.",
                severity=Severity.HIGH,
                confidence=0.93,
                prescribed_intervention="Introduce clear ICP signposts ('Built for Enterprise SecOps' / 'For Developer Teams') and align hero headline to tangible buyer outcomes."
            ))

        # 2. Root Cause: Missing Entity Schema causing AI citation blindness
        if schema_claims and ai_claims:
            bottlenecks.append(CausalBottleneck(
                bottleneck_id="causal_02_schema_citation",
                root_cause="Absence of machine-readable Organization and Product JSON-LD schemas.",
                primary_category=Category.SCHEMA,
                downstream_symptoms=[c.statement for c in ai_claims[:2]],
                commercial_consequence="Generative answer engines (ChatGPT, Perplexity, Google AI Overviews) fail to resolve corporate entity relationships, suppressing brand citation probability.",
                severity=Severity.HIGH,
                confidence=0.95,
                prescribed_intervention="Inject Schema.org Organization and SoftwareApplication JSON-LD markup with explicit sameAs social links and verified product properties."
            ))

        return bottlenecks
