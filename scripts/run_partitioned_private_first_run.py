"""Run or resume one private, recursively partitioned filesystem inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from matters.application.orchestrator import MatterService
from matters.application.partitioned_filesystem import (
    PartitionedFilesystemRunner,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--content-limit", type=int, default=0)
    parser.add_argument("--max-entries", type=int, default=25_000)
    parser.add_argument("--refresh", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repository = Path(__file__).resolve().parents[1]
    private_root = args.private_root.resolve()
    root = args.root.resolve(strict=True)
    manifest = args.manifest or (
        PartitionedFilesystemRunner.default_manifest_path(private_root, root)
    )
    service = MatterService(
        repository_root=repository,
        private_root=private_root,
    )
    runner = PartitionedFilesystemRunner(
        service,
        manifest_path=manifest,
        max_entries=args.max_entries,
        content_limit=args.content_limit,
    )
    result = runner.run(root, refresh=args.refresh)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
