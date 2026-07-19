# FlowGuard Behavior Commitment Ledger

Keep one BCL structure and one canonical `ledger.json`, but classify every
commitment into exactly one execution plane:

- `product_runtime`: behavior of the product or service seen by an end user or
  external system;
- `agent_operation`: steps the AI performs with tools, files, ports, browsers,
  publishing, or handoff operations;
- `development_process`: planning, validation, release, installation,
  synchronization, and completion gates.

`commitment_kind` remains orthogonal: UI, API, workflow, skill, or process does
not by itself decide the execution plane. Record a structured `actor_kind`,
and connect different planes only through typed relations such as `invokes`,
`validates`, `governs`, or `requires_evidence_from`. Related commitments are
context, not a second set of primary execution instructions.

At task time, perform a bounded lookup before path-only discovery. Match the
declared plane first, then exact commitment ids, tools, error signatures,
paths, workflow families, and task terms. If the plane is ambiguous, show
candidates and continue ordinary discovery; do not guess an owner or force
every action through a model.

For each commitment:

- assign one stable `business_intent_id` to one exact external purpose and keep
  exactly one active commitment for that identity;
- map repeated UI, API, CLI, alias, adapter, wrapper, and compatibility
  surfaces to the same commitment instead of creating delegate commitments;
- name exactly one primary owner model and bind current model, code-contract,
  TestMesh, coverage, and risk evidence;
- keep old or alternate success surfaces out of service through an explicit
  disposition;
- on Model Miss, query the same plane and reuse the existing commitment first;
  create a coverage-gap candidate only when no registered promise exists;
- if `path_sensitive=true`, attach one unambiguous Primary Path Authority
  identity. Legacy plural input is migration evidence only and never a second
  runtime authority.

The Python `model.py` is deliberately a thin loader. Do not rebuild an embedded
inventory beside `ledger.json`; that would create two authorities.
