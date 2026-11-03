"""Pre-SOL v0.1: Autonomous Diagnostic and Task Framing Module.

Pre-SOL operates strictly as an external pre-processing and diagnostic layer.
It preserves raw_query immutably, classifies statements on dual axes,
evaluates analysis and formalization readiness separately, enforces the
safety barrier invariant, and NEVER creates mock evidence or authorizes execution.
"""

from .models import (
    StatementType,
    GroundingSource,
    DiagnosticSeverity,
    FindingCode,
    ReadinessStatus,
    SafetyBarrierState,
    ParsedStatement,
    DiagnosticFinding,
    ClarificationQuestion,
    TaskFramingReport,
)
from .engine import PreSolEngine
from .hash_chain import DiagnosticHashChain, DiagnosticBlock, ChainIntegrityError
from .adapter_bridge import (
    PreSolTriadBridge,
    PreSolBridgeError,
    SelfMintingViolationError,
    SafetyBarrierViolationError,
)

__all__ = [
    "PreSolEngine",
    "StatementType",
    "GroundingSource",
    "DiagnosticSeverity",
    "FindingCode",
    "ReadinessStatus",
    "SafetyBarrierState",
    "ParsedStatement",
    "DiagnosticFinding",
    "ClarificationQuestion",
    "TaskFramingReport",
    "DiagnosticHashChain",
    "DiagnosticBlock",
    "ChainIntegrityError",
    "PreSolTriadBridge",
    "PreSolBridgeError",
    "SelfMintingViolationError",
    "SafetyBarrierViolationError",
]
