"""In-process MCP adapter for the autonomous Matter object browser."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping

from matters.application.maintenance_orchestration import MaintenanceRunRequest
from matters.presentation.localization import UnsupportedLocale


CATALOG_STATUSES = ("all", "planned", "in_progress", "completed")
CATALOG_TIME_FILTERS = ("all",)
CATALOG_SORTS = ("activity",)
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
            "start_year": {
                "type": "string",
                "pattern": "^(all|[0-9]{4})$",
            },
            "people": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "maxItems": 50,
            },
            "relationships": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "maxItems": 50,
            },
            "topic_types": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "maxItems": 50,
            },
            "source_types": {
                "type": "array",
                "items": {"type": "string", "maxLength": 200},
                "maxItems": 50,
            },
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
        "name": "list_source_groups",
        "description": (
            "Return one bounded path-free page of current source groups."
        ),
        "inputSchema": _object_schema(
            {
                **_page_schema()["properties"],
                "query": {"type": "string"},
            }
        ),
    },
    {
        "name": "get_source_group",
        "description": (
            "Return one bounded path-free source group and its members."
        ),
        "inputSchema": _object_schema(
            {
                "group_id": {"type": "string", "minLength": 1},
                "member_offset": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_OFFSET,
                },
                "member_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                },
            },
            required=("group_id",),
        ),
    },
    {
        "name": "rebase_source_groups",
        "description": (
            "Repair one bounded page of the rebuildable SourceGroup index."
        ),
        "inputSchema": _object_schema(
            {
                "after_object_id": {"type": "string"},
                "after_scope_id": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                },
            }
        ),
    },
    {
        "name": "get_matter_graph",
        "description": (
            "Return one bounded current SituationGraph page for a Matter."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "locale": {"type": "string"},
                "continuation": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                },
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "get_node_quick_view",
        "description": (
            "Return the single-layer quick view for one SituationGraph node."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "node_id": {"type": "string", "minLength": 1},
                "locale": {"type": "string"},
            },
            required=("matter_id", "node_id"),
        ),
    },
    {
        "name": "get_world_model",
        "description": (
            "Return one bounded advisory World Model page for a Matter."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "locale": {"type": "string"},
                "continuation": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                },
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "list_model_contracts",
        "description": (
            "Return one bounded functional map of Matters model owners and "
            "supported AI operations."
        ),
        "inputSchema": _object_schema(
            {
                "purpose": {"type": "string", "maxLength": 500},
                "related_to": {"type": "string", "maxLength": 200},
                **_page_schema()["properties"],
            }
        ),
    },
    {
        "name": "get_model_contract",
        "description": "Return one exact Matters functional-owner contract.",
        "inputSchema": _object_schema(
            {"model_id": {"type": "string", "minLength": 1, "maxLength": 200}},
            required=("model_id",),
        ),
    },
    {
        "name": "get_situation_context",
        "description": (
            "Return one bounded, modality-aware Matter context packet for AI."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "locale": {"type": "string"},
                "graph_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                },
                "world_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_LIMIT,
                },
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "get_ai_history",
        "description": (
            "Return bounded Matter timeline, user-observation, prediction-"
            "feedback, and correction history."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "locale": {"type": "string"},
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_OFFSET,
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "list_pending_ai_feedback",
        "description": (
            "Return one bounded page of append-only AI observations still "
            "waiting for their original owner."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                **_page_schema()["properties"],
            },
            required=("matter_id",),
        ),
    },
    {
        "name": "record_user_observation",
        "description": (
            "Append one minimized reported user observation for later "
            "original-owner validation; this is not a correction."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "observation_kind": {
                    "type": "string",
                    "enum": [
                        "fact",
                        "event",
                        "state",
                        "outcome",
                        "relationship",
                        "source_gap",
                        "other",
                    ],
                },
                "statement": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4_000,
                },
                "observed_at": {"type": "string", "minLength": 1},
                "source_ref": {"type": "string", "maxLength": 240},
            },
            required=(
                "matter_id",
                "observation_kind",
                "statement",
                "observed_at",
            ),
        ),
    },
    {
        "name": "record_prediction_feedback",
        "description": (
            "Compare one frozen prediction with later licensed evidence while "
            "preserving both records."
        ),
        "inputSchema": _object_schema(
            {
                "matter_id": {"type": "string", "minLength": 1},
                "advisory_id": {"type": "string", "minLength": 1},
                "disposition": {
                    "type": "string",
                    "enum": ["confirmed", "contradicted", "unresolved"],
                },
                "observed_at": {"type": "string", "minLength": 1},
                "observation_statement": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4_000,
                },
                "observation_evidence_ids": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1,
                    "maxItems": MAX_PAGE_LIMIT,
                },
            },
            required=(
                "matter_id",
                "advisory_id",
                "disposition",
                "observed_at",
                "observation_statement",
                "observation_evidence_ids",
            ),
        ),
    },
    {
        "name": "report_model_miss",
        "description": (
            "Append one bounded software/model gap for the development pipeline; "
            "runtime code and rules are never self-edited."
        ),
        "inputSchema": _object_schema(
            {
                "failure_class": {"type": "string", "minLength": 1},
                "expected_behavior": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4_000,
                },
                "observed_behavior": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4_000,
                },
                "model_path": {"type": "string", "minLength": 1},
                "private_evidence_handle": {
                    "type": "string",
                    "pattern": "^private-evidence:",
                },
                "current_runtime_disposition": {
                    "type": "string",
                    "enum": ["partial", "blocked"],
                },
            },
            required=(
                "failure_class",
                "expected_behavior",
                "observed_behavior",
                "model_path",
                "private_evidence_handle",
                "current_runtime_disposition",
            ),
        ),
    },
    {
        "name": "get_coverage",
        "description": "Return aggregate object-coverage and worker progress.",
        "inputSchema": _object_schema(),
    },
    {
        "name": "get_stage_audit",
        "description": (
            "Return one bounded read-only page showing each object's exact "
            "stage state and first current coverage gap."
        ),
        "inputSchema": _object_schema(
            {
                **_page_schema()["properties"],
                "object_kind": {
                    "type": "string",
                    "enum": ["occurrence", "matter"],
                },
                "surface_id": {"type": "string"},
                "surface_status": {"type": "string"},
                "owner_id": {"type": "string"},
                "failure_class": {"type": "string"},
                "freshness": {"type": "string"},
                "ui_ready": {"type": "boolean"},
            }
        ),
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
        "name": "run_planned_maintenance",
        "description": (
            "Run one model-independent Codex-hosted maintenance plan through "
            "injected private adapters."
        ),
        "inputSchema": _object_schema(
            {
                "run_id": {"type": "string", "minLength": 1},
                "authorization_identity": {
                    "type": "string",
                    "minLength": 1,
                },
                "inventory_identity": {
                    "type": "string",
                    "minLength": 1,
                },
                "coverage_identity": {
                    "type": "string",
                    "minLength": 1,
                },
                "changed_object_ids": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "maxItems": 10_000,
                },
                "resource_budget": _object_schema(
                    {
                        "max_tasks": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10_000,
                        },
                        "max_retries_per_task": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                        },
                        "max_concurrency": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 32,
                        },
                    }
                ),
            },
            required=(
                "run_id",
                "authorization_identity",
                "inventory_identity",
                "coverage_identity",
                "changed_object_ids",
            ),
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
            elif name == "list_source_groups":
                self._reject_unknown(args, {"offset", "limit", "query"})
                offset = self._bounded_integer(
                    args,
                    "offset",
                    default=0,
                    minimum=0,
                    maximum=MAX_OFFSET,
                )
                limit = self._bounded_integer(
                    args,
                    "limit",
                    default=50,
                    minimum=1,
                    maximum=MAX_PAGE_LIMIT,
                )
                result = self._invoke(
                    "source_groups",
                    offset=offset,
                    limit=limit,
                    query=self._optional_string(args, "query", ""),
                )
            elif name == "get_source_group":
                self._reject_unknown(
                    args,
                    {"group_id", "member_offset", "member_limit"},
                )
                result = self._invoke(
                    "source_group_detail",
                    group_id=self._required_string(args, "group_id"),
                    member_offset=self._bounded_integer(
                        args,
                        "member_offset",
                        default=0,
                        minimum=0,
                        maximum=MAX_OFFSET,
                    ),
                    member_limit=self._bounded_integer(
                        args,
                        "member_limit",
                        default=100,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                )
            elif name == "rebase_source_groups":
                self._reject_unknown(
                    args,
                    {"after_object_id", "after_scope_id", "limit"},
                )
                result = self._invoke(
                    "rebase_source_group_index",
                    after_object_id=self._optional_string(
                        args,
                        "after_object_id",
                        "",
                    ),
                    after_scope_id=self._optional_string(
                        args,
                        "after_scope_id",
                        "",
                    ),
                    limit=self._bounded_integer(
                        args,
                        "limit",
                        default=500,
                        minimum=1,
                        maximum=500,
                    ),
                )
            elif name == "get_matter_graph":
                self._reject_unknown(
                    args,
                    {"matter_id", "locale", "continuation", "limit"},
                )
                result = self._invoke(
                    "matter_situation_graph",
                    matter_id=self._required_string(args, "matter_id"),
                    locale=self._optional_string(args, "locale", "en"),
                    continuation=self._optional_string(
                        args,
                        "continuation",
                        "",
                    ),
                    limit=self._bounded_integer(
                        args,
                        "limit",
                        default=120,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                )
            elif name == "get_node_quick_view":
                self._reject_unknown(
                    args,
                    {"matter_id", "node_id", "locale"},
                )
                result = self._invoke(
                    "matter_node_quick_view",
                    matter_id=self._required_string(args, "matter_id"),
                    node_id=self._required_string(args, "node_id"),
                    locale=self._optional_string(args, "locale", "en"),
                )
            elif name == "get_world_model":
                self._reject_unknown(
                    args,
                    {"matter_id", "locale", "continuation", "limit"},
                )
                result = self._invoke(
                    "matter_world_model",
                    matter_id=self._required_string(args, "matter_id"),
                    locale=self._optional_string(args, "locale", "en"),
                    continuation=self._optional_string(
                        args,
                        "continuation",
                        "",
                    ),
                    limit=self._bounded_integer(
                        args,
                        "limit",
                        default=50,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                )
            elif name == "list_model_contracts":
                self._reject_unknown(
                    args,
                    {"purpose", "related_to", "offset", "limit"},
                )
                result = self._invoke(
                    "ai_model_contracts",
                    purpose=self._optional_string(args, "purpose", ""),
                    related_to=self._optional_string(
                        args,
                        "related_to",
                        "",
                    ),
                    offset=self._bounded_integer(
                        args,
                        "offset",
                        default=0,
                        minimum=0,
                        maximum=MAX_OFFSET,
                    ),
                    limit=self._bounded_integer(
                        args,
                        "limit",
                        default=50,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                )
            elif name == "get_model_contract":
                self._reject_unknown(args, {"model_id"})
                result = self._invoke(
                    "ai_model_contract",
                    model_id=self._required_string(args, "model_id"),
                )
            elif name == "get_situation_context":
                self._reject_unknown(
                    args,
                    {
                        "matter_id",
                        "locale",
                        "graph_limit",
                        "world_limit",
                    },
                )
                result = self._invoke(
                    "ai_situation_context",
                    matter_id=self._required_string(args, "matter_id"),
                    locale=self._optional_string(args, "locale", "en"),
                    graph_limit=self._bounded_integer(
                        args,
                        "graph_limit",
                        default=80,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                    world_limit=self._bounded_integer(
                        args,
                        "world_limit",
                        default=40,
                        minimum=1,
                        maximum=MAX_PAGE_LIMIT,
                    ),
                )
            elif name == "get_ai_history":
                self._reject_unknown(
                    args,
                    {"matter_id", "locale", "offset", "limit"},
                )
                result = self._invoke(
                    "ai_history",
                    matter_id=self._required_string(args, "matter_id"),
                    locale=self._optional_string(args, "locale", "en"),
                    offset=self._bounded_integer(
                        args,
                        "offset",
                        default=0,
                        minimum=0,
                        maximum=MAX_OFFSET,
                    ),
                    limit=self._bounded_integer(
                        args,
                        "limit",
                        default=50,
                        minimum=1,
                        maximum=50,
                    ),
                )
            elif name == "list_pending_ai_feedback":
                offset, limit = self._page_arguments(
                    args,
                    default_limit=50,
                    extra_keys={"matter_id"},
                )
                result = self._invoke(
                    "pending_ai_feedback",
                    matter_id=self._required_string(args, "matter_id"),
                    offset=offset,
                    limit=limit,
                )
            elif name == "record_user_observation":
                self._reject_unknown(
                    args,
                    {
                        "matter_id",
                        "observation_kind",
                        "statement",
                        "observed_at",
                        "source_ref",
                    },
                )
                observation_kind = self._required_string(
                    args,
                    "observation_kind",
                )
                if observation_kind not in {
                    "fact",
                    "event",
                    "state",
                    "outcome",
                    "relationship",
                    "source_gap",
                    "other",
                }:
                    raise ValueError("observation_kind_invalid")
                result = self._invoke(
                    "record_user_observation",
                    matter_id=self._required_string(args, "matter_id"),
                    observation_kind=observation_kind,
                    statement=self._required_string(args, "statement"),
                    observed_at=self._required_string(args, "observed_at"),
                    source_ref=self._optional_string(
                        args,
                        "source_ref",
                        "",
                    ),
                )
            elif name == "record_prediction_feedback":
                self._reject_unknown(
                    args,
                    {
                        "matter_id",
                        "advisory_id",
                        "disposition",
                        "observed_at",
                        "observation_statement",
                        "observation_evidence_ids",
                    },
                )
                evidence_ids = args.get("observation_evidence_ids")
                disposition = self._required_string(args, "disposition")
                if (
                    disposition
                    not in {"confirmed", "contradicted", "unresolved"}
                    or not isinstance(evidence_ids, list)
                    or not evidence_ids
                    or len(evidence_ids) > MAX_PAGE_LIMIT
                    or any(
                        not isinstance(item, str) or not item.strip()
                        for item in evidence_ids
                    )
                ):
                    raise ValueError("prediction_feedback_schema_invalid")
                result = self._invoke(
                    "record_world_model_feedback",
                    matter_id=self._required_string(args, "matter_id"),
                    advisory_id=self._required_string(args, "advisory_id"),
                    disposition=disposition,
                    observed_at=self._required_string(args, "observed_at"),
                    observation_statement=self._required_string(
                        args,
                        "observation_statement",
                    ),
                    observation_evidence_ids=tuple(evidence_ids),
                )
            elif name == "report_model_miss":
                self._reject_unknown(
                    args,
                    {
                        "failure_class",
                        "expected_behavior",
                        "observed_behavior",
                        "model_path",
                        "private_evidence_handle",
                        "current_runtime_disposition",
                    },
                )
                evidence_handle = self._required_string(
                    args,
                    "private_evidence_handle",
                )
                runtime_disposition = self._required_string(
                    args,
                    "current_runtime_disposition",
                )
                if (
                    not evidence_handle.startswith("private-evidence:")
                    or runtime_disposition not in {"partial", "blocked"}
                ):
                    raise ValueError("model_miss_schema_invalid")
                result = self._invoke(
                    "report_model_miss",
                    failure_class=self._required_string(
                        args,
                        "failure_class",
                    ),
                    expected_behavior=self._required_string(
                        args,
                        "expected_behavior",
                    ),
                    observed_behavior=self._required_string(
                        args,
                        "observed_behavior",
                    ),
                    model_path=self._required_string(args, "model_path"),
                    private_evidence_handle=evidence_handle,
                    current_runtime_disposition=runtime_disposition,
                )
            elif name == "get_coverage":
                self._require_no_arguments(args)
                result = self._invoke("object_coverage_summary")
            elif name == "get_stage_audit":
                object_kind = self._optional_string(
                    args,
                    "object_kind",
                    "",
                )
                if object_kind not in {"", "occurrence", "matter"}:
                    raise ValueError("invalid_object_kind")
                extra_keys = {
                    "object_kind",
                    "surface_id",
                    "surface_status",
                    "owner_id",
                    "failure_class",
                    "freshness",
                    "ui_ready",
                }
                offset, limit = self._page_arguments(
                    args,
                    default_limit=100,
                    extra_keys=extra_keys,
                )
                ui_ready = args.get("ui_ready")
                if ui_ready is not None and not isinstance(ui_ready, bool):
                    raise ValueError("ui_ready must be boolean")
                audit_kwargs: dict[str, Any] = {
                    "offset": offset,
                    "limit": limit,
                    "object_kind": object_kind,
                }
                for key in (
                    "surface_id",
                    "surface_status",
                    "owner_id",
                    "failure_class",
                    "freshness",
                ):
                    if value := self._optional_string(args, key, ""):
                        audit_kwargs[key] = value
                if ui_ready is not None:
                    audit_kwargs["ui_ready"] = ui_ready
                result = self._invoke(
                    "object_stage_audit",
                    **audit_kwargs,
                )
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
            elif name == "run_planned_maintenance":
                self._reject_unknown(
                    args,
                    {
                        "run_id",
                        "authorization_identity",
                        "inventory_identity",
                        "coverage_identity",
                        "changed_object_ids",
                        "resource_budget",
                    },
                )
                changed = args.get("changed_object_ids")
                budget = args.get("resource_budget")
                if not isinstance(changed, list) or (
                    budget is not None and not isinstance(budget, Mapping)
                ):
                    raise ValueError("maintenance_request_schema_invalid")
                request = MaintenanceRunRequest.create(
                    run_id=self._required_string(args, "run_id"),
                    authorization_identity=self._required_string(
                        args,
                        "authorization_identity",
                    ),
                    inventory_identity=self._required_string(
                        args,
                        "inventory_identity",
                    ),
                    coverage_identity=self._required_string(
                        args,
                        "coverage_identity",
                    ),
                    changed_object_ids=tuple(
                        str(item) for item in changed if str(item)
                    ),
                    resource_budget=(
                        {
                            str(key): int(value)
                            for key, value in budget.items()
                        }
                        if isinstance(budget, Mapping)
                        else None
                    ),
                )
                try:
                    result = self._invoke(
                        "run_planned_maintenance",
                        request=request,
                    )
                except RuntimeError as exc:
                    if str(exc).startswith("capability_unavailable:"):
                        raise CapabilityUnavailable(
                            "run_planned_maintenance"
                        ) from exc
                    raise
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
    def _optional_string_list(
        arguments: Mapping[str, object],
        key: str,
    ) -> tuple[str, ...]:
        raw = arguments.get(key, ())
        if (
            isinstance(raw, (str, bytes))
            or not isinstance(raw, (list, tuple))
            or len(raw) > 50
        ):
            raise ValueError(f"invalid_{key}")
        values = []
        for item in raw:
            if (
                not isinstance(item, str)
                or not item.strip()
                or len(item) > 200
            ):
                raise ValueError(f"invalid_{key}")
            values.append(item.strip())
        return tuple(dict.fromkeys(values))

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
                "start_year",
                "people",
                "relationships",
                "topic_types",
                "source_types",
                "offset",
                "limit",
            },
        )
        locale = cls._optional_string(arguments, "locale", "en")
        query = cls._optional_string(arguments, "query", "")
        status = cls._optional_string(arguments, "status", "all")
        time_filter = cls._optional_string(arguments, "time", "all")
        sort = cls._optional_string(arguments, "sort", "activity")
        start_year = cls._optional_string(arguments, "start_year", "all")
        if status not in CATALOG_STATUSES:
            raise ValueError("invalid_status")
        if time_filter not in CATALOG_TIME_FILTERS:
            raise ValueError("invalid_time")
        if sort not in CATALOG_SORTS:
            raise ValueError("invalid_sort")
        if (
            start_year != "all"
            and (len(start_year) != 4 or not start_year.isdigit())
        ):
            raise ValueError("invalid_start_year")
        offset, limit = cls._page_arguments(
            arguments,
            default_limit=DEFAULT_CATALOG_LIMIT,
            extra_keys={
                "locale",
                "query",
                "status",
                "time",
                "sort",
                "start_year",
                "people",
                "relationships",
                "topic_types",
                "source_types",
            },
        )
        return {
            "locale": locale,
            "query": query,
            "status": status,
            "time_filter": time_filter,
            "sort": sort,
            "start_year": start_year,
            "people": cls._optional_string_list(arguments, "people"),
            "relationships": cls._optional_string_list(
                arguments,
                "relationships",
            ),
            "topic_types": cls._optional_string_list(
                arguments,
                "topic_types",
            ),
            "source_types": cls._optional_string_list(
                arguments,
                "source_types",
            ),
            "offset": offset,
            "limit": limit,
        }

    @staticmethod
    def _error(code: str, **detail: object) -> dict[str, object]:
        return {"ok": False, "error": {"code": code, **detail}}


__all__ = ["MattersMCP", "TOOLS"]
