# O7 → S-C-D Mapping Layer: Audit, Semantics, and Verification Report

**Document Version:** 1.0.0  
**Target Module:** `sol_triad/o7_mapping.py`  
**Associated Test Suite:** `tests/test_o7_triad_semantics.py`  
**Kernel Baseline:** `SOL-Triad-Engine v0.4.0` (main branch)  
**Status:** PROPOSED / ISOLATED (Not connected to adapter ingress or verification kernel)

---

## 1. Executive Summary & Layer Scope

The `sol_triad/o7_mapping.py` module defines a translation layer bridging the **O7 primitive set** (`SOL-2-sol-for-agents`) to the canonical three-primitive state machine of the **SOL-Triad Engine** ($\langle S, C, D \rangle$ plus `SystemState`).

### Operational Status in Codebase
* **Isolated**: The module is standalone. Neither `sol_triad/engine.py`, `sol_triad/adapter.py`, nor the JSON ingress schema references or imports `o7_mapping.py`.
* **Experimental / Non-Executable by Default**: Automated execution via `get_engine_inputs()` is strictly fail-closed (`is_executable=False`) whenever any unrepresented semantic fields, structural gaps, or ambiguities are detected.

### Boundaries of Responsibility
* **In Scope**:
  1. Translating well-formed `O7Bundle` dataclasses into `SourcePrimitive`, `ConstraintPrimitive`, `DissipatePrimitive`, and `SystemState`.
  2. Fail-closed structural and type validation (null-guards, non-empty IDs, non-empty authority domains, numeric delta/cost types, string unit types).
  3. Strict physical unit resolution across candidate sources (`flow.units`, `dissipate.units`, `state.units`, `constraint.units`) using `UnitRegistry`.
  4. Explicit tracking of all semantic dimensions absent in the Triad kernel inside `unrepresented_fields` and `ambiguities`.
* **Out of Scope (Explicit Kernel Non-Goals)**:
  1. No execution of external tools or capabilities (`O7Capability`).
  2. No evaluation of natural language or ethical rules (`policy_rules`).
  3. No dynamic loop, sequence step, or branching management (`sequence_step`, `branch_conditions`, `rollback_vector`).
  4. No economic utility or goal optimization (`goal_utility_function`, `expected_gain`).
  5. No thermodynamic entropy tracking (`entropy_delta`).
  6. No cryptographic asymmetric signature verification (`creator_signature`).

---

## 2. Transformation Architecture: O7 → S-C-D

```
       O7 Bundle Inputs                            Triad Canonical Primitives
┌─────────────────────────────┐                  ┌─────────────────────────────┐
│          O7Source           │ ───────────────> │       SourcePrimitive       │
│ (id, authority_domain, ...) │                  │  (evidence_id, scope, ...)  │
└─────────────────────────────┘                  └─────────────────────────────┘
┌─────────────────────────────┐                  ┌─────────────────────────────┐
│        O7Constraint         │ ───────────────> │     ConstraintPrimitive     │
│ (domain_scope, bounds, ...) │                  │  (domain_scope, bounds, ...)│
└─────────────────────────────┘                  └─────────────────────────────┘
┌─────────────────────────────┐
│           O7Flow            │ ───┐
│(state_delta, resource_cost) │    │             ┌─────────────────────────────┐
├─────────────────────────────┤    ├───────────> │     DissipatePrimitive      │
│         O7Dissipate         │    │             │  (loss_domain, target_states│
│(loss_domain, side_effects)  │ ───┤             │   state_delta, costs, units)│
├─────────────────────────────┤    │             └─────────────────────────────┘
│          O7Compare          │ ───┘
│       (target_states)       │
└─────────────────────────────┘
┌─────────────────────────────┐                  ┌─────────────────────────────┐
│           O7State           │ ───────────────> │         SystemState         │
│(current_values, active_flags│                  │ (current_values, flags, u)  │
└─────────────────────────────┘                  └─────────────────────────────┘
┌─────────────────────────────┐                  ┌─────────────────────────────┐
│        O7Capability         │ ───────────────> │    unrepresented_fields     │
│ (tool APIs, rate limits)    │                  │  (Execution gate: BLOCKED)  │
└─────────────────────────────┘                  └─────────────────────────────┘
```

---

## 3. Comprehensive Field Mapping Matrix

| O7 Primitive | O7 Field | Target in Triad | Loss / Gap / Ambiguity Status | Impact on Automated Execution |
|---|---|---|---|---|
| **O7Source** | `id` | `SourcePrimitive.evidence_id` | Preserved (whitespace trimmed) | Validated non-empty; rejects if blank |
| | `authority_domain` | `SourcePrimitive.authority_domain` | Preserved (converted to `set`) | Validated not None; rejects if None |
| | `granted_scope` | `SourcePrimitive.granted_scope` | Preserved (`set` or `None`) | Full adherence to P_SC scope validation |
| | `granted_loss_domains` | `SourcePrimitive.granted_loss_domains` | Preserved (`set` or `None`) | Full adherence to P_SD loss validation |
| | `epistemic_status` | `SourcePrimitive.epistemic_type` | Preserved (`EpistemicStatus`) | Evaluated by Epistemic Arbiter |
| | `timestamp_sec` | `SourcePrimitive.timestamp_sec` | Preserved | Evaluated by Temporal Arbiter |
| | `max_age_sec` | `SourcePrimitive.max_age_sec` | Preserved | Evaluated by Temporal Arbiter |
| | `corroborating_evidence_ids` | `SourcePrimitive.corroborating_evidence_ids` | Preserved (`set`) | Evaluated in multi-source inference chains |
| | `payload_hash` | `SourcePrimitive.payload_hash` | Preserved | Verified if present |
| | `creator_signature` | **None** | **Unrepresented**: Triad does not verify asymmetric keys | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `provenance_chain` | **None** | **Unrepresented**: Multi-agent provenance graph requires v0.4.1+ oracle | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| **O7State** | `current_values` | `SystemState.current_values` | Preserved (`dict`) | Used as $S_0$ baseline |
| | `active_flags` | `SystemState.active_flags` | Preserved (`dict`) | Evaluated in invariant checks |
| | `units` | `SystemState.units` | Preserved (`dict`) | Validated string format; checked for compatibility |
| | `memory_context` | **None** | **Unrepresented**: Unstructured LLM context cannot be checked as scalar | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `observer_id` | **None** | **Unrepresented**: Observer metadata not evaluated by kernel | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| **O7Flow** | `state_delta` | `DissipatePrimitive.state_delta` | Preserved (`dict`) | Validated numeric; requires explicit physical units |
| | `resource_cost` | `DissipatePrimitive.resource_cost` | Preserved (`dict`) | Validated numeric; requires explicit physical units |
| | `flag_delta` | `DissipatePrimitive.flag_delta` | Preserved (`dict`) | Simulated into $S'$ |
| | `units` | `DissipatePrimitive.units` | Preserved (`dict`) | Resolved against candidates |
| | `sequence_step` | **None** | **Unrepresented** if $\ne 1$: Kernel evaluates single transitions only | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `branch_conditions` | **None** | **Unrepresented**: Dynamic execution branches not modeled | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `rollback_vector` | **None** | **Unrepresented**: Transactional rollback handled by orchestrator | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| **O7Constraint** | `domain_scope` | `ConstraintPrimitive.domain_scope` | Preserved (`set`) | P_SC containment check |
| | `target_objects` | `ConstraintPrimitive.target_objects` | Preserved (`set`) | P_SC containment check |
| | `protected_set` | `ConstraintPrimitive.protected_set` | Preserved (`set`) | Mutation forbidden check |
| | `protected_values` | `ConstraintPrimitive.protected_values` | Preserved (`dict`) | Constant value check |
| | `max_bounds` / `min_bounds` | `ConstraintPrimitive.max_bounds` / `min_bounds` | Preserved (`dict`) | Evaluated against simulated state $S'$ |
| | `units` | `ConstraintPrimitive.units` | Preserved (`dict`) | Cross-validated against physical dimensions |
| | `protected_flags` / `forbidden_flags` / `required_flags` | Flag constraints | Preserved | Evaluated against simulated flags |
| | `policy_rules` | **None** | **Unrepresented**: Natural language rules not evaluable numerically | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| **O7Compare** | `target_states` | `DissipatePrimitive.target_states` | Preserved (`set`) | P_CD coherence checks |
| | `tolerance_thresholds` | **None** | **Unrepresented**: Kernel evaluates exact bounds, not metric tolerances | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `goal_utility_function` | **None** | **Unrepresented**: Kernel checks safety, not utility maximization | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| | `expected_gain` | **None** | **Unrepresented**: Economic utility gain outside verification scope | Recorded in `unrepresented_fields`; sets `is_executable=False` |
| **O7Dissipate** | `loss_domain` | `DissipatePrimitive.loss_domain` | Preserved (`set`) | P_SD loss authorization check |
| | `side_effects` | `DissipatePrimitive.side_effects` | Preserved (`set`) | Audit record |
| | `units` | `DissipatePrimitive.units` | Preserved (`dict`) | Merged with resolved units |
| | `entropy_delta` | **None** | **Unrepresented** if not `None`: Thermodynamic entropy deltas not modeled | If not `None` (even `0.0`), recorded in `unrepresented_fields`; blocks execution |
| **O7Capability** | `tool_name`, `allowed_operations`, `rate_limits` | **None** | **Unrepresented**: Kernel has no executable tool invocation subsystem | If present, recorded in `unrepresented_fields`; blocks execution |

---

## 4. Contract of `O7MappingResult` and `get_engine_inputs()`

The execution gate is mathematically specified as:

$$\text{is\_executable} \iff (\text{is\_valid} \land |\text{unrepresented\_fields}| = 0 \land |\text{ambiguities}| = 0)$$

### Method: `get_engine_inputs(allow_unrepresented: bool = False)`
1. **Invariant 1 (Validity Precedence)**: If `is_valid` is `False`, raises `ValueError(f"Mapping is invalid: {self.rejection_reason}")`. Calling with `allow_unrepresented=True` **never** bypasses an invalid mapping.
2. **Invariant 2 (Ambiguity Rejection)**: If `len(self.ambiguities) > 0`, raises `ValueError`. Ambiguities are distinct from unrepresented fields and cannot be bypassed with `allow_unrepresented=True`.
3. **Invariant 3 (Unrepresented Field Protection)**: If `is_executable` is `False` and `allow_unrepresented` is `False`, raises `ValueError` listing all unrepresented fields.
4. **Invariant 4 (Structure Completeness)**: Ensures `source_primitive`, `constraint_primitive`, `dissipate_primitive`, and `system_state` are all populated before returning the 4-tuple.

---

## 5. Physical Unit Resolution & Dimensionality Rules

Variables declared in `flow.state_delta` and `flow.resource_cost` must have explicit physical units. The resolution algorithm operates as follows:

1. **Candidate Gathering**: For each variable $v \in \text{vars}(\text{state\_delta}) \cup \text{vars}(\text{resource\_cost})$, candidates are gathered from:
   - `flow.units[v]`
   - `dissipate.units[v]`
   - `state.units[v]`
   - `constraint.units[v]`
2. **Missing Unit Check**: If no candidates are found, mapping immediately fails closed (`is_valid=False`, `rejection_reason="REJECTED: Missing physical unit for variable 'v'..."`).
3. **Source Order Independence (All-Pairs Compatibility)**:
   For every pair $(c_i, c_j)$ where $i < j$:
   - If $u_i = u_j$ (case-insensitive string match), the pair is identical and valid.
   - Otherwise, `UnitRegistry.are_compatible(u_i, u_j)` is evaluated.
   - If incompatible, mapping immediately fails closed with `REJECTED: Conflicting units for variable 'v': ... Incompatible physical dimensions: ...`.
4. **Primary Unit Selection**: `primary_unit = flow_u or diss_u or state_u or const_u`.
5. **Format Validation**: All unit dictionary values across all 4 components must be non-empty strings. Non-string or whitespace strings fail closed.

---

## 6. Verification Results

### Automated Unit Test Execution
* **Command**: `python3 -m unittest discover -s tests -p "*.py"`
* **Total Tests Executed**: 75
* **Errors / Failures**: 0
* **Execution Time**: 0.084s
* **Status**: **PASS (OK)**

### Static Syntax & Whitespace Checks
* `python3 -m py_compile sol_triad/o7_mapping.py tests/test_o7_triad_semantics.py` $\implies$ Exit code 0.
* `git diff --no-index --check /dev/null sol_triad/o7_mapping.py` $\implies$ No whitespace or conflict marker errors.
* `git diff --no-index --check /dev/null tests/test_o7_triad_semantics.py` $\implies$ No whitespace or conflict marker errors.

---

## 7. Known Risks & Integration Prerequisites

Before `sol_triad/o7_mapping.py` can be connected to the public JSON ingress or `adapter.py`:

1. **Schema Definition**: A formal JSON Schema for `O7Bundle` (including `source`, `flow`, `state`, `constraint`, `compare`, `dissipate`, `capability`) must be added to `schemas/`.
2. **Untrusted Input Ingress Quarantine**: The public JSON ingress must not allow clients to specify arbitrary internal evaluation times or inject unverified evidence records.
3. **Loss Acknowledgement Flow**: If host systems choose to bypass unrepresented fields via `allow_unrepresented=True`, an audit logging mechanism must record every bypassed field and reason into an immutable audit trail.
4. **Epistemic Arbiter Alignment**: Proof that `O7Source.corroborating_evidence_ids` properly grounds multi-agent collaborative plans in the `EvidenceRegistry` without circular dependency loops.
