"""Read-only preflight for one bounded Jira evaluation slice.

This command never contacts Jira and never writes a receipt. Any real
authorization or prior decision file must live outside the public repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for import_root in (REPOSITORY_ROOT / "src", REPOSITORY_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from flowguard_models.delivery_flow import _g8_gate
from matters.providers.jira.contracts import JiraAuthorizationManifest
from matters.providers.jira.slices import (
    JiraSliceGate,
    SLICE_ORDER,
    SliceDecisionRecord,
)


def _external_file(path: Path, repository_root: Path) -> Path:
    resolved = path.resolve()
    root = repository_root.resolve()
    if resolved == root or resolved.is_relative_to(root):
        raise ValueError("private Jira control files must remain outside Git")
    if not resolved.is_file():
        raise ValueError(f"control file does not exist: {resolved}")
    return resolved


def _authorization_from_payload(payload: dict[str, Any]):
    return JiraAuthorizationManifest(
        authorization_scope_id=str(payload["authorization_scope_id"]),
        instance_ref_hash=str(payload["instance_ref_hash"]),
        provider_edition=str(payload["provider_edition"]),
        provider_version=str(payload["provider_version"]),
        capabilities=tuple(payload["capabilities"]),
        project_ref_hashes=frozenset(payload["project_ref_hashes"]),
        object_ids=frozenset(payload["object_ids"]),
        object_types=frozenset(payload["object_types"]),
        time_start=str(payload["time_start"]),
        time_end=str(payload["time_end"]),
        permission_fingerprint=str(payload["permission_fingerprint"]),
        expires_at=str(payload["expires_at"]),
        attachment_metadata_allowed=bool(
            payload.get("attachment_metadata_allowed", False)
        ),
        attachment_content_allowed=bool(
            payload.get("attachment_content_allowed", False)
        ),
        active=bool(payload.get("active", True)),
        operations=frozenset(payload.get("operations", ("read",))),
    )


def _prior_decisions_from_payload(
    payload: list[dict[str, Any]],
) -> tuple[SliceDecisionRecord, ...]:
    return tuple(
        SliceDecisionRecord(
            slice_id=str(row["slice_id"]),
            decision=str(row["decision"]),
            coverage_receipt_id=str(row["coverage_receipt_id"]),
            depth_report_id=str(row["depth_report_id"]),
            user_decision_id=str(row["user_decision_id"]),
        )
        for row in payload
    )


def build_preflight(
    *,
    repository_root: Path,
    slice_id: str,
    g8_current: bool,
    authorization_path: Path | None = None,
    prior_decisions_path: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    authorization = None
    if authorization_path is not None:
        path = _external_file(authorization_path, repository_root)
        authorization = _authorization_from_payload(
            json.loads(path.read_text(encoding="utf-8"))
        )
    prior_decisions: tuple[SliceDecisionRecord, ...] = ()
    if prior_decisions_path is not None:
        path = _external_file(prior_decisions_path, repository_root)
        prior_decisions = _prior_decisions_from_payload(
            json.loads(path.read_text(encoding="utf-8"))
        )
    result = JiraSliceGate().preflight(
        slice_id=slice_id,
        g8_current=g8_current,
        authorization=authorization,
        prior_decisions=prior_decisions,
        as_of=as_of,
    )
    return {
        "artifact_type": "matters.jira-slice-preflight.v1",
        "slice_id": result.slice_id,
        "status": result.status,
        "read_allowed": result.read_allowed,
        "blockers": list(result.blockers),
        "real_jira_access": "not_run",
        "claim_boundary": result.claim_boundary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", choices=SLICE_ORDER, default="J1")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--prior-decisions", type=Path)
    parser.add_argument("--as-of")
    args = parser.parse_args()
    root = REPOSITORY_ROOT
    as_of = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else None
    )
    g8 = _g8_gate(root)
    try:
        payload = build_preflight(
            repository_root=root,
            slice_id=args.slice,
            g8_current=bool(g8["ok"]),
            authorization_path=args.authorization,
            prior_decisions_path=args.prior_decisions,
            as_of=as_of,
        )
    except (KeyError, TypeError, ValueError) as exc:
        payload = {
            "artifact_type": "matters.jira-slice-preflight.v1",
            "slice_id": args.slice,
            "status": "not_run",
            "read_allowed": False,
            "blockers": [f"invalid_private_control:{exc}"],
            "real_jira_access": "not_run",
            "claim_boundary": (
                "Invalid private control input blocks before provider access."
            ),
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["read_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
