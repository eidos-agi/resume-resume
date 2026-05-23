---
id: TASK-0016
title: Fix cache invalidation — stop busting on active sessions
status: To Do
created: '2026-03-31'
priority: High
milestone: MS-0001
tags:
  - performance
  - cache
  - commons
acceptance-criteria:
  - Calling session_summary twice on an active session within 5 minutes returns cached
  result on second call
  - No regression on stale summary detection for genuinely changed sessions
  - Change lives in commons cache.py, not resume-resume
definition-of-done:
  - Active session summaries survive new message appends without full invalidation
  - Cache hit rate >80% for sessions accessed within 1 hour
  - Summary still refreshes when session content changes meaningfully (>10 new messages
  or >50KB growth)
---
cache.py:32-38 uses md5(path:mtime) as cache key. Every message to an active session changes mtime, invalidating the summary cache. The sessions you use most are the ones that never have cached summaries. Change key to use file size + last entry hash, or add a staleness threshold so summaries survive minor appends.
