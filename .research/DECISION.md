# Decision

**Date:** 2026-04-15
**Status:** Decided
**ADR:** pending visionlog ADR this session

## Decision

Build the full A1+A2 stack now. A1 (product-improvement AI) reads telemetry, writes recommendations, auto-applies low-risk classes within guardrails. A2 (process-management AI) reads A1's config + outputs + telemetry trends and proposes methodology changes to A1. A2's output is what the human sees in the inbox. Every layer is instrumented (audit log of proposals + outcomes) so slow feedback loops remain reviewable.

## Rationale

Scored 25/23/20 vs alternatives. Wins on learning value (deliverable IS the experience of running multi-level AI management) and human attention efficiency (inbox holds only methodology proposals, not per-item approvals). Single-user blast radius keeps A1 auto-apply safe. Slow feedback loops on A2 are a real cost mitigated by instrumenting A2 itself. Fixed-cost LLM constraint (claude -p only) already satisfied. Defers only to formal peer review + human approval of the ADR.
