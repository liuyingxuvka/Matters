from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from io import BytesIO
from threading import Barrier

import pytest
from PIL import Image

from matters.infrastructure.blobs.store import BlobStore
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.heroes import (
    GeneratedHeroOwner,
    GeneratedHeroProjectionOwner,
    GeneratedHeroRecord,
    HERO_BRIEF_CONTRACT_REVISION,
    HERO_ELIGIBILITY_DISPOSITIONS,
    HERO_GENERATION_POLICY_REVISION,
    HERO_INVALIDATION_REASONS,
    HERO_STATUSES,
    HeroIneligibleError,
    HeroPrivacyError,
    HeroStyleError,
    HeroSubject,
    HeroTransitionError,
)

_PHOTO_ALT = {
    "en": "A traveler preparing for a journey in a naturally lit station",
    "zh-CN": "一位旅行者在自然光照亮的车站准备启程",
}


def _owner(tmp_path, *, max_attempts=3):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    store = SQLiteStore(private, repository)
    return (
        GeneratedHeroOwner(
            store=store,
            blob_store=BlobStore(private, repository),
            max_attempts=max_attempts,
        ),
        store,
    )


def _subject(
    *,
    object_id="matter:trip",
    object_kind="matter",
    is_root=True,
    independently_openable=False,
    **overrides,
):
    values = {
        "object_id": object_id,
        "object_kind": object_kind,
        "semantic_identity_id": "semantic-private-identity",
        "topic_concepts": ("travel planning",),
        "theme_concepts": (
            "traveler with luggage at station",
            "waiting train and platform",
        ),
        "hierarchy_revision": "hierarchy-private-revision",
        "is_root": is_root,
        "independently_openable": independently_openable,
    }
    values.update(overrides)
    return HeroSubject(**values)


def _image_bytes(color="#416d89"):
    output = BytesIO()
    Image.new("RGB", (48, 30), color).save(output, format="PNG")
    return output.getvalue()


def _generated(owner, subject=None):
    pending = owner.prepare(subject or _subject())
    return owner.register_generated(
        matter_id=pending.matter_id,
        brief_fingerprint=pending.brief_fingerprint,
        content=_image_bytes(),
        media_type="image/png",
        localized_alt=_PHOTO_ALT,
        runner_contract_id="hero-runner-contract:v1",
        execution_identity="private-execution-receipt",
    )


def test_status_vocabulary_is_exact_and_records_reject_other_states():
    assert HERO_STATUSES == frozenset(
        {
            "generated_current",
            "generation_pending_placeholder",
            "generation_blocked_placeholder",
        }
    )
    with pytest.raises(ValueError, match="unsupported generated hero status"):
        GeneratedHeroRecord(
            matter_id="matter:one",
            generation_revision=1,
            status="stale",
            semantic_identity_fingerprint="sha256:a",
            topic_fingerprint="sha256:b",
            theme_fingerprint="sha256:c",
            hierarchy_fingerprint="sha256:d",
            permission_fingerprint="sha256:e",
            safety_fingerprint="sha256:f",
            policy_fingerprint="sha256:g",
            brief_fingerprint="",
            brief_payload={},
            runner_contract_id="",
            execution_identity="",
            private_asset_token="",
            private_blob_ref="",
            media_type="",
            localized_alt={"en": "Pending", "zh-CN": "等待中"},
            safety_disposition="pending",
        )


@pytest.mark.parametrize(
    ("topic", "theme"),
    [
        (
            "travel planning",
            "traveler with luggage at station",
        ),
        (
            "hackathon",
            "electronics demo with teams and judges",
        ),
        (
            "software project",
            "validation rack with gates and binders",
        ),
        (
            "subscription",
            "billing papers and refund checklist",
        ),
    ],
)
def test_root_gets_private_minimized_photographic_brief(
    tmp_path,
    topic,
    theme,
):
    owner, _store = _owner(tmp_path)

    root = owner.prepare(
        _subject(
            topic_concepts=(topic,),
            theme_concepts=(theme,),
        )
    )

    assert root.status == "generation_pending_placeholder"
    assert root.brief_fingerprint.startswith("sha256:")
    serialized = str(root.brief_payload)
    assert "matter:trip" not in serialized
    assert "semantic-private-identity" not in serialized
    assert "hierarchy-private-revision" not in serialized
    assert "synthetic-image" not in serialized
    assert root.brief_payload["topic_concepts"] == [topic]
    assert HERO_BRIEF_CONTRACT_REVISION == (
        "hero-brief:v4-photoreal-two-cue-documentary"
    )
    assert HERO_GENERATION_POLICY_REVISION == (
        "hero-generation-policy:4-photoreal-two-cue-documentary"
    )
    style = str(root.brief_payload["style"]).casefold()
    constraints = " ".join(
        str(item) for item in root.brief_payload["negative_constraints"]
    ).casefold()
    assert "photorealistic" in style
    assert "documentary" in style
    assert "editorial" in style
    assert "natural available light" in style
    assert "plausible real-world environment" in style
    assert "scene-defining physical setting" in style
    assert "specific to the matter" in style
    assert "recognizable without a caption" in style
    assert "at least two independently recognizable" in style
    assert "generic fictional non-identifiable people" in style
    assert "generic person working at a desk" in constraints
    assert "interchangeable office scene" in constraints
    assert "only distinguishing cue" in constraints
    for forbidden_style in (
        "abstract",
        "conceptual illustration",
        "vector",
        "3d render",
        "isometric",
        "infographic",
        "collage",
        "screenshot",
        "literal text",
        "logos",
    ):
        assert forbidden_style in constraints
    assert set(root.localized_alt) == {"en", "zh-CN"}


@pytest.mark.parametrize(
    "theme",
    [
        "progress",
        "journey preparation",
        "participant working at a computer",
        "developer working in a studio",
        "developer at hackathon workstation",
        "personal administration at home",
        "workflow review meeting",
    ],
)
def test_generic_or_person_led_brief_remains_pending_for_deeper_modeling(
    tmp_path,
    theme,
):
    owner, _store = _owner(tmp_path)

    root = owner.prepare(
        _subject(
            topic_concepts=("personal project",),
            theme_concepts=(theme,),
        )
    )

    assert root.status == "generation_pending_placeholder"
    assert root.failure_kind == "insufficient_matter_specificity"
    assert root.brief_fingerprint == ""
    assert root.brief_payload == {}


@pytest.mark.parametrize(
    ("object_kind", "is_root", "independently_openable"),
    [
        ("matter", False, True),
        ("matter", False, False),
        ("work_item", True, True),
        ("event", True, True),
        ("source", True, True),
        ("source_version", True, True),
        ("quick_view", True, True),
    ],
)
def test_non_root_matter_objects_are_explicitly_not_applicable(
    tmp_path,
    object_kind,
    is_root,
    independently_openable,
):
    owner, store = _owner(tmp_path)
    subject = _subject(
        object_id=f"{object_kind}:one",
        object_kind=object_kind,
        is_root=is_root,
        independently_openable=independently_openable,
    )

    assert HERO_ELIGIBILITY_DISPOSITIONS == frozenset(
        {"eligible", "not_applicable"}
    )
    assert subject.eligibility_disposition == "not_applicable"
    assert subject.eligible is False
    with pytest.raises(HeroIneligibleError, match="not applicable"):
        owner.prepare(subject)

    assert store.list_current(owner.record_owner) == ()
    assert store.list_current(owner.token_owner) == ()


def test_stale_generation_policy_is_rejected_before_a_brief_is_written(
    tmp_path,
):
    owner, store = _owner(tmp_path)

    with pytest.raises(ValueError, match="stale hero generation policy"):
        _subject(generation_policy_revision="hero-generation-policy:1")

    assert store.list_current(owner.record_owner) == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("topic_concepts", ("synthetic://private/plan",)),
        ("topic_concepts", ("person@example.com",)),
        ("topic_concepts", ("booking id abcd1234",)),
        ("topic_concepts", ("logo design",)),
        ("theme_concepts", ("message body",)),
        ("theme_concepts", ("identifiable person portrait",)),
        ("theme_concepts", ("literal text 2026",)),
    ],
)
def test_brief_concepts_reject_paths_mail_ids_text_logos_and_people(field, value):
    with pytest.raises(HeroPrivacyError):
        _subject(**{field: value})


@pytest.mark.parametrize(
    "flag",
    [
        "contains_source_excerpt",
        "contains_literal_text",
        "contains_logo_or_brand",
        "contains_private_identifier",
        "contains_path",
        "contains_email_body",
        "contains_identifiable_real_people",
    ],
)
def test_explicit_private_brief_inputs_are_rejected(flag):
    with pytest.raises(HeroPrivacyError):
        _subject(**{flag: True})


def test_unstable_matter_gets_pending_and_permission_or_safety_gets_blocked(
    tmp_path,
):
    owner, _store = _owner(tmp_path)

    unstable = owner.prepare(
        _subject(
            object_id="matter:unstable",
            identity_current=False,
        )
    )
    permission_blocked = owner.prepare(
        _subject(
            object_id="matter:permission",
            permission_disposition="blocked",
        )
    )
    safety_blocked = owner.prepare(
        _subject(
            object_id="matter:safety",
            safety_disposition="blocked",
        )
    )

    assert unstable.status == "generation_pending_placeholder"
    assert not unstable.brief_fingerprint
    assert permission_blocked.status == "generation_blocked_placeholder"
    assert permission_blocked.invalidated_by == "permission"
    assert safety_blocked.status == "generation_blocked_placeholder"
    assert safety_blocked.invalidated_by == "safety"


def test_generated_asset_is_private_bilingual_and_projection_hides_internal_ids(
    tmp_path,
):
    owner, store = _owner(tmp_path)
    generated = _generated(owner)
    projection = GeneratedHeroProjectionOwner.project(generated)

    assert generated.status == "generated_current"
    assert generated.private_asset_token.startswith("hero:")
    assert "matter:trip" not in generated.private_asset_token
    assert "semantic-private-identity" not in generated.private_asset_token
    assert set(generated.localized_alt) == {"en", "zh-CN"}
    resolved_bytes, resolved_media_type = owner.resolve(
        generated.private_asset_token
    )
    assert resolved_media_type == "image/png"
    with Image.open(BytesIO(resolved_bytes)) as opened:
        assert opened.size == (48, 30)
    assert projection.status == "generated_current"
    assert projection.private_asset_token == generated.private_asset_token
    assert "private_blob_ref" not in asdict(projection)
    assert "runner_contract_id" not in asdict(projection)
    assert "execution_identity" not in asdict(projection)

    assert store.list_current("source_version") == ()
    assert store.list_current("evidence_anchor") == ()
    assert store.list_current("visual_asset") == ()
    assert store.list_current("card_visual_decision") == ()
    assert store.list_current("image_gallery") == ()


@pytest.mark.parametrize(
    "hazard",
    [
        "contains_literal_text",
        "contains_logo_or_brand",
        "contains_identifiable_real_people",
    ],
)
def test_unsafe_generated_output_never_becomes_current(tmp_path, hazard):
    owner, _store = _owner(tmp_path)
    pending = owner.prepare(_subject())

    with pytest.raises(HeroPrivacyError):
        owner.register_generated(
            matter_id=pending.matter_id,
            brief_fingerprint=pending.brief_fingerprint,
            content=_image_bytes(),
            media_type="image/png",
            localized_alt=_PHOTO_ALT,
            runner_contract_id="hero-runner-contract:v1",
            execution_identity="private-execution-receipt",
            **{hazard: True},
        )

    assert owner.current(pending.matter_id).status == (
        "generation_pending_placeholder"
    )


def test_alt_text_requires_both_locales_and_rejects_private_content(tmp_path):
    owner, _store = _owner(tmp_path)
    pending = owner.prepare(_subject())
    common = {
        "matter_id": pending.matter_id,
        "brief_fingerprint": pending.brief_fingerprint,
        "content": _image_bytes(),
        "media_type": "image/png",
        "runner_contract_id": "hero-runner-contract:v1",
        "execution_identity": "private-execution-receipt",
    }

    with pytest.raises(ValueError, match="requires exactly"):
        owner.register_generated(
            **common,
            localized_alt={"en": _PHOTO_ALT["en"]},
        )
    with pytest.raises(HeroPrivacyError, match="prohibited"):
        owner.register_generated(
            **common,
            localized_alt={
                "en": "Portrait of person@example.com",
                "zh-CN": _PHOTO_ALT["zh-CN"],
            },
        )

    assert owner.current(pending.matter_id).status == (
        "generation_pending_placeholder"
    )


@pytest.mark.parametrize(
    "localized_alt",
    [
        {
            "en": "Conceptual illustration of a journey",
            "zh-CN": _PHOTO_ALT["zh-CN"],
        },
        {
            "en": _PHOTO_ALT["en"],
            "zh-CN": "旅行规划的抽象插图",
        },
    ],
)
def test_alt_text_rejects_abstract_or_illustration_language(
    tmp_path,
    localized_alt,
):
    owner, _store = _owner(tmp_path)
    pending = owner.prepare(_subject())

    with pytest.raises(HeroStyleError, match="non-photographic"):
        owner.register_generated(
            matter_id=pending.matter_id,
            brief_fingerprint=pending.brief_fingerprint,
            content=_image_bytes(),
            media_type="image/png",
            localized_alt=localized_alt,
            runner_contract_id="hero-runner-contract:v1",
            execution_identity="private-execution-receipt",
        )

    assert owner.current(pending.matter_id).status == (
        "generation_pending_placeholder"
    )


def test_stale_or_foreign_result_cannot_replace_current_generation(tmp_path):
    owner, _store = _owner(tmp_path)
    pending = owner.prepare(_subject())

    with pytest.raises(HeroTransitionError, match="current brief"):
        owner.register_generated(
            matter_id=pending.matter_id,
            brief_fingerprint="sha256:foreign",
            content=_image_bytes(),
            media_type="image/png",
            localized_alt=_PHOTO_ALT,
            runner_contract_id="hero-runner-contract:v1",
            execution_identity="private-execution-receipt",
        )


def test_transient_failures_retry_with_a_bound_then_block(tmp_path):
    owner, _store = _owner(tmp_path, max_attempts=2)
    pending = owner.prepare(_subject())

    first = owner.record_failure(
        matter_id=pending.matter_id,
        failure_kind="generation_failed",
    )
    second = owner.record_failure(
        matter_id=pending.matter_id,
        failure_kind="generation_failed",
    )

    assert first.status == "generation_pending_placeholder"
    assert first.retryable is True
    assert first.attempt == 1
    assert second.status == "generation_blocked_placeholder"
    assert second.retryable is False
    assert second.failure_kind == "retry_exhausted"


@pytest.mark.parametrize(
    "ordinary_change",
    [
        "ordinary_clue",
        "material_clue",
        "summary",
        "localization",
        "scan",
        "retry_metadata",
        "technical_receipt",
        "start_time",
    ],
)
def test_ordinary_clues_and_processing_changes_keep_the_same_hero(
    tmp_path,
    ordinary_change,
):
    owner, store = _owner(tmp_path)
    current = _generated(owner)
    revision_count = len(store.history(owner.record_owner, current.matter_id))

    retained = owner.apply_change(
        matter_id=current.matter_id,
        change_kind=ordinary_change,
    )

    assert retained == current
    assert retained.private_asset_token == current.private_asset_token
    assert owner.resolve(retained.private_asset_token)[1] == "image/png"
    assert len(store.history(owner.record_owner, current.matter_id)) == revision_count


@pytest.mark.parametrize("reason", sorted(HERO_INVALIDATION_REASONS))
def test_only_declared_dependency_classes_invalidate_the_current_hero(
    tmp_path,
    reason,
):
    owner, _store = _owner(tmp_path)
    current = _generated(owner)

    invalidated = owner.apply_change(
        matter_id=current.matter_id,
        change_kind=reason,
    )

    expected = (
        "generation_blocked_placeholder"
        if reason in {"permission", "safety", "policy"}
        else "generation_pending_placeholder"
    )
    assert invalidated.status == expected
    assert invalidated.invalidated_by == reason
    assert not invalidated.private_asset_token
    with pytest.raises(KeyError):
        owner.resolve(current.private_asset_token)


def test_current_record_with_legacy_policy_fingerprint_is_requeued(tmp_path):
    owner, store = _owner(tmp_path)
    current = _generated(owner)
    legacy_payload = asdict(current)
    legacy_payload["generation_revision"] = store.next_revision(
        owner.record_owner,
        current.matter_id,
    )
    legacy_payload["policy_fingerprint"] = "sha256:legacy-policy"
    legacy = GeneratedHeroRecord(**legacy_payload)
    store.append(
        owner.record_owner,
        legacy.matter_id,
        legacy.generation_revision,
        asdict(legacy),
    )

    requeued = owner.prepare(_subject())

    assert requeued.status == "generation_pending_placeholder"
    assert requeued.invalidated_by == "policy"
    assert requeued.policy_fingerprint != legacy.policy_fingerprint
    assert requeued.brief_fingerprint.startswith("sha256:")
    with pytest.raises(KeyError):
        owner.resolve(current.private_asset_token)


def test_prepare_is_idempotent_until_a_declared_dependency_changes(tmp_path):
    owner, store = _owner(tmp_path)
    subject = _subject()
    first = owner.prepare(subject)
    second = owner.prepare(subject)

    assert second == first
    assert len(store.list_current(owner.record_owner)) == 1

    current = _generated(owner, subject)
    retained = owner.prepare(
        _subject(hierarchy_revision="ordinary-new-hierarchy-snapshot")
    )
    assert retained == current

    changed = owner.prepare(
        _subject(
            theme_concepts=(
                "departure board with luggage",
                "platform with waiting train",
            )
        )
    )
    assert changed.status == "generation_pending_placeholder"
    assert changed.invalidated_by == "theme"
    with pytest.raises(KeyError):
        owner.resolve(current.private_asset_token)


def test_concurrent_prepare_serializes_the_first_generated_hero_revision(tmp_path):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    repository.mkdir()
    SQLiteStore(private, repository)
    owners = tuple(
        GeneratedHeroOwner(
            store=SQLiteStore(private, repository),
            blob_store=BlobStore(private, repository),
        )
        for _ in range(16)
    )
    barrier = Barrier(len(owners))
    subject = _subject(object_id="matter:concurrent-startup")

    def prepare(owner):
        barrier.wait()
        return owner.prepare(subject)

    with ThreadPoolExecutor(max_workers=len(owners)) as executor:
        records = tuple(executor.map(prepare, owners))

    assert {record.generation_revision for record in records} == {1}
    assert len(
        owners[0].store.history(owners[0].record_owner, subject.object_id)
    ) == 1


def test_current_registration_is_idempotent_for_the_exact_same_result(tmp_path):
    owner, _store = _owner(tmp_path)
    pending = owner.prepare(_subject())
    kwargs = {
        "matter_id": pending.matter_id,
        "brief_fingerprint": pending.brief_fingerprint,
        "content": _image_bytes(),
        "media_type": "image/png",
        "localized_alt": _PHOTO_ALT,
        "runner_contract_id": "hero-runner-contract:v1",
        "execution_identity": "private-execution-receipt",
    }

    first = owner.register_generated(**kwargs)
    second = owner.register_generated(**kwargs)

    assert second == first
