---
locked: true
locked_date: '2026-04-15'
---
# Decision Criteria — multi-level-ai-management

Each candidate is scored 1-5 on the criteria below. Weights sum to 1.0.

| ID | Criterion | Weight | Meaning |
|---|---|---|---|
| C1 | Learning value | 0.30 | How much does this teach us about multi-level AI management? The deliverable IS the experience. |
| C2 | Human attention efficiency | 0.25 | Does this keep the human at the highest-leverage decisions? Lower volume + higher abstraction = higher score. |
| C3 | Reversibility / blast radius | 0.15 | If it goes wrong, can we back out? Single-user tool = low blast radius is acceptable. |
| C4 | Feedback-loop quality | 0.15 | Can we tell whether changes are working? Short, instrumented loops score higher. |
| C5 | Fit with existing constraints | 0.10 | fastmcp v2 middleware, claude -p fixed cost, visionlog guardrails already in place. |
| C6 | Cost to rework | 0.05 | If we pick wrong, how expensive to pivot? Lower is better. |

## Candidates to be scored

- `a1-only-human-is-a2` — Build A1 (product-improvement AI) now; human manually does A2's job for 2 months; automate A2 once ground truth exists. (Claude's original recommendation.)
- `full-stack-now` — Build A1 + A2 simultaneously; A1 auto-applies within guardrails; A2 watches A1 and proposes methodology changes to human. (User's preferred option.)
- `defer` — Do not build beyond current self_insights; continue with ad-hoc manual review. (Null option.)
