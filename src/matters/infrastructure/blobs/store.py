"""External-root immutable blob store."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from matters.infrastructure.capability_status.status import validate_private_root


class BlobStore:
    def __init__(self, private_root: Path, repository_root: Path):
        status = validate_private_root(private_root, repository_root)
        if status.status != "active":
            raise ValueError(status.reason)
        self.root = private_root / "blobs"
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes) -> str:
        digest = sha256(content).hexdigest()
        path = self.root / digest
        if not path.exists():
            path.write_bytes(content)
        return "sha256:" + digest

    def get(self, blob_ref: str) -> bytes:
        """Read one immutable private blob by its opaque content reference."""

        if not blob_ref.startswith("sha256:"):
            raise ValueError("unsupported blob reference")
        digest = blob_ref.removeprefix("sha256:")
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("malformed blob reference")
        path = self.root / digest
        if not path.is_file():
            raise KeyError("private blob is unavailable")
        return path.read_bytes()


__all__ = ["BlobStore"]
