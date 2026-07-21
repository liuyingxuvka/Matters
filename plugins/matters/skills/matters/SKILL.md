---
name: matters
description: Use the local Matters information map whenever an AI needs to understand a person's current situations, relevant history, people, events, open loops, outcomes, future predictions, coverage gaps, or latest progress; also use it to record a new user observation, submit an explicit correction, compare a prediction with reality, report a model miss, or invoke bounded Matters maintenance. This is the single public AI gateway, not one of Matters' eleven internal maintenance skills and not a bundled Guard implementation.
---

# Matters

Use the Matters MCP tools as the authoritative AI access path. Do not inspect
the private SQLite store, scrape the UI, infer a write route from a table, or
treat conversation memory as if Matters had recorded it.

## Understand a situation

1. Call `capabilities` when availability or ResearchGuard currentness matters.
2. Call `list_model_contracts` only when the owning model or supported operation
   is unclear. Use `get_model_contract` for one exact owner.
3. Find the relevant Matter with `list_matters`, then call
   `get_situation_context`.
4. Read the packet's `as_of`, modality, currentness, completeness, and `gaps`
   before answering. Keep confirmed/observed, reported, planned, and
   `ai_inferred` statements distinct.
5. Use `get_ai_history`, `get_matter_graph`, `get_world_model`,
   `get_evidence`, or bounded continuations only when the question needs more
   detail. Never request or reconstruct an unbounded personal-data dump.

Treat the context packet as a current read model. It may be partial. A missing
ResearchGuard receipt blocks the research-dependent portion and its
completeness claim, not ordinary Matter/history access. Never substitute
SourceGuard, TraceGuard, LogicGuard, or a guessed web search as an equivalent
ResearchGuard success.

## Leave the right kind of trace

Choose exactly one path:

- New user-provided context that does not say the record is wrong:
  `record_user_observation`.
- An explicit statement that an existing record is wrong:
  `submit_correction`.
- A later licensed observation that tests a frozen prediction:
  `record_prediction_feedback`.
- A software/model/owner gap that Matters cannot represent correctly:
  `report_model_miss`.

For `record_user_observation`, submit one bounded statement, its true
timezone-qualified observation time, and only a short opaque `source_ref`.
Never store the full chat, a local path, URL, token, message body, or secret in
that reference. The returned `pending_owner` receipt means the clue is durable;
it does not mean a canonical fact changed.

Use `submit_correction` only for an explicit correction because C10 invalidates
and recomputes affected owners. Do not disguise an ordinary new detail as a
correction.

Use `record_prediction_feedback` only with evidence already licensed in the
current SituationGraph. Preserve the original prediction and the later
observation. A contradiction may create a model-miss item; it never rewrites
history silently.

Use `report_model_miss` only with an existing opaque `private-evidence:` handle.
Do not fabricate a handle. Runtime model-miss reporting leaves the current
result partial or blocked and never edits code, OpenSpec, FlowGuard, or product
rules automatically.

## Maintenance

Use `list_pending_ai_feedback` to see durable observations waiting for an
owner. A later A2-owned maintenance run may consume them; do not claim
consumption until the owner receipt says so.

Invoke `run_maintenance` for one bounded ordinary cycle or
`run_planned_maintenance` only when the caller supplied its exact run,
authorization, inventory, coverage, changed-object, and resource identities.
Opening the installed UI, first run, explicit invocation, or a registered
source/project change may use the same path. Do not create or assume a daily
schedule; recurrence is explicit user opt-in.

## Distribution boundary

The public `$matters` skill is a thin discovery and routing layer over the
installed Matters service. The eleven `matters-*` maintenance skills are
immutable app-local implementation skills and are not globally overlaid by
this skill.

FlowGuard, WorldGuard, ResearchGuard, SourceGuard, TraceGuard, LogicGuard,
SkillGuard, and other Guard-family projects stay independent. Matters does not
vendor or maintain them. ResearchGuard is the sole external real research
provider.

Read [service-contract.md](references/service-contract.md) when exact tool
selection, feedback semantics, or claim boundaries are needed.
