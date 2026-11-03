# Нормативная спецификация ядра SOL-Triad (SOL-Triad Kernel Specification)

**Версия спецификации:** 1.0.0-canonical  
**Статус документа:** Нормативный стандарт ядра (Language-Independent Normative Specification)

---

## 1. Введение и область применения

Настоящая спецификация определяет поведение, интерфейсы, математические аксиомы и правила верификации ядра **SOL-Triad Core**. 

Спецификация является строго языконезависимой (Language-Agnostic). Любая реализация ядра (на Python, Rust, Go, C++, TypeScript или ином языке), претендующая на соответствие стандарту SOL-Triad Kernel v1.0, обязана:
1. Реализовывать каноническую модель данных и семантику примитивов триады.
2. Исполнять все нормативные аксиомы верификации ($P_{SC}, P_{SD}, P_{CD}$) в режиме **Fail-Closed**.
3. Вычислять детерминированный вердикт арбитра (`PASS`, `REVIEW`, `FAIL`) по установленным правилам.
4. Обеспечивать неизменность результата при повторных вычислениях на идентичных входах.
5. Не принимать доверенные параметры оценки (время хоста $t_{eval}$, реестр доказательств) из недоверенных источников.

---

## 2. Математические сущности канонической модели

### 2.1 Пространства и типы
- $\mathbb{R}$: множество вещественных конечных чисел (числа $\pm\infty$ и $NaN$ строго запрещены).
- $\mathcal{I}$: счётное множество строковых идентификаторов (ASCII / UTF-8 токены без пустых значений).
- $\mathcal{D}$: множество доменов полномочий ($\mathcal{D} \subset \mathcal{I}$).
- $\mathcal{O}$: множество объектов целевого воздействия ($\mathcal{O} \subset \mathcal{I}$).
- $\mathcal{L}$: множество доменов потерь ($\mathcal{L} \subset \mathcal{I}$).
- $\mathcal{P}$: множество физических и логических параметров состояния ($\mathcal{P} \subset \mathcal{I}$).
- $\mathcal{U}$: множество физических размерностей и единиц измерения.
- $\mathcal{E} \in \{\text{FACT}, \text{INFERENCE}, \text{UNKNOWN}\}$: эпистемический статус свидетельства.
- $\mathcal{V} \in \{\text{PASS}, \text{REVIEW}, \text{FAIL}\}$: итоговый вердикт ядра.

### 2.2 Кортеж примитива SOURCE ($S$)
$$S = \langle id, \mathcal{D}_S, \mathcal{O}_S, \mathcal{L}_S, \mathcal{E}_S, t_S, \tau_{\max}, H_S, \mathcal{C}_S \rangle$$
где:
- $id \in \mathcal{I}$: уникальный идентификатор свидетельства (`evidence_id`).
- $\mathcal{D}_S \subseteq \mathcal{D}$: непустое множество доменов компетенции (`authority_domain`).
- $\mathcal{O}_S \subseteq \mathcal{O}$: множество авторизованных объектов воздействия (`granted_scope`).
- $\mathcal{L}_S \subseteq \mathcal{L}$: множество разрешённых доменов потерь/рассеяния (`granted_loss_domains`).
- $\mathcal{E}_S \in \mathcal{E}$: заявленный эпистемический тип (`epistemic_type`).
- $t_S \in \mathbb{R}$: временная метка наблюдения свидетельства в секундах (`timestamp_sec`).
- $\tau_{\max} \in \mathbb{R}_{\ge 0}$: максимальное допустимое время жизни свидетельства (`max_age_sec`).
- $H_S \in \mathcal{I} \cup \{\bot\}$: строковый криптографический хэш полезной нагрузки (`payload_hash`).
- $\mathcal{C}_S \subseteq \mathcal{I}$: множество идентификаторов подкрепляющих свидетельств (`corroborating_evidence_ids`), непустое для $\mathcal{E}_S = \text{INFERENCE}$.

### 2.3 Кортеж примитива CONSTRAINT ($C$)
$$C = \langle \mathcal{D}_C, \mathcal{O}_C, \mathcal{P}_{\text{prot}}, B_{\min}, B_{\max}, K_{\text{prot}}, F_{\text{prot}}, F_{\text{forbid}}, F_{\text{req}}, U_C \rangle$$
где:
- $\mathcal{D}_C \subseteq \mathcal{D}$: домен применимости ограничения (`domain_scope`).
- $\mathcal{O}_C \subseteq \mathcal{O}$: целевые объекты действия (`target_objects`).
- $\mathcal{P}_{\text{prot}} \subseteq \mathcal{P}$: защищённое множество параметров, запрещённых к любой мутации (`protected_set`).
- $B_{\min}: \mathcal{P} \to \mathbb{R}$: нижние допустимые границы непрерывных величин (`min_bounds`).
- $B_{\max}: \mathcal{P} \to \mathbb{R}$: верхние допустимые границы непрерывных величин (`max_bounds`).
- $K_{\text{prot}}: \mathcal{P} \to \mathbb{R}$: инвариантные постоянные значения параметров (`protected_values`).
- $F_{\text{prot}} \subseteq \mathcal{P}$: флаги, значение которых запрещено изменять (`protected_flags`).
- $F_{\text{forbid}} \subseteq \mathcal{P}$: флаги, которым запрещено принимать значение `True` (`forbidden_flags`).
- $F_{\text{req}} \subseteq \mathcal{P}$: флаги, обязанные иметь значение `True` в терминальном состоянии (`required_flags`).
- $U_C: \mathcal{P} \to \mathcal{U}$: единицы измерения параметров ограничения (`units`).

### 2.4 Кортеж примитива DISSIPATE ($D$)
$$D = \langle \mathcal{L}_D, \mathcal{S}_{\text{target}}, \mathcal{S}_{\text{side}}, \Delta, \Gamma, \Phi, U_D \rangle$$
где:
- $\mathcal{L}_D \subseteq \mathcal{L}$: запрашиваемый домен потерь (`loss_domain`).
- $\mathcal{S}_{\text{target}} \subseteq \mathcal{P}$: целевые параметры/состояния воздействия (`target_states`).
- $\mathcal{S}_{\text{side}} \subseteq \mathcal{P}$: декларированные побочные эффекты (`side_effects`).
- $\Delta: \mathcal{P} \to \mathbb{R}$: предлагаемые числовые смещения величин (`state_delta`).
- $\Gamma: \mathcal{P} \to \mathbb{R}_{\ge 0}$: потребление ресурсов (`resource_cost`).
- $\Phi: \mathcal{P} \to \{0, 1\}$: мутации логических флагов (`flag_mutations`).
- $U_D: \mathcal{P} \to \mathcal{U}$: единицы измерения дельт и затрат (`units`).

### 2.5 Начальное состояние системы ($S_0$)
$$S_0 = \langle V_0, F_0, U_0 \rangle$$
где $V_0: \mathcal{P} \to \mathbb{R}$ — начальные числовые значения, $F_0: \mathcal{P} \to \{0, 1\}$ — начальные флаги, $U_0: \mathcal{P} \to \mathcal{U}$ — единицы измерения.

---

## 3. Парные отношения согласованности (The Three Pairwise Checks)

Верификация ядра разделяется на три независимых математических проекции:

### 3.1 Отношение $P_{SC}$: Заземление свидетельств и полномочия (Grounding & Authority)
Определяет соответствие между обоснованием $S$ и контекстом ограничений $C$.

#### Аксиома SC-1 (Целостность структуры):
Ни одно из обязательных полей $\mathcal{D}_S, \mathcal{O}_S, \mathcal{L}_S, \mathcal{D}_C, \mathcal{O}_C$ не должно быть неопределено ($\bot$).
$$\mathcal{D}_S \ne \bot \land \mathcal{O}_S \ne \bot \land \mathcal{L}_S \ne \bot \land \mathcal{D}_C \ne \bot \land \mathcal{O}_C \ne \bot$$
При нарушении: $P_{SC} = \text{FAIL}$ (`SCOPE_DEFECT_NONE`).

#### Аксиома SC-2 (Авторитетный домен):
Домен ограничений $C$ обязан быть строгим подмножеством полномочий источника $S$:
$$\mathcal{D}_C \subseteq \mathcal{D}_S$$
При нарушении: $P_{SC} = \text{FAIL}$ (`SCOPE_EXCEEDED_DOMAIN`).

#### Аксиома SC-3 (Объекты воздействия):
Целевые объекты $C$ обязаны входить в разрешённый периметр $S$:
$$\mathcal{O}_C \subseteq \mathcal{O}_S$$
При нарушении: $P_{SC} = \text{FAIL}$ (`SCOPE_EXCEEDED_OBJECTS`).

#### Аксиома SC-4 (Временное якорение):
Время наблюдения свидетельства $t_S$ не может находиться в будущем относительно системного времени оценки хоста $t_{eval}$:
$$t_S \le t_{eval}$$
При нарушении: $P_{SC} = \text{FAIL}$ (`TEMPORAL_FUTURE`).

#### Аксиома SC-5 (Окно актуальности / Свежесть):
Возраст свидетельства не должен превышать предельный возраст $\tau_{\max}$:
$$(t_{eval} - t_S) \le \tau_{\max}$$
При нарушении: если все остальные проверки успешны $\rightarrow P_{SC} = \text{REVIEW}$ (`TEMPORAL_STALE`).

#### Аксиома SC-6 (Верификация по авторитетному реестру):
В доверенном реестре $\mathcal{R}$ хоста обязана существовать запись $R \in \mathcal{R}$, такая что $R.id = S.id$:
1. Если реестр недоступен, а $\mathcal{E}_S \in \{\text{FACT}, \text{INFERENCE}\} \rightarrow P_{SC} = \text{REVIEW}$ (`REGISTRY_OFFLINE`).
2. Если реестр доступен, но $R$ не найдена $\rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_NOT_FOUND`).
3. Если $R$ найдена, но $R.\text{domain} \notin \mathcal{D}_S \rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_DOMAIN_MISMATCH`).
4. Если $R$ найдена, но $R.\text{status} \ne \mathcal{E}_S \rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_MISMATCH`).
5. **Целостность хэша (Fail-Closed Hash Match):**
   - Если $(S.H_S \ne \bot \land R.H_R = \bot) \rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_HASH_MISSING_IN_REGISTRY`).
   - Если $(S.H_S = \bot \land R.H_R \ne \bot) \rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_HASH_REQUIRED_BY_REGISTRY`).
   - Если $(S.H_S \ne \bot \land R.H_R \ne \bot \land S.H_S \ne R.H_R) \rightarrow P_{SC} = \text{FAIL}$ (`EVIDENCE_PAYLOAD_MISMATCH`).

#### Аксиома SC-7 (Строгость логического вывода для INFERENCE):
Если $\mathcal{E}_S = \text{INFERENCE}$:
1. Множество подкрепляющих свидетельств $\mathcal{C}_S$ не должно быть пусто: $\mathcal{C}_S \ne \emptyset$. Иначе $P_{SC} = \text{REVIEW}$ (`INFERENCE_UNSUPPORTED`).
2. Для каждого $premise\_id \in \mathcal{C}_S$:
   - $premise\_id \ne S.id$ (Запрет циклической зависимости). Иначе $P_{SC} = \text{FAIL}$ (`INFERENCE_CIRCULAR_DEPENDENCY`).
   - В реестре $\mathcal{R}$ обязана существовать запись $P \in \mathcal{R}$ с идентификатором $premise\_id$. Иначе $P_{SC} = \text{FAIL}$ (`EVIDENCE_NOT_FOUND`).
   - $P.\text{status} \in \{\text{FACT}, \text{INFERENCE}\}$. Иначе $P_{SC} = \text{FAIL}$ (`INFERENCE_PREMISE_INVALID_STATUS`).
   - $P.\text{domain} \in \mathcal{D}_S$. Иначе $P_{SC} = \text{FAIL}$ (`EVIDENCE_DOMAIN_MISMATCH`).
   - $P.t \le t_{eval}$. Иначе $P_{SC} = \text{FAIL}$ (`TEMPORAL_FUTURE`).
   - $(t_{eval} - P.t) \le \tau_{\max}$. Иначе $P_{SC} = \text{REVIEW}$ (`TEMPORAL_STALE`).

---

### 3.2 Отношение $P_{SD}$: Авторизация домена потерь (Loss Scope)
Определяет соответствие между запрашиваемыми потерями/возмущениями $D$ и мандатом $S$.

#### Аксиома SD-1 (Вхождение домена потерь):
Запрашиваемый домен потерь действия $D$ обязан быть строгим подмножеством разрешённых доменов потерь $S$:
$$\mathcal{L}_D \subseteq \mathcal{L}_S$$
При нарушении: $P_{SD} = \text{FAIL}$ (`SCOPE_EXCEEDED_LOSS`).

---

### 3.3 Отношение $P_{CD}$: Физические инварианты и симуляция состояния (Invariant & State)
Определяет допустимость терминального состояния системы $S'$ после применения воздействия $D$ к $S_0$ в границах ограничений $C$.

#### Аксиома CD-1 (Корректность числовых типов):
Все числовые значения в $S_0, \Delta, \Gamma, B_{\min}, B_{\max}, K_{\text{prot}}$ обязаны быть конечными:
$$\forall x \in \text{Values}, \neg \text{isnan}(x) \land \neg \text{isinf}(x)$$
При нарушении: $P_{CD} = \text{FAIL}$ (`STATE_INVALID_NUMERIC`).

#### Аксиома CD-2 (Неотрицательность затрат):
$$\forall r \in \text{dom}(\Gamma), \Gamma(r) \ge 0.0$$
При нарушении: $P_{CD} = \text{FAIL}$ (`STATE_NEGATIVE_RESOURCE_COST`).

#### Аксиома CD-3 (Неприкосновенность защищённого множества):
Определим полное множество мутируемых параметров воздействия $\mathcal{M}$:
$$\mathcal{M} = \mathcal{S}_{\text{target}} \cup \mathcal{S}_{\text{side}} \cup \text{dom}(\Delta) \cup \text{dom}(\Gamma) \cup \text{dom}(\Phi)$$
Пересечение множества мутаций с защищённым множеством параметров обязано быть строго пустым:
$$\mathcal{M} \cap \mathcal{P}_{\text{prot}} = \emptyset$$
При нарушении: $P_{CD} = \text{FAIL}$ (`STATE_PROTECTED_PARAM_MUTATED`).

#### Аксиома CD-4 (Совместимость физических размерностей):
Для каждого мутируемого параметра $p \in \mathcal{M}$:
Единицы измерения $U_D(p), U_C(p), U_0(p)$ обязаны принадлежать одной физической размерности (например, `pressure`, `time`, `temperature`, `energy`, `ratio`).
При нарушении или указании неизвестной единицы: $P_{CD} = \text{FAIL}$ (`UNIT_INCOMPATIBLE`).

#### Аксиома CD-5 (Детерминированная симуляция терминального состояния):
Терминальное значение каждого параметра $p \in \text{dom}(V_0) \cup \text{dom}(\Delta) \cup \text{dom}(\Gamma)$ вычисляется строго по формуле:
$$V'(p) = V_0(p) + \text{convert}(\Delta(p), U_D(p) \to U_0(p)) - \text{convert}(\Gamma(p), U_D(p) \to U_0(p))$$
Флаги терминального состояния:
$$F'(p) = \begin{cases} \Phi(p), & \text{если } p \in \text{dom}(\Phi) \\ F_0(p), & \text{иначе} \end{cases}$$

#### Аксиома CD-6 (Полнота пространства параметров):
Все параметры, для которых заданы $B_{\min}, B_{\max}$ или $K_{\text{prot}}$, обязаны присутствовать в симулированном терминальном состоянии $V'$:
$$(\text{dom}(B_{\min}) \cup \text{dom}(B_{\max}) \cup \text{dom}(K_{\text{prot}})) \subseteq \text{dom}(V')$$
При отсутствии параметра: $P_{CD} = \text{FAIL}$ (`STATE_MISSING_VAR`).

#### Аксиома CD-7 (Соблюдение инвариантных констант):
$$\forall p \in \text{dom}(K_{\text{prot}}), |V'(p) - \text{convert}(K_{\text{prot}}(p), U_C(p) \to U_0(p))| \le \epsilon$$
При нарушении: $P_{CD} = \text{FAIL}$ (`STATE_PROTECTED_VALUE_MUTATED`).

#### Аксиома CD-8 (Соблюдение граничных условий):
$$\forall p \in \text{dom}(B_{\min}), V'(p) \ge \text{convert}(B_{\min}(p), U_C(p) \to U_0(p)) - \epsilon$$
$$\forall p \in \text{dom}(B_{\max}), V'(p) \le \text{convert}(B_{\max}(p), U_C(p) \to U_0(p)) + \epsilon$$
При нарушении: $P_{CD} = \text{FAIL}$ (`STATE_MIN_BOUND_BREACH` или `STATE_MAX_BOUND_BREACH`).

#### Аксиома CD-9 (Соблюдение инвариантов логических флагов):
1. $\forall f \in F_{\text{prot}}, F'(f) = F_0(f)$ (Иначе `FAIL (STATE_FLAG_MUTATED)`).
2. $\forall f \in F_{\text{forbid}}, F'(f) \ne 1$ (Иначе `FAIL (STATE_FORBIDDEN_FLAG_ACTIVE)`).
3. $\forall f \in F_{\text{req}}, F'(f) = 1$ (Иначе `FAIL (STATE_REQUIRED_FLAG_MISSING)`).

---

## 4. Логика арбитра решений (Decision Arbiter)

Итоговый вердикт $\mathcal{V}$ формируется строгой детерминированной сверткой:

$$\mathcal{V} = \begin{cases} 
\text{FAIL}, & \text{если } (P_{SC} = \text{FAIL}) \lor (P_{SD} = \text{FAIL}) \lor (P_{CD} = \text{FAIL}) \\
\text{REVIEW}, & \text{иначе если } (P_{SC} = \text{REVIEW}) \lor (P_{SD} = \text{REVIEW}) \lor (P_{CD} = \text{REVIEW}) \\
\text{PASS}, & \text{если } (P_{SC} = \text{PASS}) \land (P_{SD} = \text{PASS}) \land (P_{CD} = \text{PASS})
\end{cases}$$

### Инварианты арбитра:
1. **Никакого повышения вердикта:** Ядро ни при каких условиях не преобразует `REVIEW` или `FAIL` в `PASS`.
2. **Приоритет отказа:** Если обнаружен хотя бы один `FAIL`, итоговый вердикт — строго `FAIL`, даже при наличии предупреждений категории `REVIEW`.
3. **Сохранение диагностик:** Каждая выявленная ошибка или предупреждение фиксируется в диагностическом журнале с указанием машиночитаемого кода, уровня серьёзности (`ERROR`, `WARNING`, `INFO`), примитива и целевого поля.
