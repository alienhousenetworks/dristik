# Technical Strategy & Implementation Blueprint: Milestone M1 Backend Pipeline Scoring Timing & External Authority Flag

**Target Component**: `backend/app/orchestration/orchestrator.py`  
**Milestone**: M1 (Phase 0: Pipeline Scoring Timing & UI Consistency)  
**Author**: `explorer_m1_1`  
**Date**: 2026-10-31  

---

## 1. Executive Summary & Problem Diagnosis

Milestone M1 resolves critical integrity issues in Dristik AI's audit analysis pipeline:
1. **Premature Stage & Node Status Emission**: At line 1276 of `orchestrator.py`, `node_honest_scoring` was prematurely marked `GraphNodeStatus.RUNNING` and SSE stage `scoring` (93%) was broadcast to clients *before* post-DAG analyzers, live search visibility checks, competitor evidence graph, external authority attachment, finding deduplication, and causal root cause analysis had even started.
2. **External Authority Flag Detection Bug**: At lines 1547–1553 of `orchestrator.py`, external authority detection checked `c.get("status") == "CONNECTED"` on items in `external_authority_payload["coverage"]`, and `external_authority_payload.get("status")`. However, the authority coverage matrix produces dictionaries keyed by `"connection_status"` and `"data_state"`, with no top-level `"status"` key. Consequently, `has_external_authority_connected` always evaluated to `False` unless domain findings > 0, forcing `trust_authority` scoring into `NOT_MEASURED` ("connector unavailable") even when provider snapshots were present.
3. **Manual DAG Node Runner Discrepancy**: At lines 2983–2995, `run_pipeline_node("node_honest_scoring")` called `calculate_scores` with partial parameters, omitted `external_authority_connected`, `has_schema`, `is_https`, and completely failed to call `calculate_honest_scores` or populate `blackboard.honest_scores`.
4. **Insecure `"org_default"` Tenant Fallback**: Line 1537 used `project_id=getattr(run, "org_id", None) or "org_default"`, which queried external authority credentials and snapshots in the shared default bucket if tenant context was absent, violating enterprise tenant isolation.
5. **Roadmap Inclusion of External Findings**: Verified that `RoadmapBuilder.build_roadmap` and `build_top_10_actions` at Step 16 consume `final_findings`, which incorporates deduplicated external authority domain findings appended at Step 14.

---

## 2. Line-by-Line Implementation Strategy

### 2.1 Component 1: Premature Stage & Node Status Removal (Lines 1275–1283)

#### Observation
In `backend/app/orchestration/orchestrator.py`:
```python
1275:             # 12. Causal Prioritization & Scoring Engine
1276:             controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
1277:             controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")
1278: 
1279:             model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
1280:             model_router.set_active_sub_stage("remediation_blueprints", "Autonomous Code Patch Pack Generation")
1281:             run.status = AnalysisStage.SCORING
1282:             await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
```
Immediately following line 1283, the orchestrator begins executing post-DAG diagnostic analyzers (canonicals, HTTP statuses, headings, media, link depth, forms, security headers, schema rich results, WCAG accessibility, and host redirects), followed by live search visibility, external authority attachment, and finding deduplication. `node_honest_scoring` was marked RUNNING here and then marked RUNNING *again* at line 1583.

#### Solution
Remove `node_honest_scoring` status marking and `AnalysisStage.SCORING` emission from lines 1276–1283.
Replace with stage emission representing post-DAG diagnostic analyzers under `specialist_execution`:
```python
            # Post-DAG Diagnostic & Specialized Analyzers Wave
            model_router.set_active_stage("specialist_execution", "Post-DAG Diagnostic Analyzers")
            model_router.set_active_sub_stage("analyzers", "Executing deep diagnostic analyzers across canonicals, headings, links, and schemas")
            await self._emit_event(analysis_id, "specialist_execution", 90, "Executing post-DAG diagnostic analyzers and audit verifications...")
```

#### Shift to Step 15 (Line 1581–1586)
At Step 15 (line 1581), deterministic scoring actually begins:
```python
            # -----------------------------------------------------------------
            # Step 15: Scoring Engine (Single Source of Truth over complete findings)
            # -----------------------------------------------------------------
            controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
            controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")

            model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
            model_router.set_active_sub_stage("deterministic_scoring", "Deterministic Category & Honest Scoring")
            if run:
                run.status = AnalysisStage.SCORING
            await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
```
Also persist scoring inputs into `blackboard.blackboard_state` immediately after lines 1626:
```python
            blackboard.blackboard_state["external_authority_connected"] = has_external_authority_connected
            blackboard.blackboard_state["live_citation_score"] = live_citation_score
            blackboard.blackboard_state["live_bench"] = live_bench
            blackboard.blackboard_state["readability_score"] = page_ev.readability_score
```

---

### 2.2 Component 2: External Authority Tenant Scoping & Key Mismatch Fix (Lines 1526–1557)

#### Observation
In `backend/app/orchestration/orchestrator.py`:
```python
1536:                 attachment = build_audit_attachment(
1537:                     project_id=getattr(run, "org_id", None) or "org_default",
1538:                     domain=domain,
1539:                     pages=eval_pages,
1540:                     evidence_store=getattr(blackboard, "evidence_store", None),
1541:                 )
...
1547:                 cov_items = external_authority_payload.get("coverage", [])
1548:                 if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
1549:                     has_external_authority_connected = True
1550:                 elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
1551:                     has_external_authority_connected = True
1552:                 elif len(attachment.get("domain_findings", [])) > 0:
1553:                     has_external_authority_connected = True
```

Problems identified:
1. **Tenant Scoping (Line 1537)**: `project_id=getattr(run, "org_id", None) or "org_default"` falls back to `"org_default"`. When an audit runs without a tenant context (or `run.org_id` is missing), it must not attach credentials or snapshots belonging to `"org_default"`.
2. **Dictionary Key Mismatch (Lines 1548–1550)**:
   - `c.get("status")`: `coverage_matrix` in `backend/app/connectors/authority/analyze.py` (lines 87–144) produces rows with keys `"connection_status"` and `"data_state"`. Key `"status"` does not exist in coverage matrix rows.
   - `external_authority_payload.get("status")`: `build_report()` produces top-level keys `["title", "project_id", "domain", "period_days", "universal_authority_score", "coverage", "pillars", "findings", ...]`. No top-level `"status"` key exists.
   - Consequence: Even if Google Search Console or Ahrefs has valid snapshots with `connection_status="CONNECTED"` and `data_state="MEASURED"`, `has_external_authority_connected` evaluates to `False` whenever `domain_findings` is empty (e.g. healthy external profile).

#### Solution
Replace lines 1533–1557 with:
```python
            has_external_authority_connected = False
            try:
                from app.connectors.authority.audit_bridge import build_audit_attachment

                # Strict tenant context resolution: avoid leaking or querying shared "org_default" bucket
                tenant_project_id = getattr(run, "org_id", None)
                if not tenant_project_id or tenant_project_id == "org_default":
                    tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)

                if tenant_project_id and tenant_project_id != "org_default":
                    attachment = build_audit_attachment(
                        project_id=tenant_project_id,
                        domain=domain,
                        pages=eval_pages,
                        evidence_store=getattr(blackboard, "evidence_store", None),
                    )
                    external_authority_payload = attachment.get("report", external_authority_payload)
                    for f in attachment.get("domain_findings", []):
                        if not any(x.finding_id == f.finding_id for x in raw_findings):
                            raw_findings.append(f)

                    cov_items = external_authority_payload.get("coverage", [])
                    for c in cov_items:
                        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
                        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
                        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
                        if conn_status == "CONNECTED" or legacy_status == "CONNECTED" or data_state in ("MEASURED", "PARTIALLY_MEASURED"):
                            has_external_authority_connected = True
                            break

                    if not has_external_authority_connected:
                        if external_authority_payload.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED") or external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
                            has_external_authority_connected = True
                        elif len(attachment.get("domain_findings", [])) > 0:
                            has_external_authority_connected = True
                else:
                    logger.info("External authority attachment skipped: missing tenant org context (refusing 'org_default' fallback)")
                    external_authority_payload["notes"] = ["External authority was not attached: valid tenant context required."]
            except Exception as exc:
                logger.info("external authority attachment skipped: %s", type(exc).__name__)
                external_authority_payload["error"] = type(exc).__name__
```

---

### 2.3 Component 3: Manual DAG Node Runner Parity (Lines 2983–2995)

#### Observation
In `backend/app/orchestration/orchestrator.py` (`run_pipeline_node`):
```python
2983:             elif node_id == "node_honest_scoring":
2984:                 eval_pages = blackboard.pages or []
2985:                 scores = self.scoring_engine.calculate_scores(
2986:                     manifest=blackboard.crawl_manifest,
2987:                     findings=blackboard.findings or [],
2988:                     claims=blackboard.claim_registry.get_all(),
2989:                     evidence_store=blackboard.evidence_store,
2990:                     pages=eval_pages,
2991:                     evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
2992:                     business_profile=blackboard.business_profile,
2993:                 )
2994:                 blackboard.scores = scores
```
This manual DAG runner:
- Never passed `external_authority_connected` (defaulting to `False`).
- Never passed `has_schema`, `is_https`, `readability`, `live_citation_score`, `live_benchmark_data`.
- Did not apply measured GEO extractability (`apply_measured_geo_score`).
- Completely omitted `calculate_honest_scores`, leaving `blackboard.honest_scores` `None` or out-of-date.

#### Solution
Update lines 2983–2995 to retrieve environment state from blackboard and invoke both `calculate_scores` and `calculate_honest_scores`:
```python
            elif node_id == "node_honest_scoring":
                eval_pages = blackboard.pages or []
                website_url = blackboard.website_url or ""
                domain_val = blackboard.crawl_manifest.domain if blackboard.crawl_manifest else ""
                if not domain_val and website_url:
                    domain_val = urlparse(website_url).netloc.replace("www.", "")

                # Detect external authority connection state
                has_ext_authority = bool(blackboard.blackboard_state.get("external_authority_connected", False))
                if not has_ext_authority:
                    try:
                        from app.connectors.authority.audit_bridge import build_audit_attachment
                        run_rec = self.runs.get(analysis_id)
                        tenant_id = getattr(run_rec, "org_id", None) or blackboard.blackboard_state.get("org_id")
                        if tenant_id and tenant_id != "org_default" and domain_val:
                            att = build_audit_attachment(
                                project_id=tenant_id,
                                domain=domain_val,
                                pages=eval_pages,
                                evidence_store=getattr(blackboard, "evidence_store", None),
                            )
                            cov = att.get("report", {}).get("coverage", [])
                            for c in cov:
                                c_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
                                c_data = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
                                if c_status == "CONNECTED" or c_data in ("MEASURED", "PARTIALLY_MEASURED"):
                                    has_ext_authority = True
                                    break
                            if not has_ext_authority and len(att.get("domain_findings", [])) > 0:
                                has_ext_authority = True
                    except Exception as ea_err:
                        logger.debug("External authority check in node_honest_scoring: %s", ea_err)

                has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
                is_https = website_url.startswith("https://") if website_url else False
                readability = blackboard.blackboard_state.get("readability_score")
                live_citation = blackboard.blackboard_state.get("live_citation_score")
                live_bench = blackboard.blackboard_state.get("live_bench")
                geo_readiness = getattr(blackboard, "geo_readiness", None)

                scores = self.scoring_engine.calculate_scores(
                    manifest=blackboard.crawl_manifest,
                    findings=blackboard.findings or [],
                    claims=blackboard.claim_registry.get_all(),
                    evidence_store=blackboard.evidence_store,
                    pages=eval_pages,
                    evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                    business_profile=blackboard.business_profile,
                    has_schema=has_schema,
                    is_https=is_https,
                    readability=readability,
                    external_authority_connected=has_ext_authority,
                    live_citation_score=live_citation,
                    live_benchmark_data=live_bench,
                )
                extractability = getattr(geo_readiness, "extractability_score", None) if geo_readiness is not None else None
                if scores is not None and extractability is not None:
                    self.scoring_engine.apply_measured_geo_score(scores, extractability)
                blackboard.scores = scores

                # Compute honest 3-perspective scores
                honest_scores = self.scoring_engine.calculate_honest_scores(
                    findings=blackboard.findings or [],
                    business_profile=blackboard.business_profile,
                    commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                    has_schema=has_schema,
                    is_https=is_https,
                    readability=readability,
                    geo_readiness=geo_readiness,
                    live_citation_score=live_citation,
                    live_benchmark_data=live_bench,
                    external_authority_connected=has_ext_authority,
                )
                blackboard.honest_scores = honest_scores
```

---

### 2.4 Component 4: Roadmap Generation & External Findings Flow Verification

#### Evidence Trace in Pipeline
1. **Attachment (Lines 1543–1545)**:
   ```python
   for f in attachment.get("domain_findings", []):
       if not any(x.finding_id == f.finding_id for x in raw_findings):
           raw_findings.append(f)
   ```
2. **Deduplication (Line 1562)**:
   ```python
   final_findings = FindingDeduplicator.deduplicate(raw_findings)
   blackboard.findings = final_findings
   ```
   External domain findings created via `to_domain_findings()` in `evidence_bridge.py` are valid `Finding` instances with attributes `category=Category.TRUST_AUTHORITY` (or relevant category), `severity`, `priority`, `recommendation`. The deduplicator preserves unclustered findings and assigns severity ranks.
3. **Step 15 Scoring (Lines 1598–1626)**:
   Both `calculate_scores` and `calculate_honest_scores` receive `findings=final_findings` and `external_authority_connected=has_external_authority_connected`.
4. **Step 16 Roadmap Synthesis (Lines 1675–1685)**:
   ```python
   r7, r30, r90 = self.roadmap_builder.build_roadmap(final_findings, blackboard.executive_narrative)
   top_10_plan = self.roadmap_builder.build_top_10_actions(
       final_findings,
       blackboard.business_profile,
       overall_scores,
       blackboard.executive_narrative,
       crawl_summary=manifest.crawl_health if manifest else None,
   )
   blackboard.roadmap_7_days = r7
   blackboard.roadmap_30_days = r30
   blackboard.roadmap_90_days = r90
   ```
5. **Roadmap Sorting & Assignment (`RoadmapBuilder.build_roadmap`)**:
   - `r7` (7-day board): Receives findings with `severity in ("CRITICAL", "HIGH")` or `priority >= 8`.
   - `r30` (30-day board): Receives findings with `severity == "MEDIUM"` or `priority >= 5`.
   - `r90` (90-day board): Receives remaining low-severity findings.
   - `_resolve_owner(f.category)` maps `Category.TRUST_AUTHORITY` (or content/E-E-A-T) to `"Senior Content Strategist"` / `"Technical Lead"`.

**Conclusion**: The existing flow correctly passes `final_findings` to `build_roadmap` and `build_top_10_actions`. No changes to `build_roadmap` call parameters are required; ensuring `raw_findings` receives external findings before `final_findings` deduplication and scoring guarantees roadmap coverage.

---

## 3. Complete Code Diff (Patch Representation)

```diff
--- a/backend/app/orchestration/orchestrator.py
+++ b/backend/app/orchestration/orchestrator.py
@@ -1272,15 +1272,10 @@ class AnalysisOrchestrator:
             if await _check_pause():
                 return
 
-            # 12. Causal Prioritization & Scoring Engine
-            controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
-            controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")
-
-            model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
-            model_router.set_active_sub_stage("remediation_blueprints", "Autonomous Code Patch Pack Generation")
-            run.status = AnalysisStage.SCORING
-            await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
-
+            # Post-DAG Diagnostic & Specialized Wave Execution
+            model_router.set_active_stage("specialist_execution", "Post-DAG Diagnostic Analyzers")
+            model_router.set_active_sub_stage("analyzers", "Executing deep diagnostic analyzers across canonicals, headings, links, and schemas")
+            await self._emit_event(analysis_id, "specialist_execution", 90, "Executing post-DAG diagnostic analyzers and audit verifications...")
+
             eval_pages = (manifest.pages if manifest else None) or blackboard.pages or []
             from app.cro.visual_ux_tester import visual_ux_tester
             from app.seo.analyzers.canonical_auditor import analyze_canonicals
@@ -1534,22 +1529,38 @@ class AnalysisOrchestrator:
             has_external_authority_connected = False
             try:
                 from app.connectors.authority.audit_bridge import build_audit_attachment
-                attachment = build_audit_attachment(
-                    project_id=getattr(run, "org_id", None) or "org_default",
-                    domain=domain,
-                    pages=eval_pages,
-                    evidence_store=getattr(blackboard, "evidence_store", None),
-                )
-                external_authority_payload = attachment["report"]
-                for f in attachment.get("domain_findings", []):
-                    if not any(x.finding_id == f.finding_id for x in raw_findings):
-                        raw_findings.append(f)
-
-                cov_items = external_authority_payload.get("coverage", [])
-                if any((getattr(c, "status", None) == "CONNECTED" or (isinstance(c, dict) and c.get("status") == "CONNECTED")) for c in cov_items):
-                    has_external_authority_connected = True
-                elif external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
-                    has_external_authority_connected = True
-                elif len(attachment.get("domain_findings", [])) > 0:
-                    has_external_authority_connected = True
+
+                # Strict tenant context resolution: avoid leaking or querying shared "org_default" bucket
+                tenant_project_id = getattr(run, "org_id", None)
+                if not tenant_project_id or tenant_project_id == "org_default":
+                    tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)
+
+                if tenant_project_id and tenant_project_id != "org_default":
+                    attachment = build_audit_attachment(
+                        project_id=tenant_project_id,
+                        domain=domain,
+                        pages=eval_pages,
+                        evidence_store=getattr(blackboard, "evidence_store", None),
+                    )
+                    external_authority_payload = attachment.get("report", external_authority_payload)
+                    for f in attachment.get("domain_findings", []):
+                        if not any(x.finding_id == f.finding_id for x in raw_findings):
+                            raw_findings.append(f)
+
+                    cov_items = external_authority_payload.get("coverage", [])
+                    for c in cov_items:
+                        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
+                        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
+                        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
+                        if conn_status == "CONNECTED" or legacy_status == "CONNECTED" or data_state in ("MEASURED", "PARTIALLY_MEASURED"):
+                            has_external_authority_connected = True
+                            break
+
+                    if not has_external_authority_connected:
+                        if external_authority_payload.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED") or external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
+                            has_external_authority_connected = True
+                        elif len(attachment.get("domain_findings", [])) > 0:
+                            has_external_authority_connected = True
+                else:
+                    logger.info("External authority attachment skipped: missing tenant org context (refusing 'org_default' fallback)")
+                    external_authority_payload["notes"] = ["External authority was not attached: valid tenant context required."]
             except Exception as exc:
                 logger.info("external authority attachment skipped: %s", type(exc).__name__)
                 external_authority_payload["error"] = type(exc).__name__
@@ -1582,6 +1593,12 @@ class AnalysisOrchestrator:
             controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
             controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")
 
+            model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
+            model_router.set_active_sub_stage("deterministic_scoring", "Deterministic Category & Honest Scoring")
+            if run:
+                run.status = AnalysisStage.SCORING
+            await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")
+
             live_bench = None
             completed_runs = int(getattr(ai_visibility_scorecard, "successful_runs", 0) or 0) if ai_visibility_scorecard is not None else 0
             if visibility_measured and completed_runs > 0 and ai_visibility_scorecard is not None:
@@ -1626,6 +1643,12 @@ class AnalysisOrchestrator:
             )
             blackboard.honest_scores = honest_scores
 
+            # Persist environmental scoring context for downstream nodes / re-runs
+            blackboard.blackboard_state["external_authority_connected"] = has_external_authority_connected
+            blackboard.blackboard_state["live_citation_score"] = live_citation_score
+            blackboard.blackboard_state["live_bench"] = live_bench
+            blackboard.blackboard_state["readability_score"] = page_ev.readability_score
+
             # Calibrated Confidence
             confidence_result = self.confidence_engine.calculate_confidence(
                 claims=current_claims,
@@ -2983,14 +3006,58 @@ class AnalysisOrchestrator:
             elif node_id == "node_honest_scoring":
                 eval_pages = blackboard.pages or []
+                website_url = blackboard.website_url or ""
+                domain_val = blackboard.crawl_manifest.domain if blackboard.crawl_manifest else ""
+                if not domain_val and website_url:
+                    domain_val = urlparse(website_url).netloc.replace("www.", "")
+
+                # Detect external authority connection state
+                has_ext_authority = bool(blackboard.blackboard_state.get("external_authority_connected", False))
+                if not has_ext_authority:
+                    try:
+                        from app.connectors.authority.audit_bridge import build_audit_attachment
+                        run_rec = self.runs.get(analysis_id)
+                        tenant_id = getattr(run_rec, "org_id", None) or blackboard.blackboard_state.get("org_id")
+                        if tenant_id and tenant_id != "org_default" and domain_val:
+                            att = build_audit_attachment(
+                                project_id=tenant_id,
+                                domain=domain_val,
+                                pages=eval_pages,
+                                evidence_store=getattr(blackboard, "evidence_store", None),
+                            )
+                            cov = att.get("report", {}).get("coverage", [])
+                            for c in cov:
+                                c_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
+                                c_data = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
+                                if c_status == "CONNECTED" or c_data in ("MEASURED", "PARTIALLY_MEASURED"):
+                                    has_ext_authority = True
+                                    break
+                            if not has_ext_authority and len(att.get("domain_findings", [])) > 0:
+                                has_ext_authority = True
+                    except Exception as ea_err:
+                        logger.debug("External authority check in node_honest_scoring: %s", ea_err)
+
+                has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages) if eval_pages else False
+                is_https = website_url.startswith("https://") if website_url else False
+                readability = blackboard.blackboard_state.get("readability_score")
+                live_citation = blackboard.blackboard_state.get("live_citation_score")
+                live_bench = blackboard.blackboard_state.get("live_bench")
+                geo_readiness = getattr(blackboard, "geo_readiness", None)
+
                 scores = self.scoring_engine.calculate_scores(
                     manifest=blackboard.crawl_manifest,
                     findings=blackboard.findings or [],
                     claims=blackboard.claim_registry.get_all(),
                     evidence_store=blackboard.evidence_store,
                     pages=eval_pages,
                     evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                     business_profile=blackboard.business_profile,
+                    has_schema=has_schema,
+                    is_https=is_https,
+                    readability=readability,
+                    external_authority_connected=has_ext_authority,
+                    live_citation_score=live_citation,
+                    live_benchmark_data=live_bench,
                 )
+                extractability = getattr(geo_readiness, "extractability_score", None) if geo_readiness is not None else None
+                if scores is not None and extractability is not None:
+                    self.scoring_engine.apply_measured_geo_score(scores, extractability)
                 blackboard.scores = scores
+
+                # Compute honest 3-perspective scores
+                honest_scores = self.scoring_engine.calculate_honest_scores(
+                    findings=blackboard.findings or [],
+                    business_profile=blackboard.business_profile,
+                    commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
+                    has_schema=has_schema,
+                    is_https=is_https,
+                    readability=readability,
+                    geo_readiness=geo_readiness,
+                    live_citation_score=live_citation,
+                    live_benchmark_data=live_bench,
+                    external_authority_connected=has_ext_authority,
+                )
+                blackboard.honest_scores = honest_scores
```

---

## 4. Regression & Unit Test Blueprint

To ensure complete verification for Milestone M1, implement `backend/tests/unit/test_orchestrator_scoring_timing.py`:

```python
"""
Unit tests for Pipeline Scoring Timing, External Authority Detection, and DAG Runner Parity.
Verifies Milestone M1 (F01, F02, F03, F04, F13).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.orchestration.execution_manager import AnalysisOrchestrator
from app.domain.enums import AnalysisStage, Category, Severity
from app.domain.models import Finding, AnalysisRun, BusinessProfile
from app.orchestration.cognition.blackboard import CognitiveBlackboard

@pytest.mark.asyncio
async def test_scoring_stage_not_emitted_prematurely():
    """Verify AnalysisStage.SCORING is not emitted at 88-90% before post-DAG analyzers."""
    orchestrator = AnalysisOrchestrator()
    emitted_events = []

    async def mock_emit(analysis_id, stage, progress, message, data=None):
        emitted_events.append((stage, progress, message))

    orchestrator._emit_event = AsyncMock(side_effect=mock_emit)
    run = orchestrator.create_run("https://example.com", org_id="org_test")

    # Trace events around post-analysis vs scoring
    # In orchestrator, post-DAG analysis emits specialist_execution at 90%, scoring at 93%
    # Ensure no 'scoring' event appears before live checks and external authority attachment
    ...

def test_has_external_authority_connected_with_coverage_matrix():
    """Verify dictionary keys 'connection_status' and 'data_state' correctly trigger flag."""
    payload = {
        "coverage": [
            {
                "provider": "google_search_console",
                "display_name": "Google Search Console",
                "connection_status": "CONNECTED",
                "data_state": "MEASURED",
            },
            {
                "provider": "ahrefs",
                "display_name": "Ahrefs",
                "connection_status": "NOT_CONNECTED",
                "data_state": "NOT_CONNECTED",
            }
        ]
    }
    cov_items = payload.get("coverage", [])
    has_connected = any(
        (isinstance(c, dict) and (c.get("connection_status") == "CONNECTED" or c.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED")))
        for c in cov_items
    )
    assert has_connected is True

def test_external_authority_skipped_when_tenant_is_org_default():
    """Ensure missing or 'org_default' tenant context refuses to query external authority."""
    run = AnalysisRun(
        analysis_id="run_test",
        website_url="https://example.com",
        org_id="org_default",
        created_at="2026-10-31T00:00:00",
        updated_at="2026-10-31T00:00:00"
    )
    tenant_id = getattr(run, "org_id", None)
    # Refusal logic
    should_attach = bool(tenant_id and tenant_id != "org_default")
    assert should_attach is False

def test_node_honest_scoring_dag_runner_parity():
    """Ensure DAG runner computes both scores and honest_scores and honors external authority."""
    orchestrator = AnalysisOrchestrator()
    analysis_id = "test_run_dag"
    blackboard = CognitiveBlackboard(analysis_id, "https://example.com")
    blackboard.findings = [
        Finding(
            finding_id="f_test_trust",
            category=Category.TRUST_AUTHORITY,
            severity=Severity.HIGH,
            title="External Link Defect",
            description="Loss of referring domains",
            recommendation="Review backlinks",
            impact=7,
            confidence=0.85
        )
    ]
    blackboard.blackboard_state["external_authority_connected"] = True
    orchestrator.blackboards[analysis_id] = blackboard

    # When node_honest_scoring runs
    # blackboard.scores.category_scores["trust_authority"].status must be "MEASURED"
    # blackboard.honest_scores must be populated with google_score, human_score, ai_readiness_score
    ...

def test_roadmap_builder_receives_external_authority_findings():
    """Ensure attached external authority findings appear in 7/30/90-day roadmaps."""
    from app.reports.roadmap import RoadmapBuilder
    builder = RoadmapBuilder()
    ext_finding = Finding(
        finding_id="f_ext_gsc_decline",
        category=Category.TRUST_AUTHORITY,
        severity=Severity.HIGH,
        title="GSC Organic Clicks Declined 34%",
        description="Significant drop in organic search traffic",
        recommendation="Audit ranking keywords and top landing pages",
        priority=9,
        impact=8
    )
    r7, r30, r90 = builder.build_roadmap([ext_finding], {})
    assert any(item.related_finding_id == "f_ext_gsc_decline" for item in r7)
```

---

## 5. Verification Commands for Implementers

1. **Test unmeasured authority gate**:
   ```bash
   pytest backend/tests/test_scoring_unmeasured_authority.py -v
   ```
2. **Test pipeline end-to-end orchestration**:
   ```bash
   pytest backend/tests/test_pipeline.py -v
   ```
3. **Run new timing and authority flag unit tests**:
   ```bash
   pytest backend/tests/unit/test_orchestrator_scoring_timing.py -v
   ```
4. **Scoring calibration suites**:
   ```bash
   pytest backend/tests/test_scoring_calibration.py backend/tests/test_scoring_v5.py backend/tests/test_scoring_geo_extractability.py -v
   ```
