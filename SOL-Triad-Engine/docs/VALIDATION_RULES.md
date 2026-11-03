# Validation Rules & Verification Axioms — SOL-Triad Engine v0.3.2

This document formalizes the validation axioms implemented across the SOL-Triad Engine.

---

## 1. Evidence Grounding Axioms ($P_{SC}$)

1. **Axiom EV-1 (Finite Time Anchor):**  
   $\text{timestamp\_sec}(S) \in \mathbb{R} \land \neg \text{isnan}(t) \land \neg \text{isinf}(t)$.  
   If violated $\rightarrow$ `FAIL (STATE_INVALID_NUMERIC)`.

2. **Axiom EV-2 (No Prophetic Observation):**  
   $\text{timestamp\_sec}(S) \le t_{\text{current}}$.  
   If violated $\rightarrow$ `FAIL (TEMPORAL_FUTURE)`.

3. **Axiom EV-3 (Freshness Window):**  
   $(t_{\text{current}} - \text{timestamp\_sec}(S)) \le \text{max\_age\_sec}(S)$.  
   If violated $\rightarrow$ `REVIEW (TEMPORAL_STALE)`.

4. **Axiom EV-4 (Authoritative Grounding):**  
   $\exists R \in \text{Registry} : R.\text{evidence\_id} = S.\text{evidence\_id}$.  
   If Registry is unavailable and status is `FACT`/`INFERENCE` $\rightarrow$ `REVIEW (REGISTRY_OFFLINE)`.  
   If Registry is online and $R$ does not exist $\rightarrow$ `FAIL (EVIDENCE_NOT_FOUND)`.

5. **Axiom EV-5 (Epistemic Status Coherence):**  
   If $S.\text{epistemic\_type} = \text{FACT}$, then $R.\text{epistemic\_status} = \text{FACT}$.  
   If violated $\rightarrow$ `FAIL (EVIDENCE_MISMATCH)`.

6. **Axiom EV-6 (Domain Grounding):**  
   $R.\text{domain} \in S.\text{authority\_domain}$.  
   If violated $\rightarrow$ `FAIL (EVIDENCE_DOMAIN_MISMATCH)`.

7. **Axiom EV-7 (Inference Corroboration Existence):**  
   If $S.\text{epistemic\_type} = \text{INFERENCE}$, then $S.\text{corroborating\_evidence\_ids} \ne \emptyset$, and $\forall id \in S.\text{corroborating\_evidence\_ids}, \exists R_{id} \in \text{Registry}$.  
   If corroborating IDs is empty $\rightarrow$ `REVIEW (INFERENCE_UNSUPPORTED)`.  
   If an ID is missing in registry $\rightarrow$ `FAIL (EVIDENCE_NOT_FOUND)`.

8. **Axiom EV-8 (Fail-Closed Cryptographic Hash Integrity):**  
   - If $S.\text{payload\_hash} \ne \text{None} \land R.\text{payload\_hash} = \text{None} \rightarrow \text{FAIL (EVIDENCE_HASH_MISSING_IN_REGISTRY)}$.  
   - If $S.\text{payload\_hash} = \text{None} \land R.\text{payload\_hash} \ne \text{None} \rightarrow \text{FAIL (EVIDENCE_HASH_REQUIRED_BY_REGISTRY)}$.  
   - If $S.\text{payload\_hash} \ne R.\text{payload\_hash} \rightarrow \text{FAIL (EVIDENCE_PAYLOAD_MISMATCH)}$.  
   - Hash evaluation never silently ignores asymmetric presence.

9. **Axiom EV-9 (Inference Premise Rigor & Anti-Recursion):**  
   For each corroborating premise $P_{id}$ of an `INFERENCE`:  
   - $P_{id}.\text{evidence\_id} \ne S.\text{evidence\_id}$ (Anti-circular dependency) $\rightarrow \text{FAIL (INFERENCE_CIRCULAR_DEPENDENCY)}$.  
   - $P_{id}.\text{epistemic\_status} \in \{\text{FACT}, \text{INFERENCE}\}$ $\rightarrow \text{FAIL (INFERENCE_PREMISE_INVALID_STATUS)}$.  
   - $P_{id}.\text{domain} \in S.\text{authority\_domain}$ $\rightarrow \text{FAIL (EVIDENCE_DOMAIN_MISMATCH)}$.  
   - $P_{id}.\text{timestamp\_sec} \le t_{\text{current}}$ $\rightarrow \text{FAIL (TEMPORAL_FUTURE)}$.  
   - $(t_{\text{current}} - P_{id}.\text{timestamp\_sec}) \le S.\text{max\_age\_sec}$ $\rightarrow \text{REVIEW (TEMPORAL_STALE)}$.

---

## 2. Scope & Authority Axioms ($P_{SC}$ and $P_{SD}$)

1. **Axiom SC-1 (No Structural Defects):**  
   $S.\text{authority\_domain} \ne \text{None} \land S.\text{granted\_scope} \ne \text{None} \land S.\text{granted\_loss\_domains} \ne \text{None}$.  
   If violated $\rightarrow$ `FAIL (SCOPE_DEFECT_NONE)`.

2. **Axiom SC-2 (Domain Authority Containment):**  
   $C.\text{domain\_scope} \subseteq S.\text{authority\_domain}$.  
   If violated $\rightarrow$ `FAIL (SCOPE_EXCEEDED_DOMAIN)`.

3. **Axiom SC-3 (Object Target Containment):**  
   $C.\text{target\_objects} \subseteq S.\text{granted\_scope}$.  
   If violated $\rightarrow$ `FAIL (SCOPE_EXCEEDED_OBJECTS)`.

4. **Axiom SC-4 (Loss Domain Containment):**  
   $D.\text{loss\_domain} \subseteq S.\text{granted\_loss\_domains}$.  
   If violated $\rightarrow$ `FAIL (SCOPE_EXCEEDED_LOSS)`.

---

## 3. State & Invariant Axioms ($P_{CD}$)

1. **Axiom ST-1 (Numeric Sanity):**  
   All numerical values in $S_0, D_{\text{delta}}, D_{\text{cost}}, C_{\text{min}}, C_{\text{max}}, C_{\text{protected}}$ must be finite ($\neg \text{isnan} \land \neg \text{isinf}$).  
   If violated $\rightarrow$ `FAIL (STATE_INVALID_NUMERIC)`.

2. **Axiom ST-2 (Non-Negative Resource Costs):**  
   $\forall r \in \text{dom}(D_{\text{cost}}), D_{\text{cost}}[r] \ge 0.0$.  
   If violated $\rightarrow$ `FAIL (STATE_NEGATIVE_RESOURCE_COST)`.

3. **Axiom ST-3 (Protected Parameter Inviolability):**  
   Let $M = D_{\text{target\_states}} \cup D_{\text{side\_effects}} \cup \text{dom}(D_{\text{delta}}) \cup \text{dom}(D_{\text{cost}}) \cup \text{dom}(D_{\text{flags}})$.  
   $M \cap C.\text{protected\_set} = \emptyset$.  
   If violated $\rightarrow$ `FAIL (STATE_PROTECTED_PARAM_MUTATED)`.

4. **Axiom ST-4 (Dimensional Typing Compatibility):**  
   For all $p \in M$, units must be dimensionally compatible ($\text{dim}(D_{\text{unit}}) = \text{dim}(C_{\text{unit}}) = \text{dim}(S_{0,\text{unit}})$).  
   If an unknown unit or dimension mismatch occurs $\rightarrow$ `FAIL (UNIT_INCOMPATIBLE)`.

5. **Axiom ST-5 (Fail-Closed Required Variables):**  
   Let $R_{\text{vars}} = \text{dom}(C_{\text{min}}) \cup \text{dom}(C_{\text{max}}) \cup \text{dom}(C_{\text{protected\_values}})$.  
   $R_{\text{vars}} \subseteq \text{dom}(S')$.  
   If violated $\rightarrow$ `FAIL (STATE_MISSING_VAR)`.

6. **Axiom ST-6 (Invariant Constants):**  
   $\forall v \in \text{dom}(C_{\text{protected\_values}}), |S'[v] - C_{\text{protected\_values}}[v]| \le \epsilon$.  
   If violated $\rightarrow$ `FAIL (STATE_PROTECTED_VALUE_VIOLATED)`.

7. **Axiom ST-7 (Physical Boundary Bounds):**  
   $\forall v \in \text{dom}(C_{\text{min}}), S'[v] \ge C_{\text{min}}[v]$.  
   $\forall v \in \text{dom}(C_{\text{max}}), S'[v] \le C_{\text{max}}[v]$.  
   If violated $\rightarrow$ `FAIL (STATE_MIN_BOUND_BREACH | STATE_MAX_BOUND_BREACH)`.

8. **Axiom ST-8 (Flag Invariants):**  
   - $\forall f \in C_{\text{protected\_flags}}, S'_f = S_{0,f}$.
   - $\forall f, v \in C_{\text{forbidden\_flags}}, S'_f \ne v$.
   - $\forall f, v \in C_{\text{required\_flags}}, S'_f = v$.  
   If violated $\rightarrow$ `FAIL`.
