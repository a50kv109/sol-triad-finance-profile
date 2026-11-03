"""
Канонический детерминированный движок верификации SOL-Triad Core (SolTriadCoreKernel).
"""

import time
from typing import Optional, Callable, Dict, Any, List

from .models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    CoherenceVerdict,
    CoherenceDiagnostic,
    PairwiseStatus,
    EvaluationReport,
)
from .errors import DiagnosticCode
from .validators import EvidenceValidator, ScopeValidator, StateValidator
from .evidence import EvidenceRegistryOracle


class SolTriadCoreKernel:
    """
    Каноническое детерминированное ядро верификации согласованности SOL-Triad.
    Спецификация: 1.0.0-canonical.
    """
    PROTOCOL_VERSION = "1.0.0-canonical"
    ENGINE_VERSION = "1.0.0"

    def __init__(
        self,
        default_registry: Optional[EvidenceRegistryOracle] = None,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.default_registry = default_registry
        self.clock: Callable[[], float] = clock if clock is not None else time.time

    def evaluate(
        self,
        source: SourcePrimitive,
        constraint: ConstraintPrimitive,
        dissipate: DissipatePrimitive,
        initial_state: SystemState,
        evaluation_time_sec: Optional[float] = None,
        registry: Optional[EvidenceRegistryOracle] = None,
    ) -> EvaluationReport:
        """
        Выполняет строгую детерминированную верификацию триады (S, C, D).
        
        Параметры:
          source: Недоверенный примитив обоснования и полномочий
          constraint: Спецификация ограничений и инвариантов
          dissipate: Предлагаемое воздействие / дельта действия
          initial_state: Текущее состояние параметров среды
          evaluation_time_sec: Доверенное системное время хоста (если None, берётся из clock())
          registry: Авторитетный реестр свидетельств хоста (если None, берётся default_registry)
          
        Возвращает:
          EvaluationReport с неизменным вердиктом (PASS, REVIEW, FAIL) и execution_permitted=False.
        """
        eval_time = evaluation_time_sec if evaluation_time_sec is not None else self.clock()
        active_registry = registry if registry is not None else self.default_registry

        evidence_val = EvidenceValidator(active_registry, eval_time)
        scope_val = ScopeValidator()
        state_val = StateValidator()

        all_diagnostics: List[CoherenceDiagnostic] = []

        # 1. Верификация свидетельств (проекция P_SC)
        ev_ok, ev_verdict, ev_diags = evidence_val.validate(source)
        all_diagnostics.extend(ev_diags)

        # 2. Верификация полномочий и доменов (проекции P_SC и P_SD)
        sc_ok, sc_verdict, sc_diags = scope_val.validate(source, constraint, dissipate)
        all_diagnostics.extend(sc_diags)

        # 3. Верификация состояния, физических инвариантов и симуляция (проекция P_CD)
        st_ok, st_verdict, st_diags, sim_values, sim_flags = state_val.validate(
            constraint, dissipate, initial_state
        )
        all_diagnostics.extend(st_diags)

        # Формирование статусов парных проекций:
        # P_SC: Обоснование и полномочия (Source <-> Constraint)
        p_sc_fail = (
            ev_verdict == CoherenceVerdict.FAIL or
            any(d.code in (
                DiagnosticCode.SCOPE_EXCEEDED_DOMAIN,
                DiagnosticCode.SCOPE_EXCEEDED_OBJECTS,
                DiagnosticCode.SCOPE_DEFECT_NONE,
            ) for d in sc_diags)
        )
        p_sc_review = (ev_verdict == CoherenceVerdict.REVIEW)
        p_sc_verdict = (
            CoherenceVerdict.FAIL if p_sc_fail
            else (CoherenceVerdict.REVIEW if p_sc_review else CoherenceVerdict.PASS)
        )
        p_sc_diags = [
            d for d in (ev_diags + sc_diags)
            if d.primitive in ("SOURCE", "CONSTRAINT")
        ]
        p_sc = PairwiseStatus(
            is_valid=(p_sc_verdict == CoherenceVerdict.PASS),
            verdict=p_sc_verdict,
            diagnostics=p_sc_diags,
        )

        # P_SD: Авторизация домена потерь (Source <-> Dissipate)
        p_sd_fail = any(d.code == DiagnosticCode.SCOPE_EXCEEDED_LOSS for d in sc_diags)
        p_sd_verdict = CoherenceVerdict.FAIL if p_sd_fail else CoherenceVerdict.PASS
        p_sd_diags = [d for d in sc_diags if d.primitive == "DISSIPATE"]
        p_sd = PairwiseStatus(
            is_valid=(p_sd_verdict == CoherenceVerdict.PASS),
            verdict=p_sd_verdict,
            diagnostics=p_sd_diags,
        )

        # P_CD: Состояние и инварианты (Constraint <-> Dissipate)
        p_cd = PairwiseStatus(
            is_valid=st_ok,
            verdict=st_verdict,
            diagnostics=st_diags,
        )

        # 4. Логика арбитра решений (Decision Arbiter)
        if (p_sc.verdict == CoherenceVerdict.FAIL or
            p_sd.verdict == CoherenceVerdict.FAIL or
            p_cd.verdict == CoherenceVerdict.FAIL):
            final_verdict = CoherenceVerdict.FAIL
        elif (p_sc.verdict == CoherenceVerdict.REVIEW or
              p_sd.verdict == CoherenceVerdict.REVIEW or
              p_cd.verdict == CoherenceVerdict.REVIEW):
            final_verdict = CoherenceVerdict.REVIEW
        else:
            final_verdict = CoherenceVerdict.PASS

        return EvaluationReport(
            protocol_version=self.PROTOCOL_VERSION,
            verdict=final_verdict,
            pairwise_checks={
                "P_SC": p_sc,
                "P_SD": p_sd,
                "P_CD": p_cd,
            },
            simulated_values=sim_values,
            simulated_flags=sim_flags,
            diagnostics=all_diagnostics,
            execution_permitted=False,  # Ядро принципиально не даёт разрешения на исполнение!
        )
