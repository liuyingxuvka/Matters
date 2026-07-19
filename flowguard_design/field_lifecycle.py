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
EXTRA_MODULES = {
    "A0_matters_source_analysis_operation": "analysis.operations",
    "A1_matters_research_operation": "skills.research",
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
PARTITION_FIELDS = (
    ("filesystem.max_depth", "providers.filesystem"),
    ("partition_manifest.manifest_revision", "application.partitioned_filesystem"),
    ("partition_manifest.node.status", "application.partitioned_filesystem"),
    ("partition_manifest.node.parent_node_id", "application.partitioned_filesystem"),
    ("partition_manifest.node.child_node_ids", "application.partitioned_filesystem"),
    ("partition_manifest.node.attempt_count", "application.partitioned_filesystem"),
    ("partition_manifest.node.error_code", "application.partitioned_filesystem"),
    ("partition_manifest.inventory_status", "application.partitioned_filesystem"),
)


def _role(model_id: str, field: str) -> str:
    if model_id == CHILD_IDS[0] and (
        "authorization" in field or "private_root" in field
    ):
        return FIELD_ROLE_PERMISSION
    if model_id == CHILD_IDS[11]:
        return FIELD_ROLE_PRESENTATION
    return FIELD_ROLE_STATE


def _impacts(model_id: str) -> tuple[str, ...]:
    impacts = [FIELD_IMPACT_STATE, FIELD_IMPACT_EXTERNAL_CONTRACT]
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
            "matters-canonical-fields",
            boundary_kind="canonical_state",
            field_ids=tuple(
                f"field:{model_id}:{field}"
                for model_id in FIELD_MODEL_ORDER
                for field in FIELD_MODELS[model_id].owned_write_fields
            )
            + tuple(field_id for field_id, _ in RETIRED_C12_LOCALIZATION_FIELDS),
            child_group_ids=tuple(
                f"fields:{model_id}" for model_id in FIELD_MODEL_ORDER
            )
            + ("fields:C12_projection_bilingual_ui:retired-localization",),
            owner_route="field_lifecycle_mesh",
            rationale=(
                "Parent group accounts the complete model-owned field boundary "
                "without putting every leaf into M0."
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
                parent_group_id="matters-canonical-fields",
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
                            "Behavior-bearing canonical field requires the "
                            "model obligation, unique owner contract, negative "
                            "test, and conformance replay."
                        ),
                    ),
                    metadata={
                        "owner_model_id": model_id,
                        "owner_module_id": _module(model_id),
                        "depends_on_models": list(
                            _dependencies(model_id)
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
            parent_group_id="matters-canonical-fields",
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
            "to projection.localized_values; there are no aliases, fallback "
            "readers, compatibility paths, or unknown old-field dispositions."
        ),
    )


def run_review():
    value = plan()
    return value, review_field_lifecycle(value)
