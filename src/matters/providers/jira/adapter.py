"""Capability-gated, read-only Jira-to-ProviderEnvelope adapter.

No network client is embedded here. A discovered and explicitly authorized
read function must be injected after the synthetic gate.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from matters.authorization.coverage import (
    AuthorizationCoverage,
    AuthorizationError,
)
from matters.providers.base import (
    ExternalReference,
    ProviderEnvelope,
    ProviderWriteForbidden,
)
from matters.providers.jira.contracts import JiraAuthorizationManifest


FetchPage = Callable[[Sequence[str], str], Mapping[str, Any]]


class JiraReadOnlyAdapter:
    provider_id = "jira"

    def __init__(
        self,
        fetch_page: FetchPage,
        *,
        authorization: JiraAuthorizationManifest,
        g8_current: bool,
        authorization_owner: AuthorizationCoverage | None = None,
        as_of: datetime | None = None,
        max_pages: int = 100,
    ):
        if not g8_current:
            raise AuthorizationError("g8_not_current")
        if authorization is None:
            raise AuthorizationError("explicit_authorization_missing")
        blockers = authorization.blockers(as_of=as_of)
        if blockers:
            raise AuthorizationError(",".join(blockers))
        self._fetch_page = fetch_page
        self._authorization = authorization
        self._scope = authorization.to_scope()
        self._authorization_owner = (
            authorization_owner or AuthorizationCoverage()
        )
        self._as_of = as_of
        self._max_pages = max_pages

    def read(
        self,
        *,
        object_ids: Sequence[str],
        cursor: str = "",
        object_types: Sequence[str] = ("issue",),
    ) -> tuple[ProviderEnvelope, ...]:
        if not object_ids:
            return ()
        requested_ids = tuple(dict.fromkeys(str(item) for item in object_ids))
        requested_types = tuple(
            dict.fromkeys(str(item) for item in object_types)
        )
        self._authorization_owner.assert_read_allowed(
            self._scope,
            provider=self.provider_id,
            object_ids=requested_ids,
            object_types=requested_types,
            instance_ref_hash=self._authorization.instance_ref_hash,
            as_of=self._as_of,
            require_explicit_boundary=True,
        )
        envelopes: list[ProviderEnvelope] = []
        next_cursor = cursor
        pages = 0
        while True:
            pages += 1
            if pages > self._max_pages:
                raise RuntimeError("pagination boundary exceeded")
            page = self._fetch_page(tuple(object_ids), next_cursor)
            denied = tuple(str(item) for item in page.get("denied_fields", ()))
            coverage = str(page.get("coverage", "complete"))
            if denied and coverage == "complete":
                coverage = "partial"
            page_cursor = str(page.get("next_cursor", ""))
            for row in page.get("objects", ()):
                external_id = str(row["external_id"])
                object_type = str(row.get("object_type", "issue"))
                authorization_object_id = str(
                    row.get("authorization_object_id", external_id)
                )
                if authorization_object_id not in requested_ids:
                    raise AuthorizationError("returned_object_outside_scope")
                if (
                    object_type not in self._scope.object_types
                    or object_type not in requested_types
                ):
                    raise AuthorizationError("returned_object_type_outside_scope")
                payload = dict(row.get("payload", row))
                envelopes.append(
                    ProviderEnvelope(
                        provider="jira",
                        external_id=external_id,
                        object_type=object_type,
                        payload=payload,
                        coverage=coverage,
                        cursor=page_cursor,
                        denied_fields=denied,
                        references=(
                            ExternalReference("jira", external_id, object_type),
                        ),
                        metadata={
                            "page": pages,
                            "authorization_scope_id": self._scope.scope_id,
                            "authorization_object_id": authorization_object_id,
                        },
                    )
                )
            if not page_cursor:
                break
            next_cursor = page_cursor
        return tuple(envelopes)

    @staticmethod
    def write(*_args, **_kwargs) -> None:
        raise ProviderWriteForbidden("Jira writes are forbidden")


__all__ = ["JiraReadOnlyAdapter"]
