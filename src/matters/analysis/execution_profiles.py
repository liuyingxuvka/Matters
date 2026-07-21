"""Private, replaceable Codex capability profiles.

Concrete model and reasoning choices live only in MATTERS_HOME.  Product work
packages name capability roles and keep the same identity when this profile is
replaced.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

from matters.analysis.operations import (
    CAPABILITY_ROLES,
    AgentRunner,
    AnalysisWorkPackage,
)
from matters.infrastructure.sqlite.store import SQLiteStore


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _direct_provider_api_target(value: str) -> bool:
    lowered = value.casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    return (
        "://" in lowered
        or any(
            marker in normalized
            for marker in (
                "openai api",
                "direct api",
                "provider api",
                "api key",
                "api openai com",
            )
        )
    )


@dataclass(frozen=True)
class CapabilityProfileEntry:
    capability_role: str
    execution_target: str
    reasoning_level: str
    availability: str = "available"

    def __post_init__(self) -> None:
        if self.capability_role not in CAPABILITY_ROLES:
            raise ValueError("unsupported capability role")
        if not self.execution_target.strip():
            raise ValueError("execution target is required")
        if _direct_provider_api_target(self.execution_target):
            raise ValueError("direct provider API targets are forbidden")
        if self.reasoning_level not in {
            "minimal",
            "low",
            "medium",
            "high",
            "adaptive",
        }:
            raise ValueError("unsupported reasoning level")
        if self.availability not in {"available", "unavailable", "disabled"}:
            raise ValueError("unsupported capability availability")


@dataclass(frozen=True)
class PrivateCodexExecutionProfile:
    profile_identity: str
    revision: int
    entries: tuple[CapabilityProfileEntry, ...]
    status: str = "current"

    def __post_init__(self) -> None:
        if (
            not self.profile_identity.startswith("execution-profile:")
            or self.revision < 1
            or self.status not in {"current", "unavailable"}
        ):
            raise ValueError("private Codex profile identity is invalid")
        roles = tuple(item.capability_role for item in self.entries)
        if len(roles) != len(set(roles)):
            raise ValueError("a capability role has multiple active mappings")
        object.__setattr__(self, "entries", tuple(self.entries))

    def resolve(self, capability_role: str) -> CapabilityProfileEntry | None:
        return next(
            (
                item
                for item in self.entries
                if item.capability_role == capability_role
                and item.availability == "available"
            ),
            None,
        )


class ExecutionProfileRegistry:
    """Append-only private profile activation and resolution."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def activate(
        self,
        entries: tuple[CapabilityProfileEntry, ...],
    ) -> PrivateCodexExecutionProfile:
        normalized = tuple(entries)
        revision = self.store.next_revision(
            "codex_execution_profile",
            "active",
        )
        identity = "execution-profile:" + _fingerprint(
            {
                "revision": revision,
                "entries": tuple(asdict(item) for item in normalized),
            }
        ).removeprefix("sha256:")[:24]
        profile = PrivateCodexExecutionProfile(
            profile_identity=identity,
            revision=revision,
            entries=normalized,
        )
        self.store.append(
            "codex_execution_profile",
            "active",
            revision,
            asdict(profile),
        )
        return profile

    def current(self) -> PrivateCodexExecutionProfile | None:
        payload = self.store.current("codex_execution_profile", "active")
        if payload is None:
            return None
        return PrivateCodexExecutionProfile(
            profile_identity=str(payload["profile_identity"]),
            revision=int(payload["revision"]),
            entries=tuple(
                CapabilityProfileEntry(**dict(item))
                for item in payload.get("entries", ())
            ),
            status=str(payload.get("status", "current")),
        )

    def resolve(self, capability_role: str) -> CapabilityProfileEntry | None:
        profile = self.current()
        return profile.resolve(capability_role) if profile is not None else None

    def public_status(self) -> dict[str, Any]:
        profile = self.current()
        if profile is None:
            return {
                "status": "not_configured",
                "profile_revision": 0,
                "available_capability_roles": (),
            }
        return {
            "status": profile.status,
            "profile_revision": profile.revision,
            "available_capability_roles": tuple(
                sorted(
                    item.capability_role
                    for item in profile.entries
                    if item.availability == "available"
                )
            ),
        }


class CodexCapabilityRunner(AgentRunner):
    """Injected Codex host adapter; it never calls a provider API itself."""

    provider_id = "codex-hosted-capability-router"
    provider_version = "capability-contract-v1"

    def __init__(
        self,
        registry: ExecutionProfileRegistry,
        executor: Callable[
            [AnalysisWorkPackage, CapabilityProfileEntry],
            Mapping[str, Any],
        ],
    ) -> None:
        self.registry = registry
        self.executor = executor

    def execute(self, package: AnalysisWorkPackage) -> Mapping[str, Any]:
        profile = self.registry.current()
        entry = (
            profile.resolve(package.capability_role)
            if profile is not None
            else None
        )
        if profile is None or entry is None:
            return {
                "status": "blocked",
                "failure_class": "codex_capability_unavailable",
                "input_dispositions": [
                    {
                        "input_id": input_id,
                        "disposition": "insufficient",
                        "reason": "No current private Codex capability mapping.",
                    }
                    for input_id in (
                        *package.allowed_evidence_ids,
                        *package.allowed_asset_ids,
                    )
                ],
                "findings": [],
                "execution_profile_identity": (
                    profile.profile_identity
                    if profile is not None
                    else "execution-profile:unavailable"
                ),
                "concrete_execution_identity": (
                    "execution:capability-unavailable"
                ),
                "escalation_status": "capability_unavailable",
                "resource_usage": {"input_count": 0},
            }
        raw = dict(self.executor(package, entry))
        raw["execution_profile_identity"] = profile.profile_identity
        raw.setdefault(
            "concrete_execution_identity",
            "execution:"
            + _fingerprint(
                {
                    "profile_identity": profile.profile_identity,
                    "capability_role": entry.capability_role,
                    "execution_target": entry.execution_target,
                    "reasoning_level": entry.reasoning_level,
                    "package_id": package.package_id,
                }
            ).removeprefix("sha256:")[:24],
        )
        return raw


__all__ = [
    "CapabilityProfileEntry",
    "CodexCapabilityRunner",
    "ExecutionProfileRegistry",
    "PrivateCodexExecutionProfile",
]
