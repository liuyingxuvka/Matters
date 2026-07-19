from matters.domain.admission import AdmissionPacket, MatterAdmission


def test_source_only_uncertain_admitted_and_blocked_are_distinct():
    owner = MatterAdmission()
    source = ("source:1",)
    assert owner.decide(AdmissionPacket(source, possibility_only=True)).status == "source_only"
    uncertain = owner.decide(AdmissionPacket(source))
    assert uncertain.status == "uncertain"
    assert uncertain.candidate is not None
    assert owner.admitted_count == 0
    admitted = owner.decide(
        AdmissionPacket(
            source,
            evidence_ids=("evidence:1",),
            explicit_goal_or_obligation=True,
        )
    )
    assert admitted.status == "admitted"
    assert owner.admitted_count == 1
    conflicted = owner.decide(AdmissionPacket(source, conflict=True))
    assert conflicted.status == "uncertain"
    assert conflicted.candidate is not None
    assert owner.decide(AdmissionPacket(source, access_blocked=True)).status == "blocked"
