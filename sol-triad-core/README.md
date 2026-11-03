# SOL-Triad Core (Ядро SOL-Triad)

**Каноническое, переносимое, детерминированное ядро верификации согласованности действий (Coherence Verification Kernel)**

Версия спецификации ядра: **1.0.0-canonical**  
Эталонная реализация: **Python 3.9+ (Zero-Dependency Reference Implementation)**

---

## 1. Миссия и границы ядра

### Что гарантирует ядро (Guarantees):
1. **Математическая и логическая строгость:** Проверка предлагаемых действий против аксиом теории множеств (вхождение полномочий, непересечение с защищёнными параметрами), предикатной логики и алгебры физических размерностей.
2. **Детерминизм:** При одинаковых канонических входах $(S, C, D, S_0, t_{eval}, \text{Registry})$ ядро всегда возвращает строго идентичный вердикт (`PASS`, `REVIEW`, `FAIL`), неизменные парные статусы ($P_{SC}, P_{CD}, P_{SD}$) и эквивалентный набор диагностических кодов.
3. **Бескомпромиссный принцип Fail-Closed:** Любая неопределённость, повреждение структуры, деление на ноль, нечисловые значения ($NaN, \pm\infty$), отсутствие свидетельств в доверенном реестре или отсутствие прав трактуются как `FAIL`. Эпистемическое устаревание свидетельств без нарушений инвариантов трактуется строго как `REVIEW`.
4. **Невозможность самоприсвоения доверия:** Ядро не принимает доверенные данные (время оценки $t_{eval}$, авторитетный реестр свидетельств) из недоверенного контекста или пользовательского ввода.
5. **Языковая и продуктовая независимость:** Ядро не содержит специфики финансов, робототехники, веб-фреймворков или протоколов связи. Любое подключение к продуктам выполняется через внешние изолированные адаптеры.

### Чего ядро принципиально НЕ делает (Non-Goals):
1. **Не исполняет действия (No Execution):** Ядро — чистый валидатор-симулятор. Оно никогда не переводит деньги, не отправляет сигналы контроллерам, не мутирует внешнюю память и не вызывает внешние API.
2. **Не выдаёт «разрешений на действие»:** Поле `execution_permitted` во всех отчётах ядра отсутствует либо жёстко равно `False`. Разрешение и физическое исполнение — исключительная прерогатива внешнего Исполнительного Контроллера (Execution Controller) хоста.
3. **Не заменяет эвристики и планировщики (No Planning/No LLM):** Ядро не генерирует планы и не оптимизирует пути; оно лишь проверяет предложенный план на допустимость и когерентность.
4. **Не вычисляет самостоятельно криптографические хэши сырых бинарных тел:** Ядро проверяет равенство строковых маркеров хэшей свидетельств с авторитетным реестром, но доверенное вычисление хэшей данных возлагается на источник свидетельства.

---

## 2. Архитектура триады SOL

В основе верификации лежит концепция триады сущностей:

```
                  ┌────────────────────────┐
                  │    SOURCE (S)          │
                  │ Обоснование и мандат   │
                  └───────────┬────────────┘
                             / \
                            /   \
                 P_SC      /     \     P_SD
       (Grounding & Scope)/       \(Loss Scope)
                         /         \
                        /           \
     ┌─────────────────▼──┐       ┌──▼─────────────────┐
     │  CONSTRAINT (C)    │       │   DISSIPATE (D)    │
     │  Границы и условия │◄─────►│   Действие и дельта│
     └────────────────────┘ P_CD  └────────────────────┘
                      (Invariant & State)
```

1. **SOURCE ($S$):** Эпистемический базис и полномочия. Указывает `evidence_id`, авторитетный домен, разрешённые объекты воздействия (`granted_scope`), разрешённые домены потерь (`granted_loss_domains`), временной штамп и хэш полезной нагрузки.
2. **CONSTRAINT ($C$):** Защитный периметр и физические ограничения. Задаёт домен применимости, целевые объекты, защищённые параметры (`protected_set`), защищённые/запрещённые флаги, допустимые диапазоны (`min_bounds`, `max_bounds`) и инвариантные константы.
3. **DISSIPATE ($D$):** Предлагаемое действие (вектор возмущения). Содержит домен потерь (`loss_domain`), целевые состояния, побочные эффекты, затраты ресурсов, дельты непрерывных величин (`state_delta`) и мутации флагов.
4. **INITIAL STATE ($S_0$):** Базовое состояние системы на момент оценки (числовые параметры, флаги, единицы измерения).

---

## 3. Быстрый старт

### Требования
- Python 3.9 или выше.
- Стандартная библиотека Python (нет внешних зависимостей для ядра и тестов).

### Запуск тестов ядра и адаптеров
```bash
# Из корневой папки репозитория:
python3 tests/run_all_tests.py
```

### Минимальный пример использования ядра
```python
from sol_triad_core import (
    SolTriadCoreKernel,
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict
)

# 1. Хост инициализирует доверенный реестр и время оценки
now = 1740000000.0
registry = InMemoryEvidenceRegistry()
registry.register(EvidenceRecord(
    evidence_id="ev-telemetry-01",
    domain="power_grid",
    epistemic_status=EpistemicStatus.FACT,
    timestamp_sec=now - 5.0,
    payload_hash="sha256-hash-ok"
))

# 2. Формируются примитивы триады
source = SourcePrimitive(
    evidence_id="ev-telemetry-01",
    authority_domain={"power_grid"},
    granted_scope={"generator_substation_4"},
    granted_loss_domains={"electrical_load"},
    epistemic_type=EpistemicStatus.FACT,
    timestamp_sec=now - 5.0,
    max_age_sec=60.0,
    payload_hash="sha256-hash-ok"
)

constraint = ConstraintPrimitive(
    domain_scope={"power_grid"},
    target_objects={"generator_substation_4"},
    protected_set={"emergency_cutoff_relay"},
    max_bounds={"grid_voltage_kv": 115.0},
    min_bounds={"grid_voltage_kv": 105.0},
    units={"grid_voltage_kv": "volt"}
)

dissipate = DissipatePrimitive(
    loss_domain={"electrical_load"},
    state_delta={"grid_voltage_kv": 2.0},
    units={"grid_voltage_kv": "volt"}
)

initial_state = SystemState(
    current_values={"grid_voltage_kv": 110.0},
    units={"grid_voltage_kv": "volt"}
)

# 3. Детерминированная верификация ядром
kernel = SolTriadCoreKernel()
report = kernel.evaluate(
    source=source,
    constraint=constraint,
    dissipate=dissipate,
    initial_state=initial_state,
    evaluation_time_sec=now,
    registry=registry
)

print(f"Вердикт: {report.verdict.value}")  # PASS
print(f"Конечное напряжение: {report.simulated_values['grid_voltage_kv']} kV")  # 112.0
assert report.verdict == CoherenceVerdict.PASS
```

---

## 4. Структура репозитория

```
sol-triad-core/
├── README.md                          # Данный документ: миссия, архитектура, быстрый старт
├── SPECIFICATION.md                   # Нормативная языконезависимая спецификация ядра v1.0
├── docs/
│   ├── CANONICAL_MODEL.md             # Каноническая модель данных и интерфейсы
│   ├── TRUST_BOUNDARIES.md            # Анализ границ доверия и модель угроз
│   ├── ERROR_HANDLING.md              # Классификация диагностик, ошибок и граничных случаев
│   ├── ADAPTER_CONFORMANCE.md         # Руководство по разработке конформных адаптеров
│   └── KNOWN_LIMITATIONS.md           # Известные ограничения и вопросы на согласование
├── schemas/
│   ├── sol_triad_canonical_request.schema.json  # JSON-схема входа ядра
│   └── sol_triad_canonical_response.schema.json # JSON-схема выхода ядра
├── src/
│   └── sol_triad_core/                # Чистое эталонное ядро (Reference Implementation)
│       ├── __init__.py
│       ├── models.py                  # Примитивы триады и структуры данных
│       ├── kernel.py                  # Канонический детерминированный движок
│       ├── evidence.py                # Интерфейс и память реестра свидетельств
│       ├── validators.py              # Валидаторы P_SC, P_SD, P_CD
│       ├── units.py                   # Алгебра размерностей и конверсии
│       └── errors.py                  # Диагностические коды и исключения
├── adapters/                          # Внешние адаптеры (НЕ часть ядра)
│   ├── __init__.py
│   ├── json_adapter/                  # Универсальный JSON-шлюз с защитой от инъекций
│   │   ├── __init__.py
│   │   └── adapter.py
│   └── finance_fx_adapter/            # Продуктовый адаптер профиля валютных платежей
│       ├── __init__.py
│       ├── models.py
│       └── adapter.py
├── tests/                             # Автономный тестовый комплект
│   ├── run_all_tests.py               # Единый раннер всех тестов
│   ├── unit/                          # Модульные тесты компонентов ядра
│   ├── security/                      # Тесты границ доверия, анти-байпаса и детерминизма
│   └── adapters/                      # Тесты адаптеров (JSON и Finance FX)
├── examples/                          # Примеры применения
│   ├── minimal_kernel_usage.py        # Прямое использование ядра
│   └── fx_payment_pipeline_demo.py    # Сквозной цикл интеграции через адаптер
└── pyproject.toml                     # Метаданные пакета
```
