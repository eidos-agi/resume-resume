---
id: TASK-0001
title: 'boot_up: dirty repo scanning + urgency scoring'
status: Done
created: '2026-03-25'
completed: '2026-03-25'
priority: high
tags:
  - boot_up
  - dirty-repos
  - crash-recovery
  - core-feature
---
## What was shipped

1. **`dirty_repos` tool** — standalone MCP tool that scans all repos Claude Code has ever touched for dirty git state. No time window. Sorted by urgency (file count + recency of dirty files).

2. **boot_up dirty repo integration** — boot_up now scans all project dirs for git state in parallel, enriches sessions with live dirty file data, and includes a `dirty_repos` section + `scan_report` (negative space).

3. **Urgency scoring** — repos scored by `0.5 * file_count_normalized + 0.5 * recency_of_dirty_files`. Same score flows into boot_up session scoring via `repo_urgency`.

4. **Dirty bypasses age filter** — sessions whose repos are dirty are pulled in regardless of age cutoff. Only the most recent session per dirty repo is included (avoids flooding).

5. **Resume commands** — every session row includes `resume_cmd` with correct `cd <project> && claude --resume <id>`.

6. **Noise filtering** — `~` home sessions with no summary and no dirty files are suppressed.

7. **Last user message extraction** — sessions with no cached summary show last user message from JSONL tail.

## What's left (future tasks)

- TASK-0005: Extract richer context from crashed sessions (beyond last user message)
- TASK-0006: Surface repos touched during a session (cross-repo tracing from tool calls)
- Tests
