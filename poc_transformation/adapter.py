"""
poc_transformation/adapter.py
Decoupled Adapter bridging TransformationContractValidator artifacts to SOL-Triad v1 Primitives.

Adheres strictly to core interfaces:
- sol_triad.models: EvidenceRecord, SourcePrimitive, ConstraintPrimitive, DissipatePrimitive, SystemState
- sol_triad.validators: EvidenceValidator
- sol_triad.engine: SolTriadEngine
"""

from typing import Set, Optional, Tuple, List, Dict, Any

from sol_triad.models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    CoherenceDiagnostic,
    EvaluationReport,
)
from sol_triad.evidence import EvidenceRegistryOracle
from sol_triad.validators import EvidenceValidator
from sol_triad.engine import SolTriadEngine

from poc_transformation.validator import ContractValidationResult


class TransformationToSolTriadAdapter:
    """
    Formal bridge between Transformation Validation and SOL-Triad v1 Core.

    Responsibilities:
    1. Registers the validated derived EvidenceRecord (INFERENCE) into the authoritative registry.
    2. Constructs a fully grounded SourcePrimitive citing all corroborating_evidence_ids.
    3. Exposes direct execution against core EvidenceValidator (step 7 INFERENCE check).
    4. Exposes full end-to-end evaluation against SolTriadEngine.
    """

    def __init__(self, registry: EvidenceRegistryOracle, engine: Optional[SolTriadEngine] = None):
        self.registry = registry
        self.engine = engine if engine is not None else SolTriadEngine(registry=registry)

    def register_derived_evidence(self, result: ContractValidationResult) -> EvidenceRecord:
        """
        Registers the derived record in the authoritative registry.
        Fails closed if the validation result is not valid.
        """
        if not result.is_valid or result.derived_record is None:
            raise ValueError("Cannot register invalid transformation result in authoritative registry.")
        self.registry.register(result.derived_record)
        return result.derived_record

    def build_source_primitive(
        self,
        result: ContractValidationResult,
        authority_domain: Set[str],
        granted_scope: Set[str],
        granted_loss_domains: Optional[Set[str]] = None,
        max_age_sec: float = 300.0,
        omit_premises_for_testing: bool = False,
    ) -> SourcePrimitive:
        """
        Constructs a SOL-Triad v1 SourcePrimitive for the derived evidence.
        Transfers the corroborating premises from the validator result into
        SourcePrimitive.corroborating_evidence_ids.
        """
        if not result.is_valid or result.derived_record is None:
            raise ValueError("Cannot build SourcePrimitive from an invalid ContractValidationResult.")

        premises = set() if omit_premises_for_testing else set(result.corroborating_evidence_ids)

        return SourcePrimitive(
            evidence_id=result.derived_record.evidence_id,
            authority_domain=authority_domain,
            granted_scope=granted_scope,
            granted_loss_domains=granted_loss_domains if granted_loss_domains is not None else set(),
            epistemic_type=EpistemicStatus.INFERENCE,
            timestamp_sec=result.derived_record.timestamp_sec,
            max_age_sec=max_age_sec,
            corroborating_evidence_ids=premises,
            payload_hash=result.derived_record.payload_hash,
        )

    def validate_with_evidence_validator(
        self,
        source: SourcePrimitive,
        current_time_sec: float,
    ) -> Tuple[bool, CoherenceVerdict, List[CoherenceDiagnostic]]:
        """
        Directly invokes the core SOL-Triad v1 EvidenceValidator on the constructed SourcePrimitive.
        """
        validator = EvidenceValidator(registry=self.registry, current_time_sec=current_time_sec)
        return validator.validate(source)

    def evaluate_with_engine(
        self,
        source: SourcePrimitive,
        constraint: ConstraintPrimitive,
        dissipate: DissipatePrimitive,
        state: SystemState,
        evaluation_time: Optional[float] = None,
    ) -> EvaluationReport:
        """
        Executes complete end-to-end triadic evaluation through the SolTriadEngine.
        """
        return self.engine.evaluate(
            s=source,
            c=constraint,
            d=dissipate,
            initial_state=state,
            evaluation_time=evaluation_time,
        )
