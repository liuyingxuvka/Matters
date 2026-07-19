"""Run bounded filesystem first-pass inventory in one private-runtime process."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.filesystem import FilesystemReadOnlyAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--content-limit", type=int, default=0)
    parser.add_argument("--max-entries", type=int, default=100_000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.content_limit < 0 or args.max_entries < 1:
        raise SystemExit(2)
    repository = Path(__file__).resolve().parents[1]
    service = MatterService(
        repository_root=repository,
        private_root=args.private_root,
    )
    workflow = SourceWorkflow(service)
    results = []
    ok = True
    for root in args.root:
        try:
            result = workflow.run_filesystem(
                FilesystemReadOnlyAdapter(
                    root,
                    page_size=args.max_entries,
                    max_entries=args.max_entries,
                ),
                content_limit=args.content_limit,
            )
            row = {"ok": True, "summary": asdict(result.summary)}
        except Exception as exc:
            ok = False
            row = {
                "ok": False,
                "error": {
                    "code": type(exc).__name__,
                    "message": str(exc),
                },
            }
        results.append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
    print(
        json.dumps(
            {
                "ok": ok,
                "root_count": len(args.root),
                "passed_count": sum(bool(item["ok"]) for item in results),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
