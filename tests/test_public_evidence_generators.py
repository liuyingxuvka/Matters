import json
from pathlib import Path
import sys

from flowguard_design.run_test_mesh import (
    _deferred_suite_ids,
    _execution_test_command,
    _parent_claim_boundary,
    _parent_receipt_status,
    _portable_output_tail,
    _public_test_command,
)
from flowguard_design.run_alignment import (
    MAX_PUBLIC_ALIGNMENT_BYTES,
    _compact_model_row,
)
from flowguard_design.run_g4_review import (
    _compact_contract_exhaustion,
    _compact_test_mesh,
)
from flowguard_models.delivery_flow import _portable_openspec_projection
from flowguard_models.delivery_flow import (
    REQUIRED_UI_CHECKS,
    _installed_ui_gate,
    _private_first_run_gate,
)
from flowguard_design.ui_flow_structure import current_revision


def test_test_mesh_executes_real_interpreter_but_serializes_canonical_command():
    path = Path("tests/test_tm01_authorization_coverage.py")
    execution = _execution_test_command(path)
    public = _public_test_command(path)

    assert execution[0] == sys.executable
    assert execution[1:] == (
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        path.as_posix(),
    )
    assert public == (
        "python -m pytest -q -o addopts= "
        "tests/test_tm01_authorization_coverage.py"
    )
    assert sys.executable not in public
    assert str(Path.home()) not in public


def test_test_mesh_output_tail_replaces_machine_local_paths():
    local_output = (
        "runner="
        + sys.executable
        + "\nrepo="
        + str(Path.cwd().resolve())
        + "\nhome="
        + str(Path.home())
    )
    portable = _portable_output_tail(local_output)

    assert sys.executable not in portable
    assert str(Path.cwd().resolve()) not in portable
    assert str(Path.home()) not in portable
    assert "runner=python" in portable
    assert "repo=repo://" in portable
    assert "home=home://" in portable


def test_test_mesh_parent_receipt_distinguishes_routine_and_release():
    deferred = ["TM19_clean_install_release"]
    assert (
        _parent_receipt_status(
            report_ok=True,
            deferred_suite_ids=deferred,
        )
        == "routine_green"
    )
    assert "TM19 remains release-only" in _parent_claim_boundary(deferred)
    assert "TM20-TM27" in _parent_claim_boundary(deferred)
    assert _deferred_suite_ids(("TM01_authorization_coverage",)) == deferred

    assert (
        _parent_receipt_status(
            report_ok=True,
            deferred_suite_ids=[],
        )
        == "release_green"
    )
    release_boundary = _parent_claim_boundary([])
    assert "TM01-TM27" in release_boundary
    assert "does not claim complete private semantic coverage" in release_boundary
    assert _deferred_suite_ids(("TM19_clean_install_release",)) == []

    assert (
        _parent_receipt_status(
            report_ok=False,
            deferred_suite_ids=[],
        )
        == "blocked"
    )


def test_openspec_projection_drops_provider_roots_and_raw_output():
    machine_root = "C:" + "\\\\" + "Users" + "\\\\" + "local-user" + "\\\\" + "repo"
    payload = {
        "summary": {
            "totals": {
                "passed": 1,
                "failed": 0,
                "warnings": 2,
                "errors": 0,
            }
        },
        "root": {"path": machine_root},
        "results": [{"path": machine_root, "valid": True}],
        "stdout": machine_root,
    }
    projected = _portable_openspec_projection(payload, 0)
    serialized = json.dumps(projected, sort_keys=True)

    assert projected["ok"]
    assert projected["provider"] == "openspec"
    assert projected["change_id"] == "build-matters-model-driven-core"
    assert projected["validation_mode"] == "strict"
    assert projected["totals"] == {
        "passed": 1,
        "failed": 0,
        "warnings": 2,
        "errors": 0,
    }
    assert machine_root not in serialized
    assert "root" not in projected
    assert "result" not in projected
    assert "stdout" not in projected
    assert "stderr" not in projected


def test_openspec_invalid_json_is_visible_without_echoing_raw_output():
    projected = _portable_openspec_projection(None, 1)
    assert not projected["ok"]
    assert projected["exit_code"] == 1
    assert projected["error_code"] == "invalid_json_output"
    assert projected["totals"] == {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "errors": 0,
    }


def test_private_first_run_gate_consumes_only_safe_aggregate(
    tmp_path: Path,
    monkeypatch,
):
    aggregate = tmp_path / "private-aggregate.json"
    aggregate.write_text(
        json.dumps(
            {
                "artifact_type": "matters.private-first-run-aggregate.v2",
                "ok": True,
                "status": "current_with_open_work",
                "coverage_complete": False,
                "private_evidence_handle": "private-evidence:bounded-v1",
                "inventory": {
                    "reconciled": True,
                    "catalog_reconciled": True,
                },
                "partition_inventory": {
                    "status": "complete",
                    "failed_partition_count": 0,
                },
                    "semantic_depth": {"all_accounted": True},
                    "localization": {"current": True},
                    "storage_migrations": {
                        "status": "current",
                        "migration_order": [
                            "evidence_pointer_rebase",
                            "coverage_history_archive",
                        ],
                        "verified_restorable_copy": True,
                        "all_other_writers_stopped": True,
                        "evidence_pointer_rebase_terminal": True,
                        "coverage_history_archive_terminal": True,
                        "archive_verified_before_original_retirement": True,
                        "integrity_check_current": True,
                        "count_check_current": True,
                        "sampled_history_equivalence_current": True,
                        "startup_migration_attempt_count": 0,
                        "vacuum_attempt_count": 0,
                        "evidence_pointer_rebase_terminal_receipt_id": (
                            "storage-migration:evidence-pointer:synthetic"
                        ),
                        "coverage_history_archive_terminal_receipt_id": (
                            "storage-migration:coverage-history:synthetic"
                        ),
                    },
                    "codex_daily_maintenance": {
                    "status": "current",
                    "current": True,
                    "schedule_identity": "codex-automation:synthetic-daily",
                    "execution_profile_identity": "execution-profile:synthetic",
                    "manual_rehearsal_receipt_id": "maintenance-rehearsal:synthetic",
                    "manual_rehearsal_fingerprint": "sha256:synthetic-rehearsal",
                    "install_currentness_receipt_id": "maintenance-install:synthetic",
                    "install_currentness_fingerprint": "sha256:synthetic-install",
                    "shared_service_entrypoint_fingerprint": "sha256:synthetic-service",
                    "run_receipt_ids": ["maintenance-run:synthetic"],
                    "installed": True,
                    "manual_rehearsal_current": True,
                    "shared_service_path": True,
                    "model_agnostic": True,
                    "app_api_key_required": False,
                    "mutation_attempt_counts": {
                        "source": 0,
                        "mailbox": 0,
                        "outbound": 0,
                        "grant": 0,
                        "code": 0,
                        "model": 0,
                        "install": 0,
                        "git": 0,
                        "tag": 0,
                        "release": 0,
                    },
                    "unattended_final_verification": False,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MATTERS_PRIVATE_AGGREGATE", str(aggregate))

    gate = _private_first_run_gate()

    assert gate["ok"]
    assert gate["status"] == "passed"
    assert gate["coverage_complete"] is False
    assert gate["private_evidence_handle"] == "private-evidence:bounded-v1"
    assert gate["storage_migrations_current"] is True
    assert gate["storage_migration_order_current"] is True
    assert gate["storage_restorable_copy_verified"] is True
    assert gate["storage_startup_migration_attempt_count"] == 0
    assert gate["storage_vacuum_attempt_count"] == 0
    assert str(tmp_path) not in json.dumps(gate)


def test_installed_ui_gate_requires_exact_current_revision(tmp_path: Path):
    revision = current_revision(tmp_path)
    receipt = (
        tmp_path
        / ".flowguard"
        / "evidence"
        / "ui"
        / "G10_live_ui.json"
    )
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "artifact_type": "matters.live-ui-evidence.v1",
                "status": "passed",
                "evidence_id": "evidence:ui:synthetic",
                "ui_revision": revision,
                "checks": {
                    check_name: True for check_name in REQUIRED_UI_CHECKS
                },
                "browser_errors": [],
                "missing_checks": [],
                "claim_boundary": "synthetic installed UI only",
            }
        ),
        encoding="utf-8",
    )

    assert _installed_ui_gate(tmp_path)["ok"]

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["ui_revision"] = "sha256:stale"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    stale = _installed_ui_gate(tmp_path)
    assert not stale["ok"]
    assert stale["evidence_current"] is False


def test_ui_revision_is_stable_across_text_line_endings(tmp_path: Path):
    authority = tmp_path / "ui" / "index.html"
    authority.parent.mkdir(parents=True)
    authority.write_bytes(b"<main>\nMatter\n</main>\n")
    lf_revision = current_revision(tmp_path)

    authority.write_bytes(b"<main>\r\nMatter\r\n</main>\r\n")
    crlf_revision = current_revision(tmp_path)

    assert crlf_revision == lf_revision


def test_live_ui_verifier_uses_the_exact_current_inventory_and_guards_mutation():
    contract = json.loads(
        Path("flowguard_design/ui_runtime_required_checks.json").read_text(
            encoding="utf-8"
        )
    )
    verifier = Path("scripts/verify_live_ui.js").read_text(encoding="utf-8")

    assert len(contract["required_checks"]) == 72
    assert "const checks = checkMap();" in verifier
    assert "REQUIRED_CHECKS.filter" in verifier
    assert "required_check_count: REQUIRED_CHECKS.length" in verifier
    assert "evidence_reveal_and_return" not in verifier
    assert "optional_cover_correction" not in verifier
    assert "ordinary_correction_absent" in contract["required_checks"]
    assert "data-correction-form" in verifier
    assert "data-open-correction" in verifier
    assert "data-save-correction" in verifier
    assert "correction-scope" not in verifier
    assert ".matters-synthetic-fixture.json" not in verifier
    assert "child_node_count: graph.nodes.length" in verifier
    assert "child_row_count: childRows" not in verifier


class _PublicEvidencePayload:
    def __init__(self, payload, *, model_id="synthetic-model"):
        self.payload = payload
        self.model_id = model_id

    def to_dict(self):
        return self.payload


def test_g4_public_receipts_fingerprint_instead_of_copying_derived_rows():
    repeated_ids = [f"case:{index}" for index in range(10_000)]
    contract = _compact_contract_exhaustion(
        _PublicEvidencePayload(
            {
                "plan_id": "plan",
                "model_id": "model",
                "model_level": "parent",
                "source_model_ids": [],
                "generation_policy": "cartesian",
                "required_route_ids": [],
                "cartesian_case_limit": 20_000,
                "axes": [],
                "interaction_groups": [],
                "oracles": [],
                "coverage_universe": {},
                "inventory_revision": "inventory",
                "inventory_current": True,
            }
        ),
        _PublicEvidencePayload(
            {
                "ok": True,
                "decision": "accept",
                "confidence": "high",
                "summary": "synthetic",
                "inventory_revision": "inventory",
                "findings": [],
                "generated_cases": repeated_ids,
                "combination_cases": repeated_ids,
                "contract_fault_profiles": [],
                "composite_handoff_acceptances": [],
                "coverage_shards": repeated_ids,
                "coverage_receipts": repeated_ids,
                "required_route_case_ids": repeated_ids,
                "missing_oracle_case_ids": [],
                "model_gap_dimension_ids": [],
            }
        ),
    )
    suite = {
        "suite_id": "TM01",
        "layer": "unit",
        "command": "python -m pytest -q tests/test_synthetic.py",
        "diagnostic_boundary": "targeted",
        "planned_count": 0,
        "executed_count": 0,
        "failed_count": 0,
        "not_run_count": 0,
        "not_run_reason": "",
        "result_status": "not_run",
        "terminal_status": "not_run",
        "evidence_tier": "candidate_only",
        "evidence_current": True,
        "release_required": False,
        "covered_obligation_ids": repeated_ids,
        "owned_coverage_shard_ids": [],
        "owned_inventory_item_ids": [],
        "owned_leaf_cell_ids": repeated_ids,
        "owns_side_effects": [],
        "owns_state": [],
    }
    mesh = _compact_test_mesh(
        _PublicEvidencePayload(
            {
                "parent_suite_id": "parent",
                "decision_scope": "routine",
                "inventory_revision": "inventory",
                "release_deferred_allowed": True,
                "require_complete_inventory": True,
                "require_final_receipts": False,
                "require_proof_artifacts": False,
                "required_evidence_tier": "candidate_only",
                "partition_items": [],
                "target_split_derivation": {},
                "child_suites": [suite],
                "required_coverage_shard_ids": [],
                "required_inventory_item_ids": [],
                "required_leaf_cell_ids": repeated_ids,
            }
        ),
        _PublicEvidencePayload(
            {
                "ok": False,
                "decision": "blocked",
                "decision_scope": "routine",
                "inventory_revision": "inventory",
                "summary": "synthetic",
                "release_obligations": [],
                "findings": [
                    {"code": "not_run", "payload": repeated_ids}
                ],
                "covered_inventory_item_ids": [],
                "missing_inventory_item_ids": [],
                "scoped_inventory_item_ids": [],
            }
        ),
    )

    assert contract["report"]["required_route_case_ids"]["count"] == 10_000
    assert mesh["plan"]["required_leaf_cell_ids"]["count"] == 10_000
    serialized = json.dumps(
        {"contract": contract, "mesh": mesh},
        separators=(",", ":"),
        sort_keys=True,
    )
    assert "case:9999" not in serialized
    assert len(serialized) < 100_000


def test_alignment_receipt_deduplicates_proof_payload_without_losing_failures():
    repeated_ids = [f"obligation:{index}" for index in range(10_000)]
    proof_artifact = {
        "artifact_id": "artifact:synthetic-test-run",
        "producer_route": "test_mesh",
        "command": "python -m pytest -q tests/test_synthetic.py",
        "result_path": ".flowguard/evidence/tests/TM-synthetic.json",
        "result_status": "passed",
        "exit_code": 0,
        "started_at": "2026-07-20T00:00:00+00:00",
        "finished_at": "2026-07-20T00:00:01+00:00",
        "artifact_fingerprints": {
            f"artifact:{index}": f"sha256:{index:064x}"
            for index in range(1_000)
        },
        "covered_obligation_ids": repeated_ids,
        "assertion_scope": "external_contract",
        "current": True,
        "route_evidence_current": True,
        "progress_only": False,
        "stale_reasons": [],
        "route_gap_codes": [],
        "metadata": {},
    }
    findings = [
        {
            "code": "test_proof_artifact_missing_obligation",
            "severity": "error",
            "message": "synthetic missing obligation",
            "obligation_id": f"required:{index}",
            "code_contract_id": "CC-synthetic",
            "evidence_id": f"TE-synthetic-{index}",
            "metadata": {
                "proof_artifact": proof_artifact,
                "test_name": f"test:{index}",
                "covered_obligations": [f"required:{index}"],
            },
        }
        for index in range(100)
    ]
    plan = _PublicEvidencePayload(
        {
            "model_id": "synthetic-model",
            "boundary_observations": [],
            "obligations": [
                {"obligation_id": "required:0"},
            ],
            "code_contracts": [
                {"code_contract_id": "CC-synthetic"},
            ],
            "test_evidence": [
                {"evidence_id": "TE-synthetic-0"},
            ],
        }
    )
    report = _PublicEvidencePayload(
        {
            "model_id": "synthetic-model",
            "ok": False,
            "decision": "model_test_alignment_blocked",
            "summary": "blocked",
            "findings": findings,
            "binding_rows": [],
        }
    )

    compact = _compact_model_row(plan, report)
    serialized = json.dumps(compact, separators=(",", ":"), sort_keys=True)

    assert compact["report"]["finding_count"] == 100
    assert len(compact["report"]["proof_artifacts"]) == 1
    assert {
        finding["obligation_id"]
        for finding in compact["report"]["findings"]
    } == {f"required:{index}" for index in range(100)}
    proof = compact["report"]["proof_artifacts"][0]
    assert proof["artifact_id"] == "artifact:synthetic-test-run"
    assert proof["result_status"] == "passed"
    assert proof["covered_obligation_ids"]["count"] == 10_000
    assert proof["artifact_fingerprints"]["count"] == 1_000
    assert all(
        "proof_artifact_ref" in finding["metadata"]
        and "proof_artifact" not in finding["metadata"]
        for finding in compact["report"]["findings"]
    )
    assert len(serialized) < 100_000
    assert len(serialized.encode("utf-8")) < MAX_PUBLIC_ALIGNMENT_BYTES


def test_current_alignment_receipt_is_bounded_and_semantically_accounted():
    path = Path(".flowguard/evidence/alignment/model_code_test.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.stat().st_size < MAX_PUBLIC_ALIGNMENT_BYTES
    assert payload["artifact_type"] == (
        "matters.model-code-test-alignment-receipt.v2"
    )
    assert payload["models"]
    for model in payload["models"]:
        report = model["report"]
        assert model["plan_fingerprint"].startswith("sha256:")
        assert report["findings_fingerprint"].startswith("sha256:")
        assert report["finding_count"] == len(report["findings"])
        proof_refs = {
            proof["artifact_ref"] for proof in report["proof_artifacts"]
        }
        referenced = {
            finding["metadata"]["proof_artifact_ref"]
            for finding in report["findings"]
            if "proof_artifact_ref" in finding["metadata"]
        }
        assert referenced <= proof_refs
