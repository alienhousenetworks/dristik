"""
Literal CERTAIN | LIKELY | GUESSING rubric for every finding.

CERTAIN: >=2 independent sources (DOM + external, or two distinct external
         sources) agree, and no contradicting token is present.
LIKELY:  exactly 1 supporting source, OR 2+ agree but at least one supporting
         token has low confidence_basis (inferred).
GUESSING: inference from absence, pattern-match on partial text, or
          extrapolation beyond what any token states.

GUESSING + materiality CRITICAL is held from strategy.executive.v3 until
verification.adversarial.v3 reviews it.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Set, Tuple

from app.domain.enums import (
    ClaimType,
    EvidenceLevel,
    Materiality,
    ObservationType,
    RubricConfidence,
    Severity,
    SourceIntegrityLabel,
    VerificationStatus,
)
from app.domain.models import Claim, Finding
from app.evidence.models import Evidence
from app.evidence.store import EvidenceStore

ADVERSARIAL_AGENT_ID = "verification.adversarial.v3"
EXECUTIVE_AGENT_ID = "strategy.executive.v3"

_LOW_BASIS = {"inferred", "guess", "pattern", "extrapolat", "simulation"}
_ABSENCE_MARKERS = (
    "not_in_evidence",
    "not in evidence",
    "no evidence",
    "absence of",
    "cannot determine",
    "appears to",
    "seems to",
    "might be",
    "may be",
    "suggests that",
    "likely missing",
    "we infer",
    "inferred from",
    "pattern-match",
    "extrapolat",
)
_STUB_STATUSES = {
    "NOT_CONFIGURED",
    "NOT_CONNECTED",
    "UNAVAILABLE",
    "NOT_RUN",
    "FAILED",
    "NOT_FOUND",
    "NO_MATCH",
    "NO_ENTITY",
    "INSUFFICIENT_TRAFFIC_FOR_CRUX",
}


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _is_usable(ev: Optional[Evidence], ref: str) -> bool:
    if ev is None:
        return bool(ref)
    payload = _as_dict(ev.value)
    status = str(payload.get("status") or (ev.metadata or {}).get("status") or "").upper()
    if status in _STUB_STATUSES:
        return False
    return True


def _source_key(ref: str, ev: Optional[Evidence]) -> Optional[str]:
    if not _is_usable(ev, ref):
        return None
    if str(ref).startswith("ev_"):
        return "dom"
    if str(ref).startswith("ext_"):
        if ev is None:
            return "ext:unknown"
        meta = ev.metadata or {}
        payload = _as_dict(ev.value)
        name = str(meta.get("source") or payload.get("source") or ev.analyzer or "external").lower()
        return f"ext:{name}"
    return f"other:{str(ref).split('_')[0]}"


def _basis_of(ev: Optional[Evidence]) -> str:
    if ev is None:
        return ""
    meta = ev.metadata or {}
    payload = _as_dict(ev.value)
    return str(meta.get("confidence_basis") or payload.get("confidence_basis") or "").lower()


def _conflicts(ev: Optional[Evidence]) -> List[str]:
    if ev is None:
        return []
    meta = ev.metadata or {}
    payload = _as_dict(ev.value)
    raw = meta.get("conflicts_with") or payload.get("conflicts_with") or []
    if isinstance(raw, str):
        return [raw]
    return [str(x) for x in raw if x]


def independent_support(
    refs: Sequence[str],
    store: Optional[EvidenceStore],
) -> Tuple[int, List[str], bool, bool]:
    """Return (count, source keys, has_contradiction, has_low_basis)."""
    keys: Set[str] = set()
    has_contradiction = False
    has_low_basis = False
    cited = [str(r) for r in (refs or []) if r]
    for ref in cited:
        ev = store.get(ref) if store else None
        key = _source_key(ref, ev)
        if not key:
            continue
        keys.add(key)
        basis = _basis_of(ev)
        if any(token in basis for token in _LOW_BASIS) or basis == "inferred":
            has_low_basis = True
        conflicts = set(_conflicts(ev))
        if conflicts & set(cited):
            has_contradiction = True
        elif conflicts:
            has_contradiction = True
    return len(keys), sorted(keys), has_contradiction, has_low_basis


def infer_materiality(severity: Severity, impact: int = 5) -> Materiality:
    if severity == Severity.CRITICAL or impact >= 9:
        return Materiality.CRITICAL
    if severity == Severity.HIGH or impact >= 7:
        return Materiality.MAJOR
    return Materiality.MINOR


def _is_guessing_language(text: str) -> bool:
    blob = (text or "").lower()
    return any(m in blob for m in _ABSENCE_MARKERS)


def classify_rubric(
    *,
    statement: str,
    evidence_refs: Sequence[str],
    store: Optional[EvidenceStore] = None,
    observation_type: Optional[ObservationType] = None,
    claim_type: Optional[ClaimType] = None,
    evidence_level: Optional[EvidenceLevel] = None,
    source_integrity: Optional[SourceIntegrityLabel] = None,
    verification_status: Optional[VerificationStatus] = None,
    severity: Severity = Severity.MEDIUM,
    impact: int = 5,
) -> dict:
    agreement, sources, has_contradiction, has_low_basis = independent_support(evidence_refs, store)
    materiality = infer_materiality(severity, impact)

    guessing_from_type = observation_type in {
        ObservationType.INFERRED,
        ObservationType.HYPOTHESIS,
        ObservationType.SIMULATION,
        ObservationType.UNKNOWN,
    }
    guessing_from_level = evidence_level in {
        EvidenceLevel.E0_NONE,
        EvidenceLevel.E1_LLM_ASSERTION,
    }
    guessing_from_language = _is_guessing_language(statement)
    no_tokens = agreement == 0

    # Evidentiary standard: A claim backed by direct DOM tokens (ev_*) is verified from
    # the page AST. Phrasing containing "absence of" or "missing" reflects an observed structural
    # defect, NOT an epistemic guess.
    has_dom_tokens = any(str(r).startswith("ev_") for r in (evidence_refs or []))
    if has_dom_tokens and not guessing_from_type and not guessing_from_level:
        guessing_from_language = False

    if (
        guessing_from_type
        or guessing_from_level
        or guessing_from_language
        or no_tokens
        or (claim_type == ClaimType.INFERENCE and agreement < 1)
    ):
        rubric = RubricConfidence.GUESSING
        if no_tokens:
            basis = "GUESSING because no independent evidence token supports the claim, so the next level (LIKELY) would require one supporting source."
        elif guessing_from_language:
            basis = "GUESSING because the claim infers from absence or hedges beyond what any cited token states, so it cannot be LIKELY."
        elif guessing_from_type:
            basis = f"GUESSING because observation_type={observation_type.value if observation_type else 'unknown'} is inference/hypothesis/simulation, not a direct token."
        else:
            basis = "GUESSING because the claim extrapolates past the cited tokens; LIKELY requires a supporting source that actually states it."
    elif has_contradiction:
        rubric = RubricConfidence.LIKELY
        basis = "LIKELY because a contradicting token is present, so CERTAIN is blocked even if multiple sources are cited."
    elif agreement >= 2 and has_low_basis:
        rubric = RubricConfidence.LIKELY
        basis = "LIKELY because two or more sources agree but at least one has a low confidence_basis (inferred), which bars CERTAIN."
    elif agreement >= 2:
        rubric = RubricConfidence.CERTAIN
        basis = (
            f"CERTAIN because {agreement} independent sources ({', '.join(sources)}) agree "
            "with no contradicting token; this is the top of the rubric."
        )
    else:
        rubric = RubricConfidence.LIKELY
        basis = "LIKELY because exactly one independent evidence source supports the claim; CERTAIN requires two agreeing independent sources."

    if source_integrity == SourceIntegrityLabel.CONTESTED or verification_status == VerificationStatus.CONTESTED:
        if rubric == RubricConfidence.CERTAIN:
            rubric = RubricConfidence.LIKELY
            basis = "LIKELY because DOM and external tokens are CONTESTED; CERTAIN forbids a contradicting token."

    if (
        source_integrity == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
        or "SINGLE_SOURCE_UNVERIFIED" in statement
        or verification_status == VerificationStatus.SINGLE_SOURCE_UNVERIFIED
    ):
        if rubric == RubricConfidence.CERTAIN:
            rubric = RubricConfidence.LIKELY
            basis = "LIKELY (confidence capped at MEDIUM): uncorroborated single-source claim; CERTAIN is strictly forbidden."

    held = rubric == RubricConfidence.GUESSING and materiality == Materiality.CRITICAL
    return {
        "confidence_rubric": rubric,
        "confidence_basis": basis,
        "materiality": materiality,
        "source_agreement": agreement,
        "held_from_executive": held,
        "routed_to": ADVERSARIAL_AGENT_ID if held else None,
        "supporting_sources": sources,
    }


def apply_rubric_to_claim(claim: Claim, store: Optional[EvidenceStore] = None) -> Claim:
    result = classify_rubric(
        statement=claim.statement,
        evidence_refs=claim.evidence_refs or [],
        store=store,
        observation_type=claim.observation_type,
        claim_type=claim.claim_type,
        evidence_level=claim.evidence_level,
        source_integrity=claim.source_integrity_label,
        verification_status=claim.verification_status,
        severity=claim.severity,
        impact=claim.impact,
    )
    claim.confidence_rubric = result["confidence_rubric"]
    claim.confidence_basis = result["confidence_basis"]
    claim.materiality = result["materiality"]
    claim.source_agreement = result["source_agreement"]
    if result["held_from_executive"] and not claim.adversarial_reviewed:
        claim.held_from_executive = True
        claim.routed_to = ADVERSARIAL_AGENT_ID
        note = (
            "GUESSING + CRITICAL held from strategy.executive.v3 until "
            f"{ADVERSARIAL_AGENT_ID} completes explicit review."
        )
        existing = claim.verification_notes or ""
        if note not in existing:
            claim.verification_notes = f"{existing} | {note}".strip(" |")
        if claim.verification_status == VerificationStatus.PROVISIONAL:
            claim.verification_status = VerificationStatus.PENDING_VERIFICATION
    elif claim.adversarial_reviewed:
        claim.held_from_executive = False
    return claim


def apply_rubric_to_finding(finding: Finding, store: Optional[EvidenceStore] = None) -> Finding:
    result = classify_rubric(
        statement=finding.finding or finding.title or finding.description,
        evidence_refs=finding.evidence_refs or [],
        store=store,
        severity=finding.severity,
        impact=finding.impact,
        source_integrity=finding.source_integrity_label,
        verification_status=finding.verification_status,
    )
    finding.finding = finding.finding or finding.title
    finding.confidence_rubric = result["confidence_rubric"]
    finding.confidence_basis = result["confidence_basis"]
    finding.materiality = result["materiality"]
    finding.source_agreement = result["source_agreement"]
    if result["held_from_executive"] and not finding.adversarial_reviewed:
        finding.held_from_executive = True
        finding.routed_to = ADVERSARIAL_AGENT_ID
        note = (
            "GUESSING + CRITICAL held from strategy.executive.v3 until "
            f"{ADVERSARIAL_AGENT_ID} completes explicit review."
        )
        existing = finding.verification_notes or ""
        if note not in existing:
            finding.verification_notes = f"{existing} | {note}".strip(" |")
        if finding.verification_status == VerificationStatus.VERIFIED:
            finding.verification_status = VerificationStatus.PENDING_VERIFICATION
    elif finding.adversarial_reviewed:
        finding.held_from_executive = False
    return finding


def executive_eligible_claims(claims: Iterable[Claim]) -> List[Claim]:
    out = []
    for claim in claims:
        if claim.held_from_executive and not claim.adversarial_reviewed:
            continue
        if (
            claim.confidence_rubric == RubricConfidence.GUESSING
            and claim.materiality == Materiality.CRITICAL
            and not claim.adversarial_reviewed
        ):
            continue
        out.append(claim)
    return out
