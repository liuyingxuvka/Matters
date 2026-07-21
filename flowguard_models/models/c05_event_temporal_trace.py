"""C5 Event & Temporal Trace finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C5_event_temporal_trace",
    title="C5 Event & Temporal Trace",
    modeled_boundary=(
        "typed events, record/claimed time, modality, supersession, contradiction, "
        "logical-event identity and revision projection, gaps, Start-time versus "
        "meaningful-clue-time separation, canonical "
        "material-clue dispositions, explicit observed/reported/planned/"
        "ai-inferred certainty, SituationGraph event-node revision, and bounded "
        "Matter-link candidates that never promote an Event into a Matter, plus "
        "current-projection exclusion of rebased stale analysis-owner outputs"
    ),
    state_fields=(
        "event.identity",
        "event.logical_event_key",
        "event.current_revision",
        "event.supersedes_event_id",
        "event.durable_registry_revision",
        "event.owning_matter_path",
        "event.importance",
        "event.temporal_fields",
        "event.matter_relation_candidate",
        "trace.supersession",
        "trace.conflict",
        "trace.material_clue_identity",
        "trace.materiality_disposition",
        "trace.materiality_rationale",
        "trace.start_time",
        "trace.start_time_basis",
        "trace.start_time_source_provider",
        "trace.start_time_revision",
        "trace.latest_meaningful_clue_at",
        "trace.material_clue_revision",
        "trace.supersedes_clue_id",
        "trace.observation_time_source_revision",
        "trace.parent_narrative_refresh_trigger_revision",
        "trace.situation_graph_event_revision",
        "event.certainty_class",
        "event.inference_confidence",
        "event.alternative_interpretations",
    ),
    owned_write_fields=(
        "event.identity",
        "event.logical_event_key",
        "event.current_revision",
        "event.supersedes_event_id",
        "event.durable_registry_revision",
        "event.owning_matter_path",
        "event.importance",
        "event.temporal_fields",
        "event.matter_relation_candidate",
        "trace.supersession",
        "trace.conflict",
        "trace.material_clue_identity",
        "trace.materiality_disposition",
        "trace.materiality_rationale",
        "trace.start_time",
        "trace.start_time_basis",
        "trace.start_time_source_provider",
        "trace.start_time_revision",
        "trace.latest_meaningful_clue_at",
        "trace.material_clue_revision",
        "trace.supersedes_clue_id",
        "trace.observation_time_source_revision",
        "trace.parent_narrative_refresh_trigger_revision",
        "trace.situation_graph_event_revision",
        "event.certainty_class",
        "event.inference_confidence",
        "event.alternative_interpretations",
    ),
    side_effect_classes=("event_registry_write",),
    completion_evidence=(
        "TypedEvent",
        "LogicalEventCurrentProjection",
        "LogicalEventSupersession",
        "TimelineCandidate",
        "TemporalGap",
        "TemporalConflict",
        "CurrentBestTemporalInterpretation",
        "MatterEventLinkCandidate",
        "EventOnly",
        "MaterialClue",
        "NonMaterialProcessing",
        "TemporalFieldsSeparated",
        "StartBoundary",
        "StartBoundaryRevision",
        "ObservationTimeCorrected",
        "MatterActivityBackfilled",
        "ObservationTimeGap",
        "ParentNarrativeRefreshRequired",
        "SituationGraphEventNode",
        "EventCertainty",
        "InferenceAlternatives",
        "StaleTemporalOwnerOutputExcluded",
        "AnalysisOutputReplacementPending",
        "DurableEventRegistryRestored",
    ),
    rules=(
        CaseRule(
            case_id="same_logical_event_multiple_source_revisions",
            decision="one_current_logical_event_projected",
            label="one_current_logical_event_projected",
            writes=(
                "event.logical_event_key",
                "event.current_revision",
                "event.supersedes_event_id",
                "event.owning_matter_path",
                "event.importance",
                "trace.supersession",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "TypedEvent",
                "TimelineCandidate",
                "LogicalEventCurrentProjection",
                "LogicalEventSupersession",
            ),
            reason=(
                "all SourceVersions and analysis revisions describing one "
                "licensed occurrence share one stable logical event key; one "
                "current revision owns the ordinary Timeline row while prior "
                "revisions remain on demand"
            ),
        ),
        CaseRule(
            case_id="restart_before_event_correction",
            decision="durable_event_registry_restored_before_revision",
            label="durable_event_registry_restored_before_revision",
            writes=(
                "event.durable_registry_revision",
                "event.logical_event_key",
                "event.current_revision",
                "event.supersedes_event_id",
                "trace.supersession",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "DurableEventRegistryRestored",
                "LogicalEventCurrentProjection",
                "LogicalEventSupersession",
            ),
            reason=(
                "service startup restores every durable current event object "
                "and explicit supersession edge before C5 appends a correction "
                "to the existing event id, so restart never revives an older "
                "deadline or creates a duplicate peer Timeline row"
            ),
        ),
        CaseRule(
            case_id="logical_event_revision_conflicts",
            decision="one_conflict_preserved_timeline_row",
            label="one_conflict_preserved_timeline_row",
            writes=(
                "event.logical_event_key",
                "event.current_revision",
                "trace.supersession",
                "trace.conflict",
                "event.alternative_interpretations",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "TimelineCandidate",
                "TemporalConflict",
                "CurrentBestTemporalInterpretation",
                "LogicalEventCurrentProjection",
            ),
            reason=(
                "materially incompatible revisions remain alternatives inside "
                "one conflict-preserved logical event instead of unexplained "
                "duplicate peer timeline rows"
            ),
        ),
        CaseRule(
            case_id="earliest_traceable_start_boundary",
            decision="earliest_start_boundary_registered",
            label="earliest_start_boundary_registered",
            writes=(
                "trace.start_time",
                "trace.start_time_basis",
                "trace.start_time_source_provider",
                "trace.start_time_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "StartBoundary",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "C5 compares every parseable claimed Event time, Event record "
                "time, and exact related SourceVersion authored, created, "
                "modified, sent, received, observed, or Codex first-recorded "
                "time; the earliest user-world candidate becomes the auditable "
                "Matter Start boundary without becoming an occurred Event"
            ),
        ),
        CaseRule(
            case_id="new_evidence_predates_start_boundary",
            decision="earlier_start_boundary_revision_appended",
            label="earlier_start_boundary_revision_appended",
            writes=(
                "trace.start_time",
                "trace.start_time_basis",
                "trace.start_time_source_provider",
                "trace.start_time_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "StartBoundary",
                "StartBoundaryRevision",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "newly covered current evidence that predates the current Start "
                "boundary appends an earlier revision and refreshes the Start "
                "filter while preserving latest-meaningful-clue activity order"
            ),
        ),
        CaseRule(
            case_id="only_processing_time_for_start",
            decision="start_boundary_gap_preserved",
            label="start_boundary_gap_preserved",
            writes=("trace.conflict",),
            emitted_tokens=("TemporalGap",),
            reason=(
                "scan, registration, extraction, analysis, migration, deadline, "
                "due, expiry, and Hero timestamps cannot fill a missing Matter "
                "Start boundary"
            ),
        ),
        CaseRule(
            case_id="typed_event_projected_to_situation_graph",
            decision="situation_graph_event_revision_current",
            label="situation_graph_event_revision_current",
            writes=(
                "trace.situation_graph_event_revision",
                "event.certainty_class",
                "event.inference_confidence",
                "event.alternative_interpretations",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "TypedEvent",
                "SituationGraphEventNode",
                "EventCertainty",
                "InferenceAlternatives",
            ),
            reason=(
                "each timeline event is projected once with its source time, "
                "claimed time, modality, and exactly one visible certainty class; "
                "an AI-inferred event keeps confidence and alternatives and never "
                "becomes confirmed merely because its expected date elapsed"
            ),
        ),
        CaseRule(
            case_id="future_due_activity_has_historical_observation",
            decision="observation_time_correction_appended",
            label="observation_time_correction_appended",
            writes=(
                "trace.material_clue_identity",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
                "trace.supersedes_clue_id",
                "trace.observation_time_source_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "MaterialClue",
                "ObservationTimeCorrected",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "a future due or claimed time is replaced for activity ordering "
                "by the parseable observation time on the exact historical "
                "SourceVersion or current typed Event while the due time remains "
                "a separate temporal field"
            ),
        ),
        CaseRule(
            case_id="canonical_matter_missing_activity_with_source_time",
            decision="matter_activity_backfilled_from_observation",
            label="matter_activity_backfilled_from_observation",
            writes=(
                "trace.material_clue_identity",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
                "trace.observation_time_source_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "MaterialClue",
                "MatterActivityBackfilled",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "a canonical Matter without an activity row may use the exact "
                "historical SourceVersion or current inventory occurrence "
                "observation time plus its current bilingual semantic summary; "
                "due, deadline, scan, processing, and retry times remain forbidden"
            ),
        ),
        CaseRule(
            case_id="corrected_clue_late_bound_to_canonical_matter",
            decision="corrected_activity_projection_extended",
            label="corrected_activity_projection_extended",
            writes=(
                "trace.material_clue_revision",
                "trace.supersedes_clue_id",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=("ObservationTimeCorrected",),
            reason=(
                "an existing correction clue may be projected to a later "
                "canonical Matter without duplicating the clue or reviving the "
                "superseded future due time"
            ),
        ),
        CaseRule(
            case_id="no_parseable_observation_time",
            decision="observation_time_gap_preserved",
            label="observation_time_gap_preserved",
            writes=("trace.conflict",),
            side_effects=("event_registry_write",),
            emitted_tokens=("ObservationTimeGap", "TemporalGap"),
            reason=(
                "missing historical and event observation timestamps remain a "
                "visible gap; processing time is not substituted as user-world evidence"
            ),
        ),
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
            case_id="explicit_source_modality_preserved",
            decision="source_modality_preserved",
            label="source_modality_preserved",
            writes=("event.identity", "event.temporal_fields"),
            side_effects=("event_registry_write",),
            emitted_tokens=("TypedEvent", "EventCertainty"),
            reason=(
                "an issued boarding pass, received message, reported result, or "
                "future schedule retains its observed, reported, or planned "
                "modality and is never relabeled as AI inference"
            ),
        ),
        CaseRule(
            case_id="necessary_past_gap_supported",
            decision="revisable_historical_gap_inference",
            label="revisable_historical_gap_inference",
            writes=(
                "event.identity",
                "event.temporal_fields",
                "event.certainty_class",
                "event.inference_confidence",
                "event.alternative_interpretations",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=("TypedEvent", "EventCertainty", "InferenceAlternatives"),
            reason=(
                "only a necessary already-elapsed gap may receive an ai_inferred "
                "candidate, bound to analysis time, past target time, current "
                "evidence coverage, confidence, alternatives, contradiction "
                "triggers, and a revisable disposition"
            ),
        ),
        CaseRule(
            case_id="future_candidate_marked_ai_inferred",
            decision="future_inference_rejected_to_world_model",
            label="future_inference_rejected_to_world_model",
            emitted_tokens=("TemporalGap",),
            reason=(
                "a future expectation cannot enter C5 as occurred or AI inferred; "
                "it may be reformulated only as a testable C11 World Model prediction"
            ),
        ),
        CaseRule(
            case_id="rebased_stale_temporal_owner_output",
            decision="stale_temporal_output_excluded_pending_replacement",
            label="stale_temporal_output_excluded_pending_replacement",
            emitted_tokens=(
                "StaleTemporalOwnerOutputExcluded",
                "AnalysisOutputReplacementPending",
                "TemporalGap",
            ),
            reason=(
                "a current-contract rebase preserves the old package, result, "
                "finding, and temporal output in history but current cards, "
                "timelines, hierarchy inventory, and SituationGraph exclude it "
                "until an active current-contract result owns that exact output "
                "again; affected graph coverage stays partial"
            ),
        ),
        CaseRule(
            case_id="assignment_without_start",
            decision="temporal_gap",
            label="assignment_temporal_gap",
            writes=(
                "event.temporal_fields",
                "trace.start_time",
                "trace.start_time_basis",
                "trace.start_time_source_provider",
                "trace.start_time_revision",
            ),
            emitted_tokens=("RecordEvent", "TemporalGap", "StartBoundary"),
            reason=(
                "assignment is a provider record rather than proof of actual "
                "work occurrence, but its record time may be the earliest "
                "traceable Matter Start boundary while the actual-start gap remains"
            ),
        ),
        CaseRule(
            case_id="file_or_exif_time_without_event_claim",
            decision="metadata_time_only",
            label="metadata_time_only",
            writes=(
                "event.temporal_fields",
                "trace.start_time",
                "trace.start_time_basis",
                "trace.start_time_source_provider",
                "trace.start_time_revision",
            ),
            emitted_tokens=("RecordEvent", "TemporalGap", "StartBoundary"),
            reason=(
                "filesystem, message, or EXIF time remains source metadata and "
                "does not license an occurred Event, but may establish the "
                "earliest traceable Matter Start boundary"
            ),
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
        CaseRule(
            case_id="bounded_child_activity_event",
            decision="event_registered_with_matter_link_candidate",
            label="event_registered_with_matter_link_candidate",
            writes=(
                "event.identity",
                "event.temporal_fields",
                "event.matter_relation_candidate",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "TypedEvent",
                "TimelineCandidate",
                "MatterEventLinkCandidate",
                "EventOnly",
            ),
            reason=(
                "a booking, application reply, payment, or other bounded occurrence "
                "remains one Event; C6 may consume its evidence-backed link candidate "
                "but only C6 can decide whether a separate child Matter exists"
            ),
        ),
        CaseRule(
            case_id="material_user_world_clue",
            decision="material_clue_registered",
            label="material_clue_registered",
            writes=(
                "event.temporal_fields",
                "trace.material_clue_identity",
                "trace.materiality_disposition",
                "trace.materiality_rationale",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "MaterialClue",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "new evidence that changes state, outcome, next step, important "
                "time, person, relationship, hierarchy, or useful summary keeps "
                "its user-world clue time distinct from Start and processing time"
            ),
        ),
        CaseRule(
            case_id="material_child_clue_changes_parent_understanding",
            decision="parent_narrative_refresh_triggered",
            label="parent_narrative_refresh_triggered",
            writes=(
                "trace.parent_narrative_refresh_trigger_revision",
            ),
            side_effects=("event_registry_write",),
            emitted_tokens=(
                "MaterialClue",
                "ParentNarrativeRefreshRequired",
                "TemporalFieldsSeparated",
            ),
            reason=(
                "one material descendant clue queues an idempotent narrative "
                "refresh for each current ancestor while the clue observation "
                "time, not later narrative generation time, remains the sole "
                "activity-order authority"
            ),
        ),
        CaseRule(
            case_id="scan_retry_or_reword_without_semantic_change",
            decision="non_material_processing_recorded",
            label="non_material_processing_recorded",
            writes=("event.temporal_fields",),
            emitted_tokens=("NonMaterialProcessing", "TemporalFieldsSeparated"),
            reason=(
                "inventory, retry, receipt, read timestamp, localization, hero "
                "generation, or rewording without semantic change cannot advance "
                "Matter activity time"
            ),
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C5-016-restart-revives-superseded-event",
            protected_error_class="durable_event_registry_not_restored",
            description=(
                "the service restarts with an empty in-memory event registry, "
                "then appends a corrected deadline without restoring the prior "
                "durable event and supersession edge"
            ),
            protected_harm=(
                "the old and corrected deadline both appear as peer Timeline "
                "rows after restart"
            ),
            case_id="restart_before_event_correction",
            broken_decision="correction_appended_to_empty_registry",
            broken_writes=(
                "event.logical_event_key",
                "event.current_revision",
                "event.supersedes_event_id",
            ),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TimelineCandidate",),
        ),
        HazardSpec(
            failure_id="H-C5-015-logical-event-revisions-duplicate-timeline",
            protected_error_class="logical_event_revision_duplication",
            description=(
                "two SourceVersions or analysis revisions of one occurrence "
                "receive unrelated current event identities and render twice"
            ),
            protected_harm=(
                "the Timeline repeats the same purchase, booking, entry, or "
                "completion and makes the Matter chronology misleading"
            ),
            case_id="same_logical_event_multiple_source_revisions",
            broken_decision="duplicate_timeline_rows_projected",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TimelineCandidate",),
        ),
        HazardSpec(
            failure_id="H-C5-014-rebased-output-remains-current",
            protected_error_class="stale_analysis_output_projection",
            description=(
                "a temporal output from a superseded analysis contract remains "
                "visible in a current card, timeline, hierarchy inventory, or "
                "SituationGraph without an active current replacement owner"
            ),
            protected_harm=(
                "obsolete future inference or another stale model output is "
                "presented as current user-world chronology"
            ),
            case_id="rebased_stale_temporal_owner_output",
            broken_decision="stale_temporal_output_projected_current",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("TypedEvent", "SituationGraphEventNode"),
        ),
        HazardSpec(
            failure_id="H-C5-011-first-nonempty-time-hides-earlier-start",
            protected_error_class="start_boundary_candidate_loss",
            description=(
                "one claimed or preferred timestamp is selected before all "
                "Event and exact SourceVersion candidates are compared"
            ),
            protected_harm=(
                "the card stays blank or starts too late even though an earlier "
                "cover letter, message, file, or Codex record is traceable"
            ),
            case_id="earliest_traceable_start_boundary",
            broken_decision="preferred_time_registered_without_candidate_exhaustion",
            broken_writes=("trace.start_time", "trace.start_time_revision"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("StartBoundary",),
        ),
        HazardSpec(
            failure_id="H-C5-012-processing-time-fills-missing-start",
            protected_error_class="start_processing_time_substitution",
            description=(
                "scan, registration, analysis, migration, due, deadline, or "
                "Hero time is used when no user-world Start candidate exists"
            ),
            protected_harm=(
                "technical maintenance or a future obligation is presented as "
                "the beginning of the user's Matter"
            ),
            case_id="only_processing_time_for_start",
            broken_decision="processing_time_registered_as_start",
            broken_writes=("trace.start_time", "trace.start_time_revision"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("StartBoundary",),
        ),
        HazardSpec(
            failure_id="H-C5-008-parent-narrative-generation-bubbles-activity",
            protected_error_class="narrative_processing_activity_conflation",
            description=(
                "AI parent-overview generation time replaces the descendant "
                "clue observation time or advances parent activity"
            ),
            protected_harm=(
                "background narrative maintenance appears as new user-world progress"
            ),
            case_id="material_child_clue_changes_parent_understanding",
            broken_decision="narrative_generation_registered_as_material_clue",
            broken_writes=(
                "trace.latest_meaningful_clue_at",
                "trace.parent_narrative_refresh_trigger_revision",
            ),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("MaterialClue",),
        ),
        HazardSpec(
            failure_id="H-C5-006-future-due-used-as-activity-observation",
            protected_error_class="activity_observation_due_time_conflation",
            description=(
                "a future deadline or claimed time orders current activity even "
                "though the exact historical source revision has an earlier "
                "observation timestamp"
            ),
            protected_harm=(
                "inactive Matters bubble above genuinely recent work and the "
                "timeline misstates when evidence arrived"
            ),
            case_id="future_due_activity_has_historical_observation",
            broken_decision="material_clue_registered",
            broken_writes=("trace.latest_meaningful_clue_at",),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("MaterialClue",),
        ),
        HazardSpec(
            failure_id="H-C5-017-source-time-eligible-activity-remains-missing",
            protected_error_class="matter_activity_backfill_omission",
            description=(
                "a canonical Matter has a current bilingual semantic projection "
                "and an exact parseable SourceVersion or inventory occurrence "
                "observation time but remains without current activity"
            ),
            protected_harm=(
                "the card has no activity date and latest-clue ordering cannot "
                "reflect the user's real chronology despite available evidence"
            ),
            case_id="canonical_matter_missing_activity_with_source_time",
            broken_decision="activity_gap_silently_accepted",
            broken_writes=(
                "trace.material_clue_identity",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
                "trace.observation_time_source_revision",
            ),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("MatterActivityBackfilled",),
        ),
        HazardSpec(
            failure_id="H-C5-007-observation-gap-uses-processing-time",
            protected_error_class="processing_time_evidence_substitution",
            description=(
                "repair uses scan, migration, or retry processing time when no "
                "source/event observation time exists"
            ),
            protected_harm=(
                "technical maintenance becomes false user-world activity"
            ),
            case_id="no_parseable_observation_time",
            broken_decision="observation_time_correction_appended",
            broken_writes=("trace.latest_meaningful_clue_at",),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("ObservationTimeCorrected",),
        ),
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
        HazardSpec(
            failure_id="H-C5-005-event-mechanically-promoted-to-matter",
            protected_error_class="event_matter_identity_conflation",
            description="one bounded occurrence is mechanically promoted into a Matter",
            protected_harm=(
                "timeline granularity creates noisy duplicate Matters and bypasses "
                "C6 admission and hierarchy decisions"
            ),
            case_id="bounded_child_activity_event",
            broken_decision="matter_admitted",
            broken_writes=("matter.identity", "matter.admission_status"),
            broken_side_effects=("matter_registry_write",),
            broken_tokens=("AdmittedMatter",),
        ),
        HazardSpec(
            failure_id="H-C5-006-processing-time-becomes-clue-time",
            protected_error_class="processing_activity_time_conflation",
            description="a scan, retry, or AI completion timestamp advances Matter activity",
            protected_harm="inactive Matters bubble merely because the backend processed them",
            case_id="scan_retry_or_reword_without_semantic_change",
            broken_decision="material_clue_registered",
            broken_writes=(
                "trace.material_clue_identity",
                "trace.materiality_disposition",
                "trace.latest_meaningful_clue_at",
                "trace.material_clue_revision",
            ),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("MaterialClue",),
        ),
        HazardSpec(
            failure_id="H-C5-007-start-time-becomes-clue-time",
            protected_error_class="start_activity_time_conflation",
            description="Matter Start time is reused as latest meaningful clue time",
            protected_harm="filter chronology and dynamic activity ordering become indistinguishable",
            case_id="material_user_world_clue",
            broken_decision="start_time_reused_for_activity_order",
            broken_writes=("trace.latest_meaningful_clue_at",),
            broken_tokens=("MaterialClue",),
        ),
        HazardSpec(
            failure_id="H-C5-009-explicit-source-modality-relabeled-inferred",
            protected_error_class="source_modality_authority_loss",
            description="an observed, reported, or planned source record is relabeled AI inferred",
            protected_harm="the UI hides which information came directly from evidence",
            case_id="explicit_source_modality_preserved",
            broken_decision="ai_inferred_event_candidate",
            broken_writes=("event.temporal_fields", "event.certainty_class"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("EventCertainty",),
        ),
        HazardSpec(
            failure_id="H-C5-010-future-ai-inference-enters-occurred-trace",
            protected_error_class="future_prediction_temporal_backwrite",
            description="a future AI expectation is written as an occurred temporal event",
            protected_harm="a forecast becomes false history before it can be observed",
            case_id="future_candidate_marked_ai_inferred",
            broken_decision="occurred_event_candidate",
            broken_writes=("event.identity", "event.temporal_fields"),
            broken_side_effects=("event_registry_write",),
            broken_tokens=("ModalityOccurred",),
        ),
    ),
    risk_classes=("ordering", "state_transition", "evidence", "side_effect"),
    template_no_match_reason=(
        "The Phase A template search returned no temporal modality and supersession template."
    ),
    blindspots=(
        "timezone parsing and provider clock skew require concrete payload tests",
        "ResearchGuard temporal and hierarchy suggestions remain advisory and are not canonical writers",
    ),
    claim_boundary=(
        "This receipt can establish C5 abstract modality, record/reality, "
        "Start/clue/processing separation, material-clue admission, supersession, "
        "and Event/Matter separation hazards. It does not establish "
        "factual occurrence, clock accuracy, canonical Matter hierarchy, "
        "ResearchGuard coverage, or production replay."
    ),
)
