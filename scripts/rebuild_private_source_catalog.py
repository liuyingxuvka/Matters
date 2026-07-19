"""Rebuild the private paged UI catalog from durable inventory snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from matters.application.orchestrator import MatterService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    service = MatterService(
        repository_root=repository,
        private_root=args.private_root.resolve(),
    )
    if service.inventory is None:
        raise RuntimeError("private inventory owner is unavailable")
    rebuilt = service.inventory.rebuild_catalog()
    summary = service.store.source_catalog_status_counts()
    print(
        json.dumps(
            {
                "ok": rebuilt == summary["total_count"],
                "rebuilt_count": rebuilt,
                "active_count": summary["total_count"],
                "review_count": summary["review_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if rebuilt == summary["total_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
