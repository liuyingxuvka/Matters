from pathlib import Path

from flowguard import review_hierarchical_mesh

from flowguard_models.harness import (
    CaseInput,
    DecisionOutput,
    ModelState,
    build_workflow,
)
from flowguard_models.models.s00_skill_runtime import CHILDREN, MODELS
from flowguard_models.run_skill_runtime_model import run_one
from flowguard_models.skill_runtime_mesh import build_partition, run_mesh


def test_s0_s5_declared_cases_and_zero_canonical_matter_writes():
    expected_cases = {
        "S0_matters_skill_runtime": {
            "bundled_only_internal_ready",
            "researchguard_pending",
            "legacy_three_guard_fallback_requested",
            "canonical_matter_write_requested",
        },
        "S1_skill_bundle_inventory": {
            "bundled_only_no_global_install",
            "author_control_residual_present",
        },
        "S2_skill_compatibility": {
            "exact_version_hash_match",
            "newer_local_compatible",
            "same_version_different_hash",
            "invalid_candidate",
            "incompatible_candidate",
            "prerelease_candidate",
            "researchguard_integration_incomplete",
            "researchguard_integration_current",
        },
        "S3_active_skill_resolution": {
            "exact_match_candidates",
            "newer_compatible_local_overlay",
            "bundled_newer_unmanaged_local",
            "bundled_newer_matters_managed",
            "active_view_input_changed",
            "legacy_three_guard_candidate",
        },
        "S4_matters_managed_skill_sync": {
            "bundled_only_no_global_install",
            "bundled_newer_unmanaged_local",
            "bundled_newer_matters_managed",
        },
        "S5_skill_validation_rollback": {
            "post_activation_check_failed",
            "author_control_residual_detected",
            "researchguard_integration_pending",
            "researchguard_integration_current",
        },
    }
    assert set(MODELS) == {
        "S0_matters_skill_runtime",
        "S1_skill_bundle_inventory",
        "S2_skill_compatibility",
        "S3_active_skill_resolution",
        "S4_matters_managed_skill_sync",
        "S5_skill_validation_rollback",
    }
    for model_id, spec in MODELS.items():
        rule_ids = {rule.case_id for rule in spec.rules}
        assert expected_cases[model_id] <= rule_ids
        assert all(field.startswith("skill_runtime.") for field in spec.owned_write_fields)
        assert all(
            set(rule.writes) <= set(spec.owned_write_fields)
            for rule in spec.rules
        )


def test_each_skill_runtime_owner_is_an_input_state_set_relation():
    for spec in MODELS.values():
        workflow = build_workflow(spec)
        block = workflow.blocks[0]
        rule = spec.rules[0]
        results = tuple(
            block.apply(
                CaseInput(spec.model_id, rule.case_id, rule.key()),
                ModelState(),
            )
        )
        assert block.accepted_input_type is CaseInput
        assert len(results) == 1
        assert isinstance(results[0].output, DecisionOutput)
        assert isinstance(results[0].new_state, ModelState)


def test_tm20_real_flowguard_owners_known_bad_and_mesh(tmp_path):
    receipt_root = tmp_path / "skill-runtime-models"
    receipts = {
        spec.model_id: run_one(spec, receipt_root=receipt_root)
        for spec in MODELS.values()
    }
    for model_id, receipt in receipts.items():
        assert receipt["model_id"] == model_id
        assert receipt["pass_for_skill_runtime"], receipt
        assert {"abstract_green", "hazard_green"} <= set(receipt["evidence_tiers"])
        assert receipt["contract_exhaustion"]["report"]["ok"]
        assert all(
            proof["observed_status"] == "failed"
            for proof in receipt["known_bad_proofs"]
        )
        assert str(Path.home()) not in str(receipt)

    mesh = run_mesh(receipt_root=receipt_root)
    assert mesh["status"] == "mesh_green", mesh["native_report"]
    assert mesh["parent_model_id"] == "S0_matters_skill_runtime"
    assert set(mesh["child_evidence_ids"]) == {
        spec.model_id for spec in CHILDREN
    }

    partition = build_partition(receipts)
    native = review_hierarchical_mesh(partition, model_count=len(CHILDREN))
    assert native.ok, native.to_dict()
