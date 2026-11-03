"""
Адаптер специализированного финансового профиля (Finance FX Adapter).
Транслирует валютный платеж в канонические примитивы SOL-Triad Core и обратно.
"""

from typing import Optional, Dict, Any, List

from sol_triad_core import (
    EvidenceRegistryOracle,
    CoherenceVerdict,
    DiagnosticCode,
    DiagnosticSeverity,
)
from adapters.json_adapter import SolTriadJsonGateway
from .models import TaskRequest, HostPolicy, FxPaymentResult


class FinanceFxAdapter:
    """
    Продуктовый адаптер профиля валютных платежей.
    
    Гарантии:
      1. Заявка агента (TaskRequest) отделена от доверенной политики хоста (HostPolicy).
      2. Несовпадение запрашиваемого домена потерь (requested_loss_domain) с политикой отсекается до ядра.
      3. Время оценки и балансы извлекаются строго из HostPolicy.
      4. Котировка верифицируется через host_registry.
      5. Проводка реальных средств заблокирована (execution_permitted=False).
    """

    def __init__(self, json_gateway: Optional[SolTriadJsonGateway] = None):
        self.gateway = json_gateway or SolTriadJsonGateway()

    def process_payment(
        self,
        task_req: TaskRequest,
        policy: HostPolicy,
        host_registry: EvidenceRegistryOracle
    ) -> FxPaymentResult:
        # Шаг 0: Валидация типов аргументов (защита от неявного вызова)
        if not isinstance(task_req, TaskRequest):
            return self._build_adapter_rejection(
                task_req.request_id if hasattr(task_req, "request_id") else "invalid_request",
                f"task_req must be an instance of TaskRequest, got {type(task_req).__name__}"
            )
        if not isinstance(policy, HostPolicy):
            return self._build_adapter_rejection(
                task_req.request_id,
                f"policy must be an instance of HostPolicy, got {type(policy).__name__}"
            )

        # Шаг 1a: Базовая валидация параметров платежа
        if task_req.source_account_id != policy.authorized_account_id:
            return self._build_adapter_rejection(
                task_req.request_id,
                f"Unauthorized source account: {task_req.source_account_id} != policy {policy.authorized_account_id}"
            )

        if task_req.amount_source <= 0 or task_req.amount_target <= 0 or task_req.quoted_rate <= 0:
            return self._build_adapter_rejection(
                task_req.request_id,
                "Payment amounts and exchange rate must be strictly positive."
            )

        # Шаг 1b: Проверка нетавтологичного домена потерь
        if task_req.requested_loss_domain != policy.authorized_loss_domain:
            return FxPaymentResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                verdict=CoherenceVerdict.FAIL.value,
                source_delta=0.0,
                target_delta=0.0,
                diagnostics=[{
                    "code": DiagnosticCode.UNAUTHORIZED_LOSS_DOMAIN.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"Requested loss domain '{task_req.requested_loss_domain}' is not authorized by host policy '{policy.authorized_loss_domain}'.",
                    "primitive": "ADAPTER",
                    "field_name": "requested_loss_domain"
                }],
                execution_permitted=False
            )

        # Шаг 2: Проверка математической формулы конверсии в шлюзе
        expected_target = round(task_req.amount_source * task_req.quoted_rate, 4)
        if abs(task_req.amount_target - expected_target) > 0.01:
            return self._build_adapter_rejection(
                task_req.request_id,
                f"Conversion calculation mismatch: {task_req.amount_source} * {task_req.quoted_rate} = {expected_target}, got {task_req.amount_target}"
            )

        # Шаг 3: Поиск котировки в доверенном реестре хоста
        quote_rec = host_registry.lookup(task_req.evidence_quote_id)
        if not quote_rec:
            return FxPaymentResult(
                request_id=task_req.request_id,
                status="REJECTED",
                verdict=CoherenceVerdict.FAIL.value,
                source_delta=0.0,
                target_delta=0.0,
                diagnostics=[{
                    "code": DiagnosticCode.EVIDENCE_NOT_FOUND.value,
                    "severity": DiagnosticSeverity.ERROR.value,
                    "message": f"FX Quote evidence '{task_req.evidence_quote_id}' not found in authoritative host registry.",
                    "primitive": "SOURCE",
                    "field_name": "evidence_id"
                }],
                execution_permitted=False
            )

        # Шаг 4: Трансляция в канонический запрос SOL-Triad
        triad_request = {
            "request_id": task_req.request_id,
            "protocol_version": "1.0.0-canonical",
            "source": {
                "evidence_id": task_req.evidence_quote_id,
                "authority_domain": ["finance_fx", "funds_transfer"],
                "granted_scope": [task_req.source_account_id, task_req.destination_account_id],
                "granted_loss_domains": [policy.authorized_loss_domain],
                "epistemic_type": quote_rec.epistemic_status.value,
                "timestamp_sec": quote_rec.timestamp_sec,
                "max_age_sec": 300.0,
                "payload_hash": quote_rec.payload_hash,
                "corroborating_evidence_ids": []
            },
            "constraint": {
                "domain_scope": ["finance_fx"],
                "target_objects": [task_req.source_account_id],
                "protected_set": [],
                "min_bounds": {
                    task_req.source_account_id: 0.0  # Запрет овердрафта
                },
                "max_bounds": {},
                "protected_values": {},
                "protected_flags": [],
                "forbidden_flags": [],
                "required_flags": [],
                "units": {
                    task_req.source_account_id: "usd"
                }
            },
            "dissipate": {
                "loss_domain": [task_req.requested_loss_domain],
                "target_states": [task_req.destination_account_id],
                "side_effects": [],
                "resource_cost": {},
                "state_delta": {
                    task_req.source_account_id: -task_req.amount_source
                },
                "flag_mutations": {},
                "units": {
                    task_req.source_account_id: "usd"
                }
            },
            "initial_state": {
                "current_values": {
                    task_req.source_account_id: policy.current_balance
                },
                "active_flags": {},
                "units": {
                    task_req.source_account_id: "usd"
                }
            }
        }

        # Шаг 5: Вызов ядра через универсальный JSON-шлюз с доверенными временем и реестром хоста
        eval_response = self.gateway.evaluate_json(
            request_input=triad_request,
            evaluation_time=policy.evaluation_time,
            registry=host_registry
        )

        verdict = eval_response.get("verdict", CoherenceVerdict.FAIL.value)
        diagnostics = eval_response.get("diagnostics", [])

        if verdict == CoherenceVerdict.PASS.value:
            status = "SUCCESS"
        elif verdict == CoherenceVerdict.REVIEW.value:
            status = "REVIEW"
        else:
            status = "REJECTED"

        return FxPaymentResult(
            request_id=task_req.request_id,
            status=status,
            verdict=verdict,
            source_delta=-task_req.amount_source if verdict == "PASS" else 0.0,
            target_delta=task_req.amount_target if verdict == "PASS" else 0.0,
            diagnostics=diagnostics,
            execution_permitted=False
        )

    def _build_adapter_rejection(self, request_id: str, message: str) -> FxPaymentResult:
        return FxPaymentResult(
            request_id=request_id,
            status="ADAPTER_REJECTED",
            verdict=CoherenceVerdict.FAIL.value,
            source_delta=0.0,
            target_delta=0.0,
            diagnostics=[{
                "code": DiagnosticCode.ADAPTER_REJECTED.value,
                "severity": DiagnosticSeverity.ERROR.value,
                "message": message,
                "primitive": "ADAPTER",
                "field_name": None
            }],
            execution_permitted=False
        )
