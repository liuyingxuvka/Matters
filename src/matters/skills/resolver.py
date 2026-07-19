"""Compatibility-aware singular active-view resolution for consumer skills."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Iterable

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .inventory import InstalledSkill, MachineSkillInventory
from .manifest import (
    BundleManifest,
    InstallationPolicy,
    SkillIdentity,
    SkillManifest,
    SkillOrigin,
)
from .research import (
    ResearchGuardGate,
    ResearchGuardStatus,
    ResearchProviderDecision,
    resolve_research_provider,
)


class ValidationStatus(StrEnum):
    CURRENT = "current"
    FAILED = "failed"
    STALE = "stale"


@dataclass(frozen=True)
class CandidateValidation:
    candidate_manifest_fingerprint: str
    validator_identity: str
    status: ValidationStatus
    reason: str = ""


@dataclass(frozen=True)
class DependencyIdentity:
    skill_id: str
    version: Version | str
    content_hash: str
    runtime_identity: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "version",
            self.version if isinstance(self.version, Version) else Version(self.version),
        )

    def canonical(self) -> dict[str, str]:
        return {
            "skill_id": self.skill_id,
            "version": str(self.version),
            "content_hash": self.content_hash,
            "runtime_identity": self.runtime_identity,
        }


@dataclass(frozen=True)
class ResolutionEnvironment:
    matters_version: Version | str
    skill_schema_version: Version | str
    available_runtime_identities: tuple[str, ...]
    dependency_identities: tuple[DependencyIdentity, ...]
    validations: tuple[CandidateValidation, ...]
    researchguard: ResearchGuardGate

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "matters_version",
            self.matters_version
            if isinstance(self.matters_version, Version)
            else Version(self.matters_version),
        )
        object.__setattr__(
            self,
            "skill_schema_version",
            self.skill_schema_version
            if isinstance(self.skill_schema_version, Version)
            else Version(self.skill_schema_version),
        )
        runtimes = tuple(sorted(set(self.available_runtime_identities)))
        object.__setattr__(self, "available_runtime_identities", runtimes)
        dependencies = tuple(
            sorted(
                self.dependency_identities,
                key=lambda item: (
                    item.skill_id,
                    item.version,
                    item.content_hash,
                    item.runtime_identity,
                ),
            )
        )
        object.__setattr__(self, "dependency_identities", dependencies)
        validations = tuple(
            sorted(
                self.validations,
                key=lambda item: (
                    item.candidate_manifest_fingerprint,
                    item.validator_identity,
                ),
            )
        )
        keys = [
            (row.candidate_manifest_fingerprint, row.validator_identity)
            for row in validations
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("candidate validations must be unique per manifest and validator")
        object.__setattr__(self, "validations", validations)

    @property
    def fingerprint(self) -> str:
        return _json_hash(
            {
                "matters_version": str(self.matters_version),
                "skill_schema_version": str(self.skill_schema_version),
                "available_runtime_identities": list(self.available_runtime_identities),
                "dependency_identities": [
                    row.canonical() for row in self.dependency_identities
                ],
                "validations": [
                    {
                        "candidate_manifest_fingerprint": row.candidate_manifest_fingerprint,
                        "validator_identity": row.validator_identity,
                        "status": row.status.value,
                        "reason": row.reason,
                    }
                    for row in self.validations
                ],
                "researchguard": self.researchguard.fingerprint,
            }
        )


@dataclass(frozen=True)
class CandidateDisposition:
    manifest_fingerprint: str
    origin: SkillOrigin
    version: Version
    content_hash: str
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ActiveSkillDecision:
    skill_id: str
    required: bool
    status: str
    disposition: str
    selected_identity: SkillIdentity | None
    selected_manifest_fingerprint: str
    update_available: bool
    sync_required: bool
    candidate_dispositions: tuple[CandidateDisposition, ...]

    @property
    def usable(self) -> bool:
        return self.status == "current" and self.selected_identity is not None


@dataclass(frozen=True)
class ActiveSkillView:
    status: str
    decisions: tuple[ActiveSkillDecision, ...]
    research_provider: ResearchProviderDecision
    input_fingerprint: str
    view_fingerprint: str
    view_schema: str = "matters.active-skill-view.v1"

    def decision_for(self, skill_id: str) -> ActiveSkillDecision:
        for decision in self.decisions:
            if decision.skill_id == skill_id:
                return decision
        raise KeyError(skill_id)

    def is_current_for(
        self,
        *,
        bundle: BundleManifest,
        inventory: MachineSkillInventory,
        environment: ResolutionEnvironment,
    ) -> bool:
        return self.input_fingerprint == active_view_input_fingerprint(
            bundle=bundle,
            inventory=inventory,
            environment=environment,
        )


class ActiveSkillResolver:
    """Select one validated compatible identity for each bundled skill."""

    def resolve(
        self,
        *,
        bundle: BundleManifest,
        inventory: MachineSkillInventory,
        environment: ResolutionEnvironment,
    ) -> ActiveSkillView:
        if not bundle.matters_compatibility.contains(
            environment.matters_version,
            prereleases=True,
        ):
            raise ValueError("bundle is incompatible with the current Matters version")
        if bundle.skill_schema_version != environment.skill_schema_version:
            raise ValueError("bundle skill schema identity does not match the runtime")

        research = resolve_research_provider(environment.researchguard)
        decisions = tuple(
            self._resolve_skill(
                bundled=bundled,
                installed=inventory.for_skill(bundled.skill_id),
                environment=environment,
                research=research,
            )
            for bundled in bundle.skills
        )
        required_blocked = any(
            decision.required and not decision.usable for decision in decisions
        )
        if required_blocked or research.status == ResearchGuardStatus.BLOCKED:
            status = "blocked"
        elif research.status == ResearchGuardStatus.PENDING:
            status = "partial"
        else:
            status = "current"
        input_fingerprint = active_view_input_fingerprint(
            bundle=bundle,
            inventory=inventory,
            environment=environment,
        )
        view_fingerprint = _json_hash(
            {
                "input_fingerprint": input_fingerprint,
                "status": status,
                "research_status": research.status.value,
                "research_identity": research.provider_identity,
                "decisions": [
                    {
                        "skill_id": decision.skill_id,
                        "status": decision.status,
                        "disposition": decision.disposition,
                        "selected_identity": (
                            decision.selected_identity.fingerprint
                            if decision.selected_identity
                            else ""
                        ),
                        "update_available": decision.update_available,
                        "sync_required": decision.sync_required,
                        "candidates": [
                            {
                                "manifest": row.manifest_fingerprint,
                                "eligible": row.eligible,
                                "reasons": list(row.reasons),
                            }
                            for row in decision.candidate_dispositions
                        ],
                    }
                    for decision in decisions
                ],
            }
        )
        return ActiveSkillView(
            status=status,
            decisions=decisions,
            research_provider=research,
            input_fingerprint=input_fingerprint,
            view_fingerprint=view_fingerprint,
        )

    def _resolve_skill(
        self,
        *,
        bundled: SkillManifest,
        installed: tuple[InstalledSkill, ...],
        environment: ResolutionEnvironment,
        research: ResearchProviderDecision,
    ) -> ActiveSkillDecision:
        manifests = (bundled,) + tuple(row.manifest for row in installed)
        dispositions = tuple(
            self._candidate_disposition(
                manifest,
                environment=environment,
                research=research,
            )
            for manifest in manifests
        )

        collisions = _same_version_hash_collisions(manifests)
        duplicate_installed = _duplicate_installed_content_identities(installed)
        if collisions or duplicate_installed:
            reasons = tuple(
                sorted(
                    {
                        *(
                            f"same_version_hash_collision:{version}"
                            for version in collisions
                        ),
                        *(
                            f"duplicate_installed_identity:{identity}"
                            for identity in duplicate_installed
                        ),
                    }
                )
            )
            return ActiveSkillDecision(
                skill_id=bundled.skill_id,
                required=bundled.required,
                status="blocked",
                disposition="identity_collision",
                selected_identity=None,
                selected_manifest_fingerprint="",
                update_available=False,
                sync_required=False,
                candidate_dispositions=tuple(
                    CandidateDisposition(
                        manifest_fingerprint=row.manifest_fingerprint,
                        origin=row.origin,
                        version=row.version,
                        content_hash=row.content_hash,
                        eligible=False,
                        reasons=tuple(sorted(set(row.reasons + reasons))),
                    )
                    for row in dispositions
                ),
            )

        disposition_by_fingerprint = {
            row.manifest_fingerprint: row for row in dispositions
        }
        eligible = tuple(
            manifest
            for manifest in manifests
            if disposition_by_fingerprint[manifest.manifest_fingerprint].eligible
        )
        if not eligible:
            return ActiveSkillDecision(
                skill_id=bundled.skill_id,
                required=bundled.required,
                status="blocked" if bundled.required else "optional_unavailable",
                disposition="no_validated_compatible_candidate",
                selected_identity=None,
                selected_manifest_fingerprint="",
                update_available=False,
                sync_required=False,
                candidate_dispositions=dispositions,
            )

        eligible_installed = tuple(
            manifest
            for manifest in eligible
            if manifest.origin == SkillOrigin.MACHINE_INSTALLED
        )
        exact_local = tuple(
            manifest
            for manifest in eligible_installed
            if manifest.version == bundled.version
            and manifest.content_hash == bundled.content_hash
        )
        if (
            exact_local
            and disposition_by_fingerprint[bundled.manifest_fingerprint].eligible
        ):
            selected = sorted(
                exact_local,
                key=lambda item: item.manifest_fingerprint,
            )[0]
            decision = "exact_match"
            update_available = False
            sync_required = False
        else:
            selected = sorted(
                eligible,
                key=lambda item: (
                    item.version,
                    item.origin == SkillOrigin.MACHINE_INSTALLED,
                    item.manifest_fingerprint,
                ),
                reverse=True,
            )[0]
            if selected.origin == SkillOrigin.MACHINE_INSTALLED:
                decision = "machine_overlay"
                update_available = False
                sync_required = False
            else:
                older_installed = tuple(
                    row
                    for row in installed
                    if row.manifest.version < selected.version
                )
                managed = tuple(row for row in older_installed if row.matters_managed)
                unmanaged = tuple(row for row in older_installed if not row.matters_managed)
                if managed:
                    decision = "bundled_managed_sync_required"
                    update_available = False
                    sync_required = True
                elif unmanaged:
                    decision = "bundled_update_available"
                    update_available = True
                    sync_required = False
                else:
                    decision = "bundled_internal"
                    update_available = False
                    sync_required = False

        return ActiveSkillDecision(
            skill_id=bundled.skill_id,
            required=bundled.required,
            status="current",
            disposition=decision,
            selected_identity=selected.identity,
            selected_manifest_fingerprint=selected.manifest_fingerprint,
            update_available=update_available,
            sync_required=sync_required,
            candidate_dispositions=dispositions,
        )

    @staticmethod
    def _candidate_disposition(
        manifest: SkillManifest,
        *,
        environment: ResolutionEnvironment,
        research: ResearchProviderDecision,
    ) -> CandidateDisposition:
        failures = list(
            manifest.compatibility_failures(
                matters_version=environment.matters_version,
                skill_schema_version=environment.skill_schema_version,
            )
        )
        if manifest.runtime_identity not in environment.available_runtime_identities:
            failures.append("runtime_identity_unavailable")

        validation = next(
            (
                row
                for row in environment.validations
                if row.candidate_manifest_fingerprint
                == manifest.manifest_fingerprint
                and row.validator_identity == manifest.validator_identity
            ),
            None,
        )
        if validation is None:
            failures.append("native_validation_missing")
        elif validation.status != ValidationStatus.CURRENT:
            failures.append(f"native_validation_{validation.status.value}")
            if validation.reason:
                failures.append(f"native_validation_reason:{validation.reason}")

        for dependency in manifest.dependencies:
            matching = tuple(
                row
                for row in environment.dependency_identities
                if row.skill_id == dependency.skill_id
                and dependency.version_compatibility.contains(
                    row.version,
                    prereleases=True,
                )
                and (
                    not dependency.content_hash
                    or dependency.content_hash == row.content_hash
                )
                and (
                    not dependency.runtime_identity
                    or dependency.runtime_identity == row.runtime_identity
                )
            )
            if not matching:
                failures.append(f"dependency_identity_missing:{dependency.skill_id}")

        if manifest.researchguard_identity:
            if research.status != ResearchGuardStatus.CURRENT:
                failures.append("researchguard_identity_not_current")
            elif manifest.researchguard_identity != research.provider_identity:
                failures.append("researchguard_identity_mismatch")

        reasons = tuple(sorted(set(failures)))
        return CandidateDisposition(
            manifest_fingerprint=manifest.manifest_fingerprint,
            origin=manifest.origin,
            version=manifest.version,
            content_hash=manifest.content_hash,
            eligible=not reasons,
            reasons=reasons,
        )


def active_view_input_fingerprint(
    *,
    bundle: BundleManifest,
    inventory: MachineSkillInventory,
    environment: ResolutionEnvironment,
) -> str:
    return _json_hash(
        {
            "bundle_hash": bundle.bundle_hash,
            "inventory_revision": inventory.revision,
            "environment_fingerprint": environment.fingerprint,
        }
    )


def _same_version_hash_collisions(
    manifests: Iterable[SkillManifest],
) -> tuple[str, ...]:
    hashes_by_version: dict[Version, set[str]] = {}
    for manifest in manifests:
        hashes_by_version.setdefault(manifest.version, set()).add(manifest.content_hash)
    return tuple(
        str(version)
        for version, hashes in sorted(hashes_by_version.items())
        if len(hashes) > 1
    )


def _duplicate_installed_content_identities(
    installed: Iterable[InstalledSkill],
) -> tuple[str, ...]:
    manifests = tuple(row.manifest for row in installed)
    counts: dict[tuple[Version, str], int] = {}
    for manifest in manifests:
        key = (manifest.version, manifest.content_hash)
        counts[key] = counts.get(key, 0) + 1
    return tuple(
        f"{version}:{content_hash}"
        for (version, content_hash), count in sorted(counts.items())
        if count > 1
    )


def _json_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


__all__ = [
    "ActiveSkillDecision",
    "ActiveSkillResolver",
    "ActiveSkillView",
    "CandidateDisposition",
    "CandidateValidation",
    "DependencyIdentity",
    "ResolutionEnvironment",
    "ValidationStatus",
    "active_view_input_fingerprint",
]
