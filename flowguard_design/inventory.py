"""Stable model/module/contract inventory shared by all G4 design routes."""

from __future__ import annotations

from flowguard_models.model_mesh import (
    ACCEPTED_INPUTS,
    AFFECTED_SIBLINGS,
    CHILD_IDS,
    DEPENDENCIES,
    PARENT_ID,
)
from flowguard_models.run_model import MODELS


MODEL_ORDER = (PARENT_ID,) + CHILD_IDS

MODEL_MODULES = {
    PARENT_ID: "application.orchestrator",
    CHILD_IDS[0]: "authorization.coverage",
    CHILD_IDS[1]: "provenance.source_registry",
    CHILD_IDS[2]: "provenance.evidence",
    CHILD_IDS[3]: "identity.people",
    CHILD_IDS[4]: "timeline.events",
    CHILD_IDS[5]: "domain.admission",
    CHILD_IDS[6]: "state.lifecycle",
    CHILD_IDS[7]: "state.open_loops",
    CHILD_IDS[8]: "state.outcomes",
    CHILD_IDS[9]: "revisions.corrections",
    CHILD_IDS[10]: "analysis.operations",
    CHILD_IDS[11]: "presentation.projections",
}

MODULE_PATHS = {
    "application.orchestrator": "src/matters/application/orchestrator.py",
    "application.partitioned_filesystem": "src/matters/application/partitioned_filesystem.py",
    "authorization.scopes": "src/matters/authorization/scopes.py",
    "authorization.coverage": "src/matters/authorization/coverage.py",
    "provenance.source_registry": "src/matters/provenance/source_registry.py",
    "provenance.evidence": "src/matters/provenance/evidence.py",
    "provenance.extraction": "src/matters/provenance/extraction.py",
    "identity.people": "src/matters/identity/people.py",
    "identity.roles": "src/matters/identity/roles.py",
    "timeline.events": "src/matters/timeline/events.py",
    "timeline.traces": "src/matters/timeline/traces.py",
    "domain.matters": "src/matters/domain/matters.py",
    "domain.admission": "src/matters/domain/admission.py",
    "domain.relations": "src/matters/domain/relations.py",
    "state.lifecycle": "src/matters/state/lifecycle.py",
    "state.open_loops": "src/matters/state/open_loops.py",
    "state.blocking": "src/matters/state/blocking.py",
    "state.outcomes": "src/matters/state/outcomes.py",
    "revisions.corrections": "src/matters/revisions/corrections.py",
    "revisions.invalidation": "src/matters/revisions/invalidation.py",
    "revisions.deletion": "src/matters/revisions/deletion.py",
    "analysis.guard_bridge": "src/matters/analysis/guard_bridge.py",
    "analysis.guard_receipts": "src/matters/analysis/guard_receipts.py",
    "analysis.forecasts": "src/matters/analysis/forecasts.py",
    "analysis.operations": "src/matters/analysis/operations.py",
    "analysis.research": "src/matters/analysis/research.py",
    "analysis.depth": "src/matters/analysis/depth.py",
    "presentation.narratives": "src/matters/presentation/narratives.py",
    "presentation.localization": "src/matters/presentation/localization.py",
    "presentation.projections": "src/matters/presentation/projections.py",
    "providers.base": "src/matters/providers/base.py",
    "providers.jira": "src/matters/providers/jira/adapter.py",
    "providers.jira.contracts": "src/matters/providers/jira/contracts.py",
    "providers.jira.depth": "src/matters/providers/jira/depth.py",
    "providers.jira.slices": "src/matters/providers/jira/slices.py",
    "providers.filesystem": "src/matters/providers/filesystem/adapter.py",
    "providers.gmail": "src/matters/providers/gmail/adapter.py",
    "providers.documents": "src/matters/providers/documents/adapter.py",
    "providers.images": "src/matters/providers/images/adapter.py",
    "providers.cloud": "src/matters/providers/cloud/adapter.py",
    "providers.connector_bridge": "src/matters/providers/connector_bridge/adapter.py",
    "inventory.owners": "src/matters/inventory/owners.py",
    "infrastructure.sqlite": "src/matters/infrastructure/sqlite/store.py",
    "infrastructure.blobs": "src/matters/infrastructure/blobs/store.py",
    "infrastructure.jobs": "src/matters/infrastructure/jobs/runner.py",
    "infrastructure.capability_status": "src/matters/infrastructure/capability_status/status.py",
    "api.mcp": "src/matters/api/mcp/server.py",
    "api.http": "src/matters/api/http/app.py",
    "api.cli": "src/matters/cli/main.py",
    "skills.manifest": "src/matters/skills/manifest.py",
    "skills.resolver": "src/matters/skills/resolver.py",
    "skills.managed_install": "src/matters/skills/projection.py",
    "ui.index": "ui/index.html",
    "ui.app": "ui/app.js",
    "ui.styles": "ui/styles.css",
}

HELPER_MODULES = {
    "authorization.scopes": (
        "authorization scope value objects only; C1 coverage remains writer"
    ),
    "provenance.extraction": (
        "pure extraction helpers; C3 owns evidence qualification writes"
    ),
    "identity.roles": "role value objects; C4 owns identity and role writes",
    "timeline.traces": "trace assembly helpers; C5 owns temporal writes",
    "domain.matters": "Matter entities; C6 owns admission and membership writes",
    "domain.relations": "relationship values; no automatic causal inference",
    "state.blocking": "blocking value helpers; C8 remains the only writer",
    "revisions.invalidation": (
        "compute invalidation plans; C10 owns append and dispatch"
    ),
    "revisions.deletion": (
        "deletion request values; C10 owns append and propagation"
    ),
    "analysis.guard_receipts": (
        "validate advisory receipt freshness; C11 owns advisory registry"
    ),
    "analysis.forecasts": (
        "forecast values only; never writes current canonical state"
    ),
    "analysis.depth": (
        "pure semantic-depth assessment helpers; C11 owns persisted depth status"
    ),
    "inventory.owners": (
        "paged occurrence/change-set values; C1 owns tracking and C2 owns freshness writes"
    ),
    "presentation.narratives": (
        "narrative formatting; C12 owns projection revision"
    ),
    "presentation.localization": (
        "language rendering; C12 owns semantic equivalence status"
    ),
}

MODEL_CODE_CONTRACTS = {
    model_id: f"CC-{model_id.split('_', 1)[0]}-owner"
    for model_id in CHILD_IDS
}

MODEL_SYMBOLS = {
    PARENT_ID: "MatterService",
    CHILD_IDS[0]: "AuthorizationCoverage",
    CHILD_IDS[1]: "SourceRegistry",
    CHILD_IDS[2]: "EvidenceQualifier",
    CHILD_IDS[3]: "PersonRegistry",
    CHILD_IDS[4]: "EventRegistry",
    CHILD_IDS[5]: "MatterAdmission",
    CHILD_IDS[6]: "LifecycleOwner",
    CHILD_IDS[7]: "OpenLoopOwner",
    CHILD_IDS[8]: "OutcomeOwner",
    CHILD_IDS[9]: "CorrectionCoordinator",
    CHILD_IDS[10]: "AgentOperationOwner",
    CHILD_IDS[11]: "ProjectionOwner",
}

MODEL_TEST_SUITES = {
    CHILD_IDS[0]: "TM01_authorization_coverage",
    CHILD_IDS[1]: "TM02_source_registry",
    CHILD_IDS[2]: "TM03_evidence_qualification",
    CHILD_IDS[3]: "TM04_identity_resolution",
    CHILD_IDS[4]: "TM05_event_trace",
    CHILD_IDS[5]: "TM06_matter_admission",
    CHILD_IDS[6]: "TM07_lifecycle_board_state",
    CHILD_IDS[7]: "TM08_open_loop_blocking",
    CHILD_IDS[8]: "TM09_completion_reopen",
    CHILD_IDS[9]: "TM10_correction_invalidation",
    CHILD_IDS[10]: "TM11_guard_prediction_boundary",
    CHILD_IDS[11]: "TM12_projection_bilingual_ui",
}

ALL_TEST_SUITES = tuple(MODEL_TEST_SUITES.values()) + (
    "TM13_model_mesh_closure",
    "TM14_end_to_end_conformance",
    "TM15_connector_pagination_retry",
    "TM16_bilingual_semantic_equivalence",
    "TM17_revocation_full_propagation",
    "TM18_privacy_public_boundary",
    "TM19_clean_install_release",
    "TM20_autonomous_owner_dispatch",
    "TM21_object_coverage_worker",
    "TM22_representative_visual",
    "TM23_desktop_object_browser",
)

__all__ = [
    "ACCEPTED_INPUTS",
    "AFFECTED_SIBLINGS",
    "ALL_TEST_SUITES",
    "CHILD_IDS",
    "DEPENDENCIES",
    "HELPER_MODULES",
    "MODEL_CODE_CONTRACTS",
    "MODEL_MODULES",
    "MODEL_ORDER",
    "MODEL_SYMBOLS",
    "MODEL_TEST_SUITES",
    "MODELS",
    "MODULE_PATHS",
    "PARENT_ID",
]
