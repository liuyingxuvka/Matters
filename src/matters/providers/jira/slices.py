"""Fail-closed sequencing for the ten bounded Jira evaluation slices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from matters.providers.jira.contracts import (
    JiraAuthorizationManifest,
    JiraSliceCoverageReceipt,
)
from matters.providers.jira.depth import MatterDepthReport


SLICE_ORDER = tuple(f"J{index}" for index in range(1, 11))
SLICE_DECISIONS = frozenset({"GO", "HOLD", "ABORT"})


@dataclass(frozen=True)
class SliceDecisionRecord:
    slice_id: str
    decision: str
    coverage_receipt_id: str
    depth_report_id: str
    user_decision_id: str

    def __post_init__(self) -> None:
        if self.slice_id not in SLICE_ORDER:
            raise ValueError("slice_id must be J1 through J10")
        if self.decision not in SLICE_DECISIONS:
            raise ValueError("decision must be GO, HOLD, or ABORT")
        if not self.user_decision_id:
            raise ValueError("an explicit user decision id is required")


@dataclass(frozen=True)
class SlicePreflight:
    slice_id: str
    status: str
    read_allowed: bool
    blockers: tuple[str, ...]
    claim_boundary: str


class JiraSliceGate:
    """DPF-owned gate evaluator. It performs no provider I/O."""

    def preflight(
        self,
        *,
        slice_id: str,
        g8_current: bool,
        authorization: JiraAuthorizationManifest | None,
        prior_decisions: tuple[SliceDecisionRecord, ...] = (),
        as_of: datetime | None = None,
    ) -> SlicePreflight:
        if slice_id not in SLICE_ORDER:
            raise ValueError("slice_id must be J1 through J10")
        blockers: list[str] = []
        if not g8_current:
            blockers.append("g8_not_current")
        if authorization is None:
            blockers.append("explicit_authorization_missing")
        else:
            blockers.extend(authorization.blockers(as_of=as_of))
        index = SLICE_ORDER.index(slice_id)
        required_prior = SLICE_ORDER[:index]
        by_slice = {row.slice_id: row for row in prior_decisions}
        for prior_slice in required_prior:
            row = by_slice.get(prior_slice)
            if row is None:
                blockers.append(f"prior_slice_not_run:{prior_slice}")
            elif row.decision != "GO":
                blockers.append(
                    f"prior_slice_not_go:{prior_slice}:{row.decision}"
                )
        return SlicePreflight(
            slice_id=slice_id,
            status="ready" if not blockers else "not_run",
            read_allowed=not blockers,
            blockers=tuple(blockers),
            claim_boundary=(
                "ready licenses only one bounded read for this slice. It does "
                "not prove provider coverage, product correctness, privacy, "
                "depth, user GO, or eligibility of any later slice."
            ),
        )

    def validate_user_decision(
        self,
        *,
        decision: str,
        coverage_receipt: JiraSliceCoverageReceipt,
        depth_report: MatterDepthReport,
        user_decision_id: str,
    ) -> SliceDecisionRecord:
        if decision not in SLICE_DECISIONS:
            raise ValueError("decision must be GO, HOLD, or ABORT")
        if decision == "GO":
            blockers = []
            if coverage_receipt.test_result != "pass":
                blockers.append("test_result_not_pass")
            if coverage_receipt.privacy_scan_status != "pass":
                blockers.append("privacy_scan_not_pass")
            if not depth_report.analysis_complete:
                blockers.extend(
                    f"depth_incomplete:{layer}"
                    for layer in depth_report.blocking_layers
                )
            if blockers:
                raise ValueError("GO is not licensed: " + ",".join(blockers))
        return SliceDecisionRecord(
            slice_id=coverage_receipt.slice_id,
            decision=decision,
            coverage_receipt_id=coverage_receipt.experiment_id,
            depth_report_id=depth_report.case_ref_hash,
            user_decision_id=user_decision_id,
        )


__all__ = [
    "JiraSliceGate",
    "SLICE_DECISIONS",
    "SLICE_ORDER",
    "SliceDecisionRecord",
    "SlicePreflight",
]
