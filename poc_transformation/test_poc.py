"""
poc_transformation/test_poc.py
Definitive Executable Test Suite for TransformationContractValidator,
TransformationToSolTriadAdapter, and SOL-Triad v1 Core Interfaces.

Runs without external test frameworks (pure standard library).
"""

import sys
import os
import time

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from sol_triad.models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
    DiagnosticSeverity,
)
from sol_triad.evidence import InMemoryEvidenceRegistry
from sol_triad.engine import SolTriadEngine
from sol_triad.validators import EvidenceValidator

from poc_transformation.validator import (
    TransformationContract,
    TransformationExecutionArtifact,
    TransformationContractValidator,
    SUPPORTED_OUTPUT_DIMENSIONS,
)
from poc_transformation.adapter import TransformationToSolTriadAdapter


def run_all_tests() -> bool:
    print("=" * 80)
    print("EXHAUSTIVE TEST SUITE: TransformationContractValidator & Adapter (SOL-Triad v1)")
    print(f"Python Runtime: {sys.version.split()[0]} | PID: {os.getpid()}")
    print("=" * 80)

    all_passed = True

    # Standard valid rectangular area contract
    valid_contract = TransformationContract(
        transform_id="rect_area_calc",
        version="1.0.0",
        input_schema={"width": "length", "height": "length"},
        input_base_units={"width": "m", "height": "m"},
        output_schema={"area": "area"},
        output_units={"area": "m2"},
        rule_id="area_multiplication_v1",
        preconditions={
            "width": {"min_exclusive": 0.0, "max_inclusive": 1000.0},
            "height": {"min_exclusive": 0.0, "max_inclusive": 1000.0},
        },
        postconditions={"area": {"min_exclusive": 0.0}},
        invariants=["area_positive_definiteness", "commutativity"],
        target_domain="structural_engineering",
    )

    current_ts = 1740000100.0

    # Initialize authoritative evidence registry
    registry = InMemoryEvidenceRegistry()

    # Fact 1: width in meters (5.0 m)
    rec_w_m = EvidenceRecord(
        evidence_id="ev-sensor-w1-m",
        domain="structural_engineering",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=1740000000.0,
        metadata={"value": 5.0, "unit": "m", "sensor_serial": "LIDAR-01"},
    )
    # Fact 2: height in meters (3.0 m)
    rec_h_m = EvidenceRecord(
        evidence_id="ev-sensor-h1-m",
        domain="structural_engineering",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=1740000000.0,
        metadata={"value": 3.0, "unit": "m", "sensor_serial": "LIDAR-02"},
    )
    # Fact 3: width stored in centimeters (500.0 cm = 5.0 m)
    rec_w_cm = EvidenceRecord(
        evidence_id="ev-sensor-w-500cm",
        domain="structural_engineering",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=1740000000.0,
        metadata={"value": 500.0, "unit": "cm", "sensor_serial": "CALIPER-03"},
    )

    registry.register(rec_w_m)
    registry.register(rec_h_m)
    registry.register(rec_w_cm)

    validator = TransformationContractValidator(valid_contract, registry)

    # -------------------------------------------------------------------------
    # TEST 1: Baseline Valid Execution (5.0 m * 3.0 m = 15.0 m2)
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Базовый валидный расчёт (5.0 m * 3.0 m = 15.0 m^2)")
    art1 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w1-m", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 5.0, "height": 3.0},
        input_units={"width": "m", "height": "m"},
        claimed_output_values={"area": 15.0},
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res1 = validator.validate(art1, current_ts)
    t1_ok = (
        res1.is_valid is True
        and res1.contract_syntactic_and_arithmetic_satisfied is True
        and res1.derived_record is not None
        and res1.derived_record.epistemic_status == EpistemicStatus.INFERENCE
        and res1.derived_record.metadata["computed_values"]["area"] == 15.0
        and res1.derived_record.metadata["epistemic_scope"] == "SYNTACTIC_ARITHMETIC_COHERENCE_ONLY"
    )
    print(f"  Result: is_valid={res1.is_valid}, derived_id={res1.derived_record.evidence_id if res1.derived_record else None}")
    print(f"  Verdict: {'PASS' if t1_ok else 'FAIL'}")
    all_passed = all_passed and t1_ok

    # -------------------------------------------------------------------------
    # TEST 2: User Requested Case: Registered 500 cm vs Claimed 5 m
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Запрос пользователя: в реестре 500 cm, заявлен вход 5 m")
    art2 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w-500cm", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 5.0, "height": 3.0},   # Claimed in meters!
        input_units={"width": "m", "height": "m"},             # Claimed unit: m
        claimed_output_values={"area": 15.0},
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res2 = validator.validate(art2, current_ts)
    t2_ok = (
        res2.is_valid is True
        and res2.derived_record is not None
        and res2.derived_record.metadata["normalized_inputs"]["width"] == 5.0
        and res2.derived_record.metadata["computed_values"]["area"] == 15.0
    )
    print(f"  Registered: 500.0 cm -> Converted to claimed unit 'm': 5.0 m | Claimed: 5.0 m")
    print(f"  Result: is_valid={res2.is_valid}, normalized_width={res2.derived_record.metadata['normalized_inputs']['width'] if res2.derived_record else None}m")
    print(f"  Verdict: {'PASS' if t2_ok else 'FAIL'}")
    all_passed = all_passed and t2_ok

    # -------------------------------------------------------------------------
    # TEST 3: Tampering on Converted Value: Registered 500 cm vs Claimed 6 m
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Защита от подмены: в реестре 500 cm, а агент заявляет 6 m")
    art3 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w-500cm", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 6.0, "height": 3.0},   # TAMPERED: 6.0 m != 500 cm (5.0 m)
        input_units={"width": "m", "height": "m"},
        claimed_output_values={"area": 18.0},
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res3 = validator.validate(art3, current_ts)
    t3_ok = (
        res3.is_valid is False
        and any("INPUT_VALUE_TAMPERED" in e for e in res3.errors)
    )
    print(f"  Result: is_valid={res3.is_valid}, errors={res3.errors}")
    print(f"  Verdict: {'PASS' if t3_ok else 'FAIL'}")
    all_passed = all_passed and t3_ok

    # -------------------------------------------------------------------------
    # TEST 4: Output Dimensionality Inconsistency in Contract (area vs 'm')
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Несогласованность выходной размерности: declared dimension 'area' with unit 'm'")
    inconsistent_output_contract = TransformationContract(
        transform_id="inconsistent_area_calc",
        version="1.0.0",
        input_schema={"width": "length", "height": "length"},
        input_base_units={"width": "m", "height": "m"},
        output_schema={"area": "area"},
        output_units={"area": "m"},  # INCONSISTENT: linear meters for area dimension!
        rule_id="area_multiplication_v1",
        preconditions={"width": {"min_exclusive": 0.0}, "height": {"min_exclusive": 0.0}},
        postconditions={"area": {"min_exclusive": 0.0}},
        invariants=[],
        target_domain="structural_engineering",
    )
    val4 = TransformationContractValidator(inconsistent_output_contract, registry)
    res4 = val4.validate(art1, current_ts)
    t4_ok = (
        res4.is_valid is False
        and any("incompatible with unit 'm'" in e for e in res4.errors)
    )
    print(f"  Result: is_valid={res4.is_valid}, errors={res4.errors}")
    print(f"  Verdict: {'PASS' if t4_ok else 'FAIL'}")
    all_passed = all_passed and t4_ok

    # -------------------------------------------------------------------------
    # TEST 5: Extraneous Keys in input_units
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Посторонние ключи в словаре input_units артефакта")
    art5 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w1-m", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 5.0, "height": 3.0},
        input_units={"width": "m", "height": "m", "extraneous_unit": "m"},  # Extra key!
        claimed_output_values={"area": 15.0},
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res5 = validator.validate(art5, current_ts)
    t5_ok = (
        res5.is_valid is False
        and any("EXTRANEOUS_ARTIFACT_KEYS" in e and "extraneous_unit" in e for e in res5.errors)
    )
    print(f"  Result: is_valid={res5.is_valid}, errors={res5.errors}")
    print(f"  Verdict: {'PASS' if t5_ok else 'FAIL'}")
    all_passed = all_passed and t5_ok

    # -------------------------------------------------------------------------
    # TEST 6: Extraneous Keys in claimed_output_values
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Посторонние ключи в словаре claimed_output_values артефакта")
    art6 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w1-m", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 5.0, "height": 3.0},
        input_units={"width": "m", "height": "m"},
        claimed_output_values={"area": 15.0, "perimeter": 16.0},  # Extra key!
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res6 = validator.validate(art6, current_ts)
    t6_ok = (
        res6.is_valid is False
        and any("EXTRANEOUS_ARTIFACT_KEYS" in e and "perimeter" in e for e in res6.errors)
    )
    print(f"  Result: is_valid={res6.is_valid}, errors={res6.errors}")
    print(f"  Verdict: {'PASS' if t6_ok else 'FAIL'}")
    all_passed = all_passed and t6_ok

    # -------------------------------------------------------------------------
    # TEST 7: Unsupported Condition Operator in Contract Definition
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Неподдерживаемый оператор предусловия в контракте")
    bad_op_contract = TransformationContract(
        transform_id="bad_op_contract",
        version="1.0.0",
        input_schema={"width": "length", "height": "length"},
        input_base_units={"width": "m", "height": "m"},
        output_schema={"area": "area"},
        output_units={"area": "m2"},
        rule_id="area_multiplication_v1",
        preconditions={"width": {"custom_sql_injection": 5.0}},  # Unsupported op!
        postconditions={"area": {"min_exclusive": 0.0}},
        invariants=[],
        target_domain="structural_engineering",
    )
    val7 = TransformationContractValidator(bad_op_contract, registry)
    res7 = val7.validate(art1, current_ts)
    t7_ok = (
        res7.is_valid is False
        and any("Unsupported precondition operator 'custom_sql_injection'" in e for e in res7.errors)
    )
    print(f"  Result: is_valid={res7.is_valid}, errors={res7.errors}")
    print(f"  Verdict: {'PASS' if t7_ok else 'FAIL'}")
    all_passed = all_passed and t7_ok

    # -------------------------------------------------------------------------
    # TEST 8: Untrusted Rule Identifier (Zero eval/exec)
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Неизвестное правило трансформации (запрет eval/exec)")
    untrusted_contract = TransformationContract(
        transform_id="untrusted_calc",
        version="1.0.0",
        input_schema={"width": "length", "height": "length"},
        input_base_units={"width": "m", "height": "m"},
        output_schema={"area": "area"},
        output_units={"area": "m2"},
        rule_id="os_system_shell_v1",  # Not in trusted pure functions
        preconditions={"width": {"min_exclusive": 0.0}, "height": {"min_exclusive": 0.0}},
        postconditions={"area": {"min_exclusive": 0.0}},
        invariants=[],
        target_domain="structural_engineering",
    )
    val8 = TransformationContractValidator(untrusted_contract, registry)
    res8 = val8.validate(art1, current_ts)
    t8_ok = (
        res8.is_valid is False
        and any("UNTRUSTED_RULE" in e for e in res8.errors)
    )
    print(f"  Result: is_valid={res8.is_valid}, errors={res8.errors}")
    print(f"  Verdict: {'PASS' if t8_ok else 'FAIL'}")
    all_passed = all_passed and t8_ok

    # -------------------------------------------------------------------------
    # TEST 9: Incompatible Input Physical Dimension
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Физическая несовместимость размерности входа ('bar' давления для 'length')")
    art9 = TransformationExecutionArtifact(
        contract_id="rect_area_calc",
        input_evidence_ids={"width": "ev-sensor-w1-m", "height": "ev-sensor-h1-m"},
        claimed_input_values={"width": 5.0, "height": 3.0},
        input_units={"width": "bar", "height": "m"},  # Dimension 'pressure' instead of 'length'
        claimed_output_values={"area": 15.0},
        output_units={"area": "m2"},
        provenance_reference="cad/panel_alpha_rev2",
        claimed_rule_id="area_multiplication_v1",
    )
    res9 = validator.validate(art9, current_ts)
    t9_ok = (
        res9.is_valid is False
        and any("UNIT_DIMENSION_MISMATCH" in e for e in res9.errors)
    )
    print(f"  Result: is_valid={res9.is_valid}, errors={res9.errors}")
    print(f"  Verdict: {'PASS' if t9_ok else 'FAIL'}")
    all_passed = all_passed and t9_ok

    # -------------------------------------------------------------------------
    # TEST 10: Multi-Process Collision-Free ID Generation
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Бесколлизионная генерация ID (PID + наносекунды + счетчик + дайджест)")
    generated_ids = set()
    num_samples = 100
    for _ in range(num_samples):
        res = validator.validate(art1, current_ts)
        assert res.derived_record is not None
        generated_ids.add(res.derived_record.evidence_id)

    t10_ok = len(generated_ids) == num_samples
    sample_id = next(iter(generated_ids))
    print(f"  Generated {num_samples} sequential IDs, unique set count: {len(generated_ids)}")
    print(f"  Sample ID format: {sample_id}")
    print(f"  Verdict: {'PASS' if t10_ok else 'FAIL'}")
    all_passed = all_passed and t10_ok

    # -------------------------------------------------------------------------
    # TEST 11: Direct Verification via TransformationToSolTriadAdapter & EvidenceValidator
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Прямой вызов EvidenceValidator ядра v1 через TransformationToSolTriadAdapter")
    adapter = TransformationToSolTriadAdapter(registry=registry)

    # Register the valid derived evidence from Test 1
    adapter.register_derived_evidence(res1)

    # Subtest 11A: Omit premises -> EvidenceValidator step 7 triggers INFERENCE_UNSUPPORTED
    source_no_premises = adapter.build_source_primitive(
        result=res1,
        authority_domain={"structural_engineering"},
        granted_scope={"plate_mesh_alpha"},
        omit_premises_for_testing=True,  # VIOLATION: no corroborating premises!
    )
    is_valid_11a, verdict_11a, diags_11a = adapter.validate_with_evidence_validator(source_no_premises, current_ts + 1.0)
    has_unsupported_diag = any(d.code == DiagnosticCode.INFERENCE_UNSUPPORTED for d in diags_11a)
    t11a_ok = (is_valid_11a is False) and (verdict_11a == CoherenceVerdict.REVIEW) and has_unsupported_diag
    print(f"  Subtest 11A (Omitted premises -> REVIEW + INFERENCE_UNSUPPORTED): is_valid={is_valid_11a}, verdict={verdict_11a.value}, diag_code={diags_11a[0].code.value}")

    # Subtest 11B: Valid premises -> EvidenceValidator step 7 passes and returns EVIDENCE_PASS
    source_valid_premises = adapter.build_source_primitive(
        result=res1,
        authority_domain={"structural_engineering"},
        granted_scope={"plate_mesh_alpha"},
        omit_premises_for_testing=False,  # Cites corroborating_evidence_ids!
    )
    is_valid_11b, verdict_11b, diags_11b = adapter.validate_with_evidence_validator(source_valid_premises, current_ts + 1.0)
    has_evidence_pass = any(d.code == DiagnosticCode.EVIDENCE_PASS for d in diags_11b)
    has_errors_11b = any(d.severity == DiagnosticSeverity.ERROR for d in diags_11b)
    t11b_ok = (is_valid_11b is True) and (verdict_11b == CoherenceVerdict.PASS) and has_evidence_pass and (not has_errors_11b)
    print(f"  Subtest 11B (Valid premises -> PASS + EVIDENCE_PASS): is_valid={is_valid_11b}, verdict={verdict_11b.value}, diag_code={diags_11b[0].code.value}")

    t11_ok = t11a_ok and t11b_ok
    print(f"  Verdict: {'PASS' if t11_ok else 'FAIL'}")
    all_passed = all_passed and t11_ok

    # -------------------------------------------------------------------------
    # TEST 12: End-to-End Evaluation via SolTriadEngine (Pairwise Triadic Checks)
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Полный триадический цикл через SolTriadEngine.evaluate()")
    constraint = ConstraintPrimitive(
        domain_scope={"structural_engineering"},
        target_objects={"plate_mesh_alpha"},
        protected_set=set(),
        max_bounds={"area": 20.0},
    )
    dissipate = DissipatePrimitive(loss_domain=set(), target_states=set(), side_effects=set())
    state = SystemState(current_values={"area": 15.0}, active_flags={}, units={"area": "m2"})

    report = adapter.evaluate_with_engine(
        source=source_valid_premises,
        constraint=constraint,
        dissipate=dissipate,
        state=state,
        evaluation_time=current_ts + 2.0,
    )

    t12_ok = (
        report.verdict == CoherenceVerdict.PASS
        and report.pairwise_checks["P_SC"].is_valid is True
        and report.pairwise_checks["P_CD"].is_valid is True
        and report.pairwise_checks["P_SD"].is_valid is True
    )
    print(f"  Triad Verdict: {report.verdict.value}")
    print(f"  Pairwise P_SC: {report.pairwise_checks['P_SC'].verdict.value} (is_valid={report.pairwise_checks['P_SC'].is_valid})")
    print(f"  Pairwise P_CD: {report.pairwise_checks['P_CD'].verdict.value} (is_valid={report.pairwise_checks['P_CD'].is_valid})")
    print(f"  Pairwise P_SD: {report.pairwise_checks['P_SD'].verdict.value} (is_valid={report.pairwise_checks['P_SD'].is_valid})")
    print(f"  Verdict: {'PASS' if t12_ok else 'FAIL'}")
    all_passed = all_passed and t12_ok

    # -------------------------------------------------------------------------
    # FINAL SUITE SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"ALL 12 TEST SUITE SCENARIOS PASSED: {all_passed}")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
