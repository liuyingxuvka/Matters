"""Matters public package."""

from matters.application.orchestrator import MatterService, SourceProcessingResult
from matters._version import VERSION

__all__ = ["MatterService", "SourceProcessingResult"]
__version__ = VERSION
