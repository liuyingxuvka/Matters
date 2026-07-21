from __future__ import annotations

import pytest

from matters.analysis.operations import AnalysisWorkPackage
from matters.application.orchestrator import MatterService
from matters.application.source_revision_reconciliation import (
    MatterSourceRevisionReconciliationOwner,
)
from matters.infrastructure.sqlite.store import SQLiteStore


def _source(
    source_id: str,
    version: int,
    *,
    content_hash: str,
    body_fingerprint: str,
    body_length: int,
) -> dict:
    return {
        "source_id": source_id,
        "version": version,
        "provider": "gmail",
        "content_hash": content_hash,
        "metadata_hash": f"metadata:{version}",
        "content": {
            "body_text_fingerprint": body_fingerprint,
            "body_text_byte_length": body_length,
        },
        "tombstone": False,
    }


def _admission(
    matter_id: str,
    source_ids: list[str],
    *,
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "status": "admitted",
        "rationale": "current evidence licenses admission",
        "candidate": None,
        "matter": {
            "matter_id": matter_id,
            "source_ids": source_ids,
            "evidence_ids": evidence_ids or ["evidence:1"],
            "rationale": "current evidence licenses admission",
            "semantic_identity_id": "semantic:1",
            "object_kind": "matter",
            "admitted": True,
        },
    }


def _anchor(source_id: str, version: int, evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_version": version,
        "location": {"field": "body"},
        "text": "synthetic evidence",
        "modality": "reported",
        "current": True,
    }


def test_removes_old_revision_when_current_is_already_admitted(tmp_path):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    source_id = "source:abc"
    matter_id = "matter:abc"
    store.append(
        "source_version",
        source_id,
        1,
        _source(
            source_id,
            1,
            content_hash="hash:old",
            body_fingerprint="body:old",
            body_length=10,
        ),
    )
    store.append(
        "source_version",
        source_id,
        2,
        _source(
            source_id,
            2,
            content_hash="hash:new",
            body_fingerprint="body:new",
            body_length=20,
        ),
    )
    store.append(
        "evidence_anchor",
        "evidence:old",
        1,
        _anchor(source_id, 1, "evidence:old"),
    )
    store.append(
        "evidence_anchor",
        "evidence:new",
        1,
        _anchor(source_id, 2, "evidence:new"),
    )
    store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(
            matter_id,
            [f"{source_id}:v1", f"{source_id}:v2"],
            evidence_ids=["evidence:old", "evidence:new"],
        ),
    )

    owner = MatterSourceRevisionReconciliationOwner(store)
    result = owner.reconcile(matter_id)

    assert result["status"] == "current"
    assert result["write_status"] == "appended"
    assert len(result["applied_actions"]) == 1
    assert store.current("admission_decision", matter_id)["matter"][
        "source_ids"
    ] == [f"{source_id}:v2"]
    assert store.current("admission_decision", matter_id)["matter"][
        "evidence_ids"
    ] == ["evidence:new"]
    assert len(store.history("admission_decision", matter_id)) == 2

    retry = owner.reconcile(matter_id)
    assert retry["write_status"] == "current"
    assert len(store.history("admission_decision", matter_id)) == 2


def test_current_source_without_current_evidence_does_not_retire_old_revision(
    tmp_path,
):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    source_id = "source:abc"
    matter_id = "matter:abc"
    store.append(
        "source_version",
        source_id,
        1,
        _source(
            source_id,
            1,
            content_hash="hash:old",
            body_fingerprint="body:old",
            body_length=10,
        ),
    )
    store.append(
        "source_version",
        source_id,
        2,
        _source(
            source_id,
            2,
            content_hash="hash:new",
            body_fingerprint="body:new",
            body_length=20,
        ),
    )
    store.append(
        "evidence_anchor",
        "evidence:old",
        1,
        _anchor(source_id, 1, "evidence:old"),
    )
    store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(
            matter_id,
            [f"{source_id}:v1", f"{source_id}:v2"],
            evidence_ids=["evidence:old"],
        ),
    )

    result = MatterSourceRevisionReconciliationOwner(store).reconcile(
        matter_id
    )

    assert result["status"] == "analysis_required"
    assert result["analysis_required"][0]["reason"] == (
        "current_revision_needs_current_evidence_anchors"
    )
    admission = store.current("admission_decision", matter_id)["matter"]
    assert admission["source_ids"] == [
        f"{source_id}:v1",
        f"{source_id}:v2",
    ]
    assert admission["evidence_ids"] == ["evidence:old"]


def test_equivalent_current_revision_still_requires_current_evidence(tmp_path):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    source_id = "source:abc"
    matter_id = "matter:abc"
    store.append(
        "source_version",
        source_id,
        1,
        _source(
            source_id,
            1,
            content_hash="hash:old",
            body_fingerprint="body:same",
            body_length=10,
        ),
    )
    store.append(
        "source_version",
        source_id,
        2,
        _source(
            source_id,
            2,
            content_hash="hash:new-metadata",
            body_fingerprint="body:same",
            body_length=10,
        ),
    )
    store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(matter_id, [f"{source_id}:v1"]),
    )

    result = MatterSourceRevisionReconciliationOwner(store).reconcile(
        matter_id
    )

    assert result["status"] == "analysis_required"
    assert result["analysis_required"][0]["content_equivalent"] is True
    assert result["analysis_required"][0]["current_source_ref"].endswith(
        ":v2"
    )
    assert store.current("admission_decision", matter_id)["matter"][
        "source_ids"
    ] == [f"{source_id}:v1"]


def test_material_change_requires_analysis_and_does_not_rewrite_admission(
    tmp_path,
):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    source_id = "source:abc"
    matter_id = "matter:abc"
    store.append(
        "source_version",
        source_id,
        1,
        _source(
            source_id,
            1,
            content_hash="hash:old",
            body_fingerprint="body:old",
            body_length=10,
        ),
    )
    store.append(
        "source_version",
        source_id,
        2,
        _source(
            source_id,
            2,
            content_hash="hash:new",
            body_fingerprint="body:new",
            body_length=20,
        ),
    )
    store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(matter_id, [f"{source_id}:v1"]),
    )

    result = MatterSourceRevisionReconciliationOwner(store).reconcile(
        matter_id
    )

    assert result["status"] == "analysis_required"
    assert result["analysis_required"][0]["content_equivalent"] is False
    assert len(store.history("admission_decision", matter_id)) == 1


def test_exact_target_refresh_adopts_current_revision_without_new_root(
    tmp_path,
):
    repository = tmp_path / "repo"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    source_id = "source:abc"
    old_ref = f"{source_id}:v1"
    current_ref = f"{source_id}:v2"
    matter_id = "matter:abc"
    old_evidence_id = f"evidence:{source_id}:1:old"
    current_evidence_id = f"evidence:{source_id}:2:new"
    service.store.append(
        "source_version",
        source_id,
        1,
        _source(
            source_id,
            1,
            content_hash="hash:old",
            body_fingerprint="body:old",
            body_length=10,
        ),
    )
    service.store.append(
        "source_version",
        source_id,
        2,
        _source(
            source_id,
            2,
            content_hash="hash:new",
            body_fingerprint="body:new",
            body_length=20,
        ),
    )
    service.store.append(
        "evidence_anchor",
        old_evidence_id,
        1,
        _anchor(source_id, 1, old_evidence_id),
    )
    service.store.append(
        "evidence_anchor",
        current_evidence_id,
        1,
        _anchor(source_id, 2, current_evidence_id),
    )
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(
            matter_id,
            [old_ref],
            evidence_ids=[old_evidence_id],
        ),
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_revision": old_ref,
            "state": "in_progress",
            "evidence_ids": [old_evidence_id],
            "localized_values": {"en": "Trip", "zh-CN": "旅行"},
            "localized_rationale": {
                "en": "The trip is in progress.",
                "zh-CN": "旅行正在进行中。",
            },
            "locale_revisions": {"en": old_ref, "zh-CN": old_ref},
            "locales": ["en", "zh-CN"],
            "equivalence_status": "equivalent",
        },
    )
    annotation = AnalysisWorkPackage.create(
        operation_type="text_analysis",
        task_kind="source_annotation",
        capability_role="low_cost_annotator",
        requested_output_types=("source_annotation",),
        source_revision_ids=(current_ref,),
        model_revision="matters-source-annotation:v1",
        allowed_evidence_ids=(current_evidence_id,),
        private_evidence={
            "evidence": [
                {
                    "evidence_id": current_evidence_id,
                    "text": "The current booking confirms the trip.",
                }
            ]
        },
        prompt_contract_id="matters.source-annotation",
    )
    service.operations.queue(annotation)
    annotation_result = service.import_autonomous_result(
        package_id=annotation.package_id,
        provider_id=annotation.required_runner_id,
        provider_version=annotation.required_runner_version,
        result={
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": current_evidence_id,
                    "disposition": "used",
                    "reason": "Current source evidence was annotated.",
                }
            ],
            "findings": [
                {
                    "finding_type": "source_annotation",
                    "owner_model_id": "A0_matters_source_analysis_operation",
                    "statement": "The current booking confirms the trip.",
                    "localized_statement": {
                        "en": "The current booking confirms the trip.",
                        "zh-CN": "当前预订确认了这次旅行。",
                    },
                    "semantic_revision": current_ref,
                    "evidence_ids": [current_evidence_id],
                    "confidence": "bounded",
                    "modality": "reported",
                    "attributes": {
                        "content_kind": "booking",
                        "user_relevance": "relevant",
                    },
                }
            ],
        },
    )
    assert annotation_result["status"] == "passed"

    first_plan = service.source_revision_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert first_plan["status"] == "current", first_plan
    assert first_plan["status_counts"] == {"queued": 1}
    refresh_package_id = first_plan["items"][0]["semantic_package_id"]
    refresh_package = service.operations.package(refresh_package_id)
    imported = service.import_autonomous_result(
        package_id=refresh_package_id,
        provider_id=refresh_package.required_runner_id,
        provider_version=refresh_package.required_runner_version,
        result={
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": current_evidence_id,
                    "disposition": "used",
                    "reason": "Current evidence refreshes the existing Matter.",
                }
            ],
            "findings": [
                {
                    "finding_type": "matter_candidate",
                    "owner_model_id": "C6_matter_admission",
                    "statement": "Trip",
                    "localized_statement": {
                        "en": "Trip",
                        "zh-CN": "旅行",
                    },
                    "semantic_revision": current_ref,
                    "evidence_ids": [current_evidence_id],
                    "confidence": "bounded",
                    "modality": "observed",
                    "attributes": {
                        "matter_id": matter_id,
                        "semantic_identity_key": "semantic:1",
                    },
                }
            ],
        },
    )
    assert imported["status"] == "passed"
    assert imported["auto_apply_status"] == "auto_applied", imported
    current = service.store.current("admission_decision", matter_id)["matter"]
    assert current["source_ids"] == [old_ref, current_ref]
    assert current["evidence_ids"] == [
        old_evidence_id,
        current_evidence_id,
    ]
    assert service.store.count_current("admission_decision") == 1

    reconciled = service.reconcile_matter_source_revisions(limit=10)
    assert reconciled["status"] == "current"
    current = service.store.current("admission_decision", matter_id)["matter"]
    assert current["source_ids"] == [current_ref]
    assert current["evidence_ids"] == [current_evidence_id]

    retry = service.source_revision_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert retry["item_count"] == 0
    assert service.store.count_current("admission_decision") == 1


def test_same_matter_refreshes_rebase_stale_sibling_to_one_current_successor(
    tmp_path,
):
    repository = tmp_path / "repo"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    matter_id = "matter:shared"
    source_ids = ("source:alpha", "source:beta")
    old_refs = tuple(f"{source_id}:v1" for source_id in source_ids)
    current_refs = tuple(f"{source_id}:v2" for source_id in source_ids)
    old_evidence_ids = tuple(
        f"evidence:{source_id}:1:old" for source_id in source_ids
    )
    current_evidence_ids = tuple(
        f"evidence:{source_id}:2:new" for source_id in source_ids
    )
    for index, source_id in enumerate(source_ids):
        service.store.append(
            "source_version",
            source_id,
            1,
            _source(
                source_id,
                1,
                content_hash=f"hash:old:{index}",
                body_fingerprint=f"body:old:{index}",
                body_length=10 + index,
            ),
        )
        service.store.append(
            "source_version",
            source_id,
            2,
            _source(
                source_id,
                2,
                content_hash=f"hash:new:{index}",
                body_fingerprint=f"body:new:{index}",
                body_length=20 + index,
            ),
        )
        service.store.append(
            "evidence_anchor",
            old_evidence_ids[index],
            1,
            _anchor(source_id, 1, old_evidence_ids[index]),
        )
        service.store.append(
            "evidence_anchor",
            current_evidence_ids[index],
            1,
            _anchor(source_id, 2, current_evidence_ids[index]),
        )
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(
            matter_id,
            list(old_refs),
            evidence_ids=list(old_evidence_ids),
        ),
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_revision": old_refs[0],
            "state": "in_progress",
            "evidence_ids": list(old_evidence_ids),
            "localized_values": {
                "en": "Shared trip",
                "zh-CN": "共同旅行",
            },
            "localized_rationale": {
                "en": "The trip combines two current source changes.",
                "zh-CN": "该旅行包含两个当前来源变更。",
            },
            "locale_revisions": {
                "en": old_refs[0],
                "zh-CN": old_refs[0],
            },
            "locales": ["en", "zh-CN"],
            "equivalence_status": "equivalent",
        },
    )

    for source_ref, evidence_id in zip(
        current_refs,
        current_evidence_ids,
        strict=True,
    ):
        annotation = AnalysisWorkPackage.create(
            operation_type="text_analysis",
            task_kind="source_annotation",
            capability_role="low_cost_annotator",
            requested_output_types=("source_annotation",),
            source_revision_ids=(source_ref,),
            model_revision="matters-source-annotation:v1",
            allowed_evidence_ids=(evidence_id,),
            private_evidence={
                "evidence": [
                    {
                        "evidence_id": evidence_id,
                        "text": f"Current evidence for {source_ref}.",
                    }
                ]
            },
            prompt_contract_id="matters.source-annotation",
        )
        service.operations.queue(annotation)
        imported_annotation = service.import_autonomous_result(
            package_id=annotation.package_id,
            provider_id=annotation.required_runner_id,
            provider_version=annotation.required_runner_version,
            result={
                "status": "passed",
                "input_dispositions": [
                    {
                        "input_id": evidence_id,
                        "disposition": "used",
                        "reason": "Current source evidence was annotated.",
                    }
                ],
                "findings": [
                    {
                        "finding_type": "source_annotation",
                        "owner_model_id": (
                            "A0_matters_source_analysis_operation"
                        ),
                        "statement": f"Current evidence for {source_ref}.",
                        "localized_statement": {
                            "en": f"Current evidence for {source_ref}.",
                            "zh-CN": f"{source_ref} 的当前证据。",
                        },
                        "semantic_revision": source_ref,
                        "evidence_ids": [evidence_id],
                        "confidence": "bounded",
                        "modality": "reported",
                        "attributes": {
                            "content_kind": "booking",
                            "user_relevance": "relevant",
                        },
                    }
                ],
            },
        )
        assert imported_annotation["status"] == "passed"

    initial = service.source_revision_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert initial["status_counts"] == {"queued": 2}
    packages_by_source = {
        str(item["current_source_ref"]): service.operations.package(
            str(item["semantic_package_id"])
        )
        for item in initial["items"]
    }

    def refresh_result(source_ref: str, evidence_id: str) -> dict:
        return {
            "status": "passed",
            "input_dispositions": [
                {
                    "input_id": evidence_id,
                    "disposition": "used",
                    "reason": "Current evidence refreshes the exact Matter.",
                }
            ],
            "findings": [
                {
                    "finding_type": "matter_candidate",
                    "owner_model_id": "C6_matter_admission",
                    "statement": "Shared trip",
                    "localized_statement": {
                        "en": "Shared trip",
                        "zh-CN": "共同旅行",
                    },
                    "semantic_revision": source_ref,
                    "evidence_ids": [evidence_id],
                    "confidence": "bounded",
                    "modality": "observed",
                    "attributes": {
                        "matter_id": matter_id,
                        "semantic_identity_key": "semantic:1",
                    },
                }
            ],
        }

    first_package = packages_by_source[current_refs[0]]
    first_import = service.import_autonomous_result(
        package_id=first_package.package_id,
        provider_id=first_package.required_runner_id,
        provider_version=first_package.required_runner_version,
        result=refresh_result(current_refs[0], current_evidence_ids[0]),
    )
    assert first_import["auto_apply_status"] == "auto_applied"

    stale_package = packages_by_source[current_refs[1]]
    stale_import = service.import_autonomous_result(
        package_id=stale_package.package_id,
        provider_id=stale_package.required_runner_id,
        provider_version=stale_package.required_runner_version,
        result=refresh_result(current_refs[1], current_evidence_ids[1]),
    )
    assert stale_import["status"] == "passed"
    assert stale_import["auto_apply_status"] == "blocked"

    rebased = service.source_revision_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert rebased["status_counts"] == {"queued": 1}
    replacement_id = str(rebased["items"][0]["semantic_package_id"])
    assert replacement_id != stale_package.package_id
    assert rebased["items"][0]["superseded_semantic_package_id"] == (
        stale_package.package_id
    )
    replacement = service.operations.package(replacement_id)
    assert replacement.matter_revision != stale_package.matter_revision
    invalidation = service.store.current(
        "analysis_result_invalidation",
        stale_package.package_id,
    )
    assert invalidation["status"] == "superseded"
    assert invalidation["replacement_package_id"] == replacement_id
    assert service.store.current(
        "source_revision_analysis_rebase",
        stale_package.package_id,
    )["replacement_package_id"] == replacement_id

    relation_id = service.source_revision_analysis._pair_id(
        matter_id,
        current_refs[1],
    )
    relation_history_count = len(
        service.store.history(
            "source_revision_analysis_relation",
            relation_id,
        )
    )
    repeated = service.source_revision_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert repeated["items"][0]["semantic_package_id"] == replacement_id
    assert len(
        service.store.history(
            "source_revision_analysis_relation",
            relation_id,
        )
    ) == relation_history_count

    with pytest.raises(ValueError, match="superseded"):
        service.import_autonomous_result(
            package_id=stale_package.package_id,
            provider_id=stale_package.required_runner_id,
            provider_version=stale_package.required_runner_version,
            result=refresh_result(
                current_refs[1],
                current_evidence_ids[1],
            ),
        )

    replacement_import = service.import_autonomous_result(
        package_id=replacement.package_id,
        provider_id=replacement.required_runner_id,
        provider_version=replacement.required_runner_version,
        result=refresh_result(current_refs[1], current_evidence_ids[1]),
    )
    assert replacement_import["auto_apply_status"] == "auto_applied"
    current_matter = service.store.current(
        "admission_decision",
        matter_id,
    )["matter"]
    assert set(current_matter["source_ids"]) == {
        *old_refs,
        *current_refs,
    }
    assert service.store.count_current("admission_decision") == 1


def test_cross_source_matter_semantic_refresh_keeps_identity_and_dispatches_work_item(
    tmp_path,
):
    repository = tmp_path / "repo"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    matter_id = "matter:build-week"
    source_ids = ("source:registration", "source:deadline")
    source_refs = tuple(f"{source_id}:v1" for source_id in source_ids)
    evidence_ids = tuple(
        f"evidence:{source_id}:1:current" for source_id in source_ids
    )
    for index, source_id in enumerate(source_ids):
        service.store.append(
            "source_version",
            source_id,
            1,
            _source(
                source_id,
                1,
                content_hash=f"hash:{index}",
                body_fingerprint=f"body:{index}",
                body_length=20 + index,
            ),
        )
        service.store.append(
            "evidence_anchor",
            evidence_ids[index],
            1,
            _anchor(source_id, 1, evidence_ids[index]),
        )
    service.store.append(
        "admission_decision",
        matter_id,
        1,
        _admission(matter_id, list(source_refs), evidence_ids=list(evidence_ids)),
    )
    service.store.append(
        "projection",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "semantic_revision": source_refs[0],
            "state": "in_progress",
            "evidence_ids": list(evidence_ids),
            "localized_values": {"en": "Build Week", "zh-CN": "Build Week"},
            "localized_rationale": {
                "en": "Registration is complete and submission preparation remains active.",
                "zh-CN": "报名已完成，参赛作品仍在准备中。",
            },
            "locale_revisions": {"en": source_refs[0], "zh-CN": source_refs[0]},
            "locales": ["en", "zh-CN"],
            "equivalence_status": "equivalent",
        },
    )
    for loop_id in (
        "loop:legacy-submission-a",
        "loop:legacy-submission-b",
    ):
        service.store.append(
            "open_loop",
            loop_id,
            1,
            {
                "loop_id": loop_id,
                "matter_id": matter_id,
                "wait_target": "Build Week project submission",
                "closure_condition": "A submission receipt is recorded.",
                "critical": True,
                "status": "open",
                "evidence_ids": list(evidence_ids),
            },
        )
    for source_ref, evidence_id in zip(source_refs, evidence_ids, strict=True):
        annotation = AnalysisWorkPackage.create(
            operation_type="text_analysis",
            task_kind="source_annotation",
            capability_role="low_cost_annotator",
            requested_output_types=("source_annotation",),
            source_revision_ids=(source_ref,),
            model_revision="matters-source-annotation:v1",
            allowed_evidence_ids=(evidence_id,),
            private_evidence={"evidence": [{"evidence_id": evidence_id, "text": source_ref}]},
            prompt_contract_id="matters.source-annotation",
        )
        service.operations.queue(annotation)
        imported_annotation = service.import_autonomous_result(
            package_id=annotation.package_id,
            provider_id=annotation.required_runner_id,
            provider_version=annotation.required_runner_version,
            result={
                "status": "passed",
                "input_dispositions": [{"input_id": evidence_id, "disposition": "used", "reason": "annotated"}],
                "findings": [{
                    "finding_type": "source_annotation",
                    "owner_model_id": "A0_matters_source_analysis_operation",
                    "statement": source_ref,
                    "localized_statement": {"en": source_ref, "zh-CN": source_ref},
                    "semantic_revision": source_ref,
                    "evidence_ids": [evidence_id],
                    "confidence": "bounded",
                    "modality": "reported",
                    "attributes": {"content_kind": "mail", "user_relevance": "relevant"},
                }],
            },
        )
        assert imported_annotation["status"] == "passed"

    planned = service.matter_semantic_analysis_plan(
        matter_id=matter_id,
        queue=True,
    )
    assert planned["status"] == "current"
    assert planned["status_counts"] == {"queued": 1}
    package = service.operations.package(planned["items"][0]["semantic_package_id"])
    assert package.task_kind == "matter_semantic_refresh"
    assert package.model_revision == "matters-matter-semantic-refresh:v2"
    assert package.prompt_contract_revision == "v5"
    assert package.source_revision_ids == tuple(sorted(source_refs))
    assert package.allowed_evidence_ids == tuple(sorted(evidence_ids))
    assert len(package.dependency_package_ids) == 2
    assert len(
        package.untrusted_evidence["current_semantic_state"][
            "open_loops"
        ]
    ) == 2
    analysis_as_of = str(package.untrusted_evidence["analysis_as_of"])

    admission_before = service.store.current("admission_decision", matter_id)
    imported = service.import_autonomous_result(
        package_id=package.package_id,
        provider_id=package.required_runner_id,
        provider_version=package.required_runner_version,
        result={
            "status": "passed",
            "input_dispositions": [
                {"input_id": evidence_id, "disposition": "used", "reason": "cross-source understanding"}
                for evidence_id in evidence_ids
            ],
            "findings": [
                {
                    "finding_type": "matter_candidate",
                    "owner_model_id": "C6_matter_admission",
                    "statement": "Preserve Build Week participation.",
                    "localized_statement": {"en": "Build Week participation", "zh-CN": "Build Week 参赛"},
                    "semantic_revision": source_refs[0],
                    "evidence_ids": list(evidence_ids),
                    "confidence": "bounded",
                    "modality": "reported",
                    "attributes": {"matter_id": matter_id, "semantic_identity_key": "semantic:1"},
                },
                {
                    "finding_type": "work_item_candidate",
                    "owner_model_id": "C6_matter_admission",
                    "statement": "Prepare the project submission.",
                    "localized_statement": {"en": "Prepare the project submission", "zh-CN": "准备提交参赛项目"},
                    "semantic_revision": source_refs[1],
                    "evidence_ids": list(evidence_ids),
                    "confidence": "bounded",
                    "modality": "inferred",
                    "attributes": {
                        "matter_id": matter_id,
                        "item_id": "work-item:build-week-preparation",
                        "semantic_role_key": "preparation",
                        "kind": "milestone",
                        "status": "in_progress",
                        "basis_scope": "current_phase",
                        "temporal_direction": "present",
                        "temporal_assertion": "ongoing",
                        "inference_purpose": "current_phase",
                        "inference_as_of": analysis_as_of,
                        "target_time": analysis_as_of,
                        "revisable": True,
                        "terminality": "provisional",
                        "required_for_parent": True,
                        "material_stage": True,
                        "prerequisite_evidence_ids": [evidence_ids[0]],
                        "remaining_obligation_ids": ["submit-project"],
                        "active_window_start": "2026-01-01T00:00:00+00:00",
                        "active_window_end": "2027-01-01T00:00:00+00:00",
                        "contradiction_checked": True,
                        "coverage_boundary": "registration and deadline messages",
                        "supporting_signals": [
                            "registration is confirmed and submission remains open"
                        ],
                        "alternative_explanations": [
                            "preparation may be paused or already submitted"
                        ],
                        "contradiction_triggers": [
                            "submission receipt, withdrawal, or deadline change"
                        ],
                        "expires_at": "2027-01-01T00:00:00+00:00",
                        "localized_result": {"en": "Preparation is in progress.", "zh-CN": "准备工作正在进行中。"},
                    },
                },
                {
                    "finding_type": "open_loop_candidate",
                    "owner_model_id": "C8_open_loop_waiting_blocking",
                    "statement": "Wait for a submission receipt.",
                    "localized_statement": {
                        "en": "Wait for a submission receipt",
                        "zh-CN": "等待提交回执",
                    },
                    "semantic_revision": source_refs[1],
                    "evidence_ids": list(evidence_ids),
                    "confidence": "bounded",
                    "modality": "planned",
                    "attributes": {
                        "matter_id": matter_id,
                        "loop_id": "loop:build-week-submission",
                        "semantic_role_key": "submission-receipt",
                        "wait_target": "Build Week project submission",
                        "closure_condition": (
                            "A submission receipt is recorded."
                        ),
                        "critical": True,
                        "supersedes_loop_ids": [
                            "loop:legacy-submission-a",
                            "loop:legacy-submission-b",
                        ],
                    },
                },
                {
                    "finding_type": "event_candidate",
                    "owner_model_id": "C5_event_temporal_trace",
                    "statement": "Registration was confirmed.",
                    "localized_statement": {
                        "en": "Registration was confirmed.",
                        "zh-CN": "报名已经确认。",
                    },
                    "semantic_revision": source_refs[0],
                    "evidence_ids": [evidence_ids[0]],
                    "confidence": "bounded",
                    "modality": "reported",
                    "alternative_explanations": [
                        "The registration could later be withdrawn."
                    ],
                    "attributes": {
                        "matter_id": matter_id,
                        "object_ref": matter_id,
                        "event_kind": "registration_confirmed",
                        "logical_event_key": "build-week:registration-confirmed",
                        "occurrence_boundary": "the registration confirmation message",
                        "claimed_time": "2026-07-01T10:00:00+00:00",
                        "record_time": "2026-07-01T10:00:00+00:00",
                        "actor": "OpenAI",
                        "temporal_direction": "past",
                        "temporal_assertion": "occurred",
                    },
                },
                {
                    "finding_type": "bounded_summary",
                    "owner_model_id": "C12_projection_bilingual_ui",
                    "statement": (
                        "Registration is complete and project preparation "
                        "remains active."
                    ),
                    "localized_statement": {
                        "en": (
                            "Registration is complete and project "
                            "preparation remains active."
                        ),
                        "zh-CN": "报名已完成，参赛项目仍在准备中。",
                    },
                    "semantic_revision": source_refs[1],
                    "evidence_ids": list(evidence_ids),
                    "confidence": "bounded",
                    "modality": "reported",
                    "attributes": {
                        "matter_id": matter_id,
                        "workflow_state": "in_progress",
                        "terminality": "provisional",
                        "completion_licensed": False,
                    },
                },
            ],
        },
    )
    assert imported["auto_apply_status"] == "auto_applied", imported
    assert imported["dispatch_statuses"] == (
        "auto_applied",
        "auto_applied",
        "auto_applied",
        "auto_applied",
        "auto_applied",
    ), imported
    assert service.store.current("admission_decision", matter_id) == admission_before
    work_items = service.matter_work_items(matter_id=matter_id)
    assert work_items["total_count"] == 1
    assert work_items["items"][0]["item_id"] == "work-item:build-week-preparation"
    assert work_items["items"][0]["semantic_role_key"] == "preparation"
    projection = service.store.current("projection", matter_id)
    assert projection["localized_values"]["en"] == "Build Week participation"
    assert projection["localized_rationale"]["en"] == (
        "Registration is complete and project preparation remains active."
    )
    successor = service.matter_semantic_analysis_plan(
        matter_id=matter_id,
        queue=False,
    )
    assert successor["status_counts"] == {"rebase_required": 1}
    assert successor["items"][0]["current_semantic_state"][
        "work_items"
    ][0]["item_id"] == "work-item:build-week-preparation"
    assert [
        item["loop_id"]
        for item in successor["items"][0][
            "current_semantic_state"
        ]["open_loops"]
    ] == ["loop:build-week-submission"]
    detail = service.matter_detail(
        matter_id=matter_id,
        locale="en",
    )
    assert len(detail["open_loops"]) == 1
    assert detail["open_loops"][0]["wait_target"] == (
        "Build Week project submission"
    )
    timeline = tuple(service.store.iter_current("temporal_event"))
    registration = next(
        item
        for item in timeline
        if item["kind"] == "registration_confirmed"
    )
    assert registration["modality"] == "reported"
    assert registration["alternative_explanations"] == []
