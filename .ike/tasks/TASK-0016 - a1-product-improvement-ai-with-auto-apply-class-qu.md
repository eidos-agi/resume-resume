---
id: TASK-0016
title: 'A1: product-improvement AI with auto-apply class + queued class'
status: To Do
created: '2026-04-15'
priority: high
tags:
  - meta-ai
  - a1
acceptance-criteria:
  - A1 writes recommendations to a1_recommendations.jsonl
  - auto-class recommendations result in real actions (file edits / config updates)
  attributable to A1
  - queued-class recommendations sit in a separate store; A2 can see them but human
  does not
  - A1 can be invoked via MCP tool self_run_a1 and via cron-style schedule
  - A1's prompt/config is readable by A2 (separate file, not inline code)
---
Rework uncommitted evaluator.py into A1. Reads telemetry insights + prior A1 outcomes; drafts product recommendations. Each recommendation has an action_class: 'auto' (threshold tweaks, doc edits, behind-a-flag dead-tool removals) or 'queued' (code/signature changes — not human-facing, just holding). A1 auto-applies 'auto' class within guardrails; 'queued' items sit in a secondary store. No per-item human approval.
