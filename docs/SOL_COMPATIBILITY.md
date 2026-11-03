# SOL Compatibility & Architectural Lineage

**Document Version:** 1.0.0  
**Target Package:** `SOL-Triad-Engine v0.3.1`  
**Status:** Canonical Reference

---

## 1. Context and Architectural References

The `SOL-Triad-Engine` is designed as an independent, deterministic verification kernel. It does not replace or modify foundational SOL specifications, but instead provides an executable coherence verification layer for proposed agent actions and state mutations.

Three foundational repositories serve as reference baselines:

| Repository | Primary Focus | Primitive Set / Ontology | Role in SOL-Triad |
|---|---|---|---|
| **[SOL-Engineering-Core](https://github.com/a50kv109/SOL-Engineering-Core)** | Foundational mathematical and ontological core of SOL | `SOURCE`, `CONSTRAINT`, `DISSIPATE`, `COMPARE` | Ontological baseline and grounding semantics |
| **[SOL-2-sol-for-agents](https://github.com/a50kv109/SOL-2-sol-for-agents)** | Operational runtime and agent guardrails (Action Gate) | O7: `SOURCE`, `STATE`, `FLOW`, `CONSTRAINT`, `COMPARE`, `DISSIPATE`, `CAPABILITY` | Action Gate methodology and threat mitigation patterns |
| **[Deep-Seek--engineering-os-core-](https://github.com/a50kv109/Deep-Seek--engineering-os-core-)** | Engineering Operating System (E-OS, ISA, EIR, EEL, Runtime) | System execution layers, instruction architectures | Execution substrate (decoupled from verification kernel) |

---

## 2. Cross-Repository Differences & Primitive Analysis

### 2.1 Primitive Evolution & Divergence
1. **SOL-Engineering-Core** defines the classical triad (`SOURCE`, `CONSTRAINT`, `DISSIPATE`) augmented by `COMPARE` as a relational operator for formal parity checks and SPC:2.0 validation.
2. **SOL-2-sol-for-agents** expands the ontology to a 7-element set (**O7**):
   - `SOURCE`: Provenance and authority.
   - `STATE`: Current memory and observed environmental conditions.
   - `FLOW`: Dynamic execution paths and transitions.
   - `CONSTRAINT`: Boundaries, safety envelopes, and invariants.
   - `COMPARE`: Evaluation of candidate actions against goals.
   - `DISSIPATE`: Actuation costs, irreversible side effects, and entropy loss.
   - `CAPABILITY`: Functional affordances and tool APIs.
3. **Deep-Seek--engineering-os-core-** embeds SOL into an operating system structure (ISA / EIR bytecode / EEL execution loops), treating SOL concepts as runtime state-machines and memory buses.

---

## 3. Scope Implemented by SOL-Triad-Engine

To ensure mathematical decidability, strict separation of concerns, and fail-closed security, **SOL-Triad-Engine strictly fixes its verification kernel to the canonical triad**:

$$\text{Triad} = \langle \text{SOURCE}, \text{CONSTRAINT}, \text{DISSIPATE} \rangle$$

### Canonical Primitives:
1. **`SOURCE` (S):**
   - Epistemic origin and record grounding (`evidence_id`, `payload_hash`).
   - Authority domains (`authority_domain`).
   - Granted object scope (`granted_scope`).
   - Granted loss domains (`granted_loss_domains`).
   - Epistemic status (`FACT`, `INFERENCE`, `UNKNOWN`).
   - Temporal anchoring (`timestamp_sec`, `max_age_sec`).
   - Corroborating dependencies for inferences (`corroborating_evidence_ids`).

2. **`CONSTRAINT` (C):**
   - Domain bounds (`domain_scope`).
   - Target objects (`target_objects`).
   - Invariant protected set (`protected_set`).
   - Invariant protected values (`protected_values`).
   - Physical min and max bounds (`min_bounds`, `max_bounds`).
   - Dimensional typing (`units`).
   - Flag invariants (`protected_flags`, `forbidden_flags`, `required_flags`).

3. **`DISSIPATE` (D):**
   - Actualized loss domains (`loss_domain`).
   - Target states (`target_states`).
   - Declared side effects (`side_effects`).
   - State mutations (`state_delta`).
   - Resource costs (`resource_cost`).
   - Flag mutations (`flag_delta`).
   - Dimensional typing (`units`).

---

## 4. O7 vs S-C-D Primitive Semantic Mapping & Identified Gaps

The 7 primitives of the **O7 ontology** (`SOL-2-sol-for-agents`) relate to the **Triad Engine** structures as follows:

| O7 Primitive | Triad Implementation | Semantic Scope in Kernel | Verified Semantic Gaps & Absent Features | Status |
|---|---|---|---|:---:|
| **`SOURCE`** | `SourcePrimitive` + `EvidenceRecord` | Epistemic provenance, authority domain, granted scope, temporal freshness, payload hash. | Asymmetric signatures (Ed25519) and multi-hop inference graphs not verified in v0.4.0 kernel. | **CONFIRMED_IN_CODE** |
| **`STATE`** | `SystemState` ($S_0$) | Environmental snapshot (`current_values`, `active_flags`, `units`) used to simulate $S' = S_0 + \Delta - \text{Cost}$. | Passive input only. `SystemState` CANNOT initiate actions, propose mutations, or evaluate context. | **CONFIRMED_IN_CODE** |
| **`FLOW`** | Encoded as `state_delta`, `flag_delta`, `resource_cost` in `DissipatePrimitive` | Static discrete delta transitions and single-step resource expenditures. | **NO dynamic execution paths**, branching conditions, sequence step loops, or rollback vectors in kernel. | **CONFIRMED_GAP** |
| **`CONSTRAINT`**| `ConstraintPrimitive` | Protected sets, protected scalar values, numerical min/max bounds, dimensional units, flag requirements. | Natural language ethical rules, policy directives, and multi-variable non-linear envelopes absent. | **CONFIRMED_IN_CODE** |
| **`COMPARE`** | Pairwise Coherence Engine ($P_{SC}, P_{CD}, P_{SD}$) | Deterministic boolean and dimensional set containment and boundary inequality checks. | **NO goal comparison**, utility function optimization, or reward evaluation. Coherence $\ne$ Goal alignment. | **CONFIRMED_GAP** |
| **`DISSIPATE`** | `DissipatePrimitive` | Authorized loss domains, side effects, and non-negative resource costs. | Non-physical information entropy and subjective social loss domains require domain adapters. | **CONFIRMED_IN_CODE** |
| **`CAPABILITY`** | Passive set-containment in `SOURCE.granted_scope` and `granted_loss_domains` | Agent operations are bounded by permitted object and domain sets. | **NO tool API execution**, RPC dispatch, or capability negotiation in kernel. Handled by host orchestrators. | **CONFIRMED_GAP** |

### Proposed Translation Layer (PROPOSED / ISOLATED):
A typed mapping layer is implemented in `sol_triad/o7_mapping.py` (`map_o7_to_triad(O7Bundle) -> O7MappingResult`).

* **Status**: **PROPOSED / ISOLATED**. It is **not** connected to the public JSON adapter ingress (`SolTriadJsonAdapter`) or the core execution pipeline of `SolTriadEngine`.
* **Full Audit Report**: Detailed audit findings, verification results, and mapping rules are documented in [`docs/O7_MAPPING_AUDIT.md`](O7_MAPPING_AUDIT.md).
* **The `O7MappingResult` Execution Contract**:
  - `is_valid: bool`: Indicates whether structural validation (non-empty ID, authority domain present, valid types) and strict physical unit resolution passed.
  - `is_executable: bool`: Evaluated strictly as `is_valid and len(unrepresented_fields) == 0 and len(ambiguities) == 0`. Default is `False` whenever any information loss occurs.
  - Fail-closed execution gate (`get_engine_inputs(allow_unrepresented: bool = False)`):
    1. If `is_valid=False`, **always** raises `ValueError` (cannot be bypassed by any flag).
    2. If `ambiguities` is non-empty, **always** raises `ValueError`.
    3. If `is_executable=False` and `allow_unrepresented=False`, raises `ValueError`.
    4. **Critical Policy Invariant**: `allow_unrepresented=True` is **strictly an explicit override for a human-verified/policy-reviewed case**; it is **never** a standard or automatic permission for automated execution.
* **Fields Unrepresented in Canonical S-C-D**:
  - `O7Source`: `creator_signature` (no asymmetric key verification in kernel), `provenance_chain` (requires graph oracle).
  - `O7State`: `memory_context` (unstructured LLM memory), `observer_id`.
  - `O7Flow`: `sequence_step != 1` (kernel evaluates single transitions only), `branch_conditions`, `rollback_vector`.
  - `O7Constraint`: `policy_rules` (natural language ethical/policy directives).
  - `O7Compare`: `tolerance_thresholds`, `goal_utility_function`, `expected_gain`.
  - `O7Dissipate`: `entropy_delta` (thermodynamic entropy deltas are unmodeled; captured whenever specified, even if `0.0`).
  - `O7Capability`: tool invocation rights and rate limits (kernel has no tool execution subsystem).
* **Critical Dimensional Limitation**: String compatibility of units (e.g., via `UnitRegistry.are_compatible()`) proves dimensional consistency, but **does not by itself prove semantic correctness of a unit for a specific domain variable** (e.g., assigning a pressure unit to an electrical sensor).
* **Automated Test Coverage**: Verified by 25 dedicated semantic tests in `tests/test_o7_triad_semantics.py` (75 passing tests across the entire repository).


---

## 5. Pairwise Verification Topology

The verification kernel proves coherence along three orthogonal projections:

```
                  SOURCE (S)
                  /        \
          P_SC   /          \   P_SD
                /            \
               v              v
      CONSTRAINT (C) <------> DISSIPATE (D)
                      P_CD
```

1. **$P_{SC}$ (Grounding & Authority):**
   - Proves that the evidence justifying the action is verified in an authoritative registry.
   - Proves that `C.domain_scope` $\subseteq$ `S.authority_domain`.
   - Proves that `C.target_objects` $\subseteq$ `S.granted_scope`.
2. **$P_{SD}$ (Loss Authority):**
   - Proves that `D.loss_domain` $\subseteq$ `S.granted_loss_domains`.
   - Prevents an agent from dissipating unauthorized resources or venting entropy into forbidden sinks.
3. **$P_{CD}$ (State Invariant Integrity):**
   - Proves that all mutated parameters ($D_{\text{delta}} \cup D_{\text{cost}} \cup D_{\text{side\_effects}} \cup D_{\text{flags}}$) do not intersect $C_{\text{protected\_set}}$.
   - Simulates terminal state $S' = S_0 + \Delta - \text{Cost}$.
   - Proves $S'$ satisfies $C_{\text{min\_bounds}}$, $C_{\text{max\_bounds}}$, and $C_{\text{protected\_values}}$.
   - Proves that dimensional units between $C$, $D$, and $S_0$ are compatible and applies required SI conversions.

---

## 6. Unresolved Questions & Planned Alignment

1. **Cryptographic Signatures on Evidence:**  
   Currently, evidence records support payload hash comparison (`payload_hash`). Full Ed25519 or ECDSA public-key signature verification will be introduced in an optional cryptographic provider module without altering the primitive schema.
2. **Dynamic Unit Conversions with Dynamic Scales:**  
   The current `UnitRegistry` handles affine transformations ($y = ax + b$). Non-linear conversions (e.g., logarithmic dB, decibels) remain slated for v0.4.
3. **Multi-Agent Cross-Triad Composition:**  
   Formalizing algebraic composition ($S_1 \circ S_2$, $D_1 \oplus D_2$) for multi-agent chains will be investigated in conjunction with ACP-Core adapters.
