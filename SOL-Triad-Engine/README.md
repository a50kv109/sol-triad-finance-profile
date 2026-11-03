# SOL-Triad-Engine v0.4.0
**Universal Structural Coherence Verification Kernel & Agent Integration Layer**

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Verification Status](https://img.shields.io/badge/verification-deterministic-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen.svg)]()

---

## 1. Purpose & Intended Use

The **SOL-Triad Engine** is an independent, standalone structural verification mechanism designed to be attached to external software systems, cyber-physical infrastructure, and autonomous AI agents.

### Core Mission
The engine accepts a formalized description of an object, system state, decision, or proposed action and evaluates its structural coherence using the canonical triad:
- **`SOURCE`** — Foundations, authoritative origins, actors, credentials, and epistemic evidence.
- **`CONSTRAINT`** — Invariants, operational boundaries, permission scopes, and dimensional requirements.
- **`DISSIPATE`** — Resource expenditures, state deltas, side effects, and entropy consequences.

### Deterministic Outcomes
- **`PASS`** — Formalized conditions, epistemic groundings, scope boundaries, and state invariants are satisfied.
- **`REVIEW`** — Required evidence is absent, expired, unverified, or ambiguous; execution must halt until an external arbiter (human supervisor or fresh sensor reading) confirms validity. The engine *never* silently promotes `REVIEW` to `PASS`.
- **`FAIL`** — A direct violation of conditions, invariants, authority, or bounds has been detected. The proposed action must be blocked.

### Key Architectural Properties
1. **Not an AI Agent:** The engine is a deterministic verification kernel, not an autonomous agent or reasoning planner.
2. **Does Not Replace Agent Reasoning:** It does not synthesize goals or formulate strategies. It evaluates candidate actions submitted to it.
3. **Does Not Execute Actions:** It has no network actuators, shell access, or execution controllers. It returns a verdict; enforcement is strictly the responsibility of the calling host application.
4. **Independent Verification Layer:** It operates as an external gate or middleware attachable to host architectures.
5. **Cross-Domain Structural Procedure:** It applies the same formal verification geometry ($\text{Triad} = \langle S, C, D \rangle$) across physical, computational, and organizational domains.
6. **No Claim to Absolute Truth:** It verifies formal consistency *within the formalized model and evidence registry supplied to it*, without claiming metaphysical or moral truth.
7. **Strict Model Boundedness:** It verifies whether proposed actions satisfy the explicit constraints, authorities, and state transformations declared in the request.

For detailed domain applications, see [`docs/PURPOSE_AND_USE_CASES.md`](docs/PURPOSE_AND_USE_CASES.md).

---

## 2. Seven Universal Application Domains

SOL provides a universal structural-causal vocabulary across seven core domains (see [`docs/PURPOSE_AND_USE_CASES.md`](docs/PURPOSE_AND_USE_CASES.md) for full breakdown):

| Domain | What the Engine Verifies | Status in v0.4.0 |
|---|---|---|
| **1. Engineering Systems** | Telemetry freshness, physical unit consistency, resource limits, safety interlocks | **Demonstrated & Verified** (`examples/basic_pass.py`) |
| **2. Software Systems** | State transitions, protected configuration keys, forbidden mutation vectors | **Demonstrated & Verified** (`tests/unit/test_state_validator.py`) |
| **3. AI Agents** | Action gate checks, tool call parameter boundaries, prompt-injection containment | **Demonstrated & Verified** (`examples/agent_integration_demo.py`) |
| **4. Math / Geometric** | Numerical interval constraints, bounds preservation, `NaN`/`Inf` rejection | **Partial (Sanity checks implemented)** |
| **5. Information Systems** | Cryptographic payload hashes, data provenance, freshness windows | **Demonstrated & Verified** (`tests/adversarial/test_epistemic_evidence_bypass.py`) |
| **6. Organizational / Social** | Formal authorization mandates, delegation scope, committee approval boundaries | **Architectural Specification** (Level II Modeling) |
| **7. Cognitive / Analytic** | Epistemic grounding of inferences, premise validity, anti-circularity | **Demonstrated & Verified** (`sol_triad.validators.EvidenceValidator`) |

---

## 3. Real Agent Integration Readiness Audit

| Integration Mode | Real Status in v0.4.0 | What an External Agent / Developer Can Do |
|---|---|---|
| **Python SDK** | **Fully Implemented** | Direct in-process import (`SolTriadEngine`, `SourcePrimitive`, `SystemState`). Ideal for Python agents. |
| **JSON Adapter** | **Fully Implemented** | Send structured JSON matching `schemas/sol_triad_request.schema.json` to `SolTriadJsonAdapter` and receive `schemas/sol_triad_response.schema.json`. |
| **REST API** | **Planned (v0.5.0)** | No HTTP daemon is bundled in core. Host developers wrap Python SDK/JSON Adapter in their own web service if HTTP is needed. |
| **MCP Server** | **Planned (v0.5.0)** | No native Model Context Protocol binary is bundled yet. Direct zero-code use in Claude/ChatGPT requires an MCP wrapper. |
| **Action Gate** | **Demonstrated Pattern** | Verified in `examples/agent_integration_demo.py` with an external `ExecutionController`. |

For complete answers to integration readiness questions, see [`docs/RELEASE_STATUS.md`](docs/RELEASE_STATUS.md).

---

## 4. The Canonical Triad & Verification Geometry

$$\text{Triad} = \langle \text{SOURCE}, \text{CONSTRAINT}, \text{DISSIPATE} \rangle$$

```
                  SOURCE (S)
                  /        \
          P_SC   /          \   P_SD
                /            \
               v              v
      CONSTRAINT (C) <------> DISSIPATE (D)
                      P_CD
```

- **$P_{SC}$ (Grounding & Authority):** Proves that evidence is registered, unexpired, matching hash digests, and that $C.\text{domain\_scope} \subseteq S.\text{authority\_domain}$ and $C.\text{target\_objects} \subseteq S.\text{granted\_scope}$.
- **$P_{SD}$ (Loss Domain Authority):** Proves that $D.\text{loss\_domain} \subseteq S.\text{granted\_loss\_domains}$.
- **$P_{CD}$ (State Invariant Integrity):** Simulates terminal state $S' = S_0 + \Delta - \text{Cost}$ and proves zero mutation of protected parameters, respects bounds, and verifies dimensional units.

---

## 5. Practical Agent Integration Example

Below is the minimal, working code pattern using the current v0.4.0 API:

```python
from sol_triad import (
    SolTriadJsonAdapter,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
)

# 1. Authoritative Evidence Registry (Managed by host/sensors, NOT the agent)
registry = InMemoryEvidenceRegistry()
registry.register(EvidenceRecord(
    evidence_id="sensor-coolant-temp-01",
    domain="thermal_management",
    status=EpistemicStatus.FACT,
    created_at=1740000000.0,
    max_age_sec=60.0,
    data={"temperature_celsius": 84.5}
))

# 2. Initialize Adapter
adapter = SolTriadJsonAdapter(evidence_registry=registry)

# 3. AI Agent proposes candidate action (JSON request payload)
agent_plan = {
    "request_id": "action-plan-001",
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
        "protected_set": ["emergency_valve"],
        "max_bounds": {"coolant_flow": 50.0},
        "min_bounds": {"coolant_flow": 0.0},
        "units": {"coolant_flow": "L/min"}
    },
    "dissipate": {
        "loss_domain": ["electrical_power"],
        "target_states": ["coolant_circulating"],
        "side_effects": [],
        "resource_cost": {"electrical_energy": 2.5},
        "state_delta": {"coolant_flow": 15.0},
        "units": {"coolant_flow": "L/min", "electrical_energy": "kWh"}
    },
    "initial_state": {
        "current_values": {"coolant_flow": 20.0},
        "active_flags": {"system_nominal": True, "emergency_valve": True},
        "units": {"coolant_flow": "L/min"}
    }
}

# 4. Evaluate Triad
response = adapter.evaluate_json(agent_plan)
verdict = response["verdict"]

# 5. External Execution Controller (Enforces verdict)
if verdict == "PASS":
    print("Action approved. Dispatching actuation commands.")
elif verdict == "REVIEW":
    print("Action held for review. Requires sensor refresh or supervisor sign-off.")
elif verdict == "FAIL":
    print(f"Action blocked! Violations: {response['diagnostics']}")
```

---

## 6. Installation & Testing

```bash
# Clone and install in editable mode
git clone https://github.com/a50kv109/SOL-Triad-Engine.git
cd SOL-Triad-Engine
pip install -e .

# Run the full 73-test verification suite
pytest -q
```

---

## 7. Documentation Index

- [`docs/PURPOSE_AND_USE_CASES.md`](docs/PURPOSE_AND_USE_CASES.md) — Comprehensive purpose, non-goals, and 7 application domains.
- [`docs/RELEASE_STATUS.md`](docs/RELEASE_STATUS.md) — Factual readiness audit and answers to integration questions.
- [`docs/AGENT_INTEGRATION.md`](docs/AGENT_INTEGRATION.md) — Complete agent integration architecture, JSON contract, and controller patterns.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Component architecture and host topology.
- [`docs/UNIVERSAL_STRUCTURAL_APPLICABILITY.md`](docs/UNIVERSAL_STRUCTURAL_APPLICABILITY.md) — Level I (Physical) vs Level II (Semantic/Social) modeling.
- [`docs/VALIDATION_RULES.md`](docs/VALIDATION_RULES.md) — Mathematical verification rules and axioms.
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — Adversarial threat vectors and fail-closed mitigations.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Milestones for v0.5.0 (MCP & REST) and v0.6.0.
