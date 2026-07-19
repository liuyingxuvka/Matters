---
name: matters-card-visual-curation
description: Select one representative card visual from the current MatterService allowlist and return bilingual display text. Use after source assets and document previews exist; never fetch, generate, or treat a visual as identity or event proof.
---

# Matters Card Visual Curation

Read `references/service-contract.md`. Use only the current eligible asset
package supplied by MatterService.

1. Verify the target Matter revision, visual-policy revision, locale-registry
   revision, and `eligible_asset_ids`.
2. Compare only the supplied current photo, existing-image, embedded-image,
   and document-preview candidates.
3. Choose the single candidate that best represents the Matter using
   evidence relevance, human recognizability, legibility, privacy/safety, and
   crop resilience.
4. Return `selected_asset_id`, evidence ids, confidence, bilingual alt text,
   and bilingual selection reason for exactly the required locales.
5. When two candidates are materially tied, use only a package-declared
   `deterministic_fallback_policy_id`; otherwise return the declared
   no-candidate or blocked disposition.
6. Submit the advisory selection through MatterService so C12 validates and
   writes the presentation-only visual authority.

Never return a local path or arbitrary URL, scan adjacent folders, fetch from
the internet, create a synthetic/stock image, select an asset outside the
allowlist, infer identity from a face, or use filename/EXIF alone as event
proof. Standard and compact card density share the same selected asset and
selection revision.
