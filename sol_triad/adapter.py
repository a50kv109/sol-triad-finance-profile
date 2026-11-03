"""
SOL-Triad Engine v0.4.0
Agent Integration Adapter & Machine-Readable Contract.

Provides a decoupled, fail-closed bridge between AI Agent architectures
(planners, tool-calling systems, reasoning loops) and the core SolTriadEngine.
"""

import json
import time
from typing import Dict, Any, Optional, Union, List, Set

from .models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    CoherenceDiagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    PairwiseEvaluation,
    EvaluationReport,
)
from .evidence import EvidenceRegistryOracle, InMemoryEvidenceRegistry
from .engine import SolTriadEngine


class SolTriadJsonAdapter:
    """
    Standard JSON Adapter for SOL-Triad Engine v0.4.0.

    Adheres to schemas/sol_triad_request.schema.json and
    schemas/sol_triad_response.schema.json.
    """
    PROTOCOL_VERSION = "0.4.0"
    SUPPORTED_VERSIONS = {"0.4.0"}

    def __init__(
        self,
        default_registry: Optional[EvidenceRegistryOracle] = None,
        engine: Optional[SolTriadEngine] = None,
    ):
        self.default_registry = default_registry
        self.engine = engine if engine is not None else SolTriadEngine(registry=default_registry)

    def evaluate_json(
        self,
        request_input: Union[str, Dict[str, Any]],
        registry: Optional[EvidenceRegistryOracle] = None,
        evaluation_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Parses a JSON string or dict request, validates its structure,
        evaluates via SolTriadEngine, and serializes the report to a
        JSON-compatible dictionary matching sol_triad_response.schema.json.
        """
        if evaluation_time is not None:
            current_ts = float(evaluation_time)
        elif hasattr(self.engine, "clock") and callable(self.engine.clock):
            current_ts = float(self.engine.clock())
        else:
            current_ts = time.time()
        request_id = "unknown_request"

        # 1. Parse JSON if string
        if isinstance(request_input, str):
            try:
                data = json.loads(request_input)
            except Exception as e:
                return self._create_fail_response(
                    request_id="malformed_json",
                    message=f"JSON decoding failure: {str(e)}",
                    code=DiagnosticCode.STRUCTURAL_DEFECT,
                    timestamp_sec=current_ts,
                )
        elif isinstance(request_input, dict):
            data = request_input
        else:
            return self._create_fail_response(
                request_id="invalid_input_type",
                message=f"Expected JSON string or dict, got {type(request_input).__name__}",
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                timestamp_sec=current_ts,
            )

        # 2. Extract request_id
        raw_request_id = data.get("request_id")
        if not raw_request_id or not isinstance(raw_request_id, str):
            return self._create_fail_response(
                request_id="missing_request_id",
                message="Field 'request_id' is required and must be a non-empty string",
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                timestamp_sec=current_ts,
            )
        request_id = raw_request_id

        # 3. Validate Protocol Version
        proto_ver = data.get("protocol_version")
        if proto_ver not in self.SUPPORTED_VERSIONS:
            return self._create_fail_response(
                request_id=request_id,
                message=f"Unsupported protocol_version '{proto_ver}'. Supported: {sorted(list(self.SUPPORTED_VERSIONS))}",
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                timestamp_sec=current_ts,
            )

        # 4. Check Required Primitives
        for req_field in ("source", "constraint", "dissipate", "initial_state"):
            if req_field not in data or not isinstance(data[req_field], dict):
                return self._create_fail_response(
                    request_id=request_id,
                    message=f"Missing or invalid required section '{req_field}' in request payload",
                    code=DiagnosticCode.STRUCTURAL_DEFECT,
                    field_name=req_field,
                    timestamp_sec=current_ts,
                )

        # 5. Evaluation Time Policy:
        # Untrusted client payload field 'evaluation_time' is strictly IGNORED.
        # Evaluation time is authoritative and governed by orchestrator parameter / engine clock.

        # 6. Parse and Build Primitives
        try:
            source = self._parse_source(data["source"])
            constraint = self._parse_constraint(data["constraint"])
            dissipate = self._parse_dissipate(data["dissipate"])
            initial_state = self._parse_initial_state(data["initial_state"])
        except ValueError as ve:
            return self._create_fail_response(
                request_id=request_id,
                message=f"Validation error in request primitives: {str(ve)}",
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                timestamp_sec=current_ts,
            )
        except Exception as ex:
            return self._create_fail_response(
                request_id=request_id,
                message=f"Unexpected error constructing primitives: {str(ex)}",
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                timestamp_sec=current_ts,
            )

        # 7. Setup Evidence Registry
        active_registry = self._resolve_registry(data, registry)

        # 8. Evaluate via Engine
        evaluator = self.engine
        if active_registry is not None and active_registry != self.engine.registry:
            evaluator = SolTriadEngine(registry=active_registry, clock=lambda: current_ts)

        report = evaluator.evaluate(
            s=source,
            c=constraint,
            d=dissipate,
            initial_state=initial_state,
            evaluation_time=current_ts,
        )

        # 9. Format response according to schema
        return self._format_response(request_id, report)

    def _parse_source(self, s_dict: Dict[str, Any]) -> SourcePrimitive:
        if "evidence_id" not in s_dict or not isinstance(s_dict["evidence_id"], str):
            raise ValueError("source.evidence_id must be a non-empty string")
        if "epistemic_type" not in s_dict:
            raise ValueError("source.epistemic_type is required")
        if "timestamp_sec" not in s_dict:
            raise ValueError("source.timestamp_sec is required")

        try:
            epistemic_type = EpistemicStatus(s_dict["epistemic_type"])
        except Exception:
            raise ValueError(f"Invalid source.epistemic_type '{s_dict.get('epistemic_type')}'")

        # Crucial: Distinguish None (structural defect) from empty list [] (zero privileges)
        authority_domain = (
            set(s_dict["authority_domain"])
            if s_dict.get("authority_domain") is not None
            else None
        )
        granted_scope = (
            set(s_dict["granted_scope"])
            if s_dict.get("granted_scope") is not None
            else None
        )
        granted_loss_domains = (
            set(s_dict["granted_loss_domains"])
            if s_dict.get("granted_loss_domains") is not None
            else None
        )

        corroborating = set(s_dict.get("corroborating_evidence_ids") or [])

        return SourcePrimitive(
            evidence_id=str(s_dict["evidence_id"]),
            authority_domain=authority_domain,
            granted_scope=granted_scope,
            granted_loss_domains=granted_loss_domains,
            epistemic_type=epistemic_type,
            timestamp_sec=float(s_dict["timestamp_sec"]),
            max_age_sec=float(s_dict.get("max_age_sec", 300.0)),
            corroborating_evidence_ids=corroborating,
            payload_hash=s_dict.get("payload_hash"),
        )

    def _parse_constraint(self, c_dict: Dict[str, Any]) -> ConstraintPrimitive:
        domain_scope = set(c_dict.get("domain_scope") or [])
        target_objects = set(c_dict.get("target_objects") or [])
        protected_set = set(c_dict.get("protected_set") or [])
        protected_flags = set(c_dict.get("protected_flags") or [])

        protected_values = {
            str(k): float(v) for k, v in (c_dict.get("protected_values") or {}).items()
        }
        max_bounds = {
            str(k): float(v) for k, v in (c_dict.get("max_bounds") or {}).items()
        }
        min_bounds = {
            str(k): float(v) for k, v in (c_dict.get("min_bounds") or {}).items()
        }
        units = {
            str(k): str(v) for k, v in (c_dict.get("units") or {}).items()
        }
        forbidden_flags = {
            str(k): bool(v) for k, v in (c_dict.get("forbidden_flags") or {}).items()
        }
        required_flags = {
            str(k): bool(v) for k, v in (c_dict.get("required_flags") or {}).items()
        }

        return ConstraintPrimitive(
            domain_scope=domain_scope,
            target_objects=target_objects,
            protected_set=protected_set,
            protected_values=protected_values,
            max_bounds=max_bounds,
            min_bounds=min_bounds,
            units=units,
            protected_flags=protected_flags,
            forbidden_flags=forbidden_flags,
            required_flags=required_flags,
        )

    def _parse_dissipate(self, d_dict: Dict[str, Any]) -> DissipatePrimitive:
        loss_domain = set(d_dict.get("loss_domain") or [])
        target_states = set(d_dict.get("target_states") or [])
        side_effects = set(d_dict.get("side_effects") or [])

        resource_cost = {
            str(k): float(v) for k, v in (d_dict.get("resource_cost") or {}).items()
        }
        state_delta = {
            str(k): float(v) for k, v in (d_dict.get("state_delta") or {}).items()
        }
        flag_delta = {
            str(k): bool(v) for k, v in (d_dict.get("flag_delta") or {}).items()
        }
        units = {
            str(k): str(v) for k, v in (d_dict.get("units") or {}).items()
        }

        return DissipatePrimitive(
            loss_domain=loss_domain,
            target_states=target_states,
            side_effects=side_effects,
            resource_cost=resource_cost,
            state_delta=state_delta,
            flag_delta=flag_delta,
            units=units,
        )

    def _parse_initial_state(self, s_dict: Dict[str, Any]) -> SystemState:
        current_values = {
            str(k): float(v) for k, v in (s_dict.get("current_values") or {}).items()
        }
        active_flags = {
            str(k): bool(v) for k, v in (s_dict.get("active_flags") or {}).items()
        }
        units = {
            str(k): str(v) for k, v in (s_dict.get("units") or {}).items()
        }

        return SystemState(
            current_values=current_values,
            active_flags=active_flags,
            units=units,
        )

    def _resolve_registry(
        self,
        data: Dict[str, Any],
        override_registry: Optional[EvidenceRegistryOracle],
    ) -> Optional[EvidenceRegistryOracle]:
        """
        Public ingress registry resolver.
        Strictly enforces trusted registry: uses override_registry if provided,
        otherwise falls back to self.default_registry (or self.engine.registry).
        Untrusted inline 'evidence_records' in client JSON payload are NEVER registered
        into the active verification registry.
        """
        if override_registry is not None:
            return override_registry
        if self.default_registry is not None:
            return self.default_registry
        return self.engine.registry if self.engine is not None else None

    @staticmethod
    def create_test_registry(records: List[Dict[str, Any]]) -> InMemoryEvidenceRegistry:
        """
        Explicit helper for test environments: parses raw record dictionaries into
        an InMemoryEvidenceRegistry instance.
        Must be explicitly provided to SolTriadJsonAdapter(default_registry=...) or
        evaluate_json(registry=...) by a trusted host/test runner.
        """
        mem_reg = InMemoryEvidenceRegistry()
        for rec_dict in records:
            try:
                rec = EvidenceRecord(
                    evidence_id=str(rec_dict["evidence_id"]),
                    domain=str(rec_dict["domain"]),
                    epistemic_status=EpistemicStatus(rec_dict["epistemic_status"]),
                    timestamp_sec=float(rec_dict["timestamp_sec"]),
                    payload_hash=rec_dict.get("payload_hash"),
                    metadata=rec_dict.get("metadata", {}),
                )
                mem_reg.register(rec)
            except Exception:
                pass  # Ignore malformed test records
        return mem_reg

    def _format_response(
        self,
        request_id: str,
        report: EvaluationReport,
    ) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "protocol_version": self.PROTOCOL_VERSION,
            "engine_version": report.engine_version,
            "verdict": report.verdict.value,
            "pairwise_checks": {
                k: v.as_dict() for k, v in report.pairwise_checks.items()
            },
            "diagnostics": [d.as_dict() for d in report.diagnostics],
            "simulated_values": report.simulated_values,
            "simulated_flags": report.simulated_flags,
            "evaluation_timestamp": report.timestamp_sec,
            "messages": [f"[{d.code.value}] {d.message}" for d in report.diagnostics],
        }

    def _create_fail_response(
        self,
        request_id: str,
        message: str,
        code: DiagnosticCode = DiagnosticCode.STRUCTURAL_DEFECT,
        primitive: Optional[str] = None,
        field_name: Optional[str] = None,
        timestamp_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        ts = timestamp_sec if timestamp_sec is not None else time.time()
        diag = CoherenceDiagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            primitive=primitive,
            field_name=field_name,
        )
        fail_pairwise = {
            rel: {
                "relationship": rel,
                "is_valid": False,
                "verdict": CoherenceVerdict.FAIL.value,
                "diagnostics": [diag.as_dict()],
            }
            for rel in ("P_SC", "P_CD", "P_SD")
        }
        return {
            "request_id": request_id,
            "protocol_version": self.PROTOCOL_VERSION,
            "engine_version": SolTriadEngine.VERSION,
            "verdict": CoherenceVerdict.FAIL.value,
            "pairwise_checks": fail_pairwise,
            "diagnostics": [diag.as_dict()],
            "simulated_values": {},
            "simulated_flags": {},
            "evaluation_timestamp": ts,
            "messages": [f"[{code.value}] {message}"],
        }
