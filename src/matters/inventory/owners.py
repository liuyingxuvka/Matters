"""Durable candidate-scope, tracking-policy, inventory, and change-set owners."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import PurePath
from typing import Any, Iterable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


DISPOSITIONS = frozenset(
    {
        "tracked",
        "not_tracked",
        "metadata_only",
        "hard_excluded",
        "blocked",
        "unavailable",
    }
)
USER_INTENTS = {
    "track": "tracked",
    "do_not_track": "not_tracked",
    "metadata_only": "metadata_only",
    "restore": "tracked",
}
DEPENDENCY_KINDS = (
    "triage",
    "extraction",
    "analysis",
    "evidence",
    "projection",
)
CURRENT_TRACKING_POLICY_REVISION = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CandidateScope:
    scope_id: str
    revision: int
    provider: str
    root_locator: str
    object_types: tuple[str, ...]
    include_hidden: bool = False
    follow_links: bool = False
    active: bool = True

    def __post_init__(self) -> None:
        if not self.scope_id or not self.provider or not self.root_locator:
            raise ValueError("scope_id, provider, and root_locator are required")
        if self.revision < 1:
            raise ValueError("scope revision must be positive")
        object.__setattr__(self, "object_types", tuple(self.object_types))


@dataclass(frozen=True)
class TrackingPolicy:
    policy_id: str
    revision: int
    protected_classes: tuple[str, ...] = (
        "credential",
        "system_software",
        "security_material",
    )
    ignored_names: tuple[str, ...] = (
        ".flowpilot",
        ".git",
        ".skillguard",
        ".svn",
        ".gradle",
        ".idea",
        ".ipynb_checkpoints",
        ".next",
        ".nox",
        ".nuxt",
        ".playwright-mcp",
        ".terraform",
        ".tmp",
        ".tox",
        ".vscode",
        ".vs",
        "__pycache__",
        "bower_components",
        "coverage",
        "htmlcov",
        "logs",
        "node_modules",
        ".cache",
        "cache",
        "release_artifacts",
        "runs",
        "sessions",
        "site-packages",
        "state",
        "tmp",
        "temp",
        "thumbs.db",
        "desktop.ini",
    )
    archive_size_limit: int = 256 * 1024 * 1024
    changed_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.policy_id or self.revision < 1:
            raise ValueError("policy_id and positive revision are required")


@dataclass(frozen=True)
class SourceDisposition:
    occurrence_id: str
    status: str
    reason: str
    policy_revision: int
    decided_by: str = "policy"
    user_intent: str = ""

    def __post_init__(self) -> None:
        if self.status not in DISPOSITIONS:
            raise ValueError(f"unsupported source disposition: {self.status}")
        if self.user_intent and self.user_intent not in USER_INTENTS:
            raise ValueError(f"unsupported user intent: {self.user_intent}")

    @property
    def terminal(self) -> bool:
        return self.status in DISPOSITIONS


@dataclass(frozen=True)
class InventoryOccurrence:
    occurrence_id: str
    provider: str
    object_type: str
    locator: str
    metadata: Mapping[str, Any]
    content_identity: str = ""
    discovery_reason: str = "enumerated"
    parent_occurrence_id: str = ""

    def __post_init__(self) -> None:
        if not self.occurrence_id or not self.provider or not self.object_type:
            raise ValueError("occurrence identity, provider, and type are required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def metadata_identity(self) -> str:
        return _fingerprint(
            {
                "provider": self.provider,
                "object_type": self.object_type,
                "locator": self.locator,
                "metadata": self.metadata,
                "content_identity": self.content_identity,
                "parent_occurrence_id": self.parent_occurrence_id,
            }
        )


@dataclass(frozen=True)
class InventorySnapshot:
    snapshot_id: str
    scope_id: str
    revision: int
    policy_revision: int
    occurrences: tuple[InventoryOccurrence, ...]
    dispositions: tuple[SourceDisposition, ...]
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        occurrence_ids = [item.occurrence_id for item in self.occurrences]
        disposition_ids = [item.occurrence_id for item in self.dispositions]
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise ValueError("inventory occurrence ids must be unique")
        if set(occurrence_ids) != set(disposition_ids):
            raise ValueError("every occurrence requires exactly one disposition")


@dataclass(frozen=True)
class ChangeSet:
    change_set_id: str
    scope_id: str
    prior_revision: int | None
    current_revision: int
    added: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    moved: tuple[tuple[str, str], ...] = ()
    deleted: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    newly_reachable: tuple[str, ...] = ()
    policy_changed: tuple[str, ...] = ()
    stale_dependencies: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stale_dependencies",
            {
                str(key): tuple(value)
                for key, value in self.stale_dependencies.items()
            },
        )

    @property
    def changed_occurrence_ids(self) -> tuple[str, ...]:
        moved_ids = tuple(target for _, target in self.moved)
        return tuple(
            dict.fromkeys(
                self.added
                + self.modified
                + moved_ids
                + self.deleted
                + self.newly_reachable
                + self.policy_changed
            )
        )

    @property
    def no_delta(self) -> bool:
        return not self.changed_occurrence_ids


def occurrence_id(provider: str, object_type: str, locator: str) -> str:
    raw = f"{provider}\0{object_type}\0{locator}"
    return "occurrence:" + sha256(raw.encode("utf-8")).hexdigest()[:24]


def classify_occurrence(
    occurrence: InventoryOccurrence,
    policy: TrackingPolicy,
    *,
    user_intent: str = "",
) -> SourceDisposition:
    """Apply hard exclusions, then an explicit user override, then AI/policy triage."""

    lowered = "/".join(part.lower() for part in PurePath(occurrence.locator).parts)
    source_class = str(occurrence.metadata.get("source_class", "")).lower()
    recommended = str(
        occurrence.metadata.get("recommended_disposition", "")
    ).lower()
    if recommended == "hard_excluded":
        return SourceDisposition(
            occurrence.occurrence_id,
            "hard_excluded",
            str(
                occurrence.metadata.get(
                    "disposition_reason",
                    "provider hard exclusion",
                )
            ),
            policy.revision,
            decided_by="policy",
            user_intent=user_intent,
        )
    if source_class in policy.protected_classes:
        return SourceDisposition(
            occurrence.occurrence_id,
            "hard_excluded",
            f"protected source class: {source_class}",
            policy.revision,
            decided_by="policy",
            user_intent=user_intent,
        )
    if bool(occurrence.metadata.get("credential_like")):
        return SourceDisposition(
            occurrence.occurrence_id,
            "hard_excluded",
            "credential-like occurrence",
            policy.revision,
            decided_by="policy",
            user_intent=user_intent,
        )
    if user_intent:
        return SourceDisposition(
            occurrence.occurrence_id,
            USER_INTENTS[user_intent],
            f"user intent: {user_intent}",
            policy.revision,
            decided_by="user",
            user_intent=user_intent,
        )
    if recommended in {
        "not_tracked",
        "metadata_only",
        "blocked",
        "unavailable",
    }:
        return SourceDisposition(
            occurrence.occurrence_id,
            recommended,
            str(
                occurrence.metadata.get(
                    "disposition_reason",
                    f"provider recommendation: {recommended}",
                )
            ),
            policy.revision,
            decided_by="provider_policy",
        )
    name_parts = set(part.lower() for part in PurePath(occurrence.locator).parts)
    name_parts.update(
        str(part).lower()
        for part in occurrence.metadata.get("policy_path_tokens", ())
    )
    if name_parts.intersection(name.lower() for name in policy.ignored_names):
        return SourceDisposition(
            occurrence.occurrence_id,
            "not_tracked",
            "known cache, generated, or software-state location",
            policy.revision,
            decided_by="policy",
        )
    if recommended == "tracked":
        return SourceDisposition(
            occurrence.occurrence_id,
            "tracked",
            str(
                occurrence.metadata.get(
                    "disposition_reason",
                    "provider recommendation: tracked",
                )
            ),
            policy.revision,
            decided_by="provider_policy",
        )
    size = int(occurrence.metadata.get("size", 0) or 0)
    if occurrence.object_type == "archive" and size > policy.archive_size_limit:
        return SourceDisposition(
            occurrence.occurrence_id,
            "metadata_only",
            "large archive is registered without recursive extraction",
            policy.revision,
            decided_by="policy",
        )
    if occurrence.object_type in {"unknown", "cloud_placeholder"}:
        return SourceDisposition(
            occurrence.occurrence_id,
            "metadata_only",
            "source is registered but content is not currently readable",
            policy.revision,
            decided_by="ai",
        )
    if any(token in lowered for token in ("/logs/", "/sessions/", "/state/")):
        return SourceDisposition(
            occurrence.occurrence_id,
            "not_tracked",
            "application state inside an authorized user root is excluded by default",
            policy.revision,
            decided_by="ai",
        )
    return SourceDisposition(
        occurrence.occurrence_id,
        "tracked",
        "supported user-owned occurrence",
        policy.revision,
        decided_by="ai",
    )


def compare_snapshots(
    prior: InventorySnapshot | None,
    current: InventorySnapshot,
) -> ChangeSet:
    old = {item.occurrence_id: item for item in prior.occurrences} if prior else {}
    new = {item.occurrence_id: item for item in current.occurrences}
    old_dispositions = (
        {item.occurrence_id: item for item in prior.dispositions} if prior else {}
    )
    new_dispositions = {item.occurrence_id: item for item in current.dispositions}

    added_ids = set(new) - set(old)
    deleted_ids = set(old) - set(new)
    moved: list[tuple[str, str]] = []
    deleted_by_content: dict[str, list[str]] = {}
    for item_id in sorted(deleted_ids):
        identity = old[item_id].content_identity
        if identity:
            deleted_by_content.setdefault(identity, []).append(item_id)
    for item_id in tuple(sorted(added_ids)):
        identity = new[item_id].content_identity
        prior_candidates = deleted_by_content.get(identity) if identity else None
        if prior_candidates:
            prior_id = prior_candidates.pop(0)
            moved.append((prior_id, item_id))
            added_ids.remove(item_id)
            deleted_ids.remove(prior_id)

    common = set(old).intersection(new)
    modified = tuple(
        sorted(
            item_id
            for item_id in common
            if old[item_id].metadata_identity != new[item_id].metadata_identity
        )
    )
    unchanged = tuple(sorted(common - set(modified)))
    newly_reachable = tuple(
        sorted(
            item_id
            for item_id in added_ids
            if new[item_id].discovery_reason == "newly_reachable"
        )
    )
    added = tuple(sorted(added_ids - set(newly_reachable)))
    policy_changed = tuple(
        sorted(
            item_id
            for item_id in common
            if (
                old_dispositions[item_id].status
                != new_dispositions[item_id].status
                or old_dispositions[item_id].reason
                != new_dispositions[item_id].reason
                or old_dispositions[item_id].decided_by
                != new_dispositions[item_id].decided_by
            )
        )
    )
    changed_ids = tuple(
        dict.fromkeys(
            added
            + modified
            + tuple(target for _, target in moved)
            + tuple(sorted(deleted_ids))
            + newly_reachable
            + policy_changed
        )
    )
    stale = {item_id: DEPENDENCY_KINDS for item_id in changed_ids}
    return ChangeSet(
        change_set_id=f"change:{current.scope_id}:{current.revision}",
        scope_id=current.scope_id,
        prior_revision=prior.revision if prior else None,
        current_revision=current.revision,
        added=added,
        modified=modified,
        moved=tuple(sorted(moved)),
        deleted=tuple(sorted(deleted_ids)),
        unchanged=unchanged,
        newly_reachable=newly_reachable,
        policy_changed=policy_changed,
        stale_dependencies=stale,
    )


@dataclass
class InventoryOwner:
    store: "SQLiteStore"

    def _save_catalog(
        self,
        snapshot: InventorySnapshot,
        *,
        deleted_ids: tuple[str, ...] = (),
    ) -> None:
        """Project a private row catalog for bounded UI/API paging."""

        occurrence_by_id = {
            item.occurrence_id: item for item in snapshot.occurrences
        }
        disposition_by_id = {
            item.occurrence_id: item for item in snapshot.dispositions
        }
        current_catalog = self.store.current_many(
            "source_catalog",
            (*occurrence_by_id, *deleted_ids),
        )
        catalog_ids = (*occurrence_by_id, *deleted_ids)
        catalog_revisions = self.store.next_revisions(
            "source_catalog",
            catalog_ids,
        )
        catalog_rows: list[tuple[str, str, int, Any]] = []
        for occurrence_id_value, occurrence in occurrence_by_id.items():
            disposition = disposition_by_id[occurrence_id_value]
            display_name = str(
                occurrence.metadata.get(
                    "display_name",
                    occurrence.object_type.replace("_", " ").title(),
                )
            )
            catalog_rows.append(
                (
                    "source_catalog",
                    occurrence_id_value,
                    catalog_revisions[occurrence_id_value],
                    {
                        "occurrence_id": occurrence_id_value,
                        "scope_id": snapshot.scope_id,
                        "snapshot_id": snapshot.snapshot_id,
                        "object_type": occurrence.object_type,
                        "display_name": display_name,
                        "disposition": disposition.status,
                        "disposition_reason": disposition.reason,
                        "active": True,
                    },
                )
            )
        for occurrence_id_value in deleted_ids:
            prior = dict(current_catalog.get(occurrence_id_value, {}))
            prior.update(
                {
                    "occurrence_id": occurrence_id_value,
                    "snapshot_id": snapshot.snapshot_id,
                    "active": False,
                }
            )
            catalog_rows.append(
                (
                    "source_catalog",
                    occurrence_id_value,
                    catalog_revisions[occurrence_id_value],
                    prior,
                )
            )
        self.store.append_many(catalog_rows)

    def rebuild_catalog(self) -> int:
        """Rebuild the private UI catalog from current inventory snapshots."""

        count = 0
        for payload in self.store.iter_current("inventory_snapshot"):
            snapshot = self._snapshot_from_payload(payload)
            self._save_catalog(snapshot)
            count += len(snapshot.occurrences)
        return count

    def save_scope(self, scope: CandidateScope) -> None:
        current = self.store.current("candidate_scope", scope.scope_id)
        if current and _fingerprint(current) == _fingerprint(asdict(scope)):
            return
        self.store.append(
            "candidate_scope",
            scope.scope_id,
            scope.revision,
            asdict(scope),
        )

    def save_policy(self, policy: TrackingPolicy) -> None:
        current = self.store.current("tracking_policy", policy.policy_id)
        if current and _fingerprint(current) == _fingerprint(asdict(policy)):
            return
        self.store.append(
            "tracking_policy",
            policy.policy_id,
            policy.revision,
            asdict(policy),
        )

    def latest_snapshot(self, scope_id: str) -> InventorySnapshot | None:
        payload = self.store.current("inventory_snapshot", scope_id)
        return self._snapshot_from_payload(payload) if payload else None

    def reconcile(
        self,
        *,
        scope: CandidateScope,
        policy: TrackingPolicy,
        occurrences: Iterable[InventoryOccurrence],
        user_intents: Mapping[str, str] | None = None,
    ) -> tuple[InventorySnapshot, ChangeSet]:
        self.save_scope(scope)
        self.save_policy(policy)
        prior = self.latest_snapshot(scope.scope_id)
        # The current pointer can legitimately lag the append-only history
        # after an interrupted or competing reconciliation.  Allocate from
        # both histories so recovery never reuses an already committed
        # inventory/change-set revision.
        revision = max(
            self.store.next_revision("inventory_snapshot", scope.scope_id),
            self.store.next_revision("change_set", scope.scope_id),
        )
        ordered = tuple(sorted(occurrences, key=lambda item: item.occurrence_id))
        intents = {
            item.occurrence_id: item.user_intent
            for item in prior.dispositions
            if item.user_intent
        } if prior else {}
        intents.update(user_intents or {})
        dispositions = tuple(
            classify_occurrence(
                item,
                policy,
                user_intent=intents.get(item.occurrence_id, ""),
            )
            for item in ordered
        )
        snapshot = InventorySnapshot(
            snapshot_id=f"inventory:{scope.scope_id}:{revision}",
            scope_id=scope.scope_id,
            revision=revision,
            policy_revision=policy.revision,
            occurrences=ordered,
            dispositions=dispositions,
        )
        change_set = compare_snapshots(prior, snapshot)
        self.store.append(
            "inventory_snapshot",
            scope.scope_id,
            revision,
            asdict(snapshot),
        )
        self.store.append(
            "change_set",
            scope.scope_id,
            revision,
            asdict(change_set),
        )
        self._save_catalog(
            snapshot,
            deleted_ids=change_set.deleted,
        )
        freshness_revisions = self.store.next_revisions(
            "dependency_freshness",
            change_set.stale_dependencies,
        )
        self.store.append_many(
            (
                "dependency_freshness",
                occurrence_id_value,
                freshness_revisions[occurrence_id_value],
                {
                    "occurrence_id": occurrence_id_value,
                    "inventory_revision": revision,
                    "status": "stale",
                    "dependencies": dependencies,
                },
            )
            for occurrence_id_value, dependencies in (
                change_set.stale_dependencies.items()
            )
        )
        return snapshot, change_set

    @staticmethod
    def _snapshot_from_payload(payload: Mapping[str, Any]) -> InventorySnapshot:
        return InventorySnapshot(
            snapshot_id=str(payload["snapshot_id"]),
            scope_id=str(payload["scope_id"]),
            revision=int(payload["revision"]),
            policy_revision=int(payload["policy_revision"]),
            occurrences=tuple(
                InventoryOccurrence(**dict(item))
                for item in payload.get("occurrences", ())
            ),
            dispositions=tuple(
                SourceDisposition(**dict(item))
                for item in payload.get("dispositions", ())
            ),
            created_at=str(payload.get("created_at", "")),
        )


__all__ = [
    "CandidateScope",
    "ChangeSet",
    "CURRENT_TRACKING_POLICY_REVISION",
    "DEPENDENCY_KINDS",
    "DISPOSITIONS",
    "InventoryOccurrence",
    "InventoryOwner",
    "InventorySnapshot",
    "SourceDisposition",
    "TrackingPolicy",
    "classify_occurrence",
    "compare_snapshots",
    "occurrence_id",
]
