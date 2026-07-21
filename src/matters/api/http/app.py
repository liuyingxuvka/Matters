"""Bounded HTTP transport for the autonomous Matter object browser."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, unquote

from matters.application.maintenance_orchestration import MaintenanceRunRequest
from matters.presentation.localization import UnsupportedLocale


MAX_BODY_BYTES = 2 * 1024 * 1024
StartResponse = Callable[[str, list[tuple[str, str]]], object]


class CapabilityUnavailable(RuntimeError):
    pass


class RequestError(ValueError):
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


def _response(
    start_response: StartResponse,
    status: str,
    payload: Mapping[str, object],
    *,
    extra_headers: Iterable[tuple[str, str]] = (),
) -> list[bytes]:
    body = json.dumps(
        _jsonable(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            *extra_headers,
        ],
    )
    return [body]


def _binary_response(
    start_response: StartResponse,
    content: bytes,
    media_type: str,
) -> list[bytes]:
    start_response(
        "200 OK",
        [
            ("Content-Type", media_type),
            ("Content-Length", str(len(content))),
            ("Cache-Control", "private, max-age=300"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Security-Policy", "default-src 'none'"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [content]


def _error(
    start_response: StartResponse,
    status: str,
    code: str,
    *,
    operation: str = "",
    detail: Mapping[str, object] | None = None,
    extra_headers: Iterable[tuple[str, str]] = (),
) -> list[bytes]:
    error: dict[str, object] = {"code": code}
    if operation:
        error["operation"] = operation
    if detail:
        error.update(detail)
    return _response(
        start_response,
        status,
        {"ok": False, "error": error},
        extra_headers=extra_headers,
    )


def _read_json(environ: Mapping[str, object]) -> Mapping[str, object]:
    raw_length = str(environ.get("CONTENT_LENGTH", "") or "0")
    try:
        length = int(raw_length)
    except ValueError as exc:
        raise RequestError("invalid_content_length") from exc
    if length < 0 or length > MAX_BODY_BYTES:
        raise RequestError("body_too_large")
    stream = environ.get("wsgi.input")
    if stream is None:
        raise RequestError("missing_body")
    raw = stream.read(length) if length else b""
    if not raw:
        raise RequestError("missing_body")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestError("invalid_json") from exc
    if not isinstance(payload, Mapping):
        raise RequestError("object_body_required")
    return payload


def _planned_maintenance_request(
    payload: Mapping[str, object],
) -> MaintenanceRunRequest:
    allowed = {
        "run_id",
        "authorization_identity",
        "inventory_identity",
        "coverage_identity",
        "changed_object_ids",
        "resource_budget",
    }
    if any(str(key) not in allowed for key in payload):
        raise RequestError("maintenance_request_unknown_fields")
    changed = payload.get("changed_object_ids", ())
    budget = payload.get("resource_budget")
    if not isinstance(changed, list) or (
        budget is not None and not isinstance(budget, Mapping)
    ):
        raise RequestError("maintenance_request_schema_invalid")
    try:
        return MaintenanceRunRequest.create(
            run_id=str(payload.get("run_id", "")),
            authorization_identity=str(
                payload.get("authorization_identity", "")
            ),
            inventory_identity=str(payload.get("inventory_identity", "")),
            coverage_identity=str(payload.get("coverage_identity", "")),
            changed_object_ids=tuple(str(item) for item in changed),
            resource_budget=(
                {str(key): int(value) for key, value in budget.items()}
                if isinstance(budget, Mapping)
                else None
            ),
        )
    except (TypeError, ValueError) as exc:
        raise RequestError("maintenance_request_schema_invalid") from exc


def _query(environ: Mapping[str, object]) -> Mapping[str, list[str]]:
    return parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)


def _int_query(
    query: Mapping[str, list[str]],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(query.get(key, [str(default)])[0])
    except ValueError as exc:
        raise RequestError("invalid_page_bounds") from exc
    if value < minimum or value > maximum:
        raise RequestError("invalid_page_bounds")
    return value


def _int_value(
    raw: object,
    default: int,
    *,
    minimum: int,
    maximum: int,
    error: str = "invalid_page_bounds",
) -> int:
    try:
        value = int(default if raw is None else raw)
    except (TypeError, ValueError) as exc:
        raise RequestError(error) from exc
    if value < minimum or value > maximum:
        raise RequestError(error)
    return value


def _one(query: Mapping[str, list[str]], key: str, default: str) -> str:
    return str(query.get(key, [default])[0])


def _many(
    query: Mapping[str, list[str]],
    key: str,
    *,
    maximum: int = 50,
) -> tuple[str, ...]:
    values = tuple(
        value
        for raw in query.get(key, ())
        if (value := str(raw).strip())
    )
    if len(values) > maximum or any(len(value) > 200 for value in values):
        raise RequestError("invalid_filter_values")
    return tuple(dict.fromkeys(values))


def _bool_query(
    query: Mapping[str, list[str]],
    key: str,
    default: bool,
) -> bool:
    raw = str(
        query.get(key, ["true" if default else "false"])[0]
    ).strip().casefold()
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise RequestError("invalid_boolean_query")


def _matter_path(path: str) -> tuple[str, str] | None:
    prefix = "/api/matters/"
    if not path.startswith(prefix):
        return None
    remainder = path[len(prefix) :]
    if not remainder:
        return None
    if "/" in remainder:
        matter_id, suffix = remainder.split("/", 1)
    else:
        matter_id, suffix = remainder, ""
    return unquote(matter_id), suffix


def _source_group_path(path: str) -> str | None:
    prefix = "/api/source-groups/"
    if not path.startswith(prefix):
        return None
    group_id = unquote(path[len(prefix) :])
    if not group_id or "/" in group_id:
        return None
    return group_id


class MattersHTTP:
    """Transport adapter; all state ownership remains in MatterService."""

    def __init__(self, service: object):
        self._service = service

    def _invoke(self, method_name: str, /, **kwargs: object) -> Any:
        method = getattr(self._service, method_name, None)
        if not callable(method):
            raise CapabilityUnavailable(method_name)
        return method(**kwargs)

    def __call__(
        self,
        environ: Mapping[str, object],
        start_response: StartResponse,
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        try:
            if method == "GET" and path in {"/health", "/api/capabilities"}:
                result = self._invoke("capabilities")
            elif method == "GET" and path == "/api/locales":
                result = self._invoke("locale_registry")
            elif method == "GET" and path == "/api/coverage":
                result = self._invoke("object_coverage_summary")
            elif method == "GET" and path == "/api/coverage/audit":
                query = _query(environ)
                object_kind = _one(query, "object_kind", "")
                if object_kind not in {"", "occurrence", "matter"}:
                    raise RequestError("invalid_object_kind")
                ui_ready = (
                    _bool_query(query, "ui_ready", False)
                    if "ui_ready" in query
                    else None
                )
                audit_kwargs: dict[str, Any] = {
                    "offset": _int_query(
                        query,
                        "offset",
                        0,
                        minimum=0,
                        maximum=10_000_000,
                    ),
                    "limit": _int_query(
                        query,
                        "limit",
                        100,
                        minimum=1,
                        maximum=200,
                    ),
                    "object_kind": object_kind,
                }
                if "surface_only" in query:
                    audit_kwargs["surface_only"] = _bool_query(
                        query,
                        "surface_only",
                        False,
                    )
                for key in (
                    "surface_id",
                    "surface_status",
                    "owner_id",
                    "failure_class",
                    "freshness",
                ):
                    if value := _one(query, key, ""):
                        audit_kwargs[key] = value
                if ui_ready is not None:
                    audit_kwargs["ui_ready"] = ui_ready
                result = self._invoke(
                    "object_stage_audit",
                    **audit_kwargs,
                )
            elif method == "GET" and path == "/api/source-groups":
                query = _query(environ)
                result = self._invoke(
                    "source_groups",
                    offset=_int_query(
                        query,
                        "offset",
                        0,
                        minimum=0,
                        maximum=10_000_000,
                    ),
                    limit=_int_query(
                        query,
                        "limit",
                        50,
                        minimum=1,
                        maximum=200,
                    ),
                    query=_one(query, "query", ""),
                )
            elif method == "POST" and path == "/api/source-groups/rebase":
                payload = _read_json(environ)
                result = self._invoke(
                    "rebase_source_group_index",
                    after_object_id=str(
                        payload.get("after_object_id", "")
                    ),
                    after_scope_id=str(
                        payload.get("after_scope_id", "")
                    ),
                    limit=_int_value(
                        payload.get("limit", 500),
                        500,
                        minimum=1,
                        maximum=500,
                        error="invalid_source_group_rebase_limit",
                    ),
                )
            elif (
                method == "GET"
                and (source_group_id := _source_group_path(path)) is not None
            ):
                query = _query(environ)
                result = self._invoke(
                    "source_group_detail",
                    group_id=source_group_id,
                    member_offset=_int_query(
                        query,
                        "member_offset",
                        0,
                        minimum=0,
                        maximum=10_000_000,
                    ),
                    member_limit=_int_query(
                        query,
                        "member_limit",
                        100,
                        minimum=1,
                        maximum=200,
                    ),
                )
            elif method == "GET" and path in {"/api/browser", "/api/catalog"}:
                query = _query(environ)
                kwargs = {
                    "locale": _one(query, "locale", "en"),
                    "query": _one(query, "query", ""),
                    "status": _one(query, "status", "all"),
                    "time_filter": _one(query, "time", "all"),
                    "sort": _one(query, "sort", "activity"),
                    "offset": _int_query(
                        query,
                        "offset",
                        0,
                        minimum=0,
                        maximum=10_000_000,
                    ),
                    "limit": _int_query(
                        query,
                        "limit",
                        60,
                        minimum=1,
                        maximum=200,
                    ),
                    "root_only": _bool_query(
                        query,
                        "root_only",
                        True,
                    ),
                    "start_year": _one(query, "start_year", "all"),
                    "people": _many(query, "people"),
                    "relationships": _many(query, "relationships"),
                    "topic_types": _many(query, "topic_type"),
                    "source_types": _many(query, "source_type"),
                }
                result = self._invoke(
                    (
                        "object_browser_projection"
                        if path == "/api/browser"
                        else "object_catalog_page"
                    ),
                    **kwargs,
                )
            elif method == "GET" and path == "/api/analysis/packages":
                query = _query(environ)
                result = self._invoke(
                    "pending_analysis_packages",
                    offset=_int_query(
                        query,
                        "offset",
                        0,
                        minimum=0,
                        maximum=10_000_000,
                    ),
                    limit=_int_query(
                        query,
                        "limit",
                        20,
                        minimum=1,
                        maximum=200,
                    ),
                )
            elif method == "POST" and path == "/api/analysis/results":
                payload = _read_json(environ)
                returned = payload.get("result")
                if not isinstance(returned, Mapping):
                    raise RequestError("analysis_result_required")
                result = self._invoke(
                    "import_autonomous_result",
                    package_id=str(payload.get("package_id", "")),
                    provider_id=str(payload.get("provider_id", "")),
                    provider_version=str(payload.get("provider_version", "")),
                    result=returned,
                )
            elif method == "POST" and path == "/api/maintenance/run":
                payload = _read_json(environ)
                result = self._invoke(
                    "run_maintenance_cycle",
                    limit=int(payload.get("limit", 20)),
                )
            elif (
                method == "POST"
                and path == "/api/maintenance/orchestration/run"
            ):
                payload = _read_json(environ)
                try:
                    result = self._invoke(
                        "run_planned_maintenance",
                        request=_planned_maintenance_request(payload),
                    )
                except RuntimeError as exc:
                    if str(exc).startswith("capability_unavailable:"):
                        raise CapabilityUnavailable(
                            "run_planned_maintenance"
                        ) from exc
                    raise
            elif method == "GET" and path.startswith("/api/visuals/"):
                token = unquote(path.removeprefix("/api/visuals/"))
                query = _query(environ)
                content, media_type = self._invoke(
                    "resolve_visual_preview",
                    preview_token=token,
                    hero=_one(query, "size", "thumbnail") == "hero",
                )
                return _binary_response(start_response, content, media_type)
            elif method == "GET" and path.startswith("/api/heroes/"):
                token = unquote(path.removeprefix("/api/heroes/"))
                content, media_type = self._invoke(
                    "resolve_generated_hero",
                    preview_token=token,
                )
                return _binary_response(start_response, content, media_type)
            elif (parsed := _matter_path(path)) is not None:
                matter_id, suffix = parsed
                query = _query(environ)
                if method == "GET" and suffix == "":
                    result = self._invoke(
                        "matter_detail",
                        matter_id=matter_id,
                        locale=_one(query, "locale", "en"),
                    )
                elif method == "GET" and suffix == "evidence":
                    result = self._invoke(
                        "matter_evidence",
                        matter_id=matter_id,
                        offset=_int_query(
                            query,
                            "offset",
                            0,
                            minimum=0,
                            maximum=10_000_000,
                        ),
                        limit=_int_query(
                            query,
                            "limit",
                            50,
                            minimum=1,
                            maximum=200,
                        ),
                    )
                elif method == "GET" and suffix == "children":
                    result = self._invoke(
                        "matter_children",
                        matter_id=matter_id,
                        locale=_one(query, "locale", "en"),
                        offset=_int_query(
                            query,
                            "offset",
                            0,
                            minimum=0,
                            maximum=10_000_000,
                        ),
                        limit=_int_query(
                            query,
                            "limit",
                            50,
                            minimum=1,
                            maximum=200,
                        ),
                    )
                elif method == "GET" and suffix == "work-items":
                    result = self._invoke(
                        "matter_work_items",
                        matter_id=matter_id,
                        offset=_int_query(
                            query,
                            "offset",
                            0,
                            minimum=0,
                            maximum=10_000_000,
                        ),
                        limit=_int_query(
                            query,
                            "limit",
                            50,
                            minimum=1,
                            maximum=200,
                        ),
                    )
                elif method == "GET" and suffix == "graph":
                    result = self._invoke(
                        "matter_situation_graph",
                        matter_id=matter_id,
                        locale=_one(query, "locale", "en"),
                        continuation=_one(query, "continuation", ""),
                        limit=_int_query(
                            query,
                            "limit",
                            120,
                            minimum=1,
                            maximum=200,
                        ),
                    )
                elif (
                    method == "GET"
                    and suffix.startswith("nodes/")
                    and suffix.endswith("/quick-view")
                ):
                    node_id = unquote(
                        suffix[
                            len("nodes/") : -len("/quick-view")
                        ]
                    )
                    if not node_id or "/" in node_id:
                        raise RequestError("invalid_node_id")
                    result = self._invoke(
                        "matter_node_quick_view",
                        matter_id=matter_id,
                        node_id=node_id,
                        locale=_one(query, "locale", "en"),
                    )
                elif method == "GET" and suffix == "world-model":
                    result = self._invoke(
                        "matter_world_model",
                        matter_id=matter_id,
                        locale=_one(query, "locale", "en"),
                        continuation=_one(query, "continuation", ""),
                        limit=_int_query(
                            query,
                            "limit",
                            50,
                            minimum=1,
                            maximum=200,
                        ),
                    )
                elif method == "POST" and suffix == "world-model/feedback":
                    payload = _read_json(environ)
                    evidence_ids = payload.get("observation_evidence_ids", ())
                    if not isinstance(evidence_ids, list):
                        raise RequestError("invalid_observation_evidence_ids")
                    result = self._invoke(
                        "record_world_model_feedback",
                        matter_id=matter_id,
                        advisory_id=str(payload.get("advisory_id", "")),
                        disposition=str(payload.get("disposition", "")),
                        observed_at=str(payload.get("observed_at", "")),
                        observation_statement=str(
                            payload.get("observation_statement", "")
                        ),
                        observation_evidence_ids=tuple(
                            str(item) for item in evidence_ids
                        ),
                    )
                elif method == "POST" and suffix == "corrections":
                    payload = _read_json(environ)
                    result = self._invoke(
                        "submit_matter_correction",
                        matter_id=matter_id,
                        rationale=str(payload.get("rationale", "")),
                        field_name=str(payload.get("field_name", "")),
                        corrected_value=str(payload.get("corrected_value", "")),
                    )
                else:
                    return _error(start_response, "404 Not Found", "not_found")
            elif path in {
                "/health",
                "/api/capabilities",
                "/api/locales",
                "/api/coverage",
                "/api/coverage/audit",
                "/api/source-groups",
                "/api/source-groups/rebase",
                "/api/browser",
                "/api/catalog",
                "/api/analysis/packages",
                "/api/analysis/results",
                "/api/maintenance/run",
                "/api/maintenance/orchestration/run",
            }:
                allowed = (
                    "POST"
                    if path
                    in {
                        "/api/analysis/results",
                        "/api/maintenance/run",
                        "/api/maintenance/orchestration/run",
                        "/api/source-groups/rebase",
                    }
                    else "GET"
                )
                return _error(
                    start_response,
                    "405 Method Not Allowed",
                    "method_not_allowed",
                    extra_headers=(("Allow", allowed),),
                )
            else:
                return _error(start_response, "404 Not Found", "not_found")
        except CapabilityUnavailable as exc:
            return _error(
                start_response,
                "501 Not Implemented",
                "capability_unavailable",
                operation=str(exc),
            )
        except RequestError as exc:
            return _error(start_response, "400 Bad Request", str(exc))
        except UnsupportedLocale:
            manifest = _jsonable(self._invoke("locale_registry"))
            return _error(
                start_response,
                "422 Unprocessable Entity",
                "unsupported_locale",
                detail={
                    "available_locales": manifest.get("available_locales", ())
                },
            )
        except KeyError:
            return _error(start_response, "404 Not Found", "object_not_found")
        except (TypeError, UnicodeError, ValueError):
            return _error(
                start_response,
                "422 Unprocessable Entity",
                "service_rejected_request",
            )
        except Exception:
            return _error(
                start_response,
                "500 Internal Server Error",
                "service_error",
            )
        return _response(
            start_response,
            "200 OK",
            {"ok": True, "result": _jsonable(result)},
        )


def create_application(service: object) -> MattersHTTP:
    return MattersHTTP(service)


def application(
    _environ: Mapping[str, object],
    start_response: StartResponse,
) -> list[bytes]:
    return _error(
        start_response,
        "503 Service Unavailable",
        "service_not_injected",
    )


__all__ = ["MattersHTTP", "application", "create_application"]
