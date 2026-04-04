---
id: TASK-0003
title: 'boot_up: surface repos touched during a session, not just project root'
status: To Do
created: '2026-03-25'
priority: low
tags:
  - boot_up
  - cross-repo
updated: '2026-03-31'
---
A session in `director-of-ai-cockpit` can touch files in `ciso` via tool calls. Currently boot_up only maps sessions to their project root.

Parse Read/Edit/Bash tool calls from the JSONL to find repos actually touched. Surface these as secondary repo associations so cross-repo work doesn't go invisible.

Low priority — the dirty_repos tool already catches the repo-level view regardless of which session created the files.

Remains low priority. dirty_repos() already covers the repo-level view. Cross-repo tracing is interesting but not on the critical path for instant project context.
