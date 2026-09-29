"""
Dristik AI Canonical Finding Registry
======================================
Thread-safe, per-run canonical store for all audit findings.

Key guarantees:
  - Deduplicate by canonical_id = (category, rule_id) to prevent multiple agents
    emitting the same finding class.
  - Enforce lifecycle state machine: OPEN → ACKNOWLEDGED → RECOMMENDED →
    PATCH_READY → APPROVED → APPLIED → VALIDATED / REGRESSED.
  - Translate legacy RubricConfidence.GUESSING → LOW_CONFIDENCE so that the
    word "GUESSING" is never surfaced in any downstream artifact.
  - Gate hypotheses (LOW_CONFIDENCE, UNVERIFIED) from executive-level score
    deductions while keeping them in the exploratory section.
  - Expose `executive_findings()` vs `hypothesis_findings()` views.

Thread safety: all mutations are protected by a re-entrant lock so the registry
can be safely updated from concurrent agent coroutines inside a single run.
"""
from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.domain.enums import (
    FindingLifecycle,
    RubricConfidence,
    Severity,
    Category,
)
from app.domain.models import Finding, SubObservation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical_id(finding: Finding) -> str:
    """
    Generate a stable canonical root-cause ID.
    Two findings map to the same canonical_id iff they address the same structural defect,
    even if reported by different agents, across different surfaces, or categorized under
    different pillars.
    """
    norm_text = f"{finding.title} {finding.description} {getattr(finding, 'finding', '')}".lower()
    rule = finding.rule_id or ""
    if rule == "entity_graph_contradiction":
        return f"root_schema_identity_contradiction_{finding.finding_id}"
    if rule == "entity_graph_incomplete":
        return "root_schema_entity_graph_incomplete"
    if rule == "entity_graph_contact":
        return "root_schema_contact_details"
    if rule == "entity_graph_applicability":
        return "root_schema_applicable_type_absent"

    # Align with authoritative Root Cause Clusters
    from app.remediation.deduplicator import ROOT_CAUSE_CLUSTERS
    for cluster in ROOT_CAUSE_CLUSTERS:
        if any(kw in norm_text for kw in cluster["keywords"]):
            return f"root_{cluster['id'].lower()}"

    # 1. Structural Archetype Clustering - Heading & Identity
    if ("h1" in norm_text or "headline" in norm_text) and (
        "slogan" in norm_text or "tagline" in norm_text or ("identity" in norm_text and "h1" in norm_text)
    ):
        return "root_h1_identity_slogan_mismatch"

    if ("missing" in norm_text or "no h1" in norm_text or "lacks an h1" in norm_text or "without an h1" in norm_text) and "h1" in norm_text:
        return "root_h1_missing"

    if "multiple h1" in norm_text or "duplicate h1" in norm_text or "more than one h1" in norm_text:
        return "root_h1_multiple"

    if ("skip" in norm_text or "hierarchy" in norm_text or "non-hierarchical" in norm_text) and (
        "heading" in norm_text or "h2" in norm_text or "h3" in norm_text
    ):
        return "root_heading_hierarchy_skip"

    # 2. Security Headers (must evaluate BEFORE generic header/meta rules)
    if "hsts" in norm_text or "strict-transport-security" in norm_text:
        return "root_security_hsts_missing"

    if "csp" in norm_text or "content-security-policy" in norm_text:
        return "root_security_csp_missing"

    if "x-frame-options" in norm_text or "clickjacking" in norm_text:
        return "root_security_x_frame_options_missing"

    if "x-content-type-options" in norm_text or "mime-sniffing" in norm_text or "nosniff" in norm_text:
        return "root_security_nosniff_missing"

    if "not https" in norm_text or "insecure http" in norm_text or "ssl" in norm_text:
        return "root_security_ssl_tls_missing"

    # 3. Crawl & Indexing Architecture
    if "robots.txt" in norm_text and ("missing" in norm_text or "not found" in norm_text):
        return "root_crawl_robots_txt_missing"

    if "sitemap" in norm_text and ("missing" in norm_text or "not found" in norm_text):
        return "root_crawl_sitemap_missing"

    if ("gptbot" in norm_text or "claudebot" in norm_text or "perplexitybot" in norm_text) and ("block" in norm_text or "directive" in norm_text):
        return "root_ai_crawler_bot_directives"

    if "canonical" in norm_text and ("missing" in norm_text or "no rel=canonical" in norm_text or "lacks a canonical" in norm_text):
        return "root_canonical_tag_missing"

    if "canonical" in norm_text and ("mismatch" in norm_text or "points to" in norm_text or "conflict" in norm_text):
        return "root_canonical_tag_mismatch"

    if "noindex" in norm_text:
        return "root_indexability_unintended_noindex"

    # 4. Media & Assets
    if "alt" in norm_text and ("image" in norm_text or "img" in norm_text or "asset" in norm_text or "missing" in norm_text):
        return "root_media_missing_alt_attributes"

    # 5. Schema & Structured Data
    if ("schema" in norm_text or "json-ld" in norm_text or "structured data" in norm_text) and ("missing" in norm_text or "no " in norm_text or "not parsed" in norm_text):
        return "root_schema_knowledge_graph_missing"

    if "sameas" in norm_text or "entity clarity" in norm_text or "unlinked entity" in norm_text:
        return "root_schema_entity_disambiguation"

    # 6. Metadata Quality
    if "meta description" in norm_text and ("missing" in norm_text or "no meta" in norm_text or "not found" in norm_text):
        return "root_meta_description_missing"

    if "meta description" in norm_text and ("short" in norm_text or "long" in norm_text or "length" in norm_text or "truncate" in norm_text):
        return "root_meta_description_quality"

    if ("missing" in norm_text or "no title" in norm_text) and ("title tag" in norm_text or "page title" in norm_text):
        return "root_title_tag_missing"

    if "title tag" in norm_text or ("page title" in norm_text and ("short" in norm_text or "duplicate" in norm_text or "long" in norm_text or "length" in norm_text)):
        return "root_title_tag_optimization"

    # 7. UX, CRO & Ergonomics
    if "form" in norm_text and ("label" in norm_text or "captcha" in norm_text or "submission" in norm_text or "wcag" in norm_text or "friction" in norm_text):
        return "root_form_accessibility_friction"

    if ("cta" in norm_text or "call to action" in norm_text or "3-second hook" in norm_text) and ("missing" in norm_text or "weak" in norm_text):
        return "root_cro_primary_cta_hook"

    if "click depth" in norm_text or "orphan" in norm_text or "inlink" in norm_text:
        return "root_architecture_crawl_depth"

    if "contrast" in norm_text or "readability" in norm_text or "wcag" in norm_text or "font" in norm_text:
        return "root_visual_accessibility_contrast"

    if "ttfb" in norm_text or "core web vitals" in norm_text or "latency" in norm_text or "lcp" in norm_text:
        return "root_server_latency_performance"

    if "redirect" in norm_text or "301" in norm_text or "canonical host" in norm_text or "www" in norm_text or "hop" in norm_text:
        return "root_host_redirection_consolidation"

    if finding.rule_id:
        return f"root_rule_{finding.rule_id}"

    # 8. Generic normalized stem clustering fallback
    norm_title = "".join(c for c in finding.title.lower() if c.isalnum() or c == " ").strip()
    words = [w for w in norm_title.split() if len(w) > 3][:4]
    stem = "_".join(words) or "generic"
    return "root_" + hashlib.sha1(f"{finding.category.value}::{stem}".encode()).hexdigest()[:12]


def _normalise_confidence(f: Finding) -> Finding:
    """
    Ensure customer display label is populated while preserving canonical RubricConfidence enum.
    The customer label maps GUESSING -> LOW_CONFIDENCE, LIKELY -> HIGH_CONFIDENCE, CERTAIN -> VERIFIED.
    """
    rubric = getattr(f, "confidence_rubric", None)
    if rubric is None:
        return f
    if not getattr(f, "confidence_display_label", None) and hasattr(rubric, "customer_label"):
        return f.model_copy(update={"confidence_display_label": rubric.customer_label})
    return f


# ---------------------------------------------------------------------------
# Registry entry
# ---------------------------------------------------------------------------

class RegistryEntry:
    """
    Wraps a canonical Finding with lifecycle metadata.
    """
    __slots__ = (
        "canonical_id",
        "finding",
        "lifecycle",
        "duplicate_ids",
        "registered_at",
        "last_updated_at",
        "patch_id",
        "blocked_reason",
    )

    def __init__(self, canonical_id: str, finding: Finding) -> None:
        self.canonical_id = canonical_id
        self.finding = finding
        self.lifecycle: FindingLifecycle = FindingLifecycle.OPEN
        self.duplicate_ids: List[str] = []      # finding_ids subsumed into this entry
        self.registered_at: datetime = datetime.now(timezone.utc)
        self.last_updated_at: datetime = self.registered_at
        self.patch_id: Optional[str] = None
        self.blocked_reason: Optional[str] = None

    def _touch(self) -> None:
        self.last_updated_at = datetime.now(timezone.utc)

    # --- Lifecycle transitions -----------------------------------------------

    def acknowledge(self) -> None:
        if self.lifecycle == FindingLifecycle.OPEN:
            self.lifecycle = FindingLifecycle.ACKNOWLEDGED
            self._touch()

    def recommend(self) -> None:
        if self.lifecycle in (FindingLifecycle.OPEN, FindingLifecycle.ACKNOWLEDGED):
            self.lifecycle = FindingLifecycle.RECOMMENDED
            self._touch()

    def mark_patch_ready(self, patch_id: str) -> None:
        self.patch_id = patch_id
        self.lifecycle = FindingLifecycle.PATCH_READY
        self._touch()

    def approve(self) -> None:
        if self.lifecycle in (FindingLifecycle.PATCH_READY, FindingLifecycle.RECOMMENDED):
            self.lifecycle = FindingLifecycle.APPROVED
            self._touch()

    def mark_applied(self) -> None:
        self.lifecycle = FindingLifecycle.APPLIED
        self._touch()

    def validate(self) -> None:
        self.lifecycle = FindingLifecycle.VALIDATED
        self._touch()

    def regress(self) -> None:
        self.lifecycle = FindingLifecycle.REGRESSED
        self._touch()

    def block(self, reason: str) -> None:
        self.lifecycle = FindingLifecycle.BLOCKED
        self.blocked_reason = reason
        self._touch()

    # --- Classification -------------------------------------------------------

    @property
    def is_hypothesis(self) -> bool:
        """True → LOW_CONFIDENCE / UNVERIFIED; should go to exploratory section."""
        rubric = getattr(self.finding, "confidence_rubric", None)
        if rubric is None:
            return False
        return getattr(rubric, "is_hypothesis", False)

    @property
    def affects_score(self) -> bool:
        """True → directly feeds category score deductions."""
        rubric = getattr(self.finding, "confidence_rubric", None)
        if rubric is None:
            return True
        return getattr(rubric, "affects_score", True)

    # --- Serialisation --------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "finding_id": self.finding.finding_id,
            "lifecycle": self.lifecycle.value,
            "is_hypothesis": self.is_hypothesis,
            "affects_score": self.affects_score,
            "patch_id": self.patch_id,
            "blocked_reason": self.blocked_reason,
            "duplicate_ids": self.duplicate_ids,
            "registered_at": self.registered_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Finding Registry
# ---------------------------------------------------------------------------

class FindingRegistry:
    """
    Per-run canonical finding store.

    Usage::

        registry = FindingRegistry(run_id="run_abc")
        registry.register(finding_obj)           # idempotent
        ...
        exec_findings = registry.executive_findings()
        hypotheses    = registry.hypothesis_findings()
    """

    def __init__(self, run_id: str = "run_default") -> None:
        self.run_id = run_id
        self._lock = threading.RLock()
        # canonical_id → RegistryEntry
        self._entries: Dict[str, RegistryEntry] = {}
        # finding_id → canonical_id (for fast look-up)
        self._id_index: Dict[str, str] = {}

    # --- Mutation ------------------------------------------------------------

    def register(self, finding: Finding, *, auto_acknowledge: bool = True) -> Tuple[RegistryEntry, bool]:
        """
        Register a finding.

        Returns
        -------
        (entry, is_new)
            is_new is True when this is the first finding for a canonical_id.
            If False the incoming finding is recorded as a duplicate and its affected
            surfaces and evidence tokens are consolidated into the canonical entry.
        """
        finding = _normalise_confidence(finding)
        cid = _canonical_id(finding)

        with self._lock:
            if cid in self._entries:
                entry = self._entries[cid]
                if finding.finding_id not in entry.duplicate_ids:
                    entry.duplicate_ids.append(finding.finding_id)
                    self._id_index[finding.finding_id] = cid

                existing = entry.finding
                surfaces = list(getattr(existing, "surfaces_affected", []) or [])

                # Consolidate directly specified surfaces on incoming finding
                for surf in (getattr(finding, "surfaces_affected", []) or []):
                    if not any(
                        s.get("surface") == surf.get("surface") and s.get("url") == surf.get("url")
                        for s in surfaces
                    ):
                        surfaces.append(surf)

                # Consolidate affected surfaces from incoming finding evidence
                for ev in (finding.evidence or []):
                    surf_name = ev.element or ev.selector or "Affected Element"
                    if not any(s.get("selector") == ev.selector and s.get("url") == ev.url for s in surfaces):
                        surfaces.append({
                            "surface": surf_name[:70],
                            "url": ev.url,
                            "selector": ev.selector,
                            "details": (ev.snippet or ev.value or "")[:120] or None,
                        })

                # Combine evidence tokens and references
                combined_refs = list(set(existing.evidence_refs + finding.evidence_refs))
                seen_ev_ids = {e.evidence_id for e in existing.evidence if e.evidence_id}
                combined_ev = list(existing.evidence)
                for e in finding.evidence:
                    if not e.evidence_id or e.evidence_id not in seen_ev_ids:
                        combined_ev.append(e)
                        if e.evidence_id:
                            seen_ev_ids.add(e.evidence_id)

                # Consolidate sub-observations and detailed observations
                sub_obs = list(getattr(existing, "sub_observations", []) or [])
                if not sub_obs:
                    sub_obs = [existing.title]
                if finding.title not in sub_obs:
                    sub_obs.append(finding.title)

                detailed_obs = list(getattr(existing, "detailed_observations", []) or [])
                if not detailed_obs:
                    p_ev = existing.evidence[0] if (existing.evidence and len(existing.evidence) > 0) else None
                    detailed_obs.append(SubObservation(
                        observation_id=existing.finding_id,
                        title=existing.title,
                        description=existing.description or getattr(existing, "finding", "") or existing.title,
                        selector=p_ev.selector if p_ev and p_ev.selector else (p_ev.element if p_ev else None),
                        snippet=(p_ev.snippet or p_ev.value) if p_ev else None,
                        url=p_ev.url if p_ev else None,
                        severity=existing.severity,
                        category=existing.category,
                        evidence_refs=existing.evidence_refs or []
                    ))

                in_p_ev = finding.evidence[0] if (finding.evidence and len(finding.evidence) > 0) else None
                detailed_obs.append(SubObservation(
                    observation_id=finding.finding_id,
                    title=finding.title,
                    description=finding.description or getattr(finding, "finding", "") or finding.title,
                    selector=in_p_ev.selector if in_p_ev and in_p_ev.selector else (in_p_ev.element if in_p_ev else None),
                    snippet=(in_p_ev.snippet or in_p_ev.value) if in_p_ev else None,
                    url=in_p_ev.url if in_p_ev else None,
                    severity=finding.severity,
                    category=finding.category,
                    evidence_refs=finding.evidence_refs or []
                ))

                # Upgrade severity to the highest
                best_severity = existing.severity
                if self._severity_rank(finding.severity) > self._severity_rank(existing.severity):
                    best_severity = finding.severity

                best_impact = max(existing.impact or 5, finding.impact or 5)

                entry.finding = existing.model_copy(update={
                    "severity": best_severity,
                    "impact": best_impact,
                    "surfaces_affected": surfaces,
                    "evidence_refs": combined_refs,
                    "evidence": combined_ev,
                    "sub_observations": sub_obs,
                    "detailed_observations": detailed_obs,
                })
                return entry, False
            else:
                initial_surfaces = list(getattr(finding, "surfaces_affected", []) or [])
                for ev in (finding.evidence or []):
                    surf_name = ev.element or ev.selector or "Affected Element"
                    if not any(s.get("selector") == ev.selector and s.get("url") == ev.url for s in initial_surfaces):
                        initial_surfaces.append({
                            "surface": surf_name[:70],
                            "url": ev.url,
                            "selector": ev.selector,
                            "details": (ev.snippet or ev.value or "")[:120] or None,
                        })

                init_sub = list(getattr(finding, "sub_observations", []) or [])
                if not init_sub:
                    init_sub = [finding.title]
                init_detailed = list(getattr(finding, "detailed_observations", []) or [])
                if not init_detailed:
                    p_ev = finding.evidence[0] if (finding.evidence and len(finding.evidence) > 0) else None
                    init_detailed = [SubObservation(
                        observation_id=finding.finding_id,
                        title=finding.title,
                        description=finding.description or getattr(finding, "finding", "") or finding.title,
                        selector=p_ev.selector if p_ev and p_ev.selector else (p_ev.element if p_ev else None),
                        snippet=(p_ev.snippet or p_ev.value) if p_ev else None,
                        url=p_ev.url if p_ev else None,
                        severity=finding.severity,
                        category=finding.category,
                        evidence_refs=finding.evidence_refs or []
                    )]

                finding = finding.model_copy(update={
                    "surfaces_affected": initial_surfaces,
                    "sub_observations": init_sub,
                    "detailed_observations": init_detailed,
                })
                entry = RegistryEntry(canonical_id=cid, finding=finding)
                self._entries[cid] = entry
                self._id_index[finding.finding_id] = cid
                if auto_acknowledge:
                    entry.acknowledge()
                return entry, True

    def get_by_finding_id(self, finding_id: str) -> Optional[RegistryEntry]:
        cid = self._id_index.get(finding_id)
        if cid:
            return self._entries.get(cid)
        return None

    def get_by_canonical_id(self, canonical_id: str) -> Optional[RegistryEntry]:
        return self._entries.get(canonical_id)

    def transition(self, finding_id: str, target_lifecycle: FindingLifecycle, **kwargs) -> bool:
        """
        Advance the lifecycle of a finding by its finding_id.
        Returns True if the transition succeeded.
        """
        entry = self.get_by_finding_id(finding_id)
        if not entry:
            return False
        with self._lock:
            if target_lifecycle == FindingLifecycle.ACKNOWLEDGED:
                entry.acknowledge()
            elif target_lifecycle == FindingLifecycle.RECOMMENDED:
                entry.recommend()
            elif target_lifecycle == FindingLifecycle.PATCH_READY:
                entry.mark_patch_ready(kwargs.get("patch_id", ""))
            elif target_lifecycle == FindingLifecycle.APPROVED:
                entry.approve()
            elif target_lifecycle == FindingLifecycle.APPLIED:
                entry.mark_applied()
            elif target_lifecycle == FindingLifecycle.VALIDATED:
                entry.validate()
            elif target_lifecycle == FindingLifecycle.REGRESSED:
                entry.regress()
            elif target_lifecycle == FindingLifecycle.BLOCKED:
                entry.block(kwargs.get("reason", "No reason provided"))
        return True

    # --- Views ---------------------------------------------------------------

    def all_findings(self) -> List[Finding]:
        with self._lock:
            return [e.finding for e in self._entries.values()]

    def all_entries(self) -> List[RegistryEntry]:
        with self._lock:
            return list(self._entries.values())

    def executive_findings(self) -> List[Finding]:
        """
        Findings suitable for the executive section.
        Excludes: hypotheses, blocked, explicit held_from_executive.
        """
        with self._lock:
            return [
                e.finding
                for e in self._entries.values()
                if not e.is_hypothesis
                and e.lifecycle not in (FindingLifecycle.BLOCKED,)
                and not getattr(e.finding, "held_from_executive", False)
            ]

    def hypothesis_findings(self) -> List[Finding]:
        """
        Findings that are LOW_CONFIDENCE or UNVERIFIED — shown in exploratory section.
        """
        with self._lock:
            return [
                e.finding
                for e in self._entries.values()
                if e.is_hypothesis
            ]

    def score_contributing_findings(self) -> List[Finding]:
        """
        Subset that actually feeds into scoring deductions.
        GUESSING/LOW_CONFIDENCE/UNVERIFIED never reduce the category score.
        """
        with self._lock:
            return [
                e.finding
                for e in self._entries.values()
                if e.affects_score
                and e.lifecycle not in (FindingLifecycle.BLOCKED,)
            ]

    def findings_by_category(self, category: Category) -> List[Finding]:
        with self._lock:
            return [
                e.finding for e in self._entries.values()
                if e.finding.category == category
            ]

    def lifecycle_summary(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {lc.value: 0 for lc in FindingLifecycle}
            for e in self._entries.values():
                counts[e.lifecycle.value] += 1
            return counts

    def deduplication_report(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "canonical_id": e.canonical_id,
                    "primary_finding_id": e.finding.finding_id,
                    "duplicate_count": len(e.duplicate_ids),
                    "duplicate_ids": e.duplicate_ids,
                }
                for e in self._entries.values()
                if e.duplicate_ids
            ]

    def confidence_distribution(self) -> Dict[str, int]:
        with self._lock:
            dist: Dict[str, int] = {}
            for e in self._entries.values():
                rubric = getattr(e.finding, "confidence_rubric", None)
                label = rubric.value if rubric else "UNKNOWN"
                dist[label] = dist.get(label, 0) + 1
            return dist

    # --- Helpers -------------------------------------------------------------

    @staticmethod
    def _severity_rank(s: Severity) -> int:
        return {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }.get(s, 0)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return (
            f"<FindingRegistry run={self.run_id!r} "
            f"total={len(self)} "
            f"executive={len(self.executive_findings())} "
            f"hypotheses={len(self.hypothesis_findings())}>"
        )
