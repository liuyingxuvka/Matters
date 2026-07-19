"""Apply the current reversible tracking policy to private current inventory."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path, PurePath

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.inventory.owners import (
    CandidateScope,
    InventoryOwner,
    InventoryOccurrence,
    classify_occurrence,
)


def _scope(payload: dict[str, object]) -> CandidateScope:
    return CandidateScope(
        scope_id=str(payload["scope_id"]),
        revision=int(payload["revision"]),
        provider=str(payload["provider"]),
        root_locator=str(payload["root_locator"]),
        object_types=tuple(str(item) for item in payload["object_types"]),
        include_hidden=bool(payload.get("include_hidden", False)),
        follow_links=bool(payload.get("follow_links", False)),
        active=bool(payload.get("active", True)),
    )


def reclassify(private_root: Path, repository_root: Path) -> dict[str, int]:
    service = MatterService(
        private_root=private_root,
        repository_root=repository_root,
    )
    assert service.store is not None
    workflow = SourceWorkflow(service)
    policy = workflow._policy("tracking-policy:default")
    ignored = {name.casefold() for name in policy.ignored_names}
    policy_roots: list[Path] = []
    manifest_root = private_root / "runs" / "filesystem-partitions"
    for manifest_path in manifest_root.glob("*.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            policy_roots.append(Path(str(manifest["authorized_root"])).resolve())
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            continue
    inspected_scopes = changed_scopes = changed_occurrences = 0

    for payload in service.store.iter_current("inventory_snapshot"):
        snapshot = InventoryOwner._snapshot_from_payload(payload)
        scope_payload = service.store.current(
            "candidate_scope",
            snapshot.scope_id,
        )
        if (
            scope_payload is None
            or str(scope_payload.get("provider")) != "filesystem"
        ):
            continue
        inspected_scopes += 1
        scope = _scope(scope_payload)
        scope_root = Path(scope.root_locator).resolve()
        prefix_parts: tuple[str, ...] = ()
        containing_roots = []
        for policy_root in policy_roots:
            try:
                relative_scope = scope_root.relative_to(policy_root)
            except ValueError:
                continue
            containing_roots.append((len(policy_root.parts), relative_scope))
        if containing_roots:
            prefix_parts = tuple(
                str(item)
                for item in max(containing_roots, key=lambda item: item[0])[1].parts
            )
        prior_dispositions = {
            item.occurrence_id: item for item in snapshot.dispositions
        }
        updated: list[InventoryOccurrence] = []
        scope_changed = 0
        for occurrence in snapshot.occurrences:
            full_parts = (
                *prefix_parts,
                *PurePath(occurrence.locator).parts,
            )
            tokens = tuple(
                sorted(
                    {
                        str(part).casefold()
                        for part in full_parts
                        if str(part).casefold() in ignored
                    }
                )
            )
            metadata = dict(occurrence.metadata)
            if tokens:
                metadata["policy_path_tokens"] = tokens
            candidate = replace(occurrence, metadata=metadata)
            prior = prior_dispositions[occurrence.occurrence_id]
            revised = classify_occurrence(
                candidate,
                policy,
                user_intent=prior.user_intent,
            )
            if (
                revised.status,
                revised.reason,
                revised.decided_by,
            ) != (
                prior.status,
                prior.reason,
                prior.decided_by,
            ):
                scope_changed += 1
            updated.append(candidate)
        if not scope_changed:
            continue
        service.reconcile_inventory(
            scope=scope,
            policy=policy,
            occurrences=tuple(updated),
        )
        changed_scopes += 1
        changed_occurrences += scope_changed

    return {
        "policy_revision": policy.revision,
        "inspected_scope_count": inspected_scopes,
        "changed_scope_count": changed_scopes,
        "changed_occurrence_count": changed_occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    print(
        json.dumps(
            reclassify(args.private_root, args.repository_root),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
