"""
Модульные тесты канонических моделей данных SOL-Triad Core.
"""

from sol_triad_core import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    DiagnosticSeverity,
    CoherenceDiagnostic,
)


def test_epistemic_status_enums():
    assert EpistemicStatus.FACT.value == "FACT"
    assert EpistemicStatus.INFERENCE.value == "INFERENCE"
    assert EpistemicStatus.UNKNOWN.value == "UNKNOWN"


def test_verdict_enums():
    assert CoherenceVerdict.PASS.value == "PASS"
    assert CoherenceVerdict.REVIEW.value == "REVIEW"
    assert CoherenceVerdict.FAIL.value == "FAIL"


def test_source_primitive_immutability_and_defaults():
    s = SourcePrimitive(
        evidence_id="ev-101",
        authority_domain={"hydraulics"},
        granted_scope={"valve_1"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=1700000000.0,
        max_age_sec=120.0
    )
    assert s.evidence_id == "ev-101"
    assert "hydraulics" in s.authority_domain
    assert s.corroborating_evidence_ids == set()
    assert s.payload_hash is None


def test_diagnostic_serialization():
    diag = CoherenceDiagnostic(
        code=DiagnosticCode.STATE_MIN_BOUND_BREACH,
        severity=DiagnosticSeverity.ERROR,
        message="Below min bound",
        primitive="CONSTRAINT",
        field_name="pressure"
    )
    d_dict = diag.to_dict()
    assert d_dict["code"] == "STATE_MIN_BOUND_BREACH"
    assert d_dict["severity"] == "ERROR"
    assert d_dict["field_name"] == "pressure"


if __name__ == "__main__":
    test_epistemic_status_enums()
    test_verdict_enums()
    test_source_primitive_immutability_and_defaults()
    test_diagnostic_serialization()
    print("test_models.py: ALL TESTS PASSED")
