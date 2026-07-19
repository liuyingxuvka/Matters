from matters.state.open_loops import OpenLoopOwner


def test_wait_target_condition_scoped_block_and_independent_closure():
    owner = OpenLoopOwner()
    assert owner.create(loop_id="x", matter_id="m", wait_target="", closure_condition="reply") is None
    partial = owner.create(
        loop_id="p",
        matter_id="m",
        wait_target="reply",
        closure_condition="reply received",
    )
    critical = owner.create(
        loop_id="c",
        matter_id="m",
        wait_target="approval",
        closure_condition="approval received",
        critical=True,
    )
    assert owner.blocking(partial).scope == "partial"
    assert owner.blocking(critical).scope == "full"
    assert owner.close("c").status == "open"
    assert owner.close("c", closure_evidence_ids=("e:1",)).status == "closed"
