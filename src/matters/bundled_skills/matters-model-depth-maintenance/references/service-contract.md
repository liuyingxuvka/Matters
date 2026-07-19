# MatterService model-depth contract

## Input

The service supplies one revision-bound `criteria_map` containing:

- `coverage_terminal`
- `extraction_current`
- `analysis_terminal`
- `evidence_anchored`
- `original_owner_terminal`
- `localization_terminal`
- `representative_visual_terminal`
- `projection_terminal`
- `ui_reachability_terminal`

Each criterion includes applicability, owner, dependency identities, and the
current terminal receipt when one exists.

## Output

Return one state:

- `not_assessed`
- `partial`
- `sufficient`
- `blocked`
- `stale`

Also return exact `missing_criteria`, `non_applicable_criteria`,
`blocking_criteria`, `dependency_fingerprint`, and proposed owner work items.
`sufficient` requires every applicable criterion to be current and terminal.

## Ownership and hard boundaries

Depth is a product assessment, not an AI confidence score. MatterService owns
the assessment and work queue. The skill cannot declare evidence anchored,
original-owner work terminal, a representative visual current, or UI
reachability complete on another owner's behalf.
