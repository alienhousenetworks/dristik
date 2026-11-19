"""
Dristik AI Independent Verification Engine — Phase 9 (10/10 Transformation)
"""
from __future__ import annotations

import sys

# Backward compatibility imports
from app.remediation.verifier import VerificationEngine, verification_engine
from app.remediation.verification_loop import verification_loop_service
from app.remediation import verifier, verification_loop

sys.modules["app.verification.verifier"] = verifier
sys.modules["app.verification.verification_loop"] = verification_loop

# Phase 9 Canonical Exports
from app.verification.models import (
    VerificationState,
    TestCategory,
    TestExecutionResult,
    MachineAcceptanceCriterion,
    EvidenceComparisonRecord,
    RegressionCheckResult,
    VerificationRunReport,
)
from app.verification.test_registry import (
    VerificationTestRegistry,
    verification_test_registry,
)
from app.verification.acceptance_criteria import (
    AcceptanceCriteriaFactory,
    acceptance_criteria_factory,
)
from app.verification.retester import (
    IndependentRetester,
    independent_retester,
)
from app.verification.regression_engine import (
    CrossDisciplineRegressionEngine,
    cross_discipline_regression_engine,
)
from app.verification.state_machine import (
    VerificationStateMachine,
    verification_state_machine,
)
from app.verification.engine import (
    IndependentVerificationEngine,
    independent_verification_engine,
)

__all__ = [
    # Backward compatibility
    "VerificationEngine",
    "verification_engine",
    "verification_loop_service",
    # Phase 9 Canonical
    "VerificationState",
    "TestCategory",
    "TestExecutionResult",
    "MachineAcceptanceCriterion",
    "EvidenceComparisonRecord",
    "RegressionCheckResult",
    "VerificationRunReport",
    "VerificationTestRegistry",
    "verification_test_registry",
    "AcceptanceCriteriaFactory",
    "acceptance_criteria_factory",
    "IndependentRetester",
    "independent_retester",
    "CrossDisciplineRegressionEngine",
    "cross_discipline_regression_engine",
    "VerificationStateMachine",
    "verification_state_machine",
    "IndependentVerificationEngine",
    "independent_verification_engine",
]
