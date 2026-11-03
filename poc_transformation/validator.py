"""
poc_transformation/validator.py
Strict External Transformation Contract Validator for SOL-Triad v1.

Architectural Guarantees:
1. Zero dynamic code execution (closed dictionary of pure Python arithmetic functions).
2. Grounded Data Anchoring with multi-unit comparison:
   Registered EvidenceRecord metadata['value'] and metadata['unit'] are converted
   to the artifact's claimed unit before anti-tampering verification.
3. Physical dimensionality checks via UnitRegistry.DIMENSIONS and output dimension taxonomy.
4. Output unit consistency verification (ensuring output_schema and output_units agree).
5. Exhaustive Schema Enforcement: rejection of extraneous keys, missing keys,
   unsupported operators, or non-finite condition thresholds.
6. Multi-process collision-free ID generation incorporating PID, nanosecond timestamp,
   monotonic counter, and SHA-256 parameter digest.
7. Explicit epistemic boundaries (syntactic & arithmetic coherence vs physical truth).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Callable, Tuple
import os
import time
import math
import itertools
import hashlib

from sol_triad.models import (
    EvidenceRecord,
    EpistemicStatus,
)
from sol_triad.evidence import EvidenceRegistryOracle
from sol_triad.units import UnitRegistry, UnknownUnitError, DimensionalityError


# -------------------------------------------------------------------------
# Taxonomy of Known Physical Dimensions & Allowed Units
# -------------------------------------------------------------------------
SUPPORTED_OUTPUT_DIMENSIONS: Dict[str, Set[str]] = {
    "area": {"m2", "cm2", "mm2", "km2"},
    "length": {"m", "cm", "mm", "km", "inch", "ft"},
    "pressure": {"pa", "kpa", "mpa", "bar", "mbar", "psi", "atm", "torr"},
    "time": {"s", "sec", "ms", "min", "hr", "hour", "day"},
    "energy": {"j", "joule", "kj", "kwh", "cal", "kcal"},
    "mass": {"kg", "g", "mg", "lb"},
    "ratio": {"ratio", "fraction", "percent", "%", "ppm"},
    "frequency": {"hz", "khz", "mhz"},
}

SUPPORTED_CONDITION_OPERATORS: Set[str] = {
    "min_exclusive",
    "max_inclusive",
    "min_inclusive",
    "max_exclusive",
}


# -------------------------------------------------------------------------
# Closed Registry of Trusted Pure Functions (Zero eval/exec)
# -------------------------------------------------------------------------
def _rule_rect_area_v1(normalized_inputs: Dict[str, float]) -> Dict[str, float]:
    """
    Computes rectangular area: area = width * height.
    Expects inputs normalized to meters ('m'). Returns area in square meters ('m2').
    """
    w = normalized_inputs["width"]
    h = normalized_inputs["height"]
    return {"area": w * h}


TRUSTED_TRANSFORMATION_RULES: Dict[str, Callable[[Dict[str, float]], Dict[str, float]]] = {
    "area_multiplication_v1": _rule_rect_area_v1,
}


# -------------------------------------------------------------------------
# Formal Contract Schema
# -------------------------------------------------------------------------
@dataclass(frozen=True)
class TransformationContract:
    transform_id: str
    version: str
    input_schema: Dict[str, str]       # {param: expected_dimension, e.g., 'length'}
    input_base_units: Dict[str, str]   # {param: base_unit_for_rule, e.g., 'm'}
    output_schema: Dict[str, str]      # {param: dimension_name, e.g., 'area'}
    output_units: Dict[str, str]       # {param: required_output_unit, e.g., 'm2'}
    rule_id: str                       # must exist in TRUSTED_TRANSFORMATION_RULES
    preconditions: Dict[str, Dict[str, float]]
    postconditions: Dict[str, Dict[str, float]]
    invariants: List[str]
    target_domain: str


@dataclass
class TransformationExecutionArtifact:
    contract_id: str
    input_evidence_ids: Dict[str, str]       # param -> evidence_id in registry
    claimed_input_values: Dict[str, float]   # values claimed by agent
    input_units: Dict[str, str]              # units of inputs claimed by agent
    claimed_output_values: Dict[str, float]  # values claimed as output
    output_units: Dict[str, str]             # units of output claimed by agent
    provenance_reference: str                # audit reference
    claimed_rule_id: str                     # rule claimed by agent


@dataclass
class ContractValidationResult:
    is_valid: bool
    errors: List[str]
    contract_syntactic_and_arithmetic_satisfied: bool = False
    derived_record: Optional[EvidenceRecord] = None
    corroborating_evidence_ids: Set[str] = field(default_factory=set)


# -------------------------------------------------------------------------
# Validator Implementation
# -------------------------------------------------------------------------
class TransformationContractValidator:
    TOLERANCE: float = 1e-9
    _id_counter = itertools.count(1)

    def __init__(self, contract: TransformationContract, registry: EvidenceRegistryOracle):
        self.contract = contract
        self.registry = registry

    def _validate_contract_definition(self) -> List[str]:
        """
        Exhaustively validates contract internal consistency.
        Rejects unknown fields, cross-dictionary key mismatches,
        inconsistent dimensions/units, and unsupported condition operators.
        """
        errs: List[str] = []

        if not self.contract.transform_id or not self.contract.transform_id.strip():
            errs.append("CONTRACT_DEFECT: Missing or empty transform_id.")
        if not self.contract.version or not self.contract.version.strip():
            errs.append("CONTRACT_DEFECT: Missing or empty version.")

        if not self.contract.input_schema or not self.contract.output_schema:
            errs.append("CONTRACT_DEFECT: Missing input_schema or output_schema definitions.")

        # Cross-dictionary key consistency for inputs
        in_schema_keys = set(self.contract.input_schema.keys())
        in_base_keys = set(self.contract.input_base_units.keys())
        if in_schema_keys != in_base_keys:
            errs.append(
                f"CONTRACT_DEFECT: input_schema keys {sorted(list(in_schema_keys))} != input_base_units keys {sorted(list(in_base_keys))}."
            )

        # Cross-dictionary key consistency for outputs
        out_schema_keys = set(self.contract.output_schema.keys())
        out_units_keys = set(self.contract.output_units.keys())
        if out_schema_keys != out_units_keys:
            errs.append(
                f"CONTRACT_DEFECT: output_schema keys {sorted(list(out_schema_keys))} != output_units keys {sorted(list(out_units_keys))}."
            )

        # Input dimensions verification
        for param, dim in self.contract.input_schema.items():
            base_u = self.contract.input_base_units.get(param)
            if base_u:
                base_u_norm = UnitRegistry.normalize_unit(base_u)
                base_dim = UnitRegistry.get_dimension(base_u_norm)
                if base_dim != dim:
                    errs.append(
                        f"CONTRACT_DEFECT: Input '{param}' base_unit '{base_u}' dimension '{base_dim}' != schema '{dim}'."
                    )

        # Output dimensions verification and consistency check
        for param, dim in self.contract.output_schema.items():
            req_u = self.contract.output_units.get(param)
            if not req_u:
                continue
            req_u_norm = req_u.strip().lower()
            if dim not in SUPPORTED_OUTPUT_DIMENSIONS:
                errs.append(f"CONTRACT_DEFECT: Unsupported output dimension '{dim}' for '{param}'.")
            else:
                allowed_units = SUPPORTED_OUTPUT_DIMENSIONS[dim]
                if req_u_norm not in allowed_units:
                    errs.append(
                        f"CONTRACT_DEFECT: Output '{param}' declared dimension '{dim}' is incompatible with unit '{req_u}'. Allowed: {sorted(list(allowed_units))}."
                    )

        # Trusted rule registration check
        if self.contract.rule_id not in TRUSTED_TRANSFORMATION_RULES:
            errs.append(f"UNTRUSTED_RULE: Rule '{self.contract.rule_id}' not in trusted registry.")

        # Precondition structure and operator verification
        for param, conds in self.contract.preconditions.items():
            if param not in in_schema_keys:
                errs.append(f"CONTRACT_DEFECT: Precondition references undeclared input '{param}'.")
            if not isinstance(conds, dict) or not conds:
                errs.append(f"CONTRACT_DEFECT: Preconditions for '{param}' must be a non-empty dictionary.")
                continue
            for op, val in conds.items():
                if op not in SUPPORTED_CONDITION_OPERATORS:
                    errs.append(f"CONTRACT_DEFECT: Unsupported precondition operator '{op}' on '{param}'.")
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    errs.append(f"CONTRACT_DEFECT: Precondition threshold for '{param}.{op}' must be a finite number.")

        # Postcondition structure and operator verification
        for param, conds in self.contract.postconditions.items():
            if param not in out_schema_keys:
                errs.append(f"CONTRACT_DEFECT: Postcondition references undeclared output '{param}'.")
            if not isinstance(conds, dict) or not conds:
                errs.append(f"CONTRACT_DEFECT: Postconditions for '{param}' must be a non-empty dictionary.")
                continue
            for op, val in conds.items():
                if op not in SUPPORTED_CONDITION_OPERATORS:
                    errs.append(f"CONTRACT_DEFECT: Unsupported postcondition operator '{op}' on '{param}'.")
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    errs.append(f"CONTRACT_DEFECT: Postcondition threshold for '{param}.{op}' must be a finite number.")

        return errs

    def validate(
        self,
        artifact: TransformationExecutionArtifact,
        current_time_sec: float,
    ) -> ContractValidationResult:
        errors: List[str] = []

        # 1. Contract Definition Validation
        contract_errors = self._validate_contract_definition()
        if contract_errors:
            return ContractValidationResult(
                is_valid=False,
                errors=contract_errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        if artifact.contract_id != self.contract.transform_id:
            return ContractValidationResult(
                is_valid=False,
                errors=[f"CONTRACT_MISMATCH: Artifact specifies '{artifact.contract_id}', expected '{self.contract.transform_id}'."],
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        if artifact.claimed_rule_id != self.contract.rule_id:
            return ContractValidationResult(
                is_valid=False,
                errors=[f"RULE_ID_MISMATCH: Artifact claimed rule '{artifact.claimed_rule_id}', contract requires '{self.contract.rule_id}'."],
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 2. Exhaustive Key Verification across all Artifact Dictionaries
        expected_in_keys = set(self.contract.input_schema.keys())
        expected_out_keys = set(self.contract.output_schema.keys())

        # Check input_evidence_ids
        if set(artifact.input_evidence_ids.keys()) != expected_in_keys:
            extra = set(artifact.input_evidence_ids.keys()) - expected_in_keys
            missing = expected_in_keys - set(artifact.input_evidence_ids.keys())
            if extra:
                errors.append(f"EXTRANEOUS_INPUT_PARAMETERS: Unexpected input_evidence_ids keys {sorted(list(extra))}.")
            if missing:
                errors.append(f"MISSING_INPUT_PARAMETERS: Missing input_evidence_ids keys {sorted(list(missing))}.")

        # Check claimed_input_values
        if set(artifact.claimed_input_values.keys()) != expected_in_keys:
            extra = set(artifact.claimed_input_values.keys()) - expected_in_keys
            missing = expected_in_keys - set(artifact.claimed_input_values.keys())
            if extra:
                errors.append(f"EXTRANEOUS_ARTIFACT_KEYS: Unexpected claimed_input_values keys {sorted(list(extra))}.")
            if missing:
                errors.append(f"MISSING_ARTIFACT_KEYS: Missing claimed_input_values keys {sorted(list(missing))}.")

        # Check input_units
        if set(artifact.input_units.keys()) != expected_in_keys:
            extra = set(artifact.input_units.keys()) - expected_in_keys
            missing = expected_in_keys - set(artifact.input_units.keys())
            if extra:
                errors.append(f"EXTRANEOUS_ARTIFACT_KEYS: Unexpected input_units keys {sorted(list(extra))}.")
            if missing:
                errors.append(f"MISSING_ARTIFACT_KEYS: Missing input_units keys {sorted(list(missing))}.")

        # Check claimed_output_values
        if set(artifact.claimed_output_values.keys()) != expected_out_keys:
            extra = set(artifact.claimed_output_values.keys()) - expected_out_keys
            missing = expected_out_keys - set(artifact.claimed_output_values.keys())
            if extra:
                errors.append(f"EXTRANEOUS_ARTIFACT_KEYS: Unexpected claimed_output_values keys {sorted(list(extra))}.")
            if missing:
                errors.append(f"MISSING_ARTIFACT_KEYS: Missing claimed_output_values keys {sorted(list(missing))}.")

        # Check output_units
        if set(artifact.output_units.keys()) != expected_out_keys:
            extra = set(artifact.output_units.keys()) - expected_out_keys
            missing = expected_out_keys - set(artifact.output_units.keys())
            if extra:
                errors.append(f"EXTRANEOUS_ARTIFACT_KEYS: Unexpected output_units keys {sorted(list(extra))}.")
            if missing:
                errors.append(f"MISSING_ARTIFACT_KEYS: Missing output_units keys {sorted(list(missing))}.")

        # Audit Reference
        if not artifact.provenance_reference or not artifact.provenance_reference.strip():
            errors.append("PROVENANCE_MISSING: artifact.provenance_reference must not be empty.")

        if errors:
            return ContractValidationResult(
                is_valid=False,
                errors=errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 3. Input Grounding, Dimensionality, & Multi-Unit Comparison
        corroborating_ids: Set[str] = set()
        normalized_inputs_for_rule: Dict[str, float] = {}

        for param_name, expected_dim in self.contract.input_schema.items():
            ev_id = artifact.input_evidence_ids[param_name]
            record = self.registry.get_record(ev_id)
            if not record:
                errors.append(f"EVIDENCE_NOT_FOUND: EvidenceRecord '{ev_id}' for '{param_name}' not found in registry.")
                continue

            corroborating_ids.add(ev_id)

            if record.epistemic_status not in (EpistemicStatus.FACT, EpistemicStatus.INFERENCE):
                errors.append(f"EVIDENCE_INVALID_STATUS: Record '{ev_id}' has invalid status '{record.epistemic_status.value}'.")

            if record.timestamp_sec > current_time_sec:
                errors.append(f"TEMPORAL_FUTURE: Record '{ev_id}' has future timestamp ({record.timestamp_sec} > {current_time_sec}).")

            # Extract truth values from authoritative registry record
            registered_raw_val = record.metadata.get("value")
            registered_unit = record.metadata.get("unit")

            if registered_raw_val is None:
                errors.append(f"EVIDENCE_METADATA_DEFECT: Record '{ev_id}' lacks 'value' in metadata.")
                continue

            if not isinstance(registered_raw_val, (int, float)) or math.isnan(registered_raw_val) or math.isinf(registered_raw_val):
                errors.append(f"EVIDENCE_VALUE_NONFINITE: Record '{ev_id}' contains non-finite number: {registered_raw_val}.")
                continue

            claimed_unit = artifact.input_units[param_name].strip().lower()
            claimed_unit_dim = UnitRegistry.DIMENSIONS.get(claimed_unit)
            if claimed_unit_dim != expected_dim:
                errors.append(
                    f"UNIT_DIMENSION_MISMATCH: Input '{param_name}' claimed unit '{claimed_unit}' dimension '{claimed_unit_dim}' != expected '{expected_dim}'."
                )
                continue

            # If registered record has a unit, verify dimensional compatibility
            if registered_unit:
                reg_norm_unit = registered_unit.strip().lower()
                reg_dim = UnitRegistry.DIMENSIONS.get(reg_norm_unit)
                if reg_dim != expected_dim:
                    errors.append(
                        f"REGISTERED_UNIT_DIMENSION_MISMATCH: Record '{ev_id}' unit '{registered_unit}' dimension '{reg_dim}' != expected '{expected_dim}'."
                    )
                    continue

                # Multi-unit anti-tampering verification:
                # Convert registered value from registered unit to claimed unit
                try:
                    registered_val_in_claimed_units = UnitRegistry.convert(
                        float(registered_raw_val), reg_norm_unit, claimed_unit
                    )
                except Exception as conv_err:
                    errors.append(
                        f"UNIT_CONVERSION_FAILED: Cannot convert registered '{ev_id}' from '{registered_unit}' to claimed '{claimed_unit}': {conv_err}"
                    )
                    continue

                claimed_val = artifact.claimed_input_values[param_name]
                if abs(claimed_val - registered_val_in_claimed_units) > self.TOLERANCE:
                    errors.append(
                        f"INPUT_VALUE_TAMPERED: Claimed '{param_name}' ({claimed_val} {claimed_unit}) != registered '{ev_id}' ({registered_raw_val} {registered_unit} -> {registered_val_in_claimed_units} {claimed_unit})."
                    )
                    continue
            else:
                # If no registered unit is given, compare directly assuming same unit
                claimed_val = artifact.claimed_input_values[param_name]
                if abs(claimed_val - float(registered_raw_val)) > self.TOLERANCE:
                    errors.append(
                        f"INPUT_VALUE_TAMPERED: Claimed '{param_name}' ({claimed_val}) != registered '{ev_id}' ({registered_raw_val})."
                    )
                    continue

            # Convert to contract's base unit for rule execution
            base_unit = self.contract.input_base_units[param_name]
            try:
                converted_for_rule = UnitRegistry.convert(claimed_val, claimed_unit, base_unit)
            except Exception as conv_err:
                errors.append(
                    f"UNIT_CONVERSION_FAILED: Failed converting '{param_name}' from '{claimed_unit}' to '{base_unit}': {conv_err}"
                )
                continue

            normalized_inputs_for_rule[param_name] = converted_for_rule

        if errors:
            return ContractValidationResult(
                is_valid=False,
                errors=errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 4. Precondition Evaluation on Converted Base Values
        for param_name, cond in self.contract.preconditions.items():
            val = normalized_inputs_for_rule[param_name]
            if "min_exclusive" in cond and val <= cond["min_exclusive"]:
                errors.append(f"PRECONDITION_VIOLATION: Input '{param_name}' in base units ({val}) must be > {cond['min_exclusive']}.")
            if "min_inclusive" in cond and val < cond["min_inclusive"]:
                errors.append(f"PRECONDITION_VIOLATION: Input '{param_name}' in base units ({val}) must be >= {cond['min_inclusive']}.")
            if "max_inclusive" in cond and val > cond["max_inclusive"]:
                errors.append(f"PRECONDITION_VIOLATION: Input '{param_name}' in base units ({val}) must be <= {cond['max_inclusive']}.")
            if "max_exclusive" in cond and val >= cond["max_exclusive"]:
                errors.append(f"PRECONDITION_VIOLATION: Input '{param_name}' in base units ({val}) must be < {cond['max_exclusive']}.")

        if errors:
            return ContractValidationResult(
                is_valid=False,
                errors=errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 5. Output Units Verification
        for out_name, exp_unit in self.contract.output_units.items():
            claimed_out_unit = artifact.output_units[out_name].strip().lower()
            if claimed_out_unit != exp_unit.strip().lower():
                errors.append(f"OUTPUT_UNIT_MISMATCH: Output '{out_name}' unit '{claimed_out_unit}' != contract required '{exp_unit}'.")

        if errors:
            return ContractValidationResult(
                is_valid=False,
                errors=errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 6. Trusted Pure Rule Execution
        trusted_func = TRUSTED_TRANSFORMATION_RULES[self.contract.rule_id]
        try:
            computed_outputs = trusted_func(normalized_inputs_for_rule)
        except Exception as exc:
            return ContractValidationResult(
                is_valid=False,
                errors=[f"EXECUTION_FAILURE: Trusted rule error: {exc}."],
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # Check that computed outputs strictly match output_schema keys
        if set(computed_outputs.keys()) != expected_out_keys:
            return ContractValidationResult(
                is_valid=False,
                errors=[f"RULE_OUTPUT_SCHEMA_MISMATCH: Rule returned {sorted(list(computed_outputs.keys()))} != schema {sorted(list(expected_out_keys))}."],
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 7. Output Numerical Verification
        for out_name in self.contract.output_schema.keys():
            expected_val = computed_outputs[out_name]
            claimed_val = artifact.claimed_output_values[out_name]

            if math.isnan(claimed_val) or math.isinf(claimed_val):
                errors.append(f"OUTPUT_NONFINITE: Output '{out_name}' is non-finite.")
                continue

            if abs(claimed_val - expected_val) > self.TOLERANCE:
                errors.append(f"OUTPUT_CALCULATION_MISMATCH: Claimed '{out_name}' ({claimed_val}) != computed ({expected_val}).")

        # 8. Postconditions Verification
        for out_name, cond in self.contract.postconditions.items():
            val = computed_outputs[out_name]
            if "min_exclusive" in cond and val <= cond["min_exclusive"]:
                errors.append(f"POSTCONDITION_VIOLATION: Computed output '{out_name}' ({val}) must be > {cond['min_exclusive']}.")
            if "min_inclusive" in cond and val < cond["min_inclusive"]:
                errors.append(f"POSTCONDITION_VIOLATION: Computed output '{out_name}' ({val}) must be >= {cond['min_inclusive']}.")
            if "max_inclusive" in cond and val > cond["max_inclusive"]:
                errors.append(f"POSTCONDITION_VIOLATION: Computed output '{out_name}' ({val}) must be <= {cond['max_inclusive']}.")
            if "max_exclusive" in cond and val >= cond["max_exclusive"]:
                errors.append(f"POSTCONDITION_VIOLATION: Computed output '{out_name}' ({val}) must be < {cond['max_exclusive']}.")

        if errors:
            return ContractValidationResult(
                is_valid=False,
                errors=errors,
                contract_syntactic_and_arithmetic_satisfied=False,
            )

        # 9. Multi-Process Collision-Free Unique Derived Evidence ID
        counter_val = next(self._id_counter)
        ts_ns = time.time_ns()
        pid = os.getpid()
        inputs_digest = hashlib.sha256(
            f"{pid}:{ts_ns}:{counter_val}:" .join(f"{k}:{v}" for k, v in sorted(normalized_inputs_for_rule.items())).encode("utf-8")
        ).hexdigest()[:10]
        unique_evidence_id = f"ev-derived-{self.contract.transform_id}-{ts_ns}-p{pid}-c{counter_val}-{inputs_digest}"

        derived_record = EvidenceRecord(
            evidence_id=unique_evidence_id,
            domain=self.contract.target_domain,
            epistemic_status=EpistemicStatus.INFERENCE,
            timestamp_sec=current_time_sec,
            metadata={
                "contract_id": self.contract.transform_id,
                "version": self.contract.version,
                "rule_id": self.contract.rule_id,
                "provenance_reference": artifact.provenance_reference,
                "computed_values": computed_outputs,
                "output_units": artifact.output_units,
                "normalized_inputs": normalized_inputs_for_rule,
                "corroborating_evidence_ids": sorted(list(corroborating_ids)),
                "contract_syntactic_and_arithmetic_satisfied": True,
                "epistemic_scope": "SYNTACTIC_ARITHMETIC_COHERENCE_ONLY",
                "epistemic_boundary_notice": (
                    "Confirms arithmetic correctness, unit conversion consistency, and contract schema "
                    "against registered evidence premises. Does NOT assert empirical ground truth of the model itself."
                ),
            },
        )

        return ContractValidationResult(
            is_valid=True,
            errors=[],
            contract_syntactic_and_arithmetic_satisfied=True,
            derived_record=derived_record,
            corroborating_evidence_ids=corroborating_ids,
        )
