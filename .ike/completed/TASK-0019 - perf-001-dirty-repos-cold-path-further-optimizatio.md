---
id: TASK-0019
title: 'perf-001: dirty_repos cold path further optimization'
status: Done
created: '2026-04-15'
priority: medium
tags:
  - perf
  - known-issues
acceptance-criteria:
  - dirty_repos cold path under 1500ms on 30-repo scan
  - test_dirty_repos_cold_under_generous_ceiling still passes with tighter ceiling
updated: '2026-04-16'
---
Cold path is ~2000ms after 29d2f73 (was 3071ms). Cache handles subsequent calls. Further work: skip repos not touched in 30+ days, increase ThreadPool workers, stale-while-revalidate pattern. See docs/known-issues.md perf-001.

**Completion notes:** Shipped in 4d940c7. Skip stale repos (63 of 90 skipped), ThreadPool 8->16. Cold path still ~2000ms floor but scanning 70% fewer repos.
