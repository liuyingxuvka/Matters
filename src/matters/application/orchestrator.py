"""M0: the single end-to-end facade over C1-C12 owner services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from matters._version import VERSION
from matters.application.coverage_ledger import (
    ObjectCoverageLedger,
    STAGE_ORDER,
    bounded_stage_output_set_ref,
)
from matters.application.coverage_audit import CoverageAuditService
from matters.application.gmail_coverage_audit import (
    GmailManifestCoverageAuditService,
)
from matters.application.current_scope_reconciliation import (
    GmailCurrentScopeReconciliationOwner,
)
from matters.application.activity import (
    MatterActivityOwner,
    resolve_source_activity_time,
)
from matters.application.ai_gateway import (
    AI_GATEWAY_CONTRACT_REVISION,
    MattersAIGateway,
)
from matters.application.dispatcher import AutonomousFindingDispatcher
from matters.application.hierarchy import MatterHierarchyOwner
from matters.application.maintenance import AutonomousMaintenanceWorker
from matters.application.maintenance_orchestration import (
    MaintenanceOrchestrationOwner,
    MaintenanceOrchestrationService,
    MaintenancePlanner,
    MaintenanceRunRequest,
    MaintenanceTaskExecutor,
)
from matters.application.reconciliation import MatterReconciliationOwner
from matters.application.source_revision_reconciliation import (
    MatterSourceRevisionReconciliationOwner,
)
from matters.application.source_revision_analysis import (
    MatterSemanticAnalysisOwner,
    MatterSourceRevisionAnalysisOwner,
)
from matters.application.source_group_projection import SourceGroupProjection
from matters.application.situation_graph import (
    SituationGraphBuilder,
    SituationGraphSnapshot,
    situation_graph_snapshot_from_payload,
)
from matters.analysis.depth import (
    MatterSemanticDepthOwner,
    SemanticDepth,
    SemanticDepthOwner,
)
from matters.analysis.execution_profiles import (
    CapabilityProfileEntry,
    CodexCapabilityRunner,
    ExecutionProfileRegistry,
)
from matters.analysis.guard_bridge import GuardBridge
from matters.analysis.operations import (
    AgentOperationOwner,
    AgentOperationResult,
    AgentRunner,
    AnalysisWorkPackage,
    ResearchProviderStatus,
)
from matters.analysis.world_inference import PersistentAdvisoryWorldModel
from matters.authorization.coverage import (
    AuthorizationCoverage,
    AuthorizationError,
    CoverageReceipt,
)
from matters.authorization.scopes import AuthorizationScope
from matters.bundled_skills import build_bundle, load_projections
from matters.config import RuntimeConfig
from matters.domain.admission import AdmissionPacket, MatterAdmission
from matters.domain.activity import MaterialClue
from matters.domain.context import (
    ContextSignal,
    GranularityAssessment,
    MatterReconciliationRequest,
    ProjectContext,
)
from matters.domain.hierarchy import (
    HierarchyMemberDisposition,
    MatterChildAttachment,
    MatterWorkItem,
)
from matters.domain.matters import AdmissionDecision, Matter
from matters.domain.relations import MatterRelationCandidate
from matters.identity.people import PersonCandidate, PersonRegistry
from matters.infrastructure.jobs.runner import DurableWorkQueue
from matters.infrastructure.blobs.store import BlobStore
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.inventory.owners import (
    CURRENT_TRACKING_POLICY_REVISION,
    CandidateScope,
    ChangeSet,
    InventoryOccurrence,
    InventoryOwner,
    InventorySnapshot,
    TrackingPolicy,
)
from matters.maintenance.model_miss import ModelMissOwner, ModelMissWorkItem
from matters.presentation.projections import MatterProjection, ProjectionOwner
from matters.presentation.heroes import GeneratedHeroOwner, HeroSubject
from matters.presentation.visuals import VisualAssetOwner
from matters.presentation.browser import (
    ObjectBrowserProjection,
    logical_event_key_for_payload,
    project_matter_only_graph,
)
from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
    rationale_localized,
    user_text_localized,
)
from matters.providers.base import ProviderEnvelope
from matters.provenance.evidence import (
    EvidenceAnchor,
    EvidenceGap,
    EvidenceQualifier,
)
from matters.provenance.extraction import source_assertions
from matters.provenance.source_registry import RegistrationResult, SourceRegistry
from matters.provenance.storage_policy import SourceAvailability
from matters.provenance.source_in_place_migration import (
    apply_database_batch,
    clean_staging,
    create_verified_backup,
    reclaim_orphan_blobs,
    residual_report as source_in_place_residual_report,
    verify_backup as verify_source_in_place_backup,
    verify_migration as verify_source_in_place_migration,
)
from matters.revisions.corrections import (
    CorrectionCoordinator,
    InvalidationPlan,
    RecomputeRequest,
    Revision,
)
from matters.revisions.recompute import OriginalOwnerRecompute, RecomputeBatch
from matters.skills import (
    ActiveSkillResolver,
    ActiveSkillView,
    CandidateValidation,
    FilesystemManagedProjectionStore,
    MachineSkillInventory,
    ManagedProjectionSynchronizer,
    ResearchGuardGate,
    ResearchGuardStatus,
    ResolutionEnvironment,
    ValidationStatus,
    VerificationResult,
    default_codex_skill_root,
    discover_machine_skills,
)
from matters.state.lifecycle import (
    LifecycleDecision,
    LifecycleOwner,
    StateProofPacket,
)


def _parse_observation_time(value: Any) -> datetime | None:
    """Normalize source-observation timestamps without treating due dates as recency."""

    raw = str(value or "").strip()
    if not raw or raw.casefold() in {"none", "null", "unknown"}:
        return None
    normalized = raw.replace("Z", "+00:00")
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for template in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, template)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _raise_followup_plan_conflict() -> dict[str, Any]:
    raise RuntimeError(
        "annotation semantic follow-up identity conflicts with current state"
    )


from matters.state.open_loops import BlockingDecision, OpenLoop, OpenLoopOwner
from matters.state.outcomes import (
    CompletionCriterion,
    OutcomeDecision,
    OutcomeOwner,
)
from matters.timeline.events import Event, EventRegistry, TemporalTrace
from matters.timeline.traces import has_actual_start


@dataclass(frozen=True)
class SourceProcessingResult:
    terminal_status: str
    reason: str
    coverage: CoverageReceipt | None = None
    registration: RegistrationResult | None = None
    evidence: tuple[EvidenceAnchor, ...] = ()
    gaps: tuple[EvidenceGap, ...] = ()
    people: tuple[PersonCandidate, ...] = ()
    trace: TemporalTrace | None = None
    admission: AdmissionDecision | None = None
    lifecycle: LifecycleDecision | None = None
    open_loops: tuple[OpenLoop, ...] = ()
    blocking: BlockingDecision | None = None
    outcome: OutcomeDecision | None = None
    relations: tuple[MatterRelationCandidate, ...] = ()
    projections: tuple[MatterProjection, ...] = ()
    uncertainty_notes: tuple[str, ...] = ()
    child_receipts: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityReport:
    package_status: str
    private_runtime_status: str
    private_runtime_reason: str
    persistence: str
    researchguard: str
    bundled_skill_pack: str
    bundled_skill_count: int
    active_skill_view: str
    machine_skill_inventory: str = "not_checked"
    machine_skill_candidate_count: int = 0
    machine_skill_finding_count: int = 0
    legacy_guard_fallback: str = "rejected"
    maintenance_orchestration: str = "unavailable"
    ai_gateway: str = "available"
    public_gateway_is_internal_skill: bool = False
    guard_family_skills_bundled: bool = False
    recurring_daily_maintenance: str = "explicit_user_opt_in_only"


class MatterService:
    """Stable public facade; it delegates and never becomes a child writer."""

    def __init__(
        self,
        *,
        private_root: Path | str | None = None,
        repository_root: Path | str | None = None,
        research_status: ResearchProviderStatus | None = None,
        codex_executor: Callable[
            [AnalysisWorkPackage, CapabilityProfileEntry],
            Mapping[str, Any],
        ]
        | None = None,
        maintenance_planner: MaintenancePlanner | None = None,
        maintenance_task_executor: MaintenanceTaskExecutor | None = None,
    ) -> None:
        if (maintenance_planner is None) != (
            maintenance_task_executor is None
        ):
            raise ValueError(
                "maintenance planner and task executor must be configured together"
            )
        repo = (
            Path(repository_root)
            if repository_root is not None
            else Path(__file__).resolve().parents[3]
        )
        self.config = RuntimeConfig.resolve(
            repository_root=repo,
            private_root=private_root,
        )
        private_status = self.config.private_status()
        self.store: SQLiteStore | None = None
        self.inventory: InventoryOwner | None = None
        self.work_queue: DurableWorkQueue | None = None
        self.recompute: OriginalOwnerRecompute | None = None
        self.coverage_ledger: ObjectCoverageLedger | None = None
        self.coverage_audit: CoverageAuditService | None = None
        self.blobs: BlobStore | None = None
        self.migrated_coverage_stage_count = 0
        if private_status.status == "active":
            private_path = self.config.activate_private_root()
            self.store = SQLiteStore(private_path, self.config.repository_root)
            self.blobs = BlobStore(private_path, self.config.repository_root)
            self.inventory = InventoryOwner(self.store)
            self.work_queue = DurableWorkQueue(self.store)
            self.recompute = OriginalOwnerRecompute(self.work_queue)
            self.coverage_ledger = ObjectCoverageLedger(self.store)
            self.coverage_audit = CoverageAuditService(self.coverage_ledger)
            self._register_recompute_handlers()
        self.maintenance_orchestration = (
            MaintenanceOrchestrationService(
                planner=maintenance_planner,
                executor=maintenance_task_executor,
                owner=MaintenanceOrchestrationOwner(store=self.store),
            )
            if self.store is not None
            and maintenance_planner is not None
            and maintenance_task_executor is not None
            else None
        )
        self.authorization = AuthorizationCoverage()
        self.sources = SourceRegistry(store=self.store)
        self.evidence = EvidenceQualifier()
        self.people = PersonRegistry()
        self.events = EventRegistry()
        if self.store is not None:
            self.events.restore(
                Event(
                    event_id=str(payload.get("event_id", "")),
                    kind=str(payload.get("kind", "")),
                    modality=str(payload.get("modality", "inferred")),
                    record_time=str(payload.get("record_time", "")),
                    claimed_time=str(payload.get("claimed_time", "")),
                    actor=str(payload.get("actor", "")),
                    object_ref=str(payload.get("object_ref", "")),
                    evidence_ids=tuple(
                        str(item)
                        for item in payload.get("evidence_ids", ())
                        if str(item)
                    ),
                    logical_event_key=str(
                        payload.get("logical_event_key", "")
                    ),
                    current_revision=bool(
                        payload.get("current_revision", True)
                    ),
                    supersedes_event_id=str(
                        payload.get("supersedes_event_id", "")
                    ),
                    temporal_direction=str(
                        payload.get("temporal_direction", "")
                    ),
                    inference_purpose=str(
                        payload.get("inference_purpose", "")
                    ),
                    inference_as_of=str(
                        payload.get("inference_as_of", "")
                    ),
                    target_time=str(payload.get("target_time", "")),
                    revisable=bool(payload.get("revisable", False)),
                    contradiction_triggers=tuple(
                        str(item)
                        for item in payload.get(
                            "contradiction_triggers",
                            (),
                        )
                        if str(item)
                    ),
                )
                for payload in self.store.list_current("temporal_event")
                if str(payload.get("event_id", "")).strip()
            )
        self.admission = MatterAdmission()
        if self.store is not None:
            for payload in self.store.list_current("admission_decision"):
                if str(payload.get("status", "")) != "admitted":
                    continue
                matter_payload = payload.get("matter")
                if not isinstance(matter_payload, Mapping):
                    continue
                self.admission.restore(
                    Matter(
                        matter_id=str(matter_payload["matter_id"]),
                        source_ids=tuple(matter_payload.get("source_ids", ())),
                        rationale=str(matter_payload.get("rationale", "")),
                        evidence_ids=tuple(matter_payload.get("evidence_ids", ())),
                        admitted=bool(matter_payload.get("admitted", True)),
                        semantic_identity_id=str(
                            matter_payload.get("semantic_identity_id", "")
                        ),
                        object_kind=str(
                            matter_payload.get("object_kind", "matter")
                        ),
                    )
                )
        self.lifecycle = LifecycleOwner()
        self.open_loops = OpenLoopOwner()
        self.outcomes = OutcomeOwner()
        durable_revisions = (
            [
                Revision(
                    revision_id=str(item["revision_id"]),
                    kind=str(item["kind"]),
                    target_id=str(item["target_id"]),
                    prior_revision_id=str(item["prior_revision_id"]),
                    rationale=str(item["rationale"]),
                    evidence_ids=tuple(item.get("evidence_ids", ())),
                )
                for item in self.store.list_current("revision")
            ]
            if self.store is not None
            else []
        )
        durable_revisions.sort(
            key=lambda item: int(item.revision_id.rsplit(":", 1)[-1])
        )
        self.corrections = CorrectionCoordinator(_revisions=durable_revisions)
        self.guards = GuardBridge()
        self.operations = AgentOperationOwner(self.store)
        self.migrated_analysis_package_count = 0
        self.depth = SemanticDepthOwner(
            self.store,
            result_sink=(
                lambda results: (
                    self.coverage_ledger.sync_semantic_depth_owner_results(
                        results,
                        refresh_summary=False,
                    )
                )
                if self.coverage_ledger is not None
                else None
            ),
        )
        self.matter_depth = (
            MatterSemanticDepthOwner(
                self.store,
                result_sink=(
                    lambda results: (
                        self.coverage_ledger.sync_semantic_depth_owner_results(
                            results,
                            refresh_summary=False,
                        )
                    )
                    if self.coverage_ledger is not None
                    else None
                ),
            )
            if self.store is not None
            else None
        )
        if self.coverage_ledger is not None:
            self.coverage_ledger.owner_terminal_sink = (
                self._refresh_semantic_depth_for_object
            )
        self.execution_profiles = (
            ExecutionProfileRegistry(self.store)
            if self.store is not None
            else None
        )
        self.codex_runner = (
            CodexCapabilityRunner(
                self.execution_profiles,
                codex_executor,
            )
            if self.execution_profiles is not None
            and codex_executor is not None
            else None
        )
        self.projections = ProjectionOwner()
        self.reconciliation = MatterReconciliationOwner(self.admission)
        self.gmail_current_scope_reconciliation = (
            GmailCurrentScopeReconciliationOwner(self.store)
            if self.store is not None
            else None
        )
        self.source_revision_reconciliation = (
            MatterSourceRevisionReconciliationOwner(self.store)
            if self.store is not None
            else None
        )
        self.source_revision_analysis = (
            MatterSourceRevisionAnalysisOwner(
                store=self.store,
                operations=self.operations,
                reconciliation=self.source_revision_reconciliation,
                locale_registry_revision=DEFAULT_LOCALE_REGISTRY.revision,
            )
            if self.store is not None
            and self.source_revision_reconciliation is not None
            else None
        )
        self.matter_semantic_analysis = (
            MatterSemanticAnalysisOwner(
                store=self.store,
                operations=self.operations,
                locale_registry_revision=DEFAULT_LOCALE_REGISTRY.revision,
            )
            if self.store is not None
            else None
        )
        self.visuals = (
            VisualAssetOwner(store=self.store, blob_store=self.blobs)
            if self.store is not None and self.blobs is not None
            else None
        )
        self.heroes = (
            GeneratedHeroOwner(store=self.store, blob_store=self.blobs)
            if self.store is not None and self.blobs is not None
            else None
        )
        self.retired_visual_override_count = 0
        self.hierarchy = (
            MatterHierarchyOwner(
                self.store,
                coverage_result_sink=(
                    lambda results: (
                        self.coverage_ledger.sync_hierarchy_owner_results(
                            results,
                            refresh_summary=False,
                        )
                    )
                    if self.coverage_ledger is not None
                    else None
                ),
            )
            if self.store is not None
            else None
        )
        self.activity = (
            MatterActivityOwner(
                append_many=self.store.append_many,
                current=self.store.current,
                ancestor_resolver=lambda matter_id: (
                    self.hierarchy.ancestors(
                        matter_id,
                        current_only=True,
                    )
                    if self.hierarchy is not None
                    else ()
                ),
            )
            if self.store is not None
            else None
        )
        self.browser = (
            ObjectBrowserProjection(self.store)
            if self.store is not None
            else None
        )
        self.situation_graph_builder = SituationGraphBuilder()
        self.world_model = (
            PersistentAdvisoryWorldModel(self.store)
            if self.store is not None
            else None
        )
        self.migrated_root_hierarchy_count = 0
        self.dispatcher = (
            AutonomousFindingDispatcher(
                store=self.store,
                coverage_ledger=self.coverage_ledger,
                people=self.people,
                events=self.events,
                admission=self.admission,
                lifecycle=self.lifecycle,
                open_loops=self.open_loops,
                outcomes=self.outcomes,
                projections=self.projections,
                visuals=self.visuals,
                hierarchy=self.hierarchy,
                reconciliation=self.reconciliation,
                activity=self.activity,
                heroes=self.heroes,
            )
            if self.store is not None
            and self.coverage_ledger is not None
            and self.visuals is not None
            and self.activity is not None
            and self.heroes is not None
            else None
        )
        self.maintenance_worker = (
            AutonomousMaintenanceWorker(
                store=self.store,
                ledger=self.coverage_ledger,
                operations=self.operations,
                dispatcher=self.dispatcher,
                runner_provider=lambda: self.codex_runner,
                post_dispatch=self._post_autonomous_dispatch,
                hierarchy_recovery=self._resume_hierarchy_dispositions,
                analysis_expansion=self._resume_source_analysis_expansions,
            )
            if self.store is not None
            and self.coverage_ledger is not None
            and self.dispatcher is not None
            else None
        )
        self.locale_registry_owner = DEFAULT_LOCALE_REGISTRY
        self.migrated_distinct_title_summary_count = 0
        self.migrated_matter_activity_count = 0
        self.prepared_generated_hero_count = 0
        self.research_status = research_status or ResearchProviderStatus(
            "researchguard_pending_integration"
        )
        self.model_misses = (
            ModelMissOwner(self.store, self.work_queue)
            if self.store is not None and self.work_queue is not None
            else None
        )
        self.ai_gateway = MattersAIGateway(self.store)

    def rebase_coverage_stage_schema(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Advance one explicit, bounded coverage-stage schema rebase page."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for coverage rebase")
        if limit < 1 or limit > 500:
            raise ValueError("coverage stage rebase limit is invalid")
        migration_id = "coverage-stage-schema-v2"
        selection_contract = "active_current_object_coverage_v5"
        stage_order_fingerprint = sha256(
            "\0".join(STAGE_ORDER).encode("utf-8")
        ).hexdigest()
        existing = self.store.current("schema_migration", migration_id)
        if (
            existing is not None
            and str(existing.get("status", "")) == "current"
            and str(existing.get("stage_order_fingerprint", ""))
            == stage_order_fingerprint
            and str(existing.get("selection_contract", ""))
            == selection_contract
        ):
            return {
                "scanned_object_count": 0,
                "migrated_object_count": 0,
                "next_cursor": "",
                "has_more": False,
                "status": "current",
            }
        effective_after_object_id = after_object_id
        if (
            not effective_after_object_id
            and existing is not None
            and str(existing.get("status", "")) == "partial"
            and str(existing.get("stage_order_fingerprint", ""))
            == stage_order_fingerprint
            and str(existing.get("selection_contract", ""))
            == selection_contract
        ):
            effective_after_object_id = str(
                existing.get("next_cursor", "")
            )
        rows = self.store.legacy_coverage_stage_schema_page(
            after_object_id=effective_after_object_id,
            limit=limit,
            current_stage_order=STAGE_ORDER,
        )
        migrated = 0
        replacements: list[tuple[str, dict[str, Any]]] = []
        for payload in rows:
            raw_stages = payload.get("stages", {})
            if not isinstance(raw_stages, Mapping):
                raw_stages = {}
            disposition = str(payload.get("disposition", "tracked"))
            current_required = ObjectCoverageLedger.required_stages(
                disposition
            )
            required = tuple(payload.get("required_stages", ()))
            if (
                "visual" not in raw_stages
                and "visual" not in required
                and required == current_required
                and set(raw_stages).issubset(current_required)
            ):
                continue
            stages = {
                str(stage_id): dict(pointer)
                for stage_id, pointer in raw_stages.items()
                if stage_id in current_required
                and isinstance(pointer, Mapping)
            }
            updated_at = datetime.now(timezone.utc).isoformat()
            not_applicable = (
                ObjectCoverageLedger._not_applicable_after_disposition(
                    disposition
                )
            )
            for stage_id in current_required:
                stages.setdefault(
                    stage_id,
                    {
                        "stage_id": stage_id,
                        "status": (
                            "not_applicable"
                            if stage_id in not_applicable
                            else "pending"
                        ),
                        "owner_id": ObjectCoverageLedger._stage_owner(
                            stage_id
                        ),
                        "input_fingerprint": (
                            f"coverage-stage-schema:{stage_order_fingerprint}"
                        ),
                        "output_ref": (
                            f"disposition:{disposition}"
                            if stage_id in not_applicable
                            else ""
                        ),
                        "failure_class": "",
                        "updated_at": updated_at,
                    },
                )
            replacement = dict(payload)
            replacement["required_stages"] = current_required
            replacement["stages"] = stages
            replacement["revision"] = int(payload.get("revision", 1)) + 1
            replacement["updated_at"] = updated_at
            object_id = str(payload["object_id"])
            replacements.append((object_id, replacement))
            migrated += 1
        next_revisions = self.store.next_revisions(
            "object_coverage",
            (object_id for object_id, _replacement in replacements),
        )
        self.store.append_many(
            (
                (
                    "object_coverage",
                    object_id,
                    next_revisions[object_id],
                    replacement,
                )
                for object_id, replacement in replacements
            )
        )
        next_cursor = (
            str(rows[-1].get("object_id", ""))
            if rows
            else ""
        )
        has_more = bool(
            self.store.legacy_coverage_stage_schema_page(
                after_object_id=(
                    next_cursor or effective_after_object_id
                ),
                limit=1,
                current_stage_order=STAGE_ORDER,
            )
        )
        prior_migrated = int(
            existing.get("migrated_object_count", 0)
            if (
                existing is not None
                and str(existing.get("stage_order_fingerprint", ""))
                == stage_order_fingerprint
                and str(existing.get("selection_contract", ""))
                == selection_contract
            )
            else 0
        )
        marker = {
            "migration_id": migration_id,
            "status": "partial" if has_more else "current",
            "migrated_object_count": prior_migrated + migrated,
            "next_cursor": next_cursor if has_more else "",
            "stage_order_fingerprint": stage_order_fingerprint,
            "selection_contract": selection_contract,
        }
        self.store.compare_current_and_append(
            "schema_migration",
            migration_id,
            is_equivalent=lambda current: current == marker,
            payload_factory=lambda _revision, _current: marker,
        )
        self.migrated_coverage_stage_count += migrated
        return {
            "scanned_object_count": len(rows),
            "migrated_object_count": migrated,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def rebase_content_selection(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Explicitly plan one bounded page of existing registered sources."""

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError("MATTERS_HOME is required for content selection")
        from matters.application.content_selection import (
            CONTENT_SELECTION_REVISION,
            ContentSelectionOwner,
        )
        from matters.inventory.owners import InventoryOccurrence

        migration_id = "content-selection-rebase-v2"
        selection_contract = "active_tracked_inventory_identity_v2"
        inventory_identity = self.store.current_inventory_identity()
        planner_fingerprint = sha256(
            (
                CONTENT_SELECTION_REVISION
                + "\0"
                + selection_contract
            ).encode("utf-8")
        ).hexdigest()
        existing = self.store.current("schema_migration", migration_id)
        if (
            existing is not None
            and str(existing.get("status", "")) == "current"
            and str(existing.get("planner_fingerprint", ""))
            == planner_fingerprint
            and str(existing.get("selection_contract", ""))
            == selection_contract
            and str(existing.get("inventory_identity", ""))
            == inventory_identity
        ):
            return {
                "scanned_object_count": 0,
                "planned_object_count": 0,
                "next_cursor": "",
                "has_more": False,
                "status": "current",
            }
        effective_after_object_id = after_object_id
        if (
            not effective_after_object_id
            and existing is not None
            and str(existing.get("status", "")) == "partial"
            and str(existing.get("planner_fingerprint", ""))
            == planner_fingerprint
            and str(existing.get("selection_contract", ""))
            == selection_contract
            and str(existing.get("inventory_identity", ""))
            == inventory_identity
        ):
            effective_after_object_id = str(
                existing.get("next_cursor", "")
            )
        rows, has_more = self.store.content_selection_rebase_page(
            after_object_id=effective_after_object_id,
            limit=limit,
        )
        plans = ContentSelectionOwner(
            self.store,
            self.coverage_ledger,
        ).plan_rows(
            (
                (
                    InventoryOccurrence(**dict(row["occurrence"])),
                    str(row["disposition"]),
                    int(row["inventory_revision"]),
                )
                for row in rows
            )
        )
        self.coverage_ledger.refresh_summary()
        completed_inventory_identity = (
            self.store.current_inventory_identity()
        )
        inventory_changed = (
            completed_inventory_identity != inventory_identity
        )
        next_cursor = str(rows[-1]["object_id"]) if rows and has_more else ""
        prior_planned = int(
            existing.get("planned_object_count", 0)
            if (
                existing is not None
                and str(existing.get("planner_fingerprint", ""))
                == planner_fingerprint
                and str(existing.get("selection_contract", ""))
                == selection_contract
                and str(existing.get("inventory_identity", ""))
                == inventory_identity
            )
            else 0
        )
        marker = {
            "migration_id": migration_id,
            "status": (
                "restart_required"
                if inventory_changed
                else ("partial" if has_more else "current")
            ),
            "planned_object_count": (
                0
                if inventory_changed
                else prior_planned + len(plans)
            ),
            "next_cursor": (
                ""
                if inventory_changed
                else next_cursor
            ),
            "planner_fingerprint": planner_fingerprint,
            "selection_contract": selection_contract,
            "inventory_identity": (
                completed_inventory_identity
                if inventory_changed
                else inventory_identity
            ),
        }
        self.store.compare_current_and_append(
            "schema_migration",
            migration_id,
            is_equivalent=lambda current: current == marker,
            payload_factory=lambda _revision, _current: marker,
        )
        return {
            "scanned_object_count": len(rows),
            "planned_object_count": len(plans),
            "next_cursor": "" if inventory_changed else next_cursor,
            "has_more": has_more or inventory_changed,
            "status": (
                "restart_required"
                if inventory_changed
                else ("partial" if has_more else "current")
            ),
        }

    def archive_object_coverage_history(
        self,
        *,
        after_object_id: str = "",
        after_revision: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Compress one explicit, bounded page of non-current coverage history."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for coverage history archive")
        return self.store.archive_object_coverage_history_page(
            after_object_id=after_object_id,
            after_revision=after_revision,
            limit=limit,
        )

    def rebase_legacy_evidence_pointers(
        self,
        *,
        after_object_id: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Compact one explicit page of current legacy evidence pointers."""

        if self.coverage_ledger is None:
            raise RuntimeError("MATTERS_HOME is required for evidence pointer rebase")
        return self.coverage_ledger.rebase_legacy_evidence_pointers(
            after_object_id=after_object_id,
            limit=limit,
        )

    def rebase_existing_matter_coverage(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Register one bounded, restart-safe page of existing Matters."""

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Matter coverage rebase"
            )
        rows, has_more = self.store.missing_matter_coverage_page(
            after_matter_id=after_matter_id,
            limit=limit,
        )
        registered = self.coverage_ledger.register_matters(
            matters=rows,
            refresh_summary=False,
        )
        matter_ids = tuple(str(row["matter_id"]) for row in rows)
        depth_results = self.store.current_many(
            "semantic_depth",
            matter_ids,
        )
        if depth_results:
            self.coverage_ledger.sync_semantic_depth_owner_results(
                depth_results.values(),
                refresh_summary=False,
            )
        hierarchy_results = self.store.current_many(
            "matter_hierarchy_audit",
            matter_ids,
        )
        if hierarchy_results:
            self.coverage_ledger.sync_hierarchy_owner_results(
                hierarchy_results.values(),
                refresh_summary=False,
            )
        if registered:
            self.coverage_ledger.refresh_summary()
        next_cursor = (
            str(rows[-1]["matter_id"])
            if rows and has_more
            else ""
        )
        return {
            "scanned_matter_count": len(rows),
            "registered_matter_count": len(registered),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def rebase_matter_semantic_depth(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 100,
        max_descendants: int = 1000,
        max_sources: int = 10000,
    ) -> dict[str, Any]:
        """Assess one exact-admission page with a resumable keyset cursor."""

        if (
            self.store is None
            or self.coverage_ledger is None
            or self.matter_depth is None
        ):
            raise RuntimeError(
                "MATTERS_HOME is required for Matter semantic-depth rebase"
            )
        rows, has_more = self.store.canonical_matter_presentation_page(
            after_matter_id=after_matter_id,
            limit=limit,
        )
        results: list[SemanticDepth] = []
        missing_coverage_ids: list[str] = []
        state_counts: dict[str, int] = {}
        for row in rows:
            matter_id = str(row["matter_id"])
            coverage = self.coverage_ledger.current(matter_id)
            if (
                coverage is None
                or not coverage.active
                or coverage.provider != "matters"
            ):
                missing_coverage_ids.append(matter_id)
                continue
            result = self.matter_depth.assess(
                matter_id=matter_id,
                inventory_revision=coverage.inventory_revision,
                max_descendants=max_descendants,
                max_sources=max_sources,
            )
            results.append(result)
            state_counts[result.state] = (
                state_counts.get(result.state, 0) + 1
            )
        if results:
            self.coverage_ledger.refresh_summary()
        next_cursor = (
            str(rows[-1]["matter_id"])
            if rows and has_more
            else ""
        )
        return {
            "scanned_matter_count": len(rows),
            "assessed_matter_count": len(results),
            "missing_coverage_count": len(missing_coverage_ids),
            "missing_coverage_ids": tuple(missing_coverage_ids),
            "state_counts": state_counts,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": (
                "blocked"
                if missing_coverage_ids
                else ("partial" if has_more else "current")
            ),
            "assessment_owner": "M0_matters_end_to_end_authority",
            "assessment_kind": "matter",
        }

    def reconcile_matter_source_revisions(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Reconcile one bounded canonical-Matter source-revision page."""

        if (
            self.store is None
            or self.source_revision_reconciliation is None
        ):
            raise RuntimeError(
                "MATTERS_HOME is required for Matter source reconciliation"
            )
        if limit < 1 or limit > 500:
            raise ValueError("Matter source reconciliation limit is invalid")
        rows, has_more = self.store.canonical_matter_presentation_page(
            after_matter_id=after_matter_id,
            limit=limit,
        )
        results = tuple(
            self.source_revision_reconciliation.reconcile(
                str(row["matter_id"])
            )
            for row in rows
        )
        status_counts: dict[str, int] = {}
        changed_matter_count = 0
        analysis_required_count = 0
        blocked_matter_ids: list[str] = []
        for result in results:
            status = str(result.get("status", "blocked"))
            status_counts[status] = status_counts.get(status, 0) + 1
            if result.get("applied_actions"):
                changed_matter_count += 1
            analysis_required_count += len(
                tuple(result.get("analysis_required", ()))
            )
            if status == "blocked":
                blocked_matter_ids.append(str(result.get("matter_id", "")))
        next_cursor = (
            str(rows[-1]["matter_id"])
            if rows and has_more
            else ""
        )
        return {
            "scanned_matter_count": len(rows),
            "changed_matter_count": changed_matter_count,
            "analysis_required_count": analysis_required_count,
            "blocked_matter_ids": tuple(blocked_matter_ids),
            "status_counts": status_counts,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": (
                "blocked"
                if blocked_matter_ids
                else "partial"
                if has_more
                else "current_with_analysis_required"
                if analysis_required_count
                else "current"
            ),
        }

    def source_revision_analysis_plan(
        self,
        *,
        matter_id: str = "",
        after_matter_id: str = "",
        limit: int = 100,
        queue: bool = False,
    ) -> dict[str, Any]:
        """Plan or queue exact Matter/current-source semantic refreshes."""

        if self.store is None or self.source_revision_analysis is None:
            raise RuntimeError(
                "MATTERS_HOME is required for source revision analysis"
            )
        if limit < 1 or limit > 500:
            raise ValueError("source revision analysis limit is invalid")
        if matter_id:
            matter_ids = (matter_id,)
            has_more = False
        else:
            rows, has_more = self.store.canonical_matter_presentation_page(
                after_matter_id=after_matter_id,
                limit=limit,
            )
            matter_ids = tuple(str(item["matter_id"]) for item in rows)
        items = tuple(
            item
            for current_matter_id in matter_ids
            for item in (
                self.source_revision_analysis.queue(current_matter_id)
                if queue
                else self.source_revision_analysis.plan(current_matter_id)
            )
        )
        status_counts: dict[str, int] = {}
        for item in items:
            status = str(item.get("status", "blocked"))
            status_counts[status] = status_counts.get(status, 0) + 1
        next_cursor = (
            matter_ids[-1] if matter_ids and has_more and not matter_id else ""
        )
        return {
            "scanned_matter_count": len(matter_ids),
            "item_count": len(items),
            "status_counts": status_counts,
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "queue_requested": queue,
            "status": (
                "blocked"
                if status_counts.get("blocked", 0)
                else "partial"
                if has_more
                else "current"
            ),
        }

    def matter_semantic_analysis_plan(
        self,
        *,
        matter_id: str = "",
        after_matter_id: str = "",
        limit: int = 100,
        queue: bool = False,
    ) -> dict[str, Any]:
        """Plan or queue one exact cross-source semantic refresh per Matter."""

        if self.store is None or self.matter_semantic_analysis is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Matter semantic analysis"
            )
        if limit < 1 or limit > 500:
            raise ValueError("Matter semantic analysis limit is invalid")
        if matter_id:
            matter_ids = (matter_id,)
            has_more = False
        else:
            rows, has_more = self.store.canonical_matter_presentation_page(
                after_matter_id=after_matter_id,
                limit=limit,
            )
            matter_ids = tuple(str(item["matter_id"]) for item in rows)
        items = tuple(
            self.matter_semantic_analysis.queue(current_matter_id)
            if queue
            else self.matter_semantic_analysis.plan(current_matter_id)
            for current_matter_id in matter_ids
        )
        status_counts: dict[str, int] = {}
        for item in items:
            status = str(item.get("status", "blocked"))
            status_counts[status] = status_counts.get(status, 0) + 1
        next_cursor = (
            matter_ids[-1] if matter_ids and has_more and not matter_id else ""
        )
        return {
            "scanned_matter_count": len(matter_ids),
            "item_count": len(items),
            "status_counts": status_counts,
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "queue_requested": queue,
            "status": (
                "blocked"
                if status_counts.get("blocked", 0)
                else "partial"
                if has_more
                else "current"
            ),
        }

    def reconcile_gmail_current_scope(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Rebind one bounded Gmail metadata-only page to current tracked scope."""

        if self.gmail_current_scope_reconciliation is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Gmail scope reconciliation"
            )
        if limit < 1 or limit > 500:
            raise ValueError("Gmail scope reconciliation limit is invalid")
        return asdict(
            self.gmail_current_scope_reconciliation.reconcile_page(
                after_object_id=after_object_id,
                limit=limit,
            )
        )

    def rebase_gmail_content_receipts(
        self,
        *,
        after_object_id: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Backfill exact no-body-copy Gmail content receipts."""

        if self.gmail_current_scope_reconciliation is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Gmail content receipt rebase"
            )
        return asdict(
            self.gmail_current_scope_reconciliation.rebase_content_receipts_page(
                after_object_id=after_object_id,
                limit=limit,
            )
        )

    def reconcile_noncanonical_matter_coverage(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Retire one bounded page of projection-leaked Matter coverage."""

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Matter coverage reconciliation"
            )
        object_ids, has_more = self.store.noncanonical_matter_coverage_page(
            after_object_id=after_object_id,
            limit=limit,
        )
        retired = ()
        if not dry_run:
            retired = self.coverage_ledger.retire_objects(
                object_ids=object_ids,
                scope_id="matter:canonical-admission-reconciliation",
                inventory_revision=1,
                reason="noncanonical_hierarchy_projection_leak",
                refresh_summary=False,
            )
            if retired:
                self.coverage_ledger.refresh_summary()
        return {
            "scanned_object_count": len(object_ids),
            "retired_object_count": len(retired),
            "dry_run": dry_run,
            "next_cursor": (
                object_ids[-1] if object_ids and has_more else ""
            ),
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def reconcile_noncanonical_matter_hierarchy(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 200,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Retire one bounded page of hierarchy-only non-Matter authority."""

        if self.store is None:
            raise RuntimeError(
                "MATTERS_HOME is required for Matter hierarchy reconciliation"
            )
        with self.store.immediate_transaction():
            matter_ids, has_more = (
                self.store.noncanonical_matter_hierarchy_page(
                    after_matter_id=after_matter_id,
                    limit=limit,
                )
            )
            result = self.store.retire_noncanonical_matter_hierarchy_ids(
                matter_ids,
                dry_run=dry_run,
            )
        blocked = str(result["status"]) == "blocked"
        next_cursor = (
            after_matter_id
            if blocked
            else (
                matter_ids[-1]
                if matter_ids and has_more
                else ""
            )
        )
        return {
            **result,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": (
                "blocked"
                if blocked
                else ("partial" if has_more else "current")
            ),
        }

    def _retire_canonicalized_hierarchy_authority(
        self,
        matter_id: str,
    ) -> dict[str, Any]:
        """Reuse the hierarchy reconciliation owner inside canonicalization."""

        if self.store is None:
            raise RuntimeError(
                "MATTERS_HOME is required for hierarchy canonicalization"
            )
        result = self.store.retire_noncanonical_matter_hierarchy_ids(
            (matter_id,),
        )
        if str(result["status"]) == "blocked":
            raise ValueError(
                "noncanonical Matter retains an active containment edge: "
                + ",".join(result["blocked_matter_ids"])
            )
        return result

    def content_selection_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Expose bounded, locator-free content-selection progress."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for content selection")
        rows, total = self.store.content_selection_page(
            offset=offset,
            limit=limit,
        )
        return {"items": rows, "total": total, "offset": offset, "limit": limit}

    def reconcile_coverage_inventory_orphans(
        self,
        *,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Retire one bounded page of source coverage absent from inventory."""

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError(
                "MATTERS_HOME is required for coverage reconciliation"
            )
        if limit < 1 or limit > 500:
            raise ValueError("coverage reconciliation limit is invalid")
        object_ids = self.store.orphaned_active_source_coverage_page(
            limit=limit,
        )
        retired = self.coverage_ledger.retire_objects(
            object_ids=object_ids,
            scope_id="inventory:current-occurrence-reconciliation",
            inventory_revision=1,
            reason="absent_from_current_inventory",
            refresh_summary=False,
        )
        has_more = bool(
            self.store.orphaned_active_source_coverage_page(limit=1)
        )
        if retired:
            self.coverage_ledger.refresh_summary()
        return {
            "scanned_object_count": len(object_ids),
            "retired_object_count": len(retired),
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def _migrate_projection_locale_maps(self) -> None:
        """Replace legacy fixed-language current rows with locale-map rows."""

        assert self.store is not None
        migrated = 0
        for payload in self.store.list_current("projection"):
            if "localized_values" in payload:
                continue
            required = {
                "matter_id",
                "semantic_revision",
                "state",
                "rationale",
                "english",
                "zh_cn",
            }
            missing = required - set(payload)
            if missing:
                raise ValueError(
                    "legacy projection migration is missing fields: "
                    + ", ".join(sorted(missing))
                )
            semantic_revision = str(payload["semantic_revision"])
            projection = self.projections.publish(
                matter_id=str(payload["matter_id"]),
                semantic_revision=semantic_revision,
                state=str(payload["state"]),
                rationale=str(payload["rationale"]),
                evidence_ids=tuple(
                    str(item) for item in payload.get("evidence_ids", ())
                ),
                localized_rationale=rationale_localized(
                    str(payload["rationale"]),
                    semantic_revision=semantic_revision,
                ),
                localized_values={
                    "en": str(payload["english"]),
                    "zh-CN": str(payload["zh_cn"]),
                },
            )
            self.store.append(
                "projection",
                projection.matter_id,
                self.store.next_revision("projection", projection.matter_id),
                asdict(projection),
            )
            migrated += 1
        if migrated:
            migration_id = "projection-locale-map-v1"
            self.store.append(
                "schema_migration",
                migration_id,
                self.store.next_revision("schema_migration", migration_id),
                {
                    "migration_id": migration_id,
                    "status": "current",
                    "migrated_projection_count": migrated,
                    "required_locales": list(
                        self.locale_registry_owner.available_locales
                    ),
                    "locale_registry_revision": (
                        self.locale_registry_owner.revision
                    ),
                },
            )

    def _migrate_distinct_title_summary_projections(self) -> int:
        """Project legacy C12 cards into separate localized title and summary."""

        assert self.store is not None
        with self.store.connection_session():
            return self._migrate_distinct_title_summary_projections_connected()

    def _migrate_distinct_title_summary_projections_connected(self) -> int:
        """Run the bounded migration with one reusable SQLite connection."""

        assert self.store is not None
        assert self.dispatcher is not None
        migration_id = "projection-distinct-title-summary-v2"
        selection_contract = (
            "current_projection_exact_owner_join_v2"
        )
        input_fingerprint = (
            self._distinct_title_summary_migration_input_fingerprint()
        )
        existing = self.store.current("schema_migration", migration_id)
        if (
            existing is not None
            and str(existing.get("input_fingerprint", ""))
            == input_fingerprint
            and str(existing.get("selection_contract", ""))
            == selection_contract
        ):
            return 0

        migrated = 0
        blocked = 0
        unchanged = 0
        conflicted = 0
        not_applicable = 0
        checked_projection_count = 0
        owner_records = tuple(
            self.store.iter_current("autonomous_finding")
        )
        owner_packages = self.store.current_many(
            "analysis_work_package",
            tuple(
                dict.fromkeys(
                    str(item.get("package_id", ""))
                    for item in owner_records
                    if str(item.get("package_id", ""))
                )
            ),
        )
        owner_records_by_semantic_revision: dict[
            str,
            list[Mapping[str, Any]],
        ] = {}
        for record in owner_records:
            finding = record.get("finding")
            if not isinstance(finding, Mapping):
                continue
            semantic_revision = str(
                finding.get("semantic_revision", "")
            )
            if semantic_revision:
                owner_records_by_semantic_revision.setdefault(
                    semantic_revision,
                    [],
                ).append(record)
        for projection in tuple(
            self.store.iter_current("projection")
        ):
            checked_projection_count += 1
            projection_semantic_revision = str(
                projection.get("semantic_revision", "")
            )
            disposition = (
                self.dispatcher.rebuild_distinct_title_summary_projection(
                    projection,
                    tuple(
                        owner_records_by_semantic_revision.get(
                            projection_semantic_revision,
                            (),
                        )
                    ),
                    packages_by_id=owner_packages,
                )
            )
            if disposition == "migrated":
                migrated += 1
            elif disposition == "blocked":
                blocked += 1
            elif disposition == "unchanged":
                unchanged += 1
            elif disposition == "conflicted":
                conflicted += 1
            else:
                not_applicable += 1

        final_fingerprint = (
            self._distinct_title_summary_migration_input_fingerprint()
        )
        marker_payload = {
            "migration_id": migration_id,
            "status": (
                "current"
                if blocked == 0 and conflicted == 0
                else "current_with_gaps"
            ),
            "input_fingerprint": final_fingerprint,
            "checked_projection_count": checked_projection_count,
            "migrated_projection_count": migrated,
            "blocked_projection_count": blocked,
            "conflicted_projection_count": conflicted,
            "unchanged_projection_count": unchanged,
            "not_applicable_projection_count": not_applicable,
            "title_owner": "C6_matter_admission",
            "summary_owner": "C12_projection_bilingual_ui",
            "selection_contract": selection_contract,
            "fallback": "forbidden",
        }
        self.store.compare_current_and_append(
            "schema_migration",
            migration_id,
            is_equivalent=lambda current: (
                current is not None
                and str(current.get("input_fingerprint", ""))
                == final_fingerprint
                and str(current.get("selection_contract", ""))
                == marker_payload["selection_contract"]
            ),
            payload_factory=lambda _revision, _current: marker_payload,
        )
        return migrated

    def _migrate_current_matter_activity(self) -> int:
        """Publish direct current activity rows from evidence-bound legacy events."""

        if self.store is None or self.activity is None:
            return 0
        events = self._active_temporal_events(
            self.store.iter_current("temporal_event")
        )
        events_by_matter: dict[str, list[Mapping[str, Any]]] = {}
        events_by_evidence: dict[str, list[Mapping[str, Any]]] = {}
        for event in events:
            object_ref = str(event.get("object_ref", ""))
            if object_ref:
                events_by_matter.setdefault(object_ref, []).append(event)
            for evidence_id in event.get("evidence_ids", ()):
                normalized = str(evidence_id)
                if normalized:
                    events_by_evidence.setdefault(
                        normalized,
                        [],
                    ).append(event)
        eligible_matter_ids = {
            str(item.get("matter", {}).get("matter_id", ""))
            if isinstance(item.get("matter"), Mapping)
            else str(item.get("candidate", {}).get("candidate_id", ""))
            if isinstance(item.get("candidate"), Mapping)
            else ""
            for item in self.store.iter_current("admission_decision")
            if str(item.get("status", "")) in {"admitted", "uncertain"}
        }
        eligible_matter_ids.discard("")
        candidates: list[
            tuple[datetime, Mapping[str, Any], str, tuple[str, ...]]
        ] = []
        source_time_cache: dict[tuple[str, int], datetime | None] = {}
        for projection in self.store.iter_current("projection"):
            matter_id = str(projection.get("matter_id", ""))
            if (
                not matter_id
                or matter_id not in eligible_matter_ids
                or self.store.current("matter_activity", matter_id) is not None
                or str(projection.get("equivalence_status", ""))
                != "equivalent"
            ):
                continue
            evidence_ids = tuple(
                str(item)
                for item in projection.get("evidence_ids", ())
                if str(item)
            )
            if not evidence_ids:
                continue
            relevant_by_id = {
                str(item.get("event_id", "")): item
                for item in (
                    *events_by_matter.get(matter_id, ()),
                    *(
                        event
                        for evidence_id in evidence_ids
                        for event in events_by_evidence.get(evidence_id, ())
                    ),
                )
                if str(item.get("event_id", ""))
            }
            relevant = tuple(
                relevant_by_id[event_id]
                for event_id in sorted(relevant_by_id)
            )
            timed: list[tuple[datetime, str]] = []
            for event in relevant:
                raw = str(event.get("record_time") or "").strip()
                parsed = _parse_observation_time(raw)
                if parsed is not None:
                    timed.append((parsed, raw))
            if not timed:
                observed = self._source_observation_time(
                    evidence_ids=evidence_ids,
                    semantic_revision=str(
                        projection.get("semantic_revision", "")
                    ),
                    cache=source_time_cache,
                )
                if observed is not None:
                    timed.append((observed, observed.isoformat()))
            if not timed:
                continue
            latest = max(timed, key=lambda item: item[0])[0]
            candidates.append(
                (latest, projection, matter_id, evidence_ids)
            )
        migrated = 0
        for latest, projection, matter_id, evidence_ids in sorted(
            candidates,
            key=lambda item: (item[0], item[2]),
        ):
            localized_summary = {
                locale: str(
                    dict(
                        projection.get("localized_rationale", {})
                    ).get(locale, "")
                ).strip()
                for locale in ("en", "zh-CN")
            }
            if not all(localized_summary.values()):
                continue
            semantic_revision = str(
                projection.get("semantic_revision", "")
            )
            clue_id = (
                "activity-migration:"
                + sha256(
                    f"{matter_id}\0{semantic_revision}\0{latest.isoformat()}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:24]
            )
            self.activity.record(
                MaterialClue(
                    clue_id=clue_id,
                    matter_id=matter_id,
                    clue_kind="legacy_semantic_event",
                    user_world_at=latest.isoformat(),
                    disposition="material",
                    rationale=(
                        "Direct migration of the latest current "
                        "evidence-bound semantic event."
                    ),
                    localized_summary=localized_summary,
                    semantic_revision=semantic_revision,
                    evidence_ids=evidence_ids,
                )
            )
            for row in self._coverage_rows_for_matter(matter_id):
                if self.coverage_ledger is not None:
                    self.coverage_ledger.mark_stage(
                        object_id=str(row["object_id"]),
                        stage_id="meaningful_clue_summary",
                        status="current",
                        input_fingerprint=semantic_revision,
                        output_ref=f"matter_activity:{matter_id}",
                        matter_ids=(matter_id,),
                        refresh_summary=False,
                    )
            migrated += 1
        return migrated

    def _source_observation_time(
        self,
        *,
        evidence_ids: Sequence[str],
        semantic_revision: str = "",
        cache: dict[tuple[str, int], datetime | None] | None = None,
    ) -> datetime | None:
        """Return when evidence entered the user's world, never its due time."""

        if self.store is None:
            return None
        refs: list[tuple[str, int]] = []
        semantic = str(semantic_revision).strip()
        if semantic.startswith("source:") and ":v" in semantic:
            source_id, version_text = semantic.rsplit(":v", 1)
            try:
                refs.append((source_id, int(version_text)))
            except ValueError:
                pass
        for evidence_id in evidence_ids:
            raw = str(evidence_id).strip()
            if not raw.startswith("evidence:"):
                continue
            try:
                source_id, version_text, _digest = raw.removeprefix(
                    "evidence:"
                ).rsplit(":", 2)
                refs.append((source_id, int(version_text)))
            except (TypeError, ValueError):
                continue
        observed: list[datetime] = []
        for source_id, version in dict.fromkeys(refs):
            key = (source_id, version)
            if cache is not None and key in cache:
                parsed = cache[key]
            else:
                current = self.store.current("source_version", source_id)
                candidate = (
                    current
                    if current is not None
                    and int(current.get("version", 0) or 0) == version
                    else next(
                        (
                            item
                            for item in self.store.history(
                                "source_version",
                                source_id,
                            )
                            if int(item.get("version", 0) or 0) == version
                        ),
                        None,
                    )
                )
                resolution = resolve_source_activity_time(candidate or {})
                if (
                    not resolution.resolved
                    and isinstance(candidate, Mapping)
                ):
                    reference = candidate.get("external_reference")
                    occurrence_id = (
                        str(reference.get("external_id", ""))
                        if isinstance(reference, Mapping)
                        else ""
                    )
                    occurrence_rows = (
                        self.store.inventory_occurrences_by_object_ids(
                            (occurrence_id,)
                        ).get(occurrence_id, ())
                        if occurrence_id
                        else ()
                    )
                    if occurrence_rows:
                        occurrence = max(
                            occurrence_rows,
                            key=lambda item: (
                                int(item.get("inventory_revision", 0)),
                                str(item.get("scope_id", "")),
                            ),
                        ).get("occurrence", {})
                        resolution = resolve_source_activity_time(occurrence)
                parsed = (
                    _parse_observation_time(resolution.observed_at)
                    if resolution.resolved
                    else None
                )
                if cache is not None:
                    cache[key] = parsed
            if parsed is not None:
                observed.append(parsed)
        return max(observed) if observed else None

    def repair_current_activity_observation_times(self) -> dict[str, Any]:
        """Correct legacy activity that used a scheduled time as clue recency."""

        if self.store is None or self.activity is None:
            raise RuntimeError("MATTERS_HOME is required for activity repair")
        activity_rows = tuple(self.store.iter_current("matter_activity"))
        clue_ids = tuple(
            dict.fromkeys(
                str(item.get("material_clue_id", ""))
                for item in activity_rows
                if str(item.get("material_clue_id", ""))
            )
        )
        clues = self.store.current_many("matter_activity_clue", clue_ids)
        events = self._active_temporal_events(
            self.store.iter_current("temporal_event")
        )
        bound_matter_ids = {
            clue_id: tuple(
                dict.fromkeys(
                    str(item.get("matter_id", ""))
                    for item in activity_rows
                    if str(item.get("material_clue_id", "")) == clue_id
                    and str(item.get("matter_id", ""))
                )
            )
            for clue_id in clue_ids
        }
        source_time_cache: dict[tuple[str, int], datetime | None] = {}
        repaired = 0
        skipped = 0
        for clue_id in clue_ids:
            clue = clues.get(clue_id)
            if clue is None:
                skipped += 1
                continue
            evidence = {
                str(item)
                for item in clue.get("evidence_ids", ())
                if str(item)
            }
            matter_id = str(clue.get("matter_id", ""))
            relevant = tuple(
                event
                for event in events
                if (
                    str(event.get("object_ref", "")) == matter_id
                    or evidence.intersection(event.get("evidence_ids", ()))
                )
            )
            event_times = tuple(
                parsed
                for event in relevant
                if (
                    parsed := _parse_observation_time(
                        event.get("record_time")
                    )
                )
                is not None
            )
            observed = (
                max(event_times)
                if event_times
                else self._source_observation_time(
                    evidence_ids=tuple(clue.get("evidence_ids", ())),
                    semantic_revision=str(
                        clue.get("semantic_revision", "")
                    ),
                    cache=source_time_cache,
                )
            )
            if observed is None:
                skipped += 1
                continue
            observed_at = observed.isoformat()
            if observed_at == str(clue.get("user_world_at", "")):
                skipped += 1
                continue
            correction_id = (
                "activity-observation-time:"
                + sha256(
                    f"{clue_id}\0{observed_at}".encode("utf-8")
                ).hexdigest()[:24]
            )
            self.activity.correct_observation_time(
                MaterialClue(
                    clue_id=correction_id,
                    matter_id=matter_id,
                    clue_kind=(
                        str(clue.get("clue_kind", "semantic_event"))
                        + "_observation_time_correction"
                    ),
                    user_world_at=observed_at,
                    disposition="material",
                    rationale=(
                        "Activity recency uses the evidence observation time, "
                        "not the scheduled or due time."
                    ),
                    localized_summary=dict(
                        clue.get("localized_summary", {})
                    ),
                    semantic_revision=str(
                        clue.get("semantic_revision", "")
                    ),
                    evidence_ids=tuple(clue.get("evidence_ids", ())),
                ),
                superseded_clue_id=clue_id,
                projection_matter_ids=bound_matter_ids.get(clue_id, ()),
            )
            repaired += 1
        return {
            "checked_clue_count": len(clue_ids),
            "repaired_clue_count": repaired,
            "skipped_clue_count": skipped,
            "status": "current",
        }

    def reconcile_current_matter_activity(self) -> dict[str, Any]:
        """Fill missing activity and correct observation-time regressions."""

        if self.store is None or self.activity is None:
            raise RuntimeError("MATTERS_HOME is required for activity reconciliation")
        migrated = self._migrate_current_matter_activity()
        repair = self.repair_current_activity_observation_times()
        eligible_matter_ids = {
            str(item.get("matter", {}).get("matter_id", ""))
            for item in self.store.iter_current("admission_decision")
            if str(item.get("status", "")) == "admitted"
            and isinstance(item.get("matter"), Mapping)
            and str(item.get("matter", {}).get("matter_id", ""))
        }
        current_activity_ids = {
            str(item.get("matter_id", ""))
            for item in self.store.iter_current("matter_activity")
            if str(item.get("matter_id", "")) in eligible_matter_ids
        }
        missing = tuple(sorted(eligible_matter_ids - current_activity_ids))
        return {
            "eligible_matter_count": len(eligible_matter_ids),
            "current_activity_count": len(current_activity_ids),
            "missing_activity_count": len(missing),
            "migrated_activity_count": migrated,
            "checked_clue_count": int(repair["checked_clue_count"]),
            "repaired_clue_count": int(repair["repaired_clue_count"]),
            "skipped_clue_count": int(repair["skipped_clue_count"]),
            "status": "current" if not missing else "current_with_gaps",
        }

    def _prepare_current_generated_heroes(self) -> int:
        """Create one private pending generation brief for each visible Matter."""

        if self.store is None:
            return 0
        matter_ids = tuple(
            str(item.get("matter", {}).get("matter_id", ""))
            for item in self.store.iter_current("admission_decision")
            if str(item.get("status", "")) == "admitted"
            and isinstance(item.get("matter"), Mapping)
            and str(item.get("matter", {}).get("matter_id", ""))
        )
        return int(
            self.prepare_generated_heroes(matter_ids=matter_ids)[
                "prepared_count"
            ]
        )

    def reconcile_admitted_matter_presentation(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Advance one exact-admission page toward projection and hero readiness."""

        if (
            self.store is None
            or self.dispatcher is None
            or self.heroes is None
            or self.hierarchy is None
        ):
            raise RuntimeError(
                "MATTERS_HOME is required for presentation reconciliation"
            )
        rows, has_more = self.store.canonical_matter_presentation_page(
            after_matter_id=after_matter_id,
            limit=limit,
        )
        projection_current_count = 0
        projection_repair_queued_count = 0
        projection_repair_blocked_count = 0
        hero_current_count = 0
        hero_pending_count = 0
        hero_blocked_count = 0
        hero_prepared_count = 0
        items: list[dict[str, Any]] = []
        for row in rows:
            matter_id = str(row["matter_id"])
            projection = row.get("projection")
            repair_package_id = ""
            repair_status = "not_required"
            blocker = ""
            if (
                not isinstance(projection, Mapping)
                or str(projection.get("equivalence_status", ""))
                != "equivalent"
            ):
                try:
                    package, queued = self._queue_matter_projection_repair(row)
                    repair_package_id = package.package_id
                    repair_status = queued.status
                    if queued.status == "passed":
                        self.dispatcher.dispatch(package, queued)
                    else:
                        projection_repair_queued_count += 1
                except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                    projection_repair_blocked_count += 1
                    repair_status = "blocked"
                    blocker = str(exc)
                projection = self.store.current("projection", matter_id)

            projection_current = bool(
                isinstance(projection, Mapping)
                and str(projection.get("equivalence_status", ""))
                == "equivalent"
            )
            if projection_current:
                projection_current_count += 1
                parent = self.hierarchy.parent_edge(
                    matter_id,
                    current_only=True,
                )
                if parent is not None:
                    hero_status = "not_applicable"
                    not_applicable_fingerprint = _fingerprint(
                        {
                            "matter_id": matter_id,
                            "eligibility": "not_applicable",
                            "parent_matter_id": parent.parent_matter_id,
                        }
                    )
                    for coverage_row in self._coverage_rows_for_matter(
                        matter_id
                    ):
                        if self.coverage_ledger is not None:
                            self.coverage_ledger.mark_stage(
                                object_id=str(coverage_row["object_id"]),
                                stage_id="generated_hero",
                                status="not_applicable",
                                input_fingerprint=(
                                    not_applicable_fingerprint
                                ),
                                output_ref="",
                                matter_ids=(matter_id,),
                                refresh_summary=False,
                            )
                else:
                    hero = self.store.current(
                        "generated_hero_record",
                        matter_id,
                    )
                    if hero is None:
                        prepared = self.prepare_generated_heroes(
                            matter_ids=(matter_id,)
                        )
                        if prepared["prepared_count"]:
                            hero_prepared_count += 1
                        hero = self.store.current(
                            "generated_hero_record",
                            matter_id,
                        )
                    hero_status = str((hero or {}).get("status", ""))
                if hero_status == "generated_current":
                    hero_current_count += 1
                elif hero_status == "generation_pending_placeholder":
                    hero_pending_count += 1
                elif hero_status == "generation_blocked_placeholder":
                    hero_blocked_count += 1
                elif hero_status == "not_applicable":
                    pass
                elif not blocker:
                    blocker = "generated hero owner did not publish a disposition"
            else:
                hero_status = str(
                    (row.get("generated_hero") or {}).get("status", "")
                )
                if not blocker and repair_status == "passed":
                    blocker = "projection repair result did not reach C12"

            items.append(
                {
                    "matter_id": matter_id,
                    "admission_revision": int(row["admission_revision"]),
                    "projection_status": (
                        "current" if projection_current else "pending"
                    ),
                    "projection_repair_package_id": repair_package_id,
                    "projection_repair_status": repair_status,
                    "generated_hero_status": hero_status or "not_prepared",
                    "blocker": blocker,
                }
            )

        next_cursor = (
            str(rows[-1]["matter_id"]) if rows and has_more else ""
        )
        return {
            "scanned_matter_count": len(rows),
            "projection_current_count": projection_current_count,
            "projection_repair_queued_count": (
                projection_repair_queued_count
            ),
            "projection_repair_blocked_count": (
                projection_repair_blocked_count
            ),
            "hero_current_count": hero_current_count,
            "hero_pending_count": hero_pending_count,
            "hero_blocked_count": hero_blocked_count,
            "hero_prepared_count": hero_prepared_count,
            "items": tuple(items),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": (
                "partial"
                if has_more
                else (
                    "current_with_gaps"
                    if projection_repair_blocked_count or hero_blocked_count
                    else (
                        "pending"
                        if (
                            projection_repair_queued_count
                            or hero_pending_count
                        )
                        else "current"
                    )
                )
            ),
        }

    def _queue_matter_projection_repair(
        self,
        row: Mapping[str, Any],
    ) -> tuple[AnalysisWorkPackage, AgentOperationResult]:
        """Queue a title/summary-only repair without replaying C6 admission."""

        assert self.store is not None
        admission = row.get("admission")
        matter = (
            admission.get("matter")
            if isinstance(admission, Mapping)
            else None
        )
        matter_id = str(row.get("matter_id", ""))
        if (
            not isinstance(admission, Mapping)
            or str(admission.get("status", "")) != "admitted"
            or not isinstance(matter, Mapping)
            or str(matter.get("matter_id", "")) != matter_id
            or matter.get("admitted") is False
        ):
            raise ValueError("exact current admitted Matter is unavailable")
        semantic_identity_id = str(
            matter.get("semantic_identity_id", "")
        ).strip()
        if not semantic_identity_id:
            raise ValueError("current Matter semantic identity is unavailable")

        evidence_ids = tuple(
            sorted(
                {
                    str(item)
                    for item in matter.get("evidence_ids", ())
                    if str(item)
                }
            )
        )
        anchor_rows = self.store.current_many(
            "evidence_anchor",
            evidence_ids,
        )
        anchors = tuple(
            anchor_rows[evidence_id]
            for evidence_id in evidence_ids
            if evidence_id in anchor_rows
            and bool(anchor_rows[evidence_id].get("current", True))
            and str(anchor_rows[evidence_id].get("text", "")).strip()
        )[:20]
        if not anchors:
            raise ValueError(
                "projection repair has no current admitted evidence"
            )
        allowed_evidence_ids = tuple(
            str(anchor["evidence_id"]) for anchor in anchors
        )
        source_revision_ids = tuple(
            dict.fromkeys(
                f"{anchor['source_id']}:v{int(anchor['source_version'])}"
                for anchor in anchors
                if str(anchor.get("source_id", ""))
                and int(anchor.get("source_version", 0) or 0) > 0
            )
        )
        if not source_revision_ids:
            raise ValueError(
                "projection repair has no current source revision"
            )
        package = AnalysisWorkPackage.create(
            operation_type="text_analysis",
            task_kind="matter_projection_repair",
            capability_role="matter_modeler",
            requested_output_types=(
                "matter_candidate",
                "bounded_summary",
            ),
            source_revision_ids=source_revision_ids,
            model_revision="matters-projection-repair:v2",
            allowed_evidence_ids=allowed_evidence_ids,
            private_evidence={
                "matter_projection_repair": {
                    "matter_id": matter_id,
                    "semantic_identity_key": semantic_identity_id,
                    "admission_revision": int(
                        row.get("admission_revision", 0)
                    ),
                    "canonical_write_allowed": False,
                },
                "evidence": tuple(
                    {
                        "evidence_id": str(anchor["evidence_id"]),
                        "text": str(anchor.get("text", ""))[:800],
                        "modality": str(
                            anchor.get("modality", "inferred")
                        ),
                        "location": {
                            key: value
                            for key, value in dict(
                                anchor.get("location", {})
                            ).items()
                            if key
                            in {
                                "field",
                                "page",
                                "line",
                                "line_start",
                                "line_end",
                                "region",
                            }
                        },
                    }
                    for anchor in anchors
                ),
                "required_output": {
                    "finding_types": (
                        "matter_candidate",
                        "bounded_summary",
                    ),
                    "required_locales": ("en", "zh-CN"),
                    "existing_matter_id": matter_id,
                    "semantic_identity_key": semantic_identity_id,
                    "repair_projection_only": True,
                    "matter_candidate_purpose": (
                        "short standalone bilingual title"
                    ),
                    "bounded_summary_purpose": (
                        "one-line bilingual current-state summary"
                    ),
                    "do_not_admit_or_merge": True,
                    "human_confirmation_required": False,
                },
            },
            matter_id=matter_id,
            matter_revision=f"admission:{int(row['admission_revision'])}",
            prompt_contract_id="matters.semantic-understanding",
            prompt_contract_revision="v4",
            output_schema_id="matters.agent-operation-result.v4",
            required_skill_id="matters-semantic-understanding",
            locale_registry_revision=self.locale_registry_owner.revision,
            required_locales=self.locale_registry_owner.available_locales,
            disclosure_policy="private_local_authorized",
            resource_budget={
                "max_inputs": 20,
                "max_chars": 16000,
            },
        )
        return package, self.operations.queue(package)

    def prepare_generated_heroes(
        self,
        *,
        matter_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Prepare one bounded, explicit set of independently openable Matters."""

        if (
            self.store is None
            or self.heroes is None
            or self.hierarchy is None
        ):
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        normalized_ids = tuple(
            dict.fromkeys(
                str(item).strip() for item in matter_ids if str(item).strip()
            )
        )
        if not normalized_ids or len(normalized_ids) > 100:
            raise ValueError(
                "generated hero preparation requires between 1 and 100 Matters"
            )
        prepared_ids: list[str] = []
        skipped_ids: list[str] = []
        for matter_id in normalized_ids:
            projection = self.store.current("projection", matter_id) or {}
            if (
                str(projection.get("equivalence_status", ""))
                != "equivalent"
            ):
                skipped_ids.append(matter_id)
                continue
            admission = self.store.current(
                "admission_decision",
                matter_id,
            ) or {}
            matter_payload = admission.get("matter", {})
            if (
                str(admission.get("status", "")) != "admitted"
                or not isinstance(matter_payload, Mapping)
            ):
                skipped_ids.append(matter_id)
                continue
            semantic_identity_id = str(
                matter_payload.get("semantic_identity_id", "")
            )
            if not semantic_identity_id:
                skipped_ids.append(matter_id)
                continue
            classification = self.store.current(
                "matter_classification",
                matter_id,
            ) or {}
            topic_values = " ".join(
                str(item.get("value", ""))
                for item in classification.get("topic_types", ())
                if isinstance(item, Mapping)
            ).casefold()
            if any(
                token in topic_values
                for token in ("travel", "trip", "flight", "hotel")
            ):
                topic = "travel planning"
            elif any(
                token in topic_values
                for token in ("career", "job", "application", "interview")
            ):
                topic = "career transition"
            elif any(
                token in topic_values
                for token in ("software", "code", "development", "project")
            ):
                topic = "software project"
            elif any(
                token in topic_values
                for token in ("refund", "subscription", "purchase", "account")
            ):
                topic = "personal administration"
            elif any(
                token in topic_values
                for token in ("event", "challenge", "competition")
            ):
                topic = "creative challenge"
            else:
                topic = "personal project"
            title = str(
                dict(projection.get("localized_values", {})).get("en", "")
            ).casefold()
            if "physicsguard" in title or "evidence catalog" in title:
                topic = "physical system validation"
                themes = (
                    "vibration rig with calibrated sensors",
                    "laboratory measurement instruments",
                )
            elif "heating" in title or "energy" in title:
                topic = "home heating assessment"
                themes = (
                    "residential boiler and radiator inspection",
                    "home heating equipment room",
                )
            elif "job search" in title:
                topic = "career transition"
                themes = (
                    "job interview across meeting table",
                    "application portfolio and recruiting notes",
                )
            elif "khaos brain" in title or "memory system" in title:
                topic = "personal memory system"
                themes = (
                    "home archive with albums and notebooks",
                    "connected digital memory map",
                )
            elif "access" in title or "security" in title:
                topic = "digital access security"
                themes = (
                    "hardware security keys on desk",
                    "trusted phone and laptop verification",
                )
            elif "skillguard" in title:
                topic = "software skill governance"
                themes = (
                    "contract matrix and dependency graph",
                    "release checklist with security keys",
                )
            elif "flowpilot" in title or "control-plane" in title:
                topic = "software control plane repair"
                themes = (
                    "operations room with recovery diagram",
                    "diagnostic hardware and failure indicators",
                )
            elif "flowguard" in title or "governance" in title:
                topic = "workflow assurance software"
                themes = (
                    "workflow lab with state transition map",
                    "test gates binders and hardware rack",
                )
            elif "build week" in title or "submission" in title:
                topic = "hackathon submission"
                themes = (
                    "hackathon hall with multiple teams",
                    "electronics prototype judging demonstration",
                )
            elif "subscription" in title or "refund" in title:
                topic = "digital subscription administration"
                themes = (
                    "cancellation screen and billing statements",
                    "payment card with refund checklist",
                )
            elif "travel" in title or "journey" in title:
                topic = "travel planning"
                themes = (
                    "traveler with luggage at station",
                    "waiting train at Japanese transport hub",
                )
            elif "authorization" in title or "payment" in title:
                themes = ("payment card and verification terminal",)
            elif "visit" in title:
                themes = ("theme park entrance and admission gate",)
            elif "flight" in title:
                themes = ("airport gate with luggage and aircraft",)
            elif "contract" in title:
                themes = ("contract pages with validation checklist",)
            elif "repair" in title:
                themes = ("diagnostic console with recovery indicators",)
            elif "memory" in title:
                themes = ("photo albums notebooks and archive shelves",)
            elif "catalog" in title:
                themes = ("labeled evidence cases and catalog drawers",)
            elif "authentication" in title:
                themes = ("hardware key with device verification",)
            elif "replay" in title:
                themes = ("test bench with replay controls",)
            elif "adoption" in title:
                themes = ("connected equipment during system integration",)
            else:
                themes = ("progress",)
            parent = self.hierarchy.parent_edge(
                matter_id,
                current_only=True,
            )
            if parent is not None:
                not_applicable_fingerprint = _fingerprint(
                    {
                        "matter_id": matter_id,
                        "eligibility": "not_applicable",
                        "parent_matter_id": parent.parent_matter_id,
                    }
                )
                for row in self._coverage_rows_for_matter(matter_id):
                    if self.coverage_ledger is not None:
                        self.coverage_ledger.mark_stage(
                            object_id=str(row["object_id"]),
                            stage_id="generated_hero",
                            status="not_applicable",
                            input_fingerprint=not_applicable_fingerprint,
                            output_ref="",
                            matter_ids=(matter_id,),
                            refresh_summary=False,
                        )
                skipped_ids.append(matter_id)
                continue
            hierarchy_projection = self.store.current(
                "matter_hierarchy_projection",
                matter_id,
            ) or {}
            record = self.heroes.prepare(
                HeroSubject(
                    object_id=matter_id,
                    object_kind="matter",
                    semantic_identity_id=semantic_identity_id,
                    topic_concepts=(topic,),
                    theme_concepts=themes,
                    hierarchy_revision=str(
                        hierarchy_projection.get(
                            "input_fingerprint",
                            projection.get("semantic_revision", ""),
                        )
                    ),
                    is_root=parent is None,
                    independently_openable=True,
                )
            )
            for row in self._coverage_rows_for_matter(matter_id):
                if self.coverage_ledger is not None:
                    self.coverage_ledger.mark_stage(
                        object_id=str(row["object_id"]),
                        stage_id="generated_hero",
                        status=(
                            "current"
                            if record.status == "generated_current"
                            else "pending"
                        ),
                        input_fingerprint=record.brief_fingerprint,
                        output_ref=f"generated_hero_record:{matter_id}",
                        matter_ids=(matter_id,),
                        refresh_summary=False,
                    )
            prepared_ids.append(matter_id)
        if prepared_ids and self.coverage_ledger is not None:
            self.coverage_ledger.refresh_summary()
        return {
            "requested_count": len(normalized_ids),
            "prepared_count": len(prepared_ids),
            "skipped_count": len(skipped_ids),
            "prepared_matter_ids": tuple(prepared_ids),
            "skipped_matter_ids": tuple(skipped_ids),
            "status": "current",
        }

    def _distinct_title_summary_migration_input_fingerprint(self) -> str:
        assert self.store is not None
        projections = tuple(
            sorted(
                (
                    str(item.get("matter_id", "")),
                    str(item.get("semantic_revision", "")),
                    str(item.get("equivalence_status", "")),
                    dict(item.get("localized_values", {})),
                    dict(item.get("localized_rationale", {})),
                )
                for item in self.store.iter_current("projection")
            )
        )
        results = tuple(
            sorted(
                (
                    str(item.get("package_id", "")),
                    str(item.get("terminal_receipt", "")),
                )
                for item in self.store.iter_current(
                    "agent_operation_result"
                )
                if any(
                    isinstance(finding, Mapping)
                    and str(finding.get("finding_type", ""))
                    == "bounded_summary"
                    for finding in item.get("findings", ())
                )
            )
        )
        owner_findings = tuple(
            sorted(
                (
                    str(item.get("finding_id", "")),
                    str(item.get("package_id", "")),
                    str(item.get("package_input_fingerprint", "")),
                    str(item.get("owner_model_id", "")),
                    str(item.get("status", "")),
                    str(item.get("owner_output_ref", "")),
                    dict(item.get("finding", {})),
                )
                for item in self.store.iter_current(
                    "autonomous_finding"
                )
                if str(item.get("owner_model_id", ""))
                in {
                    "C6_matter_admission",
                    "C12_projection_bilingual_ui",
                }
            )
        )
        package_ids = tuple(
            dict.fromkeys(item[1] for item in owner_findings if item[1])
        )
        current_packages = self.store.current_many(
            "analysis_work_package",
            package_ids,
        )
        packages = tuple(
            sorted(
                (
                    package_id,
                    str(
                        current_packages.get(package_id, {}).get(
                            "input_fingerprint",
                            "",
                        )
                    ),
                )
                for package_id in package_ids
            )
        )
        return "sha256:" + sha256(
            json.dumps(
                {
                    "projections": projections,
                    "results": results,
                    "owner_findings": owner_findings,
                    "packages": packages,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def _migrate_root_hierarchy_audits(self) -> int:
        """Register legacy admitted Matters as roots without inferring edges."""

        if self.store is None or self.hierarchy is None:
            return 0
        expected_stages = {
            "hierarchy_decision",
            "containment_current",
            "child_state_current",
            "ancestor_rollup_current",
            "hierarchy_projection_current",
            "ui_reachable",
        }
        migrated = 0
        for admission in self.store.list_current("admission_decision"):
            matter = admission.get("matter")
            if (
                admission.get("status") != "admitted"
                or not isinstance(matter, Mapping)
            ):
                continue
            matter_id = str(matter.get("matter_id", ""))
            if not matter_id:
                continue
            with self.store.immediate_transaction():
                current = self.store.current(
                    "matter_hierarchy_audit",
                    matter_id,
                )
                if current is not None and set(
                    dict(current.get("stages", {}))
                ) == expected_stages:
                    continue
                self.hierarchy.register_matter(
                    matter_id,
                    change_ref="migration:legacy-matter-as-root:v1",
                )
                migrated += 1
        return migrated

    def capabilities(self) -> CapabilityReport:
        status = self.config.private_status()
        discovery = self._discover_machine_skill_inventory()
        skill_view = self.resolve_skill_view(discovery.inventory)
        return CapabilityReport(
            package_status="active",
            private_runtime_status=status.status,
            private_runtime_reason=status.reason,
            persistence="sqlite_external_root" if self.store else "synthetic_only",
            researchguard=(
                "researchguard_current"
                if self.research_status.current
                else self.research_status.status
            ),
            bundled_skill_pack=build_bundle().bundle_hash,
            bundled_skill_count=len(build_bundle().skills),
            active_skill_view=skill_view.status,
            machine_skill_inventory=discovery.status,
            machine_skill_candidate_count=len(discovery.inventory.entries),
            machine_skill_finding_count=len(discovery.findings),
            maintenance_orchestration=(
                "available"
                if self.maintenance_orchestration is not None
                else "unavailable"
            ),
        )

    def _discover_machine_skill_inventory(self):
        managed_root = (
            self.config.private_root / "managed-skills"
            if self.config.private_root is not None
            else None
        )
        return discover_machine_skills(
            build_bundle(),
            external_roots=(default_codex_skill_root(),),
            managed_root=managed_root,
        )

    def resolve_skill_view(
        self,
        machine_inventory: MachineSkillInventory | None = None,
        research_gate: ResearchGuardGate | None = None,
    ) -> ActiveSkillView:
        bundle = build_bundle()
        inventory = (
            machine_inventory
            if machine_inventory is not None
            else self._discover_machine_skill_inventory().inventory
        )
        if research_gate is None:
            if self.research_status.current:
                gate = ResearchGuardGate(
                    ResearchGuardStatus.CURRENT,
                    identity=(
                        "researchguard:"
                        f"{self.research_status.provider_version}:"
                        f"{self.research_status.source_commit[:12]}"
                    ),
                    currentness_receipt_identity=(
                        self.research_status.portable_receipt_id
                    ),
                    requested_provider_ids=("researchguard",),
                )
            elif self.research_status.status == "researchguard_blocked":
                gate = ResearchGuardGate(
                    ResearchGuardStatus.BLOCKED,
                    requested_provider_ids=("researchguard",),
                )
            else:
                gate = ResearchGuardGate(
                    ResearchGuardStatus.PENDING,
                    requested_provider_ids=("researchguard",),
                )
        else:
            gate = research_gate
        validation_manifests = (
            tuple(bundle.skills)
            + tuple(item.manifest for item in inventory.entries)
        )
        validations = tuple(
            CandidateValidation(
                candidate_manifest_fingerprint=manifest.manifest_fingerprint,
                validator_identity=manifest.validator_identity,
                status=ValidationStatus.CURRENT,
            )
            for manifest in validation_manifests
        )
        environment = ResolutionEnvironment(
            matters_version=VERSION,
            skill_schema_version="1.0",
            available_runtime_identities=tuple(
                sorted({manifest.runtime_identity for manifest in bundle.skills})
            ),
            dependency_identities=(),
            validations=validations,
            researchguard=gate,
        )
        return ActiveSkillResolver().resolve(
            bundle=bundle,
            inventory=inventory,
            environment=environment,
        )

    @staticmethod
    def _validate_managed_skill_projection(
        path: Path,
        _projection,
    ) -> VerificationResult:
        try:
            skill_text = (path / "SKILL.md").read_text(encoding="utf-8")
            if "MatterService" not in skill_text:
                raise ValueError("shared service boundary missing")
            if any(
                ".skillguard" in item.parts
                for item in path.rglob("*")
            ):
                raise ValueError("author control residual")
        except (OSError, UnicodeError, ValueError) as exc:
            return VerificationResult(
                False,
                "matters:managed-skill-validation:failed",
                str(exc),
            )
        identity = sha256(
            skill_text.encode("utf-8")
        ).hexdigest()
        return VerificationResult(
            True,
            f"matters:managed-skill-validation:{identity}",
        )

    def synchronize_managed_skill_projections(
        self,
        *,
        transaction_id_prefix: str,
    ) -> dict[str, Any]:
        """Update only already marked Matters-managed local projections."""

        if self.config.private_root is None:
            raise RuntimeError("MATTERS_HOME is required for managed skill sync")
        if (
            not transaction_id_prefix
            or any(
                item not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                for item in transaction_id_prefix
            )
        ):
            raise ValueError("transaction id prefix is invalid")
        bundle = build_bundle()
        projections = {
            item.manifest.skill_id: item for item in load_projections()
        }
        discovery = self._discover_machine_skill_inventory()
        view = self.resolve_skill_view(discovery.inventory)
        managed_root = self.config.private_root / "managed-skills"
        synchronizer = ManagedProjectionSynchronizer(
            FilesystemManagedProjectionStore(managed_root)
        )
        installed_by_id = {
            item.manifest.skill_id: item
            for item in discovery.inventory.entries
            if item.matters_managed
        }
        receipts = []
        for decision in view.decisions:
            if not decision.sync_required:
                continue
            installed = installed_by_id.get(decision.skill_id)
            projection = projections.get(decision.skill_id)
            if installed is None or projection is None:
                raise RuntimeError("managed sync inputs are incomplete")
            receipts.append(
                synchronizer.synchronize(
                    transaction_id=(
                        f"{transaction_id_prefix}-{decision.skill_id}"
                    ),
                    decision=decision,
                    installed=installed,
                    projection=projection,
                    staged_validator=self._validate_managed_skill_projection,
                    installed_currentness_validator=(
                        self._validate_managed_skill_projection
                    ),
                )
            )
        current_discovery = self._discover_machine_skill_inventory()
        current_view = self.resolve_skill_view(current_discovery.inventory)
        return {
            "status": current_view.status,
            "receipt_count": len(receipts),
            "receipts": tuple(asdict(item) for item in receipts),
            "machine_inventory_revision": current_discovery.inventory.revision,
            "default_global_install": False,
        }

    def _register_recompute_handlers(self) -> None:
        assert self.work_queue is not None
        assert self.store is not None
        owner_ids = (
            "C3_evidence_qualification",
            "C4_person_entity_resolution",
            "C5_event_temporal_trace",
            "C6_matter_admission",
            "C7_lifecycle_board_state",
            "C8_open_loop_waiting_blocking",
            "C9_completion_cancellation_reopen",
            "C12_projection_bilingual_ui",
        )
        for owner_id in owner_ids:
            self.work_queue.register_handler(
                owner_id,
                self._owner_recompute_handler(owner_id),
            )

    def _owner_recompute_handler(self, owner_id: str):
        def handle(payload: Mapping[str, Any]) -> None:
            assert self.store is not None
            revision_id = str(payload["revision_id"])
            correction = self.store.current("correction_input", revision_id)
            if correction is None:
                raise RuntimeError("correction input is unavailable")
            matter_id = str(correction["matter_id"])
            status = "no_finding"
            output_ref = ""
            if owner_id == "C12_projection_bilingual_ui":
                prior = self.store.current("projection", matter_id)
                if prior is None:
                    raise RuntimeError("projection is unavailable")
                field_name = str(correction.get("field_name", "")).strip()
                corrected_value = str(
                    correction.get("corrected_value", "")
                ).strip()
                state = str(prior["state"])
                if field_name == "state" and corrected_value:
                    allowed_states = {
                        "planned",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "reopened",
                        "uncertain",
                        "source_only",
                        "not_started",
                    }
                    if corrected_value not in allowed_states:
                        raise ValueError("corrected state is unsupported")
                    state = corrected_value
                localized_values = dict(prior["localized_values"])
                if field_name in {"title", "summary"} and corrected_value:
                    localized_values = user_text_localized(
                        corrected_value,
                        semantic_revision=revision_id,
                    )
                projection = self.projections.publish(
                    matter_id=matter_id,
                    semantic_revision=revision_id,
                    state=state,
                    rationale=str(correction["rationale"]),
                    evidence_ids=tuple(prior.get("evidence_ids", ())),
                    localized_values=localized_values,
                    localized_rationale=user_text_localized(
                        str(correction["rationale"]),
                        semantic_revision=revision_id,
                    ),
                )
                self.store.append(
                    "projection",
                    matter_id,
                    self.store.next_revision("projection", matter_id),
                    asdict(projection),
                )
                status = "auto_applied"
                output_ref = f"projection:{matter_id}"
                for row in self._coverage_rows_for_matter(matter_id):
                    if self.coverage_ledger is None:
                        continue
                    object_id = str(row["object_id"])
                    for stage_id in (
                        "localization",
                        "meaningful_clue_summary",
                        "generated_hero",
                        "supplemental_information",
                        "ui_projection",
                    ):
                        self.coverage_ledger.mark_stage(
                            object_id=object_id,
                            stage_id=stage_id,
                            status=(
                                "current"
                                if stage_id == "localization"
                                else "pending"
                            ),
                            input_fingerprint=revision_id,
                            output_ref=output_ref,
                            matter_ids=(matter_id,),
                        )
            elif owner_id == "C6_matter_admission":
                for row in self._coverage_rows_for_matter(matter_id):
                    if self.coverage_ledger is not None:
                        self.coverage_ledger.mark_stage(
                            object_id=str(row["object_id"]),
                            stage_id="matter",
                            status="current",
                            input_fingerprint=revision_id,
                            output_ref=f"admission:retained:{matter_id}",
                            matter_ids=(matter_id,),
                        )
                output_ref = f"admission:retained:{matter_id}"
            self.store.append(
                "owner_recompute",
                f"{revision_id}:{owner_id}",
                self.store.next_revision(
                    "owner_recompute", f"{revision_id}:{owner_id}"
                ),
                {
                    "revision_id": revision_id,
                    "owner_id": owner_id,
                    "dependent_ids": tuple(payload.get("dependent_ids", ())),
                    "status": status,
                    "output_ref": output_ref,
                },
            )

        return handle

    @staticmethod
    def _completion_evidence(
        payload: Mapping[str, Any],
        anchors: tuple[EvidenceAnchor, ...],
    ) -> tuple[CompletionCriterion, ...]:
        by_field: dict[str, list[str]] = {}
        for anchor in anchors:
            field_name = str(anchor.location.get("field", ""))
            by_field.setdefault(field_name, []).append(anchor.evidence_id)
        confirmation = tuple(
            anchor.evidence_id
            for anchor in anchors
            if "completion criteria" in anchor.text.lower()
            or "completed" in anchor.text.lower()
        )
        return (
            CompletionCriterion(
                "provider_resolution",
                bool(payload.get("resolution")),
                tuple(by_field.get("resolution", ())),
                owner_evidence_licensed=bool(
                    by_field.get("resolution", ())
                ),
            ),
            CompletionCriterion(
                "result_attachment",
                bool(payload.get("attachments")),
                tuple(by_field.get("attachments", ())),
                owner_evidence_licensed=bool(
                    by_field.get("attachments", ())
                ),
            ),
            CompletionCriterion(
                "explicit_confirmation",
                bool(confirmation),
                confirmation,
                owner_evidence_licensed=bool(confirmation),
            ),
        )

    @staticmethod
    def _relations(payload: Mapping[str, Any]) -> tuple[MatterRelationCandidate, ...]:
        return tuple(
            MatterRelationCandidate(
                source_matter_id=str(item.get("from", "")),
                relation_type=str(item.get("type", "relates")),
                target_matter_id=str(item.get("to", "")),
            )
            for item in payload.get("links", ())
        )

    def process_envelope(
        self,
        *,
        scope: AuthorizationScope,
        envelope: ProviderEnvelope,
        idempotency_key: str,
        refresh_coverage_summary: bool = True,
    ) -> SourceProcessingResult:
        if (
            self.store is None
            and bool(envelope.metadata.get("requires_private_runtime", False))
        ):
            return SourceProcessingResult(
                "blocked",
                "MATTERS_HOME is required for private provider activation",
            )
        try:
            coverage = self.authorization.authorize_envelope(scope, envelope)
        except AuthorizationError as exc:
            return SourceProcessingResult("blocked", str(exc))

        registration = self.sources.register(
            envelope,
            idempotency_key=idempotency_key,
        )
        if registration.status == "no_delta":
            return SourceProcessingResult(
                "no_delta",
                registration.reason,
                coverage=coverage,
                registration=registration,
                child_receipts={"C1": "current", "C2": "no_delta"},
            )
        source = registration.source_version
        if source is None:
            return SourceProcessingResult(
                "blocked",
                "source registration produced no version",
            )

        anchors: list[EvidenceAnchor] = []
        gaps: list[EvidenceGap] = []
        for assertion in source_assertions(envelope.payload):
            result = self.evidence.qualify(
                source,
                text=str(assertion["text"]),
                location=assertion.get("anchor"),
                modality=str(assertion.get("modality", "reported")),
            )
            if isinstance(result, EvidenceAnchor):
                anchors.append(result)
            else:
                gaps.append(result)

        trace = self.events.from_provider_payload(
            envelope.external_id,
            dict(envelope.payload),
        )
        persons: list[PersonCandidate] = []
        if envelope.payload.get("assignee"):
            persons.append(
                self.people.candidate(
                    str(envelope.payload["assignee"]),
                    f"{envelope.external_id}:assignee",
                )
            )

        summary = str(envelope.payload.get("summary", "")).strip()
        possibility_only = summary.lower().startswith(("maybe ", "perhaps "))
        semantic_hierarchy_review = bool(envelope.payload.get("children"))
        access_blocked = coverage.status != "complete"
        evidence_ids = tuple(item.evidence_id for item in anchors)
        provider_status = str(envelope.payload.get("status", ""))
        semantic_identity_key = str(
            envelope.payload.get("semantic_identity_key") or summary
        )
        if evidence_ids:
            context_signals = []
            if semantic_identity_key:
                context_signals.append(
                    ContextSignal(
                        kind=(
                            "goal"
                            if bool(
                                envelope.payload.get(
                                    "explicit_goal_or_obligation",
                                    False,
                                )
                            )
                            else "subject"
                        ),
                        value=semantic_identity_key,
                        evidence_ids=evidence_ids,
                    )
                )
            reconciliation_execution = self.reconciliation.resolve(
                MatterReconciliationRequest(
                    source_ids=(source.source_id,),
                    evidence_ids=evidence_ids,
                    semantic_identity_key=semantic_identity_key,
                    context=ProjectContext(signals=tuple(context_signals)),
                    granularity=GranularityAssessment(
                        independently_useful_goal=bool(
                            envelope.payload.get(
                                "explicit_goal_or_obligation",
                                False,
                            )
                        ),
                        independently_useful_state=bool(
                            provider_status
                            or envelope.payload.get("change_items")
                            or envelope.payload.get("worklog")
                        ),
                        independently_useful_outcome=bool(
                            envelope.payload.get("resolution")
                            or envelope.payload.get("attachments")
                        ),
                        independently_useful_next_step=bool(
                            envelope.payload.get("due_date")
                            or envelope.payload.get("assignee")
                            or envelope.payload.get("sprint")
                        ),
                        bounded_task=bool(
                            provider_status
                            or envelope.payload.get("due_date")
                            or envelope.payload.get("assignee")
                        ),
                        one_time_occurrence=bool(
                            envelope.payload.get(
                                "one_time_occurrence",
                                False,
                            )
                        ),
                    ),
                    access_blocked=access_blocked,
                    conflict=(
                        bool(trace.conflicts)
                        or semantic_hierarchy_review
                    ),
                ),
                useful_content=bool(
                    summary or envelope.payload.get("links")
                ),
                possibility_only=possibility_only,
            )
        else:
            reconciliation_execution = (
                self.reconciliation.retain_unqualified_source(
                    source_ids=(source.source_id,),
                    semantic_identity_key=semantic_identity_key,
                    useful_content=bool(
                        summary or envelope.payload.get("links")
                    ),
                    possibility_only=possibility_only,
                    conflict=(
                        bool(trace.conflicts)
                        or semantic_hierarchy_review
                    ),
                    access_blocked=access_blocked,
                )
            )
        admission = reconciliation_execution.admission
        if admission is None:
            raise RuntimeError(
                "C6 reconciliation did not produce an admission decision"
            )

        scheduled = bool(
            envelope.payload.get("due_date")
            or envelope.payload.get("sprint")
            or envelope.payload.get("assignee")
        )
        completion_criteria = self._completion_evidence(envelope.payload, tuple(anchors))
        completion_licensed = all(
            item.satisfied and item.evidence_ids for item in completion_criteria
        )
        lifecycle = self.lifecycle.decide(
            StateProofPacket(
                coverage=coverage.status,
                explicit_start=has_actual_start(trace),
                work_recorded=any(
                    event.kind == "work_recorded" for event in trace.events
                ),
                scheduled=scheduled,
                provider_status=provider_status,
                completion_licensed=completion_licensed,
                evidence_ids=evidence_ids,
            )
        )

        matter_ref = (
            admission.matter.matter_id
            if admission.matter
            else admission.candidate.candidate_id
            if admission.candidate
            else source.source_id
        )
        loops: list[OpenLoop] = []
        blocking: BlockingDecision | None = None
        for index, comment in enumerate(envelope.payload.get("comments", ())):
            body = str(comment.get("body", ""))
            if "blocked by" in body.lower():
                target = body.lower().split("blocked by", 1)[1].strip(" .")
                loop = self.open_loops.create(
                    loop_id=f"loop:{envelope.external_id}:{index}",
                    matter_id=matter_ref,
                    wait_target=target,
                    closure_condition=f"confirmation from {target}",
                    critical=True,
                    evidence_ids=evidence_ids,
                )
                if loop:
                    loops.append(loop)
                    blocking = self.open_loops.blocking(loop)

        outcome: OutcomeDecision | None = None
        if (
            provider_status.lower() == "done"
            or envelope.payload.get("resolution")
            or envelope.payload.get("attachments")
        ):
            outcome = self.outcomes.decide_completion(
                matter_ref,
                completion_criteria,
                provider_done=provider_status.lower() == "done",
                result_attachment_only=bool(envelope.payload.get("attachments")),
            )
        if trace.conflicts and provider_status.lower() == "reopened":
            outcome = self.outcomes.reopen(
                matter_ref,
                new_obligation_id="provider_reopen_with_blocker",
            )

        terminal = admission.status
        uncertainty_notes: list[str] = []
        if trace.conflicts:
            terminal = "uncertain"
            uncertainty_notes.extend(trace.conflicts)
        if semantic_hierarchy_review:
            terminal = "uncertain"
            uncertainty_notes.append("one Matter with actions versus split Matters")
        if access_blocked:
            terminal = "blocked"
            uncertainty_notes.append("partial or denied coverage")

        display_state = (
            outcome.status
            if outcome and outcome.status in {"completed", "reopened"}
            else lifecycle.state
            if terminal not in {"source_only", "uncertain", "blocked"}
            else terminal
        )
        projection = self.projections.publish(
            matter_id=matter_ref,
            semantic_revision=f"{source.source_id}:v{source.version}",
            state=display_state,
            rationale=(
                outcome.rationale
                if outcome and display_state == outcome.status
                else admission.rationale
            ),
            evidence_ids=evidence_ids,
        )
        relations = self._relations(envelope.payload)
        if relations and terminal == "uncertain":
            uncertainty_notes.append(
                "relationship candidates remain explicitly uncertain"
            )
        child_receipts = {
            f"C{index}": "current"
            for index in range(1, 13)
        }
        result = SourceProcessingResult(
            terminal_status=terminal,
            reason=admission.rationale,
            coverage=coverage,
            registration=registration,
            evidence=tuple(anchors),
            gaps=tuple(gaps),
            people=tuple(persons),
            trace=trace,
            admission=admission,
            lifecycle=lifecycle,
            open_loops=tuple(loops),
            blocking=blocking,
            outcome=outcome,
            relations=relations,
            projections=(projection,),
            uncertainty_notes=tuple(uncertainty_notes),
            child_receipts=child_receipts,
        )
        self._persist_source_processing(
            result,
            refresh_coverage_summary=refresh_coverage_summary,
        )
        return result

    def _persist_source_processing(
        self,
        result: SourceProcessingResult,
        *,
        refresh_coverage_summary: bool = True,
    ) -> None:
        if self.store is None or result.registration is None:
            return
        source = result.registration.source_version
        if source is None:
            return
        payload = asdict(result)
        # A SourceVersion can carry complete provider content only for the
        # duration of the active extraction call.  ``asdict`` would otherwise
        # bypass SourceRegistry._serialize and persist that transient payload
        # inside the processing receipt.
        registration_payload = payload.get("registration")
        if isinstance(registration_payload, dict):
            source_payload = registration_payload.get("source_version")
            if isinstance(source_payload, dict):
                source_payload.pop("transient_content", None)
        self.store.append(
            "source_processing_result",
            source.source_id,
            self.store.next_revision("source_processing_result", source.source_id),
            payload,
        )
        if result.admission is not None:
            object_id = (
                result.admission.matter.matter_id
                if result.admission.matter is not None
                else result.admission.candidate.candidate_id
                if result.admission.candidate is not None
                else source.source_id
            )
            self.store.append(
                "admission_decision",
                object_id,
                self.store.next_revision("admission_decision", object_id),
                asdict(result.admission),
            )
        for anchor in result.evidence:
            self.store.append(
                "evidence_anchor",
                anchor.evidence_id,
                self.store.next_revision("evidence_anchor", anchor.evidence_id),
                asdict(anchor),
            )
        for gap in result.gaps:
            gap_digest = sha256(
                f"{gap.reason}\0{gap.claim}".encode("utf-8")
            ).hexdigest()[:16]
            gap_id = f"{gap.source_id}:gap:{gap_digest}"
            self.store.append(
                "evidence_gap",
                gap_id,
                self.store.next_revision("evidence_gap", gap_id),
                asdict(gap),
            )
        for person in result.people:
            self.store.append(
                "person_candidate",
                person.person_id,
                self.store.next_revision("person_candidate", person.person_id),
                asdict(person),
            )
        if result.trace is not None:
            trace_id = f"{source.source_id}:trace"
            self.store.append(
                "temporal_trace",
                trace_id,
                self.store.next_revision("temporal_trace", trace_id),
                asdict(result.trace),
            )
        if result.lifecycle is not None:
            lifecycle_id = f"{source.source_id}:lifecycle"
            self.store.append(
                "lifecycle_decision",
                lifecycle_id,
                self.store.next_revision("lifecycle_decision", lifecycle_id),
                asdict(result.lifecycle),
            )
        for loop in result.open_loops:
            self.store.append(
                "open_loop",
                loop.loop_id,
                self.store.next_revision("open_loop", loop.loop_id),
                asdict(loop),
            )
        if result.outcome is not None:
            outcome_id = f"{source.source_id}:outcome"
            self.store.append(
                "outcome_decision",
                outcome_id,
                self.store.next_revision("outcome_decision", outcome_id),
                asdict(result.outcome),
            )
        for relation in result.relations:
            relation_id = (
                f"{relation.source_matter_id}:{relation.relation_type}:"
                f"{relation.target_matter_id}"
            )
            self.store.append(
                "relation_candidate",
                relation_id,
                self.store.next_revision("relation_candidate", relation_id),
                asdict(relation),
            )
        for projection in result.projections:
            self.store.append(
                "projection",
                projection.matter_id,
                self.store.next_revision("projection", projection.matter_id),
                asdict(projection),
            )
        if (
            self.hierarchy is not None
            and result.admission is not None
            and result.admission.matter is not None
        ):
            self.hierarchy.register_matter(
                result.admission.matter.matter_id,
                change_ref=(
                    f"admission:{result.admission.matter.matter_id}:"
                    f"{self.store.next_revision('admission_decision', result.admission.matter.matter_id) - 1}"
                ),
            )
        self._update_coverage_from_processing(
            result,
            refresh_coverage_summary=refresh_coverage_summary,
        )

    def _update_coverage_from_processing(
        self,
        result: SourceProcessingResult,
        *,
        refresh_coverage_summary: bool = True,
    ) -> None:
        """Join current child outputs into M0 without copying their facts."""

        if (
            self.coverage_ledger is None
            or result.registration is None
            or result.registration.source_version is None
        ):
            return
        source = result.registration.source_version
        object_id = source.external_reference.external_id
        if self.coverage_ledger.current(object_id) is None:
            return
        source_ref = f"{source.source_id}:v{source.version}"
        fingerprint = "sha256:" + sha256(
            json.dumps(
                {
                    "source_ref": source_ref,
                    "content_hash": source.content_hash,
                    "metadata_hash": source.metadata_hash,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.coverage_ledger.mark_stage(
            object_id=object_id,
            stage_id="source_version",
            status="current",
            input_fingerprint=fingerprint,
            output_ref=source_ref,
            refresh_summary=False,
        )
        self.coverage_ledger.mark_stage(
            object_id=object_id,
            stage_id="evidence",
            status="current" if result.evidence else "no_finding",
            input_fingerprint=fingerprint,
            output_ref=(
                bounded_stage_output_set_ref(
                    "evidence_anchor",
                    source_ref,
                    (anchor.evidence_id for anchor in result.evidence),
                )
                if result.evidence
                else "evidence:none"
            ),
            refresh_summary=False,
        )
        matter_ids: tuple[str, ...] = ()
        if result.admission is not None:
            if result.admission.matter is not None:
                matter_ids = (result.admission.matter.matter_id,)
            elif result.admission.candidate is not None:
                matter_ids = (result.admission.candidate.candidate_id,)
            matter_status = {
                "admitted": "current",
                "uncertain": "uncertain",
                "source_only": "not_applicable",
                "not_applicable": "not_applicable",
                "blocked": "blocked",
            }.get(result.admission.status, "uncertain")
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="matter",
                status=matter_status,
                input_fingerprint=fingerprint,
                output_ref=(
                    f"admission:{matter_ids[0]}"
                    if matter_ids
                    else f"admission:{result.admission.status}"
                ),
                matter_ids=matter_ids,
                refresh_summary=False,
            )
        if result.projections:
            projection = result.projections[0]
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="localization",
                status=(
                    "current"
                    if projection.equivalence_status == "equivalent"
                    else "blocked"
                ),
                input_fingerprint=fingerprint,
                output_ref=f"projection:{projection.matter_id}",
                matter_ids=matter_ids or None,
                refresh_summary=False,
            )
        if refresh_coverage_summary:
            self.coverage_ledger.refresh_summary()

    def reconcile_inventory(
        self,
        *,
        scope: CandidateScope,
        policy: TrackingPolicy,
        occurrences: tuple[InventoryOccurrence, ...],
        user_intents: Mapping[str, str] | None = None,
        refresh_coverage_summary: bool = True,
    ) -> tuple[InventorySnapshot, ChangeSet]:
        if self.inventory is None:
            raise RuntimeError("MATTERS_HOME is required for durable inventory")
        snapshot, changes = self.inventory.reconcile(
            scope=scope,
            policy=policy,
            occurrences=occurrences,
            user_intents=user_intents,
        )
        dispositions = {
            item.occurrence_id: item.status
            for item in snapshot.dispositions
        }
        group_occurrences = tuple(
            item
            for item in snapshot.occurrences
            if dispositions.get(item.occurrence_id)
            not in {"hard_excluded", "not_tracked"}
        )
        group_projection = SourceGroupProjection.from_occurrences(
            group_occurrences,
            availability_by_occurrence={
                item.occurrence_id: (
                    SourceAvailability.SOURCE_UNAVAILABLE
                    if dispositions.get(item.occurrence_id)
                    in {"blocked", "unavailable"}
                    else SourceAvailability.AVAILABLE
                )
                for item in group_occurrences
            },
        )
        assert self.store is not None
        self.store.replace_source_group_scope(
            scope_id=snapshot.scope_id,
            inventory_revision=snapshot.revision,
            rows=(asdict(item) for item in group_projection.index_rows()),
        )
        self.depth.mark_stale_many(
            inventory_revision=snapshot.revision,
            dependencies_by_occurrence=changes.stale_dependencies,
        )
        if self.coverage_ledger is not None:
            self.coverage_ledger.reconcile_inventory(
                scope_id=snapshot.scope_id,
                inventory_revision=snapshot.revision,
                occurrences=(asdict(item) for item in snapshot.occurrences),
                dispositions=(asdict(item) for item in snapshot.dispositions),
                refresh_summary=False,
            )
            deleted = set(changes.deleted)
            stale_stages_by_object = {
                occurrence_id: tuple(
                    stage_id
                    for dependency, stage_id in (
                        ("extraction", "extraction"),
                        ("analysis", "analysis"),
                        ("evidence", "evidence"),
                        ("projection", "ui_projection"),
                    )
                    if dependency in dependencies
                )
                for occurrence_id, dependencies in (
                    changes.stale_dependencies.items()
                )
                if occurrence_id not in deleted
            }
            if stale_stages_by_object:
                self.coverage_ledger.mark_stale_many(
                    stage_ids_by_object=stale_stages_by_object,
                    input_fingerprint=changes.change_set_id,
                    refresh_summary=False,
                )
            if deleted:
                self.coverage_ledger.retire_objects(
                    object_ids=deleted,
                    scope_id=snapshot.scope_id,
                    inventory_revision=snapshot.revision,
                    reason="inventory_deleted_or_policy_pruned",
                    refresh_summary=False,
                )
            if refresh_coverage_summary:
                self.coverage_ledger.refresh_summary()
        return snapshot, changes

    def rebase_current_inventory_policy(
        self,
        *,
        provider: str,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Reclassify current durable snapshots under the current policy."""

        if self.store is None or self.inventory is None:
            raise RuntimeError("MATTERS_HOME is required for inventory policy rebase")
        normalized_provider = str(provider).strip().casefold()
        if not normalized_provider:
            raise ValueError("inventory policy provider is required")
        if offset < 0 or limit < 1 or limit > 100:
            raise ValueError("inventory policy rebase bounds are invalid")
        scope_rows, total = self.store.current_filtered_page(
            "candidate_scope",
            json_field="provider",
            values=(normalized_provider,),
            offset=offset,
            limit=limit,
        )
        current_policy_payload = self.store.current(
            "tracking_policy",
            "tracking-policy:default",
        )
        if (
            current_policy_payload is None
            or int(current_policy_payload.get("revision", 0))
            < CURRENT_TRACKING_POLICY_REVISION
        ):
            current_policy = TrackingPolicy(
                policy_id="tracking-policy:default",
                revision=CURRENT_TRACKING_POLICY_REVISION,
            )
        else:
            current_policy = TrackingPolicy(
                policy_id=str(current_policy_payload["policy_id"]),
                revision=int(current_policy_payload["revision"]),
                protected_classes=tuple(
                    current_policy_payload.get("protected_classes", ())
                ),
                ignored_names=tuple(
                    current_policy_payload.get("ignored_names", ())
                ),
                archive_size_limit=int(
                    current_policy_payload.get("archive_size_limit", 0)
                ),
                changed_at=str(current_policy_payload.get("changed_at", "")),
            )

        rebased = already_current = missing_snapshot = 0
        for scope_payload in scope_rows:
            scope = CandidateScope(
                scope_id=str(scope_payload["scope_id"]),
                revision=int(scope_payload["revision"]),
                provider=str(scope_payload["provider"]),
                root_locator=str(scope_payload["root_locator"]),
                object_types=tuple(scope_payload.get("object_types", ())),
                include_hidden=bool(scope_payload.get("include_hidden", False)),
                follow_links=bool(scope_payload.get("follow_links", False)),
                active=bool(scope_payload.get("active", True)),
            )
            snapshot_payload = self.store.current(
                "inventory_snapshot",
                scope.scope_id,
            )
            if snapshot_payload is None:
                missing_snapshot += 1
                continue
            if int(snapshot_payload.get("policy_revision", 0)) == (
                current_policy.revision
            ):
                already_current += 1
                continue
            self.reconcile_inventory(
                scope=scope,
                policy=current_policy,
                occurrences=tuple(
                    InventoryOccurrence(**dict(item))
                    for item in snapshot_payload.get("occurrences", ())
                ),
                refresh_coverage_summary=False,
            )
            rebased += 1
        if rebased and self.coverage_ledger is not None:
            self.coverage_ledger.refresh_summary()
        next_offset = offset + len(scope_rows)
        has_more = next_offset < total
        return {
            "provider": normalized_provider,
            "scanned_scope_count": len(scope_rows),
            "rebased_scope_count": rebased,
            "already_current_scope_count": already_current,
            "missing_snapshot_scope_count": missing_snapshot,
            "next_offset": next_offset if has_more else 0,
            "has_more": has_more,
            "status": (
                "blocked"
                if missing_snapshot
                else "partial"
                if has_more
                else "current"
            ),
        }

    def rebase_source_group_index(
        self,
        *,
        after_object_id: str = "",
        after_scope_id: str = "",
        limit: int = 500,
    ) -> dict[str, Any]:
        """Repair one bounded page of the rebuildable SourceGroup index."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for source groups")
        rows, has_more = self.store.source_group_rebase_page(
            after_object_id=after_object_id,
            after_scope_id=after_scope_id,
            limit=limit,
        )
        target_by_id = {
            str(row["object_id"]): InventoryOccurrence(
                **dict(row["occurrence"])
            )
            for row in rows
            if row["disposition"] not in {"hard_excluded", "not_tracked"}
        }
        context_by_id = dict(target_by_id)
        frontier = {
            item.parent_occurrence_id
            for item in context_by_id.values()
            if item.parent_occurrence_id
        }
        for _ in range(4):
            missing = tuple(
                sorted(frontier.difference(context_by_id))
            )
            if not missing:
                break
            resolved = self.store.inventory_occurrences_by_object_ids(
                missing
            )
            frontier = set()
            for object_id in missing:
                candidates = resolved.get(object_id, ())
                if not candidates:
                    continue
                selected = max(
                    candidates,
                    key=lambda item: (
                        int(item["inventory_revision"]),
                        str(item["scope_id"]),
                    ),
                )
                occurrence = InventoryOccurrence(
                    **dict(selected["occurrence"])
                )
                context_by_id[occurrence.occurrence_id] = occurrence
                if occurrence.parent_occurrence_id:
                    frontier.add(occurrence.parent_occurrence_id)
        availability_by_occurrence = {
            str(row["object_id"]): (
                SourceAvailability.SOURCE_UNAVAILABLE
                if row["disposition"] in {"blocked", "unavailable"}
                else SourceAvailability.AVAILABLE
            )
            for row in rows
        }
        projection = SourceGroupProjection.from_occurrences(
            context_by_id.values(),
            availability_by_occurrence=availability_by_occurrence,
        )
        projected_by_occurrence: dict[str, list[dict[str, Any]]] = {}
        for item in projection.index_rows():
            if item.inventory_occurrence_id not in target_by_id:
                continue
            projected_by_occurrence.setdefault(
                item.inventory_occurrence_id,
                [],
            ).append(asdict(item))
        index_rows: list[dict[str, Any]] = []
        for row in rows:
            if row["disposition"] in {"hard_excluded", "not_tracked"}:
                continue
            for item in projected_by_occurrence.get(
                str(row["object_id"]),
                (),
            ):
                index_rows.append(
                    {
                        **item,
                        "scope_id": row["scope_id"],
                        "inventory_revision": row["inventory_revision"],
                    }
                )
        indexed_count = self.store.replace_source_group_occurrences(index_rows)
        cleared_count = self.store.clear_source_group_occurrences(
            (
                (
                    str(row["scope_id"]),
                    str(row["object_id"]),
                    int(row["inventory_revision"]),
                )
                for row in rows
                if row["disposition"] in {"hard_excluded", "not_tracked"}
            )
        )
        next_object_id = str(rows[-1]["object_id"]) if rows and has_more else ""
        next_scope_id = str(rows[-1]["scope_id"]) if rows and has_more else ""
        status = self.store.source_group_index_status()
        return {
            **status,
            "scanned_occurrence_count": len(rows),
            "indexed_membership_count": indexed_count,
            "cleared_membership_count": cleared_count,
            "next_object_id": next_object_id,
            "next_scope_id": next_scope_id,
            "has_more": has_more,
        }

    def assess_depth(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        criteria: Mapping[str, bool],
        blocked_by: str = "",
        stale_dependencies: tuple[str, ...] = (),
    ) -> SemanticDepth:
        return self.depth.assess(
            occurrence_id=occurrence_id,
            inventory_revision=inventory_revision,
            criteria=criteria,
            blocked_by=blocked_by,
            stale_dependencies=stale_dependencies,
        )

    def run_analysis(
        self,
        package: AnalysisWorkPackage,
        *,
        runner: AgentRunner,
    ) -> AgentOperationResult:
        return self.operations.run(
            package,
            runner=runner,
            research_status=self.research_status,
        )

    def queue_source_understanding(
        self,
        *,
        source_revision: str,
        source_kind: str,
        anchors: tuple[EvidenceAnchor, ...],
        source_context: Mapping[str, Any] | None = None,
        chunk_size: int = 20,
        text_limit: int = 800,
        max_packages_per_call: int = 5,
        inventory_identity: str | None = None,
    ) -> tuple[AgentOperationResult, ...]:
        """Materialize one bounded page of a durable source-analysis expansion."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for durable analysis")
        if (
            chunk_size < 1
            or chunk_size > 50
            or text_limit < 80
            or text_limit > 4000
            or max_packages_per_call < 1
            or max_packages_per_call > 25
        ):
            raise ValueError("analysis work package bounds are invalid")
        current = tuple(
            sorted(
                (
                    item
                    for item in anchors
                    if item.current and item.text.strip()
                ),
                key=lambda item: (
                    repr(sorted(dict(item.location).items())),
                    item.evidence_id,
                ),
            )
        )
        anchor_fingerprint = "sha256:" + sha256(
            json.dumps(
                [item.evidence_id for item in current],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        allowed_context = {
            key: value
            for key, value in dict(source_context or {}).items()
            if key
            in {
                "source_neighborhood_id",
                "source_group_chain",
                "source_group_labels",
                "source_spatial_context_revision",
                "path_depth",
                "file_kind",
            }
        }
        expansion = self.store.current(
            "source_analysis_expansion",
            source_revision,
        )
        start_offset = 0
        if (
            expansion is not None
            and str(expansion.get("anchor_fingerprint", ""))
            == anchor_fingerprint
            and int(expansion.get("chunk_size", 0) or 0) == chunk_size
            and int(expansion.get("text_limit", 0) or 0) == text_limit
        ):
            start_offset = min(
                len(current),
                max(0, int(expansion.get("next_anchor_offset", 0))),
            )
        end_offset = min(
            len(current),
            start_offset + chunk_size * max_packages_per_call,
        )
        visual_assets = tuple(
            item
            for item in self.store.iter_current("visual_asset")
            if str(item.get("source_revision_id", "")) == source_revision
            and bool(item.get("current", False))
            and bool(item.get("display_allowed", False))
        )
        allowed_asset_ids = tuple(
            str(item["asset_id"]) for item in visual_assets
        )
        resolved_inventory_identity = (
            str(inventory_identity)
            if inventory_identity
            else str(
                (self.store.latest("inventory_snapshot") or {}).get(
                    "snapshot_id",
                    "inventory:current",
                )
            )
        )
        queued: list[AgentOperationResult] = []
        for start in range(start_offset, end_offset, chunk_size):
            chunk = current[start : min(end_offset, start + chunk_size)]
            package = AnalysisWorkPackage.create(
                operation_type="text_analysis",
                task_kind="source_annotation",
                capability_role="low_cost_annotator",
                requested_output_types=("source_annotation",),
                source_revision_ids=(source_revision,),
                model_revision="matters-source-annotation:v1",
                allowed_evidence_ids=tuple(item.evidence_id for item in chunk),
                allowed_asset_ids=allowed_asset_ids,
                private_evidence={
                    "source_kind": source_kind,
                    "source_context": allowed_context,
                    "evidence": tuple(
                        {
                            "evidence_id": item.evidence_id,
                            "text": item.text[:text_limit],
                            "modality": item.modality,
                            "location": {
                                key: value
                                for key, value in dict(item.location).items()
                                if key
                                in {
                                    "field",
                                    "page",
                                    "line",
                                    "line_start",
                                    "line_end",
                                    "region",
                                }
                            },
                        }
                        for item in chunk
                    ),
                    "visual_candidates": tuple(
                        {
                            "asset_id": str(item["asset_id"]),
                            "kind": str(item.get("kind", "")),
                            "width": int(item.get("width", 0)),
                            "height": int(item.get("height", 0)),
                            "preview_token": str(
                                item.get("preview_token", "")
                            ),
                        }
                        for item in visual_assets
                    ),
                    "required_output": {
                        "finding_types": ("source_annotation",),
                        "required_locales": ("en", "zh-CN"),
                        "advisory_only": True,
                        "human_confirmation_required": False,
                    },
                },
                inventory_identity=resolved_inventory_identity,
                locale_registry_revision=self.locale_registry_owner.revision,
                prompt_contract_id="matters.source-annotation",
            )
            queued.append(self.operations.queue(package))
        descriptor = {
            "source_revision": source_revision,
            "source_kind": source_kind,
            "anchor_fingerprint": anchor_fingerprint,
            "anchor_count": len(current),
            "chunk_size": chunk_size,
            "text_limit": text_limit,
            "next_anchor_offset": end_offset,
            "remaining_anchor_count": max(0, len(current) - end_offset),
            "status": (
                "complete" if end_offset >= len(current) else "pending"
            ),
            "source_context": allowed_context,
            "inventory_identity": resolved_inventory_identity,
            "bounded_materialization": True,
        }
        if expansion != descriptor:
            self.store.append_next(
                "source_analysis_expansion",
                source_revision,
                descriptor,
            )
        return tuple(queued)

    def expand_pending_source_understanding(
        self,
        *,
        limit_sources: int = 20,
        max_packages_per_source: int = 5,
    ) -> dict[str, int | str]:
        """Resume bounded package materialization without rereading a source."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for durable analysis")
        if (
            limit_sources < 1
            or limit_sources > 200
            or max_packages_per_source < 1
            or max_packages_per_source > 25
        ):
            raise ValueError("source analysis expansion bounds are invalid")
        pending = tuple(
            sorted(
                (
                    item
                    for item in self.store.iter_current(
                        "source_analysis_expansion"
                    )
                    if str(item.get("status", "")) == "pending"
                ),
                key=lambda item: str(item.get("source_revision", "")),
            )
        )
        expanded_sources = 0
        queued_packages = 0
        for descriptor in pending[:limit_sources]:
            source_revision = str(descriptor.get("source_revision", ""))
            source_id, separator, raw_version = source_revision.rpartition(
                ":v"
            )
            if not separator or not source_id or not raw_version.isdigit():
                continue
            anchor_rows = (
                self.store.evidence_anchors_for_source_version(
                    source_id=source_id,
                    source_version=int(raw_version),
                )
            )
            anchors = tuple(EvidenceAnchor(**dict(item)) for item in anchor_rows)
            results = self.queue_source_understanding(
                source_revision=source_revision,
                source_kind=str(descriptor.get("source_kind", "document")),
                anchors=anchors,
                source_context=dict(descriptor.get("source_context", {})),
                chunk_size=int(descriptor.get("chunk_size", 20)),
                text_limit=int(descriptor.get("text_limit", 800)),
                max_packages_per_call=max_packages_per_source,
                inventory_identity=str(
                    descriptor.get(
                        "inventory_identity",
                        "inventory:current",
                    )
                ),
            )
            expanded_sources += 1
            queued_packages += len(results)
        remaining_sources = sum(
            1
            for item in self.store.iter_current(
                "source_analysis_expansion"
            )
            if str(item.get("status", "")) == "pending"
        )
        return {
            "status": (
                "progressed" if expanded_sources else "idle"
            ),
            "expanded_source_count": expanded_sources,
            "queued_package_count": queued_packages,
            "remaining_source_count": remaining_sources,
        }

    def pending_analysis_packages(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        package_id: str = "",
        source_revision: str = "",
        task_kind: str = "",
    ) -> dict[str, Any]:
        """Return private, bounded packages only to the local AI operation path."""

        rows, total = self.operations.pending_packages(
            offset=offset,
            limit=limit,
            package_id=package_id,
            source_revision=source_revision,
            task_kind=task_kind,
        )
        next_offset = offset + len(rows)
        active_profile = (
            self.execution_profiles.current()
            if self.execution_profiles is not None
            else None
        )
        return {
            "items": rows,
            "offset": offset,
            "limit": limit,
            "total_count": total,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
            "exact_selectors": {
                "package_id": package_id.strip(),
                "source_revision": source_revision.strip(),
                "task_kind": task_kind.strip(),
            },
            "execution_profile_identity": (
                active_profile.profile_identity
                if active_profile is not None
                else "execution-profile:unavailable"
            ),
            "disclosure": "private_local_ai_operation_only",
        }

    def rebase_analysis_contracts(
        self,
        *,
        after_package_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Advance one explicit, bounded current-contract rebase page."""

        return asdict(
            self.operations.rebase_work_packages_to_current_contract(
                after_package_id=after_package_id,
                limit=limit,
            )
        )

    def queue_research_operation(
        self,
        matter_id: str,
        question: str = "",
    ) -> dict[str, Any]:
        """Queue one evidence-bound A1 request without executing research."""

        if self.store is None or self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for durable research")
        normalized_matter_id = matter_id.strip()
        if not normalized_matter_id:
            raise ValueError("matter_id is required")
        if "\n" in question or "\r" in question:
            raise ValueError("research question must be a single line")
        normalized_question = " ".join(question.split())
        if len(normalized_question) > 1000:
            raise ValueError("research question is too long")
        question_tokens = (
            item.strip("()[]{}<>\"'.,;:")
            for item in normalized_question.split()
        )
        if any(
            token and Path(token).is_absolute()
            for token in question_tokens
        ):
            raise ValueError("research question cannot contain an absolute path")

        admission = self.store.current(
            "admission_decision",
            normalized_matter_id,
        )
        matter = (
            admission.get("matter")
            if isinstance(admission, Mapping)
            else None
        )
        if (
            not isinstance(admission, Mapping)
            or str(admission.get("status", "")) != "admitted"
            or not isinstance(matter, Mapping)
            or str(matter.get("matter_id", "")) != normalized_matter_id
            or matter.get("admitted") is False
        ):
            raise KeyError("current admitted Matter is unavailable")

        projection = self.store.current("projection", normalized_matter_id)
        cards = self.browser.cards((normalized_matter_id,))
        if (
            not isinstance(projection, Mapping)
            or str(projection.get("equivalence_status", "")) != "equivalent"
            or len(cards) != 1
        ):
            raise RuntimeError("current bilingual Matter projection is unavailable")
        card = cards[0]
        title = {
            locale: str(dict(card.get("title", {})).get(locale, "")).strip()
            for locale in ("en", "zh-CN")
        }
        summary = {
            locale: str(dict(card.get("summary", {})).get(locale, "")).strip()
            for locale in ("en", "zh-CN")
        }
        if not all((*title.values(), *summary.values())):
            raise RuntimeError("current bilingual Matter context is incomplete")

        admitted_evidence_ids = {
            str(item)
            for item in matter.get("evidence_ids", ())
            if str(item)
        }
        allowed_evidence_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in projection.get("evidence_ids", ())
                if str(item) in admitted_evidence_ids
            )
        )
        source_revision = str(
            projection.get("semantic_revision", "")
        ).strip()
        if not source_revision or not allowed_evidence_ids:
            raise RuntimeError("current Matter evidence binding is unavailable")

        provider_gate = {
            "provider_id": "researchguard",
            "status": (
                "current" if self.research_status.current else "pending"
            ),
            "provider_status": self.research_status.status,
            "execution_deferred": not self.research_status.current,
        }
        package = AnalysisWorkPackage.create(
            operation_type="research_operation",
            task_kind="supplemental_information_research",
            capability_role="ambiguity_resolver",
            requested_output_types=("supplemental_information_candidate",),
            source_revision_ids=(source_revision,),
            model_revision="A1_matters_research_operation:v1",
            allowed_evidence_ids=allowed_evidence_ids,
            allowed_tool_ids=("researchguard",),
            private_evidence={
                "matter_context": {
                    "title": title,
                    "summary": summary,
                },
                "research_question": normalized_question,
                "provider_gate": provider_gate,
                "required_output": {
                    "finding_types": (
                        "supplemental_information_candidate",
                    ),
                    "required_locales": ("en", "zh-CN"),
                    "advisory_only": True,
                    "canonical_write_allowed": False,
                },
            },
            matter_id=normalized_matter_id,
            matter_revision=source_revision,
            prompt_contract_id="matters.research-orchestration",
            prompt_contract_revision="v1",
            output_schema_id="matters.research-operation-result.v2",
            required_skill_id="matters-research-orchestration",
            required_runner_id="researchguard",
            required_runner_version="researchguard-provider-contract:v1",
            locale_registry_revision=self.locale_registry_owner.revision,
            disclosure_policy="external_pseudonymized",
            resource_budget={"max_inputs": 4, "max_chars": 4000},
            auto_apply_policy="validate_then_dispatch_original_owner",
        )
        queued = self.operations.queue(package)
        return {
            "status": queued.status,
            "provider_gate": provider_gate,
            "package": asdict(package),
        }

    def pending_generated_heroes(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return private minimized briefs for a Codex image-generation lane."""

        if self.store is None or self.heroes is None:
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        if offset < 0 or limit < 1 or limit > 100:
            raise ValueError("generated hero page bounds are invalid")
        page, total = self.store.pending_generated_hero_page(
            offset=offset,
            limit=limit,
        )
        return {
            "items": tuple(
                {
                    "matter_id": str(item["matter_id"]),
                    "brief_fingerprint": str(
                        item["brief_fingerprint"]
                    ),
                    "brief": dict(item.get("brief_payload", {})),
                    "attempt": int(item.get("attempt", 0)),
                    "max_attempts": int(item.get("max_attempts", 3)),
                }
                for item in page
            ),
            "offset": offset,
            "limit": limit,
            "total_count": total,
            "next_offset": (
                offset + len(page)
                if offset + len(page) < total
                else None
            ),
            "has_more": offset + len(page) < total,
            "disclosure": "private_minimized_generation_brief_only",
        }

    def source_in_place_migration_plan(self) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for storage migration")
        return source_in_place_residual_report(
            self.config.private_root / "matters.sqlite3"
        )

    def create_source_in_place_backup(
        self,
        *,
        backup_root: str,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for storage migration")
        return create_verified_backup(
            private_root=self.config.private_root,
            backup_root=Path(backup_root),
        )

    def verify_source_in_place_backup(
        self,
        *,
        backup_root: str,
    ) -> dict[str, Any]:
        return verify_source_in_place_backup(Path(backup_root))

    def apply_source_in_place_migration_batch(
        self,
        *,
        backup_root: str,
        limit: int = 200,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for storage migration")
        return apply_database_batch(
            private_root=self.config.private_root,
            backup_root=Path(backup_root),
            limit=limit,
        )

    def clean_source_in_place_storage(
        self,
        *,
        backup_root: str,
        blob_limit: int = 2000,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for storage migration")
        blobs = reclaim_orphan_blobs(
            database_path=self.config.private_root / "matters.sqlite3",
            blob_root=self.config.private_root / "blobs",
            limit=blob_limit,
        )
        staging = (
            clean_staging(
                private_root=self.config.private_root,
                backup_root=Path(backup_root),
            )
            if not int(blobs["remaining_orphan_count"])
            else {
                "status": "pending_blob_cleanup",
                "deleted_file_count": 0,
                "deleted_bytes": 0,
            }
        )
        result = {
            "status": (
                "current"
                if staging["status"] == "staging_current"
                else "pending"
            ),
            "blobs": blobs,
            "staging": staging,
        }
        cleanup_fingerprint = _fingerprint(result)
        self.store.record_coverage_surface_status(
            surface_id="raw_cleanup",
            status=(
                "current"
                if not int(blobs["remaining_orphan_count"])
                else "pending"
            ),
            input_fingerprint=cleanup_fingerprint,
            failure_class=(
                ""
                if not int(blobs["remaining_orphan_count"])
                else "orphan_blob_cleanup_pending"
            ),
        )
        self.store.record_coverage_surface_status(
            surface_id="staging_cleanup",
            status=(
                "current"
                if staging["status"] == "staging_current"
                else "pending"
            ),
            input_fingerprint=cleanup_fingerprint,
            failure_class=(
                ""
                if staging["status"] == "staging_current"
                else "staging_cleanup_pending"
            ),
        )
        return result

    def verify_source_in_place_migration(
        self,
        *,
        backup_root: str,
    ) -> dict[str, Any]:
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for storage migration")
        return verify_source_in_place_migration(
            private_root=self.config.private_root,
            backup_root=Path(backup_root),
        )

    def register_generated_hero(
        self,
        *,
        matter_id: str,
        brief_fingerprint: str,
        content: bytes,
        media_type: str,
        localized_alt: Mapping[str, str],
        runner_contract_id: str,
        execution_identity: str,
        refresh_coverage_summary: bool = True,
    ) -> dict[str, Any]:
        if self.heroes is None:
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        record = self.heroes.register_generated(
            matter_id=matter_id,
            brief_fingerprint=brief_fingerprint,
            content=content,
            media_type=media_type,
            localized_alt=localized_alt,
            runner_contract_id=runner_contract_id,
            execution_identity=execution_identity,
        )
        for row in self._coverage_rows_for_matter(matter_id):
            if self.coverage_ledger is not None:
                self.coverage_ledger.mark_stage(
                    object_id=str(row["object_id"]),
                    stage_id="generated_hero",
                    status="current",
                    input_fingerprint=brief_fingerprint,
                    output_ref=f"generated_hero_record:{matter_id}",
                    matter_ids=(matter_id,),
                    refresh_summary=False,
                )
        self._mark_matter_ui_if_ready(
            matter_id,
            brief_fingerprint,
            refresh_summary=refresh_coverage_summary,
        )
        return {
            "matter_id": matter_id,
            "status": record.status,
            "preview_token": record.private_asset_token,
            "generation_revision": record.generation_revision,
        }

    def refresh_generated_hero(
        self,
        *,
        matter_id: str,
    ) -> dict[str, Any]:
        """Retire a visually unrepresentative Hero and queue one replacement."""

        if self.heroes is None:
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        invalidated = self.heroes.apply_change(
            matter_id=matter_id,
            change_kind="quality",
        )
        preparation = self.prepare_generated_heroes(
            matter_ids=(matter_id,),
        )
        current = self.heroes.current(matter_id)
        if current is None:
            raise RuntimeError("generated hero replacement was not prepared")
        return {
            "matter_id": matter_id,
            "status": current.status,
            "invalidated_revision": invalidated.generation_revision,
            "generation_revision": current.generation_revision,
            "brief_fingerprint": current.brief_fingerprint,
            "prepared": preparation,
        }

    def record_generated_hero_failure(
        self,
        *,
        matter_id: str,
        failure_kind: str,
    ) -> dict[str, Any]:
        if self.heroes is None:
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        record = self.heroes.record_failure(
            matter_id=matter_id,
            failure_kind=failure_kind,
        )
        return {
            "matter_id": matter_id,
            "status": record.status,
            "attempt": record.attempt,
            "retryable": record.retryable,
            "failure_kind": record.failure_kind,
        }

    def import_autonomous_result(
        self,
        *,
        package_id: str,
        provider_id: str,
        provider_version: str,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Validate WorkPackageV2 and dispatch findings without confirmation."""

        if self.dispatcher is None or self.store is None:
            raise RuntimeError("MATTERS_HOME is required for durable analysis")
        package = self.operations.package(package_id)
        invalidation = self.store.current(
            "analysis_result_invalidation",
            package_id,
        )
        if (
            invalidation is not None
            and str(invalidation.get("status", "")) == "superseded"
        ):
            raise ValueError(
                "analysis work package was superseded by a current successor"
            )
        current_result = self.operations.current_result(package_id)
        if (
            current_result is not None
            and current_result.status == "passed"
            and current_result.receipt_current
            and current_result.package_input_fingerprint
            == package.input_fingerprint
        ):
            response = {
                "status": current_result.status,
                "result_id": current_result.result_id,
                "finding_count": len(current_result.findings),
                "dispatch_count": 0,
                "dispatch_statuses": (),
                "advisory_only": current_result.advisory_only,
                "auto_apply_status": current_result.auto_apply_status,
                "write_status": "current",
            }
            if package.task_kind == "source_annotation":
                followup = self._queue_semantic_modeling_from_annotation(
                    package,
                    current_result,
                )
                response["followup_package_id"] = followup.package_id
                response["followup_capability_role"] = (
                    followup.capability_role
                )
            return response
        imported_payload = dict(result)
        active_profile = (
            self.execution_profiles.current()
            if self.execution_profiles is not None
            else None
        )
        if active_profile is not None and str(
            imported_payload.get("execution_profile_identity", "")
        ) != active_profile.profile_identity:
            imported_payload = {
                "status": "blocked",
                "failure_class": "execution_profile_identity_mismatch",
                "input_dispositions": [
                    {
                        "input_id": input_id,
                        "disposition": "insufficient",
                        "reason": (
                            "Result did not identify the active private "
                            "Codex execution profile."
                        ),
                    }
                    for input_id in (
                        *package.allowed_evidence_ids,
                        *package.allowed_asset_ids,
                    )
                ],
                "findings": [],
                "execution_profile_identity": (
                    active_profile.profile_identity
                ),
                "concrete_execution_identity": (
                    "execution:profile-mismatch"
                ),
                "escalation_status": "profile_mismatch",
                "resource_usage": {},
            }
        operation_result = self.operations.import_result(
            package_id=package_id,
            provider_id=provider_id,
            provider_version=provider_version,
            result=imported_payload,
            research_status=self.research_status,
        )
        outcomes = self.dispatcher.dispatch(package, operation_result)
        response = {
            "status": operation_result.status,
            "result_id": operation_result.result_id,
            "finding_count": len(operation_result.findings),
            "dispatch_count": len(outcomes),
            "dispatch_statuses": tuple(item.status for item in outcomes),
            "advisory_only": operation_result.advisory_only,
            "auto_apply_status": (
                "blocked"
                if operation_result.status != "passed"
                or any(item.status == "blocked" for item in outcomes)
                else (
                    "no_finding"
                    if not operation_result.findings
                    else "auto_applied"
                )
            ),
        }
        followup = self._post_autonomous_dispatch(
            package,
            operation_result,
        )
        if followup is not None:
            response["followup_package_id"] = followup.package_id
            response["followup_capability_role"] = followup.capability_role
        return response

    def activate_codex_execution_profile(
        self,
        entries: tuple[Mapping[str, str], ...],
    ) -> dict[str, Any]:
        """Activate private deployment mappings without changing packages."""

        if self.execution_profiles is None:
            raise RuntimeError(
                "MATTERS_HOME is required for a private Codex profile"
            )
        profile = self.execution_profiles.activate(
            tuple(
                CapabilityProfileEntry(
                    capability_role=str(item["capability_role"]),
                    execution_target=str(item["execution_target"]),
                    reasoning_level=str(item["reasoning_level"]),
                    availability=str(item.get("availability", "available")),
                )
                for item in entries
            )
        )
        return {
            "status": profile.status,
            "profile_identity": profile.profile_identity,
            "profile_revision": profile.revision,
            "available_capability_roles": tuple(
                sorted(item.capability_role for item in profile.entries)
            ),
            "disclosure": "private_local_deployment_only",
        }

    def codex_execution_profile_status(self) -> dict[str, Any]:
        if self.execution_profiles is None:
            return {
                "status": "unavailable",
                "profile_revision": 0,
                "available_capability_roles": (),
            }
        return self.execution_profiles.public_status()

    def codex_execution_profile_receipt(self) -> dict[str, Any]:
        """Return the private identity needed by a Codex-hosted worker."""

        if self.execution_profiles is None:
            return {
                "status": "unavailable",
                "profile_identity": "",
                "profile_revision": 0,
                "available_capability_roles": (),
            }
        profile = self.execution_profiles.current()
        if profile is None:
            return {
                "status": "not_configured",
                "profile_identity": "",
                "profile_revision": 0,
                "available_capability_roles": (),
            }
        return {
            "status": profile.status,
            "profile_identity": profile.profile_identity,
            "profile_revision": profile.revision,
            "available_capability_roles": tuple(
                sorted(
                    item.capability_role
                    for item in profile.entries
                    if item.availability == "available"
                )
            ),
            "disclosure": "private_codex_worker_only",
        }

    def _post_autonomous_dispatch(
        self,
        package: AnalysisWorkPackage,
        result: AgentOperationResult,
    ) -> AnalysisWorkPackage | None:
        if (
            package.task_kind == "source_annotation"
            and result.status == "passed"
        ):
            return self._queue_semantic_modeling_from_annotation(
                package,
                result,
            )
        return None

    def reconcile_annotation_semantic_followups(
        self,
        *,
        after_package_id: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Retire duplicate unexecuted semantic follow-ups per exact A0 result."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for follow-up repair")
        if limit < 1 or limit > 500:
            raise ValueError("follow-up reconciliation limit is invalid")
        annotations = self.store.analysis_work_package_page(
            after_package_id=after_package_id,
            limit=limit,
            task_kinds=("source_annotation",),
        )
        annotation_ids = tuple(
            str(item.get("package_id", ""))
            for item in annotations
            if str(item.get("package_id", ""))
        )
        dependent_map = self.store.current_by_json_array_members(
            "analysis_work_package",
            json_field="dependency_package_ids",
            values=annotation_ids,
        )
        dependent_ids = tuple(
            str(item.get("package_id", ""))
            for rows in dependent_map.values()
            for item in rows
            if str(item.get("task_kind", "")) == "semantic_understanding"
            and str(item.get("package_id", ""))
        )
        invalidations = self.store.current_many(
            "analysis_result_invalidation",
            dependent_ids,
        )
        results = self.store.current_many(
            "agent_operation_result",
            dependent_ids,
        )
        relations = self.store.current_many(
            "analysis_followup_relation",
            annotation_ids,
        )
        retired = blocked = duplicate_groups = 0
        for annotation in annotations:
            annotation_id = str(annotation.get("package_id", ""))
            dependents = dependent_map.get(annotation_id, ())
            active = tuple(
                item
                for item in dependents
                if str(item.get("task_kind", ""))
                == "semantic_understanding"
                and str(item.get("package_id", ""))
                and str(item.get("package_id", "")) not in invalidations
            )
            if len(active) <= 1:
                continue
            duplicate_groups += 1
            active_ids = tuple(
                str(item.get("package_id", "")) for item in active
            )
            relation = relations.get(annotation_id)
            relation_id = str(
                (relation or {}).get("followup_package_id", "")
            )
            passed_ids = tuple(
                package_id
                for package_id in active_ids
                if (
                    (result := results.get(package_id))
                    is not None
                    and str(result.get("status", "")) == "passed"
                    and bool(result.get("receipt_current", False))
                )
            )
            canonical_id = (
                relation_id
                if relation_id in active_ids
                else passed_ids[0]
                if len(passed_ids) == 1
                else ""
            )
            if not canonical_id:
                blocked += 1
                continue
            extras = tuple(
                package_id
                for package_id in active_ids
                if package_id != canonical_id
            )
            executed_extra = False
            for package_id in extras:
                result = results.get(package_id)
                if (
                    result is not None
                    and str(result.get("status", "")) == "passed"
                    and str(result.get("auto_apply_status", ""))
                    in {"auto_applied", "uncertain"}
                ):
                    executed_extra = True
                    break
            if executed_extra:
                blocked += 1
                continue
            canonical = next(
                item
                for item in active
                if str(item.get("package_id", "")) == canonical_id
            )
            if relation_id != canonical_id:
                self.store.compare_current_and_append(
                    "analysis_followup_relation",
                    annotation_id,
                    is_equivalent=lambda current, expected=canonical_id: (
                        current is not None
                        and str(current.get("followup_package_id", ""))
                        == expected
                    ),
                    payload_factory=lambda _revision, _current, expected=canonical: {
                        "annotation_package_id": annotation_id,
                        "annotation_input_fingerprint": str(
                            annotation.get("input_fingerprint", "")
                        ),
                        "followup_package_id": str(
                            expected.get("package_id", "")
                        ),
                        "followup_input_fingerprint": (
                            str(expected.get("input_fingerprint", ""))
                        ),
                        "status": "current",
                    },
                )
            for package_id in extras:
                result = results.get(package_id)
                payload = {
                    "package_id": package_id,
                    "result_id": str((result or {}).get("result_id", "")),
                    "status": "superseded",
                    "reason": "duplicate_annotation_semantic_followup",
                    "replacement_package_id": canonical_id,
                    "source_result_preserved": result is not None,
                }
                write = self.store.compare_current_and_append(
                    "analysis_result_invalidation",
                    package_id,
                    is_equivalent=lambda current, expected=payload: (
                        current == expected
                    ),
                    payload_factory=lambda _revision, _current, expected=payload: (
                        expected
                    ),
                )
                retired += int(str(write["status"]) == "appended")
        next_cursor = (
            str(annotations[-1].get("package_id", ""))
            if len(annotations) == limit
            else ""
        )
        return {
            "scanned_annotation_count": len(annotations),
            "duplicate_group_count": duplicate_groups,
            "retired_package_count": retired,
            "blocked_group_count": blocked,
            "next_cursor": next_cursor,
            "has_more": bool(next_cursor),
            "status": (
                "blocked"
                if blocked
                else "partial"
                if next_cursor
                else "current"
            ),
        }

    def _refresh_semantic_depth_for_object(
        self,
        object_id: str,
        input_fingerprint: str,
    ) -> None:
        if self.coverage_ledger is None:
            return
        row = self.coverage_ledger.current(object_id)
        if row is None:
            return
        if row.provider == "matters":
            # Canonical Matters require aggregate C6/C12/activity/hierarchy
            # evidence. Occurrence-only ``not_applicable`` stages cannot
            # license Matter sufficiency.
            return
        blocked_pointer = next(
            (
                pointer
                for stage_id in (
                    "extraction",
                    "evidence",
                    "analysis",
                    "owner_dispatch",
                )
                if (pointer := row.stages.get(stage_id)) is not None
                and pointer.status == "blocked"
            ),
            None,
        )

        def current_or_explicit(stage_id: str) -> bool:
            pointer = row.stages.get(stage_id)
            return (
                pointer is not None
                and pointer.status
                in {"current", "no_finding", "not_applicable", "uncertain"}
            )

        self.depth.assess(
            occurrence_id=object_id,
            inventory_revision=row.inventory_revision,
            criteria={
                "coverage_terminal": (
                    current_or_explicit("authorization")
                    and current_or_explicit("inventory")
                ),
                "extraction_current": current_or_explicit("extraction"),
                "analysis_terminal": current_or_explicit("analysis"),
                "evidence_anchored": current_or_explicit("evidence"),
                "owner_dispatch_terminal": current_or_explicit(
                    "owner_dispatch"
                ),
            },
            blocked_by=(
                (
                    blocked_pointer.failure_class
                    or f"{blocked_pointer.stage_id}_blocked"
                )
                if blocked_pointer is not None
                else ""
            ),
        )
        for matter_id in row.matter_ids:
            self._mark_matter_ui_if_ready(
                matter_id,
                input_fingerprint,
                refresh_summary=False,
            )

    def _queue_semantic_modeling_from_annotation(
        self,
        annotation_package: AnalysisWorkPackage,
        annotation_result: AgentOperationResult,
    ) -> AnalysisWorkPackage:
        if self.store is None:
            raise RuntimeError("durable private runtime is required")
        dependent_rows = self.store.current_by_json_array_members(
            "analysis_work_package",
            json_field="dependency_package_ids",
            values=(annotation_package.package_id,),
        ).get(annotation_package.package_id, ())
        existing_ids = tuple(
            str(item.get("package_id", ""))
            for item in dependent_rows
            if str(item.get("task_kind", "")) == "semantic_understanding"
            and tuple(item.get("source_revision_ids", ()))
            == annotation_package.source_revision_ids
            and str(item.get("package_id", ""))
            and self.store.current(
                "analysis_result_invalidation",
                str(item.get("package_id", "")),
            )
            is None
        )
        if len(existing_ids) > 1:
            relation = self.store.current(
                "analysis_followup_relation",
                annotation_package.package_id,
            )
            relation_id = str(
                (relation or {}).get("followup_package_id", "")
            )
            if relation_id in existing_ids:
                return self.operations.package(relation_id)
            raise RuntimeError(
                "annotation has multiple current semantic follow-up packages"
            )
        if existing_ids:
            return self.operations.package(existing_ids[0])
        plan_write = self.store.compare_current_and_append(
            "analysis_followup_plan",
            annotation_package.package_id,
            is_equivalent=lambda current: (
                current is not None
                and str(current.get("annotation_input_fingerprint", ""))
                == annotation_package.input_fingerprint
                and str(current.get("annotation_terminal_receipt", ""))
                == annotation_result.terminal_receipt
            ),
            payload_factory=lambda _revision, current: (
                {
                    "annotation_package_id": annotation_package.package_id,
                    "annotation_input_fingerprint": (
                        annotation_package.input_fingerprint
                    ),
                    "annotation_terminal_receipt": (
                        annotation_result.terminal_receipt
                    ),
                    "analysis_as_of": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "status": "planned",
                }
                if current is None
                else _raise_followup_plan_conflict()
            ),
        )
        analysis_as_of = str(
            plan_write["payload"].get("analysis_as_of", "")
        )
        if not analysis_as_of:
            raise RuntimeError(
                "annotation semantic follow-up plan has no analysis time"
            )
        requested_outputs = (
            "matter_candidate",
            "matter_hierarchy_candidate",
            "work_item_candidate",
            "person_candidate",
            "event_candidate",
            "deadline_candidate",
            "open_loop_candidate",
            "lifecycle_candidate",
            "outcome_candidate",
            "completion_gap",
            "conflict",
            "bounded_summary",
            "material_clue_candidate",
            "generated_hero_candidate",
            "supplemental_information_candidate",
        )
        evidence = dict(annotation_package.untrusted_evidence)
        evidence["analysis_as_of"] = analysis_as_of
        evidence["source_annotations"] = tuple(
            {
                "finding_id": finding.finding_id,
                "statement": finding.statement,
                "localized_statement": dict(
                    finding.localized_statement
                ),
                "attributes": dict(finding.attributes),
                "confidence": finding.confidence,
            }
            for finding in annotation_result.findings
        )
        evidence["required_output"] = {
            "finding_types": requested_outputs,
            "required_locales": ("en", "zh-CN"),
            "advisory_only": True,
            "human_confirmation_required": False,
            "hierarchy_required": True,
            "work_items_required": True,
            "lifecycle_and_outcome_required": True,
        }
        package = AnalysisWorkPackage.create(
            operation_type=annotation_package.operation_type,
            task_kind="semantic_understanding",
            capability_role="matter_modeler",
            requested_output_types=requested_outputs,
            dependency_package_ids=(annotation_package.package_id,),
            source_revision_ids=annotation_package.source_revision_ids,
            model_revision="matters-semantic-understanding:v4",
            allowed_evidence_ids=annotation_package.allowed_evidence_ids,
            allowed_asset_ids=annotation_package.allowed_asset_ids,
            allowed_tool_ids=annotation_package.allowed_tool_ids,
            private_evidence=evidence,
            matter_id=annotation_package.matter_id,
            matter_revision=annotation_package.matter_revision,
            authorization_identity=(
                annotation_package.authorization_identity
            ),
            scope_identity=annotation_package.scope_identity,
            inventory_identity=annotation_package.inventory_identity,
            tracking_policy_identity=(
                annotation_package.tracking_policy_identity
            ),
            prompt_contract_id="matters.semantic-understanding",
            prompt_contract_revision="v4",
            output_schema_id="matters.agent-operation-result.v4",
            required_skill_id="matters-semantic-understanding",
            required_skill_version=(
                annotation_package.required_skill_version
            ),
            locale_registry_revision=(
                annotation_package.locale_registry_revision
            ),
            required_locales=annotation_package.required_locales,
            disclosure_policy=annotation_package.disclosure_policy,
            resource_budget=annotation_package.resource_budget,
            auto_apply_policy=annotation_package.auto_apply_policy,
            synthetic=annotation_package.synthetic,
        )
        self.operations.queue(package)
        self.store.compare_current_and_append(
            "analysis_followup_relation",
            annotation_package.package_id,
            is_equivalent=lambda current: (
                current is not None
                and str(current.get("followup_package_id", ""))
                == package.package_id
                and str(current.get("annotation_input_fingerprint", ""))
                == annotation_package.input_fingerprint
            ),
            payload_factory=lambda _revision, current: (
                {
                    "annotation_package_id": annotation_package.package_id,
                    "annotation_input_fingerprint": (
                        annotation_package.input_fingerprint
                    ),
                    "followup_package_id": package.package_id,
                    "followup_input_fingerprint": package.input_fingerprint,
                    "status": "current",
                }
                if current is None
                else _raise_followup_plan_conflict()
            ),
        )
        return package

    def current_records(self, owner: str) -> tuple[dict, ...]:
        if self.store is None:
            return ()
        return self.store.list_current(owner)

    def import_gmail_body_continuation(
        self,
        *,
        manifest_bytes: bytes,
        connector_result: Mapping[str, Any],
    ) -> object:
        """Import one exact already-read Gmail body batch without model use."""

        from matters.application.gmail_body_continuation import (
            GmailBodyContinuationImporter,
        )

        return GmailBodyContinuationImporter(self).import_batch(
            manifest_bytes=manifest_bytes,
            connector_result=connector_result,
        )

    def object_coverage_summary(self) -> dict[str, Any]:
        """Return aggregate progress without exposing private object identities."""

        if self.coverage_ledger is None:
            return {
                "coverage_status": "unavailable",
                "registered_object_count": 0,
                "terminal_object_count": 0,
                "ui_ready_object_count": 0,
                "blocked_object_count": 0,
                "pending_object_count": 0,
                "next_stage_counts": {},
                "worker_health": "inactive",
                "worker_checkpoint": "",
            }
        current = self.coverage_ledger.current_summary()
        source_summary = asdict(
            current if current is not None else self.coverage_ledger.summary()
        )
        hierarchy = (
            self.store.matter_hierarchy_summary_counts()
            if self.store is not None
            else {
                "registered_matter_count": 0,
                "hierarchy_terminal_matter_count": 0,
                "ui_reachable_matter_count": 0,
                "hierarchy_blocked_matter_count": 0,
                "hierarchy_pending_matter_count": 0,
                "hierarchy_current_matter_count": 0,
            }
        )
        hierarchy_complete = (
            hierarchy["registered_matter_count"] == 0
            or (
                hierarchy["ui_reachable_matter_count"]
                == hierarchy["registered_matter_count"]
                and hierarchy["hierarchy_blocked_matter_count"] == 0
            )
        )
        if (
            source_summary["coverage_status"] == "complete"
            and not hierarchy_complete
        ):
            source_summary["coverage_status"] = "partial"
        return {**source_summary, **hierarchy}

    def object_coverage_snapshot(self) -> dict[str, Any]:
        """Return the last published compact status for the catalog shell.

        The full coverage contract deliberately performs exact, whole-ledger
        reconciliation.  It remains available through the coverage and audit
        endpoints, but it must not block the first catalog paint.  Every
        coverage writer publishes this aggregate after its bounded batch, so
        the catalog can project that checkpoint and keep exact drill-down as a
        separate on-demand operation.
        """

        if self.coverage_ledger is None or self.store is None:
            return self.object_coverage_summary()
        payload = self.store.current(
            "object_coverage_summary",
            "current",
        )
        if payload is None:
            return self.object_coverage_summary()
        source_summary = dict(payload)
        if int(source_summary.get("contract_version", 0)) != 2:
            source_summary["coverage_status"] = "partial"
            reasons = tuple(source_summary.get("coverage_reasons", ()))
            source_summary["coverage_reasons"] = tuple(
                dict.fromkeys((*reasons, "coverage_snapshot_requires_rebase"))
            )
        hierarchy = self.store.matter_hierarchy_summary_counts()
        hierarchy_complete = (
            hierarchy["registered_matter_count"] == 0
            or (
                hierarchy["ui_reachable_matter_count"]
                == hierarchy["registered_matter_count"]
                and hierarchy["hierarchy_blocked_matter_count"] == 0
            )
        )
        if (
            source_summary.get("coverage_status") == "complete"
            and not hierarchy_complete
        ):
            source_summary["coverage_status"] = "partial"
        source_summary["summary_freshness"] = (
            "persisted_background_checkpoint"
        )
        return {**source_summary, **hierarchy}

    def source_groups(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        query: str = "",
    ) -> dict[str, Any]:
        """Return one bounded path-free page of current source groups."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for source groups")
        items, total = self.store.source_group_page(
            offset=offset,
            limit=limit,
            query=query,
        )
        next_offset = offset + len(items)
        status = self.store.source_group_index_status()
        return {
            "items": items,
            "total_count": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "freshness_fingerprint": self.store.current_inventory_identity(),
            "registered_occurrence_count": status[
                "eligible_occurrence_count"
            ],
            "index_status": status["status"],
            "indexed_occurrence_count": status[
                "indexed_occurrence_count"
            ],
        }

    def source_group_detail(
        self,
        *,
        group_id: str,
        member_offset: int = 0,
        member_limit: int = 100,
    ) -> dict[str, Any]:
        """Return one bounded path-free current source-group detail."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for source groups")
        detail = self.store.source_group_detail_page(
            group_id=group_id,
            member_offset=member_offset,
            member_limit=member_limit,
        )
        if detail is None:
            raise KeyError(f"unknown SourceGroup: {group_id}")
        status = self.store.source_group_index_status()
        return {
            **detail,
            "freshness_fingerprint": self.store.current_inventory_identity(),
            "registered_occurrence_count": status[
                "eligible_occurrence_count"
            ],
            "index_status": status["status"],
            "indexed_occurrence_count": status[
                "indexed_occurrence_count"
            ],
        }

    def object_coverage_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        next_stage: str = "",
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Return a bounded indexed progress view for local diagnostics."""

        if self.coverage_ledger is None:
            return (), 0
        return self.coverage_ledger.page(
            offset=offset,
            limit=limit,
            next_stage=next_stage,
        )

    def object_stage_audit(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        object_kind: str = "",
        surface_id: str = "",
        surface_status: str = "",
        owner_id: str = "",
        failure_class: str = "",
        freshness: str = "",
        ui_ready: bool | None = None,
        surface_only: bool = False,
    ) -> dict[str, Any]:
        """Return the bounded one-scan path from registration to UI reachability."""

        if self.coverage_audit is None:
            return {
                "run_identity": "coverage-audit:private-runtime-unavailable",
                "ledger_revision": 0,
                "total_objects": 0,
                "occurrence_objects": 0,
                "matter_objects": 0,
                "ui_ready_objects": 0,
                "blocked_objects": 0,
                "stage_counts": {},
                "gaps": (),
                "objects": (),
                "surface_order": (),
                "surface_status_counts": {},
                "total_surfaces": 0,
                "current_surfaces": 0,
                "gap_surfaces": 0,
                "surface_gaps": (),
                "surfaces": (),
                "surface_applicability": {
                    "system": (),
                    "root_matter": (),
                    "child_matter": (),
                    "occurrence": (),
                },
                "offset": offset,
                "limit": limit,
                "total_matching": 0,
                "generated_at": "",
            }
        if surface_only:
            return asdict(
                self.coverage_audit.surface_audit(
                    offset=offset,
                    limit=limit,
                    surface_id=surface_id,
                    surface_status=surface_status,
                    owner_id=owner_id,
                    failure_class=failure_class,
                    freshness=freshness,
                    ui_ready=ui_ready,
                )
            )
        return asdict(
            self.coverage_audit.audit(
                offset=offset,
                limit=limit,
                object_kind=object_kind,
                surface_id=surface_id,
                surface_status=surface_status,
                owner_id=owner_id,
                failure_class=failure_class,
                freshness=freshness,
                ui_ready=ui_ready,
            )
        )

    def gmail_manifest_coverage_audit(
        self,
        *,
        receipt_path: str = "",
        page_paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Audit one verified Gmail manifest using local indexes only."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for Gmail coverage audit")
        return GmailManifestCoverageAuditService(self.store).audit(
            receipt_path=receipt_path,
            page_paths=page_paths,
        )

    def matter_hierarchy_coverage_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        next_stage: str = "",
    ) -> dict[str, Any]:
        """Return one indexed Matter-stage page for the one-scan audit."""

        if self.hierarchy is None:
            return {
                "items": (),
                "total_count": 0,
                "offset": offset,
                "limit": limit,
                "next_offset": None,
                "has_more": False,
                "disclosure": "private_local_audit_only",
            }
        return self.hierarchy.audit_page(
            offset=offset,
            limit=limit,
            next_stage=next_stage,
        )

    def object_catalog_page(
        self,
        *,
        locale: str = "en",
        query: str = "",
        status: str = "all",
        time_filter: str = "all",
        sort: str = "activity",
        offset: int = 0,
        limit: int = 60,
        root_only: bool = True,
        start_year: str = "all",
        people: Sequence[str] = (),
        relationships: Sequence[str] = (),
        topic_types: Sequence[str] = (),
        source_types: Sequence[str] = (),
    ) -> dict[str, Any]:
        if self.browser is None:
            return {
                "items": (),
                "offset": offset,
                "limit": limit,
                "total_count": 0,
                "next_offset": None,
                "has_more": False,
                "catalog_revision": "catalog:private-runtime-unavailable",
                "selected_locale": locale,
                "query": query,
                "filters": {
                    "status": status,
                    "time": time_filter,
                    "sort": sort,
                    "start_year": start_year,
                    "people": tuple(people),
                    "relationships": tuple(relationships),
                    "topic_types": tuple(topic_types),
                    "source_types": tuple(source_types),
                },
                "facets": {
                    "status": {
                        "all": 0,
                        "planned": 0,
                        "in_progress": 0,
                        "completed": 0,
                    },
                    "hierarchy": {"root": 0, "nested": 0},
                    "start_year": (),
                    "people": (),
                    "relationships": (),
                    "topic_types": (),
                    "source_types": (),
                },
                "hierarchy_scope": "roots" if root_only else "all",
            }
        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for the object catalog")
        # One catalog projection performs many bounded current-pointer reads.
        # Reusing one SQLite connection prevents connection setup from being
        # multiplied by the number of registered Matter projections.
        with self.store.connection_session():
            return self.browser.catalog(
                locale=locale,
                query=query,
                status=status,
                time_filter=time_filter,
                sort=sort,
                offset=offset,
                limit=limit,
                root_only=root_only,
                start_year=start_year,
                people=people,
                relationships=relationships,
                topic_types=topic_types,
                source_types=source_types,
            )

    def matter_detail(
        self,
        *,
        matter_id: str,
        locale: str = "en",
    ) -> dict[str, Any]:
        if self.browser is None or self.store is None:
            raise RuntimeError("MATTERS_HOME is required for Matter details")
        with self.store.connection_session():
            return self._matter_detail_in_session(
                matter_id=matter_id,
                locale=locale,
            )

    def _matter_detail_in_session(
        self,
        *,
        matter_id: str,
        locale: str,
    ) -> dict[str, Any]:
        if self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for Matter details")
        detail = self.browser.detail(matter_id, locale=locale)
        if self.hierarchy is None:
            return detail
        children_page = self.matter_children(
            matter_id=matter_id,
            locale=locale,
            offset=0,
            limit=50,
        )
        path_ids = self.hierarchy.path(matter_id)
        path_cards = {
            str(item["matter_id"]): item
            for item in self.browser.cards(path_ids)
        }
        breadcrumb = tuple(
            {
                "matter_id": item_id,
                "title": dict(
                    path_cards.get(item_id, {}).get(
                        "title",
                        {
                            "en": "Unavailable matter",
                            "zh-CN": "事项暂不可用",
                        },
                    )
                ),
            }
            for item_id in path_ids
        )
        parent_edge = self.hierarchy.parent_edge(
            matter_id,
            current_only=True,
        )
        parent = None
        if parent_edge is not None:
            parent_card = path_cards.get(parent_edge.parent_matter_id, {})
            parent = {
                "matter_id": parent_edge.parent_matter_id,
                "role": parent_edge.role,
                "title": dict(
                    parent_card.get(
                        "title",
                        {
                            "en": "Unavailable matter",
                            "zh-CN": "事项暂不可用",
                        },
                    )
                ),
            }
        child_ids = {
            str(item["matter_id"]) for item in children_page["items"]
        }
        excluded_related = child_ids | set(path_ids[:-1])
        related = tuple(
            item
            for item in detail.get("related_matters", ())
            if str(item.get("matter_id", "")) not in excluded_related
        )
        summary = self.store.current(
            "matter_hierarchy_summary",
            matter_id,
        )
        summary_payload = {
            "total_count": int(
                (summary or {}).get(
                    "child_count",
                    children_page["total_count"],
                )
            ),
            "child_state_counts": dict(
                (summary or {}).get("child_state_counts", {})
            ),
            "required_incomplete_count": int(
                (summary or {}).get("required_incomplete_count", 0)
            ),
            "critical_attention_count": int(
                (summary or {}).get("critical_attention_count", 0)
            ),
            "completion_coherent": bool(
                (summary or {}).get("completion_coherent", False)
            ),
        }
        raw_work_items = self.matter_work_items(
            matter_id=matter_id,
            offset=0,
            limit=50,
        )
        work_items = {
            "items": tuple(
                {
                    "kind": str(item.get("kind", "action")),
                    "status": str(item.get("status", "uncertain")),
                    "title": dict(item.get("localized_title", {})),
                    "result": dict(item.get("localized_result", {})),
                    "planned_start": str(item.get("planned_start", "")),
                    "planned_end": str(item.get("planned_end", "")),
                    "actual_start": str(item.get("actual_start", "")),
                    "actual_end": str(item.get("actual_end", "")),
                    "required_for_parent": bool(
                        item.get("required_for_parent", False)
                    ),
                }
                for item in raw_work_items.get("items", ())
            ),
            "total_count": int(raw_work_items.get("total_count", 0)),
            "offset": int(raw_work_items.get("offset", 0)),
            "limit": int(raw_work_items.get("limit", 50)),
            "has_more": bool(raw_work_items.get("has_more", False)),
            "next_offset": raw_work_items.get("next_offset"),
        }
        timeline, timeline_summary = self._hierarchy_timeline(
            matter_id,
            tuple(detail.get("timeline", ())),
        )
        overview = {
            **dict(detail.get("overview", {})),
            "actions": work_items["items"],
        }
        sections = {
            **dict(detail.get("sections", {})),
            "overview": overview,
            "sub_matters": children_page,
            "timeline": timeline,
            "related_matters": related,
        }
        return {
            **detail,
            "parent": parent,
            "breadcrumb": breadcrumb,
            "path": breadcrumb,
            "children": children_page["items"],
            "sub_matters": children_page,
            "children_page": children_page,
            "children_summary": summary_payload,
            "child_counts": dict(
                (summary or {}).get("child_state_counts", {})
            ),
            "overview": overview,
            "sections": sections,
            "work_items": work_items,
            "timeline": timeline,
            "timeline_summary": timeline_summary,
            "related_matters": related,
        }

    def _root_matter_id(self, matter_id: str) -> str:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        path = self.hierarchy.path(matter_id)
        if not path:
            raise KeyError("Matter hierarchy path is unavailable")
        return str(path[0])

    def _active_temporal_events(
        self,
        rows: Iterable[Mapping[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        if self.browser is None:
            return tuple(dict(row) for row in rows)
        return self.browser.active_temporal_events(rows)

    def _current_situation_graph(
        self,
        *,
        matter_id: str,
    ) -> SituationGraphSnapshot:
        if (
            self.store is None
            or self.browser is None
            or self.hierarchy is None
        ):
            raise RuntimeError("MATTERS_HOME is required for SituationGraph")
        root_matter_id = self._root_matter_id(matter_id)
        descendant_ids, descendant_total = (
            self.store.hierarchy_descendant_ids_page(
                root_matter_id,
                offset=0,
                limit=500,
                current_only=True,
            )
        )
        matter_ids = (root_matter_id, *descendant_ids)
        matter_records = tuple(self.browser.cards(matter_ids))
        matter_id_set = {
            str(item.get("matter_id", ""))
            for item in matter_records
            if str(item.get("matter_id", ""))
        }
        visible_matter_ids = tuple(
            item for item in matter_ids if item in matter_id_set
        )
        containment_edges = tuple(
            asdict(edge)
            for child_id in descendant_ids
            if (
                edge := self.hierarchy.parent_edge(
                    child_id,
                    current_only=True,
                )
            )
            is not None
            and edge.parent_matter_id in matter_id_set
            and edge.child_matter_id in matter_id_set
        )
        work_items, work_item_total = (
            self.store.matter_work_items_for_matters_page(
                visible_matter_ids,
                offset=0,
                limit=500,
            )
        )
        raw_events, event_total = self.store.current_filtered_page(
            "temporal_event",
            json_field="object_ref",
            values=visible_matter_ids,
            offset=0,
            limit=200,
        )
        events = self._active_temporal_events(raw_events)
        relation_rows: dict[str, dict[str, Any]] = {}
        for json_field in ("source_matter_id", "target_matter_id"):
            grouped = self.store.current_by_json_scalar_values(
                "relation_candidate",
                json_field=json_field,
                values=visible_matter_ids,
            )
            for candidates in grouped.values():
                for candidate in candidates:
                    source_id = str(
                        candidate.get("source_matter_id", "")
                    )
                    target_id = str(
                        candidate.get("target_matter_id", "")
                    )
                    if (
                        source_id not in matter_id_set
                        or target_id not in matter_id_set
                    ):
                        continue
                    relation_key = str(
                        candidate.get("relation_id", "")
                    ) or sha256(
                        json.dumps(
                            candidate,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                            default=str,
                        ).encode("utf-8")
                    ).hexdigest()
                    relation_rows[relation_key] = dict(candidate)
        coverage_gaps = []
        if descendant_total > len(descendant_ids):
            coverage_gaps.append("descendant_page_truncated")
        if work_item_total > len(work_items):
            coverage_gaps.append("work_item_page_truncated")
        if event_total > len(raw_events):
            coverage_gaps.append("event_page_truncated")
        if len(events) < len(raw_events):
            coverage_gaps.append("analysis_output_replacement_pending")
        missing_matters = set(matter_ids) - matter_id_set
        if missing_matters:
            coverage_gaps.append("matter_projection_unavailable")
            invalidated_matter_outputs = (
                self.store.invalidated_analysis_output_refs(
                    output_ref
                    for missing_matter_id in missing_matters
                    for output_ref in (
                        f"projection:{missing_matter_id}",
                        f"admission_decision:{missing_matter_id}",
                    )
                )
            )
            if invalidated_matter_outputs:
                coverage_gaps.append(
                    "analysis_output_replacement_pending"
                )
        owner_inputs = {
            "root_matter_id": root_matter_id,
            "matter_records": matter_records,
            "containment_edges": containment_edges,
            "work_items": work_items,
            "events": events,
            "relations": tuple(relation_rows.values()),
            "coverage_gaps": tuple(coverage_gaps),
        }
        owner_input_fingerprint = "sha256:" + sha256(
            json.dumps(
                owner_inputs,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        current_payload = self.store.current(
            "situation_graph_projection",
            root_matter_id,
        )
        if (
            current_payload is not None
            and str(
                current_payload.get("owner_input_fingerprint", "")
            )
            == owner_input_fingerprint
        ):
            current_snapshot = situation_graph_snapshot_from_payload(
                current_payload
            )
            if current_snapshot.effective_currentness() == "current":
                return current_snapshot

        generated_at = datetime.now(timezone.utc)
        snapshot = self.situation_graph_builder.build(
            root_matter_id=root_matter_id,
            matter_records=matter_records,
            containment_edges=containment_edges,
            work_items=work_items,
            events=events,
            relations=tuple(relation_rows.values()),
            generated_at=generated_at,
            expires_at=generated_at + timedelta(hours=24),
            coverage="partial" if coverage_gaps else "complete",
            coverage_gaps=tuple(coverage_gaps),
        )
        snapshot_payload = {
            **asdict(snapshot),
            "owner_input_fingerprint": owner_input_fingerprint,
        }
        stored = self.store.compare_current_and_append(
            "situation_graph_projection",
            root_matter_id,
            is_equivalent=lambda current: bool(
                current
                and str(current.get("input_fingerprint", ""))
                == snapshot.input_fingerprint
                and situation_graph_snapshot_from_payload(
                    current
                ).effective_currentness()
                == "current"
            ),
            payload_factory=lambda _revision, _current: snapshot_payload,
        )
        return situation_graph_snapshot_from_payload(stored["payload"])

    def matter_situation_graph(
        self,
        *,
        matter_id: str,
        locale: str = "en",
        continuation: str = "",
        limit: int = 120,
    ) -> dict[str, Any]:
        self.locale_registry_owner.require(locale)
        graph = self._current_situation_graph(matter_id=matter_id)
        public_graph = project_matter_only_graph(
            graph.page(
                continuation=continuation,
                limit=limit,
            )
        )
        return {
            **public_graph,
            "selected_locale": locale,
            "requested_node_id": matter_id,
        }

    def matter_node_quick_view(
        self,
        *,
        matter_id: str,
        node_id: str,
        locale: str = "en",
    ) -> dict[str, Any]:
        self.locale_registry_owner.require(locale)
        if self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for node quick view")
        graph = self._current_situation_graph(matter_id=matter_id)
        node = next(
            (
                item
                for item in graph.nodes
                if item.node_id == node_id
                and item.node_type in {"matter", "work_item"}
            ),
            None,
        )
        if node is None:
            raise KeyError("Matter or stage graph node is unavailable")
        quick_view = (
            self.browser.node_quick_view(node.node_id, locale=locale)
            if node.node_type == "matter"
            else self.browser.work_item_quick_view(
                node.node_id,
                locale=locale,
            )
        )
        return {
            **quick_view,
            "root_matter_id": graph.root_matter_id,
            "requested_root_matter_id": matter_id,
        }

    def matter_world_model(
        self,
        *,
        matter_id: str,
        locale: str = "en",
        continuation: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        self.locale_registry_owner.require(locale)
        if self.world_model is None:
            raise RuntimeError("MATTERS_HOME is required for World Model")
        graph = self._current_situation_graph(matter_id=matter_id)
        current = self.world_model.current(
            matter_id=graph.root_matter_id,
            expected_graph_fingerprint=graph.input_fingerprint,
        )
        if current is None:
            return {
                "matter_id": graph.root_matter_id,
                "graph_fingerprint": graph.input_fingerprint,
                "advisories": (),
                "total_count": 0,
                "next_continuation": "",
                "has_more": False,
                "coverage": "unknown",
                "coverage_gaps": ("world_model_not_run",),
                "currentness": "pending",
                "selected_locale": locale,
            }
        return {
            **asdict(
                current.page(
                    continuation=continuation,
                    limit=limit,
                    expected_graph_fingerprint=graph.input_fingerprint,
                )
            ),
            "selected_locale": locale,
        }

    def record_world_model_feedback(
        self,
        *,
        matter_id: str,
        advisory_id: str,
        disposition: str,
        observed_at: str,
        observation_statement: str,
        observation_evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Compare a frozen forecast with later licensed evidence.

        This appends advisory feedback only.  A contradictory result queues the
        existing development-owned Model-Miss route; no Matter state is changed.
        """

        if self.world_model is None or self.model_misses is None:
            raise RuntimeError(
                "MATTERS_HOME is required for World Model feedback"
            )
        graph = self._current_situation_graph(matter_id=matter_id)
        evidence_ids = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in observation_evidence_ids
                if str(item).strip()
            )
        )
        if not evidence_ids or not set(evidence_ids).issubset(
            set(graph.evidence_ids)
        ):
            raise ValueError(
                "World Model feedback requires evidence in the current SituationGraph"
            )
        normalized_time = str(observed_at).strip()
        if normalized_time.endswith("Z"):
            normalized_time = normalized_time[:-1] + "+00:00"
        try:
            observed = datetime.fromisoformat(normalized_time)
        except ValueError as exc:
            raise ValueError(
                "observed_at must be an ISO-8601 timestamp"
            ) from exc
        if observed.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return asdict(
            self.world_model.evaluate_prediction(
                matter_id=graph.root_matter_id,
                advisory_id=advisory_id,
                disposition=disposition,
                observed_at=observed,
                observation_statement=observation_statement,
                observation_evidence_ids=evidence_ids,
                observation_graph_fingerprint=graph.input_fingerprint,
                model_miss_owner=self.model_misses,
            )
        )

    def ai_model_contracts(
        self,
        *,
        purpose: str = "",
        related_to: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return the A3 functional map without exposing persistence layout."""

        return self.ai_gateway.list_model_contracts(
            purpose=purpose,
            related_to=related_to,
            offset=offset,
            limit=limit,
        )

    def ai_model_contract(self, *, model_id: str) -> dict[str, Any]:
        """Return one exact functional owner contract."""

        return self.ai_gateway.get_model_contract(model_id)

    def ai_situation_context(
        self,
        *,
        matter_id: str,
        locale: str = "en",
        graph_limit: int = 80,
        world_limit: int = 40,
    ) -> dict[str, Any]:
        """Compose one bounded, modality-aware AI context packet."""

        if graph_limit < 1 or graph_limit > 200:
            raise ValueError("graph_limit is invalid")
        if world_limit < 1 or world_limit > 200:
            raise ValueError("world_limit is invalid")
        detail = self.matter_detail(matter_id=matter_id, locale=locale)
        graph = self.matter_situation_graph(
            matter_id=matter_id,
            locale=locale,
            limit=graph_limit,
        )
        world_model = self.matter_world_model(
            matter_id=matter_id,
            locale=locale,
            limit=world_limit,
        )
        researchguard = {
            **asdict(self.research_status),
            "current": self.research_status.current,
            "sole_real_research_provider": True,
            "legacy_guard_fallback": False,
        }
        gaps = tuple(
            dict.fromkeys(
                (
                    *(
                        str(item)
                        for item in graph.get("coverage_gaps", ())
                        if str(item)
                    ),
                    *(
                        str(item)
                        for item in world_model.get("coverage_gaps", ())
                        if str(item)
                    ),
                    *(
                        ()
                        if self.research_status.current
                        else ("researchguard_not_current",)
                    ),
                )
            )
        )
        context = {
            "artifact_type": "matters.situation-context-packet.v1",
            "contract_revision": AI_GATEWAY_CONTRACT_REVISION,
            "matter_id": matter_id,
            "selected_locale": locale,
            "as_of": {
                "semantic_revision": str(
                    dict(detail.get("matter", {})).get(
                        "semantic_revision",
                        "",
                    )
                ),
                "graph_fingerprint": str(
                    graph.get("input_fingerprint", "")
                ),
                "world_model_currentness": str(
                    world_model.get("currentness", "unknown")
                ),
            },
            "modality_contract": (
                "confirmed_observed",
                "reported",
                "planned",
                "ai_inferred",
            ),
            "matter": detail,
            "situation_graph": graph,
            "world_model": world_model,
            "researchguard": researchguard,
            "gaps": gaps,
            "completeness": "partial" if gaps else "current",
        }
        receipt = self.ai_gateway.record_query_receipt(
            request_kind="situation_context",
            matter_id=matter_id,
            request_shape={
                "locale": locale,
                "graph_limit": graph_limit,
                "world_limit": world_limit,
            },
            result_identity=_fingerprint(context),
        )
        return {**context, "query_receipt": receipt}

    def ai_history(
        self,
        *,
        matter_id: str,
        locale: str = "en",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return bounded human/event and AI-feedback history for one Matter."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for AI history")
        if offset < 0 or limit < 1 or limit > 50:
            raise ValueError("AI history page bounds are invalid")
        detail = self.matter_detail(matter_id=matter_id, locale=locale)
        timeline = tuple(detail.get("timeline", ()))
        timeline_page = timeline[offset : offset + limit]
        observations, observation_total = self.store.current_filtered_page(
            "ai_user_observation",
            json_field="matter_id",
            values=(matter_id,),
            offset=offset,
            limit=limit,
        )
        prediction_feedback, prediction_feedback_total = (
            self.store.current_filtered_page(
                "world_model_feedback",
                json_field="matter_id",
                values=(matter_id,),
                offset=offset,
                limit=limit,
            )
        )
        corrections, correction_total = self.store.current_filtered_page(
            "correction_input",
            json_field="matter_id",
            values=(matter_id,),
            offset=offset,
            limit=limit,
        )
        result = {
            "artifact_type": "matters.ai-history-page.v1",
            "contract_revision": AI_GATEWAY_CONTRACT_REVISION,
            "matter_id": matter_id,
            "selected_locale": locale,
            "timeline": timeline_page,
            "user_observations": observations,
            "prediction_feedback": prediction_feedback,
            "corrections": corrections,
            "offset": offset,
            "limit": limit,
            "totals": {
                "timeline": len(timeline),
                "user_observations": observation_total,
                "prediction_feedback": prediction_feedback_total,
                "corrections": correction_total,
            },
            "has_more": any(
                total > offset + limit
                for total in (
                    len(timeline),
                    observation_total,
                    prediction_feedback_total,
                    correction_total,
                )
            ),
        }
        receipt = self.ai_gateway.record_query_receipt(
            request_kind="bounded_history",
            matter_id=matter_id,
            request_shape={
                "locale": locale,
                "offset": offset,
                "limit": limit,
                "history_classes": (
                    "timeline",
                    "user_observation",
                    "prediction_feedback",
                    "correction",
                ),
            },
            result_identity=_fingerprint(result),
        )
        return {**result, "query_receipt": receipt}

    def record_user_observation(
        self,
        *,
        matter_id: str,
        observation_kind: str,
        statement: str,
        observed_at: str,
        source_ref: str = "",
    ) -> dict[str, Any]:
        """Append a minimized reported clue; do not treat it as correction."""

        return self.ai_gateway.record_user_observation(
            matter_id=matter_id,
            observation_kind=observation_kind,
            statement=statement,
            observed_at=observed_at,
            source_ref=source_ref,
        )

    def pending_ai_feedback(
        self,
        *,
        matter_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Expose the durable A3 inbox that a later A2 run can consume."""

        return self.ai_gateway.pending_user_observations(
            matter_id=matter_id,
            offset=offset,
            limit=limit,
        )

    def _hierarchy_timeline(
        self,
        matter_id: str,
        base_timeline: tuple[Mapping[str, Any], ...],
    ) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
        """Project each current logical Event once across the whole Matter tree."""

        if self.store is None or self.browser is None:
            return tuple(dict(item) for item in base_timeline), {
                "total_count": len(base_timeline),
                "descendant_count": 0,
                "truncated": False,
            }
        descendant_ids, descendant_total = (
            self.store.hierarchy_descendant_ids_page(
                matter_id,
                offset=0,
                limit=500,
                current_only=True,
            )
        )
        matter_ids = (matter_id, *descendant_ids)
        cards = {
            str(item["matter_id"]): item
            for item in self.browser.cards(matter_ids)
        }
        raw_events, event_total = self.store.current_filtered_page(
            "temporal_event",
            json_field="object_ref",
            values=matter_ids,
            offset=0,
            limit=200,
        )
        events = self._active_temporal_events(raw_events)
        items: list[dict[str, Any]] = []
        for event in events:
            owner_id = str(event.get("object_ref", ""))
            item = self.browser.timeline_item(event)
            item["source_level"] = (
                "current_matter"
                if owner_id == matter_id
                else "descendant_matter"
            )
            if owner_id != matter_id:
                item["sub_matter"] = dict(
                    cards.get(owner_id, {}).get(
                        "title",
                        {
                            "en": "Sub-matter",
                            "zh-CN": "子事项",
                        },
                    )
                )
            items.append(item)
        if not raw_events:
            items.extend(
                {
                    **dict(item),
                    "source_level": "current_matter",
                }
                for item in base_timeline
            )
        work_items, work_total = self.store.matter_work_items_for_matters_page(
            matter_ids,
            offset=0,
            limit=200,
        )
        for item in work_items:
            key_time = str(
                item.get("actual_end")
                or item.get("actual_start")
                or item.get("planned_end")
                or item.get("planned_start")
                or ""
            )
            if not key_time:
                continue
            owner_id = str(item.get("matter_id", ""))
            title = item.get("localized_title", {})
            if not isinstance(title, Mapping):
                title = {}
            items.append(
                {
                    "sentence": {
                        "en": str(title.get("en") or "Matter action"),
                        "zh-CN": str(title.get("zh-CN") or "事项行动"),
                    },
                    "claimed_time": key_time,
                    "record_time": "",
                    "modality": (
                        "observed"
                        if str(item.get("status", "")) == "completed"
                        else "planned"
                    ),
                    "confidence": 1.0,
                    "conflict": False,
                    "source_level": (
                        "current_matter"
                        if owner_id == matter_id
                        else "descendant_matter"
                    ),
                    "sub_matter": (
                        dict(
                            cards.get(owner_id, {}).get(
                                "title",
                                {
                                    "en": "Sub-matter",
                                    "zh-CN": "子事项",
                                },
                            )
                        )
                        if owner_id != matter_id
                        else {}
                    ),
                    "work_item_status": str(
                        item.get("status", "uncertain")
                    ),
                }
            )
        items.sort(
            key=lambda item: (
                str(item.get("claimed_time") or item.get("record_time") or ""),
                str(dict(item.get("sentence", {})).get("en", "")),
            ),
            reverse=True,
        )
        projected = tuple(items[:200])
        deduplicated_revision_count = max(0, len(raw_events) - len(events))
        # The reader-facing total belongs to the logical, displayable
        # projection.  Counting active logical revisions before projection can
        # overstate the result when an event is intentionally suppressed as an
        # incomplete/non-displayable row.
        total_count = len(items)
        return projected, {
            "total_count": total_count,
            "descendant_count": descendant_total,
            "deduplicated_revision_count": deduplicated_revision_count,
            "analysis_output_replacement_pending": False,
            "truncated": (
                descendant_total > len(descendant_ids)
                or event_total > len(raw_events)
                or work_total > len(work_items)
                or total_count > len(projected)
            ),
        }

    def matter_children(
        self,
        *,
        matter_id: str,
        locale: str = "en",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.locale_registry_owner.require(locale)
        if self.hierarchy is None or self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        page = self.hierarchy.children_page(
            matter_id,
            offset=offset,
            limit=limit,
        )
        edges = tuple(page["items"])
        cards = {
            str(item["matter_id"]): item
            for item in self.browser.cards(
                str(edge["child_matter_id"]) for edge in edges
            )
        }
        items = []
        for edge in edges:
            child_id = str(edge["child_matter_id"])
            card = cards.get(child_id, {})
            outcome = self.store.current(
                "outcome_decision",
                f"{child_id}:outcome",
            ) or {}
            items.append(
                {
                    **card,
                    "matter_id": child_id,
                    "parent_matter_id": matter_id,
                    "role": str(edge["role"]),
                    "title": dict(
                        card.get(
                            "title",
                            {
                                "en": "Projection pending",
                                "zh-CN": "投影生成中",
                            },
                        )
                    ),
                    "status": str(card.get("state", "uncertain")),
                    "state": str(card.get("state", "uncertain")),
                    "status_group": str(
                        card.get("status_group", "in_progress")
                    ),
                    "key_time": str(card.get("key_time", "")),
                    "latest_result": dict(
                        card.get(
                            "summary",
                            {
                                "en": str(outcome.get("rationale", "")),
                                "zh-CN": str(outcome.get("rationale", "")),
                            },
                        )
                    ),
                    "result_status": str(outcome.get("status", "")),
                    "related_file_count": int(
                        card.get("source_count", 0)
                    ),
                    "file_count": int(card.get("source_count", 0)),
                    "has_children": int(card.get("child_count", 0)) > 0,
                }
            )
        return {
            **page,
            "items": tuple(items),
            "selected_locale": locale,
        }

    def matter_work_items(
        self,
        *,
        matter_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for WorkItems")
        return self.hierarchy.work_items_page(
            matter_id,
            offset=offset,
            limit=limit,
        )

    def attach_matter_child(
        self,
        *,
        parent_matter_id: str,
        child_matter_id: str,
        role: str,
        confidence: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        ordinal: int = 0,
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        return asdict(
            self.hierarchy.attach_child(
                parent_matter_id=parent_matter_id,
                child_matter_id=child_matter_id,
                role=role,
                confidence=confidence,
                rationale=rationale,
                evidence_ids=evidence_ids,
                ordinal=ordinal,
            )
        )

    def attach_matter_children_batch(
        self,
        *,
        parent_matter_id: str,
        attachments: Sequence[Mapping[str, Any]],
        rationale: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        return asdict(
            self.hierarchy.attach_children_batch(
                parent_matter_id=parent_matter_id,
                attachments=tuple(
                    MatterChildAttachment(
                        child_matter_id=str(item["child_matter_id"]),
                        role=str(item["role"]),
                        confidence=str(item["confidence"]),
                        rationale=str(item["rationale"]),
                        evidence_ids=tuple(
                            str(value)
                            for value in item.get("evidence_ids", ())
                        ),
                        ordinal=int(item.get("ordinal", 0)),
                    )
                    for item in attachments
                ),
                rationale=rationale,
                evidence_ids=evidence_ids,
            )
        )

    def compose_parent_matter(
        self,
        *,
        semantic_identity_key: str,
        localized_title: Mapping[str, str],
        localized_summary: Mapping[str, str],
        state: str,
        topic_type: str,
        localized_topic_type: Mapping[str, str],
        hero_theme_concepts: Sequence[str] = (),
        attachments: Sequence[Mapping[str, Any]],
        rationale: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Compose one evidence-bounded parent and attach current child Matters."""

        if (
            self.store is None
            or self.coverage_ledger is None
            or self.hierarchy is None
            or self.activity is None
            or self.heroes is None
        ):
            raise RuntimeError("MATTERS_HOME is required for parent composition")
        locales = set(self.locale_registry_owner.available_locales)
        if set(localized_title) != locales or set(localized_summary) != locales:
            raise ValueError("parent title and summary require every locale")
        if set(localized_topic_type) != locales:
            raise ValueError("parent topic type requires every locale")
        if any(
            not str(values[locale]).strip()
            for values in (
                localized_title,
                localized_summary,
                localized_topic_type,
            )
            for locale in locales
        ):
            raise ValueError("parent localized values cannot be empty")
        normalized_attachments = tuple(dict(item) for item in attachments)
        if len(normalized_attachments) < 2:
            raise ValueError("a composed parent requires at least two children")
        child_ids = tuple(
            str(item.get("child_matter_id", "")).strip()
            for item in normalized_attachments
        )
        if any(not child_id for child_id in child_ids):
            raise ValueError("parent attachment requires child Matter ids")
        if len(set(child_ids)) != len(child_ids):
            raise ValueError("parent attachment children must be unique")

        child_admissions: list[Mapping[str, Any]] = []
        available_evidence: list[str] = []
        source_ids: list[str] = []
        for child_id in child_ids:
            decision = self.store.current("admission_decision", child_id) or {}
            matter = decision.get("matter")
            if (
                str(decision.get("status", "")) != "admitted"
                or not isinstance(matter, Mapping)
                or self.store.current("projection", child_id) is None
            ):
                raise KeyError(
                    f"current admitted child Matter is unavailable: {child_id}"
                )
            child_admissions.append(matter)
            source_ids.extend(
                str(item)
                for item in matter.get("source_ids", ())
                if str(item)
            )
            child_evidence = tuple(
                str(item)
                for item in matter.get("evidence_ids", ())
                if str(item)
            )
            available_evidence.extend(child_evidence)
        available_evidence_ids = tuple(dict.fromkeys(available_evidence))
        selected_evidence_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    evidence_ids
                    or tuple(
                        next(
                            (
                                str(value)
                                for value in matter.get("evidence_ids", ())
                                if str(value)
                            ),
                            "",
                        )
                        for matter in child_admissions
                    )
                )
                if str(item)
            )
        )
        if (
            not selected_evidence_ids
            or not set(selected_evidence_ids).issubset(
                available_evidence_ids
            )
        ):
            raise ValueError(
                "parent evidence must be a non-empty subset of child evidence"
            )
        decision = self.admission.decide(
            AdmissionPacket(
                source_ids=tuple(dict.fromkeys(source_ids)),
                evidence_ids=selected_evidence_ids,
                explicit_goal_or_obligation=True,
                semantic_identity_key=semantic_identity_key,
            )
        )
        if decision.status != "admitted" or decision.matter is None:
            raise ValueError("parent composition did not produce an admitted Matter")
        matter_id = decision.matter.matter_id
        if matter_id in child_ids:
            raise ValueError("parent semantic identity aliases a child Matter")
        semantic_revision = (
            "parent-composition:"
            + sha256(
                json.dumps(
                    {
                        "semantic_identity_key": semantic_identity_key,
                        "localized_title": dict(localized_title),
                        "localized_summary": dict(localized_summary),
                        "state": state,
                        "topic_type": topic_type,
                        "children": child_ids,
                        "evidence_ids": selected_evidence_ids,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
        )
        prepared_attachments = tuple(
            MatterChildAttachment(
                child_matter_id=child_id,
                role=str(item.get("role", "optional")),
                confidence=str(item.get("confidence", "bounded")),
                rationale=str(item.get("rationale", rationale)),
                evidence_ids=tuple(
                    str(value)
                    for value in item.get("evidence_ids", ())
                    if str(value)
                ),
                ordinal=int(item.get("ordinal", index)),
            )
            for index, (child_id, item) in enumerate(
                zip(child_ids, normalized_attachments, strict=True)
            )
        )
        supplemental_payload = {
            "matter_id": matter_id,
            "semantic_revision": semantic_revision,
            "items": (),
            "status": "pending",
        }
        with self.store.immediate_transaction():
            self.store.compare_current_and_append(
                "admission_decision",
                matter_id,
                is_equivalent=lambda current: current == asdict(decision),
                payload_factory=lambda _revision, _current: asdict(decision),
            )
            projection = self.projections.publish(
                matter_id=matter_id,
                semantic_revision=semantic_revision,
                state=state,
                rationale=str(localized_summary["en"]),
                evidence_ids=selected_evidence_ids,
                localized_values=localized_title,
                localized_rationale=localized_summary,
            )
            projection_payload = asdict(projection)
            self.store.compare_current_and_append(
                "projection",
                matter_id,
                is_equivalent=lambda current: current == projection_payload,
                payload_factory=lambda _revision, _current: projection_payload,
            )
            classification = {
                "matter_id": matter_id,
                "semantic_revision": semantic_revision,
                "topic_types": (
                    {
                        "value": " ".join(topic_type.casefold().split()),
                        "label": {
                            locale: str(localized_topic_type[locale]).strip()
                            for locale in self.locale_registry_owner.available_locales
                        },
                    },
                ),
                "evidence_ids": selected_evidence_ids,
                "freshness": "current",
            }
            self.store.compare_current_and_append(
                "matter_classification",
                matter_id,
                is_equivalent=lambda current: current == classification,
                payload_factory=lambda _revision, _current: classification,
            )
            self.coverage_ledger.register_matters(
                matters=(
                    {
                        "matter_id": matter_id,
                        "matter_kind": "root_matter",
                        "semantic_revision": semantic_revision,
                        "hierarchy_revision": "parent-composition",
                    },
                ),
                refresh_summary=False,
            )
            revision = self.hierarchy.attach_children_batch(
                parent_matter_id=matter_id,
                attachments=prepared_attachments,
                rationale=rationale,
                evidence_ids=selected_evidence_ids,
            )
            activity = self.activity.refresh_parent_from_descendants(
                parent_matter_id=matter_id,
                descendant_matter_ids=child_ids,
            )
            self.store.compare_current_and_append(
                "matter_supplemental_information",
                matter_id,
                is_equivalent=lambda current: current
                == supplemental_payload,
                payload_factory=lambda _revision, _current: supplemental_payload,
            )
        hierarchy_projection = self.store.current(
            "matter_hierarchy_projection",
            matter_id,
        ) or {}
        topic_words: list[str] = []
        for word in " ".join(topic_type.split()).split():
            candidate = " ".join((*topic_words, word))
            if len(candidate) > 20 or len(topic_words) == 2:
                break
            topic_words.append(word)
        topic_prefix = " ".join(topic_words) or "matter"
        hero_themes = tuple(
            dict.fromkeys(
                " ".join(str(item).strip().split())
                for item in hero_theme_concepts
                if str(item).strip()
            )
        ) or (
            f"{topic_prefix} real-world activity scene",
        )
        hero = self.heroes.prepare(
            HeroSubject(
                object_id=matter_id,
                object_kind="matter",
                semantic_identity_id=decision.matter.semantic_identity_id,
                topic_concepts=(topic_type,),
                theme_concepts=hero_themes,
                hierarchy_revision=str(
                    hierarchy_projection.get(
                        "input_fingerprint",
                        semantic_revision,
                    )
                ),
                is_root=True,
                independently_openable=True,
            )
        )
        for stage_id, status, output_ref in (
            ("localization", "current", f"projection:{matter_id}"),
            (
                "meaningful_clue_summary",
                "current" if activity is not None else "no_finding",
                (
                    f"matter_activity:{matter_id}"
                    if activity is not None
                    else "matter_activity:no_finding"
                ),
            ),
            (
                "generated_hero",
                (
                    "current"
                    if hero.status == "generated_current"
                    else "pending"
                ),
                f"generated_hero_record:{matter_id}",
            ),
            (
                "supplemental_information",
                "pending",
                f"matter_supplemental_information:{matter_id}",
            ),
            ("ui_projection", "pending", f"projection:{matter_id}"),
            ("ui_reachable", "pending", f"object_browser:{matter_id}"),
        ):
            self.coverage_ledger.mark_stage(
                object_id=matter_id,
                stage_id=stage_id,
                status=status,
                input_fingerprint=semantic_revision,
                output_ref=output_ref,
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
        self.coverage_ledger.refresh_summary()
        return {
            "matter_id": matter_id,
            "semantic_revision": semantic_revision,
            "hierarchy_revision_id": revision.revision_id,
            "child_count": len(child_ids),
            "activity_status": "current" if activity is not None else "no_finding",
            "hero_status": hero.status,
        }

    def rebase_empty_supplemental_information(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Move legacy empty/current supplemental rows back to pending.

        An empty supplemental projection is a work queue entry, not evidence
        that research completed.  This bounded, restart-safe repair keeps the
        coverage ledger truthful without copying or rewriting source content.
        """

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError(
                "MATTERS_HOME is required for supplemental reconciliation"
            )
        if limit <= 0:
            raise ValueError("limit must be positive")
        rows = tuple(
            row
            for row in self.store.list_current(
                "matter_supplemental_information"
            )
            if str(row.get("matter_id", "")) > after_matter_id
        )
        page = rows[:limit]
        repaired_count = 0
        already_pending_count = 0
        explicit_disposition_count = 0
        nonempty_count = 0
        items: list[dict[str, str]] = []
        for row in page:
            matter_id = str(row.get("matter_id", "")).strip()
            status = str(row.get("status", "")).strip()
            supplemental_items = tuple(row.get("items", ()))
            if supplemental_items:
                nonempty_count += 1
                disposition = "nonempty_unchanged"
            elif status == "pending":
                already_pending_count += 1
                disposition = "already_pending"
            elif status in {
                "blocked",
                "unavailable",
                "stale",
                "not_applicable",
            }:
                explicit_disposition_count += 1
                disposition = f"explicit_{status}_unchanged"
            else:
                repaired = {
                    **dict(row),
                    "matter_id": matter_id,
                    "items": (),
                    "status": "pending",
                }
                self.store.append_next(
                    "matter_supplemental_information",
                    matter_id,
                    repaired,
                )
                input_fingerprint = str(
                    row.get("semantic_revision", "")
                ).strip() or f"supplemental-rebase:{matter_id}"
                for coverage_row in self._coverage_rows_for_matter(
                    matter_id
                ):
                    self.coverage_ledger.mark_stage(
                        object_id=str(coverage_row["object_id"]),
                        stage_id="supplemental_information",
                        status="pending",
                        input_fingerprint=input_fingerprint,
                        output_ref=(
                            "matter_supplemental_information:"
                            f"{matter_id}"
                        ),
                        matter_ids=tuple(
                            str(item)
                            for item in coverage_row.get(
                                "matter_ids",
                                (matter_id,),
                            )
                        ),
                        refresh_summary=False,
                    )
                repaired_count += 1
                disposition = "repaired_to_pending"
            items.append(
                {
                    "matter_id": matter_id,
                    "disposition": disposition,
                }
            )
        if repaired_count:
            self.coverage_ledger.refresh_summary()
        has_more = len(rows) > len(page)
        next_cursor = (
            str(page[-1].get("matter_id", ""))
            if page and has_more
            else ""
        )
        return {
            "scanned_matter_count": len(page),
            "repaired_count": repaired_count,
            "already_pending_count": already_pending_count,
            "explicit_disposition_count": explicit_disposition_count,
            "nonempty_count": nonempty_count,
            "items": tuple(items),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def queue_eligible_supplemental_research(
        self,
        *,
        after_matter_id: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Disposition one admitted Matter page and queue eligible A1 work.

        Only root Matters with a current bilingual projection are research
        eligible.  Descendants receive an explicit ``not_applicable``
        disposition because their context is inherited from the root Matter.
        Missing prerequisites and an unavailable ResearchGuard remain visible;
        an empty projection is never reported current.
        """

        if (
            self.store is None
            or self.hierarchy is None
            or self.coverage_ledger is None
        ):
            raise RuntimeError(
                "MATTERS_HOME is required for supplemental research queuing"
            )
        if limit < 1 or limit > 500:
            raise ValueError("supplemental research queue limit is invalid")

        rows, has_more = self.store.canonical_matter_presentation_page(
            after_matter_id=after_matter_id,
            limit=limit,
        )
        queued_count = 0
        current_count = 0
        not_applicable_count = 0
        unavailable_count = 0
        blocked_count = 0
        unchanged_count = 0
        changed = False
        items: list[dict[str, str]] = []

        for row in rows:
            matter_id = str(row["matter_id"])
            projection = row.get("projection")
            semantic_revision = (
                str(
                    projection.get("semantic_revision", "")
                    if isinstance(projection, Mapping)
                    else ""
                ).strip()
                or f"supplemental-queue:{matter_id}"
            )
            current_payload = self.store.current(
                "matter_supplemental_information",
                matter_id,
            ) or {}
            current_items = tuple(current_payload.get("items", ()))
            current_usable_items = tuple(
                item
                for item in current_items
                if isinstance(item, Mapping)
                and str(item.get("freshness", "current")).strip().casefold()
                == "current"
                and str(current_payload.get("status", "")).strip().casefold()
                == "current"
            )
            parent = self.hierarchy.parent_edge(
                matter_id,
                current_only=True,
            )
            package_id = ""

            if current_usable_items:
                disposition = "current_nonempty"
                status = "current"
                current_count += 1
                desired_payload = dict(current_payload)
            elif parent is not None:
                disposition = "descendant_not_applicable"
                status = "not_applicable"
                not_applicable_count += 1
                desired_payload = {
                    "matter_id": matter_id,
                    "semantic_revision": semantic_revision,
                    "items": [],
                    "status": status,
                    "disposition_reason": disposition,
                    "provider_gate": {
                        "provider_id": "researchguard",
                        "status": "not_applicable",
                    },
                }
            elif (
                not isinstance(projection, Mapping)
                or str(projection.get("equivalence_status", ""))
                != "equivalent"
            ):
                disposition = "current_bilingual_projection_unavailable"
                status = "blocked"
                blocked_count += 1
                desired_payload = {
                    "matter_id": matter_id,
                    "semantic_revision": semantic_revision,
                    "items": list(current_items),
                    "status": status,
                    "disposition_reason": disposition,
                    "provider_gate": {
                        "provider_id": "researchguard",
                        "status": "not_started",
                    },
                }
            else:
                queued = self.queue_research_operation(matter_id)
                package_id = str(
                    dict(queued.get("package", {})).get("package_id", "")
                )
                provider_gate = dict(queued.get("provider_gate", {}))
                operation_status = str(queued.get("status", "queued"))
                if not bool(self.research_status.current):
                    disposition = "researchguard_unavailable"
                    status = "unavailable"
                    unavailable_count += 1
                elif operation_status == "blocked":
                    disposition = "research_operation_blocked"
                    status = "blocked"
                    blocked_count += 1
                elif operation_status == "passed":
                    disposition = "research_completed_without_current_items"
                    status = "unavailable"
                    unavailable_count += 1
                else:
                    disposition = "research_queued"
                    status = "pending"
                    queued_count += 1
                desired_payload = {
                    "matter_id": matter_id,
                    "semantic_revision": semantic_revision,
                    "items": list(current_items),
                    "status": status,
                    "disposition_reason": disposition,
                    "provider_gate": provider_gate,
                    "research_package_id": package_id,
                }

            stored = self.store.compare_current_and_append(
                "matter_supplemental_information",
                matter_id,
                is_equivalent=lambda current, desired=desired_payload: (
                    current == desired
                ),
                payload_factory=lambda _revision, _current, desired=desired_payload: (
                    desired
                ),
            )
            changed |= str(stored.get("status", "")) == "appended"
            if str(stored.get("status", "")) == "current":
                unchanged_count += 1

            input_fingerprint = _fingerprint(
                {
                    "matter_id": matter_id,
                    "semantic_revision": semantic_revision,
                    "status": status,
                    "disposition": disposition,
                    "research_package_id": package_id,
                    "provider_status": self.research_status.status,
                    "parent_matter_id": (
                        parent.parent_matter_id if parent is not None else ""
                    ),
                }
            )
            for coverage_row in self._coverage_rows_for_matter(matter_id):
                self.coverage_ledger.mark_stage(
                    object_id=str(coverage_row["object_id"]),
                    stage_id="supplemental_information",
                    status=status,
                    input_fingerprint=input_fingerprint,
                    output_ref=(
                        f"matter_supplemental_information:{matter_id}"
                    ),
                    matter_ids=tuple(
                        str(item)
                        for item in coverage_row.get(
                            "matter_ids",
                            (matter_id,),
                        )
                    ),
                    failure_class=(
                        disposition
                        if status in {"blocked", "unavailable"}
                        else ""
                    ),
                    refresh_summary=False,
                )
            items.append(
                {
                    "matter_id": matter_id,
                    "status": status,
                    "disposition": disposition,
                    "research_package_id": package_id,
                }
            )

        if rows:
            self.coverage_ledger.refresh_summary()
        next_cursor = (
            str(rows[-1]["matter_id"])
            if rows and has_more
            else ""
        )
        return {
            "scanned_matter_count": len(rows),
            "queued_count": queued_count,
            "current_count": current_count,
            "not_applicable_count": not_applicable_count,
            "unavailable_count": unavailable_count,
            "blocked_count": blocked_count,
            "unchanged_count": unchanged_count,
            "changed": changed,
            "items": tuple(items),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "status": "partial" if has_more else "current",
        }

    def refresh_parent_matter_summary(
        self,
        *,
        matter_id: str,
        localized_summary: Mapping[str, str],
        evidence_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Refresh a parent overview without changing its world-state activity."""

        if (
            self.store is None
            or self.coverage_ledger is None
            or self.hierarchy is None
        ):
            raise RuntimeError("MATTERS_HOME is required for parent summary refresh")
        locales = set(self.locale_registry_owner.available_locales)
        if set(localized_summary) != locales or any(
            not str(localized_summary[locale]).strip() for locale in locales
        ):
            raise ValueError("parent summary requires every non-empty locale")
        projection = self.store.current("projection", matter_id) or {}
        admission = self.store.current("admission_decision", matter_id) or {}
        matter = admission.get("matter")
        if (
            str(admission.get("status", "")) != "admitted"
            or not isinstance(matter, Mapping)
            or str(projection.get("equivalence_status", "")) != "equivalent"
        ):
            raise KeyError("current admitted parent projection is unavailable")
        children = self.hierarchy.children_page(
            matter_id,
            offset=0,
            limit=100,
        )
        if children["has_more"] or int(children["total_count"]) < 2:
            raise ValueError("summary refresh requires one bounded parent hierarchy")
        child_ids = tuple(
            str(item["child_matter_id"]) for item in children["items"]
        )
        child_projections = self.store.current_many("projection", child_ids)
        if set(child_projections) != set(child_ids):
            raise KeyError("current child projection is unavailable")
        selected_evidence_ids = tuple(
            dict.fromkeys(str(item) for item in evidence_ids if str(item))
        )
        parent_evidence = {
            str(item) for item in matter.get("evidence_ids", ()) if str(item)
        }
        child_evidence = {
            str(item)
            for child_projection in child_projections.values()
            for item in child_projection.get("evidence_ids", ())
            if str(item)
        }
        licensed_summary_evidence = parent_evidence | child_evidence
        if (
            not selected_evidence_ids
            or not set(selected_evidence_ids).issubset(
                licensed_summary_evidence
            )
        ):
            raise ValueError(
                "parent summary evidence must be a non-empty current parent "
                "or child projection evidence subset"
            )
        title = {
            locale: str(
                dict(projection.get("localized_values", {})).get(locale, "")
            ).strip()
            for locale in self.locale_registry_owner.available_locales
        }
        if not all(title.values()):
            raise ValueError("current parent title is not bilingual")
        state = str(projection.get("state", "")).strip()
        if not state:
            raise ValueError("current parent state is missing")
        prior_semantic_revision = str(
            projection.get("semantic_revision", "")
        )
        semantic_revision = (
            "parent-summary:"
            + sha256(
                json.dumps(
                    {
                        "matter_id": matter_id,
                        "prior_semantic_revision": prior_semantic_revision,
                        "child_semantic_revisions": {
                            child_id: str(
                                child_projections[child_id].get(
                                    "semantic_revision",
                                    "",
                                )
                            )
                            for child_id in sorted(child_ids)
                        },
                        "localized_summary": {
                            locale: str(localized_summary[locale]).strip()
                            for locale in sorted(locales)
                        },
                        "evidence_ids": selected_evidence_ids,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
        )
        updated_projection = asdict(
            self.projections.publish(
                matter_id=matter_id,
                semantic_revision=semantic_revision,
                state=state,
                rationale=str(localized_summary["en"]).strip(),
                evidence_ids=selected_evidence_ids,
                localized_values=title,
                localized_rationale={
                    locale: str(localized_summary[locale]).strip()
                    for locale in self.locale_registry_owner.available_locales
                },
            )
        )
        current_summary = dict(
            projection.get("localized_rationale", {})
        )
        if (
            current_summary
            == dict(updated_projection["localized_rationale"])
            and tuple(projection.get("evidence_ids", ()))
            == selected_evidence_ids
        ):
            return {
                "matter_id": matter_id,
                "semantic_revision": prior_semantic_revision,
                "updated": False,
                "child_count": len(child_ids),
            }
        revision_payload = {
            "matter_id": matter_id,
            "prior_semantic_revision": prior_semantic_revision,
            "semantic_revision": semantic_revision,
            "child_matter_ids": child_ids,
            "child_semantic_revisions": {
                child_id: str(
                    child_projections[child_id].get(
                        "semantic_revision",
                        "",
                    )
                )
                for child_id in sorted(child_ids)
            },
            "evidence_ids": selected_evidence_ids,
            "localized_summary": dict(
                updated_projection["localized_rationale"]
            ),
            "activity_time_changed": False,
            "hero_identity_changed": False,
            "status": "current",
        }
        with self.store.immediate_transaction():
            self.store.compare_current_and_append(
                "projection",
                matter_id,
                is_equivalent=lambda current: current == updated_projection,
                payload_factory=lambda _revision, _current: updated_projection,
            )
            self.store.compare_current_and_append(
                "matter_narrative_revision",
                matter_id,
                is_equivalent=lambda current: current == revision_payload,
                payload_factory=lambda _revision, _current: revision_payload,
            )
        for row in self._coverage_rows_for_matter(matter_id):
            object_id = str(row["object_id"])
            for stage_id, output_ref in (
                ("localization", f"projection:{matter_id}"),
                (
                    "meaningful_clue_summary",
                    f"matter_narrative_revision:{matter_id}",
                ),
                ("ui_projection", f"projection:{matter_id}"),
                ("ui_reachable", f"object_browser:{matter_id}"),
            ):
                self.coverage_ledger.mark_stage(
                    object_id=object_id,
                    stage_id=stage_id,
                    status="current",
                    input_fingerprint=semantic_revision,
                    output_ref=output_ref,
                    matter_ids=(matter_id,),
                    refresh_summary=False,
                )
        self.coverage_ledger.refresh_summary()
        return {
            "matter_id": matter_id,
            "semantic_revision": semantic_revision,
            "updated": True,
            "child_count": len(child_ids),
        }

    def merge_same_matter(
        self,
        *,
        source_matter_id: str,
        target_matter_id: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        _in_transaction: bool = False,
    ) -> dict[str, Any]:
        """Merge a duplicate admitted Matter through complete owner dispositions."""

        if (
            self.store is None
            or self.hierarchy is None
            or self.dispatcher is None
            or self.coverage_ledger is None
            or self.activity is None
        ):
            raise RuntimeError("MATTERS_HOME is required for Matter merge")
        if (
            not source_matter_id
            or not target_matter_id
            or source_matter_id == target_matter_id
        ):
            raise ValueError("distinct source and target Matters are required")
        if not _in_transaction:
            with self.store.immediate_transaction():
                return self.merge_same_matter(
                    source_matter_id=source_matter_id,
                    target_matter_id=target_matter_id,
                    rationale=rationale,
                    evidence_ids=evidence_ids,
                    _in_transaction=True,
                )
        source_decision = self.store.current(
            "admission_decision",
            source_matter_id,
        ) or {}
        target_decision = self.store.current(
            "admission_decision",
            target_matter_id,
        ) or {}
        source_matter = source_decision.get("matter")
        target_matter = target_decision.get("matter")
        if (
            str(source_decision.get("status", "")) == "merged"
            and str(source_decision.get("canonical_matter_id", ""))
            == target_matter_id
        ):
            canonicalization = self.store.current(
                "matter_canonicalization",
                source_matter_id,
            ) or {}
            return {
                "source_matter_id": source_matter_id,
                "canonical_matter_id": target_matter_id,
                "hierarchy_revision_id": str(
                    canonicalization.get("hierarchy_revision_id", "")
                ),
                "disposition_count": 0,
                "coverage_row_count": 0,
                "activity_status": (
                    "current"
                    if self.store.current(
                        "matter_activity",
                        target_matter_id,
                    )
                    is not None
                    else "no_finding"
                ),
                "hierarchy_pointer_count": int(
                    self._retire_canonicalized_hierarchy_authority(
                        source_matter_id
                    )["retired_pointer_count"]
                ),
                "idempotent": True,
            }
        if (
            str(source_decision.get("status", "")) != "admitted"
            or str(target_decision.get("status", "")) != "admitted"
            or not isinstance(source_matter, Mapping)
            or not isinstance(target_matter, Mapping)
        ):
            raise ValueError("same-Matter merge requires two admitted Matters")
        available_evidence = tuple(
            dict.fromkeys(
                (
                    *tuple(source_matter.get("evidence_ids", ())),
                    *tuple(target_matter.get("evidence_ids", ())),
                )
            )
        )
        normalized_evidence = tuple(
            dict.fromkeys(str(item) for item in evidence_ids if str(item))
        )
        if (
            not normalized_evidence
            or not set(normalized_evidence).issubset(available_evidence)
        ):
            raise ValueError("merge evidence must come from the two Matters")
        source_members = self.hierarchy._member_inventory(
            (source_matter_id,)
        )
        target_members = self.hierarchy._member_inventory(
            (target_matter_id,)
        )
        dispositions = tuple(
            {
                "member_kind": kind,
                "member_id": member_id,
                "action": (
                    "move"
                    if (kind, member_id) in source_members
                    else "retain"
                ),
                "target_matter_ids": (target_matter_id,),
                "evidence_ids": normalized_evidence,
            }
            for kind, member_id in sorted(
                source_members | target_members
            )
        )
        revision = self.record_matter_split_or_merge(
            change_kind="merge",
            subject_matter_ids=(
                source_matter_id,
                target_matter_id,
            ),
            rationale=rationale,
            evidence_ids=normalized_evidence,
            dispositions=dispositions,
        )
        moved_target_decision = self.store.current(
            "admission_decision",
            target_matter_id,
        ) or target_decision
        moved_target_matter = dict(
            moved_target_decision.get("matter", target_matter)
        )
        moved_target_matter["evidence_ids"] = tuple(
            dict.fromkeys(
                (
                    *tuple(target_matter.get("evidence_ids", ())),
                    *tuple(source_matter.get("evidence_ids", ())),
                )
            )
        )
        self.store.append_next(
            "admission_decision",
            target_matter_id,
            {
                **moved_target_decision,
                "matter": moved_target_matter,
            },
        )
        self.admission.restore(Matter(**moved_target_matter))
        moved_source_decision = self.store.current(
            "admission_decision",
            source_matter_id,
        ) or source_decision
        self.store.append_next(
            "admission_decision",
            source_matter_id,
            {
                **moved_source_decision,
                "status": "merged",
                "rationale": rationale,
                "canonical_matter_id": target_matter_id,
            },
        )
        canonicalization = {
            "source_matter_id": source_matter_id,
            "canonical_matter_id": target_matter_id,
            "disposition": "merged_same_matter",
            "hierarchy_revision_id": revision["revision_id"],
            "rationale": rationale,
            "evidence_ids": normalized_evidence,
            "status": "current",
        }
        self.store.compare_current_and_append(
            "matter_canonicalization",
            source_matter_id,
            is_equivalent=lambda current: current == canonicalization,
            payload_factory=lambda _revision, _current: canonicalization,
        )
        coverage_rows = self.coverage_ledger.replace_matter_reference(
            source_matter_id=source_matter_id,
            target_matter_id=target_matter_id,
            refresh_summary=False,
        )
        hierarchy_cleanup = (
            self._retire_canonicalized_hierarchy_authority(
                source_matter_id
            )
        )
        activity = self.activity.refresh_parent_from_descendants(
            parent_matter_id=target_matter_id,
            descendant_matter_ids=(source_matter_id, target_matter_id),
        )
        self.coverage_ledger.refresh_summary()
        return {
            "source_matter_id": source_matter_id,
            "canonical_matter_id": target_matter_id,
            "hierarchy_revision_id": revision["revision_id"],
            "disposition_count": len(dispositions),
            "coverage_row_count": len(coverage_rows),
            "hierarchy_pointer_count": int(
                hierarchy_cleanup["retired_pointer_count"]
            ),
            "activity_status": "current" if activity is not None else "no_finding",
            "idempotent": False,
        }

    def append_candidate_to_matter(
        self,
        *,
        candidate_id: str,
        target_matter_id: str,
        materialization: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        _in_transaction: bool = False,
    ) -> dict[str, Any]:
        """Append one non-independent candidate to its canonical Matter."""

        if (
            self.store is None
            or self.hierarchy is None
            or self.coverage_ledger is None
            or self.activity is None
        ):
            raise RuntimeError("MATTERS_HOME is required for candidate append")
        if materialization not in {"event_update", "work_item"}:
            raise ValueError("unsupported candidate materialization")
        if not _in_transaction:
            with self.store.immediate_transaction():
                return self.append_candidate_to_matter(
                    candidate_id=candidate_id,
                    target_matter_id=target_matter_id,
                    materialization=materialization,
                    rationale=rationale,
                    evidence_ids=evidence_ids,
                    _in_transaction=True,
                )
        candidate_decision = self.store.current(
            "admission_decision",
            candidate_id,
        ) or {}
        candidate = candidate_decision.get("candidate")
        target_decision = self.store.current(
            "admission_decision",
            target_matter_id,
        ) or {}
        target_matter = target_decision.get("matter")
        if (
            str(candidate_decision.get("status", "")) == "appended"
            and str(candidate_decision.get("canonical_matter_id", ""))
            == target_matter_id
        ):
            canonicalization = self.store.current(
                "matter_canonicalization",
                candidate_id,
            ) or {}
            if str(canonicalization.get("disposition", "")) != (
                f"appended_as_{materialization}"
            ):
                raise ValueError(
                    "candidate was appended with a different materialization"
                )
            return {
                "candidate_id": candidate_id,
                "canonical_matter_id": target_matter_id,
                "materialization": materialization,
                "moved_event_count": 0,
                "coverage_row_count": 0,
                "hierarchy_pointer_count": int(
                    self._retire_canonicalized_hierarchy_authority(
                        candidate_id
                    )["retired_pointer_count"]
                ),
                "idempotent": True,
            }
        if (
            str(candidate_decision.get("status", "")) != "uncertain"
            or not isinstance(candidate, Mapping)
            or str(target_decision.get("status", "")) != "admitted"
            or not isinstance(target_matter, Mapping)
        ):
            raise ValueError(
                "candidate append requires an uncertain candidate and admitted target"
            )
        available_evidence = tuple(
            dict.fromkeys(
                (
                    *tuple(candidate.get("evidence_ids", ())),
                    *tuple(target_matter.get("evidence_ids", ())),
                )
            )
        )
        normalized_evidence = tuple(
            dict.fromkeys(str(item) for item in evidence_ids if str(item))
        )
        if (
            not normalized_evidence
            or not set(normalized_evidence).issubset(available_evidence)
        ):
            raise ValueError("append evidence must come from candidate or target")
        updated_matter = dict(target_matter)
        updated_matter["source_ids"] = tuple(
            dict.fromkeys(
                (
                    *tuple(target_matter.get("source_ids", ())),
                    *tuple(candidate.get("source_ids", ())),
                )
            )
        )
        updated_matter["evidence_ids"] = tuple(
            dict.fromkeys(
                (
                    *tuple(target_matter.get("evidence_ids", ())),
                    *tuple(candidate.get("evidence_ids", ())),
                )
            )
        )
        self.store.append_next(
            "admission_decision",
            target_matter_id,
            {**target_decision, "matter": updated_matter},
        )
        self.admission.restore(Matter(**updated_matter))
        candidate_projection = self.store.current(
            "projection",
            candidate_id,
        ) or {}
        target_projection = self.store.current(
            "projection",
            target_matter_id,
        ) or {}
        moved_events: list[Mapping[str, Any]] = []
        for event in self._active_temporal_events(
            self.store.iter_current("temporal_event")
        ):
            if str(event.get("object_ref", "")) != candidate_id:
                continue
            moved = {**event, "object_ref": target_matter_id}
            self.store.append_next(
                "temporal_event",
                str(event["event_id"]),
                moved,
            )
            moved_events.append(moved)
        if materialization == "work_item":
            self.hierarchy.save_work_item(
                MatterWorkItem(
                    item_id=(
                        "work-item:"
                        + sha256(
                            f"{candidate_id}\0{target_matter_id}".encode(
                                "utf-8"
                            )
                        ).hexdigest()[:24]
                    ),
                    matter_id=target_matter_id,
                    kind="action",
                    status="planned",
                    localized_title=dict(
                        candidate_projection.get("localized_values", {})
                    ),
                    localized_result=dict(
                        candidate_projection.get(
                            "localized_rationale",
                            candidate_projection.get("localized_values", {}),
                        )
                    ),
                    evidence_ids=normalized_evidence,
                    source_ids=tuple(candidate.get("source_ids", ())),
                )
            )
        elif target_projection and candidate_projection:
            semantic_revision = (
                "candidate-append:"
                + sha256(
                    f"{candidate_id}\0{target_matter_id}".encode("utf-8")
                ).hexdigest()
            )
            projection = self.projections.publish(
                matter_id=target_matter_id,
                semantic_revision=semantic_revision,
                state=str(
                    candidate_projection.get(
                        "state",
                        target_projection.get("state", "in_progress"),
                    )
                ),
                rationale=str(
                    dict(
                        candidate_projection.get(
                            "localized_rationale",
                            {},
                        )
                    ).get("en", rationale)
                ),
                evidence_ids=updated_matter["evidence_ids"],
                localized_values=dict(
                    target_projection.get("localized_values", {})
                ),
                localized_rationale=dict(
                    candidate_projection.get(
                        "localized_rationale",
                        target_projection.get("localized_rationale", {}),
                    )
                ),
            )
            self.store.append_next(
                "projection",
                target_matter_id,
                asdict(projection),
            )
        timed_events = tuple(
            event
            for event in moved_events
            if str(
                event.get("claimed_time")
                or event.get("record_time")
                or ""
            ).strip()
        )
        if timed_events and candidate_projection:
            latest = max(
                timed_events,
                key=lambda event: (
                    str(
                        event.get("record_time")
                        or event.get("claimed_time")
                    ),
                    str(event.get("event_id", "")),
                ),
            )
            user_world_at = str(
                latest.get("record_time")
                or latest.get("claimed_time")
            )
            self.activity.record(
                MaterialClue(
                    clue_id=(
                        "candidate-append:"
                        + sha256(
                            f"{candidate_id}\0{target_matter_id}\0{user_world_at}".encode(
                                "utf-8"
                            )
                        ).hexdigest()[:24]
                    ),
                    matter_id=target_matter_id,
                    clue_kind=materialization,
                    user_world_at=user_world_at,
                    disposition="material",
                    rationale=rationale,
                    localized_summary=dict(
                        candidate_projection.get(
                            "localized_rationale",
                            candidate_projection.get("localized_values", {}),
                        )
                    ),
                    semantic_revision=str(
                        candidate_projection.get("semantic_revision", "")
                    ),
                    evidence_ids=normalized_evidence,
                )
            )
        self.store.append_next(
            "admission_decision",
            candidate_id,
            {
                **candidate_decision,
                "status": "appended",
                "rationale": rationale,
                "canonical_matter_id": target_matter_id,
            },
        )
        canonicalization = {
            "source_matter_id": candidate_id,
            "canonical_matter_id": target_matter_id,
            "disposition": f"appended_as_{materialization}",
            "hierarchy_revision_id": "",
            "rationale": rationale,
            "evidence_ids": normalized_evidence,
            "status": "current",
        }
        self.store.compare_current_and_append(
            "matter_canonicalization",
            candidate_id,
            is_equivalent=lambda current: current == canonicalization,
            payload_factory=lambda _revision, _current: canonicalization,
        )
        coverage_rows = self.coverage_ledger.replace_matter_reference(
            source_matter_id=candidate_id,
            target_matter_id=target_matter_id,
            refresh_summary=False,
        )
        hierarchy_cleanup = (
            self._retire_canonicalized_hierarchy_authority(candidate_id)
        )
        self.hierarchy.mark_dependency_changed(
            target_matter_id,
            change_ref=f"candidate-append:{candidate_id}",
            refresh=True,
        )
        self.coverage_ledger.refresh_summary()
        return {
            "candidate_id": candidate_id,
            "canonical_matter_id": target_matter_id,
            "materialization": materialization,
            "moved_event_count": len(moved_events),
            "coverage_row_count": len(coverage_rows),
            "hierarchy_pointer_count": int(
                hierarchy_cleanup["retired_pointer_count"]
            ),
            "idempotent": False,
        }

    def retire_candidate_to_source_only(
        self,
        *,
        candidate_id: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        _in_transaction: bool = False,
    ) -> dict[str, Any]:
        """Keep useful evidence but remove a candidate with no trackable goal."""

        if self.store is None or self.coverage_ledger is None:
            raise RuntimeError("MATTERS_HOME is required for candidate retirement")
        normalized_rationale = str(rationale).strip()
        if not normalized_rationale:
            raise ValueError("candidate retirement rationale is required")
        if not _in_transaction:
            with self.store.immediate_transaction():
                return self.retire_candidate_to_source_only(
                    candidate_id=candidate_id,
                    rationale=rationale,
                    evidence_ids=evidence_ids,
                    _in_transaction=True,
                )
        decision = self.store.current("admission_decision", candidate_id) or {}
        candidate = decision.get("candidate")
        if str(decision.get("status", "")) == "source_only":
            return {
                "candidate_id": candidate_id,
                "status": "source_only",
                "coverage_row_count": 0,
                "hierarchy_pointer_count": int(
                    self._retire_canonicalized_hierarchy_authority(
                        candidate_id
                    )["retired_pointer_count"]
                ),
                "evidence_preserved": True,
                "idempotent": True,
            }
        if (
            str(decision.get("status", "")) != "uncertain"
            or not isinstance(candidate, Mapping)
        ):
            raise ValueError(
                "source-only retirement requires an uncertain candidate"
            )
        available_evidence = tuple(candidate.get("evidence_ids", ()))
        normalized_evidence = tuple(
            dict.fromkeys(str(item) for item in evidence_ids if str(item))
        )
        if (
            not normalized_evidence
            or not set(normalized_evidence).issubset(available_evidence)
        ):
            raise ValueError(
                "candidate retirement evidence must come from the candidate"
            )
        self.store.append_next(
            "admission_decision",
            candidate_id,
            {
                **decision,
                "status": "source_only",
                "rationale": normalized_rationale,
                "canonical_matter_id": "",
            },
        )
        canonicalization = {
            "source_matter_id": candidate_id,
            "canonical_matter_id": "",
            "disposition": "retired_to_source_only",
            "hierarchy_revision_id": "",
            "rationale": normalized_rationale,
            "evidence_ids": normalized_evidence,
            "status": "current",
        }
        self.store.compare_current_and_append(
            "matter_canonicalization",
            candidate_id,
            is_equivalent=lambda current: current == canonicalization,
            payload_factory=lambda _revision, _current: canonicalization,
        )
        coverage_rows = self.coverage_ledger.remove_matter_reference(
            matter_id=candidate_id,
            reason="insufficient_goal_or_obligation",
            refresh_summary=False,
        )
        hierarchy_cleanup = (
            self._retire_canonicalized_hierarchy_authority(candidate_id)
        )
        self.coverage_ledger.refresh_summary()
        return {
            "candidate_id": candidate_id,
            "status": "source_only",
            "coverage_row_count": len(coverage_rows),
            "hierarchy_pointer_count": int(
                hierarchy_cleanup["retired_pointer_count"]
            ),
            "evidence_preserved": True,
            "idempotent": False,
        }

    def reparent_matter_child(
        self,
        *,
        child_matter_id: str,
        expected_parent_matter_id: str,
        new_parent_matter_id: str,
        role: str,
        confidence: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
        ordinal: int = 0,
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        return asdict(
            self.hierarchy.reparent_child(
                child_matter_id=child_matter_id,
                expected_parent_matter_id=expected_parent_matter_id,
                new_parent_matter_id=new_parent_matter_id,
                role=role,
                confidence=confidence,
                rationale=rationale,
                evidence_ids=evidence_ids,
                ordinal=ordinal,
            )
        )

    def detach_matter_child(
        self,
        *,
        child_matter_id: str,
        expected_parent_matter_id: str,
        rationale: str,
        evidence_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        return asdict(
            self.hierarchy.detach_child(
                child_matter_id=child_matter_id,
                expected_parent_matter_id=expected_parent_matter_id,
                rationale=rationale,
                evidence_ids=evidence_ids,
            )
        )

    def upsert_matter_work_item(
        self,
        *,
        item_id: str,
        matter_id: str,
        kind: str,
        status: str,
        localized_title: Mapping[str, str],
        localized_result: Mapping[str, str],
        evidence_ids: tuple[str, ...] = (),
        source_ids: tuple[str, ...] = (),
        planned_start: str = "",
        planned_end: str = "",
        actual_start: str = "",
        actual_end: str = "",
        required_for_parent: bool = False,
        freshness: str = "current",
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for WorkItems")
        return asdict(
            self.hierarchy.save_work_item(
                MatterWorkItem(
                    item_id=item_id,
                    matter_id=matter_id,
                    kind=kind,
                    status=status,
                    localized_title=localized_title,
                    localized_result=localized_result,
                    evidence_ids=evidence_ids,
                    source_ids=source_ids,
                    planned_start=planned_start,
                    planned_end=planned_end,
                    actual_start=actual_start,
                    actual_end=actual_end,
                    required_for_parent=required_for_parent,
                    freshness=freshness,
                )
            )
        )

    def record_matter_split_or_merge(
        self,
        *,
        change_kind: str,
        subject_matter_ids: tuple[str, ...],
        rationale: str,
        evidence_ids: tuple[str, ...],
        dispositions: tuple[Mapping[str, Any], ...],
    ) -> dict[str, Any]:
        if self.hierarchy is None:
            raise RuntimeError("MATTERS_HOME is required for Matter hierarchy")
        normalized = tuple(
            HierarchyMemberDisposition(
                member_kind=str(item["member_kind"]),
                member_id=str(item["member_id"]),
                action=str(item["action"]),
                target_matter_ids=tuple(item.get("target_matter_ids", ())),
                evidence_ids=tuple(item.get("evidence_ids", ())),
            )
            for item in dispositions
        )
        revision = self.hierarchy.record_split_or_merge(
            change_kind=change_kind,
            subject_matter_ids=subject_matter_ids,
            rationale=rationale,
            evidence_ids=evidence_ids,
            dispositions=normalized,
        )
        if self.dispatcher is None:
            raise RuntimeError("original-owner dispatcher is unavailable")
        self.dispatcher.apply_hierarchy_revision(revision)
        return asdict(revision)

    def matter_evidence(
        self,
        *,
        matter_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for Matter evidence")
        return self.browser.evidence(
            matter_id,
            offset=offset,
            limit=limit,
        )

    def object_browser_projection(
        self,
        *,
        locale: str = "en",
        query: str = "",
        status: str = "all",
        time_filter: str = "all",
        sort: str = "activity",
        offset: int = 0,
        limit: int = 60,
        root_only: bool = True,
        start_year: str = "all",
        people: Sequence[str] = (),
        relationships: Sequence[str] = (),
        topic_types: Sequence[str] = (),
        source_types: Sequence[str] = (),
    ) -> dict[str, Any]:
        catalog = self.object_catalog_page(
            locale=locale,
            query=query,
            status=status,
            time_filter=time_filter,
            sort=sort,
            offset=offset,
            limit=limit,
            root_only=root_only,
            start_year=start_year,
            people=people,
            relationships=relationships,
            topic_types=topic_types,
            source_types=source_types,
        )
        coverage = self.object_coverage_snapshot()
        worker = (
            self.store.latest("maintenance_cycle")
            if self.store is not None
            else None
        )
        return {
            "product": "Matters",
            "surface": "object_browser",
            "default_locale": self.locale_registry_owner.default_locale,
            "selected_locale": locale,
            "available_locales": self.locale_registry_owner.available_locales,
            "locale_registry_revision": self.locale_registry_owner.revision,
            "catalog": catalog,
            "coverage": coverage,
            "background": {
                "status": str(
                    (worker or {}).get(
                        "status",
                        coverage.get("worker_health", "idle"),
                    )
                ),
                "checkpoint": str(
                    (worker or {}).get(
                        "checkpoint",
                        coverage.get("worker_checkpoint", ""),
                    )
                ),
            },
        }

    def resolve_visual_preview(
        self,
        *,
        preview_token: str,
        hero: bool = False,
    ) -> tuple[bytes, str]:
        if self.visuals is None:
            raise RuntimeError("MATTERS_HOME is required for visual previews")
        return self.visuals.resolve(preview_token, hero=hero)

    def resolve_generated_hero(
        self,
        *,
        preview_token: str,
    ) -> tuple[bytes, str]:
        if self.heroes is None:
            raise RuntimeError("MATTERS_HOME is required for generated heroes")
        return self.heroes.resolve(preview_token)

    def submit_matter_correction(
        self,
        *,
        matter_id: str,
        rationale: str,
        field_name: str = "",
        corrected_value: str = "",
    ) -> dict[str, Any]:
        if self.store is None or self.recompute is None:
            raise RuntimeError("MATTERS_HOME is required for corrections")
        if not rationale.strip():
            raise ValueError("correction rationale is required")
        projection = self.store.current("projection", matter_id)
        if projection is None:
            raise KeyError("matter is unavailable")
        revision = self.corrections.append(
            kind="correction",
            target_id=matter_id,
            prior_revision_id=str(projection["semantic_revision"]),
            rationale=rationale.strip(),
            evidence_ids=tuple(projection.get("evidence_ids", ())),
        )
        self.store.append(
            "revision",
            revision.revision_id,
            1,
            asdict(revision),
        )
        self.store.append(
            "correction_input",
            revision.revision_id,
            1,
            {
                "revision_id": revision.revision_id,
                "matter_id": matter_id,
                "field_name": field_name,
                "corrected_value": corrected_value,
                "rationale": rationale.strip(),
                "status": "accepted_recompute_queued",
            },
        )
        dependents = (
            ("matter", "C6_matter_admission"),
            ("lifecycle", "C7_lifecycle_board_state"),
            ("open_loop", "C8_open_loop_waiting_blocking"),
            ("outcome", "C9_completion_cancellation_reopen"),
            ("projection", "C12_projection_bilingual_ui"),
        )
        plan, requests = self.corrections.invalidate(revision, dependents)
        if self.hierarchy is not None:
            self.hierarchy.mark_dependency_changed(
                matter_id,
                change_ref=revision.revision_id,
                refresh=False,
            )
        for row in self._coverage_rows_for_matter(matter_id):
            if self.coverage_ledger is not None:
                self.coverage_ledger.mark_stale(
                    object_id=str(row["object_id"]),
                    stage_ids=(
                        "matter",
                        "localization",
                        "meaningful_clue_summary",
                        "generated_hero",
                        "supplemental_information",
                        "ui_projection",
                    ),
                    input_fingerprint=revision.revision_id,
                )
        batch = self.recompute.submit(requests)
        terminal = self.recompute.run_to_terminal(batch)
        if self.hierarchy is not None and terminal.status == "passed":
            self.hierarchy.mark_dependency_changed(
                matter_id,
                change_ref=revision.revision_id,
                refresh=True,
            )
        return {
            "revision": asdict(revision),
            "invalidation_plan": asdict(plan),
            "recompute_status": terminal.status,
            "status": (
                "auto_applied"
                if terminal.status == "passed"
                else "recompute_blocked"
            ),
        }

    def _coverage_rows_for_matter(
        self,
        matter_id: str,
    ) -> tuple[dict[str, Any], ...]:
        if self.store is None:
            return ()
        return self.store.current_by_json_array_members(
            "object_coverage",
            json_field="matter_ids",
            values=(matter_id,),
        ).get(matter_id, ())

    def _mark_matter_ui_if_ready(
        self,
        matter_id: str,
        input_fingerprint: str,
        *,
        refresh_summary: bool = True,
    ) -> None:
        if self.coverage_ledger is None:
            return
        prerequisites = (
            "matter",
            "semantic_depth",
            "hierarchy_registration",
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
            "localization",
            "meaningful_clue_summary",
            "generated_hero",
            "supplemental_information",
        )
        for payload in self._coverage_rows_for_matter(matter_id):
            object_id = str(payload["object_id"])
            row = self.coverage_ledger.current(object_id)
            if row is None:
                continue
            ready = all(
                (pointer := row.stages.get(stage_id)) is not None
                and pointer.status in {"current", "uncertain"}
                for stage_id in prerequisites
            )
            status = "current" if ready else "pending"
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="ui_projection",
                status=status,
                input_fingerprint=input_fingerprint,
                output_ref=f"projection:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="ui_reachable",
                status=status,
                input_fingerprint=input_fingerprint,
                output_ref=f"object_browser:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
        if refresh_summary:
            self.coverage_ledger.refresh_summary()

    def next_coverage_work(
        self,
        *,
        limit: int = 100,
    ) -> tuple[tuple[str, str], ...]:
        if self.coverage_ledger is None:
            return ()
        return self.coverage_ledger.next_work(limit=limit)

    def rebase_temporal_event_logical_identity(
        self,
        *,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Backfill stable logical identities without changing event meaning."""

        if self.store is None:
            raise RuntimeError(
                "MATTERS_HOME is required for temporal event rebase"
            )
        rows, total = self.store.current_page(
            "temporal_event",
            offset=offset,
            limit=limit,
        )
        migrated = 0
        for row in rows:
            event_id = str(row.get("event_id", "")).strip()
            if not event_id:
                continue
            updated = dict(row)
            updated.setdefault(
                "logical_event_key",
                logical_event_key_for_payload(updated),
            )
            updated.setdefault("current_revision", True)
            updated.setdefault("supersedes_event_id", "")
            updated.setdefault(
                "occurrence_boundary",
                "|".join(
                    (
                        str(updated.get("object_ref", "")).strip(),
                        str(updated.get("kind", "")).strip().casefold(),
                        str(updated.get("actor", "")).strip().casefold(),
                        str(updated.get("claimed_time", "")).strip(),
                        str(updated.get("record_time", "")).strip(),
                    )
                ),
            )
            stored = self.store.compare_current_and_append(
                "temporal_event",
                event_id,
                is_equivalent=lambda current, value=updated: current == value,
                payload_factory=lambda _revision, _current, value=updated: value,
            )
            migrated += int(str(stored.get("status", "")) == "appended")
        next_offset = offset + len(rows)
        return {
            "offset": offset,
            "limit": limit,
            "processed_count": len(rows),
            "migrated_count": migrated,
            "total_count": total,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
        }

    def run_maintenance_cycle(self, *, limit: int = 20) -> dict[str, Any]:
        if self.maintenance_worker is None:
            raise RuntimeError("MATTERS_HOME is required for autonomous maintenance")
        cycle = asdict(self.maintenance_worker.run_cycle(limit=limit))
        owner_recovery_only = int(
            cycle.get("owner_redispatch_count", 0)
        ) > 0
        coverage_reconciliation = (
            self.reconcile_coverage_inventory_orphans(
                limit=min(500, max(1, limit)),
            )
        )
        hierarchy_reconciliation = (
            self.reconcile_noncanonical_matter_hierarchy(
                limit=min(500, max(1, limit)),
            )
        )
        presentation_reconciliation = (
            self._deferred_presentation_reconciliation()
            if owner_recovery_only
            else self.reconcile_admitted_matter_presentation(
                limit=min(500, max(1, limit)),
            )
        )
        supplemental_reconciliation = (
            self.rebase_empty_supplemental_information(
                limit=min(500, max(1, limit)),
            )
        )
        supplemental_research_queue = (
            self._deferred_supplemental_research_queue()
            if owner_recovery_only
            else self.queue_eligible_supplemental_research(
                limit=min(500, max(1, limit)),
            )
        )
        return {
            **cycle,
            "followup_ai_expansion_status": (
                "deferred_owner_redispatch"
                if owner_recovery_only
                else "eligible"
            ),
            "coverage_orphan_reconciliation": coverage_reconciliation,
            "noncanonical_matter_hierarchy_reconciliation": (
                hierarchy_reconciliation
            ),
            "matter_presentation_reconciliation": (
                presentation_reconciliation
            ),
            "empty_supplemental_information_reconciliation": (
                supplemental_reconciliation
            ),
            "supplemental_research_queue": supplemental_research_queue,
        }

    @staticmethod
    def _deferred_presentation_reconciliation() -> dict[str, Any]:
        """Return the typed no-write result for an owner-recovery-only cycle."""

        return {
            "scanned_matter_count": 0,
            "projection_current_count": 0,
            "projection_repair_queued_count": 0,
            "projection_repair_blocked_count": 0,
            "hero_current_count": 0,
            "hero_pending_count": 0,
            "hero_blocked_count": 0,
            "hero_prepared_count": 0,
            "items": (),
            "next_cursor": "",
            "has_more": False,
            "status": "deferred_owner_redispatch",
        }

    @staticmethod
    def _deferred_supplemental_research_queue() -> dict[str, Any]:
        """Return the typed no-write result for an owner-recovery-only cycle."""

        return {
            "scanned_matter_count": 0,
            "queued_count": 0,
            "current_count": 0,
            "not_applicable_count": 0,
            "unavailable_count": 0,
            "blocked_count": 0,
            "unchanged_count": 0,
            "changed": False,
            "items": (),
            "next_cursor": "",
            "has_more": False,
            "status": "deferred_owner_redispatch",
        }

    def run_planned_maintenance(
        self,
        request: MaintenanceRunRequest,
    ) -> dict[str, Any]:
        """Run one host-planned maintenance request through injected adapters."""

        if self.maintenance_orchestration is None:
            raise RuntimeError(
                "capability_unavailable: Codex maintenance adapters are not configured"
            )
        return asdict(self.maintenance_orchestration.run(request))

    def _resume_hierarchy_dispositions(
        self,
        limit: int,
    ) -> tuple[int, int]:
        if self.hierarchy is None or self.dispatcher is None:
            return (0, 0)
        recovered = 0
        blocked = 0
        for revision_id in self.hierarchy.pending_disposition_revision_ids(
            limit=limit,
        ):
            try:
                self.dispatcher.apply_hierarchy_revision(
                    self.hierarchy.revision(revision_id)
                )
                recovered += 1
            except Exception:
                blocked += 1
        return recovered, blocked

    def _resume_source_analysis_expansions(
        self,
        limit: int,
    ) -> tuple[int, int]:
        result = self.expand_pending_source_understanding(
            limit_sources=limit,
            max_packages_per_source=5,
        )
        return (
            int(result["expanded_source_count"]),
            int(result["queued_package_count"]),
        )

    def start_autonomous_maintenance(self) -> None:
        if self.maintenance_worker is None:
            raise RuntimeError("MATTERS_HOME is required for autonomous maintenance")
        self.maintenance_worker.start()

    def stop_autonomous_maintenance(self, *, timeout: float = 5.0) -> bool:
        if self.maintenance_worker is None:
            return True
        return self.maintenance_worker.stop(timeout=timeout)

    def version(self) -> dict[str, str]:
        return {
            "package_version": VERSION,
            "source_schema_version": "1.0",
            "skill_schema_version": "1.0",
        }

    def work_status(self) -> tuple[dict[str, Any], ...]:
        if self.work_queue is None:
            return ()
        return tuple(
            {
                "job_id": item.job_id,
                "owner_id": item.owner_id,
                "status": item.status,
                "attempt": item.attempt,
                "checkpoint": item.checkpoint,
                "failure_class": item.failure_class,
                "updated_at": item.updated_at,
            }
            for item in self.work_queue.list_items()
        )

    def pause_work(self, *, job_id: str) -> dict[str, Any]:
        if self.work_queue is None:
            raise RuntimeError("MATTERS_HOME is required for durable work")
        item = self.work_queue.pause(job_id)
        return {
            "job_id": item.job_id,
            "status": item.status,
            "checkpoint": item.checkpoint,
        }

    def resume_work(self, *, job_id: str) -> dict[str, Any]:
        if self.work_queue is None:
            raise RuntimeError("MATTERS_HOME is required for durable work")
        item = self.work_queue.resume(job_id)
        return {
            "job_id": item.job_id,
            "status": item.status,
            "checkpoint": item.checkpoint,
        }

    def scan_filesystem(
        self,
        *,
        root: str,
        content_limit: int | None,
    ) -> object:
        """Run or resume one partition-bounded private source pass."""

        if self.config.private_root is None:
            raise RuntimeError("MATTERS_HOME is required for filesystem inventory")
        from matters.application.partitioned_filesystem import (
            PartitionedFilesystemRunner,
        )

        source_root = Path(root).resolve(strict=True)
        runner = PartitionedFilesystemRunner(
            self,
            manifest_path=PartitionedFilesystemRunner.default_manifest_path(
                self.config.private_root,
                source_root,
            ),
            max_entries=25_000,
            content_limit=0 if content_limit is None else content_limit,
        )
        return runner.run(source_root)

    def process_registered_filesystem_batch(
        self,
        *,
        limit: int,
    ) -> object:
        """Advance one bounded page of already-inventoried filesystem work."""

        from matters.application.source_workflows import SourceWorkflow

        return SourceWorkflow(self).process_registered_filesystem_batch(
            limit=limit,
        )

    def register_codex_sources(
        self,
        *,
        manifest: object,
        projects: Sequence[object],
    ) -> object:
        """Persist and run one explicit source-in-place Codex registration."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for Codex sources")
        from matters.application.source_workflows import SourceWorkflow
        from matters.providers.codex import (
            CodexProjectReference,
            CodexRegistrationAdapter,
            CodexSourceManifest,
        )

        if not isinstance(manifest, CodexSourceManifest) or not all(
            isinstance(item, CodexProjectReference) for item in projects
        ):
            raise TypeError(
                "Codex registration requires current manifest and project "
                "contracts"
            )
        adapter = CodexRegistrationAdapter(manifest, projects)
        payload = {
            "scope_id": manifest.scope_id,
            "manifest": asdict(manifest),
            "projects": tuple(asdict(item) for item in projects),
            "storage_policy": "source_in_place_metadata_only",
            "content_copied": False,
        }
        self.store.compare_current_and_append(
            "codex_source_configuration",
            manifest.scope_id,
            is_equivalent=lambda current: current == payload,
            payload_factory=lambda _revision, _current: payload,
        )
        return SourceWorkflow(self).run_codex(adapter)

    def refresh_registered_codex_sources(
        self,
        *,
        scope_id: str,
    ) -> object:
        """Re-run one persisted Codex registration without rediscovering paths."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for Codex sources")
        from matters.providers.codex import (
            CodexProjectReference,
            CodexSourceManifest,
            refresh_codex_project_references,
        )

        payload = self.store.current(
            "codex_source_configuration",
            scope_id,
        )
        if payload is None:
            raise KeyError("Codex source configuration is unavailable")
        manifest = CodexSourceManifest(**dict(payload["manifest"]))
        projects = tuple(
            CodexProjectReference(**dict(item))
            for item in payload.get("projects", ())
        )
        projects = refresh_codex_project_references(projects)
        return self.register_codex_sources(
            manifest=manifest,
            projects=projects,
        )

    def locale_registry(self) -> dict[str, object]:
        return self.locale_registry_owner.manifest()

    def _partition_inventory_progress(self) -> dict[str, Any]:
        """Project private partition manifests without exposing paths or ids."""

        private_root = self.config.private_root
        if private_root is None:
            return {
                "status": "not_configured",
                "manifest_count": 0,
                "partition_count": 0,
                "terminal_partition_count": 0,
                "failed_partition_count": 0,
            }
        manifest_root = (
            private_root / "runs" / "filesystem-partitions"
        )
        manifest_count = 0
        partition_count = 0
        terminal_count = 0
        failed_count = 0
        open_count = 0
        invalid_count = 0
        for manifest_path in sorted(manifest_root.glob("*.json")):
            manifest_count += 1
            try:
                payload = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
                nodes = payload["nodes"]
                if (
                    payload.get("schema")
                    != "matters.private-filesystem-partitions.v1"
                    or not isinstance(nodes, dict)
                ):
                    raise ValueError("partition manifest is malformed")
            except (OSError, KeyError, ValueError, json.JSONDecodeError):
                invalid_count += 1
                continue
            for node in nodes.values():
                partition_count += 1
                status = str(node.get("status", ""))
                if status in {"complete", "partitioned"}:
                    terminal_count += 1
                elif status == "failed":
                    failed_count += 1
                else:
                    open_count += 1
            if payload.get("inventory_status") not in {"complete", "blocked"}:
                open_count += 1
        if invalid_count or failed_count:
            status = "blocked"
        elif open_count:
            status = "partial"
        elif manifest_count:
            status = "complete"
        else:
            status = "not_started"
        return {
            "status": status,
            "manifest_count": manifest_count,
            "partition_count": partition_count,
            "terminal_partition_count": terminal_count,
            "failed_partition_count": failed_count + invalid_count,
        }

    def report_model_miss(
        self,
        *,
        failure_class: str,
        expected_behavior: str,
        observed_behavior: str,
        model_path: str,
        private_evidence_handle: str,
        current_runtime_disposition: str,
    ) -> ModelMissWorkItem:
        if self.model_misses is None:
            raise RuntimeError("MATTERS_HOME is required for model-miss evidence")
        return self.model_misses.report(
            failure_class=failure_class,
            expected_behavior=expected_behavior,
            observed_behavior=observed_behavior,
            model_path=model_path,
            private_evidence_handle=private_evidence_handle,
            current_runtime_disposition=current_runtime_disposition,
        )

__all__ = [
    "CapabilityReport",
    "MatterService",
    "SourceProcessingResult",
]
