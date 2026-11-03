"""
Канонический универсальный JSON-шлюз SOL-Triad (SolTriadJsonGateway).
Обеспечивает структурную валидацию, защиту от инъекций и двусторонний перевод JSON-сообщений.
"""

import json
from typing import Dict, Any, Union, Optional, Set

from sol_triad_core import (
    SolTriadCoreKernel,
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRegistryOracle,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    DiagnosticSeverity,
)


class SolTriadJsonGateway:
    """
    Универсальный JSON-адаптер к каноническому ядру.
    
    Гарантии безопасности:
      1. Безусловное отклонение JSON-нагрузок, содержащих 'evaluation_time' или 'evidence_records'.
      2. Полное отсутствие параметров вроде 'trusted_host_context' в API вызова.
      3. Строгий Fail-Closed при любых структурных дефектах JSON.
      4. Возвращаемый результат всегда содержит execution_permitted: False.
    """

    def __init__(
        self,
        kernel: Optional[SolTriadCoreKernel] = None,
        default_registry: Optional[EvidenceRegistryOracle] = None
    ):
        self.kernel = kernel or SolTriadCoreKernel()
        self.default_registry = default_registry

    def evaluate_json(
        self,
        request_input: Union[str, Dict[str, Any]],
        evaluation_time: Optional[float] = None,
        registry: Optional[EvidenceRegistryOracle] = None
    ) -> Dict[str, Any]:
        """
        Верифицирует JSON-запрос к ядру.
        
        Параметры:
          request_input: JSON-строка или словарь с полями {request_id, protocol_version, source, constraint, dissipate, initial_state}.
          evaluation_time: ДОВЕРЕННОЕ системное время хоста. Запрещено передавать внутри request_input!
          registry: ДОВЕРЕННЫЙ реестр доказательств хоста.
        """
        # 1. Парсинг строки JSON в словарь
        if isinstance(request_input, str):
            try:
                req_dict = json.loads(request_input)
            except Exception as e:
                return self._build_fail_response(
                    request_id="malformed_json",
                    diagnostics=[{
                        "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                        "severity": DiagnosticSeverity.ERROR.value,
                        "message": f"Malformed JSON: {str(e)}",
                        "primitive": "GATEWAY",
                        "field_name": None
                    }]
                )
        elif isinstance(request_input, dict):
            req_dict = request_input
        else:
            return self._build_fail_response(
                request_id="invalid_type",
                diagnostics=[{
                    "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"Expected JSON string or dict, got {type(request_input).__name__}",
                    "primitive": "GATEWAY",
                    "field_name": None
                }]
            )

        # 2. Безусловная блокировка инъекции доверенных полей хоста через недоверенный JSON
        forbidden_injected_fields = [k for k in ("evaluation_time", "evidence_records") if k in req_dict]
        if forbidden_injected_fields:
            return self._build_fail_response(
                request_id=str(req_dict.get("request_id", "rejected_payload")),
                diagnostics=[{
                    "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"Untrusted payload cannot inject host fields: {forbidden_injected_fields}. "
                               f"evaluation_time and evidence_records must only be supplied by host context.",
                    "primitive": "GATEWAY",
                    "field_name": None
                }]
            )

        # 3. Валидация базовых полей запроса
        req_id = req_dict.get("request_id")
        if not req_id:
            return self._build_fail_response(
                request_id="missing_request_id",
                diagnostics=[{
                    "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": "Missing required field: 'request_id'",
                    "primitive": "GATEWAY",
                    "field_name": "request_id"
                }]
            )

        proto_ver = req_dict.get("protocol_version")
        if proto_ver not in ("1.0.0-canonical", "0.4.0"):
            return self._build_fail_response(
                request_id=str(req_id),
                diagnostics=[{
                    "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"Unsupported protocol_version '{proto_ver}'. Supported: '1.0.0-canonical', '0.4.0'",
                    "primitive": "GATEWAY",
                    "field_name": "protocol_version"
                }]
            )

        # Проверка обязательных примитивов
        for prim_name in ("source", "constraint", "dissipate", "initial_state"):
            if prim_name not in req_dict or not isinstance(req_dict[prim_name], dict):
                return self._build_fail_response(
                    request_id=str(req_id),
                    diagnostics=[{
                        "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                        "severity": DiagnosticSeverity.ERROR.value,
                        "message": f"Missing or invalid required primitive: '{prim_name}'",
                        "primitive": "GATEWAY",
                        "field_name": prim_name
                    }]
                )

        # 4. Десериализация канонических примитивов
        try:
            source = self._parse_source(req_dict["source"])
            constraint = self._parse_constraint(req_dict["constraint"])
            dissipate = self._parse_dissipate(req_dict["dissipate"])
            initial_state = self._parse_initial_state(req_dict["initial_state"])
        except Exception as e:
            return self._build_fail_response(
                request_id=str(req_id),
                diagnostics=[{
                    "code": DiagnosticCode.STRUCTURAL_DEFECT.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"Failed to parse canonical primitives: {str(e)}",
                    "primitive": "GATEWAY",
                    "field_name": None
                }]
            )

        # 5. Разрешение реестра и вызов ядра
        active_registry = registry if registry is not None else self.default_registry
        report = self.kernel.evaluate(
            source=source,
            constraint=constraint,
            dissipate=dissipate,
            initial_state=initial_state,
            evaluation_time_sec=evaluation_time,
            registry=active_registry
        )

        res = report.to_dict()
        res["request_id"] = str(req_id)
        return res

    def _parse_source(self, data: Dict[str, Any]) -> SourcePrimitive:
        def _to_set(val: Any) -> Optional[Set[str]]:
            if val is None:
                return None
            return set(val)

        ep_str = data.get("epistemic_type", "UNKNOWN")
        try:
            ep_status = EpistemicStatus(ep_str)
        except ValueError:
            raise ValueError(f"Invalid epistemic_type '{ep_str}'")

        return SourcePrimitive(
            evidence_id=str(data.get("evidence_id", "")),
            authority_domain=_to_set(data.get("authority_domain")),
            granted_scope=_to_set(data.get("granted_scope")),
            granted_loss_domains=_to_set(data.get("granted_loss_domains")),
            epistemic_type=ep_status,
            timestamp_sec=float(data.get("timestamp_sec", 0.0)),
            max_age_sec=float(data.get("max_age_sec", 300.0)),
            payload_hash=data.get("payload_hash"),
            corroborating_evidence_ids=set(data.get("corroborating_evidence_ids", [])),
            metadata=dict(data.get("metadata", {}))
        )

    def _parse_constraint(self, data: Dict[str, Any]) -> ConstraintPrimitive:
        return ConstraintPrimitive(
            domain_scope=set(data.get("domain_scope", [])),
            target_objects=set(data.get("target_objects", [])),
            protected_set=set(data.get("protected_set", [])),
            min_bounds={k: float(v) for k, v in data.get("min_bounds", {}).items()},
            max_bounds={k: float(v) for k, v in data.get("max_bounds", {}).items()},
            protected_values={k: float(v) for k, v in data.get("protected_values", {}).items()},
            protected_flags=set(data.get("protected_flags", [])),
            forbidden_flags={k: bool(v) for k, v in data.get("forbidden_flags", {}).items()} if isinstance(data.get("forbidden_flags"), dict) else {f: True for f in data.get("forbidden_flags", [])},
            required_flags={k: bool(v) for k, v in data.get("required_flags", {}).items()} if isinstance(data.get("required_flags"), dict) else {f: True for f in data.get("required_flags", [])},
            units=dict(data.get("units", {}))
        )

    def _parse_dissipate(self, data: Dict[str, Any]) -> DissipatePrimitive:
        flag_muts = data.get("flag_delta", data.get("flag_mutations", {}))
        return DissipatePrimitive(
            loss_domain=set(data.get("loss_domain", [])),
            target_states=set(data.get("target_states", [])),
            side_effects=set(data.get("side_effects", [])),
            resource_cost={k: float(v) for k, v in data.get("resource_cost", {}).items()},
            state_delta={k: float(v) for k, v in data.get("state_delta", {}).items()},
            flag_mutations={k: bool(v) for k, v in flag_muts.items()},
            units=dict(data.get("units", {}))
        )

    def _parse_initial_state(self, data: Dict[str, Any]) -> SystemState:
        return SystemState(
            current_values={k: float(v) for k, v in data.get("current_values", {}).items()},
            active_flags={k: bool(v) for k, v in data.get("active_flags", {}).items()},
            units=dict(data.get("units", {}))
        )

    def _build_fail_response(self, request_id: str, diagnostics: list) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "protocol_version": "1.0.0-canonical",
            "verdict": CoherenceVerdict.FAIL.value,
            "pairwise_checks": {
                "P_SC": {"is_valid": False, "verdict": CoherenceVerdict.FAIL.value, "diagnostics": diagnostics},
                "P_SD": {"is_valid": False, "verdict": CoherenceVerdict.FAIL.value, "diagnostics": []},
                "P_CD": {"is_valid": False, "verdict": CoherenceVerdict.FAIL.value, "diagnostics": []},
            },
            "simulated_values": {},
            "simulated_flags": {},
            "diagnostics": diagnostics,
            "execution_permitted": False
        }
