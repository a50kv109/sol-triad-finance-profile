# AI Agent Integration Architecture — SOL-Triad Engine v0.4.0

## 1. Overview & Architectural Role

The **SOL-Triad Engine** is an independent, non-executing verification kernel. It is not an LLM agent, not a prompt orchestration framework, and not an autonomous runtime.

Instead, SOL serves as an **External Structural Verification Layer (Action Gate)** for AI agents:
- The AI Agent generates thoughts, plans, and candidate tool calls.
- Before those actions touch actuators, APIs, or databases, the candidate plan is translated into the canonical triad ($\mathbf{S}, \mathbf{C}, \mathbf{D}$).
- The **SOL-Triad Engine** evaluates the plan against epistemic ground truth, scope bounds, and state invariants.
- An **External Execution Controller** enforces the resulting verdict: allowing execution (`PASS`), halting for human confirmation or telemetry refresh (`REVIEW`), or completely blocking execution (`FAIL`).

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

| Mode | Description | Status in v0.4.0 | Capabilities |
| :--- | :--- | :--- | :--- |
| **A. Python SDK** | Direct in-process import of `sol_triad` classes (`SolTriadEngine`, `SourcePrimitive`, etc.) | **Implemented** | Any Python agent can instantiate and run evaluations directly in-process. |
| **B. JSON Interface** | Standardized JSON contract via `SolTriadJsonAdapter` and JSON Schemas | **Implemented** | Polyglot agents can serialize requests to JSON and receive standardized JSON reports. |
| **C. REST API** | Remote HTTP microservice (`POST /api/v1/evaluate`) for network-separated agent runtimes | **Planned (v0.5.0)** | Requires host developer to wrap Python SDK in FastAPI/Flask if network transport is needed. |
| **D. MCP Server** | Model Context Protocol server exposing `sol_evaluate_triad` as an agent tool | **Planned (v0.5.0)** | Direct zero-code tool invocation by Claude/Gemini/OpenAI apps via desktop/CLI MCP. |
| **E. Agent Action Gate** | Middleware policy enforcement pattern | **Demonstrated Pattern** | Verified pattern in `examples/agent_integration_demo.py` with external `ExecutionController`. |

---

## 4. Practical Implementation: Step-by-Step Code Example

Below is the complete, working code illustrating how a third-party developer integrates `SOL-Triad-Engine v0.4.0` into an autonomous agent pipeline:

```python
import sys
import os
from sol_triad import (
    SolTriadJsonAdapter,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
)

# 1. Host System sets up the Authoritative Evidence Registry
# (Populated by trusted hardware/sensors, NEVER directly by the AI agent)
registry = InMemoryEvidenceRegistry()
registry.register(EvidenceRecord(
    evidence_id="sensor-coolant-temp-01",
    domain="thermal_management",
    status=EpistemicStatus.FACT,
    created_at=1740000000.0,
    max_age_sec=60.0,
    data={"temperature_celsius": 84.5}
))

# 2. Instantiate the Adapter (Bridges JSON to Engine models)
adapter = SolTriadJsonAdapter(evidence_registry=registry)

# 3. External AI Agent produces a candidate action request (JSON dict)
agent_proposed_plan = {
    "request_id": "agent-action-cycle-42",
    "protocol_version": "0.4.0",
    "engine_version": "0.4.0",
    "source": {
        "evidence_id": "sensor-coolant-temp-01",
        "authority_domain": ["thermal_management"],
        "granted_scope": ["pump_alpha"],
        "granted_loss_domains": ["electrical_power"],
        "epistemic_type": "FACT",
        "timestamp_sec": 1740000010.0,
        "max_age_sec": 60.0
    },
    "constraint": {
        "domain_scope": ["thermal_management"],
        "target_objects": ["pump_alpha"],
        "protected_set": ["emergency_isolation_valve"],
        "max_bounds": {"coolant_flow_rate": 50.0},
        "min_bounds": {"coolant_flow_rate": 0.0},
        "units": {"coolant_flow_rate": "L/min"}
    },
    "dissipate": {
        "loss_domain": ["electrical_power"],
        "target_states": ["coolant_circulating"],
        "side_effects": [],
        "resource_cost": {"electrical_energy": 2.5},
        "state_delta": {"coolant_flow_rate": 15.0},
        "units": {"coolant_flow_rate": "L/min", "electrical_energy": "kWh"}
    },
    "initial_state": {
        "current_values": {"coolant_flow_rate": 20.0},
        "active_flags": {"system_nominal": True, "emergency_isolation_valve": True},
        "units": {"coolant_flow_rate": "L/min"}
    }
}

# 4. Engine evaluates the Triad deterministically
response = adapter.evaluate_json(agent_proposed_plan)
verdict = response["verdict"]

# 5. External Execution Controller (Host Application Gate)
class ExternalExecutionController:
    def dispatch(self, verdict: str, response: dict):
        if verdict == "PASS":
            print("[CONTROLLER] Approved: Dispatching actuation commands.")
            # Execute hardware command here
        elif verdict == "REVIEW":
            print("[CONTROLLER] Held for Review: Sensor data stale or unverified.")
            # Request operator confirmation or refresh telemetry
        elif verdict == "FAIL":
            print(f"[CONTROLLER] Blocked: Violation detected. Diagnostics: {response['diagnostics']}")
            # Feed diagnostics back to agent for replanning

controller = ExternalExecutionController()
controller.dispatch(verdict, response)
```

---

## 5. The JSON Interface Contract Specification

### 5.1 Mandatory Fields
In `schemas/sol_triad_request.schema.json`:
- `request_id` (string): Unique identifier for audit correlation.
- `protocol_version` (string): Must match `"0.4.0"`.
- `source` (object):
  - `evidence_id` (string): Key matching an authoritative record.
  - `authority_domain` (list[str]): Declared domains of authority.
  - `granted_scope` (list[str]): Objects permitted to be targeted.
  - `granted_loss_domains` (list[str]): Resource/loss categories permitted to be dissipated.
- `constraint` (object):
  - `domain_scope` (list[str]): Operational domain (must be subset of `authority_domain`).
  - `target_objects` (list[str]): Specific systems affected (must be subset of `granted_scope`).
- `dissipate` (object):
  - `loss_domain` (list[str]): Domains of loss/expenditure (must be subset of `granted_loss_domains`).
  - `resource_cost` (dict[str, float]): Non-negative costs deducted from state.
- `initial_state` (object):
  - `current_values` (dict[str, float]): Starting numerical variables.

### 5.2 Pairwise Verification Projections
The response object includes detailed diagnostic records for each projection:
- **`P_SC` (Grounding & Authority):** Confirms evidence exists in the registry, within freshness window, hash matches, and that $C.\text{domain\_scope} \subseteq S.\text{authority\_domain}$ and $C.\text{target\_objects} \subseteq S.\text{granted\_scope}$.
- **`P_SD` (Loss Domain Containment):** Proves $D.\text{loss\_domain} \subseteq S.\text{granted\_loss\_domains}$.
- **`P_CD` (Invariant Preservation):** Simulates terminal values ($S' = S_0 + \Delta - \text{Cost}$) and proves zero mutation of protected parameters, respects numerical bounds, and checks dimensional unit validity.

### 5.3 Error Handling & Diagnostics
If structural flaws, schema violations, or invalid numbers (`NaN`, `Inf`) are passed:
- The adapter does not crash; it catches schema/data errors and returns a fail-closed response with `verdict: "FAIL"` and descriptive error messages in `diagnostics`.
- Severe violations (e.g. attempting to mutate protected parameters) produce `STATE_PROTECTED_PARAM_MUTATED` diagnostics.

---

## 6. Security & Trust Boundaries

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
