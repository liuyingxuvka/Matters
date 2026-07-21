"""C11: advisory-only Guard artifacts and forecasts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from matters.analysis.forecasts import reject_weak_forecast_entrypoint
from matters.analysis.guard_receipts import GuardReceipt


@dataclass(frozen=True)
class GuardArtifact:
    artifact_id: str
    matter_id: str
    kind: str
    statement: str
    receipt_id: str
    status: str
    advisory_only: bool = True


@dataclass
class GuardBridge:
    _artifacts: list[GuardArtifact] = field(default_factory=list)

    def register(
        self,
        *,
        artifact_id: str,
        matter_id: str,
        kind: str,
        statement: str,
        receipt: GuardReceipt,
    ) -> GuardArtifact:
        status = "accepted" if receipt.current else "stale_or_nonterminal"
        artifact = GuardArtifact(
            artifact_id,
            matter_id,
            kind,
            statement,
            receipt.receipt_id,
            status,
        )
        self._artifacts.append(artifact)
        return artifact

    def register_forecast(self, _forecast: object) -> NoReturn:
        """Reject the retired shortcut instead of keeping a second prediction owner."""
        reject_weak_forecast_entrypoint()

    @staticmethod
    def write_canonical(*_args, **_kwargs) -> None:
        raise PermissionError("Guard artifacts are advisory only")


__all__ = ["GuardArtifact", "GuardBridge"]
