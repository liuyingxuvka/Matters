"""C8: waiting objects, closure conditions, and scoped blocking."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class OpenLoop:
    loop_id: str
    matter_id: str
    wait_target: str
    closure_condition: str
    critical: bool = False
    status: str = "open"
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlockingDecision:
    scope: str
    reason: str
    loop_id: str = ""


@dataclass
class OpenLoopOwner:
    _loops: dict[str, OpenLoop] = field(default_factory=dict)

    def create(
        self,
        *,
        loop_id: str,
        matter_id: str,
        wait_target: str,
        closure_condition: str,
        critical: bool = False,
        evidence_ids: tuple[str, ...] = (),
    ) -> OpenLoop | None:
        if not wait_target or not closure_condition:
            return None
        loop = OpenLoop(
            loop_id,
            matter_id,
            wait_target,
            closure_condition,
            critical,
            "open",
            evidence_ids,
        )
        self._loops[loop_id] = loop
        return loop

    @staticmethod
    def blocking(loop: OpenLoop | None) -> BlockingDecision:
        if loop is None:
            return BlockingDecision(
                "open_loop_gap",
                "wait target or closure condition is not yet evidenced",
            )
        return BlockingDecision(
            "full" if loop.critical else "partial",
            "critical dependency is open" if loop.critical else "noncritical wait is open",
            loop.loop_id,
        )

    def close(
        self,
        loop_id: str,
        *,
        closure_evidence_ids: tuple[str, ...] = (),
        user_decision: bool = False,
    ) -> OpenLoop:
        loop = self._loops[loop_id]
        if not closure_evidence_ids and not user_decision:
            return loop
        closed = replace(
            loop,
            status="closed",
            evidence_ids=loop.evidence_ids + closure_evidence_ids,
        )
        self._loops[loop_id] = closed
        return closed


__all__ = ["BlockingDecision", "OpenLoop", "OpenLoopOwner"]
