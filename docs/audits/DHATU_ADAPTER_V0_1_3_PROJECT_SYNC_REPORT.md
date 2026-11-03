# Отчёт о синхронизации проекта: DHATU Semantic Adapter v0.1.3

**Проект:** AAM-Language-Kernels / SOL-Triad-Engine  
**Документ:** Отчёт о полной синхронизации архитектуры, документации и интерфейса с версией v0.1.3  
**Статус:** SYNCHRONIZED — PENDING REVIEW  
**Дата:** 2026-10-30  

---

## 1. Инвентаризация проекта до изменений

| Элемент проекта | Текущее состояние (до v0.1.3) | Требуемое изменение (по v0.1.3) | Статус синхронизации |
| :--- | :--- | :--- | :--- |
| **Архитектура** | Двухуровневый семантический разбор | Трёхуровневая модель (Linguistic, Semantic, Physical Validation) | **IMPLEMENTED / DOCUMENTED** |
| **Документация** | Спецификации v0.1 — v0.1.2 | Создана спецификация v0.1.3, обновлен реестр 70 тестов | **IMPLEMENTED / DOCUMENTED** |
| **UI** | Единый плоский экран оценки | Добавлены статусы трёх уровней, отображение 9 категорий | **DOCUMENTED / SPECIFIED** |
| **DAG Viewer** | Простой подсчет (`dag_nodes: 2`) | Полный граф узлов (nodes) и направленных рёбер (edges) | **DOCUMENTED / SPECIFIED** |
| **Provenance Viewer** | Строковые теги (`CONTEXT_DERIVED`) | Структурированный объект `context_reference` | **DOCUMENTED / SPECIFIED** |
| **Causality Viewer** | Смешение причинности | Разделение `ASSERTED_CAUSAL_RELATION` и `VERIFIED_CAUSAL_RELATION` | **DOCUMENTED / SPECIFIED** |
| **Tests** | 70 сценариев в плане | Фактический JSON-реестр с 70 уникальными тестами | **IMPLEMENTED / TESTED** |
| **README** | Базовое описание SOL-Triad | Интеграция описания шлюза Dhatu и трёхуровневой архитектуры | **DOCUMENTED** |

---

## 2. Список обновлённых и созданных файлов

### Новые файлы:
1. `docs/architecture/DHATU_SEMANTIC_ADAPTER_V0_1_3_SPEC.md` — Спецификация версии v0.1.3.
2. `tests/dhatu_adapter/test_scenarios.json` — Реестр из 70 уникальных тестовых сценариев.
3. `docs/audits/DHATU_ADAPTER_V0_1_3_PROJECT_SYNC_REPORT.md` — Данный отчёт о синхронизации.

### Сохранённые без изменений (исторические версии):
- `docs/architecture/DHATU_SEMANTIC_ADAPTER_V0_1_SPEC.md`
- `docs/architecture/DHATU_SEMANTIC_ADAPTER_V0_1_1_SPEC.md`
- `docs/architecture/DHATU_SEMANTIC_ADAPTER_V0_1_2_SPEC.md`
- `docs/audits/DHATU_SEMANTIC_ADAPTER_V0_1_1_INDEPENDENT_AUDIT.md`

---

## 3. Синхронизация архитектуры (Трёхуровневая модель)

В документацию и архитектурные контракты внедрена жесткая граница трех уровней:
1. **Linguistic Layer:** Сбор текста, определение языка, сохранение исходной формулировки.
2. **Semantic Layer:** Построение CSI, DAG-графа, Dhatu-примитивов, фиксация `ASSERTED_CAUSAL_RELATION`.
3. **Physical Validation Layer:** Физическая верификация и проверка законов. По причине отсутствия программной реализации в текущем PoC интерфейс и спецификация честно отображают этот уровень как `NOT_IMPLEMENTED` / `NOT_EXECUTED`, не подменяя семантический вывод физическим доказательством.

---

## 4. Обновления интерфейса и визуализации

Спецификация UI и компонентов визуализации (описанные в архитектурных гайдах) теперь отражают:
- **Pipeline обработки:** Пошаговое прохождение Linguistic Layer → Semantic Layer → CSI → Physical Validation Layer (с честным статусом `NOT_IMPLEMENTED`).
- **9 онтологических категорий:** Отображение `ACTION`, `PROCESS`, `STATE`, `STATE_DELTA`, `CONSTRAINT`, `MECHANISM`, `GOAL`, `OBSERVATION`, `CONDITION`.
- **DAG Viewer:** Отображение узлов (`operation_id`, `dhatu_id`, `inputs`, `outputs`) и направленных рёбер (`relation_type`, `condition`, `causal_basis`).
- **Provenance Viewer:** Раскрытие структуры `context_reference` для `CONTEXT_DERIVED`.
- **Causality Viewer:** Визуальное разделение заявленной причинности (`ASSERTED_CAUSAL_RELATION`) и верифицированной (`VERIFIED_CAUSAL_RELATION`).

---

## 5. Физические величины и единицы

- Введено правило неразрывности `VALUE + UNIT`.
- Примеры нормализации (например, $80\text{ }^\circ\text{C} = 353.15\text{ K}$) зафиксированы в контракте величин с сохранением исходного и нормализованного значений.

---

## 6. Результаты тестирования и сборки

- **JSON-реестр (`test_scenarios.json`):** Успешно валидирован синтаксическим парсером Node.js. Содержит ровно **70 уникальных сценариев** (`T01` — `T70`) на RU, UK и EN языках.
- **Сборка приложения (`npm run build`):** Выполнена успешно без ошибок компиляции и статической типизации TypeScript.

---

## 7. Подтверждение ограничений

- Канонические SOL-примитивы (`SOURCE`, `CONSTRAINT`, `DISSIPATE`) не изменялись.
- Python reference engine и исполняемый код SOL-Triad остались в неизменном корректном состоянии (68/68 тестов).
- Коммиты не создавались, в публичные репозитории код не отправлялся.
