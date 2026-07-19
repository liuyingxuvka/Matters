"""C5 Event & Temporal Trace finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C5_event_temporal_trace",
    title="C5 Event & Temporal Trace",
    modeled_boundary="typed events, record/claimed time, modality, supersession, contradiction, and gaps",
    state_fields=(
        "event.identity",
        "event.temporal_fields",
        "trace.supersession",
        "trace.conflict",
    ),
    owned_write_fields=(
        "event.identity",
        "event.temporal_fields",
        "trace.supersession",
        "trace.conflict",
    ),
    side_effect_classes=("event_registry_write",),
    completion_evidence=(
        "TypedEvent",
        "TimelineCandidate",
        "TemporalGap",
        "TemporalConflict",
        "CurrentBestTemporalInterpretation",
    ),
    rules=(
        CaseRule(
            case_id="explicit_actual_start",
            decision="occurred_event_candidate",
            label="occurred_event_candidate",
            writes=("event.identity", "event.temporal_fields"),
            side_effects=("event_registry_write",),
            emitted_tokens=("TypedEvent", "ModalityOccurred"),
            reason="anchored evidence explicitly records actual start",
        ),
        CaseRule(
            case_id="future_meeting",
            decision="planned_event_candidate",
            label="planned_event_candidate",
            writes=("event.identity", "event.temporal_fields"),
            side_effects=("event_registry_write",),
            emitted_tokens=("TypedEvent", "ModalityPlanned"),
            reason="future meeting remains planned",
        ),
        CaseRule(
            case_id="assignment_without_start",
            decision="temporal_gap",
            label="assignment_temporal_gap",
            writes=("event.temporal_fields",),
            emitted_tokens=("RecordEvent", "TemporalGap"),
            reason="assignment is a provider record, not actual work start",
        ),
        CaseRule(
            case_id="file_or_exif_time_without_event_claim",
            decision="metadata_time_only",
            label="metadata_time_only",
            writes=("event.temporal_fields",),
            emitted_tokens=("RecordEvent", "TemporalGap"),
            reason="filesystem, message, or EXIF time remains metadata until content licenses an event",
        ),
        CaseRule(
            case_id="done_then_reopen_blocked",
            decision="temporal_conflict_preserved",
            label="temporal_conflict_preserved",
            writes=(
                "event.identity",
                "event.temporal_fields",
                "trace.supersession",
                "trace.conflict",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "TimelineCandidate",
                "TemporalConflict",
                "CurrentBestTemporalInterpretation",
            ),
            reason=(
                "reopen and blocker preserve contradiction with earlier Done "
                "while publishing the current best-supported interpretation"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C5-001-future-event-marked-occurred",
            protected_error_class="future_past_confusion",
            description="a future planned meeting is recorded as occurred",
            protected_harm="the timeline reports an event that has not happened",
            case_id="future_meeting",
            broken_decision="occurred_event_candidate",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TypedEvent", "ModalityOccurred"),
        ),
        HazardSpec(
            failure_id="H-C5-002-assignment-proves-start",
            protected_error_class="record_reality_conflation",
            description="provider assignment is treated as actual work starting",
            protected_harm="lifecycle state advances without occurrence evidence",
            case_id="assignment_without_start",
            broken_decision="occurred_event_candidate",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TypedEvent", "ModalityOccurred"),
        ),
        HazardSpec(
            failure_id="H-C5-003-latest-field-erases-conflict",
            protected_error_class="temporal_supersession_loss",
            description="the latest field erases Done/reopen contradiction history",
            protected_harm="state decisions ignore material contrary evidence",
            case_id="done_then_reopen_blocked",
            broken_decision="latest_state_only",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TypedEvent",),
        ),
        HazardSpec(
            failure_id="H-C5-004-metadata-time-becomes-event",
            protected_error_class="metadata_event_time_conflation",
            description="file, mail, or EXIF metadata time is treated as occurred event time",
            protected_harm="the timeline fabricates an event from record metadata",
            case_id="file_or_exif_time_without_event_claim",
            broken_decision="occurred_event_candidate",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TypedEvent", "ModalityOccurred"),
        ),
    ),
    risk_classes=("ordering", "state_transition", "evidence", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no temporal modality and supersession template."
    ),
    blindspots=(
        "timezone parsing and provider clock skew require concrete payload tests",
        "ResearchGuard temporal-trace suggestions remain advisory and are not canonical writers",
    ),
    claim_boundary=(
        "This receipt can establish C5 abstract modality, record/reality, and "
        "supersession hazards. It does not establish factual occurrence, clock "
        "accuracy, ResearchGuard coverage, or production replay."
    ),
)
