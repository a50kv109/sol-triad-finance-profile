"""
Минимальный пример прямого использования канонического ядра SOL-Triad Core.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

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


def main():
    print("=== SOL-Triad Core: Минимальный пример прямого использования ядра ===")

    # 1. Хост подготавливает доверенное системное время и реестр
    now = 1740000000.0
    registry = InMemoryEvidenceRegistry()
    registry.register(EvidenceRecord(
        evidence_id="ev-sensor-telemetry-01",
        domain="thermal_control",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 5.0,
        payload_hash="sha256-verified-digest"
    ))

    # 2. Недоверенная заявка агента (S), ограничения хоста (C), действие (D), состояние (S0)
    source = SourcePrimitive(
        evidence_id="ev-sensor-telemetry-01",
        authority_domain={"thermal_control"},
        granted_scope={"coolant_pump_alpha"},
        granted_loss_domains={"heat_dissipation"},
        epistemic_type=EpistemicStatus.FACT,
        timestamp_sec=now - 5.0,
        max_age_sec=60.0,
        payload_hash="sha256-verified-digest"
    )

    constraint = ConstraintPrimitive(
        domain_scope={"thermal_control"},
        target_objects={"coolant_pump_alpha"},
        protected_set={"reactor_emergency_cutoff"},
        min_bounds={"coolant_pressure_bar": 1.0},
        max_bounds={"coolant_pressure_bar": 6.0},
        units={"coolant_pressure_bar": "bar"}
    )

    dissipate = DissipatePrimitive(
        loss_domain={"heat_dissipation"},
        state_delta={"coolant_pressure_bar": 1.2},
        units={"coolant_pressure_bar": "bar"}
    )

    initial_state = SystemState(
        current_values={"coolant_pressure_bar": 2.5},
        units={"coolant_pressure_bar": "bar"}
    )

    # 3. Вызов детерминированного ядра
    kernel = SolTriadCoreKernel()
    report = kernel.evaluate(
        source=source,
        constraint=constraint,
        dissipate=dissipate,
        initial_state=initial_state,
        evaluation_time_sec=now,
        registry=registry
    )

    print(f"Вердикт ядра: {report.verdict.value}")
    print(f"Статус P_SC (Grounding/Scope): {report.pairwise_checks['P_SC'].verdict.value}")
    print(f"Статус P_SD (Loss Scope):      {report.pairwise_checks['P_SD'].verdict.value}")
    print(f"Статус P_CD (Invariants):      {report.pairwise_checks['P_CD'].verdict.value}")
    print(f"Симулированное давление:       {report.simulated_values['coolant_pressure_bar']} bar")
    print(f"Разрешение на исполнение:     {report.execution_permitted} (СТРОГО FALSE)")

    assert report.verdict == CoherenceVerdict.PASS
    assert report.execution_permitted is False


if __name__ == "__main__":
    main()
