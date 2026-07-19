from matters.revisions.corrections import CorrectionCoordinator
from matters.revisions.invalidation import undisposed
import pytest


def test_correction_is_append_only_and_routes_to_original_owners():
    owner = CorrectionCoordinator()
    revision = owner.append(
        kind="correction",
        target_id="state:1",
        prior_revision_id="r:old",
        rationale="user supplied corrected evidence",
    )
    plan, requests = owner.invalidate(
        revision,
        (("matter:1", "C6"), ("state:1", "C7"), ("projection:1", "C12")),
    )
    assert revision.prior_revision_id == "r:old"
    assert not undisposed(("matter:1", "state:1", "projection:1"), plan.dispositions)
    assert {item.owner_model_id for item in requests} == {"C6", "C7", "C12"}
    with pytest.raises(PermissionError):
        owner.write_foreign_state("C7", "completed")
