"""Jira read-only adapter and bounded evaluation contracts."""

from matters.providers.jira.adapter import JiraReadOnlyAdapter
from matters.providers.jira.contracts import (
    JiraAuthorizationManifest,
    JiraSliceCoverageReceipt,
    ObjectTypeCoverage,
)
from matters.providers.jira.depth import DepthLayer, MatterDepthReport
from matters.providers.jira.slices import (
    JiraSliceGate,
    SliceDecisionRecord,
)

__all__ = [
    "DepthLayer",
    "JiraAuthorizationManifest",
    "JiraReadOnlyAdapter",
    "JiraSliceCoverageReceipt",
    "JiraSliceGate",
    "MatterDepthReport",
    "ObjectTypeCoverage",
    "SliceDecisionRecord",
]
