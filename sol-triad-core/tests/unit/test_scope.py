"""
Модульные тесты ScopeValidator (P_SC & P_SD).
"""

from sol_triad_core import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    ScopeValidator,
)


def _base_source():
    return SourcePrimitive(
        evidence_id="ev-1",
        authority_domain={"energy", "hvac"},
        granted_scope={"chiller_1", "pump_1"},
        granted_loss_domains={"thermal_loss"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=100.0,
        max_age_sec=300.0
    )


def test_scope_structural_defect_none_rejected():
    s = _base_source()
    s.authority_domain = None  # type: ignore

    c = ConstraintPrimitive(
        domain_scope={"energy"},
        target_objects={"chiller_1"}
    )
    d = DissipatePrimitive(loss_domain={"thermal_loss"})

    val = ScopeValidator()
    is_valid, verdict, diags = val.validate(s, c, d)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.SCOPE_DEFECT_NONE for d in diags)


def test_scope_zero_privileges_empty_set():
    s = _base_source()
    s.authority_domain = set()  # Explicit zero privileges

    c = ConstraintPrimitive(
        domain_scope={"energy"},  # Requests energy with 0 authority
        target_objects={"chiller_1"}
    )
    d = DissipatePrimitive(loss_domain={"thermal_loss"})

    val = ScopeValidator()
    is_valid, verdict, diags = val.validate(s, c, d)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.SCOPE_EXCEEDED_DOMAIN for d in diags)


def test_scope_exceeded_objects_rejected():
    s = _base_source()
    c = ConstraintPrimitive(
        domain_scope={"energy"},
        target_objects={"chiller_1", "unauthorized_pump_99"}
    )
    d = DissipatePrimitive(loss_domain={"thermal_loss"})

    val = ScopeValidator()
    is_valid, verdict, diags = val.validate(s, c, d)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.SCOPE_EXCEEDED_OBJECTS for d in diags)


def test_scope_exceeded_loss_domain_rejected():
    s = _base_source()
    c = ConstraintPrimitive(
        domain_scope={"energy"},
        target_objects={"chiller_1"}
    )
    d = DissipatePrimitive(loss_domain={"rogue_loss_domain"})

    val = ScopeValidator()
    is_valid, verdict, diags = val.validate(s, c, d)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.SCOPE_EXCEEDED_LOSS for d in diags)


if __name__ == "__main__":
    test_scope_structural_defect_none_rejected()
    test_scope_zero_privileges_empty_set()
    test_scope_exceeded_objects_rejected()
    test_scope_exceeded_loss_domain_rejected()
    print("test_scope.py: ALL TESTS PASSED")
