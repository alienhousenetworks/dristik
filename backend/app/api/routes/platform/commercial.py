"""Commercial workflow API.

These routes expose the shared evidence, measurement, and outcome contracts.
They do not replace the audit, remediation, or payment routes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user

from app.commercial.evidence_record import StructuredEvidenceRecord
from app.commercial.integrity import IntegritySeal, verify_seal
from app.commercial.measurement import (
    VISIBILITY_METRICS,
    assess_proportion,
    engine_capability_registry,
)
from app.commercial.outcomes import FlywheelObservation, gross_margin_pct, verified_remediation_count
from app.commercial.plans import PLANNING_NOTE, SUBSCRIPTION_HYPOTHESES
from app.commercial.remediation_policy import deployment_decision
from app.commercial.workflow import project_operating_workflow
from app.intelligence.geo.adapters.registry import get_adapter

router = APIRouter(prefix="/commercial", tags=["Commercial product"])


class ProportionRequest(BaseModel):
    successes: int = Field(ge=0)
    trials: int = Field(ge=0)
    target_half_width_pct: float = Field(default=10.0, gt=0, le=50)


class SealRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=1)
    leaf_index: int = 0


class VerifyRequest(BaseModel):
    record: dict[str, Any]
    seal: IntegritySeal


class MarginRequest(BaseModel):
    revenue: float
    direct_service_costs: float


class PatchPolicyRequest(BaseModel):
    title: str = ""
    explanation: str = ""
    after_snippet: str = ""
    operation: str = "REPLACE"
    risk_level: str = "SAFE_AUTO"
    asserts_facts: bool = False
    explicit_production_authorization: bool = False


@router.get("/engines")
async def list_engine_capabilities():
    capabilities = []
    for item in engine_capability_registry():
        payload = item.model_dump()
        adapter = get_adapter(item.engine_id)
        payload["configured"] = bool(adapter and adapter.is_configured()) if adapter else False
        capabilities.append(payload)
    return {
        "engines": capabilities,
        "metrics": list(VISIBILITY_METRICS),
        "rule": "An answer from a model API is not reported as the consumer search product.",
    }


@router.post("/measurement/assess")
async def assess_visibility_sample(req: ProportionRequest):
    try:
        assessment = assess_proportion(
            req.successes,
            req.trials,
            target_half_width_pct=req.target_half_width_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return assessment


@router.post("/workflow")
async def project_workflow(report: dict[str, Any]):
    return project_operating_workflow(report)


@router.post("/integrity/seal")
async def seal_evidence(req: SealRequest, user: UserIdentity = Depends(get_current_user)):
    """Refuse to sign a payload the caller invented.

    Audit sealing happens inside the pipeline, over records the server stored.
    This route stays available so clients learn that limitation instead of
    receiving a signature.
    """
    del req, user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "The server signs only evidence records it produced for an audit in your organization. "
            "It does not sign caller-supplied records."
        ),
    )


@router.post("/integrity/verify")
async def verify_evidence(req: VerifyRequest, user: UserIdentity = Depends(get_current_user)):
    del user
    try:
        record = StructuredEvidenceRecord.model_validate(req.record).canonical_body()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return verify_seal(record, req.seal)


@router.post("/remediation/policy")
async def remediation_policy(req: PatchPolicyRequest):
    patch = type("PatchView", (), {})()
    patch.title = req.title
    patch.explanation = req.explanation
    patch.after_snippet = req.after_snippet
    patch.operation = req.operation
    patch.risk_level = req.risk_level
    patch.metadata_payload = {"asserts_facts": req.asserts_facts}
    return deployment_decision(patch, explicit_production_authorization=req.explicit_production_authorization)


@router.post("/outcomes/flywheel")
async def validate_flywheel(observation: FlywheelObservation):
    return {
        "observation": observation,
        "stored": False,
        "reuse_allowed": observation.reuse_permitted,
        "note": "A record is eligible for reuse only when reuse_permitted is true. Dropping a name does not anonymize it.",
    }


@router.post("/economics/margin")
async def margin(req: MarginRequest):
    value = gross_margin_pct(req.revenue, req.direct_service_costs)
    return {"gross_margin_pct": value, "formula": "(revenue - direct service costs) / revenue"}


@router.post("/economics/verified-remediations")
async def count_verified(records: list[dict[str, Any]]):
    return {"verified_remediations": verified_remediation_count(records)}


@router.get("/plans/hypotheses")
async def plan_hypotheses():
    return {"hypotheses": SUBSCRIPTION_HYPOTHESES, "note": PLANNING_NOTE, "purchasable": False}
