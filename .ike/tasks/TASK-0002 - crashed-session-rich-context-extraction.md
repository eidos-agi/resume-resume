---
id: TASK-0002
title: 'boot_up: extract richer context from crashed sessions'
status: To Do
created: '2026-03-25'
priority: medium
tags:
  - boot_up
  - crash-recovery
  - ux
---
Currently crashed sessions with no cached summary show "Last message: <last user msg>". This is better than blank but still weak.

Improve by extracting from the JSONL tail:
- Last assistant message (what was Claude doing when it crashed)
- Last tool call (what file/repo was being touched)
- Session duration and message count (was this a 2-minute or 2-hour session?)

This gives enough context to decide whether a crashed session is worth resuming without having to read_session first.
