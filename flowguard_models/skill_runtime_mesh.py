"""Native bounded ModelMesh for the auxiliary S0-S5 skill-runtime hierarchy."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

from flowguard import (
    ChildModelEvidence,
    ChildReattachmentContract,
    HierarchyCoverageItem,
    HierarchyPartitionMap,
    MeshClosureModel,
    MeshClosureTerminal,
    MeshClosureTransition,
    ModelTargetSplitDerivation,
    review_hierarchical_mesh,
)

from flowguard_models.models.s00_skill_runtime import CHILDREN, MODELS, S0
from flowguard_models.run_skill_runtime_model import DEFAULT_RECEIPT_ROOT


MESH_RECEIPT = Path(
    ".flowguard/evidence/skill_runtime/S0_skill_runtime_mesh.json"
)
PARENT_ID = S0.model_id
CHILD_IDS = tuple(spec.model_id for spec in CHILDREN)
INPUTS: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: ("S0:SkillRuntimeRequest",),
    CHILD_IDS[1]: ("S1:InventoryDisposition",),
    CHILD_IDS[2]: ("S2:CompatibilityDisposition",),
    CHILD_IDS[3]: ("S3:ActiveViewDisposition",),
    CHILD_IDS[4]: ("S4:ManagedProjectionDisposition",),
}
OUTPUTS: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: ("S1:InventoryDisposition",),
    CHILD_IDS[1]: ("S2:CompatibilityDisposition",),
    CHILD_IDS[2]: ("S3:ActiveViewDisposition",),
    CHILD_IDS[3]: ("S4:ManagedProjectionDisposition",),
    CHILD_IDS[4]: ("S5:ActivationDisposition",),
}
DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    CHILD_IDS[0]: (),
    CHILD_IDS[1]: (CHILD_IDS[0],),
    CHILD_IDS[2]: (CHILD_IDS[1],),
    CHILD_IDS[3]: (CHILD_IDS[2],),
    CHILD_IDS[4]: (CHILD_IDS[3],),
}


def _load_receipts(receipt_root: Path) -> dict[str, dict]:
    receipts: dict[str, dict] = {}
    for model_id, spec in MODELS.items():
        path = receipt_root / f"{model_id}.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("model_id") != model_id:
            raise ValueError(f"{model_id} receipt names a foreign model")
        if receipt.get("model_fingerprint") != spec.fingerprint():
            raise ValueError(f"{model_id} receipt is stale")
        if receipt.get("pass_for_skill_runtime") is not True:
            raise ValueError(f"{model_id} receipt did not pass")
        if "hazard_green" not in receipt.get("evidence_tiers", ()):
            raise ValueError(f"{model_id} receipt lacks hazard_green evidence")
        receipts[model_id] = receipt
    return receipts


def _coverage_items() -> tuple[HierarchyCoverageItem, ...]:
    rows: list[HierarchyCoverageItem] = []
    for model_id, spec in MODELS.items():
        ownership = "parent" if model_id == PARENT_ID else "child"
        rows.append(
            HierarchyCoverageItem(
                f"function:{model_id}:finite_transition",
                item_type="function",
                owner_model_id=model_id,
                ownership=ownership,
                description=f"{model_id} Input x State finite relation",
            )
        )
        for field in spec.owned_write_fields:
            rows.append(
                HierarchyCoverageItem(
                    f"state:{model_id}:{field}",
                    item_type="state",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"unique skill-runtime writer for {field}",
                )
            )
        for effect in spec.side_effect_classes:
            rows.append(
                HierarchyCoverageItem(
                    f"side_effect:{model_id}:{effect}",
                    item_type="side_effect",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"unique auxiliary side-effect owner for {effect}",
                )
            )
        for name in (
            "declared_transition_contract",
            "owned_writes_only",
            "side_effect_at_most_once",
            "canonical_write_at_most_once",
        ):
            rows.append(
                HierarchyCoverageItem(
                    f"invariant:{model_id}:{name}",
                    item_type="invariant",
                    owner_model_id=model_id,
                    ownership=ownership,
                    description=f"{model_id} owns {name}",
                )
            )
    return tuple(rows)


def _children(receipts: Mapping[str, dict]) -> tuple[ChildModelEvidence, ...]:
    return tuple(
        ChildModelEvidence(
            model_id=spec.model_id,
            evidence_id=receipts[spec.model_id]["evidence_id"],
            risk_boundary=spec.modeled_boundary,
            inputs_accepted=INPUTS[spec.model_id],
            outputs_emitted=OUTPUTS[spec.model_id],
            state_owned=spec.owned_write_fields,
            side_effects_owned=spec.side_effect_classes,
            functional_areas=(f"skill_runtime:{spec.model_id}",),
            contracts_in=tuple(
                f"input_contract:{spec.model_id}:{token}"
                for token in INPUTS[spec.model_id]
            ),
            contracts_out=(f"guarantee:{spec.model_id}:finite_relation",),
            depends_on=DEPENDENCIES[spec.model_id],
            evidence_tier="hazard_green",
            evidence_current=True,
            estimated_state_count=len(spec.rules) + 1,
            observed_state_count=len(spec.rules) + 1,
            structurally_cohesive=True,
            functions_owned=(f"{spec.model_id}:finite_transition",),
            invariants_owned=tuple(
                f"{spec.model_id}:{name}"
                for name in (
                    "declared_transition_contract",
                    "owned_writes_only",
                    "side_effect_at_most_once",
                    "canonical_write_at_most_once",
                )
            ),
            risk_classes=tuple(
                f"{spec.model_id}:{risk}" for risk in spec.risk_classes
            ),
            validation_evidence=(
                receipts[spec.model_id]["evidence_id"],
                *(
                    proof["evidence_id"]
                    for proof in receipts[spec.model_id]["known_bad_proofs"]
                ),
            ),
        )
        for spec in CHILDREN
    )


def _closure() -> MeshClosureModel:
    transitions: list[MeshClosureTransition] = []
    consumes = "S0:SkillRuntimeRequest"
    for index, model_id in enumerate(CHILD_IDS):
        emits = OUTPUTS[model_id][0]
        transitions.append(
            MeshClosureTransition(
                transition_id=f"skill-runtime-step-{index + 1}",
                consumes=(consumes,),
                emits=(emits,),
                consumer_model_id=model_id,
                code_contract_id=f"abstract:{model_id}:finite_relation",
                rationale=f"{model_id} consumes the prior auxiliary disposition",
            )
        )
        consumes = emits
    transitions.append(
        MeshClosureTransition(
            transition_id="skill-runtime-parent-terminal",
            consumes=(consumes,),
            emits=("S0:SkillRuntimeTerminal",),
            consumer_model_id=PARENT_ID,
            code_contract_id=f"abstract:{PARENT_ID}:finite_relation",
            rationale="S0 publishes only a current terminal auxiliary disposition",
        )
    )
    return MeshClosureModel(
        parent_model_id=PARENT_ID,
        root_entries=("S0:SkillRuntimeRequest",),
        transitions=tuple(transitions),
        terminals=(
            MeshClosureTerminal(
                terminal_id="skill-runtime-terminal",
                consumes=("S0:SkillRuntimeTerminal",),
                terminal_kind="normal_exit",
                rationale="current, blocked, pending, or rollback dispositions terminate visibly",
            ),
        ),
        required_outputs=tuple(
            token
            for model_id in CHILD_IDS
            for token in OUTPUTS[model_id]
        ),
        require_normal_exit=True,
        rationale="S0 consumes every S1-S5 disposition without entering M0/C1-C12.",
    )


def build_partition(
    receipts: Mapping[str, dict],
) -> HierarchyPartitionMap:
    children = _children(receipts)
    coverage = _coverage_items()
    return HierarchyPartitionMap(
        parent_model_id=PARENT_ID,
        coverage_items=coverage,
        child_models=children,
        target_split_derivation=ModelTargetSplitDerivation(
            source_model_id=PARENT_ID,
            target_child_model_ids=CHILD_IDS,
            covered_partition_item_ids=tuple(row.item_id for row in coverage),
            state_owner_fields=tuple(
                field for spec in CHILDREN for field in spec.owned_write_fields
            ),
            side_effect_owner_fields=tuple(
                effect for spec in CHILDREN for effect in spec.side_effect_classes
            ),
            source_model_path=(
                "flowguard_models/models/s00_skill_runtime.py"
            ),
            rationale=(
                "S0 partitions inventory, compatibility, resolution, managed "
                "synchronization, and validation/rollback into five disjoint children."
            ),
            derived_from_flowguard_model=True,
        ),
        reattachment_contracts=tuple(
            ChildReattachmentContract(
                child_model_id=child.model_id,
                consumed_evidence_id=child.evidence_id,
                expected_inputs=child.inputs_accepted,
                expected_outputs=child.outputs_emitted,
                expected_state_owned=child.state_owned,
                expected_side_effects_owned=child.side_effects_owned,
                expected_contracts_out=child.contracts_out,
                rationale=f"S0 consumes current {child.model_id} evidence",
            )
            for child in children
        ),
        required_evidence_tier="hazard_green",
        closure_model=_closure(),
    )


def run_mesh(
    *,
    receipt_root: Path = DEFAULT_RECEIPT_ROOT,
) -> dict:
    receipts = _load_receipts(receipt_root)
    partition = build_partition(receipts)
    report = review_hierarchical_mesh(partition, model_count=len(CHILD_IDS))
    parent = receipts[PARENT_ID]
    parent_current = (
        parent["model_fingerprint"] == S0.fingerprint()
        and parent["pass_for_skill_runtime"] is True
        and "hazard_green" in parent["evidence_tiers"]
    )
    status = "mesh_green" if report.ok and parent_current else "blocked"
    identity = {
        "parent": S0.fingerprint(),
        "children": {
            spec.model_id: spec.fingerprint() for spec in CHILDREN
        },
        "evidence": {
            model_id: receipt["evidence_id"]
            for model_id, receipt in receipts.items()
        },
        "partition": partition.to_dict(),
    }
    fingerprint = "sha256:" + sha256(
        json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "artifact_type": "matters.skill-runtime-model-mesh-receipt.v1",
        "mesh_id": "S0_skill_runtime_mesh",
        "mesh_fingerprint": fingerprint,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "evidence_tier": "mesh_green" if status == "mesh_green" else "candidate_only",
        "parent_model_id": PARENT_ID,
        "parent_evidence_id": parent["evidence_id"],
        "parent_current": parent_current,
        "child_evidence_ids": {
            model_id: receipts[model_id]["evidence_id"]
            for model_id in CHILD_IDS
        },
        "native_report": report.to_dict(),
        "partition": partition.to_dict(),
        "claim_boundary": (
            "mesh_green proves only the bounded abstract S0/S1-S5 partition, "
            "unique auxiliary ownership, current child receipt reattachment, "
            "and terminal interface closure. It does not prove product runtime, "
            "M0/C1-C12 integration, installed skill bytes, global installation, "
            "ResearchGuard execution, or live conformance."
        ),
        "non_supporting_unrun_layers": (
            "production_code_contract",
            "installed_projection",
            "native_skill_validation",
            "live_researchguard",
            "m0_c1_c12_integration",
            "release",
        ),
    }


def main() -> int:
    result = run_mesh()
    MESH_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    MESH_RECEIPT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": result["status"] == "mesh_green",
                "status": result["status"],
                "receipt": "repo://.flowguard/evidence/skill_runtime/S0_skill_runtime_mesh.json",
                "claim_boundary": result["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "mesh_green" else 1


if __name__ == "__main__":
    raise SystemExit(main())
