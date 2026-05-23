---
id: "GOAL-009"
type: "goal"
title: "Wire ONNX model into _window_summary_adapter (replace fallback)"
status: "locked"
date: "2026-03-21"
depends_on: ["GOAL-004", "GOAL-008"]
unlocks: []
---

Once model is on HF Hub and origin conditioning in place: `_window_summary_adapter` classifies session origin first, passes correct prefix to `summarize()`, ONNX model returns sub-100ms summary. Fallback (last user message) remains as safety net.
