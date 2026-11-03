# Контракт интеграции с ядром (Integration Contract)

**Статус:** Описание интеграционного моста

---

## 1. Роль и обязанности `FinanceFxAdapter`

Адаптер финансового профиля выступает связующим звеном между финансовым приложением и ядром `sol-triad-core`.

### Поток данных и преобразований:
```
[ Financial Product ] ──► [ FinanceFxAdapter ] ──► [ SOL-Triad Core ] ──► [ FxPaymentResult ] ──► [ External Controller ]
```

1. **Приём входных данных:** Адаптер принимает `TaskRequest` от агента и доверенную структуру `HostPolicy` от хоста.
2. **Проверка границ до вызова ядра:**
   - Сверяет `source_account_id` с `authorized_account_id`.
   - Проверяет нетавтологичность домена потерь: `task_req.requested_loss_domain == policy.authorized_loss_domain`. При несовпадении отклоняет запрос со статусом `ADAPTER_REJECTED` до обращения к ядру.
   - Проверяет математическую корректность расчёта суммы и курса.
3. **Трансляция в канонические примитивы ядра:**
   - **SOURCE ($S$):** Отражает свидетельство котировки из реестра хоста (`evidence_quote_id`), статус `FACT`, время и хэш.
   - **CONSTRAINT ($C$):** Устанавливает минимальную границу баланса счёта ($B_{\min} = 0.0$ для запрета овердрафта) и разрешённые домены.
   - **DISSIPATE ($D$):** Задаёт дельту списания со счёта (`state_delta = {account: -amount}`).
   - **INITIAL STATE ($S_0$):** Передаёт текущий баланс счёта из `HostPolicy.current_balance`.
4. **Вызов ядра с доверенными параметрами:** Передаёт `evaluation_time=policy.evaluation_time` и `registry=host_registry`.
5. **Формирование результата:** Возвращает `FxPaymentResult` с полем `execution_permitted = False`.
