"""Canonical local CLI for the autonomous Matter object browser."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Protocol, Sequence, TextIO

from matters.presentation.localization import UnsupportedLocale


class EntrypointService(Protocol):
    def capabilities(self) -> object: ...
    def locale_registry(self) -> object: ...
    def object_browser_projection(self, **kwargs: object) -> object: ...
    def object_catalog_page(self, **kwargs: object) -> object: ...
    def matter_detail(self, *, matter_id: str, locale: str) -> object: ...
    def matter_evidence(self, *, matter_id: str, offset: int, limit: int) -> object: ...
    def object_coverage_summary(self) -> object: ...
    def pending_analysis_packages(self, *, offset: int, limit: int) -> object: ...
    def import_autonomous_result(self, **kwargs: object) -> object: ...
    def run_maintenance_cycle(self, *, limit: int) -> object: ...
    def submit_matter_correction(self, **kwargs: object) -> object: ...
    def set_matter_cover(self, **kwargs: object) -> object: ...
    def version(self) -> object: ...
    def work_status(self) -> object: ...
    def pause_work(self, *, job_id: str) -> object: ...
    def resume_work(self, *, job_id: str) -> object: ...
    def scan_filesystem(self, *, root: str, content_limit: int | None) -> object: ...
    def synchronize_managed_skill_projections(
        self,
        *,
        transaction_id_prefix: str,
    ) -> object: ...


class CapabilityUnavailable(RuntimeError):
    pass


def _jsonable(value: object) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    raise TypeError(f"unsupported service result type: {type(value).__name__}")


def _invoke(service: object, method_name: str, /, **kwargs: object) -> Any:
    method = getattr(service, method_name, None)
    if not callable(method):
        raise CapabilityUnavailable(method_name)
    return _jsonable(method(**kwargs))


def _catalog_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    parser.add_argument("--query", default="")
    parser.add_argument(
        "--status",
        default="all",
        choices=("all", "planned", "in_progress", "completed"),
    )
    parser.add_argument(
        "--time",
        default="all",
        choices=("all", "recent", "upcoming", "undated"),
    )
    parser.add_argument("--sort", default="recent", choices=("recent", "title", "state"))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matters",
        description="Operate the local autonomous Matters object browser.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    commands.add_parser("locales")
    commands.add_parser("coverage")
    commands.add_parser("version")
    commands.add_parser("status")
    browser = commands.add_parser("browser")
    _catalog_arguments(browser)
    catalog = commands.add_parser("catalog")
    _catalog_arguments(catalog)
    detail = commands.add_parser("detail")
    detail.add_argument("matter_id")
    detail.add_argument("--locale", default="en", choices=("en", "zh-CN"))
    evidence = commands.add_parser("evidence")
    evidence.add_argument("matter_id")
    evidence.add_argument("--offset", type=int, default=0)
    evidence.add_argument("--limit", type=int, default=50)
    packages = commands.add_parser("analysis-packages")
    packages.add_argument("--offset", type=int, default=0)
    packages.add_argument("--limit", type=int, default=20)
    imported = commands.add_parser("analysis-import")
    imported.add_argument("package_id")
    imported.add_argument("result_file", type=Path)
    imported.add_argument("--provider-id", default="codex-local")
    imported.add_argument("--provider-version", required=True)
    maintenance = commands.add_parser("maintenance")
    maintenance.add_argument("--limit", type=int, default=20)
    correction = commands.add_parser("correct")
    correction.add_argument("matter_id")
    correction.add_argument("rationale")
    correction.add_argument("--field", default="")
    correction.add_argument("--value", default="")
    cover = commands.add_parser("cover")
    cover.add_argument("matter_id")
    cover.add_argument("asset_id", nargs="?", default="")
    cover.add_argument("--automatic", action="store_true")
    cover.add_argument("--rationale", default="user_selected_representative_visual")
    skill_sync = commands.add_parser("skill-sync")
    skill_sync.add_argument("transaction_id_prefix")
    pause = commands.add_parser("pause")
    pause.add_argument("job_id")
    resume = commands.add_parser("resume")
    resume.add_argument("job_id")
    for name, help_text, default_limit in (
        ("inventory", "Inventory one authorized root without content reads.", 0),
        ("canary", "Run a small private source-modeling pass.", 20),
        ("expand", "Expand bounded private source modeling.", 1000),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("root", type=Path)
        if default_limit:
            command.add_argument("--limit", type=int, default=default_limit)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _catalog_kwargs(args: argparse.Namespace) -> dict[str, object]:
    if args.offset < 0 or args.limit < 1 or args.limit > 200:
        raise ValueError("invalid_page_bounds")
    return {
        "locale": args.locale,
        "query": args.query,
        "status": args.status,
        "time_filter": args.time,
        "sort": args.sort,
        "offset": args.offset,
        "limit": args.limit,
    }


def run(
    argv: Sequence[str] | None = None,
    *,
    service: EntrypointService,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        command = args.command
        if command in {"capabilities", "locales", "coverage", "version", "status"}:
            method = {
                "capabilities": "capabilities",
                "locales": "locale_registry",
                "coverage": "object_coverage_summary",
                "version": "version",
                "status": "work_status",
            }[command]
            result = _invoke(service, method)
        elif command in {"browser", "catalog"}:
            result = _invoke(
                service,
                (
                    "object_browser_projection"
                    if command == "browser"
                    else "object_catalog_page"
                ),
                **_catalog_kwargs(args),
            )
        elif command == "detail":
            result = _invoke(
                service,
                "matter_detail",
                matter_id=args.matter_id,
                locale=args.locale,
            )
        elif command == "evidence":
            result = _invoke(
                service,
                "matter_evidence",
                matter_id=args.matter_id,
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "analysis-packages":
            result = _invoke(
                service,
                "pending_analysis_packages",
                offset=args.offset,
                limit=args.limit,
            )
        elif command == "analysis-import":
            payload = json.loads(args.result_file.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("result_object_required")
            result = _invoke(
                service,
                "import_autonomous_result",
                package_id=args.package_id,
                provider_id=args.provider_id,
                provider_version=args.provider_version,
                result=payload,
            )
        elif command == "maintenance":
            result = _invoke(
                service,
                "run_maintenance_cycle",
                limit=args.limit,
            )
        elif command == "correct":
            result = _invoke(
                service,
                "submit_matter_correction",
                matter_id=args.matter_id,
                rationale=args.rationale,
                field_name=args.field,
                corrected_value=args.value,
            )
        elif command == "cover":
            result = _invoke(
                service,
                "set_matter_cover",
                matter_id=args.matter_id,
                asset_id=args.asset_id,
                active=not args.automatic,
                rationale=args.rationale,
            )
        elif command == "skill-sync":
            result = _invoke(
                service,
                "synchronize_managed_skill_projections",
                transaction_id_prefix=args.transaction_id_prefix,
            )
        elif command == "pause":
            result = _invoke(service, "pause_work", job_id=args.job_id)
        elif command == "resume":
            result = _invoke(service, "resume_work", job_id=args.job_id)
        elif command in {"inventory", "canary", "expand"}:
            result = _invoke(
                service,
                "scan_filesystem",
                root=str(args.root),
                content_limit=0 if command == "inventory" else args.limit,
            )
        else:
            raise CapabilityUnavailable("serve_requires_local_composition")
    except CapabilityUnavailable as exc:
        error = {"code": "capability_unavailable", "operation": str(exc)}
        exit_code = 3
    except RuntimeError:
        error = {"code": "runtime_unavailable"}
        exit_code = 5
    except UnsupportedLocale:
        error = {"code": "unsupported_locale"}
        exit_code = 4
    except (KeyError, TypeError, ValueError):
        error = {"code": "invalid_request"}
        exit_code = 4
    else:
        json.dump({"ok": True, "result": result}, output, ensure_ascii=False, sort_keys=True)
        output.write("\n")
        return 0
    json.dump({"ok": False, "error": error}, errors, ensure_ascii=False, sort_keys=True)
    errors.write("\n")
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    from matters.runtime import create_service, repository_root

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "serve":
        parsed = build_parser().parse_args(arguments)
        from wsgiref.simple_server import make_server

        from matters.api.http.static import create_local_application

        service = create_service()
        service.start_autonomous_maintenance()
        application = create_local_application(
            service,
            ui_root=repository_root() / "ui",
        )
        try:
            with make_server(parsed.host, parsed.port, application) as server:
                print(
                    f"Matters is available at http://{parsed.host}:{parsed.port}/",
                    flush=True,
                )
                server.serve_forever()
        finally:
            service.stop_autonomous_maintenance()
        return 0
    return run(arguments, service=create_service())


__all__ = [
    "CapabilityUnavailable",
    "EntrypointService",
    "build_parser",
    "main",
    "run",
]


if __name__ == "__main__":
    raise SystemExit(main())
