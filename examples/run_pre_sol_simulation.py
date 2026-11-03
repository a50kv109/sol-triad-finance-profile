"""Pre-SOL Simulation Runner: Generates comprehensive demonstration output and reports."""

import json
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pre_sol import PreSolEngine, SafetyBarrierState, ReadinessStatus

def run_simulation():
    engine = PreSolEngine()

    test_scenarios = [
        {
            "name": "Scenario 1: Свободный анализ гипотезы (без согласия оператора)",
            "query": "Предположим, что пропускная способность канала увеличится на 20% при изменении топологии сети. Какой будет теоретический предел?",
            "context": None,
        },
        {
            "name": "Scenario 2: Гипотеза, принятая оператором как рабочее допущение",
            "query": "В предположении, что пропускная способность канала равна 100 Мбит/с, рассчитать задержку пакетов.",
            "context": {"adopted_assumptions": ["пропускная способность"]},
        },
        {
            "name": "Scenario 3: Утверждение о факте без свидетельства (evidence_id)",
            "query": "Известно, что текущее давление в контуре равно 8.5 bar. Принять к расчету.",
            "context": None,
        },
        {
            "name": "Scenario 4: Качественная неквантифицированная цель",
            "query": "Цель: сделать обработку запросов как можно быстрее и оптимизировать сетевую задержку.",
            "context": None,
        },
        {
            "name": "Scenario 5: Прямое логическое противоречие (пустой интервал)",
            "query": "Ограничение 1: p > 10 bar. Ограничение 2: p < 5 bar.",
            "context": None,
        },
        {
            "name": "Scenario 6: Круговое обоснование (petitio principii)",
            "query": "Гипотеза верна, потому что архитектура эффективна, а архитектура эффективна, потому что гипотеза верна.",
            "context": None,
        },
        {
            "name": "Scenario 7: Несовместимые физические размерности",
            "query": "Сложить лимиты: p = 10 bar + 5 s.",
            "context": None,
        },
        {
            "name": "Scenario 8: Запрос на опасную мутацию (барьер ENGAGED)",
            "query": "Выполнить сброс конфигурации базы данных и удалить все временные таблицы.",
            "context": None,
        },
        {
            "name": "Scenario 9: Чистый аналитический запрос (проверка ложных тревог)",
            "query": "Рассмотреть модель теплопередачи при постоянной температуре 300 k.",
            "context": None,
        },
    ]

    print("=" * 80)
    print(" PRE-SOL v0.1 AUTONOMOUS SIMULATION REPORT ")
    print("=" * 80)

    for i, sc in enumerate(test_scenarios, 1):
        print(f"\n--- [{i}/9] {sc['name']} ---")
        print(f"RAW_QUERY: {sc['query']}")
        report = engine.analyze(sc["query"], context=sc["context"])

        print(f"-> analysis_readiness:      {report.analysis_readiness.value}")
        print(f"-> formalization_readiness: {report.formalization_readiness.value}")
        print(f"-> safety_barrier_state:    {report.safety_barrier_state.value}")
        print(f"-> mutation_requested:       {report.mutation_requested}")
        print(f"-> statements count:         {len(report.statements)}")
        for stmt in report.statements:
            print(f"   * [{stmt.statement_type.value} | {stmt.grounding_source.value}] {stmt.text}")
        print(f"-> findings count:           {len(report.findings)}")
        for f in report.findings:
            print(f"   ! [{f.severity.value}] {f.code.value}: {f.message}")
        if report.clarification_questions:
            print(f"-> questions to operator:   {len(report.clarification_questions)}")
            for q in report.clarification_questions:
                print(f"   ? {q.question_text}")
        print(f"-> summary: {report.summary_explanation}")

if __name__ == "__main__":
    run_simulation()
