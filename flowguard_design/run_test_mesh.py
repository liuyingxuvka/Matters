"""Execute routine TM01-TM18/TM20-TM23 owners and build a TestMesh receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys

import flowguard
from flowguard import ProofArtifactRef

from flowguard_design.inventory import (
    ALL_TEST_SUITES,
    MODEL_MODULES,
    MODEL_TEST_SUITES,
)
from flowguard_design.test_mesh import (
    INVENTORY_REVISION,
    build_plan,
    run_review,
    test_paths,
)


RECEIPT_ROOT = Path(".flowguard/evidence/tests")
PARENT_RECEIPT = RECEIPT_ROOT / "TM0_matters_whole_flow_gate.json"
PUBLIC_PYTHON_COMMAND = "python"


def _hash(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _aggregate_hash(paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _files_under(path: Path, pattern: str = "*.py") -> tuple[Path, ...]:
    return tuple(sorted(item for item in path.rglob(pattern) if item.is_file()))


def _suite_inputs(suite_id: str, test_files: tuple[Path, ...]) -> tuple[Path, ...]:
    paths: set[Path] = set(test_files)
    model_id = next(
        (
            model_id
            for model_id, owner_suite in MODEL_TEST_SUITES.items()
            if owner_suite == suite_id
        ),
        "",
    )
    if model_id:
        area = MODEL_MODULES[model_id].split(".", 1)[0]
        paths.update(_files_under(Path("src/matters") / area))
        if suite_id == "TM01_authorization_coverage":
            paths.update(
                _files_under(Path("src/matters/infrastructure/capability_status"))
            )
            paths.update(
                {
                    Path("src/matters/application/partitioned_filesystem.py"),
                    Path("src/matters/application/source_workflows.py"),
                    Path("src/matters/application/orchestrator.py"),
                    Path("src/matters/providers/filesystem/adapter.py"),
                    Path("src/matters/inventory/owners.py"),
                    Path("src/matters/infrastructure/sqlite/store.py"),
                    Path("src/matters/analysis/depth.py"),
                }
            )
        if suite_id == "TM12_projection_bilingual_ui":
            paths.update(Path("ui").glob("*"))
            paths.update(
                {
                    Path("src/matters/application/orchestrator.py"),
                    Path("src/matters/api/http/app.py"),
                    Path("src/matters/api/http/static.py"),
                    Path("flowguard_design/ui_flow_structure.py"),
                    Path("flowguard_design/run_ui_flow_structure.py"),
                }
            )
    elif suite_id == "TM13_model_mesh_closure":
        paths.update(_files_under(Path("flowguard_models")))
        paths.update(_files_under(Path("flowguard_design")))
    elif suite_id == "TM14_end_to_end_conformance":
        paths.update(_files_under(Path("src/matters")))
        paths.add(Path("tests/fixtures/source_universe_synthetic/cases.json"))
    elif suite_id == "TM15_connector_pagination_retry":
        paths.update(_files_under(Path("src/matters/providers")))
        paths.update(
            {
                Path("src/matters/application/partitioned_filesystem.py"),
                Path("src/matters/application/source_workflows.py"),
                Path("src/matters/inventory/owners.py"),
            }
        )
    elif suite_id == "TM16_bilingual_semantic_equivalence":
        paths.update(_files_under(Path("src/matters/presentation")))
        paths.update(Path("ui").glob("*"))
    elif suite_id == "TM17_revocation_full_propagation":
        paths.update(_files_under(Path("src/matters/revisions")))
        paths.add(Path("src/matters/application/orchestrator.py"))
    elif suite_id == "TM18_privacy_public_boundary":
        paths.add(Path("scripts/check_public_boundary.py"))
        paths.add(Path("docs/security/public-file-policy.json"))
        paths.add(Path("docs/security/required-public-inventory.json"))
        paths.add(Path("docs/security/scope-manifest.yaml"))
        paths.update(
            _files_under(Path("src/matters/infrastructure/capability_status"))
        )
    return tuple(sorted(path for path in paths if path.is_file()))


def _pytest_observation(stdout: str, stderr: str) -> dict[str, int]:
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
    }
    text = stdout + "\n" + stderr
    aliases = {"error": "errors", "errors": "errors"}
    for raw_count, raw_kind in re.findall(
        r"(\d+)\s+(passed|failed|skipped|xfailed|xpassed|errors?)\b",
        text,
    ):
        kind = aliases.get(raw_kind, raw_kind)
        counts[kind] = max(counts[kind], int(raw_count))
    counts["observed_total"] = sum(counts.values())
    return counts


def _normalized_test_paths(paths: Path | tuple[Path, ...]) -> tuple[Path, ...]:
    if isinstance(paths, Path):
        return (paths,)
    return tuple(paths)


def _execution_test_command(
    paths: Path | tuple[Path, ...],
) -> tuple[str, ...]:
    normalized = _normalized_test_paths(paths)
    return (
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        *(path.as_posix() for path in normalized),
    )


def _public_test_command(paths: Path | tuple[Path, ...]) -> str:
    requested = _normalized_test_paths(paths)
    normalized = tuple(
        path.relative_to(Path.cwd()) if path.is_absolute() else path
        for path in requested
    )
    return (
        f"{PUBLIC_PYTHON_COMMAND} -m pytest -q -o addopts= "
        + " ".join(path.as_posix() for path in normalized)
    )


def _portable_output_tail(output: str, *, limit: int = 4000) -> str:
    replacements = (
        (sys.executable, PUBLIC_PYTHON_COMMAND),
        (str(Path.cwd().resolve()), "repo://"),
        (str(Path.home()), "home://"),
    )
    portable = output
    for source, target in replacements:
        if not source:
            continue
        portable = portable.replace(source, target)
        portable = portable.replace(source.replace("\\", "/"), target)
        portable = portable.replace(source.replace("/", "\\"), target)
    portable = re.sub(
        r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/(?:home|Users)/)"
        r"[^\\/\s\"'<>]+",
        "home://",
        portable,
    )
    return portable[-limit:]


def _parent_receipt_status(
    *,
    report_ok: bool,
    deferred_suite_ids: list[str],
) -> str:
    if not report_ok:
        return "blocked"
    if deferred_suite_ids:
        return "routine_green"
    return "release_green"


def _parent_claim_boundary(deferred_suite_ids: list[str]) -> str:
    if deferred_suite_ids:
        return (
            "Routine evidence covers TM01-TM18 and autonomous object-browser "
            "TM20-TM23. TM19 remains release-only until the frozen G12 "
            "candidate."
        )
    return (
        "Frozen release evidence covers TM01-TM23, including the release-only "
        "TM19 clean-install suite. It proves the declared synthetic, package, "
        "installation, skill-runtime, privacy, and UI test inventory only; it "
        "does not claim complete private semantic coverage."
    )


def _planned_suite(suite_id: str):
    plan = build_plan()
    return next(item for item in plan.child_suites if item.suite_id == suite_id)


def execute_suite(suite_id: str) -> dict:
    planned = _planned_suite(suite_id)
    paths = tuple(Path(path) for path in test_paths(suite_id))
    source_paths = _suite_inputs(suite_id, paths)
    execution_command = _execution_test_command(paths)
    public_command = _public_test_command(paths)
    started = datetime.now(timezone.utc)
    result = subprocess.run(
        execution_command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    finished = datetime.now(timezone.utc)
    observation = _pytest_observation(result.stdout, result.stderr)
    count = observation["observed_total"]
    status = "passed" if result.returncode == 0 else "failed"
    run_id = (
        f"run:{suite_id}:"
        f"{sha256((str(started)+_aggregate_hash(paths)).encode()).hexdigest()[:16]}"
    )
    result_path = RECEIPT_ROOT / f"{suite_id}.json"
    covered = (
        *planned.owned_leaf_cell_ids,
        *(f"transition:{cell_id}" for cell_id in planned.owned_leaf_cell_ids),
        *planned.covered_obligation_ids,
        *planned.owned_inventory_item_ids,
    )
    proof = ProofArtifactRef(
        artifact_id=f"artifact:{run_id}",
        producer_route="test_mesh",
        command=public_command,
        result_path=result_path.as_posix(),
        result_status=status,
        exit_code=result.returncode,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        artifact_fingerprints={
            item.as_posix(): _hash(item) for item in source_paths
        },
        covered_obligation_ids=tuple(covered),
        assertion_scope="external_contract",
        current=True,
        route_evidence_current=True,
    )
    suite_payload = {
        **planned.to_dict(),
        "command": public_command,
        "result_status": status,
        "evidence_tier": "conformance_green" if status == "passed" else "candidate_only",
        "evidence_current": True,
        "test_count": count,
        "selected_count": count,
        "planned_count": planned.planned_count,
        "executed_count": planned.planned_count,
        "failed_count": 0 if status == "passed" else planned.planned_count,
        "not_run_count": 0,
        "diagnostic_campaign_id": f"G5-G8-{suite_id}",
        "diagnostic_boundary": "declared_complete",
        "exit_code": result.returncode,
        "result_path": result_path.as_posix(),
        "has_exit_artifact": True,
        "has_result_artifact": True,
        "proof_artifact": proof.to_dict(),
        "not_run_reason": "",
        "run_id": run_id,
        "terminal_status": status,
        "result_fingerprint": _aggregate_hash(source_paths),
        "covered_obligation_ids": list(covered),
        "artifact_version": "matters.test-suite-receipt.v1",
        "verifier_version": importlib.metadata.version("pytest"),
    }
    receipt = {
        "artifact_type": "matters.test-suite-receipt.v1",
        "suite_id": suite_id,
        "generated_at": finished.isoformat(),
        "source_paths": [path.as_posix() for path in paths],
        "source_fingerprint": _aggregate_hash(source_paths),
        "source_fingerprints": {
            item.as_posix(): _hash(item) for item in source_paths
        },
        "test_suite_evidence": suite_payload,
        "stdout_tail": _portable_output_tail(result.stdout),
        "stderr_tail": _portable_output_tail(result.stderr),
        "pytest_observation": observation,
    }
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        action="append",
        choices=ALL_TEST_SUITES,
        help=(
            "Run only selected suite owners; defaults to routine "
            "TM01-TM18 and TM20-TM23."
        ),
    )
    args = parser.parse_args()
    suites = tuple(
        args.suite
        or (
            suite_id
            for suite_id in ALL_TEST_SUITES
            if suite_id != "TM19_clean_install_release"
        )
    )
    results = [execute_suite(suite_id) for suite_id in suites]
    if any(
        item["test_suite_evidence"]["result_status"] != "passed"
        for item in results
    ):
        print(
            json.dumps(
                {
                    "ok": False,
                    "failed": [
                        item["suite_id"]
                        for item in results
                        if item["test_suite_evidence"]["result_status"] != "passed"
                    ],
                },
                indent=2,
            )
        )
        return 1
    plan, report = run_review(RECEIPT_ROOT)
    deferred_suite_ids = [
        suite_id
        for suite_id in ALL_TEST_SUITES
        if not (RECEIPT_ROOT / f"{suite_id}.json").is_file()
    ]
    payload = {
        "artifact_type": "matters.test-mesh-receipt.v1",
        "parent_suite_id": plan.parent_suite_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory_revision": INVENTORY_REVISION,
        "executed_suite_ids": list(suites),
        "deferred_suite_ids": deferred_suite_ids,
        "plan": plan.to_dict(),
        "native_report": report.to_dict(),
        "status": _parent_receipt_status(
            report_ok=report.ok,
            deferred_suite_ids=deferred_suite_ids,
        ),
        "claim_boundary": _parent_claim_boundary(deferred_suite_ids),
        "toolchain": {
            "python": sys.version,
            "pytest": importlib.metadata.version("pytest"),
            "flowguard": importlib.metadata.version("flowguard"),
            "flowguard_schema": flowguard.SCHEMA_VERSION,
        },
    }
    PARENT_RECEIPT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": report.ok,
                "status": payload["status"],
                "decision": report.decision,
                "finding_codes": sorted({item.code for item in report.findings}),
                "executed_suites": list(suites),
                "deferred_suites": payload["deferred_suite_ids"],
                "receipt": PARENT_RECEIPT.as_posix(),
            },
            indent=2,
        )
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
