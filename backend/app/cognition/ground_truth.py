"""
External Ground-Truth Enrichment (v4)

Before a claim about ICP / pricing / performance / trust / authorship is
finalized, bind it to the ext_xxx feed:

- CONFIRMS  → cite ev_xxx + ext_xxx, confidence HIGH, CORROBORATED
- CONTRADICTS → status CONTESTED, cite both, do not pick a winner;
                route to verification.contradiction.v3
- no usable ext_xxx for that family → MEDIUM at best, SINGLE_SOURCE_UNVERIFIED

NOT_CONFIGURED / empty stubs are not usable ground truth.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.domain.enums import (
    ClaimFamily,
    ClaimState,
    ConfidenceBand,
    EvidenceLevel,
    GroundTruthRelation,
    SourceIntegrityLabel,
    VerificationStatus,
)
from app.domain.models import Claim, Contradiction
from app.evidence.models import Evidence
from app.evidence.store import EvidenceStore

CONTRADICTION_AGENT_ID = "verification.contradiction.v3"
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE_CAP = 0.70

GATED_AGENT_FAMILIES: Dict[str, ClaimFamily] = {
    "business.icp.v3": ClaimFamily.ICP,
    "business.discovery.v3": ClaimFamily.ICP,
    "business.commercial.v3": ClaimFamily.PRICING,
    "seo.performance.v3": ClaimFamily.PERFORMANCE,
    "trust.authority.v3": ClaimFamily.TRUST,
    "content.eeat.v3": ClaimFamily.AUTHORSHIP,
}

FAMILY_KEYWORDS: Dict[ClaimFamily, Tuple[str, ...]] = {
    ClaimFamily.ICP: (
        "icp", "buyer", "audience", "company size", "employee", "employees",
        "enterprise", "smb", "mid-market", "b2b", "b2c", "ideal customer",
        "target customer", "org scale", "headcount",
    ),
    ClaimFamily.PRICING: (
        "price", "pricing", "plan", "cost", "currency", "checkout", "inr",
        "usd", "₹", "$", "fee", "tier", "not_in_evidence",
    ),
    ClaimFamily.PERFORMANCE: (
        "lcp", "inp", "cls", "cwv", "ttfb", "core web vital", "crux",
        "largest contentful", "payload", "performance",
    ),
    ClaimFamily.TRUST: (
        "testimonial", "review", "rating", "trustpilot", "g2", "capterra",
        "social proof", "trust", "authority", "google business", "ambitionbox",
    ),
    ClaimFamily.AUTHORSHIP: (
        "author", "eeat", "e-e-a-t", "credential", "byline", "editorial",
        "about page", "first-hand",
    ),
}

FAMILY_EXT_SOURCES: Dict[ClaimFamily, Set[str]] = {
    ClaimFamily.ICP: {"linkedin", "clearbit", "crunchbase", "builtwith"},
    ClaimFamily.PRICING: {"linkedin", "g2", "capterra", "inferred_jurisdiction", "crunchbase"},
    ClaimFamily.PERFORMANCE: {"crux"},
    ClaimFamily.TRUST: {
        "g2", "capterra", "trustpilot", "google_business_profile", "ambitionbox",
    },
    ClaimFamily.AUTHORSHIP: {"linkedin", "crunchbase"},
}

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


def classify_claim_family(claim: Claim) -> Optional[ClaimFamily]:
    mapped = GATED_AGENT_FAMILIES.get(claim.agent_id)
    if mapped:
        if mapped == ClaimFamily.ICP and claim.agent_id == "business.discovery.v3":
            text = (claim.statement or "").lower()
            if not any(k in text for k in FAMILY_KEYWORDS[ClaimFamily.ICP]):
                return None
        return mapped
    text = (claim.statement or "").lower()
    for family, keywords in FAMILY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return family
    return None


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def is_usable_external(ev: Evidence) -> bool:
    if not (ev.id or "").startswith("ext_"):
        return False
    payload = _as_dict(ev.value)
    status = str(payload.get("status") or (ev.metadata or {}).get("status") or "").upper()
    if status in _STUB_STATUSES:
        return False
    return True


def external_source_name(ev: Evidence) -> str:
    meta = ev.metadata or {}
    payload = _as_dict(ev.value)
    return str(meta.get("source") or payload.get("source") or ev.analyzer or "").lower()


def external_conflicts_with(ev: Evidence) -> List[str]:
    meta = ev.metadata or {}
    payload = _as_dict(ev.value)
    raw = meta.get("conflicts_with") or payload.get("conflicts_with") or []
    if isinstance(raw, str):
        return [raw]
    return [str(x) for x in raw if x]


def get_external_feed(store: EvidenceStore) -> List[Evidence]:
    return [ev for ev in store.get_all() if (ev.id or "").startswith("ext_")]


def usable_ext_for_family(store: EvidenceStore, family: ClaimFamily) -> List[Evidence]:
    allowed = FAMILY_EXT_SOURCES.get(family, set())
    out: List[Evidence] = []
    for ev in get_external_feed(store):
        if not is_usable_external(ev):
            continue
        src = external_source_name(ev)
        if src in allowed or not src:
            # Unnamed usable ext still counts if the family has any feed at all
            if src in allowed:
                out.append(ev)
    return out


def _relation_for(claim: Claim, ext_items: Sequence[Evidence]) -> GroundTruthRelation:
    dom_refs = {r for r in (claim.evidence_refs or []) if str(r).startswith("ev_")}
    for ev in ext_items:
        conflicts = set(external_conflicts_with(ev))
        if conflicts & dom_refs:
            return GroundTruthRelation.CONTRADICTS
        if conflicts and not dom_refs:
            # Ext recorded a DOM conflict even if this claim omitted the ev id.
            return GroundTruthRelation.CONTRADICTS
    return GroundTruthRelation.CONFIRMS


def apply_ground_truth_to_claim(
    claim: Claim,
    store: EvidenceStore,
    registry=None,
) -> Claim:
    family = classify_claim_family(claim)
    if family is None:
        claim.source_integrity_label = SourceIntegrityLabel.NOT_APPLICABLE
        claim.ground_truth_relation = GroundTruthRelation.NOT_APPLICABLE
        claim.claim_family = None
        from app.cognition.finding_rubric import apply_rubric_to_claim
        apply_rubric_to_claim(claim, store)
        return claim

    claim.claim_family = family
    ext_items = usable_ext_for_family(store, family)

    if not ext_items:
        claim.ground_truth_relation = GroundTruthRelation.MISSING_EXTERNAL
        claim.source_integrity_label = SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
        claim.confidence_band = ConfidenceBand.MEDIUM
        if claim.confidence > MEDIUM_CONFIDENCE_CAP:
            claim.confidence = MEDIUM_CONFIDENCE_CAP
        if claim.verification_status not in {
            VerificationStatus.REJECTED,
            VerificationStatus.CONTESTED,
            VerificationStatus.CONFLICTED,
        }:
            claim.verification_status = VerificationStatus.SINGLE_SOURCE_UNVERIFIED
        claim.claim_state = ClaimState.SINGLE_SOURCE_UNVERIFIED
        note = "SINGLE_SOURCE_UNVERIFIED: no usable ext_xxx for this claim family; DOM-only, confidence capped at MEDIUM."
        claim.verification_notes = _merge_note(claim.verification_notes, note)
        from app.cognition.finding_rubric import apply_rubric_to_claim
        apply_rubric_to_claim(claim, store)
        return claim

    relation = _relation_for(claim, ext_items)
    ext_ids = [ev.id for ev in ext_items]
    claim.evidence_refs = _unique(list(claim.evidence_refs or []) + ext_ids)

    if relation == GroundTruthRelation.CONFIRMS:
        claim.ground_truth_relation = GroundTruthRelation.CONFIRMS
        claim.source_integrity_label = SourceIntegrityLabel.CORROBORATED
        claim.confidence_band = ConfidenceBand.HIGH
        claim.confidence = max(float(claim.confidence or 0), HIGH_CONFIDENCE)
        claim.evidence_level = EvidenceLevel.E6_CORROBORATED
        if claim.verification_status == VerificationStatus.PROVISIONAL:
            claim.verification_status = VerificationStatus.PARTIALLY_VERIFIED
        claim.claim_state = ClaimState.SOURCE_VALIDATED
        claim.verification_notes = _merge_note(
            claim.verification_notes,
            f"CORROBORATED by external feed {ext_ids}; cite ev_xxx + ext_xxx; confidence HIGH.",
        )
        from app.cognition.finding_rubric import apply_rubric_to_claim
        apply_rubric_to_claim(claim, store)
        return claim

    # CONTRADICTS — do not pick a winner
    claim.ground_truth_relation = GroundTruthRelation.CONTRADICTS
    claim.source_integrity_label = SourceIntegrityLabel.CONTESTED
    claim.verification_status = VerificationStatus.CONTESTED
    claim.claim_state = ClaimState.CONTESTED
    claim.routed_to = CONTRADICTION_AGENT_ID
    claim.verification_notes = _merge_note(
        claim.verification_notes,
        (
            f"CONTESTED: external feed {ext_ids} contradicts DOM evidence. "
            f"Cited both token classes. Routed to {CONTRADICTION_AGENT_ID}; winner not selected."
        ),
    )
    if registry is not None:
        _ensure_contested_contradiction(registry, claim, ext_ids)
    from app.cognition.finding_rubric import apply_rubric_to_claim
    apply_rubric_to_claim(claim, store)
    return claim


def apply_ground_truth_feed(claims: Iterable[Claim], store: EvidenceStore, registry=None) -> List[Claim]:
    applied = []
    for claim in claims:
        applied.append(apply_ground_truth_to_claim(claim, store, registry))
    return applied


def _ensure_contested_contradiction(registry, claim: Claim, ext_ids: List[str]) -> Optional[Contradiction]:
    desc = (
        f"DOM vs external ground truth on {claim.claim_family.value if claim.claim_family else 'claim'}: "
        f"{claim.id} cites {claim.evidence_refs}."
    )
    existing = registry.get_contradictions() if hasattr(registry, "get_contradictions") else []
    for contra in existing:
        if contra.claim_a_id == claim.id and contra.routed_to == CONTRADICTION_AGENT_ID:
            return contra
    return registry.register_contradiction(
        claim_a_id=claim.id,
        claim_b_id=claim.id,
        description=desc,
        resolution=f"ROUTED_TO_{CONTRADICTION_AGENT_ID}",
        winner_claim_id=None,
        routed_to=CONTRADICTION_AGENT_ID,
        ext_refs=ext_ids,
    )


def _unique(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _merge_note(existing: Optional[str], addition: str) -> str:
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f"{existing} | {addition}"
