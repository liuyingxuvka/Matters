"""C10: append-only correction and invalidation coordination."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Revision:
    revision_id: str
    kind: str
    target_id: str
    prior_revision_id: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DependentDisposition:
    dependent_id: str
    owner_model_id: str
    action: str
    reason: str


@dataclass(frozen=True)
class InvalidationPlan:
    revision_id: str
    dispositions: tuple[DependentDisposition, ...]


@dataclass(frozen=True)
class RecomputeRequest:
    revision_id: str
    owner_model_id: str
    dependent_ids: tuple[str, ...]


@dataclass
class CorrectionCoordinator:
    _revisions: list[Revision] = field(default_factory=list)

    def append(
        self,
        *,
        kind: str,
        target_id: str,
        prior_revision_id: str,
        rationale: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> Revision:
        if kind not in {
            "correction",
            "revocation",
            "supersession",
            "deletion",
            "reopening",
        }:
            raise ValueError("unsupported revision kind")
        revision = Revision(
            revision_id=f"revision:{len(self._revisions) + 1}",
            kind=kind,
            target_id=target_id,
            prior_revision_id=prior_revision_id,
            rationale=rationale,
            evidence_ids=evidence_ids,
        )
        self._revisions.append(revision)
        return revision

    def invalidate(
        self,
        revision: Revision,
        dependents: tuple[tuple[str, str], ...],
    ) -> tuple[InvalidationPlan, tuple[RecomputeRequest, ...]]:
        if not dependents:
            raise ValueError("dependent inventory is required")
        dispositions = tuple(
            DependentDisposition(
                dependent_id=dependent_id,
                owner_model_id=owner_model_id,
                action="recompute",
                reason=f"invalidated by {revision.revision_id}",
            )
            for dependent_id, owner_model_id in dependents
        )
        owners: dict[str, list[str]] = {}
        for item in dispositions:
            owners.setdefault(item.owner_model_id, []).append(item.dependent_id)
        requests = tuple(
            RecomputeRequest(revision.revision_id, owner, tuple(ids))
            for owner, ids in owners.items()
        )
        return InvalidationPlan(revision.revision_id, dispositions), requests

    @property
    def history(self) -> tuple[Revision, ...]:
        return tuple(self._revisions)

    @staticmethod
    def write_foreign_state(*_args, **_kwargs) -> None:
        raise PermissionError(
            "C10 issues recompute requests; original owners write canonical state"
        )


__all__ = [
    "CorrectionCoordinator",
    "DependentDisposition",
    "InvalidationPlan",
    "RecomputeRequest",
    "Revision",
]
