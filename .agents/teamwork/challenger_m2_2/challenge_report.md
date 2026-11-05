# Empirical Challenge Report — Milestone M2 (Schema Models & Migration Integrity)

**Verdict**: **APPROVE** (with 3 low/medium architectural advisories)
**Overall Risk Assessment**: LOW
**Agent**: `challenger_m2_2` (empirical_challenger / critic)
**Timestamp**: 2026-10-31T20:45:00Z

---

## Executive Summary
Milestone M2 schema models (`backend/app/db/models/`) and Alembic migration `backend/migrations/versions/001_initial_enterprise_schema.py` were subjected to adversarial empirical verification and stress testing across:
1. Alembic offline SQL generation (PostgreSQL and SQLite) and online upgrade/downgrade/upgrade lifecycle.
2. Complete schema parity across all 8 foundational enterprise tables (columns, nullability, types, foreign keys, unique constraints, indexes).
3. 5-tier foreign key cascade deletion across both SQLAlchemy ORM and raw database engine triggers (SQLite `PRAGMA foreign_keys=ON`).
4. Multi-tenant isolation enforcement via `uq_workspaces_org_slug`.
5. Edge cases, volume stress (106 records across 5 tiers), JSON payload round-tripping, and fail-fast connectivity.

All core invariants PASSED empirical verification.

---

## Empirical Verification Matrix

| Target Invariant | Method | Execution Command | Result |
|---|---|---|---|
| **Alembic Offline SQL (SQLite)** | Offline migration DDL dump | `alembic -c alembic.ini upgrade head --sql` | **PASS** (Exit 0, clean DDL) |
| **Alembic Offline SQL (PostgreSQL)** | Offline migration DDL with PG URL | `DATABASE_URL=postgresql://... alembic upgrade head --sql` | **PASS** (Exit 0, TIMESTAMPTZ, BEGIN/COMMIT) |
| **Alembic Migration Lifecycle** | Online upgrade -> downgrade -> re-upgrade | `alembic upgrade head && downgrade base && upgrade head` | **PASS** (Exit 0, idempotent, all tables dropped/rebuilt) |
| **8 Enterprise Tables Parity** | Automated AST/metadata reflection audit | `verify_detailed_schema_parity.py` | **PASS** (100% column/type/nullability parity) |
| **Unique Constraint Multi-Tenancy** | Insert duplicate slug same org vs cross org | `verify_m2_empirical.py::test_unique_constraints` | **PASS** (Rejected same org, allowed across orgs) |
| **5-Tier Deep Cascade (ORM)** | 106 records across Org->WS->Domain->Run->Findings/Evidence | `stress_test_enterprise_hierarchy.py::test_deep_orm_cascade` | **PASS** (106 records created, 106 deleted on org delete) |
| **5-Tier Deep Cascade (Engine FK)** | 106 records deleted via raw SQL with `PRAGMA foreign_keys=ON` | `stress_test_enterprise_hierarchy.py::test_deep_raw_sql_cascade` | **PASS** (SQLite engine FK triggers wiped all 106 records) |
| **Intermediate Tier Cascade** | Delete Domain (preserves WS/Org); Delete Run (preserves Domain) | `stress_test_enterprise_hierarchy.py::test_intermediate_tier_cascades` | **PASS** (Surgical downstream cascade) |
| **Data Boundaries & Precision** | 512-char title, float precision, deep unicode JSON | `stress_test_enterprise_hierarchy.py::test_data_boundaries` | **PASS** (Fidelity verified) |
| **Fail-Fast Engine Probe** | Unreachable port probe + password masking | `verify_m2_empirical.py::test_fail_fast_and_url_masking` | **PASS** (Raised DatabaseConnectionError, masked URL) |

---

## Challenges & Adversarial Findings

### Challenge 1: `EvidenceNode.node_metadata` vs `metadata` attribute shadowing [MEDIUM]
- **Observation**: In `EvidenceNode` (`backend/app/db/models/evidence_node.py`), the column is mapped as `node_metadata = Column("metadata", JSON, default=dict, nullable=False)`.
- **Attack Scenario**: Because `metadata` is a reserved attribute on SQLAlchemy's `DeclarativeBase` (`Base.metadata`), calling `EvidenceNode(..., metadata={"key": "val"})` attaches `metadata` as an ordinary instance attribute in `__dict__`, bypassing the mapped column `node_metadata`. When persisted, `node_metadata` falls back to its default `{}` and the input data is silently lost.
- **Blast Radius**: Code that passes `metadata={...}` instead of `node_metadata={...}` will store empty JSON in `evidence_nodes.metadata`.
- **Mitigation**: Add an `__init__` constructor intercept to `EvidenceNode` to check for `kwargs.pop("metadata", None)` and assign it to `self.node_metadata`, or document the mandatory use of `node_metadata` in repository layers.

### Challenge 2: Supporting Tables `users` and `integrations` Foreign Key Cascade Gap [LOW]
- **Observation**: In `001_initial_enterprise_schema.py`:
  - `users.org_id` references `organizations.id` without `ondelete="CASCADE"`.
  - `integrations.org_id` references `organizations.id` without `ondelete="CASCADE"`.
  - In `Organization` model, relationships to `User` and `Integration` are omitted.
- **Attack Scenario**: If an organization that has users or integration credentials is deleted with database foreign keys enabled (`PRAGMA foreign_keys=ON` or PostgreSQL), the deletion fails with `IntegrityError: FOREIGN KEY constraint failed`.
- **Blast Radius**: Hard deletion of organizations that contain users or integrations will fail at the database level unless those related records are deleted first.
- **Mitigation**: In Milestone M3 (Tenant Scoping), add `ondelete="CASCADE"` to `users.org_id` and `integrations.org_id` in a follow-up migration, or define relationship cascades on `Organization`.

### Challenge 3: Client-side `default` vs Database `server_default` Divergence on Raw Inserts [LOW]
- **Observation**: `001_initial_enterprise_schema.py` specifies `server_default` on DDL columns (`plan`, `status`, `stage`, `pages_crawled`, etc.), but SQLAlchemy model definitions in `app/db/models/` specify only Python client-side `default=...`.
- **Attack Scenario**: When tables are initialized using `Base.metadata.create_all()` in test harnesses rather than through Alembic, executing raw SQL `INSERT` statements without providing values for those non-nullable columns raises `IntegrityError: NOT NULL constraint failed: organizations.plan`.
- **Blast Radius**: Affects raw SQL fixtures that omit defaults on `create_all`-generated tables. ORM usage (`session.add(Organization(...))`) and Alembic-migrated databases are unaffected.
- **Mitigation**: For complete consistency, mirror `server_default` on the SQLAlchemy model column definitions.

---

## Stress Test Results Verbatim Log
```
[STRESS TEST 1] Deep ORM Cascade Volume Test (106 records)...
 -> Successfully seeded full enterprise hierarchy: 106 records across 5 tiers.
 -> PASS: Complete 106-record ORM cascade deletion verified clean!

[STRESS TEST 2] Deep Raw SQL Foreign Key Cascade Test on Alembic DDL (106 records)...
 -> PASS: Deep Raw SQL engine cascade deletion wiped all 106 records via SQLite FK triggers!

[STRESS TEST 3] Intermediate Tier Cascades (Workspace, Domain, AuditRun)...
 -> PASS: Domain deletion cleanly cascaded children while preserving parent Workspace/Org!
 -> PASS: AuditRun deletion cleanly cascaded findings/evidence while preserving Domain!

[STRESS TEST 4] Extreme Data Boundaries and Data Types...
 -> PASS: 512-char finding titles, float precision, and unicode JSON verified!

ALL STRESS TESTS COMPLETED SUCCESSFULLY!
```

---

## Verdict & Recommendation
**VERDICT: APPROVE**
The schema models, migrations, and cascade relationships satisfy all Milestone M2 persistence requirements. The discovered advisories do not block M2 and can be seamlessly addressed in Phase 1 Milestone M3.
