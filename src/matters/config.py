"""Runtime configuration with a hard public/private filesystem boundary."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from matters.infrastructure.capability_status.status import (
    CapabilityStatus,
    validate_private_root,
)


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved runtime roots.

    An absent private root is a valid package-health state, but it is not an
    activated private runtime.  Resolution never creates directories.
    """

    repository_root: Path
    private_root: Path | None
    eval_vault: Path | None = None

    @classmethod
    def resolve(
        cls,
        *,
        repository_root: Path,
        private_root: Path | str | None = None,
        eval_vault: Path | str | None = None,
    ) -> "RuntimeConfig":
        home_value = private_root or os.environ.get("MATTERS_HOME")
        vault_value = eval_vault or os.environ.get("MATTERS_EVAL_VAULT")
        return cls(
            repository_root=repository_root.resolve(),
            private_root=(
                Path(home_value).expanduser().resolve() if home_value else None
            ),
            eval_vault=(
                Path(vault_value).expanduser().resolve() if vault_value else None
            ),
        )

    def private_status(self) -> CapabilityStatus:
        if self.private_root is None:
            return CapabilityStatus(
                "private_root",
                "not_configured",
                "MATTERS_HOME is not configured; private sources are disabled",
            )
        return validate_private_root(self.private_root, self.repository_root)

    def eval_status(self) -> CapabilityStatus:
        if self.eval_vault is None:
            return CapabilityStatus(
                "eval_vault",
                "not_configured",
                "MATTERS_EVAL_VAULT is not configured",
            )
        status = validate_private_root(self.eval_vault, self.repository_root)
        return CapabilityStatus("eval_vault", status.status, status.reason)

    def activate_private_root(self) -> Path:
        status = self.private_status()
        if status.status != "active" or self.private_root is None:
            raise ValueError(status.reason)
        self.private_root.mkdir(parents=True, exist_ok=True)
        return self.private_root


__all__ = ["RuntimeConfig"]
