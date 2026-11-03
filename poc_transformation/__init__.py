"""
poc_transformation
External Transformation Contract Validator & Adapter for SOL-Triad Engine v1.
"""

from poc_transformation.validator import (
    TransformationContract,
    TransformationExecutionArtifact,
    ContractValidationResult,
    TransformationContractValidator,
    TRUSTED_TRANSFORMATION_RULES,
    SUPPORTED_OUTPUT_DIMENSIONS,
    SUPPORTED_CONDITION_OPERATORS,
)
from poc_transformation.adapter import TransformationToSolTriadAdapter

__all__ = [
    "TransformationContract",
    "TransformationExecutionArtifact",
    "ContractValidationResult",
    "TransformationContractValidator",
    "TransformationToSolTriadAdapter",
    "TRUSTED_TRANSFORMATION_RULES",
    "SUPPORTED_OUTPUT_DIMENSIONS",
    "SUPPORTED_CONDITION_OPERATORS",
]
