"""C3 Evidence Qualification finite FlowGuard model declaration."""

from flowguard_models.harness import CaseRule, FiniteModelSpec, HazardSpec


SPEC = FiniteModelSpec(
    model_id="C3_evidence_qualification",
    title="C3 Evidence Qualification",
    modeled_boundary=(
        "precise line/character, page/passage, sheet/cell, message/thread/"
        "attachment, image/OCR-region and metadata anchors, modality, gaps, "
        "display safety, representative-visual eligibility, and source-version freshness"
    ),
    state_fields=(
        "evidence.anchor",
        "evidence.modality",
        "evidence.freshness",
        "evidence.gap",
        "evidence.display_permission",
        "evidence.visual_eligibility",
    ),
    owned_write_fields=(
        "evidence.anchor",
        "evidence.modality",
        "evidence.freshness",
        "evidence.gap",
        "evidence.display_permission",
        "evidence.visual_eligibility",
    ),
    side_effect_classes=("evidence_registry_write",),
    completion_evidence=(
        "EvidenceAnchor",
        "AssertionCandidate",
        "EvidenceGap",
        "StaleEvidence",
        "VisualAnchor",
        "DisplayPermission",
    ),
    rules=(
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
            case_id="exact_safe_visual_anchor",
            decision="visual_anchor_eligible",
            label="visual_anchor_eligible",
            writes=(
                "evidence.anchor",
                "evidence.freshness",
                "evidence.display_permission",
                "evidence.visual_eligibility",
            ),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("VisualAnchor", "DisplayPermission"),
            reason=(
                "one exact current image, page, region, or screenshot derivative "
                "is display-safe and eligible for C11 visual recommendation"
            ),
        ),
        CaseRule(
            case_id="visual_anchor_denied_or_unrelated",
            decision="visual_anchor_ineligible",
            label="visual_anchor_ineligible",
            writes=("evidence.display_permission", "evidence.visual_eligibility"),
            side_effects=("evidence_registry_write",),
            emitted_tokens=("DisplayPermission", "EvidenceGap"),
            reason=(
                "denied, unsafe, stale, or unrelated visual material remains "
                "ineligible and cannot be projected as representative evidence"
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
            failure_id="H-C3-005-denied-visual-promoted",
            protected_error_class="visual_display_authority_escape",
            description="a denied, unsafe, stale, or unrelated visual is marked eligible",
            protected_harm="a card image misrepresents the Matter or exposes private content",
            case_id="visual_anchor_denied_or_unrelated",
            broken_decision="visual_anchor_eligible",
            broken_writes=(
                "evidence.anchor",
                "evidence.display_permission",
                "evidence.visual_eligibility",
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
        "This receipt can establish C3 finite anchor admission, modality, and "
        "staleness hazards. It does not establish OCR accuracy, factual truth, "
        "payload conformance, or downstream claim validity."
    ),
)
