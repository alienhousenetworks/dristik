"""Dristik backend.

Packages:
  api/            HTTP routes, grouped by product area
  core/           settings, security, privacy, policy
  domain/         shared models and enums
  crawl/          fetch, render, parse, embeddings
  evidence/       evidence graph and external measurements
  agents/         specialist runtime, page intelligence, legacy wrappers
  cognition/      claims, rubric, decisions
  orchestration/  live audit pipeline
  mission/        mission director and checkpointed state machine
  intelligence/   geo, competitive, citations, outcomes, business, monitoring
  audit/          sealed manifest, snapshots, ledger, regression
  inference/      model gateway, prompts, pricing
  connectors/     CMS and repository connectors
  identity/       auth, sessions, SSO
  tenancy/        orgs, workspaces, white-label
  remediation/    patches, approval, sync
  reports/        narrative, roadmap, PDF
  scoring/        category scores
  persistence/    SQLite repositories
  workers/        reusable cognitive workers
"""
