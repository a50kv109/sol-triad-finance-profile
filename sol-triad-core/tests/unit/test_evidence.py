"""
Модульные тесты EvidenceValidator (P_SC Grounding).
"""

from sol_triad_core import (
    SourcePrimitive,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    EvidenceValidator,
)


def test_evidence_future_timestamp_rejected():
    reg = InMemoryEvidenceRegistry()
    s = SourcePrimitive(
        evidence_id="ev-future",
        authority_domain={"energy"},
        granted_scope={"sensor_1"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=500.0,
        max_age_sec=300.0
    )
    validator = EvidenceValidator(reg, current_time_sec=200.0)
    is_valid, verdict, diags = validator.validate(s)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.TEMPORAL_FUTURE for d in diags)


def test_evidence_missing_in_registry_fails():
    reg = InMemoryEvidenceRegistry()  # Empty registry
    s = SourcePrimitive(
        evidence_id="ev-ghost",
        authority_domain={"energy"},
        granted_scope={"sensor_1"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=100.0,
        max_age_sec=300.0
    )
    validator = EvidenceValidator(reg, current_time_sec=150.0)
    is_valid, verdict, diags = validator.validate(s)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.EVIDENCE_NOT_FOUND for d in diags)


def test_evidence_hash_mismatch_fails_closed():
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-secure",
        domain="energy",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=100.0,
        payload_hash="sha256-authentic"
    ))

    s = SourcePrimitive(
        evidence_id="ev-secure",
        authority_domain={"energy"},
        granted_scope={"sensor_1"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=100.0,
        max_age_sec=300.0,
        payload_hash="sha256-tampered"
    )

    validator = EvidenceValidator(reg, current_time_sec=150.0)
    is_valid, verdict, diags = validator.validate(s)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.EVIDENCE_PAYLOAD_MISMATCH for d in diags)


def test_inference_circular_dependency_fails():
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-claim-1",
        domain="energy",
        epistemic_status=EpistemicStatus.INFERENCE,
        timestamp_sec=100.0
    ))

    # Cites itself as corroborating evidence
    s = SourcePrimitive(
        evidence_id="ev-claim-1",
        authority_domain={"energy"},
        granted_scope={"sensor_1"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.INFERENCE,
        timestamp_sec=100.0,
        max_age_sec=300.0,
        corroborating_evidence_ids={"ev-claim-1"}
    )

    validator = EvidenceValidator(reg, current_time_sec=150.0)
    is_valid, verdict, diags = validator.validate(s)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.INFERENCE_CIRCULAR_DEPENDENCY for d in diags)


if __name__ == "__main__":
    test_evidence_future_timestamp_rejected()
    test_evidence_missing_in_registry_fails()
    test_evidence_hash_mismatch_fails_closed()
    test_inference_circular_dependency_fails()
    print("test_evidence.py: ALL TESTS PASSED")
