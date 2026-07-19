"""Optional cloud-source provider with explicit capability state."""

from .adapter import (
    CloudAuthorizedPage,
    CloudCapability,
    CloudDiscoveryItem,
    CloudDiscoveryPage,
    CloudOccurrence,
    CloudPageRejected,
    CloudReadManifest,
    CloudReadOnlyAdapter,
)

__all__ = [
    "CloudAuthorizedPage",
    "CloudCapability",
    "CloudDiscoveryItem",
    "CloudDiscoveryPage",
    "CloudOccurrence",
    "CloudPageRejected",
    "CloudReadManifest",
    "CloudReadOnlyAdapter",
]
