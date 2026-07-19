"""Bounded durable work queue with explicit pause, resume, cancel, and recovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any, Callable, Generic, Mapping, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore

T = TypeVar("T")


@dataclass(frozen=True)
class JobResult(Generic[T]):
    job_id: str
    status: str
    value: T | None = None
    error: str = ""


@dataclass(frozen=True)
class WorkItem:
    job_id: str
    owner_id: str
    payload: Mapping[str, Any]
    status: str = "queued"
    attempt: int = 0
    checkpoint: str = ""
    failure_class: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if self.status not in {
            "queued",
            "running",
            "paused",
            "cancelled",
            "passed",
            "failed",
        }:
            raise ValueError("unsupported work status")
        object.__setattr__(self, "payload", dict(self.payload))


def run_job(job_id: str, work: Callable[[], T]) -> JobResult[T]:
    try:
        return JobResult(job_id, "passed", work())
    except Exception as exc:
        return JobResult(job_id, "failed", error=str(exc))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DurableWorkQueue:
    """One queue owner; final verification is intentionally outside this API."""

    store: "SQLiteStore"
    capacity: int = 1000
    _handlers: dict[str, Callable[[Mapping[str, Any]], Any]] = field(
        default_factory=dict
    )
    _items: dict[str, WorkItem] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    _stop: Event = field(default_factory=Event)
    _thread: Thread | None = None

    def __post_init__(self) -> None:
        for payload in self.store.list_current("work_item"):
            item = WorkItem(**dict(payload))
            if item.status == "running":
                item = replace(
                    item,
                    status="queued",
                    failure_class="recovered_after_interrupted_owner",
                    updated_at=_utc_now(),
                )
                self._persist(item)
            self._items[item.job_id] = item

    def register_handler(
        self,
        owner_id: str,
        handler: Callable[[Mapping[str, Any]], Any],
    ) -> None:
        if not owner_id:
            raise ValueError("owner_id is required")
        self._handlers[owner_id] = handler

    def enqueue(
        self,
        *,
        job_id: str,
        owner_id: str,
        payload: Mapping[str, Any],
    ) -> WorkItem:
        with self._lock:
            existing = self._items.get(job_id)
            if existing is not None:
                return existing
            active_count = sum(
                item.status in {"queued", "running", "paused"}
                for item in self._items.values()
            )
            if active_count >= self.capacity:
                raise OverflowError("bounded work queue is full")
            item = WorkItem(
                job_id=job_id,
                owner_id=owner_id,
                payload=dict(payload),
                updated_at=_utc_now(),
            )
            self._items[job_id] = item
            self._persist(item)
            return item

    def status(self, job_id: str) -> WorkItem | None:
        return self._items.get(job_id)

    def list_items(self) -> tuple[WorkItem, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.job_id))

    def pause(self, job_id: str) -> WorkItem:
        return self._transition(job_id, {"queued"}, "paused")

    def resume(self, job_id: str) -> WorkItem:
        return self._transition(job_id, {"paused", "failed"}, "queued")

    def cancel(self, job_id: str) -> WorkItem:
        return self._transition(job_id, {"queued", "paused"}, "cancelled")

    def checkpoint(self, job_id: str, value: str) -> WorkItem:
        with self._lock:
            item = self._require(job_id)
            if item.status != "running":
                raise ValueError("only a running owner can checkpoint work")
            updated = replace(item, checkpoint=value, updated_at=_utc_now())
            self._items[job_id] = updated
            self._persist(updated)
            return updated

    def run_next(self) -> WorkItem | None:
        with self._lock:
            item = next(
                (
                    candidate
                    for candidate in self.list_items()
                    if candidate.status == "queued"
                ),
                None,
            )
            if item is None:
                return None
            handler = self._handlers.get(item.owner_id)
            if handler is None:
                failed = replace(
                    item,
                    status="failed",
                    failure_class="owner_handler_missing",
                    updated_at=_utc_now(),
                )
                self._items[item.job_id] = failed
                self._persist(failed)
                return failed
            running = replace(
                item,
                status="running",
                attempt=item.attempt + 1,
                failure_class="",
                updated_at=_utc_now(),
            )
            self._items[item.job_id] = running
            self._persist(running)
        try:
            handler(dict(running.payload))
            terminal = replace(
                running,
                status="passed",
                checkpoint="terminal",
                updated_at=_utc_now(),
            )
        except Exception as exc:
            terminal = replace(
                running,
                status="failed",
                failure_class=type(exc).__name__,
                updated_at=_utc_now(),
            )
        with self._lock:
            self._items[item.job_id] = terminal
            self._persist(terminal)
        return terminal

    def start_background(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def worker() -> None:
            while not self._stop.is_set():
                item = self.run_next()
                if item is None:
                    self._stop.wait(0.1)

        self._thread = Thread(
            target=worker,
            name="matters-product-work-queue",
            daemon=True,
        )
        self._thread.start()

    def stop_background(self, timeout: float = 5.0) -> bool:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        return not (self._thread and self._thread.is_alive())

    def _transition(
        self,
        job_id: str,
        allowed: set[str],
        target: str,
    ) -> WorkItem:
        with self._lock:
            item = self._require(job_id)
            if item.status not in allowed:
                raise ValueError(
                    f"cannot transition work from {item.status} to {target}"
                )
            updated = replace(item, status=target, updated_at=_utc_now())
            self._items[job_id] = updated
            self._persist(updated)
            return updated

    def _require(self, job_id: str) -> WorkItem:
        try:
            return self._items[job_id]
        except KeyError as exc:
            raise KeyError(f"unknown job_id: {job_id}") from exc

    def _persist(self, item: WorkItem) -> None:
        self.store.append(
            "work_item",
            item.job_id,
            self.store.next_revision("work_item", item.job_id),
            asdict(item),
        )


__all__ = ["DurableWorkQueue", "JobResult", "WorkItem", "run_job"]
