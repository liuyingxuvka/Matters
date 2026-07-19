"""Privacy-safe, metadata-first filesystem provider."""

from .adapter import (
    FilesystemBinaryRead,
    FilesystemCursorError,
    FilesystemDiscoveryPage,
    FilesystemOccurrence,
    FilesystemReadOnlyAdapter,
    FilesystemReadResult,
    FilesystemResourceLimit,
    HardExclusionPolicy,
)

__all__ = [
    "FilesystemBinaryRead",
    "FilesystemCursorError",
    "FilesystemDiscoveryPage",
    "FilesystemOccurrence",
    "FilesystemReadOnlyAdapter",
    "FilesystemReadResult",
    "FilesystemResourceLimit",
    "HardExclusionPolicy",
]
