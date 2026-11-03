"""
Валидаторы канонического ядра SOL-Triad Core.
Реализует:
  1. EvidenceValidator (P_SC: временное якорение, авторитетный реестр, хэши, инференция).
  2. ScopeValidator (P_SC, P_SD: вхождение доменов, объектов и доменов потерь).
  3. StateValidator (P_CD: симуляция состояния, инварианты, границы, флаги, размерности).
"""

import math
from typing import Tuple, Optional, List, Dict, Set, Any

from .models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    CoherenceVerdict,
    CoherenceDiagnostic,
)
from .errors import (
    EpistemicStatus,
    DiagnosticCode,
    DiagnosticSeverity,
)
from .units import UnitRegistry, DimensionalityError, UnknownUnitError
from .evidence import EvidenceRegistryOracle


class EvidenceValidator:
    """
    Валидатор эпистемического обоснования и временного якорения примитива SOURCE (S).
    """

    def __init__(self, registry: Optional[EvidenceRegistryOracle], current_time_sec: float):
        self.registry = registry
        self.current_time_sec = current_time_sec

    def validate(self, s: SourcePrimitive) -> Tuple[bool, CoherenceVerdict, List[CoherenceDiagnostic]]:
        diagnostics: List[CoherenceDiagnostic] = []

        # 1. Временная шкала и конечные числа
        if math.isnan(s.timestamp_sec) or math.isinf(s.timestamp_sec):
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.STATE_INVALID_NUMERIC,
                severity=DiagnosticSeverity.ERROR,
                message=f"Source timestamp is non-finite: {s.timestamp_sec}",
                primitive="SOURCE",
                field_name="timestamp_sec"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        if s.max_age_sec <= 0 or math.isnan(s.max_age_sec) or math.isinf(s.max_age_sec):
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.STRUCTURAL_DEFECT,
                severity=DiagnosticSeverity.ERROR,
                message=f"Source max_age_sec must be positive and finite: {s.max_age_sec}",
                primitive="SOURCE",
                field_name="max_age_sec"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        if s.timestamp_sec > self.current_time_sec:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.TEMPORAL_FUTURE,
                severity=DiagnosticSeverity.ERROR,
                message=f"Source timestamp is in the future ({s.timestamp_sec:.2f} > current {self.current_time_sec:.2f})",
                primitive="SOURCE",
                field_name="timestamp_sec"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        age = self.current_time_sec - s.timestamp_sec
        if age > s.max_age_sec:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.TEMPORAL_STALE,
                severity=DiagnosticSeverity.WARNING,
                message=f"Evidence is stale: age {age:.2f}s exceeds max_age_sec ({s.max_age_sec:.2f}s)",
                primitive="SOURCE",
                field_name="timestamp_sec"
            ))
            return False, CoherenceVerdict.REVIEW, diagnostics

        # 2. Доступность реестра свидетельств
        if self.registry is None or not self.registry.is_available():
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.REGISTRY_OFFLINE,
                severity=DiagnosticSeverity.WARNING,
                message="Evidence registry is offline or not provided; cannot verify claim.",
                primitive="SOURCE",
                field_name="epistemic_type"
            ))
            return False, CoherenceVerdict.REVIEW, diagnostics

        # 3. Поиск авторитетной записи в реестре
        record = self.registry.lookup(s.evidence_id)
        if not record:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.EVIDENCE_NOT_FOUND,
                severity=DiagnosticSeverity.ERROR,
                message=f"Primary evidence ID '{s.evidence_id}' not found in registry.",
                primitive="SOURCE",
                field_name="evidence_id"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        if record.timestamp_sec > self.current_time_sec:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.TEMPORAL_FUTURE,
                severity=DiagnosticSeverity.ERROR,
                message=f"Registry record '{record.evidence_id}' has future timestamp ({record.timestamp_sec:.2f} > {self.current_time_sec:.2f})",
                primitive="SOURCE",
                field_name="evidence_id"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        # 4. Согласованность эпистемического статуса
        if s.epistemic_type == EpistemicStatus.FACT and record.epistemic_status != EpistemicStatus.FACT:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.EVIDENCE_MISMATCH,
                severity=DiagnosticSeverity.ERROR,
                message=f"Claimed FACT, but registry records status as {record.epistemic_status.value}.",
                primitive="SOURCE",
                field_name="epistemic_type"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        # 5. Доменная принадлежность
        if s.authority_domain is not None and record.domain not in s.authority_domain:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.EVIDENCE_DOMAIN_MISMATCH,
                severity=DiagnosticSeverity.ERROR,
                message=f"Evidence domain '{record.domain}' is not within claimed authority {s.authority_domain}.",
                primitive="SOURCE",
                field_name="authority_domain"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        # 6. Проверка криптографического хэша полезной нагрузки (Fail-Closed)
        if s.payload_hash is not None and record.payload_hash is None:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.EVIDENCE_HASH_MISSING_IN_REGISTRY,
                severity=DiagnosticSeverity.ERROR,
                message=f"Source supplied payload_hash '{s.payload_hash}', but registry record '{s.evidence_id}' lacks a payload_hash.",
                primitive="SOURCE",
                field_name="payload_hash"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        if record.payload_hash is not None and s.payload_hash is None:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.EVIDENCE_HASH_REQUIRED_BY_REGISTRY,
                severity=DiagnosticSeverity.ERROR,
                message=f"Registry record '{s.evidence_id}' requires payload_hash verification, but Source omitted payload_hash.",
                primitive="SOURCE",
                field_name="payload_hash"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics

        if s.payload_hash is not None and record.payload_hash is not None:
            if s.payload_hash != record.payload_hash:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.EVIDENCE_PAYLOAD_MISMATCH,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Payload hash mismatch for evidence '{s.evidence_id}': '{s.payload_hash}' != '{record.payload_hash}'.",
                    primitive="SOURCE",
                    field_name="payload_hash"
                ))
                return False, CoherenceVerdict.FAIL, diagnostics

        # 7. Проверка подкрепляющих доказательств для INFERENCE
        if s.epistemic_type == EpistemicStatus.INFERENCE:
            if not s.corroborating_evidence_ids:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.INFERENCE_UNSUPPORTED,
                    severity=DiagnosticSeverity.WARNING,
                    message="Claimed INFERENCE lacks corroborating evidence IDs; requires epistemic review.",
                    primitive="SOURCE",
                    field_name="corroborating_evidence_ids"
                ))
                return False, CoherenceVerdict.REVIEW, diagnostics

            if s.evidence_id in s.corroborating_evidence_ids:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.INFERENCE_CIRCULAR_DEPENDENCY,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Circular inference dependency: evidence '{s.evidence_id}' cites itself as a corroborating premise.",
                    primitive="SOURCE",
                    field_name="corroborating_evidence_ids"
                ))
                return False, CoherenceVerdict.FAIL, diagnostics

            for corrob_id in sorted(s.corroborating_evidence_ids):
                corrob_rec = self.registry.lookup(corrob_id)
                if not corrob_rec:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.EVIDENCE_NOT_FOUND,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Corroborating evidence ID '{corrob_id}' not found in registry.",
                        primitive="SOURCE",
                        field_name="corroborating_evidence_ids"
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics

                if s.authority_domain is not None and corrob_rec.domain not in s.authority_domain:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.EVIDENCE_DOMAIN_MISMATCH,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Corroborating evidence '{corrob_id}' domain '{corrob_rec.domain}' not in authority domain.",
                        primitive="SOURCE",
                        field_name="corroborating_evidence_ids"
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics

                if corrob_rec.epistemic_status not in [EpistemicStatus.FACT, EpistemicStatus.INFERENCE]:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.INFERENCE_PREMISE_INVALID_STATUS,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Corroborating premise '{corrob_id}' has invalid status '{corrob_rec.epistemic_status.value}'; must be FACT or verified INFERENCE.",
                        primitive="SOURCE",
                        field_name="corroborating_evidence_ids"
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics

                if corrob_rec.timestamp_sec > self.current_time_sec:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.TEMPORAL_FUTURE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Corroborating evidence '{corrob_id}' has future timestamp ({corrob_rec.timestamp_sec:.2f} > {self.current_time_sec:.2f}).",
                        primitive="SOURCE",
                        field_name="corroborating_evidence_ids"
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics

                corrob_age = self.current_time_sec - corrob_rec.timestamp_sec
                if corrob_age > s.max_age_sec:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.TEMPORAL_STALE,
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Corroborating evidence '{corrob_id}' is stale: age {corrob_age:.2f}s exceeds max_age_sec ({s.max_age_sec:.2f}s).",
                        primitive="SOURCE",
                        field_name="corroborating_evidence_ids"
                    ))
                    return False, CoherenceVerdict.REVIEW, diagnostics

        diagnostics.append(CoherenceDiagnostic(
            code=DiagnosticCode.EVIDENCE_PASS,
            severity=DiagnosticSeverity.INFO,
            message="Evidence verified against authoritative registry.",
            primitive="SOURCE"
        ))
        return True, CoherenceVerdict.PASS, diagnostics


class ScopeValidator:
    """
    Валидатор полномочий (P_SC и P_SD).
    Проверяет:
      C.domain_scope ⊆ S.authority_domain
      C.target_objects ⊆ S.granted_scope
      D.loss_domain ⊆ S.granted_loss_domains
    """

    def validate(
        self,
        s: SourcePrimitive,
        c: ConstraintPrimitive,
        d: DissipatePrimitive,
    ) -> Tuple[bool, CoherenceVerdict, List[CoherenceDiagnostic]]:
        diagnostics: List[CoherenceDiagnostic] = []

        # 1. Структурный дефект vs Нулевые привилегии
        # None = Структурный дефект
        # set() = Явно предоставленные нулевые привилегии
        has_defect = False
        if s.authority_domain is None:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_DEFECT_NONE,
                severity=DiagnosticSeverity.ERROR,
                message="Source authority_domain is None (structural defect).",
                primitive="SOURCE",
                field_name="authority_domain"
            ))
            has_defect = True

        if s.granted_scope is None:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_DEFECT_NONE,
                severity=DiagnosticSeverity.ERROR,
                message="Source granted_scope is None (structural defect).",
                primitive="SOURCE",
                field_name="granted_scope"
            ))
            has_defect = True

        if s.granted_loss_domains is None:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_DEFECT_NONE,
                severity=DiagnosticSeverity.ERROR,
                message="Source granted_loss_domains is None (structural defect).",
                primitive="SOURCE",
                field_name="granted_loss_domains"
            ))
            has_defect = True

        if has_defect:
            return False, CoherenceVerdict.FAIL, diagnostics

        failed = False

        # 2. Domain Scope Containment (P_SC)
        if not c.domain_scope.issubset(s.authority_domain):
            exceeded = c.domain_scope - s.authority_domain
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_EXCEEDED_DOMAIN,
                severity=DiagnosticSeverity.ERROR,
                message=f"Constraint domain scope {sorted(c.domain_scope)} exceeds granted authority: unauthorized {sorted(exceeded)}.",
                primitive="CONSTRAINT",
                field_name="domain_scope"
            ))
            failed = True

        # 3. Target Objects Containment (P_SC)
        if not c.target_objects.issubset(s.granted_scope):
            exceeded = c.target_objects - s.granted_scope
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_EXCEEDED_OBJECTS,
                severity=DiagnosticSeverity.ERROR,
                message=f"Constraint target objects {sorted(c.target_objects)} exceed granted scope: unauthorized {sorted(exceeded)}.",
                primitive="CONSTRAINT",
                field_name="target_objects"
            ))
            failed = True

        # 4. Loss Domain Containment (P_SD)
        if not d.loss_domain.issubset(s.granted_loss_domains):
            exceeded = d.loss_domain - s.granted_loss_domains
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.SCOPE_EXCEEDED_LOSS,
                severity=DiagnosticSeverity.ERROR,
                message=f"Dissipate loss domain {sorted(d.loss_domain)} exceeds granted loss domains: unauthorized {sorted(exceeded)}.",
                primitive="DISSIPATE",
                field_name="loss_domain"
            ))
            failed = True

        if failed:
            return False, CoherenceVerdict.FAIL, diagnostics

        diagnostics.append(CoherenceDiagnostic(
            code=DiagnosticCode.SCOPE_PASS,
            severity=DiagnosticSeverity.INFO,
            message="Scope and authority checks satisfied.",
            primitive="SOURCE"
        ))
        return True, CoherenceVerdict.PASS, diagnostics


class StateValidator:
    """
    Валидатор состояния, инвариантов и детерминированная симуляция (P_CD).
    """

    def validate(
        self,
        c: ConstraintPrimitive,
        d: DissipatePrimitive,
        initial_state: SystemState,
    ) -> Tuple[bool, CoherenceVerdict, List[CoherenceDiagnostic], Dict[str, float], Dict[str, bool]]:
        diagnostics: List[CoherenceDiagnostic] = []
        simulated_values: Dict[str, float] = {}
        simulated_flags: Dict[str, bool] = {}

        # 1. Проверка чисел (NaN, Inf)
        all_numeric_dicts = [
            ("initial_state.current_values", initial_state.current_values),
            ("dissipate.state_delta", d.state_delta),
            ("dissipate.resource_cost", d.resource_cost),
            ("constraint.min_bounds", c.min_bounds),
            ("constraint.max_bounds", c.max_bounds),
            ("constraint.protected_values", c.protected_values),
        ]
        for dict_name, ndict in all_numeric_dicts:
            for k, val in ndict.items():
                if math.isnan(val) or math.isinf(val):
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.STATE_INVALID_NUMERIC,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Non-finite numeric value ({val}) detected in '{dict_name}' for key '{k}'.",
                        primitive="DISSIPATE" if "dissipate" in dict_name else "CONSTRAINT",
                        field_name=k
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 2. Неотрицательность затрат ресурсов
        for res_name, cost in d.resource_cost.items():
            if cost < 0.0:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_NEGATIVE_RESOURCE_COST,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Negative resource cost ({cost}) for '{res_name}' is forbidden.",
                    primitive="DISSIPATE",
                    field_name=res_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 3. Полный вектор мутаций против защищённого множества (protected_set)
        flag_mut_keys = set(getattr(d, 'flag_delta', getattr(d, 'flag_mutations', {})))
        all_modified_params: Set[str] = (
            set(d.target_states) |
            set(d.side_effects) |
            set(d.state_delta.keys()) |
            set(d.resource_cost.keys()) |
            flag_mut_keys
        )

        protected_intersection = all_modified_params & c.protected_set
        if protected_intersection:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.STATE_PROTECTED_PARAM_MUTATED,
                severity=DiagnosticSeverity.ERROR,
                message=f"Dissipation mutates protected parameters: {sorted(protected_intersection)}.",
                primitive="DISSIPATE",
                field_name="protected_set"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 4. Проверка совместимости размерностей единиц
        for param in all_modified_params:
            d_unit = d.units.get(param)
            c_unit = c.units.get(param)
            s_unit = initial_state.units.get(param)

            if d_unit or c_unit:
                comp_dc, msg_dc = UnitRegistry.are_compatible(d_unit, c_unit)
                if not comp_dc:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Unit mismatch for param '{param}' between Dissipate ('{d_unit}') and Constraint ('{c_unit}'): {msg_dc}",
                        primitive="DISSIPATE",
                        field_name=param
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            if d_unit or s_unit:
                comp_ds, msg_ds = UnitRegistry.are_compatible(d_unit, s_unit)
                if not comp_ds:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Unit mismatch for param '{param}' between Dissipate ('{d_unit}') and SystemState ('{s_unit}'): {msg_ds}",
                        primitive="DISSIPATE",
                        field_name=param
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 5. Симуляция числовых параметров терминального состояния
        simulated_values = dict(initial_state.current_values)

        # Применение дельт со строгой конверсией размерностей
        for var_name, raw_delta in d.state_delta.items():
            base_unit = initial_state.units.get(var_name)
            delta_unit = d.units.get(var_name)
            effective_delta = raw_delta
            if delta_unit and base_unit and delta_unit.lower() != base_unit.lower():
                try:
                    effective_delta = UnitRegistry.convert(raw_delta, delta_unit, base_unit)
                except (DimensionalityError, UnknownUnitError) as err:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Failed to convert delta for '{var_name}' from '{delta_unit}' to '{base_unit}': {err}",
                        primitive="DISSIPATE",
                        field_name=var_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            simulated_values[var_name] = simulated_values.get(var_name, 0.0) + effective_delta

        # Вычитание затрат ресурсов
        for var_name, raw_cost in d.resource_cost.items():
            base_unit = initial_state.units.get(var_name)
            cost_unit = d.units.get(var_name)
            effective_cost = raw_cost
            if cost_unit and base_unit and cost_unit.lower() != base_unit.lower():
                try:
                    effective_cost = UnitRegistry.convert(raw_cost, cost_unit, base_unit)
                except (DimensionalityError, UnknownUnitError) as err:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Failed to convert resource cost for '{var_name}' from '{cost_unit}' to '{base_unit}': {err}",
                        primitive="DISSIPATE",
                        field_name=var_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            current_val = simulated_values.get(var_name, 0.0)
            simulated_values[var_name] = current_val - effective_cost

        # 6. Симуляция логических флагов
        simulated_flags = dict(initial_state.active_flags)
        flag_mutations_map = getattr(d, 'flag_delta', getattr(d, 'flag_mutations', {}))
        for flag_name, new_val in flag_mutations_map.items():
            if flag_name in c.protected_flags:
                initial_val = initial_state.active_flags.get(flag_name, False)
                if initial_val != new_val:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.STATE_FLAG_MUTATED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Flag '{flag_name}' is in protected_flags and cannot be mutated from {initial_val} to {new_val}.",
                        primitive="CONSTRAINT",
                        field_name=flag_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags
            simulated_flags[flag_name] = new_val

        # 7. Проверка обязательных переменных (Fail-Closed)
        required_vars = set(c.min_bounds.keys()) | set(c.max_bounds.keys()) | set(c.protected_values.keys())
        missing_vars = required_vars - set(simulated_values.keys())
        if missing_vars:
            diagnostics.append(CoherenceDiagnostic(
                code=DiagnosticCode.STATE_MISSING_VAR,
                severity=DiagnosticSeverity.ERROR,
                message=f"Missing required state variables in terminal simulation: {sorted(missing_vars)}.",
                primitive="CONSTRAINT",
                field_name="required_variables"
            ))
            return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 8. Проверка инвариантов флагов (запрещённые и обязательные)
        # Обработка как dict (flag -> val) так и set/list (flag names where forbidden is True)
        for flag_name, forbidden_val in (c.forbidden_flags.items() if isinstance(c.forbidden_flags, dict) else [(f, True) for f in c.forbidden_flags]):
            active_val = simulated_flags.get(flag_name, False)
            if active_val == forbidden_val:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_FORBIDDEN_FLAG_ACTIVE,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Terminal state flag '{flag_name}' holds forbidden value ({forbidden_val}).",
                    primitive="CONSTRAINT",
                    field_name=flag_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        for flag_name, required_val in (c.required_flags.items() if isinstance(c.required_flags, dict) else [(f, True) for f in c.required_flags]):
            active_val = simulated_flags.get(flag_name, False)
            if active_val != required_val:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_REQUIRED_FLAG_MISSING,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Terminal state flag '{flag_name}' is {active_val}, but required to be {required_val}.",
                    primitive="CONSTRAINT",
                    field_name=flag_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 9. Проверка инвариантных постоянных значений (protected_values)
        for var_name, expected_val in c.protected_values.items():
            sim_val = simulated_values[var_name]
            c_u = c.units.get(var_name)
            s_u = initial_state.units.get(var_name)
            eff_expected = expected_val
            if c_u and s_u and c_u.lower() != s_u.lower():
                try:
                    eff_expected = UnitRegistry.convert(expected_val, c_u, s_u)
                except Exception as err:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Failed to convert protected_value for '{var_name}': {err}",
                        primitive="CONSTRAINT",
                        field_name=var_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            if abs(sim_val - eff_expected) > 1e-9:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_PROTECTED_VALUE_MUTATED,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Protected value for '{var_name}' violated: simulated {sim_val:.4f} != expected {eff_expected:.4f}.",
                    primitive="CONSTRAINT",
                    field_name=var_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        # 10. Проверка границ (min_bounds и max_bounds)
        for var_name, min_bound in c.min_bounds.items():
            sim_val = simulated_values[var_name]
            c_u = c.units.get(var_name)
            s_u = initial_state.units.get(var_name)
            eff_min = min_bound
            if c_u and s_u and c_u.lower() != s_u.lower():
                try:
                    eff_min = UnitRegistry.convert(min_bound, c_u, s_u)
                except Exception as err:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Failed to convert min_bound for '{var_name}': {err}",
                        primitive="CONSTRAINT",
                        field_name=var_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            if sim_val < eff_min:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_MIN_BOUND_BREACH,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Variable '{var_name}' ({sim_val:.4f}) falls below min_bound ({eff_min:.4f}).",
                    primitive="CONSTRAINT",
                    field_name=var_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        for var_name, max_bound in c.max_bounds.items():
            sim_val = simulated_values[var_name]
            c_u = c.units.get(var_name)
            s_u = initial_state.units.get(var_name)
            eff_max = max_bound
            if c_u and s_u and c_u.lower() != s_u.lower():
                try:
                    eff_max = UnitRegistry.convert(max_bound, c_u, s_u)
                except Exception as err:
                    diagnostics.append(CoherenceDiagnostic(
                        code=DiagnosticCode.UNIT_INCOMPATIBLE,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Failed to convert max_bound for '{var_name}': {err}",
                        primitive="CONSTRAINT",
                        field_name=var_name
                    ))
                    return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

            if sim_val > eff_max:
                diagnostics.append(CoherenceDiagnostic(
                    code=DiagnosticCode.STATE_MAX_BOUND_BREACH,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Variable '{var_name}' ({sim_val:.4f}) exceeds max_bound ({eff_max:.4f}).",
                    primitive="CONSTRAINT",
                    field_name=var_name
                ))
                return False, CoherenceVerdict.FAIL, diagnostics, simulated_values, simulated_flags

        diagnostics.append(CoherenceDiagnostic(
            code=DiagnosticCode.STATE_PASS,
            severity=DiagnosticSeverity.INFO,
            message="State simulation and invariant checks satisfied.",
            primitive="STATE"
        ))
        return True, CoherenceVerdict.PASS, diagnostics, simulated_values, simulated_flags
