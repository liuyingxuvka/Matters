# Matters AI gateway service contract

## Query tools

| Need | Tool | Meaning |
|---|---|---|
| Availability and ResearchGuard status | `capabilities` | Current service/dependency status |
| Find an owner or operation | `list_model_contracts` | Bounded functional model map |
| Inspect one owner | `get_model_contract` | Exact owner purpose and operations |
| Understand one Matter now | `get_situation_context` | Joined bounded situation packet |
| Review what happened | `get_ai_history` | Timeline plus observation, prediction-feedback, and correction history |
| Inspect structure | `get_matter_graph` | Bounded Matter-only graph page |
| Inspect advisory expectations | `get_world_model` | Current World Model page |
| Inspect pending AI clues | `list_pending_ai_feedback` | A3 observations awaiting original-owner validation |

Every query returns or is covered by an A3 query receipt. Query receipts store
the request shape and result identity, not the user's question or a full chat.

## Feedback tools

| Input | Tool | Owner after A3 |
|---|---|---|
| New reported fact/context | `record_user_observation` | C2/C5/C6/C7/C9 or M0 route according to kind |
| Explicit correction | `submit_correction` | C10 invalidation and recomputation |
| Prediction versus later evidence | `record_prediction_feedback` | C11 advisory feedback; contradiction may queue Model Miss |
| Product/model gap | `report_model_miss` | Development pipeline |

A3 records and routes. It never becomes C13, never writes a C1-C12 canonical
field, never completes A2 maintenance, and never edits software rules at
runtime.

## Modality and truth

- `confirmed_observed`: licensed evidence records the event/fact.
- `reported`: a person or source reports it; an owner still evaluates it.
- `planned`: an intention or expected action, not an occurrence.
- `ai_inferred`: advisory reasoning with confidence, alternatives, coverage,
  and expiry.
- prediction: a frozen testable future expectation, never a current fact.

Preserve `as_of`, currentness, gaps, and the original statement. A feedback
receipt proves recording, not factual truth.

## Research and skill boundary

The public `matters` skill and the eleven internal `matters-*` skills are
different products surfaces. The public skill teaches Codex how to use MCP.
The internal pack implements one Matters release and never receives a
machine-global overlay.

ResearchGuard stays external and is the only real research provider.
FlowGuard, WorldGuard, SourceGuard, TraceGuard, LogicGuard, SkillGuard, and
other Guard-family skills are not included in the Matters plugin.
