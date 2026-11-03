"""
Модульные тесты канонического ядра SolTriadCoreKernel.
"""

from sol_triad_core import (
    SolTriadCoreKernel,
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
)


def _setup_base_fixture(current_time=1740000000.0):
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-sensor-100",
        domain="thermal_control",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        payload_hash="sha256-ok"
    ))

    source = SourcePrimitive(
        evidence_id="ev-sensor-100",
        authority_domain={"thermal_control"},
        granted_scope={"pump_alpha"},
        granted_loss_domains={"thermal_entropy"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        max_age_sec=300.0,
        payload_hash="sha256-ok"
    )

    constraint = ConstraintPrimitive(
        domain_scope={"thermal_control"},
        target_objects={"pump_alpha"},
        protected_set={"emergency_valve"},
        max_bounds={"coolant_pressure": 10.0},
        min_bounds={"coolant_pressure": 0.5},
        units={"coolant_pressure": "bar"}
    )

    dissipate = DissipatePrimitive(
        loss_domain={"thermal_entropy"},
        state_delta={"coolant_pressure": 1.5},
        units={"coolant_pressure": "bar"}
    )

    initial_state = SystemState(
        current_values={"coolant_pressure": 3.0},
        units={"coolant_pressure": "bar"}
    )

    return reg, source, constraint, dissipate, initial_state, current_time


def test_kernel_valid_triad_pass():
    reg, s, c, d, s0, now = _setup_base_fixture()
    kernel = SolTriadCoreKernel(default_registry=reg)

    report = kernel.evaluate(s, c, d, s0, evaluation_time_sec=now)

    assert report.verdict == CoherenceVerdict.PASS
    assert report.pairwise_checks["P_SC"].is_valid is True
    assert report.pairwise_checks["P_SD"].is_valid is True
    assert report.pairwise_checks["P_CD"].is_valid is True
    assert report.simulated_values["coolant_pressure"] == 4.5
    assert report.execution_permitted is False, "Kernel MUST NEVER permit execution"


def test_kernel_stale_evidence_review():
    reg, s, c, d, s0, now = _setup_base_fixture()
    # Make source stale: age 500s > max_age 300s
    s.timestamp_sec = now - 500.0
    reg.register(EvidenceRecord(
        evidence_id=s.evidence_id,
        domain="thermal_control",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 500.0,
        payload_hash=s.payload_hash
    ))

    kernel = SolTriadCoreKernel(default_registry=reg)
    report = kernel.evaluate(s, c, d, s0, evaluation_time_sec=now)

    assert report.verdict == CoherenceVerdict.REVIEW
    assert any(diag.code == DiagnosticCode.TEMPORAL_STALE for diag in report.diagnostics)
    assert report.execution_permitted is False


def test_kernel_protected_parameter_mutation_fail():
    reg, s, c, d, s0, now = _setup_base_fixture()
    # Mutate protected parameter 'emergency_valve'
    d.side_effects = {"emergency_valve"}

    kernel = SolTriadCoreKernel(default_registry=reg)
    report = kernel.evaluate(s, c, d, s0, evaluation_time_sec=now)

    assert report.verdict == CoherenceVerdict.FAIL
    assert report.pairwise_checks["P_CD"].is_valid is False
    assert any(diag.code == DiagnosticCode.STATE_PROTECTED_PARAM_MUTATED for diag in report.diagnostics)
    assert report.execution_permitted is False


def test_kernel_unauthorized_loss_domain_fail():
    reg, s, c, d, s0, now = _setup_base_fixture()
    # Request unauthorized loss domain
    d.loss_domain = {"unauthorized_wild_entropy"}

    kernel = SolTriadCoreKernel(default_registry=reg)
    report = kernel.evaluate(s, c, d, s0, evaluation_time_sec=now)

    assert report.verdict == CoherenceVerdict.FAIL
    assert report.pairwise_checks["P_SD"].is_valid is False
    assert any(diag.code == DiagnosticCode.SCOPE_EXCEEDED_LOSS for diag in report.diagnostics)


def test_kernel_bound_breach_fail():
    reg, s, c, d, s0, now = _setup_base_fixture()
    # Add large delta exceeding max_bound 10.0: 3.0 + 8.0 = 11.0
    d.state_delta = {"coolant_pressure": 8.0}

    kernel = SolTriadCoreKernel(default_registry=reg)
    report = kernel.evaluate(s, c, d, s0, evaluation_time_sec=now)

    assert report.verdict == CoherenceVerdict.FAIL
    assert any(diag.code == DiagnosticCode.STATE_MAX_BOUND_BREACH for diag in report.diagnostics)


if __name__ == "__main__":
    test_kernel_valid_triad_pass()
    test_kernel_stale_evidence_review()
    test_kernel_protected_parameter_mutation_fail()
    test_kernel_unauthorized_loss_domain_fail()
    test_kernel_bound_breach_fail()
    print("test_kernel.py: ALL TESTS PASSED")
