## 2026-10-31T17:05:08Z
[Message] timestamp=2026-10-31T17:05:08Z sender=530d48e9-ac3f-4fe2-8d83-6df3cf3f882f priority=MESSAGE_PRIORITY_HIGH content=You are spec_miner_m1_3, a teamwork_preview_spec_miner.
Working directory: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_3
Project root: /Users/sayantande/Downloads/dristik-main
Original Request: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md
Scope document: /Users/sayantande/Downloads/dristik-main/PROJECT.md

Your task is to produce the test specification and verification assertions for Milestone M1 (Phase 0):
1. Read /Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md and /Users/sayantande/Downloads/dristik-main/PROJECT.md.
2. Review the Acceptance Criteria for Scoring & Integrity in ORIGINAL_REQUEST.md:
   - Category scores and 7/30/90 roadmap reflect external findings when external authority data is connected.
   - Honest score pass (calculate_honest_scores) dynamically receives external_authority_connected=True when provider snapshots exist.
   - Overview tab, Rubric modal, and report header display consistent category scores derived from canonical weights.
3. Design specific pytest test cases (e.g. backend/tests/test_scoring_timing_and_honest_flag.py) with exact assertion logic, fixtures, and execution steps.
4. Document any existing test suites that must pass without regression (e.g. test_confidence_gating.py, test_scoring_unmeasured_authority.py, test_scoring_v5.py).
5. Output the test blueprint to /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m1_3/test_spec_m1.md and write a complete handoff.md following the Handoff Protocol.
6. Report completion to parent via send_message.
Do NOT modify source code files. You are read-only.
