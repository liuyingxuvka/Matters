from __future__ import annotations

from io import StringIO

from matters.analysis.depth import MatterSemanticDepthOwner
from matters.application.orchestrator import MatterService
from matters.cli.main import run


def _service(tmp_path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )


def _append(service: MatterService, owner: str, object_id: str, payload) -> None:
    assert service.store is not None
    service.store.append(
        owner,
        object_id,
        service.store.next_revision(owner, object_id),
        payload,
    )


def _seed_source(
    service: MatterService,
    *,
    suffix: str,
) -> tuple[str, str, str]:
    assert service.coverage_ledger is not None
    source_id = f"source:{suffix}"
    occurrence_id = f"occurrence:{suffix}"
    evidence_id = f"evidence:{source_id}:1:anchor"
    _append(
        service,
        "source_version",
        source_id,
        {
            "source_id": source_id,
            "version": 1,
            "provider": "filesystem",
            "external_reference": {
                "provider": "filesystem",
                "external_id": occurrence_id,
                "object_type": "document",
                "locator": "",
            },
            "content": {"text": f"Evidence for {suffix}"},
            "content_hash": f"sha256:content-{suffix}",
            "metadata_hash": f"sha256:metadata-{suffix}",
            "tombstone": False,
        },
    )
    _append(
        service,
        "evidence_anchor",
        evidence_id,
        {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_version": 1,
            "location": {"field": "text"},
            "text": f"Evidence for {suffix}",
            "modality": "reported",
            "current": True,
        },
    )
    service.coverage_ledger.reconcile_inventory(
        scope_id="scope:test",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": occurrence_id,
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {"occurrence_id": occurrence_id, "status": "tracked"},
        ),
    )
    for stage_id in ("extraction", "analysis", "evidence"):
        service.coverage_ledger.mark_stage(
            object_id=occurrence_id,
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"sha256:{stage_id}-{suffix}",
            refresh_summary=False,
        )
    service.coverage_ledger.mark_stage(
        object_id=occurrence_id,
        stage_id="owner_dispatch",
        status="current",
        input_fingerprint=f"sha256:owner-{suffix}",
        refresh_summary=False,
    )
    service.assess_depth(
        occurrence_id=occurrence_id,
        inventory_revision=1,
        criteria={
            "coverage_terminal": True,
            "extraction_current": True,
            "analysis_terminal": True,
            "evidence_anchored": True,
            "owner_dispatch_terminal": True,
        },
    )
    return source_id, occurrence_id, evidence_id


def _seed_matter(
    service: MatterService,
    *,
    suffix: str,
    source_id: str,
    evidence_id: str,
) -> str:
    assert service.coverage_ledger is not None
    matter_id = f"matter:{suffix}"
    semantic_revision = f"semantic:{suffix}:v1"
    _append(
        service,
        "admission_decision",
        matter_id,
        {
            "status": "admitted",
            "rationale": f"Admit {suffix}",
            "matter": {
                "matter_id": matter_id,
                "source_ids": (f"{source_id}:v1",),
                "evidence_ids": (evidence_id,),
                "rationale": f"Admit {suffix}",
                "admitted": True,
                "semantic_identity_id": f"identity:{suffix}",
                "object_kind": "matter",
            },
        },
    )
    _append(
        service,
        "projection",
        matter_id,
        {
            "matter_id": matter_id,
            "semantic_revision": semantic_revision,
            "state": "in_progress",
            "evidence_ids": (evidence_id,),
            "localized_values": {
                "en": f"Matter {suffix}",
                "zh-CN": f"事项 {suffix}",
            },
            "localized_rationale": {
                "en": f"Summary for {suffix}",
                "zh-CN": f"{suffix} 的摘要",
            },
            "locale_revisions": {
                "en": semantic_revision,
                "zh-CN": semantic_revision,
            },
            "available_locales": ("en", "zh-CN"),
            "default_locale": "en",
            "equivalence_status": "equivalent",
        },
    )
    _append(
        service,
        "matter_activity",
        matter_id,
        {
            "matter_id": matter_id,
            "source_matter_id": matter_id,
            "material_clue_id": f"clue:{suffix}",
            "latest_meaningful_clue_at": "2026-07-20T12:00:00+00:00",
            "localized_summary": {
                "en": f"Latest clue for {suffix}",
                "zh-CN": f"{suffix} 的最新线索",
            },
            "semantic_revision": semantic_revision,
            "material_clue_revision": f"clue:{suffix}:v1",
            "summary_revision": semantic_revision,
            "activity_order_revision": f"activity:{suffix}:v1",
            "evidence_ids": (evidence_id,),
            "ancestor_propagated": False,
            "persistence_revision": 1,
            "processed_at": "2026-07-20T12:01:00+00:00",
        },
    )
    _append(
        service,
        "matter_hierarchy_audit",
        matter_id,
        {
            "matter_id": matter_id,
            "revision": 1,
            "status": "current",
            "change_ref": f"seed:{suffix}",
            "stages": {
                "hierarchy_decision": "current",
                "containment_current": "current",
                "child_state_current": "current",
                "ancestor_rollup_current": "current",
                "hierarchy_projection_current": "current",
                "ui_reachable": "current",
            },
        },
    )
    service.coverage_ledger.register_matters(
        matters=(
            {
                "matter_id": matter_id,
                "matter_kind": "root_matter",
                "semantic_revision": semantic_revision,
                "hierarchy_revision": f"hierarchy:{suffix}:v1",
            },
        ),
    )
    return matter_id


def _attach(
    service: MatterService,
    *,
    parent_id: str,
    child_id: str,
    evidence_id: str,
) -> None:
    _append(
        service,
        "matter_containment_edge",
        f"edge:{parent_id}:{child_id}",
        {
            "edge_id": f"edge:{parent_id}:{child_id}",
            "parent_matter_id": parent_id,
            "child_matter_id": child_id,
            "role": "required",
            "confidence": "high",
            "rationale": "The child is part of the parent.",
            "evidence_ids": (evidence_id,),
            "ordinal": 0,
            "boundary_revision": 1,
            "freshness": "current",
            "active": True,
            "updated_at": "2026-07-20T12:02:00+00:00",
        },
    )


def test_matter_depth_requires_real_aggregate_owner_results(tmp_path):
    service = _service(tmp_path)
    root_source, _root_occurrence, root_evidence = _seed_source(
        service,
        suffix="root",
    )
    child_source, child_occurrence, child_evidence = _seed_source(
        service,
        suffix="child",
    )
    root_id = _seed_matter(
        service,
        suffix="root",
        source_id=root_source,
        evidence_id=root_evidence,
    )
    child_id = _seed_matter(
        service,
        suffix="child",
        source_id=child_source,
        evidence_id=child_evidence,
    )
    _attach(
        service,
        parent_id=root_id,
        child_id=child_id,
        evidence_id=child_evidence,
    )
    assert service.store is not None
    owner = MatterSemanticDepthOwner(service.store)

    sufficient = owner.assess(
        matter_id=root_id,
        inventory_revision=1,
    )
    history_count = len(service.store.history("semantic_depth", root_id))
    repeated = owner.assess(
        matter_id=root_id,
        inventory_revision=1,
    )

    assert sufficient.state == "sufficient"
    assert sufficient.assessment_kind == "matter"
    assert sufficient.related_matter_count == 2
    assert repeated == sufficient
    assert len(service.store.history("semantic_depth", root_id)) == history_count

    service.depth.mark_stale(
        occurrence_id=child_occurrence,
        inventory_revision=1,
        dependencies=("source_changed",),
    )
    stale = owner.assess(
        matter_id=root_id,
        inventory_revision=1,
    )
    assert stale.state == "stale"
    assert "source_depth_current" in stale.missing


def test_projection_only_object_is_not_a_canonical_matter(tmp_path):
    service = _service(tmp_path)
    projection_only_id = "matter:projection-only"
    _append(
        service,
        "projection",
        projection_only_id,
        {
            "matter_id": projection_only_id,
            "semantic_revision": "semantic:v1",
            "equivalence_status": "equivalent",
        },
    )

    result = service.rebase_matter_semantic_depth(limit=100)

    assert result["scanned_matter_count"] == 0
    assert service.store is not None
    assert service.store.current(
        "semantic_depth",
        projection_only_id,
    ) is None


def test_matter_depth_rebase_is_bounded_resumable_and_cli_exposed(tmp_path):
    service = _service(tmp_path)
    for suffix in ("a", "b", "c"):
        source_id, _occurrence_id, evidence_id = _seed_source(
            service,
            suffix=suffix,
        )
        _seed_matter(
            service,
            suffix=suffix,
            source_id=source_id,
            evidence_id=evidence_id,
        )

    first = service.rebase_matter_semantic_depth(limit=2)
    assert service.store is not None
    coverage_history_count = len(
        service.store.history("object_coverage", "matter:a")
    )
    repeated_first = service.rebase_matter_semantic_depth(limit=2)
    second = service.rebase_matter_semantic_depth(
        after_matter_id=first["next_cursor"],
        limit=2,
    )

    assert first["scanned_matter_count"] == 2
    assert first["assessed_matter_count"] == 2
    assert first["has_more"] is True
    assert repeated_first["state_counts"] == {"sufficient": 2}
    assert (
        len(service.store.history("object_coverage", "matter:a"))
        == coverage_history_count
    )
    assert second["scanned_matter_count"] == 1
    assert second["has_more"] is False
    assert second["state_counts"] == {"sufficient": 1}

    class Stub:
        def rebase_matter_semantic_depth(self, **kwargs):
            return kwargs

    stdout = StringIO()
    assert (
        run(
            [
                "matter-depth-rebase",
                "--after-matter-id",
                "matter:a",
                "--limit",
                "7",
                "--max-descendants",
                "900",
                "--max-sources",
                "8000",
            ],
            service=Stub(),
            stdout=stdout,
        )
        == 0
    )
    assert '"after_matter_id": "matter:a"' in stdout.getvalue()
    assert '"max_descendants": 900' in stdout.getvalue()


def test_occurrence_callback_cannot_green_a_canonical_matter(tmp_path):
    service = _service(tmp_path)
    source_id, _occurrence_id, evidence_id = _seed_source(
        service,
        suffix="guard",
    )
    matter_id = _seed_matter(
        service,
        suffix="guard",
        source_id=source_id,
        evidence_id=evidence_id,
    )
    assert service.coverage_ledger is not None
    before = service.store.current("semantic_depth", matter_id)

    service._refresh_semantic_depth_for_object(
        matter_id,
        "sha256:owner-result",
    )

    assert service.store.current("semantic_depth", matter_id) == before


def test_matter_depth_accepts_not_applicable_owner_terminal(tmp_path):
    service = _service(tmp_path)
    source_id, occurrence_id, evidence_id = _seed_source(
        service,
        suffix="not-applicable",
    )
    matter_id = _seed_matter(
        service,
        suffix="not-applicable",
        source_id=source_id,
        evidence_id=evidence_id,
    )
    assert service.coverage_ledger is not None
    service.coverage_ledger.mark_stage(
        object_id=occurrence_id,
        stage_id="owner_dispatch",
        status="not_applicable",
        input_fingerprint="sha256:owner-not-applicable",
        refresh_summary=False,
    )

    result = MatterSemanticDepthOwner(service.store).assess(
        matter_id=matter_id,
        inventory_revision=1,
    )

    assert result.state == "sufficient"
    assert "owner_results_terminal" in result.satisfied


def test_matter_depth_separates_stale_source_from_exact_anchor(tmp_path):
    service = _service(tmp_path)
    source_id, occurrence_id, evidence_id = _seed_source(
        service,
        suffix="source-updated",
    )
    matter_id = _seed_matter(
        service,
        suffix="source-updated",
        source_id=source_id,
        evidence_id=evidence_id,
    )
    _append(
        service,
        "source_version",
        source_id,
        {
            "source_id": source_id,
            "version": 2,
            "provider": "filesystem",
            "external_reference": {
                "provider": "filesystem",
                "external_id": occurrence_id,
                "object_type": "document",
                "locator": "",
            },
            "content": {"text": "Updated evidence"},
            "content_hash": "sha256:updated-content",
            "metadata_hash": "sha256:updated-metadata",
            "tombstone": False,
        },
    )

    result = MatterSemanticDepthOwner(service.store).assess(
        matter_id=matter_id,
        inventory_revision=1,
    )

    assert result.state == "stale"
    assert "source_depth_current" in result.missing
    assert "evidence_anchored" in result.satisfied
    assert f"source_version:{source_id}:v1" in result.stale_dependencies
    assert f"evidence_anchor:{evidence_id}" not in result.stale_dependencies


def test_matter_depth_blocks_malformed_source_revision_ref(tmp_path):
    service = _service(tmp_path)
    source_id, _occurrence_id, evidence_id = _seed_source(
        service,
        suffix="malformed",
    )
    matter_id = _seed_matter(
        service,
        suffix="malformed",
        source_id=source_id,
        evidence_id=evidence_id,
    )
    assert service.store is not None
    current = service.store.current("admission_decision", matter_id)
    assert current is not None
    current["matter"]["source_ids"] = (source_id,)
    _append(service, "admission_decision", matter_id, current)

    result = MatterSemanticDepthOwner(service.store).assess(
        matter_id=matter_id,
        inventory_revision=1,
    )

    assert result.state == "blocked"
    assert (
        f"source_revision_ref_invalid:{source_id}"
        in result.blocker_class
    )
