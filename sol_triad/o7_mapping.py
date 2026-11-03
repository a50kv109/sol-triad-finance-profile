"""
Proposed O7 -> S-C-D Mapping Layer (PROPOSED - NOT CANONICAL).

Defines typed O7 primitives and an explicit, non-destructive mapping function
to the canonical Triad Engine primitives <SOURCE, CONSTRAINT, DISSIPATE> + SystemState.

Status: PROPOSED
Design Rule: No silent information loss. Any unrepresented fields, semantic gaps,
or ungrounded authorities must be explicitly returned in the mapping report.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any, List, Tuple

from .models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EpistemicStatus,
)
from .units import UnitRegistry


@dataclass
class O7Source:
    """O7 SOURCE: Epistemic provenance and root authority."""
    id: str
    authority_domain: Set[str]
    granted_scope: Set[str]
    granted_loss_domains: Set[str]
    epistemic_status: EpistemicStatus
    timestamp_sec: float
    max_age_sec: float = 300.0
    payload_hash: Optional[str] = None
    corroborating_evidence_ids: Set[str] = field(default_factory=set)
    # Extra O7 metadata not directly in triad kernel:
    creator_signature: Optional[str] = None
    provenance_chain: List[str] = field(default_factory=list)


@dataclass
class O7State:
    """O7 STATE: Observed snapshot of environmental parameters and memory."""
    current_values: Dict[str, float] = field(default_factory=dict)
    active_flags: Dict[str, bool] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    # O7 environmental state elements:
    memory_context: Dict[str, Any] = field(default_factory=dict)
    observer_id: Optional[str] = None


@dataclass
class O7Flow:
    """O7 FLOW: Dynamic execution vectors, state transitions, and step sequences."""
    state_delta: Dict[str, float] = field(default_factory=dict)
    flag_delta: Dict[str, bool] = field(default_factory=dict)
    resource_cost: Dict[str, float] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    # O7 dynamic flow elements (unsupported by single-triad kernel):
    sequence_step: int = 1
    branch_conditions: Dict[str, Any] = field(default_factory=dict)
    rollback_vector: Optional[Dict[str, float]] = None


@dataclass
class O7Constraint:
    """O7 CONSTRAINT: Operational boundaries, protected sets, bounds, and invariants."""
    domain_scope: Set[str] = field(default_factory=set)
    target_objects: Set[str] = field(default_factory=set)
    protected_set: Set[str] = field(default_factory=set)
    protected_values: Dict[str, float] = field(default_factory=dict)
    min_bounds: Dict[str, float] = field(default_factory=dict)
    max_bounds: Dict[str, float] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    protected_flags: Set[str] = field(default_factory=set)
    forbidden_flags: Dict[str, bool] = field(default_factory=dict)
    required_flags: Dict[str, bool] = field(default_factory=dict)
    # O7 high-level ethical / policy constraints (not numerical scalars):
    policy_rules: List[str] = field(default_factory=list)


@dataclass
class O7Compare:
    """O7 COMPARE: Operator of divergence, metric deltas, and goal evaluation."""
    target_states: Set[str] = field(default_factory=set)
    tolerance_thresholds: Dict[str, float] = field(default_factory=dict)
    # O7 Goal evaluation (unsupported by kernel arbiter):
    goal_utility_function: Optional[str] = None
    expected_gain: Optional[float] = None


@dataclass
class O7Dissipate:
    """O7 DISSIPATE: Loss channels, entropy dissipation, and actuation side effects."""
    loss_domain: Set[str] = field(default_factory=set)
    side_effects: Set[str] = field(default_factory=set)
    entropy_delta: Optional[float] = None
    units: Dict[str, str] = field(default_factory=dict)


@dataclass
class O7Capability:
    """O7 CAPABILITY: Executive permission, tool invocation rights, and API access."""
    tool_name: Optional[str] = None
    allowed_operations: Set[str] = field(default_factory=set)
    rate_limits: Dict[str, int] = field(default_factory=dict)


@dataclass
class O7Bundle:
    """Complete bundle of O7 primitives submitted by an agent."""
    source: O7Source
    state: O7State
    flow: O7Flow
    constraint: O7Constraint
    compare: O7Compare
    dissipate: O7Dissipate
    capability: Optional[O7Capability] = None


@dataclass
class O7MappingResult:
    """Result of attempting to map an O7Bundle to Triad Engine input."""
    is_valid: bool
    is_executable: bool = False
    source_primitive: Optional[SourcePrimitive] = None
    constraint_primitive: Optional[ConstraintPrimitive] = None
    dissipate_primitive: Optional[DissipatePrimitive] = None
    system_state: Optional[SystemState] = None
    applied_transformations: List[str] = field(default_factory=list)
    unrepresented_fields: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    def get_engine_inputs(
        self,
        allow_unrepresented: bool = False,
    ) -> Tuple[SourcePrimitive, ConstraintPrimitive, DissipatePrimitive, SystemState]:
        """
        Safely retrieves the canonical triad engine inputs for execution.

        Fail-closed gate: Raises ValueError if the mapping is not valid or contains
        unrepresented fields without explicit acknowledgement (allow_unrepresented=True).
        Prevents unverified/lossy mappings from accidentally being executed.
        """
        if not self.is_valid:
            raise ValueError(f"Mapping is invalid: {self.rejection_reason}")
        if self.ambiguities:
            raise ValueError(
                f"Mapping cannot be executed automatically: ambiguities present: {self.ambiguities}. "
                "Resolve semantic ambiguities before executing."
            )
        if not self.is_executable and not allow_unrepresented:
            raise ValueError(
                f"Mapping cannot be executed automatically: unrepresented fields present: {self.unrepresented_fields}. "
                "Pass allow_unrepresented=True only after explicit human/policy review of dropped semantic fields."
            )
        if (
            self.source_primitive is None
            or self.constraint_primitive is None
            or self.dissipate_primitive is None
            or self.system_state is None
        ):
            raise ValueError("Mapping has missing primitive structures; cannot form engine inputs.")
        return (
            self.source_primitive,
            self.constraint_primitive,
            self.dissipate_primitive,
            self.system_state,
        )


def map_o7_to_triad(bundle: O7Bundle) -> O7MappingResult:
    """
    Proposed explicit mapping function from O7Bundle to Triad Engine inputs.

    Translates:
    - O7Source -> SourcePrimitive
    - O7Constraint -> ConstraintPrimitive
    - O7Flow + O7Dissipate + O7Compare -> DissipatePrimitive
    - O7State -> SystemState

    Guarantees:
    - Zero silent information loss: Any unrepresented fields, semantic gaps,
      or ungrounded authorities are explicitly recorded with original values.
    - Strict physical units: Missing or conflicting physical dimensions in
      state_delta and resource_cost are rejected fail-closed.
    - Execution-readiness gate: is_executable is False whenever unrepresented
      fields exist, preventing accidental automated execution.
    """
    applied_transforms: List[str] = []
    unrepresented: List[str] = []
    ambiguities: List[str] = []

    # 1. Structural validation of bundle and nested objects
    if bundle is None or not isinstance(bundle, O7Bundle):
        return O7MappingResult(
            is_valid=False,
            is_executable=False,
            rejection_reason="REJECTED: bundle is None or not an instance of O7Bundle.",
        )

    for field_name, expected_type in [
        ("source", O7Source),
        ("state", O7State),
        ("flow", O7Flow),
        ("constraint", O7Constraint),
        ("compare", O7Compare),
        ("dissipate", O7Dissipate),
    ]:
        obj = getattr(bundle, field_name, None)
        if obj is None or not isinstance(obj, expected_type):
            return O7MappingResult(
                is_valid=False,
                is_executable=False,
                rejection_reason=f"REJECTED: O7Bundle.{field_name} is None or invalid type (expected {expected_type.__name__}).",
            )

    # Validate mandatory source fields
    if not bundle.source.id or not str(bundle.source.id).strip():
        return O7MappingResult(
            is_valid=False,
            is_executable=False,
            rejection_reason="REJECTED: O7Source.id is empty or whitespace. Evidence grounding impossible.",
        )

    if bundle.source.authority_domain is None:
        return O7MappingResult(
            is_valid=False,
            is_executable=False,
            rejection_reason="REJECTED: O7Source.authority_domain is None (structural defect).",
        )

    # Validate unit dictionary contents
    for loc_name, unit_dict in [
        ("flow.units", bundle.flow.units),
        ("dissipate.units", bundle.dissipate.units),
        ("state.units", bundle.state.units),
        ("constraint.units", bundle.constraint.units),
    ]:
        if not isinstance(unit_dict, dict):
            return O7MappingResult(
                is_valid=False,
                is_executable=False,
                rejection_reason=f"REJECTED: {loc_name} must be a dictionary, got {type(unit_dict).__name__}.",
            )
        for var_name, u_val in unit_dict.items():
            if not isinstance(u_val, str) or not u_val.strip():
                return O7MappingResult(
                    is_valid=False,
                    is_executable=False,
                    rejection_reason=(
                        f"REJECTED: Unit for '{var_name}' in {loc_name} must be a non-empty string, "
                        f"got {u_val!r}."
                    ),
                )

    # Validate numeric types in delta and costs
    for var, val in bundle.flow.state_delta.items():
        if not isinstance(val, (int, float)):
            return O7MappingResult(
                is_valid=False,
                is_executable=False,
                rejection_reason=f"REJECTED: flow.state_delta['{var}'] must be a numeric value, got {type(val).__name__}.",
            )
    for var, val in bundle.flow.resource_cost.items():
        if not isinstance(val, (int, float)):
            return O7MappingResult(
                is_valid=False,
                is_executable=False,
                rejection_reason=f"REJECTED: flow.resource_cost['{var}'] must be a numeric value, got {type(val).__name__}.",
            )

    # 2. Map SOURCE
    source_prim = SourcePrimitive(
        evidence_id=bundle.source.id.strip(),
        authority_domain=set(bundle.source.authority_domain),
        granted_scope=set(bundle.source.granted_scope) if bundle.source.granted_scope is not None else None,
        granted_loss_domains=set(bundle.source.granted_loss_domains) if bundle.source.granted_loss_domains is not None else None,
        epistemic_type=bundle.source.epistemic_status,
        timestamp_sec=bundle.source.timestamp_sec,
        max_age_sec=bundle.source.max_age_sec,
        corroborating_evidence_ids=set(bundle.source.corroborating_evidence_ids),
        payload_hash=bundle.source.payload_hash,
    )
    applied_transforms.append("O7Source -> SourcePrimitive (direct field mapping)")

    if bundle.source.creator_signature is not None and str(bundle.source.creator_signature).strip() != "":
        unrepresented.append(f"O7Source.creator_signature={bundle.source.creator_signature!r} (triad v0.4 kernel does not verify asymmetric signatures)")
    if bundle.source.provenance_chain:
        unrepresented.append(f"O7Source.provenance_chain={bundle.source.provenance_chain!r} (provenance graph tracking requires v0.4.1+ graph oracle)")

    # 3. Map CONSTRAINT
    constraint_prim = ConstraintPrimitive(
        domain_scope=set(bundle.constraint.domain_scope),
        target_objects=set(bundle.constraint.target_objects),
        protected_set=set(bundle.constraint.protected_set),
        protected_values=dict(bundle.constraint.protected_values),
        max_bounds=dict(bundle.constraint.max_bounds),
        min_bounds=dict(bundle.constraint.min_bounds),
        units=dict(bundle.constraint.units),
        protected_flags=set(bundle.constraint.protected_flags),
        forbidden_flags=dict(bundle.constraint.forbidden_flags),
        required_flags=dict(bundle.constraint.required_flags),
    )
    applied_transforms.append("O7Constraint -> ConstraintPrimitive (boundary and invariant fields mapped)")

    if bundle.constraint.policy_rules:
        unrepresented.append(f"O7Constraint.policy_rules={bundle.constraint.policy_rules!r} (natural language ethical/policy rules cannot be evaluated numerically)")

    # 4. Resolve and Validate Units for Flow and Dissipate
    # Variables appearing in flow.state_delta and flow.resource_cost MUST have explicit physical units.
    resolved_dissipate_units: Dict[str, str] = {}
    flow_and_dissipate_vars = set(bundle.flow.state_delta.keys()) | set(bundle.flow.resource_cost.keys())

    for var in sorted(flow_and_dissipate_vars):
        # Sourcing candidates:
        # 1. bundle.flow.units
        # 2. bundle.dissipate.units
        # 3. bundle.state.units (if declared for that physical state variable)
        # 4. bundle.constraint.units (if declared in constraint invariants)
        flow_u = bundle.flow.units.get(var)
        diss_u = bundle.dissipate.units.get(var)
        state_u = bundle.state.units.get(var)
        const_u = bundle.constraint.units.get(var)

        candidates: List[Tuple[str, str]] = []
        if flow_u:
            candidates.append((f"flow.units['{var}']", flow_u))
        if diss_u:
            candidates.append((f"dissipate.units['{var}']", diss_u))
        if state_u:
            candidates.append((f"state.units['{var}']", state_u))
        if const_u:
            candidates.append((f"constraint.units['{var}']", const_u))

        if not candidates:
            return O7MappingResult(
                is_valid=False,
                is_executable=False,
                rejection_reason=(
                    f"REJECTED: Missing physical unit for variable '{var}' in flow/dissipate. "
                    "Units must be explicitly declared (no guessing or defaults permitted)."
                ),
            )

        # Check for conflicts between declared units across ALL candidate pairs (source order independent)
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                loc_a, u_a = candidates[i]
                loc_b, u_b = candidates[j]
                if u_a.strip().lower() == u_b.strip().lower():
                    continue
                comp, msg = UnitRegistry.are_compatible(u_a, u_b)
                if not comp:
                    return O7MappingResult(
                        is_valid=False,
                        is_executable=False,
                        rejection_reason=(
                            f"REJECTED: Conflicting units for variable '{var}': {loc_a}='{u_a}' "
                            f"vs {loc_b}='{u_b}'. Incompatible physical dimensions: {msg}"
                        ),
                    )

        # Primary operational unit comes from flow.units if specified, otherwise dissipate.units, else state.units
        primary_unit = flow_u or diss_u or state_u or const_u
        resolved_dissipate_units[var] = primary_unit

    # Copy any remaining explicit units declared in dissipate.units or flow.units
    for k, v in bundle.dissipate.units.items():
        if k not in resolved_dissipate_units:
            resolved_dissipate_units[k] = v
    for k, v in bundle.flow.units.items():
        if k not in resolved_dissipate_units:
            resolved_dissipate_units[k] = v

    # 5. Map DISSIPATE (merging O7Flow + O7Dissipate + O7Compare target states)
    dissipate_prim = DissipatePrimitive(
        loss_domain=set(bundle.dissipate.loss_domain),
        target_states=set(bundle.compare.target_states),
        side_effects=set(bundle.dissipate.side_effects),
        resource_cost=dict(bundle.flow.resource_cost),
        state_delta=dict(bundle.flow.state_delta),
        flag_delta=dict(bundle.flow.flag_delta),
        units=resolved_dissipate_units,
    )
    applied_transforms.append(
        "O7Flow (state_delta, flag_delta, resource_cost) + O7Dissipate (loss_domain, side_effects) + "
        "O7Compare (target_states) -> DissipatePrimitive"
    )

    if bundle.flow.sequence_step != 1:
        unrepresented.append(f"O7Flow.sequence_step={bundle.flow.sequence_step} (triad evaluates single transition, not sequential multi-step loops)")
    if bundle.flow.branch_conditions:
        unrepresented.append(f"O7Flow.branch_conditions={bundle.flow.branch_conditions!r} (conditional branching execution paths are not modeled in triad delta)")
    if bundle.flow.rollback_vector:
        unrepresented.append(f"O7Flow.rollback_vector={bundle.flow.rollback_vector!r} (transactional rollback is handled by host orchestrator)")
    if bundle.compare.goal_utility_function:
        unrepresented.append(f"O7Compare.goal_utility_function={bundle.compare.goal_utility_function!r} (kernel verifies coherence, not goal optimization)")
    if bundle.compare.expected_gain is not None:
        unrepresented.append(f"O7Compare.expected_gain={bundle.compare.expected_gain} (economic/utility gain is outside verification scope)")
    if bundle.compare.tolerance_thresholds:
        unrepresented.append(f"O7Compare.tolerance_thresholds={dict(bundle.compare.tolerance_thresholds)!r} (kernel evaluates exact coherence bounds, metric tolerance thresholds are not modeled)")
    if bundle.dissipate.entropy_delta is not None:
        unrepresented.append(f"O7Dissipate.entropy_delta={bundle.dissipate.entropy_delta} (triad kernel evaluates scalar resource costs, not thermodynamic entropy deltas)")

    # 6. Map CAPABILITY
    if bundle.capability is not None:
        unrepresented.append(
            f"O7Capability(tool_name={bundle.capability.tool_name!r}, "
            f"allowed_operations={sorted(list(bundle.capability.allowed_operations))!r}, "
            f"rate_limits={bundle.capability.rate_limits!r}) "
            "(kernel has no tool execution subsystem; capabilities must be bounded passively via SOURCE.granted_scope)"
        )
    else:
        applied_transforms.append("O7Capability is None (no active tool invocation privileges requested)")

    # 7. Map STATE -> SystemState
    system_state = SystemState(
        current_values=dict(bundle.state.current_values),
        active_flags=dict(bundle.state.active_flags),
        units=dict(bundle.state.units),
    )
    applied_transforms.append("O7State (current_values, active_flags, units) -> SystemState")

    if bundle.state.memory_context:
        unrepresented.append(f"O7State.memory_context={bundle.state.memory_context!r} (unstructured LLM memory context cannot be verified as scalar state)")
    if bundle.state.observer_id:
        unrepresented.append(f"O7State.observer_id={bundle.state.observer_id!r} (observer metadata is not evaluated by kernel)")

    # 8. Execution-readiness Gate
    # is_executable is True ONLY if the translation is completely lossless (zero unrepresented fields)
    is_exec = (len(unrepresented) == 0 and len(ambiguities) == 0)

    return O7MappingResult(
        is_valid=True,
        is_executable=is_exec,
        source_primitive=source_prim,
        constraint_primitive=constraint_prim,
        dissipate_primitive=dissipate_prim,
        system_state=system_state,
        applied_transformations=applied_transforms,
        unrepresented_fields=unrepresented,
        ambiguities=ambiguities,
    )
