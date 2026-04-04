---
id: TASK-0016
title: Write-at-land pre-computation — trigger L2 refresh on session end
status: To Do
created: '2026-03-31'
priority: High
milestone: MS-0001
tags:
  - architecture
  - daemon
  - write-heavy
dependencies:
  - Wire L2 project summaries into MCP tools
acceptance-criteria:
  - /land in project A → daemon refreshes L2 for project A → next /takeoff gets instant
  context
  - If daemon is not running, degrades gracefully (no crash, just stale L2)
  - Queue mechanism uses existing daemon task format
definition-of-done:
  - Bookmark write or session finalization queues L2 refresh to daemon
  - Daemon processes L2 refresh within 60s of queue entry
  - Next /takeoff for that project gets warm L2 without any claude -p call
---
Currently all context is computed at read time (/takeoff). Invert this: when a session ends (/land or bookmark write), trigger L2 summary refresh for that project. The daemon exists and works — use it. Queue an L2 regeneration task to the daemon when a bookmark is written or a session JSONL is finalized. This ensures /takeoff always finds warm L2 content.
