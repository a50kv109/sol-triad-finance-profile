"""
Модели данных специализированного финансового профиля (Finance FX Profile).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class TaskRequest:
    """Заявка агента на проведение конверсионного валютного платежа."""
    request_id: str
    source_account_id: str
    destination_account_id: str
    amount_source: float
    currency_source: str
    amount_target: float
    currency_target: str
    quoted_rate: float
    evidence_quote_id: str
    requested_loss_domain: str = "funds_transfer"  # Запрашиваемый агентом домен потерь


# Сохраняем обратную совместимость с именованием FinancePaymentRequest
FinancePaymentRequest = TaskRequest


@dataclass
class HostPolicy:
    """Доверенная финансовая политика и параметры безопасности хоста."""
    authorized_account_id: str
    authorized_loss_domain: str = "funds_transfer"  # Авторизованный хостом домен потерь
    max_transaction_amount: float = 10000.0
    current_balance: float = 50000.0
    evaluation_time: float = 1740000000.0  # Доверенное системное время хоста
    currency: str = "USD"


@dataclass
class FxPaymentResult:
    """Результат верификации финансового платежа."""
    request_id: str
    status: str            # "SUCCESS" | "REVIEW" | "REJECTED" | "ADAPTER_REJECTED"
    verdict: str           # "PASS" | "REVIEW" | "FAIL"
    source_delta: float
    target_delta: float
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    execution_permitted: bool = False  # Строго False! Адаптер ядра НЕ осуществляет проводку денег.
