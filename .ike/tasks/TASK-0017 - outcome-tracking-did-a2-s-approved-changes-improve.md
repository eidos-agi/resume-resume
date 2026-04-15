---
id: TASK-0017
title: 'Outcome tracking: did A2''s approved changes improve A1?'
status: To Do
created: '2026-04-15'
priority: medium
tags:
  - meta-ai
  - instrumentation
dependencies:
  - inbox-task
acceptance-criteria:
  - Every approved A2 proposal records a 'before' snapshot of A1 output
  - After 7/14/28 days, 'after' snapshots auto-captured
  - self_a2_scorecard returns proposal -> effect table
---
For every approved A2 proposal, start tracking: what did A1 output before vs after the change? Quality metric TBD (user approval rate of A1's auto-class recommendations, or telemetry error rate improvement). Surface via self_a2_scorecard showing: for last N approved A2 proposals, estimated effect on A1's output quality.
