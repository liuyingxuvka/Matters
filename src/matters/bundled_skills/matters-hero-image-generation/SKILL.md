---
name: matters-hero-image-generation
description: Generate one private photorealistic documentary/editorial hero for each eligible root Matter from a minimized topic-and-theme brief. Use only after identity, merge, hierarchy, permission, and safety dispositions are current; child Matters, WorkItems, Events, Sources, and quick views are not applicable, and source images, excerpts, private identifiers, brands, literal text, or identifiable people are forbidden.
---

# Matters Hero Image Generation

Read `references/service-contract.md`. Work only through MatterService and the
private `hero_image_generator` capability route.

1. Request a current minimized hero brief. It contains bounded topic/theme
   concepts and negative constraints, never source excerpts or user records.
2. Verify the Matter is a root and that
   identity, merge, hierarchy, permission, safety, policy, and brief
   fingerprints are current. Child Matters, WorkItems, Events, Sources,
   SourceVersions, and quick views terminate as `not_applicable` without a
   generation request or placeholder.
3. Generate one photorealistic candid documentary/editorial photograph with
   natural available light, a plausible real-world environment, and an
   ordinary camera perspective. The scene-defining physical place, objects,
   equipment, and activity must be specific enough that the Matter is
   recognizable without a caption. At least two independently recognizable
   Matter-specific physical cues must dominate the frame; a person, pose, or
   generic work activity cannot be the only distinguishing cue. A travel Matter should show a relevant
   destination or transport setting; a heating assessment should show a real
   home heating system; a physics-validation Matter should show its physical
   test apparatus. Prefer object-led or place-led compositions whenever a
   generic person at a desk or computer would be interchangeable with another
   Matter.
4. Use only fictional, generic, non-identifiable people, preferably at medium
   distance or without face emphasis. The image is a presentation-only
   reconstruction and must not imply that the depicted scene actually
   happened.
5. Reject abstract or conceptual illustration, vector/icon art, 3D or
   isometric rendering, infographic, collage, diagram, poster, surreal or
   metaphorical composition, generic office or desk scenes without
   topic-specific objects or activity, screenshot,
   email/message/document preview, legible screen content,
   literal text, logos, brands, private identifiers, paths, source excerpts, or
   identifiable/recognizable real people.
6. Return image bytes plus browser-safe media type and equivalent non-empty
   English/Chinese alt text through the private registration boundary.
   Alt text describes the photographic scene and never calls it abstract,
   conceptual, an illustration, a render, or a metaphor.
7. Review the current card crop after publication. If the image could
   represent an unrelated Matter, lacks two independently recognizable
   Matter-specific physical cues, defaults to a generic person at a computer,
   or omits the Matter-specific setting, equipment, objects, or activity,
   invoke the typed `quality` refresh, retire the old private token, and
   generate exactly one replacement from the new pending brief.
8. On a typed failure, record one bounded retry; after exhaustion publish only
   the declared blocked placeholder.

The hero is presentation-only. It is never a SourceVersion, EvidenceAnchor,
Matter identity, event proof, or Images-gallery item. Real photos, screenshots,
attachments, and document previews remain only in the Images evidence gallery.
For eligible root Matters, standard and compact cards share the same generated hero and revision.

Only identity, topic, theme, merge, split, reparent, permission, safety,
policy, or a typed visual-quality review invalidates a current hero. Ordinary
new clues, summary wording, translation, scanning, retries, technical receipts,
or start-time changes do not regenerate it.

The software is model-independent and never requests an API key or calls a
provider API directly. `maintenance_orchestrator` may delegate this bounded
lane to any compatible Codex-hosted image capability. `research_operation`
and ResearchGuard remain separate evidence-enrichment work and cannot generate
or publish the hero.

Shared handoff vocabulary: `deterministic_hard_exclusion`,
`deterministic_preprocessor`, `low_cost_annotator`, `ambiguity_resolver`,
`matter_modeler`, `hero_image_generator`, `consistency_reviewer`,
`maintenance_orchestrator`, `source_neighborhood_id`, `source_group_chain`,
`source_group_labels`, `source_spatial_context_revision`, parent, child,
WorkItem hierarchy audit, English/Chinese title, summary, topic type,
`generated_hero`, and `research_operation`. Canonical state never exposes an
absolute path publicly and never binds a named model, API key, direct API, or
fallback.

This presentation skill cannot create a Matter. Program, cache, and
internal-application records remain hard-excluded before this route.

Contract applicability: storage_pointer=not_applicable_no_source_original_access;
source_group=not_applicable_opaque_gate_only;
situation_graph=not_applicable_no_graph_node_access;
world_model=not_applicable_no_inference_access;
hero=applicable_root_only_generation_child_not_applicable;
unattended=applicable_bounded_generation_no_final_verification.

This skill receives no original file, message body, source image, SourceGroup
membership, SituationGraph node, or World Model inference. It consumes only
the minimized root-Matter brief and stores only the private generated
presentation asset and its derived registration state. Source originals remain
in place; they are never copied into the Skill Pack or used as a Hero fallback.
A missing compatible machine-installed skill means this bundled consumer is
used internally without creating a machine-global installation.
