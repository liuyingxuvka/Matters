"""Model-miss handoff from runtime evidence to the explicit development pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.jobs.runner import DurableWorkQueue
    from matters.infrastructure.sqlite.store import SQLiteStore


@dataclass(frozen=True)
class ModelMissWorkItem:
    miss_id: str
    failure_class: str
    expected_behavior: str
    observed_behavior: str
    model_path: str
    private_evidence_handle: str
    current_runtime_disposition: str
    status: str = "development_repair_queued"


@dataclass
class ModelMissOwner:
    store: "SQLiteStore"
    queue: "DurableWorkQueue"

    def report(
        self,
        *,
        failure_class: str,
        expected_behavior: str,
        observed_behavior: str,
        model_path: str,
        private_evidence_handle: str,
        current_runtime_disposition: str,
    ) -> ModelMissWorkItem:
        if not private_evidence_handle.startswith("private-evidence:"):
            raise ValueError("an opaque private evidence handle is required")
        if current_runtime_disposition not in {"partial", "blocked"}:
            raise ValueError("a model miss must keep runtime partial or blocked")
        raw = "\0".join(
            (
                failure_class,
                expected_behavior,
                observed_behavior,
                model_path,
                private_evidence_handle,
            )
        )
        miss_id = "model-miss:" + sha256(raw.encode("utf-8")).hexdigest()[:24]
        item = ModelMissWorkItem(
            miss_id=miss_id,
            failure_class=failure_class,
            expected_behavior=expected_behavior,
            observed_behavior=observed_behavior,
            model_path=model_path,
            private_evidence_handle=private_evidence_handle,
            current_runtime_disposition=current_runtime_disposition,
        )
        if self.store.current("model_miss", miss_id) is None:
            self.store.append("model_miss", miss_id, 1, asdict(item))
        self.queue.enqueue(
            job_id=f"development:{miss_id}",
            owner_id="development_pipeline",
            payload={
                "miss_id": miss_id,
                "failure_class": failure_class,
                "private_evidence_handle": private_evidence_handle,
            },
        )
        return item

    @staticmethod
    def edit_runtime(*_args, **_kwargs) -> None:
        raise PermissionError(
            "runtime model-miss handling cannot edit requirements, models, or code"
        )


__all__ = ["ModelMissOwner", "ModelMissWorkItem"]
