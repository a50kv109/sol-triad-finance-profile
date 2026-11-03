# Каноническая модель данных и интерфейсы SOL-Triad Core

**Статус:** Канонический контракт (Canonical Data Model & Contract Definition)

---

## 1. Канонический контракт входа ядра (`EvaluationContext`)

Ядро принимает на вход строго типизированный кортеж или эквивалентную неизменяемую структуру:

```python
EvaluationContext:
  source: SourcePrimitive                # [Недоверенный запрос / Заявка агента]
  constraint: ConstraintPrimitive        # [Спецификация границ и ограничений]
  dissipate: DissipatePrimitive          # [Предлагаемое воздействие / Дельта]
  initial_state: SystemState             # [Базовое состояние параметров]
  evaluation_time_sec: float             # [ДОВЕРЕННОЕ: Время хоста]
  registry: Optional[EvidenceRegistry]   # [ДОВЕРЕННОЕ: Авторитетный реестр хоста]
```

### Источники происхождения данных:
| Поле входа | Источник | Уровень доверия | Правило проверки |
|---|---|---|---|
| `source` | Агент / Заявитель | **Недоверенный** | Верифицируется против реестра $\mathcal{R}$ и времени $t_{eval}$ |
| `constraint` | Хост / Политика / Спецификация | **Контекстно-доверенный** | Проверяется на вхождение в полномочия $S$ |
| `dissipate` | Агент / Планировщик | **Недоверенный** | Симулируется и проверяется на непересечение с $C$ |
| `initial_state` | Среда / Датчики хоста | **Доверенный** | Проверяется на корректность чисел и размерностей |
| `evaluation_time_sec`| Хост-среда (`time.time()`) | **Абсолютно доверенный** | Запрещено передавать из недоверенного JSON |
| `registry` | Хост-хранилище доказательств | **Абсолютно доверенный** | Передаётся только хост-окружением |

---

## 2. Канонический контракт выхода ядра (`EvaluationReport`)

Результат вычисления ядра представляет собой строго детерминированный отчёт:

```python
EvaluationReport:
  protocol_version: str                  # "1.0.0-canonical"
  verdict: CoherenceVerdict              # PASS | REVIEW | FAIL
  pairwise_checks:
    P_SC: PairwiseStatus                 # { is_valid: bool, verdict: CoherenceVerdict, diagnostics: [...] }
    P_SD: PairwiseStatus                 # { is_valid: bool, verdict: CoherenceVerdict, diagnostics: [...] }
    P_CD: PairwiseStatus                 # { is_valid: bool, verdict: CoherenceVerdict, diagnostics: [...] }
  simulated_values: Dict[str, float]     # Терминальные значения физических параметров V'
  simulated_flags: Dict[str, bool]       # Терминальные логические флаги F'
  diagnostics: List[CoherenceDiagnostic] # Полный список сообщений и кодов
  execution_permitted: bool              # СТРОГО False (Ядро НЕ даёт разрешения на исполнение!)
```

### Предусловия вызова (Preconditions):
1. `evaluation_time_sec` обязано быть конечным числом ($\neg\text{isnan} \land \neg\text{isinf}$).
2. Если `registry` не передан (`None`), ядро считает реестр недоступным и переводит любые проверки свидетельств статусов `FACT`/`INFERENCE` в вердикт `REVIEW (REGISTRY_OFFLINE)`.
3. Все структуры $S, C, D, S_0$ обязаны быть предварительно провалидированы на базовый синтаксический тип.

### Постусловия вызова (Postconditions):
1. `execution_permitted` всегда возвращается равным `False`. Никакое сочетание успешных проверок не переключает этот флаг в `True`.
2. Если `verdict == PASS`, то гарантируется:
   - $C.\text{domain\_scope} \subseteq S.\text{authority\_domain}$
   - $C.\text{target\_objects} \subseteq S.\text{granted\_scope}$
   - $D.\text{loss\_domain} \subseteq S.\text{granted\_loss\_domains}$
   - Свидетельство $S$ зарегистрировано в $\mathcal{R}$, не просрочено, хэш совпадает, домен совпадает.
   - Ни один параметр из $C.\text{protected\_set}$ не затронут мутациями $D$.
   - Все размерности физических величин согласованы и конвертированы.
   - Симулированные терминальные значения $V'$ находятся строго внутри $[B_{\min}, B_{\max}]$ и равны $K_{\text{prot}}$.
   - Запрещённые флаги выключены, обязательные — включены, защищённые — неизменны.
3. Если хотя бы одно условие нарушено, `verdict == FAIL`.
4. Если нарушений нет, но свидетельству не хватает свежести или реестр оффлайн, `verdict == REVIEW`.

---

## 3. Описание канонических структур данных

### 3.1 `SourcePrimitive`
- `evidence_id: str` — Идентификатор подтверждающего свидетельства.
- `authority_domain: Set[str]` — Множество доменов компетенции (например, `{"power_grid", "hvac"}`). Пустое множество означает **нулевые привилегии**, значение `None` — **структурный дефект**.
- `granted_scope: Set[str]` — Разрешённые объекты воздействия (например, `{"generator_substation_4"}`).
- `granted_loss_domains: Set[str]` — Разрешённые домены потерь (например, `{"electrical_load"}`).
- `epistemic_type: EpistemicStatus` — `FACT`, `INFERENCE` или `UNKNOWN`.
- `timestamp_sec: float` — Время наблюдения свидетельства.
- `max_age_sec: float` — Предельное время жизни свидетельства в секундах.
- `payload_hash: Optional[str]` — Опциональный криптографический хэш полезной нагрузки.
- `corroborating_evidence_ids: Set[str]` — Идентификаторы посылок для логического вывода.

### 3.2 `ConstraintPrimitive`
- `domain_scope: Set[str]` — Домен действия ограничения.
- `target_objects: Set[str]` — Целевые объекты.
- `protected_set: Set[str]` — Защищённый периметр параметров.
- `min_bounds: Dict[str, float]` — Нижние границы допустимых значений.
- `max_bounds: Dict[str, float]` — Верхние границы допустимых значений.
- `protected_values: Dict[str, float]` — Инвариантные постоянные значения параметров.
- `protected_flags: Set[str]` — Неизменяемые булевы флаги.
- `forbidden_flags: Set[str]` — Запрещённые к активации флаги.
- `required_flags: Set[str]` — Флаги, обязанные быть активными.
- `units: Dict[str, str]` — Единицы измерения параметров.

### 3.3 `DissipatePrimitive`
- `loss_domain: Set[str]` — Запрашиваемый домен потерь.
- `target_states: Set[str]` — Целевые состояния.
- `side_effects: Set[str]` — Побочные эффекты.
- `state_delta: Dict[str, float]` — Смещения непрерывных параметров ($\Delta$).
- `resource_cost: Dict[str, float]` — Потребление ресурсов ($\Gamma \ge 0$).
- `flag_mutations: Dict[str, bool]` — Переключения булевых флагов.
- `units: Dict[str, str]` — Единицы измерения величин воздействия.

### 3.4 `SystemState`
- `current_values: Dict[str, float]` — Начальные значения величин ($V_0$).
- `active_flags: Dict[str, bool]` — Начальные состояния флагов ($F_0$).
- `units: Dict[str, str]` — Базовые единицы измерения ($U_0$).
