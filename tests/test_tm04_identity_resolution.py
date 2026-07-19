from matters.identity.people import PersonRegistry


def test_same_names_stay_distinct_and_roles_are_matter_scoped():
    registry = PersonRegistry()
    a = registry.candidate("Alex", "source:a")
    b = registry.candidate("Alex", "source:b")
    assert a.person_id != b.person_id
    assert not registry.assert_identity(a, strong_link_evidence=False).resolved
    resolved = registry.assert_identity(a, strong_link_evidence=True)
    role = registry.matter_role(resolved, "matter:1", "assignee_candidate")
    assert resolved.resolved
    assert role.matter_id == "matter:1"
    revision = registry.split((a.person_id, b.person_id), reason="user correction")
    assert revision.action == "split"
