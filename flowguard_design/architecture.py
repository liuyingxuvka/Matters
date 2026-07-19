"""Native FlowGuard code-structure recommendation derived from M0/C1-C12."""

from __future__ import annotations

from flowguard import (
    CodeStructureRecommendation,
    TargetModuleRecommendation,
    review_code_structure_recommendation,
)

from flowguard_design.inventory import (
    CHILD_IDS,
    HELPER_MODULES,
    MODEL_MODULES,
    MODEL_ORDER,
    MODELS,
    MODULE_PATHS,
    PARENT_ID,
)


def _primary_module(model_id: str) -> TargetModuleRecommendation:
    spec = MODELS[model_id]
    module_id = MODEL_MODULES[model_id]
    public_entrypoints = (
        ("MatterService.review",)
        if model_id == PARENT_ID
        else (f"{module_id}.apply",)
    )
    rationale = (
        "M0 owns orchestration order and evidence joins only; it cannot write "
        "a child canonical field."
        if model_id == PARENT_ID
        else (
            f"{model_id} is the unique model and code owner for its declared "
            "canonical fields and side-effect boundary."
        )
    )
    return TargetModuleRecommendation(
        module_id=module_id,
        path=MODULE_PATHS[module_id],
        layer="parent" if model_id == PARENT_ID else "child",
        owns_function_blocks=(f"{model_id}:finite_transition",),
        owns_state=spec.owned_write_fields,
        owns_side_effects=spec.side_effect_classes,
        owns_fields=spec.owned_write_fields,
        reads_fields=spec.state_fields,
        writes_fields=spec.owned_write_fields,
        public_entrypoints=public_entrypoints,
        validation_boundaries=(
            f"leaf-matrix:{model_id}",
            f"contract:{model_id}",
            f"conformance:{model_id}",
        ),
        rationale=rationale,
    )


def recommendation() -> CodeStructureRecommendation:
    primary_modules = tuple(
        _primary_module(model_id) for model_id in MODEL_ORDER
    )
    helper_modules = tuple(
        TargetModuleRecommendation(
            module_id=module_id,
            path=MODULE_PATHS[module_id],
            layer="helper",
            validation_boundaries=(f"delegation:{module_id}",),
            rationale=rationale,
        )
        for module_id, rationale in HELPER_MODULES.items()
    )
    adapter_modules = (
        TargetModuleRecommendation(
            "providers.base",
            path=MODULE_PATHS["providers.base"],
            layer="adapter",
            public_entrypoints=("ReadOnlyProvider.discover", "ReadOnlyProvider.read"),
            validation_boundaries=(
                "provider-envelope-schema",
                "provider-read-only-capability",
                "terminal-disposition-schema",
            ),
            rationale="Provider-neutral discovery/read contracts own no canonical state.",
        ),
        TargetModuleRecommendation(
            "providers.filesystem",
            path=MODULE_PATHS["providers.filesystem"],
            layer="adapter",
            public_entrypoints=("FilesystemReadOnlyAdapter.discover", "FilesystemReadOnlyAdapter.read"),
            validation_boundaries=(
                "root-containment",
                "symlink-junction-cycle",
                "bounded-depth-partition-boundary",
                "no-whole-tree-memory-retry",
                "change-during-read",
                "cloud-placeholder",
            ),
            rationale="Metadata-first local discovery, bounded child partitioning, and content reads delegate tracking and coverage to C1 and freshness to C2.",
        ),
        TargetModuleRecommendation(
            "application.partitioned_filesystem",
            path=MODULE_PATHS["application.partitioned_filesystem"],
            layer="adapter",
            public_entrypoints=("PartitionedFilesystemRunner.run",),
            validation_boundaries=(
                "private-manifest-only",
                "atomic-checkpoint",
                "safe-child-containment",
                "resume-after-interruption",
                "inventory-not-content-overclaim",
            ),
            rationale=(
                "The C1-delegated coordinator checkpoints bounded directory "
                "scopes without becoming a second authorization or coverage owner."
            ),
        ),
        TargetModuleRecommendation(
            "providers.gmail",
            path=MODULE_PATHS["providers.gmail"],
            layer="adapter",
            public_entrypoints=("GmailReadOnlyAdapter.discover", "GmailReadOnlyAdapter.read"),
            validation_boundaries=(
                "gmail-read-only",
                "gmail-page-cursor",
                "gmail-thread-attachment-provenance",
                "spam-trash-policy",
            ),
            rationale="Gmail pagination and reads cannot send, delete, archive, or change labels.",
        ),
        TargetModuleRecommendation(
            "providers.documents",
            path=MODULE_PATHS["providers.documents"],
            layer="adapter",
            public_entrypoints=("DocumentExtractor.extract",),
            validation_boundaries=(
                "document-resource-budget",
                "page-passage-anchor",
                "spreadsheet-no-formula-execution",
                "unsupported-visible",
            ),
            rationale="Bounded document and spreadsheet extraction emits source parts and gaps only.",
        ),
        TargetModuleRecommendation(
            "providers.images",
            path=MODULE_PATHS["providers.images"],
            layer="adapter",
            public_entrypoints=("ImageExtractor.extract",),
            validation_boundaries=(
                "image-resource-budget",
                "ocr-region-anchor",
                "exif-separate-from-event",
                "visual-inference-advisory",
            ),
            rationale="Image metadata, OCR, and inference remain distinct evidence modalities.",
        ),
        TargetModuleRecommendation(
            "providers.cloud",
            path=MODULE_PATHS["providers.cloud"],
            layer="adapter",
            validation_boundaries=("placeholder-versus-hydrated",),
            rationale="Cloud placeholder metadata never proves content was read.",
        ),
        TargetModuleRecommendation(
            "analysis.research",
            path=MODULE_PATHS["analysis.research"],
            layer="adapter",
            public_entrypoints=("ResearchOperationRunner.run",),
            validation_boundaries=(
                "single-researchguard-provider",
                "researchguard-currentness",
                "no-legacy-guard-fallback",
                "scope-bound-work-package",
            ),
            rationale="One abstract ResearchOperation binds ResearchGuard only when its exact external identity is current.",
        ),
        TargetModuleRecommendation(
            "infrastructure.sqlite",
            path=MODULE_PATHS["infrastructure.sqlite"],
            layer="adapter",
            validation_boundaries=("external-private-root", "append-only-transaction", "restart-recovery"),
            rationale="Durable private repositories live under MATTERS_HOME and implement owner interfaces.",
        ),
        TargetModuleRecommendation(
            "infrastructure.blobs",
            path=MODULE_PATHS["infrastructure.blobs"],
            layer="adapter",
            validation_boundaries=("external-private-root", "immutable-blob", "reference-integrity"),
            rationale="Private immutable source bodies never enter the repository.",
        ),
        TargetModuleRecommendation(
            "infrastructure.jobs",
            path=MODULE_PATHS["infrastructure.jobs"],
            layer="adapter",
            validation_boundaries=("bounded-queue", "single-writer", "pause-cancel-resume", "checkpoint-recovery"),
            rationale="Background work executes bounded owner requests; it never owns final verification.",
        ),
        TargetModuleRecommendation(
            "skills.manifest",
            path=MODULE_PATHS["skills.manifest"],
            layer="adapter",
            validation_boundaries=("consumer-manifest-schema", "no-author-control-residual"),
            rationale="The immutable app-local Skill Pack declares exact consumer identities.",
        ),
        TargetModuleRecommendation(
            "skills.resolver",
            path=MODULE_PATHS["skills.resolver"],
            layer="adapter",
            public_entrypoints=("SkillResolver.resolve",),
            validation_boundaries=("pep440-order", "compatibility-range", "singular-active-view", "freshness"),
            rationale="Resolves bundled, machine-installed, and active-view layers without mutating them.",
        ),
        TargetModuleRecommendation(
            "skills.managed_install",
            path=MODULE_PATHS["skills.managed_install"],
            layer="adapter",
            validation_boundaries=("matters-managed-only", "transactional-activation", "rollback"),
            rationale="Only Matters-managed machine projections may be synchronized automatically.",
        ),
        *tuple(
            TargetModuleRecommendation(
                module_id,
                path=MODULE_PATHS[module_id],
                layer="facade",
                public_entrypoints=(entrypoint,),
                validation_boundaries=("facade-delegates-to-orchestrator",),
                rationale="Delegates to one MatterService path and owns no business-success branch.",
            )
            for module_id, entrypoint in (
                ("api.cli", "matters"),
                ("api.http", "application"),
                ("api.mcp", "MattersMCP"),
            )
        ),
    )
    function_map = tuple(
        (f"{model_id}:finite_transition", MODEL_MODULES[model_id])
        for model_id in MODEL_ORDER
    )
    state_map = tuple(
        (field, MODEL_MODULES[model_id])
        for model_id in MODEL_ORDER
        for field in MODELS[model_id].owned_write_fields
    )
    side_effect_map = tuple(
        (effect, MODEL_MODULES[model_id])
        for model_id in MODEL_ORDER
        for effect in MODELS[model_id].side_effect_classes
    )
    field_reader_map = tuple(
        (field, MODEL_MODULES[model_id])
        for model_id in MODEL_ORDER
        for field in MODELS[model_id].state_fields
    )
    return CodeStructureRecommendation(
        recommendation_id="CSR0_matters_model_derived_structure",
        source_model_id=PARENT_ID,
        source_model_path=(
            "flowguard_models/models/m00_end_to_end_authority.py"
        ),
        source_model_evidence_tier="mesh_green",
        parent_module_id="matters",
        target_modules=primary_modules + helper_modules + adapter_modules,
        function_block_map=function_map,
        state_owner_map=state_map,
        side_effect_owner_map=side_effect_map,
        field_owner_map=state_map,
        field_reader_map=field_reader_map,
        field_writer_map=state_map,
        public_entrypoint_map=(
            ("MatterService", "application.orchestrator"),
            ("matters", "api.cli"),
            ("application", "api.http"),
            ("MattersMCP", "api.mcp"),
            ("ReadOnlyProvider.discover", "providers.base"),
            ("ReadOnlyProvider.read", "providers.base"),
            (
                "PartitionedFilesystemRunner.run",
                "application.partitioned_filesystem",
            ),
            ("ResearchOperationRunner.run", "analysis.research"),
        ),
        facade_module_id="api.mcp",
        validation_boundaries=tuple(
            f"leaf-matrix:{model_id}" for model_id in MODEL_ORDER
        )
        + (
            "provider-envelope-schema",
            "filesystem-root-containment",
            "filesystem-bounded-partition-resume",
            "gmail-read-only",
            "document-image-resource-budgets",
            "researchguard-currentness",
            "no-legacy-guard-fallback",
            "skill-active-view-singular",
            "managed-install-rollback",
            "facade-delegates-to-orchestrator",
            "no-required-jira-fields-in-core",
        ),
        rationale=(
            "The checked M0/C1-C12 partition determines modules. Canonical "
            "state and side effects have one child owner; orchestration, "
            "helpers, adapters, and facades cannot become alternate writers."
        ),
        hierarchical_model_used=True,
    )


def run_review():
    value = recommendation()
    return value, review_code_structure_recommendation(value)
