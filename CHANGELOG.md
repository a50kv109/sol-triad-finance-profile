# Pre-SOL Changelog

All notable changes to the `pre_sol` autonomous diagnostics module are documented here.
This project follows a strict empirical verification policy: changes are recorded with their verifying tests and actual test execution outputs.

> **Environment Note:** This workspace operates in a containerized environment without an initialized `.git` repository (`fatal: not a git repository`). No synthetic commit hashes, git branches, or timestamps are fabricated. Version tags represent verified test baselines.

---

## [v0.1-exp] — Round 5: Temperature Delta Conversion Fix (convert_delta) & Resource Cost Invariant (2026-11-02)

### Fixed
- **Temperature Delta Conversion in State Simulation (`sol_triad/units.py`, `sol_triad/validators.py`):**
  - Added `UnitRegistry.convert_delta(value, from_unit, to_unit)` for additive and subtractive difference conversions without applying affine offsets ($y = x \cdot m_{\text{from}} / m_{\text{to}}$).
  - Updated `StateValidator` to route `d.state_delta` (additive transitions) and `d.resource_cost` (subtracted expenditures) through `convert_delta()`.
  - Preserved standard `UnitRegistry.convert()` for absolute invariants and bounds (`protected_values`, `min_bounds`, `max_bounds`).
- **Dissipate Primitive Semantics (`sol_triad/models.py`):**
  - Clarified and documented that `DissipatePrimitive.resource_cost` represents subtracted delta expenditures, converting via `convert_delta()` rather than affine `convert()`.
- **Contract & Schema Invariance:**
  - Internal algorithmic fix: does NOT modify JSON schemas (`schemas/sol_triad_request.schema.json`, `schemas/sol_triad_response.schema.json`), wire formats, or public API signatures.

### Added Tests
- Added unit tests in `tests/unit/test_units.py` (12 tests) for `convert_delta` across temperature (Celsius, Kelvin, Fahrenheit) and non-temperature dimensions, verifying zero offset distortion.
- Added unit tests in `tests/unit/test_state_validator.py` (12 tests) for delta addition, resource cost subtraction, and absolute bounds checking under cross-unit conditions.
- Added `test_26_temperature_delta_and_resource_cost_conversions` in `tests/test_o7_triad_semantics.py` verifying end-to-end engine coherence with temperature deltas and costs.

### Verification
- **Test Runner:** Tests executed strictly using Python's standard `unittest` framework. Note: `pytest` is not installed in this execution container (`sh: 1: pytest: not found`).
- `python3 -m unittest discover -s tests -p "test_*.py"`: **76 tests passing (100% OK, 0.054s)**.
  - `tests/test_adapter_security.py`: 7 tests passing.
  - `tests/test_hash_chain.py`: 11 tests passing.
  - `tests/test_o7_triad_semantics.py`: 26 tests passing.
  - `tests/test_pre_sol.py`: 32 tests passing.
- `python3 -m unittest tests/unit/test_units.py tests/unit/test_state_validator.py`: **24 tests passing (100% OK, 0.001s)**.
  - `tests/unit/test_units.py`: 12 tests passing.
  - `tests/unit/test_state_validator.py`: 12 tests passing.
- **Combined Test Total:** **100 verified tests passing (100% OK)**.

---

## [v0.1-exp] — Round 4: Diagnostic Hash Chain (belov-fiber-sdk) & Fail-Closed Adapter Bridge (2026-11-01)

### Added
- **Diagnostic Hash Chain (`pre_sol/hash_chain.py`):**
  - Implemented `DiagnosticBlock` and `DiagnosticHashChain` inspired by `belov-fiber-sdk` distributed log verification.
  - Deterministic canonical serialization (`sort_keys=True`, compact separators) and SHA-256 block hashing over `(index, timestamp, step_name, prev_hash, canonical_payload)`.
  - Sequential linking from genesis (`"0" * 64`) to `head_hash`.
  - Full audit trail export/import and tamper detection (`verify_integrity()`) catching payload mutations, forged timestamps, deleted blocks, and index desynchronizations.
- **Fail-Closed Adapter Bridge (`pre_sol/adapter_bridge.py`):**
  - Implemented `PreSolTriadBridge` governing the contract between Pre-SOL Task Framing and `SolTriadJsonAdapter`.
  - **Anti-Self-Minting Invariant:** Explicitly raises `SelfMintingViolationError` if any ungrounded claim carries synthetic or mock `evidence_id`.
  - **Fail-Closed Mutation Barrier:** Raises `SafetyBarrierViolationError` if mutation is requested without explicit external operator authorization.
  - **Evidence Cryptographic Binding:** `create_diagnostic_evidence_record()` binds Pre-SOL `audit_trail_hash` as `payload_hash` in an authoritative `EvidenceRecord`.
  - **Validated Request Generator:** `build_verification_request()` compiles a valid JSON payload matching `sol_triad_request.schema.json`.
- **Pre-SOL Engine Integration (`pre_sol/engine.py` & `pre_sol/models.py`):**
  - Updated `PreSolEngine.analyze()` to seal each diagnostic step into the hash chain:
    - Block 0: `TSK_STEP_1_RAW_QUERY_INGEST` (preserves raw query SHA-256 and byte length).
    - Block 1: `TSK_STEP_3_STATEMENT_EXTRACTION` (preserves extracted statements and grounding sources).
    - Block 2: `TSK_STEP_4_CONTRADICTION_ANALYSIS` (preserves diagnostic findings and severity).
    - Block 3: `TSK_STEP_5_6_READINESS_AND_BARRIER_EVALUATION` (preserves readiness states and barrier engagement).
    - Block 4: `TSK_STEP_7_CLARIFICATION_DISPATCH` (preserves clarification questions and provisional flags).
  - Added `audit_trail` and `audit_trail_hash` fields and `verify_audit_trail()` verification method to `TaskFramingReport`.
- **Hash Chain & Bridge Test Suite (`tests/test_hash_chain.py`):**
  - 11 unit and integration tests covering:
    - `test_01`: Genesis prev_hash invariant and sequential SHA-256 linking.
    - `test_02`: Payload tampering detection and corrupted block indexing.
    - `test_03`: Timestamp tampering detection.
    - `test_04`: Block deletion and desynchronization detection.
    - `test_05`: Deterministic canonical hashing across key orders.
    - `test_06`: Engine automatic generation of verified 5-block TSK chain.
    - `test_07`: Tampered JSON audit trail deserialization rejection.
    - `test_08`: Forged head hash detection.
    - `test_09`: Anti-self-minting rejection in bridge.
    - `test_10`: Fail-closed safety barrier enforcement on mutation commands.
    - `test_11`: End-to-end integration: operator evidence binding -> `InMemoryEvidenceRegistry` -> `SolTriadJsonAdapter.evaluate_json()` -> deterministic `PASS` verdict.

### Verification
- `python3 -m unittest tests/test_pre_sol.py`: **32 tests passing (100% OK, 0.066s)**.
- `python3 -m unittest tests/test_o7_triad_semantics.py`: **9 tests passing (100% OK, 0.002s)**.
- `python3 -m unittest tests/test_hash_chain.py`: **11 tests passing (100% OK, 0.025s)**.
- **Combined Test Suite:** `python3 -m unittest tests/test_pre_sol.py tests/test_o7_triad_semantics.py tests/test_hash_chain.py`: **52 tests passing (100% OK, 0.083s)**.
- Applet compilation (`compile_applet`): **Build succeeded cleanly**.

---

## [v0.1-exp] — Round 3: O7 ↔ S-C-D Semantic Alignment & Pre-SOL Boundary Hardening (2026-11-01)

### Added
- **O7 Mapping Model (`sol_triad/o7_mapping.py`):**
  Implemented typed O7 data classes (`O7Source`, `O7State`, `O7Flow`, `O7Constraint`, `O7Compare`, `O7Dissipate`, `O7Capability`, `O7Bundle`) and non-destructive mapping function `map_o7_to_triad(bundle) -> O7MappingResult`. Enforces zero silent data loss: all unrepresented fields are returned in an explicit audit list. Marked as `PROPOSED`.
- **O7 Semantics Test Suite (`tests/test_o7_triad_semantics.py`):**
  Added 9 automated unit/semantic tests verifying the operational semantics and exact structural gaps of all 7 O7 primitives against the Triad Engine:
  - `test_01`: SOURCE epistemic grounding, authority domain containment, and anti-self-minting.
  - `test_02`: STATE terminal simulation $S' = S_0 + \Delta - \text{Cost}$ and passive environmental input boundary.
  - `test_03`: FLOW static delta transition verification vs dynamic branching gap.
  - `test_04`: CONSTRAINT invariant protection and numeric/flag bound checks.
  - `test_05`: COMPARE pairwise verification ($P_{SC}, P_{CD}, P_{SD}$) vs goal utility evaluation gap.
  - `test_06`: DISSIPATE non-negative costs and loss domain containment.
  - `test_07`: CAPABILITY passive authority bounding vs tool execution API gap.
  - `test_08`: O7 mapping layer audit trail (file modification scenario) verifying zero silent data loss.
  - `test_09`: Epistemic arbiter stability: stale/unknown evidence strictly yields `REVIEW`, never `PASS`.

### Enhanced
- **Pre-SOL Test Suite (`tests/test_pre_sol.py`):**
  Added tests 29 through 32 (total 32 tests, 100% PASS):
  - `test_29`: Epistemic boundary check: ungrounded fact claims yield `NEEDS_CLARIFICATION`, never promoted to `READY` or `PASS`.
  - `test_30`: Data deficiency: action command without explicit constraints triggers `DATA_DEFICIENCY` and blocks formalization.
  - `test_31`: Epistemic isolation: verifies Pre-SOL never synthesizes or injects fake evidence IDs or mock tokens.
  - `test_32`: Qualitative unmeasurable goal prevents promotion to `READY`.
- **Documentation Synchronization:**
  - `docs/SOL_COMPATIBILITY.md`: Synchronized O7 ↔ S-C-D primitive mapping table, highlighting confirmed gaps.
  - `PRE_SOL_EXPERIMENTAL_STATUS.md`: Added interface specification table and comprehensive mapping matrix against the 7 diagnostic questions of TSK (Виногродский), distinguishing code implementation from human/LLM requirements.

### Verification
- `python3 -m unittest tests/test_pre_sol.py -v`: **32 tests passing (100% OK, 0.067s)**.
- `python3 -m unittest tests/test_o7_triad_semantics.py -v`: **9 tests passing (100% OK, 0.002s)**.
- Total test coverage: **41 verified tests passing (100% OK)**.

---

## [v0.1-exp] — Round 2: Boundary Cases & Baseline Hardening (2026-11-01)


### Fixed & Enhanced
- **Imperative Mutation Verb Recognition (`pre_sol/config.py`):**
  Added imperative forms (`удали`, `удаляй`, `выполни`, `выполняй`, `сбрось`, `сбрасывай`, `запусти`, `запускай`, `останови`, `останавливай`) to `PROVISIONAL_MUTATION_VERBS`. Enables accurate recognition of both direct commands and negative prohibitions.
- **Sequential Action Clause Splitting (`pre_sol/classifier.py`):**
  Added split patterns for sequential action connectors (`", а затем "`, `", затем "`, `", после чего "`, `", and then "`). Prevents requests from masking subsequent execution commands behind analytical preambles.
- **Quoted Action Masquerade Protection (`pre_sol/classifier.py`):**
  Added `unquoted_text` evaluation in `_classify_type`. If an action command verb occurs outside quoted content (e.g., `'проанализируй "удали", а затем выполни её'`), the clause is unconditionally classified as `ACTION_COMMAND`, triggering `safety_barrier_state = ENGAGED`.
- **Conditional Action Directive Detection (`pre_sol/classifier.py`):**
  Enhanced conditional clause classification: purely hypothetical scenarios (`"Если p < 1 bar, оценить последствия"`) remain `HYPOTHESIS`, while conditional action directives (`"Если p > 10 bar, то выполни сброс"`) trigger `ACTION_COMMAND` and engage the safety barrier.
- **Single-Point Interval Support (`pre_sol/diagnostics.py`):**
  Added `math.isclose` tolerance to boundary checks in `_check_logical_contradictions`. Boundaries that meet exactly at a single point after physical unit conversion (e.g., `p >= 1 bar` and `p <= 100 kPa`, both equal to $100\,000\text{ Pa}$) are recognized as a valid single-point interval $[100000, 100000]\text{ Pa}$ rather than a `LOGICAL_CONTRADICTION`.

### Added Tests
- `tests/test_pre_sol.py`: Added 6 boundary test cases (`test_23` to `test_28`):
  - `test_23_negative_prohibition_not_mutation_command`: Validates `"не удаляй таблицы"` as `CONSTRAINT`, non-mutating, barrier `NOT_APPLICABLE`.
  - `test_24_quoted_command_with_subsequent_action_request`: Validates prompt masquerading detection.
  - `test_25_conditional_scenario_vs_conditional_action_request`: Validates hypothesis vs action in conditional branches.
  - `test_26_unit_conversion_equivalent_bounds_single_point_and_incompatible`: Validates $[1\text{ bar}, 100\text{ kPa}]$ single point pass and incompatible dimension failure.
  - `test_27_circular_reasoning_positive_vs_linear_deduction`: Validates *petitio principii* detection vs linear causal chain.
  - `test_28_exact_raw_query_byte_preservation_utf8`: Validates byte-for-byte SHA256 immutability of multiline Unicode input.

### Verification
- `python3 -m unittest tests/test_pre_sol.py -v`: **28 tests passing (100% OK, ~0.06s)**.

---

## [v0.1-exp] — Round 1: Autonomous Diagnostics Prototype (2026-11-01)

### Added
- **Core Architecture (`pre_sol/`):**
  - `models.py`: Immutable data structures (`Statement`, `PreSolReport`, `DiagnosticIssue`, `UnitInterval`) with strict enums (`StatementType`, `GroundingSource`, `PreSolCode`, `SafetyBarrierState`, `ReadinessStatus`).
  - `classifier.py`: Two-axis classification (`StatementType` x `GroundingSource`) without coupling to external proof systems.
  - `diagnostics.py`: Independent checks for logical contradictions, physical unit consistency, circular reasoning (*petitio principii*), ungrounded fact assertions, and qualitative unmeasurable goals.
  - `engine.py`: Pre-SOL pipeline orchestrator enforcing strict byte-level preservation of `raw_query` in UTF-8.
  - `config.py`: Declarative dictionaries of provisional markers and SI physical unit dimension registry (`pressure`, `time`, `length`, `mass`, `temperature`).

### Added Tests
- `tests/test_pre_sol.py`: Initial test suite of 22 test cases covering:
  - Hypothesis exploration without operator consent barrier.
  - Working assumption tracking.
  - Fact claims without verification.
  - Qualitative goal detection.
  - Dimensional unit verification.
  - Safety barrier guarantees (`ENGAGED` under mutation, never `AUTHORIZED` or `DISENGAGED`).
  - Deserialization tampering rejection (`from_dict` validation).
