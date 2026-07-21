"""Create one privacy-safe receipt across verified Gmail query chains."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from audit_gmail_page_chain import audit_page_paths


def _digest(value: object) -> str:
    return "sha256:" + sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _ids(paths: Iterable[Path]) -> set[str]:
    return {
        str(item["id"])
        for path in paths
        for item in json.loads(path.read_text(encoding="utf-8")).get(
            "messages",
            (),
        )
        if item.get("id")
    }


def summarize(
    *,
    after_pages: tuple[Path, ...],
    middle_pages: tuple[Path, ...],
    before_pages: tuple[Path, ...],
    legacy_partial_pages: tuple[Path, ...],
) -> dict[str, Any]:
    verified_groups = {
        "after_2021": after_pages,
        "2017_2021": middle_pages,
        "before_2017": before_pages,
    }
    audits = {
        name: audit_page_paths(paths)
        for name, paths in verified_groups.items()
    }
    if any(
        not bool(chain.report["safe_terminal_coverage"])
        for chain in audits.values()
    ):
        raise RuntimeError("gmail_verified_chain_not_terminal")
    legacy = audit_page_paths(legacy_partial_pages)
    if legacy.report["status"] != "partial":
        raise RuntimeError("gmail_legacy_chain_not_partial")

    after_ids = _ids(after_pages)
    middle_ids = _ids(middle_pages)
    before_ids = _ids(before_pages)
    legacy_ids = _ids(legacy_partial_pages)
    verified_union = after_ids | middle_ids | before_ids
    return {
        "artifact_type": "matters.gmail-combined-coverage-receipt.v1",
        "status": "current",
        "verified_scopes": {
            name: {
                "status": "complete",
                "page_count": int(chain.report["page_count"]),
                "unique_message_count": int(
                    chain.report["unique_message_count"]
                ),
                "cursor_chain_verified": True,
                "terminal": True,
            }
            for name, chain in audits.items()
        },
        "verified_union_message_count": len(verified_union),
        "cross_scope_overlap": {
            "after_2021_and_2017_2021": len(after_ids & middle_ids),
            "after_2021_and_before_2017": len(after_ids & before_ids),
            "2017_2021_and_before_2017": len(middle_ids & before_ids),
        },
        "legacy_broad_partial": {
            "status": "partial",
            "page_count": int(legacy.report["page_count"]),
            "unique_message_count": len(legacy_ids),
            "cursor_chain_verified": False,
            "terminal": False,
            "covered_by_verified_union_count": len(
                legacy_ids & verified_union
            ),
            "not_in_verified_union_count": len(
                legacy_ids - verified_union
            ),
        },
        "verified_union_fingerprint": _digest(sorted(verified_union)),
        "claim_boundary": (
            "Complete applies separately to the three exact verified query "
            "chains at message-id enumeration depth. The legacy broad query "
            "remains partial. Cross-scope duplicates are counted once in the "
            "verified union."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--after-page",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--middle-page",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--before-page",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--legacy-partial-page",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = summarize(
        after_pages=tuple(args.after_page),
        middle_pages=tuple(args.middle_page),
        before_pages=tuple(args.before_page),
        legacy_partial_pages=tuple(args.legacy_partial_page),
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
