# SOL-Triad-Engine v0.4.0 & Pre-SOL v0.1-exp — Distribution Manifest

**Baseline Test Status:** 100/100 passed (100% OK via unittest)  
- `python3 -m unittest discover -s tests -p "test_*.py"`: 76/76 tests passed (7 adapter security + 11 hash chain + 26 semantics + 32 pre-sol)
- `python3 -m unittest tests/unit/test_units.py tests/unit/test_state_validator.py`: 24/24 tests passed (12 units algebra + 12 state validator simulation)

---

## Key Modules

1. **`sol_triad/` (Core Kernel & Adapter):**
   - Deterministic verification engine $\langle S, C, D \rangle$, pairwise projectors ($P_{SC}, P_{SD}, P_{CD}$), unit registry, and `SolTriadJsonAdapter`.
2. **`sol_triad/o7_mapping.py`:**
   - Formal O7 primitive mapping (`O7Source`, `O7State`, `O7Flow`, `O7Constraint`, `O7Compare`, `O7Dissipate`, `O7Capability`, `O7Bundle`) with explicit unrepresented field audits.
3. **`pre_sol/hash_chain.py` (Finding 4 — `belov-fiber-sdk` pattern):**
   - Tamper-evident `DiagnosticHashChain` ensuring raw query, extracted statements, findings, and barrier states are immutably sealed across TSK diagnostic stages.
4. **`pre_sol/adapter_bridge.py`:**
   - Fail-closed bridge enforcing Anti-Self-Minting, safety barrier locking, and cryptographic evidence binding (`payload_hash == audit_trail_hash`) for `SolTriadJsonAdapter`.
5. **`pre_sol/` (Autonomous Diagnostics):**
   - Dual-axis proposition classifier, interval contradiction and *petitio principii* analyzer, and readiness evaluator.
