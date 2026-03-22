---
id: "GOAL-008"
type: "goal"
title: "Export to ONNX and upload to HuggingFace Hub"
status: "locked"
date: "2026-03-21"
depends_on: ["GOAL-006"]
unlocks: []
---

Once ROUGE-L > 0.40: export to quantized INT8 ONNX (target &lt;80MB), upload to `eidos-agi/session-summarizer` on HF Hub, update inference.py DEFAULT_MODEL_URL, publish model card.
