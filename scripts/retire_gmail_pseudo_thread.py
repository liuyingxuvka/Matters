"""Retire the historical Gmail thread synthesized from ``str(None)``.

The repair is allowed only when the exact derived pseudo thread is present,
has no remaining occurrence references, and has no current source version.
It uses the ordinary inventory reconciliation owner so coverage retirement is
durable and auditable.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from matters.application.orchestrator import MatterService
from matters.inventory.owners import CandidateScope, TrackingPolicy

from ingest_gmail_export import manifest_from_payload


def _pseudo_thread_id(account_ref: str) -> str:
    raw = f"{account_ref}\0thread\0None"
    return (
        "gmail:thread:"
        + sha256(raw.encode("utf-8")).hexdigest()[:24]
    )


def retire_pseudo_thread(
    *,
    repository_root: Path,
    private_root: Path,
    scope_page: Path,
) -> dict[str, Any]:
    page = json.loads(scope_page.read_text(encoding="utf-8"))
    manifest = manifest_from_payload(page)
    service = MatterService(
        repository_root=repository_root,
        private_root=private_root,
    )
    if service.store is None or service.inventory is None:
        raise RuntimeError("private Gmail runtime is unavailable")
    snapshot = service.inventory.latest_snapshot(manifest.scope_id)
    if snapshot is None:
        raise RuntimeError("gmail_scope_snapshot_missing")
    pseudo_thread_id = _pseudo_thread_id(manifest.account_ref)
    matches = tuple(
        item
        for item in snapshot.occurrences
        if item.occurrence_id == pseudo_thread_id
    )
    if not matches:
        return {
            "artifact_type": "matters.gmail-pseudo-thread-retirement.v1",
            "status": "already_absent",
            "scope_ref": manifest.scope_id,
            "prior_revision": snapshot.revision,
            "current_revision": snapshot.revision,
            "pseudo_thread_refs_before": 0,
            "retired_count": 0,
        }
    if len(matches) != 1 or matches[0].object_type != "thread":
        raise RuntimeError("gmail_pseudo_thread_identity_conflict")
    reference_count = sum(
        item.parent_occurrence_id == pseudo_thread_id
        for item in snapshot.occurrences
    )
    if reference_count:
        raise RuntimeError("gmail_pseudo_thread_still_referenced")
    current_sources = service.current_records("source_version")
    if any(
        item.get("provider") == "gmail"
        and dict(item.get("external_reference", {})).get("external_id")
        == pseudo_thread_id
        for item in current_sources
    ):
        raise RuntimeError("gmail_pseudo_thread_current_source_present")

    scope_payload = service.store.current(
        "candidate_scope",
        manifest.scope_id,
    )
    policy_payload = service.store.current(
        "tracking_policy",
        "tracking-policy:default",
    )
    if scope_payload is None or policy_payload is None:
        raise RuntimeError("gmail_inventory_owner_inputs_missing")
    scope = CandidateScope(
        scope_id=str(scope_payload["scope_id"]),
        revision=int(scope_payload["revision"]),
        provider=str(scope_payload["provider"]),
        root_locator=str(scope_payload["root_locator"]),
        object_types=tuple(scope_payload.get("object_types", ())),
        include_hidden=bool(scope_payload.get("include_hidden", False)),
        follow_links=bool(scope_payload.get("follow_links", False)),
        active=bool(scope_payload.get("active", True)),
    )
    policy = TrackingPolicy(
        policy_id=str(policy_payload["policy_id"]),
        revision=int(policy_payload["revision"]),
        protected_classes=tuple(
            policy_payload.get("protected_classes", ())
        ),
        ignored_names=tuple(policy_payload.get("ignored_names", ())),
        archive_size_limit=int(policy_payload["archive_size_limit"]),
        changed_at=str(policy_payload["changed_at"]),
    )
    repaired, changes = service.reconcile_inventory(
        scope=scope,
        policy=policy,
        occurrences=tuple(
            item
            for item in snapshot.occurrences
            if item.occurrence_id != pseudo_thread_id
        ),
    )
    if changes.deleted != (pseudo_thread_id,):
        raise RuntimeError("gmail_pseudo_thread_retirement_not_isolated")
    if any(
        item.occurrence_id == pseudo_thread_id
        for item in repaired.occurrences
    ):
        raise RuntimeError("gmail_pseudo_thread_retirement_not_current")
    return {
        "artifact_type": "matters.gmail-pseudo-thread-retirement.v1",
        "status": "retired",
        "scope_ref": manifest.scope_id,
        "prior_revision": snapshot.revision,
        "current_revision": repaired.revision,
        "pseudo_thread_refs_before": reference_count,
        "retired_count": 1,
        "deleted_count": len(changes.deleted),
        "claim_boundary": (
            "Only the exact unreferenced thread derived from the historical "
            "literal None provider id was retired."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--scope-page", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = retire_pseudo_thread(
        repository_root=Path(__file__).resolve().parents[1],
        private_root=args.private_root,
        scope_page=args.scope_page,
    )
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.receipt.with_suffix(args.receipt.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.receipt)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
