"""Evaluator for Pre-SOL v0.1.

Synthesizes diagnostic findings into:
- analysis_readiness
- formalization_readiness
- safety_barrier_state (ENGAGED | NOT_APPLICABLE; NEVER DISENGAGED or AUTHORIZED)
- clarification questions
- concise human-readable summary explanation
"""

from typing import List, Tuple
from .models import (
    ParsedStatement,
    DiagnosticFinding,
    ClarificationQuestion,
    ReadinessStatus,
    SafetyBarrierState,
    FindingCode,
    DiagnosticSeverity,
    StatementType,
    GroundingSource,
)


class PreSolEvaluator:
    """Evaluates readiness statuses and enforces safety barriers."""

    def evaluate(
        self,
        raw_query: str,
        statements: List[ParsedStatement],
        findings: List[DiagnosticFinding],
    ) -> Tuple[ReadinessStatus, ReadinessStatus, SafetyBarrierState, bool, List[ClarificationQuestion], str, List[str]]:
        provisional_flags: List[str] = []

        # 1. Determine if mutation is requested
        has_action_stmt = any(s.statement_type == StatementType.ACTION_COMMAND for s in statements)
        has_mutation_finding = any(f.code == FindingCode.MUTATION_ATTEMPT for f in findings)
        mutation_requested = has_action_stmt or has_mutation_finding

        # 2. Safety Barrier State Invariant
        # In Pre-SOL, barrier is NEVER DISENGAGED and execution is NEVER AUTHORIZED.
        if mutation_requested:
            safety_barrier_state = SafetyBarrierState.ENGAGED
        else:
            safety_barrier_state = SafetyBarrierState.NOT_APPLICABLE

        # 3. Collect Critical/Error/Warning Finding Codes
        has_fatal_error = any(f.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL) for f in findings)
        finding_codes = {f.code for f in findings}

        # 4. Evaluate Analysis Readiness
        # Analysis can proceed freely on hypotheses without operator consent!
        # It is blocked only by fatal contradictions or broken premises.
        if FindingCode.LOGICAL_CONTRADICTION in finding_codes:
            analysis_readiness = ReadinessStatus.BLOCKED
        elif FindingCode.CIRCULAR_REASONING in finding_codes:
            analysis_readiness = ReadinessStatus.NEEDS_CLARIFICATION
        elif FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY in finding_codes:
            analysis_readiness = ReadinessStatus.BLOCKED
        else:
            # Hypotheses, qualitative questions, and ungrounded statements can still be analyzed freely
            analysis_readiness = ReadinessStatus.READY

        # 5. Evaluate Formalization Readiness
        # Formalization into a rigorous schema requires unambiguous parameters,
        # non-contradictory constraints, grounded facts or adopted assumptions.
        if has_fatal_error:
            formalization_readiness = ReadinessStatus.BLOCKED
        elif FindingCode.CIRCULAR_REASONING in finding_codes:
            formalization_readiness = ReadinessStatus.BLOCKED
        elif FindingCode.AMBIGUOUS_QUALITATIVE_GOAL in finding_codes:
            formalization_readiness = ReadinessStatus.NEEDS_CLARIFICATION
        elif FindingCode.UNGROUNDED_FACT_CLAIM in finding_codes:
            formalization_readiness = ReadinessStatus.NEEDS_CLARIFICATION
        elif any(s.statement_type == StatementType.HYPOTHESIS and s.grounding_source != GroundingSource.WORKING_ASSUMPTION for s in statements):
            # Pure hypothesis without operator adoption cannot be directly formalized as a binding premise
            # unless adopted as ASSUMPTION.
            if not any(s.statement_type == StatementType.CONSTRAINT for s in statements):
                formalization_readiness = ReadinessStatus.NEEDS_CLARIFICATION
            else:
                formalization_readiness = ReadinessStatus.READY
        elif FindingCode.DATA_DEFICIENCY in finding_codes:
            formalization_readiness = ReadinessStatus.NEEDS_CLARIFICATION
        else:
            formalization_readiness = ReadinessStatus.READY

        # If a mutation command is issued without verified kernel integration, formalization is blocked
        if mutation_requested:
            formalization_readiness = ReadinessStatus.BLOCKED

        # 6. Build Clarification Questions
        questions: List[ClarificationQuestion] = []
        q_idx = 1
        for finding in findings:
            if finding.suggested_question:
                questions.append(
                    ClarificationQuestion(
                        id=f"cq-{q_idx}",
                        question_text=finding.suggested_question,
                        target_parameter=finding.code.value,
                        context_statement_id=finding.related_statement_ids[0] if finding.related_statement_ids else None,
                        suggested_options=[],
                    )
                )
                q_idx += 1

        # Track provisional mechanisms used
        for s in statements:
            if s.maturity.value != "MANDATORY":
                provisional_flags.append(f"Statement {s.id} uses {s.maturity.value} heuristic: {s.statement_type.value}")
        for f in findings:
            if f.maturity.value != "MANDATORY":
                provisional_flags.append(f"Finding {f.code.value} uses {f.maturity.value} heuristic")

        # 7. Generate Concise Human-Readable Summary Explanation
        summary_explanation = self._generate_summary(
            analysis_readiness=analysis_readiness,
            formalization_readiness=formalization_readiness,
            safety_barrier_state=safety_barrier_state,
            mutation_requested=mutation_requested,
            statements=statements,
            findings=findings,
        )

        return (
            analysis_readiness,
            formalization_readiness,
            safety_barrier_state,
            mutation_requested,
            questions,
            summary_explanation,
            list(set(provisional_flags)),
        )

    def _generate_summary(
        self,
        analysis_readiness: ReadinessStatus,
        formalization_readiness: ReadinessStatus,
        safety_barrier_state: SafetyBarrierState,
        mutation_requested: bool,
        statements: List[ParsedStatement],
        findings: List[DiagnosticFinding],
    ) -> str:
        parts = []

        # Statement composition
        type_counts = {}
        for s in statements:
            type_counts[s.statement_type.value] = type_counts.get(s.statement_type.value, 0) + 1
        comp_str = ", ".join([f"{k}: {v}" for k, v in type_counts.items()])
        parts.append(f"Извлечено высказываний ({len(statements)}): [{comp_str}].")

        # Diagnostics overview
        if findings:
            finding_summaries = [f"[{f.severity.value}] {f.code.value}" for f in findings]
            parts.append(f"Диагностические замечания ({len(findings)}): {', '.join(finding_summaries)}.")
        else:
            parts.append("Диагностических дефектов и противоречий не выявлено.")

        # Readiness breakdown
        parts.append(
            f"Статус: Готовность к анализу={analysis_readiness.value}, "
            f"Готовность к формализации={formalization_readiness.value}."
        )

        # Safety barrier
        if mutation_requested:
            parts.append(
                f"Защитный барьер: {safety_barrier_state.value}. Запрошена мутация/действие — "
                "Pre-SOL блокирует исполнение (статус AUTHORIZED не выдаётся)."
            )
        else:
            parts.append(
                f"Защитный барьер: {safety_barrier_state.value} (мутации не запрошены, чисто аналитический запрос)."
            )

        return " ".join(parts)
