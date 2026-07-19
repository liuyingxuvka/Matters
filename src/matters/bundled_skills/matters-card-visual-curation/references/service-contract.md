# MatterService card-visual-curation contract

## Input

The frozen package binds:

- `matter_id` and `matter_revision`
- `visual_policy_revision`
- `locale_registry_revision` and exact `required_locales`
- `eligible_asset_ids`
- allowlisted candidate rows with asset kind, opaque preview handle,
  source/evidence ids, dimensions, privacy disposition, and currentness
- optional `deterministic_fallback_policy_id`

Allowed kinds are `photo`, `existing_image`, `embedded_image`, and
`document_preview`. Candidate bytes or minimized thumbnails remain inside the
private runtime.

## Output

Return:

- exact Matter and policy revisions
- `status`: `selected`, `no_candidate`, `blocked`, or `failed`
- one `selected_asset_id` when selected
- allowed source/evidence ids
- `confidence`: `high`, `medium`, or `low`
- localized `alt_text` and `selection_reason` for every required locale
- privacy and uncertainty dispositions
- the consumed `deterministic_fallback_policy_id` when a declared tie-break
  was required

## Ownership and hard boundaries

The selected id must belong to `eligible_asset_ids` and remain current. The
skill cannot create or fetch evidence, return a filesystem path or arbitrary
URL, infer a person identity from a face, or treat filename, EXIF, OCR, or
visual similarity alone as event proof. C12 owns the presentation-only visual
selection and currentness. Standard and compact cards consume the same
selection; density never triggers a different semantic choice.
