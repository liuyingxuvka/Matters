"""Pure contracts for the packaged Windows shell and transactional install.

This module performs no installation and launches no process.  It gives a
native shell/packager and the installer one shared, portable identity and
release gate so the browser-development wrapper cannot be mistaken for the
installed product.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from packaging.version import Version


BROWSER_DEVELOPMENT_SHELL = "browser_development"
PACKAGED_WINDOWS_WEBVIEW_SHELL = "packaged_windows_webview"
SUPPORTED_SHELL_KINDS = frozenset(
    {
        BROWSER_DEVELOPMENT_SHELL,
        PACKAGED_WINDOWS_WEBVIEW_SHELL,
    }
)
INSTALL_STAGES = (
    "snapshot_prior_install",
    "stage_candidate_package",
    "verify_staged_package",
    "activate_candidate",
    "verify_installed_currentness",
    "publish_application_shortcuts",
    "publish_install_receipt",
)
ROLLBACK_STAGES = (
    "remove_failed_candidate",
    "restore_prior_package",
    "restore_prior_shortcuts",
    "restore_prior_install_receipt",
    "verify_restored_identity",
)

_SHA256_IDENTITY = re.compile(r"^sha256:[0-9a-f]{64}$")
_PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not _SHA256_IDENTITY.fullmatch(value):
        raise ValueError(f"{name} must be a portable sha256 identity")


def _require_portable_id(name: str, value: str) -> None:
    if not _PORTABLE_ID.fullmatch(value):
        raise ValueError(f"{name} must be an opaque portable identity")


@dataclass(frozen=True)
class DesktopPackageManifest:
    application_id: str
    matters_version: str
    shell_kind: str
    package_sha256: str
    executable_sha256: str
    build_toolchain_sha256: str
    ui_bundle_sha256: str
    icon_sha256: str
    service_contract_identity: str
    worker_contract_identity: str
    skill_pack_identity: str
    available_locales: tuple[str, ...]
    loopback_only: bool
    owns_application_window: bool
    packaged_ui: bool
    private_shell_profile: bool
    persists_locale_density_window_state: bool
    startup_health_gate: bool
    in_shell_recovery_surface: bool
    clean_owned_process_shutdown: bool
    manifest_fingerprint: str

    def __post_init__(self) -> None:
        _require_portable_id("application_id", self.application_id)
        Version(self.matters_version)
        if self.shell_kind not in SUPPORTED_SHELL_KINDS:
            raise ValueError("unsupported desktop shell kind")
        for name, value in (
            ("package_sha256", self.package_sha256),
            ("executable_sha256", self.executable_sha256),
            ("build_toolchain_sha256", self.build_toolchain_sha256),
            ("ui_bundle_sha256", self.ui_bundle_sha256),
            ("icon_sha256", self.icon_sha256),
        ):
            _require_sha256(name, value)
        for name, value in (
            ("service_contract_identity", self.service_contract_identity),
            ("worker_contract_identity", self.worker_contract_identity),
            ("skill_pack_identity", self.skill_pack_identity),
        ):
            _require_portable_id(name, value)
        if (
            not isinstance(self.available_locales, tuple)
            or not self.available_locales
            or any(not isinstance(item, str) or not item for item in self.available_locales)
            or len(set(self.available_locales)) != len(self.available_locales)
        ):
            raise ValueError("desktop locales must be a non-empty unique tuple")
        for name in (
            "loopback_only",
            "owns_application_window",
            "packaged_ui",
            "private_shell_profile",
            "persists_locale_density_window_state",
            "startup_health_gate",
            "in_shell_recovery_surface",
            "clean_owned_process_shutdown",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")
        payload = {
            key: value
            for key, value in asdict(self).items()
            if key != "manifest_fingerprint"
        }
        if self.manifest_fingerprint != _fingerprint(payload):
            raise ValueError("desktop package manifest fingerprint is invalid")

    @classmethod
    def create(
        cls,
        *,
        application_id: str,
        matters_version: str,
        shell_kind: str,
        package_sha256: str,
        executable_sha256: str,
        build_toolchain_sha256: str,
        ui_bundle_sha256: str,
        icon_sha256: str,
        service_contract_identity: str,
        worker_contract_identity: str,
        skill_pack_identity: str,
        available_locales: tuple[str, ...] = ("en", "zh-CN"),
        loopback_only: bool = True,
        owns_application_window: bool = True,
        packaged_ui: bool = True,
        private_shell_profile: bool = True,
        persists_locale_density_window_state: bool = True,
        startup_health_gate: bool = True,
        in_shell_recovery_surface: bool = True,
        clean_owned_process_shutdown: bool = True,
    ) -> "DesktopPackageManifest":
        _require_portable_id("application_id", application_id)
        Version(matters_version)
        if shell_kind not in SUPPORTED_SHELL_KINDS:
            raise ValueError("unsupported desktop shell kind")
        _require_sha256("package_sha256", package_sha256)
        _require_sha256("executable_sha256", executable_sha256)
        _require_sha256("build_toolchain_sha256", build_toolchain_sha256)
        _require_sha256("ui_bundle_sha256", ui_bundle_sha256)
        _require_sha256("icon_sha256", icon_sha256)
        for name, value in (
            ("service_contract_identity", service_contract_identity),
            ("worker_contract_identity", worker_contract_identity),
            ("skill_pack_identity", skill_pack_identity),
        ):
            _require_portable_id(name, value)
        locales = tuple(available_locales)
        if (
            not locales
            or any(not isinstance(item, str) or not item for item in locales)
            or len(set(locales)) != len(locales)
        ):
            raise ValueError("desktop locales must be non-empty and unique")
        payload: dict[str, Any] = {
            "application_id": application_id,
            "matters_version": matters_version,
            "shell_kind": shell_kind,
            "package_sha256": package_sha256,
            "executable_sha256": executable_sha256,
            "build_toolchain_sha256": build_toolchain_sha256,
            "ui_bundle_sha256": ui_bundle_sha256,
            "icon_sha256": icon_sha256,
            "service_contract_identity": service_contract_identity,
            "worker_contract_identity": worker_contract_identity,
            "skill_pack_identity": skill_pack_identity,
            "available_locales": locales,
            "loopback_only": loopback_only,
            "owns_application_window": owns_application_window,
            "packaged_ui": packaged_ui,
            "private_shell_profile": private_shell_profile,
            "persists_locale_density_window_state": (
                persists_locale_density_window_state
            ),
            "startup_health_gate": startup_health_gate,
            "in_shell_recovery_surface": in_shell_recovery_surface,
            "clean_owned_process_shutdown": clean_owned_process_shutdown,
        }
        return cls(
            **payload,
            manifest_fingerprint=_fingerprint(payload),
        )

    def release_gate_findings(self) -> tuple[str, ...]:
        findings: list[str] = []
        if self.shell_kind != PACKAGED_WINDOWS_WEBVIEW_SHELL:
            findings.append("browser_development_surface_only")
        if "en" not in self.available_locales or "zh-CN" not in self.available_locales:
            findings.append("required_bilingual_locales_missing")
        required_flags = {
            "loopback_only": self.loopback_only,
            "owns_application_window": self.owns_application_window,
            "packaged_ui": self.packaged_ui,
            "private_shell_profile": self.private_shell_profile,
            "persists_locale_density_window_state": (
                self.persists_locale_density_window_state
            ),
            "startup_health_gate": self.startup_health_gate,
            "in_shell_recovery_surface": self.in_shell_recovery_surface,
            "clean_owned_process_shutdown": self.clean_owned_process_shutdown,
        }
        findings.extend(
            f"{name}_missing"
            for name, current in required_flags.items()
            if not current
        )
        return tuple(findings)

    @property
    def release_ready(self) -> bool:
        return not self.release_gate_findings()

    def canonical(self) -> Mapping[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> "DesktopPackageManifest":
        values = dict(payload)
        values["available_locales"] = tuple(values.get("available_locales", ()))
        return cls(**values)


@dataclass(frozen=True)
class DesktopInstallTransactionPlan:
    transaction_id: str
    candidate_manifest_fingerprint: str
    prior_install_identity: str
    active_slot_id: str
    receipt_id: str
    stages: tuple[str, ...]
    rollback_stages: tuple[str, ...]
    rollback_required_after_activation: bool
    plan_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("transaction_id", self.transaction_id),
            ("active_slot_id", self.active_slot_id),
            ("receipt_id", self.receipt_id),
        ):
            _require_portable_id(name, value)
        _require_sha256(
            "candidate_manifest_fingerprint",
            self.candidate_manifest_fingerprint,
        )
        if self.prior_install_identity:
            _require_sha256(
                "prior_install_identity",
                self.prior_install_identity,
            )
        if self.stages != INSTALL_STAGES or self.rollback_stages != ROLLBACK_STAGES:
            raise ValueError("desktop install transaction stages are invalid")
        if self.rollback_required_after_activation is not True:
            raise ValueError("desktop install transaction must require rollback")
        payload = {
            key: value
            for key, value in asdict(self).items()
            if key != "plan_fingerprint"
        }
        if self.plan_fingerprint != _fingerprint(payload):
            raise ValueError("desktop install transaction fingerprint is invalid")

    @classmethod
    def create(
        cls,
        *,
        transaction_id: str,
        candidate: DesktopPackageManifest,
        prior_install_identity: str,
        active_slot_id: str = "matters:user:active",
        receipt_id: str = "matters:user:install-receipt",
    ) -> "DesktopInstallTransactionPlan":
        if not candidate.release_ready:
            raise ValueError(
                "desktop candidate is not release-ready: "
                + ",".join(candidate.release_gate_findings())
            )
        for name, value in (
            ("transaction_id", transaction_id),
            ("active_slot_id", active_slot_id),
            ("receipt_id", receipt_id),
        ):
            _require_portable_id(name, value)
        if prior_install_identity:
            _require_sha256("prior_install_identity", prior_install_identity)
        payload: Mapping[str, Any] = {
            "transaction_id": transaction_id,
            "candidate_manifest_fingerprint": (
                candidate.manifest_fingerprint
            ),
            "prior_install_identity": prior_install_identity,
            "active_slot_id": active_slot_id,
            "receipt_id": receipt_id,
            "stages": INSTALL_STAGES,
            "rollback_stages": ROLLBACK_STAGES,
            "rollback_required_after_activation": True,
        }
        return cls(
            **payload,
            plan_fingerprint=_fingerprint(payload),
        )

    def canonical(self) -> Mapping[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> "DesktopInstallTransactionPlan":
        values = dict(payload)
        values["stages"] = tuple(values.get("stages", ()))
        values["rollback_stages"] = tuple(values.get("rollback_stages", ()))
        return cls(**values)


__all__ = [
    "BROWSER_DEVELOPMENT_SHELL",
    "DesktopInstallTransactionPlan",
    "DesktopPackageManifest",
    "INSTALL_STAGES",
    "PACKAGED_WINDOWS_WEBVIEW_SHELL",
    "ROLLBACK_STAGES",
    "SUPPORTED_SHELL_KINDS",
]
