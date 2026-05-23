---
id: "GUARD-001"
type: "guardrail"
title: "Never mix human and AI-spawned sessions in the resume feed"
status: "active"
date: "2026-03-21"
---

## Rule
The resume-resume session list must never present AI-spawned (automated) sessions alongside human-initiated sessions as if they are equivalent. The default view shows human sessions only. AI sessions belong in a separate review queue.

## Why
Daniel does not resume non-interactive sessions. Presenting them in the resume feed creates wrong expectations at the worst moment — he enters re-entry mode when he should be in evaluation mode. That context switch is expensive and the confusion it causes undermines the entire purpose of the tool.

The origin label is the primary routing decision. Everything else (recency, length, lifecycle state) is secondary.

## Violation Examples
- Showing a Reeves Tower subagent session in the main resume list
- Summarizing an AI session with "you were working on..." framing
- Training the summarizer on mixed unlabeled data without origin conditioning
- Omitting the origin label from the session cache
