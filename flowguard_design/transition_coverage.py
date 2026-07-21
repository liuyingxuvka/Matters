"""Independent transition coverage inventories for product and operation planes."""

from __future__ import annotations

from flowguard.transition_coverage import (
    TransitionCoverageCell,
    TransitionCoverageMatrix,
)

from flowguard_design.commitments import commitment_bindings
from flowguard_design.inventory import (
    AGENT_OPERATION_MODELS,
    AGENT_OPERATION_ORDER,
    MODEL_CODE_CONTRACTS,
    MODEL_ORDER,
    MODELS,
    PARENT_ID,
)


PARENT_CODE_CONTRACT_ID = "CC-M0-orchestrator"
AGENT_OPERATION_CODE_CONTRACTS = {
    "A0_matters_source_analysis_operation": "CC-A0-agent-operation",
    "A1_matters_research_operation": "CC-A1-research-operation",
    "A2_matters_maintenance_orchestrator_operation": "CC-A2-maintenance-orchestration",
    "A3_matters_ai_gateway_operation": "CC-A3-ai-gateway",
}


def code_contract_id(model_id: str) -> str:
    if model_id in AGENT_OPERATION_CODE_CONTRACTS:
        return AGENT_OPERATION_CODE_CONTRACTS[model_id]
    return (
        PARENT_CODE_CONTRACT_ID
        if model_id == PARENT_ID
        else MODEL_CODE_CONTRACTS[model_id]
    )


def _plane_inventory():
    yield "product_runtime", MODEL_ORDER, MODELS
    yield "agent_operation", AGENT_OPERATION_ORDER, AGENT_OPERATION_MODELS


def build_matrices() -> tuple[TransitionCoverageMatrix, ...]:
    matrices: list[TransitionCoverageMatrix] = []
    for behavior_plane, model_order, models in _plane_inventory():
        bindings = commitment_bindings(behavior_plane)
        for model_id in model_order:
            spec = models[model_id]
            binding = {
                key: value
                for key, value in bindings[model_id].items()
                if key != "behavior_plane"
            }
            cells: list[TransitionCoverageCell] = []
            for rule in spec.rules:
                source_field = spec.state_fields[0]
                target_field = rule.writes[0] if rule.writes else source_field
                risk_class = (
                    "rejection"
                    if rule.decision.endswith(("rejected", "blocked"))
                    or "gap" in rule.decision
                    or "review" in rule.decision
                    else "normal"
                )
                cells.append(
                    TransitionCoverageCell(
                        cell_id=f"TC-{model_id}-{rule.case_id}",
                        source_state=source_field,
                        trigger=rule.case_id,
                        target_state=target_field,
                        expected_output=rule.decision,
                        function_block=f"{model_id}_finite_transition",
                        code_contract_id=code_contract_id(model_id),
                        risk_class=risk_class,
                        required_test_kinds=(
                            ("rejection", "side_effect")
                            if risk_class == "rejection"
                            else ("happy_path", "side_effect")
                        ),
                        side_effects=rule.side_effects,
                        rationale=rule.reason
                        or f"{rule.case_id} must reach {rule.decision}",
                        **binding,
                    )
                )
                cells.append(
                    TransitionCoverageCell(
                        cell_id=f"TC-{model_id}-{rule.case_id}-retry",
                        source_state=target_field,
                        trigger=f"repeat:{rule.case_id}",
                        target_state=target_field,
                        expected_output=rule.retry_decision,
                        function_block=f"{model_id}_finite_transition",
                        code_contract_id=code_contract_id(model_id),
                        risk_class="retry_or_rejection",
                        required_test_kinds=("retry", "side_effect"),
                        rationale=(
                            f"repeating logical input {rule.case_id} must be "
                            "idempotent and emit no canonical write"
                        ),
                        **binding,
                    )
                )
            matrices.append(
                TransitionCoverageMatrix(
                    matrix_id=f"TCM-{model_id}",
                    model_id=model_id,
                    source_route="model",
                    cells=tuple(cells),
                    rationale=(
                        "Independent finite inventory of every declared "
                        f"{behavior_plane} transition and its idempotent retry."
                    ),
                )
            )
    return tuple(matrices)


def required_cell_ids() -> tuple[str, ...]:
    return tuple(
        cell_id
        for matrix in build_matrices()
        for cell_id in matrix.required_cell_ids()
    )


__all__ = [
    "PARENT_CODE_CONTRACT_ID",
    "AGENT_OPERATION_CODE_CONTRACTS",
    "build_matrices",
    "code_contract_id",
    "required_cell_ids",
]
