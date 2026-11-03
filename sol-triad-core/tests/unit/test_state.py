"""
Модульные тесты StateValidator (P_CD State & Invariants).
"""

from sol_triad_core import (
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    CoherenceVerdict,
    DiagnosticCode,
    StateValidator,
)


def test_state_nan_numeric_fails_closed():
    c = ConstraintPrimitive(domain_scope={"power"}, target_objects={"gen_1"})
    d = DissipatePrimitive(loss_domain={"power"}, state_delta={"voltage": float("nan")})
    s0 = SystemState(current_values={"voltage": 220.0})

    val = StateValidator()
    is_valid, verdict, diags, _, _ = val.validate(c, d, s0)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.STATE_INVALID_NUMERIC for d in diags)


def test_state_negative_resource_cost_fails():
    c = ConstraintPrimitive(domain_scope={"power"}, target_objects={"gen_1"})
    d = DissipatePrimitive(loss_domain={"power"}, resource_cost={"fuel": -5.0})
    s0 = SystemState(current_values={"fuel": 100.0})

    val = StateValidator()
    is_valid, verdict, diags, _, _ = val.validate(c, d, s0)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.STATE_NEGATIVE_RESOURCE_COST for d in diags)


def test_state_protected_values_inviolability():
    c = ConstraintPrimitive(
        domain_scope={"power"},
        target_objects={"gen_1"},
        protected_values={"grid_frequency": 50.0}
    )
    # Delta mutates frequency to 51.0
    d = DissipatePrimitive(loss_domain={"power"}, state_delta={"grid_frequency": 1.0})
    s0 = SystemState(current_values={"grid_frequency": 50.0})

    val = StateValidator()
    is_valid, verdict, diags, _, _ = val.validate(c, d, s0)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.STATE_PROTECTED_VALUE_MUTATED for d in diags)


def test_state_forbidden_flag_breach():
    c = ConstraintPrimitive(
        domain_scope={"power"},
        target_objects={"gen_1"},
        forbidden_flags={"meltdown_warning": True}
    )
    # Mutation sets forbidden flag to True
    d = DissipatePrimitive(loss_domain={"power"}, flag_mutations={"meltdown_warning": True})
    s0 = SystemState(current_values={}, active_flags={"meltdown_warning": False})

    val = StateValidator()
    is_valid, verdict, diags, _, _ = val.validate(c, d, s0)

    assert is_valid is False
    assert verdict == CoherenceVerdict.FAIL
    assert any(d.code == DiagnosticCode.STATE_FORBIDDEN_FLAG_ACTIVE for d in diags)


if __name__ == "__main__":
    test_state_nan_numeric_fails_closed()
    test_state_negative_resource_cost_fails()
    test_state_protected_values_inviolability()
    test_state_forbidden_flag_breach()
    print("test_state.py: ALL TESTS PASSED")
