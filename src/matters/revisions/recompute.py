"""Durable original-owner recomputation and terminal join."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from matters.infrastructure.jobs.runner import DurableWorkQueue, WorkItem
from matters.revisions.corrections import RecomputeRequest


@dataclass(frozen=True)
class RecomputeBatch:
    revision_id: str
    job_ids: tuple[str, ...]
    status: str
    failed_job_ids: tuple[str, ...] = ()


class OriginalOwnerRecompute:
    def __init__(self, queue: DurableWorkQueue):
        self.queue = queue

    def submit(
        self,
        requests: tuple[RecomputeRequest, ...],
    ) -> RecomputeBatch:
        if not requests:
            raise ValueError("at least one original-owner request is required")
        revision_ids = {item.revision_id for item in requests}
        if len(revision_ids) != 1:
            raise ValueError("a recompute batch must bind one revision")
        revision_id = next(iter(revision_ids))
        job_ids: list[str] = []
        for request in requests:
            job_id = f"recompute:{revision_id}:{request.owner_model_id}"
            self.queue.enqueue(
                job_id=job_id,
                owner_id=request.owner_model_id,
                payload={
                    "revision_id": revision_id,
                    "owner_model_id": request.owner_model_id,
                    "dependent_ids": request.dependent_ids,
                },
            )
            job_ids.append(job_id)
        return RecomputeBatch(revision_id, tuple(job_ids), "queued")

    def run_to_terminal(self, batch: RecomputeBatch) -> RecomputeBatch:
        while True:
            items = tuple(self.queue.status(job_id) for job_id in batch.job_ids)
            if any(item is None for item in items):
                raise RuntimeError("recompute job disappeared")
            concrete = tuple(item for item in items if item is not None)
            if all(item.status in {"passed", "failed", "cancelled"} for item in concrete):
                failed = tuple(
                    item.job_id
                    for item in concrete
                    if item.status != "passed"
                )
                return RecomputeBatch(
                    revision_id=batch.revision_id,
                    job_ids=batch.job_ids,
                    status="passed" if not failed else "failed",
                    failed_job_ids=failed,
                )
            progressed = self.queue.run_next()
            if progressed is None:
                return RecomputeBatch(
                    revision_id=batch.revision_id,
                    job_ids=batch.job_ids,
                    status="blocked",
                    failed_job_ids=tuple(
                        item.job_id
                        for item in concrete
                        if item.status != "passed"
                    ),
                )


__all__ = ["OriginalOwnerRecompute", "RecomputeBatch"]
