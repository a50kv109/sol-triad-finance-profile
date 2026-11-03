# Roadmap — SOL-Triad Engine

## Version 0.4.0 (Current Release)
- [x] Universal Structural Applicability framework documented (Level I Technical vs Level II Philosophical/Social systems).
- [x] Formal Non-Equivalence Axiom: structural isomorphism is not semantic equivalence.
- [x] Machine-readable JSON Request and Response Schemas (`schemas/sol_triad_request.schema.json`, `schemas/sol_triad_response.schema.json`).
- [x] Decoupled `SolTriadJsonAdapter` for polyglot AI Agent Integration.
- [x] Executable AI Agent integration demonstration with External Execution Controller (`examples/agent_integration_demo.py`).
- [x] Comprehensive agent integration test suite (73 passing tests).

---

## Version 0.3.2 (Previous Release)
- [x] Fail-closed cryptographic evidence payload hash integrity validation (`EVIDENCE_HASH_MISSING_IN_REGISTRY`, `EVIDENCE_HASH_REQUIRED_BY_REGISTRY`).
- [x] Strict corroborating premise validation for `INFERENCE` claims (existence, status validity, temporal bounds, freshness, and anti-circular dependency rejection).
- [x] 62 unit, integration, and adversarial regression tests passing 100%.
- [x] Clean standalone distribution package without development artifacts or cache bloat.

---

## Version 0.3.1 (Baseline Release)
- [x] Unified `CoherenceVerdict` (`PASS`, `REVIEW`, `FAIL`) with fail-closed arbiter.
- [x] Strict Unit Registry with dimensional checking and base SI conversions.
- [x] Full simulation of terminal state including `state_delta`, `resource_cost`, and `flag_delta`.
- [x] Invariant constant enforcement (`protected_values`) and flag invariants (`protected_flags`, `forbidden_flags`, `required_flags`).
- [x] Non-negative resource cost validation and numeric sanity (`NaN`, `Inf` rejection).
- [x] Deterministic evaluation with injectable clock.

---

## Version 0.5.0 (Universal Agent Connectivity)
- [ ] **Model Context Protocol (MCP) Server (`sol-triad-mcp`):** Native MCP tool integration allowing Anthropic/Claude, OpenAI, and Gemini desktop/CLI agents to call `sol_verify_action` with zero custom code.
- [ ] **REST API Server (`sol-triad-serve`):** Lightweight OpenAPI/FastAPI service daemon (`POST /api/v1/verify`) for network-isolated microservice environments.
- [ ] **Standard Domain Adapters:** Ready-to-use translation templates for common tool-calling frameworks (LangChain, AutoGen, CrewAI).
- [ ] **Cryptographic Signatures:** Pluggable Ed25519 / ECDSA signature verifiers for `EvidenceRecord`.

---

## Version 0.6.0 (Formal Solvers & Multi-Triad Composition)
- [ ] **Multi-Triad Algebraic Composition:** Chaining multiple sequential or parallel triads ($T_1 \otimes T_2$) with transactional rollback.
- [ ] **Formal Verification Integration:** Integration with Z3 or SMT solvers for automated constraint satisfiability proving across large parameter state spaces.
- [ ] **Real-Time Telemetry Bridge:** Live streaming audit logs to OpenTelemetry collectors.
