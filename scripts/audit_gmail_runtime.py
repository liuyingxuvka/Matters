"""Privacy-safe aggregate audit for the local Gmail runtime."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from matters.application.orchestrator import MatterService

from ingest_gmail_export import manifest_from_payload


def _pseudo_thread_id(account_ref: str) -> str:
    raw = f"{account_ref}\0thread\0None"
    return (
        "gmail:thread:"
        + sha256(raw.encode("utf-8")).hexdigest()[:24]
    )


def _scope_summary(service: MatterService, page_path: Path) -> dict[str, Any]:
    payload = json.loads(page_path.read_text(encoding="utf-8"))
    manifest = manifest_from_payload(payload)
    snapshot = service.inventory.latest_snapshot(manifest.scope_id)
    if snapshot is None:
        return {
            "scope_ref": manifest.scope_id,
            "status": "missing",
            "revision": 0,
            "messages": 0,
            "threads": 0,
            "attachments": 0,
            "parented_messages": 0,
            "pseudo_thread_refs": 0,
            "pseudo_thread_present": False,
        }
    pseudo_thread_id = _pseudo_thread_id(manifest.account_ref)
    return {
        "scope_ref": manifest.scope_id,
        "status": "current",
        "revision": snapshot.revision,
        "messages": sum(
            item.object_type == "message" for item in snapshot.occurrences
        ),
        "threads": sum(
            item.object_type == "thread" for item in snapshot.occurrences
        ),
        "attachments": sum(
            item.object_type == "attachment"
            for item in snapshot.occurrences
        ),
        "parented_messages": sum(
            item.object_type == "message"
            and bool(item.parent_occurrence_id)
            for item in snapshot.occurrences
        ),
        "pseudo_thread_refs": sum(
            item.parent_occurrence_id == pseudo_thread_id
            for item in snapshot.occurrences
        ),
        "pseudo_thread_present": any(
            item.occurrence_id == pseudo_thread_id
            for item in snapshot.occurrences
        ),
    }


def audit_runtime(
    *,
    repository_root: Path,
    private_root: Path,
    scope_pages: tuple[Path, ...],
) -> dict[str, Any]:
    service = MatterService(
        repository_root=repository_root,
        private_root=private_root,
    )
    if service.store is None or service.inventory is None:
        raise RuntimeError("private Gmail runtime is unavailable")
    sources = tuple(
        item
        for item in service.current_records("source_version")
        if item.get("provider") == "gmail"
    )
    message_sources = tuple(
        item
        for item in sources
        if dict(item.get("external_reference", {})).get("object_type")
        == "gmail_message"
    )
    thread_sources = tuple(
        item
        for item in sources
        if dict(item.get("external_reference", {})).get("object_type")
        == "gmail_thread"
    )
    return {
        "artifact_type": "matters.gmail-runtime-audit.v1",
        "status": "current",
        "gmail_current_source_count": len(sources),
        "gmail_current_message_source_count": len(message_sources),
        "gmail_current_body_source_count": sum(
            "body_text_fingerprint" in dict(item.get("content", {}))
            for item in message_sources
        ),
        "gmail_current_thread_source_count": len(thread_sources),
        "scopes": [
            _scope_summary(service, path) for path in scope_pages
        ],
        "claim_boundary": (
            "Counts describe current local projections for the supplied Gmail "
            "scope pages. They expose no message ids, addresses, content, or "
            "cursor tokens."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument(
        "--scope-page",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    report = audit_runtime(
        repository_root=Path(__file__).resolve().parents[1],
        private_root=args.private_root,
        scope_pages=tuple(args.scope_page),
    )
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.receipt.with_suffix(args.receipt.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.receipt)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
