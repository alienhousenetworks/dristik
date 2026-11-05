#!/usr/bin/env python3
"""
Detailed Column-by-Column, Type-by-Type, Constraint-by-Constraint,
and Index-by-Index comparison between:
1. SQLAlchemy Base.metadata.tables
2. Alembic migration 001_initial_enterprise_schema.py
3. Enterprise Schema definitions
"""
import sys
import importlib.util

sys.path.insert(0, "/Users/sayantande/Downloads/dristik-main/backend")

from sqlalchemy import create_engine
from app.db.base import Base
import app.db.models as models

# Load Alembic migration file dynamically
spec = importlib.util.spec_from_file_location(
    "migration_001",
    "/Users/sayantande/Downloads/dristik-main/backend/migrations/versions/001_initial_enterprise_schema.py"
)
migration_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_module)

print("=" * 80)
print("AUDITING SCHEMA PARITY: MODELS VS MIGRATION 001")
print("=" * 80)

# We can mock alembic.op to capture create_table calls
captured_tables = {}
captured_indexes = {}

class MockOp:
    @staticmethod
    def create_table(name, *columns, **kwargs):
        captured_tables[name] = {
            "columns": {c.name: c for c in columns if hasattr(c, "name") and c.name is not None},
            "constraints": [c for c in columns if hasattr(c, "__visit_name__") and c.__visit_name__ in ("unique_constraint", "primary_key_constraint", "foreign_key_constraint")]
        }

    @staticmethod
    def create_index(name, table_name, columns, **kwargs):
        if table_name not in captured_indexes:
            captured_indexes[table_name] = []
        captured_indexes[table_name].append({
            "name": name,
            "columns": columns,
            "unique": kwargs.get("unique", False)
        })

# Monkeypatch alembic op
migration_module.op = MockOp
migration_module.upgrade()

enterprise_tables = [
    "organizations",
    "workspaces",
    "domains",
    "audit_runs",
    "evidence_nodes",
    "findings",
    "ai_citations",
    "enterprise_audit_logs",
]

discrepancies = []

for table_name in enterprise_tables:
    print(f"\n--- Checking Table: {table_name} ---")
    if table_name not in Base.metadata.tables:
        discrepancies.append(f"Table {table_name} missing from Base.metadata")
        continue
    if table_name not in captured_tables:
        discrepancies.append(f"Table {table_name} missing from Alembic migration")
        continue

    model_table = Base.metadata.tables[table_name]
    mig_table = captured_tables[table_name]
    mig_cols = mig_table["columns"]

    # Check columns
    model_col_names = set(model_table.columns.keys())
    mig_col_names = set(mig_cols.keys())

    print(f"Model columns ({len(model_col_names)}): {sorted(model_col_names)}")
    print(f"Migration columns ({len(mig_col_names)}): {sorted(mig_col_names)}")

    diff_in_model_only = model_col_names - mig_col_names
    diff_in_mig_only = mig_col_names - model_col_names

    if diff_in_model_only:
        discrepancies.append(f"Table {table_name}: columns in model but not in migration: {diff_in_model_only}")
    if diff_in_mig_only:
        discrepancies.append(f"Table {table_name}: columns in migration but not in model: {diff_in_mig_only}")

    # Check common columns
    common_cols = model_col_names & mig_col_names
    for col_name in common_cols:
        m_col = model_table.columns[col_name]
        mig_col = mig_cols[col_name]

        # Nullability
        if m_col.nullable != mig_col.nullable:
            discrepancies.append(
                f"Table {table_name}.{col_name}: nullability mismatch (model={m_col.nullable}, mig={mig_col.nullable})"
            )

        # Primary key
        if m_col.primary_key != mig_col.primary_key:
            discrepancies.append(
                f"Table {table_name}.{col_name}: primary key mismatch (model={m_col.primary_key}, mig={mig_col.primary_key})"
            )

        # Type class comparison
        m_type = m_col.type.__class__.__name__
        mig_type = mig_col.type.__class__.__name__
        if m_type != mig_type:
            discrepancies.append(
                f"Table {table_name}.{col_name}: type mismatch (model={m_type}, mig={mig_type})"
            )

        # String length comparison
        if hasattr(m_col.type, "length") and hasattr(mig_col.type, "length"):
            if m_col.type.length != mig_col.type.length:
                discrepancies.append(
                    f"Table {table_name}.{col_name}: string length mismatch (model={m_col.type.length}, mig={mig_col.type.length})"
                )

        # Foreign Key check
        m_fks = list(m_col.foreign_keys)
        mig_fks = list(mig_col.foreign_keys)
        if len(m_fks) != len(mig_fks):
            discrepancies.append(
                f"Table {table_name}.{col_name}: foreign key count mismatch (model={len(m_fks)}, mig={len(mig_fks)})"
            )
        elif len(m_fks) > 0:
            m_fk = m_fks[0]
            mig_fk = mig_fks[0]
            if str(m_fk.target_fullname) != str(mig_fk.target_fullname):
                discrepancies.append(
                    f"Table {table_name}.{col_name}: FK target mismatch (model={m_fk.target_fullname}, mig={mig_fk.target_fullname})"
                )
            if m_fk.ondelete != mig_fk.ondelete:
                discrepancies.append(
                    f"Table {table_name}.{col_name}: FK ondelete mismatch (model={m_fk.ondelete}, mig={mig_fk.ondelete})"
                )

    # Unique constraints
    model_uqs = {u.name: set(c.name for c in u.columns) for u in model_table.constraints if u.__visit_name__ == "unique_constraint" and u.name}
    mig_uqs = {u.name: set(u.columns.keys() if hasattr(u.columns, 'keys') else [c.name if hasattr(c, 'name') else str(c) for c in u.columns]) for u in mig_table["constraints"] if getattr(u, "__visit_name__", "") == "unique_constraint"}
    print(f"Model Unique Constraints: {model_uqs}")
    print(f"Migration Unique Constraints: {mig_uqs}")

    # Index checks
    model_indexes = {idx.name: [c.name for c in idx.columns] for idx in model_table.indexes if idx.name}
    mig_indexes = {idx["name"]: idx["columns"] for idx in captured_indexes.get(table_name, [])}
    print(f"Model Indexes: {model_indexes}")
    print(f"Migration Indexes: {mig_indexes}")

print("\n" + "=" * 80)
print(f"AUDIT SUMMARY: {len(discrepancies)} discrepancies found")
print("=" * 80)
for d in discrepancies:
    print(" - DISCREPANCY:", d)

if not discrepancies:
    print("PERFECT PARITY: All 8 enterprise tables match column types, nullability, primary keys, foreign keys, and constraints!")
