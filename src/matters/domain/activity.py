"""C5/C12 Matter activity values and ordering invariants.

Activity is driven by a user-world MaterialClue, never by backend processing
time.  The application owner atomically binds a current material clue to the
bilingual summary and activity-order revisions consumed by C12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping


MATERIALITY_DISPOSITIONS = frozenset(
    {"material", "nonmaterial", "uncertain"}
)
REQUIRED_ACTIVITY_LOCALES = ("en", "zh-CN")
NON_BUBBLING_CLUE_KINDS = frozenset(
    {
        "scan",
        "retry",
        "localization",
        "translation",
        "hero",
        "hero_generation",
        "image_generation",
        "reword",
        "summary_reword",
        "classification_only",
        "projection_refresh",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_utc_timestamp(value: str, field_name: str) -> str:
    """Return one timezone-aware timestamp in canonical UTC form."""

    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _localized(
    values: Mapping[str, str],
    *,
    required: bool,
) -> dict[str, str]:
    normalized = {
        str(locale): str(value).strip()
        for locale, value in values.items()
        if str(locale).strip() and str(value).strip()
    }
    if required and any(not normalized.get(locale) for locale in REQUIRED_ACTIVITY_LOCALES):
        raise ValueError(
            "material activity summary requires non-empty en and zh-CN values"
        )
    return normalized


def _fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MaterialClue:
    """One canonical activity observation with an explicit disposition.

    The class name follows the C5 contract.  ``nonmaterial`` and ``uncertain``
    observations are preserved for audit but can never advance Matter activity.
    """

    clue_id: str
    matter_id: str
    clue_kind: str
    user_world_at: str
    disposition: str
    rationale: str
    localized_summary: Mapping[str, str] = field(default_factory=dict)
    semantic_revision: str = ""
    evidence_ids: tuple[str, ...] = ()
    processed_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        clue_id = str(self.clue_id).strip()
        matter_id = str(self.matter_id).strip()
        clue_kind = str(self.clue_kind).strip().lower()
        disposition = str(self.disposition).strip().lower()
        rationale = str(self.rationale).strip()
        evidence_ids = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.evidence_ids if str(item).strip()
            )
        )
        if not clue_id or not matter_id or not clue_kind:
            raise ValueError("clue, Matter, and clue-kind identities are required")
        if disposition not in MATERIALITY_DISPOSITIONS:
            raise ValueError("unsupported materiality disposition")
        if not rationale:
            raise ValueError("materiality rationale is required")
        if disposition == "material" and clue_kind in NON_BUBBLING_CLUE_KINDS:
            raise ValueError(
                f"{clue_kind} is processing-only and cannot be material activity"
            )
        if disposition == "material" and not str(self.semantic_revision).strip():
            raise ValueError("material activity requires a semantic revision")
        if disposition == "material" and not evidence_ids:
            raise ValueError("material activity requires evidence provenance")

        object.__setattr__(self, "clue_id", clue_id)
        object.__setattr__(self, "matter_id", matter_id)
        object.__setattr__(self, "clue_kind", clue_kind)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(
            self,
            "user_world_at",
            canonical_utc_timestamp(self.user_world_at, "user_world_at"),
        )
        object.__setattr__(
            self,
            "processed_at",
            canonical_utc_timestamp(self.processed_at, "processed_at"),
        )
        object.__setattr__(
            self,
            "localized_summary",
            _localized(
                self.localized_summary,
                required=disposition == "material",
            ),
        )
        object.__setattr__(
            self,
            "semantic_revision",
            str(self.semantic_revision).strip(),
        )
        object.__setattr__(self, "evidence_ids", evidence_ids)

    @property
    def advances_activity(self) -> bool:
        return (
            self.disposition == "material"
            and self.clue_kind not in NON_BUBBLING_CLUE_KINDS
        )

    @property
    def binding_revision(self) -> str:
        """One immutable identity for clue, summary, and ordering publication."""

        return _fingerprint(
            {
                "clue_id": self.clue_id,
                "matter_id": self.matter_id,
                "user_world_at": self.user_world_at,
                "semantic_revision": self.semantic_revision,
                "localized_summary": dict(self.localized_summary),
                "evidence_ids": self.evidence_ids,
            }
        )

    @property
    def identity_fingerprint(self) -> str:
        """Retry-stable identity excluding the non-authoritative process time."""

        return _fingerprint(
            {
                "clue_id": self.clue_id,
                "matter_id": self.matter_id,
                "clue_kind": self.clue_kind,
                "user_world_at": self.user_world_at,
                "disposition": self.disposition,
                "rationale": self.rationale,
                "localized_summary": dict(self.localized_summary),
                "semantic_revision": self.semantic_revision,
                "evidence_ids": self.evidence_ids,
            }
        )


@dataclass(frozen=True)
class MatterActivityProjection:
    """Current atomic C12 projection for one Matter."""

    matter_id: str
    source_matter_id: str
    material_clue_id: str
    latest_meaningful_clue_at: str
    localized_summary: Mapping[str, str]
    semantic_revision: str
    material_clue_revision: str
    summary_revision: str
    activity_order_revision: str
    evidence_ids: tuple[str, ...]
    ancestor_propagated: bool
    persistence_revision: int
    processed_at: str

    def __post_init__(self) -> None:
        if (
            not self.matter_id
            or not self.source_matter_id
            or not self.material_clue_id
        ):
            raise ValueError("activity projection identities are required")
        if self.persistence_revision < 1:
            raise ValueError("activity persistence revision must be positive")
        if not (
            self.material_clue_revision
            == self.summary_revision
            == self.activity_order_revision
        ):
            raise ValueError(
                "clue, bilingual summary, and activity order must share one revision"
            )
        object.__setattr__(
            self,
            "latest_meaningful_clue_at",
            canonical_utc_timestamp(
                self.latest_meaningful_clue_at,
                "latest_meaningful_clue_at",
            ),
        )
        object.__setattr__(
            self,
            "processed_at",
            canonical_utc_timestamp(self.processed_at, "processed_at"),
        )
        object.__setattr__(
            self,
            "localized_summary",
            _localized(self.localized_summary, required=True),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence_ids
                    if str(item).strip()
                )
            ),
        )

    @property
    def stable_order_key(self) -> tuple[int, str]:
        return stable_activity_order_key(self)


def stable_activity_order_key(
    projection: MatterActivityProjection | Mapping[str, Any],
) -> tuple[int, str]:
    """Ascending sort key that yields newest activity first and stable ties."""

    if isinstance(projection, MatterActivityProjection):
        timestamp = projection.latest_meaningful_clue_at
        matter_id = projection.matter_id
    else:
        timestamp = str(projection["latest_meaningful_clue_at"])
        matter_id = str(projection["matter_id"])
    parsed = datetime.fromisoformat(
        canonical_utc_timestamp(timestamp, "latest_meaning_clue_at")
    )
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = parsed - epoch
    microseconds = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    return (-microseconds, matter_id)


__all__ = [
    "MATERIALITY_DISPOSITIONS",
    "NON_BUBBLING_CLUE_KINDS",
    "REQUIRED_ACTIVITY_LOCALES",
    "MaterialClue",
    "MatterActivityProjection",
    "canonical_utc_timestamp",
    "stable_activity_order_key",
]
