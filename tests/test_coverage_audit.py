from matters.analysis.depth import SemanticDepthOwner
from matters.application.coverage_audit import CoverageAuditService
from matters.application.coverage_ledger import (
    ObjectCoverageLedger,
    STAGE_ORDER,
    bounded_stage_output_set_ref,
)
from matters.application.hierarchy import MatterHierarchyOwner
from matters.application.orchestrator import MatterService
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.inventory.owners import (
    CandidateScope,
    InventoryOccurrence,
    TrackingPolicy,
)


def _ready_root_coverage(
    store: SQLiteStore,
    ledger: ObjectCoverageLedger,
    matter_id: str,
) -> None:
    ledger.register_matters(
        matters=(
            {
                "matter_id": matter_id,
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:current",
                "hierarchy_revision": "hierarchy:current",
            },
        ),
        inventory_revision=1,
    )
    store.append(
        "admission_decision",
        matter_id,
        1,
        {"status": "admitted", "matter": {"matter_id": matter_id}},
    )
    for stage_id in STAGE_ORDER[9:]:
        ledger.mark_stage(
            object_id=matter_id,
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"sha256:{stage_id}",
            refresh_summary=False,
        )
    with store.connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO matter_hierarchy_stage_index"
            "(matter_id, next_stage, terminal, ui_reachable, blocked, "
            "revision, change_ref, updated_at) VALUES (?, '', 1, 1, 0, 1, ?, ?)",
            (matter_id, "hierarchy:current", "2099-01-01T00:00:00+00:00"),
        )


def test_coverage_output_set_pointer_is_exact_and_bounded():
    output_ids = tuple(f"evidence:source:1:{index:06d}" for index in range(50_000))

    pointer = bounded_stage_output_set_ref(
        "evidence_anchor",
        "source:one:v1",
        output_ids,
    )

    assert pointer.startswith(
        "evidence_anchor_set:source:one:v1:count:50000:sha256:"
    )
    assert len(pointer) < 160
    assert output_ids[0] not in pointer
    assert pointer == bounded_stage_output_set_ref(
        "evidence_anchor",
        "source:one:v1",
        output_ids,
    )


def test_legacy_evidence_pointer_rebase_preserves_exact_set_and_stage_state(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    service = MatterService(
        private_root=tmp_path / "private",
        repository_root=repository_root,
    )
    store = service.store
    ledger = service.coverage_ledger
    assert store is not None
    assert ledger is not None
    ledger.reconcile_inventory(
        scope_id="scope:test",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:legacy-evidence",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:legacy-evidence",
                "status": "tracked",
            },
        ),
    )
    ledger.mark_stage(
        object_id="occurrence:legacy-evidence",
        stage_id="source_version",
        status="current",
        input_fingerprint="sha256:source",
        output_ref="source:one:v1",
    )
    anchor_ids = ("evidence:source:one:1:0001", "evidence:source:one:1:0002")
    ledger.mark_stage(
        object_id="occurrence:legacy-evidence",
        stage_id="evidence",
        status="current",
        input_fingerprint="sha256:evidence",
        output_ref=",".join(anchor_ids),
    )

    result = service.rebase_legacy_evidence_pointers(limit=1)

    assert result == {
        "scanned_object_count": 1,
        "migrated_object_count": 1,
        "next_cursor": "",
        "has_more": False,
        "status": "current",
    }
    current = ledger.current("occurrence:legacy-evidence")
    assert current is not None
    pointer = current.stages["evidence"]
    assert pointer.status == "current"
    assert pointer.input_fingerprint == "sha256:evidence"
    assert pointer.output_ref == bounded_stage_output_set_ref(
        "evidence_anchor",
        "source:one:v1",
        anchor_ids,
    )
    evidence_history = tuple(
        row["stages"]["evidence"]["output_ref"]
        for row in store.history(
            "object_coverage",
            "occurrence:legacy-evidence",
        )
        if "evidence" in row["stages"]
    )
    assert evidence_history[-2:] == (
        ",".join(anchor_ids),
        pointer.output_ref,
    )


def test_coverage_audit_reports_occurrence_and_matter_first_gap(tmp_path):
    ledger = ObjectCoverageLedger(SQLiteStore(tmp_path / "private", tmp_path / "repo"))
    ledger.reconcile_inventory(
        scope_id="scope:test",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:1",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {"occurrence_id": "occurrence:1", "status": "tracked"},
        ),
    )
    ledger.register_matters(
        matters=(
            {
                "matter_id": "matter:1",
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:1",
                "hierarchy_revision": "hierarchy:1",
            },
        ),
        inventory_revision=1,
    )
    ledger.mark_stage(
        object_id="occurrence:1",
        stage_id="source_version",
        status="current",
        input_fingerprint="sha256:source",
    )
    snapshot = CoverageAuditService(ledger).audit()

    assert snapshot.total_objects == 2
    assert snapshot.occurrence_objects == 1
    assert snapshot.matter_objects == 1
    assert tuple(snapshot.stage_counts) == STAGE_ORDER
    by_id = {row.object_id: row for row in snapshot.objects}
    assert by_id["occurrence:1"].first_gap_stage == "content_selection"
    assert by_id["matter:1"].first_gap_stage == "semantic_depth"
    assert snapshot.run_identity.startswith("sha256:")


def test_surface_audit_skips_object_universe_contract_scan(tmp_path, monkeypatch):
    ledger = ObjectCoverageLedger(
        SQLiteStore(tmp_path / "private", tmp_path / "repo")
    )
    ledger.register_matters(
        matters=(
            {
                "matter_id": "matter:surface",
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:surface",
                "hierarchy_revision": "hierarchy:surface",
            },
        ),
        inventory_revision=1,
    )
    ledger.store.append(
        "admission_decision",
        "matter:surface",
        1,
        {
            "status": "admitted",
            "matter": {"matter_id": "matter:surface"},
        },
    )
    monkeypatch.setattr(
        ledger.store,
        "coverage_contract_status",
        lambda: (_ for _ in ()).throw(
            AssertionError("surface audit must not scan the object contract")
        ),
    )

    snapshot = CoverageAuditService(ledger).surface_audit(limit=100)

    assert snapshot.total_surfaces == 7
    assert snapshot.gap_surfaces >= 1
    assert snapshot.coverage_contract["surface_status"] == "partial"
    assert snapshot.run_identity.startswith("sha256:")


def test_registered_matter_is_ui_ready_only_after_every_owned_stage(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    depth = SemanticDepthOwner(
        store,
        result_sink=ledger.sync_semantic_depth_owner_results,
    )
    hierarchy = MatterHierarchyOwner(
        store,
        coverage_result_sink=ledger.sync_hierarchy_owner_results,
    )
    ledger.register_matters(
        matters=(
            {
                "matter_id": "matter:ready",
                "matter_kind": "child_matter",
                "semantic_revision": "semantic:1",
                "hierarchy_revision": "hierarchy:1",
            },
        ),
        inventory_revision=1,
    )
    pending = ledger.current("matter:ready")
    assert pending is not None
    assert pending.stages["semantic_depth"].status == "pending"
    assert all(
        pending.stages[stage_id].status == "pending"
        for stage_id in (
            "hierarchy_registration",
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
        )
    )

    depth.assess(
        occurrence_id="matter:ready",
        inventory_revision=1,
        criteria={
            "coverage_terminal": True,
            "extraction_current": True,
            "analysis_terminal": True,
            "evidence_anchored": True,
            "owner_dispatch_terminal": True,
        },
    )
    store.append(
        "admission_decision",
        "matter:ready",
        1,
        {"status": "admitted", "matter": {"matter_id": "matter:ready"}},
    )
    store.append(
        "projection",
        "matter:ready",
        1,
        {
            "matter_id": "matter:ready",
            "semantic_revision": "semantic:1",
            "state": "planned",
            "localized_values": {
                "en": "Ready matter",
                "zh-CN": "就绪事项",
            },
            "localized_rationale": {
                "en": "Ready matter summary",
                "zh-CN": "就绪事项摘要",
            },
            "locale_revisions": {
                "en": "semantic:1",
                "zh-CN": "semantic:1",
            },
            "equivalence_status": "equivalent",
        },
    )
    hierarchy.register_matter(
        "matter:ready",
        change_ref="hierarchy:1",
    )
    owner_joined = ledger.current("matter:ready")
    assert owner_joined is not None
    assert owner_joined.stages["semantic_depth"].status == "current"
    assert all(
        owner_joined.stages[stage_id].status == "current"
        for stage_id in (
            "hierarchy_registration",
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
        )
    )
    assert owner_joined.ui_ready is False

    for stage_id in (
        "localization",
        "meaningful_clue_summary",
        "generated_hero",
        "supplemental_information",
        "ui_projection",
        "ui_reachable",
    ):
        ledger.mark_stage(
            object_id="matter:ready",
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"sha256:{stage_id}",
            refresh_summary=stage_id == STAGE_ORDER[-1],
        )
    snapshot = CoverageAuditService(ledger).audit(object_kind="matter")

    assert snapshot.total_objects == 1
    assert snapshot.ui_ready_objects == 1
    assert snapshot.objects[0].ui_ready is True
    assert snapshot.objects[0].first_gap_stage == ""


def test_depth_and_hierarchy_invalidation_follow_owner_results(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    depth = SemanticDepthOwner(
        store,
        result_sink=ledger.sync_semantic_depth_owner_results,
    )
    hierarchy = MatterHierarchyOwner(
        store,
        coverage_result_sink=ledger.sync_hierarchy_owner_results,
    )
    ledger.register_matters(
        matters=(
            {
                "matter_id": "matter:owner-sync",
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:1",
                "hierarchy_revision": "hierarchy:1",
            },
        ),
        inventory_revision=1,
    )
    depth.assess(
        occurrence_id="matter:owner-sync",
        inventory_revision=1,
        criteria={
            "coverage_terminal": True,
            "extraction_current": True,
            "analysis_terminal": True,
            "evidence_anchored": True,
            "owner_dispatch_terminal": True,
        },
    )
    store.append(
        "admission_decision",
        "matter:owner-sync",
        1,
        {
            "status": "admitted",
            "matter": {"matter_id": "matter:owner-sync"},
        },
    )
    store.append(
        "projection",
        "matter:owner-sync",
        1,
        {
            "matter_id": "matter:owner-sync",
            "semantic_revision": "semantic:1",
            "state": "planned",
            "localized_values": {
                "en": "Owner sync",
                "zh-CN": "所有者同步",
            },
            "localized_rationale": {
                "en": "Owner sync summary",
                "zh-CN": "所有者同步摘要",
            },
            "locale_revisions": {
                "en": "semantic:1",
                "zh-CN": "semantic:1",
            },
            "equivalence_status": "equivalent",
        },
    )
    hierarchy.register_matter(
        "matter:owner-sync",
        change_ref="hierarchy:1",
    )

    current = ledger.current("matter:owner-sync")
    assert current is not None
    assert current.stages["semantic_depth"].status == "current"
    assert all(
        current.stages[stage_id].status == "current"
        for stage_id in (
            "hierarchy_registration",
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
        )
    )

    depth.assess(
        occurrence_id="matter:owner-sync",
        inventory_revision=2,
        criteria={},
        stale_dependencies=("analysis",),
    )
    hierarchy.mark_dependency_changed(
        "matter:owner-sync",
        change_ref="hierarchy:2",
        refresh=False,
    )
    stale = ledger.current("matter:owner-sync")
    assert stale is not None
    assert stale.stages["semantic_depth"].status == "stale"
    assert stale.stages["hierarchy_registration"].status == "current"
    assert all(
        stale.stages[stage_id].status == "stale"
        for stage_id in (
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
        )
    )
    assert stale.ui_ready is False

    depth.assess(
        occurrence_id="matter:owner-sync",
        inventory_revision=2,
        criteria={
            "coverage_terminal": True,
            "extraction_current": True,
            "analysis_terminal": True,
            "evidence_anchored": True,
            "owner_dispatch_terminal": True,
        },
    )
    hierarchy.mark_dependency_changed(
        "matter:owner-sync",
        change_ref="hierarchy:2",
        refresh=True,
    )
    recomputed = ledger.current("matter:owner-sync")
    assert recomputed is not None
    assert recomputed.stages["semantic_depth"].status == "current"
    assert all(
        recomputed.stages[stage_id].status == "current"
        for stage_id in (
            "hierarchy_registration",
            "hierarchy_local_validation",
            "hierarchy_global_validation",
            "hierarchy_freshness",
            "hierarchy_projection",
        )
    )


def test_hierarchy_owner_sync_reads_only_indexed_affected_coverage(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    hierarchy = MatterHierarchyOwner(
        store,
        coverage_result_sink=ledger.sync_hierarchy_owner_results,
    )
    ledger.register_matters(
        matters=tuple(
            {
                "matter_id": f"matter:{index:04d}",
                "matter_kind": "root_matter",
                "semantic_revision": f"semantic:{index}",
                "hierarchy_revision": f"hierarchy:{index}",
            }
            for index in range(250)
        ),
        inventory_revision=1,
    )
    target_id = "matter:0249"
    store.append(
        "projection",
        target_id,
        1,
        {
            "matter_id": target_id,
            "semantic_revision": "semantic:249",
            "state": "planned",
            "localized_values": {
                "en": "Indexed hierarchy target",
                "zh-CN": "索引层级目标",
            },
            "localized_rationale": {
                "en": "Only this Matter should be synchronized.",
                "zh-CN": "只应同步这一事项。",
            },
            "locale_revisions": {
                "en": "semantic:249",
                "zh-CN": "semantic:249",
            },
            "equivalence_status": "equivalent",
        },
    )
    store.append(
        "admission_decision",
        target_id,
        1,
        {"status": "admitted", "matter": {"matter_id": target_id}},
    )
    original_current_many = store.current_many
    hydrated: list[tuple[str, int]] = []

    def recorded_current_many(owner, object_ids):
        ids = tuple(object_ids)
        hydrated.append((owner, len(ids)))
        return original_current_many(owner, ids)

    def forbidden_iter_current(owner):
        raise AssertionError(
            f"hierarchy sync must not scan the full {owner} owner"
        )

    store.current_many = recorded_current_many  # type: ignore[method-assign]
    store.iter_current = forbidden_iter_current  # type: ignore[method-assign]

    hierarchy.register_matter(target_id, change_ref="hierarchy:0249")

    target = ledger.current(target_id)
    assert target is not None
    assert target.stages["hierarchy_registration"].status == "current"
    assert ("object_coverage", 1) in hydrated
    assert ("matter_hierarchy_audit", 1) in hydrated
    assert all(count == 1 for _owner, count in hydrated)


def test_existing_matter_coverage_rebase_is_bounded_resumable_and_not_startup(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    private_root = tmp_path / "private"
    service = MatterService(
        private_root=private_root,
        repository_root=repository_root,
    )
    projected_matter_ids = tuple(
        f"matter:legacy:{index}" for index in range(3)
    )
    for index, matter_id in enumerate(projected_matter_ids):
        service.store.append(
            "admission_decision",
            matter_id,
            1,
            {
                "status": "admitted",
                "matter": {"matter_id": matter_id},
            },
        )
        service.store.append(
            "projection",
            matter_id,
            1,
            {
                "matter_id": matter_id,
                "semantic_revision": f"semantic:{index}",
                "state": "planned",
                "localized_values": {
                    "en": f"Legacy Matter {index}",
                    "zh-CN": f"历史事项 {index}",
                },
                "localized_rationale": {
                    "en": f"Legacy summary {index}",
                    "zh-CN": f"历史摘要 {index}",
                },
                "locale_revisions": {
                    "en": f"semantic:{index}",
                    "zh-CN": f"semantic:{index}",
                },
                "equivalence_status": "equivalent",
            },
        )
        service.hierarchy.register_matter(
            matter_id,
            change_ref=f"hierarchy:{index}",
        )
    missing_projection_id = "matter:legacy:missing-projection"
    service.store.append(
        "admission_decision",
        missing_projection_id,
        1,
        {
            "status": "admitted",
            "matter": {
                "matter_id": missing_projection_id,
            },
        },
    )
    service.hierarchy.register_matter(
        missing_projection_id,
        change_ref="hierarchy:missing-projection",
    )
    matter_ids = (*projected_matter_ids, missing_projection_id)
    assert all(
        service.coverage_ledger.current(matter_id) is None
        for matter_id in matter_ids
    )

    restarted = MatterService(
        private_root=private_root,
        repository_root=repository_root,
    )
    assert all(
        restarted.coverage_ledger.current(matter_id) is None
        for matter_id in matter_ids
    )

    def forbidden_iter_current(owner):
        raise AssertionError(
            f"Matter coverage rebase must not scan the full {owner} owner"
        )

    restarted.store.iter_current = forbidden_iter_current  # type: ignore[method-assign]
    cursor = ""
    batches = []
    for _attempt in range(5):
        batch = restarted.rebase_existing_matter_coverage(
            after_matter_id=cursor,
            limit=1,
        )
        batches.append(batch)
        assert batch["scanned_matter_count"] <= 1
        if not batch["has_more"]:
            break
        cursor = batch["next_cursor"]

    assert [batch["status"] for batch in batches] == [
        "partial",
        "partial",
        "partial",
        "current",
    ]
    for matter_id in matter_ids:
        row = restarted.coverage_ledger.current(matter_id)
        assert row is not None
        assert row.provider == "matters"
        assert row.stages["semantic_depth"].status == "pending"
        assert row.stages["hierarchy_registration"].status == "current"
        if matter_id in projected_matter_ids:
            assert all(
                row.stages[stage_id].status == "current"
                for stage_id in (
                    "hierarchy_local_validation",
                    "hierarchy_global_validation",
                    "hierarchy_freshness",
                    "hierarchy_projection",
                )
            )
        else:
            assert row.stages["hierarchy_projection"].status != "current"
    assert restarted.rebase_existing_matter_coverage(limit=1) == {
        "scanned_matter_count": 0,
        "registered_matter_count": 0,
        "next_cursor": "",
        "has_more": False,
        "status": "current",
    }


def test_matter_coverage_rebase_sql_excludes_projection_only_source_and_candidate(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    canonical_id = "matter:canonical"
    store.append(
        "admission_decision",
        canonical_id,
        1,
        {"status": "admitted", "matter": {"matter_id": canonical_id}},
    )
    expected_stages = {
        "hierarchy_decision": "current",
        "containment_current": "current",
        "child_state_current": "current",
        "ancestor_rollup_current": "current",
        "hierarchy_projection_current": "current",
        "ui_reachable": "current",
    }
    for object_id in (canonical_id, "source:projected", "candidate:projected"):
        store.append(
            "matter_hierarchy_audit",
            object_id,
            1,
            {
                "matter_id": object_id,
                "stages": expected_stages,
                "change_ref": "test:legacy-index",
            },
        )

    page, has_more = store.missing_matter_coverage_page(
        after_matter_id="",
        limit=10,
    )

    assert has_more is False
    assert tuple(item["matter_id"] for item in page) == (canonical_id,)


def test_noncanonical_matter_coverage_reconcile_dry_run_then_retires_append_only(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    service = MatterService(
        private_root=tmp_path / "private",
        repository_root=repository_root,
    )
    canonical_id = "matter:canonical"
    service.store.append(
        "admission_decision",
        canonical_id,
        1,
        {"status": "admitted", "matter": {"matter_id": canonical_id}},
    )
    service.coverage_ledger.register_matters(
        matters=tuple(
            {
                "matter_id": object_id,
                "matter_kind": "root_matter",
                "semantic_revision": "semantic:test",
                "hierarchy_revision": "hierarchy:test",
            }
            for object_id in (
                canonical_id,
                "source:projected",
                "candidate:projected",
            )
        )
    )

    preview = service.reconcile_noncanonical_matter_coverage(
        limit=10,
        dry_run=True,
    )
    assert preview == {
        "scanned_object_count": 2,
        "retired_object_count": 0,
        "dry_run": True,
        "next_cursor": "",
        "has_more": False,
        "status": "current",
    }
    assert service.coverage_ledger.current("source:projected").active is True

    applied = service.reconcile_noncanonical_matter_coverage(limit=10)
    assert applied["retired_object_count"] == 2
    assert applied["dry_run"] is False
    for object_id in ("source:projected", "candidate:projected"):
        retired = service.coverage_ledger.current(object_id)
        assert retired is not None
        assert retired.active is False
        assert retired.stages["matter"].output_ref == (
            "retired:noncanonical_hierarchy_projection_leak"
        )
    assert service.coverage_ledger.current(canonical_id).active is True


def test_coverage_audit_excludes_inactive_legacy_stage_rows(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:test",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:active",
                "provider": "filesystem",
                "object_type": "document",
            },
            {
                "occurrence_id": "occurrence:retired",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {"occurrence_id": "occurrence:active", "status": "tracked"},
            {"occurrence_id": "occurrence:retired", "status": "tracked"},
        ),
    )
    retired = store.current("object_coverage", "occurrence:retired")
    assert retired is not None
    retired["active"] = False
    retired["stages"]["visual"] = {"retired_legacy_shape": True}
    store.append(
        "object_coverage",
        "occurrence:retired",
        store.next_revision("object_coverage", "occurrence:retired"),
        retired,
    )

    snapshot = CoverageAuditService(ledger).audit()

    assert snapshot.total_objects == 1
    assert [row.object_id for row in snapshot.objects] == [
        "occurrence:active"
    ]
    assert "visual" not in snapshot.stage_counts


def test_stage_rebase_preserves_nontracked_legacy_visual_history(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:test",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:hard-excluded",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:hard-excluded",
                "status": "tracked",
            },
        ),
    )
    legacy = store.current(
        "object_coverage",
        "occurrence:hard-excluded",
    )
    assert legacy is not None
    legacy["active"] = False
    legacy["disposition"] = "hard_excluded"
    legacy["required_stages"] = (*STAGE_ORDER, "visual")
    legacy["stages"]["visual"] = {"retired_legacy_shape": True}
    store.append(
        "object_coverage",
        "occurrence:hard-excluded",
        store.next_revision(
            "object_coverage",
            "occurrence:hard-excluded",
        ),
        legacy,
    )

    candidates = store.legacy_coverage_stage_schema_page(
        after_object_id="",
        limit=10,
        current_stage_order=STAGE_ORDER,
    )

    assert candidates == ()


def test_coverage_audit_uses_only_materialized_indexes_for_its_page(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    occurrences = tuple(
        {
            "occurrence_id": f"occurrence:{index:04d}",
            "provider": "filesystem",
            "object_type": "document",
        }
        for index in range(250)
    )
    ledger.reconcile_inventory(
        scope_id="scope:scale",
        inventory_revision=1,
        occurrences=occurrences,
        dispositions=tuple(
            {
                "occurrence_id": item["occurrence_id"],
                "status": "tracked",
            }
            for item in occurrences
        ),
    )

    def forbidden_rows():
        raise AssertionError("coverage audit must not decode the full ledger")

    ledger.rows = forbidden_rows  # type: ignore[method-assign]
    original_current_many = store.current_many
    hydrated: list[int] = []

    def recorded_current_many(owner, object_ids):
        ids = tuple(object_ids)
        if owner == "object_coverage":
            hydrated.append(len(ids))
        return original_current_many(owner, ids)

    store.current_many = recorded_current_many  # type: ignore[method-assign]

    snapshot = CoverageAuditService(ledger).audit(offset=100, limit=7)

    assert snapshot.total_objects == 250
    assert snapshot.total_matching == 250
    assert len(snapshot.objects) == 7
    assert snapshot.stage_counts["authorization"]["current"] == 250
    # Reconciliation has not dispatched source-version work yet.
    assert snapshot.stage_counts["source_version"]["missing"] == 250
    assert snapshot.audit_index_status == "current"
    assert snapshot.indexed_objects == 250
    assert snapshot.unindexed_objects == 0
    assert hydrated == []


def test_materialized_first_gap_prefers_earlier_blocked_stage(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    ledger = ObjectCoverageLedger(
        SQLiteStore(tmp_path / "private", repository_root)
    )
    ledger.reconcile_inventory(
        scope_id="scope:blocked",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:blocked",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:blocked",
                "status": "tracked",
            },
        ),
    )
    ledger.mark_stage(
        object_id="occurrence:blocked",
        stage_id="content_selection",
        status="current",
        input_fingerprint="sha256:selection",
    )
    ledger.mark_stage(
        object_id="occurrence:blocked",
        stage_id="source_version",
        status="blocked",
        input_fingerprint="sha256:source",
        failure_class="source_unavailable",
    )

    snapshot = CoverageAuditService(ledger).audit()

    assert snapshot.audit_index_status == "current"
    assert snapshot.gaps[0].first_gap_stage == "source_version"
    assert snapshot.gaps[0].status == "blocked"
    assert snapshot.gaps[0].failure_class == "source_unavailable"
    assert snapshot.objects[0].stages["extraction"] == "missing"


def test_blocked_disposition_is_a_materialized_blocker_not_a_false_green(
    tmp_path,
):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:blocked-disposition",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:blocked-disposition",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:blocked-disposition",
                "status": "blocked",
            },
        ),
    )

    row = ledger.current("occurrence:blocked-disposition")
    snapshot = CoverageAuditService(ledger).audit()
    summary = ledger.current_summary()

    assert row is not None
    assert row.blocked is True
    assert row.required_stages == STAGE_ORDER
    assert snapshot.blocked_objects == 1
    assert snapshot.gaps[0].first_gap_stage == "content_selection"
    assert snapshot.gaps[0].status == "blocked"
    assert snapshot.gaps[0].failure_class == "source_disposition_blocked"
    assert summary is not None
    assert summary.coverage_status == "partial"
    assert summary.blocked_object_count == 1
    assert "coverage_blocked" in summary.coverage_reasons


def test_hard_exclusion_has_explicit_nonapplicable_audit_stages(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    ledger = ObjectCoverageLedger(
        SQLiteStore(tmp_path / "private", repository_root)
    )
    ledger.reconcile_inventory(
        scope_id="scope:excluded",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:excluded",
                "provider": "filesystem",
                "object_type": "software_source",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:excluded",
                "status": "hard_excluded",
            },
        ),
    )

    snapshot = CoverageAuditService(ledger).audit()

    assert snapshot.objects[0].first_gap_stage == ""
    assert snapshot.objects[0].stages["analysis"] == "not_applicable"
    assert snapshot.stage_counts["analysis"]["not_applicable"] == 1
    assert snapshot.stage_counts["analysis"]["missing"] == 0


def test_legacy_first_gap_index_rebase_is_explicit_bounded_and_resumable(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:legacy-audit",
        inventory_revision=1,
        occurrences=tuple(
            {
                "occurrence_id": f"occurrence:legacy:{index}",
                "provider": "filesystem",
                "object_type": "document",
            }
            for index in range(3)
        ),
        dispositions=tuple(
            {
                "occurrence_id": f"occurrence:legacy:{index}",
                "status": "tracked",
            }
            for index in range(3)
        ),
    )
    with store.connection() as connection:
        connection.execute(
            "UPDATE coverage_stage_index "
            "SET first_gap_indexed_revision=0"
        )
        connection.execute("DELETE FROM coverage_stage_status_index")

    before = CoverageAuditService(ledger).audit(limit=1)
    assert before.audit_index_status == "partial"
    assert before.unindexed_objects == 3
    assert before.gaps[0].first_gap_stage == "coverage_first_gap_index"

    cursor = ""
    pages = []
    for _ in range(3):
        page = ledger.rebase_audit_index(
            after_object_id=cursor,
            limit=1,
        )
        pages.append(page)
        if not page["has_more"]:
            break
        cursor = page["next_cursor"]

    assert [page["status"] for page in pages] == [
        "partial",
        "partial",
        "current",
    ]
    after = CoverageAuditService(ledger).audit()
    assert after.audit_index_status == "current"
    assert after.unindexed_objects == 0
    assert all(
        row.first_gap_stage == "content_selection"
        for row in after.objects
    )


def test_strict_contract_detects_a_missing_coverage_index_row(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:missing-audit-row",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:missing-audit-row",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:missing-audit-row",
                "status": "tracked",
            },
        ),
    )
    with store.connection() as connection:
        connection.execute(
            "DELETE FROM coverage_stage_index "
            "WHERE object_id='occurrence:missing-audit-row'"
        )
        connection.execute(
            "DELETE FROM coverage_stage_status_index "
            "WHERE object_id='occurrence:missing-audit-row'"
        )

    status = store.coverage_audit_index_status()
    summary = ledger.summary()
    snapshot = CoverageAuditService(ledger).audit()

    assert status["status"] == "partial"
    assert status["registered_object_count"] == 1
    assert status["indexed_object_count"] == 0
    assert status["remaining_object_count"] == 1
    assert summary.coverage_status == "partial"
    assert "coverage_audit_index_stale" in summary.coverage_reasons
    assert snapshot.total_objects == 1
    assert snapshot.indexed_objects == 0
    assert snapshot.unindexed_objects == 1
    assert snapshot.objects[0].object_kind == "occurrence"
    assert (
        snapshot.objects[0].first_gap_stage
        == "coverage_first_gap_index"
    )
    assert (
        CoverageAuditService(ledger).audit(
            object_kind="occurrence"
        ).total_objects
        == 1
    )
    assert (
        CoverageAuditService(ledger).audit(
            object_kind="matter"
        ).total_objects
        == 0
    )

    rebased = ledger.rebase_audit_index(limit=1)

    assert rebased["status"] == "current"
    assert store.coverage_audit_index_status()["status"] == "current"


def test_audit_page_rejects_a_stale_coverage_row_revision(tmp_path):
    store = SQLiteStore(tmp_path / "private", tmp_path / "repo")
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:stale-audit-row",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:stale-audit-row",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:stale-audit-row",
                "status": "tracked",
            },
        ),
    )
    with store.connection() as connection:
        connection.execute(
            "UPDATE coverage_stage_index SET revision=0, "
            "first_gap_indexed_revision=0 "
            "WHERE object_id='occurrence:stale-audit-row'"
        )

    snapshot = CoverageAuditService(ledger).audit()

    assert snapshot.indexed_objects == 0
    assert snapshot.unindexed_objects == 1
    assert snapshot.objects[0].first_gap_stage == (
        "coverage_first_gap_index"
    )
    assert snapshot.gaps[0].failure_class == (
        "coverage_first_gap_index_stale"
    )


def test_store_startup_does_not_run_an_unbounded_coverage_rebuild(tmp_path):
    private_root = tmp_path / "private"
    repository_root = tmp_path / "repo"
    store = SQLiteStore(private_root, repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:startup-rebase",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:startup-rebase",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:startup-rebase",
                "status": "tracked",
            },
        ),
    )
    with store.connection() as connection:
        connection.execute(
            "DELETE FROM coverage_stage_status_index "
            "WHERE object_id='occurrence:startup-rebase'"
        )
        connection.execute(
            "DELETE FROM coverage_stage_index "
            "WHERE object_id='occurrence:startup-rebase'"
        )
        connection.execute(
            "DELETE FROM store_metadata "
            "WHERE key='coverage_stage_index:v2'"
        )

    restarted = SQLiteStore(private_root, repository_root)

    assert restarted.coverage_audit_index_status()["status"] == "partial"
    with restarted.connection() as connection:
        assert connection.execute(
            "SELECT 1 FROM coverage_stage_index "
            "WHERE object_id='occurrence:startup-rebase'"
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM store_metadata "
            "WHERE key='coverage_stage_index:v2'"
        ).fetchone() is None

    page = restarted.rebase_coverage_audit_index_page(limit=1)

    assert page["status"] == "current"
    with restarted.connection() as connection:
        assert connection.execute(
            "SELECT value FROM store_metadata "
            "WHERE key='coverage_stage_index:v2'"
        ).fetchone()[0] == "complete"


def test_store_startup_leaves_all_materialized_rebases_explicit_and_bounded(
    tmp_path,
):
    private_root = tmp_path / "private"
    repository_root = tmp_path / "repo"
    store = SQLiteStore(private_root, repository_root)
    store.append(
        "matter_context",
        "matter:context",
        1,
        {
            "freshness": "current",
            "context_revision": 1,
            "signals": (
                {"kind": "topic", "value": "travel", "freshness": "current"},
            ),
        },
    )
    store.append(
        "object_coverage",
        "occurrence:coverage-index",
        1,
        {
            "object_id": "occurrence:coverage-index",
            "provider": "filesystem",
            "object_type": "document",
            "disposition": "tracked",
            "active": True,
            "matter_ids": ("matter:coverage-index",),
            "required_stages": (),
            "stages": {},
        },
    )
    store.append(
        "inventory_snapshot",
        "scope:materialized-index",
        1,
        {
            "scope_id": "scope:materialized-index",
            "revision": 1,
            "occurrences": (
                {
                    "occurrence_id": "occurrence:materialized-index",
                    "provider": "filesystem",
                    "object_type": "document",
                    "locator": "Documents/example.txt",
                    "metadata": {},
                },
            ),
            "dispositions": (
                {
                    "occurrence_id": "occurrence:materialized-index",
                    "status": "tracked",
                },
            ),
        },
    )
    store.append(
        "matter_containment_edge",
        "edge:materialized-index",
        1,
        {
            "active": True,
            "child_matter_id": "matter:child",
            "parent_matter_id": "matter:parent",
            "role": "submatter",
            "ordinal": 1,
            "freshness": "current",
        },
    )
    store.append(
        "matter_hierarchy_audit",
        "matter:parent",
        1,
        {
            "change_ref": "hierarchy:1",
            "updated_at": "2026-07-20T00:00:00+00:00",
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
    store.append(
        "matter_work_item",
        "work-item:materialized-index",
        1,
        {
            "matter_id": "matter:parent",
            "status": "planned",
            "planned_start": "2026-07-20",
        },
    )
    specs = {
        "matter_context_signal_index:v1": "matter_context_signal_index",
        "coverage_matter_index:v1": "coverage_matter_index",
        "inventory_occurrence_current:v1": "inventory_occurrence_current",
        "matter_hierarchy_index:v1": "matter_hierarchy_index",
        "matter_hierarchy_stage_index:v1": "matter_hierarchy_stage_index",
        "matter_work_item_index:v1": "matter_work_item_index",
    }
    with store.connection() as connection:
        for index_id, table_name in specs.items():
            connection.execute(f"DELETE FROM {table_name}")
            connection.execute(
                "DELETE FROM store_metadata WHERE key=?",
                (index_id,),
            )

    restarted = SQLiteStore(private_root, repository_root)

    with restarted.connection() as connection:
        for index_id, table_name in specs.items():
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0] == 0
            assert restarted.materialized_index_status(index_id)[
                "status"
            ] == "partial"

    for index_id in specs:
        current_page = restarted.rebase_materialized_index_page(
            index_id=index_id,
            phase="current",
            limit=1,
        )
        assert current_page["next_phase"] == "stale"
        terminal_page = restarted.rebase_materialized_index_page(
            index_id=index_id,
            phase=current_page["next_phase"],
            after_object_id=current_page["next_cursor"],
            limit=1,
        )
        assert terminal_page["status"] == "current"
        assert restarted.materialized_index_status(index_id)[
            "status"
        ] == "current"


def test_persisted_summary_cannot_hide_a_new_index_gap(tmp_path):
    service = MatterService(
        repository_root=tmp_path / "repo",
        private_root=tmp_path / "private",
    )
    occurrence = InventoryOccurrence(
        occurrence_id="filesystem:summary-gap",
        provider="filesystem",
        object_type="document",
        locator="Documents/summary-gap.txt",
        metadata={
            "display_name": "summary-gap.txt",
            "source_group_chain": ("filesystem-group:documents",),
            "source_group_labels": ("Documents",),
            "recommended_disposition": "tracked",
        },
    )
    service.reconcile_inventory(
        scope=CandidateScope(
            scope_id="scope:summary-gap",
            revision=1,
            provider="filesystem",
            root_locator="Documents",
            object_types=("document",),
        ),
        policy=TrackingPolicy(
            policy_id="tracking-policy:summary-gap",
            revision=1,
        ),
        occurrences=(occurrence,),
    )
    assert service.coverage_ledger is not None
    assert service.store is not None
    for stage_id in STAGE_ORDER[2:]:
        service.coverage_ledger.mark_stage(
            object_id=occurrence.occurrence_id,
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"sha256:{stage_id}",
            refresh_summary=False,
        )
    for surface_id in ("raw_cleanup", "staging_cleanup"):
        service.store.record_coverage_surface_status(
            surface_id=surface_id,
            status="current",
            input_fingerprint=f"sha256:{surface_id}",
        )
    complete = service.coverage_ledger.refresh_summary()
    assert complete.coverage_status == "complete"

    with service.store.connection() as connection:
        connection.execute(
            "DELETE FROM source_group_member_index "
            "WHERE object_id=?",
            (occurrence.occurrence_id,),
        )

    current = service.coverage_ledger.current_summary()

    assert current is not None
    assert current.coverage_status == "partial"
    assert current.source_group_status == "partial"
    assert "source_group_reconciliation_pending" in (
        current.coverage_reasons
    )


def test_strict_coverage_contract_rejects_missing_source_group(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    store.append(
        "inventory_snapshot",
        "scope:strict",
        1,
        {
            "scope_id": "scope:strict",
            "revision": 1,
            "occurrences": (
                {
                    "occurrence_id": "occurrence:strict",
                    "provider": "filesystem",
                    "object_type": "document",
                },
            ),
            "dispositions": (
                {
                    "occurrence_id": "occurrence:strict",
                    "status": "tracked",
                },
            ),
        },
    )
    ledger.reconcile_inventory(
        scope_id="scope:strict",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:strict",
                "provider": "filesystem",
                "object_type": "document",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:strict",
                "status": "tracked",
            },
        ),
    )
    for stage_id in STAGE_ORDER[2:]:
        ledger.mark_stage(
            object_id="occurrence:strict",
            stage_id=stage_id,
            status="current",
            input_fingerprint=f"sha256:{stage_id}",
            refresh_summary=False,
        )

    summary = ledger.summary()

    assert summary.terminal_object_count == 1
    assert summary.coverage_status == "partial"
    assert summary.source_group_status == "partial"
    assert "source_group_reconciliation_pending" in (
        summary.coverage_reasons
    )


def test_surface_contract_rejects_ui_ready_root_with_missing_graph_world_and_cleanup(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    _ready_root_coverage(store, ledger, "matter:surface-gap")

    snapshot = CoverageAuditService(ledger).audit(object_kind="matter")

    assert snapshot.objects[0].ui_ready is True
    assert snapshot.coverage_contract["status"] == "partial"
    assert snapshot.coverage_contract["surface_status"] == "partial"
    assert snapshot.gap_surfaces == 5
    assert {
        (gap.first_gap_stage, gap.status)
        for gap in snapshot.surface_gaps
    } >= {
        ("raw_cleanup", "missing"),
        ("staging_cleanup", "missing"),
        ("situation_graph", "pending"),
        ("node_quick_view", "pending"),
        ("world_model", "pending"),
    }


def test_terminal_hard_exclusions_cannot_produce_false_green(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    ledger.reconcile_inventory(
        scope_id="scope:hard-only",
        inventory_revision=1,
        occurrences=(
            {
                "occurrence_id": "occurrence:hard-only",
                "provider": "filesystem",
                "object_type": "cache",
            },
        ),
        dispositions=(
            {
                "occurrence_id": "occurrence:hard-only",
                "status": "hard_excluded",
            },
        ),
    )
    for surface_id in ("raw_cleanup", "staging_cleanup"):
        store.record_coverage_surface_status(
            surface_id=surface_id,
            status="current",
            input_fingerprint=f"sha256:{surface_id}",
        )

    contract = store.coverage_contract_status()

    assert contract["status"] == "partial"
    assert contract["eligible_object_count"] == 0
    assert "terminal_hard_exclusion_only" in contract["reasons"]


def test_surface_audit_is_current_and_filterable_from_materialized_owner_rows(
    tmp_path,
):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    matter_id = "matter:surface-current"
    _ready_root_coverage(store, ledger, matter_id)
    graph_fingerprint = "sha256:graph-current"
    store.append(
        "situation_graph_projection",
        matter_id,
        1,
        {
            "root_matter_id": matter_id,
            "input_fingerprint": graph_fingerprint,
            "coverage": "complete",
        },
    )
    store.append(
        "world_model_advisory",
        matter_id,
        1,
        {
            "matter_id": matter_id,
            "graph_fingerprint": graph_fingerprint,
            "expires_at": "2099-01-01T00:00:00+00:00",
            "coverage": "complete",
        },
    )
    for surface_id in ("raw_cleanup", "staging_cleanup"):
        store.record_coverage_surface_status(
            surface_id=surface_id,
            status="current",
            input_fingerprint=f"sha256:{surface_id}",
        )

    snapshot = CoverageAuditService(ledger).audit(
        surface_id="world_model",
        surface_status="current",
        owner_id="C11_guard_prediction",
        freshness="current",
        ui_ready=True,
    )

    assert snapshot.coverage_contract["status"] == "complete"
    assert snapshot.total_surfaces == 1
    assert snapshot.current_surfaces == 1
    assert snapshot.gap_surfaces == 0
    assert len(snapshot.surfaces) == 1
    assert snapshot.surfaces[0].surface_id == "world_model"
    assert snapshot.surfaces[0].subject_id == matter_id


def test_coverage_first_page_is_bounded_at_180k_registered_objects(tmp_path):
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    store = SQLiteStore(tmp_path / "private", repository_root)
    ledger = ObjectCoverageLedger(store)
    total = 180_000
    batch_size = 10_000
    with store.connection() as connection:
        for start in range(0, total, batch_size):
            rows = tuple(
                (
                    f"occurrence:scale:{index:06d}",
                    "filesystem",
                    "document",
                    "hard_excluded",
                    "",
                    1,
                    0,
                    0,
                    1,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    1,
                    1,
                    "2099-01-01T00:00:00+00:00",
                )
                for index in range(start, min(total, start + batch_size))
            )
            connection.executemany(
                "INSERT INTO coverage_stage_index"
                "(object_id, provider, object_type, disposition, next_stage, "
                "terminal, ui_ready, blocked, active, first_gap_stage, "
                "first_gap_status, first_gap_owner_id, first_gap_failure_class, "
                "first_gap_input_fingerprint, first_gap_updated_at, "
                "first_gap_indexed_revision, revision, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
    started = perf_counter()
    page = store.coverage_audit_page(
        offset=0,
        limit=50,
        object_kind="occurrence",
        stage_order=STAGE_ORDER,
    )
    elapsed = perf_counter() - started

    assert page["total_objects"] == total
    assert len(page["rows"]) == 50
    assert elapsed < 5.0
from time import perf_counter
