---
id: TASK-0016
title: 'A1: product-improvement AI with auto-apply class + queued class'
status: Done
created: '2026-04-15'
priority: high
tags:
  - meta-ai
  - a1
acceptance-criteria:
  - A1 writes recommendations to a1_recommendations.jsonl
  - auto-class recommendations result in real actions attributable to A1
  - queued-class recommendations sit in a separate store
  - A1 can be invoked via skill or MCP tool
  - A1 prompt is readable by A2 (separate file, not inline code)
updated: '2026-04-15'
---
Rework uncommitted evaluator.py into A1. Reads telemetry insights + prior A1 outcomes; drafts product recommendations. Each recommendation has an action_class: 'auto' (threshold tweaks, doc edits, behind-a-flag dead-tool removals) or 'queued' (code/signature changes — not human-facing, just holding). A1 auto-applies 'auto' class within guardrails; 'queued' items sit in a secondary store. No per-item human approval.

**Completion notes:** All three TASK-0016 items (A1, A2, inbox) shipped in bbaa36e+d42ec0a+29d2f73. A1+A2 are Claude Code skills. Inbox is self_process_proposals + self_process_decide. 76 tests passing.
