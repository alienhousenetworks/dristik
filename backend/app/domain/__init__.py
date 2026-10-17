"""Domain contracts: pillars, models, capabilities, enums, errors, multi-engine scoring, and evidence graph."""
import sys

from app.domain import evidence
from app.domain.evidence import (
    acquisition,
    claim_ledger,
    contradiction_detector,
    coverage,
    derived,
    deterministic_rules,
    enrichment,
    evidence_validator,
    fusion,
    graph,
    models as evidence_models,
    provenance,
    retriever,
    site_facts,
    store,
    taxonomy,
    validation,
)

sys.modules["app.evidence"] = evidence
sys.modules["app.evidence.acquisition"] = acquisition
sys.modules["app.evidence.claim_ledger"] = claim_ledger
sys.modules["app.evidence.contradiction_detector"] = contradiction_detector
sys.modules["app.evidence.coverage"] = coverage
sys.modules["app.evidence.derived"] = derived
sys.modules["app.evidence.deterministic_rules"] = deterministic_rules
sys.modules["app.evidence.enrichment"] = enrichment
sys.modules["app.evidence.evidence_validator"] = evidence_validator
sys.modules["app.evidence.fusion"] = fusion
sys.modules["app.evidence.graph"] = graph
sys.modules["app.evidence.models"] = evidence_models
sys.modules["app.evidence.provenance"] = provenance
sys.modules["app.evidence.retriever"] = retriever
sys.modules["app.evidence.site_facts"] = site_facts
sys.modules["app.evidence.store"] = store
sys.modules["app.evidence.taxonomy"] = taxonomy
sys.modules["app.evidence.validation"] = validation

from app.domain.contracts import PillarExecutionRequest
from app.domain.exceptions import DomainError, PillarNotFound, UnmeasuredDependency
from app.domain.pillar import DomainPillar, PillarId, PillarScoreResult

from app.domain import scoring
from app.domain.scoring import (
    calibration,
    calibration_v5,
    config_v5,
    curves,
    displayed_score,
    engine,
    score_explanations,
    scoring_rubric,
    weights,
)

sys.modules["app.scoring"] = scoring
sys.modules["app.scoring.calibration"] = calibration
sys.modules["app.scoring.calibration_v5"] = calibration_v5
sys.modules["app.scoring.config_v5"] = config_v5
sys.modules["app.scoring.curves"] = curves
sys.modules["app.scoring.displayed_score"] = displayed_score
sys.modules["app.scoring.engine"] = engine
sys.modules["app.scoring.score_explanations"] = score_explanations
sys.modules["app.scoring.scoring_rubric"] = scoring_rubric
sys.modules["app.scoring.weights"] = weights

from app.domain import commercial
sys.modules["app.commercial"] = commercial

__all__ = [
    "DomainError",
    "DomainPillar",
    "PillarExecutionRequest",
    "PillarId",
    "PillarNotFound",
    "PillarScoreResult",
    "UnmeasuredDependency",
    "scoring",
    "evidence",
    "commercial",
]

