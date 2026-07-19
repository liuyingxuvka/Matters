"""Guard receipt freshness predicates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardReceipt:
    receipt_id: str
    result_status: str
    source_revision: str
    model_revision: str
    current_source_revision: str
    current_model_revision: str
    progress_only: bool = False

    @property
    def current(self) -> bool:
        return (
            self.result_status == "passed"
            and not self.progress_only
            and self.source_revision == self.current_source_revision
            and self.model_revision == self.current_model_revision
        )


__all__ = ["GuardReceipt"]
