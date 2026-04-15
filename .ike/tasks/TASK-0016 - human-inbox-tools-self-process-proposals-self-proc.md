---
id: TASK-0016
title: 'Human inbox tools: self_process_proposals, self_process_decide'
status: To Do
created: '2026-04-15'
priority: high
tags:
  - meta-ai
  - human-surface
dependencies:
  - A2-task
acceptance-criteria:
  - Approving a proposal actually modifies A1's config/prompt file
  - Rejection reason is visible to A2 on next run (calibration feedback)
  - Inbox surface shows only pending proposals; decided ones move to history
---
Two MCP tools the human uses weekly. self_process_proposals() returns pending A2 proposals. self_process_decide(id, verdict, reason) applies the decision. On approve: the proposal's target config is edited (A1's prompt file updated, threshold changed, etc.). On reject: proposal marked rejected with reason, fed back to A2's next run as negative feedback.
