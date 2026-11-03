# Architecture Specification — SOL-Triad Engine v0.4.0

## 1. System Mission
The **SOL-Triad Engine** is an independent, deterministic verification kernel designed to evaluate proposed actions against foundational structural, epistemic, and invariant constraints.

Unlike conventional heuristic guardrails or LLM-as-a-judge approaches, the SOL-Triad Engine operates strictly on:
- Set theory (containment, intersection, disjointness).
- Propositional logic and fail-closed security invariants.
- Deterministic numerical simulation and physical dimensionality algebra.
- Explicit epistemic verification against external authoritative ground truth.

---

## 2. Component Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          SOL-Triad Engine v0.4.0                       │
│                                                                        │
│   ┌───────────────────┐    ┌───────────────────┐   ┌─────────────────┐ │
│   │ EvidenceValidator │    │  ScopeValidator   │   │ StateValidator  │ │
│   │  (P_SC Grounding) │    │(P_SC/P_SD Scope)  │   │(P_CD Invariants)│ │
│   └─────────┬─────────┘    └─────────┬─────────┘   └────────┬────────┘ │
│             │                        │                      │          │
│             │       ┌────────────────┴────────────────┐     │          │
│             └──────►│        Decision Arbiter         │◄────┘          │
│                     │  (PASS / REVIEW / FAIL Logic)   │                │
│                     └────────────────┬────────────────┘                │
│                                      │                                 │
│                                      ▼                                 │
│                              EvaluationReport                          │
└──────────────────────────────────────┼─────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        Authoritative Registry                      Unit Registry
        (EvidenceRegistryOracle)               (Physical Dimensions)
```

### 2.1 The Validators
1. **EvidenceValidator (`sol_triad.validators`):**
   - Validates the epistemic integrity of the `SOURCE` primitive.
   - Enforces time grounding: rejects future timestamps, detects stale evidence (`age > max_age_sec`).
   - Looks up ground-truth records in `EvidenceRegistryOracle`.
   - Reconciles claimed epistemic status (`FACT`, `INFERENCE`, `UNKNOWN`).
   - For `INFERENCE`: requires corroborating evidence IDs, validates each in the registry, enforces valid premise statuses (`FACT`, `INFERENCE`), checks premise domain authority and freshness, and rejects circular self-dependencies.
   - Verifies cryptographic payload hashes fail-closed (rejects asymmetric absence and digests mismatch).

2. **ScopeValidator (`sol_triad.validators`):**
   - Differentiates between **structural defects** (`None` fields) and **zero privileges** (empty sets `set()`).
   - Enforces domain confinement: `C.domain_scope ⊆ S.authority_domain`.
   - Enforces target object authorization: `C.target_objects ⊆ S.granted_scope`.
   - Enforces loss domain authorization: `D.loss_domain ⊆ S.granted_loss_domains`.

3. **StateValidator (`sol_triad.validators`):**
   - Prevents numerical exploits: rejects `NaN`, `±Inf`.
   - Validates resource costs: enforces non-negative costs (`cost >= 0`).
   - Unifies all mutation vectors:
     $$\text{Mutations} = D_{\text{target\_states}} \cup D_{\text{side\_effects}} \cup \text{dom}(D_{\text{delta}}) \cup \text{dom}(D_{\text{cost}}) \cup \text{dom}(D_{\text{flags}})$$
   - Proves disjointness with protected parameters: $\text{Mutations} \cap C_{\text{protected\_set}} = \emptyset$.
   - Performs dimensional compatibility checks across $C$, $D$, and $S_0$.
   - Simulates terminal state $S' = S_0 + \text{convert}(D_{\text{delta}}) - \text{convert}(D_{\text{cost}})$.
   - Evaluates boolean flag invariants (`protected_flags`, `forbidden_flags`, `required_flags`).
   - Enforces invariant constants (`protected_values`) and range bounds (`min_bounds`, `max_bounds`).

4. **UnitRegistry (`sol_triad.units`):**
   - Normalized physical dimensions: Pressure, Time, Temperature, Ratio, Energy, Mass, Length, Frequency, Rotational Speed.
   - Deterministic linear conversions to base SI units.
   - Strict anti-bypass: missing units or unknown dimensions are rejected with explicit diagnostics.

---

## 3. Decision Arbiter Logic

The engine aggregates diagnostics and verdicts across all three verification branches. The final verdict is computed deterministically:

1. **FAIL:**  
   If any branch reports a structural defect, unauthorized scope, forged or missing evidence, invariant violation, or dimensional mismatch.
2. **REVIEW:**  
   If no branch reported a FAIL, but any branch reported epistemic uncertainty (stale evidence, offline registry for UNKNOWN/ambient claims, uncorroborated inference).  
   *Invariant:* The engine **never silently promotes a REVIEW into a PASS**.
3. **PASS:**  
   If and only if all checks pass strictly.

---

## 4. Agent Integration & Decoupled Verification Layer

In v0.4.0, the engine introduces a decoupled integration architecture for AI Agents:

```
[ AI Agent Planner ] ──► [ SOL Adapter ] ──► [ SOL-Triad Engine ] ──► [ Execution Controller ]
   (Generates plan)      (JSON Schema)        (PASS / REVIEW / FAIL)    (Enforces verdict)
```

The engine provides:
- Machine-readable JSON request schema (`schemas/sol_triad_request.schema.json`).
- Machine-readable JSON response schema (`schemas/sol_triad_response.schema.json`).
- `SolTriadJsonAdapter` for polyglot agent runtimes.
- Clear trust boundaries separating agent planning from verification and execution control.

---

## 5. Host Integration Topology & Non-Interference Guarantees

The SOL-Triad Engine operates strictly out-of-band relative to the agent's internal reasoning loop:

```
HOST APPLICATION ARCHITECTURE
┌────────────────────────────────────────────────────────┐
│  AI Agent Core (Planner / ReAct / LLM Tool Caller)     │
└───────────────────────────┬────────────────────────────┘
                            │ Proposes Action Candidate
                            ▼
┌────────────────────────────────────────────────────────┐
│  SOL Interceptor / Gate Middleware                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ SolTriadJsonAdapter (Request Schema Validation)  │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │ Calls Engine               │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │ SOL-Triad Engine v0.4.0 (P_SC, P_CD, P_SD)       │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │ Emits Response JSON        │
│                           ▼                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Host Execution Controller (Enforcement Gate)     │  │
│  │  - PASS   -> Dispatches to Environment Actuator  │  │
│  │  - REVIEW -> Pauses for Operator / Re-telemetry  │  │
│  │  - FAIL   -> Blocks and informs Agent to Replan  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Guarantees:
1. **Zero Side-Effects:** Evaluating a triad mutates no global state, touches no network endpoints, and performs no disk I/O.
2. **Determinism:** Given the same inputs and clock timestamp, the evaluation produces identical outputs every time.
3. **Fail-Closed:** Any unhandled exception, syntax failure, or structural anomaly immediately yields `verdict: "FAIL"` with diagnostic explanations.

