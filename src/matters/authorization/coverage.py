"""C1: authorization and explicit coverage decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections.abc import Sequence

from matters.authorization.scopes import AuthorizationScope
from matters.providers.base import ProviderEnvelope


@dataclass(frozen=True)
class CoverageReceipt:
    scope_id: str
    provider: str
    object_id: str
    status: str
    cursor: str = ""
    denied_fields: tuple[str, ...] = ()
    reason: str = ""

    @property
    def complete(self) -> bool:
        return self.status == "complete"


class AuthorizationError(PermissionError):
    pass


class AuthorizationCoverage:
    """The only owner of authorization and coverage decisions."""

    def assert_read_allowed(
        self,
        scope: AuthorizationScope,
        *,
        provider: str,
        object_ids: Sequence[str],
        object_types: Sequence[str],
        instance_ref_hash: str,
        as_of: datetime | None = None,
        require_explicit_boundary: bool = False,
    ) -> None:
        """Fail before transport when any requested read is outside the grant."""

        if not scope.current(as_of):
            reason = (
                "authorization_revoked"
                if not scope.active
                else "authorization_expired"
            )
            raise AuthorizationError(reason)
        if require_explicit_boundary:
            gaps = scope.explicit_read_boundary_gaps()
            if gaps:
                raise AuthorizationError(
                    "authorization_boundary_incomplete:" + ",".join(gaps)
                )
        if provider != scope.provider:
            raise AuthorizationError("provider_outside_scope")
        if instance_ref_hash != scope.instance_ref_hash:
            raise AuthorizationError("instance_outside_scope")
        if not object_ids:
            raise AuthorizationError("object_scope_empty")
        if not object_types:
            raise AuthorizationError("object_type_scope_empty")
        outside_ids = sorted(set(object_ids) - set(scope.object_ids))
        if outside_ids:
            raise AuthorizationError("outside_scope")
        outside_types = sorted(set(object_types) - set(scope.object_types))
        if outside_types:
            raise AuthorizationError("object_type_outside_scope")
        if scope.operations != frozenset({"read"}):
            raise AuthorizationError("read_only_operation_required")

    def authorize_envelope(
        self,
        scope: AuthorizationScope,
        envelope: ProviderEnvelope,
    ) -> CoverageReceipt:
        if not scope.active:
            raise AuthorizationError("authorization_revoked")
        if not scope.covers(envelope.provider, envelope.external_id, "read"):
            raise AuthorizationError("outside_scope")
        status = envelope.coverage
        reason = ""
        if envelope.denied_fields and status == "complete":
            status = "partial"
            reason = "denied fields prevent complete coverage"
        return CoverageReceipt(
            scope_id=scope.scope_id,
            provider=envelope.provider,
            object_id=envelope.external_id,
            status=status,
            cursor=envelope.cursor,
            denied_fields=envelope.denied_fields,
            reason=reason,
        )


__all__ = [
    "AuthorizationCoverage",
    "AuthorizationError",
    "CoverageReceipt",
]
