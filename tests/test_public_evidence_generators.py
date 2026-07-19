import json
from pathlib import Path
import sys

from flowguard_design.run_test_mesh import (
    _execution_test_command,
    _parent_claim_boundary,
    _parent_receipt_status,
    _portable_output_tail,
    _public_test_command,
)
from flowguard_models.delivery_flow import _portable_openspec_projection
from flowguard_models.delivery_flow import (
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

    assert (
        _parent_receipt_status(
            report_ok=True,
            deferred_suite_ids=[],
        )
        == "release_green"
    )
    release_boundary = _parent_claim_boundary([])
    assert "TM01-TM23" in release_boundary
    assert "does not claim complete private semantic coverage" in release_boundary

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
                "artifact_type": "matters.private-first-run-aggregate.v1",
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
                "checks": {"installed_runtime": True},
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
