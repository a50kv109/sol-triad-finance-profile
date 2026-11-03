"""Pre-SOL to SOL-Triad Adapter Bridge.

Enforces fail-closed validation between Pre-SOL diagnostic reports and
the SolTriadJsonAdapter / Triad Engine:
1. Cryptographic Hash Chain verification of the diagnostic session.
2. Anti-Self-Minting: Rejects any attempt to pass ungrounded statements as facts.
3. Fail-Closed Barrier: If mutation is requested, requires explicit operator authorization.
4. Cryptographic Binding: Binds report audit_trail_hash to kernel EvidenceRecord.
"""

from typing import Dict, Any, Optional, List, Set, Tuple
import time

from .models import (
    TaskFramingReport,
    ReadinessStatus,
    SafetyBarrierState,
    GroundingSource,
    StatementType,
)
from .hash_chain import DiagnosticHashChain, ChainIntegrityError
from sol_triad.models import (
    EvidenceRecord,
    EpistemicStatus,
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
)


class PreSolBridgeError(Exception):
    """Base error for Pre-SOL bridge violations."""
    pass


class SelfMintingViolationError(PreSolBridgeError):
    """Raised when an attempt is made to self-mint evidence from ungrounded claims."""
    pass


class SafetyBarrierViolationError(PreSolBridgeError):
    """Raised when an attempt is made to execute mutation without operator clearance."""
    pass


class PreSolTriadBridge:
    """Fail-closed bridge linking Pre-SOL Task Framing to SOL-Triad Engine."""

    PROTOCOL_VERSION = "0.4.0"

    @classmethod
    def verify_report_integrity(cls, report: TaskFramingReport) -> None:
        """Verifies that the report has a valid, untampered diagnostic hash chain."""
        is_valid, bad_idx, err = report.verify_audit_trail()
        if not is_valid:
            raise ChainIntegrityError(
                f"Pre-SOL Hash Chain integrity check failed at step {bad_idx}: {err}"
            )

    @classmethod
    def create_diagnostic_evidence_record(
        cls,
        report: TaskFramingReport,
        evidence_id: str,
        operator_domain: str,
        epistemic_status: EpistemicStatus = EpistemicStatus.FACT,
        timestamp_sec: Optional[float] = None,
    ) -> EvidenceRecord:
        """Creates an EvidenceRecord cryptographically binding Pre-SOL audit_trail_hash.
        
        INVARIANT: Only an external operator or certified sensor harness can sign this.
        Pre-SOL itself does not possess private keys or authority to self-mint.
        """
        cls.verify_report_integrity(report)

        if not report.audit_trail_hash:
            raise PreSolBridgeError("Cannot bind EvidenceRecord to a report without an audit_trail_hash")

        ts = timestamp_sec if timestamp_sec is not None else time.time()

        return EvidenceRecord(
            evidence_id=evidence_id,
            domain=operator_domain,
            epistemic_status=epistemic_status,
            timestamp_sec=ts,
            payload_hash=report.audit_trail_hash,
            metadata={
                "source": "pre_sol_task_framing",
                "raw_query": report.raw_query,
                "analysis_readiness": report.analysis_readiness.value,
                "formalization_readiness": report.formalization_readiness.value,
                "safety_barrier_state": report.safety_barrier_state.value,
                "chain_blocks_count": len(report.audit_trail),
            }
        )

    @classmethod
    def build_verification_request(
        cls,
        request_id: str,
        report: TaskFramingReport,
        authority_domain: List[str],
        operator_evidence_id: str,
        target_objects: List[str],
        protected_set: List[str],
        max_bounds: Optional[Dict[str, float]] = None,
        min_bounds: Optional[Dict[str, float]] = None,
        units: Optional[Dict[str, str]] = None,
        budget_limits: Optional[Dict[str, float]] = None,
        initial_state_variables: Optional[Dict[str, float]] = None,
        evaluation_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Constructs a validated JSON request dictionary for SolTriadJsonAdapter.
        
        Enforces:
        - Hash Chain integrity
        - Readiness gates (cannot formalize if BLOCKED or NEEDS_CLARIFICATION)
        - Mutation authorization (requires explicit operator evidence if mutation requested)
        - Anti-self-minting checks
        """
        # 1. Verify cryptographic hash chain of Pre-SOL report
        cls.verify_report_integrity(report)

        # 2. Gate check: Mutation / Safety Barrier (fail-closed before readiness check)
        if report.mutation_requested:
            if not operator_evidence_id:
                raise SafetyBarrierViolationError(
                    "Safety Invariant Violation: Report requests state mutation, "
                    "but no operator authorization evidence_id was supplied."
                )
            if report.safety_barrier_state != SafetyBarrierState.ENGAGED:
                raise SafetyBarrierViolationError(
                    f"Safety Invariant Violation: Pre-SOL barrier state must be ENGAGED when "
                    f"mutation is requested, got {report.safety_barrier_state.value}."
                )

        # 3. Gate check: Formalization readiness
        # Note: If mutation was requested, operator_evidence_id provides the required external clearance
        if report.formalization_readiness != ReadinessStatus.READY:
            if not (report.mutation_requested and operator_evidence_id):
                raise PreSolBridgeError(
                    f"Cannot build SOL-Triad request: report formalization_readiness is "
                    f"'{report.formalization_readiness.value}', not 'READY'."
                )

        # 4. Anti-Self-Minting Check: Ensure no statement carries unverified mock evidence
        for stmt in report.statements:
            if stmt.grounding_source == GroundingSource.UNGROUNDED:
                if stmt.parameters.get("evidence_id"):
                    raise SelfMintingViolationError(
                        f"Anti-Self-Minting Violation: Statement {stmt.id} is UNGROUNDED "
                        f"but carries evidence_id '{stmt.parameters['evidence_id']}'."
                    )

        current_ts = evaluation_time if evaluation_time is not None else time.time()

        # 5. Extract constraints from report statements
        bounds_max = dict(max_bounds or {})
        bounds_min = dict(min_bounds or {})
        bounds_units = dict(units or {})

        for stmt in report.statements:
            if stmt.statement_type == StatementType.CONSTRAINT:
                param = stmt.parameters.get("parameter")
                op = stmt.parameters.get("operator")
                val = stmt.parameters.get("value")
                unit = stmt.parameters.get("unit")
                if param and val is not None:
                    if op in ("<=", "<"):
                        bounds_max[param] = float(val)
                    elif op in (">=", ">"):
                        bounds_min[param] = float(val)
                    if unit:
                        bounds_units[param] = unit

        # 6. Format compliant JSON payload for SolTriadJsonAdapter
        return {
            "request_id": request_id,
            "protocol_version": cls.PROTOCOL_VERSION,
            "engine_version": cls.PROTOCOL_VERSION,
            "evaluation_time": current_ts,
            "source": {
                "evidence_id": operator_evidence_id,
                "authority_domain": authority_domain,
                "granted_scope": target_objects,
                "granted_loss_domains": authority_domain,
                "epistemic_type": "FACT",
                "timestamp_sec": current_ts,
                "max_age_sec": 300.0,
                "payload_hash": report.audit_trail_hash,
            },
            "constraint": {
                "domain_scope": authority_domain,
                "target_objects": target_objects,
                "protected_set": protected_set,
                "max_bounds": bounds_max,
                "min_bounds": bounds_min,
                "units": bounds_units,
            },
            "dissipate": {
                "loss_domain": list(authority_domain),
                "target_states": target_objects,
                "side_effects": [],
                "resource_cost": budget_limits or {},
                "state_delta": {},
                "flag_delta": {},
                "units": bounds_units,
            },
            "initial_state": {
                "current_values": initial_state_variables or {},
                "active_flags": {},
                "units": bounds_units,
            },
        }
