"""Automated Test Suite for Pre-SOL v0.1 Autonomous Prototype.

Verifies:
- 8 core test scenarios from specification v0.4.1
- Clean / valid baseline queries to ensure low False Positive Rate (OFR-V)
- Byte-for-byte immutability of raw_query
- Strict invariant that Pre-SOL never issues AUTHORIZED or DISENGAGED
- Strict separation of CIRCULAR_REASONING from LOGICAL_CONTRADICTION
"""

import unittest
import hashlib
from pre_sol import (
    PreSolEngine,
    StatementType,
    GroundingSource,
    FindingCode,
    ReadinessStatus,
    SafetyBarrierState,
    DiagnosticSeverity,
)


class TestPreSolEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PreSolEngine()

    def test_01_hypothesis_analyzable_without_consent(self):
        """Scenario 1: Pure hypothesis can be analyzed freely without operator consent."""
        raw_query = "Предположим, что пропускная способность канала увеличится на 20% при изменении топологии. Какой теоретический предел?"
        report = self.engine.analyze(raw_query)

        # Invariant checks
        self.assertEqual(report.raw_query, raw_query)
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)
        self.assertNotEqual(report.safety_barrier_state.value, "AUTHORIZED")
        self.assertNotEqual(report.safety_barrier_state.value, "DISENGAGED")

        # Readiness checks
        self.assertEqual(report.analysis_readiness, ReadinessStatus.READY)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)

        # Statement checks
        stmt = report.statements[0]
        self.assertEqual(stmt.statement_type, StatementType.HYPOTHESIS)
        self.assertEqual(stmt.grounding_source, GroundingSource.RAW_TEXT)

    def test_02_hypothesis_adopted_as_working_assumption(self):
        """Scenario 2: Hypothesis explicitly adopted by operator as a working assumption."""
        raw_query = "В предположении, что пропускная способность канала равна 100 Мбит/с, рассчитать задержку."
        context = {"adopted_assumptions": ["пропускная способность"]}
        report = self.engine.analyze(raw_query, context=context)

        self.assertEqual(report.raw_query, raw_query)
        self.assertEqual(report.statements[0].statement_type, StatementType.ASSUMPTION)
        self.assertEqual(report.statements[0].grounding_source, GroundingSource.WORKING_ASSUMPTION)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.READY)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)

    def test_03_fact_assertion_without_verification(self):
        """Scenario 3: Fact claim without verification or evidence ID."""
        raw_query = "Известно, что текущее давление в контуре равно 8.5 bar. Принять к расчету."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertEqual(report.statements[0].statement_type, StatementType.FACT_CLAIM)
        self.assertEqual(report.statements[0].grounding_source, GroundingSource.UNGROUNDED)

        # Must flag ungrounded fact claim
        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.UNGROUNDED_FACT_CLAIM, finding_codes)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertTrue(len(report.clarification_questions) > 0)

    def test_04_qualitative_unquantified_goal(self):
        """Scenario 4: Qualitative goal lacking measurable metrics."""
        raw_query = "Цель: сделать обработку запросов как можно быстрее и оптимизировать задержку."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertEqual(report.statements[0].statement_type, StatementType.GOAL)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.AMBIGUOUS_QUALITATIVE_GOAL, finding_codes)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertTrue(any("измеримую" in q.question_text.lower() for q in report.clarification_questions))

    def test_05_direct_logical_contradiction(self):
        """Scenario 5: Directly contradictory constraints resulting in empty valid set."""
        raw_query = "Ограничение 1: p > 10 bar. Ограничение 2: p < 5 bar."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.LOGICAL_CONTRADICTION, finding_codes)

        # Fatal error blocks both analysis and formalization
        self.assertEqual(report.analysis_readiness, ReadinessStatus.BLOCKED)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_06_circular_reasoning_distinct_from_contradiction(self):
        """Scenario 6: Petitio principii (circular reasoning) must NOT be labeled as contradiction."""
        raw_query = "Гипотеза верна, потому что архитектура эффективна, а архитектура эффективна, потому что гипотеза верна."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        finding_codes = [f.code for f in report.findings]

        # Critical v0.4.1 requirement: CIRCULAR_REASONING is detected, but NOT LOGICAL_CONTRADICTION!
        self.assertIn(FindingCode.CIRCULAR_REASONING, finding_codes)
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, finding_codes)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_07_incompatible_physical_units(self):
        """Scenario 7: Combining incompatible physical dimensions (pressure and time)."""
        raw_query = "Сложить лимиты: p = 10 bar + 5 s."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY, finding_codes)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.BLOCKED)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_08_dangerous_mutation_command(self):
        """Scenario 8: State mutation command must trigger ENGAGED barrier and never authorize."""
        raw_query = "Выполнить сброс конфигурации базы данных и удалить все временные таблицы."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertTrue(report.mutation_requested)

        # Safety barrier MUST be ENGAGED, and NEVER AUTHORIZED
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.ENGAGED)
        self.assertNotEqual(report.safety_barrier_state.value, "AUTHORIZED")
        self.assertNotEqual(report.safety_barrier_state.value, "DISENGAGED")
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_09_clean_analytical_request_no_false_alarm(self):
        """Scenario 9 (Baseline): Clean analytical request should not produce false alarms."""
        raw_query = "Рассмотреть модель теплопередачи при постоянной температуре 300 k."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.READY)
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)

        # No error or contradiction findings
        for f in report.findings:
            self.assertNotEqual(f.severity, DiagnosticSeverity.ERROR)
            self.assertNotEqual(f.severity, DiagnosticSeverity.CRITICAL)

    def test_10_byte_exactness_and_safety_invariant(self):
        """Scenario 10: Strict byte preservation across whitespace, newlines, and unicode."""
        complex_query = "  Строка \n\tс табуляцией; и спецсимволами: P <= 100 bar; α=0.05, 🚀.  "
        report = self.engine.analyze(complex_query)

        # Absolute byte-for-byte equality
        self.assertEqual(report.raw_query, complex_query)
        self.assertEqual(len(report.raw_query), len(complex_query))

        # Absolute safety barrier invariant check
        self.assertIn(report.safety_barrier_state, (SafetyBarrierState.ENGAGED, SafetyBarrierState.NOT_APPLICABLE))
        self.assertNotIn(report.safety_barrier_state.value, ["AUTHORIZED", "DISENGAGED", "PASSED"])

    def test_11_negation_directive_treated_as_constraint_not_mutation(self):
        """Scenario 11: Negative directive ('не удалять', 'запрещено сбрасывать') is a CONSTRAINT, not a mutation."""
        raw_query = "В процессе оптимизации запрещено сбрасывать конфигурацию и не удалять временные таблицы."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        # Invariant: Negative prohibition is a constraint, not an action command to mutate
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)

        # Confirm statement types are CONSTRAINT
        stmt_types = [s.statement_type for s in report.statements]
        self.assertIn(StatementType.CONSTRAINT, stmt_types)
        self.assertNotIn(StatementType.ACTION_COMMAND, stmt_types)

        # Finding must NOT include MUTATION_ATTEMPT
        finding_codes = [f.code for f in report.findings]
        self.assertNotIn(FindingCode.MUTATION_ATTEMPT, finding_codes)

    def test_12_quoted_command_treated_as_hypothesis_not_execution(self):
        """Scenario 12: Quoted action command in an analytical request must not trigger mutation barrier."""
        raw_query = 'Проанализировать команду "удалить все записи" и оценить риски для безопасности.'
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.READY)

        stmt = report.statements[0]
        self.assertEqual(stmt.statement_type, StatementType.HYPOTHESIS)
        finding_codes = [f.code for f in report.findings]
        self.assertNotIn(FindingCode.MUTATION_ATTEMPT, finding_codes)

    def test_13_conditional_scenario_with_action_verb(self):
        """Scenario 13: Conditional scenario ('если потребуется сбросить...') is a HYPOTHESIS, not an active command."""
        raw_query = "Если потребуется сбросить давление в контуре, оценить последствия для температуры."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.READY)

        stmt = report.statements[0]
        self.assertEqual(stmt.statement_type, StatementType.HYPOTHESIS)
        self.assertNotEqual(stmt.statement_type, StatementType.ACTION_COMMAND)

    def test_14_hypothesis_never_receives_external_evidence_ref(self):
        """Scenario 14: A hypothesis referencing an evidence ID never receives EXTERNAL_EVIDENCE_REF grounding."""
        raw_query = "Предположим, что датчик ev-9876 зафиксировал утечку газа в основном контуре."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        stmt = report.statements[0]
        self.assertEqual(stmt.statement_type, StatementType.HYPOTHESIS)

        # CRITICAL INVARIANT: Pre-SOL cannot fabricate or attach verified evidence status to a hypothesis!
        self.assertEqual(stmt.grounding_source, GroundingSource.RAW_TEXT)
        self.assertNotEqual(stmt.grounding_source, GroundingSource.EXTERNAL_EVIDENCE_REF)

    def test_15_working_assumption_vs_unverified_fact(self):
        """Scenario 15: Working assumption is distinct from an ungrounded fact claim."""
        # Case A: Operator adopted working assumption
        query_a = "Допустим, что коэффициент трения mu = 0.15."
        report_a = self.engine.analyze(query_a, context={"adopted_assumptions": ["коэффициент трения"]})
        self.assertEqual(report_a.statements[0].statement_type, StatementType.ASSUMPTION)
        self.assertEqual(report_a.statements[0].grounding_source, GroundingSource.WORKING_ASSUMPTION)
        self.assertEqual(report_a.formalization_readiness, ReadinessStatus.READY)

        # Case B: Unverified fact claim without operator assumption or evidence ID
        query_b = "Известно, что коэффициент трения mu = 0.15."
        report_b = self.engine.analyze(query_b)
        self.assertEqual(report_b.statements[0].statement_type, StatementType.FACT_CLAIM)
        self.assertEqual(report_b.statements[0].grounding_source, GroundingSource.UNGROUNDED)
        self.assertEqual(report_b.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertIn(FindingCode.UNGROUNDED_FACT_CLAIM, [f.code for f in report_b.findings])

    def test_16_linear_causal_deduction_not_circular(self):
        """Scenario 16: Linear causal deduction (A, because B) must NOT trigger circular reasoning."""
        raw_query = "Температура растет; давление растет, потому что температура растет."
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        finding_codes = [f.code for f in report.findings]

        # Invariant: linear deduction is valid and NOT petitio principii
        self.assertNotIn(FindingCode.CIRCULAR_REASONING, finding_codes)
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, finding_codes)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.READY)

    def test_17_compatible_bounds_across_units_pass_without_contradiction(self):
        """Scenario 17: Compatible bounds with unit conversion (p > 5 bar and p < 1000 kPa) must not contradict."""
        # 5 bar = 500 kPa. The interval [500 kPa, 1000 kPa] is valid and non-empty.
        compatible_query = "Ограничение 1: p > 5 bar; Ограничение 2: p < 1000 kPa."
        report_comp = self.engine.analyze(compatible_query)

        finding_codes_comp = [f.code for f in report_comp.findings]
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, finding_codes_comp)
        self.assertEqual(report_comp.analysis_readiness, ReadinessStatus.READY)

        # Conversely: 15 bar = 1500 kPa > 1000 kPa -> empty interval -> contradiction
        incompatible_query = "Ограничение 1: p > 15 bar; Ограничение 2: p < 1000 kPa."
        report_incomp = self.engine.analyze(incompatible_query)
        finding_codes_incomp = [f.code for f in report_incomp.findings]
        self.assertIn(FindingCode.LOGICAL_CONTRADICTION, finding_codes_incomp)
        self.assertEqual(report_incomp.analysis_readiness, ReadinessStatus.BLOCKED)

    def test_18_incompatible_physical_dimensions_single_variable(self):
        """Scenario 18: Assigning different physical dimensions to the same variable is detected."""
        # Same variable 'p' assigned pressure (bar) and time (s)
        conflicting_query = "Ограничение 1: p > 5 bar; Ограничение 2: p < 10 s."
        report = self.engine.analyze(conflicting_query)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY, finding_codes)
        self.assertEqual(report.analysis_readiness, ReadinessStatus.BLOCKED)

        # But independent variables with different dimensions in one query are valid
        valid_multi_query = "Ограничение 1: p < 10 bar; Ограничение 2: t < 60 s."
        report_valid = self.engine.analyze(valid_multi_query)
        self.assertNotIn(FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY, [f.code for f in report_valid.findings])

    def test_19_exact_raw_query_immutability_multiline_unicode_tabs(self):
        """Scenario 19: Strict byte-for-byte preservation across unicode, newlines, tabs, and quotes."""
        raw_query = """\t\t[TASK-SPEC] 'v0.4.1':\r\n\t* "Цель": Рассчитать тепловой поток;\r\n\t* Инвариант: T_max <= 450 K;\r\n\t* Примечание: 🚀 Никаких мутаций!"""
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        self.assertEqual(report.raw_query.encode("utf-8"), raw_query.encode("utf-8"))
        self.assertEqual(hash(report.raw_query), hash(raw_query))

    def test_20_safety_barrier_guarantee_never_disengaged_or_authorized(self):
        """Scenario 20: Pre-SOL under heavy mutation commands keeps barrier ENGAGED and never AUTHORIZED."""
        raw_query = "Сбросить аварийный клапан, стереть журнал событий и выкатить обновление базы данных."
        report = self.engine.analyze(raw_query)

        self.assertTrue(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.ENGAGED)
        self.assertNotIn(report.safety_barrier_state.value, ["AUTHORIZED", "DISENGAGED", "PASSED", "UNRESTRICTED"])
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_21_neutral_analytical_baselines_zero_false_alarms(self):
        """Scenario 21: Neutral analytical domain queries produce READY analysis with zero false alarms."""
        query_a = "Вычислить плотность потока нейтронов при известной температуре 320 k."
        report_a = self.engine.analyze(query_a)
        self.assertEqual(report_a.analysis_readiness, ReadinessStatus.READY)
        self.assertFalse(report_a.mutation_requested)
        for f in report_a.findings:
            self.assertNotEqual(f.severity, DiagnosticSeverity.ERROR)
            self.assertNotEqual(f.severity, DiagnosticSeverity.CRITICAL)

        query_b = "Определить резонансную частоту колебаний балки длиной 2.5 m и массой 12 kg."
        report_b = self.engine.analyze(query_b)
        self.assertEqual(report_b.analysis_readiness, ReadinessStatus.READY)
        self.assertFalse(report_b.mutation_requested)
        for f in report_b.findings:
            self.assertNotEqual(f.severity, DiagnosticSeverity.ERROR)
            self.assertNotEqual(f.severity, DiagnosticSeverity.CRITICAL)

    def test_22_deserialization_tampering_rejection(self):
        """Scenario 22: Deserialization via from_dict strictly rejects forged safety states."""
        raw_query = "Рассмотреть модель теплопередачи при постоянной температуре 300 k."
        report = self.engine.analyze(raw_query)

        # Normal round-trip serialization/deserialization
        data = report.to_dict()
        restored = report.from_dict(data)
        self.assertEqual(restored.raw_query, report.raw_query)
        self.assertEqual(restored.safety_barrier_state, report.safety_barrier_state)

        # Attempt to spoof safety_barrier_state to AUTHORIZED
        tampered_auth = dict(data)
        tampered_auth["safety_barrier_state"] = "AUTHORIZED"
        with self.assertRaises(ValueError) as ctx:
            report.from_dict(tampered_auth)
        self.assertIn("Security Invariant Violation", str(ctx.exception))

        # Attempt to spoof safety_barrier_state to DISENGAGED
        tampered_dis = dict(data)
        tampered_dis["safety_barrier_state"] = "DISENGAGED"
        with self.assertRaises(ValueError) as ctx:
            report.from_dict(tampered_dis)
        self.assertIn("Security Invariant Violation", str(ctx.exception))

        # Attempt to set mutation_requested=True with safety_barrier_state=NOT_APPLICABLE
        tampered_mut = dict(data)
        tampered_mut["mutation_requested"] = True
        tampered_mut["safety_barrier_state"] = "NOT_APPLICABLE"
        with self.assertRaises(ValueError) as ctx:
            report.from_dict(tampered_mut)
        self.assertIn("Invariant Violation", str(ctx.exception))

    # ==========================================================================
    # Round 2: Targeted Boundary Cases (6 Specific Scenarios)
    # ==========================================================================

    def test_23_negative_prohibition_not_mutation_command(self):
        """Case 1: Negative prohibition ('не удаляй таблицы') must be a CONSTRAINT, not an action command."""
        raw_query = "не удаляй таблицы"
        report = self.engine.analyze(raw_query)

        # Invariant checks
        self.assertEqual(report.raw_query, "не удаляй таблицы")
        self.assertFalse(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)
        self.assertEqual(len(report.statements), 1)
        self.assertEqual(report.statements[0].statement_type, StatementType.CONSTRAINT)
        self.assertNotEqual(report.statements[0].statement_type, StatementType.ACTION_COMMAND)

        finding_codes = [f.code for f in report.findings]
        self.assertNotIn(FindingCode.MUTATION_ATTEMPT, finding_codes)

    def test_24_quoted_command_with_subsequent_action_request(self):
        """Case 2: Quoted command PLUS subsequent action command ('проанализируй команду "удали таблицу", а затем выполни её').
        Quotes must NOT mask the subsequent explicit execution request!
        """
        raw_query = 'проанализируй команду "удали таблицу", а затем выполни её'
        report = self.engine.analyze(raw_query)

        self.assertEqual(report.raw_query, raw_query)
        # CRITICAL INVARIANT: Subsequent execution command must be detected and safety barrier ENGAGED!
        self.assertTrue(report.mutation_requested)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.ENGAGED)
        self.assertNotIn(report.safety_barrier_state.value, ["AUTHORIZED", "DISENGAGED", "PASSED"])

        # Check statement types: contains ACTION_COMMAND
        stmt_types = [s.statement_type for s in report.statements]
        self.assertIn(StatementType.ACTION_COMMAND, stmt_types)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.MUTATION_ATTEMPT, finding_codes)

    def test_25_conditional_scenario_vs_conditional_action_request(self):
        """Case 3: Distinguish purely hypothetical scenario from conditional action request.
        Analysis of scenario must not authorize action; if action requested, barrier must engage.
        """
        # Subcase 3A: Pure hypothetical conditional scenario
        query_hyp = "Если давление упадет ниже 1 bar, оценить последствия для температуры."
        report_hyp = self.engine.analyze(query_hyp)

        self.assertEqual(report_hyp.raw_query, query_hyp)
        self.assertFalse(report_hyp.mutation_requested)
        self.assertEqual(report_hyp.safety_barrier_state, SafetyBarrierState.NOT_APPLICABLE)
        self.assertEqual(report_hyp.analysis_readiness, ReadinessStatus.READY)
        self.assertEqual(report_hyp.statements[0].statement_type, StatementType.HYPOTHESIS)
        self.assertNotIn(FindingCode.MUTATION_ATTEMPT, [f.code for f in report_hyp.findings])

        # Subcase 3B: Conditional with explicit action execution request
        query_act = "Если давление превысит 10 bar, то выполни сброс клапана."
        report_act = self.engine.analyze(query_act)

        self.assertEqual(report_act.raw_query, query_act)
        # CRITICAL INVARIANT: Action execution upon condition must trigger mutation_requested and ENGAGED barrier!
        self.assertTrue(report_act.mutation_requested)
        self.assertEqual(report_act.safety_barrier_state, SafetyBarrierState.ENGAGED)
        self.assertNotIn(report_act.safety_barrier_state.value, ["AUTHORIZED", "DISENGAGED", "PASSED"])
        self.assertIn(FindingCode.MUTATION_ATTEMPT, [f.code for f in report_act.findings])

    def test_26_unit_conversion_equivalent_bounds_single_point_and_incompatible(self):
        """Case 4: Dimensions and units:
        - Coincident bounds with conversion (p >= 1 bar and p <= 100 kPa) form a valid single-point interval, NOT a contradiction.
        - Incompatible dimensions (pressure vs time) must NOT be compared numerically.
        """
        # Subcase 4A: Coincident bounds with conversion (1 bar = 100 kPa = 100000 Pa)
        query_coincident = "p >= 1 bar; p <= 100 kPa"
        report_coincident = self.engine.analyze(query_coincident)

        self.assertEqual(report_coincident.raw_query, query_coincident)
        coincident_findings = [f.code for f in report_coincident.findings]
        # Invariant: Single-point interval [100000, 100000] is non-empty, NOT a contradiction!
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, coincident_findings)
        self.assertNotIn(FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY, coincident_findings)
        self.assertEqual(report_coincident.analysis_readiness, ReadinessStatus.READY)

        # Subcase 4B: Incompatible dimensions across variable (pressure vs time)
        query_incompatible = "p >= 1 bar; p <= 10 s"
        report_incompatible = self.engine.analyze(query_incompatible)

        incomp_findings = [f.code for f in report_incompatible.findings]
        # Invariant: Dimension conflict detected, but NOT compared as numerical contradiction!
        self.assertIn(FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY, incomp_findings)
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, incomp_findings)
        self.assertEqual(report_incompatible.analysis_readiness, ReadinessStatus.BLOCKED)

    def test_27_circular_reasoning_positive_vs_linear_deduction(self):
        """Case 5: Circular reasoning (petitio principii):
        - Positive test for true bidirectional circularity.
        - Negative test for linear causal deduction without circularity.
        """
        # Subcase 5A: True circular reasoning (mutual justification)
        query_circ = "Давление растет, потому что температура повышается. Температура повышается, потому что давление растет."
        report_circ = self.engine.analyze(query_circ)

        circ_findings = [f.code for f in report_circ.findings]
        self.assertIn(FindingCode.CIRCULAR_REASONING, circ_findings)
        # CRITICAL INVARIANT: Circular reasoning must NOT be labeled as contradiction!
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, circ_findings)
        self.assertEqual(report_circ.analysis_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertEqual(report_circ.formalization_readiness, ReadinessStatus.BLOCKED)

        # Subcase 5B: Linear causal chain (A <- B <- C, non-circular)
        query_linear = "Клапан открыт, потому что давление превысило предел. Давление превысило предел, потому что насос работает на полную мощность."
        report_linear = self.engine.analyze(query_linear)

        linear_findings = [f.code for f in report_linear.findings]
        # Invariant: Linear deduction must NOT trigger circular reasoning or contradiction!
        self.assertNotIn(FindingCode.CIRCULAR_REASONING, linear_findings)
        self.assertNotIn(FindingCode.LOGICAL_CONTRADICTION, linear_findings)

    def test_28_exact_raw_query_byte_preservation_utf8(self):
        """Case 6: Strict byte-for-byte raw_query preservation across UTF-8, whitespace, quotes, tabs, CRLF."""
        raw_query = "   \n\tПример запроса: p >= 1 bar; «не удаляй» — ΔT = 5°C, \"test\"!   \r\n   "
        report = self.engine.analyze(raw_query)

        # 1. Exact string equality
        self.assertEqual(report.raw_query, raw_query)

        # 2. Exact UTF-8 byte representation
        raw_bytes = raw_query.encode("utf-8")
        report_bytes = report.raw_query.encode("utf-8")
        self.assertEqual(report_bytes, raw_bytes)
        self.assertEqual(len(report_bytes), len(raw_bytes))

        # 3. Exact SHA256 cryptographic digest
        expected_hash = hashlib.sha256(raw_bytes).hexdigest()
        actual_hash = hashlib.sha256(report_bytes).hexdigest()
        self.assertEqual(actual_hash, expected_hash)

    def test_29_unconfirmed_claims_never_yield_pass_or_unauthorized_ready(self):
        """Case 7: Epistemic boundary check:
        Ungrounded fact claims must produce UNGROUNDED_FACT_CLAIM, keep formalization
        in NEEDS_CLARIFICATION, and Pre-SOL must never output a kernel PASS verdict.
        """
        query = "Известно, что клапан полностью открыт. Принять к расчету."
        report = self.engine.analyze(query)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.UNGROUNDED_FACT_CLAIM, finding_codes)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertNotEqual(report.formalization_readiness, ReadinessStatus.READY)
        # Pre-SOL report uses ReadinessStatus (READY, NEEDS_CLARIFICATION, BLOCKED),
        # confirming that kernel-level 'PASS' is structurally impossible in Pre-SOL.
        self.assertNotIn("PASS", [report.analysis_readiness.value, report.formalization_readiness.value])

    def test_30_data_deficiency_on_unconstrained_action(self):
        """Case 8: Missing constraints for action command triggers DATA_DEFICIENCY."""
        query = "Выполни сброс клапана."
        report = self.engine.analyze(query)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.DATA_DEFICIENCY, finding_codes)
        self.assertIn(FindingCode.MUTATION_ATTEMPT, finding_codes)
        self.assertEqual(report.safety_barrier_state, SafetyBarrierState.ENGAGED)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.BLOCKED)

    def test_31_epistemic_isolation_pre_sol_never_generates_fake_evidence_id(self):
        """Case 9: Epistemic isolation: Pre-SOL must NEVER synthesize or inject fake evidence IDs."""
        query = "Предположим, что температура достигла 150 C. Если это так, исследовать расширение трубы."
        report = self.engine.analyze(query)

        # Confirm all extracted statements have no fabricated evidence_id and no kernel evidence_id
        for stmt in report.statements:
            self.assertIsNone(stmt.parameters.get("evidence_id"))
            self.assertNotEqual(stmt.grounding_source, GroundingSource.EXTERNAL_EVIDENCE_REF)
            self.assertFalse(hasattr(stmt, "evidence_id"))
            self.assertNotIn("mock-evidence-id", str(stmt.parameters))
            self.assertNotIn("fake-evidence", str(stmt.parameters))



    def test_32_qualitative_unquantified_goal_blocks_formalization(self):
        """Case 10: Qualitative unmeasurable goal prevents promotion to READY."""
        query = "Цель: сделать работу системы максимально быстрой и надежной."
        report = self.engine.analyze(query)

        finding_codes = [f.code for f in report.findings]
        self.assertIn(FindingCode.AMBIGUOUS_QUALITATIVE_GOAL, finding_codes)
        self.assertEqual(report.formalization_readiness, ReadinessStatus.NEEDS_CLARIFICATION)
        self.assertNotEqual(report.formalization_readiness, ReadinessStatus.READY)


if __name__ == "__main__":
    unittest.main()


