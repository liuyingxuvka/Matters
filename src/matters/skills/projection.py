"""Transactional synchronization for an existing Matters-managed projection.

The filesystem adapter is inert until called with an explicit root.  It never
discovers or chooses a global Codex directory.  Tests exercise it only under a
temporary directory.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
from typing import Callable

from .inventory import InstalledSkill
from .manifest import (
    InstallationPolicy,
    ProjectionFile,
    SkillOrigin,
    SkillProjection,
    projection_content_hash,
)
from .resolver import ActiveSkillDecision


_TRANSACTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MARKER = ".matters-managed.json"


class ManagedProjectionError(RuntimeError):
    pass


class UnmanagedProjectionError(ManagedProjectionError):
    pass


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    verification_identity: str
    reason: str = ""


@dataclass(frozen=True)
class ManagedProjectionReceipt:
    transaction_id: str
    skill_id: str
    status: str
    source_identity: str
    prior_installed_identity: str
    active_identity: str
    staged_verification_identity: str
    installed_currentness_identity: str
    rollback_identity: str
    update_available: bool
    reason: str
    receipt_schema: str = "matters.managed-skill-sync-receipt.v1"

    @property
    def synchronized(self) -> bool:
        return self.status == "installed_current"


Verifier = Callable[[Path, SkillProjection], VerificationResult]


class FilesystemManagedProjectionStore:
    """Filesystem transaction restricted to an explicitly managed skill root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def initialize_managed_projection(self, projection: SkillProjection) -> None:
        """Create an explicitly Matters-managed projection.

        This is a bootstrap primitive, not an automatic resolver action.  The
        synchronizer itself updates only an already marked managed projection.
        """

        if projection.manifest.installation_policy != InstallationPolicy.MATTERS_MANAGED:
            raise UnmanagedProjectionError(
                "initial managed projection requires matters_managed policy"
            )
        active = self._active_path(projection.manifest.skill_id)
        if active.exists():
            raise ManagedProjectionError("managed projection already exists")
        self._write_projection(active, projection)

    def assert_current_managed(self, installed: InstalledSkill) -> str:
        if not installed.matters_managed:
            raise UnmanagedProjectionError("installed inventory entry is not Matters-managed")
        marker = self._read_marker(self._active_path(installed.manifest.skill_id))
        if marker.get("skill_id") != installed.manifest.skill_id:
            raise ManagedProjectionError("managed marker skill identity mismatch")
        expected = installed.manifest.identity.fingerprint
        if marker.get("skill_identity") != expected:
            raise ManagedProjectionError("managed marker does not match inventory identity")
        actual_hash = self._directory_content_hash(
            self._active_path(installed.manifest.skill_id)
        )
        if actual_hash != installed.manifest.content_hash:
            raise ManagedProjectionError("managed projection bytes do not match inventory")
        return expected

    def stage(
        self,
        *,
        transaction_id: str,
        projection: SkillProjection,
    ) -> Path:
        transaction = self._transaction_path(
            projection.manifest.skill_id,
            transaction_id,
        )
        if transaction.exists():
            raise ManagedProjectionError("transaction already exists")
        staged = transaction / "staged"
        self._write_projection(staged, projection)
        return staged

    def verify_projection(
        self,
        path: Path,
        projection: SkillProjection,
    ) -> VerificationResult:
        try:
            marker = self._read_marker(path)
            if marker.get("skill_identity") != projection.manifest.identity.fingerprint:
                return VerificationResult(
                    ok=False,
                    verification_identity="internal:marker-mismatch",
                    reason="projection marker identity mismatch",
                )
            content_hash = self._directory_content_hash(path)
            if content_hash != projection.manifest.content_hash:
                return VerificationResult(
                    ok=False,
                    verification_identity="internal:content-hash-mismatch",
                    reason="projection content hash mismatch",
                )
        except (OSError, ValueError, ManagedProjectionError) as exc:
            return VerificationResult(
                ok=False,
                verification_identity="internal:projection-invalid",
                reason=str(exc),
            )
        return VerificationResult(
            ok=True,
            verification_identity=(
                "internal:"
                + sha256(
                    (
                        projection.manifest.identity.fingerprint
                        + ":"
                        + content_hash
                    ).encode("utf-8")
                ).hexdigest()
            ),
        )

    def activate(
        self,
        *,
        skill_id: str,
        transaction_id: str,
    ) -> Path:
        transaction = self._transaction_path(skill_id, transaction_id)
        staged = transaction / "staged"
        prior = transaction / "prior"
        active = self._active_path(skill_id)
        if not staged.is_dir() or not active.is_dir() or prior.exists():
            raise ManagedProjectionError("transaction activation inputs are incomplete")
        os.replace(active, prior)
        try:
            os.replace(staged, active)
        except BaseException:
            os.replace(prior, active)
            raise
        return active

    def restore(self, *, skill_id: str, transaction_id: str) -> str:
        transaction = self._transaction_path(skill_id, transaction_id)
        prior = transaction / "prior"
        active = self._active_path(skill_id)
        if not prior.is_dir():
            raise ManagedProjectionError("prior managed projection is unavailable")
        failed_identity = ""
        if active.exists():
            marker = self._read_marker(active)
            failed_identity = str(marker.get("skill_identity", ""))
            self._remove_tree(active)
        os.replace(prior, active)
        restored = self._read_marker(active)
        return _portable_rollback_identity(
            restored_identity=str(restored.get("skill_identity", "")),
            failed_identity=failed_identity,
            transaction_id=transaction_id,
        )

    def finish(self, *, skill_id: str, transaction_id: str) -> None:
        transaction = self._transaction_path(skill_id, transaction_id)
        if transaction.exists():
            self._remove_tree(transaction)
        parent = transaction.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()

    def active_path(self, skill_id: str) -> Path:
        return self._active_path(skill_id)

    def _write_projection(self, destination: Path, projection: SkillProjection) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()
        try:
            for row in projection.files:
                target = self._contained(destination, row.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(row.content)
            marker = {
                "schema": "matters.managed-skill-projection-marker.v1",
                "owner": "matters",
                "skill_id": projection.manifest.skill_id,
                "skill_identity": projection.manifest.identity.fingerprint,
                "content_hash": projection.manifest.content_hash,
                "manifest": projection.manifest.canonical(),
            }
            (destination / _MARKER).write_text(
                json.dumps(
                    marker,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except BaseException:
            if destination.exists():
                self._remove_tree(destination)
            raise

    def _directory_content_hash(self, directory: Path) -> str:
        rows: list[ProjectionFile] = []
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ManagedProjectionError("links are forbidden in managed projections")
            if not path.is_file() or path.name == _MARKER:
                continue
            relative = path.relative_to(directory).as_posix()
            rows.append(ProjectionFile(path=relative, content=path.read_bytes()))
        if not rows:
            raise ManagedProjectionError("managed projection contains no consumer files")
        return projection_content_hash(rows)

    def _read_marker(self, directory: Path) -> dict[str, object]:
        marker_path = directory / _MARKER
        if not marker_path.is_file():
            raise UnmanagedProjectionError("Matters-managed ownership marker is missing")
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
        if (
            payload.get("schema") != "matters.managed-skill-projection-marker.v1"
            or payload.get("owner") != "matters"
        ):
            raise UnmanagedProjectionError("managed ownership marker is invalid")
        return payload

    def _active_path(self, skill_id: str) -> Path:
        if not skill_id or "/" in skill_id or "\\" in skill_id or ".." in skill_id:
            raise ValueError("skill_id is not path-safe")
        return self._contained(self.root, f"{skill_id}/active")

    def _transaction_path(self, skill_id: str, transaction_id: str) -> Path:
        if not _TRANSACTION_ID.fullmatch(transaction_id):
            raise ValueError("transaction_id is not path-safe")
        return self._contained(
            self.root,
            f"{skill_id}/.transactions/{transaction_id}",
        )

    @staticmethod
    def _contained(root: Path, relative: str) -> Path:
        candidate = (root / Path(relative)).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("projection path escapes the configured managed root")
        return candidate

    def _remove_tree(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved == self.root or self.root not in resolved.parents:
            raise ManagedProjectionError("refusing to remove outside the managed root")
        shutil.rmtree(resolved)


class ManagedProjectionSynchronizer:
    """Stage, verify, activate, verify installed currentness, then commit/restore."""

    def __init__(self, store: FilesystemManagedProjectionStore) -> None:
        self.store = store

    def synchronize(
        self,
        *,
        transaction_id: str,
        decision: ActiveSkillDecision,
        installed: InstalledSkill,
        projection: SkillProjection,
        staged_validator: Verifier,
        installed_currentness_validator: Verifier,
    ) -> ManagedProjectionReceipt:
        source_identity = projection.manifest.identity.fingerprint
        prior_identity = installed.manifest.identity.fingerprint
        if not decision.sync_required:
            if decision.update_available and not installed.matters_managed:
                status = "unmanaged_unchanged"
                reason = "external machine-installed projection is not mutation-authorized"
            else:
                status = "no_delta"
                reason = "active-view decision does not require managed synchronization"
            return ManagedProjectionReceipt(
                transaction_id=transaction_id,
                skill_id=projection.manifest.skill_id,
                status=status,
                source_identity=source_identity,
                prior_installed_identity=prior_identity,
                active_identity=prior_identity,
                staged_verification_identity="",
                installed_currentness_identity="",
                rollback_identity="",
                update_available=decision.update_available,
                reason=reason,
            )
        if not installed.matters_managed:
            return ManagedProjectionReceipt(
                transaction_id=transaction_id,
                skill_id=projection.manifest.skill_id,
                status="unmanaged_unchanged",
                source_identity=source_identity,
                prior_installed_identity=prior_identity,
                active_identity=prior_identity,
                staged_verification_identity="",
                installed_currentness_identity="",
                rollback_identity="",
                update_available=True,
                reason="unmanaged projection rejected before any filesystem write",
            )
        self._validate_request(
            decision=decision,
            installed=installed,
            projection=projection,
        )
        self.store.assert_current_managed(installed)
        target_projection = matters_managed_projection(projection)
        target_identity = target_projection.manifest.identity.fingerprint

        staged_identity = ""
        installed_identity = ""
        activated = False
        activation_validated = False
        try:
            staged = self.store.stage(
                transaction_id=transaction_id,
                projection=target_projection,
            )
            internal_stage = self.store.verify_projection(staged, target_projection)
            if not internal_stage.ok:
                self.store.finish(
                    skill_id=projection.manifest.skill_id,
                    transaction_id=transaction_id,
                )
                return self._blocked_before_activation(
                    transaction_id=transaction_id,
                    source_projection=projection,
                    prior_identity=prior_identity,
                    verification=internal_stage,
                )
            staged_result = staged_validator(staged, target_projection)
            staged_identity = staged_result.verification_identity
            if not staged_result.ok:
                self.store.finish(
                    skill_id=projection.manifest.skill_id,
                    transaction_id=transaction_id,
                )
                return self._blocked_before_activation(
                    transaction_id=transaction_id,
                    source_projection=projection,
                    prior_identity=prior_identity,
                    verification=staged_result,
                )

            active = self.store.activate(
                skill_id=projection.manifest.skill_id,
                transaction_id=transaction_id,
            )
            activated = True
            internal_active = self.store.verify_projection(active, target_projection)
            if not internal_active.ok:
                return self._restore_after_failure(
                    transaction_id=transaction_id,
                    source_projection=projection,
                    prior_identity=prior_identity,
                    staged_identity=staged_identity,
                    installed_result=internal_active,
                )
            installed_result = installed_currentness_validator(
                active,
                target_projection,
            )
            installed_identity = installed_result.verification_identity
            if not installed_result.ok:
                return self._restore_after_failure(
                    transaction_id=transaction_id,
                    source_projection=projection,
                    prior_identity=prior_identity,
                    staged_identity=staged_identity,
                    installed_result=installed_result,
                )
            activation_validated = True
            self.store.finish(
                skill_id=projection.manifest.skill_id,
                transaction_id=transaction_id,
            )
            return ManagedProjectionReceipt(
                transaction_id=transaction_id,
                skill_id=projection.manifest.skill_id,
                status="installed_current",
                source_identity=source_identity,
                prior_installed_identity=prior_identity,
                active_identity=target_identity,
                staged_verification_identity=staged_identity,
                installed_currentness_identity=installed_identity,
                rollback_identity="",
                update_available=False,
                reason="managed projection staged, validated, activated, and revalidated",
            )
        except Exception as exc:
            rollback_identity = ""
            status = "blocked_before_activation"
            if activation_validated:
                status = "installed_current_cleanup_failed"
            elif activated:
                try:
                    rollback_identity = self.store.restore(
                        skill_id=projection.manifest.skill_id,
                        transaction_id=transaction_id,
                    )
                    status = "restored"
                except BaseException as rollback_exc:
                    status = "rollback_failed"
                    exc = ManagedProjectionError(
                        f"{type(exc).__name__}; rollback:{type(rollback_exc).__name__}"
                    )
            if status != "rollback_failed":
                try:
                    self.store.finish(
                        skill_id=projection.manifest.skill_id,
                        transaction_id=transaction_id,
                    )
                except Exception:
                    if status == "restored":
                        status = "restored_cleanup_pending"
            return ManagedProjectionReceipt(
                transaction_id=transaction_id,
                skill_id=projection.manifest.skill_id,
                status=status,
                source_identity=source_identity,
                prior_installed_identity=prior_identity,
                active_identity=(
                    source_identity
                    if status == "installed_current_cleanup_failed"
                    else prior_identity
                    if status in {"restored", "restored_cleanup_pending"}
                    else ""
                ),
                staged_verification_identity=staged_identity,
                installed_currentness_identity=installed_identity,
                rollback_identity=rollback_identity,
                update_available=False,
                reason=f"managed synchronization failed:{type(exc).__name__}",
            )

    @staticmethod
    def _validate_request(
        *,
        decision: ActiveSkillDecision,
        installed: InstalledSkill,
        projection: SkillProjection,
    ) -> None:
        if decision.status != "current" or decision.selected_identity is None:
            raise ManagedProjectionError("managed synchronization requires a current selection")
        if decision.disposition != "bundled_managed_sync_required":
            raise ManagedProjectionError("active-view decision does not authorize synchronization")
        if projection.manifest.origin != SkillOrigin.BUNDLED:
            raise ManagedProjectionError("managed synchronization source must be bundled")
        if decision.selected_identity.fingerprint != projection.manifest.identity.fingerprint:
            raise ManagedProjectionError("projection does not match selected active identity")
        if installed.manifest.skill_id != projection.manifest.skill_id:
            raise ManagedProjectionError("installed and selected skill ids differ")

    @staticmethod
    def _blocked_before_activation(
        *,
        transaction_id: str,
        source_projection: SkillProjection,
        prior_identity: str,
        verification: VerificationResult,
    ) -> ManagedProjectionReceipt:
        return ManagedProjectionReceipt(
            transaction_id=transaction_id,
            skill_id=source_projection.manifest.skill_id,
            status="blocked_before_activation",
            source_identity=source_projection.manifest.identity.fingerprint,
            prior_installed_identity=prior_identity,
            active_identity=prior_identity,
            staged_verification_identity=verification.verification_identity,
            installed_currentness_identity="",
            rollback_identity="",
            update_available=False,
            reason=verification.reason or "staged validation failed",
        )

    def _restore_after_failure(
        self,
        *,
        transaction_id: str,
        source_projection: SkillProjection,
        prior_identity: str,
        staged_identity: str,
        installed_result: VerificationResult,
    ) -> ManagedProjectionReceipt:
        rollback_identity = self.store.restore(
            skill_id=source_projection.manifest.skill_id,
            transaction_id=transaction_id,
        )
        status = "restored"
        try:
            self.store.finish(
                skill_id=source_projection.manifest.skill_id,
                transaction_id=transaction_id,
            )
        except Exception:
            status = "restored_cleanup_pending"
        return ManagedProjectionReceipt(
            transaction_id=transaction_id,
            skill_id=source_projection.manifest.skill_id,
            status=status,
            source_identity=source_projection.manifest.identity.fingerprint,
            prior_installed_identity=prior_identity,
            active_identity=prior_identity,
            staged_verification_identity=staged_identity,
            installed_currentness_identity=installed_result.verification_identity,
            rollback_identity=rollback_identity,
            update_available=False,
            reason=installed_result.reason or "post-activation validation failed",
        )


def matters_managed_projection(source: SkillProjection) -> SkillProjection:
    """Project bundled consumer bytes into the machine-installed managed layer."""

    if source.manifest.origin != SkillOrigin.BUNDLED:
        raise ManagedProjectionError("managed projection source must be bundled")
    target_manifest = replace(
        source.manifest,
        origin=SkillOrigin.MACHINE_INSTALLED,
        installation_policy=InstallationPolicy.MATTERS_MANAGED,
    )
    return SkillProjection(manifest=target_manifest, files=source.files)


def _portable_rollback_identity(
    *,
    restored_identity: str,
    failed_identity: str,
    transaction_id: str,
) -> str:
    payload = json.dumps(
        {
            "restored_identity": restored_identity,
            "failed_identity": failed_identity,
            "transaction_id": transaction_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + sha256(payload).hexdigest()


__all__ = [
    "FilesystemManagedProjectionStore",
    "ManagedProjectionError",
    "ManagedProjectionReceipt",
    "ManagedProjectionSynchronizer",
    "UnmanagedProjectionError",
    "VerificationResult",
    "matters_managed_projection",
]
