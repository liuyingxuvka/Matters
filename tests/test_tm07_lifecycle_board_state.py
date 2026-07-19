from matters.state.lifecycle import LifecycleOwner, StateProofPacket
import pytest


def test_lifecycle_requires_proof_and_provider_done_is_not_authority():
    owner = LifecycleOwner()
    assert owner.decide(StateProofPacket("complete", explicit_start=True)).state == "in_progress"
    assert owner.decide(StateProofPacket("complete", scheduled=True)).state == "planned"
    assert owner.decide(StateProofPacket("partial")).state == "uncertain"
    conflict = owner.decide(StateProofPacket("complete", provider_status="Done"))
    assert conflict.state == "completion_unproven"
    assert conflict.board_column == "Uncertain"
    assert conflict.provider_conflict
    with pytest.raises(PermissionError):
        owner.write_from_ui("in_progress")
