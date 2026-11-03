# SOL-Triad-Engine v0.4.0
**Universal Structural Coherence Verification Kernel & Agent Integration Layer**

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Verification Status](https://img.shields.io/badge/verification-deterministic-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-100%20passed%20(unittest)-brightgreen.svg)]()

---

## 1. Overview & Objective

The **SOL-Triad Engine** is an independent, deterministic verification kernel designed to verify whether a proposed action or state transition has:
1. **A verified and epistemically sound source of truth** (`SOURCE`).
2. **Sufficient authority and explicitly bounded target scope** (`CONSTRAINT`).
3. **An authorized and safely bounded dissipation of resources and entropy** (`DISSIPATE`).
4. **Valid state transitions that preserve protected invariants, bounds, and dimensional units**.

Rather than relying on non-deterministic LLM self-evaluations ("LLM-as-a-judge"), the SOL-Triad Engine applies propositional logic, set containment, physical dimensionality algebra, and deterministic terminal state simulation before any external execution takes place.

---

## 2. Universal Structural Applicability

SOL provides a universal structural-causal vocabulary for representing, analyzing, and verifying systems across diverse domains of knowledge:

- **Level I: Physical, Technical, and Computational Systems:**  
  Engineering structures, energy grids, computational state machines, and autonomous software agents where parameters represent concrete physical or numerical variables (pressure, temperature, power, memory locks).
- **Level II: Semantic, Philosophical, Ethical, and Social Systems:**  
  Concepts such as responsibility, justice, fairness, and trust that are not physical scalars, but possess clear preconditions, boundaries, and consequences.

### The Non-Equivalence Axiom
> **Structural isomorphism is NOT semantic equivalence.**

SOL does not reduce ethics to physics or physics to ethics. Physical energy dissipation is not identical to information loss; resource costs are not identical to moral harms; and mathematical invariant preservation does not replace moral inquiry. The engine verifies structural and logical consistency of formalized models, but relies on domain interpretation modules and authoritative registries for real-world grounding.

For full architectural details, see [`docs/UNIVERSAL_STRUCTURAL_APPLICABILITY.md`](docs/UNIVERSAL_STRUCTURAL_APPLICABILITY.md).

---

## 3. The Canonical Triad

The engine is strictly anchored to the canonical triad:
$$\text{Triad} = \langle \text{SOURCE}, \text{CONSTRAINT}, \text{DISSIPATE} \rangle$$

| Primitive | Mathematical Model | Semantic Purpose |
|---|---|---|
| **`SOURCE` (S)** | $\langle \text{id}, \text{auth}, \text{scope}, \text{loss\_auth}, \text{status}, t_0, \Delta t_{\text{max}}, \text{corrob}, \text{hash} \rangle$ | Epistemic grounding, authoritative registry lookup, and granted operational privileges. |
| **`CONSTRAINT` (C)** | $\langle \text{domain}, \text{targets}, \text{protected}, \text{constants}, \text{bounds}, \text{units}, \text{flags} \rangle$ | Operational boundaries, forbidden mutations, physical numerical bounds, and unit types. |
| **`DISSIPATE` (D)** | $\langle \text{loss\_domain}, \text{states}, \text{side\_effects}, \text{cost}, \Delta S, \Delta F, \text{units} \rangle$ | The proposed actuation: state deltas, resource costs, flag transitions, and entropy loss. |

---

## 4. AI Agent Integration Architecture

In version 0.4.0, the engine provides an **Agent Integration Layer** allowing external AI agents (planners, reasoning loops, tool-calling frameworks) to submit candidate actions for verification before execution:

```
TASK / OBSERVATION
        │
        ▼
   AI AGENT PLANNER  (Formulates candidate tool call or intervention)
        │
        ▼
    SOL ADAPTER      (Translates plan to JSON Request Schema)
        │
        ▼
 SOL-TRIAD-ENGINE    (Evaluates P_SC, P_CD, P_SD deterministically)
        │
   [ PASS / REVIEW / FAIL Report ]
        │
        ▼
EXECUTION CONTROLLER (Enforces verdict: dispatch, hold for review, or block)
```

### Integration Modes & Status

| Mode | Description | Status in v0.4.0 |
|---|---|---|
| **Python SDK** | Direct in-process import (`SolTriadEngine`, `SourcePrimitive`) | **Implemented** |
| **JSON Interface** | Standardized JSON contract via `SolTriadJsonAdapter` | **Implemented** |
| **REST API** | Lightweight HTTP service daemon | **Designed / Planned** |
| **MCP Server** | Model Context Protocol tool provider | **Designed / Planned** |
| **Action Gate** | Middleware policy enforcement pattern | **Architectural Pattern** |

See [`docs/AGENT_INTEGRATION.md`](docs/AGENT_INTEGRATION.md) for schemas, security boundaries, and controller gate rules.

---

## 5. Verification Architecture & Pairwise Checks

Evaluation is structured across three orthogonal verification projections:

```
                  SOURCE (S)
                  /        \
          P_SC   /          \   P_SD
                /            \
               v              v
      CONSTRAINT (C) <------> DISSIPATE (D)
                      P_CD
```

- **$P_{SC}$ (Grounding & Authority):** Proves that the evidence justifying the action is authenticated in the registry, within the freshness window, hashes match fail-closed, and that $C.\text{domain\_scope} \subseteq S.\text{authority\_domain}$ and $C.\text{target\_objects} \subseteq S.\text{granted\_scope}$.
- **$P_{SD}$ (Loss Domain Authority):** Proves that $D.\text{loss\_domain} \subseteq S.\text{granted\_loss\_domains}$.
- **$P_{CD}$ (State Invariant Integrity):** Simulates terminal state $S' = S_0 + \text{convert\_delta}(\Delta) - \text{convert\_delta}(\text{Cost})$ and proves that no protected variables or flags are mutated, all bounds ($C_{\text{min}}, C_{\text{max}}$) and invariant targets ($C_{\text{protected\_values}}$) are respected via absolute `convert()`, and dimensional units match. Relative deltas and resource costs use linear scaling without affine offsets, leaving public schemas and API contracts unaltered.

---

## 6. Verdict Semantics

The public API returns a single unified `CoherenceVerdict`:

- **`PASS`**: All required checks passed with grounded evidence and verified invariants.
- **`REVIEW`**: Insufficient evidence, stale observation, uncorroborated inference, or offline registry for ambient claims.  
  *Rule:* **The engine never silently converts `REVIEW` into `PASS`**.
- **`FAIL`**: Structural defect, unauthorized authority/scope, invariant violation, bounds breach, negative resource cost, or dimensional mismatch.

---

## 7. Installation & Quickstart

### Installation
```bash
git clone https://github.com/a50kv109/SOL-Triad-Engine.git
cd SOL-Triad-Engine
pip install -e .
```

### Direct Python SDK Usage
```python
from sol_triad import (
    SourcePrimitive, ConstraintPrimitive, DissipatePrimitive,
    SystemState, EvidenceRecord, EpistemicStatus,
    InMemoryEvidenceRegistry, SolTriadEngine,
)

registry = InMemoryEvidenceRegistry()
registry.register(EvidenceRecord(
    evidence_id="ev-pwr-01",
    domain="power",
    epistemic_status=EpistemicStatus.FACT,
    timestamp_sec=1000.0,
))

engine = SolTriadEngine(registry=registry)
report = engine.evaluate(source, constraint, dissipate, state, evaluation_time=1010.0)
print(f"Verdict: {report.verdict.value}")  # PASS / REVIEW / FAIL
```

### JSON Agent Adapter Usage
```python
from sol_triad import SolTriadJsonAdapter

adapter = SolTriadJsonAdapter(default_registry=registry)
response = adapter.evaluate_json(request_payload_dict_or_str)
print(f"Verdict: {response['verdict']}")
```

---

## 8. Running Tests

The test suite covers unit, integration, adversarial attacks, security bridges, and semantic contracts (**100 tests total** across verified test suites, 100% passing):

> **Environment Note:** Tests are executed using Python's standard `unittest` framework without external dependencies (`pytest` is not installed in the container environment).

```bash
# Run integration, security, and semantic contract tests (76 tests total)
python3 -m unittest discover -s tests -p "test_*.py"

# Run core unit tests for dimensional algebra and state validator simulation (24 tests total)
python3 -m unittest tests/unit/test_units.py tests/unit/test_state_validator.py
```

---

## 9. Directory Structure

```
SOL-Triad-Engine/
├── schemas/
│   ├── sol_triad_request.schema.json   # Machine-readable request schema (v0.4.0)
│   └── sol_triad_response.schema.json  # Machine-readable response schema (v0.4.0)
├── sol_triad/
│   ├── __init__.py                     # Public API exports
│   ├── adapter.py                      # SolTriadJsonAdapter (Agent Integration Layer)
│   ├── engine.py                       # SolTriadEngine coordinator & Decision Arbiter
│   ├── evidence.py                     # EvidenceRegistryOracle & InMemoryEvidenceRegistry
│   ├── models.py                       # Typed dataclasses & CoherenceVerdict enum
│   ├── units.py                        # UnitRegistry & dimensional conversion algebra
│   └── validators.py                   # EvidenceValidator, ScopeValidator, StateValidator
├── tests/
│   ├── unit/                           # Unit tests for models, units, validators, adapter
│   ├── integration/                    # Full pipeline end-to-end tests
│   └── adversarial/                    # Comprehensive attack vectors & bypass tests
├── docs/
│   ├── ARCHITECTURE.md                 # Structural architecture and component flows
│   ├── AGENT_INTEGRATION.md            # Agent integration architecture & security gates
│   ├── UNIVERSAL_STRUCTURAL_APPLICABILITY.md # Level I vs Level II systemic modeling
│   ├── DATA_MODEL.md                   # Data models and attribute schemas
│   ├── VALIDATION_RULES.md             # Formal verification axioms
│   ├── THREAT_MODEL.md                 # Security threat model and mitigations
│   ├── EXPERIMENTS.md                  # Empirical benchmarks & prototype defect audit
│   ├── ROADMAP.md                      # Release roadmap and future milestones
│   └── SOL_COMPATIBILITY.md            # Reference repository alignment & O7 taxonomy
├── examples/
│   ├── basic_pass.py                   # Complete PASS execution example
│   ├── evidence_review.py              # REVIEW scenario example (stale evidence)
│   ├── invariant_fail.py               # FAIL scenario example (protected mutation)
│   └── agent_integration_demo.py       # Complete agent integration with execution controller
├── README.md
├── pyproject.toml
└── LICENSE
```
