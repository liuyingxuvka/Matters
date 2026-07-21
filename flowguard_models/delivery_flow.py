"""Current DevelopmentProcessFlow projection for the G0-G12 Matters gates."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile

from flowguard import (
    DevelopmentProcessPlan,
    FreshnessRule,
    ProcessAction,
    ProcessArtifact,
    ProcessEvidence,
    ProofArtifactRef,
    ValidationRequirement,
    review_behavior_commitment_ledger,
    review_development_process_flow,
)

from flowguard_models.model_mesh import PARENT_ID, CHILD_IDS, run_mesh
from flowguard_models.agent_operation_models import AGENT_OPERATION_MODELS
from flowguard_models.run_model import MODELS
from flowguard_design.run_g4_review import _fingerprint as g4_design_fingerprint
from flowguard_design.ui_runtime_contract import REQUIRED_UI_CHECKS
from flowguard_design.ui_flow_structure import current_revision as ui_revision
from matters._version import VERSION
from matters.integrations.researchguard import probe_researchguard
from scripts.check_public_boundary import check as check_public_boundary


PROCESS_ID = "DPF_matters_delivery_gate"
SNAPSHOT_PATH = Path(".flowguard/evidence/process/g0_g4_snapshot.json")
RECEIPT_PATH = Path(
    ".flowguard/evidence/process/DPF_matters_delivery_gate.json"
)

DEFERRED_BCL_FINDINGS = frozenset(
    {
        "commitment_current_evidence_missing",
        "commitment_evidence_links_missing",
        "commitment_model_sync_not_current",
        "commitment_test_mesh_not_current",
        "commitment_primary_path_blocked",
        "commitment_primary_path_material_evidence_missing",
        "commitment_primary_path_risk_gate_missing",
    }
)


def _file_hash(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _json_hash(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


def _aggregate_hash(root: Path, paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _portable_openspec_projection(payload: object, exit_code: int) -> dict:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    totals = summary.get("totals", {}) if isinstance(summary, dict) else {}
    if not isinstance(totals, dict):
        totals = {}

    def count(name: str) -> int:
        value = totals.get(name, 0)
        return value if isinstance(value, int) and value >= 0 else 0

    projected_totals = {
        "passed": count("passed"),
        "failed": count("failed"),
        "warnings": count("warnings"),
        "errors": count("errors"),
    }
    valid_payload = isinstance(payload, dict)
    ok = (
        valid_payload
        and exit_code == 0
        and projected_totals["failed"] == 0
        and projected_totals["passed"] >= 1
    )
    return {
        "ok": ok,
        "provider": "openspec",
        "change_id": "build-matters-model-driven-core",
        "validation_mode": "strict",
        "exit_code": exit_code,
        "totals": projected_totals,
        "error_code": "" if valid_payload else "invalid_json_output",
        "claim_boundary": (
            "This portable projection records only provider identity, change "
            "identity, validation mode, terminal exit code, and aggregate "
            "counts. Provider roots, launcher paths, stdout, stderr, and "
            "machine-local metadata are intentionally not serialized."
        ),
    }


def _openspec_validate(root: Path) -> dict:
    node = shutil.which("node.exe") or shutil.which("node")
    cli = (
        Path.home()
        / "AppData"
        / "Roaming"
        / "npm"
        / "node_modules"
        / "@fission-ai"
        / "openspec"
        / "bin"
        / "openspec.js"
    )
    if not node or not cli.is_file():
        return {
            "ok": False,
            "provider": "openspec",
            "change_id": "build-matters-model-driven-core",
            "validation_mode": "strict",
            "exit_code": None,
            "totals": {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "errors": 0,
            },
            "error_code": "launcher_unavailable",
            "claim_boundary": (
                "The OpenSpec launcher was unavailable; no validation result "
                "or machine-local launcher path was serialized."
            ),
        }
    result = subprocess.run(
        (
            node,
            str(cli),
            "validate",
            "build-matters-model-driven-core",
            "--type",
            "change",
            "--strict",
            "--json",
            "--no-interactive",
        ),
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = None
    return _portable_openspec_projection(payload, result.returncode)


def _behavior_ledger_review(root: Path) -> dict:
    ledger_dir = root / ".flowguard" / "behavior_commitment_ledger"
    sys.path.insert(0, str(ledger_dir))
    try:
        from model import build_behavior_commitment_ledger

        report = review_behavior_commitment_ledger(
            build_behavior_commitment_ledger()
        )
    finally:
        sys.path.pop(0)
    codes = tuple(sorted({finding.code for finding in report.findings}))
    unexpected = tuple(sorted(set(codes) - DEFERRED_BCL_FINDINGS))
    return {
        "structural_inventory_ok": not unexpected,
        "native_ok": report.ok,
        "native_decision": report.decision,
        "finding_count": len(report.findings),
        "finding_codes": list(codes),
        "unexpected_finding_codes": list(unexpected),
        "deferred_finding_codes": sorted(DEFERRED_BCL_FINDINGS),
        "claim_boundary": (
            "structural_inventory_ok proves no unexpected ownership, relation, "
            "surface, lookup, or lifecycle defect. Native broad behavior "
            "coverage remains blocked until code contracts, TestMesh, current "
            "primary paths, and material runtime evidence exist."
        ),
    }


def _model_gate(root: Path) -> dict:
    inventories = (
        (
            "product_runtime",
            root / ".flowguard" / "evidence" / "models",
            {model_id: MODELS[model_id] for model_id in (PARENT_ID,) + CHILD_IDS},
        ),
        (
            "agent_operation",
            root / ".flowguard" / "evidence" / "agent_operations" / "models",
            AGENT_OPERATION_MODELS,
        ),
    )
    rows = []
    for behavior_plane, receipt_root, models in inventories:
        for model_id, model in models.items():
            path = receipt_root / f"{model_id}.json"
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                receipt = {}
            current = (
                receipt.get("model_id") == model_id
                and receipt.get("model_fingerprint") == model.fingerprint()
                and receipt.get("pass_for_g2") is True
                and "abstract_green" in receipt.get("evidence_tiers", ())
                and "hazard_green" in receipt.get("evidence_tiers", ())
                and all(
                    proof.get("observed_status") == "failed"
                    for proof in receipt.get("known_bad_proofs", ())
                )
            )
            rows.append(
                {
                    "behavior_plane": behavior_plane,
                    "model_id": model_id,
                    "current": current,
                    "evidence_id": receipt.get("evidence_id", ""),
                    "model_fingerprint": receipt.get("model_fingerprint", ""),
                }
            )
    return {
        "ok": all(row["current"] for row in rows),
        "models": rows,
        "product_model_count": sum(
            row["behavior_plane"] == "product_runtime" for row in rows
        ),
        "agent_operation_model_count": sum(
            row["behavior_plane"] == "agent_operation" for row in rows
        ),
        "claim_boundary": (
            "G2 validates M0/C1-C12 product receipts and A0/A1/A2/A3 operation "
            "receipts from separate evidence roots. A pass in one plane never "
            "substitutes for the other."
        ),
    }


def _mesh_gate(root: Path) -> dict:
    path = (
        root
        / ".flowguard"
        / "evidence"
        / "model_mesh"
        / "MM0_matters_parent_child_mesh.json"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    current = run_mesh(
        receipt_root=root / ".flowguard" / "evidence" / "models"
    )
    return {
        "ok": (
            persisted.get("status") == "mesh_green"
            and persisted.get("mesh_fingerprint")
            == current.get("mesh_fingerprint")
            and persisted.get("native_report", {}).get("ok") is True
            and persisted.get("layered_boundary_report", {}).get("ok") is True
            and not persisted.get("unbound_outputs")
        ),
        "persisted_mesh_fingerprint": persisted.get("mesh_fingerprint", ""),
        "current_mesh_fingerprint": current.get("mesh_fingerprint", ""),
        "native_decision": persisted.get("native_report", {}).get(
            "decision", ""
        ),
        "closure_decision": persisted.get("native_report", {})
        .get("closure_report", {})
        .get("decision", ""),
        "layered_decision": persisted.get(
            "layered_boundary_report", {}
        ).get("decision", ""),
    }


def _design_gate(root: Path) -> dict:
    path = (
        root
        / ".flowguard"
        / "evidence"
        / "design"
        / "G4_model_derived_design.json"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    previous = Path.cwd()
    try:
        # The design fingerprint is deliberately relative to the repository.
        import os

        os.chdir(root)
        current_fingerprint = g4_design_fingerprint()
    finally:
        os.chdir(previous)
    invariants = persisted.get("checks", {}).get("test_mesh_invariants", {})
    return {
        "ok": (
            persisted.get("structural_status") == "g4_design_green"
            and persisted.get("execution_status") == "not_run"
            and persisted.get("design_fingerprint") == current_fingerprint
            and persisted.get("checks", {}).get("architecture_native_ok") is True
            and persisted.get("checks", {}).get("field_lifecycle_native_ok") is True
            and persisted.get("checks", {}).get(
                "transition_matrix_structural_ok"
            )
            is True
            and persisted.get("checks", {}).get(
                "contract_exhaustion_native_ok"
            )
            is True
            and persisted.get("checks", {}).get("alignment_structural_ok")
            is True
            and persisted.get("checks", {}).get("test_mesh_structural_ok")
            is True
            and invariants.get("all_tests_not_run") is True
            and invariants.get("executed_count") == 0
        ),
        "evidence_id": persisted.get("evidence_id", ""),
        "persisted_design_fingerprint": persisted.get(
            "design_fingerprint", ""
        ),
        "current_design_fingerprint": current_fingerprint,
        "structural_status": persisted.get("structural_status", ""),
        "execution_status": persisted.get("execution_status", ""),
        "claim_boundary": persisted.get("claim_boundary", ""),
    }


def _g8_gate(root: Path) -> dict:
    path = (
        root
        / ".flowguard"
        / "evidence"
        / "synthetic"
        / "G8_fully_synthetic_end_to_end.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    fingerprints = payload.get("source_fingerprints", {})
    current_sources = bool(fingerprints) and all(
        (root / source_path).is_file()
        and _file_hash(root / source_path) == fingerprint
        for source_path, fingerprint in fingerprints.items()
    )
    gates = payload.get("gates", {})
    return {
        "ok": (
            payload.get("status") == "g8_synthetic_green"
            and current_sources
            and tuple(sorted(gates)) == ("G5", "G6", "G7", "G8")
            and all(row.get("status") == "passed" for row in gates.values())
        ),
        "evidence_id": payload.get("evidence_id", ""),
        "source_fingerprint": payload.get("source_fingerprint", ""),
        "current_sources": current_sources,
        "gates": gates,
        "claim_boundary": payload.get("claim_boundary", ""),
    }


def _private_first_run_gate() -> dict:
    configured = os.environ.get("MATTERS_PRIVATE_AGGREGATE", "")
    if not configured:
        return {
            "ok": False,
            "status": "not_run",
            "reason": "private_aggregate_not_supplied",
        }
    path = Path(configured).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {
            "ok": False,
            "status": "blocked",
            "reason": "private_aggregate_unreadable",
        }
    inventory = payload.get("inventory", {})
    partitions = payload.get("partition_inventory", {})
    depth = payload.get("semantic_depth", {})
    localization = payload.get("localization", {})
    maintenance = payload.get("codex_daily_maintenance", {})
    storage = payload.get("storage_migrations", {})
    evidence_handle = str(payload.get("private_evidence_handle", ""))
    safe_handle = (
        evidence_handle.startswith("private-evidence:")
        and "/" not in evidence_handle
        and "\\" not in evidence_handle
    )
    mutation_counts = maintenance.get("mutation_attempt_counts", {})
    mutation_keys = {
        "source",
        "mailbox",
        "outbound",
        "grant",
        "code",
        "model",
        "install",
        "git",
        "tag",
        "release",
    }
    zero_mutation = (
        isinstance(mutation_counts, dict)
        and set(mutation_counts) == mutation_keys
        and all(
            isinstance(mutation_counts[key], int)
            and mutation_counts[key] == 0
            for key in mutation_keys
        )
    )
    storage_migrations_current = (
        isinstance(storage, dict)
        and storage.get("status") == "current"
        and storage.get("migration_order")
        == ["evidence_pointer_rebase", "coverage_history_archive"]
        and storage.get("verified_restorable_copy") is True
        and storage.get("all_other_writers_stopped") is True
        and storage.get("evidence_pointer_rebase_terminal") is True
        and storage.get("coverage_history_archive_terminal") is True
        and storage.get("archive_verified_before_original_retirement") is True
        and storage.get("integrity_check_current") is True
        and storage.get("count_check_current") is True
        and storage.get("sampled_history_equivalence_current") is True
        and storage.get("startup_migration_attempt_count") == 0
        and storage.get("vacuum_attempt_count") == 0
        and str(
            storage.get("evidence_pointer_rebase_terminal_receipt_id", "")
        ).startswith("storage-migration:evidence-pointer:")
        and str(
            storage.get("coverage_history_archive_terminal_receipt_id", "")
        ).startswith("storage-migration:coverage-history:")
    )
    run_receipt_ids = maintenance.get("run_receipt_ids", ())
    identity_current = (
        str(maintenance.get("schedule_identity", "")).startswith(
            "codex-automation:"
        )
        and str(maintenance.get("execution_profile_identity", "")).startswith(
            "execution-profile:"
        )
        and str(
            maintenance.get("manual_rehearsal_receipt_id", "")
        ).startswith("maintenance-rehearsal:")
        and str(
            maintenance.get("manual_rehearsal_fingerprint", "")
        ).startswith("sha256:")
        and str(
            maintenance.get("install_currentness_receipt_id", "")
        ).startswith("maintenance-install:")
        and str(
            maintenance.get("install_currentness_fingerprint", "")
        ).startswith("sha256:")
        and str(
            maintenance.get("shared_service_entrypoint_fingerprint", "")
        ).startswith("sha256:")
        and isinstance(run_receipt_ids, list)
        and bool(run_receipt_ids)
        and all(
            str(receipt_id).startswith("maintenance-run:")
            for receipt_id in run_receipt_ids
        )
    )
    ok = (
        payload.get("artifact_type")
        == "matters.private-first-run-aggregate.v2"
        and payload.get("ok") is True
        and payload.get("status")
        in {"current_with_open_work", "coverage_complete"}
        and inventory.get("reconciled") is True
        and inventory.get("catalog_reconciled") is True
        and partitions.get("failed_partition_count") == 0
        and depth.get("all_accounted") is True
        and localization.get("current") is True
        and storage_migrations_current
        and maintenance.get("status") == "current"
        and maintenance.get("current") is True
        and identity_current
        and maintenance.get("installed") is True
        and maintenance.get("manual_rehearsal_current") is True
        and maintenance.get("shared_service_path") is True
        and maintenance.get("model_agnostic") is True
        and maintenance.get("app_api_key_required") is False
        and zero_mutation
        and maintenance.get("unattended_final_verification") is False
        and safe_handle
    )
    return {
        "ok": ok,
        "status": "passed" if ok else "blocked",
        "aggregate_fingerprint": _json_hash(payload),
        "private_evidence_handle": evidence_handle if safe_handle else "",
        "coverage_complete": payload.get("coverage_complete") is True,
        "runtime_status": str(payload.get("status", "")),
        "inventory_reconciled": inventory.get("reconciled") is True,
        "catalog_reconciled": inventory.get("catalog_reconciled") is True,
        "partition_status": str(partitions.get("status", "")),
        "failed_partition_count": int(
            partitions.get("failed_partition_count", 0) or 0
        ),
        "semantic_depth_accounted": depth.get("all_accounted") is True,
        "localization_current": localization.get("current") is True,
        "storage_migrations_current": storage_migrations_current,
        "storage_migration_order_current": (
            isinstance(storage, dict)
            and storage.get("migration_order")
            == ["evidence_pointer_rebase", "coverage_history_archive"]
        ),
        "storage_restorable_copy_verified": (
            isinstance(storage, dict)
            and storage.get("verified_restorable_copy") is True
        ),
        "storage_startup_migration_attempt_count": (
            storage.get("startup_migration_attempt_count")
            if isinstance(storage, dict)
            and isinstance(storage.get("startup_migration_attempt_count"), int)
            else -1
        ),
        "storage_vacuum_attempt_count": (
            storage.get("vacuum_attempt_count")
            if isinstance(storage, dict)
            and isinstance(storage.get("vacuum_attempt_count"), int)
            else -1
        ),
        "codex_daily_maintenance_installed": maintenance.get("installed") is True,
        "codex_daily_maintenance_rehearsed": (
            maintenance.get("manual_rehearsal_current") is True
        ),
        "codex_daily_maintenance_shared_path": (
            maintenance.get("shared_service_path") is True
        ),
        "codex_daily_maintenance_model_agnostic": (
            maintenance.get("model_agnostic") is True
        ),
        "codex_daily_maintenance_identity_current": identity_current,
        "codex_daily_maintenance_zero_mutation": zero_mutation,
        "codex_daily_maintenance_foreground_final_gates": (
            maintenance.get("unattended_final_verification") is False
        ),
        "claim_boundary": (
            "This gate consumes only a privacy-minimized aggregate and opaque "
            "handle. It proves a bounded real-private first run with exact "
            "inventory/depth/localization accounting, exact ordered bounded "
            "evidence-pointer and coverage-history migrations from a verified "
            "restorable copy with zero startup/VACUUM attempts, plus one manually rehearsed "
            "model-agnostic Codex-hosted daily maintenance schedule through the "
            "shared service path with zero mailbox/source/outbound mutation and "
            "no unattended final gate; coverage_complete=false remains open work "
            "and no private payload or concrete model mapping is serialized."
        ),
    }


def _generic_release_private_separation_gate() -> dict:
    private_aggregate = os.environ.get("MATTERS_PRIVATE_AGGREGATE", "")
    ok = not private_aggregate
    return {
        "ok": ok,
        "status": "passed" if ok else "blocked",
        "private_first_run_required_for_generic_release": False,
        "private_first_run_deferred_until_after_release": True,
        "private_aggregate_consumed": False,
        "reason": (
            ""
            if ok
            else "private_aggregate_must_not_be_consumed_by_generic_release"
        ),
        "claim_boundary": (
            "The generic release lane does not consume, validate, serialize, "
            "or claim completion of a private first-run aggregate. Private "
            "Gmail, filesystem, Codex-project, migration, maintenance, and "
            "semantic-coverage evidence remain a post-release acceptance "
            "domain. Supplying MATTERS_PRIVATE_AGGREGATE to this lane blocks "
            "release instead of widening the claim."
        ),
    }


def _installed_ui_gate(root: Path) -> dict:
    path = root / ".flowguard" / "evidence" / "ui" / "G10_live_ui.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {
            "ok": False,
            "status": "not_run",
            "reason": "installed_ui_evidence_unavailable",
        }
    revision = ui_revision(root)
    checks = payload.get("checks", {})
    required_checks = set(REQUIRED_UI_CHECKS)
    exact_check_inventory = (
        isinstance(checks, dict) and set(checks) == required_checks
    )
    ok = (
        payload.get("artifact_type") == "matters.live-ui-evidence.v1"
        and payload.get("status") == "passed"
        and payload.get("ui_revision") == revision
        and isinstance(checks, dict)
        and exact_check_inventory
        and all(value is True for value in checks.values())
        and not payload.get("browser_errors")
        and not payload.get("missing_checks")
    )
    return {
        "ok": ok,
        "status": "passed" if ok else "blocked",
        "evidence_id": str(payload.get("evidence_id", "")),
        "ui_revision": revision,
        "evidence_current": payload.get("ui_revision") == revision,
        "check_count": len(checks) if isinstance(checks, dict) else 0,
        "required_check_count": len(required_checks),
        "exact_check_inventory": exact_check_inventory,
        "browser_error_count": len(payload.get("browser_errors", ())),
        "claim_boundary": str(payload.get("claim_boundary", "")),
    }


def _release_artifacts(root: Path) -> tuple[Path, ...]:
    configured = tuple(
        value
        for value in (
            os.environ.get("MATTERS_RELEASE_WHEEL", ""),
            os.environ.get("MATTERS_RELEASE_SDIST", ""),
            os.environ.get("MATTERS_RELEASE_DESKTOP", ""),
        )
        if value
    )
    if configured:
        return tuple(Path(value).expanduser().resolve() for value in configured)
    candidate_root = root / "build" / "frozen-dist"
    return tuple(
        sorted(
            (
                *candidate_root.glob("matters-*.whl"),
                *candidate_root.glob("matters-*.tar.gz"),
                *candidate_root.glob("Matters-*-windows-x64.zip"),
            )
        )
    )


def _public_release_gate(root: Path) -> dict:
    artifacts = _release_artifacts(root)
    if len(artifacts) != 3 or not all(path.is_file() for path in artifacts):
        return {
            "ok": False,
            "status": "not_run",
            "reason": "frozen_release_artifact_trio_not_supplied",
            "artifact_count": len(artifacts),
        }
    configured_clone = os.environ.get("MATTERS_CLEAN_CLONE_ROOT", "")
    if not configured_clone:
        return {
            "ok": False,
            "status": "not_run",
            "reason": "external_clean_clone_not_supplied",
            "artifact_count": len(artifacts),
        }
    clean_clone_root = Path(configured_clone).expanduser().resolve()
    if clean_clone_root == root.resolve() or not clean_clone_root.is_dir():
        return {
            "ok": False,
            "status": "blocked",
            "reason": "clean_clone_must_be_distinct_existing_root",
            "artifact_count": len(artifacts),
        }
    report = check_public_boundary(
        root,
        root / "docs" / "security" / "public-file-policy.json",
        clean_clone_root=clean_clone_root,
        package_artifacts=artifacts,
        release=True,
    )
    package_rows = report.get("inventories", {}).get("package", {}).get(
        "artifacts", ()
    )
    ok = (
        report.get("ok") is True
        and report.get("inventories", {}).get("tracked", {}).get("status")
        == "pass"
        and report.get("inventories", {}).get("clean_clone", {}).get("status")
        == "pass"
        and len(package_rows) == 3
        and {str(row.get("kind", "")) for row in package_rows}
        == {"wheel", "sdist", "desktop"}
        and all(row.get("status") == "pass" for row in package_rows)
    )
    return {
        "ok": ok,
        "status": "passed" if ok else "blocked",
        "boundary_fingerprint": _json_hash(report),
        "tracked_status": report.get("inventories", {})
        .get("tracked", {})
        .get("status", ""),
        "clean_clone_status": report.get("inventories", {})
        .get("clean_clone", {})
        .get("status", ""),
        "clean_clone_distinct": clean_clone_root != root.resolve(),
        "package_statuses": [
            str(row.get("status", "")) for row in package_rows
        ],
        "finding_codes": sorted(
            {
                str(row.get("code", ""))
                for row in report.get("findings", ())
                if row.get("code")
            }
        ),
        "artifact_hashes": {
            path.name: _file_hash(path) for path in artifacts
        },
        "claim_boundary": str(report.get("claim_boundary", "")),
    }


def _git_value(root: Path, *args: str) -> str:
    candidates = (
        shutil.which("git.exe"),
        str(Path(os.environ.get("ProgramFiles", "")) / "Git" / "cmd" / "git.exe"),
        shutil.which("git"),
    )
    executable = next(
        (
            candidate
            for candidate in candidates
            if candidate
            and Path(candidate).suffix.casefold() != ".cmd"
            and Path(candidate).is_file()
        ),
        "",
    )
    if not executable:
        return ""
    result = subprocess.run(
        (executable, *args),
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _source_version_identity(root: Path) -> dict:
    try:
        project = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
        plugin = json.loads(
            (root / "plugin" / "matters-plugin.json").read_text(
                encoding="utf-8"
            )
        )
        sbom = json.loads((root / "sbom.json").read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "ok": False,
            "version": VERSION,
            "checks": {"identity_files_readable": False},
        }

    project_section = project.get("project", {})
    setuptools_dynamic = (
        project.get("tool", {})
        .get("setuptools", {})
        .get("dynamic", {})
        .get("version", {})
    )
    sbom_component = sbom.get("metadata", {}).get("component", {})
    expected_purl = f"pkg:pypi/matters@{VERSION}"
    checks = {
        "identity_files_readable": True,
        "runtime_authority": bool(VERSION),
        "project_uses_dynamic_version": (
            "version" in project_section.get("dynamic", ())
            and "version" not in project_section
        ),
        "setuptools_reads_runtime_authority": (
            setuptools_dynamic.get("attr") == "matters._version.VERSION"
        ),
        "plugin_projection": plugin.get("version") == VERSION,
        "sbom_projection": (
            sbom_component.get("version") == VERSION
            and sbom_component.get("bom-ref") == expected_purl
            and sbom_component.get("purl") == expected_purl
        ),
    }
    return {
        "ok": all(checks.values()),
        "version": VERSION,
        "checks": checks,
    }


def _standard_plugin_gate(root: Path) -> dict:
    plugin_root = root / "plugins" / "matters"
    try:
        mcp = json.loads(
            (plugin_root / ".mcp.json").read_text(encoding="utf-8")
        )
        metadata = json.loads(
            (plugin_root / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {"ok": False, "reason": "standard_plugin_unreadable"}
    matters_server = mcp.get("mcpServers", {}).get("matters", {})
    required_paths = (
        plugin_root / "skills" / "matters" / "SKILL.md",
        plugin_root
        / "skills"
        / "matters"
        / "references"
        / "service-contract.md",
    )
    checks = {
        "plugin_version": metadata.get("version") == VERSION,
        "skill_paths_current": all(path.is_file() for path in required_paths),
        "mcp_binding": (
            matters_server.get("command") == "matters-mcp"
            and matters_server.get("args") == []
        ),
    }
    return {"ok": all(checks.values()), "checks": checks}


def _desktop_install_gate(root: Path) -> dict:
    manifest_path = Path(
        os.environ.get(
            "MATTERS_DESKTOP_MANIFEST",
            str(root / "dist" / "desktop" / "desktop-manifest.json"),
        )
    ).expanduser()
    receipt_path = Path(
        os.environ.get(
            "MATTERS_DESKTOP_INSTALL_RECEIPT",
            str(
                Path.home()
                / ".matters"
                / "install"
                / "desktop"
                / "active-install.json"
            ),
        )
    ).expanduser()
    toolchain_path = Path(
        os.environ.get(
            "MATTERS_DESKTOP_TOOLCHAIN_RECEIPT",
            str(root / "dist" / "desktop" / "desktop-build-toolchain.json"),
        )
    ).expanduser()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        toolchain = json.loads(toolchain_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "ok": False,
            "reason": "desktop_manifest_or_install_receipt_unavailable",
        }
    desktop_archive_path = Path(
        os.environ.get("MATTERS_RELEASE_DESKTOP", "")
    ).expanduser()
    try:
        with zipfile.ZipFile(desktop_archive_path) as archive:
            archived_manifest = json.loads(
                archive.read("desktop-manifest.json")
            )
    except (
        OSError,
        TypeError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ):
        archived_manifest = {}
    launcher = Path(str(receipt.get("launcher", ""))).expanduser()
    launcher_hash = _file_hash(launcher) if launcher.is_file() else ""
    checks = {
        "manifest_version": manifest.get("matters_version") == VERSION,
        "manifest_fingerprint": bool(manifest.get("manifest_fingerprint")),
        "manifest_executable_hash": bool(manifest.get("executable_sha256")),
        "release_archive_manifest": archived_manifest == manifest,
        "toolchain_schema": (
            toolchain.get("schema") == "matters.desktop-build-toolchain.v1"
        ),
        "toolchain_identity": (
            manifest.get("build_toolchain_sha256")
            == receipt.get("build_toolchain_sha256")
            == _file_hash(toolchain_path)
        ),
        "receipt_schema": (
            receipt.get("schema") == "matters.desktop-install-receipt.v1"
        ),
        "receipt_version": receipt.get("matters_version") == VERSION,
        "receipt_manifest": (
            receipt.get("manifest_fingerprint")
            == manifest.get("manifest_fingerprint")
        ),
        "receipt_executable": (
            receipt.get("executable_sha256")
            == manifest.get("executable_sha256")
            == launcher_hash
        ),
        "receipt_package": (
            receipt.get("package_sha256") == manifest.get("package_sha256")
        ),
        "prior_process_shutdown": (
            receipt.get("prior_process_shutdown_verified") is True
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "manifest_fingerprint": str(
            manifest.get("manifest_fingerprint", "")
        ),
        "executable_sha256": launcher_hash,
    }


def _frozen_release_gate(
    root: Path,
    *,
    models: dict,
    installed_ui: dict,
    public_release: dict,
) -> dict:
    source_version_identity = _source_version_identity(root)
    version = str(source_version_identity["version"])
    commit = _git_value(root, "rev-parse", "HEAD")
    tag = _git_value(root, "describe", "--tags", "--exact-match", "HEAD")
    expected_tag = f"v{version}"
    artifacts = _release_artifacts(root)
    wheel = next((path for path in artifacts if path.suffix == ".whl"), None)
    install_path = Path(
        os.environ.get(
            "MATTERS_INSTALL_RECEIPT",
            str(Path.home() / ".matters" / "install" / "install-receipt.json"),
        )
    ).expanduser()
    try:
        install = json.loads(install_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        install = {}
    try:
        installed_version = importlib.metadata.version("matters")
    except importlib.metadata.PackageNotFoundError:
        installed_version = ""
    try:
        distribution = importlib.metadata.distribution("matters")
        installed_stdio = distribution.locate_file(
            "matters/api/mcp/stdio.py"
        )
        mcp_entrypoints = tuple(
            entry
            for entry in distribution.entry_points
            if entry.group == "console_scripts" and entry.name == "matters-mcp"
        )
    except importlib.metadata.PackageNotFoundError:
        installed_stdio = Path()
        mcp_entrypoints = ()
    standard_plugin = _standard_plugin_gate(root)
    desktop_install = _desktop_install_gate(root)
    tm0_path = (
        root
        / ".flowguard"
        / "evidence"
        / "tests"
        / "TM0_matters_whole_flow_gate.json"
    )
    tm19_path = (
        root
        / ".flowguard"
        / "evidence"
        / "tests"
        / "TM19_clean_install_release.json"
    )
    try:
        tm0 = json.loads(tm0_path.read_text(encoding="utf-8"))
        tm19 = json.loads(tm19_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        tm0, tm19 = {}, {}
    skill_root = root / ".flowguard" / "evidence" / "skill_runtime"
    skill_receipts = tuple(
        skill_root / "models" / f"{model_id}.json"
        for model_id in (
            "S0_matters_skill_runtime",
            "S1_skill_bundle_inventory",
            "S2_skill_compatibility",
            "S3_active_skill_resolution",
            "S4_matters_managed_skill_sync",
            "S5_skill_validation_rollback",
        )
    )
    skill_models_current = all(
        path.is_file()
        and {
            "abstract_green",
            "hazard_green",
        }.issubset(
            set(
                json.loads(path.read_text(encoding="utf-8")).get(
                    "evidence_tiers", ()
                )
            )
        )
        for path in skill_receipts
    )
    skill_mesh = (
        json.loads(
            (skill_root / "S0_skill_runtime_mesh.json").read_text(
                encoding="utf-8"
            )
        )
        if (skill_root / "S0_skill_runtime_mesh.json").is_file()
        else {}
    )
    research = probe_researchguard()
    wheel_hash = _file_hash(wheel).removeprefix("sha256:") if wheel else ""
    agent_operation_rows = tuple(
        row
        for row in models.get("models", ())
        if row.get("behavior_plane") == "agent_operation"
    )
    checks = {
        "installed_ui": installed_ui.get("ok") is True,
        "public_release_boundary": public_release.get("ok") is True,
        "git_commit": len(commit) == 40,
        "exact_release_tag": tag == expected_tag,
        "source_version": source_version_identity.get("ok") is True,
        "installed_version": installed_version == version,
        "installed_mcp_module": installed_stdio.is_file(),
        "installed_mcp_entrypoint": (
            len(mcp_entrypoints) == 1
            and mcp_entrypoints[0].value == "matters.api.mcp.stdio:main"
        ),
        "install_receipt": (
            install.get("schema") == "matters.local-install-receipt.v1"
            and install.get("matters_version") == version
            and install.get("wheel_sha256") == wheel_hash
        ),
        "product_models": models.get("ok") is True,
        "agent_operation_models": (
            models.get("agent_operation_model_count")
            == len(AGENT_OPERATION_MODELS)
            and {
                str(row.get("model_id", ""))
                for row in agent_operation_rows
            }
            == set(AGENT_OPERATION_MODELS)
            and all(row.get("current") is True for row in agent_operation_rows)
        ),
        "skill_models": skill_models_current,
        "skill_mesh": skill_mesh.get("status") == "mesh_green",
        "test_mesh": (
            tm0.get("native_report", {}).get("ok") is True
            and not tm0.get("deferred_suite_ids")
        ),
        "tm19": (
            tm19.get("test_suite_evidence", {}).get("result_status")
            == "passed"
        ),
        "researchguard": research.status == "current",
        "standard_plugin": standard_plugin.get("ok") is True,
        "desktop_install": desktop_install.get("ok") is True,
    }
    ok = all(checks.values())
    return {
        "ok": ok,
        "status": "passed" if ok else "not_run",
        "checks": checks,
        "version": version,
        "commit": commit,
        "tag": tag,
        "installed_version": installed_version,
        "wheel_sha256": wheel_hash,
        "source_version_identity": source_version_identity,
        "researchguard_status": research.status,
        "standard_plugin": standard_plugin,
        "desktop_install": desktop_install,
        "claim_boundary": (
            "This frozen local-release gate binds exact Git/tag/version, "
            "wheel/install, M0/C1-C12 product, A0/A1/A2/A3 agent-operation, and "
            "S0-S5 skill-runtime model evidence from separate roots, complete "
            "TestMesh including TM19, current installed UI, public package "
            "boundary including the desktop release archive, explicit "
            "private-first-run separation, and the frozen "
            "ResearchGuard currentness identity. It does not claim GitHub "
            "publication, Linux CI, Figma evidence, or complete private "
            "semantic coverage."
        ),
    }


def capture_delivery_snapshot(root: Path) -> dict:
    root = root.resolve()
    public = check_public_boundary(
        root,
        root / "docs" / "security" / "public-file-policy.json",
    )
    openspec = _openspec_validate(root)
    behavior_ledger = _behavior_ledger_review(root)
    models = _model_gate(root)
    mesh = _mesh_gate(root)
    design = _design_gate(root)
    g8 = _g8_gate(root)
    private = _private_first_run_gate()
    private_separation = _generic_release_private_separation_gate()
    installed_ui = _installed_ui_gate(root)
    public_release = _public_release_gate(root)
    frozen_release = _frozen_release_gate(
        root,
        models=models,
        installed_ui=installed_ui,
        public_release=public_release,
    )
    gates = {
        "G0": {
            "status": "passed" if public["ok"] else "blocked",
            "evidence": public,
        },
        "G1": {
            "status": (
                "passed"
                if (
                    openspec["ok"]
                    and behavior_ledger["structural_inventory_ok"]
                )
                else "blocked"
            ),
            "evidence": {
                "openspec": openspec,
                "behavior_ledger": behavior_ledger,
            },
        },
        "G2": {
            "status": "passed" if models["ok"] else "blocked",
            "evidence": models,
        },
        "G3": {
            "status": "passed" if mesh["ok"] else "blocked",
            "evidence": mesh,
        },
        "G4": {
            "status": "passed" if design["ok"] else "blocked",
            "evidence": design,
        },
    }
    for index in range(5, 9):
        gate_id = f"G{index}"
        gate_evidence = g8.get("gates", {}).get(gate_id, {})
        gates[gate_id] = {
            "status": (
                "passed"
                if g8["ok"] and gate_evidence.get("status") == "passed"
                else "blocked"
            ),
            "evidence": {
                "g8_receipt": {
                    "ok": g8["ok"],
                    "evidence_id": g8["evidence_id"],
                    "source_fingerprint": g8["source_fingerprint"],
                    "current_sources": g8["current_sources"],
                },
                "gate": gate_evidence,
            },
        }
    for gate_id, evidence in (
        ("G9", private_separation),
        ("G10", installed_ui),
        ("G11", public_release),
        ("G12", frozen_release),
    ):
        gates[gate_id] = {
            "status": (
                "passed"
                if evidence.get("ok") is True
                else str(evidence.get("status", "not_run"))
            ),
            "evidence": evidence,
        }
    current_index = -1
    for index in range(13):
        if gates[f"G{index}"]["status"] != "passed":
            break
        current_index = index
    current_gate = f"G{current_index}" if current_index >= 0 else "none"
    next_gate = f"G{current_index + 1}" if current_index < 12 else "complete"
    return {
        "artifact_type": "matters.delivery-snapshot.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_gate": current_gate,
        "next_gate": next_gate,
        "ok": current_index == 12,
        "gates": gates,
        "post_release_private_first_run": private,
        "claim_boundary": (
            "This snapshot advances only through consecutive current gates. "
            "G9 proves that the generic release does not consume or claim a "
            "private-first-run aggregate. The private Gmail/filesystem/Codex "
            "first run is reported separately as a post-release acceptance "
            "domain and cannot block or widen the generic release claim. G10 current "
            "installed-browser evidence, G11 clean-clone/package privacy "
            "evidence, and G12 frozen local-release identities. Open private "
            "semantic coverage, Linux CI, Figma, GitHub publication, and "
            "licensing authorization remain outside any passed claim."
        ),
    }


def _proof(
    snapshot_path: Path,
    snapshot_hash: str,
    gate_id: str,
) -> ProofArtifactRef:
    portable_snapshot_path = SNAPSHOT_PATH.as_posix()
    return ProofArtifactRef(
        artifact_id=f"artifact:{PROCESS_ID}:{gate_id}",
        producer_route="development_process_flow",
        command="python -m flowguard_models.run_delivery_flow",
        result_path=portable_snapshot_path,
        result_status="passed",
        exit_code=0,
        artifact_fingerprints={portable_snapshot_path: snapshot_hash},
        covered_obligation_ids=(f"VR-{gate_id}",),
        assertion_scope="external_contract",
        current=True,
        route_evidence_current=True,
    )


def build_plan(
    *,
    root: Path,
    snapshot_path: Path,
) -> DevelopmentProcessPlan:
    root = root.resolve()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot_hash = _file_hash(snapshot_path)
    portable_snapshot_path = SNAPSHOT_PATH.as_posix()
    openspec_files = tuple(
        path for path in (root / "openspec").rglob("*") if path.is_file()
    )
    model_files = tuple(
        path
        for path in (root / "flowguard_models").rglob("*.py")
        if path.is_file()
    )
    design_files = tuple(
        path
        for path in (root / "flowguard_design").rglob("*.py")
        if path.is_file()
    )
    source_files = tuple(
        path for path in (root / "src").rglob("*") if path.is_file()
    )
    skeleton_files = (
        root / "pyproject.toml",
        root / "src" / "matters" / "__init__.py",
        root / "ui" / "index.html",
        root / "ui" / "styles.css",
        root / "ui" / "app.js",
        root / "plugin" / "matters-plugin.json",
    )
    g7_files = (
        root
        / ".flowguard"
        / "evidence"
        / "tests"
        / "TM0_matters_whole_flow_gate.json",
        root
        / ".flowguard"
        / "evidence"
        / "alignment"
        / "model_code_test.json",
    )
    g8_path = (
        root
        / ".flowguard"
        / "evidence"
        / "synthetic"
        / "G8_fully_synthetic_end_to_end.json"
    )
    artifact_versions = {
        "artifact.g0.boundary": _aggregate_hash(
            root,
            (
                root / "docs" / "security" / "scope-manifest.yaml",
                root / "docs" / "security" / "public-file-policy.json",
                root / "scripts" / "check_public_boundary.py",
            ),
        ),
        "artifact.g1.requirements": _aggregate_hash(
            root,
            openspec_files
            + (
                root
                / ".flowguard"
                / "behavior_commitment_ledger"
                / "ledger.json",
            ),
        ),
        "artifact.g2.models": _aggregate_hash(root, model_files),
        "artifact.g3.mesh": _file_hash(
            root
            / ".flowguard"
            / "evidence"
            / "model_mesh"
            / "MM0_matters_parent_child_mesh.json"
        ),
        "artifact.g4.design": _aggregate_hash(root, design_files),
        "artifact.g5.skeleton": _aggregate_hash(root, skeleton_files),
        "artifact.g6.implementation": _aggregate_hash(root, source_files),
        "artifact.g7.validation": _aggregate_hash(root, g7_files),
        "artifact.g8.synthetic": _file_hash(g8_path),
        "artifact.g9.generic_private_separation": _json_hash(
            snapshot["gates"]["G9"]["evidence"]
        ),
        "artifact.g10.installed_ui": _json_hash(
            snapshot["gates"]["G10"]["evidence"]
        ),
        "artifact.g11.public_release": _json_hash(
            snapshot["gates"]["G11"]["evidence"]
        ),
        "artifact.g12.frozen_release": _json_hash(
            snapshot["gates"]["G12"]["evidence"]
        ),
    }
    artifacts = tuple(
        ProcessArtifact(
            artifact_id,
            artifact_type=(
                "requirement" if gate_id in {"G0", "G1"} else "model"
            ),
            current_version=artifact_versions[artifact_id],
            path=path,
            owner=PROCESS_ID,
            upstream_artifact_ids=upstream,
            description=description,
        )
        for artifact_id, gate_id, path, upstream, description in (
            (
                "artifact.g0.boundary",
                "G0",
                "docs/security",
                (),
                "scope, privacy, and public candidate boundary",
            ),
            (
                "artifact.g1.requirements",
                "G1",
                "openspec",
                ("artifact.g0.boundary",),
                "OpenSpec change and Behavior Commitment Ledger",
            ),
            (
                "artifact.g2.models",
                "G2",
                "flowguard_models",
                ("artifact.g1.requirements",),
                (
                    "M0 and C1-C12 executable finite models, including "
                    "coverage/source repair, atomic parent composition, "
                    "same-Matter canonicalization, exact observation-time "
                    "correction, complete-scope parent narrative, and catalog "
                    "query-shape obligations; scan-independent selection identity, "
                    "bounded anchor-set pointers, exact compressed history, and "
                    "exact C6-admitted Matter identity are current model boundaries"
                ),
            ),
            (
                "artifact.g3.mesh",
                "G3",
                ".flowguard/evidence/model_mesh",
                ("artifact.g2.models",),
                "current M0/C1-C12 ModelMesh receipt",
            ),
            (
                "artifact.g4.design",
                "G4",
                "flowguard_design",
                ("artifact.g3.mesh",),
                (
                    "model-derived module, field, contract, coverage, and "
                    "TestMesh design; indexed catalog page selection before "
                    "visible-card hydration plus storage/identity Model-Miss "
                    "coverage remain hard G4 gates"
                ),
            ),
            (
                "artifact.g5.skeleton",
                "G5",
                "src/matters",
                ("artifact.g4.design",),
                "model-derived package, UI, plugin, and test skeleton",
            ),
            (
                "artifact.g6.implementation",
                "G6",
                "src/matters",
                ("artifact.g5.skeleton",),
                "C1-C12 owner implementations and MatterService facade",
            ),
            (
                "artifact.g7.validation",
                "G7",
                ".flowguard/evidence/tests",
                ("artifact.g6.implementation",),
                "current TestMesh and model-code-test alignment receipts",
            ),
            (
                "artifact.g8.synthetic",
                "G8",
                ".flowguard/evidence/synthetic",
                ("artifact.g7.validation",),
                "fully synthetic cross-provider and correction conformance receipt",
            ),
            (
                "artifact.g9.generic_private_separation",
                "G9",
                "release://generic-private-separation",
                ("artifact.g8.synthetic",),
                "generic release excludes and defers the private first run",
            ),
            (
                "artifact.g10.installed_ui",
                "G10",
                ".flowguard/evidence/ui",
                ("artifact.g9.generic_private_separation",),
                "current installed object-browser interaction evidence",
            ),
            (
                "artifact.g11.public_release",
                "G11",
                "package://release-boundary",
                ("artifact.g10.installed_ui",),
                "tracked, clean-clone, package, link, path, and privacy evidence",
            ),
            (
                "artifact.g12.frozen_release",
                "G12",
                f"release://local-v{VERSION}",
                ("artifact.g11.public_release",),
                "frozen local Git, tag, package, install, model, and test identities",
            ),
        )
    )
    base_evidence = tuple(
        ProcessEvidence(
            evidence_id=f"evidence:{PROCESS_ID}:{gate_id}",
            evidence_kind=kind,
            producer_route=route,
            status="passed",
            covers_artifacts=(artifact_id,),
            covered_versions={
                artifact_id: artifact_versions[artifact_id],
            },
            validation_requirement_ids=(f"VR-{gate_id}",),
            produced_by_action_id=f"action:{gate_id}",
            command=command,
            result_path=portable_snapshot_path,
            proof_artifact=_proof(snapshot_path, snapshot_hash, gate_id),
        )
        for gate_id, artifact_id, kind, route, command in (
            (
                "G0",
                "artifact.g0.boundary",
                "public_boundary",
                "development_process_flow",
                "python scripts/check_public_boundary.py --root .",
            ),
            (
                "G1",
                "artifact.g1.requirements",
                "requirements",
                "openspec",
                "openspec validate build-matters-model-driven-core --type change --strict --json --no-interactive",
            ),
            (
                "G2",
                "artifact.g2.models",
                "model",
                "model_first_function_flow",
                "python -m flowguard_models.run_model <model_id>",
            ),
            (
                "G3",
                "artifact.g3.mesh",
                "model_mesh",
                "model_mesh_maintenance",
                "python -m flowguard_models.run_mesh",
            ),
            (
                "G4",
                "artifact.g4.design",
                "model_derived_design",
                "code_structure+field_lifecycle+contract_exhaustion+model_test_alignment+test_mesh",
                "python -m flowguard_design.run_g4_review",
            ),
            (
                "G5",
                "artifact.g5.skeleton",
                "module_skeleton",
                "development_process_flow",
                "python -m flowguard_design.run_g8_review",
            ),
            (
                "G6",
                "artifact.g6.implementation",
                "implementation",
                "development_process_flow",
                "python -m flowguard_design.run_test_mesh",
            ),
            (
                "G7",
                "artifact.g7.validation",
                "model_code_test",
                "model_test_alignment+test_mesh",
                "python -m flowguard_design.run_alignment",
            ),
            (
                "G8",
                "artifact.g8.synthetic",
                "synthetic_e2e",
                "development_process_flow",
                "python -m flowguard_design.run_g8_review",
            ),
        )
    )
    release_gate_rows = (
        (
            "G9",
            "artifact.g9.generic_private_separation",
            "generic_private_separation",
            "development_process_flow",
            "python -m flowguard_models.run_delivery_flow",
        ),
        (
            "G10",
            "artifact.g10.installed_ui",
            "installed_ui",
            "ui_flow_structure",
            "node scripts/verify_live_ui.js --url <loopback> --ui-revision <current>",
        ),
        (
            "G11",
            "artifact.g11.public_release",
            "public_release_boundary",
            "development_process_flow",
            "python scripts/check_public_boundary.py --root . --release --clean-clone-root . --package-artifact <wheel> --package-artifact <sdist>",
        ),
        (
            "G12",
            "artifact.g12.frozen_release",
            "frozen_release",
            "development_process_flow",
            "python -m flowguard_models.run_delivery_flow",
        ),
    )
    release_evidence = tuple(
        ProcessEvidence(
            evidence_id=f"evidence:{PROCESS_ID}:{gate_id}",
            evidence_kind=kind,
            producer_route=route,
            status="passed",
            covers_artifacts=(artifact_id,),
            covered_versions={artifact_id: artifact_versions[artifact_id]},
            validation_requirement_ids=(f"VR-{gate_id}",),
            produced_by_action_id=f"action:{gate_id}",
            command=command,
            result_path=portable_snapshot_path,
            proof_artifact=_proof(snapshot_path, snapshot_hash, gate_id),
        )
        for gate_id, artifact_id, kind, route, command in release_gate_rows
        if snapshot["gates"][gate_id]["status"] == "passed"
    )
    evidence = base_evidence + release_evidence
    base_validations = tuple(
        ValidationRequirement(
            requirement_id=f"VR-{gate_id}",
            required_artifact_ids=(artifact_id,),
            required_evidence_kinds=(kind,),
            evidence_ids=(f"evidence:{PROCESS_ID}:{gate_id}",),
            command=command,
            description=f"{gate_id} current gate evidence",
        )
        for gate_id, artifact_id, kind, command in (
            (
                "G0",
                "artifact.g0.boundary",
                "public_boundary",
                "python scripts/check_public_boundary.py --root .",
            ),
            (
                "G1",
                "artifact.g1.requirements",
                "requirements",
                "openspec validate build-matters-model-driven-core --type change --strict --json --no-interactive",
            ),
            (
                "G2",
                "artifact.g2.models",
                "model",
                "python -m flowguard_models.run_model <model_id>",
            ),
            (
                "G3",
                "artifact.g3.mesh",
                "model_mesh",
                "python -m flowguard_models.run_mesh",
            ),
            (
                "G4",
                "artifact.g4.design",
                "model_derived_design",
                "python -m flowguard_design.run_g4_review",
            ),
            (
                "G5",
                "artifact.g5.skeleton",
                "module_skeleton",
                "python -m flowguard_design.run_g8_review",
            ),
            (
                "G6",
                "artifact.g6.implementation",
                "implementation",
                "python -m flowguard_design.run_test_mesh",
            ),
            (
                "G7",
                "artifact.g7.validation",
                "model_code_test",
                "python -m flowguard_design.run_alignment",
            ),
            (
                "G8",
                "artifact.g8.synthetic",
                "synthetic_e2e",
                "python -m flowguard_design.run_g8_review",
            ),
        )
    )
    release_validations = tuple(
        ValidationRequirement(
            requirement_id=f"VR-{gate_id}",
            required_artifact_ids=(artifact_id,),
            required_evidence_kinds=(kind,),
            evidence_ids=(f"evidence:{PROCESS_ID}:{gate_id}",),
            scope="release",
            release_required=True,
            command=command,
            description=f"{gate_id} current release-gate evidence",
        )
        for gate_id, artifact_id, kind, _route, command in release_gate_rows
        if snapshot["gates"][gate_id]["status"] == "passed"
    )
    validations = base_validations + release_validations
    actions = []
    current_artifact_ids = {
        0: "artifact.g0.boundary",
        1: "artifact.g1.requirements",
        2: "artifact.g2.models",
        3: "artifact.g3.mesh",
        4: "artifact.g4.design",
        5: "artifact.g5.skeleton",
        6: "artifact.g6.implementation",
        7: "artifact.g7.validation",
        8: "artifact.g8.synthetic",
        9: "artifact.g9.generic_private_separation",
        10: "artifact.g10.installed_ui",
        11: "artifact.g11.public_release",
        12: "artifact.g12.frozen_release",
    }
    for index in range(13):
        gate_id = f"G{index}"
        done = snapshot["gates"][gate_id]["status"] == "passed"
        order_after = ((f"action:G{index - 1}",) if index else ())
        actions.append(
            ProcessAction(
                action_id=f"action:{gate_id}",
                action_type="validation" if done else "work",
                writes_artifacts=(
                    (current_artifact_ids[index],) if done else ()
                ),
                produced_evidence_ids=(
                    (f"evidence:{PROCESS_ID}:{gate_id}",) if done else ()
                ),
                required_validation_ids=(
                    (f"VR-{gate_id}",) if done else ()
                ),
                order_after=order_after,
                status="done" if done else "planned",
                actor="primary_agent",
                description=(
                    f"{gate_id} executed and current"
                    if done
                    else f"{gate_id} is explicitly not_run"
                ),
            )
        )
    return DevelopmentProcessPlan(
        process_id=PROCESS_ID,
        artifacts=artifacts,
        actions=tuple(actions),
        evidence=evidence,
        validation_requirements=validations,
        freshness_rules=(
            FreshnessRule(
                "boundary-invalidates-requirements-model-and-mesh",
                upstream_artifact_id="artifact.g0.boundary",
                invalidates_artifact_ids=(
                    "artifact.g1.requirements",
                    "artifact.g2.models",
                    "artifact.g3.mesh",
                    "artifact.g4.design",
                    "artifact.g5.skeleton",
                    "artifact.g6.implementation",
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "requirements",
                    "model",
                    "model_mesh",
                    "model_derived_design",
                    "module_skeleton",
                    "implementation",
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description=(
                    "scope or privacy boundary change invalidates every "
                    "downstream Phase A authority and receipt"
                ),
            ),
            FreshnessRule(
                "requirements-invalidate-model-and-mesh",
                upstream_artifact_id="artifact.g1.requirements",
                invalidates_artifact_ids=(
                    "artifact.g2.models",
                    "artifact.g3.mesh",
                    "artifact.g4.design",
                    "artifact.g5.skeleton",
                    "artifact.g6.implementation",
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "model",
                    "model_mesh",
                    "model_derived_design",
                    "module_skeleton",
                    "implementation",
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description=(
                    "requirements change invalidates child and mesh evidence"
                ),
            ),
            FreshnessRule(
                "models-invalidate-mesh",
                upstream_artifact_id="artifact.g2.models",
                invalidates_artifact_ids=(
                    "artifact.g3.mesh",
                    "artifact.g4.design",
                    "artifact.g5.skeleton",
                    "artifact.g6.implementation",
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "model_mesh",
                    "model_derived_design",
                    "module_skeleton",
                    "implementation",
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description=(
                    "model declaration change invalidates mesh and derived design"
                ),
            ),
            FreshnessRule(
                "mesh-invalidates-derived-design",
                upstream_artifact_id="artifact.g3.mesh",
                invalidates_artifact_ids=("artifact.g4.design",),
                invalidates_evidence_kinds=("model_derived_design",),
                description=(
                    "ModelMesh ownership or interface change invalidates G4 design"
                ),
            ),
            FreshnessRule(
                "design-invalidates-implementation-and-synthetic-evidence",
                upstream_artifact_id="artifact.g4.design",
                invalidates_artifact_ids=(
                    "artifact.g5.skeleton",
                    "artifact.g6.implementation",
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "module_skeleton",
                    "implementation",
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description="G4 design changes invalidate G5-G8",
            ),
            FreshnessRule(
                "skeleton-invalidates-implementation-and-validation",
                upstream_artifact_id="artifact.g5.skeleton",
                invalidates_artifact_ids=(
                    "artifact.g6.implementation",
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "implementation",
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description="package boundary changes invalidate implementation evidence",
            ),
            FreshnessRule(
                "implementation-invalidates-validation-and-e2e",
                upstream_artifact_id="artifact.g6.implementation",
                invalidates_artifact_ids=(
                    "artifact.g7.validation",
                    "artifact.g8.synthetic",
                ),
                invalidates_evidence_kinds=(
                    "model_code_test",
                    "synthetic_e2e",
                ),
                description="owner code changes invalidate tests and synthetic E2E",
            ),
            FreshnessRule(
                "validation-invalidates-synthetic-e2e",
                upstream_artifact_id="artifact.g7.validation",
                invalidates_artifact_ids=("artifact.g8.synthetic",),
                invalidates_evidence_kinds=("synthetic_e2e",),
                description="test or alignment receipt changes invalidate G8",
            ),
            FreshnessRule(
                "synthetic-invalidates-generic-private-separation",
                upstream_artifact_id="artifact.g8.synthetic",
                invalidates_artifact_ids=(
                    "artifact.g9.generic_private_separation",
                    "artifact.g10.installed_ui",
                    "artifact.g11.public_release",
                    "artifact.g12.frozen_release",
                ),
                invalidates_evidence_kinds=(
                    "generic_private_separation",
                    "installed_ui",
                    "public_release_boundary",
                    "frozen_release",
                ),
                description="synthetic contract drift invalidates every generic release gate",
            ),
            FreshnessRule(
                "generic-private-separation-invalidates-installed-ui-release",
                upstream_artifact_id="artifact.g9.generic_private_separation",
                invalidates_artifact_ids=(
                    "artifact.g10.installed_ui",
                    "artifact.g11.public_release",
                    "artifact.g12.frozen_release",
                ),
                invalidates_evidence_kinds=(
                    "installed_ui",
                    "public_release_boundary",
                    "frozen_release",
                ),
                description="generic/private claim-boundary drift invalidates downstream release claims",
            ),
            FreshnessRule(
                "installed-ui-invalidates-public-release",
                upstream_artifact_id="artifact.g10.installed_ui",
                invalidates_artifact_ids=(
                    "artifact.g11.public_release",
                    "artifact.g12.frozen_release",
                ),
                invalidates_evidence_kinds=(
                    "public_release_boundary",
                    "frozen_release",
                ),
                description="installed UI drift invalidates package and frozen-release claims",
            ),
            FreshnessRule(
                "public-release-invalidates-frozen-release",
                upstream_artifact_id="artifact.g11.public_release",
                invalidates_artifact_ids=("artifact.g12.frozen_release",),
                invalidates_evidence_kinds=("frozen_release",),
                description="candidate package or privacy drift invalidates frozen release",
            ),
        ),
        decision_scope=(
            "release"
            if snapshot["gates"]["G12"]["status"] == "passed"
            else "routine"
        ),
        require_proof_artifacts=True,
        release_deferred_allowed=snapshot["gates"]["G12"]["status"] != "passed",
        process_optimization_reasons=(),
    )


def build_receipt(root: Path) -> dict:
    root = root.resolve()
    snapshot_path = root / SNAPSHOT_PATH
    snapshot = capture_delivery_snapshot(root)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    plan = build_plan(root=root, snapshot_path=snapshot_path)
    report = review_development_process_flow(plan)
    plan_payload = plan.to_dict()
    plan_fingerprint = "sha256:" + sha256(
        json.dumps(
            plan_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    current = snapshot["ok"] and report.ok
    current_gate = str(snapshot["current_gate"])
    next_gate = str(snapshot["next_gate"])
    return {
        "artifact_type": "matters.development-process-flow-receipt.v1",
        "process_id": PROCESS_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_fingerprint": plan_fingerprint,
        "evidence_id": (
            f"evidence:{PROCESS_ID}:"
            f"{plan_fingerprint.removeprefix('sha256:')[:16]}"
        ),
        "status": (
            "frozen_local_release_green"
            if current
            else f"{current_gate.lower()}_current"
            if current_gate != "none"
            else "blocked"
        ),
        "current_gate": current_gate,
        "next_gate": next_gate,
        "snapshot_path": SNAPSHOT_PATH.as_posix(),
        "snapshot_hash": _file_hash(snapshot_path),
        "snapshot": snapshot,
        "plan": plan_payload,
        "native_report": report.to_dict(),
        "claim_boundary": (
            "The receipt proves only consecutive current gates through "
            f"{current_gate}. A G12 result is a frozen local-release claim "
            "covering explicit private-first-run separation, installed UI, clean "
            "clone/packages, Git/tag/version, model, TestMesh, skill, install, "
            "and ResearchGuard identities. The separate post-release private "
            "first-run acceptance may later require exact terminal pointer/archive "
            "migration receipts, but G12 does not consume or claim them. It never "
            "claims complete private semantic coverage, Figma evidence, Linux CI, licensing approval, "
            "GitHub push, or public publication."
        ),
    }
