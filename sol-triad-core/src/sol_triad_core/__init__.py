"""
SOL-Triad Core: Каноническое, переносимое детерминированное ядро верификации согласованности.
"""

from .errors import (
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticSeverity,
    DiagnosticCode,
    SolTriadException,
    StructuralDefectException,
)
from .models import (
    CoherenceDiagnostic,
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    PairwiseStatus,
    EvaluationReport,
)
from .evidence import (
    EvidenceRecord,
    EvidenceRegistryOracle,
    InMemoryEvidenceRegistry,
)
from .units import (
    UnitRegistry,
    UnitRegistryError,
    UnknownUnitError,
    DimensionalityError,
)
from .validators import (
    EvidenceValidator,
    ScopeValidator,
    StateValidator,
)
from .kernel import SolTriadCoreKernel

__version__ = "1.0.0-canonical"
__all__ = [
    "EpistemicStatus",
    "CoherenceVerdict",
    "DiagnosticSeverity",
    "DiagnosticCode",
    "SolTriadException",
    "StructuralDefectException",
    "CoherenceDiagnostic",
    "SourcePrimitive",
    "ConstraintPrimitive",
    "DissipatePrimitive",
    "SystemState",
    "PairwiseStatus",
    "EvaluationReport",
    "EvidenceRecord",
    "EvidenceRegistryOracle",
    "InMemoryEvidenceRegistry",
    "UnitRegistry",
    "UnitRegistryError",
    "UnknownUnitError",
    "DimensionalityError",
    "EvidenceValidator",
    "ScopeValidator",
    "StateValidator",
    "SolTriadCoreKernel",
]
