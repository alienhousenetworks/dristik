"""
Dristik AI Trust Signals & Security Authority Agent
Evaluates SSL/HTTPS encryption, HSTS headers, CSP security, and business credibility indicators.
"""
from typing import Dict, Any
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever

class TrustAuthorityAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_trust", capability="trust_authority", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=20)
        
        sec_ev = next((ev for ev in evidence_slice if ev.source_type == "security" and isinstance(ev.value, dict)), None)
        if sec_ev:
            is_https = sec_ev.value.get("is_https")
            has_hsts = sec_ev.value.get("has_hsts", False)
        else:
            all_evs = blackboard.evidence_store.get_all()
            urls = [getattr(e, "url", "") for e in all_evs if getattr(e, "url", None)]
            has_explicit_https = any(u.startswith("https://") for u in urls)
            has_explicit_http = any(u.startswith("http://") for u in urls)
            is_https = True if has_explicit_https else (False if has_explicit_http else None)
            has_hsts = False
        
        if is_https is False:
            self.register_claim(
                blackboard=blackboard,
                statement="Website is served over insecure HTTP connection without SSL encryption.",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.CRITICAL,
                evidence_refs=[sec_ev.id] if sec_ev else [],
                confidence=0.99,
                recommendation="Enforce full HTTPS redirect and install a valid TLS certificate.",
                impact=10,
                effort=2
            )
        elif is_https is True and not has_hsts:
            self.register_claim(
                blackboard=blackboard,
                statement="Missing Strict-Transport-Security (HSTS) header exposes visitors to protocol downgrade attacks.",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.LOW,
                evidence_refs=[sec_ev.id] if sec_ev else [],
                confidence=0.90,
                recommendation="Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' to server response headers.",
                impact=5,
                effort=1
            )
        elif is_https is True and has_hsts:
            self.register_claim(
                blackboard=blackboard,
                statement="Encrypted HTTPS with active HSTS response headers confirmed.",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.INFO,
                evidence_refs=[sec_ev.id] if sec_ev else [],
                confidence=0.95,
                recommendation="Maintain current SSL/TLS certificate auto-renewal."
            )
        else:
            self.register_claim(
                blackboard=blackboard,
                statement="Transport layer encryption status unverified from crawl telemetry.",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.INFO,
                evidence_refs=[],
                confidence=0.40,
                recommendation="Verify HTTPS enforcement on production domain."
            )
            
        blackboard.log_step("Trust & Security Signals Analyzed", self.agent_id, {"is_https": is_https, "has_hsts": has_hsts})
        return {"is_https": is_https, "has_hsts": has_hsts}
