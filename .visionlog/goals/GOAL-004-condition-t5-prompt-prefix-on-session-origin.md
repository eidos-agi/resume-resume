---
id: "GOAL-004"
type: "goal"
title: "Condition T5 prompt prefix on session origin"
status: "complete"
date: "2026-03-21"
depends_on: ["GOAL-001"]
unlocks: []
---

Update summarizer prompt prefix to condition on origin: `"summarize human session: ..."` vs `"summarize agent session: ..."`. Training on mixed unlabeled data produces poisoned signal. Files: `claude_session_commons/summarizer/dataset.py`, `resume-resume/claude_resume/ui_v2.py`
