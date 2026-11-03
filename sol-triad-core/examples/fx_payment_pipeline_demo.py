"""
Пример сквозной интеграции через специализированный адаптер:
Продукт (Валютный платёж) -> Адаптер (Finance FX) -> Ядро (SOL-Triad) -> Контроллер Хоста.
"""

import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, BASE_DIR)

from sol_triad_core import (
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
)
from adapters.finance_fx_adapter import (
    TaskRequest,
    HostPolicy,
    FinanceFxAdapter,
)


def main():
    print("=" * 75)
    print("   Сквозной интеграционный стенд: Продукт -> Адаптер -> Ядро -> Контроллер")
    print("=" * 75)

    # 1. Хост инициализирует доверенный реестр банковских котировок
    now = 1740000000.0
    host_registry = InMemoryEvidenceRegistry()
    host_registry.register(EvidenceRecord(
        evidence_id="ecb-quote-eur-usd-live",
        domain="finance_fx",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 15.0,
        payload_hash="sha256-ecb-live-digest"
    ))

    # 2. Доверенная политика хоста
    host_policy = HostPolicy(
        authorized_account_id="CLIENT_ACC_EUR_42",
        authorized_loss_domain="funds_transfer",
        max_transaction_amount=10000.0,
        current_balance=2500.0,
        evaluation_time=now,
        currency="USD"
    )

    # 3. Агент формирует заявку на перевод
    agent_request = TaskRequest(
        request_id="tx-eur-to-usd-991",
        source_account_id="CLIENT_ACC_EUR_42",
        destination_account_id="SUPPLIER_ACC_USD_10",
        amount_source=500.0,
        currency_source="EUR",
        amount_target=542.50,
        currency_target="USD",
        quoted_rate=1.085,
        evidence_quote_id="ecb-quote-eur-usd-live",
        requested_loss_domain="funds_transfer"
    )

    print("\n1. Заявка агента (TaskRequest):")
    print(f"   Списание: {agent_request.amount_source} {agent_request.currency_source}")
    print(f"   Зачисление: {agent_request.amount_target} {agent_request.currency_target} (курс {agent_request.quoted_rate})")
    print(f"   Свидетельство котировки: {agent_request.evidence_quote_id}")

    # 4. Вызов адаптера (Finance FX Adapter)
    adapter = FinanceFxAdapter()
    result = adapter.process_payment(
        task_req=agent_request,
        policy=host_policy,
        host_registry=host_registry
    )

    print("\n2. Ответ адаптера / ядра (FxPaymentResult):")
    print(f"   Статус:  {result.status}")
    print(f"   Вердикт: {result.verdict}")
    print(f"   Дельта счёта источника: {result.source_delta}")
    print(f"   Дельта счёта получателя: {result.target_delta}")
    print(f"   Разрешение на проводку средств в ядре: {result.execution_permitted} (СТРОГО FALSE)")

    # 5. Внешний Исполнительный Контроллер Хоста (Host Execution Controller)
    print("\n3. Решение Исполнительного Контроллера Хоста (Host Execution Controller):")
    if result.verdict == "PASS" and result.status == "SUCCESS":
        print("   [КОНТРОЛЛЕР ХОСТА]: Проверка согласованности пройдена. Подтверждаем клиринг и списываем средства.")
        executed = True
    elif result.verdict == "REVIEW":
        print("   [КОНТРОЛЛЕР ХОСТА]: Неопределённость или устаревание данных. Направляем на ручной контроль комплаенс.")
        executed = False
    else:
        print("   [КОНТРОЛЛЕР ХОСТА]: ОТКАЗ. Транзакция заблокирована.")
        executed = False

    assert executed is True
    print("\nСтенд успешно завершил работу.")


if __name__ == "__main__":
    main()
