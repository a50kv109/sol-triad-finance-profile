# AI Agent Integration Architecture — SOL-Triad Engine v0.4.0

## 1. Overview & Architectural Role

The **SOL-Triad Engine** is an independent, non-executing verification kernel. It is not an LLM agent, not a prompt orchestration framework, and not an autonomous runtime.

Instead, SOL serves as an **External Structural Verification Layer (Action Gate)** for AI agents:
- The AI Agent generates thoughts, plans, and candidate tool calls.
- Before those actions touch actuators, APIs, or databases, the candidate plan is translated into the canonical triad ($\mathbf{S}, \mathbf{C}, \mathbf{D}$).
- The **SOL-Triad Engine** evaluates the plan against epistemic ground truth, scope bounds, and state invariants.
- The **External Execution Controller** enforces the resulting verdict: allowing execution (`PASS`), halting for human confirmation or telemetry refresh (`REVIEW`), or completely blocking execution (`FAIL`).

---

## 2. Agent Interaction Lifecycle

```
┌──────────────────────────────────────────────────────────┐
│                   ENVIRONMENT / SENSORS                  │
└────────────────────────────┬─────────────────────────────┘
                             │ Observes state / Receives task
                             ▼
┌──────────────────────────────────────────────────────────┐
│                 AI AGENT (LLM / PLANNER)                 │
│  - Reason over goals and constraints                     │
│  - Synthesize candidate intervention / tool call         │
└────────────────────────────┬─────────────────────────────┘
                             │ Proposed Action Plan
                             ▼
┌──────────────────────────────────────────────────────────┐
│                     SOL ADAPTER                          │
│  - Maps agent plan into canonical triad:                 │
│    * SOURCE (evidence, domains, epistemic status)        │
│    * CONSTRAINT (invariants, protected vars, bounds)     │
│    * DISSIPATE (deltas, resource costs, side effects)    │
└────────────────────────────┬─────────────────────────────┘
                             │ Evaluates Triad Coherence
                             ▼
┌──────────────────────────────────────────────────────────┐
│                 SOL-TRIAD-ENGINE v0.4.0                  │
│  - P_SC: Epistemic grounding & scope authority           │
│  - P_CD: State simulation, bounds & protected sets       │
│  - P_SD: Loss domain containment & side-effect bounds    │
│  - Decision Arbiter (Fail-Closed)                        │
└────────────────────────────┬─────────────────────────────┘
                             │ EvaluationReport (PASS / REVIEW / FAIL)
                             ▼
┌──────────────────────────────────────────────────────────┐
│               EXTERNAL EXECUTION CONTROLLER              │
│  - PASS   ──► Executes action on actuators / systems     │
│  - REVIEW ──► Requests human operator or sensor refresh  │
│  - FAIL   ──► Blocks action; sends diagnostics to agent  │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Integration Modes & Implementation Status

| Mode | Description | Status in v0.4.0 |
| :--- | :--- | :--- |
| **A. Python SDK** | Direct in-process import of `sol_triad` classes (`SolTriadEngine`, `SourcePrimitive`, etc.) | **Implemented** |
| **B. JSON Interface** | Machine-readable JSON request/response contract via `SolTriadJsonAdapter` and JSON Schemas | **Implemented** |
| **C. REST API** | Remote HTTP microservice (`POST /api/v1/evaluate`) for polyglot agent runtimes | **Designed / Planned** |
| **D. MCP Server** | Model Context Protocol server exposing `sol_evaluate_triad` as an agent tool | **Designed / Planned** |
| **E. Agent Action Gate** | Middleware interceptor wrapping LangChain, LlamaIndex, AutoGen, or custom agent loops | **Architectural Pattern** |

> **Important Notice on Status:**  
> In version 0.4.0, Modes A (Python SDK) and B (JSON Interface) are fully implemented and verified by automated tests. Modes C, D, and E are formal architectural specifications designed to use the Mode B JSON contract. An actual MCP server or HTTP daemon has not yet been packaged into this repository.

---

## 4. The JSON Interface Contract (Mode B)

The JSON interface decouples the agent's internal language (Python, TypeScript, Rust, Go) from the verification kernel.

### Request Payload (`schemas/sol_triad_request.schema.json`)
```json
{
  "request_id": "req-cooling-action-9481",
  "protocol_version": "0.4.0",
  "engine_version": "0.4.0",
  "source": {
    "evidence_id": "sensor_reading_core_temp",
    "authority_domain": ["facility_thermal_management"],
    "granted_scope": ["pump_01", "chiller_loop_a"],
    "granted_loss_domains": ["electrical_grid_power"],
    "epistemic_type": "FACT",
    "timestamp_sec": 1740000000.0,
    "max_age_sec": 30.0,
    "payload_hash": "a1b2c3d4..."
  },
  "constraint": {
    "domain_scope": ["facility_thermal_management"],
    "target_objects": ["pump_01"],
    "protected_set": ["emergency_valve_sealed"],
    "max_bounds": { "pump_rpm": 3600.0 },
    "min_bounds": { "pump_rpm": 0.0 },
    "units": { "pump_rpm": "rpm", "power_draw": "kW" },
    "required_flags": { "cooling_loop_active": true }
  },
  "dissipate": {
    "loss_domain": ["electrical_grid_power"],
    "target_states": ["coolant_circulating"],
    "side_effects": ["auxiliary_noise"],
    "resource_cost": { "power_draw": 4.5 },
    "state_delta": { "pump_rpm": 1200.0 },
    "units": { "pump_rpm": "rpm", "power_draw": "kW" }
  },
  "initial_state": {
    "current_values": { "pump_rpm": 1800.0, "power_draw": 10.0 },
    "active_flags": { "cooling_loop_active": true, "emergency_valve_sealed": true },
    "units": { "pump_rpm": "rpm", "power_draw": "kW" }
  }
}
```

### Response Payload (`schemas/sol_triad_response.schema.json`)
```json
{
  "request_id": "req-cooling-action-9481",
  "protocol_version": "0.4.0",
  "engine_version": "0.4.0",
  "verdict": "PASS",
  "pairwise_checks": {
    "P_SC": { "relationship": "P_SC", "is_valid": true, "verdict": "PASS", "diagnostics": [] },
    "P_CD": { "relationship": "P_CD", "is_valid": true, "verdict": "PASS", "diagnostics": [] },
    "P_SD": { "relationship": "P_SD", "is_valid": true, "verdict": "PASS", "diagnostics": [] }
  },
  "diagnostics": [
    { "code": "EVIDENCE_PASS", "severity": "INFO", "message": "Evidence verified." },
    { "code": "SCOPE_PASS", "severity": "INFO", "message": "Scope authorized." },
    { "code": "STATE_PASS", "severity": "INFO", "message": "State simulation invariant checks passed." }
  ],
  "simulated_values": {
    "pump_rpm": 3000.0,
    "power_draw": 5.5
  },
  "simulated_flags": {
    "cooling_loop_active": true,
    "emergency_valve_sealed": true
  },
  "evaluation_timestamp": 1740000005.0,
  "messages": ["[STATE_PASS] State simulation invariant checks passed."]
}
```

---

## 5. Security & Trust Boundaries

When deploying AI agents with the SOL verification layer, systems must enforce six strict security boundaries:

1. **No Self-Certification of Evidence:**  
   The AI agent must **never** be permitted to populate or sign its own entries in the authoritative evidence registry. Evidence records must be written exclusively by trusted sensors, cryptographic hardware, or human authorities.
2. **Registry Trust Boundary:**  
   The engine trusts the registry oracle. If an adversary compromises the registry, the engine cannot detect the fraud unless cryptographic hashes or external signatures fail.
3. **PASS is Necessary, Not Sufficient:**  
   A `PASS` verdict proves that the action satisfies all declared invariants, units, bounds, and authority domains. It does not prove that the action is optimal, intelligent, or free from omissions outside the declared constraint set.
4. **REVIEW is Fail-Closed:**  
   Under no circumstances may an adapter or execution controller automatically downgrade a `REVIEW` into a `PASS`. A `REVIEW` requires either fresh sensor telemetry or explicit operator authorization.
5. **Enforcement Separation:**  
   The SOL engine **does not execute actions** and holds no direct network or hardware actuators. An external execution controller must inspect the verdict before dispatching tool calls.
6. **Immutable Triad:**  
   No integration layer or adapter may add additional canonical primitives or bypass the pairwise evaluation pipeline ($P_{SC}$, $P_{CD}$, $P_{SD}$).
