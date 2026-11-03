"""Tests for Pre-SOL Cryptographic Hash Chain and Adapter Bridge (Finding 4).

Validates:
1. Immutable block creation and SHA-256 deterministic linking.
2. Tamper-evident log integrity (detection of modified payloads, timestamps, prev_hashes).
3. Serialization & Deserialization of audit trails in TaskFramingReport.
4. PreSolTriadBridge anti-self-minting and fail-closed safety barrier invariants.
5. End-to-end integration with SolTriadJsonAdapter.
"""

import unittest
import json
import time

from pre_sol import (
    PreSolEngine,
    ReadinessStatus,
    SafetyBarrierState,
    StatementType,
    GroundingSource,
    ParsedStatement,
    DiagnosticHashChain,
    DiagnosticBlock,
    ChainIntegrityError,
    PreSolTriadBridge,
    PreSolBridgeError,
    SelfMintingViolationError,
    SafetyBarrierViolationError,
)
from sol_triad import (
    SolTriadJsonAdapter,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
)


class TestPreSolHashChain(unittest.TestCase):
    """Test suite for DiagnosticHashChain and PreSolTriadBridge."""

    def setUp(self):
        self.engine = PreSolEngine()

    def test_01_hash_chain_genesis_and_sequential_linking(self):
        """Invariant: Block 0 has 64 zeros as prev_hash; Block N has Block N-1 hash."""
        chain = DiagnosticHashChain()
        self.assertEqual(chain.head_hash, "0" * 64)
        self.assertEqual(chain.length, 0)

        b0 = chain.append("STEP_0_INIT", {"session_id": "sess-001"}, timestamp=1000.0)
        self.assertEqual(b0.index, 0)
        self.assertEqual(b0.prev_hash, "0" * 64)
        self.assertTrue(len(b0.block_hash) == 64)
        self.assertEqual(chain.head_hash, b0.block_hash)

        b1 = chain.append("STEP_1_OBSERVATION", {"pressure": 5.0}, timestamp=1001.0)
        self.assertEqual(b1.index, 1)
        self.assertEqual(b1.prev_hash, b0.block_hash)
        self.assertEqual(chain.head_hash, b1.block_hash)

        is_valid, bad_idx, err = chain.verify_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(bad_idx)
        self.assertIsNone(err)

    def test_02_detects_payload_tampering(self):
        """Invariant: Any mutation of a past payload invalidates the chain."""
        chain = DiagnosticHashChain()
        chain.append("STEP_1", {"metric": "pressure", "value": 10.0}, timestamp=100.0)
        chain.append("STEP_2", {"action": "check_valve"}, timestamp=101.0)
        chain.append("STEP_3", {"verdict": "normal"}, timestamp=102.0)

        self.assertTrue(chain.verify_integrity()[0])

        # Adversary attempts to retroactively change pressure from 10.0 to 999.0
        chain.blocks[0].payload["value"] = 999.0

        is_valid, bad_idx, err = chain.verify_integrity()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 0)
        self.assertIn("Block hash corrupted", err)

    def test_03_detects_timestamp_tampering(self):
        """Invariant: Retroactive alteration of block timestamp invalidates the chain."""
        chain = DiagnosticHashChain()
        chain.append("STEP_1", {"data": 1}, timestamp=100.0)
        chain.append("STEP_2", {"data": 2}, timestamp=200.0)

        # Alter timestamp of block 1
        chain.blocks[1].timestamp = 150.0

        is_valid, bad_idx, err = chain.verify_integrity()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 1)
        self.assertIn("Block hash corrupted", err)

    def test_04_detects_block_deletion(self):
        """Invariant: Deleting an intermediate block breaks prev_hash and index alignment."""
        chain = DiagnosticHashChain()
        chain.append("STEP_0", {"s": 0}, timestamp=10.0)
        chain.append("STEP_1", {"s": 1}, timestamp=11.0)
        chain.append("STEP_2", {"s": 2}, timestamp=12.0)

        # Remove block 1
        del chain.blocks[1]

        is_valid, bad_idx, err = chain.verify_integrity()
        self.assertFalse(is_valid)
        # Block 2 is now at index 1, index mismatch
        self.assertEqual(bad_idx, 1)
        self.assertIn("Index mismatch", err)

    def test_05_deterministic_canonical_hashing(self):
        """Invariant: Dictionary key order does not affect computed SHA-256 block hash."""
        b_a = DiagnosticBlock(
            index=0,
            timestamp=123.456,
            step_name="CANONICAL_TEST",
            prev_hash="0" * 64,
            payload={"z_alpha": 1, "a_beta": 2, "nested": {"k2": "v2", "k1": "v1"}},
        )
        b_b = DiagnosticBlock(
            index=0,
            timestamp=123.456,
            step_name="CANONICAL_TEST",
            prev_hash="0" * 64,
            payload={"nested": {"k1": "v1", "k2": "v2"}, "a_beta": 2, "z_alpha": 1},
        )
        self.assertEqual(b_a.compute_hash(), b_b.compute_hash())

    def test_06_pre_sol_engine_produces_verified_audit_trail(self):
        """Invariant: PreSolEngine.analyze() automatically generates an intact hash chain."""
        query = "Давление в контуре p <= 10 bar. Температура T <= 300 K. Оценить стабильность."
        report = self.engine.analyze(query)

        self.assertGreater(len(report.audit_trail), 0)
        self.assertTrue(len(report.audit_trail_hash) == 64)

        is_valid, bad_idx, err = report.verify_audit_trail()
        self.assertTrue(is_valid)
        self.assertIsNone(bad_idx)
        self.assertIsNone(err)

        # Check that steps correspond to TSK diagnostic phases
        step_names = [b["step_name"] for b in report.audit_trail]
        self.assertIn("TSK_STEP_1_RAW_QUERY_INGEST", step_names)
        self.assertIn("TSK_STEP_3_STATEMENT_EXTRACTION", step_names)
        self.assertIn("TSK_STEP_4_CONTRADICTION_ANALYSIS", step_names)
        self.assertIn("TSK_STEP_5_6_READINESS_AND_BARRIER_EVALUATION", step_names)
        self.assertIn("TSK_STEP_7_CLARIFICATION_DISPATCH", step_names)

    def test_07_tampered_json_serialization_fails_verification(self):
        """Invariant: Modifying serialized report payload triggers verification failure."""
        query = "Давление p <= 10 bar."
        report = self.engine.analyze(query)
        serialized = report.to_dict()

        # Tamper with block 0 payload in serialized dictionary
        serialized["audit_trail"][0]["payload"]["byte_length"] = 999999

        tampered_report = report.from_dict(serialized)
        is_valid, bad_idx, err = tampered_report.verify_audit_trail()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 0)

    def test_08_tampered_head_hash_fails_verification(self):
        """Invariant: Forging audit_trail_hash triggers explicit mismatch error."""
        query = "Давление p <= 10 bar."
        report = self.engine.analyze(query)
        serialized = report.to_dict()

        # Tamper with the declared audit_trail_hash
        serialized["audit_trail_hash"] = "f" * 64

        tampered_report = report.from_dict(serialized)
        is_valid, bad_idx, err = tampered_report.verify_audit_trail()
        self.assertFalse(is_valid)
        self.assertIn("Audit trail head hash mismatch", err)

    def test_09_anti_self_minting_in_bridge(self):
        """Invariant: Bridge rejects statements carrying fake evidence_id if UNGROUNDED."""
        query = "Давление p <= 10 bar."
        report = self.engine.analyze(query)

        # Inject synthetic evidence_id into ungrounded statement
        fake_stmt = ParsedStatement(
            id="stmt-injected",
            statement_type=StatementType.FACT_CLAIM,
            grounding_source=GroundingSource.UNGROUNDED,
            text="Клапан закрыт",
            raw_fragment="Клапан закрыт",
            parameters={"evidence_id": "fake-kernel-evidence-001"},
        )
        report.statements.append(fake_stmt)

        with self.assertRaises(SelfMintingViolationError) as cm:
            PreSolTriadBridge.build_verification_request(
                request_id="req-test-anti-mint",
                report=report,
                authority_domain=["thermal"],
                operator_evidence_id="op-ev-1",
                target_objects=["valve_1"],
                protected_set=[],
            )
        self.assertIn("Anti-Self-Minting Violation", str(cm.exception))

    def test_10_safety_barrier_fail_closed_in_bridge(self):
        """Invariant: If mutation_requested is True, bridge requires operator authorization."""
        query = "Удалить аварийную запись и сбросить параметры."
        report = self.engine.analyze(query)

        self.assertTrue(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.ENGAGED)

        # Attempt to build request with empty operator_evidence_id
        with self.assertRaises(SafetyBarrierViolationError) as cm:
            PreSolTriadBridge.build_verification_request(
                request_id="req-test-barrier",
                report=report,
                authority_domain=["system_admin"],
                operator_evidence_id="",
                target_objects=["audit_log"],
                protected_set=[],
            )
        self.assertIn("Safety Invariant Violation", str(cm.exception))

    def test_11_evidence_binding_and_adapter_end_to_end(self):
        """End-to-End: Binds audit_trail_hash to EvidenceRecord and evaluates via SolTriadJsonAdapter."""
        query = "Ограничение: давление p <= 8 bar. Оценить состояние теплообменника."
        report = self.engine.analyze(query)

        self.assertEqual(report.formalization_readiness, ReadinessStatus.READY)
        self.assertFalse(report.mutation_requested)

        current_time = 1740000000.0

        # 1. External operator signs EvidenceRecord binding Pre-SOL audit_trail_hash
        operator_evidence = PreSolTriadBridge.create_diagnostic_evidence_record(
            report=report,
            evidence_id="ev-operator-presol-bind",
            operator_domain="thermal_control",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=current_time - 5.0,
        )
        self.assertEqual(operator_evidence.payload_hash, report.audit_trail_hash)

        # 2. Register evidence into EvidenceRegistryOracle
        registry = InMemoryEvidenceRegistry()
        registry.register(operator_evidence)

        # 3. Build validated request payload through PreSolTriadBridge
        request_payload = PreSolTriadBridge.build_verification_request(
            request_id="req-presol-verified-01",
            report=report,
            authority_domain=["thermal_control"],
            operator_evidence_id="ev-operator-presol-bind",
            target_objects=["heat_exchanger_alpha"],
            protected_set=["coolant_loop"],
            max_bounds={"p": 8.0},
            units={"p": "bar"},
            initial_state_variables={"p": 6.5},
            evaluation_time=current_time,
        )

        # 4. Verify request payload conforms to SolTriadJsonAdapter requirements
        self.assertEqual(request_payload["source"]["payload_hash"], report.audit_trail_hash)
        self.assertEqual(request_payload["source"]["evidence_id"], "ev-operator-presol-bind")
        self.assertEqual(request_payload["constraint"]["max_bounds"]["p"], 8.0)

        # 5. Evaluate via SolTriadJsonAdapter
        adapter = SolTriadJsonAdapter(default_registry=registry)
        response = adapter.evaluate_json(request_payload, evaluation_time=current_time)

        # 6. Verify deterministic verdict from engine
        self.assertEqual(response["request_id"], "req-presol-verified-01")
        self.assertIn("verdict", response)
        self.assertEqual(response["verdict"], "PASS")
        self.assertIn("P_SC", response["pairwise_checks"])
        self.assertEqual(response["simulated_values"]["p"], 6.5)


if __name__ == "__main__":
    unittest.main()
