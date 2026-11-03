"""
Тесты безопасности: Математический детерминизм и повторяемость верификации.
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
)


def test_kernel_strict_determinism_100_runs():
    """Тест детерминизма: 100 последовательных вызовов на одних и тех же входах возвращают идентичный результат."""
    now = 1740000000.0
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-det-01",
        domain="physics",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 5.0,
        payload_hash="sha256-fixed"
    ))

    source = SourcePrimitive(
        evidence_id="ev-det-01",
        authority_domain={"physics"},
        granted_scope={"subsystem_a"},
        granted_loss_domains={"heat"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=now - 5.0,
        max_age_sec=60.0,
        payload_hash="sha256-fixed"
    )

    constraint = ConstraintPrimitive(
        domain_scope={"physics"},
        target_objects={"subsystem_a"},
        protected_set={"invariant_core"},
        min_bounds={"pressure_bar": 1.0},
        max_bounds={"pressure_bar": 10.0},
        units={"pressure_bar": "bar"}
    )

    dissipate = DissipatePrimitive(
        loss_domain={"heat"},
        state_delta={"pressure_bar": 2.5},
        units={"pressure_bar": "bar"}
    )

    initial_state = SystemState(
        current_values={"pressure_bar": 4.0},
        units={"pressure_bar": "bar"}
    )

    kernel = SolTriadCoreKernel()

    # Первый прогон (эталонный)
    baseline_report = kernel.evaluate(
        source, constraint, dissipate, initial_state,
        evaluation_time_sec=now, registry=reg
    )
    baseline_dict = baseline_report.to_dict()

    for i in range(100):
        run_report = kernel.evaluate(
            source, constraint, dissipate, initial_state,
            evaluation_time_sec=now, registry=reg
        )
        run_dict = run_report.to_dict()

        assert run_dict["verdict"] == baseline_dict["verdict"], f"Run {i}: Verdict diverged"
        assert run_dict["simulated_values"] == baseline_dict["simulated_values"], f"Run {i}: Values diverged"
        assert run_dict["execution_permitted"] == baseline_dict["execution_permitted"], f"Run {i}: Permission diverged"
        assert len(run_dict["diagnostics"]) == len(baseline_dict["diagnostics"]), f"Run {i}: Diagnostics count diverged"


if __name__ == "__main__":
    test_kernel_strict_determinism_100_runs()
    print("test_determinism.py: ALL TESTS PASSED")
