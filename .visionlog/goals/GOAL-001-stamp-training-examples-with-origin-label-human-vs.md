---
id: "GOAL-001"
type: "goal"
title: "Stamp training examples with origin label (human vs agent)"
status: "complete"
date: "2026-03-21"
depends_on: []
unlocks: []
---

In `dataset.py`, call `classify_session()` from `classify.py` on each session file before writing the training example. Add `"origin": "human" | "agent"` field to every JSONL row. This is the prerequisite for origin-conditioned T5 training.

Files: `claude_session_commons/summarizer/dataset.py`, `claude_session_commons/classify.py`
