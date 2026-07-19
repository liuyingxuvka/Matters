"""Read-only Gmail provider for already-authorized page results."""

from .adapter import (
    GmailAttachmentMetadata,
    GmailAuthorizedPage,
    GmailDiscoveryItem,
    GmailDiscoveryPage,
    GmailMessageContent,
    GmailMessageMetadata,
    GmailPageRejected,
    GmailReadManifest,
    GmailReadOnlyAdapter,
    GmailReadResult,
    GmailSourceUnavailable,
)

__all__ = [
    "GmailAttachmentMetadata",
    "GmailAuthorizedPage",
    "GmailDiscoveryItem",
    "GmailDiscoveryPage",
    "GmailMessageContent",
    "GmailMessageMetadata",
    "GmailPageRejected",
    "GmailReadManifest",
    "GmailReadOnlyAdapter",
    "GmailReadResult",
    "GmailSourceUnavailable",
]
