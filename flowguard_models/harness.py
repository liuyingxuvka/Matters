"""Shared real-FlowGuard harness for finite Matters model declarations.

This module does not replace FlowGuard. It turns reviewable, immutable Matters
case declarations into FlowGuard ``Workflow`` and ``FlowGuardCheckPlan``
objects. Every configured block remains an executable
``Input x State -> Set(Output x State)`` relation checked by the installed
FlowGuard package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Iterable, Mapping, Sequence

from flowguard import (
    FlowGuardCheckPlan,
    FunctionResult,
    Invariant,
    InvariantResult,
    KnownBadProof,
    MinimumModelContract,
    RiskIntent,
    RiskProfile,
    Scenario,
    ScenarioExpectation,
    SkippedCheck,
    StateClosureDimension,
    StateClosurePlan,
    TemplateHarvestReview,
    TemplateReuseReview,
    Workflow,
    run_model_first_checks,
)


@dataclass(frozen=True)
class CaseInput:
    model_id: str
    case_id: str
    logical_key: str


@dataclass(frozen=True)
class DecisionOutput:
    model_id: str
    case_id: str
    decision: str
    writes: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    emitted_tokens: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class ModelState:
    processed_keys: tuple[str, ...] = ()
    canonical_write_events: tuple[str, ...] = ()
    side_effect_events: tuple[str, ...] = ()
    terminal_outputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaseRule:
    case_id: str
    decision: str
    label: str
    writes: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    emitted_tokens: tuple[str, ...] = ()
    reason: str = ""
    logical_key: str = ""
    retry_decision: str = "no_delta"
    retry_label: str = "retry_no_delta"
    retry_tokens: tuple[str, ...] = ("NoDelta",)

    def key(self) -> str:
        return self.logical_key or self.case_id


@dataclass(frozen=True)
class HazardSpec:
    failure_id: str
    protected_error_class: str
    description: str
    protected_harm: str
    case_id: str
    broken_decision: str
    broken_writes: tuple[str, ...] = ()
    broken_side_effects: tuple[str, ...] = ()
    broken_tokens: tuple[str, ...] = ()
    ignore_idempotency: bool = False


@dataclass(frozen=True)
class FiniteModelSpec:
    model_id: str
    title: str
    modeled_boundary: str
    state_fields: tuple[str, ...]
    owned_write_fields: tuple[str, ...]
    side_effect_classes: tuple[str, ...]
    completion_evidence: tuple[str, ...]
    rules: tuple[CaseRule, ...]
    hazards: tuple[HazardSpec, ...]
    risk_classes: tuple[str, ...] = ()
    template_ids: tuple[str, ...] = ()
    template_no_match_reason: str = ""
    blindspots: tuple[str, ...] = ()
    claim_boundary: str = ""

    def rule_map(self) -> Mapping[str, CaseRule]:
        return {rule.case_id: rule for rule in self.rules}

    def fingerprint(self) -> str:
        payload = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + sha256(payload).hexdigest()


class DeclaredFiniteTransition:
    """One model-owned finite behavior block."""

    accepted_input_type = CaseInput
    input_description = "finite Matters case input"
    output_description = "declared decision, writes, side effects, and tokens"
    idempotency = "Repeated logical_key returns NoDelta without writes or side effects."

    def __init__(self, spec: FiniteModelSpec, hazard: HazardSpec | None = None):
        self.spec = spec
        self.hazard = hazard
        self.name = f"{spec.model_id}_finite_transition"
        self.reads = ("processed_keys",) + spec.state_fields
        self.writes = (
            "processed_keys",
            "canonical_write_events",
            "side_effect_events",
            "terminal_outputs",
        ) + spec.owned_write_fields

    def apply(
        self,
        input_obj: CaseInput,
        state: ModelState,
    ) -> Iterable[FunctionResult]:
        rule = self.spec.rule_map()[input_obj.case_id]
        repeated = input_obj.logical_key in state.processed_keys
        ignore_repeat = (
            repeated
            and self.hazard is not None
            and self.hazard.case_id == input_obj.case_id
            and self.hazard.ignore_idempotency
        )
        if repeated and not ignore_repeat:
            yield FunctionResult(
                output=DecisionOutput(
                    model_id=self.spec.model_id,
                    case_id=input_obj.case_id,
                    decision=rule.retry_decision,
                    emitted_tokens=rule.retry_tokens,
                    reason="idempotent repeated input",
                ),
                new_state=state,
                label=rule.retry_label,
            )
            return

        decision = rule.decision
        writes = rule.writes
        side_effects = rule.side_effects
        emitted_tokens = rule.emitted_tokens
        reason = rule.reason
        label = rule.label
        if self.hazard is not None and self.hazard.case_id == input_obj.case_id:
            decision = self.hazard.broken_decision
            writes = self.hazard.broken_writes
            side_effects = self.hazard.broken_side_effects
            emitted_tokens = self.hazard.broken_tokens
            reason = f"known-bad variant: {self.hazard.failure_id}"
            label = f"broken_{self.hazard.failure_id}"

        processed_keys = state.processed_keys
        if input_obj.logical_key not in processed_keys:
            processed_keys = processed_keys + (input_obj.logical_key,)
        new_state = replace(
            state,
            processed_keys=processed_keys,
            canonical_write_events=state.canonical_write_events
            + tuple(f"{input_obj.logical_key}|{field}" for field in writes),
            side_effect_events=state.side_effect_events
            + tuple(f"{input_obj.logical_key}|{effect}" for effect in side_effects),
            terminal_outputs=state.terminal_outputs
            + (f"{input_obj.logical_key}|{decision}",),
        )
        yield FunctionResult(
            output=DecisionOutput(
                model_id=self.spec.model_id,
                case_id=input_obj.case_id,
                decision=decision,
                writes=writes,
                side_effects=side_effects,
                emitted_tokens=emitted_tokens,
                reason=reason,
            ),
            new_state=new_state,
            label=label,
        )


def _transition_contract_invariant(spec: FiniteModelSpec):
    rules = spec.rule_map()

    def predicate(_state: ModelState, trace) -> InvariantResult:
        for step in trace.steps:
            input_obj = step.function_input
            output = step.function_output
            if not isinstance(input_obj, CaseInput) or not isinstance(
                output, DecisionOutput
            ):
                return InvariantResult.fail(
                    f"{spec.model_id} emitted an undeclared input/output type"
                )
            if input_obj.model_id != spec.model_id or output.model_id != spec.model_id:
                return InvariantResult.fail(
                    f"{spec.model_id} consumed or emitted a foreign model id"
                )
            rule = rules[input_obj.case_id]
            repeated = input_obj.logical_key in step.old_state.processed_keys
            if repeated:
                expected = (
                    rule.retry_decision,
                    (),
                    (),
                    rule.retry_tokens,
                    rule.retry_label,
                )
            else:
                expected = (
                    rule.decision,
                    rule.writes,
                    rule.side_effects,
                    rule.emitted_tokens,
                    rule.label,
                )
            observed = (
                output.decision,
                output.writes,
                output.side_effects,
                output.emitted_tokens,
                step.label,
            )
            if observed != expected:
                return InvariantResult.fail(
                    f"{spec.model_id}:{input_obj.case_id} transition mismatch; "
                    f"expected={expected!r} observed={observed!r}"
                )
        return InvariantResult.pass_()

    return predicate


def _owned_writes_invariant(spec: FiniteModelSpec):
    owned = set(spec.owned_write_fields)

    def predicate(_state: ModelState, trace) -> InvariantResult:
        for step in trace.steps:
            output = step.function_output
            if not isinstance(output, DecisionOutput):
                continue
            foreign = tuple(sorted(set(output.writes) - owned))
            if foreign:
                return InvariantResult.fail(
                    f"{spec.model_id} wrote fields owned elsewhere: {foreign!r}"
                )
        return InvariantResult.pass_()

    return predicate


def _side_effect_at_most_once(
    state: ModelState, _trace
) -> InvariantResult:
    if len(state.side_effect_events) != len(set(state.side_effect_events)):
        return InvariantResult.fail("logical input repeated a durable side effect")
    return InvariantResult.pass_()


def _canonical_write_at_most_once(
    state: ModelState, _trace
) -> InvariantResult:
    if len(state.canonical_write_events) != len(set(state.canonical_write_events)):
        return InvariantResult.fail("logical input repeated a canonical write")
    return InvariantResult.pass_()


def invariants_for(spec: FiniteModelSpec) -> tuple[Invariant, ...]:
    return (
        Invariant(
            name=f"{spec.model_id}_declared_transition_contract",
            description="Every finite input follows its exact declared decision, write, side-effect, token, and retry relation.",
            predicate=_transition_contract_invariant(spec),
            metadata={"property_classes": ("state_transition", "contract")},
        ),
        Invariant(
            name=f"{spec.model_id}_owned_writes_only",
            description="The child writes only fields in its declared ownership partition.",
            predicate=_owned_writes_invariant(spec),
            metadata={"property_classes": ("ownership", "side_effect")},
        ),
        Invariant(
            name=f"{spec.model_id}_side_effect_at_most_once",
            description="A repeated logical input cannot repeat a durable side effect.",
            predicate=_side_effect_at_most_once,
            metadata={"property_classes": ("deduplication", "idempotency")},
        ),
        Invariant(
            name=f"{spec.model_id}_canonical_write_at_most_once",
            description="A repeated logical input cannot repeat a canonical state write.",
            predicate=_canonical_write_at_most_once,
            metadata={"property_classes": ("deduplication", "idempotency", "ownership")},
        ),
    )


def build_workflow(
    spec: FiniteModelSpec,
    *,
    hazard: HazardSpec | None = None,
) -> Workflow:
    return Workflow(
        (DeclaredFiniteTransition(spec, hazard=hazard),),
        name=spec.model_id,
    )


def _template_harvest_review(spec: FiniteModelSpec) -> TemplateHarvestReview:
    if spec.template_ids:
        return TemplateHarvestReview(
            disposition="duplicate_linked",
            linked_template_ids=spec.template_ids,
        )
    return TemplateHarvestReview(
        disposition="not_harvestable",
        not_harvestable_reason="not_reusable_project_specific",
    )


def scenarios_for(spec: FiniteModelSpec) -> tuple[Scenario, ...]:
    scenarios = [
        Scenario(
            name=f"{spec.model_id}:{rule.case_id}:known-good",
            description=f"Declared known-good finite case {rule.case_id}.",
            initial_state=ModelState(),
            external_input_sequence=(
                CaseInput(spec.model_id, rule.case_id, rule.key()),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(rule.label,),
                forbidden_trace_labels=(f"broken_{rule.case_id}",),
                summary=f"{rule.case_id} reaches {rule.decision}",
            ),
            workflow=build_workflow(spec),
            invariants=invariants_for(spec),
            tags=("known_good", spec.model_id, rule.case_id),
        )
        for rule in spec.rules
    ]
    repeat_rule = spec.rules[0]
    scenarios.append(
        Scenario(
            name=f"{spec.model_id}:repeat-idempotent",
            description="Repeating one logical input yields NoDelta without a second write or side effect.",
            initial_state=ModelState(),
            external_input_sequence=(
                CaseInput(spec.model_id, repeat_rule.case_id, repeat_rule.key()),
                CaseInput(spec.model_id, repeat_rule.case_id, repeat_rule.key()),
            ),
            expected=ScenarioExpectation(
                expected_status="ok",
                required_trace_labels=(repeat_rule.label, repeat_rule.retry_label),
                summary="repeat input is idempotent",
            ),
            workflow=build_workflow(spec),
            invariants=invariants_for(spec),
            tags=("known_good", "retry", "idempotency", spec.model_id),
        )
    )
    return tuple(scenarios)


def state_closure_plan_for(spec: FiniteModelSpec) -> StateClosurePlan:
    return StateClosurePlan(
        plan_id=f"{spec.model_id}:closed-finite-boundary",
        dimensions=(
            StateClosureDimension(
                dimension_id="external_input",
                dimension_kind="external_input",
                policy="closed_enumeration",
                known_values=tuple(rule.case_id for rule in spec.rules),
                handling="reject_before_side_effect",
                side_effects_before_resolution=False,
                description="Phase A model input cases are a declared closed abstraction.",
            ),
            StateClosureDimension(
                dimension_id="output",
                dimension_kind="output",
                policy="closed_enumeration",
                known_values=tuple(
                    dict.fromkeys(
                        [rule.decision for rule in spec.rules]
                        + [rule.retry_decision for rule in spec.rules]
                    )
                ),
                handling="reject_before_side_effect",
                side_effects_before_resolution=False,
                description="Every abstract decision and NoDelta branch is enumerated.",
            ),
        ),
        claim_scope="bounded",
        allow_scoped_confidence=False,
        notes="Unknown concrete provider or payload shapes are outside this abstraction and must be rejected before side effects.",
    )


def build_check_plan(
    spec: FiniteModelSpec,
    *,
    workflow: Workflow,
    known_bad_proofs: Sequence[KnownBadProof] = (),
) -> FlowGuardCheckPlan:
    external_inputs = tuple(
        CaseInput(spec.model_id, rule.case_id, rule.key()) for rule in spec.rules
    )
    protected_error_classes = tuple(
        hazard.protected_error_class for hazard in spec.hazards
    )
    known_bad_ids = tuple(hazard.failure_id for hazard in spec.hazards)
    used_templates = spec.template_ids
    return FlowGuardCheckPlan(
        workflow=workflow,
        initial_states=(ModelState(),),
        external_inputs=external_inputs,
        invariants=invariants_for(spec),
        max_sequence_length=2,
        required_labels=tuple(rule.label for rule in spec.rules)
        + ("retry_no_delta",),
        scenarios=scenarios_for(spec),
        risk_profile=RiskProfile(
            modeled_boundary=spec.modeled_boundary,
            risk_classes=spec.risk_classes,
            risk_intent=RiskIntent(
                failure_modes=tuple(hazard.description for hazard in spec.hazards),
                protected_error_classes=protected_error_classes,
                protected_harms=tuple(hazard.protected_harm for hazard in spec.hazards),
                must_model_state=spec.state_fields,
                must_model_side_effects=spec.side_effect_classes,
                completion_evidence=spec.completion_evidence,
                adversarial_inputs=tuple(hazard.case_id for hazard in spec.hazards)
                + ("same logical input repeated",),
                hard_invariants=tuple(
                    invariant.name for invariant in invariants_for(spec)
                ),
                known_bad_cases=known_bad_ids,
                used_template_ids=used_templates,
                template_no_match_reason=spec.template_no_match_reason,
                blindspots=spec.blindspots,
            ),
            confidence_goal="model_level",
            skipped_checks=(
                SkippedCheck(
                    "conformance_replay",
                    "production code does not exist before G4/G5",
                ),
                SkippedCheck(
                    "live_current",
                    "real providers are forbidden until G8 is current-green",
                ),
            ),
            notes=spec.claim_boundary,
        ),
        template_reuse_review=TemplateReuseReview(
            used_template_ids=used_templates,
            searched_layers=("public", "local"),
            match_template_ids=used_templates,
            no_match_reason=spec.template_no_match_reason,
        ),
        template_harvest_review=_template_harvest_review(spec),
        minimum_model_contract=MinimumModelContract(
            protected_error_classes=protected_error_classes,
            modeled_state=spec.state_fields,
            modeled_side_effects=spec.side_effect_classes,
            completion_evidence=spec.completion_evidence,
            known_bad_cases=known_bad_ids,
        ),
        known_bad_proofs=known_bad_proofs,
        state_closure_plan=state_closure_plan_for(spec),
        scenario_matrix_config={"enabled": False},
        metadata={
            "matters_model_id": spec.model_id,
            "matters_model_fingerprint": spec.fingerprint(),
            "claim_boundary": spec.claim_boundary,
        },
    )


def run_known_bad(spec: FiniteModelSpec, hazard: HazardSpec):
    return run_model_first_checks(
        build_check_plan(
            spec,
            workflow=build_workflow(spec, hazard=hazard),
        )
    )


def known_bad_proof(spec: FiniteModelSpec, hazard: HazardSpec) -> KnownBadProof:
    summary = run_known_bad(spec, hazard)
    sections = {section.name: section for section in summary.sections}
    caught = sections["model_check"].status == "failed"
    return KnownBadProof(
        hazard.failure_id,
        protected_error_class=hazard.protected_error_class,
        method="broken_workflow_variant",
        expected_failure="failed",
        observed_status="failed" if caught else "passed",
        observed_failure=(
            f"{hazard.failure_id} violated the declared finite transition or ownership invariant"
            if caught
            else f"{hazard.failure_id} unexpectedly passed"
        ),
        evidence_id=f"{spec.model_id}:known-bad:{hazard.failure_id}",
    )


def run_current(spec: FiniteModelSpec):
    proofs = tuple(known_bad_proof(spec, hazard) for hazard in spec.hazards)
    summary = run_model_first_checks(
        build_check_plan(
            spec,
            workflow=build_workflow(spec),
            known_bad_proofs=proofs,
        )
    )
    return summary, proofs
