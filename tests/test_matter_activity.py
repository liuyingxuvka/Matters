from __future__ import annotations

from dataclasses import replace

import pytest

from matters.application.activity import (
    ACTIVITY_CLUE_OWNER,
    MATTER_ACTIVITY_OWNER,
    MatterActivityOwner,
    resolve_source_activity_time,
)
from matters.application.orchestrator import (
    MatterService,
    _parse_observation_time,
)
from matters.domain.activity import (
    NON_BUBBLING_CLUE_KINDS,
    MaterialClue,
    stable_activity_order_key,
)
from matters.provenance.source_registry import SourceVersion
from matters.providers.base import ExternalReference


class _MemoryBoundary:
    def __init__(self) -> None:
        self.objects = {}
        self.append_calls = []

    def current(self, owner, object_id):
        return self.objects.get((owner, object_id))

    def append_many(self, rows):
        batch = tuple(rows)
        self.append_calls.append(batch)
        for owner, object_id, revision, payload in batch:
            prior = self.objects.get((owner, object_id))
            expected = 1 if prior is None else prior["persistence_revision"] + 1
            assert revision == expected
            self.objects[(owner, object_id)] = dict(payload)


def _clue(
    clue_id="clue:reply",
    *,
    matter_id="matter:application",
    clue_kind="reply",
    user_world_at="2026-07-19T08:30:00+02:00",
    disposition="material",
    processed_at="2026-07-19T09:00:00+02:00",
    semantic_revision="semantic:application:7",
    evidence_ids=("evidence:reply",),
):
    return MaterialClue(
        clue_id=clue_id,
        matter_id=matter_id,
        clue_kind=clue_kind,
        user_world_at=user_world_at,
        disposition=disposition,
        rationale="The employer replied and changed the next step.",
        localized_summary={
            "en": "The employer replied and requested an interview.",
            "zh-CN": "雇主已回复并邀请面试。",
        },
        semantic_revision=semantic_revision,
        evidence_ids=evidence_ids,
        processed_at=processed_at,
    )


def _owner(boundary, ancestors=()):
    return MatterActivityOwner(
        append_many=boundary.append_many,
        current=boundary.current,
        ancestor_resolver=lambda _matter_id: ancestors,
    )


def test_material_clue_requires_bilingual_summary_and_rejects_processing_bubble():
    with pytest.raises(ValueError, match="en and zh-CN"):
        replace(_clue(), localized_summary={"en": "Only English"})

    for clue_kind in NON_BUBBLING_CLUE_KINDS:
        with pytest.raises(ValueError, match="processing-only"):
            replace(_clue(), clue_kind=clue_kind)


def test_material_clue_atomically_binds_summary_order_and_ancestor_activity():
    boundary = _MemoryBoundary()
    owner = _owner(
        boundary,
        ancestors=("matter:job-search", "matter:personal-goals"),
    )

    update = owner.record(_clue())

    assert len(boundary.append_calls) == 1
    assert update.written_row_count == 4
    assert update.bubbled_matter_ids == (
        "matter:application",
        "matter:job-search",
        "matter:personal-goals",
    )
    assert boundary.append_calls[0][0][0] == ACTIVITY_CLUE_OWNER
    assert {
        row[1] for row in boundary.append_calls[0][1:]
    } == set(update.bubbled_matter_ids)

    binding_revisions = set()
    for projection in update.projections:
        assert projection.latest_meaningful_clue_at == "2026-07-19T06:30:00+00:00"
        assert projection.processed_at == "2026-07-19T07:00:00+00:00"
        assert projection.localized_summary == {
            "en": "The employer replied and requested an interview.",
            "zh-CN": "雇主已回复并邀请面试。",
        }
        assert (
            projection.material_clue_revision
            == projection.summary_revision
            == projection.activity_order_revision
        )
        binding_revisions.add(projection.summary_revision)
    assert len(binding_revisions) == 1
    assert update.projections[0].ancestor_propagated is False
    assert all(
        projection.ancestor_propagated for projection in update.projections[1:]
    )


@pytest.mark.parametrize(
    "clue_kind",
    ["scan", "retry", "localization", "hero_generation", "reword"],
)
def test_processing_only_observations_are_recorded_without_activity_bubble(
    clue_kind,
):
    boundary = _MemoryBoundary()
    owner = _owner(boundary, ancestors=("matter:parent",))
    clue = replace(
        _clue(clue_id=f"clue:{clue_kind}"),
        clue_kind=clue_kind,
        disposition="nonmaterial",
        localized_summary={},
        semantic_revision="",
        evidence_ids=(),
    )

    update = owner.record(clue)

    assert update.bubbled_matter_ids == ()
    assert update.written_row_count == 1
    assert boundary.append_calls[0][0][0] == ACTIVITY_CLUE_OWNER
    assert not any(owner_id == MATTER_ACTIVITY_OWNER for owner_id, *_ in boundary.append_calls[0])


def test_uncertain_disposition_never_bubbles():
    boundary = _MemoryBoundary()
    owner = _owner(boundary, ancestors=("matter:parent",))

    update = owner.record(
        replace(
            _clue(clue_id="clue:uncertain"),
            disposition="uncertain",
            localized_summary={},
            semantic_revision="",
        )
    )

    assert update.disposition == "uncertain"
    assert update.bubbled_matter_ids == ()
    assert boundary.current(MATTER_ACTIVITY_OWNER, "matter:application") is None


def test_older_material_clue_is_preserved_without_regressing_latest_activity():
    boundary = _MemoryBoundary()
    owner = _owner(boundary)
    newest = _clue(
        clue_id="clue:newest",
        user_world_at="2026-07-19T12:00:00+00:00",
    )
    older = _clue(
        clue_id="clue:older",
        user_world_at="2026-07-18T12:00:00+00:00",
    )

    owner.record(newest)
    update = owner.record(older)

    assert update.written_row_count == 1
    assert update.bubbled_matter_ids == ()
    current = owner.current_projection("matter:application")
    assert current is not None
    assert current.material_clue_id == "clue:newest"
    assert current.latest_meaningful_clue_at == "2026-07-19T12:00:00+00:00"


def test_observation_time_correction_can_replace_a_future_due_time():
    boundary = _MemoryBoundary()
    owner = _owner(boundary, ancestors=("matter:parent",))
    due_time_clue = _clue(
        clue_id="clue:due-time",
        user_world_at="2026-07-26T00:00:00+00:00",
    )
    owner.record(due_time_clue)

    corrected = owner.correct_observation_time(
        _clue(
            clue_id="clue:observed-time",
            user_world_at="2026-07-18T09:15:00+00:00",
        ),
        superseded_clue_id=due_time_clue.clue_id,
        projection_matter_ids=("matter:canonical",),
    )

    assert corrected.written_row_count == 4
    direct = owner.current_projection("matter:application")
    parent = owner.current_projection("matter:parent")
    canonical = owner.current_projection("matter:canonical")
    assert direct is not None and parent is not None and canonical is not None
    assert direct.material_clue_id == "clue:observed-time"
    assert parent.material_clue_id == "clue:observed-time"
    assert canonical.material_clue_id == "clue:observed-time"
    assert (
        direct.latest_meaningful_clue_at
        == "2026-07-18T09:15:00+00:00"
    )


def test_observation_time_correction_repairs_late_bound_canonical_projection():
    boundary = _MemoryBoundary()
    owner = _owner(boundary)
    due_time_clue = _clue(
        clue_id="clue:due-time",
        user_world_at="2026-07-26T00:00:00+00:00",
    )
    owner.record(due_time_clue)
    due_projection = dict(
        boundary.current(MATTER_ACTIVITY_OWNER, "matter:application")
    )
    due_projection["matter_id"] = "matter:canonical"
    boundary.objects[(MATTER_ACTIVITY_OWNER, "matter:canonical")] = due_projection
    corrected_clue = _clue(
        clue_id="clue:observed-time",
        user_world_at="2026-07-18T09:15:00+00:00",
    )
    owner.correct_observation_time(
        corrected_clue,
        superseded_clue_id=due_time_clue.clue_id,
    )

    retry = owner.correct_observation_time(
        corrected_clue,
        superseded_clue_id=due_time_clue.clue_id,
        projection_matter_ids=("matter:canonical",),
    )

    canonical = owner.current_projection("matter:canonical")
    assert retry.written_row_count == 1
    assert retry.idempotent is False
    assert canonical is not None
    assert canonical.material_clue_id == "clue:observed-time"


def test_observation_time_parser_accepts_connector_formats_and_rejects_nulls():
    assert (
        _parse_observation_time("07/14/2026 17:32:08").isoformat()
        == "2026-07-14T17:32:08+00:00"
    )
    assert (
        _parse_observation_time("2026-07-18T15:34:06+02:00").isoformat()
        == "2026-07-18T13:34:06+00:00"
    )
    assert _parse_observation_time("None") is None


def test_source_activity_time_prefers_explicit_observation_contract_fields():
    result = resolve_source_activity_time(
        {
            "source_id": "source:mail",
            "version": 3,
            "provider": "gmail",
            "created_at": "2026-07-20T12:00:00+00:00",
            "source_time_metadata": {
                "provider_metadata.modified_at": "2026-07-19T12:00:00+00:00",
                "payload.created_at": "2026-07-18T12:00:00+00:00",
                "payload.received_at": "2026-07-17T12:00:00+00:00",
                "payload.observed_at": "2026-07-16T12:00:00+02:00",
            },
        }
    )

    assert result.resolved is True
    assert result.observed_at == "2026-07-16T10:00:00+00:00"
    assert result.basis == "provider_observed_time"
    assert result.field_path == "source_time_metadata.payload.observed_at"
    assert result.source_id == "source:mail"
    assert result.source_version == 3
    assert result.rejected_fields == ("source.created_at",)


def test_source_activity_time_supports_codex_first_recorded_at():
    source = SourceVersion(
        source_id="source:codex",
        version=1,
        provider="codex",
        external_reference=ExternalReference(
            provider="codex",
            external_id="codex:project:opaque",
            object_type="codex_project",
        ),
        content={
            "metadata": {
                "first_recorded_at": "2026-06-27T09:04:52+02:00",
            }
        },
        content_hash="sha256:content",
        metadata_hash="sha256:metadata",
    )
    result = resolve_source_activity_time(source)

    assert result.observed_at == "2026-06-27T07:04:52+00:00"
    assert result.basis == "codex_first_recorded_time"
    assert result.field_path == "content.metadata.first_recorded_at"


def test_source_activity_time_supports_filesystem_modified_ns():
    result = resolve_source_activity_time(
        {
            "source_id": "source:file",
            "version": 4,
            "provider": "filesystem",
            "source_time_metadata": {
                "provider_metadata.modified_ns": 1_700_000_000_000_000_000,
            },
        }
    )

    assert result.observed_at == "2023-11-14T22:13:20+00:00"
    assert result.basis == "filesystem_modified_time"
    assert result.field_path == "source_time_metadata.provider_metadata.modified_ns"


def test_source_activity_time_never_uses_database_processing_time():
    result = resolve_source_activity_time(
        {
            "source_id": "source:processing-only",
            "provider": "filesystem",
            "created_at": "2026-07-20T12:00:00+00:00",
            "processed_at": "2026-07-20T12:01:00+00:00",
            "updated_at": "2026-07-20T12:02:00+00:00",
            "content": {"analysis_completed_at": "2026-07-20T12:03:00+00:00"},
        }
    )

    assert result.resolved is False
    assert result.observed_at == ""
    assert result.failure == "database_processing_time_not_user_world_evidence"
    assert result.rejected_fields == (
        "source.created_at",
        "source.processed_at",
        "source.updated_at",
    )


def test_source_activity_time_returns_auditable_invalid_and_missing_failures():
    invalid = resolve_source_activity_time(
        {
            "source_id": "source:invalid",
            "source_time_metadata": {"payload.received_at": "not-a-time"},
        }
    )
    missing = resolve_source_activity_time(
        {"source_id": "source:missing", "content": {"due_at": "2026-08-01"}}
    )
    tombstone = resolve_source_activity_time(
        {
            "source_id": "source:deleted",
            "tombstone": True,
            "source_time_metadata": {
                "payload.observed_at": "2026-07-18T10:00:00+00:00"
            },
        }
    )

    assert invalid.failure == "eligible_source_time_invalid"
    assert invalid.invalid_fields == (
        "source_time_metadata.payload.received_at",
    )
    assert missing.failure == "source_time_metadata_missing"
    assert tombstone.failure == "source_is_tombstoned"


def test_activity_repair_uses_exact_historical_source_revision_without_event(
    tmp_path,
):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    service = MatterService(private_root=home, repository_root=repo)
    source_id = "source:historical"
    common = {
        "source_id": source_id,
        "provider": "gmail",
        "external_reference": {
            "provider": "gmail",
            "external_id": "gmail:message:historical",
            "object_type": "gmail_message",
            "locator": "",
        },
        "content_hash": "sha256:content",
        "metadata_hash": "sha256:metadata",
        "tombstone": False,
    }
    service.store.append(
        "source_version",
        source_id,
        1,
        {
            **common,
            "version": 1,
            "predecessor_version": None,
            "content": {"internal_date": "2026-07-06T16:16:42+00:00"},
        },
    )
    service.store.append(
        "source_version",
        source_id,
        2,
        {
            **common,
            "version": 2,
            "predecessor_version": 1,
            "content": {"internal_date": "None"},
        },
    )
    evidence_id = "evidence:source:historical:1:anchor"
    service.activity.record(
        _clue(
            clue_id="clue:future-due",
            user_world_at="2026-07-26T00:00:00+00:00",
            semantic_revision="source:historical:v1",
            evidence_ids=(evidence_id,),
        )
    )

    result = service.repair_current_activity_observation_times()
    current = service.activity.current_projection("matter:application")

    assert result["repaired_clue_count"] == 1
    assert current is not None
    assert current.latest_meaningful_clue_at == "2026-07-06T16:16:42+00:00"


def test_clue_retry_is_idempotent_but_identity_conflict_is_blocked():
    boundary = _MemoryBoundary()
    owner = _owner(boundary)
    clue = _clue()

    owner.record(clue)
    retry = owner.record(replace(clue, processed_at="2026-07-19T10:00:00+02:00"))

    assert retry.idempotent is True
    assert retry.written_row_count == 0
    assert len(boundary.append_calls) == 1

    with pytest.raises(ValueError, match="different semantics"):
        owner.record(replace(clue, rationale="A conflicting interpretation."))


def test_stable_activity_order_is_newest_first_with_matter_id_tie_break():
    boundary = _MemoryBoundary()
    owner = _owner(boundary)
    first = owner.record(
        _clue(
            clue_id="clue:b",
            matter_id="matter:b",
            user_world_at="2026-07-19T12:00:00+00:00",
        )
    ).projections[0]
    second = owner.record(
        _clue(
            clue_id="clue:a",
            matter_id="matter:a",
            user_world_at="2026-07-19T12:00:00+00:00",
        )
    ).projections[0]
    older = owner.record(
        _clue(
            clue_id="clue:c",
            matter_id="matter:c",
            user_world_at="2026-07-18T12:00:00+00:00",
        )
    ).projections[0]

    ordered = sorted(
        (first, older, second),
        key=stable_activity_order_key,
    )

    assert [item.matter_id for item in ordered] == [
        "matter:a",
        "matter:b",
        "matter:c",
    ]
