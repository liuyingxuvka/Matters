"""Native FieldLifecycleMesh for every model-owned canonical field."""

from __future__ import annotations

from flowguard import (
    FIELD_IMPACT_EXTERNAL_CONTRACT,
    FIELD_IMPACT_MIGRATION,
    FIELD_IMPACT_PERMISSION,
    FIELD_IMPACT_SIDE_EFFECT,
    FIELD_IMPACT_STATE,
    FIELD_ROLE_PERMISSION,
    FIELD_ROLE_PRESENTATION,
    FIELD_ROLE_STATE,
    FIELD_LIFECYCLE_REPLACED,
    FieldLifecycleGroup,
    FieldLifecyclePlan,
    FieldLifecycleRow,
    FieldProjection,
    review_field_lifecycle,
)

from flowguard_design.inventory import (
    AFFECTED_SIBLINGS,
    CHILD_IDS,
    DEPENDENCIES,
    MODEL_CODE_CONTRACTS,
    MODEL_MODULES,
    MODEL_ORDER,
    MODELS,
    PARENT_ID,
)
from flowguard_models.agent_operation_models import AGENT_OPERATION_MODELS
from flowguard_models.models.s00_skill_runtime import MODELS as SKILL_RUNTIME_MODELS


FIELD_MODELS = {
    **MODELS,
    **AGENT_OPERATION_MODELS,
    **SKILL_RUNTIME_MODELS,
}
FIELD_MODEL_ORDER = tuple(MODEL_ORDER) + tuple(AGENT_OPERATION_MODELS) + tuple(
    SKILL_RUNTIME_MODELS
)
PRODUCT_MODEL_IDS = frozenset(MODEL_ORDER)
AGENT_OPERATION_MODEL_IDS = frozenset(AGENT_OPERATION_MODELS)
SKILL_RUNTIME_MODEL_IDS = frozenset(SKILL_RUNTIME_MODELS)
EXTRA_MODULES = {
    "A0_matters_source_analysis_operation": "analysis.operations",
    "A1_matters_research_operation": "skills.research",
    "A2_matters_maintenance_orchestrator_operation": (
        "application.maintenance_orchestration"
    ),
    "A3_matters_ai_gateway_operation": "application.ai_gateway",
    **{model_id: "skills.runtime" for model_id in SKILL_RUNTIME_MODELS},
}
EXTRA_DEPENDENCIES = {
    model_id: ()
    for model_id in tuple(AGENT_OPERATION_MODELS) + tuple(SKILL_RUNTIME_MODELS)
}

RETIRED_C12_LOCALIZATION_FIELDS = (
    ("field:retired:C12_projection_bilingual_ui:projection.english", "projection.english"),
    ("field:retired:C12_projection_bilingual_ui:projection.zh_CN", "projection.zh_CN"),
)
LOCALIZED_VALUES_FIELD_ID = (
    "field:C12_projection_bilingual_ui:projection.localized_values"
)
RETIRED_VISUAL_AUTHORITY_FIELDS = (
    (
        "field:retired:C2_source_registry:visual_asset.identity",
        "visual_asset.identity",
        "field:C2_source_registry:gallery_asset.identity",
        "direct_to_gallery_field",
    ),
    (
        "field:retired:C2_source_registry:visual_asset.derivative_revision",
        "visual_asset.derivative_revision",
        "field:C2_source_registry:gallery_asset.derivative_revision",
        "direct_to_gallery_field",
    ),
    (
        "field:retired:C2_source_registry:visual_asset.renderer_identity",
        "visual_asset.renderer_identity",
        "field:C2_source_registry:gallery_asset.renderer_identity",
        "direct_to_gallery_field",
    ),
    (
        "field:retired:C2_source_registry:visual_asset.safety_disposition",
        "visual_asset.safety_disposition",
        "field:C2_source_registry:gallery_asset.safety_disposition",
        "direct_to_gallery_field",
    ),
    (
        "field:retired:C3_evidence_qualification:evidence.visual_eligibility",
        "evidence.visual_eligibility",
        "field:C3_evidence_qualification:evidence.gallery_display_eligibility",
        "direct_to_gallery_field",
    ),
    (
        "field:retired:C10_correction_revocation:correction.card_visual_intent",
        "correction.card_visual_intent",
        "field:C10_correction_revocation:invalidation.hero_disposition",
        "retire_without_value_migration",
    ),
    (
        "field:retired:C11_guard_artifact_prediction:analysis.visual_recommendation_registry",
        "analysis.visual_recommendation_registry",
        "field:C11_guard_artifact_prediction:analysis.hero_generation_registry",
        "retire_without_value_migration",
    ),
    (
        "field:retired:C12_projection_bilingual_ui:matter.card_visual_decision",
        "matter.card_visual_decision",
        "field:C12_projection_bilingual_ui:projection.generated_hero_asset",
        "retire_without_value_migration",
    ),
    (
        "field:retired:C12_projection_bilingual_ui:matter.card_visual_revision",
        "matter.card_visual_revision",
        "field:C12_projection_bilingual_ui:projection.generated_hero_revision",
        "retire_without_value_migration",
    ),
    (
        "field:retired:C12_projection_bilingual_ui:matter.card_visual_selection_mode",
        "matter.card_visual_selection_mode",
        "field:C12_projection_bilingual_ui:projection.generated_hero_brief_fingerprint",
        "retire_without_value_migration",
    ),
    (
        "field:retired:C12_projection_bilingual_ui:matter.card_visual_status",
        "matter.card_visual_status",
        "field:C12_projection_bilingual_ui:projection.generated_hero_status",
        "retire_without_value_migration",
    ),
)
RETIRED_STORAGE_IDENTITY_FIELDS = (
    (
        "field:retired:C2_source_registry:source.content_selection_scan_bound_identity",
        "source.content_selection_scan_bound_identity",
        "field:C2_source_registry:source.content_selection_semantic_identity",
        "recompute_without_scan_revision",
    ),
    (
        "field:retired:C3_evidence_qualification:evidence.anchor_id_list",
        "evidence.anchor_id_list",
        "field:C3_evidence_qualification:evidence.anchor_set_pointer",
        "bounded_pointer_rebase",
    ),
    (
        "field:retired:C1_authorization_coverage:coverage.noncurrent_history_inline",
        "coverage.noncurrent_history_inline",
        "field:C1_authorization_coverage:coverage.noncurrent_history_archive",
        "verified_exact_archive",
    ),
    (
        "field:retired:C12_projection_bilingual_ui:projection.unadmitted_object_identity",
        "projection.unadmitted_object_identity",
        "field:C12_projection_bilingual_ui:projection.admitted_matter_id",
        "exact_c6_admission_only",
    ),
)
PARTITION_FIELDS = (
    ("filesystem.max_depth", "providers.filesystem"),
    ("partition_manifest.manifest_revision", "application.partitioned_filesystem"),
    ("partition_manifest.node.status", "application.partitioned_filesystem"),
    ("partition_manifest.node.parent_node_id", "application.partitioned_filesystem"),
    ("partition_manifest.node.child_node_ids", "application.partitioned_filesystem"),
    ("partition_manifest.node.attempt_count", "application.partitioned_filesystem"),
    ("partition_manifest.node.error_code", "application.partitioned_filesystem"),
    ("partition_manifest.inventory_status", "application.partitioned_filesystem"),
    ("partition_manifest.policy_revision", "application.partitioned_filesystem"),
    (
        "partition_manifest.superseded_manifest_identity",
        "application.partitioned_filesystem",
    ),
    (
        "partition_manifest.superseded_policy_revision",
        "application.partitioned_filesystem",
    ),
    (
        "partition_manifest.retirement_relative_paths",
        "application.partitioned_filesystem",
    ),
    (
        "partition_manifest.last_scope_retirement",
        "application.partitioned_filesystem",
    ),
    ("coverage_stage.active", "infrastructure.sqlite"),
)

HIERARCHY_FIELD_STAGES = {
    "orchestration.hierarchy_stage_terminal_index": "hierarchy_decision_to_ui_reachable",
    "orchestration.hierarchy_freshness_status": "hierarchy_decision_to_ui_reachable",
    "event.matter_relation_candidate": "hierarchy_decision",
    "matter.object_kind": "hierarchy_decision",
    "matter.primary_parent": "containment_current",
    "matter.containment_role": "containment_current",
    "matter.hierarchy_revision": "containment_current",
    "matter.hierarchy_depth_status": "hierarchy_decision",
    "matter.hierarchy_batch_status": "containment_current",
    "matter.hierarchy_publication_request": "hierarchy_projection_current",
    "matter.situation_graph_revision": "hierarchy_projection_current",
    "matter.situation_graph_primary_edges": "containment_current",
    "matter.situation_graph_secondary_edges": "hierarchy_projection_current",
    "matter.situation_graph_continuation": "hierarchy_projection_current",
    "matter.ui_hierarchy_projection_revision": "hierarchy_projection_current",
    "matter.ui_hierarchy_matter_ids": "hierarchy_projection_current",
    "matter.ui_hierarchy_secondary_edges": "hierarchy_projection_current",
    "matter.parent_composition_transaction_status": "containment_current",
    "matter.parent_narrative_scope_revision": "ancestor_rollup_current",
    "matter.parent_narrative_child_projection_revisions": "ancestor_rollup_current",
    "matter.parent_narrative_evidence_revisions": "ancestor_rollup_current",
    "matter.canonicalization_disposition": "hierarchy_decision",
    "matter.canonical_matter_id": "containment_current",
    "matter.admitted_matter_id_authority": "containment_current",
    "matter.canonicalization_materialization": "containment_current",
    "matter.canonicalization_evidence": "hierarchy_decision",
    "work_item.membership": "containment_current",
    "matter.child_state_snapshot": "child_state_current",
    "matter.ancestor_lifecycle_rollup": "ancestor_rollup_current",
    "matter.child_blocking_summary": "child_state_current",
    "matter.ancestor_blocking_rollup": "ancestor_rollup_current",
    "matter.child_outcome_summary": "child_state_current",
    "matter.ancestor_outcome_rollup": "ancestor_rollup_current",
    "invalidation.ancestor_chain_dispositions": "ancestor_rollup_current",
    "revision.hierarchy_dispositions": "containment_current",
    "analysis.hierarchy_proposal_registry": "hierarchy_decision_advisory_only",
    "analysis.situation_world_model_registry": "world_model_advisory_current",
    "analysis.situation_inference_dependency_registry": "world_model_advisory_current",
    "orchestration.coverage_first_gap_index": "ui_reachable",
    "orchestration.human_narrative_status": "hierarchy_projection_current",
    "orchestration.logical_event_projection_status": "hierarchy_projection_current",
    "orchestration.people_relation_status": "hierarchy_projection_current",
    "orchestration.matter_hierarchy_projection_status": "hierarchy_projection_current",
    "orchestration.codex_source_coverage_status": "hierarchy_decision",
    "projection.hierarchy_revision": "hierarchy_projection_current",
    "projection.admitted_matter_id": "hierarchy_projection_current",
    "projection.parent_narrative_revision": "hierarchy_projection_current",
    "projection.parent_narrative_scope_revision": "hierarchy_projection_current",
    "projection.parent_narrative_child_projection_revisions": "hierarchy_projection_current",
    "projection.parent_narrative_evidence_revisions": "hierarchy_projection_current",
    "projection.parent_narrative_refresh_status": "hierarchy_projection_current",
    "ui.situation_graph_view_state": "hierarchy_projection_current",
    "ui.matter_hierarchy_projection": "hierarchy_projection_current",
    "ui.situation_graph_continuation": "hierarchy_projection_current",
    "ui.node_quick_view_state": "ui_reachable",
    "ui.node_quick_view_facts": "ui_reachable",
    "ui.node_quick_view_source_groups": "ui_reachable",
    "ui.source_group_window": "ui_reachable",
}


def _role(model_id: str, field: str) -> str:
    if model_id == CHILD_IDS[0] and (
        "authorization" in field or "private_root" in field
    ):
        return FIELD_ROLE_PERMISSION
    if model_id == CHILD_IDS[11]:
        return FIELD_ROLE_PRESENTATION
    return FIELD_ROLE_STATE


def _plane(model_id: str) -> str:
    if model_id in AGENT_OPERATION_MODEL_IDS:
        return "agent_operation"
    if model_id in SKILL_RUNTIME_MODEL_IDS:
        return "skill_runtime"
    return "product_runtime"


def _parent_group_id(model_id: str) -> str:
    return {
        "product_runtime": "matters-product-fields",
        "agent_operation": "matters-agent-operation-fields",
        "skill_runtime": "matters-skill-runtime-fields",
    }[_plane(model_id)]


def _impacts(model_id: str) -> tuple[str, ...]:
    impacts = [FIELD_IMPACT_STATE]
    if model_id in PRODUCT_MODEL_IDS:
        impacts.append(FIELD_IMPACT_EXTERNAL_CONTRACT)
    if FIELD_MODELS[model_id].side_effect_classes:
        impacts.append(FIELD_IMPACT_SIDE_EFFECT)
    if model_id == CHILD_IDS[0]:
        impacts.append(FIELD_IMPACT_PERMISSION)
    return tuple(dict.fromkeys(impacts))


def _readers(model_id: str) -> tuple[str, ...]:
    readers = [
        MODEL_MODULES[sibling]
        for sibling in AFFECTED_SIBLINGS.get(model_id, ())
        if sibling in MODEL_MODULES
    ]
    readers.append("application.orchestrator")
    if model_id in AGENT_OPERATION_MODEL_IDS:
        readers.append("models.c11_guard_prediction")
    if model_id in CHILD_IDS[5:9]:
        readers.append("presentation.projections")
    return tuple(dict.fromkeys(readers))


def _module(model_id: str) -> str:
    return (
        MODEL_MODULES[model_id]
        if model_id in MODEL_MODULES
        else EXTRA_MODULES[model_id]
    )


def _contract(model_id: str) -> str:
    if model_id == PARENT_ID:
        return "CC-M0-orchestrator"
    if model_id in MODEL_CODE_CONTRACTS:
        return MODEL_CODE_CONTRACTS[model_id]
    return f"CC-{model_id.split('_', 1)[0]}-owner"


def _dependencies(model_id: str) -> tuple[str, ...]:
    return DEPENDENCIES.get(model_id, EXTRA_DEPENDENCIES.get(model_id, ()))


def plan() -> FieldLifecyclePlan:
    groups = [
        FieldLifecycleGroup(
            "matters-product-fields",
            boundary_kind="canonical_state",
            field_ids=tuple(
                f"field:{model_id}:{field}"
                for model_id in MODEL_ORDER
                for field in FIELD_MODELS[model_id].owned_write_fields
            )
            + tuple(field_id for field_id, _ in RETIRED_C12_LOCALIZATION_FIELDS)
            + tuple(
                field_id
                for field_id, _field_name, _replacement, _policy
                in RETIRED_VISUAL_AUTHORITY_FIELDS
            )
            + tuple(
                field_id
                for field_id, _field_name, _replacement, _policy
                in RETIRED_STORAGE_IDENTITY_FIELDS
            ),
            child_group_ids=tuple(
                f"fields:{model_id}" for model_id in MODEL_ORDER
            )
            + (
                "fields:C12_projection_bilingual_ui:retired-localization",
                "fields:retired-visual-authority",
                "fields:retired-storage-identity",
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "Product group accounts only M0/C1-C12 canonical and presentation "
                "state. Private execution identities never enter this group."
            ),
        ),
        FieldLifecycleGroup(
            "matters-agent-operation-fields",
            boundary_kind="private_agent_operation_state",
            field_ids=tuple(
                f"field:{model_id}:{field}"
                for model_id in AGENT_OPERATION_MODELS
                for field in FIELD_MODELS[model_id].owned_write_fields
            ),
            child_group_ids=tuple(
                f"fields:{model_id}" for model_id in AGENT_OPERATION_MODELS
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "A0/A1/A2/A3 execution profiles, concrete execution identities, raw "
                "handles, resource use, and terminal receipts are private runtime "
                "state; only a qualified C11 admission crosses into product state."
            ),
        ),
        FieldLifecycleGroup(
            "matters-skill-runtime-fields",
            boundary_kind="private_skill_runtime_state",
            field_ids=tuple(
                f"field:{model_id}:{field}"
                for model_id in SKILL_RUNTIME_MODELS
                for field in FIELD_MODELS[model_id].owned_write_fields
            ),
            child_group_ids=tuple(
                f"fields:{model_id}" for model_id in SKILL_RUNTIME_MODELS
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "Bundled/local skill selection and execution receipts are private "
                "runtime state and are not product canonical fields."
            ),
        )
    ]
    rows = []
    for model_id in FIELD_MODEL_ORDER:
        fields = FIELD_MODELS[model_id].owned_write_fields
        groups.append(
            FieldLifecycleGroup(
                f"fields:{model_id}",
                boundary_kind="model_owned_leaf_fields",
                parent_group_id=_parent_group_id(model_id),
                field_ids=tuple(
                    f"field:{model_id}:{field}" for field in fields
                ),
                owner_route="field_lifecycle_mesh",
                rationale=f"{model_id} is the unique writer partition.",
            )
        )
        for field in fields:
            field_id = f"field:{model_id}:{field}"
            contract_id = _contract(model_id)
            obligation_id = f"OB-FIELD:{model_id}:{field}"
            rows.append(
                FieldLifecycleRow(
                    field_id=field_id,
                    field_name=field,
                    locations=(_module(model_id),),
                    group_id=f"fields:{model_id}",
                    role=_role(model_id, field),
                    lifecycle="new",
                    behavior_impacts=_impacts(model_id),
                    reader_ids=_readers(model_id),
                    writer_ids=(_module(model_id),),
                    old_field_ids=(
                        tuple(
                            field_id
                            for field_id, _ in RETIRED_C12_LOCALIZATION_FIELDS
                        )
                        if field_id == LOCALIZED_VALUES_FIELD_ID
                        else ()
                    ),
                    disposition=(
                        "migrated"
                        if field_id == LOCALIZED_VALUES_FIELD_ID
                        else "same_contract_repaired"
                    ),
                    disposition_evidence_refs=(
                        f"gate:G4:{model_id}",
                        f"test:planned:{obligation_id}",
                        f"replay:planned:{model_id}",
                    ),
                    projection=FieldProjection(
                        projection_id=f"projection:{field_id}",
                        field_id=field_id,
                        model_obligation_id=obligation_id,
                        code_contract_id=contract_id,
                        required_test_kinds=(
                            "happy_path",
                            "failure_path",
                            "negative_path",
                            "replay",
                        ),
                        external_inputs=tuple(
                            rule.case_id for rule in FIELD_MODELS[model_id].rules
                        ),
                        external_outputs=tuple(
                            dict.fromkeys(
                                rule.decision
                                for rule in FIELD_MODELS[model_id].rules
                            )
                        ),
                        state_reads=FIELD_MODELS[model_id].state_fields,
                        state_writes=(field,),
                        side_effects=FIELD_MODELS[model_id].side_effect_classes,
                        error_paths=tuple(
                            hazard.protected_error_class
                            for hazard in FIELD_MODELS[model_id].hazards
                        ),
                        risk_level="high",
                        evidence_refs=(
                            f"gate:G4:{model_id}",
                            f"test:planned:{obligation_id}",
                            f"replay:planned:{model_id}",
                        ),
                        rationale=(
                        (
                            "Behavior-bearing product field requires the model "
                            "obligation, unique owner contract, negative test, and "
                            "conformance replay."
                            if _plane(model_id) == "product_runtime"
                            else "Private runtime field requires its plane-local "
                            "model obligation, unique writer, negative test, and "
                            "receipt-currentness check; it is not a product contract."
                        )
                        ),
                    ),
                    metadata={
                        "owner_model_id": model_id,
                        "owner_module_id": _module(model_id),
                        "behavior_plane": _plane(model_id),
                        "private_runtime_only": (
                            _plane(model_id) != "product_runtime"
                        ),
                        "depends_on_models": list(
                            _dependencies(model_id)
                        ),
                        **(
                            {
                                "hierarchy_stage": HIERARCHY_FIELD_STAGES[field],
                                "ancestor_invalidation_required": (
                                    HIERARCHY_FIELD_STAGES[field]
                                    in {
                                        "containment_current",
                                        "child_state_current",
                                        "ancestor_rollup_current",
                                    }
                                ),
                                "old_and_new_ancestor_chains_required": (
                                    field
                                    in {
                                        "matter.primary_parent",
                                        "matter.hierarchy_revision",
                                        "matter.parent_composition_transaction_status",
                                        "matter.canonical_matter_id",
                                        "matter.admitted_matter_id_authority",
                                        "matter.canonicalization_materialization",
                                        "matter.child_state_snapshot",
                                        "matter.ancestor_lifecycle_rollup",
                                        "matter.child_blocking_summary",
                                        "matter.ancestor_blocking_rollup",
                                        "matter.child_outcome_summary",
                                        "matter.ancestor_outcome_rollup",
                                        "invalidation.ancestor_chain_dispositions",
                                    }
                                ),
                            }
                            if field in HIERARCHY_FIELD_STAGES
                            else {}
                        ),
                    },
                )
            )
    partition_field_ids = tuple(
        f"field:C1_authorization_coverage:{field_name}"
        for field_name, _location in PARTITION_FIELDS
    )
    groups.append(
        FieldLifecycleGroup(
            "fields:C1_authorization_coverage:partition-runtime",
            boundary_kind="private_partition_runtime_fields",
            field_ids=partition_field_ids,
            owner_route="field_lifecycle_mesh",
            rationale=(
                "C1 delegates bounded private partition checkpoint storage "
                "without transferring authorization or aggregate coverage ownership."
            ),
        )
    )
    for field_name, location in PARTITION_FIELDS:
        field_id = f"field:C1_authorization_coverage:{field_name}"
        obligation_id = f"OB-FIELD:C1_authorization_coverage:{field_name}"
        rows.append(
            FieldLifecycleRow(
                field_id=field_id,
                field_name=field_name,
                locations=(location,),
                group_id="fields:C1_authorization_coverage:partition-runtime",
                role=(
                    FIELD_ROLE_PERMISSION
                    if field_name == "filesystem.max_depth"
                    else FIELD_ROLE_STATE
                ),
                lifecycle="new",
                behavior_impacts=(
                    FIELD_IMPACT_STATE,
                    FIELD_IMPACT_EXTERNAL_CONTRACT,
                    FIELD_IMPACT_PERMISSION,
                    FIELD_IMPACT_SIDE_EFFECT,
                ),
                reader_ids=(
                    "application.partitioned_filesystem",
                    "application.orchestrator",
                    "presentation.projections",
                ),
                writer_ids=("application.partitioned_filesystem",),
                disposition="same_contract_repaired",
                disposition_evidence_refs=(
                    "gate:G4:C1_authorization_coverage",
                    f"test:planned:{obligation_id}",
                    "replay:planned:C1_authorization_coverage",
                ),
                projection=FieldProjection(
                    projection_id=f"projection:{field_id}",
                    field_id=field_id,
                    model_obligation_id=obligation_id,
                    code_contract_id="CC-C1-owner",
                    required_test_kinds=(
                        "happy_path",
                        "failure_path",
                        "negative_path",
                        "replay",
                    ),
                    external_inputs=(
                        "large_root_budget_exceeded",
                        "partition_child_pending_failed_or_stale",
                        "all_partitions_and_items_terminal",
                    ),
                    external_outputs=(
                        "coverage_partitioned_partial",
                        "coverage_partial_partition_open",
                        "coverage_complete_partitioned",
                    ),
                    state_reads=MODELS["C1_authorization_coverage"].state_fields,
                    state_writes=(
                        "coverage.partition_manifest_revision",
                        "coverage.partition_state",
                    ),
                    side_effects=("partition_manifest_write",),
                    error_paths=(
                        "partition_coverage_overclaim",
                        "unbounded_inventory_materialization",
                    ),
                    risk_level="high",
                    evidence_refs=(
                        "gate:G4:C1_authorization_coverage",
                        f"test:planned:{obligation_id}",
                        "replay:planned:C1_authorization_coverage",
                    ),
                    rationale=(
                        "Partition config and durable node fields affect C1 "
                        "resource, resume, and coverage behavior."
                    ),
                ),
                metadata={
                    "owner_model_id": "C1_authorization_coverage",
                    "owner_module_id": "application.partitioned_filesystem",
                    "private_runtime_only": True,
                },
            )
        )
    groups.append(
        FieldLifecycleGroup(
            "fields:C12_projection_bilingual_ui:retired-localization",
            boundary_kind="replaced_presentation_fields",
            parent_group_id="matters-product-fields",
            field_ids=tuple(
                field_id for field_id, _ in RETIRED_C12_LOCALIZATION_FIELDS
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "The two fixed language fields are retired in favor of one "
                "BCP-47 locale-keyed localized-values field."
            ),
        )
    )
    for retired_field_id, retired_field_name in RETIRED_C12_LOCALIZATION_FIELDS:
        rows.append(
            FieldLifecycleRow(
                field_id=retired_field_id,
                field_name=retired_field_name,
                locations=("presentation.projections",),
                group_id="fields:C12_projection_bilingual_ui:retired-localization",
                role=FIELD_ROLE_PRESENTATION,
                lifecycle=FIELD_LIFECYCLE_REPLACED,
                behavior_impacts=(
                    FIELD_IMPACT_EXTERNAL_CONTRACT,
                    FIELD_IMPACT_MIGRATION,
                ),
                reader_ids=(),
                writer_ids=(),
                replacement_field_id=LOCALIZED_VALUES_FIELD_ID,
                disposition="migrated",
                disposition_evidence_refs=(
                    "gate:G4:C12_projection_bilingual_ui",
                    "test:planned:OB-FIELD:C12:locale-keyed-values",
                    "replay:planned:C12_projection_bilingual_ui",
                ),
                scoped_out_reason=(
                    "The retired fixed-language field has no current runtime "
                    "reader or writer; its values migrate into "
                    "projection.localized_values."
                ),
                metadata={
                    "owner_model_id": "C12_projection_bilingual_ui",
                    "replacement_policy": "direct_to_locale_keyed_values",
                },
            )
        )
    groups.append(
        FieldLifecycleGroup(
            "fields:retired-visual-authority",
            boundary_kind="replaced_visual_authority_fields",
            parent_group_id="matters-product-fields",
            field_ids=tuple(
                field_id
                for field_id, _field_name, _replacement, _policy
                in RETIRED_VISUAL_AUTHORITY_FIELDS
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "Real source imagery is direct-migrated only to Images-gallery "
                "fields. Representative/card-visual selection fields are retired "
                "without value migration; new generated-hero work starts from "
                "current Matter identity and theme."
            ),
        )
    )
    for (
        retired_field_id,
        retired_field_name,
        replacement_field_id,
        replacement_policy,
    ) in RETIRED_VISUAL_AUTHORITY_FIELDS:
        owner_model_id = retired_field_id.split(":")[2]
        is_gallery_migration = replacement_policy == "direct_to_gallery_field"
        rows.append(
            FieldLifecycleRow(
                field_id=retired_field_id,
                field_name=retired_field_name,
                locations=(
                    "presentation.visuals"
                    if owner_model_id
                    in {
                        "C10_correction_revocation",
                        "C11_guard_artifact_prediction",
                        "C12_projection_bilingual_ui",
                    }
                    else _module(owner_model_id)
                ,),
                group_id="fields:retired-visual-authority",
                role=(
                    FIELD_ROLE_PRESENTATION
                    if owner_model_id == "C12_projection_bilingual_ui"
                    else FIELD_ROLE_STATE
                ),
                lifecycle=FIELD_LIFECYCLE_REPLACED,
                behavior_impacts=(
                    FIELD_IMPACT_STATE,
                    FIELD_IMPACT_EXTERNAL_CONTRACT,
                    FIELD_IMPACT_MIGRATION,
                ),
                reader_ids=(),
                writer_ids=(),
                replacement_field_id=replacement_field_id,
                disposition=(
                    "migrated"
                    if is_gallery_migration
                    else "deleted"
                ),
                disposition_evidence_refs=(
                    f"gate:G4:{owner_model_id}",
                    f"test:planned:OB-FIELD:{owner_model_id}:retired-visual-authority",
                    f"replay:planned:{owner_model_id}",
                ),
                scoped_out_reason=(
                    "The retired field has no current runtime reader or writer. "
                    + (
                        "Its real-source display value migrates directly to the "
                        "Images-gallery-only replacement."
                        if is_gallery_migration
                        else "Its old value is not migrated because a current "
                        "generated hero must be produced from a new privacy-safe "
                        "Matter brief; there is no compatibility reader or fallback."
                    )
                ),
                metadata={
                    "owner_model_id": owner_model_id,
                    "replacement_policy": replacement_policy,
                    "generated_hero_value_migration_allowed": False,
                },
            )
        )
    groups.append(
        FieldLifecycleGroup(
            "fields:retired-storage-identity",
            boundary_kind="replaced_storage_and_identity_fields",
            parent_group_id="matters-product-fields",
            field_ids=tuple(
                field_id
                for field_id, _field_name, _replacement, _policy
                in RETIRED_STORAGE_IDENTITY_FIELDS
            ),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "Scan-bound selection identity, copied anchor-id lists, inline "
                "noncurrent coverage history, and unadmitted projection identity "
                "are direct-migrated to their single current authorities without "
                "compatibility readers or fallback paths."
            ),
        )
    )
    for (
        retired_field_id,
        retired_field_name,
        replacement_field_id,
        replacement_policy,
    ) in RETIRED_STORAGE_IDENTITY_FIELDS:
        owner_model_id = retired_field_id.split(":")[2]
        rows.append(
            FieldLifecycleRow(
                field_id=retired_field_id,
                field_name=retired_field_name,
                locations=("infrastructure.sqlite",),
                group_id="fields:retired-storage-identity",
                role=(
                    FIELD_ROLE_PRESENTATION
                    if owner_model_id == "C12_projection_bilingual_ui"
                    else FIELD_ROLE_STATE
                ),
                lifecycle=FIELD_LIFECYCLE_REPLACED,
                behavior_impacts=(
                    FIELD_IMPACT_STATE,
                    FIELD_IMPACT_EXTERNAL_CONTRACT,
                    FIELD_IMPACT_MIGRATION,
                    FIELD_IMPACT_SIDE_EFFECT,
                ),
                reader_ids=(),
                writer_ids=(),
                replacement_field_id=replacement_field_id,
                disposition="migrated",
                compatibility_intent=(
                    "one-way bounded direct migration only; no runtime "
                    "compatibility reader or fallback"
                ),
                disposition_evidence_refs=(
                    f"gate:G4:{owner_model_id}",
                    f"test:planned:OB-FIELD:{owner_model_id}:storage-identity-rebase",
                    f"replay:planned:{owner_model_id}",
                ),
                scoped_out_reason=(
                    "The retired representation has no current reader or writer. "
                    "Migration is explicit, bounded, idempotent, and verified "
                    "before original duplicated data is retired."
                ),
                metadata={
                    "owner_model_id": owner_model_id,
                    "replacement_policy": replacement_policy,
                    "startup_migration_allowed": False,
                    "vacuum_owned": False,
                },
            )
        )
    return FieldLifecyclePlan(
        mesh_id="FLM0_matters_canonical_fields",
        discovered_field_ids=tuple(row.field_id for row in rows),
        groups=tuple(groups),
        fields=tuple(rows),
        claim_scope="full",
        allow_scoped_confidence=False,
        notes=(
            "Current fields are direct current-authority fields. The retired "
            "projection.english and projection.zh_CN fields migrate directly "
            "to projection.localized_values. Real-source visual fields migrate "
            "only to Images-gallery fields; old card-visual values never become "
            "generated heroes. There are no aliases, fallback readers, "
            "compatibility paths, or unknown old-field dispositions. "
            "Scan-bound selection identity, copied anchor-id lists, inline "
            "coverage history, and unadmitted projection identity have explicit "
            "one-way bounded migration dispositions with no startup or VACUUM owner. "
            "Hierarchy-bearing fields declare their exact M0 stage and whether "
            "old and new ancestor-chain invalidation is required."
        ),
    )


def run_review():
    value = plan()
    return value, review_field_lifecycle(value)
