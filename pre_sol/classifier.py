"""Statement Classifier for Pre-SOL v0.1.

Splits raw_query into propositions and assigns dual-axis classification:
- StatementType (GOAL, CONSTRAINT, HYPOTHESIS, ASSUMPTION, FACT_CLAIM, ACTION_COMMAND)
- GroundingSource (RAW_TEXT, OPERATOR_ASSERTION, WORKING_ASSUMPTION, UNGROUNDED, EXTERNAL_EVIDENCE_REF)
"""

import re
from typing import List, Dict, Any, Optional
from .models import StatementType, GroundingSource, ParsedStatement, RuleMaturity
from .config import (
    PROVISIONAL_QUALITATIVE_MARKERS,
    PROVISIONAL_MUTATION_VERBS,
    PROVISIONAL_HYPOTHESIS_MARKERS,
    PROVISIONAL_FACT_ASSERTION_MARKERS,
    STANDARD_UNIT_DIMENSIONS,
)


class StatementClassifier:
    """Classifies propositions extracted from the raw query."""

    # Regex for extracting parameter inequalities, e.g. "P > 10 bar", "давление < 5 bar"
    BOUND_PATTERN = re.compile(
        r"([a-zA-Zа-яА-Я_][a-zA-Zа-яА-Я0-9_]*)\s*(<=|>=|<|>|==|=)\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Zа-яА-Я]+)?",
        re.UNICODE
    )

    # Regex for evidence IDs, e.g. "ev-1234", "evidence_id: ev-abc"
    EVIDENCE_PATTERN = re.compile(r"\b(ev-[a-zA-Z0-9_\-]+)\b", re.IGNORECASE)

    def extract_and_classify(
        self,
        raw_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ParsedStatement]:
        """Parses the raw_query into discrete propositions and classifies each."""
        context = context or {}
        adopted_assumptions: List[str] = context.get("adopted_assumptions", [])
        known_evidence_ids: List[str] = context.get("known_evidence_ids", [])

        # Split query by lines, bullets, or major sentence boundaries while preserving content
        raw_lines = [line.strip() for line in raw_query.splitlines() if line.strip()]
        if not raw_lines:
            # Fallback if single line
            raw_lines = [s.strip() for s in re.split(r"(?<=[.;])\s+", raw_query) if s.strip()]

        statements: List[ParsedStatement] = []
        stmt_idx = 1

        for raw_line in raw_lines:
            # Sub-split by bullet, semicolon, or sequential step connectors
            sub_clauses = re.split(r";\s*|(?<=\d\.)\s+|,\s*(?:а\s+)?затем\s+|,?\s*после\s+чего\s+|,?\s*and\s+then\s+", raw_line)
            for clause in sub_clauses:
                clause_clean = clause.strip()
                if not clause_clean or clause_clean.startswith("#"):
                    continue

                stmt_id = f"stmt-{stmt_idx}"
                stmt_idx += 1

                # 1. Check if this clause matches an adopted working assumption in context
                is_adopted = any(
                    adopted.lower() in clause_clean.lower()
                    for adopted in adopted_assumptions
                ) or context.get("all_hypotheses_as_assumptions", False)

                # 2. Detect evidence reference
                evidence_match = self.EVIDENCE_PATTERN.search(clause_clean)
                evidence_id = evidence_match.group(1) if evidence_match else None

                # 3. Classify StatementType
                stmt_type, maturity = self._classify_type(clause_clean, is_adopted)

                # 4. Classify GroundingSource
                grounding_source = self._classify_grounding(
                    clause_clean,
                    stmt_type,
                    is_adopted,
                    evidence_id,
                    known_evidence_ids
                )

                # 5. Extract structured parameters (bounds, units, targets)
                params = self._extract_parameters(clause_clean)
                if evidence_id:
                    params["evidence_id"] = evidence_id

                statement = ParsedStatement(
                    id=stmt_id,
                    statement_type=stmt_type,
                    grounding_source=grounding_source,
                    text=clause_clean,
                    raw_fragment=clause_clean,
                    parameters=params,
                    maturity=maturity,
                )
                statements.append(statement)

        return statements

    def _classify_type(self, text: str, is_adopted: bool) -> tuple[StatementType, RuleMaturity]:
        lower = text.lower()

        # Check for adopted assumption first if flagged by operator context
        if is_adopted:
            return StatementType.ASSUMPTION, RuleMaturity.MANDATORY

        # 1. Check for negative constraints (negation preceding mutation verbs, e.g. "не удалять", "запрещено сбрасывать", "не удаляй")
        mutation_verbs_pattern = "|".join(re.escape(v) for v in PROVISIONAL_MUTATION_VERBS)
        negation_prohibition_patterns = [
            rf"\b(?:не|запрещено|запрещается|нельзя|не\s+допускается|ни\s+в\s+коем\s+случае\s+не)\s+[а-яa-z0-9_\s]*?\b(?:{mutation_verbs_pattern})\b",
            rf"\b(?:do\s+not|don't|never|must\s+not|prohibited\s+to|cannot)\s+[a-z0-9_\s]*?\b(?:{mutation_verbs_pattern})\b",
        ]
        for pattern in negation_prohibition_patterns:
            if re.search(pattern, lower):
                return StatementType.CONSTRAINT, RuleMaturity.MANDATORY

        # 2. Check unquoted text for direct action commands outside any quotes.
        # If there is a quoted command PLUS an unquoted execution command outside quotes
        # (e.g. 'проанализируй команду "удали таблицу", а затем выполни её')
        # the unquoted action request must NOT be hidden by the quotes!
        has_quotes = bool(re.search(r"[\"\'«»“”]", text))
        if has_quotes:
            unquoted_text = re.sub(r"[\"\'«»“”][^\"\'«»“”]*?[\"\'«»“”]", "", text)
            unquoted_lower = unquoted_text.lower()
            has_unquoted_action = any(
                re.search(rf"\b{re.escape(v)}\b", unquoted_lower)
                for v in PROVISIONAL_MUTATION_VERBS
            )
            if has_unquoted_action:
                # Check if this unquoted action is itself negated
                is_unquoted_negated = any(re.search(p, unquoted_lower) for p in negation_prohibition_patterns)
                if not is_unquoted_negated:
                    return StatementType.ACTION_COMMAND, RuleMaturity.PROVISIONAL

        # 3. Check for quoted commands or analytical framing of commands WITHOUT subsequent execution
        # e.g., 'проанализировать команду "удалить все записи"', 'оценить последствия выполнения "сбросить базу"'
        analytical_framing = any(kw in lower for kw in (
            "проанализировать команду", "оценить команду", "рассмотреть команду",
            "смоделировать команду", "последствия команды", "проанализируй команду",
            "оцени команду", "рассмотри команду", "analyze the command",
            "evaluate the command", "simulate the command"
        ))
        quoted_mutation = bool(re.search(
            rf"[\"\'«»“”][^\"\'«»“”]*?\b(?:{mutation_verbs_pattern})\b[^\"\'«»“”]*?[\"\'«»“”]",
            text,
            re.IGNORECASE
        ))

        if analytical_framing or (quoted_mutation and any(w in lower for w in (
            "проанализировать", "проанализируй", "оценить", "оцени", "рассмотреть", "рассмотри",
            "исследовать", "исследуй", "проверить", "проверь", "смоделировать", "смоделируй",
            "analyze", "evaluate", "inspect", "assess", "simulate"
        ))):
            return StatementType.HYPOTHESIS, RuleMaturity.PROVISIONAL

        # 4. Check for conditional scenarios / hypothesis markers
        # Distinguish purely hypothetical scenarios ("если потребуется сбросить, оценить последствия")
        # from conditionals with explicit action commands ("если давление превысит 10 bar, то выполни сброс")
        conditional_markers = [
            "если", "в случае если", "в случае", "при условии, что", "при условии",
            "что если", "предположим", "допустим", "if", "in case of", "in case",
            "provided that", "suppose", "assuming"
        ]
        is_conditional = any(re.search(rf"\b{re.escape(m)}\b", lower) for m in conditional_markers)
        if is_conditional:
            has_action_verb = any(re.search(rf"\b{re.escape(v)}\b", lower) for v in PROVISIONAL_MUTATION_VERBS)
            has_analytical_verb = any(w in lower for w in (
                "оценить", "оцени", "проанализировать", "проанализируй", "рассмотреть", "рассмотри",
                "смоделировать", "смоделируй", "исследовать", "исследуй", "проверить", "проверь",
                "analyze", "evaluate", "inspect", "assess", "simulate"
            ))

            # Consequence directive check (e.g. "..., то выполни сброс", "..., тогда сбросить")
            consequence_match = re.search(r",?\s*(?:то|тогда)\s+([а-яa-z0-9_\s]+)", lower)
            if consequence_match:
                consequence_text = consequence_match.group(1)
                consequence_has_action = any(
                    re.search(rf"\b{re.escape(v)}\b", consequence_text)
                    for v in PROVISIONAL_MUTATION_VERBS
                )
                if consequence_has_action:
                    return StatementType.ACTION_COMMAND, RuleMaturity.PROVISIONAL

            if has_action_verb and not has_analytical_verb:
                return StatementType.ACTION_COMMAND, RuleMaturity.PROVISIONAL

            return StatementType.HYPOTHESIS, RuleMaturity.PROVISIONAL

        # 5. Check for direct un-negated action / mutation command
        for verb in PROVISIONAL_MUTATION_VERBS:
            if re.search(rf"\b{re.escape(verb)}", lower):
                return StatementType.ACTION_COMMAND, RuleMaturity.PROVISIONAL

        # 5. Check for hypothesis markers (general)
        for marker in PROVISIONAL_HYPOTHESIS_MARKERS:
            if re.search(rf"\b{re.escape(marker)}", lower):
                return StatementType.HYPOTHESIS, RuleMaturity.PROVISIONAL

        # 6. Check for fact claim markers
        for marker in PROVISIONAL_FACT_ASSERTION_MARKERS:
            if re.search(rf"\b{re.escape(marker)}", lower):
                return StatementType.FACT_CLAIM, RuleMaturity.PROVISIONAL

        # 7. Check for goal markers
        if any(marker in lower for marker in PROVISIONAL_QUALITATIVE_MARKERS) or lower.startswith("цель") or lower.startswith("goal:"):
            return StatementType.GOAL, RuleMaturity.PROVISIONAL

        # 8. Check for constraint / bounds pattern
        if self.BOUND_PATTERN.search(text) or "не более" in lower or "не менее" in lower or "должно быть" in lower or "must be" in lower:
            return StatementType.CONSTRAINT, RuleMaturity.MANDATORY

        # Default classification heuristic
        return StatementType.HYPOTHESIS, RuleMaturity.PROVISIONAL

    def _classify_grounding(
        self,
        text: str,
        stmt_type: StatementType,
        is_adopted: bool,
        evidence_id: Optional[str],
        known_evidence_ids: List[str]
    ) -> GroundingSource:
        # INVARIANT: HYPOTHESIS can NEVER receive EXTERNAL_EVIDENCE_REF!
        # Pre-SOL cannot convert a hypothesis into verified external evidence.
        if stmt_type == StatementType.HYPOTHESIS:
            return GroundingSource.WORKING_ASSUMPTION if is_adopted else GroundingSource.RAW_TEXT

        if is_adopted or stmt_type == StatementType.ASSUMPTION:
            return GroundingSource.WORKING_ASSUMPTION

        if evidence_id and stmt_type in (StatementType.FACT_CLAIM, StatementType.CONSTRAINT):
            return GroundingSource.EXTERNAL_EVIDENCE_REF

        if stmt_type == StatementType.FACT_CLAIM:
            # A fact claim in raw text without external evidence is UNGROUNDED in Pre-SOL
            return GroundingSource.UNGROUNDED

        if stmt_type in (StatementType.GOAL, StatementType.CONSTRAINT, StatementType.ACTION_COMMAND):
            return GroundingSource.OPERATOR_ASSERTION

        return GroundingSource.RAW_TEXT

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extracts numerical limits, comparisons, and unit tokens."""
        params: Dict[str, Any] = {}
        bounds = []

        for match in self.BOUND_PATTERN.finditer(text):
            var_name = match.group(1).lower()
            op = match.group(2)
            val = float(match.group(3))
            raw_unit = match.group(4).lower() if match.group(4) else None

            dimension = STANDARD_UNIT_DIMENSIONS.get(raw_unit) if raw_unit else None

            bounds.append({
                "variable": var_name,
                "operator": op,
                "value": val,
                "unit": raw_unit,
                "dimension": dimension,
            })

        if bounds:
            params["bounds"] = bounds

        # Check if qualitative goal
        for marker in PROVISIONAL_QUALITATIVE_MARKERS:
            if marker in text.lower():
                params["qualitative_marker"] = marker
                break

        return params
