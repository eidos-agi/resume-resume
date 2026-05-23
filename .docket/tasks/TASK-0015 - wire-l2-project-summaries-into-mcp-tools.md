---
id: TASK-0015
title: Wire L2 project summaries into MCP tools
status: Done
created: '2026-03-31'
priority: Critical
milestone: MS-0001
tags:
  - l2
  - mcp
  - last-mile
acceptance-criteria:
  - L2 summary served via MCP in <200ms
  - No claude -p call at read time
  - Fallback returns session count + last activity if no L2 exists
definition-of-done:
  - MCP tool project_summary(project_path) returns L2 summary in <200ms from cache
  - MCP tool list_projects() returns all projects with L2 summaries
  - Falls back gracefully if L2 not yet generated for a project
updated: '2026-04-01'
---
L2 generator exists in commons (TASK-0010 done 3/30) but resume-resume's MCP server exposes zero L2 tools. Add project_summary() and list_projects() tools that read from summary_levels table and serve pre-computed L2 content. This is the critical last mile — the data exists, it just isn't reachable.

Shipped: l2_tools.py with 3 MCP tools (project_summary, list_projects, project_orient). Registered via mcp_server.py. Tested against live insights.db — 6 L2 topics for ciso project confirmed working.
