---
id: "GOAL-010"
type: "goal"
title: "Benchmark: T5-small ONNX latency vs claude -p vs LLM baseline"
status: "locked"
date: "2026-03-21"
depends_on: ["GOAL-008"]
unlocks: []
---

Run 100 summaries through T5-small ONNX (CPU), claude -p Haiku, and claude -p Sonnet. Report wall-clock latency (p50/p99), ROUGE-L vs Sonnet gold labels, token cost at 10K sessions/day. Justifies shipping the fine-tuned model.
