---
id: "ADR-002"
type: "decision"
title: "Build full A1+A2 autonomous management stack on resume-resume"
status: "accepted"
date: "2026-04-15"
source_research_id: "9386d805-b79f-4fcf-bc3a-9030cb46218b"
---

# Context

resume-resume already captures MCP telemetry (commit dbfa88f) and exposes self_* introspection tools (commit b34b970). This ADR commits to the next layer: autonomous multi-level AI management.

# Decision

Build two new layers on top of telemetry:

- **A1 — Product-improvement AI.** Reads L2 insights (`insights_report`), drafts product recommendations against resume-resume. Auto-applies recommendations that fall within a named low-risk class (threshold tweaks, dead-tool removals behind a flag, doc/comment edits). Higher-risk classes (code changes, tool signature changes) go to a secondary queue, not the human.
- **A2 — Process-management AI.** Reads A1's config (prompt, thresholds, recent outputs), A1's approval/reject history, and telemetry trends. Proposes methodology changes to A1: prompt edits, threshold tunes, new criteria, removed criteria, cadence changes. A2's output is what the human sees.
- **Human role.** Approve / reject / defer A2's process proposals. Never touches A1's product recommendations.

Both A1 and A2 use `claude -p` (fixed-cost per HARD CONSTRAINTS). No variable-cost API.

# Rationale

From research project `9386d805` (scored 25/23/20 vs alternatives):

1. **Learning value is the primary deliverable.** User is an AI engineer whose stated goal is to learn from running a multi-level AI management loop on a real substrate. The small surface area of resume-resume is a safe lab, not a scope mismatch.
2. **Attention efficiency.** Human only sees methodology proposals (A2's output). A2 filters and consolidates A1's per-item activity so the human never reviews individual product changes.
3. **Blast radius is single-user.** Auto-apply is acceptable where it wouldn't be in a multi-tenant system.
4. **Slow feedback loops mitigated by instrumentation.** A2 is itself instrumented (proposal audit log with outcomes), so decisions remain reviewable on a months-long horizon.

# Consequences

- Two new Python modules, two new tool surfaces (product-recommendation auto-apply + human-facing methodology inbox), weekly cadence for both AIs.
- Audit trail for every layer: `recommendations.jsonl`, `process_proposals.jsonl`. Both append-only, both queryable.
- Maintenance cost: A1's prompt and A2's prompt both live in code; changes to them come from A2 proposals (approved by the human) or manual commits.
- Revisit if: A2 goes 60+ days without a useful proposal (then A2 is over-engineered), or if A1's auto-applied changes cause regressions the human catches manually (then the auto-apply class is miscalibrated).

# Supersedes / Relates to

Builds on telemetry capture (commit dbfa88f) and self_* tools (commit b34b970). Does not supersede existing ADRs.
