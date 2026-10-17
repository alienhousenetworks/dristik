"""Third-party platform connectors, AI search providers, and external authority bridges."""
import sys
from app.connectors import authority
from app.connectors.authority import (
    analyze,
    audit_bridge,
    crypto,
    evidence_bridge,
    http,
    jobs,
    models,
    providers,
    redact,
    registry,
    service,
    store,
    traffic_estimator,
)

sys.modules["app.external_authority"] = authority
sys.modules["app.external_authority.analyze"] = analyze
sys.modules["app.external_authority.audit_bridge"] = audit_bridge
sys.modules["app.external_authority.crypto"] = crypto
sys.modules["app.external_authority.evidence_bridge"] = evidence_bridge
sys.modules["app.external_authority.http"] = http
sys.modules["app.external_authority.jobs"] = jobs
sys.modules["app.external_authority.models"] = models
sys.modules["app.external_authority.providers"] = providers
sys.modules["app.external_authority.redact"] = redact
sys.modules["app.external_authority.registry"] = registry
sys.modules["app.external_authority.service"] = service
sys.modules["app.external_authority.store"] = store
sys.modules["app.external_authority.traffic_estimator"] = traffic_estimator

__all__ = ["authority"]
