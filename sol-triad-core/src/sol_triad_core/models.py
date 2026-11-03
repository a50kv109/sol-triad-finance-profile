"""
Канонические структуры данных и примитивы триады SOL-Triad Core.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional, Any
from .errors import (
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticSeverity,
    DiagnosticCode,
)


@dataclass(frozen=True)
class CoherenceDiagnostic:
    """Диагностическое сообщение ядра."""
    code: DiagnosticCode
    severity: DiagnosticSeverity
    message: str
    primitive: Optional[str] = None
    field_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "primitive": self.primitive,
            "field_name": self.field_name,
        }


@dataclass
class SourcePrimitive:
    """Примитив SOURCE (S) — эпистемическое обоснование и полномочия."""
    evidence_id: str
    authority_domain: Set[str]
    granted_scope: Set[str]
    granted_loss_domains: Set[str]
    epistemic_type: EpistemicStatus
    timestamp_sec: float
    max_age_sec: float
    payload_hash: Optional[str] = None
    corroborating_evidence_ids: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintPrimitive:
    """Примитив CONSTRAINT (C) — периметр ограничений и инвариантов."""
    domain_scope: Set[str]
    target_objects: Set[str]
    protected_set: Set[str] = field(default_factory=set)
    min_bounds: Dict[str, float] = field(default_factory=dict)
    max_bounds: Dict[str, float] = field(default_factory=dict)
    protected_values: Dict[str, float] = field(default_factory=dict)
    protected_flags: Set[str] = field(default_factory=set)
    forbidden_flags: Set[str] = field(default_factory=set)
    required_flags: Set[str] = field(default_factory=set)
    units: Dict[str, str] = field(default_factory=dict)


@dataclass
class DissipatePrimitive:
    """Примитив DISSIPATE (D) — предлагаемое воздействие, затраты и мутации."""
    loss_domain: Set[str]
    target_states: Set[str] = field(default_factory=set)
    side_effects: Set[str] = field(default_factory=set)
    resource_cost: Dict[str, float] = field(default_factory=dict)
    state_delta: Dict[str, float] = field(default_factory=dict)
    flag_mutations: Dict[str, bool] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)


@dataclass
class SystemState:
    """Состояние параметров системы на момент начала оценки (S0)."""
    current_values: Dict[str, float] = field(default_factory=dict)
    active_flags: Dict[str, bool] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)


@dataclass
class PairwiseStatus:
    """Статус одной из трёх парных проекций верификации."""
    is_valid: bool
    verdict: CoherenceVerdict
    diagnostics: List[CoherenceDiagnostic] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "verdict": self.verdict.value,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class EvaluationReport:
    """Итоговый детерминированный отчёт верификации ядра."""
    protocol_version: str
    verdict: CoherenceVerdict
    pairwise_checks: Dict[str, PairwiseStatus]
    simulated_values: Dict[str, float]
    simulated_flags: Dict[str, bool]
    diagnostics: List[CoherenceDiagnostic]
    execution_permitted: bool = False  # Строго False в ядре верификации!

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "verdict": self.verdict.value,
            "pairwise_checks": {
                k: v.to_dict() for k, v in self.pairwise_checks.items()
            },
            "simulated_values": dict(self.simulated_values),
            "simulated_flags": dict(self.simulated_flags),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "execution_permitted": False,
        }
