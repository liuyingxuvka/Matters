"""C3 Evidence Qualification finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C3_evidence_qualification",
    title="C3 Evidence Qualification",
    modeled_boundary=(
        "precise line/character, page/passage, sheet/cell, message/thread/"
        "attachment, image/OCR-region and metadata anchors, modality, gaps, "
        "display safety, exact Gmail-body continuation line anchors, real "
        "Images-gallery eligibility, and source-version freshness"
    ),
    state_fields=(
        "evidence.anchor",
        "evidence.modality",
        "evidence.freshness",
        "evidence.gap",
        "evidence.display_permission",
        "evidence.gallery_display_eligibility",
        "evidence.source_neighborhood_context",
        "evidence.atomic_batch_identity",
        "evidence.anchor_set_pointer",
        "evidence.anchor_set_source_version",
        "evidence.anchor_set_count",
        "evidence.anchor_set_digest",
        "evidence.gmail_no_text_disposition",
    ),
    owned_write_fields=(
        "evidence.anchor",
        "evidence.modality",
        "evidence.freshness",
        "evidence.gap",
        "evidence.display_permission",
        "evidence.gallery_display_eligibility",
        "evidence.source_neighborhood_context",
        "evidence.atomic_batch_identity",
        "evidence.anchor_set_pointer",
        "evidence.anchor_set_source_version",
        "evidence.anchor_set_count",
        "evidence.anchor_set_digest",
        "evidence.gmail_no_text_disposition",
    ),
    side_effect_classes=("evidence_registry_write",),
    completion_evidence=(
        "EvidenceAnchor",
        "AssertionCandidate",
        "EvidenceGap",
        "StaleEvidence",
        "VisualAnchor",
        "DisplayPermission",
        "SourceNeighborhoodContext",
        "AtomicEvidenceBatch",
        "BoundedAnchorSetPointer",
        "AnchorSetPointerVerified",
        "GmailNoTextEvidenceNotApplicable",
    ),
    rules=(
        CaseRule(
            case_id="complete_anchor_set_batched",
            decision="all_precise_anchors_persisted_atomically",
            label="all_precise_anchors_persisted_atomically",
            writes=(
                "evidence.anchor",
                "evidence.modality",
                "evidence.freshness",
                "evidence.atomic_batch_identity",
            ),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AtomicEvidenceBatch"),
            reason=(
                "all qualified precise anchors remain individually addressable "
                "but are committed in one bounded transaction; identical retries "
                "are no-op and conflicting content-addressed ids block"
            ),
        ),
        CaseRule(
            case_id="large_anchor_set_referenced_by_bounded_pointer",
            decision="bounded_anchor_set_pointer_verified",
            label="bounded_anchor_set_pointer_verified",
            writes=(
                "evidence.anchor_set_pointer",
                "evidence.anchor_set_source_version",
                "evidence.anchor_set_count",
                "evidence.anchor_set_digest",
            ),
            side_effects=("evidence_registry_write",),
            emitted_tokens=(
                "BoundedAnchorSetPointer",
                "AnchorSetPointerVerified",
            ),
            reason=(
                "C3 retains every individually addressable anchor while "
                "downstream owners receive only the exact SourceVersion, "
                "anchor count, and canonical set digest; bounded pages remain "
                "resolvable without copying an unbounded id list"
            ),
        ),
        CaseRule(
            case_id="folder_neighborhood_context_only",
            decision="context_registered_not_proof",
            label="context_registered_not_proof",
            writes=("evidence.source_neighborhood_context",),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("SourceNeighborhoodContext", "EvidenceGap"),
            reason=(
                "folder proximity is retained as bounded synthesis context but "
                "cannot alone prove content, one Matter, an Event, person "
                "identity, or causation"
            ),
        ),
        CaseRule(
            case_id="exact_field_anchor",
            decision="anchored_assertion_candidate",
            label="anchored_assertion_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate"),
            reason="exact current field anchor supports a bounded assertion candidate",
        ),
        CaseRule(
            case_id="exact_image_region",
            decision="anchored_multimodal_candidate",
            label="anchored_multimodal_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate"),
            reason="exact page or image region supports a bounded candidate",
        ),
        CaseRule(
            case_id="exact_document_page_passage",
            decision="anchored_document_candidate",
            label="anchored_document_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate"),
            reason="current document page and passage coordinates support a bounded candidate",
        ),
        CaseRule(
            case_id="exact_sheet_cell_range",
            decision="anchored_spreadsheet_candidate",
            label="anchored_spreadsheet_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate"),
            reason="current sheet and cell-range coordinates support a bounded candidate",
        ),
        CaseRule(
            case_id="exact_mail_attachment_anchor",
            decision="anchored_mail_candidate",
            label="anchored_mail_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate"),
            reason="current message/thread/attachment identity and range support a bounded candidate",
        ),
        CaseRule(
            case_id="exact_gmail_body_continuation_anchor",
            decision="anchored_gmail_body_candidate",
            label="anchored_gmail_body_candidate",
            writes=(
                "evidence.anchor",
                "evidence.modality",
                "evidence.freshness",
                "evidence.atomic_batch_identity",
            ),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AtomicEvidenceBatch"),
            reason=(
                "the available non-empty body is extracted without model use "
                "and every admitted line range is bound to the exact current "
                "Gmail SourceVersion in one content-addressed evidence batch"
            ),
        ),
        CaseRule(
            case_id="gmail_no_text_body_has_no_evidence",
            decision="gmail_no_text_evidence_not_applicable",
            label="gmail_no_text_evidence_not_applicable",
            writes=("evidence.gmail_no_text_disposition",),
            emitted_tokens=("GmailNoTextEvidenceNotApplicable",),
            reason=(
                "a proof-bound connector result with no textual MIME part "
                "terminates extraction and evidence as not_applicable while "
                "creating no empty or inferred EvidenceAnchor"
            ),
        ),
        CaseRule(
            case_id="exact_safe_gallery_anchor",
            decision="gallery_anchor_eligible",
            label="gallery_anchor_eligible",
            writes=(
                "evidence.anchor",
                "evidence.freshness",
                "evidence.display_permission",
                "evidence.gallery_display_eligibility",
            ),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("VisualAnchor", "DisplayPermission"),
            reason=(
                "one exact current image, page, region, or screenshot derivative "
                "is display-safe for the C12 Images evidence gallery only and "
                "never gains generated-hero authority"
            ),
        ),
        CaseRule(
            case_id="gallery_anchor_denied_or_unrelated",
            decision="gallery_anchor_ineligible",
            label="gallery_anchor_ineligible",
            writes=("evidence.display_permission", "evidence.gallery_display_eligibility"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("DisplayPermission", "EvidenceGap"),
            reason=(
                "denied, unsafe, stale, or unrelated visual material remains "
                "ineligible for the Images evidence gallery"
            ),
        ),
        CaseRule(
            case_id="unsupported_or_unreadable_payload",
            decision="evidence_gap",
            label="unsupported_evidence_gap",
            writes=("evidence.gap",),
            emitted_tokens=("EvidenceGap",),
            reason="unsupported, encrypted, corrupt, or unavailable content remains a visible gap",
        ),
        CaseRule(
            case_id="title_or_filename_only",
            decision="evidence_gap",
            label="title_evidence_gap",
            writes=("evidence.gap",),
            emitted_tokens=("EvidenceGap",),
            reason="a title or filename cannot prove detailed completion or content claims",
        ),
        CaseRule(
            case_id="planned_statement",
            decision="anchored_planned_candidate",
            label="anchored_planned_candidate",
            writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("EvidenceAnchor", "AssertionCandidate", "ModalityPlanned"),
            reason="planned modality is retained and cannot license occurred",
        ),
        CaseRule(
            case_id="superseded_anchor",
            decision="stale_evidence",
            label="stale_evidence",
            writes=("evidence.freshness", "evidence.gap"),
            emitted_tokens=("StaleEvidence", "InvalidationRequest"),
            reason="source revision changed the anchored region",
        ),
    ),
    hazards=(
        HazardSpec(
            failure_id="H-C3-008-unbounded-anchor-ids-copied-downstream",
            protected_error_class="evidence_anchor_reference_amplification",
            description=(
                "coverage or analysis rows copy the complete anchor-id list "
                "instead of a bounded count-and-digest pointer"
            ),
            protected_harm=(
                "large sources duplicate unbounded JSON across downstream "
                "history and make reads, writes, and migrations nonterminating"
            ),
            case_id="large_anchor_set_referenced_by_bounded_pointer",
            broken_decision="full_anchor_id_list_embedded",
            broken_writes=("evidence.anchor_set_pointer",),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor",),
        ),
        HazardSpec(
            failure_id="H-C3-007-per-anchor-transaction-amplification",
            protected_error_class="evidence_transaction_amplification",
            description=(
                "one source opens and commits separate revision transactions for every anchor"
            ),
            protected_harm=(
                "large documents make first-run evidence persistence effectively nonterminating"
            ),
            case_id="complete_anchor_set_batched",
            broken_decision="anchors_persisted_one_transaction_each",
            broken_writes=("evidence.anchor",),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor",),
        ),
        HazardSpec(
            failure_id="H-C3-006-folder-proximity-promoted-to-proof",
            protected_error_class="spatial_context_evidence_overclaim",
            description="shared folder location is treated as proof of one Matter or Event",
            protected_harm="unrelated user files are merged into a false storyline",
            case_id="folder_neighborhood_context_only",
            broken_decision="anchored_assertion_candidate",
            broken_writes=("evidence.anchor", "evidence.modality"),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor", "AssertionCandidate"),
        ),
        HazardSpec(
            failure_id="H-C3-001-unanchored-claim-promoted",
            protected_error_class="unanchored_evidence_promotion",
            description="a detailed claim is promoted from a title or filename",
            protected_harm="canonical decisions appear supported without inspectable source evidence",
            case_id="title_or_filename_only",
            broken_decision="anchored_assertion_candidate",
            broken_writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor", "AssertionCandidate"),
        ),
        HazardSpec(
            failure_id="H-C3-009-gmail-body-receipt-without-anchor",
            protected_error_class="gmail_body_evidence_gap_hidden",
            description=(
                "a Gmail body continuation is marked current while no exact "
                "body line anchor was registered"
            ),
            protected_harm=(
                "coverage claims usable body evidence that C3 cannot inspect "
                "or bind to the current SourceVersion"
            ),
            case_id="exact_gmail_body_continuation_anchor",
            broken_decision="gmail_body_evidence_current",
            broken_writes=("evidence.atomic_batch_identity",),
            broken_tokens=("AtomicEvidenceBatch",),
        ),
        HazardSpec(
            failure_id="H-C3-010-gmail-no-text-fake-anchor",
            protected_error_class="gmail_no_text_fake_evidence",
            description=(
                "a no_text_body disposition creates an empty, metadata-derived, "
                "or invented EvidenceAnchor"
            ),
            protected_harm=(
                "downstream semantic owners receive fabricated textual support "
                "for a message whose raw MIME recovery proved no text"
            ),
            case_id="gmail_no_text_body_has_no_evidence",
            broken_decision="gmail_no_text_evidence_current",
            broken_writes=(
                "evidence.anchor",
                "evidence.gmail_no_text_disposition",
            ),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=(
                "EvidenceAnchor",
                "GmailNoTextEvidenceNotApplicable",
            ),
        ),
        HazardSpec(
            failure_id="H-C3-002-planned-promoted-to-occurred",
            protected_error_class="evidence_modality_collapse",
            description="planned evidence is emitted as observed occurrence",
            protected_harm="future intent is presented as a completed real-world event",
            case_id="planned_statement",
            broken_decision="anchored_occurred_assertion",
            broken_writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor", "AssertionCandidate", "ModalityObserved"),
        ),
        HazardSpec(
            failure_id="H-C3-003-stale-anchor-remains-current",
            protected_error_class="stale_evidence_reuse",
            description="a superseded anchor remains current evidence",
            protected_harm="downstream conclusions survive a source correction that removed their support",
            case_id="superseded_anchor",
            broken_decision="anchored_assertion_candidate",
            broken_writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor", "AssertionCandidate"),
        ),
        HazardSpec(
            failure_id="H-C3-005-denied-gallery-asset-promoted",
            protected_error_class="gallery_display_authority_escape",
            description="a denied, unsafe, stale, or unrelated visual is marked gallery-eligible",
            protected_harm="the Images gallery exposes unrelated or denied private content",
            case_id="gallery_anchor_denied_or_unrelated",
            broken_decision="gallery_anchor_eligible",
            broken_writes=(
                "evidence.anchor",
                "evidence.display_permission",
                "evidence.gallery_display_eligibility",
            ),
            broken_tokens=("VisualAnchor",),
        ),
        HazardSpec(
            failure_id="H-C3-004-unsupported-payload-fabricated",
            protected_error_class="unsupported_equivalence_fabrication",
            description="unsupported or unreadable content is reported as if extracted",
            protected_harm="canonical decisions appear grounded in content the system never read",
            case_id="unsupported_or_unreadable_payload",
            broken_decision="anchored_assertion_candidate",
            broken_writes=("evidence.anchor", "evidence.modality", "evidence.freshness"),
            broken_side_effects=("evidence_registry_write",),
            broken_tokens=("EvidenceAnchor", "AssertionCandidate"),
        ),
    ),
    risk_classes=("provenance", "evidence", "side_effect"),
    template_no_match_reason=(
        "The Phase A public/local template search found no precise-anchor and modality template; "
        "artifact_payload_real_surface is reserved for later real payload validation."
    ),
    blindspots=(
        "OCR, document, spreadsheet, mail, and image coordinates require real payload validation",
        "semantic truth of an anchored assertion remains outside FlowGuard structural authority",
    ),
    claim_boundary=(
        "This receipt can establish C3 finite anchor admission, modality, bounded "
        "anchor-set pointer identity through exact SourceVersion plus count and "
        "canonical digest, and staleness hazards. It does not establish OCR "
        "accuracy, factual truth, payload conformance, real pointer migration, or "
        "downstream claim validity."
    ),
)
