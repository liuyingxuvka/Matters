"""M0: the single end-to-end facade over C1-C12 owner services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from matters.application.coverage_ledger import ObjectCoverageLedger
from matters.application.dispatcher import AutonomousFindingDispatcher
from matters.application.maintenance import AutonomousMaintenanceWorker
from matters.analysis.depth import SemanticDepth, SemanticDepthOwner
from matters.analysis.guard_bridge import GuardBridge
from matters.analysis.operations import (
    AgentOperationOwner,
    AgentOperationResult,
    AgentRunner,
    AnalysisWorkPackage,
    ResearchProviderStatus,
)
from matters.authorization.coverage import (
    AuthorizationCoverage,
    AuthorizationError,
    CoverageReceipt,
)
from matters.authorization.scopes import AuthorizationScope
from matters.bundled_skills import build_bundle, load_projections
from matters.config import RuntimeConfig
from matters.domain.admission import AdmissionPacket, MatterAdmission
from matters.domain.matters import AdmissionDecision
from matters.domain.relations import MatterRelationCandidate
from matters.identity.people import PersonCandidate, PersonRegistry
from matters.infrastructure.jobs.runner import DurableWorkQueue
from matters.infrastructure.blobs.store import BlobStore
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.inventory.owners import (
    CandidateScope,
    ChangeSet,
    InventoryOccurrence,
    InventoryOwner,
    InventorySnapshot,
    SourceDisposition,
    TrackingPolicy,
    tracking_action_token,
)
from matters.maintenance.model_miss import ModelMissOwner, ModelMissWorkItem
from matters.presentation.projections import MatterProjection, ProjectionOwner
from matters.presentation.visuals import CardVisualDecision, VisualAssetOwner
from matters.presentation.browser import ObjectBrowserProjection
from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
    disposition_reason_localized,
    localized,
    rationale_localized,
    state_localized,
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
from matters.state.open_loops import BlockingDecision, OpenLoop, OpenLoopOwner
from matters.state.outcomes import (
    CompletionCriterion,
    OutcomeDecision,
    OutcomeOwner,
)
from matters.timeline.events import EventRegistry, TemporalTrace
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


class MatterService:
    """Stable public facade; it delegates and never becomes a child writer."""

    def __init__(
        self,
        *,
        private_root: Path | str | None = None,
        repository_root: Path | str | None = None,
        research_status: ResearchProviderStatus | None = None,
    ) -> None:
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
        self.blobs: BlobStore | None = None
        if private_status.status == "active":
            private_path = self.config.activate_private_root()
            self.store = SQLiteStore(private_path, self.config.repository_root)
            self.blobs = BlobStore(private_path, self.config.repository_root)
            self.inventory = InventoryOwner(self.store)
            self.work_queue = DurableWorkQueue(self.store)
            self.recompute = OriginalOwnerRecompute(self.work_queue)
            self.coverage_ledger = ObjectCoverageLedger(self.store)
            self._register_recompute_handlers()
        self.authorization = AuthorizationCoverage()
        self.sources = SourceRegistry(store=self.store)
        self.evidence = EvidenceQualifier()
        self.people = PersonRegistry()
        self.events = EventRegistry()
        self.admission = MatterAdmission()
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
        self.depth = SemanticDepthOwner(self.store)
        self.projections = ProjectionOwner()
        self.visuals = (
            VisualAssetOwner(store=self.store, blob_store=self.blobs)
            if self.store is not None and self.blobs is not None
            else None
        )
        self.browser = (
            ObjectBrowserProjection(self.store)
            if self.store is not None
            else None
        )
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
            )
            if self.store is not None
            and self.coverage_ledger is not None
            and self.visuals is not None
            else None
        )
        self.maintenance_worker = (
            AutonomousMaintenanceWorker(
                store=self.store,
                ledger=self.coverage_ledger,
                operations=self.operations,
                dispatcher=self.dispatcher,
            )
            if self.store is not None
            and self.coverage_ledger is not None
            and self.dispatcher is not None
            else None
        )
        self.locale_registry_owner = DEFAULT_LOCALE_REGISTRY
        if self.store is not None:
            self._migrate_projection_locale_maps()
        self.research_status = research_status or ResearchProviderStatus(
            "researchguard_pending_integration"
        )
        self.model_misses = (
            ModelMissOwner(self.store, self.work_queue)
            if self.store is not None and self.work_queue is not None
            else None
        )

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
            matters_version="0.2.0",
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
                    for stage_id in ("localization", "visual", "ui_projection"):
                        self.coverage_ledger.mark_stage(
                            object_id=object_id,
                            stage_id=stage_id,
                            status="current",
                            input_fingerprint=revision_id,
                            output_ref=(
                                output_ref
                                if stage_id != "visual"
                                else str(
                                    (
                                        self.store.current(
                                            "card_visual_decision",
                                            matter_id,
                                        )
                                        or {}
                                    ).get(
                                        "decision_id",
                                        f"visual:placeholder:{matter_id}",
                                    )
                                )
                            ),
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
            ),
            CompletionCriterion(
                "result_attachment",
                bool(payload.get("attachments")),
                tuple(by_field.get("attachments", ())),
            ),
            CompletionCriterion(
                "explicit_confirmation",
                bool(confirmation),
                confirmation,
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
        admission = self.admission.decide(
            AdmissionPacket(
                source_ids=(source.source_id,),
                evidence_ids=tuple(item.evidence_id for item in anchors),
                explicit_goal_or_obligation=bool(
                    envelope.payload.get("explicit_goal_or_obligation", False)
                ),
                useful_content=bool(summary or envelope.payload.get("links")),
                conflict=bool(trace.conflicts) or semantic_hierarchy_review,
                access_blocked=access_blocked,
                possibility_only=possibility_only,
            )
        )

        evidence_ids = tuple(item.evidence_id for item in anchors)
        provider_status = str(envelope.payload.get("status", ""))
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
                ",".join(anchor.evidence_id for anchor in result.evidence)
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
            }
            if stale_stages_by_object:
                self.coverage_ledger.mark_stale_many(
                    stage_ids_by_object=stale_stages_by_object,
                    input_fingerprint=changes.change_set_id,
                    refresh_summary=False,
                )
            if refresh_coverage_summary:
                self.coverage_ledger.refresh_summary()
        return snapshot, changes

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
        chunk_size: int = 20,
        text_limit: int = 800,
    ) -> tuple[AgentOperationResult, ...]:
        """Queue bounded, evidence-whitelisted source chunks for injected AI."""

        if self.store is None:
            raise RuntimeError("MATTERS_HOME is required for durable analysis")
        if chunk_size < 1 or chunk_size > 50 or text_limit < 80 or text_limit > 4000:
            raise ValueError("analysis work package bounds are invalid")
        current = tuple(item for item in anchors if item.current and item.text.strip())
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
        queued: list[AgentOperationResult] = []
        for start in range(0, len(current), chunk_size):
            chunk = current[start : start + chunk_size]
            package = AnalysisWorkPackage.create(
                operation_type="text_analysis",
                task_kind="semantic_understanding",
                source_revision_ids=(source_revision,),
                model_revision="matters-semantic-understanding:v2",
                allowed_evidence_ids=tuple(item.evidence_id for item in chunk),
                allowed_asset_ids=allowed_asset_ids,
                private_evidence={
                    "source_kind": source_kind,
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
                        "finding_types": (
                            "matter_candidate",
                            "person_candidate",
                            "event_candidate",
                            "open_loop_candidate",
                            "deadline_candidate",
                            "conflict",
                            "completion_gap",
                            "bounded_summary",
                            "card_visual_candidate",
                        ),
                        "required_locales": ("en", "zh-CN"),
                        "advisory_only": True,
                        "human_confirmation_required": False,
                    },
                },
                inventory_identity=(
                    str(
                        (self.store.latest("inventory_snapshot") or {}).get(
                            "snapshot_id",
                            "inventory:current",
                        )
                    )
                ),
                locale_registry_revision=self.locale_registry_owner.revision,
            )
            queued.append(self.operations.queue(package))
        return tuple(queued)

    def pending_analysis_packages(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return private, bounded packages only to the local AI operation path."""

        rows, total = self.operations.pending_packages(
            offset=offset,
            limit=limit,
        )
        next_offset = offset + len(rows)
        return {
            "items": rows,
            "offset": offset,
            "limit": limit,
            "total_count": total,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
            "disclosure": "private_local_ai_operation_only",
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
        operation_result = self.operations.import_result(
            package_id=package_id,
            provider_id=provider_id,
            provider_version=provider_version,
            result=result,
        )
        outcomes = self.dispatcher.dispatch(package, operation_result)
        return {
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

    def current_records(self, owner: str) -> tuple[dict, ...]:
        if self.store is None:
            return ()
        return self.store.list_current(owner)

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
        return asdict(self.coverage_ledger.summary())

    def object_coverage_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[tuple[dict[str, Any], ...], int]:
        """Return a bounded private maintenance view for local diagnostics."""

        if self.store is None:
            return (), 0
        return self.store.current_page(
            "object_coverage",
            offset=offset,
            limit=limit,
        )

    def object_catalog_page(
        self,
        *,
        locale: str = "en",
        query: str = "",
        status: str = "all",
        time_filter: str = "all",
        sort: str = "recent",
        offset: int = 0,
        limit: int = 60,
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
                },
                "facets": {
                    "status": {
                        "all": 0,
                        "planned": 0,
                        "in_progress": 0,
                        "completed": 0,
                    }
                },
            }
        return self.browser.catalog(
            locale=locale,
            query=query,
            status=status,
            time_filter=time_filter,
            sort=sort,
            offset=offset,
            limit=limit,
        )

    def matter_detail(
        self,
        *,
        matter_id: str,
        locale: str = "en",
    ) -> dict[str, Any]:
        if self.browser is None:
            raise RuntimeError("MATTERS_HOME is required for Matter details")
        return self.browser.detail(matter_id, locale=locale)

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
        sort: str = "recent",
        offset: int = 0,
        limit: int = 60,
    ) -> dict[str, Any]:
        catalog = self.object_catalog_page(
            locale=locale,
            query=query,
            status=status,
            time_filter=time_filter,
            sort=sort,
            offset=offset,
            limit=limit,
        )
        coverage = self.object_coverage_summary()
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

    def set_matter_cover(
        self,
        *,
        matter_id: str,
        asset_id: str,
        active: bool,
        rationale: str,
    ) -> CardVisualDecision:
        if self.visuals is None:
            raise RuntimeError("MATTERS_HOME is required for cover correction")
        return self.visuals.set_override(
            matter_id=matter_id,
            asset_id=asset_id,
            active=active,
            rationale=rationale,
        )

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
        for row in self._coverage_rows_for_matter(matter_id):
            if self.coverage_ledger is not None:
                self.coverage_ledger.mark_stale(
                    object_id=str(row["object_id"]),
                    stage_ids=(
                        "matter",
                        "localization",
                        "visual",
                        "ui_projection",
                    ),
                    input_fingerprint=revision.revision_id,
                )
        batch = self.recompute.submit(requests)
        terminal = self.recompute.run_to_terminal(batch)
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
        return tuple(
            row
            for row in self.store.iter_current("object_coverage")
            if matter_id in row.get("matter_ids", ())
        )

    def next_coverage_work(
        self,
        *,
        limit: int = 100,
    ) -> tuple[tuple[str, str], ...]:
        if self.coverage_ledger is None:
            return ()
        return self.coverage_ledger.next_work(limit=limit)

    def run_maintenance_cycle(self, *, limit: int = 20) -> dict[str, Any]:
        if self.maintenance_worker is None:
            raise RuntimeError("MATTERS_HOME is required for autonomous maintenance")
        return asdict(self.maintenance_worker.run_cycle(limit=limit))

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
            "package_version": "0.2.0",
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

    @staticmethod
    def _localized(
        en: str,
        zh_cn: str,
        *,
        semantic_revision: str = "runtime-projection",
    ) -> dict[str, str]:
        return localized(
            en,
            zh_cn,
            semantic_revision=semantic_revision,
        )

    def locale_registry(self) -> dict[str, object]:
        return self.locale_registry_owner.manifest()

    @staticmethod
    def _tracking_action_token(
        snapshot: InventorySnapshot,
        occurrence_id: str,
        disposition: str,
    ) -> str:
        return tracking_action_token(
            snapshot.scope_id,
            occurrence_id,
            disposition,
        )

    def _source_catalog_row(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        catalog = dict(payload["catalog"])
        freshness_row = payload.get("freshness")
        depth_row = payload.get("depth")
        freshness_status = (
            str(freshness_row.get("status", "unknown"))
            if isinstance(freshness_row, Mapping)
            else "current"
        )
        depth_status = (
            str(depth_row.get("state", "not_assessed"))
            if isinstance(depth_row, Mapping)
            else "not_assessed"
        )
        object_type = str(catalog.get("object_type", "source"))
        disposition = str(catalog.get("disposition", "review_required"))
        semantic_revision = str(
            catalog.get("snapshot_id", "inventory:unknown")
        )
        action_map = {
            "tracked": ("do_not_track", "defer"),
            "not_tracked": ("track", "restore"),
            "review_required": ("track", "do_not_track", "defer"),
            "deferred": ("track", "do_not_track"),
            "hard_excluded": (),
        }
        display_value = str(catalog.get("display_name", "Source"))
        return {
            "display_name": self._localized(display_value, display_value),
            "kind_label": self._localized(
                object_type.replace("_", " ").title(),
                {
                    "file": "文件",
                    "document": "文档",
                    "image": "照片",
                    "message": "邮件",
                    "thread": "邮件会话",
                    "attachment": "附件",
                    "cloud_placeholder": "云端占位项",
                }.get(object_type, "资料"),
            ),
            "disposition": disposition,
            "disposition_reason": disposition_reason_localized(
                str(catalog.get("disposition_reason", "")),
                semantic_revision=semantic_revision,
            ),
            "freshness": {
                "status": freshness_status,
                "label": state_localized(
                    freshness_status,
                    semantic_revision=semantic_revision,
                ),
            },
            "depth": {
                "status": depth_status,
                "label": state_localized(
                    depth_status,
                    semantic_revision=semantic_revision,
                ),
            },
            "allowed_actions": action_map.get(disposition, ()),
            "action_token": str(catalog.get("action_token", "")),
            "evidence": (),
        }

    @staticmethod
    def _review_catalog_row(source: Mapping[str, Any]) -> dict[str, Any]:
        disposition = str(source["disposition"])
        depth = str(source["depth"]["status"])
        freshness = str(source["freshness"]["status"])
        reasons_en: list[str] = []
        reasons_zh: list[str] = []
        if disposition in {"review_required", "deferred"}:
            reasons_en.append(str(source["disposition_reason"]["en"]))
            reasons_zh.append(str(source["disposition_reason"]["zh-CN"]))
        if depth in {"not_assessed", "partial", "blocked", "stale"}:
            depth_label = state_localized(depth)
            reasons_en.append(
                f"Semantic depth is {depth_label['en'].lower()}"
            )
            reasons_zh.append(f"理解深度为{depth_label['zh-CN']}")
        if freshness == "stale":
            reasons_en.append("Source dependencies need refresh")
            reasons_zh.append("来源依赖需要更新")
        return {
            "title": source["display_name"],
            "reason": localized(
                "; ".join(reasons_en),
                "；".join(reasons_zh),
                semantic_revision="review-catalog",
            ),
            "next_action": localized(
                "Review the source disposition and missing work",
                "确认来源处置并补齐缺失工作",
                semantic_revision="review-catalog",
            ),
            "evidence": (),
        }

    def _catalog_revision(self) -> str:
        if self.store is None:
            return "catalog:unconfigured"
        latest = self.store.latest("source_catalog")
        if latest is None:
            return "catalog:empty"
        return str(latest.get("snapshot_id", "catalog:unknown"))

    def _retired_source_catalog_page(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if self.store is None:
            return {
                "items": (),
                "offset": offset,
                "limit": limit,
                "total_count": 0,
                "next_offset": None,
                "has_more": False,
                "catalog_revision": self._catalog_revision(),
            }
        for _attempt in range(4):
            revision_before = self._catalog_revision()
            rows, total = self.store.source_catalog_page(
                offset=offset,
                limit=limit,
            )
            revision_after = self._catalog_revision()
            if revision_before == revision_after:
                break
        else:
            raise RuntimeError("source catalog changed during page read")
        items = tuple(self._source_catalog_row(item) for item in rows)
        next_offset = offset + len(items)
        return {
            "items": items,
            "offset": offset,
            "limit": limit,
            "total_count": total,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
            "catalog_revision": revision_after,
        }

    def _retired_review_catalog_page(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        if self.store is None:
            return {
                "items": (),
                "offset": offset,
                "limit": limit,
                "total_count": 0,
                "next_offset": None,
                "has_more": False,
                "catalog_revision": self._catalog_revision(),
            }
        for _attempt in range(4):
            revision_before = self._catalog_revision()
            rows, total = self.store.source_catalog_page(
                offset=offset,
                limit=limit,
                review_only=True,
            )
            revision_after = self._catalog_revision()
            if revision_before == revision_after:
                break
        else:
            raise RuntimeError("review catalog changed during page read")
        sources = tuple(self._source_catalog_row(item) for item in rows)
        items = tuple(self._review_catalog_row(item) for item in sources)
        next_offset = offset + len(items)
        return {
            "items": items,
            "offset": offset,
            "limit": limit,
            "total_count": total,
            "next_offset": next_offset if next_offset < total else None,
            "has_more": next_offset < total,
            "catalog_revision": revision_after,
        }

    def _retired_list_sources(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._retired_source_catalog_page(offset=0, limit=50)["items"])

    def _retired_list_review_queue(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._retired_review_catalog_page(offset=0, limit=50)["items"])

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

    def _retired_current_projection(self, *, language: str = "en") -> dict[str, Any]:
        self.locale_registry_owner.require(language)
        for _attempt in range(4):
            catalog_guard = self._catalog_revision()
            understanding_guard = self._understanding_revision()
            source_page = self._retired_source_catalog_page(offset=0, limit=50)
            review_page = self._retired_review_catalog_page(offset=0, limit=50)
            understanding_page = self.understanding_catalog_page(
                offset=0,
                limit=20,
            )
            status_counts = (
                self.store.source_catalog_status_counts()
                if self.store is not None
                else {
                    "total_count": 0,
                    "review_count": 0,
                    "disposition_counts": {},
                    "freshness_counts": {},
                    "depth_counts": {},
                }
            )
            catalog_after = self._catalog_revision()
            understanding_after = self._understanding_revision()
            if (
                catalog_guard
                == source_page["catalog_revision"]
                == review_page["catalog_revision"]
                == catalog_after
                and understanding_guard
                == understanding_page["understanding_revision"]
                == understanding_after
            ):
                break
        else:
            raise RuntimeError("source catalog changed during projection read")
        sources = tuple(source_page["items"])
        review_queue = tuple(review_page["items"])
        partition_progress = self._partition_inventory_progress()
        source_count = int(status_counts["total_count"])
        tracked_count = int(
            status_counts["disposition_counts"].get("tracked", 0)
        )
        review_count = int(status_counts["review_count"])
        understanding_count = int(
            understanding_page["total_count"]
        )
        pending_analysis_count = (
            self.operations.pending_packages(offset=0, limit=1)[1]
            if self.store is not None
            else 0
        )
        freshness_states = set(status_counts["freshness_counts"])
        depth_states = set(status_counts["depth_counts"])
        if "stale" in freshness_states:
            freshness_status = "stale"
        elif source_count:
            freshness_status = "current"
        else:
            freshness_status = "unknown"
        depth_priority = ("blocked", "stale", "partial", "not_assessed", "sufficient")
        depth_status = next(
            (item for item in depth_priority if item in depth_states),
            "not_assessed",
        )
        review_status = (
            "review_required"
            if review_count or understanding_count
            else "current"
        )
        latest_inventory = (
            self.store.latest("inventory_snapshot") if self.store else None
        )
        revision = (
            str(latest_inventory.get("snapshot_id"))
            if latest_inventory
            else "runtime:unconfigured"
        )
        catalog_revision = str(source_page["catalog_revision"])
        evidence_count = (
            self.store.count_current("evidence_anchor") if self.store else 0
        )
        gap_count = self.store.count_current("evidence_gap") if self.store else 0
        blocker_count = int(status_counts["depth_counts"].get("blocked", 0))
        partition_status = str(partition_progress["status"])
        partition_summary = {
            "not_configured": self._localized(
                "Private partition inventory is not configured",
                "尚未配置私有分区清单",
            ),
            "not_started": self._localized(
                "No large-root partition run is registered",
                "尚未登记大型目录分区扫描",
            ),
            "partial": self._localized(
                (
                    f"Filesystem inventory: "
                    f"{partition_progress['terminal_partition_count']}/"
                    f"{partition_progress['partition_count']} partitions"
                ),
                (
                    f"文件清单：已完成 "
                    f"{partition_progress['terminal_partition_count']}/"
                    f"{partition_progress['partition_count']} 个分区"
                ),
            ),
            "blocked": self._localized(
                (
                    f"Filesystem inventory is blocked in "
                    f"{partition_progress['failed_partition_count']} partitions"
                ),
                (
                    f"文件清单有 "
                    f"{partition_progress['failed_partition_count']} 个受阻分区"
                ),
            ),
            "complete": self._localized(
                (
                    f"Filesystem inventory: "
                    f"{partition_progress['terminal_partition_count']}/"
                    f"{partition_progress['partition_count']} partitions; "
                    "content completion is separate"
                ),
                (
                    f"文件清单："
                    f"{partition_progress['terminal_partition_count']}/"
                    f"{partition_progress['partition_count']} 个分区已完成；"
                    "内容处理进度另行计算"
                ),
            ),
        }[partition_status]
        return {
            "semantic_revision": revision,
            "catalog_revision": catalog_revision,
            "equivalence_status": "equivalent",
            "locale_revisions": {
                locale: revision
                for locale in self.locale_registry_owner.available_locales
            },
            "default_locale": self.locale_registry_owner.default_locale,
            "selected_locale": language,
            "available_locales": self.locale_registry_owner.available_locales,
            "locale_registry_revision": self.locale_registry_owner.revision,
            "scope": {
                "status": (
                    "active"
                    if self.config.private_status().status == "active"
                    else self.config.private_status().status
                ),
                "label": self._localized("Source scope", "资料范围"),
                "summary": self._localized(
                    (
                        f"{source_count} inventoried sources. "
                        f"{partition_summary['en']}"
                    ),
                    (
                        f"已登记 {source_count} 个来源。"
                        f"{partition_summary['zh-CN']}"
                    ),
                ),
                "partition_inventory": {
                    **partition_progress,
                    "label": partition_summary,
                },
            },
            "freshness": {
                "status": freshness_status,
                "label": state_localized(
                    freshness_status,
                    semantic_revision=revision,
                ),
                "summary": self._localized(
                    "Changed dependencies remain visible",
                    "发生变化的依赖会保持可见",
                ),
            },
            "depth": {
                "status": depth_status,
                "label": state_localized(
                    depth_status,
                    semantic_revision=revision,
                ),
                "summary": self._localized(
                    "Depth is assessed per source and revision",
                    "理解深度按来源和版本评估",
                ),
            },
            "review": {
                "status": review_status,
                "label": state_localized(
                    review_status,
                    semantic_revision=revision,
                ),
                "summary": self._localized(
                    (
                        f"{review_count + understanding_count} decisions "
                        "pending"
                    ),
                    f"有 {review_count + understanding_count} 项等待确认",
                ),
            },
            "summary": {
                "source_count": source_count,
                "tracked_count": tracked_count,
                "review_count": review_count,
                "understanding_count": understanding_count,
                "pending_analysis_count": pending_analysis_count,
            },
            "sources": sources,
            "review_queue": review_queue,
            "understanding_candidates": understanding_page["items"],
            "catalog": {
                "source": {
                    key: source_page[key]
                    for key in (
                        "offset",
                        "limit",
                        "total_count",
                        "next_offset",
                        "has_more",
                        "catalog_revision",
                    )
                },
                "review": {
                    key: review_page[key]
                    for key in (
                        "offset",
                        "limit",
                        "total_count",
                        "next_offset",
                        "has_more",
                        "catalog_revision",
                    )
                },
                "understanding": {
                    key: understanding_page[key]
                    for key in (
                        "offset",
                        "limit",
                        "total_count",
                        "next_offset",
                        "has_more",
                        "understanding_revision",
                    )
                },
            },
            "signals": {
                "evidence": (
                    (
                        {
                            "statement": self._localized(
                                f"{evidence_count} anchored evidence items",
                                f"有 {evidence_count} 条带定位证据",
                            ),
                            "evidence": (
                                {
                                    "title": self._localized(
                                        "Evidence coverage",
                                        "证据覆盖情况",
                                    ),
                                    "excerpt": self._localized(
                                        (
                                            f"{evidence_count} evidence items "
                                            "are anchored to private source "
                                            "material."
                                        ),
                                        (
                                            f"已有 {evidence_count} 条证据定位"
                                            "到私有来源材料。"
                                        ),
                                    ),
                                    "note": self._localized(
                                        (
                                            "Private content, local paths, "
                                            "raw receipts, and internal "
                                            "identifiers stay hidden."
                                        ),
                                        (
                                            "私有内容、本机路径、原始回执和"
                                            "内部编号保持隐藏。"
                                        ),
                                    ),
                                },
                            ),
                        },
                    )
                    if evidence_count
                    else ()
                ),
                "gaps": (
                    tuple(
                        item
                        for item in (
                        {
                            "statement": self._localized(
                                f"{gap_count} evidence gaps remain",
                                f"仍有 {gap_count} 个证据缺口",
                            )
                        }
                        if gap_count
                        else None,
                        {
                            "statement": self._localized(
                                (
                                    f"{pending_analysis_count} bounded AI "
                                    "work packages await understanding"
                                ),
                                (
                                    f"有 {pending_analysis_count} 个限定范围的 "
                                    "AI 工作包等待理解"
                                ),
                            )
                        }
                        if pending_analysis_count
                        else None,
                        )
                        if item is not None
                    )
                ),
                "blockers": (
                    (
                        {
                            "statement": self._localized(
                                f"{blocker_count} analysis blockers remain",
                                f"仍有 {blocker_count} 个分析阻碍",
                            )
                        },
                    )
                    if blocker_count
                    else ()
                ),
                "forecasts": (),
            },
        }

    def _retired_submit_tracking_intent(
        self,
        *,
        action_token: str,
        action: str,
        language: str = "en",
    ) -> dict[str, Any]:
        self.locale_registry_owner.require(language)
        if action not in {"track", "do_not_track", "defer", "restore"}:
            raise ValueError("unsupported tracking action")
        if self.inventory is None or self.store is None:
            raise RuntimeError("MATTERS_HOME is required for tracking changes")
        token_payload = self.store.current(
            "tracking_action_token",
            action_token,
        )
        if not token_payload or token_payload.get("active") is not True:
            raise ValueError("stale or invalid tracking action token")
        occurrence_id_value = str(token_payload.get("occurrence_id", ""))
        scope_id = str(token_payload.get("scope_id", ""))
        catalog = self.store.current("source_catalog", occurrence_id_value)
        if (
            not catalog
            or catalog.get("active") is not True
            or catalog.get("action_token") != action_token
            or catalog.get("scope_id") != scope_id
        ):
            raise ValueError("stale or invalid tracking action token")
        snapshot_payload = self.store.current("inventory_snapshot", scope_id)
        if snapshot_payload is None:
            raise RuntimeError("inventory snapshot is unavailable")
        snapshot = InventoryOwner._snapshot_from_payload(snapshot_payload)
        occurrences = {
            item.occurrence_id: item for item in snapshot.occurrences
        }
        dispositions = {
            item.occurrence_id: item for item in snapshot.dispositions
        }
        occurrence = occurrences.get(occurrence_id_value)
        if occurrence is None or occurrence_id_value not in dispositions:
            raise ValueError("stale or invalid tracking action token")
        scope_payload = self.store.current("candidate_scope", snapshot.scope_id)
        if scope_payload is None:
            raise RuntimeError("candidate scope is unavailable")
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
        policy_rows = self.store.list_current("tracking_policy")
        policy_payload = next(
            (
                item
                for item in policy_rows
                if int(item.get("revision", 0)) == snapshot.policy_revision
            ),
            None,
        )
        if policy_payload is None:
            raise RuntimeError("tracking policy is unavailable")
        policy = TrackingPolicy(
            policy_id=str(policy_payload["policy_id"]),
            revision=int(policy_payload["revision"]),
            protected_classes=tuple(policy_payload.get("protected_classes", ())),
            ignored_names=tuple(policy_payload.get("ignored_names", ())),
            archive_size_limit=int(policy_payload.get("archive_size_limit", 0)),
            changed_at=str(policy_payload.get("changed_at", "")),
        )
        intents = {
            item.occurrence_id: item.user_intent
            for item in snapshot.dispositions
            if item.user_intent
        }
        intents[occurrence.occurrence_id] = action
        self.reconcile_inventory(
            scope=scope,
            policy=policy,
            occurrences=snapshot.occurrences,
            user_intents=intents,
        )
        return self._retired_current_projection(language=language)

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
