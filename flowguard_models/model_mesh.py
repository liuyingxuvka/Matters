"""Current M0/C1-C12 ModelMesh declaration and native review runner.

The project-level reattachment projection preserves the fields required by the
Matters blueprint.  The actual hierarchy, closure, ownership, freshness, and
reattachment decisions are delegated to FlowGuard's native hierarchy objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping

from flowguard import (
    ChildModelEvidence,
    ChildProofContract,
    ChildReattachmentContract,
    ChildReattachmentProof,
    HierarchyCoverageItem,
    HierarchyPartitionMap,
    LayeredBoundaryProofPlan,
    MeshClosureJoin,
    MeshClosureModel,
    MeshClosureTerminal,
    MeshClosureTransition,
    ModelTargetSplitDerivation,
    ParentCoverageItem,
    ProofArtifactRef,
    review_hierarchical_mesh,
    review_layered_boundary_proof,
)

from flowguard_models.run_model import MODELS


PARENT_ID = "M0_matters_end_to_end_authority"
CHILD_IDS = (
    "C1_authorization_coverage",
    "C2_source_registry",
    "C3_evidence_qualification",
    "C4_person_entity_resolution",
    "C5_event_temporal_trace",
    "C6_matter_formation_admission",
    "C7_lifecycle_board_state",
    "C8_open_loop_waiting_blocking",
    "C9_completion_cancellation_reopen",
    "C10_correction_revocation",
    "C11_guard_artifact_prediction",
    "C12_projection_bilingual_ui",
)


def _q(model_id: str, token: str) -> str:
    return f"{model_id}:{token}"


def _outputs(model_id: str) -> tuple[str, ...]:
    return tuple(_q(model_id, token) for token in MODELS[model_id].completion_evidence)


ACCEPTED_INPUTS: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: ("M0:AuthorizedSourceUniverseRequest",),
    CHILD_IDS[1]: (
        _q(CHILD_IDS[0], "CandidateScopeFrozen"),
        _q(CHILD_IDS[0], "Tracked"),
    ),
    CHILD_IDS[2]: (
        _q(CHILD_IDS[1], "SourceVersion"),
        _q(CHILD_IDS[1], "VisualDerivative"),
        _q(CHILD_IDS[10], "Proposal"),
    ),
    CHILD_IDS[3]: (
        _q(CHILD_IDS[2], "EvidenceAnchor"),
        _q(CHILD_IDS[2], "AssertionCandidate"),
        _q(CHILD_IDS[10], "BilingualFinding"),
    ),
    CHILD_IDS[4]: (
        _q(CHILD_IDS[2], "EvidenceAnchor"),
        _q(CHILD_IDS[2], "AssertionCandidate"),
        _q(CHILD_IDS[10], "Finding"),
    ),
    CHILD_IDS[5]: (
        _q(CHILD_IDS[3], "PersonCandidate"),
        _q(CHILD_IDS[3], "IdentityAssertion"),
        _q(CHILD_IDS[3], "MatterRole"),
        _q(CHILD_IDS[4], "TypedEvent"),
        _q(CHILD_IDS[4], "TimelineCandidate"),
        _q(CHILD_IDS[10], "BilingualFinding"),
    ),
    CHILD_IDS[6]: (
        _q(CHILD_IDS[5], "AdmittedMatter"),
        _q(CHILD_IDS[4], "TypedEvent"),
        _q(CHILD_IDS[10], "BilingualFinding"),
    ),
    CHILD_IDS[7]: (
        _q(CHILD_IDS[5], "AdmittedMatter"),
        _q(CHILD_IDS[10], "BilingualFinding"),
    ),
    CHILD_IDS[8]: (
        _q(CHILD_IDS[6], "LifecycleState"),
        _q(CHILD_IDS[7], "OpenLoop"),
        _q(CHILD_IDS[7], "Waiting"),
        _q(CHILD_IDS[7], "PartialBlock"),
        _q(CHILD_IDS[7], "FullBlock"),
        _q(CHILD_IDS[10], "BilingualFinding"),
    ),
    CHILD_IDS[9]: ("M0:CorrectionOrRevocation",),
    CHILD_IDS[10]: (
        "M0:AgentOperationRequest",
        _q(CHILD_IDS[0], "CandidateScopeFrozen"),
        _q(CHILD_IDS[0], "TrackingDisposition"),
        _q(CHILD_IDS[1], "SourceVersion"),
        _q(CHILD_IDS[1], "ChangeSet"),
        _q(CHILD_IDS[1], "VisualDerivative"),
    ),
    CHILD_IDS[11]: (
        _q(CHILD_IDS[0], "TrackingDisposition"),
        _q(CHILD_IDS[0], "CoverageComplete"),
        _q(CHILD_IDS[0], "CoveragePartial"),
        _q(CHILD_IDS[1], "InventorySnapshot"),
        _q(CHILD_IDS[1], "ChangeSet"),
        _q(CHILD_IDS[1], "VisualDerivative"),
        _q(CHILD_IDS[2], "DisplayPermission"),
        _q(CHILD_IDS[5], "MatterSourceRelation"),
        _q(CHILD_IDS[6], "LifecycleState"),
        _q(CHILD_IDS[6], "BoardPlacement"),
        _q(CHILD_IDS[6], "StateRationale"),
        _q(CHILD_IDS[7], "OpenLoop"),
        _q(CHILD_IDS[7], "Waiting"),
        _q(CHILD_IDS[7], "PartialBlock"),
        _q(CHILD_IDS[7], "FullBlock"),
        _q(CHILD_IDS[7], "LoopClosed"),
        _q(CHILD_IDS[8], "Completed"),
        _q(CHILD_IDS[8], "Cancelled"),
        _q(CHILD_IDS[8], "Abandoned"),
        _q(CHILD_IDS[8], "Reopened"),
        _q(CHILD_IDS[8], "OutcomeConflict"),
        _q(CHILD_IDS[9], "RecomputeJoinCurrent"),
        _q(CHILD_IDS[9], "RecomputeBlocked"),
        _q(CHILD_IDS[10], "DepthAssessment"),
        _q(CHILD_IDS[10], "VisualRecommendation"),
        _q(CHILD_IDS[10], "OriginalOwnerDispatch"),
        _q(CHILD_IDS[10], "ResearchGuardPending"),
    ),
}

DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: (),
    CHILD_IDS[1]: (CHILD_IDS[0],),
    CHILD_IDS[2]: (CHILD_IDS[1], CHILD_IDS[10]),
    CHILD_IDS[3]: (CHILD_IDS[2],),
    CHILD_IDS[4]: (CHILD_IDS[2], CHILD_IDS[10]),
    CHILD_IDS[5]: (CHILD_IDS[3], CHILD_IDS[4]),
    CHILD_IDS[6]: (CHILD_IDS[4], CHILD_IDS[5], CHILD_IDS[10]),
    CHILD_IDS[7]: (CHILD_IDS[5],),
    CHILD_IDS[8]: (CHILD_IDS[6], CHILD_IDS[7]),
    CHILD_IDS[9]: (),
    CHILD_IDS[10]: (CHILD_IDS[0], CHILD_IDS[1]),
    CHILD_IDS[11]: (
        CHILD_IDS[0],
        CHILD_IDS[1],
        CHILD_IDS[6],
        CHILD_IDS[7],
        CHILD_IDS[8],
        CHILD_IDS[9],
        CHILD_IDS[10],
    ),
}

AFFECTED_SIBLINGS: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: (CHILD_IDS[1], CHILD_IDS[10], CHILD_IDS[11]),
    CHILD_IDS[1]: (CHILD_IDS[2], CHILD_IDS[10], CHILD_IDS[11]),
    CHILD_IDS[2]: (CHILD_IDS[3], CHILD_IDS[4]),
    CHILD_IDS[3]: (CHILD_IDS[5],),
    CHILD_IDS[4]: (CHILD_IDS[5], CHILD_IDS[6]),
    CHILD_IDS[5]: (CHILD_IDS[6], CHILD_IDS[7]),
    CHILD_IDS[6]: (CHILD_IDS[8], CHILD_IDS[11]),
    CHILD_IDS[7]: (CHILD_IDS[8], CHILD_IDS[11]),
    CHILD_IDS[8]: (CHILD_IDS[11],),
    CHILD_IDS[9]: CHILD_IDS[1:9] + (CHILD_IDS[11],),
    CHILD_IDS[10]: (CHILD_IDS[2], CHILD_IDS[4], CHILD_IDS[6], CHILD_IDS[11]),
    CHILD_IDS[11]: (),
}


@dataclass(frozen=True)
class MattersChildReattachment:
    """Blueprint-complete projection beside the native reattachment contract."""

    child_model_id: str
    child_fingerprint: str
    parent_partition_items: tuple[str, ...]
    accepted_input_tokens: tuple[str, ...]
    emitted_output_tokens: tuple[str, ...]
    state_owner_fields: tuple[str, ...]
    side_effect_owner_fields: tuple[str, ...]
    outgoing_guarantees: tuple[str, ...]
    child_evidence_id: str
    evidence_tier: str
    runtime_path_evidence_ids: tuple[str, ...]
    affected_sibling_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "child_model_id": self.child_model_id,
            "child_fingerprint": self.child_fingerprint,
            "parent_partition_items": list(self.parent_partition_items),
            "accepted_input_tokens": list(self.accepted_input_tokens),
            "emitted_output_tokens": list(self.emitted_output_tokens),
            "state_owner_fields": list(self.state_owner_fields),
            "side_effect_owner_fields": list(self.side_effect_owner_fields),
            "outgoing_guarantees": list(self.outgoing_guarantees),
            "child_evidence_id": self.child_evidence_id,
            "evidence_tier": self.evidence_tier,
            "runtime_path_evidence_ids": list(self.runtime_path_evidence_ids),
            "affected_sibling_ids": list(self.affected_sibling_ids),
        }


def _load_current_model_receipt(receipt_root: Path, model_id: str) -> dict:
    path = receipt_root / f"{model_id}.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    spec = MODELS[model_id]
    if receipt.get("model_id") != model_id:
        raise ValueError(f"{path} names a foreign model")
    if receipt.get("model_fingerprint") != spec.fingerprint():
        raise ValueError(f"{path} is stale for the current model declaration")
    if not receipt.get("pass_for_g2"):
        raise ValueError(f"{path} did not pass the bounded G2 gate")
    if "hazard_green" not in receipt.get("evidence_tiers", ()):
        raise ValueError(f"{path} lacks hazard_green evidence")
    if any(
        proof.get("observed_status") != "failed"
        for proof in receipt.get("known_bad_proofs", ())
    ):
        raise ValueError(f"{path} has an uncaught known-bad case")
    return receipt


def _coverage_items() -> tuple[HierarchyCoverageItem, ...]:
    items: list[HierarchyCoverageItem] = []
    for model_id in (PARENT_ID,) + CHILD_IDS:
        spec = MODELS[model_id]
        ownership = "parent" if model_id == PARENT_ID else "child"
        function_id = f"function:{model_id}:finite_transition"
        items.append(
            HierarchyCoverageItem(
                function_id,
                item_type="function",
                owner_model_id=model_id,
                ownership=ownership,
                description=f"{model_id} finite Input x State relation",
            )
        )
        for field in spec.owned_write_fields:
            items.append(
                HierarchyCoverageItem(
                    f"state:{model_id}:{field}",
                    item_type="state",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"unique writer for {field}",
                )
            )
        for effect in spec.side_effect_classes:
            items.append(
                HierarchyCoverageItem(
                    f"side_effect:{model_id}:{effect}",
                    item_type="side_effect",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"unique side-effect owner for {effect}",
                )
            )
        for invariant in (
            "declared_transition_contract",
            "owned_writes_only",
            "side_effect_at_most_once",
            "canonical_write_at_most_once",
        ):
            items.append(
                HierarchyCoverageItem(
                    f"invariant:{model_id}:{invariant}",
                    item_type="invariant",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"{model_id} owns {invariant}",
                )
            )
    return tuple(items)


def _child_evidence(
    receipts: Mapping[str, dict],
) -> tuple[ChildModelEvidence, ...]:
    result: list[ChildModelEvidence] = []
    for model_id in CHILD_IDS:
        spec = MODELS[model_id]
        receipt = receipts[model_id]
        evidence_ids = [receipt["evidence_id"]]
        evidence_ids.extend(
            proof["evidence_id"] for proof in receipt["known_bad_proofs"]
        )
        result.append(
            ChildModelEvidence(
                model_id=model_id,
                evidence_id=receipt["evidence_id"],
                risk_boundary=spec.modeled_boundary,
                inputs_accepted=ACCEPTED_INPUTS[model_id],
                outputs_emitted=_outputs(model_id),
                state_owned=spec.owned_write_fields,
                side_effects_owned=spec.side_effect_classes,
                functional_areas=(f"matters:{model_id}",),
                contracts_in=tuple(
                    f"input_contract:{model_id}:{token}"
                    for token in ACCEPTED_INPUTS[model_id]
                ),
                contracts_out=(f"guarantee:{model_id}:finite_relation",),
                depends_on=DEPENDENCIES[model_id],
                evidence_tier="hazard_green",
                evidence_current=True,
                # These fields describe checks required for this G3 bounded
                # mesh claim.  The receipt separately preserves later runtime
                # layers as explicitly non-supporting/not-run.
                skipped_checks=(),
                not_run_checks=(),
                estimated_state_count=len(spec.rules) + 1,
                observed_state_count=len(spec.rules) + 1,
                structurally_cohesive=True,
                functions_owned=(f"{model_id}:finite_transition",),
                invariants_owned=tuple(
                    f"{model_id}:{name}"
                    for name in (
                        "declared_transition_contract",
                        "owned_writes_only",
                        "side_effect_at_most_once",
                        "canonical_write_at_most_once",
                    )
                ),
                risk_classes=tuple(
                    f"{model_id}:{risk_class}" for risk_class in spec.risk_classes
                ),
                validation_evidence=tuple(evidence_ids),
                runtime_path_evidence_ids=(),
            )
        )
    return tuple(result)


def _native_reattachment_contracts(
    child_evidence: Iterable[ChildModelEvidence],
) -> tuple[ChildReattachmentContract, ...]:
    return tuple(
        ChildReattachmentContract(
            child_model_id=child.model_id,
            consumed_evidence_id=child.evidence_id,
            consumed_runtime_path_evidence_ids=child.runtime_path_evidence_ids,
            expected_inputs=child.inputs_accepted,
            expected_outputs=child.outputs_emitted,
            expected_state_owned=child.state_owned,
            expected_side_effects_owned=child.side_effects_owned,
            expected_contracts_out=child.contracts_out,
            allow_extra_inputs=False,
            allow_extra_outputs=False,
            rationale=(
                "M0 consumes this exact current hazard-green child boundary; "
                "fingerprint and affected siblings are retained in the "
                "blueprint-complete project projection."
            ),
        )
        for child in child_evidence
    )


def _execution_transition(model_id: str) -> MeshClosureTransition:
    return MeshClosureTransition(
        transition_id=f"execute:{model_id}",
        consumes=ACCEPTED_INPUTS[model_id],
        emits=_outputs(model_id),
        consumer_model_id=model_id,
        rationale=f"execute the declared finite boundary for {model_id}",
    )


def _closure_model() -> MeshClosureModel:
    transitions: list[MeshClosureTransition] = [
        _execution_transition(model_id) for model_id in CHILD_IDS
    ]
    all_child_outputs = tuple(
        token for model_id in CHILD_IDS for token in _outputs(model_id)
    )
    transitions.append(
        MeshClosureTransition(
            transition_id="reattach:all_current_children",
            consumes=all_child_outputs,
            emits=tuple(f"Attached:{model_id}" for model_id in CHILD_IDS)
            + (
                "AutonomousDispositionClosed",
                "BlockedClosed",
                "NoDeltaClosed",
                "RecomputeClosed",
            ),
            consumer_model_id=PARENT_ID,
            rationale=(
                "M0 atomically consumes the complete qualified output snapshot "
                "and all exact current child evidence identities. Auto-applied, "
                "no-finding, not-applicable, blocked, no-delta, and recompute tokens receive explicit "
                "parent dispositions in the same immutable snapshot."
            ),
        )
    )

    return MeshClosureModel(
        parent_model_id=PARENT_ID,
        root_entries=(
            "M0:AuthorizedSourceUniverseRequest",
            "M0:CorrectionOrRevocation",
            "M0:AgentOperationRequest",
        ),
        transitions=tuple(transitions),
        joins=(
            MeshClosureJoin(
                join_id="join:all_current_children",
                required_inputs=tuple(
                    f"Attached:{model_id}" for model_id in CHILD_IDS
                )
                + (
                    "AutonomousDispositionClosed",
                    "BlockedClosed",
                    "NoDeltaClosed",
                    "RecomputeClosed",
                ),
                emits=("M0:MeshReady",),
                rationale=(
                    "all twelve current child boundaries and the autonomous, "
                    "blocked, no-delta, and recompute dispositions must close"
                ),
            ),
        ),
        terminals=(
            MeshClosureTerminal(
                terminal_id="terminal:auto_applied",
                consumes=("M0:MeshReady",),
                terminal_kind="normal_exit",
                rationale="all current child outputs are consumed with no pending token",
            ),
            MeshClosureTerminal(
                terminal_id="terminal:no_finding_or_not_applicable",
                consumes=("M0:MeshReady",),
                terminal_kind="normal_exit",
                rationale="no-finding and not-applicable are explicit autonomous terminals",
            ),
            MeshClosureTerminal(
                terminal_id="terminal:no_delta",
                consumes=("M0:MeshReady",),
                terminal_kind="normal_exit",
                rationale="idempotent repeat closes without a new canonical write",
            ),
            MeshClosureTerminal(
                terminal_id="terminal:blocked",
                consumes=("M0:MeshReady",),
                terminal_kind="failure_exit",
                rationale="blocked work remains a visible terminal disposition",
            ),
        ),
        required_outputs=("M0:MeshReady",),
        require_normal_exit=True,
        rationale=(
            "Executable token-closure meta-model for M0 over all current C1-C12 "
            "boundaries; qualified output tokens prevent sibling producer aliasing."
        ),
    )


def _project_reattachments(
    children: Iterable[ChildModelEvidence],
    coverage_items: Iterable[HierarchyCoverageItem],
) -> tuple[MattersChildReattachment, ...]:
    coverage_by_owner: dict[str, list[str]] = {}
    for item in coverage_items:
        coverage_by_owner.setdefault(item.owner_model_id, []).append(item.item_id)
    return tuple(
        MattersChildReattachment(
            child_model_id=child.model_id,
            child_fingerprint=MODELS[child.model_id].fingerprint(),
            parent_partition_items=tuple(
                sorted(coverage_by_owner.get(child.model_id, ()))
            ),
            accepted_input_tokens=child.inputs_accepted,
            emitted_output_tokens=child.outputs_emitted,
            state_owner_fields=child.state_owned,
            side_effect_owner_fields=child.side_effects_owned,
            outgoing_guarantees=child.contracts_out,
            child_evidence_id=child.evidence_id,
            evidence_tier=child.evidence_tier,
            runtime_path_evidence_ids=child.runtime_path_evidence_ids,
            affected_sibling_ids=AFFECTED_SIBLINGS[child.model_id],
        )
        for child in children
    )


def _consumer_bindings(
    closure: MeshClosureModel,
) -> Mapping[str, tuple[str, ...]]:
    bindings: dict[str, set[str]] = {}
    for transition in closure.transitions:
        for token in transition.consumes:
            if token.startswith("C") and ":" in token:
                bindings.setdefault(token, set()).add(
                    transition.consumer_model_id or PARENT_ID
                )
    for join in closure.joins:
        for token in join.required_inputs:
            if token.startswith("C") and ":" in token:
                bindings.setdefault(token, set()).add(PARENT_ID)
    for terminal in closure.terminals:
        for token in terminal.consumes:
            if token.startswith("C") and ":" in token:
                bindings.setdefault(token, set()).add(
                    f"terminal:{terminal.terminal_id}"
                )
    return {
        token: tuple(sorted(consumers))
        for token, consumers in sorted(bindings.items())
    }


def _layered_boundary_report(
    *,
    receipt_root: Path,
    children: tuple[ChildModelEvidence, ...],
    coverage_items: tuple[HierarchyCoverageItem, ...],
):
    parent_items = tuple(
        ParentCoverageItem(
            item_id=item.item_id,
            item_type=item.item_type,
            owner_model_id=item.owner_model_id,
            owner_kind=item.ownership,
            description=item.description,
            allowed_shared_with=item.allowed_shared_with,
            rationale="Derived from the current checked M0/C1-C12 partition.",
        )
        for item in coverage_items
    )
    responsibilities = {
        child.model_id: tuple(
            item.item_id
            for item in coverage_items
            if item.owner_model_id == child.model_id
        )
        for child in children
    }
    child_contracts: list[ChildProofContract] = []
    reattachment_proofs: list[ChildReattachmentProof] = []
    for child in children:
        receipt_path = receipt_root / f"{child.model_id}.json"
        receipt_bytes = receipt_path.read_bytes()
        receipt_hash = "sha256:" + sha256(receipt_bytes).hexdigest()
        covered = responsibilities[child.model_id]
        child_contracts.append(
            ChildProofContract(
                child_model_id=child.model_id,
                evidence_id=child.evidence_id,
                evidence_status="passed",
                evidence_current=True,
                proof_artifact=ProofArtifactRef(
                    artifact_id=f"artifact:{child.model_id}:g2",
                    producer_route="model_first_function_flow",
                    command=(
                        f"python -m flowguard_models.run_model {child.model_id}"
                    ),
                    result_path=receipt_path.as_posix(),
                    result_status="passed",
                    exit_code=0,
                    artifact_fingerprints={
                        receipt_path.as_posix(): receipt_hash,
                    },
                    covered_obligation_ids=covered,
                    assertion_scope="external_contract",
                    current=True,
                    route_evidence_current=True,
                ),
                responsibilities=covered,
                functions_owned=child.functions_owned,
                inputs_accepted=child.inputs_accepted,
                outputs_emitted=child.outputs_emitted,
                state_owned=child.state_owned,
                side_effects_owned=child.side_effects_owned,
                invariants_owned=child.invariants_owned,
                risk_classes=child.risk_classes,
                contracts_out=child.contracts_out,
                is_leaf=False,
                rationale=(
                    "G3 treats this as a checked child model boundary; the "
                    "production leaf boundary matrix is intentionally deferred "
                    "to G4-G7 and cannot support this claim."
                ),
            )
        )
        reattachment_proofs.append(
            ChildReattachmentProof(
                child_model_id=child.model_id,
                consumed_evidence_id=child.evidence_id,
                expected_inputs=child.inputs_accepted,
                expected_outputs=child.outputs_emitted,
                expected_state_owned=child.state_owned,
                expected_side_effects_owned=child.side_effects_owned,
                expected_contracts_out=child.contracts_out,
                allow_extra_inputs=False,
                allow_extra_outputs=False,
                allow_extra_state_owned=False,
                allow_extra_side_effects=False,
                allow_extra_contracts_out=False,
                rationale="M0 consumes the exact current bounded child contract.",
            )
        )
    plan = LayeredBoundaryProofPlan(
        proof_id="LBP0_matters_parent_child_models",
        parent_model_id=PARENT_ID,
        parent_items=parent_items,
        child_contracts=tuple(child_contracts),
        reattachment_proofs=tuple(reattachment_proofs),
        leaf_matrices=(),
        require_leaf_matrix_for_leaf_children=True,
        require_proof_artifacts=True,
        allow_scoped_leaf_exemptions=False,
        claim_scope="parent_child_model_boundary",
        rationale=(
            "G3 proves parent coverage, sibling disjointness, current child "
            "evidence, and exact reattachment. No production child is yet "
            "classified as a leaf, so G6 leaf matrices remain not_run."
        ),
    )
    return plan, review_layered_boundary_proof(plan)


def run_mesh(
    *,
    receipt_root: Path = Path(".flowguard/evidence/models"),
) -> dict:
    receipts = {
        model_id: _load_current_model_receipt(receipt_root, model_id)
        for model_id in (PARENT_ID,) + CHILD_IDS
    }
    parent_receipt = receipts[PARENT_ID]
    children = _child_evidence(receipts)
    coverage_items = _coverage_items()
    closure = _closure_model()
    native_contracts = _native_reattachment_contracts(children)
    project_contracts = _project_reattachments(children, coverage_items)
    consumer_bindings = _consumer_bindings(closure)
    declared_outputs = {
        token for model_id in CHILD_IDS for token in _outputs(model_id)
    }
    unbound_outputs = tuple(sorted(declared_outputs - set(consumer_bindings)))

    partition = HierarchyPartitionMap(
        parent_model_id=PARENT_ID,
        coverage_items=coverage_items,
        child_models=children,
        target_split_derivation=ModelTargetSplitDerivation(
            source_model_id=PARENT_ID,
            target_child_model_ids=CHILD_IDS,
            covered_partition_item_ids=tuple(
                item.item_id for item in coverage_items
            ),
            state_owner_fields=tuple(
                field
                for model_id in CHILD_IDS
                for field in MODELS[model_id].owned_write_fields
            ),
            side_effect_owner_fields=tuple(
                effect
                for model_id in CHILD_IDS
                for effect in MODELS[model_id].side_effect_classes
            ),
            source_model_path=(
                "flowguard_models/models/m00_end_to_end_authority.py"
            ),
            rationale=(
                "M0 delegates canonical ownership by unique state and "
                "side-effect writer to the twelve behavior children."
            ),
            derived_from_flowguard_model=True,
        ),
        reattachment_contracts=native_contracts,
        required_evidence_tier="hazard_green",
        allowed_shared_areas=(),
        boundary_changes=(),
        closure_model=closure,
    )
    report = review_hierarchical_mesh(partition, model_count=len(CHILD_IDS))
    layered_plan, layered_report = _layered_boundary_report(
        receipt_root=receipt_root,
        children=children,
        coverage_items=coverage_items,
    )
    parent_current = (
        parent_receipt["model_fingerprint"] == MODELS[PARENT_ID].fingerprint()
        and parent_receipt.get("pass_for_g2") is True
        and "hazard_green" in parent_receipt.get("evidence_tiers", ())
    )
    status = (
        "mesh_green"
        if (
            report.ok
            and layered_report.ok
            and parent_current
            and not unbound_outputs
        )
        else "blocked"
    )
    fingerprint_input = {
        "parent_fingerprint": MODELS[PARENT_ID].fingerprint(),
        "child_fingerprints": {
            model_id: MODELS[model_id].fingerprint() for model_id in CHILD_IDS
        },
        "child_evidence_ids": {
            model_id: receipts[model_id]["evidence_id"] for model_id in CHILD_IDS
        },
        "partition": partition.to_dict(),
        "consumer_bindings": consumer_bindings,
    }
    mesh_fingerprint = "sha256:" + sha256(
        json.dumps(
            fingerprint_input,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "artifact_type": "matters.model-mesh-receipt.v1",
        "mesh_id": "MM0_matters_parent_child_mesh",
        "mesh_fingerprint": mesh_fingerprint,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "evidence_tier": "mesh_green" if status == "mesh_green" else "candidate_only",
        "parent_model_id": PARENT_ID,
        "parent_model_fingerprint": MODELS[PARENT_ID].fingerprint(),
        "parent_evidence_id": parent_receipt["evidence_id"],
        "parent_current": parent_current,
        "required_child_evidence_tier": "hazard_green",
        "native_report": report.to_dict(),
        "layered_boundary_plan": layered_plan.to_dict(),
        "layered_boundary_report": layered_report.to_dict(),
        "partition": partition.to_dict(),
        "child_reattachment_contracts": [
            contract.to_dict() for contract in project_contracts
        ],
        "consumer_bindings": {
            token: list(consumers)
            for token, consumers in consumer_bindings.items()
        },
        "unbound_outputs": list(unbound_outputs),
        "claim_boundary": (
            "mesh_green proves the bounded M0/C1-C12 abstract-hazard partition, "
            "unique child writer declarations, current receipt reattachment, "
            "qualified output consumption, reachable join, and leak-free "
            "terminal dispositions. Production code, runtime paths, provider "
            "access, live currentness, and conformance remain not_run and do "
            "not support this G3 claim."
        ),
        "non_supporting_unrun_layers": (
            "code_contract",
            "production_implementation",
            "runtime_path",
            "conformance_replay",
            "live_provider",
            "test_mesh",
        ),
    }
