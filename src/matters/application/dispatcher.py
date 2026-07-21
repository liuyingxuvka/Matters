"""Deterministic WorkPackageV2 dispatch to the existing C4-C9/C12 owners."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Any, Mapping

from matters.analysis.operations import (
    AdvisoryFinding,
    AgentOperationResult,
    AnalysisWorkPackage,
)
from matters.application.coverage_ledger import ObjectCoverageLedger
from matters.application.activity import MatterActivityOwner
from matters.application.hierarchy import MatterHierarchyOwner
from matters.application.reconciliation import MatterReconciliationOwner
from matters.domain.admission import MatterAdmission
from matters.domain.activity import MaterialClue
from matters.domain.context import (
    ContextSignal,
    GranularityAssessment,
    MAX_RECONCILIATION_CANDIDATES,
    MatterPlacementCandidate,
    MatterReconciliationRequest,
    MatterRelationshipHint,
    ProjectContext,
)
from matters.domain.hierarchy import (
    HierarchyMemberDisposition,
    MatterWorkItem,
)
from matters.domain.matters import Matter
from matters.identity.people import PersonRegistry
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.projections import ProjectionOwner
from matters.presentation.heroes import (
    GeneratedHeroOwner,
    HERO_GENERATION_POLICY_REVISION,
    HeroSubject,
)
from matters.presentation.visuals import VisualAssetOwner
from matters.state.lifecycle import LifecycleOwner, StateProofPacket
from matters.state.open_loops import OpenLoopOwner
from matters.state.outcomes import CompletionCriterion, OutcomeOwner
from matters.timeline.events import EventRegistry


_RECONCILIATION_RECALL_KIND_WEIGHTS = {
    "goal": 8,
    "outcome": 8,
    "repository_project": 6,
    "codex_workspace": 5,
    "provider_thread": 4,
    "subject": 3,
    "source_neighborhood": 2,
    "person": 1,
    "time": 1,
}


def _payload_fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _raise_source_revision_admission_conflict() -> dict[str, Any]:
    raise RuntimeError(
        "Matter admission changed during exact source revision adoption"
    )


@dataclass(frozen=True)
class DispatchOutcome:
    finding_id: str
    owner_model_id: str
    status: str
    owner_output_ref: str = ""
    failure_class: str = ""
    failure_detail: str = ""


class AutonomousFindingDispatcher:
    """C11 recommends; this dispatcher invokes exactly one original owner."""

    def __init__(
        self,
        *,
        store: SQLiteStore,
        coverage_ledger: ObjectCoverageLedger,
        people: PersonRegistry,
        events: EventRegistry,
        admission: MatterAdmission,
        lifecycle: LifecycleOwner,
        open_loops: OpenLoopOwner,
        outcomes: OutcomeOwner,
        projections: ProjectionOwner,
        visuals: VisualAssetOwner,
        hierarchy: MatterHierarchyOwner | None = None,
        reconciliation: MatterReconciliationOwner | None = None,
        activity: MatterActivityOwner | None = None,
        heroes: GeneratedHeroOwner | None = None,
    ) -> None:
        self.store = store
        self.coverage_ledger = coverage_ledger
        self.people = people
        self.events = events
        self.admission = admission
        self.lifecycle = lifecycle
        self.open_loops = open_loops
        self.outcomes = outcomes
        self.projections = projections
        self.visuals = visuals
        self.hierarchy = hierarchy
        self.reconciliation = reconciliation
        self.activity = activity
        self.heroes = heroes

    def dispatch(
        self,
        package: AnalysisWorkPackage,
        result: AgentOperationResult,
    ) -> tuple[DispatchOutcome, ...]:
        if (
            result.status != "passed"
            or not result.receipt_current
            or result.package_input_fingerprint != package.input_fingerprint
        ):
            outcomes = self._block_package(
                package,
                result,
                result.failure_class or "analysis_result_not_current",
            )
            self.coverage_ledger.refresh_summary()
            return outcomes
        object_ids = self._coverage_object_ids(package)
        if package.task_kind == "source_annotation":
            outcomes = tuple(
                self._persist_source_annotation(package, finding)
                for finding in result.findings
            )
            self._mark_result_dispatched(result, "annotation_current")
            self.coverage_ledger.refresh_summary()
            return outcomes
        for object_id in object_ids:
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="analysis",
                status="current",
                input_fingerprint=package.input_fingerprint,
                output_ref=result.result_id,
                refresh_summary=False,
            )
        if not result.findings:
            for object_id in object_ids:
                self.coverage_ledger.mark_stage(
                    object_id=object_id,
                    stage_id="owner_dispatch",
                    status="no_finding",
                    input_fingerprint=package.input_fingerprint,
                    output_ref=result.result_id,
                    refresh_summary=False,
                )
            self._mark_result_dispatched(result, "no_finding")
            self.coverage_ledger.refresh_summary()
            return ()

        owner_order = {
            "C6_matter_admission": 3,
            "C4_person_entity_resolution": 4,
            "C5_event_temporal_trace": 5,
            "C7_lifecycle_board_state": 7,
            "C8_open_loop_waiting_blocking": 8,
            "C9_completion_cancellation_reopen": 9,
            "C12_projection_bilingual_ui": 12,
        }
        findings = tuple(
            sorted(
                result.findings,
                key=lambda item: (
                    owner_order.get(item.owner_model_id, 99),
                    {
                        "matter_candidate": 0,
                        "work_item_candidate": 1,
                        "matter_hierarchy_candidate": 2,
                    }.get(item.finding_type, 3),
                    item.finding_id,
                ),
            )
        )
        outcomes = tuple(
            self._dispatch_once(
                package,
                finding,
                result_findings=findings,
            )
            for finding in findings
        )
        aggregate = (
            "blocked"
            if any(item.status == "blocked" for item in outcomes)
            else (
                "uncertain"
                if any(item.status == "uncertain" for item in outcomes)
                else "current"
            )
        )
        for object_id in object_ids:
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="owner_dispatch",
                status=aggregate,
                input_fingerprint=package.input_fingerprint,
                output_ref=",".join(item.owner_output_ref for item in outcomes),
                failure_class=(
                    "owner_dispatch_blocked" if aggregate == "blocked" else ""
                ),
                refresh_summary=False,
            )
        self._mark_result_dispatched(
            result,
            "blocked" if aggregate == "blocked" else "auto_applied",
        )
        self.coverage_ledger.refresh_summary()
        return outcomes

    def rebuild_distinct_title_summary_projection(
        self,
        projection: Mapping[str, Any],
        owner_records: tuple[Mapping[str, Any], ...],
        *,
        packages_by_id: Mapping[str, Mapping[str, Any] | None] | None = None,
    ) -> str:
        """Rebuild one current C12 projection from exact current owner rows.

        This is a projection-schema migration. It deliberately does not replay
        admission, hierarchy, lifecycle, or any other canonical owner.
        """

        matter_id = str(projection.get("matter_id", ""))
        semantic_revision = str(
            projection.get("semantic_revision", "")
        )
        if not matter_id or not semantic_revision:
            return "not_applicable"
        current = self.store.current("projection", matter_id)
        if current != dict(projection):
            return "conflicted"
        current_values = dict(current.get("localized_values", {}))
        current_summary = dict(
            current.get("localized_rationale", {})
        )
        current_evidence = tuple(
            str(item) for item in current.get("evidence_ids", ())
        )
        equivalence_status = str(
            current.get("equivalence_status", "")
        )

        candidate_summary_records = tuple(
            record
            for record in owner_records
            if self._current_owner_record(
                record,
                owner_model_id="C12_projection_bilingual_ui",
                owner_output_ref=None,
                finding_type="bounded_summary",
                semantic_revision=semantic_revision,
                packages_by_id=packages_by_id,
            )
            and tuple(
                str(item)
                for item in dict(record["finding"]).get(
                    "evidence_ids",
                    (),
                )
            )
            == current_evidence
        )
        summary_records = tuple(
            record
            for record in candidate_summary_records
            if str(record.get("owner_output_ref", ""))
            == f"projection:{matter_id}"
        )
        if (
            not summary_records
            and any(
                dict(dict(record["finding"]).get(
                    "localized_statement",
                    {},
                ))
                in (current_values, current_summary)
                for record in candidate_summary_records
            )
        ):
            return self._block_ambiguous_projection(
                current,
                matter_id,
            )
        pairs: list[
            tuple[
                Mapping[str, Any],
                Mapping[str, Any] | None,
                str,
            ]
        ] = []
        for summary_record in summary_records:
            summary_finding = dict(summary_record["finding"])
            localized_summary = dict(
                summary_finding.get("localized_statement", {})
            )
            package_id = str(summary_record.get("package_id", ""))
            title_records = tuple(
                record
                for record in owner_records
                if str(record.get("package_id", "")) == package_id
                and self._current_owner_record(
                    record,
                    owner_model_id="C6_matter_admission",
                    owner_output_ref=(
                        f"admission_decision:{matter_id}"
                    ),
                    finding_type="matter_candidate",
                    semantic_revision=semantic_revision,
                    packages_by_id=packages_by_id,
                )
            )
            title_record = (
                title_records[0] if len(title_records) == 1 else None
            )
            if (
                title_record is not None
                and localized_summary == current_summary
                and dict(
                    dict(title_record["finding"]).get(
                        "localized_statement",
                        {},
                    )
                )
                == current_values
                and equivalence_status == "equivalent"
            ):
                pair_kind = "target"
            elif (
                title_record is None
                and localized_summary == current_summary
            ):
                pair_kind = "owner_gap"
            elif (
                localized_summary == current_values
                or (
                    equivalence_status
                    == "blocked_missing_localized_title"
                    and localized_summary == current_summary
                )
            ):
                pair_kind = "legacy"
            else:
                pair_kind = "unrelated"
            pairs.append((summary_record, title_record, pair_kind))

        target_pairs = tuple(
            pair for pair in pairs if pair[2] == "target"
        )
        if len(target_pairs) == 1:
            return "unchanged"
        if len(target_pairs) > 1:
            return self._block_ambiguous_projection(current, matter_id)
        if any(pair[2] == "owner_gap" for pair in pairs):
            return self._block_ambiguous_projection(current, matter_id)

        legacy_pairs = tuple(
            pair for pair in pairs if pair[2] == "legacy"
        )
        if not legacy_pairs:
            if (
                equivalence_status
                == "blocked_missing_localized_title"
            ):
                return "blocked"
            return "not_applicable"
        if (
            len(legacy_pairs) != 1
            or legacy_pairs[0][1] is None
        ):
            return self._block_ambiguous_projection(current, matter_id)

        summary_record, title_record, _kind = legacy_pairs[0]
        summary_finding = dict(summary_record["finding"])
        title_finding = dict(title_record["finding"])
        rebuilt = self.projections.publish(
            matter_id=matter_id,
            semantic_revision=semantic_revision,
            state=str(current.get("state", "uncertain")),
            rationale=str(summary_finding.get("statement", "")),
            evidence_ids=current_evidence,
            localized_values=dict(
                title_finding.get("localized_statement", {})
            ),
            localized_rationale=dict(
                summary_finding.get("localized_statement", {})
            ),
        )
        try:
            write = self._compare_projection_migration(
                expected_current=current,
                desired=asdict(rebuilt),
                matter_id=matter_id,
            )
        except RuntimeError:
            return "conflicted"
        return (
            "unchanged"
            if write["status"] == "current"
            else "migrated"
        )

    def _current_owner_record(
        self,
        record: Mapping[str, Any],
        *,
        owner_model_id: str,
        owner_output_ref: str | None,
        finding_type: str,
        semantic_revision: str,
        packages_by_id: Mapping[str, Mapping[str, Any] | None] | None = None,
    ) -> bool:
        finding = record.get("finding")
        if not isinstance(finding, Mapping):
            return False
        package_id = str(record.get("package_id", ""))
        package = (
            packages_by_id.get(package_id)
            if packages_by_id is not None
            else self.store.current(
                "analysis_work_package",
                package_id,
            )
        )
        allowed_statuses = (
            {"auto_applied"}
            if owner_model_id == "C12_projection_bilingual_ui"
            else {"auto_applied", "uncertain"}
        )
        return bool(
            package is not None
            and str(record.get("owner_model_id", ""))
            == owner_model_id
            and str(record.get("status", ""))
            in allowed_statuses
            and (
                owner_output_ref is None
                or str(record.get("owner_output_ref", ""))
                == owner_output_ref
            )
            and str(record.get("package_input_fingerprint", ""))
            == str(package.get("input_fingerprint", ""))
            and str(finding.get("finding_type", ""))
            == finding_type
            and str(finding.get("owner_model_id", ""))
            == owner_model_id
            and str(finding.get("semantic_revision", ""))
            == semantic_revision
        )

    def _block_ambiguous_projection(
        self,
        current: Mapping[str, Any],
        matter_id: str,
    ) -> str:
        blocked = dict(current)
        blocked["equivalence_status"] = (
            "blocked_missing_localized_title"
        )
        try:
            self._compare_projection_migration(
                expected_current=current,
                desired=blocked,
                matter_id=matter_id,
            )
        except RuntimeError:
            return "conflicted"
        return "blocked"

    def _compare_projection_migration(
        self,
        *,
        expected_current: Mapping[str, Any],
        desired: Mapping[str, Any],
        matter_id: str,
    ) -> dict[str, Any]:
        expected = dict(expected_current)
        target = dict(desired)

        def build(
            _revision: int,
            observed: dict[str, Any] | None,
        ) -> dict[str, Any]:
            if observed != expected:
                raise RuntimeError(
                    "projection changed during title-summary migration"
                )
            return target

        return self.store.compare_current_and_append(
            "projection",
            matter_id,
            is_equivalent=lambda observed: observed == target,
            payload_factory=build,
        )

    def _persist_source_annotation(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
    ) -> DispatchOutcome:
        if (
            finding.finding_type != "source_annotation"
            or finding.owner_model_id
            != "A0_matters_source_analysis_operation"
        ):
            raise ValueError("source annotation owner mismatch")
        self.store.append(
            "source_annotation",
            finding.finding_id,
            self.store.next_revision(
                "source_annotation",
                finding.finding_id,
            ),
            {
                "finding": asdict(finding),
                "package_id": package.package_id,
                "package_input_fingerprint": package.input_fingerprint,
                "capability_role": package.capability_role,
                "source_revision_ids": package.source_revision_ids,
            },
        )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied",
            f"source_annotation:{finding.finding_id}",
        )

    def _block_package(
        self,
        package: AnalysisWorkPackage,
        result: AgentOperationResult,
        failure_class: str,
    ) -> tuple[DispatchOutcome, ...]:
        for object_id in self._coverage_object_ids(package):
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="analysis",
                status="blocked",
                input_fingerprint=package.input_fingerprint,
                output_ref=result.result_id,
                failure_class=failure_class,
                refresh_summary=False,
            )
            self.coverage_ledger.mark_stage(
                object_id=object_id,
                stage_id="owner_dispatch",
                status="blocked",
                input_fingerprint=package.input_fingerprint,
                output_ref=result.result_id,
                failure_class=failure_class,
                refresh_summary=False,
            )
        self._mark_result_dispatched(result, "blocked")
        return ()

    def _dispatch_once(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        prior = self.store.current("autonomous_finding", finding.finding_id)
        if (
            prior is not None
            and str(prior.get("package_input_fingerprint"))
            == package.input_fingerprint
            and str(prior.get("status"))
            in {"auto_applied", "uncertain", "no_finding"}
        ):
            return DispatchOutcome(
                finding_id=finding.finding_id,
                owner_model_id=finding.owner_model_id,
                status=str(prior["status"]),
                owner_output_ref=str(prior.get("owner_output_ref", "")),
                failure_class=str(prior.get("failure_class", "")),
                failure_detail=str(prior.get("failure_detail", "")),
            )
        try:
            outcome = self._invoke_owner(
                package,
                finding,
                result_findings=result_findings,
            )
        except Exception as exc:
            outcome = DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "blocked",
                failure_class=type(exc).__name__,
                failure_detail=str(exc),
            )
        self.store.append(
            "autonomous_finding",
            finding.finding_id,
            self.store.next_revision("autonomous_finding", finding.finding_id),
            {
                "finding": asdict(finding),
                "finding_id": finding.finding_id,
                "package_id": package.package_id,
                "package_input_fingerprint": package.input_fingerprint,
                "owner_model_id": finding.owner_model_id,
                "status": outcome.status,
                "owner_output_ref": outcome.owner_output_ref,
                "failure_class": outcome.failure_class,
                "failure_detail": outcome.failure_detail,
            },
        )
        return outcome

    def _invoke_owner(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        if (
            package.task_kind
            in {"source_revision_matter_refresh", "matter_semantic_refresh"}
            and finding.finding_type == "matter_candidate"
        ):
            declared_matter_id = str(
                finding.attributes.get("matter_id", "")
            ).strip()
            if (
                not package.matter_id
                or (
                    declared_matter_id
                    and declared_matter_id != package.matter_id
                )
            ):
                raise ValueError(
                    "Matter semantic refresh finding escaped its exact Matter"
                )
        owner = finding.owner_model_id
        if owner == "C4_person_entity_resolution":
            return self._c4(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C5_event_temporal_trace":
            return self._c5(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C6_matter_admission":
            return self._c6(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C7_lifecycle_board_state":
            return self._c7(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C8_open_loop_waiting_blocking":
            return self._c8(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C9_completion_cancellation_reopen":
            return self._c9(
                package,
                finding,
                result_findings=result_findings,
            )
        if owner == "C12_projection_bilingual_ui":
            return self._c12(
                package,
                finding,
                result_findings=result_findings,
            )
        raise ValueError("unregistered original owner")

    def _c4(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        name = str(attributes.get("display_name", "")).strip()
        if not name:
            name = finding.localized_statement["en"]
        matter_id = self._matter_id(
            package,
            finding,
            result_findings=result_findings,
        )
        source_mention_id = str(
            attributes.get("source_mention_id", finding.finding_id)
        ).strip()
        candidate = self.people.candidate(name, source_mention_id)
        resolved = self.people.assert_identity(
            candidate,
            strong_link_evidence=bool(
                attributes.get("strong_link_evidence", False)
            ),
        )
        role_name = str(
            attributes.get("role", "relevant_person")
        ).strip() or "relevant_person"
        role = self.people.matter_role(
            resolved,
            matter_id,
            role_name,
            finding.evidence_ids,
        )
        self.store.append(
            "person_candidate",
            resolved.person_id,
            self.store.next_revision("person_candidate", resolved.person_id),
            {
                **asdict(resolved),
                "matter_id": matter_id,
                "matter_ids": (matter_id,),
                "role": role_name,
                "evidence_ref": (
                    finding.evidence_ids[0]
                    if finding.evidence_ids
                    else ""
                ),
                "evidence_ids": finding.evidence_ids,
                "semantic_revision": finding.semantic_revision,
            },
        )
        role_id = (
            "matter-role:"
            + sha256(
                (
                    f"{resolved.person_id}\0{matter_id}\0{role_name}"
                ).encode("utf-8")
            ).hexdigest()[:24]
        )
        self.store.append(
            "matter_role",
            role_id,
            self.store.next_revision("matter_role", role_id),
            {
                "role_id": role_id,
                **asdict(role),
                "semantic_revision": finding.semantic_revision,
            },
        )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied" if resolved.resolved else "uncertain",
            f"person_candidate:{resolved.person_id}",
        )

    def _c5(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        if finding.finding_type == "material_clue_candidate":
            if self.activity is None:
                raise ValueError("Matter activity owner is unavailable")
            matter_id = self._matter_id(
                package,
                finding,
                result_findings=result_findings,
            )
            clue_kwargs: dict[str, Any] = {
                "clue_id": str(
                    attributes.get("clue_id") or finding.finding_id
                ),
                "matter_id": matter_id,
                "clue_kind": str(
                    attributes.get("clue_kind", "semantic_event")
                ),
                "user_world_at": str(
                    attributes.get("user_world_at")
                    or attributes.get("claimed_time")
                    or attributes.get("record_time")
                ),
                "disposition": str(
                    attributes.get("disposition", "uncertain")
                ),
                "rationale": finding.statement,
                "localized_summary": finding.localized_statement,
                "semantic_revision": finding.semantic_revision,
                "evidence_ids": finding.evidence_ids,
            }
            if str(attributes.get("processed_at", "")).strip():
                clue_kwargs["processed_at"] = str(
                    attributes["processed_at"]
                )
            update = self.activity.record(MaterialClue(**clue_kwargs))
            for coverage_id in self._coverage_object_ids(package):
                self.coverage_ledger.mark_stage(
                    object_id=coverage_id,
                    stage_id="meaningful_clue_summary",
                    status=(
                        "current"
                        if update.disposition == "material"
                        else (
                            "uncertain"
                            if update.disposition == "uncertain"
                            else "no_finding"
                        )
                    ),
                    input_fingerprint=package.input_fingerprint,
                    output_ref=f"matter_activity_clue:{update.clue_id}",
                    matter_ids=(matter_id,),
                    refresh_summary=False,
                )
            self._advance_ui_reachability(package, matter_id)
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                (
                    "auto_applied"
                    if update.disposition in {"material", "nonmaterial"}
                    else "uncertain"
                ),
                f"matter_activity_clue:{update.clue_id}",
            )
        object_ref = str(attributes.get("object_ref", "")).strip()
        if not object_ref:
            object_ref = self._matter_id(
                package,
                finding,
                result_findings=result_findings,
            )
        event_kind = (
            "deadline"
            if finding.finding_type == "deadline_candidate"
            else str(attributes.get("event_kind", "semantic_event"))
        )
        claimed_time = str(
            attributes.get("claimed_time", attributes.get("deadline", ""))
        )
        record_time = str(attributes.get("record_time", ""))
        actor = str(attributes.get("actor", ""))
        logical_event_key = str(attributes.get("logical_event_key", ""))
        occurrence_boundary = str(
            attributes.get("occurrence_boundary", "")
        )
        supersedes_event_id = str(
            attributes.get("supersedes_event_id", "")
        )
        temporal_direction = str(
            attributes.get("temporal_direction", "")
        )
        inference_purpose = str(
            attributes.get("inference_purpose", "")
        )
        inference_as_of = str(attributes.get("inference_as_of", ""))
        target_time = str(attributes.get("target_time", ""))
        revisable = bool(attributes.get("revisable", False))
        inference_confidence = (
            str(attributes.get("inference_confidence", finding.confidence))
            if finding.modality == "inferred"
            else ""
        )
        supporting_signals = tuple(
            str(item)
            for item in attributes.get("supporting_signals", ())
            if str(item).strip()
        )
        counter_signals = tuple(
            str(item)
            for item in attributes.get("counter_signals", ())
            if str(item).strip()
        )
        coverage_boundary = str(attributes.get("coverage_boundary", ""))
        alternative_explanations = tuple(
            str(item)
            for item in (
                attributes.get("alternative_explanations")
                or finding.alternative_explanations
            )
            if str(item).strip()
        )
        contradiction_triggers = tuple(
            str(item)
            for item in attributes.get(
                "contradiction_triggers",
                (),
            )
        )
        expires_at = str(attributes.get("expires_at", ""))
        if finding.modality != "inferred":
            # Alternative interpretations may accompany a reported or observed
            # finding for review, but C5 inference-contract fields must never
            # turn that source-reported occurrence into an inferred Event.
            inference_purpose = ""
            inference_as_of = ""
            target_time = ""
            revisable = False
            inference_confidence = ""
            supporting_signals = ()
            counter_signals = ()
            coverage_boundary = ""
            alternative_explanations = ()
            contradiction_triggers = ()
            expires_at = ""
        revision_event_id = str(
            attributes.get("revision_event_id", "")
        ).strip()
        if revision_event_id:
            current_event = self.store.current(
                "temporal_event",
                revision_event_id,
            )
            if current_event is None:
                raise ValueError("event revision target is unavailable")
            if str(current_event.get("object_ref", "")) != object_ref:
                raise ValueError(
                    "event revision target belongs to another Matter"
                )
            event = self.events.revise_existing(
                event_id=revision_event_id,
                kind=event_kind,
                claimed_time=claimed_time,
                record_time=record_time,
                actor=actor,
                object_ref=object_ref,
                evidence_ids=finding.evidence_ids,
                modality=finding.modality,
                logical_event_key=logical_event_key,
                occurrence_boundary=occurrence_boundary,
                supersedes_event_id=supersedes_event_id,
                temporal_direction=temporal_direction,
                inference_purpose=inference_purpose,
                inference_as_of=inference_as_of,
                target_time=target_time,
                revisable=revisable,
                inference_confidence=inference_confidence,
                supporting_signals=supporting_signals,
                counter_signals=counter_signals,
                coverage_boundary=coverage_boundary,
                alternative_explanations=alternative_explanations,
                contradiction_triggers=contradiction_triggers,
                expires_at=expires_at,
            )
        else:
            event = self.events.from_understanding(
                kind=event_kind,
                source_revision=finding.semantic_revision,
                claimed_time=claimed_time,
                record_time=record_time,
                actor=actor,
                object_ref=object_ref,
                evidence_ids=finding.evidence_ids,
                modality=finding.modality,
                logical_event_key=logical_event_key,
                occurrence_boundary=occurrence_boundary,
                supersedes_event_id=supersedes_event_id,
                temporal_direction=temporal_direction,
                inference_purpose=inference_purpose,
                inference_as_of=inference_as_of,
                target_time=target_time,
                revisable=revisable,
                inference_confidence=inference_confidence,
                supporting_signals=supporting_signals,
                counter_signals=counter_signals,
                coverage_boundary=coverage_boundary,
                alternative_explanations=alternative_explanations,
                contradiction_triggers=contradiction_triggers,
                expires_at=expires_at,
            )
        self.store.append(
            "temporal_event",
            event.event_id,
            self.store.next_revision("temporal_event", event.event_id),
            {
                **asdict(event),
                "localized_sentence": dict(finding.localized_statement),
            },
        )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "uncertain" if finding.confidence == "low" else "auto_applied",
            f"temporal_event:{event.event_id}",
        )

    def _c6(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        if (
            package.task_kind == "matter_semantic_refresh"
            and finding.finding_type == "matter_candidate"
        ):
            matter_id = package.matter_id.strip()
            admission = self.store.current("admission_decision", matter_id)
            admitted_matter = (
                admission.get("matter")
                if isinstance(admission, Mapping)
                else None
            )
            semantic_identity_key = str(
                attributes.get("semantic_identity_key", "")
            ).strip()
            current_source_refs = tuple(sorted(package.source_revision_ids))
            if (
                not matter_id
                or not isinstance(admission, Mapping)
                or str(admission.get("status", "")) != "admitted"
                or not isinstance(admitted_matter, Mapping)
                or str(admitted_matter.get("matter_id", "")) != matter_id
                or admitted_matter.get("admitted") is False
                or not semantic_identity_key
                or semantic_identity_key
                != str(admitted_matter.get("semantic_identity_id", ""))
                or package.matter_revision != _payload_fingerprint(admission)
                or len(current_source_refs) < 2
                or tuple(package.source_revision_ids) != current_source_refs
                or not set(finding.evidence_ids).issubset(
                    set(package.allowed_evidence_ids)
                )
            ):
                raise ValueError(
                    "Matter semantic refresh requires the exact current "
                    "admitted Matter identity"
                )
            source_ids = set()
            for source_ref in current_source_refs:
                source_id, separator, raw_version = source_ref.rpartition(":v")
                if (
                    not separator
                    or not source_id
                    or not raw_version.isdigit()
                ):
                    raise ValueError("Matter semantic refresh source is invalid")
                current_source = self.store.current("source_version", source_id)
                if (
                    current_source is None
                    or int(current_source.get("version", 0)) != int(raw_version)
                    or bool(current_source.get("tombstone", False))
                ):
                    raise ValueError(
                        "Matter semantic refresh is not registry-current"
                    )
                source_ids.add(source_id)
            evidence_source_ids = set()
            for evidence_id in package.allowed_evidence_ids:
                anchor = self.store.current("evidence_anchor", evidence_id)
                if (
                    anchor is None
                    or not bool(anchor.get("current", True))
                    or str(anchor.get("source_id", "")) not in source_ids
                ):
                    raise ValueError(
                        "Matter semantic refresh evidence is not current"
                    )
                evidence_source_ids.add(str(anchor.get("source_id", "")))
            if evidence_source_ids != source_ids:
                raise ValueError(
                    "Matter semantic refresh lacks current evidence for a source"
                )
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"admission_decision:{matter_id}",
            )
        if (
            package.task_kind == "source_revision_matter_refresh"
            and finding.finding_type == "matter_candidate"
        ):
            matter_id = package.matter_id.strip()
            admission = self.store.current("admission_decision", matter_id)
            admitted_matter = (
                admission.get("matter")
                if isinstance(admission, Mapping)
                else None
            )
            semantic_identity_key = str(
                attributes.get("semantic_identity_key", "")
            ).strip()
            if (
                not matter_id
                or not isinstance(admission, Mapping)
                or str(admission.get("status", "")) != "admitted"
                or not isinstance(admitted_matter, Mapping)
                or str(admitted_matter.get("matter_id", "")) != matter_id
                or admitted_matter.get("admitted") is False
                or not semantic_identity_key
                or semantic_identity_key
                != str(admitted_matter.get("semantic_identity_id", ""))
                or package.matter_revision
                != _payload_fingerprint(admission)
                or len(package.source_revision_ids) != 1
            ):
                raise ValueError(
                    "source revision refresh requires the exact current "
                    "admitted Matter identity"
                )
            source_ref = package.source_revision_ids[0]
            source_id, separator, raw_version = source_ref.rpartition(":v")
            if (
                not separator
                or not source_id
                or not raw_version.isdigit()
            ):
                raise ValueError("source revision refresh source is invalid")
            source_version = int(raw_version)
            current_source = self.store.current("source_version", source_id)
            if (
                current_source is None
                or int(current_source.get("version", 0)) != source_version
                or bool(current_source.get("tombstone", False))
            ):
                raise ValueError(
                    "source revision refresh is not registry-current"
                )
            if not finding.evidence_ids:
                raise ValueError(
                    "source revision refresh requires current evidence"
                )
            for evidence_id in finding.evidence_ids:
                anchor = self.store.current("evidence_anchor", evidence_id)
                if (
                    anchor is None
                    or str(anchor.get("source_id", "")) != source_id
                    or int(anchor.get("source_version", 0))
                    != source_version
                    or not bool(anchor.get("current", True))
                ):
                    raise ValueError(
                        "source revision refresh evidence is not current"
                    )
            expected = dict(admission)
            desired = json.loads(json.dumps(admission, ensure_ascii=False))
            desired_matter = desired["matter"]
            desired_matter["source_ids"] = list(
                dict.fromkeys(
                    (
                        *desired_matter.get("source_ids", ()),
                        source_ref,
                    )
                )
            )
            desired_matter["evidence_ids"] = list(
                dict.fromkeys(
                    (
                        *desired_matter.get("evidence_ids", ()),
                        *finding.evidence_ids,
                    )
                )
            )
            self.store.compare_current_and_append(
                "admission_decision",
                matter_id,
                is_equivalent=lambda current: current == desired,
                payload_factory=lambda _revision, current: (
                    desired
                    if current == expected
                    else _raise_source_revision_admission_conflict()
                ),
            )
            self.admission.restore(
                Matter(
                    matter_id=matter_id,
                    source_ids=tuple(desired_matter["source_ids"]),
                    rationale=str(
                        desired_matter.get(
                            "rationale",
                            "current evidence licenses admission",
                        )
                    ),
                    evidence_ids=tuple(desired_matter["evidence_ids"]),
                    semantic_identity_id=semantic_identity_key,
                )
            )
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"admission_decision:{matter_id}",
            )
        if package.task_kind == "matter_projection_repair":
            matter_id = package.matter_id.strip()
            admission = self.store.current("admission_decision", matter_id)
            admitted_matter = (
                admission.get("matter")
                if isinstance(admission, Mapping)
                else None
            )
            semantic_identity_key = str(
                attributes.get("semantic_identity_key", "")
            ).strip()
            admitted_evidence_ids = (
                {
                    str(item)
                    for item in admitted_matter.get("evidence_ids", ())
                    if str(item)
                }
                if isinstance(admitted_matter, Mapping)
                else set()
            )
            if (
                finding.finding_type != "matter_candidate"
                or not matter_id
                or not isinstance(admission, Mapping)
                or str(admission.get("status", "")) != "admitted"
                or not isinstance(admitted_matter, Mapping)
                or str(admitted_matter.get("matter_id", "")) != matter_id
                or admitted_matter.get("admitted") is False
                or not semantic_identity_key
                or semantic_identity_key
                != str(admitted_matter.get("semantic_identity_id", ""))
                or not set(finding.evidence_ids).issubset(
                    admitted_evidence_ids
                )
            ):
                raise ValueError(
                    "projection repair requires the exact current admitted "
                    "Matter identity and evidence"
                )
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"admission_decision:{matter_id}",
            )
        if finding.finding_type == "work_item_candidate":
            if self.hierarchy is None:
                raise ValueError("Matter hierarchy owner is unavailable")
            matter_id = self._matter_id(
                package,
                finding,
                result_findings=result_findings,
            )
            semantic_role_key = str(
                attributes.get("semantic_role_key", "")
            ).strip().casefold()
            item_id = str(attributes.get("item_id", "")).strip()
            if not item_id:
                identity_seed = (
                    f"semantic-role:{semantic_role_key}"
                    if semantic_role_key
                    else f"finding:{finding.finding_id}"
                )
                item_id = (
                    "work-item:"
                    + sha256(
                        f"{matter_id}\0{identity_seed}".encode("utf-8")
                    ).hexdigest()[:24]
                )
            localized_result = attributes.get("localized_result")
            if not isinstance(localized_result, Mapping):
                localized_result = finding.localized_statement
            item = self.hierarchy.save_work_item(
                MatterWorkItem(
                    item_id=item_id,
                    matter_id=matter_id,
                    kind=str(attributes.get("kind", "action")),
                    status=str(attributes.get("status", "uncertain")),
                    localized_title=finding.localized_statement,
                    localized_result={
                        str(key): str(value)
                        for key, value in localized_result.items()
                    },
                    semantic_role_key=semantic_role_key,
                    evidence_ids=finding.evidence_ids,
                    source_ids=package.source_revision_ids,
                    planned_start=str(attributes.get("planned_start", "")),
                    planned_end=str(attributes.get("planned_end", "")),
                    actual_start=str(attributes.get("actual_start", "")),
                    actual_end=str(attributes.get("actual_end", "")),
                    required_for_parent=bool(
                        attributes.get("required_for_parent", False)
                    ),
                    material_stage=bool(
                        attributes.get(
                            "material_stage",
                            attributes.get("required_for_parent", False),
                        )
                    ),
                    basis_modality=(
                        "ai_inferred"
                        if finding.modality == "inferred"
                        else finding.modality
                    ),
                    basis_scope=str(
                        attributes.get(
                            "basis_scope",
                            (
                                attributes.get("inference_purpose", "")
                                if finding.modality == "inferred"
                                else (
                                    "source_record"
                                    if finding.modality
                                    in {"observed", "reported"}
                                    else ""
                                )
                            ),
                        )
                    ).replace("historical_gap_fill", "historical_gap"),
                    temporal_assertion=str(
                        attributes.get(
                            "temporal_assertion",
                            (
                                "planned"
                                if str(attributes.get("status", ""))
                                == "planned"
                                else (
                                    "ongoing"
                                    if str(attributes.get("status", ""))
                                    == "in_progress"
                                    else (
                                        "occurred"
                                        if str(attributes.get("status", ""))
                                        in {"completed", "cancelled"}
                                        else "unknown"
                                    )
                                )
                            ),
                        )
                    ),
                    terminality=str(
                        attributes.get(
                            "terminality",
                            (
                                "provisional"
                                if finding.modality == "inferred"
                                else "confirmed"
                            ),
                        )
                    ),
                    confidence=finding.confidence,
                    inference_as_of=str(
                        attributes.get("inference_as_of", "")
                    ),
                    target_time=str(attributes.get("target_time", "")),
                    prerequisite_evidence_ids=tuple(
                        str(value)
                        for value in attributes.get(
                            "prerequisite_evidence_ids",
                            (),
                        )
                        if str(value).strip()
                    ),
                    remaining_obligation_ids=tuple(
                        str(value)
                        for value in attributes.get(
                            "remaining_obligation_ids",
                            (),
                        )
                        if str(value).strip()
                    ),
                    active_window_start=str(
                        attributes.get("active_window_start", "")
                    ),
                    active_window_end=str(
                        attributes.get("active_window_end", "")
                    ),
                    contradiction_checked=bool(
                        attributes.get("contradiction_checked", False)
                    ),
                    coverage_boundary=str(
                        attributes.get("coverage_boundary", "")
                    ),
                    supporting_signals=tuple(
                        str(value)
                        for value in attributes.get(
                            "supporting_signals",
                            finding.evidence_ids,
                        )
                        if str(value).strip()
                    ),
                    counter_signals=tuple(
                        str(value)
                        for value in attributes.get("counter_signals", ())
                        if str(value).strip()
                    ),
                    alternative_explanations=tuple(
                        str(value)
                        for value in (
                            attributes.get("alternative_explanations")
                            or finding.alternative_explanations
                        )
                        if str(value).strip()
                    ),
                    contradiction_triggers=tuple(
                        str(value)
                        for value in attributes.get(
                            "contradiction_triggers",
                            (),
                        )
                        if str(value).strip()
                    ),
                    expires_at=str(attributes.get("expires_at", "")),
                    freshness="current",
                ),
                supersedes_item_ids=tuple(
                    str(value).strip()
                    for value in attributes.get(
                        "supersedes_item_ids",
                        (),
                    )
                    if str(value).strip()
                ),
            )
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"matter_work_item:{item.item_id}",
            )
        if finding.finding_type == "matter_hierarchy_candidate":
            if self.hierarchy is None:
                raise ValueError("Matter hierarchy owner is unavailable")
            change_kind = str(attributes.get("change_kind", "attach"))
            child_id = str(
                attributes.get("child_matter_id")
                or self._matter_id(
                    package,
                    finding,
                    result_findings=result_findings,
                )
            )
            rationale = finding.statement
            if change_kind in {"attach", "role_change"}:
                revision = self.hierarchy.attach_child(
                    parent_matter_id=str(attributes["parent_matter_id"]),
                    child_matter_id=child_id,
                    role=str(attributes.get("role", "optional")),
                    confidence=str(attributes.get("confidence", finding.confidence)),
                    rationale=rationale,
                    evidence_ids=finding.evidence_ids,
                    ordinal=int(attributes.get("ordinal", 0)),
                )
            elif change_kind == "reparent":
                revision = self.hierarchy.reparent_child(
                    child_matter_id=child_id,
                    expected_parent_matter_id=str(
                        attributes["expected_parent_matter_id"]
                    ),
                    new_parent_matter_id=str(attributes["parent_matter_id"]),
                    role=str(attributes.get("role", "optional")),
                    confidence=str(attributes.get("confidence", finding.confidence)),
                    rationale=rationale,
                    evidence_ids=finding.evidence_ids,
                    ordinal=int(attributes.get("ordinal", 0)),
                )
            elif change_kind == "detach":
                revision = self.hierarchy.detach_child(
                    child_matter_id=child_id,
                    expected_parent_matter_id=str(
                        attributes["expected_parent_matter_id"]
                    ),
                    rationale=rationale,
                    evidence_ids=finding.evidence_ids,
                )
            elif change_kind in {"split", "merge"}:
                dispositions = tuple(
                    HierarchyMemberDisposition(
                        member_kind=str(item["member_kind"]),
                        member_id=str(item["member_id"]),
                        action=str(item["action"]),
                        target_matter_ids=tuple(
                            item.get("target_matter_ids", ())
                        ),
                        evidence_ids=tuple(item.get("evidence_ids", ())),
                    )
                    for item in attributes.get("dispositions", ())
                    if isinstance(item, Mapping)
                )
                revision = self.hierarchy.record_split_or_merge(
                    change_kind=change_kind,
                    subject_matter_ids=tuple(
                        attributes.get("subject_matter_ids", (child_id,))
                    ),
                    rationale=rationale,
                    evidence_ids=finding.evidence_ids,
                    dispositions=dispositions,
                )
                self.apply_hierarchy_revision(revision)
            else:
                raise ValueError("unsupported hierarchy change kind")
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"matter_hierarchy_revision:{revision.revision_id}",
            )
        semantic_identity_key = str(
            attributes.get("semantic_identity_key")
            or finding.statement
        ).strip()
        context_signals = self._context_signals(
            attributes,
            finding=finding,
            semantic_identity_key=semantic_identity_key,
        )
        context = ProjectContext(
            signals=context_signals,
            revision=int(attributes.get("context_revision", 1)),
            freshness=str(attributes.get("context_freshness", "current")),
        )
        candidates = self._placement_candidates(context)
        candidate_ids = {
            candidate.matter_id for candidate in candidates
        }
        relationship_hints = tuple(
            MatterRelationshipHint(
                target_matter_id=str(item.get("target_matter_id", "")),
                relation_type=str(item.get("relation_type", "related")),
                evidence_ids=tuple(
                    str(evidence_id)
                    for evidence_id in item.get(
                        "evidence_ids",
                        finding.evidence_ids,
                    )
                ),
            )
            for item in attributes.get("relationship_hints", ())
            if isinstance(item, Mapping)
            and str(item.get("target_matter_id", "")) in candidate_ids
        )
        granularity_payload = attributes.get("granularity", {})
        if not isinstance(granularity_payload, Mapping):
            granularity_payload = {}
        granularity = GranularityAssessment(
            independently_useful_goal=bool(
                granularity_payload.get(
                    "independently_useful_goal",
                    attributes.get("explicit_goal_or_obligation", False),
                )
            ),
            independently_useful_state=bool(
                granularity_payload.get("independently_useful_state", False)
            ),
            independently_useful_outcome=bool(
                granularity_payload.get("independently_useful_outcome", False)
            ),
            independently_useful_next_step=bool(
                granularity_payload.get(
                    "independently_useful_next_step",
                    False,
                )
            ),
            bounded_task=bool(granularity_payload.get("bounded_task", False)),
            one_time_occurrence=bool(
                granularity_payload.get("one_time_occurrence", False)
            ),
        )
        reconciliation_request = MatterReconciliationRequest(
            source_ids=package.source_revision_ids,
            evidence_ids=finding.evidence_ids,
            semantic_identity_key=semantic_identity_key,
            context=context,
            candidates=candidates,
            relationship_hints=relationship_hints,
            granularity=granularity,
            access_blocked=bool(attributes.get("access_blocked", False)),
            conflict=bool(attributes.get("conflict", False)),
            revision=int(attributes.get("reconciliation_revision", 1)),
        )
        reconciliation_execution = (
            self.reconciliation.resolve(
                reconciliation_request,
                useful_content=bool(attributes.get("useful_content", True)),
                possibility_only=bool(
                    attributes.get("possibility_only", False)
                ),
            )
            if self.reconciliation is not None
            else None
        )
        placement = (
            reconciliation_execution.decision
            if reconciliation_execution is not None
            else None
        )
        if placement is not None:
            self.store.append(
                "matter_placement_decision",
                finding.finding_id,
                self.store.next_revision(
                    "matter_placement_decision",
                    finding.finding_id,
                ),
                asdict(placement),
            )
        if reconciliation_execution is None:
            raise ValueError("C6 reconciliation owner is unavailable")
        decision = reconciliation_execution.admission
        if decision is None:
            raise ValueError("C6 reconciliation did not produce an admission decision")
        object_id = (
            decision.matter.matter_id
            if decision.matter is not None
            else (
                decision.candidate.candidate_id
                if decision.candidate is not None
                else package.package_id
            )
        )
        self.store.append(
            "admission_decision",
            object_id,
            self.store.next_revision("admission_decision", object_id),
            asdict(decision),
        )
        if decision.matter is not None:
            if (
                self.coverage_ledger.current(
                    decision.matter.matter_id
                )
                is None
            ):
                self.coverage_ledger.register_matters(
                    matters=(
                        {
                            "matter_id": decision.matter.matter_id,
                            "matter_kind": (
                                "child_matter"
                                if (
                                    placement is not None
                                    and placement.status == "admit_child"
                                )
                                else "root_matter"
                            ),
                            "semantic_revision": (
                                finding.semantic_revision
                            ),
                            "hierarchy_revision": (
                                f"reconciliation:{finding.finding_id}"
                            ),
                        },
                    ),
                    refresh_summary=False,
                )
            if self.hierarchy is not None:
                self.hierarchy.register_matter(
                    decision.matter.matter_id,
                    change_ref=f"reconciliation:{finding.finding_id}",
                )
                if placement is not None and placement.status == "admit_child":
                    self.hierarchy.attach_child(
                        parent_matter_id=placement.parent_matter_id,
                        child_matter_id=decision.matter.matter_id,
                        role=str(attributes.get("hierarchy_role", "optional")),
                        confidence=finding.confidence,
                        rationale=placement.rationale,
                        evidence_ids=placement.evidence_ids,
                    )
            self._persist_matter_context(
                matter_id=decision.matter.matter_id,
                semantic_identity_key=semantic_identity_key,
                context=context,
                broad_scope=bool(attributes.get("broad_scope", False)),
            )
            if placement is not None and placement.status == "admit_related":
                self._persist_related_placements(
                    matter_id=decision.matter.matter_id,
                    related_matter_ids=placement.related_matter_ids,
                    related_matter_types=dict(
                        placement.related_matter_types
                    ),
                    rationale=placement.rationale,
                    evidence_ids=placement.evidence_ids,
                )
        raw_topic_types = attributes.get("topic_types", ())
        if isinstance(raw_topic_types, (str, bytes)) or not isinstance(
            raw_topic_types,
            (tuple, list),
        ):
            raw_topic_types = ()
        if not raw_topic_types and str(
            attributes.get("matter_type", "")
        ).strip():
            raw_topic_types = (
                {
                    "value": attributes.get("matter_type", ""),
                    "label": attributes.get("localized_matter_type", {}),
                },
            )
        topic_types = []
        for raw_topic in raw_topic_types:
            if not isinstance(raw_topic, Mapping):
                continue
            value = " ".join(
                str(raw_topic.get("value", "")).strip().casefold().split()
            )
            label = raw_topic.get("label", {})
            if (
                not value
                or not isinstance(label, Mapping)
                or set(label) != {"en", "zh-CN"}
                or any(not str(label[locale]).strip() for locale in ("en", "zh-CN"))
            ):
                continue
            topic_types.append(
                {
                    "value": value,
                    "label": {
                        locale: str(label[locale]).strip()
                        for locale in ("en", "zh-CN")
                    },
                }
            )
        if topic_types and decision.status in {"admitted", "uncertain"}:
            self.store.append(
                "matter_classification",
                object_id,
                self.store.next_revision(
                    "matter_classification",
                    object_id,
                ),
                {
                    "matter_id": object_id,
                    "semantic_revision": finding.semantic_revision,
                    "topic_types": tuple(topic_types),
                    "evidence_ids": finding.evidence_ids,
                    "freshness": "current",
                },
            )
        if self.hierarchy is not None and decision.status == "admitted":
            self.hierarchy.mark_dependency_changed(
                object_id,
                change_ref=f"lifecycle:{object_id}",
                refresh=False,
            )
        matter_ids = (
            (object_id,)
            if decision.status in {"admitted", "uncertain"}
            else ()
        )
        stage_status = {
            "admitted": "current",
            "uncertain": "uncertain",
            "source_only": "not_applicable",
            "blocked": "blocked",
        }.get(decision.status, "not_applicable")
        for coverage_id in self._coverage_object_ids(package):
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="matter",
                status=stage_status,
                input_fingerprint=package.input_fingerprint,
                output_ref=f"admission_decision:{object_id}",
                matter_ids=matter_ids,
                refresh_summary=False,
            )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied" if stage_status == "current" else stage_status,
            f"admission_decision:{object_id}",
        )

    @staticmethod
    def _context_signals(
        attributes: Mapping[str, Any],
        *,
        finding: AdvisoryFinding,
        semantic_identity_key: str,
    ) -> tuple[ContextSignal, ...]:
        raw_signals = attributes.get("context_signals", ())
        if isinstance(raw_signals, (str, bytes)) or not isinstance(
            raw_signals,
            (tuple, list),
        ):
            raw_signals = ()
        signals: list[ContextSignal] = []
        for item in raw_signals:
            if not isinstance(item, Mapping):
                continue
            evidence_ids = tuple(
                str(value)
                for value in item.get("evidence_ids", finding.evidence_ids)
                if str(value)
            )
            signals.append(
                ContextSignal(
                    kind=str(item.get("kind", "")),
                    value=str(item.get("value", "")),
                    evidence_ids=evidence_ids,
                    confidence=str(
                        item.get("confidence", finding.confidence)
                    ),
                    freshness=str(item.get("freshness", "current")),
                )
            )
        if not signals and finding.evidence_ids:
            if bool(attributes.get("explicit_goal_or_obligation", False)):
                signals.append(
                    ContextSignal(
                        kind="goal",
                        value=semantic_identity_key,
                        evidence_ids=finding.evidence_ids,
                        confidence=finding.confidence,
                    )
                )
            subject = str(
                finding.localized_statement.get("en", "")
            ).strip()
            if subject:
                signals.append(
                    ContextSignal(
                        kind="subject",
                        value=subject,
                        evidence_ids=finding.evidence_ids,
                        confidence=finding.confidence,
                    )
                )
        by_key = {signal.match_key: signal for signal in signals}
        return tuple(by_key[key] for key in sorted(by_key))

    def _placement_candidates(
        self,
        incoming_context: ProjectContext,
    ) -> tuple[MatterPlacementCandidate, ...]:
        """Recall against the full exact-signal index, then bound AI context."""

        incoming_keys = {
            signal.match_key
            for signal in incoming_context.current_signals
        }
        if not incoming_keys:
            return ()
        ranked: list[
            tuple[int, str, MatterPlacementCandidate]
        ] = []
        after_matter_id = ""
        while True:
            page = self.store.matter_context_match_page(
                tuple(sorted(incoming_keys)),
                after_matter_id=after_matter_id,
                limit=200,
            )
            if not page:
                break
            for payload in page:
                raw_signals = payload.get("signals", ())
                if not isinstance(raw_signals, (tuple, list)):
                    continue
                try:
                    context = ProjectContext(
                        signals=tuple(
                            ContextSignal(**dict(item))
                            for item in raw_signals
                            if isinstance(item, Mapping)
                        ),
                        revision=int(payload.get("context_revision", 1)),
                        freshness=str(payload.get("freshness", "current")),
                    )
                    candidate = MatterPlacementCandidate(
                        matter_id=str(payload["matter_id"]),
                        semantic_identity_key=str(
                            payload["semantic_identity_key"]
                        ),
                        context=context,
                        broad_scope=bool(
                            payload.get("broad_scope", False)
                        ),
                        parent_matter_id=str(
                            payload.get("parent_matter_id", "")
                        ),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                matched_kinds = {
                    kind
                    for kind, value in incoming_keys
                    if (kind, value)
                    in {
                        signal.match_key
                        for signal in context.current_signals
                    }
                }
                score = sum(
                    _RECONCILIATION_RECALL_KIND_WEIGHTS[kind]
                    for kind in matched_kinds
                )
                ranked.append((score, candidate.matter_id, candidate))
            ranked.sort(key=lambda item: (-item[0], item[1]))
            del ranked[MAX_RECONCILIATION_CANDIDATES:]
            next_after = str(page[-1].get("matter_id", ""))
            if not next_after or next_after <= after_matter_id:
                raise RuntimeError(
                    "Matter context recall page did not advance"
                )
            after_matter_id = next_after
            if len(page) < 200:
                break
        return tuple(item[2] for item in ranked)

    def _persist_matter_context(
        self,
        *,
        matter_id: str,
        semantic_identity_key: str,
        context: ProjectContext,
        broad_scope: bool,
    ) -> None:
        current = self.store.current("matter_context", matter_id) or {}
        merged: dict[tuple[str, str], ContextSignal] = {}
        for item in current.get("signals", ()):
            if not isinstance(item, Mapping):
                continue
            try:
                signal = ContextSignal(**dict(item))
            except (TypeError, ValueError):
                continue
            merged[signal.match_key] = signal
        for signal in context.current_signals:
            merged[signal.match_key] = signal
        parent_edge = (
            self.hierarchy.parent_edge(matter_id, current_only=True)
            if self.hierarchy is not None
            else None
        )
        self.store.append(
            "matter_context",
            matter_id,
            self.store.next_revision("matter_context", matter_id),
            {
                "matter_id": matter_id,
                "semantic_identity_key": semantic_identity_key,
                "signals": tuple(
                    asdict(merged[key]) for key in sorted(merged)
                ),
                "context_revision": int(
                    current.get("context_revision", 0)
                )
                + 1,
                "freshness": "current",
                "broad_scope": bool(
                    current.get("broad_scope", False) or broad_scope
                ),
                "parent_matter_id": (
                    parent_edge.parent_matter_id
                    if parent_edge is not None
                    else ""
                ),
            },
        )

    def _persist_related_placements(
        self,
        *,
        matter_id: str,
        related_matter_ids: tuple[str, ...],
        related_matter_types: Mapping[str, str] | None = None,
        rationale: str,
        evidence_ids: tuple[str, ...],
    ) -> None:
        for related_id in related_matter_ids:
            relation_type = str(
                (related_matter_types or {}).get(
                    related_id,
                    "related",
                )
            )
            relation_id = (
                "relation:"
                + sha256(
                    "\0".join(
                        sorted((matter_id, related_id))
                    ).encode("utf-8")
                ).hexdigest()[:24]
            )
            self.store.append(
                "relation_candidate",
                relation_id,
                self.store.next_revision(
                    "relation_candidate",
                    relation_id,
                ),
                {
                    "relation_id": relation_id,
                    "source_matter_id": matter_id,
                    "target_matter_id": related_id,
                    "relation_type": relation_type,
                    "rationale": rationale,
                    "evidence_ids": evidence_ids,
                    "freshness": "current",
                },
            )

    def apply_hierarchy_revision(
        self,
        revision,
    ) -> None:
        """Resume and finish durable split/merge owner dispositions."""

        if self.hierarchy is None:
            raise ValueError("Matter hierarchy owner is unavailable")
        for request in self.hierarchy.disposition_requests(
            revision.revision_id
        ):
            request_id = str(request["request_id"])
            if str(request.get("status", "")) == "current":
                continue
            try:
                output_refs = self._apply_hierarchy_disposition(
                    revision,
                    request,
                )
            except Exception as exc:
                self.hierarchy.mark_disposition_result(
                    request_id=request_id,
                    status="blocked",
                    failure_class=type(exc).__name__,
                )
                raise
            self.hierarchy.mark_disposition_result(
                request_id=request_id,
                status="current",
                output_refs=output_refs,
            )
        self.hierarchy.publish_revision(revision)

    def _apply_hierarchy_disposition(
        self,
        revision,
        request: Mapping[str, Any],
    ) -> tuple[str, ...]:
        action = str(request["action"])
        if action == "retain":
            return (f"retained:{request['member_kind']}:{request['member_id']}",)
        if action == "review":
            raise ValueError("review disposition is not an automatic mutation")
        targets = tuple(
            str(item)
            for item in request.get("target_matter_ids", ())
            if str(item)
        )
        if not targets:
            raise ValueError("hierarchy disposition target is required")
        if action == "move" and len(targets) != 1:
            raise ValueError("move requires exactly one target Matter")
        assert self.hierarchy is not None
        for target in targets:
            self.hierarchy.path(target)
        kind = str(request["member_kind"])
        member_id = str(request["member_id"])
        if kind == "source":
            return self._apply_source_membership(
                source_id=member_id,
                subject_matter_ids=revision.subject_matter_ids,
                target_matter_ids=targets,
                move=action == "move",
            )
        if kind == "event":
            return self._apply_event_membership(
                event_id=member_id,
                target_matter_ids=targets,
                move=action == "move",
                revision_id=revision.revision_id,
            )
        if kind == "work_item":
            return self._apply_work_item_membership(
                item_id=member_id,
                target_matter_ids=targets,
                move=action == "move",
                revision_id=revision.revision_id,
            )
        if kind == "child":
            if action != "move":
                raise ValueError(
                    "a child cannot be copied under single-primary-parent rules"
                )
            prior = self.hierarchy.parent_edge(
                member_id,
                current_only=False,
            )
            if prior is None:
                revision_value = self.hierarchy.attach_child(
                    parent_matter_id=targets[0],
                    child_matter_id=member_id,
                    role="optional",
                    confidence="bounded",
                    rationale=revision.rationale,
                    evidence_ids=revision.evidence_ids,
                )
            elif prior.parent_matter_id == targets[0]:
                return (f"matter_containment_edge:{prior.edge_id}",)
            else:
                revision_value = self.hierarchy.reparent_child(
                    child_matter_id=member_id,
                    expected_parent_matter_id=prior.parent_matter_id,
                    new_parent_matter_id=targets[0],
                    role=prior.role,
                    confidence=prior.confidence,
                    rationale=revision.rationale,
                    evidence_ids=revision.evidence_ids,
                    ordinal=prior.ordinal,
                )
            return (
                f"matter_hierarchy_revision:{revision_value.revision_id}",
            )
        if kind == "open_loop":
            return self._apply_open_loop_membership(
                loop_id=member_id,
                target_matter_ids=targets,
                move=action == "move",
                revision_id=revision.revision_id,
            )
        raise ValueError("unsupported hierarchy disposition member kind")

    def _apply_source_membership(
        self,
        *,
        source_id: str,
        subject_matter_ids: tuple[str, ...],
        target_matter_ids: tuple[str, ...],
        move: bool,
    ) -> tuple[str, ...]:
        output_refs = []
        affected = tuple(
            dict.fromkeys((*subject_matter_ids, *target_matter_ids))
        )
        for matter_id in affected:
            decision = self.store.current("admission_decision", matter_id)
            if decision is None or not isinstance(
                decision.get("matter"),
                Mapping,
            ):
                raise ValueError("source membership target is not admitted")
            matter = dict(decision["matter"])
            source_ids = list(matter.get("source_ids", ()))
            should_have = matter_id in target_matter_ids or (
                not move and matter_id in subject_matter_ids
            )
            if should_have and source_id not in source_ids:
                source_ids.append(source_id)
            if not should_have:
                source_ids = [item for item in source_ids if item != source_id]
            matter["source_ids"] = tuple(dict.fromkeys(source_ids))
            revision = self.store.next_revision(
                "admission_decision",
                matter_id,
            )
            self.store.append(
                "admission_decision",
                matter_id,
                revision,
                {**decision, "matter": matter},
            )
            output_refs.append(f"admission_decision:{matter_id}:v{revision}")
        return tuple(output_refs)

    def _apply_event_membership(
        self,
        *,
        event_id: str,
        target_matter_ids: tuple[str, ...],
        move: bool,
        revision_id: str,
    ) -> tuple[str, ...]:
        event = self.store.current("temporal_event", event_id)
        if event is None:
            raise ValueError("event disposition target is unavailable")
        output_refs = []
        for index, matter_id in enumerate(target_matter_ids):
            if move and index == 0:
                target_id = event_id
                payload = {**event, "object_ref": matter_id}
            else:
                target_id = "event:" + sha256(
                    f"{event_id}\0{matter_id}\0{revision_id}".encode("utf-8")
                ).hexdigest()[:24]
                payload = {
                    **event,
                    "event_id": target_id,
                    "object_ref": matter_id,
                    "derived_from_event_id": event_id,
                }
            revision = self.store.next_revision(
                "temporal_event",
                target_id,
            )
            self.store.append(
                "temporal_event",
                target_id,
                revision,
                payload,
            )
            output_refs.append(f"temporal_event:{target_id}:v{revision}")
        return tuple(output_refs)

    def _apply_work_item_membership(
        self,
        *,
        item_id: str,
        target_matter_ids: tuple[str, ...],
        move: bool,
        revision_id: str,
    ) -> tuple[str, ...]:
        item = self.store.current("matter_work_item", item_id)
        if item is None:
            raise ValueError("WorkItem disposition target is unavailable")
        output_refs = []
        for index, matter_id in enumerate(target_matter_ids):
            if move and index == 0:
                target_id = item_id
                payload = {**item, "matter_id": matter_id}
            else:
                target_id = "work-item:" + sha256(
                    f"{item_id}\0{matter_id}\0{revision_id}".encode("utf-8")
                ).hexdigest()[:24]
                payload = {
                    **item,
                    "item_id": target_id,
                    "matter_id": matter_id,
                    "derived_from_item_id": item_id,
                }
            revision = self.store.next_revision(
                "matter_work_item",
                target_id,
            )
            self.store.append(
                "matter_work_item",
                target_id,
                revision,
                payload,
            )
            output_refs.append(f"matter_work_item:{target_id}:v{revision}")
        return tuple(output_refs)

    def _apply_open_loop_membership(
        self,
        *,
        loop_id: str,
        target_matter_ids: tuple[str, ...],
        move: bool,
        revision_id: str,
    ) -> tuple[str, ...]:
        loop = self.store.current("open_loop", loop_id)
        if loop is None:
            raise ValueError("open-loop disposition target is unavailable")
        output_refs = []
        for index, matter_id in enumerate(target_matter_ids):
            if move and index == 0:
                target_id = loop_id
                payload = {**loop, "matter_id": matter_id}
            else:
                target_id = "loop:" + sha256(
                    f"{loop_id}\0{matter_id}\0{revision_id}".encode("utf-8")
                ).hexdigest()[:24]
                payload = {
                    **loop,
                    "loop_id": target_id,
                    "matter_id": matter_id,
                    "derived_from_loop_id": loop_id,
                }
            revision = self.store.next_revision("open_loop", target_id)
            self.store.append(
                "open_loop",
                target_id,
                revision,
                payload,
            )
            output_refs.append(f"open_loop:{target_id}:v{revision}")
        return tuple(output_refs)

    def _c7(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        decision = self.lifecycle.decide(
            StateProofPacket(
                coverage=str(attributes.get("coverage", "unknown")),
                explicit_start=bool(attributes.get("explicit_start", False)),
                work_recorded=bool(attributes.get("work_recorded", False)),
                scheduled=bool(attributes.get("scheduled", False)),
                provider_status=str(attributes.get("provider_status", "")),
                completion_licensed=bool(
                    attributes.get("completion_licensed", False)
                ),
                evidence_ids=finding.evidence_ids,
                basis_modality=(
                    "ai_inferred"
                    if finding.modality == "inferred"
                    else finding.modality
                ),
                basis_scope=str(
                    attributes.get(
                        "basis_scope",
                        (
                            "current_phase"
                            if str(
                                attributes.get("inference_purpose", "")
                            )
                            == "current_phase"
                            else (
                                "source_record"
                                if finding.modality
                                in {"observed", "reported", "planned"}
                                else ""
                            )
                        ),
                    )
                ),
                temporal_assertion=str(
                    attributes.get("temporal_assertion", "unknown")
                ),
                current_phase_requested=(
                    finding.modality == "inferred"
                    and str(attributes.get("inference_purpose", ""))
                    == "current_phase"
                ),
                prerequisite_evidence_ids=tuple(
                    str(item)
                    for item in attributes.get(
                        "prerequisite_evidence_ids",
                        (),
                    )
                    if str(item).strip()
                ),
                remaining_obligation_ids=tuple(
                    str(item)
                    for item in attributes.get(
                        "remaining_obligation_ids",
                        (),
                    )
                    if str(item).strip()
                ),
                analysis_as_of=str(
                    attributes.get("inference_as_of", "")
                ),
                active_window_start=str(
                    attributes.get("active_window_start", "")
                ),
                active_window_end=str(
                    attributes.get("active_window_end", "")
                ),
                contradiction_checked=bool(
                    attributes.get("contradiction_checked", False)
                ),
                counter_signals=tuple(
                    str(item)
                    for item in attributes.get("counter_signals", ())
                    if str(item).strip()
                ),
                confidence=finding.confidence,
                alternatives=tuple(
                    str(item)
                    for item in (
                        attributes.get("alternative_explanations")
                        or finding.alternative_explanations
                    )
                    if str(item).strip()
                ),
                coverage_boundary=str(
                    attributes.get("coverage_boundary", "")
                ),
                expires_at=str(attributes.get("expires_at", "")),
                contradiction_triggers=tuple(
                    str(item)
                    for item in attributes.get(
                        "contradiction_triggers",
                        (),
                    )
                    if str(item).strip()
                ),
            )
        )
        matter_id = self._matter_id(
            package,
            finding,
            result_findings=result_findings,
        )
        object_id = f"{matter_id}:lifecycle"
        self.store.append(
            "lifecycle_decision",
            object_id,
            self.store.next_revision("lifecycle_decision", object_id),
            asdict(decision),
        )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            (
                "uncertain"
                if decision.state in {"uncertain", "completion_unproven"}
                else "auto_applied"
            ),
            f"lifecycle_decision:{object_id}",
        )

    def _c8(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        wait_target = str(attributes.get("wait_target", "")).strip()
        closure_condition = str(attributes.get("closure_condition", "")).strip()
        if not wait_target or not closure_condition:
            raise ValueError("open loop target and closure condition are required")
        matter_id = self._matter_id(
            package,
            finding,
            result_findings=result_findings,
        )
        semantic_role_key = str(
            attributes.get("semantic_role_key", "")
        ).strip().casefold()
        loop_id = str(attributes.get("loop_id", "")).strip()
        if not loop_id:
            identity_seed = (
                f"semantic-role:{semantic_role_key}"
                if semantic_role_key
                else f"finding:{finding.finding_id}"
            )
            loop_id = "loop:" + sha256(
                f"{matter_id}\0{identity_seed}".encode("utf-8")
            ).hexdigest()[:24]
        loop = self.open_loops.build(
            loop_id=loop_id,
            matter_id=matter_id,
            wait_target=wait_target,
            closure_condition=closure_condition,
            critical=bool(attributes.get("critical", False)),
            evidence_ids=finding.evidence_ids,
            semantic_role_key=semantic_role_key,
        )
        if loop is None:
            raise ValueError("open-loop owner rejected incomplete finding")
        supersedes_loop_ids = tuple(
            dict.fromkeys(
                str(value).strip()
                for value in attributes.get(
                    "supersedes_loop_ids",
                    (),
                )
                if str(value).strip()
            )
        )
        if loop.loop_id in supersedes_loop_ids:
            raise ValueError(
                "an open loop cannot supersede its own identity"
            )
        loop_payload = asdict(loop)
        transaction = (
            nullcontext()
            if self.store.in_atomic_transaction()
            else self.store.immediate_transaction()
        )
        with transaction:
            current_rows = tuple(
                row
                for row in self.store.iter_current("open_loop")
                if str(row.get("matter_id", "")) == matter_id
            )
            if semantic_role_key:
                conflicting_ids = {
                    str(row.get("loop_id", ""))
                    for row in current_rows
                    if not bool(row.get("deleted", False))
                    and str(row.get("status", "open")) == "open"
                    and str(
                        row.get("semantic_role_key", "")
                    ).strip().casefold()
                    == semantic_role_key
                    and str(row.get("loop_id", "")) != loop.loop_id
                }
                if not conflicting_ids.issubset(
                    set(supersedes_loop_ids)
                ):
                    raise ValueError(
                        "active open loops with the same semantic role must "
                        "be explicitly superseded"
                    )
            for retired_id in supersedes_loop_ids:
                current = self.store.current("open_loop", retired_id)
                if current is None:
                    raise ValueError(
                        "superseded open loop is unavailable"
                    )
                if str(current.get("matter_id", "")) != matter_id:
                    raise ValueError(
                        "superseded open loop belongs to another Matter"
                    )
                if bool(current.get("deleted", False)):
                    if (
                        str(current.get("superseded_by", ""))
                        != loop.loop_id
                    ):
                        raise ValueError(
                            "open loop was already retired by another "
                            "replacement"
                        )
                    continue
                revision = self.store.next_revision(
                    "open_loop",
                    retired_id,
                )
                self.store.append(
                    "open_loop",
                    retired_id,
                    revision,
                    {
                        **current,
                        "deleted": True,
                        "superseded_by": loop.loop_id,
                        "retirement_reason": (
                            "semantic_identity_reconciliation"
                        ),
                    },
                )
            write = self.store.compare_current_and_append(
                "open_loop",
                loop.loop_id,
                is_equivalent=lambda current: (
                    current is not None
                    and not bool(current.get("deleted", False))
                    and _payload_fingerprint(
                        {
                            key: value
                            for key, value in current.items()
                            if key not in {
                                "deleted",
                                "superseded_by",
                                "retirement_reason",
                            }
                        }
                    )
                    == _payload_fingerprint(
                        {
                            key: value
                            for key, value in loop_payload.items()
                            if key not in {
                                "deleted",
                                "superseded_by",
                                "retirement_reason",
                            }
                        }
                    )
                ),
                payload_factory=lambda _revision, _current: loop_payload,
            )
        self.open_loops.remember(loop)
        if self.hierarchy is not None:
            self.hierarchy.mark_dependency_changed(
                matter_id,
                change_ref=(
                    f"open-loop:{loop.loop_id}:v"
                    f"{int(write['revision'])}"
                ),
                refresh=False,
            )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied",
            f"open_loop:{loop.loop_id}",
        )

    @staticmethod
    def _historical_event_contract_valid(
        event: Mapping[str, Any],
    ) -> bool:
        return bool(
            str(event.get("modality", "")) == "inferred"
            and str(event.get("temporal_direction", "")) == "past"
            and str(event.get("inference_purpose", ""))
            == "historical_gap_fill"
            and bool(event.get("revisable", False))
            and str(event.get("inference_as_of", "")).strip()
            and str(event.get("target_time", "")).strip()
            and str(event.get("inference_confidence", "")).strip()
            and tuple(event.get("supporting_signals", ()))
            and not tuple(event.get("counter_signals", ()))
            and str(event.get("coverage_boundary", "")).strip()
            and tuple(event.get("alternative_explanations", ()))
            and tuple(event.get("contradiction_triggers", ()))
            and str(event.get("expires_at", "")).strip()
        )

    @staticmethod
    def _historical_finding_contract_valid(
        finding: AdvisoryFinding,
        attributes: Mapping[str, Any],
    ) -> bool:
        alternatives = (
            tuple(attributes.get("alternative_explanations", ()))
            or finding.alternative_explanations
        )
        return bool(
            finding.modality == "inferred"
            and str(attributes.get("temporal_direction", "")) == "past"
            and str(attributes.get("inference_purpose", ""))
            == "historical_gap_fill"
            and bool(attributes.get("revisable", False))
            and str(attributes.get("inference_as_of", "")).strip()
            and str(attributes.get("target_time", "")).strip()
            and tuple(attributes.get("supporting_signals", ()))
            and not tuple(attributes.get("counter_signals", ()))
            and str(attributes.get("coverage_boundary", "")).strip()
            and tuple(alternatives)
            and tuple(attributes.get("contradiction_triggers", ()))
            and str(attributes.get("expires_at", "")).strip()
        )

    def _criterion_owner_evidence_licensed(
        self,
        *,
        matter_id: str,
        evidence_ids: tuple[str, ...],
        basis_modality: str,
        temporal_direction: str,
    ) -> bool:
        required_evidence = {
            str(item).strip() for item in evidence_ids if str(item).strip()
        }
        if not required_evidence or temporal_direction == "future":
            return False
        normalized_modality = (
            "inferred"
            if basis_modality in {"inferred", "ai_inferred"}
            else basis_modality
        )
        licensed_evidence: set[str] = set()
        for event in self.store.iter_current("temporal_event"):
            if (
                not bool(event.get("current_revision", True))
                or str(event.get("object_ref", "")) != matter_id
            ):
                continue
            event_modality = str(event.get("modality", ""))
            if normalized_modality == "reported":
                modality_matches = event_modality in {
                    "observed",
                    "reported",
                }
            else:
                modality_matches = event_modality == normalized_modality
            if not modality_matches:
                continue
            event_direction = str(event.get("temporal_direction", ""))
            if temporal_direction == "past" and event_direction != "past":
                continue
            if event_direction == "future":
                continue
            if (
                normalized_modality == "inferred"
                and not self._historical_event_contract_valid(event)
            ):
                continue
            licensed_evidence.update(
                str(item).strip()
                for item in event.get("evidence_ids", ())
                if str(item).strip()
            )
        return required_evidence.issubset(licensed_evidence)

    def _reported_termination_evidence_licensed(
        self,
        *,
        matter_id: str,
        evidence_ids: tuple[str, ...],
    ) -> bool:
        required_evidence = {
            str(item).strip() for item in evidence_ids if str(item).strip()
        }
        if not required_evidence:
            return False
        licensed_evidence: set[str] = set()
        markers = (
            "cancel",
            "withdraw",
            "refund",
            "abandon",
            "terminat",
        )
        for event in self.store.iter_current("temporal_event"):
            event_kind = str(event.get("kind", "")).casefold()
            if (
                not bool(event.get("current_revision", True))
                or str(event.get("object_ref", "")) != matter_id
                or str(event.get("modality", ""))
                not in {"observed", "reported"}
                or str(event.get("temporal_direction", ""))
                not in {"past", "present"}
                or not any(marker in event_kind for marker in markers)
            ):
                continue
            licensed_evidence.update(
                str(item).strip()
                for item in event.get("evidence_ids", ())
                if str(item).strip()
            )
        return required_evidence.issubset(licensed_evidence)

    def _c9(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        matter_id = self._matter_id(
            package,
            finding,
            result_findings=result_findings,
        )
        criteria: tuple[CompletionCriterion, ...] = ()
        requested_status = str(
            attributes.get("requested_status", "")
        ).strip()
        if finding.finding_type == "conflict":
            decision = self.outcomes.record_conflict(
                matter_id,
                rationale=finding.statement,
            )
        elif requested_status == "cancelled":
            loop_dispositions = tuple(
                str(item).strip()
                for item in attributes.get(
                    "open_loop_dispositions",
                    attributes.get("loop_dispositions", ()),
                )
                if str(item).strip()
            )
            open_loop_ids = tuple(
                str(loop.get("loop_id", ""))
                for loop in self.store.iter_current("open_loop")
                if (
                    str(loop.get("matter_id", "")) == matter_id
                    and str(loop.get("status", "open")) == "open"
                )
            )
            loop_dispositions_complete = all(
                any(loop_id in disposition for disposition in loop_dispositions)
                for loop_id in open_loop_ids
            )
            cancellation_licensed = bool(
                finding.modality in {"observed", "reported"}
                and self._reported_termination_evidence_licensed(
                    matter_id=matter_id,
                    evidence_ids=finding.evidence_ids,
                )
                and loop_dispositions_complete
            )
            if cancellation_licensed:
                decision = self.outcomes.cancel(
                    matter_id,
                    rationale=finding.statement,
                    loop_dispositions=loop_dispositions,
                    basis_modality=finding.modality,
                    terminality="confirmed",
                )
            else:
                decision = self.outcomes.record_conflict(
                    matter_id,
                    rationale=(
                        "cancellation remains unproven until a current "
                        "reported/observed termination event and every open-loop "
                        "disposition are licensed"
                    ),
                )
        elif requested_status == "reopened":
            obligation_id = str(attributes.get("new_obligation_id", "")).strip()
            if not obligation_id:
                raise ValueError("reopen requires a new obligation id")
            decision = self.outcomes.reopen(
                matter_id,
                new_obligation_id=obligation_id,
            )
        else:
            criteria_items: list[CompletionCriterion] = []
            finding_inference_contract_valid = (
                self._historical_finding_contract_valid(
                    finding,
                    attributes,
                )
            )
            for item in attributes.get("criteria", ()):
                if not isinstance(item, Mapping):
                    continue
                evidence_ids = tuple(
                    str(value).strip()
                    for value in item.get("evidence_ids", ())
                    if str(value).strip()
                )
                basis_modality = str(
                    item.get("basis_modality", finding.modality)
                )
                if basis_modality == "inferred":
                    basis_modality = "ai_inferred"
                temporal_direction = str(
                    item.get(
                        "temporal_direction",
                        attributes.get("temporal_direction", "past"),
                    )
                )
                owner_evidence_licensed = (
                    self._criterion_owner_evidence_licensed(
                        matter_id=matter_id,
                        evidence_ids=evidence_ids,
                        basis_modality=basis_modality,
                        temporal_direction=temporal_direction,
                    )
                )
                criteria_items.append(
                    CompletionCriterion(
                        criterion_id=str(item.get("criterion_id", "")),
                        satisfied=bool(item.get("satisfied", False)),
                        evidence_ids=evidence_ids,
                        basis_modality=basis_modality,
                        temporal_direction=temporal_direction,
                        freshness=str(item.get("freshness", "current")),
                        completion_licensed=bool(
                            item.get(
                                "completion_licensed",
                                finding.modality in {
                                    "observed",
                                    "reported",
                                },
                            )
                        ),
                        owner_evidence_licensed=owner_evidence_licensed,
                        terminality=str(
                            item.get(
                                "terminality",
                                (
                                    "provisional"
                                    if finding.modality == "inferred"
                                    else "confirmed"
                                ),
                            )
                        ),
                        inference_contract_valid=bool(
                            basis_modality == "ai_inferred"
                            and finding_inference_contract_valid
                            and owner_evidence_licensed
                        ),
                    )
                )
            criteria = tuple(criteria_items)
            decision = self.outcomes.decide_completion(
                matter_id,
                criteria,
                provider_done=bool(attributes.get("provider_done", False)),
                result_attachment_only=bool(
                    attributes.get("result_attachment_only", False)
                ),
            )
        object_id = f"{matter_id}:outcome"
        basis_evidence_ids = tuple(
            dict.fromkeys(
                (
                    *finding.evidence_ids,
                    *(
                        evidence_id
                        for criterion in criteria
                        for evidence_id in criterion.evidence_ids
                    ),
                )
            )
        )
        basis_scope = str(
            attributes.get(
                "basis_scope",
                attributes.get("inference_scope", ""),
            )
        ).strip()
        if (
            not basis_scope
            and finding.modality == "inferred"
            and decision.status == "completed"
        ):
            basis_scope = "historical_gap"
        self.store.append(
            "outcome_decision",
            object_id,
            self.store.next_revision("outcome_decision", object_id),
            {
                **asdict(decision),
                "criteria": tuple(asdict(item) for item in criteria),
                "basis_finding_id": finding.finding_id,
                "basis_modality": (
                    decision.basis_modality
                    if decision.basis_modality != "unknown"
                    else (
                        "ai_inferred"
                        if finding.modality == "inferred"
                        else finding.modality
                    )
                ),
                "basis_scope": basis_scope,
                "terminality": decision.terminality,
                "confidence": finding.confidence,
                "alternative_explanations": (
                    tuple(
                        attributes.get("alternative_explanations", ())
                    )
                    or finding.alternative_explanations
                ),
                "coverage_boundary": str(
                    attributes.get("coverage_boundary", "")
                ),
                "expires_at": str(attributes.get("expires_at", "")),
                "contradiction_triggers": tuple(
                    attributes.get("contradiction_triggers", ())
                ),
                "basis_evidence_ids": basis_evidence_ids,
                "basis_semantic_revision": finding.semantic_revision,
            },
        )
        if self.hierarchy is not None:
            self.hierarchy.mark_dependency_changed(
                matter_id,
                change_ref=f"outcome:{object_id}",
                refresh=False,
            )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            (
                "uncertain"
                if decision.status
                in {"completion_unproven", "outcome_conflict"}
                else "auto_applied"
            ),
            f"outcome_decision:{object_id}",
        )

    def _c12(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> DispatchOutcome:
        if finding.finding_type == "generated_hero_candidate":
            if self.heroes is None:
                raise ValueError("generated hero owner is unavailable")
            matter_id = self._matter_id(
                package,
                finding,
                result_findings=result_findings,
            )
            attributes = dict(finding.attributes)
            admission = self.store.current("admission_decision", matter_id) or {}
            admitted_matter = admission.get("matter", {})
            if not isinstance(admitted_matter, Mapping):
                admitted_matter = {}
            parent_edge = (
                self.hierarchy.parent_edge(matter_id, current_only=True)
                if self.hierarchy is not None
                else None
            )
            hierarchy_projection = self.store.current(
                "matter_hierarchy_projection",
                matter_id,
            ) or {}
            if parent_edge is not None:
                for coverage_id in self._coverage_object_ids(package):
                    self.coverage_ledger.mark_stage(
                        object_id=coverage_id,
                        stage_id="generated_hero",
                        status="not_applicable",
                        input_fingerprint=package.input_fingerprint,
                        output_ref=f"generated_hero_not_applicable:{matter_id}",
                        matter_ids=(matter_id,),
                        refresh_summary=False,
                    )
                self._advance_ui_reachability(package, matter_id)
                return DispatchOutcome(
                    finding.finding_id,
                    finding.owner_model_id,
                    "not_applicable",
                    f"generated_hero_not_applicable:{matter_id}",
                )
            topic_concepts = tuple(
                str(item)
                for item in attributes.get(
                    "topic_concepts",
                    ("personal project",),
                )
                if str(item).strip()
            )
            theme_concepts = tuple(
                str(item)
                for item in attributes.get(
                    "theme_concepts",
                    ("progress",),
                )
                if str(item).strip()
            )
            record = self.heroes.prepare(
                HeroSubject(
                    object_id=matter_id,
                    object_kind="matter",
                    semantic_identity_id=str(
                        admitted_matter.get(
                            "semantic_identity_id",
                            finding.semantic_revision,
                        )
                    ),
                    topic_concepts=topic_concepts,
                    theme_concepts=theme_concepts,
                    hierarchy_revision=str(
                        hierarchy_projection.get(
                            "input_fingerprint",
                            hierarchy_projection.get(
                                "revision",
                                finding.semantic_revision,
                            ),
                        )
                    ),
                    is_root=parent_edge is None,
                    independently_openable=True,
                    identity_current=True,
                    hierarchy_current=str(
                        hierarchy_projection.get(
                            "freshness",
                            "current",
                        )
                    )
                    != "stale",
                    merge_disposition_current=not bool(
                        attributes.get("merge_pending", False)
                    ),
                    permission_disposition=str(
                        attributes.get(
                            "permission_disposition",
                            "allowed",
                        )
                    ),
                    safety_disposition=str(
                        attributes.get(
                            "safety_disposition",
                            "allowed",
                        )
                    ),
                    generation_policy_revision=str(
                        attributes.get(
                            "generation_policy_revision",
                            HERO_GENERATION_POLICY_REVISION,
                        )
                    ),
                )
            )
            stage_status = (
                "current"
                if record.status == "generated_current"
                else (
                    "blocked"
                    if record.status == "generation_blocked_placeholder"
                    else "pending"
                )
            )
            for coverage_id in self._coverage_object_ids(package):
                self.coverage_ledger.mark_stage(
                    object_id=coverage_id,
                    stage_id="generated_hero",
                    status=stage_status,
                    input_fingerprint=package.input_fingerprint,
                    output_ref=f"generated_hero_record:{matter_id}",
                    matter_ids=(matter_id,),
                    failure_class=record.failure_kind,
                    refresh_summary=False,
                )
            self._advance_ui_reachability(package, matter_id)
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                (
                    "auto_applied"
                    if stage_status == "current"
                    else stage_status
                ),
                f"generated_hero_record:{matter_id}",
            )
        if finding.finding_type == "supplemental_information_candidate":
            matter_id = self._matter_id(
                package,
                finding,
                result_findings=result_findings,
            )
            payload = self.store.current(
                "matter_supplemental_information",
                matter_id,
            ) or {}
            items = list(payload.get("items", ()))
            item = {
                "kind": str(
                    finding.attributes.get("kind", "background")
                ),
                "localized_title": dict(
                    finding.attributes.get(
                        "localized_title",
                        finding.localized_statement,
                    )
                ),
                "localized_body": dict(finding.localized_statement),
                "relevant_time": str(
                    finding.attributes.get("relevant_time", "")
                ),
                "freshness": "current",
                "evidence_ids": finding.evidence_ids,
            }
            items.append(item)
            self.store.append(
                "matter_supplemental_information",
                matter_id,
                self.store.next_revision(
                    "matter_supplemental_information",
                    matter_id,
                ),
                {
                    "matter_id": matter_id,
                    "semantic_revision": finding.semantic_revision,
                    "items": tuple(items[-20:]),
                    "status": "current",
                },
            )
            for coverage_id in self._coverage_object_ids(package):
                self.coverage_ledger.mark_stage(
                    object_id=coverage_id,
                    stage_id="supplemental_information",
                    status="current",
                    input_fingerprint=package.input_fingerprint,
                    output_ref=(
                        f"matter_supplemental_information:{matter_id}"
                    ),
                    matter_ids=(matter_id,),
                    refresh_summary=False,
                )
            self._advance_ui_reachability(package, matter_id)
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"matter_supplemental_information:{matter_id}",
            )
        matter_id = self._matter_id(
            package,
            finding,
            result_findings=result_findings,
        )
        title_finding = self._current_localized_matter_title(
            matter_id=matter_id,
            semantic_revision=finding.semantic_revision,
            result_findings=result_findings,
        )
        lifecycle = self.store.current(
            "lifecycle_decision",
            f"{matter_id}:lifecycle",
        ) or {}
        outcome = self.store.current(
            "outcome_decision",
            f"{matter_id}:outcome",
        ) or {}
        current_projection = self.store.current("projection", matter_id) or {}
        outcome_status = str(outcome.get("status", "")).strip()
        lifecycle_state = str(lifecycle.get("state", "")).strip()
        if outcome_status in {"completed", "cancelled", "abandoned"}:
            state = outcome_status
            state_owner = outcome
        elif outcome_status == "reopened":
            state = lifecycle_state or "in_progress"
            state_owner = lifecycle or outcome
        elif lifecycle_state:
            state = lifecycle_state
            state_owner = lifecycle
        else:
            state = str(
                current_projection.get("state", "uncertain")
            ).strip() or "uncertain"
            state_owner = current_projection
        state_basis_modality = str(
            state_owner.get(
                "basis_modality",
                state_owner.get("state_basis_modality", "unknown"),
            )
        ).strip() or "unknown"
        if state_basis_modality == "inferred":
            state_basis_modality = "ai_inferred"
        state_basis_scope = str(
            state_owner.get(
                "basis_scope",
                state_owner.get("state_basis_scope", ""),
            )
        ).strip()
        state_terminality = str(
            state_owner.get(
                "terminality",
                state_owner.get("state_terminality", "confirmed"),
            )
        ).strip() or "confirmed"
        state_evidence_ids = tuple(
            str(item)
            for item in state_owner.get(
                "basis_evidence_ids",
                state_owner.get("evidence_ids", ()),
            )
            if str(item)
        )
        projection = self.projections.publish(
            matter_id=matter_id,
            semantic_revision=finding.semantic_revision,
            state=state,
            rationale=finding.statement,
            evidence_ids=tuple(
                dict.fromkeys((*finding.evidence_ids, *state_evidence_ids))
            ),
            localized_values=title_finding.localized_statement,
            localized_rationale=finding.localized_statement,
            state_basis_modality=state_basis_modality,
            state_basis_scope=state_basis_scope,
            state_terminality=state_terminality,
        )
        self.store.append(
            "projection",
            matter_id,
            self.store.next_revision("projection", matter_id),
            asdict(projection),
        )
        for coverage_id in self._coverage_object_ids(package):
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="localization",
                status="current",
                input_fingerprint=package.input_fingerprint,
                output_ref=f"projection:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="ui_projection",
                status="pending",
                input_fingerprint=package.input_fingerprint,
                output_ref=f"projection:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
        if self.hierarchy is not None:
            self.hierarchy.register_matter(
                matter_id,
                change_ref=f"projection:{matter_id}:{finding.semantic_revision}",
            )
        self._advance_ui_reachability(package, matter_id)
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied",
            f"projection:{matter_id}",
        )

    def _advance_ui_reachability(
        self,
        package: AnalysisWorkPackage,
        matter_id: str,
    ) -> None:
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
        for coverage_id in self._coverage_object_ids(package):
            row = self.coverage_ledger.current(coverage_id)
            if row is None:
                continue
            ready = all(
                (pointer := row.stages.get(stage_id)) is not None
                and pointer.status in {"current", "uncertain"}
                for stage_id in prerequisites
            )
            status = "current" if ready else "pending"
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="ui_projection",
                status=status,
                input_fingerprint=package.input_fingerprint,
                output_ref=f"projection:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="ui_reachable",
                status=status,
                input_fingerprint=package.input_fingerprint,
                output_ref=f"object_browser:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )

    def _current_localized_matter_title(
        self,
        *,
        matter_id: str,
        semantic_revision: str,
        result_findings: tuple[AdvisoryFinding, ...],
    ) -> AdvisoryFinding:
        owner_output_ref = f"admission_decision:{matter_id}"
        title_findings = tuple(
            item
            for item in result_findings
            if item.finding_type == "matter_candidate"
            and item.owner_model_id == "C6_matter_admission"
            and (
                (
                    self.store.current(
                        "autonomous_finding",
                        item.finding_id,
                    )
                    or {}
                ).get("owner_output_ref")
                == owner_output_ref
            )
        )
        if len(title_findings) != 1:
            raise ValueError(
                "bounded summary requires exactly one current "
                "owner-dispatched localized Matter title for the same "
                "canonical Matter; title and summary may use different "
                "current source revisions"
            )
        return title_findings[0]

    def _matter_id(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
        *,
        result_findings: tuple[AdvisoryFinding, ...] = (),
    ) -> str:
        declared = str(finding.attributes.get("matter_id", "")).strip()
        if declared:
            return declared
        if package.matter_id:
            return package.matter_id
        if result_findings:
            owner_bound_ids = []
            for candidate in result_findings:
                if (
                    candidate.finding_type != "matter_candidate"
                    or candidate.owner_model_id
                    != "C6_matter_admission"
                    or candidate.semantic_revision
                    != finding.semantic_revision
                ):
                    continue
                owner_record = self.store.current(
                    "autonomous_finding",
                    candidate.finding_id,
                )
                if (
                    owner_record is None
                    or str(
                        owner_record.get(
                            "package_input_fingerprint",
                            "",
                        )
                    )
                    != package.input_fingerprint
                    or str(owner_record.get("status", ""))
                    not in {"auto_applied", "uncertain"}
                ):
                    continue
                owner_output_ref = str(
                    owner_record.get("owner_output_ref", "")
                )
                prefix = "admission_decision:"
                if owner_output_ref.startswith(prefix):
                    owner_bound_ids.append(
                        owner_output_ref.removeprefix(prefix)
                    )
            unique_owner_ids = tuple(
                dict.fromkeys(owner_bound_ids)
            )
            if len(unique_owner_ids) == 1:
                return unique_owner_ids[0]
            if len(unique_owner_ids) > 1:
                raise ValueError(
                    "finding requires an explicit Matter because the "
                    "accepted result contains multiple Matter owners"
                )
            raise ValueError(
                "finding has no current same-result Matter owner"
            )
        for payload in self.store.iter_current("admission_decision"):
            matter = payload.get("matter")
            candidate = payload.get("candidate")
            if isinstance(matter, Mapping) and set(
                matter.get("source_ids", ())
            ).intersection(package.source_revision_ids):
                return str(matter["matter_id"])
            if isinstance(candidate, Mapping) and set(
                candidate.get("source_ids", ())
            ).intersection(package.source_revision_ids):
                return str(candidate["candidate_id"])
        raise ValueError("C12/C7/C8/C9 finding has no admitted or uncertain Matter")

    def _coverage_object_ids(
        self,
        package: AnalysisWorkPackage,
    ) -> tuple[str, ...]:
        result = []
        for source_revision in package.source_revision_ids:
            source_id, marker, version = source_revision.rpartition(":v")
            if not marker or not version.isdigit():
                continue
            payload = self.store.current("source_version", source_id)
            if payload is None or int(payload.get("version", 0)) != int(version):
                continue
            reference = payload.get("external_reference", {})
            if not isinstance(reference, Mapping):
                continue
            object_id = str(reference.get("external_id", ""))
            if object_id and self.coverage_ledger.current(object_id) is not None:
                result.append(object_id)
        return tuple(dict.fromkeys(result))

    def _mark_result_dispatched(
        self,
        result: AgentOperationResult,
        status: str,
    ) -> None:
        updated = replace(result, auto_apply_status=status)
        self.store.append(
            "agent_operation_result",
            result.package_id,
            self.store.next_revision(
                "agent_operation_result",
                result.package_id,
            ),
            asdict(updated),
        )


__all__ = ["AutonomousFindingDispatcher", "DispatchOutcome"]
