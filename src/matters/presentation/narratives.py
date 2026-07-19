"""Locale-specific narrative formatting without canonical inference."""

from __future__ import annotations

from typing import Mapping

from matters.presentation.localization import LocaleRegistry, LocalizationGap


def English_narrative(state: str, rationale: str) -> str:
    return f"State: {state}. Reason: {rationale}"


def Chinese_narrative(state_label: str, rationale: str) -> str:
    return f"状态：{state_label}。原因：{rationale}"


def localized_narratives(
    *,
    state_labels: Mapping[str, str],
    rationales: Mapping[str, str],
    registry: LocaleRegistry,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for locale in registry.available_locales:
        state = str(state_labels.get(locale, "")).strip()
        rationale = str(rationales.get(locale, "")).strip()
        if not state or not rationale:
            raise LocalizationGap(f"narrative inputs are incomplete for {locale}")
        if locale == "en":
            values[locale] = English_narrative(state, rationale)
        elif locale == "zh-CN":
            values[locale] = Chinese_narrative(state, rationale)
        else:
            raise LocalizationGap(
                f"locale {locale} requires an explicit localized narrative"
            )
    return values


__all__ = [
    "Chinese_narrative",
    "English_narrative",
    "localized_narratives",
]
