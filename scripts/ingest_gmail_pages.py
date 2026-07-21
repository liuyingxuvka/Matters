"""Audit and ingest one explicitly supplied Gmail page chain.

The input pages stay outside the repository.  Terminal coverage is accepted
only when the requested/next cursor chain is explicit and continuous.  A
bounded, non-terminal legacy export may be ingested only with an explicit
partial-coverage flag; it can add observations but cannot claim deletion or
mailbox completion.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.gmail import GmailReadOnlyAdapter

from audit_gmail_page_chain import (
    GmailPageChain,
    GmailPageChainError,
    audit_page_paths,
)
from ingest_gmail_export import (
    authorized_page_from_payload,
    manifest_from_payload,
)


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _cursor(
    payload: Mapping[str, Any],
    *,
    requested: bool,
) -> tuple[bool, str]:
    keys = (
        ("requested_page_token", "requested_cursor")
        if requested
        else ("next_page_token", "next_cursor")
    )
    for key in keys:
        if key in payload:
            return True, _text(payload.get(key))
    return False, ""


def _build_adapter(
    chain: GmailPageChain,
    *,
    allow_unverified_partial: bool,
) -> GmailReadOnlyAdapter:
    report = chain.report
    if report["status"] == "blocked":
        raise GmailPageChainError("gmail_page_chain_coverage_blocked")
    verified = bool(report["cursor_chain_verified"])
    terminal = bool(report["last_page_terminal"])
    if (not verified and terminal) or (
        not terminal and not allow_unverified_partial
    ):
        raise GmailPageChainError("gmail_cursor_chain_unverified")

    manifest = manifest_from_payload(chain.pages[0])
    pages_by_cursor = {}
    prior_next = ""
    for index, payload in enumerate(chain.pages):
        requested_present, requested = _cursor(payload, requested=True)
        if index == 0:
            requested = ""
        elif not requested_present:
            # Legacy exports did not preserve the requested token.  This
            # reconstruction is allowed only for an explicitly bounded partial
            # import and is never presented as cursor-chain proof.
            requested = prior_next
        _next_present, raw_next = _cursor(payload, requested=False)
        is_last = index == len(chain.pages) - 1
        page_terminal = bool(payload.get("terminal", False)) and verified
        next_cursor = "" if (is_last and not page_terminal) else raw_next
        coverage = "complete" if page_terminal else "partial"
        page = authorized_page_from_payload(
            payload,
            manifest,
            requested_cursor=requested,
            next_cursor=next_cursor,
            terminal=page_terminal,
            coverage=coverage,
        )
        if requested in pages_by_cursor:
            raise GmailPageChainError("gmail_requested_cursor_duplicate")
        pages_by_cursor[requested] = page
        prior_next = raw_next

    def page_source(cursor: str):
        try:
            return pages_by_cursor[cursor]
        except KeyError as error:
            raise GmailPageChainError(
                "gmail_page_cursor_not_supplied"
            ) from error

    return GmailReadOnlyAdapter(
        manifest,
        page_source=page_source,
    )


def ingest_page_chain(
    chain: GmailPageChain,
    *,
    private_root: Path,
    repository_root: Path,
    content_limit: int,
    content_offset: int = 0,
    allow_unverified_partial: bool = False,
) -> dict[str, Any]:
    """Ingest all supplied pages under one workflow snapshot."""

    if content_limit < 0 or content_offset < 0:
        raise ValueError("Gmail content limits must be non-negative")
    adapter = _build_adapter(
        chain,
        allow_unverified_partial=allow_unverified_partial,
    )
    service = MatterService(
        repository_root=repository_root,
        private_root=private_root,
    )
    result = SourceWorkflow(service).run_gmail(
        adapter,
        content_limit=content_limit,
        content_offset=content_offset,
        page_limit=len(chain.pages),
    )
    changes = result.changes
    return {
        "audit": dict(chain.report),
        "claim": (
            "verified_terminal_chain"
            if chain.report["safe_terminal_coverage"]
            else "explicit_bounded_partial_chain"
        ),
        "inventory_delta": {
            "added_count": len(changes.added),
            "modified_count": len(changes.modified),
            "moved_count": len(changes.moved),
            "deleted_count": len(changes.deleted),
            "unchanged_count": len(changes.unchanged),
            "no_delta": changes.no_delta,
        },
        "result": asdict(result.summary),
    }


def ingest_page_paths(
    paths: Sequence[Path],
    **kwargs: Any,
) -> dict[str, Any]:
    return ingest_page_chain(audit_page_paths(paths), **kwargs)


def reconcile_page_chain_metadata(
    chain: GmailPageChain,
    *,
    private_root: Path,
    repository_root: Path,
    after_object_id: str = "",
    metadata_limit: int = 500,
) -> dict[str, Any]:
    """Repair one bounded page of C2 owners from a verified terminal chain."""

    if metadata_limit < 1 or metadata_limit > 500:
        raise ValueError(
            "Gmail metadata reconciliation limit must be between 1 and 500"
        )
    adapter = _build_adapter(
        chain,
        allow_unverified_partial=False,
    )
    if not chain.report["safe_terminal_coverage"]:
        raise GmailPageChainError(
            "gmail_metadata_reconciliation_requires_terminal_chain"
        )
    service = MatterService(
        repository_root=repository_root,
        private_root=private_root,
    )
    result = SourceWorkflow(service).reconcile_gmail_metadata_owners(
        adapter,
        after_object_id=after_object_id,
        limit=metadata_limit,
        page_limit=len(chain.pages),
    )
    return {
        "audit": dict(chain.report),
        "claim": "verified_terminal_chain",
        "metadata_reconciliation": asdict(result),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", action="append", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--content-limit", type=int, default=20)
    parser.add_argument("--content-offset", type=int, default=0)
    parser.add_argument("--metadata-reconcile-only", action="store_true")
    parser.add_argument("--after-object-id", default="")
    parser.add_argument("--metadata-limit", type=int, default=500)
    parser.add_argument("--allow-unverified-partial", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    try:
        chain = audit_page_paths(tuple(args.page))
        if args.audit_only:
            terminal = bool(chain.report["safe_terminal_coverage"])
            output = {
                "ok": terminal,
                **chain.report,
            }
            if not terminal:
                output["reason"] = (
                    "gmail_page_chain_not_terminal_or_verified"
                )
            print(json.dumps(output, sort_keys=True))
            return 0 if terminal else 2
        if args.metadata_reconcile_only:
            if args.allow_unverified_partial:
                raise ValueError(
                    "Gmail metadata reconciliation rejects partial coverage"
                )
            result = reconcile_page_chain_metadata(
                chain,
                private_root=args.private_root,
                repository_root=Path(__file__).resolve().parents[1],
                after_object_id=args.after_object_id,
                metadata_limit=args.metadata_limit,
            )
        else:
            result = ingest_page_chain(
                chain,
                private_root=args.private_root,
                repository_root=Path(__file__).resolve().parents[1],
                content_limit=args.content_limit,
                content_offset=args.content_offset,
                allow_unverified_partial=args.allow_unverified_partial,
            )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "blocked",
                    "reason": str(error),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps({"ok": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
