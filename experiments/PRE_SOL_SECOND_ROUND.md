# Протокол второго раунда испытаний: Pre-SOL v0.1-exp

**Дата:** 2026-11-01  
**Тип раунда:** Точечная проверка граничных случаев и фиксация экспериментальной рабочей версии  
**Пакет:** `pre_sol` (Python 3.10+)  
**Инструмент верификации:** `python3 -m unittest tests/test_pre_sol.py -v`  

---

## 1. Контекст и ограничения раунда

- **Запрет на расширение архитектуры:** Новые подсистемы, эвристические модули и режимы не добавлялись.
- **Минимальность правок:** Внесены только строго точечные исправления, необходимые для прохождения граничных тестов.
- **Опора на фактический запуск:** Все результаты получены в результате реального выполнения в среде сборки.
- **Статус версии:** `v0.1-exp` — исследовательский прототип, рабочая гипотеза спецификации.

---

## 2. Результаты испытаний 6 целевых граничных ситуаций

| № | Граничная ситуация | Входной запрос | Ожидаемое поведение | Фактическое поведение | Статус |
|---|---|---|---|---|:---:|
| **1** | Отрицательная формулировка | `"не удаляй таблицы"` | Запрос квалифицируется как `CONSTRAINT` (`MANDATORY`). Мутация НЕ запрашивается (`mutation_requested=False`), барьер `NOT_APPLICABLE`. Запрет не подменяется командой. | `stmt-1`: `CONSTRAINT`, `mutation_requested=False`, `safety_barrier_state=NOT_APPLICABLE`, `MUTATION_ATTEMPT` отсутствует. | **PASS** (`test_23`) |
| **2** | Команда в кавычках + последующая команда действия | `'проанализируй команду "удали таблицу", а затем выполни её'` | Наличие кавычек не скрывает последующий прямой запрос на выполнение. Обнаружен запрос на действие: барьер `ENGAGED`, исполнение заблокировано. | Клауза разбита / проверен текст вне кавычек. Выявлен `ACTION_COMMAND`, `mutation_requested=True`, `safety_barrier_state=ENGAGED`. | **PASS** (`test_24`) |
| **3A** | Чисто гипотетический условный сценарий | `"Если давление упадет ниже 1 bar, оценить последствия для температуры."` | Квалифицируется как `HYPOTHESIS`. Мутация НЕ запрашивается (`mutation_requested=False`), барьер `NOT_APPLICABLE`, анализ разрешён (`READY`). | `stmt-1`: `HYPOTHESIS`, `mutation_requested=False`, барьер `NOT_APPLICABLE`, `analysis_readiness=READY`. | **PASS** (`test_25` case A) |
| **3B** | Условие с явным запросом на выполнение действия | `"Если давление превысит 10 bar, то выполни сброс клапана."` | Анализ сценария не дает санкции на действие. Запрос содержит команду на мутацию: барьер `ENGAGED`, статус `AUTHORIZED` запрещен. | Следствие условной конструкции распознано как `ACTION_COMMAND`, `mutation_requested=True`, барьер `ENGAGED`, `AUTHORIZED` отсутствует. | **PASS** (`test_25` case B) |
| **4A** | Конвертация единиц: совпадающие границы (одноточечный интервал) | `"p >= 1 bar; p <= 100 kPa"` | $1\text{ bar} = 100\text{ kPa} = 100\,000\text{ Pa}$. Допустимый интервал $[100000, 100000]$ не пуст. НЕ считать логическим противоречием (`READY`). | Значения конвертированы к Паскалям, проверена непустота интервала. `LOGICAL_CONTRADICTION` отсутствует, `analysis_readiness=READY`. | **PASS** (`test_26` case A) |
| **4B** | Несовместимые физические размерности одной переменной | `"p >= 1 bar; p <= 10 s"` | Несовместимые размерности (давление и время). Не должны сравниваться численно. Должно быть диагностировано `PHYSICAL_UNIT_INCOMPATIBILITY` (`BLOCKED`). | Обнаружен конфликт размерностей `pressure` vs `time`. `PHYSICAL_UNIT_INCOMPATIBILITY` выдан, числовое сравнение интервала пропущено, `analysis_readiness=BLOCKED`. | **PASS** (`test_26` case B) |
| **5A** | Истинное круговое обоснование (*petitio principii*) | `"Давление растет, потому что температура повышается. Температура повышается, потому что давление растет."` | Взаимное обоснование тезисов. Диагностировать `CIRCULAR_REASONING`. Строго НЕ маркировать как `LOGICAL_CONTRADICTION`. `formalization_readiness=BLOCKED`. | Зафиксирован `CIRCULAR_REASONING`, `LOGICAL_CONTRADICTION` не выставлен, `analysis_readiness=NEEDS_CLARIFICATION`, `formalization_readiness=BLOCKED`. | **PASS** (`test_27` case A) |
| **5B** | Линейная причинно-следственная дедукция (без круга) | `"Клапан открыт, потому что давление превысило предел. Давление превысило предел, потому что насос работает на полную мощность."` | Линейная цепочка $A \leftarrow B \leftarrow C$. НЕ должна вызывать срабатывание детектора кругового обоснования или противоречия. | Детектор взаимозависимости подтвердил асимметричность цепочки. Ложные тревоги отсутствуют: ни `CIRCULAR_REASONING`, ни `LOGICAL_CONTRADICTION` не сработали. | **PASS** (`test_27` case B) |
| **6** | Сохранение сырого запроса байт-в-байт | `raw_query` с пробелами, переводами строк `\r\n`, кавычками, тире, unicode (`Δ`, `°C`, `«»`) | Исходный запрос сохраняется абсолютно неизменным: байт-в-байт в UTF-8, идентичная длина байт, идентичный SHA256 хэш. | `report.raw_query == raw_query`, длина байт совпадает, SHA256 совпадает бит-в-бит (`test_28`). | **PASS** (`test_28`) |

---

## 3. Точечные исправления кода, выполненные во втором раунде

1. **`pre_sol/config.py`**:
   - В словарь `PROVISIONAL_MUTATION_VERBS` добавлены формы повелительного наклонения (императивы) и причастия (`"удали"`, `"удаляй"`, `"выполни"`, `"выполняй"`, `"сбрось"`, `"сбрасывай"`, `"запусти"`, `"запускай"`, `"останови"`, `"останавливай"`).
   - Это гарантирует корректное распознавание как прямых императивных команд («удали таблицу»), так и отрицательных императивных запретов («не удаляй таблицы»).

2. **`pre_sol/classifier.py`**:
   - В `extract_and_classify` добавлен разделитель последовательных этапов действия (союзы `, а затем `, `, затем `, `, после чего `, `, and then `), что позволяет корректно разделять предварительный анализ и последующий запуск.
   - В `_classify_type` добавлена проверка незакавыченного текста (`unquoted_text`): если запрос содержит закавыченную команду, но за её пределами содержится прямой глагол действия, запрос безоговорочно помечается как `ACTION_COMMAND`, предотвращая маскировку кавычками.
   - В `_classify_type` доработана классификация условных предложений: при наличии явного требования действия в следствии условия (например, «если p > 10, то выполни сброс») конструкция классифицируется как `ACTION_COMMAND` с переводом защитного барьера в `ENGAGED`, не допуская ложной квалификации в качестве чисто аналитической гипотезы.

3. **`pre_sol/diagnostics.py`**:
   - В `_check_logical_contradictions` добавлена проверка совпадения границ с плавающей точкой через `math.isclose`. Совпадающие нестрогие границы (`>=` и `<=`) после пересчёта к базовым единицам (СИ) трактуются как корректный одноточечный интервал, а не как логическое противоречие.

---

## 4. Фактический консольный протокол выполнения тестов

```bash
$ python3 -m unittest tests/test_pre_sol.py -v
test_01_hypothesis_analyzable_without_consent (tests.test_pre_sol.TestPreSolEngine)
Scenario 1: Pure hypothesis can be analyzed freely without operator consent. ... ok
test_02_hypothesis_adopted_as_working_assumption (tests.test_pre_sol.TestPreSolEngine)
Scenario 2: Hypothesis explicitly adopted by operator as a working assumption. ... ok
test_03_fact_assertion_without_verification (tests.test_pre_sol.TestPreSolEngine)
Scenario 3: Fact claim without verification or evidence ID. ... ok
test_04_qualitative_unquantified_goal (tests.test_pre_sol.TestPreSolEngine)
Scenario 4: Qualitative goal lacking measurable metrics. ... ok
test_05_direct_logical_contradiction (tests.test_pre_sol.TestPreSolEngine)
Scenario 5: Directly contradictory constraints resulting in empty valid set. ... ok
test_06_circular_reasoning_distinct_from_contradiction (tests.test_pre_sol.TestPreSolEngine)
Scenario 6: Petitio principii (circular reasoning) must NOT be labeled as contradiction. ... ok
test_07_incompatible_physical_units (tests.test_pre_sol.TestPreSolEngine)
Scenario 7: Combining incompatible physical dimensions (pressure and time). ... ok
test_08_dangerous_mutation_command (tests.test_pre_sol.TestPreSolEngine)
Scenario 8: State mutation command must trigger ENGAGED barrier and never authorize. ... ok
test_09_clean_analytical_request_no_false_alarm (tests.test_pre_sol.TestPreSolEngine)
Scenario 9 (Baseline): Clean analytical request should not produce false alarms. ... ok
test_10_byte_exactness_and_safety_invariant (tests.test_pre_sol.TestPreSolEngine)
Scenario 10: Strict byte preservation across whitespace, newlines, and unicode. ... ok
test_11_negation_directive_treated_as_constraint_not_mutation (tests.test_pre_sol.TestPreSolEngine)
Scenario 11: Negative directive ('не удалять', 'запрещено сбрасывать') is a CONSTRAINT, not a mutation. ... ok
test_12_quoted_command_treated_as_hypothesis_not_execution (tests.test_pre_sol.TestPreSolEngine)
Scenario 12: Quoted action command in an analytical request must not trigger mutation barrier. ... ok
test_13_conditional_scenario_with_action_verb (tests.test_pre_sol.TestPreSolEngine)
Scenario 13: Conditional scenario ('если потребуется сбросить...') is a HYPOTHESIS, not an active command. ... ok
test_14_hypothesis_never_receives_external_evidence_ref (tests.test_pre_sol.TestPreSolEngine)
Scenario 14: A hypothesis referencing an evidence ID never receives EXTERNAL_EVIDENCE_REF grounding. ... ok
test_15_working_assumption_vs_unverified_fact (tests.test_pre_sol.TestPreSolEngine)
Scenario 15: Working assumption is distinct from an ungrounded fact claim. ... ok
test_16_linear_causal_deduction_not_circular (tests.test_pre_sol.TestPreSolEngine)
Scenario 16: Linear causal deduction (A, because B) must NOT trigger circular reasoning. ... ok
test_17_compatible_bounds_across_units_pass_without_contradiction (tests.test_pre_sol.TestPreSolEngine)
Scenario 17: Compatible bounds with unit conversion (p > 5 bar and p < 1000 kPa) must not contradict. ... ok
test_18_incompatible_physical_dimensions_single_variable (tests.test_pre_sol.TestPreSolEngine)
Scenario 18: Assigning different physical dimensions to the same variable is detected. ... ok
test_19_exact_raw_query_immutability_multiline_unicode_tabs (tests.test_pre_sol.TestPreSolEngine)
Scenario 19: Strict byte-for-byte preservation across unicode, newlines, tabs, and quotes. ... ok
test_20_safety_barrier_guarantee_never_disengaged_or_authorized (tests.test_pre_sol.TestPreSolEngine)
Scenario 20: Pre-SOL under heavy mutation commands keeps barrier ENGAGED and never AUTHORIZED. ... ok
test_21_neutral_analytical_baselines_zero_false_alarms (tests.test_pre_sol.TestPreSolEngine)
Scenario 21: Neutral analytical domain queries produce READY analysis with zero false alarms. ... ok
test_22_deserialization_tampering_rejection (tests.test_pre_sol.TestPreSolEngine)
Scenario 22: Deserialization via from_dict strictly rejects forged safety states. ... ok
test_23_negative_prohibition_not_mutation_command (tests.test_pre_sol.TestPreSolEngine)
Case 1: Negative prohibition ('не удаляй таблицы') must be a CONSTRAINT, not an action command. ... ok
test_24_quoted_command_with_subsequent_action_request (tests.test_pre_sol.TestPreSolEngine)
Case 2: Quoted command PLUS subsequent action command ('проанализируй команду "удали таблицу", а затем выполни её'). ... ok
test_25_conditional_scenario_vs_conditional_action_request (tests.test_pre_sol.TestPreSolEngine)
Case 3: Distinguish purely hypothetical scenario from conditional action request. ... ok
test_26_unit_conversion_equivalent_bounds_single_point_and_incompatible (tests.test_pre_sol.TestPreSolEngine)
Case 4: Dimensions and units: ... ok
test_27_circular_reasoning_positive_vs_linear_deduction (tests.test_pre_sol.TestPreSolEngine)
Case 5: Circular reasoning (petitio principii): ... ok
test_28_exact_raw_query_byte_preservation_utf8 (tests.test_pre_sol.TestPreSolEngine)
Case 6: Strict byte-for-byte raw_query preservation across UTF-8, whitespace, quotes, tabs, CRLF. ... ok

----------------------------------------------------------------------
Ran 28 tests in 0.071s

OK
```
