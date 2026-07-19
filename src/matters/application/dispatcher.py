"""Deterministic WorkPackageV2 dispatch to the existing C4-C9/C12 owners."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from typing import Any, Mapping

from matters.analysis.operations import (
    AdvisoryFinding,
    AgentOperationResult,
    AnalysisWorkPackage,
)
from matters.application.coverage_ledger import ObjectCoverageLedger
from matters.domain.admission import AdmissionPacket, MatterAdmission
from matters.identity.people import PersonRegistry
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.projections import ProjectionOwner
from matters.presentation.visuals import VisualAssetOwner
from matters.state.lifecycle import LifecycleOwner, StateProofPacket
from matters.state.open_loops import OpenLoopOwner
from matters.state.outcomes import CompletionCriterion, OutcomeOwner
from matters.timeline.events import EventRegistry


@dataclass(frozen=True)
class DispatchOutcome:
    finding_id: str
    owner_model_id: str
    status: str
    owner_output_ref: str = ""
    failure_class: str = ""


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
            "C4_person_entity_resolution": 4,
            "C5_event_temporal_trace": 5,
            "C6_matter_admission": 6,
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
                    item.finding_id,
                ),
            )
        )
        outcomes = tuple(
            self._dispatch_once(package, finding) for finding in findings
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
    ) -> DispatchOutcome:
        prior = self.store.current("autonomous_finding", finding.finding_id)
        if (
            prior is not None
            and str(prior.get("package_input_fingerprint"))
            == package.input_fingerprint
            and str(prior.get("status"))
            in {"auto_applied", "uncertain", "no_finding", "blocked"}
        ):
            return DispatchOutcome(
                finding_id=finding.finding_id,
                owner_model_id=finding.owner_model_id,
                status=str(prior["status"]),
                owner_output_ref=str(prior.get("owner_output_ref", "")),
                failure_class=str(prior.get("failure_class", "")),
            )
        try:
            outcome = self._invoke_owner(package, finding)
        except Exception as exc:
            outcome = DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "blocked",
                failure_class=type(exc).__name__,
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
            },
        )
        return outcome

    def _invoke_owner(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
    ) -> DispatchOutcome:
        owner = finding.owner_model_id
        if owner == "C4_person_entity_resolution":
            return self._c4(finding)
        if owner == "C5_event_temporal_trace":
            return self._c5(package, finding)
        if owner == "C6_matter_admission":
            return self._c6(package, finding)
        if owner == "C7_lifecycle_board_state":
            return self._c7(package, finding)
        if owner == "C8_open_loop_waiting_blocking":
            return self._c8(package, finding)
        if owner == "C9_completion_cancellation_reopen":
            return self._c9(package, finding)
        if owner == "C12_projection_bilingual_ui":
            return self._c12(package, finding)
        raise ValueError("unregistered original owner")

    def _c4(self, finding: AdvisoryFinding) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        name = str(attributes.get("display_name", "")).strip()
        if not name:
            name = finding.localized_statement["en"]
        candidate = self.people.candidate(name, finding.finding_id)
        resolved = self.people.assert_identity(
            candidate,
            strong_link_evidence=bool(
                attributes.get("strong_link_evidence", False)
            ),
        )
        self.store.append(
            "person_candidate",
            resolved.person_id,
            self.store.next_revision("person_candidate", resolved.person_id),
            asdict(resolved),
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
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        event = self.events.from_understanding(
            kind=(
                "deadline"
                if finding.finding_type == "deadline_candidate"
                else str(attributes.get("event_kind", "semantic_event"))
            ),
            source_revision=finding.semantic_revision,
            claimed_time=str(
                attributes.get("claimed_time", attributes.get("deadline", ""))
            ),
            record_time=str(attributes.get("record_time", "")),
            actor=str(attributes.get("actor", "")),
            object_ref=str(attributes.get("object_ref", "")),
            evidence_ids=finding.evidence_ids,
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
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        decision = self.admission.decide(
            AdmissionPacket(
                source_ids=package.source_revision_ids,
                evidence_ids=finding.evidence_ids,
                explicit_goal_or_obligation=bool(
                    attributes.get("explicit_goal_or_obligation", False)
                ),
                useful_content=bool(attributes.get("useful_content", True)),
                conflict=bool(attributes.get("conflict", False)),
                access_blocked=bool(attributes.get("access_blocked", False)),
                possibility_only=bool(attributes.get("possibility_only", False)),
            )
        )
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

    def _c7(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
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
            )
        )
        matter_id = self._matter_id(package, finding)
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
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        wait_target = str(attributes.get("wait_target", "")).strip()
        closure_condition = str(attributes.get("closure_condition", "")).strip()
        if not wait_target or not closure_condition:
            raise ValueError("open loop target and closure condition are required")
        matter_id = self._matter_id(package, finding)
        loop_id = "loop:" + sha256(
            f"{finding.finding_id}\0{matter_id}".encode("utf-8")
        ).hexdigest()[:24]
        loop = self.open_loops.create(
            loop_id=loop_id,
            matter_id=matter_id,
            wait_target=wait_target,
            closure_condition=closure_condition,
            critical=bool(attributes.get("critical", False)),
            evidence_ids=finding.evidence_ids,
        )
        if loop is None:
            raise ValueError("open-loop owner rejected incomplete finding")
        self.store.append(
            "open_loop",
            loop.loop_id,
            self.store.next_revision("open_loop", loop.loop_id),
            asdict(loop),
        )
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied",
            f"open_loop:{loop.loop_id}",
        )

    def _c9(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
    ) -> DispatchOutcome:
        attributes = dict(finding.attributes)
        matter_id = self._matter_id(package, finding)
        if finding.finding_type == "conflict":
            decision = self.outcomes.record_conflict(
                matter_id,
                rationale=finding.statement,
            )
        elif str(attributes.get("requested_status", "")) == "reopened":
            obligation_id = str(attributes.get("new_obligation_id", "")).strip()
            if not obligation_id:
                raise ValueError("reopen requires a new obligation id")
            decision = self.outcomes.reopen(
                matter_id,
                new_obligation_id=obligation_id,
            )
        else:
            criteria = tuple(
                CompletionCriterion(
                    criterion_id=str(item.get("criterion_id", "")),
                    satisfied=bool(item.get("satisfied", False)),
                    evidence_ids=tuple(item.get("evidence_ids", ())),
                )
                for item in attributes.get("criteria", ())
                if isinstance(item, Mapping)
            )
            decision = self.outcomes.decide_completion(
                matter_id,
                criteria,
                provider_done=bool(attributes.get("provider_done", False)),
                result_attachment_only=bool(
                    attributes.get("result_attachment_only", False)
                ),
            )
        object_id = f"{matter_id}:outcome"
        self.store.append(
            "outcome_decision",
            object_id,
            self.store.next_revision("outcome_decision", object_id),
            asdict(decision),
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
    ) -> DispatchOutcome:
        if finding.finding_type == "card_visual_candidate":
            asset_id = str(finding.attributes.get("asset_id", "")).strip()
            if asset_id and self.store.current("visual_asset", asset_id) is None:
                raise ValueError("visual recommendation references a foreign asset")
            matter_id = self._matter_id(package, finding)
            self.store.append(
                "card_visual_recommendation",
                matter_id,
                self.store.next_revision(
                    "card_visual_recommendation",
                    matter_id,
                ),
                {
                    "matter_id": matter_id,
                    "package_id": package.package_id,
                    "asset_id": asset_id,
                    "finding": asdict(finding),
                },
            )
            projection = self.store.current("projection", matter_id)
            if projection is not None:
                self._publish_visual_decision(
                    package=package,
                    matter_id=matter_id,
                    semantic_revision=str(projection["semantic_revision"]),
                    recommended_asset_id=asset_id,
                )
            return DispatchOutcome(
                finding.finding_id,
                finding.owner_model_id,
                "auto_applied",
                f"card_visual_recommendation:{matter_id}",
            )
        matter_id = self._matter_id(package, finding)
        projection = self.projections.publish(
            matter_id=matter_id,
            semantic_revision=finding.semantic_revision,
            state=str(finding.attributes.get("state", "uncertain")),
            rationale=finding.statement,
            evidence_ids=finding.evidence_ids,
            localized_values=finding.localized_statement,
            localized_rationale=finding.localized_statement,
        )
        self.store.append(
            "projection",
            matter_id,
            self.store.next_revision("projection", matter_id),
            asdict(projection),
        )
        recommendation = self.store.current("card_visual_recommendation", matter_id)
        self._publish_visual_decision(
            package=package,
            matter_id=matter_id,
            semantic_revision=finding.semantic_revision,
            recommended_asset_id=(
                str(recommendation.get("asset_id", ""))
                if recommendation is not None
                else ""
            ),
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
        return DispatchOutcome(
            finding.finding_id,
            finding.owner_model_id,
            "auto_applied",
            f"projection:{matter_id}",
        )

    def _publish_visual_decision(
        self,
        *,
        package: AnalysisWorkPackage,
        matter_id: str,
        semantic_revision: str,
        recommended_asset_id: str = "",
    ) -> None:
        coverage_ids = self._coverage_object_ids(package)
        decision = self.visuals.decide(
            matter_id=matter_id,
            semantic_revision=semantic_revision,
            occurrence_ids=coverage_ids,
            recommended_asset_id=recommended_asset_id,
        )
        for coverage_id in coverage_ids:
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="visual",
                status="current",
                input_fingerprint=package.input_fingerprint,
                output_ref=f"card_visual_decision:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )
            self.coverage_ledger.mark_stage(
                object_id=coverage_id,
                stage_id="ui_projection",
                status="current",
                input_fingerprint=package.input_fingerprint,
                output_ref=f"projection:{matter_id}",
                matter_ids=(matter_id,),
                refresh_summary=False,
            )

    def _matter_id(
        self,
        package: AnalysisWorkPackage,
        finding: AdvisoryFinding,
    ) -> str:
        declared = str(finding.attributes.get("matter_id", "")).strip()
        if declared:
            return declared
        if package.matter_id:
            return package.matter_id
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
