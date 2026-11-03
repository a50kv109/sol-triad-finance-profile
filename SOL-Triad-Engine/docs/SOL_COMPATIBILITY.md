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

## 4. External Integration Structures

Other concepts from the O7 taxonomy are explicitly accommodated as **inputs or environmental interfaces**, rather than promoted into primitives of the core verification kernel:

* **`STATE` $\rightarrow$ `SystemState`:**
  Modeled as an external observed snapshot (`current_values`, `active_flags`, `units`) provided by the host environment to simulate terminal states. The engine verifies transitions *upon* `SystemState`, but `SystemState` is not a proposing primitive.
* **`COMPARE` $\rightarrow$ Pairwise Coherence Engine:**
  The pairwise verification relationships ($P_{SC}$, $P_{CD}$, $P_{SD}$) and the Decision Arbiter formalize the comparison operator into deterministic boolean and dimensional logic.
* **`FLOW` & `CAPABILITY` $\rightarrow$ Host Agent Architecture:**
  Handled outside the verification kernel by host orchestrators (e.g. AAM, ACP-Core, or E-OS). The engine acts as the gate *before* tool dispatch or flow progression.

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
