from matters.application.reconciliation import MatterReconciliationOwner
from matters.domain.admission import MatterAdmission
from matters.domain.context import (
    ContextSignal,
    GranularityAssessment,
    MAX_RECONCILIATION_CANDIDATES,
    MatterPlacementCandidate,
    MatterReconciliationRequest,
    ProjectContext,
)


def _signal(kind, value, evidence):
    return ContextSignal(kind, value, (evidence,))


def _context(*signals, freshness="current"):
    return ProjectContext(tuple(signals), freshness=freshness)


def _candidate(
    matter_id,
    *signals,
    broad_scope=False,
    semantic_identity_key=None,
):
    return MatterPlacementCandidate(
        matter_id=matter_id,
        semantic_identity_key=semantic_identity_key or matter_id,
        context=_context(*signals),
        broad_scope=broad_scope,
    )


def _request(
    *signals,
    candidates=(),
    semantic_identity_key="incoming goal",
    granularity=None,
    conflict=False,
):
    return MatterReconciliationRequest(
        source_ids=("source:incoming",),
        evidence_ids=("evidence:incoming",),
        semantic_identity_key=semantic_identity_key,
        context=_context(*signals),
        candidates=tuple(candidates),
        granularity=granularity
        or GranularityAssessment(independently_useful_goal=True),
        conflict=conflict,
    )


def test_multiple_identity_signals_append_through_existing_admission_owner():
    candidate = _candidate(
        "matter:hackathon",
        _signal("goal", "Submit Build Week project", "evidence:old-goal"),
        _signal("provider_thread", "thread:build-week", "evidence:old-thread"),
        semantic_identity_key="Build Week participation",
    )
    admission = MatterAdmission()
    owner = MatterReconciliationOwner(admission)

    result = owner.execute(
        _request(
            _signal("goal", " submit build week PROJECT ", "evidence:new-goal"),
            _signal("provider_thread", "thread:build-week", "evidence:new-thread"),
            candidates=(candidate,),
            semantic_identity_key="deadline message",
        )
    )

    assert result.decision.status == "append_to_current"
    assert result.decision.target_matter_id == "matter:hackathon"
    assert result.decision.matched_signal_kinds == ("goal", "provider_thread")
    assert result.admission is not None
    assert result.admission.matter is not None
    assert result.admission.matter.matter_id == "matter:hackathon"
    assert result.admission.matter.semantic_identity_id


def test_one_weak_signal_cannot_merge_or_create_containment():
    candidate = _candidate(
        "matter:unrelated",
        _signal("person", "Alex", "evidence:old-person"),
    )
    owner = MatterReconciliationOwner(MatterAdmission())

    decision = owner.reconcile(
        _request(
            _signal("person", "Alex", "evidence:new-person"),
            candidates=(candidate,),
        )
    )

    assert decision.status == "admit_related"
    assert decision.related_matter_ids == ("matter:unrelated",)
    assert decision.target_matter_id == ""
    assert decision.parent_matter_id == ""


def test_broad_project_context_admits_child_and_uses_hierarchy_callbacks():
    parent = _candidate(
        "matter:repository",
        _signal("repository_project", "repo:matters", "evidence:old-repo"),
        _signal("codex_workspace", "workspace:matters", "evidence:old-workspace"),
        broad_scope=True,
        semantic_identity_key="Matters software project",
    )
    registered = []
    attachments = []

    def register_matter(matter_id, *, change_ref):
        registered.append((matter_id, change_ref))

    def attach_child(**payload):
        attachments.append(payload)
        return "hierarchy:attached"

    owner = MatterReconciliationOwner(
        MatterAdmission(),
        register_matter=register_matter,
        attach_child=attach_child,
    )
    result = owner.execute(
        _request(
            _signal("repository_project", "repo:matters", "evidence:new-repo"),
            _signal(
                "codex_workspace",
                "workspace:matters",
                "evidence:new-workspace",
            ),
            candidates=(parent,),
            semantic_identity_key="Context-aware reconciliation feature",
        )
    )

    assert result.decision.status == "admit_child"
    assert result.admission is not None and result.admission.matter is not None
    child_id = result.admission.matter.matter_id
    assert registered == [(child_id, "reconciliation:1:admit_child")]
    assert attachments == [
        {
            "parent_matter_id": "matter:repository",
            "child_matter_id": child_id,
            "role": "optional",
            "confidence": "bounded",
            "rationale": result.decision.rationale,
            "evidence_ids": result.decision.evidence_ids,
        }
    ]
    assert result.hierarchy_result == "hierarchy:attached"


def test_small_occurrence_stays_event_and_appends_only_with_licensed_host():
    candidate = _candidate(
        "matter:trip",
        _signal("goal", "Japan trip", "evidence:old-goal"),
        _signal("provider_thread", "thread:trip", "evidence:old-thread"),
        semantic_identity_key="Japan trip",
    )
    owner = MatterReconciliationOwner(MatterAdmission())

    decision = owner.reconcile(
        _request(
            _signal("goal", "Japan trip", "evidence:new-goal"),
            _signal("provider_thread", "thread:trip", "evidence:new-thread"),
            candidates=(candidate,),
            semantic_identity_key="boarding notice",
            granularity=GranularityAssessment(one_time_occurrence=True),
        )
    )

    assert decision.status == "append_to_current"
    assert decision.granularity == "event"
    assert decision.target_matter_id == "matter:trip"


def test_equal_candidate_support_preserves_uncertain_alternative():
    signals_a = (
        _signal("goal", "Find a job", "evidence:a-goal"),
        _signal("subject", "job search", "evidence:a-subject"),
    )
    signals_b = (
        _signal("goal", "Find a job", "evidence:b-goal"),
        _signal("subject", "job search", "evidence:b-subject"),
    )
    owner = MatterReconciliationOwner(MatterAdmission())

    decision = owner.reconcile(
        _request(
            _signal("goal", "Find a job", "evidence:new-goal"),
            _signal("subject", "job search", "evidence:new-subject"),
            candidates=(
                _candidate("matter:a", *signals_a),
                _candidate("matter:b", *signals_b),
            ),
        )
    )

    assert decision.status == "preserve_uncertain_alternative"
    assert decision.candidate_matter_ids == ("matter:a", "matter:b")


def test_no_context_match_admits_root_and_related_dispatch_is_separate():
    related_calls = []

    def relate_matters(**payload):
        related_calls.append(payload)
        return "relation:written"

    owner = MatterReconciliationOwner(
        MatterAdmission(),
        relate_matters=relate_matters,
    )
    root = owner.execute(
        _request(
            _signal("goal", "Plan a new trip", "evidence:trip"),
            candidates=(),
            semantic_identity_key="Plan a new trip",
        )
    )
    assert root.decision.status == "admit_root"
    assert root.admission is not None and root.admission.matter is not None

    related_candidate = _candidate(
        "matter:subscription",
        _signal("person", "OpenAI", "evidence:old-openai"),
    )
    related = owner.execute(
        _request(
            _signal("person", "OpenAI", "evidence:new-openai"),
            candidates=(related_candidate,),
            semantic_identity_key="Build Week participation",
        )
    )
    assert related.decision.status == "admit_related"
    assert related.relation_result == "relation:written"
    assert related_calls[0]["related_matter_ids"] == ("matter:subscription",)


def test_stale_or_unbounded_candidate_window_blocks_without_owner_writes():
    admission = MatterAdmission()
    owner = MatterReconciliationOwner(admission)
    stale = MatterPlacementCandidate(
        matter_id="matter:stale",
        semantic_identity_key="stale",
        context=_context(
            _signal("goal", "Stale goal", "evidence:stale"),
            freshness="stale",
        ),
    )
    stale_decision = owner.reconcile(
        _request(
            _signal("goal", "Stale goal", "evidence:new"),
            candidates=(stale,),
        )
    )
    assert stale_decision.status == "blocked"

    candidates = tuple(
        _candidate(
            f"matter:{index}",
            _signal("person", f"Person {index}", f"evidence:{index}"),
        )
        for index in range(MAX_RECONCILIATION_CANDIDATES + 1)
    )
    bounded_decision = owner.reconcile(
        _request(
            _signal("person", "Nobody", "evidence:nobody"),
            candidates=candidates,
        )
    )
    assert bounded_decision.status == "blocked"
    assert len(bounded_decision.candidate_matter_ids) == MAX_RECONCILIATION_CANDIDATES
    assert admission.admitted_count == 0
