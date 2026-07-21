"""Freeze current G5-G8 fully synthetic implementation evidence."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from flowguard_design.inventory import (
    AGENT_OPERATION_ORDER,
    ALL_TEST_SUITES,
    MODEL_ORDER,
    MODULE_PATHS,
)
from flowguard_design.run_g4_review import _fingerprint as g4_fingerprint
from flowguard_design.synthetic_sources import review_fixture_inventory
from flowguard_models.delivery_flow import _mesh_gate, _model_gate
from scripts.check_public_boundary import check as check_public_boundary


ROOT = Path(".")
OUTPUT = Path(
    ".flowguard/evidence/synthetic/G8_fully_synthetic_end_to_end.json"
)
TEST_ROOT = Path(".flowguard/evidence/tests")
ALIGNMENT_PATH = Path(
    ".flowguard/evidence/alignment/model_code_test.json"
)
TEST_MESH_PATH = TEST_ROOT / "TM0_matters_whole_flow_gate.json"
G4_PATH = Path(
    ".flowguard/evidence/design/G4_model_derived_design.json"
)


def _hash(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _aggregate(paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _test_receipts_current() -> dict:
    rows = []
    routine_suite_ids = tuple(
        suite_id
        for suite_id in ALL_TEST_SUITES
        if suite_id != "TM19_clean_install_release"
    )
    for suite_id in routine_suite_ids:
        path = TEST_ROOT / f"{suite_id}.json"
        if not path.is_file():
            rows.append(
                {
                    "suite_id": suite_id,
                    "current": False,
                    "reason": "receipt missing",
                }
            )
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        evidence = payload["test_suite_evidence"]
        fingerprints = payload.get("source_fingerprints", {})
        current = (
            evidence.get("result_status") == "passed"
            and evidence.get("terminal_status") == "passed"
            and evidence.get("exit_code") == 0
            and evidence.get("evidence_current") is True
            and evidence.get("progress_only") is False
            and fingerprints
            and all(
                Path(source).is_file() and _hash(Path(source)) == fingerprint
                for source, fingerprint in fingerprints.items()
            )
        )
        rows.append(
            {
                "suite_id": payload["suite_id"],
                "receipt": path.as_posix(),
                "receipt_fingerprint": _hash(path),
                "current": bool(current),
            }
        )
    return {
        "ok": len(rows) == len(routine_suite_ids)
        and all(row["current"] for row in rows),
        "suites": rows,
    }


def _alignment_current() -> dict:
    payload = json.loads(ALIGNMENT_PATH.read_text(encoding="utf-8"))
    current_inputs = all(
        Path(path).is_file() and _hash(Path(path)) == fingerprint
        for path, fingerprint in payload.get("input_fingerprints", {}).items()
    )
    models_ok = all(
        row.get("report", {}).get("ok") is True
        and not row.get("report", {}).get("findings")
        for row in payload.get("models", ())
    )
    return {
        "ok": (
            payload.get("status") == "alignment_green"
            and current_inputs
            and models_ok
            and len(payload.get("models", ()))
            == len(MODEL_ORDER) + len(AGENT_OPERATION_ORDER)
        ),
        "evidence_id": payload.get("evidence_id", ""),
        "alignment_fingerprint": payload.get("alignment_fingerprint", ""),
        "model_count": len(payload.get("models", ())),
    }


def _optional_jira_dormant_boundary() -> dict:
    root = Path("src/matters/providers/jira")
    banned_roots = {"requests", "httpx", "atlassian", "urllib3"}
    findings = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            for name in names & banned_roots:
                findings.append(
                    {
                        "path": path.as_posix(),
                        "code": "embedded_jira_network_client",
                        "module": name,
                    }
                )
    return {
        "ok": not findings,
        "findings": findings,
        "activation_status": "not_run",
        "claim_boundary": (
            "The source-only optional Jira adapter contains no embedded network "
            "client and is not activated or required by v0.2."
        ),
    }


def _skeleton() -> dict:
    required = tuple(
        sorted(
            {
                *MODULE_PATHS.values(),
                "pyproject.toml",
                "src/matters/__init__.py",
                "ui/index.html",
                "ui/styles.css",
                "ui/app.js",
                "plugin/matters-plugin.json",
                "tests/fixtures/source_universe_synthetic/cases.json",
            }
        )
    )
    missing = tuple(path for path in required if not Path(path).is_file())
    empty = tuple(
        path
        for path in required
        if Path(path).is_file() and Path(path).stat().st_size == 0
    )
    return {
        "ok": not missing and not empty,
        "required_count": len(required),
        "missing": list(missing),
        "empty": list(empty),
    }


def main() -> int:
    root = ROOT.resolve()
    g4 = json.loads(G4_PATH.read_text(encoding="utf-8"))
    g4_current = (
        g4.get("structural_status") == "g4_design_green"
        and g4.get("design_fingerprint") == g4_fingerprint()
    )
    model_gate = _model_gate(root)
    mesh_gate = _mesh_gate(root)
    test_receipts = _test_receipts_current()
    test_mesh = json.loads(TEST_MESH_PATH.read_text(encoding="utf-8"))
    deferred_suite_ids = test_mesh.get("deferred_suite_ids")
    test_mesh_current = (
        test_mesh.get("status") in {"routine_green", "release_green"}
        and test_mesh.get("native_report", {}).get("ok") is True
        and deferred_suite_ids
        in (["TM19_clean_install_release"], [])
    )
    alignment = _alignment_current()
    fixture = review_fixture_inventory()
    optional_jira = _optional_jira_dormant_boundary()
    skeleton = _skeleton()
    public = check_public_boundary(
        root,
        root / "docs/security/public-file-policy.json",
    )
    tm14 = json.loads(
        (
            TEST_ROOT / "TM14_end_to_end_conformance.json"
        ).read_text(encoding="utf-8")
    )
    tm17 = json.loads(
        (
            TEST_ROOT / "TM17_revocation_full_propagation.json"
        ).read_text(encoding="utf-8")
    )
    e2e_current = all(
        row["test_suite_evidence"]["result_status"] == "passed"
        for row in (tm14, tm17)
    )
    source_paths = tuple(
        sorted(
            (
                *(
                    path
                    for base in ("src", "tests", "ui", "plugin", "plugins")
                    for path in Path(base).rglob("*")
                    if (
                        path.is_file()
                        and "__pycache__" not in path.parts
                        and path.suffix not in {".pyc", ".pyo", ".log"}
                    )
                ),
                Path("pyproject.toml"),
            ),
            key=lambda path: path.as_posix(),
        )
    )
    gates = {
        "G5": {"status": "passed" if skeleton["ok"] else "blocked", "evidence": skeleton},
        "G6": {
            "status": "passed" if test_receipts["ok"] else "blocked",
            "evidence": {
                "model_gate": model_gate,
                "test_receipts": test_receipts,
            },
        },
        "G7": {
            "status": (
                "passed"
                if mesh_gate["ok"] and test_mesh_current and alignment["ok"]
                else "blocked"
            ),
            "evidence": {
                "mesh": mesh_gate,
                "test_mesh_current": test_mesh_current,
                "alignment": alignment,
            },
        },
        "G8": {
            "status": (
                "passed"
                if e2e_current and fixture["ok"] and optional_jira["ok"] and public["ok"]
                else "blocked"
            ),
            "evidence": {
                "tm14_current": tm14["test_suite_evidence"]["result_status"] == "passed",
                "tm17_current": tm17["test_suite_evidence"]["result_status"] == "passed",
                "fixture": fixture,
                "optional_jira_dormant": optional_jira,
                "public_boundary": public,
            },
        },
    }
    ok = (
        g4_current
        and model_gate["ok"]
        and all(item["status"] == "passed" for item in gates.values())
    )
    source_fingerprint = _aggregate(source_paths)
    payload = {
        "artifact_type": "matters.g8-fully-synthetic-e2e-receipt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_id": (
            "evidence:G8-fully-synthetic:"
            + source_fingerprint.removeprefix("sha256:")[:16]
        ),
        "status": "g8_synthetic_green" if ok else "blocked",
        "source_fingerprint": source_fingerprint,
        "source_fingerprints": {
            path.as_posix(): _hash(path) for path in source_paths
        },
        "g4_current": g4_current,
        "gates": gates,
        "claim_boundary": (
            "Current evidence covers provider-neutral fully synthetic source "
            "universe, ResearchOperation, and correction paths only. No real "
            "private read, ResearchGuard execution, release check, GitHub "
            "action, or publication occurred."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "status": payload["status"],
                "evidence_id": payload["evidence_id"],
                "g4_current": g4_current,
                "gates": {
                    gate_id: row["status"] for gate_id, row in gates.items()
                },
                "receipt": OUTPUT.as_posix(),
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
