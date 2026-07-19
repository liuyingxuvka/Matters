"""Immutable contracts for bounded Jira authorization and slice evidence.

These records contain hashes, counts, and bounded statuses. They never contain
credentials and they do not own canonical Matter state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from matters.authorization.scopes import AuthorizationScope


COVERAGE_STATUSES = frozenset({"complete", "partial", "unknown"})
PRODUCT_OUTCOMES = frozenset(
    {"matter", "source_only", "needs_review", "access_blocked"}
)
TEST_RESULTS = frozenset({"pass", "fail", "blocked"})
PRIVACY_SCAN_STATUSES = frozenset({"pass", "fail", "blocked", "not_run"})


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _require_sha256(name: str, value: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be a sha256 reference")


@dataclass(frozen=True)
class JiraAuthorizationManifest:
    """External, explicit authorization input for one bounded Jira scope."""

    authorization_scope_id: str
    instance_ref_hash: str
    provider_edition: str
    provider_version: str
    capabilities: tuple[str, ...]
    project_ref_hashes: frozenset[str]
    object_ids: frozenset[str]
    object_types: frozenset[str]
    time_start: str
    time_end: str
    permission_fingerprint: str
    expires_at: str
    attachment_metadata_allowed: bool = False
    attachment_content_allowed: bool = False
    active: bool = True
    operations: frozenset[str] = frozenset({"read"})

    def __post_init__(self) -> None:
        if not self.authorization_scope_id:
            raise ValueError("authorization_scope_id is required")
        _require_sha256("instance_ref_hash", self.instance_ref_hash)
        _require_sha256(
            "permission_fingerprint",
            self.permission_fingerprint,
        )
        if not self.provider_edition or not self.provider_version:
            raise ValueError("provider edition and version are required")
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(
            self,
            "project_ref_hashes",
            frozenset(self.project_ref_hashes),
        )
        object.__setattr__(self, "object_ids", frozenset(self.object_ids))
        object.__setattr__(self, "object_types", frozenset(self.object_types))
        object.__setattr__(self, "operations", frozenset(self.operations))
        scope = self.to_scope()
        gaps = scope.explicit_read_boundary_gaps()
        if gaps:
            raise ValueError(
                "authorization boundary is incomplete: " + ",".join(gaps)
            )

    def to_scope(self) -> AuthorizationScope:
        return AuthorizationScope(
            scope_id=self.authorization_scope_id,
            provider="jira",
            object_ids=self.object_ids,
            operations=self.operations,
            active=self.active,
            query_snapshot="bounded_jira_slice",
            instance_ref_hash=self.instance_ref_hash,
            project_ref_hashes=self.project_ref_hashes,
            object_types=self.object_types,
            time_start=self.time_start,
            time_end=self.time_end,
            attachment_metadata_allowed=self.attachment_metadata_allowed,
            attachment_content_allowed=self.attachment_content_allowed,
            permission_fingerprint=self.permission_fingerprint,
            expires_at=self.expires_at,
        )

    def blockers(self, *, as_of: datetime | None = None) -> tuple[str, ...]:
        scope = self.to_scope()
        if scope.current(as_of):
            return ()
        return (
            "authorization_revoked"
            if not self.active
            else "authorization_expired",
        )


@dataclass(frozen=True)
class ObjectTypeCoverage:
    object_type: str
    expected: int | None
    fetched: int
    pagination_complete: bool | None
    denied: int = 0
    skipped: int = 0

    def __post_init__(self) -> None:
        if not self.object_type:
            raise ValueError("object_type is required")
        counts = (self.fetched, self.denied, self.skipped)
        if any(value < 0 for value in counts):
            raise ValueError("coverage counts must be non-negative")
        if self.expected is not None and self.expected < 0:
            raise ValueError("expected must be non-negative or unknown")
        if self.expected is not None and self.fetched > self.expected:
            raise ValueError("fetched cannot exceed the frozen expected count")

    @property
    def status(self) -> str:
        if self.expected is None or self.pagination_complete is None:
            return "unknown"
        if (
            not self.pagination_complete
            or self.denied
            or self.skipped
            or self.fetched != self.expected
        ):
            return "partial"
        return "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected": self.expected,
            "fetched": self.fetched,
            "pagination": (
                "complete"
                if self.pagination_complete is True
                else "incomplete"
                if self.pagination_complete is False
                else "unknown"
            ),
            "denied": self.denied,
            "skipped": self.skipped,
            "coverage_status": self.status,
        }


@dataclass(frozen=True)
class JiraSliceCoverageReceipt:
    """Minimum frozen evidence contract for one real Jira slice."""

    experiment_id: str
    slice_id: str
    authorization_scope_id: str
    provider_edition_and_capabilities: Mapping[str, Any]
    selected_issue_ref_hash: str
    coverage_type: str
    as_of_time: str
    permission_fingerprint: str
    per_object_type: tuple[ObjectTypeCoverage, ...]
    attachment_metadata_count: int
    attachment_content_count: int
    source_version_hashes: tuple[str, ...]
    evidence_anchor_counts: Mapping[str, int]
    person_candidate_count: int
    event_candidate_count: int
    matter_candidate_count: int
    action_candidate_count: int
    unsupported_claims: tuple[str, ...]
    contradictions: tuple[str, ...]
    review_items: tuple[str, ...]
    guard_artifact_versions: Mapping[str, str]
    localization_status: str
    privacy_scan_status: str
    idempotency_key: str
    oracle_expected_outcome: str
    product_outcome: str
    coverage_status: str
    test_result: str
    claim_boundary: str

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.authorization_scope_id:
            raise ValueError(
                "experiment_id and authorization_scope_id are required"
            )
        if self.slice_id not in {f"J{index}" for index in range(1, 11)}:
            raise ValueError("slice_id must be J1 through J10")
        _require_sha256(
            "selected_issue_ref_hash",
            self.selected_issue_ref_hash,
        )
        _require_sha256(
            "permission_fingerprint",
            self.permission_fingerprint,
        )
        if self.coverage_type not in {
            "snapshot",
            "incremental",
            "bounded_query",
        }:
            raise ValueError("unsupported coverage_type")
        if self.coverage_status not in COVERAGE_STATUSES:
            raise ValueError("invalid coverage_status")
        if self.product_outcome not in PRODUCT_OUTCOMES:
            raise ValueError("invalid product_outcome")
        if self.test_result not in TEST_RESULTS:
            raise ValueError("invalid test_result")
        if self.privacy_scan_status not in PRIVACY_SCAN_STATUSES:
            raise ValueError("invalid privacy_scan_status")
        if any(
            value < 0
            for value in (
                self.attachment_metadata_count,
                self.attachment_content_count,
                self.person_candidate_count,
                self.event_candidate_count,
                self.matter_candidate_count,
                self.action_candidate_count,
            )
        ):
            raise ValueError("receipt counts must be non-negative")
        object.__setattr__(
            self,
            "provider_edition_and_capabilities",
            _freeze_mapping(self.provider_edition_and_capabilities),
        )
        object.__setattr__(
            self,
            "evidence_anchor_counts",
            _freeze_mapping(self.evidence_anchor_counts),
        )
        object.__setattr__(
            self,
            "guard_artifact_versions",
            _freeze_mapping(self.guard_artifact_versions),
        )
        for attribute in (
            "per_object_type",
            "source_version_hashes",
            "unsupported_claims",
            "contradictions",
            "review_items",
        ):
            object.__setattr__(self, attribute, tuple(getattr(self, attribute)))
        if len({row.object_type for row in self.per_object_type}) != len(
            self.per_object_type
        ):
            raise ValueError("per_object_type entries must be unique")
        derived_statuses = {row.status for row in self.per_object_type}
        derived = (
            "unknown"
            if "unknown" in derived_statuses
            else "partial"
            if "partial" in derived_statuses
            else "complete"
        )
        if self.per_object_type and self.coverage_status != derived:
            raise ValueError(
                "coverage_status must match per-object coverage accounting"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "slice_id": self.slice_id,
            "authorization_scope_id": self.authorization_scope_id,
            "provider_edition_and_capabilities": dict(
                self.provider_edition_and_capabilities
            ),
            "selected_issue_ref_hash": self.selected_issue_ref_hash,
            "coverage_type": self.coverage_type,
            "as_of_time": self.as_of_time,
            "permission_fingerprint": self.permission_fingerprint,
            "per_object_type": {
                row.object_type: row.to_dict()
                for row in self.per_object_type
            },
            "attachment_metadata_count": self.attachment_metadata_count,
            "attachment_content_count": self.attachment_content_count,
            "source_version_hashes": list(self.source_version_hashes),
            "evidence_anchor_counts": dict(self.evidence_anchor_counts),
            "person_candidate_count": self.person_candidate_count,
            "event_candidate_count": self.event_candidate_count,
            "matter_candidate_count": self.matter_candidate_count,
            "action_candidate_count": self.action_candidate_count,
            "unsupported_claims": list(self.unsupported_claims),
            "contradictions": list(self.contradictions),
            "review_items": list(self.review_items),
            "guard_artifact_versions": dict(self.guard_artifact_versions),
            "localization_status": self.localization_status,
            "privacy_scan_status": self.privacy_scan_status,
            "idempotency_key": self.idempotency_key,
            "oracle_expected_outcome": self.oracle_expected_outcome,
            "product_outcome": self.product_outcome,
            "coverage_status": self.coverage_status,
            "test_result": self.test_result,
            "claim_boundary": self.claim_boundary,
        }


__all__ = [
    "COVERAGE_STATUSES",
    "JiraAuthorizationManifest",
    "JiraSliceCoverageReceipt",
    "ObjectTypeCoverage",
    "PRIVACY_SCAN_STATUSES",
    "PRODUCT_OUTCOMES",
    "TEST_RESULTS",
]
