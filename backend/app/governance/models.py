"""Data models for Phase 12 Enterprise-Grade Scoring, Security, and Quality Assurance."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScoringCategory(str, Enum):
    TECHNICAL_HEALTH = "TECHNICAL_HEALTH"
    CONTENT_READINESS = "CONTENT_READINESS"
    OBSERVED_VISIBILITY = "OBSERVED_VISIBILITY"
    USER_EXPERIENCE = "USER_EXPERIENCE"
    BUSINESS_PERFORMANCE = "BUSINESS_PERFORMANCE"
    COMPETITIVE_POSITIONING = "COMPETITIVE_POSITIONING"


class MetricDirection(str, Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


class RemediationPriority(str, Enum):
    P1 = "P1"  # Immediate Blocker / Live Risk
    P2 = "P2"  # High Urgency / Next Sprint
    P3 = "P3"  # Scheduled Sprint Roadmap
    P4 = "P4"  # Routine Maintenance / Nice-to-Have
    P5 = "P5"  # Informational / Low Impact


@dataclass
class MetricDefinition:
    """Canonical specification of a shared enterprise metric."""
    metric_id: str
    name: str
    category: ScoringCategory
    definition: str
    formula: str
    source: str
    required_inputs: list[str]
    benchmark_target: float
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER
    missing_data_handling: str = "UNMEASURED"
    version: str = "v1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "category": self.category.value,
            "definition": self.definition,
            "formula": self.formula,
            "source": self.source,
            "required_inputs": self.required_inputs,
            "benchmark_target": self.benchmark_target,
            "direction": self.direction.value,
            "missing_data_handling": self.missing_data_handling,
            "version": self.version,
        }


@dataclass
class SampledMetricRecord:
    """Statistical sampling metadata tracking uncertainty and empirical bounds."""
    metric_id: str
    measured_value: float
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    sample_size: int = 1
    population_size: Optional[int] = None
    population_definition: str = "All crawlable HTML pages within domain boundary"
    sampling_method: str = "EXHAUSTIVE_CRAWL"  # or RANDOM_SYSTEMATIC, STRATIFIED_TEMPLATE
    sampling_date: datetime = field(default_factory=_utcnow)
    standard_error: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    confidence_rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "measured_value": self.measured_value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "sample_size": self.sample_size,
            "population_size": self.population_size,
            "population_definition": self.population_definition,
            "sampling_method": self.sampling_method,
            "sampling_date": self.sampling_date.isoformat(),
            "standard_error": self.standard_error,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence_rationale": self.confidence_rationale,
        }


@dataclass
class SeverityFactor:
    """Multi-factor parameters governing technical severity calculation."""
    defect_scope: str = "SINGLE_PAGE"  # SINGLE_PAGE, TEMPLATE_CLUSTER, SITEWIDE
    technical_consequence: float = 0.5  # 0.0 - 1.0 (fatal crash, 5xx, or minor syntax)
    user_impact: float = 0.5  # 0.0 - 1.0 (broken checkout vs cosmetic layout)
    business_importance: float = 0.5  # 0.0 - 1.0 (revenue transaction vs policy page)
    search_impact: float = 0.5  # 0.0 - 1.0 (de-indexation vs snippet truncation)
    security_relevance: float = 0.0  # 0.0 - 1.0 (vulnerability vs zero security impact)
    frequency: float = 0.1  # occurrence proportion across inspected pages
    confidence: float = 1.0  # 1.0 verified, 0.7 inferred


@dataclass
class SeverityEvaluation:
    """Decoupled severity rating and remediation prioritization."""
    finding_id: str
    raw_severity_score: float  # 0 - 100
    severity_level: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    remediation_priority: RemediationPriority
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "raw_severity_score": self.raw_severity_score,
            "severity_level": self.severity_level,
            "remediation_priority": self.remediation_priority.value,
            "explanation": self.explanation,
        }


@dataclass
class AdversarialReviewCheck:
    """Single test executed during independent adversarial review."""
    __test__ = False  # Prevent Pytest collection warning
    check_id: str
    question: str
    passed: bool
    finding_id: Optional[str] = None
    evidence_id: Optional[str] = None
    infraction_type: Optional[str] = None
    critic_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "question": self.question,
            "passed": self.passed,
            "finding_id": self.finding_id,
            "evidence_id": self.evidence_id,
            "infraction_type": self.infraction_type,
            "critic_notes": self.critic_notes,
        }


@dataclass
class AdversarialReviewVerdict:
    """Certification result of independent adversarial critic review."""
    report_id: str
    audit_id: str
    checks_executed: int
    infractions_found: list[AdversarialReviewCheck] = field(default_factory=list)
    passed: bool = True
    certified_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "audit_id": self.audit_id,
            "checks_executed": self.checks_executed,
            "infractions_found": [c.to_dict() for c in self.infractions_found],
            "passed": self.passed,
            "certified_at": self.certified_at.isoformat(),
        }


@dataclass
class BenchmarkSiteProfile:
    """Archetype profile for regression and calibration benchmarking."""
    __test__ = False  # Prevent Pytest collection warning
    profile_id: str
    archetype_name: str
    site_type: str
    cms: str
    expected_score_ranges: dict[str, tuple[float, float]]
    known_defects: list[str]
    sample_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "archetype_name": self.archetype_name,
            "site_type": self.site_type,
            "cms": self.cms,
            "expected_score_ranges": {k: list(v) for k, v in self.expected_score_ranges.items()},
            "known_defects": self.known_defects,
        }


@dataclass
class ScoringAlgorithmSpecification:
    """Complete mathematical specification of the enterprise scoring engine."""
    title: str = "Enterprise Scoring Algorithm & Rating Specification"
    version: str = "v12.0-Enterprise"
    scoring_categories: list[str] = field(default_factory=list)
    rating_tiers: dict[str, str] = field(default_factory=dict)
    weight_distribution: dict[str, dict[str, float]] = field(default_factory=dict)
    penalty_curve_formula: str = ""
    unmeasured_isolation_rules: list[str] = field(default_factory=list)
    markdown_documentation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "scoring_categories": self.scoring_categories,
            "rating_tiers": self.rating_tiers,
            "weight_distribution": self.weight_distribution,
            "penalty_curve_formula": self.penalty_curve_formula,
            "unmeasured_isolation_rules": self.unmeasured_isolation_rules,
            "markdown_documentation": self.markdown_documentation,
        }
