"""
Security & Fail-Closed Invariant Tests for SolTriadJsonAdapter (v0.4.0).

Validates protection against untrusted client payloads:
  1. Forged / spoofed 'evaluation_time' in JSON payload is strictly ignored.
  2. Untrusted inline 'evidence_records' in JSON payload are never admitted into active registry.
  3. Legitimate trusted registries (default or override) operate correctly.
  4. Standard adapter fail-closed behaviors (malformed JSON, missing sections, scope violations) are preserved.

Framework: Python standard library unittest (no external dependencies required).
"""

import json
import unittest
from typing import Dict, Any

from sol_triad.models import (
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    DiagnosticSeverity,
)
from sol_triad.evidence import InMemoryEvidenceRegistry, EvidenceRecord
from sol_triad.adapter import SolTriadJsonAdapter
from sol_triad.engine import SolTriadEngine


class TestAdapterSecurity(unittest.TestCase):
    """Verifies that SolTriadJsonAdapter rejects client-side forgery of time and evidence."""

    def setUp(self):
        self.host_time = 1740000000.0
        self.trusted_registry = InMemoryEvidenceRegistry()
        self.trusted_registry.register(EvidenceRecord(
            evidence_id="ev-legit-001",
            domain="thermal_control",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.host_time - 10.0,
            payload_hash="sha256-trusted-valid",
        ))

        self.valid_payload: Dict[str, Any] = {
            "request_id": "req-sec-001",
            "protocol_version": "0.4.0",
            "engine_version": "0.4.0",
            "source": {
                "evidence_id": "ev-legit-001",
                "authority_domain": ["thermal_control"],
                "granted_scope": ["pump_alpha"],
                "granted_loss_domains": ["thermal_entropy"],
                "epistemic_type": "FACT",
                "timestamp_sec": self.host_time - 10.0,
                "max_age_sec": 300.0,
                "payload_hash": "sha256-trusted-valid",
            },
            "constraint": {
                "domain_scope": ["thermal_control"],
                "target_objects": ["pump_alpha"],
                "protected_set": ["emergency_valve"],
                "max_bounds": {"coolant_pressure": 10.0},
                "min_bounds": {"coolant_pressure": 0.5},
                "units": {"coolant_pressure": "bar"},
            },
            "dissipate": {
                "loss_domain": ["thermal_entropy"],
                "target_states": ["coolant_flowing"],
                "side_effects": ["pipe_vibration"],
                "resource_cost": {},
                "state_delta": {"coolant_pressure": 1.5},
                "units": {"coolant_pressure": "bar"},
            },
            "initial_state": {
                "current_values": {"coolant_pressure": 3.0},
                "active_flags": {},
                "units": {"coolant_pressure": "bar"},
            },
        }

    def test_01_spoofed_future_evaluation_time_in_payload_is_ignored(self):
        """
        Adversarial Vector: Client supplies future timestamp in source, and attempts to
        bypass TEMPORAL_FUTURE check by forging 'evaluation_time' in the JSON payload.
        Verification: Host evaluation_time governs; client's payload evaluation_time is IGNORED.
        """
        adapter = SolTriadJsonAdapter(default_registry=self.trusted_registry)

        spoofed_payload = json.loads(json.dumps(self.valid_payload))
        # Action is set 1 hour into the future relative to host
        spoofed_payload["source"]["timestamp_sec"] = self.host_time + 3600.0
        # Client tries to claim evaluation is happening 2 hours in the future
        spoofed_payload["evaluation_time"] = self.host_time + 7200.0

        # Host invokes adapter with host_time
        res = adapter.evaluate_json(spoofed_payload, evaluation_time=self.host_time)

        # Invariant 1: Response evaluation timestamp MUST reflect host time, NOT forged payload time
        self.assertEqual(res["evaluation_timestamp"], self.host_time)
        # Invariant 2: Action MUST fail closed due to future timestamp violation
        self.assertEqual(res["verdict"], CoherenceVerdict.FAIL.value)
        diag_codes = [d["code"] for d in res["diagnostics"]]
        self.assertIn(DiagnosticCode.TEMPORAL_FUTURE.value, diag_codes)

    def test_02_spoofed_past_evaluation_time_in_payload_is_ignored(self):
        """
        Adversarial Vector: Evidence is stale (1000s old). Client tries to spoof 'evaluation_time'
        in payload to make stale evidence appear fresh.
        Verification: Host evaluation_time governs; evidence is correctly identified as TEMPORAL_STALE.
        """
        adapter = SolTriadJsonAdapter(default_registry=self.trusted_registry)

        stale_payload = json.loads(json.dumps(self.valid_payload))
        # Evidence timestamp is 1000s before host_time (max_age is 300s -> stale)
        stale_payload["source"]["timestamp_sec"] = self.host_time - 1000.0
        # Client tries to spoof evaluation_time to be host_time - 990.0 (only 10s old in client frame)
        stale_payload["evaluation_time"] = self.host_time - 990.0

        # Update registry record timestamp to match stale source
        self.trusted_registry.register(EvidenceRecord(
            evidence_id="ev-legit-001",
            domain="thermal_control",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.host_time - 1000.0,
            payload_hash="sha256-trusted-valid",
        ))

        res = adapter.evaluate_json(stale_payload, evaluation_time=self.host_time)

        # Invariant: Must be REVIEW (or FAIL), NEVER PASS; TEMPORAL_STALE diagnostic present
        self.assertEqual(res["evaluation_timestamp"], self.host_time)
        self.assertEqual(res["verdict"], CoherenceVerdict.REVIEW.value)
        diag_codes = [d["code"] for d in res["diagnostics"]]
        self.assertIn(DiagnosticCode.TEMPORAL_STALE.value, diag_codes)

    def test_03_inline_evidence_records_rejected_fail_closed(self):
        """
        Adversarial Vector: Agent supplies forged evidence_records directly in the JSON payload
        without any trusted registry having knowledge of that evidence.
        Verification: Adapter public ingress does NOT register them.
        - With empty trusted registry: fails with EVIDENCE_NOT_FOUND (FAIL).
        - With no registry configured: fails with REGISTRY_OFFLINE (REVIEW).
        - In NO case does untrusted payload get admitted to yield PASS.
        """
        # Case A: An active trusted registry exists, but does not contain the forged ID
        empty_registry = InMemoryEvidenceRegistry()
        adapter_with_reg = SolTriadJsonAdapter(default_registry=empty_registry)

        untrusted_payload = json.loads(json.dumps(self.valid_payload))
        untrusted_payload["source"]["evidence_id"] = "ev-forged-untrusted-999"
        untrusted_payload["evidence_records"] = [
            {
                "evidence_id": "ev-forged-untrusted-999",
                "domain": "thermal_control",
                "epistemic_status": "FACT",
                "timestamp_sec": self.host_time - 10.0,
                "payload_hash": "sha256-trusted-valid",
            }
        ]

        res_a = adapter_with_reg.evaluate_json(untrusted_payload, evaluation_time=self.host_time)
        self.assertEqual(res_a["verdict"], CoherenceVerdict.FAIL.value)
        self.assertIn(DiagnosticCode.EVIDENCE_NOT_FOUND.value, [d["code"] for d in res_a["diagnostics"]])
        # Verify the empty registry was NOT contaminated
        self.assertIsNone(empty_registry.get_record("ev-forged-untrusted-999"))

        # Case B: No registry configured at all
        adapter_no_reg = SolTriadJsonAdapter(default_registry=None)
        res_b = adapter_no_reg.evaluate_json(untrusted_payload, evaluation_time=self.host_time)
        self.assertNotEqual(res_b["verdict"], CoherenceVerdict.PASS.value)
        self.assertEqual(res_b["verdict"], CoherenceVerdict.REVIEW.value)
        self.assertIn(DiagnosticCode.REGISTRY_OFFLINE.value, [d["code"] for d in res_b["diagnostics"]])

    def test_04_inline_evidence_records_cannot_override_trusted_registry(self):
        """
        Adversarial Vector: Agent tries to overwrite an existing record in trusted registry
        by supplying a modified record in payload 'evidence_records'.
        Verification: Trusted registry remains pristine. Tampered hash in request is caught.
        """
        adapter = SolTriadJsonAdapter(default_registry=self.trusted_registry)

        tampered_payload = json.loads(json.dumps(self.valid_payload))
        # Client tries to present an altered payload hash
        tampered_payload["source"]["payload_hash"] = "forged-hash-spoofed"
        # And injects an inline record trying to overwrite the ground truth
        tampered_payload["evidence_records"] = [
            {
                "evidence_id": "ev-legit-001",
                "domain": "thermal_control",
                "epistemic_status": "FACT",
                "timestamp_sec": self.host_time - 10.0,
                "payload_hash": "forged-hash-spoofed",  # Attempt to overwrite trusted hash!
            }
        ]

        res = adapter.evaluate_json(tampered_payload, evaluation_time=self.host_time)

        # Must fail because trusted registry has 'sha256-trusted-valid', NOT 'forged-hash-spoofed'
        self.assertEqual(res["verdict"], CoherenceVerdict.FAIL.value)
        diag_codes = [d["code"] for d in res["diagnostics"]]
        self.assertIn(DiagnosticCode.EVIDENCE_PAYLOAD_MISMATCH.value, diag_codes)

    def test_05_legitimate_trusted_registry_passes(self):
        """Legitimate path: trusted registry passed at construction or via parameter evaluates to PASS."""
        adapter = SolTriadJsonAdapter(default_registry=self.trusted_registry)
        res = adapter.evaluate_json(self.valid_payload, evaluation_time=self.host_time)

        self.assertEqual(res["verdict"], CoherenceVerdict.PASS.value)
        self.assertEqual(res["simulated_values"]["coolant_pressure"], 4.5)
        self.assertTrue(res["pairwise_checks"]["P_SC"]["is_valid"])
        self.assertTrue(res["pairwise_checks"]["P_CD"]["is_valid"])
        self.assertTrue(res["pairwise_checks"]["P_SD"]["is_valid"])

    def test_06_explicit_test_helper_registry_works_when_explicitly_passed(self):
        """
        Explicit Test Path: SolTriadJsonAdapter.create_test_registry allows test harnesses
        to parse records and explicitly supply them as trusted 'registry' parameter.
        """
        adapter = SolTriadJsonAdapter(default_registry=None)

        test_records = [
            {
                "evidence_id": "ev-test-explicit",
                "domain": "thermal_control",
                "epistemic_status": "FACT",
                "timestamp_sec": self.host_time - 10.0,
                "payload_hash": "sha256-test-explicit",
            }
        ]
        # Construct registry via explicit test helper
        explicit_reg = SolTriadJsonAdapter.create_test_registry(test_records)

        req = json.loads(json.dumps(self.valid_payload))
        req["source"]["evidence_id"] = "ev-test-explicit"
        req["source"]["payload_hash"] = "sha256-test-explicit"

        # Pass explicit_reg explicitly to evaluate_json
        res = adapter.evaluate_json(req, registry=explicit_reg, evaluation_time=self.host_time)
        self.assertEqual(res["verdict"], CoherenceVerdict.PASS.value)

    def test_07_safe_existing_adapter_behavior_preserved(self):
        """Standard fail-closed behavior for malformed requests is preserved."""
        adapter = SolTriadJsonAdapter(default_registry=self.trusted_registry)

        # 1. Malformed JSON string
        res_malformed = adapter.evaluate_json("{bad_json: 123", evaluation_time=self.host_time)
        self.assertEqual(res_malformed["verdict"], CoherenceVerdict.FAIL.value)
        self.assertEqual(res_malformed["request_id"], "malformed_json")

        # 2. Missing request_id
        no_id = json.loads(json.dumps(self.valid_payload))
        del no_id["request_id"]
        res_no_id = adapter.evaluate_json(no_id, evaluation_time=self.host_time)
        self.assertEqual(res_no_id["verdict"], CoherenceVerdict.FAIL.value)
        self.assertEqual(res_no_id["request_id"], "missing_request_id")

        # 3. Missing required section (e.g. source)
        no_source = json.loads(json.dumps(self.valid_payload))
        del no_source["source"]
        res_no_source = adapter.evaluate_json(no_source, evaluation_time=self.host_time)
        self.assertEqual(res_no_source["verdict"], CoherenceVerdict.FAIL.value)
        self.assertIn("source", res_no_source["messages"][0])


if __name__ == "__main__":
    unittest.main()
