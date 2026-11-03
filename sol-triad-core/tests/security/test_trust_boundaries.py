"""
Тесты безопасности: Границы доверия, защита от инъекций и анти-байпас.
"""

from sol_triad_core import (
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
)
from adapters.json_adapter import SolTriadJsonGateway


def _sample_json_request(now=1740000000.0):
    return {
        "request_id": "req-sec-001",
        "protocol_version": "1.0.0-canonical",
        "source": {
            "evidence_id": "ev-sec-1",
            "authority_domain": ["security_domain"],
            "granted_scope": ["target_host"],
            "granted_loss_domains": ["resource_drain"],
            "epistemic_type": "FACT",
            "timestamp_sec": now - 10.0,
            "max_age_sec": 300.0,
            "payload_hash": "sha256-verified"
        },
        "constraint": {
            "domain_scope": ["security_domain"],
            "target_objects": ["target_host"],
            "protected_set": [],
            "min_bounds": {"memory_mb": 512.0},
            "max_bounds": {"memory_mb": 4096.0},
            "units": {"memory_mb": "currency_unit"}
        },
        "dissipate": {
            "loss_domain": ["resource_drain"],
            "state_delta": {"memory_mb": 128.0},
            "units": {"memory_mb": "currency_unit"}
        },
        "initial_state": {
            "current_values": {"memory_mb": 1024.0},
            "units": {"memory_mb": "currency_unit"}
        }
    }


def test_rejection_of_injected_evaluation_time_in_json():
    """Тест 1: Недоверенный JSON с 'evaluation_time' безусловно отклоняется."""
    gateway = SolTriadJsonGateway()
    payload = _sample_json_request()
    payload["evaluation_time"] = 1740000000.0  # Попытка инъекции времени хоста

    resp = gateway.evaluate_json(payload)
    assert resp["verdict"] == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.STRUCTURAL_DEFECT.value for d in resp["diagnostics"])
    assert any("evaluation_time" in d["message"] for d in resp["diagnostics"])


def test_rejection_of_injected_evidence_records_in_json():
    """Тест 2: Недоверенный JSON с 'evidence_records' безусловно отклоняется."""
    gateway = SolTriadJsonGateway()
    payload = _sample_json_request()
    payload["evidence_records"] = [  # Попытка инъекции самоприсвоенного доказательства
        {
            "evidence_id": "ev-forged",
            "domain": "security_domain",
            "epistemic_status": "FACT",
            "timestamp_sec": 1740000000.0,
            "payload_hash": "sha256-fake"
        }
    ]

    resp = gateway.evaluate_json(payload)
    assert resp["verdict"] == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.STRUCTURAL_DEFECT.value for d in resp["diagnostics"])
    assert any("evidence_records" in d["message"] for d in resp["diagnostics"])


def test_absence_of_trusted_host_context_parameter():
    """Тест 3: Проверка полного отсутствия параметра trusted_host_context в сигнатуре API."""
    gateway = SolTriadJsonGateway()
    payload = _sample_json_request()

    try:
        gateway.evaluate_json(payload, trusted_host_context=True)  # type: ignore
        assert False, "Should have raised TypeError because trusted_host_context was completely removed!"
    except TypeError as e:
        assert "unexpected keyword argument 'trusted_host_context'" in str(e)


def test_safe_payload_with_host_parameters():
    """Тест 4: Легитимный запрос с передачей времени и реестра через параметры хоста проходит."""
    now = 1740000000.0
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-sec-1",
        domain="security_domain",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 10.0,
        payload_hash="sha256-verified"
    ))

    gateway = SolTriadJsonGateway()
    payload = _sample_json_request(now)

    resp = gateway.evaluate_json(payload, evaluation_time=now, registry=reg)
    assert resp["verdict"] == CoherenceVerdict.PASS.value
    assert resp["execution_permitted"] is False


if __name__ == "__main__":
    test_rejection_of_injected_evaluation_time_in_json()
    test_rejection_of_injected_evidence_records_in_json()
    test_absence_of_trusted_host_context_parameter()
    test_safe_payload_with_host_parameters()
    print("test_trust_boundaries.py: ALL TESTS PASSED")
