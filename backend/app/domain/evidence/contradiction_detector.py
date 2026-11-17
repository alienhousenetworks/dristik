"""
Dristik AI Contradiction Detector
Detects semantic and factual conflicts between specialist agent claims.

v4: DOM vs external (ext_xxx) conflicts are CONTESTED and must NOT be
auto-resolved here. They are routed to verification.contradiction.v3.
Populates full contradiction precision fields (question_text, statement_a, statement_b,
source_url_a, source_url_b, evidence_id_a, evidence_id_b, disputed_fact,
conflict_explanation, authoritative_correction).
"""
from typing import List, Optional
from app.domain.enums import SourceIntegrityLabel, VerificationStatus
from app.domain.models import Claim, Contradiction, ContradictionReport

CONTRADICTION_AGENT_ID = "verification.contradiction.v3"


def _extract_claim_url(claim: Claim) -> str:
    for ev_obj in (getattr(claim, "evidence_ref_objects", None) or []):
        url = getattr(ev_obj, "url", None)
        if url:
            return str(url)
    scope = getattr(claim, "scope", None)
    if scope and (scope.startswith("http://") or scope.startswith("https://") or scope.startswith("/")):
        return str(scope)
    return "/"


def _extract_claim_evidence_id(claim: Claim) -> str:
    if getattr(claim, "evidence_refs", None):
        return str(claim.evidence_refs[0])
    for ev_obj in (getattr(claim, "evidence_ref_objects", None) or []):
        sid = getattr(ev_obj, "source_id", None)
        if sid:
            return str(sid)
    return str(claim.id)


class ContradictionDetector:
    def detect_contradictions(self, claims: List[Claim]) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        c_counter = 0

        for claim in claims:
            if (
                claim.source_integrity_label == SourceIntegrityLabel.CONTESTED
                or claim.verification_status == VerificationStatus.CONTESTED
            ):
                c_counter += 1
                family_label = claim.claim_family.value if claim.claim_family else (
                    claim.category.value if hasattr(claim.category, "value") and claim.category else "brand_claim"
                )
                ev_refs = list(claim.evidence_refs or [])
                ev_a = ev_refs[0] if len(ev_refs) >= 1 else claim.id
                ev_b = ev_refs[1] if len(ev_refs) >= 2 else (ev_refs[0] if ev_refs else f"ext_{claim.id}")
                url_a = _extract_claim_url(claim)
                url_b = "external://ground-truth-feed"
                if getattr(claim, "evidence_ref_objects", None) and len(claim.evidence_ref_objects) >= 2:
                    url_b = getattr(claim.evidence_ref_objects[1], "url", None) or url_b

                desc = (
                    f"External ground-truth feed contradicts DOM evidence for "
                    f"{family_label} ({claim.id}). Tokens: {claim.evidence_refs}."
                )
                stmt_a = claim.statement or f"DOM claim ({claim.id}) for {family_label}"
                stmt_b = (
                    claim.verification_notes
                    or f"Contested external ground-truth observation for {family_label} (ref: {ev_b})"
                )
                q_text = f"What is the verified {family_label.replace('_', ' ')} status for this page?"
                disputed = f"{family_label.replace('_', ' ').title()} verification mismatch"
                correction = (
                    claim.recommendation
                    or f"Reconcile on-page DOM markup at {url_a} with external ground-truth telemetry ({ev_b})."
                )

                contradictions.append(Contradiction(
                    id=f"contra_{c_counter:03d}",
                    claim_a_id=claim.id,
                    claim_b_id=claim.id,
                    description=desc,
                    resolution=f"ROUTED_TO_{CONTRADICTION_AGENT_ID}",
                    winner_claim_id=None,
                    routed_to=CONTRADICTION_AGENT_ID,
                    question_text=q_text,
                    statement_a=stmt_a,
                    statement_b=stmt_b,
                    source_url_a=url_a,
                    source_url_b=url_b,
                    evidence_id_a=ev_a,
                    evidence_id_b=ev_b,
                    disputed_fact=disputed,
                    conflict_explanation=desc,
                    authoritative_correction=correction,
                ))

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                if c1.verification_status == VerificationStatus.CONTESTED or c2.verification_status == VerificationStatus.CONTESTED:
                    continue
                if c1.source_integrity_label == SourceIntegrityLabel.CONTESTED or c2.source_integrity_label == SourceIntegrityLabel.CONTESTED:
                    continue

                if c1.category == c2.category:
                    s1 = c1.statement.lower()
                    s2 = c2.statement.lower()

                    is_conflict = False
                    reason = ""
                    q_text = ""
                    disputed = ""
                    correction = ""

                    if (
                        (("has valid schema" in s1 or "schema found" in s1) and ("missing schema" in s2 or "no schema" in s2))
                        or (("missing schema" in s1 or "no schema" in s1) and ("has valid schema" in s2 or "schema found" in s2))
                    ):
                        is_conflict = True
                        reason = "Conflict regarding presence of structured JSON-LD schema."
                        q_text = "Does the website publish valid structured JSON-LD schema markup?"
                        disputed = "Presence and validity of JSON-LD structured data"
                        correction = "Verify rendered DOM <script type='application/ld+json'> blocks and standardize schema across templates."
                    elif (
                        (("fast" in s1 or "good performance" in s1) and ("slow" in s2 or "poor performance" in s2))
                        or (("slow" in s1 or "poor performance" in s1) and ("fast" in s2 or "good performance" in s2))
                    ):
                        is_conflict = True
                        reason = "Conflict regarding website speed and server TTFB performance."
                        q_text = "What is the verified server response speed and TTFB performance of the website?"
                        disputed = "Server response latency (TTFB) and page speed classification"
                        correction = "Use measured HTTP origin TTFB and CrUX/Lighthouse telemetry as the authoritative speed baseline."
                    elif (
                        (("clear cta" in s1) and ("missing cta" in s2 or "unclear cta" in s2))
                        or (("missing cta" in s1 or "unclear cta" in s1) and ("clear cta" in s2))
                    ):
                        is_conflict = True
                        reason = "Conflict regarding clarity of primary call-to-action."
                        q_text = "Does the landing page feature a clear, above-the-fold primary call-to-action?"
                        disputed = "Presence and clarity of primary conversion CTA"
                        correction = "Ensure a single high-contrast, action-oriented CTA button is present in the primary hero viewport."

                    if is_conflict:
                        c_counter += 1
                        winner_claim = c1 if len(c1.evidence_refs) >= len(c2.evidence_refs) else c2
                        winner = winner_claim.id
                        url_a = _extract_claim_url(c1)
                        url_b = _extract_claim_url(c2)
                        ev_a = _extract_claim_evidence_id(c1)
                        ev_b = _extract_claim_evidence_id(c2)
                        res_text = f"Resolved by prioritizing claim {winner} with higher evidence grounding ({ winner_claim.statement })."
                        contradictions.append(Contradiction(
                            id=f"contra_{c_counter:03d}",
                            claim_a_id=c1.id,
                            claim_b_id=c2.id,
                            description=reason,
                            resolution=res_text,
                            winner_claim_id=winner,
                            question_text=q_text,
                            statement_a=c1.statement,
                            statement_b=c2.statement,
                            source_url_a=url_a,
                            source_url_b=url_b,
                            evidence_id_a=ev_a,
                            evidence_id_b=ev_b,
                            disputed_fact=disputed,
                            conflict_explanation=f"{reason} Claim A ('{c1.statement}') conflicts with Claim B ('{c2.statement}').",
                            authoritative_correction=winner_claim.recommendation or correction or res_text,
                        ))

        return contradictions

    @staticmethod
    def to_contradiction_reports(contradictions: List[Contradiction]) -> List[ContradictionReport]:
        """Convert Contradiction records into full ContradictionReport models with all precision fields."""
        reports: List[ContradictionReport] = []
        for c in contradictions:
            reports.append(ContradictionReport(
                id=c.id,
                contradiction_type="inter_agent_conflict",
                declared_type=c.statement_a,
                detected_type=c.statement_b,
                confidence=0.90,
                reason=c.conflict_explanation or c.description,
                question_text=c.question_text,
                statement_a=c.statement_a,
                statement_b=c.statement_b,
                source_url_a=c.source_url_a,
                source_url_b=c.source_url_b,
                evidence_id_a=c.evidence_id_a,
                evidence_id_b=c.evidence_id_b,
                disputed_fact=c.disputed_fact,
                conflict_explanation=c.conflict_explanation or c.description,
                authoritative_correction=c.authoritative_correction or c.resolution,
            ))
        return reports
