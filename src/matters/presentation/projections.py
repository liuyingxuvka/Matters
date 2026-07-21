"""C12: locale-registry projection with same-revision semantic equivalence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
    LocaleRegistry,
    LocalizedText,
    LocalizationGap,
    rationale_localized,
    state_localized,
)
from matters.presentation.narratives import localized_narratives


@dataclass(frozen=True)
class MatterProjection:
    matter_id: str
    semantic_revision: str
    state: str
    evidence_ids: tuple[str, ...]
    localized_values: Mapping[str, str]
    localized_rationale: Mapping[str, str]
    locale_revisions: Mapping[str, str]
    available_locales: tuple[str, ...]
    default_locale: str
    equivalence_status: str
    state_basis_modality: str = "unknown"
    state_basis_scope: str = ""
    state_terminality: str = "confirmed"

    def resolve(self, locale: str) -> str:
        if locale not in self.available_locales:
            raise ProjectionConflict(f"unsupported locale: {locale}")
        value = str(self.localized_values.get(locale, "")).strip()
        if not value:
            raise LocalizationGap(f"projection is missing locale {locale}")
        return value


class ProjectionConflict(ValueError):
    pass


class ProjectionOwner:
    def __init__(
        self,
        registry: LocaleRegistry = DEFAULT_LOCALE_REGISTRY,
    ) -> None:
        self.registry = registry

    def publish_pair(
        self,
        *,
        matter_id: str,
        english_revision: str,
        zh_cn_revision: str,
        state: str,
        rationale: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> MatterProjection:
        return self.publish(
            matter_id=matter_id,
            semantic_revision=english_revision,
            state=state,
            rationale=rationale,
            evidence_ids=evidence_ids,
            locale_revisions={
                "en": english_revision,
                "zh-CN": zh_cn_revision,
            },
        )

    def publish(
        self,
        *,
        matter_id: str,
        semantic_revision: str,
        state: str,
        rationale: str,
        evidence_ids: tuple[str, ...] = (),
        locale_semantics: Mapping[str, str] | None = None,
        locale_revisions: Mapping[str, str] | None = None,
        localized_rationale: Mapping[str, str] | None = None,
        localized_state_labels: Mapping[str, str] | None = None,
        localized_values: Mapping[str, str] | None = None,
        state_basis_modality: str = "unknown",
        state_basis_scope: str = "",
        state_terminality: str = "confirmed",
    ) -> MatterProjection:
        revisions = dict(
            locale_revisions
            or {
                locale: semantic_revision
                for locale in self.registry.available_locales
            }
        )
        missing_revisions = set(self.registry.available_locales) - set(revisions)
        if missing_revisions:
            raise ProjectionConflict(
                "missing locale revisions: " + ", ".join(sorted(missing_revisions))
            )
        if any(
            revisions[locale] != semantic_revision
            for locale in self.registry.available_locales
        ):
            raise ProjectionConflict("language projections reference different revisions")

        semantics = dict(
            locale_semantics
            or {
                locale: state
                for locale in self.registry.available_locales
            }
        )
        if any(
            semantics.get(locale) != state
            for locale in self.registry.available_locales
        ):
            raise ProjectionConflict("language projections disagree semantically")

        rationale_values = dict(
            localized_rationale
            or rationale_localized(
                rationale,
                semantic_revision=semantic_revision,
            )
        )
        LocalizedText.create(
            rationale_values,
            semantic_revision=semantic_revision,
            registry=self.registry,
        )

        if localized_values is None:
            state_labels = dict(
                localized_state_labels
                or state_localized(
                    state,
                    semantic_revision=semantic_revision,
                )
            )
            values = localized_narratives(
                state_labels=state_labels,
                rationales=rationale_values,
                registry=self.registry,
            )
        else:
            values = dict(localized_values)
        localized_projection = LocalizedText.create(
            values,
            semantic_revision=semantic_revision,
            registry=self.registry,
        )
        return MatterProjection(
            matter_id=matter_id,
            semantic_revision=semantic_revision,
            state=state,
            evidence_ids=evidence_ids,
            localized_values=dict(localized_projection.values),
            localized_rationale=rationale_values,
            locale_revisions={
                locale: revisions[locale]
                for locale in self.registry.available_locales
            },
            available_locales=self.registry.available_locales,
            default_locale=self.registry.default_locale,
            equivalence_status="equivalent",
            state_basis_modality=state_basis_modality,
            state_basis_scope=state_basis_scope,
            state_terminality=state_terminality,
        )

    @staticmethod
    def submit_correction(
        correction_handler: Callable[..., object],
        **correction,
    ) -> object:
        return correction_handler(**correction)

    @staticmethod
    def infer_canonical_state(*_args, **_kwargs) -> None:
        raise PermissionError("UI projection cannot infer canonical state")


__all__ = [
    "MatterProjection",
    "ProjectionConflict",
    "ProjectionOwner",
]
