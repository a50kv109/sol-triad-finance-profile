"""
Тесты адаптера SolTriadJsonGateway.
"""

from sol_triad_core import (
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
)
from adapters.json_adapter import SolTriadJsonGateway


def _valid_json_payload(now=1740000000.0):
    return {
        "request_id": "test-json-001",
        "protocol_version": "1.0.0-canonical",
        "source": {
            "evidence_id": "ev-sens-01",
            "authority_domain": ["robotics"],
            "granted_scope": ["arm_joint_1"],
            "granted_loss_domains": ["friction"],
            "epistemic_type": "FACT",
            "timestamp_sec": now - 5.0,
            "max_age_sec": 120.0,
            "payload_hash": "sha256-joint"
        },
        "constraint": {
            "domain_scope": ["robotics"],
            "target_objects": ["arm_joint_1"],
            "protected_set": [],
            "min_bounds": {"angle_deg": -180.0},
            "max_bounds": {"angle_deg": 180.0},
            "units": {"angle_deg": "currency_unit"}
        },
        "dissipate": {
            "loss_domain": ["friction"],
            "state_delta": {"angle_deg": 45.0},
            "units": {"angle_deg": "currency_unit"}
        },
        "initial_state": {
            "current_values": {"angle_deg": 10.0},
            "units": {"angle_deg": "currency_unit"}
        }
    }


def test_gateway_valid_json_pass():
    now = 1740000000.0
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-sens-01",
        domain="robotics",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 5.0,
        payload_hash="sha256-joint"
    ))

    gw = SolTriadJsonGateway()
    payload = _valid_json_payload(now)

    resp = gw.evaluate_json(payload, evaluation_time=now, registry=reg)

    assert resp["verdict"] == CoherenceVerdict.PASS.value
    assert resp["simulated_values"]["angle_deg"] == 55.0
    assert resp["execution_permitted"] is False


def test_gateway_malformed_json_fails_closed():
    gw = SolTriadJsonGateway()
    bad_json = "{\"request_id\": \"unclosed...}"

    resp = gw.evaluate_json(bad_json)
    assert resp["verdict"] == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.STRUCTURAL_DEFECT.value for d in resp["diagnostics"])


def test_gateway_missing_required_fields():
    gw = SolTriadJsonGateway()
    payload = _valid_json_payload()
    del payload["source"]

    resp = gw.evaluate_json(payload)
    assert resp["verdict"] == CoherenceVerdict.FAIL.value
    assert any("source" in d["message"] for d in resp["diagnostics"])


if __name__ == "__main__":
    test_gateway_valid_json_pass()
    test_gateway_malformed_json_fails_closed()
    test_gateway_missing_required_fields()
    print("test_json_gateway.py: ALL TESTS PASSED")
