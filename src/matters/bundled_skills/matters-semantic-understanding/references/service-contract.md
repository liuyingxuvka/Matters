# MatterService semantic-understanding v2 contract

## Frozen input package

Every package binds:

- `package_id` and `package_version`
- `operation_id`, `operation_type`, and `task_kind`
- exact `source_revision_ids`
- optional target `matter_id` and `matter_revision`
- `authorization_id`, `scope_revision`, `inventory_snapshot_id`, and
  `tracking_policy_revision`
- `prompt_contract_id`, `prompt_contract_revision`, and
  `prompt_contract_hash`
- `result_schema_id` and `result_schema_hash`
- required skill id, version, and content hash
- runner/provider identity and `allowed_tool_ids`
- `allowed_evidence_ids`
- `locale_registry_revision` and exact `required_locales`
- disclosure policy, resource budget, and input fingerprint
- immutable control instructions separate from `untrusted_evidence`

No source, evidence, asset, tool, connector, path, or external action outside
that package is available to this skill.

## Typed result

Return an object with:

- exact `package_id` and `package_version`
- `status`: `passed`, `blocked`, or `failed`
- zero or more typed `findings`
- `input_dispositions`
- bounded `gaps`
- stable `failure_class` when non-passing

Every finding contains:

- `finding_type`
- one allowed `owner_target`
- a type-specific `semantic_payload`
- `localized_values` for exactly every required locale
- one or more allowed `evidence_ids`
- `modality`: `observed`, `reported`, `planned`, or `inferred`
- `confidence`: `high`, `medium`, or `low`
- `uncertainty_codes`
- `contradiction_ids`

Allowed finding-to-owner routes are:

- `matter_candidate` to C6
- `person_candidate` to C4
- `event_candidate` or `deadline_candidate` to C5
- `open_loop_candidate` to C8
- typed temporal, lifecycle, or outcome `conflict` to C5, C7, or C9
- `completion_gap` to C9
- `bounded_summary` to C12

`semantic_payload` is a discriminated object owned by the finding type; an
untyped catch-all `attributes` object is not valid. MatterService derives
finding ids, semantic revisions, receipts, and currentness from the frozen
package; model output cannot assert them.

## Complete input accounting

`input_dispositions` contains exactly one row per allowed evidence id with one
of:

- `used`
- `duplicate`
- `irrelevant`
- `insufficient`
- `conflicting`

A passed result with no findings is valid only when every input still has one
complete disposition. Missing or duplicate disposition rows fail validation.

## Ownership and hard boundaries

Passed results remain advisory and enter `automatic_owner_dispatch`; no user
confirmation is required. The declared original owner validates and writes its
own canonical state. Ordinary uncertainty is preserved in typed fields and
does not block. Stale authorization, scope escape, privacy/safety denial,
corrupt input, unavailable required runner/schema/skill, undeclared evidence
or tools, invalid localization, and invalid schema are explicit terminal
failures. Private package content never enters the repository, Git, public
logs, or release receipts.
