"""C8: waiting objects, closure conditions, and scoped blocking."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from matters.domain.hierarchy import normalize_semantic_role_key


@dataclass(frozen=True)
class OpenLoop:
    loop_id: str
    matter_id: str
    wait_target: str
    closure_condition: str
    critical: bool = False
    status: str = "open"
    evidence_ids: tuple[str, ...] = ()
    semantic_role_key: str = ""
    deleted: bool = False
    superseded_by: str = ""
    retirement_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "semantic_role_key",
            normalize_semantic_role_key(self.semantic_role_key),
        )
        if self.deleted and (
            not self.superseded_by or not self.retirement_reason.strip()
        ):
            raise ValueError(
                "retired open loop requires its replacement and reason"
            )


@dataclass(frozen=True)
class BlockingDecision:
    scope: str
    reason: str
    loop_id: str = ""


@dataclass
class OpenLoopOwner:
    _loops: dict[str, OpenLoop] = field(default_factory=dict)

    @staticmethod
    def build(
        *,
        loop_id: str,
        matter_id: str,
        wait_target: str,
        closure_condition: str,
        critical: bool = False,
        evidence_ids: tuple[str, ...] = (),
        semantic_role_key: str = "",
    ) -> OpenLoop | None:
        if not wait_target or not closure_condition:
            return None
        return OpenLoop(
            loop_id,
            matter_id,
            wait_target,
            closure_condition,
            critical,
            "open",
            evidence_ids,
            semantic_role_key,
        )

    def remember(self, loop: OpenLoop) -> OpenLoop:
        self._loops[loop.loop_id] = loop
        return loop

    def create(
        self,
        *,
        loop_id: str,
        matter_id: str,
        wait_target: str,
        closure_condition: str,
        critical: bool = False,
        evidence_ids: tuple[str, ...] = (),
        semantic_role_key: str = "",
    ) -> OpenLoop | None:
        loop = self.build(
            loop_id=loop_id,
            matter_id=matter_id,
            wait_target=wait_target,
            closure_condition=closure_condition,
            critical=critical,
            evidence_ids=evidence_ids,
            semantic_role_key=semantic_role_key,
        )
        if loop is None:
            return None
        return self.remember(loop)

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

    def retire(
        self,
        loop_id: str,
        *,
        superseded_by: str,
        reason: str,
    ) -> OpenLoop:
        loop = self._loops[loop_id]
        retired = replace(
            loop,
            deleted=True,
            superseded_by=superseded_by,
            retirement_reason=reason,
        )
        self._loops[loop_id] = retired
        return retired


__all__ = ["BlockingDecision", "OpenLoop", "OpenLoopOwner"]
