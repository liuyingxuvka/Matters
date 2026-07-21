"""Exact target-bound analysis for registry-current Matter source revisions."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol

from matters.analysis.operations import (
    CURRENT_SEMANTIC_OUTPUT_TYPES,
    AgentOperationOwner,
    AnalysisWorkPackage,
)
from matters.application.source_revision_reconciliation import (
    MatterSourceRevisionReconciliationOwner,
)


SOURCE_REVISION_ANALYSIS_PLAN_OWNER = "source_revision_analysis_plan"
SOURCE_REVISION_ANALYSIS_RELATION_OWNER = "source_revision_analysis_relation"
SOURCE_REVISION_ANALYSIS_REBASE_OWNER = "source_revision_analysis_rebase"
MATTER_SEMANTIC_ANALYSIS_PLAN_OWNER = "matter_semantic_analysis_plan"
MATTER_SEMANTIC_ANALYSIS_RELATION_OWNER = "matter_semantic_analysis_relation"
MATTER_SEMANTIC_ANALYSIS_REBASE_OWNER = "matter_semantic_analysis_rebase"
_SOURCE_REF = re.compile(
    r"^(?P<source_id>source:[^:]+):v(?P<version>[1-9]\d*)$"
)


class SourceRevisionAnalysisStore(Protocol):
    def current(self, owner: str, object_id: str) -> dict[str, Any] | None: ...

    def iter_current(self, owner: str) -> Any: ...

    def compare_current_and_append(
        self,
        owner: str,
        object_id: str,
        *,
        is_equivalent: Any,
        payload_factory: Any,
    ) -> dict[str, Any]: ...

    def current_by_json_array_members(
        self,
        owner: str,
        *,
        json_field: str,
        values: tuple[str, ...],
    ) -> dict[str, tuple[dict[str, Any], ...]]: ...

    def evidence_anchors_for_source_version(
        self,
        *,
        source_id: str,
        source_version: int,
    ) -> tuple[dict[str, Any], ...]: ...

    def immediate_transaction(self) -> Any: ...


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _raise_plan_conflict() -> dict[str, Any]:
    raise RuntimeError("source revision analysis plan changed concurrently")


class MatterSourceRevisionAnalysisOwner:
    """Queue one exact semantic refresh per Matter/current-source pair."""

    def __init__(
        self,
        *,
        store: SourceRevisionAnalysisStore,
        operations: AgentOperationOwner,
        reconciliation: MatterSourceRevisionReconciliationOwner,
        locale_registry_revision: str,
    ) -> None:
        self.store = store
        self.operations = operations
        self.reconciliation = reconciliation
        self.locale_registry_revision = locale_registry_revision

    @staticmethod
    def _pair_id(matter_id: str, source_ref: str) -> str:
        return (
            "source-revision-analysis:"
            + sha256(f"{matter_id}\0{source_ref}".encode("utf-8")).hexdigest()[
                :24
            ]
        )

    def _annotation_inputs(
        self,
        source_ref: str,
    ) -> tuple[
        tuple[dict[str, Any], ...],
        tuple[dict[str, Any], ...],
    ]:
        rows = self.store.current_by_json_array_members(
            "analysis_work_package",
            json_field="source_revision_ids",
            values=(source_ref,),
        ).get(source_ref, ())
        packages: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        for row in rows:
            package_id = str(row.get("package_id", ""))
            if (
                str(row.get("task_kind", "")) != "source_annotation"
                or not package_id
                or self.store.current(
                    "analysis_result_invalidation",
                    package_id,
                )
                is not None
            ):
                continue
            result = self.store.current(
                "agent_operation_result",
                package_id,
            )
            if (
                result is None
                or str(result.get("status", "")) != "passed"
                or not bool(result.get("receipt_current", False))
                or str(result.get("package_input_fingerprint", ""))
                != str(row.get("input_fingerprint", ""))
                or str(result.get("auto_apply_status", ""))
                != "annotation_current"
            ):
                continue
            packages.append(dict(row))
            results.append(dict(result))
        ordered = sorted(
            zip(packages, results, strict=True),
            key=lambda item: str(item[0].get("package_id", "")),
        )
        return (
            tuple(item[0] for item in ordered),
            tuple(item[1] for item in ordered),
        )

    def plan(self, matter_id: str) -> tuple[dict[str, Any], ...]:
        admission = self.store.current("admission_decision", matter_id)
        reconciliation = self.reconciliation.plan(matter_id)
        if admission is None:
            return (
                {
                    "matter_id": matter_id,
                    "status": "blocked",
                    "blocker": "canonical_admission_missing",
                },
            )
        admission_fingerprint = _fingerprint(admission)
        rows: list[dict[str, Any]] = []
        for disposition in reconciliation.dispositions:
            if disposition.status != "analysis_required":
                continue
            source_ref = disposition.current_source_ref
            match = _SOURCE_REF.fullmatch(source_ref)
            if match is None:
                rows.append(
                    {
                        "matter_id": matter_id,
                        "current_source_ref": source_ref,
                        "status": "blocked",
                        "blocker": "current_source_ref_invalid",
                    }
                )
                continue
            packages, results = self._annotation_inputs(source_ref)
            source_id = match.group("source_id")
            source_version = int(match.group("version"))
            anchors = tuple(
                item
                for item in self.store.evidence_anchors_for_source_version(
                    source_id=source_id,
                    source_version=source_version,
                )
                if bool(item.get("current", True))
            )
            allowed_by_annotation = {
                str(evidence_id)
                for package in packages
                for evidence_id in package.get("allowed_evidence_ids", ())
                if str(evidence_id)
            }
            current_evidence_ids = tuple(
                sorted(
                    str(item.get("evidence_id", ""))
                    for item in anchors
                    if str(item.get("evidence_id", ""))
                    in allowed_by_annotation
                )
            )
            package_ids = tuple(
                str(item.get("package_id", "")) for item in packages
            )
            blocker = ""
            if not packages:
                blocker = "current_source_annotation_missing"
            elif not current_evidence_ids:
                blocker = "current_annotated_evidence_missing"
            pair_id = self._pair_id(matter_id, source_ref)
            relation = self.store.current(
                SOURCE_REVISION_ANALYSIS_RELATION_OWNER,
                pair_id,
            )
            semantic_package_id = str(
                (relation or {}).get("semantic_package_id", "")
            )
            semantic_result = (
                self.store.current(
                    "agent_operation_result",
                    semantic_package_id,
                )
                if semantic_package_id
                else None
            )
            semantic_package = (
                self.store.current(
                    "analysis_work_package",
                    semantic_package_id,
                )
                if semantic_package_id
                else None
            )
            semantic_package_current = bool(
                semantic_package is not None
                and str(semantic_package.get("matter_id", "")) == matter_id
                and str(semantic_package.get("matter_revision", ""))
                == admission_fingerprint
                and tuple(semantic_package.get("source_revision_ids", ()))
                == (source_ref,)
                and tuple(semantic_package.get("allowed_evidence_ids", ()))
                == current_evidence_ids
            )
            status = (
                "blocked"
                if blocker
                else (
                    "current"
                    if (
                        semantic_package_current
                        and
                        semantic_result is not None
                        and str(semantic_result.get("status", "")) == "passed"
                        and bool(
                            semantic_result.get("receipt_current", False)
                        )
                        and str(
                            semantic_result.get("auto_apply_status", "")
                        )
                        in {"auto_applied", "no_finding"}
                    )
                    else "rebase_required"
                    if semantic_package_id and not semantic_package_current
                    else "queued"
                    if semantic_package_current
                    else "ready"
                )
            )
            rows.append(
                {
                    "pair_id": pair_id,
                    "matter_id": matter_id,
                    "old_source_ref": disposition.source_ref,
                    "current_source_ref": source_ref,
                    "content_equivalent": disposition.content_equivalent,
                    "admission_fingerprint": admission_fingerprint,
                    "annotation_package_ids": package_ids,
                    "annotation_result_ids": tuple(
                        str(item.get("result_id", "")) for item in results
                    ),
                    "current_evidence_ids": current_evidence_ids,
                    "semantic_package_id": semantic_package_id,
                    "semantic_package_current": semantic_package_current,
                    "status": status,
                    "blocker": blocker,
                }
            )
        return tuple(rows)

    def queue(self, matter_id: str) -> tuple[dict[str, Any], ...]:
        admission = self.store.current("admission_decision", matter_id)
        if admission is None:
            return self.plan(matter_id)
        matter = admission.get("matter")
        if not isinstance(matter, Mapping):
            return self.plan(matter_id)
        projection = self.store.current("projection", matter_id) or {}
        outputs: list[dict[str, Any]] = []
        for row in self.plan(matter_id):
            if row.get("status") not in {
                "ready",
                "queued",
                "rebase_required",
            }:
                outputs.append(dict(row))
                continue
            source_ref = str(row["current_source_ref"])
            superseded_package_id = (
                str(row.get("semantic_package_id", ""))
                if row.get("status") == "rebase_required"
                else ""
            )
            packages, results = self._annotation_inputs(source_ref)
            annotations = tuple(
                {
                    "finding_id": str(finding.get("finding_id", "")),
                    "statement": str(finding.get("statement", "")),
                    "localized_statement": dict(
                        finding.get("localized_statement", {})
                    ),
                    "attributes": dict(finding.get("attributes", {})),
                    "confidence": str(finding.get("confidence", "")),
                }
                for result in results
                for finding in result.get("findings", ())
                if str(finding.get("finding_type", ""))
                == "source_annotation"
            )
            plan_write = self.store.compare_current_and_append(
                SOURCE_REVISION_ANALYSIS_PLAN_OWNER,
                str(row["pair_id"]),
                is_equivalent=lambda current, expected=row: (
                    current is not None
                    and str(current.get("admission_fingerprint", ""))
                    == str(expected["admission_fingerprint"])
                    and tuple(current.get("annotation_package_ids", ()))
                    == tuple(expected["annotation_package_ids"])
                    and tuple(current.get("current_evidence_ids", ()))
                    == tuple(expected["current_evidence_ids"])
                ),
                payload_factory=lambda _revision, current, expected=row: (
                    {
                        "pair_id": str(expected["pair_id"]),
                        "matter_id": matter_id,
                        "current_source_ref": source_ref,
                        "admission_fingerprint": str(
                            expected["admission_fingerprint"]
                        ),
                        "annotation_package_ids": list(
                            expected["annotation_package_ids"]
                        ),
                        "current_evidence_ids": list(
                            expected["current_evidence_ids"]
                        ),
                        "analysis_as_of": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "status": "planned",
                        "supersedes_admission_fingerprint": (
                            str(
                                current.get(
                                    "admission_fingerprint",
                                    "",
                                )
                            )
                            if current is not None
                            else ""
                        ),
                    }
                    if (
                        current is None
                        or (
                            str(current.get("pair_id", ""))
                            == str(expected["pair_id"])
                            and str(current.get("matter_id", ""))
                            == matter_id
                            and str(
                                current.get(
                                    "current_source_ref",
                                    "",
                                )
                            )
                            == source_ref
                        )
                    )
                    else _raise_plan_conflict()
                ),
            )
            plan_payload = dict(plan_write["payload"])
            semantic_identity_id = str(
                matter.get("semantic_identity_id", "")
            )
            package = AnalysisWorkPackage.create(
                operation_type="text_analysis",
                task_kind="source_revision_matter_refresh",
                capability_role="matter_modeler",
                requested_output_types=CURRENT_SEMANTIC_OUTPUT_TYPES,
                dependency_package_ids=tuple(
                    str(item.get("package_id", "")) for item in packages
                ),
                source_revision_ids=(source_ref,),
                model_revision="matters-source-revision-matter-refresh:v1",
                matter_id=matter_id,
                matter_revision=str(row["admission_fingerprint"]),
                allowed_evidence_ids=tuple(row["current_evidence_ids"]),
                allowed_asset_ids=tuple(
                    dict.fromkeys(
                        str(asset_id)
                        for item in packages
                        for asset_id in item.get("allowed_asset_ids", ())
                        if str(asset_id)
                    )
                ),
                allowed_tool_ids=(),
                private_evidence={
                    "analysis_as_of": str(plan_payload["analysis_as_of"]),
                    "target_matter": {
                        "matter_id": matter_id,
                        "semantic_identity_id": semantic_identity_id,
                        "current_source_ids": tuple(
                            matter.get("source_ids", ())
                        ),
                        "localized_title": dict(
                            projection.get("localized_values", {})
                        ),
                        "localized_summary": dict(
                            projection.get("localized_rationale", {})
                        ),
                    },
                    "current_source_ref": source_ref,
                    "source_annotations": annotations,
                    "required_output": {
                        "finding_types": CURRENT_SEMANTIC_OUTPUT_TYPES,
                        "required_locales": ("en", "zh-CN"),
                        "target_existing_matter_only": True,
                        "semantic_identity_key": semantic_identity_id,
                        "historical_inference_only": True,
                        "human_confirmation_required": False,
                    },
                },
                locale_registry_revision=self.locale_registry_revision,
                prompt_contract_id="matters.semantic-understanding",
                prompt_contract_revision="v4",
                output_schema_id="matters.agent-operation-result.v4",
            )
            self.operations.queue(package)
            with self.store.immediate_transaction():
                if (
                    superseded_package_id
                    and superseded_package_id != package.package_id
                ):
                    prior_result = self.store.current(
                        "agent_operation_result",
                        superseded_package_id,
                    )
                    self.store.compare_current_and_append(
                        "analysis_result_invalidation",
                        superseded_package_id,
                        is_equivalent=lambda current, expected=package: (
                            current is not None
                            and str(current.get("status", ""))
                            == "superseded"
                            and str(
                                current.get(
                                    "replacement_package_id",
                                    "",
                                )
                            )
                            == expected.package_id
                        ),
                        payload_factory=lambda _revision, _current, expected=package: {
                            "package_id": superseded_package_id,
                            "result_id": str(
                                (prior_result or {}).get(
                                    "result_id",
                                    "",
                                )
                            ),
                            "status": "superseded",
                            "reason": (
                                "source_revision_matter_revision_rebased"
                            ),
                            "replacement_package_id": expected.package_id,
                            "source_result_preserved": (
                                prior_result is not None
                            ),
                        },
                    )
                    self.store.compare_current_and_append(
                        SOURCE_REVISION_ANALYSIS_REBASE_OWNER,
                        superseded_package_id,
                        is_equivalent=lambda current, expected=package: (
                            current is not None
                            and str(
                                current.get(
                                    "replacement_package_id",
                                    "",
                                )
                            )
                            == expected.package_id
                            and str(current.get("status", ""))
                            == "rebased"
                        ),
                        payload_factory=lambda _revision, _current, expected=package: {
                            "pair_id": str(row["pair_id"]),
                            "matter_id": matter_id,
                            "current_source_ref": source_ref,
                            "superseded_package_id": superseded_package_id,
                            "replacement_package_id": expected.package_id,
                            "replacement_matter_revision": (
                                expected.matter_revision
                            ),
                            "source_result_preserved": (
                                prior_result is not None
                            ),
                            "status": "rebased",
                        },
                    )
                relation_write = self.store.compare_current_and_append(
                    SOURCE_REVISION_ANALYSIS_RELATION_OWNER,
                    str(row["pair_id"]),
                    is_equivalent=lambda current, expected=package: (
                        current is not None
                        and str(current.get("semantic_package_id", ""))
                        == expected.package_id
                        and str(
                            current.get(
                                "semantic_input_fingerprint",
                                "",
                            )
                        )
                        == expected.input_fingerprint
                    ),
                    payload_factory=lambda _revision, current, expected=package: (
                        {
                            "pair_id": str(row["pair_id"]),
                            "matter_id": matter_id,
                            "current_source_ref": source_ref,
                            "semantic_package_id": expected.package_id,
                            "semantic_input_fingerprint": (
                                expected.input_fingerprint
                            ),
                            "supersedes_semantic_package_id": (
                                str(
                                    current.get(
                                        "semantic_package_id",
                                        "",
                                    )
                                )
                                if current is not None
                                else ""
                            ),
                            "status": "current",
                        }
                        if (
                            current is None
                            or (
                                str(current.get("pair_id", ""))
                                == str(row["pair_id"])
                                and str(current.get("matter_id", ""))
                                == matter_id
                                and str(
                                    current.get(
                                        "current_source_ref",
                                        "",
                                    )
                                )
                                == source_ref
                                and str(
                                    current.get(
                                        "semantic_package_id",
                                        "",
                                    )
                                )
                                == superseded_package_id
                            )
                        )
                        else _raise_plan_conflict()
                    ),
                )
            outputs.append(
                {
                    **dict(row),
                    "semantic_package_id": package.package_id,
                    "superseded_semantic_package_id": (
                        superseded_package_id
                    ),
                    "status": "queued",
                    "write_status": str(relation_write["status"]),
                }
            )
        return tuple(outputs)


class MatterSemanticAnalysisOwner:
    """Queue one exact cross-source semantic refresh for an admitted Matter."""

    def __init__(
        self,
        *,
        store: SourceRevisionAnalysisStore,
        operations: AgentOperationOwner,
        locale_registry_revision: str,
    ) -> None:
        self.store = store
        self.operations = operations
        self.locale_registry_revision = locale_registry_revision

    @staticmethod
    def _relation_id(matter_id: str) -> str:
        return "matter-semantic-analysis:" + sha256(
            matter_id.encode("utf-8")
        ).hexdigest()[:24]

    def _annotation_inputs(
        self,
        source_ref: str,
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        rows = self.store.current_by_json_array_members(
            "analysis_work_package",
            json_field="source_revision_ids",
            values=(source_ref,),
        ).get(source_ref, ())
        pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for row in rows:
            package_id = str(row.get("package_id", ""))
            if (
                str(row.get("task_kind", "")) != "source_annotation"
                or not package_id
                or self.store.current(
                    "analysis_result_invalidation", package_id
                )
                is not None
            ):
                continue
            result = self.store.current("agent_operation_result", package_id)
            if (
                result is None
                or str(result.get("status", "")) != "passed"
                or not bool(result.get("receipt_current", False))
                or str(result.get("package_input_fingerprint", ""))
                != str(row.get("input_fingerprint", ""))
                or str(result.get("auto_apply_status", ""))
                != "annotation_current"
            ):
                continue
            pairs.append((dict(row), dict(result)))
        pairs.sort(key=lambda item: str(item[0].get("package_id", "")))
        return (
            tuple(item[0] for item in pairs),
            tuple(item[1] for item in pairs),
        )

    def _current_semantic_state(
        self,
        matter_id: str,
    ) -> dict[str, Any]:
        work_item_fields = (
            "item_id",
            "semantic_role_key",
            "kind",
            "status",
            "localized_title",
            "localized_result",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "required_for_parent",
            "material_stage",
            "basis_modality",
            "basis_scope",
            "temporal_assertion",
            "terminality",
            "evidence_ids",
            "source_ids",
        )
        open_loop_fields = (
            "loop_id",
            "semantic_role_key",
            "wait_target",
            "closure_condition",
            "critical",
            "status",
            "evidence_ids",
        )
        work_items = tuple(
            {
                field_name: row.get(field_name)
                for field_name in work_item_fields
            }
            for row in self.store.iter_current("matter_work_item")
            if str(row.get("matter_id", "")) == matter_id
            and not bool(row.get("deleted", False))
        )
        open_loops = tuple(
            {
                field_name: row.get(field_name)
                for field_name in open_loop_fields
            }
            for row in self.store.iter_current("open_loop")
            if str(row.get("matter_id", "")) == matter_id
            and not bool(row.get("deleted", False))
            and str(row.get("status", "open")) == "open"
        )
        return {
            "work_items": tuple(
                sorted(
                    work_items,
                    key=lambda item: str(item.get("item_id", "")),
                )
            ),
            "open_loops": tuple(
                sorted(
                    open_loops,
                    key=lambda item: str(item.get("loop_id", "")),
                )
            ),
            "lifecycle": dict(
                self.store.current(
                    "lifecycle_decision",
                    f"{matter_id}:lifecycle",
                )
                or {}
            ),
            "outcome": dict(
                self.store.current(
                    "outcome_decision",
                    f"{matter_id}:outcome",
                )
                or {}
            ),
        }

    def plan(self, matter_id: str) -> dict[str, Any]:
        admission = self.store.current("admission_decision", matter_id)
        matter = admission.get("matter") if isinstance(admission, Mapping) else None
        if (
            not isinstance(admission, Mapping)
            or str(admission.get("status", "")) != "admitted"
            or not isinstance(matter, Mapping)
            or str(matter.get("matter_id", "")) != matter_id
            or matter.get("admitted") is False
        ):
            return {"matter_id": matter_id, "status": "blocked", "blocker": "canonical_admission_missing"}

        source_ids: set[str] = set()
        for source_ref in matter.get("source_ids", ()):
            match = _SOURCE_REF.fullmatch(str(source_ref))
            if match is None:
                return {
                    "matter_id": matter_id,
                    "status": "blocked",
                    "blocker": "admitted_source_ref_invalid",
                }
            source_ids.add(match.group("source_id"))
        if not source_ids:
            return {"matter_id": matter_id, "status": "blocked", "blocker": "admitted_source_set_empty"}

        source_refs: list[str] = []
        package_ids: list[str] = []
        result_ids: list[str] = []
        evidence_ids: list[str] = []
        asset_ids: list[str] = []
        annotations: list[dict[str, Any]] = []
        blockers: list[str] = []
        for source_id in sorted(source_ids):
            current = self.store.current("source_version", source_id)
            if (
                current is None
                or bool(current.get("tombstone", False))
                or int(current.get("version", 0) or 0) < 1
            ):
                blockers.append(f"registry_current_source_missing:{source_id}")
                continue
            source_version = int(current["version"])
            source_ref = f"{source_id}:v{source_version}"
            packages, results = self._annotation_inputs(source_ref)
            if not packages:
                blockers.append(f"current_source_annotation_missing:{source_id}")
                continue
            allowed_by_annotation = {
                str(evidence_id)
                for package in packages
                for evidence_id in package.get("allowed_evidence_ids", ())
                if str(evidence_id)
            }
            anchors = self.store.evidence_anchors_for_source_version(
                source_id=source_id,
                source_version=source_version,
            )
            source_evidence_ids = tuple(
                sorted(
                    str(anchor.get("evidence_id", ""))
                    for anchor in anchors
                    if bool(anchor.get("current", True))
                    and str(anchor.get("evidence_id", ""))
                    in allowed_by_annotation
                )
            )
            if not source_evidence_ids:
                blockers.append(f"current_annotated_evidence_missing:{source_id}")
                continue
            source_refs.append(source_ref)
            package_ids.extend(str(package["package_id"]) for package in packages)
            result_ids.extend(str(result.get("result_id", "")) for result in results)
            evidence_ids.extend(source_evidence_ids)
            asset_ids.extend(
                str(asset_id)
                for package in packages
                for asset_id in package.get("allowed_asset_ids", ())
                if str(asset_id)
            )
            annotations.extend(
                {
                    "source_revision": source_ref,
                    "finding_id": str(finding.get("finding_id", "")),
                    "statement": str(finding.get("statement", "")),
                    "localized_statement": dict(
                        finding.get("localized_statement", {})
                    ),
                    "attributes": dict(finding.get("attributes", {})),
                    "confidence": str(finding.get("confidence", "")),
                }
                for result in results
                for finding in result.get("findings", ())
                if str(finding.get("finding_type", "")) == "source_annotation"
            )
        if blockers:
            return {
                "matter_id": matter_id,
                "status": "blocked",
                "blocker": ";".join(sorted(blockers)),
            }
        current_source_refs = tuple(sorted(dict.fromkeys(source_refs)))
        current_package_ids = tuple(sorted(dict.fromkeys(package_ids)))
        current_result_ids = tuple(sorted(dict.fromkeys(result_ids)))
        current_evidence_ids = tuple(sorted(dict.fromkeys(evidence_ids)))
        current_asset_ids = tuple(sorted(dict.fromkeys(asset_ids)))
        admission_fingerprint = _fingerprint(admission)
        current_semantic_state = self._current_semantic_state(
            matter_id
        )
        semantic_state_fingerprint = _fingerprint(
            current_semantic_state
        )
        relation_id = self._relation_id(matter_id)
        relation = self.store.current(MATTER_SEMANTIC_ANALYSIS_RELATION_OWNER, relation_id)
        semantic_package_id = str((relation or {}).get("semantic_package_id", ""))
        semantic_package = (
            self.store.current("analysis_work_package", semantic_package_id)
            if semantic_package_id
            else None
        )
        semantic_result = (
            self.store.current("agent_operation_result", semantic_package_id)
            if semantic_package_id
            else None
        )
        semantic_package_current = bool(
            semantic_package is not None
            and str(semantic_package.get("task_kind", "")) == "matter_semantic_refresh"
            and str(semantic_package.get("model_revision", ""))
            == "matters-matter-semantic-refresh:v2"
            and str(
                semantic_package.get("prompt_contract_revision", "")
            )
            == "v5"
            and str(semantic_package.get("matter_id", "")) == matter_id
            and str(semantic_package.get("matter_revision", "")) == admission_fingerprint
            and tuple(semantic_package.get("source_revision_ids", ())) == current_source_refs
            and tuple(semantic_package.get("dependency_package_ids", ())) == current_package_ids
            and tuple(semantic_package.get("allowed_evidence_ids", ())) == current_evidence_ids
            and tuple(semantic_package.get("allowed_asset_ids", ())) == current_asset_ids
            and str(
                dict(
                    semantic_package.get("untrusted_evidence", {})
                ).get("semantic_state_fingerprint", "")
            )
            == semantic_state_fingerprint
        )
        status = (
            "current"
            if (
                semantic_package_current
                and semantic_result is not None
                and str(semantic_result.get("status", "")) == "passed"
                and bool(semantic_result.get("receipt_current", False))
                and str(semantic_result.get("auto_apply_status", ""))
                in {"auto_applied", "no_finding"}
            )
            else "rebase_required"
            if semantic_package_id and not semantic_package_current
            else "queued"
            if semantic_package_current
            else "ready"
        )
        return {
            "relation_id": relation_id,
            "matter_id": matter_id,
            "semantic_identity_id": str(matter.get("semantic_identity_id", "")),
            "admission_fingerprint": admission_fingerprint,
            "current_source_refs": current_source_refs,
            "annotation_package_ids": current_package_ids,
            "annotation_result_ids": current_result_ids,
            "current_evidence_ids": current_evidence_ids,
            "current_asset_ids": current_asset_ids,
            "current_semantic_state": current_semantic_state,
            "semantic_state_fingerprint": semantic_state_fingerprint,
            "source_annotations": tuple(annotations),
            "semantic_package_id": semantic_package_id,
            "semantic_package_current": semantic_package_current,
            "status": status,
            "blocker": "",
        }

    def queue(self, matter_id: str) -> dict[str, Any]:
        row = self.plan(matter_id)
        if row.get("status") not in {"ready", "queued", "rebase_required"}:
            return row
        admission = self.store.current("admission_decision", matter_id)
        matter = admission.get("matter") if isinstance(admission, Mapping) else {}
        projection = self.store.current("projection", matter_id) or {}
        superseded_package_id = (
            str(row.get("semantic_package_id", ""))
            if row.get("status") == "rebase_required"
            else ""
        )
        plan_write = self.store.compare_current_and_append(
            MATTER_SEMANTIC_ANALYSIS_PLAN_OWNER,
            str(row["relation_id"]),
            is_equivalent=lambda current, expected=row: (
                current is not None
                and str(current.get("admission_fingerprint", ""))
                == str(expected["admission_fingerprint"])
                and tuple(current.get("current_source_refs", ()))
                == tuple(expected["current_source_refs"])
                and tuple(current.get("annotation_package_ids", ()))
                == tuple(expected["annotation_package_ids"])
                and tuple(current.get("current_evidence_ids", ()))
                == tuple(expected["current_evidence_ids"])
                and str(
                    current.get("semantic_state_fingerprint", "")
                )
                == str(expected["semantic_state_fingerprint"])
            ),
            payload_factory=lambda _revision, current, expected=row: {
                "relation_id": str(expected["relation_id"]),
                "matter_id": matter_id,
                "admission_fingerprint": str(expected["admission_fingerprint"]),
                "current_source_refs": list(expected["current_source_refs"]),
                "annotation_package_ids": list(expected["annotation_package_ids"]),
                "current_evidence_ids": list(expected["current_evidence_ids"]),
                "semantic_state_fingerprint": str(
                    expected["semantic_state_fingerprint"]
                ),
                "analysis_as_of": datetime.now(timezone.utc).isoformat(),
                "status": "planned",
                "supersedes_admission_fingerprint": str(
                    (current or {}).get("admission_fingerprint", "")
                ),
            },
        )
        package = AnalysisWorkPackage.create(
            operation_type="text_analysis",
            task_kind="matter_semantic_refresh",
            capability_role="matter_modeler",
            requested_output_types=CURRENT_SEMANTIC_OUTPUT_TYPES,
            dependency_package_ids=tuple(row["annotation_package_ids"]),
            source_revision_ids=tuple(row["current_source_refs"]),
            model_revision="matters-matter-semantic-refresh:v2",
            matter_id=matter_id,
            matter_revision=str(row["admission_fingerprint"]),
            allowed_evidence_ids=tuple(row["current_evidence_ids"]),
            allowed_asset_ids=tuple(row["current_asset_ids"]),
            allowed_tool_ids=(),
            private_evidence={
                "analysis_as_of": str(plan_write["payload"]["analysis_as_of"]),
                "target_matter": {
                    "matter_id": matter_id,
                    "semantic_identity_id": str(row["semantic_identity_id"]),
                    "current_source_ids": tuple(matter.get("source_ids", ())),
                    "localized_title": dict(projection.get("localized_values", {})),
                    "localized_summary": dict(projection.get("localized_rationale", {})),
                },
                "current_source_refs": tuple(row["current_source_refs"]),
                "source_annotations": tuple(row["source_annotations"]),
                "current_semantic_state": dict(
                    row["current_semantic_state"]
                ),
                "semantic_state_fingerprint": str(
                    row["semantic_state_fingerprint"]
                ),
                "required_output": {
                    "finding_types": CURRENT_SEMANTIC_OUTPUT_TYPES,
                    "required_locales": ("en", "zh-CN"),
                    "target_existing_matter_only": True,
                    "matter_candidate_identity_noop": True,
                    "semantic_identity_key": str(row["semantic_identity_id"]),
                    "temporal_axes": (
                        "historical_gap",
                        "current_phase",
                        "future_planned",
                    ),
                    "future_cannot_be_completed": True,
                    "stable_semantic_member_identity": True,
                    "exact_supersession_only": True,
                    "human_confirmation_required": False,
                },
            },
            locale_registry_revision=self.locale_registry_revision,
            prompt_contract_id="matters.semantic-understanding",
            prompt_contract_revision="v5",
            output_schema_id="matters.agent-operation-result.v4",
        )
        self.operations.queue(package)
        with self.store.immediate_transaction():
            if superseded_package_id and superseded_package_id != package.package_id:
                prior_result = self.store.current("agent_operation_result", superseded_package_id)
                self.store.compare_current_and_append(
                    "analysis_result_invalidation",
                    superseded_package_id,
                    is_equivalent=lambda current, expected=package: (
                        current is not None
                        and str(current.get("status", "")) == "superseded"
                        and str(current.get("replacement_package_id", "")) == expected.package_id
                    ),
                    payload_factory=lambda _revision, _current, expected=package: {
                        "package_id": superseded_package_id,
                        "result_id": str((prior_result or {}).get("result_id", "")),
                        "status": "superseded",
                        "reason": "matter_semantic_refresh_rebased",
                        "replacement_package_id": expected.package_id,
                        "source_result_preserved": prior_result is not None,
                    },
                )
                self.store.compare_current_and_append(
                    MATTER_SEMANTIC_ANALYSIS_REBASE_OWNER,
                    superseded_package_id,
                    is_equivalent=lambda current, expected=package: (
                        current is not None
                        and str(current.get("replacement_package_id", "")) == expected.package_id
                    ),
                    payload_factory=lambda _revision, _current, expected=package: {
                        "matter_id": matter_id,
                        "superseded_package_id": superseded_package_id,
                        "replacement_package_id": expected.package_id,
                        "replacement_matter_revision": expected.matter_revision,
                        "status": "rebased",
                    },
                )
            relation_write = self.store.compare_current_and_append(
                MATTER_SEMANTIC_ANALYSIS_RELATION_OWNER,
                str(row["relation_id"]),
                is_equivalent=lambda current, expected=package: (
                    current is not None
                    and str(current.get("semantic_package_id", "")) == expected.package_id
                    and str(current.get("semantic_input_fingerprint", ""))
                    == expected.input_fingerprint
                ),
                payload_factory=lambda _revision, current, expected=package: {
                    "relation_id": str(row["relation_id"]),
                    "matter_id": matter_id,
                    "semantic_package_id": expected.package_id,
                    "semantic_input_fingerprint": expected.input_fingerprint,
                    "supersedes_semantic_package_id": str(
                        (current or {}).get("semantic_package_id", "")
                    ),
                    "status": "current",
                },
            )
        return {
            **row,
            "semantic_package_id": package.package_id,
            "superseded_semantic_package_id": superseded_package_id,
            "status": "queued",
            "write_status": str(relation_write["status"]),
        }


__all__ = [
    "MatterSourceRevisionAnalysisOwner",
    "MatterSemanticAnalysisOwner",
    "MATTER_SEMANTIC_ANALYSIS_PLAN_OWNER",
    "MATTER_SEMANTIC_ANALYSIS_RELATION_OWNER",
    "MATTER_SEMANTIC_ANALYSIS_REBASE_OWNER",
    "SOURCE_REVISION_ANALYSIS_PLAN_OWNER",
    "SOURCE_REVISION_ANALYSIS_REBASE_OWNER",
    "SOURCE_REVISION_ANALYSIS_RELATION_OWNER",
]
