"""Singular ResearchGuard integration gate.

Legacy Guard names may be retained only as source-only migration evidence.
They can never become executable fallback providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json


LEGACY_RESEARCH_PROVIDER_IDS = frozenset(
    {"sourceguard", "traceguard", "logicguard"}
)


class ResearchGuardStatus(StrEnum):
    PENDING = "researchguard_pending_integration"
    CURRENT = "researchguard_current"
    BLOCKED = "researchguard_blocked"


@dataclass(frozen=True)
class ResearchGuardGate:
    status: ResearchGuardStatus
    identity: str = ""
    currentness_receipt_identity: str = ""
    requested_provider_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        providers = tuple(provider.casefold() for provider in self.requested_provider_ids)
        if len(set(providers)) != len(providers):
            raise ValueError("requested_provider_ids must not contain duplicates")
        object.__setattr__(self, "requested_provider_ids", providers)
        if self.status == ResearchGuardStatus.CURRENT:
            if not self.identity or not self.currentness_receipt_identity:
                raise ValueError(
                    "current ResearchGuard requires exact provider and currentness receipt identities"
                )
        elif self.identity or self.currentness_receipt_identity:
            raise ValueError("non-current ResearchGuard cannot publish a provider identity")

    @property
    def legacy_fallback_requests(self) -> tuple[str, ...]:
        return tuple(
            provider
            for provider in self.requested_provider_ids
            if provider in LEGACY_RESEARCH_PROVIDER_IDS
        )

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "status": self.status.value,
                "identity": self.identity,
                "currentness_receipt_identity": self.currentness_receipt_identity,
                "requested_provider_ids": list(self.requested_provider_ids),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + sha256(payload).hexdigest()


@dataclass(frozen=True)
class ResearchProviderDecision:
    status: ResearchGuardStatus
    provider_identity: str
    currentness_receipt_identity: str
    reason: str
    legacy_dispositions: tuple[tuple[str, str], ...]

    @property
    def usable(self) -> bool:
        return self.status == ResearchGuardStatus.CURRENT


def resolve_research_provider(gate: ResearchGuardGate) -> ResearchProviderDecision:
    legacy = tuple(
        (provider, "stale_source_only")
        for provider in sorted(LEGACY_RESEARCH_PROVIDER_IDS)
    )
    if gate.legacy_fallback_requests:
        return ResearchProviderDecision(
            status=ResearchGuardStatus.BLOCKED,
            provider_identity="",
            currentness_receipt_identity="",
            reason=(
                "legacy_parallel_fallback_rejected:"
                + ",".join(gate.legacy_fallback_requests)
            ),
            legacy_dispositions=legacy,
        )
    if any(provider != "researchguard" for provider in gate.requested_provider_ids):
        return ResearchProviderDecision(
            status=ResearchGuardStatus.BLOCKED,
            provider_identity="",
            currentness_receipt_identity="",
            reason="unknown_parallel_research_provider_rejected",
            legacy_dispositions=legacy,
        )
    if gate.status == ResearchGuardStatus.CURRENT:
        return ResearchProviderDecision(
            status=ResearchGuardStatus.CURRENT,
            provider_identity=gate.identity,
            currentness_receipt_identity=gate.currentness_receipt_identity,
            reason="one_exact_researchguard_provider_current",
            legacy_dispositions=legacy,
        )
    if gate.status == ResearchGuardStatus.BLOCKED:
        return ResearchProviderDecision(
            status=ResearchGuardStatus.BLOCKED,
            provider_identity="",
            currentness_receipt_identity="",
            reason="researchguard_integration_blocked",
            legacy_dispositions=legacy,
        )
    return ResearchProviderDecision(
        status=ResearchGuardStatus.PENDING,
        provider_identity="",
        currentness_receipt_identity="",
        reason="researchguard_pending_integration",
        legacy_dispositions=legacy,
    )


__all__ = [
    "LEGACY_RESEARCH_PROVIDER_IDS",
    "ResearchGuardGate",
    "ResearchGuardStatus",
    "ResearchProviderDecision",
    "resolve_research_provider",
]
