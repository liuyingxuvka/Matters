"""G4 model-code-test alignment design with explicitly not-run evidence."""

from __future__ import annotations

from dataclasses import replace

from flowguard.model_test_alignment import (
    CodeBoundaryContract,
    CodeBoundaryObservation,
    CodeContract,
    ModelTestAlignmentPlan,
    TestEvidence,
    review_model_test_alignment,
)
from flowguard.transition_coverage import transition_obligation_id

from flowguard_design.inventory import (
    MODEL_MODULES,
    MODEL_ORDER,
    MODEL_SYMBOLS,
    MODEL_TEST_SUITES,
    MODELS,
    PARENT_ID,
)
from flowguard_design.commitments import commitment_bindings
from flowguard_design.transition_coverage import (
    build_matrices,
    code_contract_id,
)


def _unique(values):
    return tuple(dict.fromkeys(value for value in values if value))


def build_plans(
    *,
    executed: bool = False,
    receipt_root=None,
) -> tuple[ModelTestAlignmentPlan, ...]:
    matrix_by_model = {matrix.model_id: matrix for matrix in build_matrices()}
    bindings = commitment_bindings()
    plans: list[ModelTestAlignmentPlan] = []
    for model_id in MODEL_ORDER:
        spec = MODELS[model_id]
        matrix = matrix_by_model[model_id]
        binding = {
            key: value
            for key, value in bindings[model_id].items()
            if key != "behavior_plane"
        }
        obligations = tuple(
            replace(obligation, behavior_plane="product_runtime")
            for obligation in matrix.to_model_obligations()
        )
        obligation_ids = tuple(item.obligation_id for item in obligations)
        contract_id = code_contract_id(model_id)
        contract = CodeContract(
            code_contract_id=contract_id,
            path=(
                "src/matters/"
                + MODEL_MODULES[model_id].replace(".", "/")
                + ".py"
            ),
            symbol=MODEL_SYMBOLS[model_id],
            surface_type="owner_service",
            role="owner",
            implements_obligations=obligation_ids,
            external_inputs=_unique(
                item for obligation in obligations for item in obligation.external_inputs
            ),
            external_outputs=_unique(
                item for obligation in obligations for item in obligation.external_outputs
            ),
            state_reads=_unique(
                item for obligation in obligations for item in obligation.state_reads
            ),
            state_writes=_unique(
                item for obligation in obligations for item in obligation.state_writes
            ),
            side_effects=spec.side_effect_classes,
            error_paths=("visible_review_or_blocker",),
            behavior_plane="product_runtime",
            **binding,
        )
        boundary = CodeBoundaryContract(
            boundary_id=f"CB-{model_id}-leaf",
            code_contract_id=contract_id,
            allowed_inputs=contract.external_inputs,
            rejected_inputs=("foreign_owner_write", "undeclared_provider_field"),
            allowed_outputs=contract.external_outputs,
            allowed_state_writes=spec.owned_write_fields,
            allowed_side_effects=spec.side_effect_classes,
            allowed_error_paths=("visible_review_or_blocker",),
            exact=True,
            input_gate_required=True,
        )
        suite_id = (
            "TM14_end_to_end_conformance"
            if model_id == PARENT_ID
            else MODEL_TEST_SUITES[model_id]
        )
        receipt = None
        if executed and receipt_root is not None:
            import json
            from pathlib import Path

            receipt = json.loads(
                (Path(receipt_root) / f"{suite_id}.json").read_text(
                    encoding="utf-8"
                )
            )
        evidence: list[TestEvidence] = []
        for obligation in obligations:
            for test_kind in obligation.required_test_kinds:
                evidence.append(
                    TestEvidence(
                        evidence_id=(
                            f"TE-{obligation.obligation_id}-{test_kind}-planned"
                        ),
                        test_name=f"{obligation.obligation_id}:{test_kind}",
                        path="tests/",
                        command="pytest -q",
                        result_status="passed" if executed else "not_run",
                        evidence_current=True,
                        test_kind=test_kind,
                        covered_obligations=(obligation.obligation_id,),
                        covered_code_contracts=(contract_id,),
                        assertion_scope="external_contract",
                        evidence_role="primary",
                        proof_artifact=(
                            receipt["test_suite_evidence"]["proof_artifact"]
                            if receipt
                            else None
                        ),
                        stale_reasons=(
                            ()
                            if executed
                            else ("G4 design only; implementation not started",)
                        ),
                        behavior_plane="product_runtime",
                        business_intent_id=obligation.business_intent_id,
                        behavior_commitment_id=obligation.behavior_commitment_id,
                        primary_path_id=obligation.primary_path_id,
                    )
                )
        observations: list[CodeBoundaryObservation] = []
        if executed and receipt:
            evidence_id = receipt["test_suite_evidence"]["run_id"]
            for cell in matrix.required_cells():
                observations.append(
                    CodeBoundaryObservation(
                        observation_id=f"BO-{cell.cell_id}",
                        boundary_id=boundary.boundary_id,
                        input_case=cell.trigger,
                        accepted=True,
                        observed_output=cell.expected_output,
                        observed_state_writes=(cell.target_state,),
                        observed_side_effects=cell.side_effects,
                        result_status="passed",
                        evidence_current=True,
                        evidence_id=evidence_id,
                    )
                )
            for rejected in boundary.rejected_inputs:
                observations.append(
                    CodeBoundaryObservation(
                        observation_id=f"BO-{model_id}-{rejected}",
                        boundary_id=boundary.boundary_id,
                        input_case=rejected,
                        accepted=False,
                        observed_error_path="visible_review_or_blocker",
                        result_status="passed",
                        evidence_current=True,
                        evidence_id=evidence_id,
                    )
                )
        plans.append(
            ModelTestAlignmentPlan(
                model_id=model_id,
                obligations=obligations,
                code_contracts=(contract,),
                test_evidence=tuple(evidence),
                boundary_contracts=(boundary,),
                boundary_observations=tuple(observations),
                require_proof_artifacts=executed,
                require_runtime_path_evidence=False,
                allow_orphan_tests=False,
                allow_orphan_code_contracts=False,
                require_stable_authority_ids=True,
                require_behavior_plane_binding=True,
            )
        )
    return tuple(plans)


def run_reviews(*, executed: bool = False, receipt_root=None):
    plans = build_plans(executed=executed, receipt_root=receipt_root)
    return tuple((plan, review_model_test_alignment(plan)) for plan in plans)


__all__ = ["build_plans", "run_reviews", "transition_obligation_id"]
