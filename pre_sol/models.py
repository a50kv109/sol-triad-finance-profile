"""Data models and Enums for Pre-SOL v0.1 Task Framing Specification."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import json


class StatementType(str, Enum):
    """Axis 1: Epistemic role of the extracted statement."""
    GOAL = "GOAL"                         # Цель / желаемое состояние
    CONSTRAINT = "CONSTRAINT"             # Ограничение / инвариант
    HYPOTHESIS = "HYPOTHESIS"             # Исследовательская гипотеза
    ASSUMPTION = "ASSUMPTION"             # Принятое рабочее допущение (требует согласия оператора для формализации)
    FACT_CLAIM = "FACT_CLAIM"             # Утверждение о факте
    ACTION_COMMAND = "ACTION_COMMAND"     # Команда на изменение / действие


class GroundingSource(str, Enum):
    """Axis 2: Grounding origin of the extracted statement."""
    RAW_TEXT = "RAW_TEXT"                                 # Непосредственно в тексте запроса
    OPERATOR_ASSERTION = "OPERATOR_ASSERTION"             # Утверждение оператора без доказательств
    WORKING_ASSUMPTION = "WORKING_ASSUMPTION"             # Согласованное оператором допущение
    UNGROUNDED = "UNGROUNDED"                             # Не имеет источника подтверждения
    EXTERNAL_EVIDENCE_REF = "EXTERNAL_EVIDENCE_REF"       # Ссылка на внешний идентификатор свидетельства


class DiagnosticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FindingCode(str, Enum):
    AMBIGUOUS_QUALITATIVE_GOAL = "AMBIGUOUS_QUALITATIVE_GOAL"
    DATA_DEFICIENCY = "DATA_DEFICIENCY"
    UNGROUNDED_FACT_CLAIM = "UNGROUNDED_FACT_CLAIM"
    LOGICAL_CONTRADICTION = "LOGICAL_CONTRADICTION"
    CIRCULAR_REASONING = "CIRCULAR_REASONING"  # Petitio principii - distinct from logical contradiction
    PHYSICAL_UNIT_INCOMPATIBILITY = "PHYSICAL_UNIT_INCOMPATIBILITY"
    MUTATION_ATTEMPT = "MUTATION_ATTEMPT"
    UNSUPPORTED_HYPOTHESIS_AS_PREMISE = "UNSUPPORTED_HYPOTHESIS_AS_PREMISE"


class ReadinessStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SafetyBarrierState(str, Enum):
    """Pre-SOL Safety Barrier State.
    INVARIANT: Pre-SOL CAN NEVER set this to DISENGAGED or AUTHORIZED.
    """
    ENGAGED = "ENGAGED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleMaturity(str, Enum):
    """Marks whether a rule or metric is strictly proven or experimental."""
    MANDATORY = "MANDATORY"         # Explicitly proven and defined in v0.4.1
    PROVISIONAL = "PROVISIONAL"     # Practical heuristic; subject to revision
    UNVERIFIED = "UNVERIFIED"       # Relies on unconfirmed external/kernel assumptions


@dataclass
class ParsedStatement:
    id: str
    statement_type: StatementType
    grounding_source: GroundingSource
    text: str
    raw_fragment: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    maturity: RuleMaturity = RuleMaturity.MANDATORY


@dataclass
class DiagnosticFinding:
    code: FindingCode
    severity: DiagnosticSeverity
    message: str
    related_statement_ids: List[str] = field(default_factory=list)
    suggested_question: Optional[str] = None
    maturity: RuleMaturity = RuleMaturity.MANDATORY


@dataclass
class ClarificationQuestion:
    id: str
    question_text: str
    target_parameter: str
    context_statement_id: Optional[str] = None
    suggested_options: List[str] = field(default_factory=list)


@dataclass
class TaskFramingReport:
    raw_query: str
    analysis_readiness: ReadinessStatus
    formalization_readiness: ReadinessStatus
    safety_barrier_state: SafetyBarrierState
    mutation_requested: bool
    statements: List[ParsedStatement] = field(default_factory=list)
    findings: List[DiagnosticFinding] = field(default_factory=list)
    clarification_questions: List[ClarificationQuestion] = field(default_factory=list)
    summary_explanation: str = ""
    provisional_flags: List[str] = field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    audit_trail_hash: str = ""

    def __post_init__(self):
        # Strict safety invariant check
        if self.safety_barrier_state not in (SafetyBarrierState.ENGAGED, SafetyBarrierState.NOT_APPLICABLE):
            raise ValueError(
                f"Safety Invariant Violation: Pre-SOL cannot set safety barrier to {self.safety_barrier_state}. "
                "Only ENGAGED or NOT_APPLICABLE are allowed."
            )
        if self.mutation_requested and self.safety_barrier_state != SafetyBarrierState.ENGAGED:
            raise ValueError(
                "Safety Invariant Violation: If mutation_requested is True, safety_barrier_state MUST be ENGAGED."
            )

    def verify_audit_trail(self) -> Tuple[bool, Optional[int], Optional[str]]:
        """Verifies cryptographic hash chain integrity of the diagnostic report."""
        if not self.audit_trail:
            return True, None, None
        from .hash_chain import DiagnosticHashChain, DiagnosticBlock
        try:
            chain = DiagnosticHashChain([DiagnosticBlock.from_dict(d) for d in self.audit_trail])
            is_valid, bad_idx, err = chain.verify_integrity()
            if not is_valid:
                return False, bad_idx, err
            if self.audit_trail_hash and chain.head_hash != self.audit_trail_hash:
                return (
                    False,
                    len(self.audit_trail) - 1,
                    f"Audit trail head hash mismatch: expected {self.audit_trail_hash}, got {chain.head_hash}"
                )
            return True, None, None
        except Exception as e:
            return False, None, str(e)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "analysis_readiness": self.analysis_readiness.value,
            "formalization_readiness": self.formalization_readiness.value,
            "safety_barrier_state": self.safety_barrier_state.value,
            "mutation_requested": self.mutation_requested,
            "statements": [
                {
                    "id": s.id,
                    "statement_type": s.statement_type.value,
                    "grounding_source": s.grounding_source.value,
                    "text": s.text,
                    "raw_fragment": s.raw_fragment,
                    "parameters": s.parameters,
                    "maturity": s.maturity.value,
                }
                for s in self.statements
            ],
            "findings": [
                {
                    "code": f.code.value,
                    "severity": f.severity.value,
                    "message": f.message,
                    "related_statement_ids": f.related_statement_ids,
                    "suggested_question": f.suggested_question,
                    "maturity": f.maturity.value,
                }
                for f in self.findings
            ],
            "clarification_questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "target_parameter": q.target_parameter,
                    "context_statement_id": q.context_statement_id,
                    "suggested_options": q.suggested_options,
                }
                for q in self.clarification_questions
            ],
            "summary_explanation": self.summary_explanation,
            "provisional_flags": self.provisional_flags,
            "audit_trail": self.audit_trail,
            "audit_trail_hash": self.audit_trail_hash,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskFramingReport":
        """Strict deserializer enforcing Pre-SOL safety invariants against tampering."""
        barrier_raw = data.get("safety_barrier_state")
        if barrier_raw in ("AUTHORIZED", "DISENGAGED", "PASSED", "UNRESTRICTED"):
            raise ValueError(
                f"Security Invariant Violation: Deserialization rejected unsafe safety barrier state '{barrier_raw}'. "
                "Pre-SOL strictly prohibits AUTHORIZED or DISENGAGED states."
            )
        try:
            barrier_state = SafetyBarrierState(barrier_raw)
        except Exception as e:
            raise ValueError(f"Invalid safety_barrier_state: {barrier_raw}") from e

        if barrier_state not in (SafetyBarrierState.ENGAGED, SafetyBarrierState.NOT_APPLICABLE):
            raise ValueError(f"Pre-SOL safety barrier state must be ENGAGED or NOT_APPLICABLE, got: {barrier_state}")

        mutation_requested = bool(data.get("mutation_requested", False))
        if mutation_requested and barrier_state != SafetyBarrierState.ENGAGED:
            raise ValueError("Invariant Violation: If mutation_requested is True, safety_barrier_state MUST be ENGAGED.")

        statements = [
            ParsedStatement(
                id=s["id"],
                statement_type=StatementType(s["statement_type"]),
                grounding_source=GroundingSource(s["grounding_source"]),
                text=s["text"],
                raw_fragment=s["raw_fragment"],
                parameters=s.get("parameters", {}),
                maturity=RuleMaturity(s.get("maturity", "MANDATORY")),
            )
            for s in data.get("statements", [])
        ]

        findings = [
            DiagnosticFinding(
                code=FindingCode(f["code"]),
                severity=DiagnosticSeverity(f["severity"]),
                message=f["message"],
                related_statement_ids=f.get("related_statement_ids", []),
                suggested_question=f.get("suggested_question"),
                maturity=RuleMaturity(f.get("maturity", "MANDATORY")),
            )
            for f in data.get("findings", [])
        ]

        clarification_questions = [
            ClarificationQuestion(
                id=q["id"],
                question_text=q["question_text"],
                target_parameter=q["target_parameter"],
                context_statement_id=q.get("context_statement_id"),
                suggested_options=q.get("suggested_options", []),
            )
            for q in data.get("clarification_questions", [])
        ]

        return cls(
            raw_query=data["raw_query"],
            analysis_readiness=ReadinessStatus(data["analysis_readiness"]),
            formalization_readiness=ReadinessStatus(data["formalization_readiness"]),
            safety_barrier_state=barrier_state,
            mutation_requested=mutation_requested,
            statements=statements,
            findings=findings,
            clarification_questions=clarification_questions,
            summary_explanation=data.get("summary_explanation", ""),
            provisional_flags=data.get("provisional_flags", []),
            audit_trail=data.get("audit_trail", []),
            audit_trail_hash=data.get("audit_trail_hash", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskFramingReport":
        return cls.from_dict(json.loads(json_str))
