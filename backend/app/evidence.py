"""Compatibility shim for migrated evidence packages (transferred to app.domain.evidence)."""
import sys
__path__ = []

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
    models,
    provenance,
    retriever,
    site_facts,
    store,
    taxonomy,
    validation,
)

sys.modules["app.evidence"] = sys.modules[__name__]
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
sys.modules["app.evidence.models"] = models
sys.modules["app.evidence.provenance"] = provenance
sys.modules["app.evidence.retriever"] = retriever
sys.modules["app.evidence.site_facts"] = site_facts
sys.modules["app.evidence.store"] = store
sys.modules["app.evidence.taxonomy"] = taxonomy
sys.modules["app.evidence.validation"] = validation
