---
id: TASK-0016
title: Build project_orient() — single-call project context for /takeoff
status: To Do
created: '2026-03-31'
priority: Critical
milestone: MS-0001
tags:
  - ux
  - mcp
  - orient
dependencies:
  - Wire L2 project summaries into MCP tools
acceptance-criteria:
  - Single MCP call replaces 3+ current calls in /takeoff
  - Returns useful context even without L2 (falls back to recent session metadata)
  - Response includes actionable next-steps from bookmark if available
definition-of-done:
  - project_orient(path) returns L2 summary + git dirty state + last bookmark + session
  count in single call
  - Response time <500ms when L2 is cached
  - Output structured for direct consumption by /takeoff skill
---
No tool currently answers "what's happening in this project?" in one call. boot_up() is session-granular and requires multiple round-trips. Build project_orient(project_path) that returns in one call: L2 summary, dirty state, last bookmark, recent session count, active blockers. This is what /takeoff should call instead of assembling context from 3-5 separate tools.
