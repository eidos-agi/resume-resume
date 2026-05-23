---
id: "ADR-001"
type: "decision"
title: "Session origin is the primary routing decision in resume-resume"
status: "accepted"
date: "2026-03-21"
---

## Context

resume-resume surfaces Claude Code sessions so Daniel can pick up where he left off. Sessions fall into two fundamentally different categories:

1. **Human-initiated (interactive)** — Daniel typed the prompts. His brain was inside the problem. He has context, intent, and an interrupted train of thought to recover.
2. **AI-spawned (automated)** — An agent (e.g. Reeves Tower subagent, ralph-loop) ran the session with a programmatic task. Daniel was never in that problem space cognitively.

These two types require completely different cognitive modes:
- Human session → **re-entry** → reconstruct mental state, resume the thread
- AI session → **review/evaluation** → judge what was built, decide whether to ratify

Daniel has stated explicitly: *"I don't resume things that are non-interactive."*

The existing `classify.py` ML ensemble already computes this label (interactive vs automated).

## Decision

Session origin (human vs AI-spawned) is the **primary routing decision** in resume-resume.

- Human sessions → show "resume" affordance, frame summary as "you were..."
- AI sessions → show "review" affordance or exclude from resume list entirely
- Origin label must be included in every training example as a conditioning prefix
- Training on a mixed unlabeled corpus produces poisoned signal
- `classify.py` output must be written as a first-class cache field

## Consequences

- The resume list defaults to human sessions only. AI sessions are a separate review queue.
- Summaries for AI sessions never use "you" framing.
- The T5 training dataset must be split by origin before fine-tuning.

