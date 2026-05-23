---
id: "GOAL-002"
type: "goal"
title: "Write classify.py origin output to session cache as first-class field"
status: "complete"
date: "2026-03-21"
depends_on: []
unlocks: []
---

The `interactive` / `automated` label from `classify.py` is currently used only for display. It needs to be persisted to `SessionCache` so downstream consumers (TUI, summarizer, resume logic) can read it without re-classifying.

Add `origin` field to the cache schema. Write it on first classify, read it on subsequent calls.

Files: `claude_session_commons/cache.py`, `claude_session_commons/classify.py`
