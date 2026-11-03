# Data Model Specification — SOL-Triad Engine v0.3.2

## 1. Overview
This document specifies the canonical typed data structures and contracts defined in `sol_triad.models`.

---

## 2. Core Primitives

### 2.1 `SourcePrimitive`
```python
@dataclass
class SourcePrimitive:
    evidence_id: str
    authority_domain: Optional[Set[str]]       # None = Defect; set() = Zero privileges
    granted_scope: Optional[Set[str]]          # None = Defect; set() = Zero privileges
    granted_loss_domains: Optional[Set[str]]   # None = Defect; set() = Zero privileges
    epistemic_type: EpistemicStatus            # FACT | INFERENCE | UNKNOWN
    timestamp_sec: float                       # UNIX timestamp (seconds)
    max_age_sec: float = 300.0                 # Maximum freshness window
    corroborating_evidence_ids: Set[str] = field(default_factory=set)
    payload_hash: Optional[str] = None         # Optional SHA-256 payload digest
```

### 2.2 `ConstraintPrimitive`
```python
@dataclass
class ConstraintPrimitive:
    domain_scope: Set[str]                     # Operational domain of the constraint
    target_objects: Set[str]                   # Objects subject to this constraint
    protected_set: Set[str]                    # Variables forbidden from any mutation
    protected_values: Dict[str, float]         # Invariant constants that must equal simulated final state
    max_bounds: Dict[str, float]               # Upper numeric bounds
    min_bounds: Dict[str, float]               # Lower numeric bounds
    units: Dict[str, str]                      # Physical units (e.g. {"pressure": "bar"})
    protected_flags: Set[str]                  # Boolean flags forbidden from changing state
    forbidden_flags: Dict[str, bool]           # Flag name -> forbidden boolean value in final state
    required_flags: Dict[str, bool]            # Flag name -> required boolean value in final state
```

### 2.3 `DissipatePrimitive`
```python
@dataclass
class DissipatePrimitive:
    loss_domain: Set[str]                      # Domain where entropy / resource loss occurs
    target_states: Set[str]                    # Intended qualitative states achieved
    side_effects: Set[str]                     # Named collateral state parameters affected
    resource_cost: Dict[str, float]            # Subtracted resources (must be >= 0.0)
    state_delta: Dict[str, float]              # Additive deltas applied to SystemState
    flag_delta: Dict[str, bool]                # Flag state transitions applied
    units: Dict[str, str]                      # Physical units for deltas and resource costs
```

---

## 3. Environment & Evaluation Models

### 3.1 `SystemState`
```python
@dataclass
class SystemState:
    current_values: Dict[str, float]           # Observed numerical values
    active_flags: Dict[str, bool]              # Observed boolean flags
    units: Dict[str, str]                      # Declared units for current_values
```

### 3.2 `EvidenceRecord`
```python
@dataclass
class EvidenceRecord:
    evidence_id: str
    domain: str
    epistemic_status: EpistemicStatus
    timestamp_sec: float
    payload_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3.3 `EvaluationReport`
```python
@dataclass
class EvaluationReport:
    verdict: CoherenceVerdict                  # PASS | REVIEW | FAIL
    engine_version: str                        # e.g. "0.3.1"
    pairwise_checks: Dict[str, PairwiseEvaluation]  # P_SC, P_CD, P_SD
    diagnostics: List[CoherenceDiagnostic]
    simulated_values: Dict[str, float]
    simulated_flags: Dict[str, bool]
    timestamp_sec: float
```
