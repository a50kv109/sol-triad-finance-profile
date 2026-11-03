"""Diagnostic Analysis Engine for Pre-SOL v0.1.

Implements structural, epistemic, and physical consistency checks:
- Goal ambiguity detection (qualitative vs quantitative)
- Data deficiency detection
- Ungrounded fact claims
- Direct logical contradictions (mutually exclusive intervals/assertions)
- Circular reasoning (petitio principii) - strictly distinguished from logical contradiction!
- Physical unit incompatibilities (dimensional analysis)
- Mutation and state alteration attempts
"""

import re
import math
from typing import List, Dict, Any, Optional
from .models import (
    ParsedStatement,
    DiagnosticFinding,
    FindingCode,
    DiagnosticSeverity,
    StatementType,
    GroundingSource,
    RuleMaturity,
)
from .config import (
    STANDARD_UNIT_DIMENSIONS,
    UNIT_CONVERSIONS,
    PROVISIONAL_QUALITATIVE_MARKERS,
    PROVISIONAL_MUTATION_VERBS,
)


class DiagnosticAnalyzer:
    """Runs epistemic, logical, and physical diagnostics over parsed statements."""

    def analyze(self, statements: List[ParsedStatement], raw_query: str) -> List[DiagnosticFinding]:
        findings: List[DiagnosticFinding] = []

        # 1. Detect Qualitative / Ambiguous Goals
        findings.extend(self._check_ambiguous_goals(statements))

        # 2. Detect Ungrounded Fact Claims
        findings.extend(self._check_ungrounded_facts(statements))

        # 3. Detect Direct Logical Contradictions
        findings.extend(self._check_logical_contradictions(statements))

        # 4. Detect Circular Reasoning (Petitio Principii - distinct from contradiction)
        findings.extend(self._check_circular_reasoning(statements, raw_query))

        # 5. Detect Physical Unit Incompatibilities
        findings.extend(self._check_unit_incompatibilities(statements, raw_query))

        # 6. Detect Mutation Attempts
        findings.extend(self._check_mutation_attempts(statements))

        # 7. Detect Data Deficiency
        findings.extend(self._check_data_deficiency(statements))

        return findings

    def _check_ambiguous_goals(self, statements: List[ParsedStatement]) -> List[DiagnosticFinding]:
        findings = []
        for stmt in statements:
            if stmt.statement_type == StatementType.GOAL:
                bounds = stmt.parameters.get("bounds", [])
                qualitative_marker = stmt.parameters.get("qualitative_marker")

                # If goal has qualitative marker or lacks numeric bounds
                if qualitative_marker or not bounds:
                    marker_str = f" ('{qualitative_marker}')" if qualitative_marker else ""
                    findings.append(
                        DiagnosticFinding(
                            code=FindingCode.AMBIGUOUS_QUALITATIVE_GOAL,
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                f"Цель в заявлении '{stmt.id}' сформулирована качественно{marker_str} "
                                f"без численной метрики и явных допусков."
                            ),
                            related_statement_ids=[stmt.id],
                            suggested_question="Укажите измеримую целевую метрику, допустимый диапазон или критерий останова.",
                            maturity=RuleMaturity.PROVISIONAL,
                        )
                    )
        return findings

    def _check_ungrounded_facts(self, statements: List[ParsedStatement]) -> List[DiagnosticFinding]:
        findings = []
        for stmt in statements:
            if stmt.statement_type == StatementType.FACT_CLAIM:
                if stmt.grounding_source == GroundingSource.UNGROUNDED:
                    findings.append(
                        DiagnosticFinding(
                            code=FindingCode.UNGROUNDED_FACT_CLAIM,
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                f"Утверждение о факте в '{stmt.id}' не имеет зарегистрированного подтверждения (evidence_id) "
                                f"или внешнего источника верификации."
                            ),
                            related_statement_ids=[stmt.id],
                            suggested_question=(
                                f"Подтвердите источник данных для '{stmt.text}' или зарегистрируйте evidence_id."
                            ),
                            maturity=RuleMaturity.MANDATORY,
                        )
                    )
        return findings

    def _check_logical_contradictions(self, statements: List[ParsedStatement]) -> List[DiagnosticFinding]:
        """Detects mutually exclusive intervals for the same variable (e.g., P > 10 and P < 5)."""
        findings = []
        var_bounds: Dict[str, Dict[str, List[tuple]]] = {}

        for stmt in statements:
            for b in stmt.parameters.get("bounds", []):
                var = b["variable"]
                op = b["operator"]
                val = b["value"]
                unit = b.get("unit")
                dim = b.get("dimension")

                # Normalize value to base SI if conversion available
                norm_val = val
                if unit and unit in UNIT_CONVERSIONS:
                    norm_val = val * UNIT_CONVERSIONS[unit]

                if var not in var_bounds:
                    var_bounds[var] = {"min": [], "max": [], "exact": []}

                entry = (norm_val, stmt.id, val, unit, op, dim)
                if op in (">", ">="):
                    var_bounds[var]["min"].append(entry)
                elif op in ("<", "<="):
                    var_bounds[var]["max"].append(entry)
                elif op in ("==", "="):
                    var_bounds[var]["exact"].append(entry)

        for var, data in var_bounds.items():
            # 1. Check if min bound exceeds max bound for compatible dimensions
            for min_val, min_stmt, orig_min, min_u, min_op, min_dim in data["min"]:
                for max_val, max_stmt, orig_max, max_u, max_op, max_dim in data["max"]:
                    if min_dim and max_dim and min_dim != max_dim:
                        # Dimension conflict across statements is handled by PHYSICAL_UNIT_INCOMPATIBILITY
                        continue

                    # Tolerant float comparison: single-point interval [X, X] is valid if both inclusive
                    is_equal = math.isclose(min_val, max_val, rel_tol=1e-7)
                    is_contradiction = False
                    if min_val > max_val and not is_equal:
                        is_contradiction = True
                    elif is_equal and (min_op == ">" or max_op == "<"):
                        # Strict inequality at equal boundary makes interval empty: e.g. p > 1 bar and p <= 100 kPa
                        is_contradiction = True

                    if is_contradiction:
                        findings.append(
                            DiagnosticFinding(
                                code=FindingCode.LOGICAL_CONTRADICTION,
                                severity=DiagnosticSeverity.ERROR,
                                message=(
                                    f"Прямое логическое противоречие для переменной '{var}': "
                                    f"требование {min_op} {orig_min} {min_u or ''} (из {min_stmt}) "
                                    f"несовместимо с {max_op} {orig_max} {max_u or ''} (из {max_stmt}). "
                                    f"Интервал допустимых значений пуст."
                                ),
                                related_statement_ids=[min_stmt, max_stmt],
                                suggested_question=f"Устраните противоречие: скорректируйте диапазон допустимых значений для '{var}'.",
                                maturity=RuleMaturity.MANDATORY,
                            )
                        )

            # 2. Check if exact bound violates min or max bound
            for exact_val, exact_stmt, orig_ex, ex_u, ex_op, ex_dim in data["exact"]:
                for min_val, min_stmt, orig_min, min_u, min_op, min_dim in data["min"]:
                    if ex_dim and min_dim and ex_dim != min_dim:
                        continue
                    if exact_val < min_val:
                        findings.append(
                            DiagnosticFinding(
                                code=FindingCode.LOGICAL_CONTRADICTION,
                                severity=DiagnosticSeverity.ERROR,
                                message=(
                                    f"Прямое логическое противоречие для переменной '{var}': "
                                    f"точное значение {ex_op} {orig_ex} {ex_u or ''} (из {exact_stmt}) "
                                    f"меньше минимального предела {min_op} {orig_min} {min_u or ''} (из {min_stmt})."
                                ),
                                related_statement_ids=[exact_stmt, min_stmt],
                                suggested_question=f"Устраните противоречие между точным значением и ограничением для '{var}'.",
                                maturity=RuleMaturity.MANDATORY,
                            )
                        )
                for max_val, max_stmt, orig_max, max_u, max_op, max_dim in data["max"]:
                    if ex_dim and max_dim and ex_dim != max_dim:
                        continue
                    if exact_val > max_val:
                        findings.append(
                            DiagnosticFinding(
                                code=FindingCode.LOGICAL_CONTRADICTION,
                                severity=DiagnosticSeverity.ERROR,
                                message=(
                                    f"Прямое логическое противоречие для переменной '{var}': "
                                    f"точное значение {ex_op} {orig_ex} {ex_u or ''} (из {exact_stmt}) "
                                    f"превышает максимальный предел {max_op} {orig_max} {max_u or ''} (из {max_stmt})."
                                ),
                                related_statement_ids=[exact_stmt, max_stmt],
                                suggested_question=f"Устраните противоречие между точным значением и ограничением для '{var}'.",
                                maturity=RuleMaturity.MANDATORY,
                            )
                        )

        return findings

    def _check_circular_reasoning(self, statements: List[ParsedStatement], raw_query: str) -> List[DiagnosticFinding]:
        """Detects petitio principii (circular reasoning).
        CRITICAL: Circular reasoning is strictly NOT marked as logical contradiction!
        It is an invalid/unsupported inference structure.
        Linear deduction (A, because B) is NOT circular unless B also cites A or A cites itself.
        """
        findings = []
        lower_query = raw_query.lower()

        # Check 1: Explicit mutual circle or repetition of premise in justification within text
        # e.g., "A верна, потому что B ... B верна, потому что A"
        mutual_patterns = [
            r"([а-яa-z0-9_\s]{4,30})\s*,?\s*(?:потому что|так как|поскольку)\s+([а-яa-z0-9_\s]{4,30}).*?\2\s*,?\s*(?:потому что|так как|поскольку)\s+.*?\1",
            r"гипотеза верна, потому что .* потому что гипотеза верна",
            r"аргумент верен, так как .* так как аргумент верен",
        ]

        found_circular = False
        for pattern in mutual_patterns:
            if re.search(pattern, lower_query, re.DOTALL | re.IGNORECASE):
                found_circular = True
                break

        # Check 2: Cross-statement mutual justification (A cites B AND B cites A)
        if not found_circular and len(statements) >= 2:
            justification_markers = ("потому что", "так как", "поскольку", "because", "since")
            cites: Dict[str, tuple[str, str]] = {}
            for s in statements:
                s_lower = s.text.lower()
                for marker in justification_markers:
                    if marker in s_lower:
                        parts = s_lower.split(marker, 1)
                        cites[s.id] = (parts[0].strip(), parts[1].strip())
                        break

            # Circular reasoning requires bidirectional/mutual dependency
            for id1, (claim1, reason1) in cites.items():
                for id2, (claim2, reason2) in cites.items():
                    if id1 != id2:
                        claim1_words = {w for w in re.findall(r"\b\w{5,}\b", claim1)}
                        claim2_words = {w for w in re.findall(r"\b\w{5,}\b", claim2)}
                        reason1_words = {w for w in re.findall(r"\b\w{5,}\b", reason1)}
                        reason2_words = {w for w in re.findall(r"\b\w{5,}\b", reason2)}

                        if (claim2_words & reason1_words) and (claim1_words & reason2_words):
                            found_circular = True
                            break
                if found_circular:
                    break

        if found_circular:
            findings.append(
                DiagnosticFinding(
                    code=FindingCode.CIRCULAR_REASONING,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Обнаружено круговое обоснование (petitio principii): утверждение использует само себя "
                        "или своё прямое следствие в качестве аргумента. "
                        "Внимание: это логический дефект обоснования (аргумент не доказан), "
                        "но не формальное взаимное противоречие утверждений."
                    ),
                    related_statement_ids=[s.id for s in statements],
                    suggested_question="Предоставьте независимое внешнее свидетельство или объективный источник для обоснования.",
                    maturity=RuleMaturity.MANDATORY,
                )
            )

        return findings

    def _check_unit_incompatibilities(self, statements: List[ParsedStatement], raw_query: str) -> List[DiagnosticFinding]:
        """Detects dimension collisions (e.g. pressure [bar] combined with time [s])."""
        findings = []
        global_var_dims: Dict[str, Dict[str, List[str]]] = {}

        for stmt in statements:
            bounds = stmt.parameters.get("bounds", [])
            for b in bounds:
                u = b.get("unit")
                dim = b.get("dimension")
                var = b.get("variable")
                if u:
                    if dim:
                        if var:
                            if var not in global_var_dims:
                                global_var_dims[var] = {}
                            global_var_dims[var].setdefault(dim, []).append(stmt.id)
                    else:
                        # Unknown unit
                        findings.append(
                            DiagnosticFinding(
                                code=FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY,
                                severity=DiagnosticSeverity.ERROR,
                                message=f"Нераспознанная или нестандартная физическая единица '{u}' в '{stmt.id}'.",
                                related_statement_ids=[stmt.id],
                                suggested_question=f"Уточните физическую размерность единицы '{u}'.",
                                maturity=RuleMaturity.MANDATORY,
                            )
                        )

        # Check if the SAME variable across statements is given contradictory physical dimensions
        for var, dims in global_var_dims.items():
            if len(dims) > 1:
                related = sorted(list({stmt_id for s_list in dims.values() for stmt_id in s_list}))
                findings.append(
                    DiagnosticFinding(
                        code=FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            f"Несовместимые физические размерности для переменной '{var}': "
                            f"обнаружены {list(dims.keys())}."
                        ),
                        related_statement_ids=related,
                        suggested_question=f"Приведите переменную '{var}' к единой физической размерности.",
                        maturity=RuleMaturity.MANDATORY,
                    )
                )

        # Cross-statement dimensional check for equations / combinations like "P = 10 bar + 5 s"
        dim_collision_regex = re.compile(
            r"(\b(?:bar|pa|kpa|mpa|psi)\b)\s*(?:\+|\-|\=|\=\=)\s*([0-9]+(?:\.[0-9]+)?\s*(?:s|sec|second|seconds|min|minute|h|hour|meter|meters|m|kg|g)\b)",
            re.IGNORECASE
        )
        if dim_collision_regex.search(raw_query):
            findings.append(
                DiagnosticFinding(
                    code=FindingCode.PHYSICAL_UNIT_INCOMPATIBILITY,
                    severity=DiagnosticSeverity.ERROR,
                    message="Операция сложения/сравнения между несовместимыми размерностями давления и времени/длины.",
                    related_statement_ids=[],
                    suggested_question="Разделите разнородные физические величины на независимые ограничения.",
                    maturity=RuleMaturity.MANDATORY,
                )
            )

        return findings

    def _check_mutation_attempts(self, statements: List[ParsedStatement]) -> List[DiagnosticFinding]:
        """Detects if any statement requests state mutation, external side effects, or execution."""
        findings = []
        for stmt in statements:
            if stmt.statement_type == StatementType.ACTION_COMMAND:
                findings.append(
                    DiagnosticFinding(
                        code=FindingCode.MUTATION_ATTEMPT,
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"В заявлении '{stmt.id}' запрошено действие/мутация ('{stmt.text}'). "
                            "Pre-SOL фиксирует запрос на мутацию и удерживает защитный барьер ENGAGED."
                        ),
                        related_statement_ids=[stmt.id],
                        suggested_question=(
                            "Действие требует подтверждения оператора и формализации всех ограничений перед передачей в ядро."
                        ),
                        maturity=RuleMaturity.MANDATORY,
                    )
                )
        return findings

    def _check_data_deficiency(self, statements: List[ParsedStatement]) -> List[DiagnosticFinding]:
        """Detects missing essential operational parameters."""
        findings = []
        has_goal = any(s.statement_type == StatementType.GOAL for s in statements)
        has_constraints = any(s.statement_type == StatementType.CONSTRAINT for s in statements)
        has_hyp = any(s.statement_type in (StatementType.HYPOTHESIS, StatementType.ASSUMPTION) for s in statements)
        has_action = any(s.statement_type == StatementType.ACTION_COMMAND for s in statements)

        if has_action and not has_constraints:
            findings.append(
                DiagnosticFinding(
                    code=FindingCode.DATA_DEFICIENCY,
                    severity=DiagnosticSeverity.WARNING,
                    message="Запрошено действие при полном отсутствии явных ограничений (constraints).",
                    suggested_question="Задайте безопасные границы и инварианты для выполнения действия.",
                    maturity=RuleMaturity.PROVISIONAL,
                )
            )

        return findings
