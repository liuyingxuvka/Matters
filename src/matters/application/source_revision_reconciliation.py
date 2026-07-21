"""Bounded reconciliation of admitted Matter source-version references.

The owner is deliberately conservative.  It can remove an older revision when
the same Matter already cites the current revision.  It never promotes a newer
revision merely because metadata or body fingerprints look equivalent: the
current revision still needs current evidence anchors and semantic owner
results before it can replace the admitted revision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol


SOURCE_REVISION_RECONCILIATION_OWNER = "source_revision_reconciliation"
_SOURCE_REF = re.compile(r"^(?P<source_id>source:[^:]+):v(?P<version>[1-9]\d*)$")


class SourceRevisionStore(Protocol):
    def current(self, owner: str, object_id: str) -> dict[str, Any] | None: ...

    def history(self, owner: str, object_id: str) -> tuple[dict[str, Any], ...]: ...

    def compare_current_and_append(
        self,
        owner: str,
        object_id: str,
        *,
        is_equivalent: Any,
        payload_factory: Any,
    ) -> dict[str, Any]: ...

    def immediate_transaction(self) -> Any: ...


@dataclass(frozen=True)
class SourceRevisionDisposition:
    source_ref: str
    current_source_ref: str
    status: str
    reason: str
    content_equivalent: bool = False


@dataclass(frozen=True)
class MatterSourceRevisionPlan:
    matter_id: str
    status: str
    source_ids: tuple[str, ...]
    resulting_source_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    resulting_evidence_ids: tuple[str, ...]
    dispositions: tuple[SourceRevisionDisposition, ...]
    dependency_fingerprint: str

    @property
    def changed(self) -> bool:
        return (
            self.source_ids != self.resulting_source_ids
            or self.evidence_ids != self.resulting_evidence_ids
        )


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _content_equivalent(
    old: Mapping[str, Any],
    current: Mapping[str, Any],
) -> bool:
    if (
        str(old.get("content_hash", ""))
        and str(old.get("content_hash", ""))
        == str(current.get("content_hash", ""))
    ):
        return True
    old_content = old.get("content")
    current_content = current.get("content")
    if not isinstance(old_content, Mapping) or not isinstance(
        current_content,
        Mapping,
    ):
        return False
    old_fingerprint = str(old_content.get("body_text_fingerprint", ""))
    return bool(
        old_fingerprint
        and old_fingerprint
        == str(current_content.get("body_text_fingerprint", ""))
        and int(old_content.get("body_text_byte_length", -1))
        == int(current_content.get("body_text_byte_length", -2))
    )


class MatterSourceRevisionReconciliationOwner:
    """Reconcile one admitted Matter without bypassing analysis owners."""

    def __init__(self, store: SourceRevisionStore) -> None:
        self.store = store

    def plan(self, matter_id: str) -> MatterSourceRevisionPlan:
        if not matter_id:
            raise ValueError("matter_id is required")
        admission = self.store.current("admission_decision", matter_id)
        matter = admission.get("matter") if admission is not None else None
        if (
            admission is None
            or str(admission.get("status", "")) != "admitted"
            or not isinstance(matter, Mapping)
            or str(matter.get("matter_id", "")) != matter_id
        ):
            dispositions = (
                SourceRevisionDisposition(
                    "",
                    "",
                    "blocked",
                    "canonical_admission_missing",
                ),
            )
            return MatterSourceRevisionPlan(
                matter_id,
                "blocked",
                (),
                (),
                (),
                (),
                dispositions,
                _fingerprint(
                    {
                        "matter_id": matter_id,
                        "admission": admission,
                        "dispositions": tuple(
                            asdict(item) for item in dispositions
                        ),
                    }
                ),
            )

        source_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in matter.get("source_ids", ())
                if str(item)
            )
        )
        source_id_set = set(source_ids)
        evidence_ids = tuple(
            dict.fromkeys(
                str(item)
                for item in matter.get("evidence_ids", ())
                if str(item)
            )
        )
        evidence_anchors = {
            evidence_id: self.store.current("evidence_anchor", evidence_id)
            for evidence_id in evidence_ids
        }
        anchor_ids_by_revision: dict[tuple[str, int], set[str]] = {}
        for evidence_id, anchor in evidence_anchors.items():
            if not isinstance(anchor, Mapping):
                continue
            source_id = str(anchor.get("source_id", ""))
            source_version = int(anchor.get("source_version", 0) or 0)
            if source_id and source_version > 0 and bool(
                anchor.get("current", True)
            ):
                anchor_ids_by_revision.setdefault(
                    (source_id, source_version),
                    set(),
                ).add(evidence_id)
        resulting: list[str] = []
        retired_evidence_ids: set[str] = set()
        dispositions: list[SourceRevisionDisposition] = []
        dependencies: dict[str, Any] = {}

        for source_ref in source_ids:
            match = _SOURCE_REF.fullmatch(source_ref)
            if match is None:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        "",
                        "blocked",
                        "source_revision_ref_invalid",
                    )
                )
                continue

            source_id = match.group("source_id")
            expected_version = int(match.group("version"))
            current = self.store.current("source_version", source_id)
            if current is None:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        "",
                        "blocked",
                        "current_source_version_missing",
                    )
                )
                continue

            current_version = int(current.get("version", 0))
            current_ref = f"{source_id}:v{current_version}"
            dependencies[source_id] = {
                "version": current_version,
                "content_hash": str(current.get("content_hash", "")),
                "metadata_hash": str(current.get("metadata_hash", "")),
                "tombstone": bool(current.get("tombstone", False)),
            }
            if bool(current.get("tombstone", False)) or current_version < 1:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        current_ref,
                        "blocked",
                        "current_source_version_unavailable",
                    )
                )
                continue
            if current_version == expected_version:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        current_ref,
                        "current",
                        "admission_already_uses_current_revision",
                        True,
                    )
                )
                continue
            if current_version < expected_version:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        current_ref,
                        "blocked",
                        "admission_revision_is_newer_than_registry_current",
                    )
                )
                continue

            old = next(
                (
                    payload
                    for payload in self.store.history(
                        "source_version",
                        source_id,
                    )
                    if int(payload.get("version", 0)) == expected_version
                ),
                None,
            )
            if old is None:
                resulting.append(source_ref)
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        current_ref,
                        "blocked",
                        "admitted_source_revision_missing",
                    )
                )
                continue

            equivalent = _content_equivalent(old, current)
            if current_ref in source_id_set:
                current_anchor_ids = anchor_ids_by_revision.get(
                    (source_id, current_version),
                    set(),
                )
                if not current_anchor_ids:
                    resulting.append(source_ref)
                    dispositions.append(
                        SourceRevisionDisposition(
                            source_ref,
                            current_ref,
                            "analysis_required",
                            "current_revision_needs_current_evidence_anchors",
                            equivalent,
                        )
                    )
                    continue
                retired_evidence_ids.update(
                    anchor_ids_by_revision.get(
                        (source_id, expected_version),
                        set(),
                    )
                )
                dispositions.append(
                    SourceRevisionDisposition(
                        source_ref,
                        current_ref,
                        "deduplicated",
                        "same_matter_already_admits_current_revision",
                        equivalent,
                    )
                )
                continue

            resulting.append(source_ref)
            dispositions.append(
                SourceRevisionDisposition(
                    source_ref,
                    current_ref,
                    "analysis_required",
                    (
                        "current_revision_needs_current_evidence_anchors"
                        if equivalent
                        else "current_revision_contains_material_content_change"
                    ),
                    equivalent,
                )
            )

        resulting_source_ids = tuple(dict.fromkeys(resulting))
        resulting_evidence_ids = tuple(
            evidence_id
            for evidence_id in evidence_ids
            if evidence_id not in retired_evidence_ids
        )
        statuses = {item.status for item in dispositions}
        status = (
            "blocked"
            if "blocked" in statuses
            else "analysis_required"
            if "analysis_required" in statuses
            else "reconciled"
            if "deduplicated" in statuses
            else "current"
        )
        dependency_fingerprint = _fingerprint(
            {
                "matter_id": matter_id,
                "source_ids": resulting_source_ids,
                "evidence_ids": resulting_evidence_ids,
                "evidence_anchor_dependencies": {
                    evidence_id: (
                        {
                            "source_id": str(anchor.get("source_id", "")),
                            "source_version": int(
                                anchor.get("source_version", 0) or 0
                            ),
                            "current": bool(anchor.get("current", True)),
                        }
                        if isinstance(anchor, Mapping)
                        else None
                    )
                    for evidence_id, anchor in evidence_anchors.items()
                },
                "dependencies": dependencies,
                "terminal_dispositions": tuple(
                    asdict(item)
                    for item in dispositions
                    if item.status != "deduplicated"
                ),
            }
        )
        return MatterSourceRevisionPlan(
            matter_id=matter_id,
            status=status,
            source_ids=source_ids,
            resulting_source_ids=resulting_source_ids,
            evidence_ids=evidence_ids,
            resulting_evidence_ids=resulting_evidence_ids,
            dispositions=tuple(dispositions),
            dependency_fingerprint=dependency_fingerprint,
        )

    def reconcile(self, matter_id: str) -> dict[str, Any]:
        initial = self.plan(matter_id)
        applied_actions = tuple(
            asdict(item)
            for item in initial.dispositions
            if item.status == "deduplicated"
        )

        with self.store.immediate_transaction():
            if initial.changed:
                expected = self.store.current(
                    "admission_decision",
                    matter_id,
                )
                if expected is None:
                    raise RuntimeError(
                        "admission changed during source revision reconciliation"
                    )
                desired = json.loads(
                    json.dumps(expected, ensure_ascii=False)
                )
                desired["matter"]["source_ids"] = list(
                    initial.resulting_source_ids
                )
                desired["matter"]["evidence_ids"] = list(
                    initial.resulting_evidence_ids
                )
                self.store.compare_current_and_append(
                    "admission_decision",
                    matter_id,
                    is_equivalent=lambda observed: observed == desired,
                    payload_factory=lambda _revision, observed: (
                        desired
                        if observed == expected
                        else (_raise_concurrent_admission())
                    ),
                )

            terminal = self.plan(matter_id)
            payload = {
                "matter_id": matter_id,
                "status": terminal.status,
                "source_ids": list(terminal.resulting_source_ids),
                "evidence_ids": list(terminal.resulting_evidence_ids),
                "analysis_required": [
                    asdict(item)
                    for item in terminal.dispositions
                    if item.status == "analysis_required"
                ],
                "blocked": [
                    asdict(item)
                    for item in terminal.dispositions
                    if item.status == "blocked"
                ],
                "applied_actions": list(applied_actions),
                "dependency_fingerprint": terminal.dependency_fingerprint,
            }
            stored = self.store.compare_current_and_append(
                SOURCE_REVISION_RECONCILIATION_OWNER,
                matter_id,
                is_equivalent=lambda current: (
                    current is not None
                    and str(current.get("dependency_fingerprint", ""))
                    == terminal.dependency_fingerprint
                ),
                payload_factory=lambda _revision, _current: payload,
            )
        return {
            **dict(stored["payload"]),
            "write_status": str(stored["status"]),
        }


def _raise_concurrent_admission() -> dict[str, Any]:
    raise RuntimeError(
        "admission changed during source revision reconciliation"
    )


__all__ = [
    "MatterSourceRevisionPlan",
    "MatterSourceRevisionReconciliationOwner",
    "SOURCE_REVISION_RECONCILIATION_OWNER",
    "SourceRevisionDisposition",
]
