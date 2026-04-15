---
id: TASK-0016
title: 'A2: process-management AI that critiques A1'
status: To Do
created: '2026-04-15'
priority: high
tags:
  - meta-ai
  - a2
dependencies:
  - A1-task
acceptance-criteria:
  - A2 writes proposals to process_proposals.jsonl
  - Each proposal has target, evidence, confidence, and an actionable diff or config
  delta
  - A2 sees A1's prompt as a file it can reason about (not hardcoded)
  - A2 is itself invokable via self_run_a2
---
Build A2 as resume_resume/process_manager.py. Reads A1's prompt file, A1's recent output (a1_recommendations.jsonl), telemetry trends, and A2's own prior proposal outcomes. Produces proposals for methodology changes to A1: prompt edits (diffs), threshold tunes, new criteria, removed criteria, cadence changes. Each proposal includes: target (A1 prompt / thresholds / criteria), evidence, confidence, suggested_diff, expected_effect.
