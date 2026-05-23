---
id: TASK-0022
title: 'A1 skill: add known-issues.md dedup + regression detection criterion'
status: Done
created: '2026-04-15'
priority: medium
tags:
  - meta-ai
  - a1
updated: '2026-04-16'
---
A1 should read docs/known-issues.md before filing to avoid re-proposing catalogued items. Also missing from A1 prompt: regression detection (p95 growing week-over-week). Both are A2-territory observations from the first A2 run but need concrete implementation.

**Completion notes:** Shipped in 4d940c7. A1 SKILL.md now reads known-issues.md for dedup, has regression detection criterion (p95 2x growth), and has the A2-proposed low-volume noise guardrail.
