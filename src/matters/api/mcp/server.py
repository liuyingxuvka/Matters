"""In-process MCP adapter for the autonomous Matter object browser."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping

from matters.presentation.localization import UnsupportedLocale


CATALOG_STATUSES = ("all", "planned", "in_progress", "completed")
CATALOG_TIME_FILTERS = ("all", "recent", "upcoming", "undated")
CATALOG_SORTS = ("recent", "title", "state")
DEFAULT_CATALOG_LIMIT = 60
DEFAULT_EVIDENCE_LIMIT = 50
DEFAULT_OPERATION_LIMIT = 20
MAX_PAGE_LIMIT = 200
MAX_OFFSET = 10_000_000


class CapabilityUnavailable(RuntimeError):
    """The injected service does not implement the requested MCP operation."""


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


def _object_schema(
    properties: Mapping[str, object] | None = None,
    *,
    required: tuple[str, ...] = (),
) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "object",
        "properties": dict(properties or {}),
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


def _catalog_schema() -> dict[str, object]:
    return _object_schema(
        {
            "locale": {
                "type": "string",
                "description": "A locale tag returned by the locales tool.",
            },
            "query": {"type": "string"},
            "status": {"type": "string", "enum": list(CATALOG_STATUSES)},
            "time": {
                "type": "string",
                "enum": list(CATALOG_TIME_FILTERS),
            },
            "sort": {"type": "string", "enum": list(CATALOG_SORTS)},
            "offset": {
                "type": "integer",
                "minimum": 0,
                "maximum": MAX_OFFSET,
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_PAGE_LIMIT,
            },
        }
    )


def _page_schema() -> dict[str, object]:
    return _object_schema(
        {
            "offset": {
                "type": "integer",
                "minimum": 0,
                "maximum": MAX_OFFSET,
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_PAGE_LIMIT,
            },
        }
    )


TOOLS: tuple[dict[str, object], ...] = (
    {
        "name": "capabilities",
        "description": "Return current Matters capabilities and availability.",
        "inputSchema": _object_schema(),
    },
    {
        "name": "locales",
        "description": "Return the locale registry and default locale.",
        "inputSchema": _object_schema(),
    },
    {
        "name": "get_browser",
        "description": (
            "Return one bounded autonomous object-browser projection, "
            "including catalog, coverage, and background status."
        ),
        "inputSchema": _catalog_schema(),
    },
    {
        "name": "list_matters",
        "description": "Return one bounded, filtered Matter-card page.",
        "inputSchema": _catalog_schema(),
    },
    {
        "name": "get_matter",
        "description": "Return the current localized detail for one Matter.",
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "locale": {
                    "type": "string",
                    "description": "A locale tag returned by the locales tool.",
                },
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "get_evidence",
        "description": "Return one bounded evidence page for a Matter.",
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                **_page_schema()["properties"],
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "get_coverage",
        "description": "Return aggregate object-coverage and worker progress.",
        "inputSchema": _object_schema(),
    },
    {
        "name": "list_pending_analysis",
        "description": (
            "Return a bounded private page of pending autonomous AI work "
            "packages."
        ),
        "inputSchema": _page_schema(),
    },
    {
        "name": "import_autonomous_result",
        "description": (
            "Validate and import one evidence-bounded autonomous AI result, "
            "then dispatch it to canonical owners."
        ),
        "inputSchema": _object_schema(
            {
                "package_id": {"type": "string", "minLength": 1},
                "provider_id": {"type": "string", "minLength": 1},
                "provider_version": {"type": "string", "minLength": 1},
                "result": {"type": "object"},
            },
            required=(
                "package_id",
                "provider_id",
                "provider_version",
                "result",
            ),
        ),
    },
    {
        "name": "run_maintenance",
        "description": "Run one bounded autonomous maintenance cycle.",
        "inputSchema": _object_schema(
            {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                }
            }
        ),
    },
    {
        "name": "submit_correction",
        "description": (
            "Submit an optional post-publication Matter correction and "
            "request canonical recomputation."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "rationale": {"type": "string", "minLength": 1},
                "field_name": {"type": "string"},
                "corrected_value": {"type": "string"},
            },
            required=("matter_id", "rationale"),
        ),
    },
    {
        "name": "set_cover",
        "description": (
            "Pin an allowed representative visual or return cover choice "
            "to autonomous selection."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "asset_id": {"type": "string"},
                "active": {"type": "boolean"},
                "rationale": {"type": "string", "minLength": 1},
            },
            required=("matter_id", "active", "rationale"),
        ),
    },
    {
        "name": "sync_skills",
        "description": (
            "Synchronize only already managed local skill projections."
        ),
        "inputSchema": _object_schema(
            {
                "transaction_id_prefix": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 64,
                }
            },
            required=("transaction_id_prefix",),
        ),
    },
)


class MattersMCP:
    """Stateless MCP dispatcher delegating every operation to MatterService."""

    def __init__(self, service: object):
        self._service = service

    @staticmethod
    def list_tools() -> tuple[dict[str, object], ...]:
        return TOOLS

    def _invoke(self, method_name: str, /, **kwargs: object) -> Any:
        method = getattr(self._service, method_name, None)
        if not callable(method):
            raise CapabilityUnavailable(method_name)
        return _jsonable(method(**kwargs))

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        if arguments is not None and not isinstance(arguments, Mapping):
            return self._error("invalid_arguments")
        args = dict(arguments or {})
        try:
            if name == "capabilities":
                self._require_no_arguments(args)
                result = self._invoke("capabilities")
            elif name == "locales":
                self._require_no_arguments(args)
                result = self._invoke("locale_registry")
            elif name in {"get_browser", "list_matters"}:
                catalog_args = self._catalog_arguments(args)
                result = self._invoke(
                    (
                        "object_browser_projection"
                        if name == "get_browser"
                        else "object_catalog_page"
                    ),
                    **catalog_args,
                )
            elif name == "get_matter":
                self._reject_unknown(args, {"matter_id", "locale"})
                result = self._invoke(
                    "matter_detail",
                    matter_id=self._required_string(args, "matter_id"),
                    locale=self._optional_string(args, "locale", "en"),
                )
            elif name == "get_evidence":
                self._reject_unknown(
                    args,
                    {"matter_id", "offset", "limit"},
                )
                offset, limit = self._page_arguments(
                    args,
                    default_limit=DEFAULT_EVIDENCE_LIMIT,
                    extra_keys={"matter_id"},
                )
                result = self._invoke(
                    "matter_evidence",
                    matter_id=self._required_string(args, "matter_id"),
                    offset=offset,
                    limit=limit,
                )
            elif name == "get_coverage":
                self._require_no_arguments(args)
                result = self._invoke("object_coverage_summary")
            elif name == "list_pending_analysis":
                offset, limit = self._page_arguments(
                    args,
                    default_limit=DEFAULT_OPERATION_LIMIT,
                )
                result = self._invoke(
                    "pending_analysis_packages",
                    offset=offset,
                    limit=limit,
                )
            elif name == "import_autonomous_result":
                self._reject_unknown(
                    args,
                    {
                        "package_id",
                        "provider_id",
                        "provider_version",
                        "result",
                    },
                )
                result_payload = args.get("result")
                if not isinstance(result_payload, Mapping):
                    raise ValueError("result_object_required")
                result = self._invoke(
                    "import_autonomous_result",
                    package_id=self._required_string(args, "package_id"),
                    provider_id=self._required_string(args, "provider_id"),
                    provider_version=self._required_string(
                        args,
                        "provider_version",
                    ),
                    result=dict(result_payload),
                )
            elif name == "run_maintenance":
                self._reject_unknown(args, {"limit"})
                limit = self._bounded_integer(
                    args,
                    "limit",
                    default=DEFAULT_OPERATION_LIMIT,
                    minimum=1,
                    maximum=MAX_PAGE_LIMIT,
                )
                result = self._invoke(
                    "run_maintenance_cycle",
                    limit=limit,
                )
            elif name == "submit_correction":
                self._reject_unknown(
                    args,
                    {
                        "matter_id",
                        "rationale",
                        "field_name",
                        "corrected_value",
                    },
                )
                result = self._invoke(
                    "submit_matter_correction",
                    matter_id=self._required_string(args, "matter_id"),
                    rationale=self._required_string(args, "rationale"),
                    field_name=self._optional_string(args, "field_name", ""),
                    corrected_value=self._optional_string(
                        args,
                        "corrected_value",
                        "",
                    ),
                )
            elif name == "set_cover":
                self._reject_unknown(
                    args,
                    {"matter_id", "asset_id", "active", "rationale"},
                )
                active = self._required_boolean(args, "active")
                asset_id = self._optional_string(args, "asset_id", "")
                if active and not asset_id:
                    raise ValueError("asset_id_required")
                result = self._invoke(
                    "set_matter_cover",
                    matter_id=self._required_string(args, "matter_id"),
                    asset_id=asset_id,
                    active=active,
                    rationale=self._required_string(args, "rationale"),
                )
            elif name == "sync_skills":
                self._reject_unknown(args, {"transaction_id_prefix"})
                prefix = self._required_string(
                    args,
                    "transaction_id_prefix",
                )
                if len(prefix) > 64:
                    raise ValueError("transaction_id_prefix_too_long")
                result = self._invoke(
                    "synchronize_managed_skill_projections",
                    transaction_id_prefix=prefix,
                )
            else:
                return self._error("tool_not_found", tool=name)
        except CapabilityUnavailable as exc:
            return self._error(
                "capability_unavailable",
                operation=str(exc),
            )
        except UnsupportedLocale:
            try:
                manifest = self._invoke("locale_registry")
                available = manifest.get("available_locales", ())
            except Exception:
                available = ()
            return self._error(
                "unsupported_locale",
                available_locales=available,
            )
        except (KeyError, ValueError):
            return self._error("invalid_arguments")
        except TypeError:
            return self._error("invalid_service_result")
        except Exception:
            return self._error("service_error")
        return {"ok": True, "result": result}

    @staticmethod
    def _require_no_arguments(arguments: Mapping[str, object]) -> None:
        if arguments:
            raise ValueError("arguments_not_allowed")

    @staticmethod
    def _reject_unknown(
        arguments: Mapping[str, object],
        allowed: set[str],
    ) -> None:
        if set(arguments) - allowed:
            raise ValueError("unknown_argument")

    @staticmethod
    def _required_string(
        arguments: Mapping[str, object],
        key: str,
    ) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key}_required")
        return value

    @staticmethod
    def _optional_string(
        arguments: Mapping[str, object],
        key: str,
        default: str,
    ) -> str:
        value = arguments.get(key, default)
        if not isinstance(value, str):
            raise ValueError(f"{key}_must_be_string")
        return value

    @staticmethod
    def _required_boolean(
        arguments: Mapping[str, object],
        key: str,
    ) -> bool:
        value = arguments.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"{key}_required")
        return value

    @staticmethod
    def _bounded_integer(
        arguments: Mapping[str, object],
        key: str,
        *,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        value = arguments.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
            or value > maximum
        ):
            raise ValueError(f"invalid_{key}")
        return value

    @classmethod
    def _page_arguments(
        cls,
        arguments: Mapping[str, object],
        *,
        default_limit: int,
        extra_keys: set[str] | None = None,
    ) -> tuple[int, int]:
        cls._reject_unknown(
            arguments,
            {"offset", "limit", *(extra_keys or set())},
        )
        return (
            cls._bounded_integer(
                arguments,
                "offset",
                default=0,
                minimum=0,
                maximum=MAX_OFFSET,
            ),
            cls._bounded_integer(
                arguments,
                "limit",
                default=default_limit,
                minimum=1,
                maximum=MAX_PAGE_LIMIT,
            ),
        )

    @classmethod
    def _catalog_arguments(
        cls,
        arguments: Mapping[str, object],
    ) -> dict[str, object]:
        cls._reject_unknown(
            arguments,
            {
                "locale",
                "query",
                "status",
                "time",
                "sort",
                "offset",
                "limit",
            },
        )
        locale = cls._optional_string(arguments, "locale", "en")
        query = cls._optional_string(arguments, "query", "")
        status = cls._optional_string(arguments, "status", "all")
        time_filter = cls._optional_string(arguments, "time", "all")
        sort = cls._optional_string(arguments, "sort", "recent")
        if status not in CATALOG_STATUSES:
            raise ValueError("invalid_status")
        if time_filter not in CATALOG_TIME_FILTERS:
            raise ValueError("invalid_time")
        if sort not in CATALOG_SORTS:
            raise ValueError("invalid_sort")
        offset, limit = cls._page_arguments(
            arguments,
            default_limit=DEFAULT_CATALOG_LIMIT,
            extra_keys={"locale", "query", "status", "time", "sort"},
        )
        return {
            "locale": locale,
            "query": query,
            "status": status,
            "time_filter": time_filter,
            "sort": sort,
            "offset": offset,
            "limit": limit,
        }

    @staticmethod
    def _error(code: str, **detail: object) -> dict[str, object]:
        return {"ok": False, "error": {"code": code, **detail}}


__all__ = ["MattersMCP", "TOOLS"]
