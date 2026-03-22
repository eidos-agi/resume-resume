---
id: "GOAL-006"
type: "goal"
title: "Train T5-small with origin conditioning — target ROUGE-L > 0.40"
status: "available"
date: "2026-03-21"
depends_on: ["GOAL-001", "GOAL-004", "GOAL-003"]
unlocks: []
---

Fine-tune T5-small on origin-conditioned examples. ROUGE-L > 0.40 floor. If stalls: scale to 5000 labels, upgrade to T5-base, more Sonnet labels. Requires GOAL-001 + GOAL-003 + GOAL-005 complete.
