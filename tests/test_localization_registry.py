import pytest

from matters.application.orchestrator import MatterService
from matters.presentation.localization import (
    DEFAULT_LOCALE_REGISTRY,
    LocaleDefinition,
    LocalizedText,
    LocalizationGap,
    UnsupportedLocale,
)


def test_default_locale_is_english_and_no_missing_value_falls_back():
    assert DEFAULT_LOCALE_REGISTRY.default_locale == "en"
    assert DEFAULT_LOCALE_REGISTRY.available_locales == ("en", "zh-CN")
    with pytest.raises(LocalizationGap):
        LocalizedText.create(
            {"en": "Current"},
            semantic_revision="revision:1",
        )
    complete = LocalizedText.create(
        {"en": "Current", "zh-CN": "当前有效"},
        semantic_revision="revision:1",
    )
    with pytest.raises(UnsupportedLocale):
        complete.resolve("fr")


def test_future_locale_is_selectable_only_with_complete_registered_content():
    registry = DEFAULT_LOCALE_REGISTRY.register(
        LocaleDefinition("fr", "French", "Français")
    )
    with pytest.raises(LocalizationGap):
        LocalizedText.create(
            {"en": "Current", "zh-CN": "当前有效"},
            semantic_revision="revision:2",
            registry=registry,
        )
    complete = LocalizedText.create(
        {
            "en": "Current",
            "zh-CN": "当前有效",
            "fr": "À jour",
        },
        semantic_revision="revision:2",
        registry=registry,
    )
    assert complete.resolve("fr", registry=registry) == "À jour"


def test_private_store_migrates_legacy_projection_pair_to_locale_maps(tmp_path):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    first = MatterService(private_root=home, repository_root=repo)
    assert first.store is not None
    first.store.append(
        "projection",
        "matter:legacy",
        1,
        {
            "matter_id": "matter:legacy",
            "semantic_revision": "revision:legacy",
            "state": "candidate",
            "evidence_ids": [],
            "english": "Candidate — no current goal or obligation",
            "zh_cn": "候选事项——目前没有明确目标或义务",
            "rationale": "no current goal or obligation",
            "equivalence_status": "equivalent",
        },
    )

    MatterService(private_root=home, repository_root=repo)

    payload = first.store.current("projection", "matter:legacy")
    assert payload is not None
    assert set(payload["localized_values"]) == {"en", "zh-CN"}
    assert set(payload["localized_rationale"]) == {"en", "zh-CN"}
    assert set(payload["locale_revisions"]) == {"en", "zh-CN"}
    assert "english" not in payload
    assert "zh_cn" not in payload
    migration = first.store.current(
        "schema_migration",
        "projection-locale-map-v1",
    )
    assert migration is not None
    assert migration["migrated_projection_count"] == 1
