"""
Evidence Classification Engine — Enterprise Quality Standard (Phase 0.2)

Enforces mandatory evidence classification across the 8-state enterprise taxonomy,
cryptographic artifact hashing, collection metadata capture, and separation
of record integrity hashing from empirical source provenance.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.domain.enums import EvidenceStatus
from app.domain.canonical_audit_model import EvidenceRecord


class EvidenceClassificationEngine:
    """
    Standardizes raw observations into immutable, classified, content-hashed EvidenceRecords.
    """

    VALID_STATUSES = set(EvidenceStatus)

    @classmethod
    def create_evidence_record(
        cls,
        audit_run_id: str,
        domain_id: str,
        classification: EvidenceStatus,
        source_system: str,
        collection_method: str,
        raw_value: Any,
        expected_condition: Optional[str] = None,
        observed_condition: Optional[str] = None,
        confidence_rationale: str = "Direct observation verified by scanner.",
        page_id: Optional[str] = None,
        url: Optional[str] = None,
        scope: str = "PAGE",
        collection_duration_ms: Optional[int] = None,
        artifact_location: Optional[str] = None,
        provenance_details: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default_tenant",
    ) -> EvidenceRecord:
        """
        Builds a canonical, cryptographically hashed EvidenceRecord.
        """
        if classification not in cls.VALID_STATUSES:
            raise ValueError(f"Invalid EvidenceStatus: {classification}. Must be one of {cls.VALID_STATUSES}")

        # Compute deterministic content SHA-256 hash of the observation payload
        content_bytes = json.dumps(raw_value, sort_keys=True, default=str).encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Build separate provenance record
        provenance = {
            "source_system": source_system,
            "collection_method": collection_method,
            "captured_timestamp": datetime.now(timezone.utc).isoformat(),
            "provenance_verified": classification in (EvidenceStatus.OBSERVED, EvidenceStatus.MEASURED),
            **(provenance_details or {}),
        }

        # Generate unique immutable evidence ID
        evidence_id = f"ev_{uuid.uuid4().hex[:12]}"

        return EvidenceRecord(
            tenant_id=tenant_id,
            audit_run_id=audit_run_id,
            domain_id=domain_id,
            evidence_id=evidence_id,
            page_id=page_id,
            url=url,
            classification=classification,
            collection_method=collection_method,
            source_system=source_system,
            collection_duration_ms=collection_duration_ms,
            scope=scope,
            raw_value=raw_value,
            normalized_value=raw_value,
            expected_condition=expected_condition,
            observed_condition=observed_condition,
            confidence_rationale=confidence_rationale,
            artifact_location=artifact_location,
            content_hash=content_hash,
            hash_validation_status="VALID",
            provenance_details=provenance,
        )

    @staticmethod
    def verify_record_integrity(record: EvidenceRecord) -> Tuple[bool, str]:
        """
        Verifies that record content has not been tampered with since creation.
        Important: Hashing proves integrity of the record itself, not that the external observation was true.
        """
        content_bytes = json.dumps(record.raw_value, sort_keys=True, default=str).encode("utf-8")
        computed_hash = hashlib.sha256(content_bytes).hexdigest()
        if computed_hash != record.content_hash:
            return False, f"Integrity violation: expected {record.content_hash}, calculated {computed_hash}"
        return True, "Record integrity valid."
