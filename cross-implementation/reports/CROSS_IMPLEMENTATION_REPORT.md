# SOL-Triad Cross-Implementation Consistency Audit Report

**Date:** 2026-10-30T10:46:17.830Z
**Reference Kernel:** Python SOL-Triad-Engine v0.4.1
**Evaluated Simulator:** TypeScript SOL-Triad v1 (v0.4.1)
**Protocol Version:** 0.4.0

## 1. Executive Summary

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Scenarios Evaluated** | **68** | 100.0% |
| **MATCH (Exact 100% Parity)** | **68** | **100.0%** |
| **PARTIAL_MATCH (Benign Minor Diff)** | **0** | 0.0% |
| **MISMATCH (Substantive Divergence)** | **0** | 0.0% |
| **NOT_COMPARABLE (Execution Failure)** | **0** | 0.0% |

## 2. Breakdown by Subsystem Group

| Group | Subsystem Domain | Total | MATCH | PARTIAL | MISMATCH | Parity Rate |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| A | SOURCE & Evidence Grounding | 8 | 8 | 0 | 0 | **100.0%** |
| B | INFERENCE Recursive DAG & Cycles | 10 | 10 | 0 | 0 | **100.0%** |
| C | SCOPE & Authority Domains | 9 | 9 | 0 | 0 | **100.0%** |
| D | CONSTRAINT & State Invariants | 8 | 8 | 0 | 0 | **100.0%** |
| E | DISSIPATE & Resource Costs | 5 | 5 | 0 | 0 | **100.0%** |
| F | Units of Measurement & Conversions | 8 | 8 | 0 | 0 | **100.0%** |
| G | JSON & Protocol Structure | 9 | 9 | 0 | 0 | **100.0%** |
| H | Combined Multi-Violation Scenarios | 11 | 11 | 0 | 0 | **100.0%** |

## 3. Discrepancy Registry

**Zero discrepancies detected.** All 68 scenarios matched across verdict, channels P_SC / P_CD / P_SD, diagnostic codes, and simulated state vectors.

## 4. Detailed Scenario Inventory

| ID | Group | Verdict (Py / TS) | P_SC | P_CD | P_SD | Codes Match | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| A01_valid_source | A | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| A02_missing_evidence_id | A | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| A03_stale_evidence | A | REVIEW / REVIEW | REVIEW/REVIEW | PASS/PASS | PASS/PASS | YES | MATCH |
| A04_future_timestamp | A | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| A05_unknown_epistemic_type | A | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| A06_missing_registry_record | A | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| A07_incomplete_premise_chain | A | REVIEW / REVIEW | REVIEW/REVIEW | PASS/PASS | PASS/PASS | YES | MATCH |
| A08_valid_corroborating_chain | A | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B09_inference_single_level | B | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B10_inference_multi_step_chain | B | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B11_inference_nested_chain | B | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B12_inference_branching_tree | B | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B13_inference_diamond_dag | B | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| B14_inference_2_node_cycle | B | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| B15_inference_3_node_cycle | B | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| B16_inference_deep_cycle | B | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| B17_inference_max_depth_exceeded | B | REVIEW / REVIEW | REVIEW/REVIEW | PASS/PASS | PASS/PASS | YES | MATCH |
| B18_inference_max_nodes_exceeded | B | REVIEW / REVIEW | REVIEW/REVIEW | PASS/PASS | PASS/PASS | YES | MATCH |
| C19_fully_authorized_scope | C | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| C20_authority_domain_null | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | FAIL/FAIL | YES | MATCH |
| C21_granted_scope_null | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | FAIL/FAIL | YES | MATCH |
| C22_granted_loss_domains_null | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | FAIL/FAIL | YES | MATCH |
| C23_all_scopes_empty_zero_requests | C | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| C24_empty_scope_with_actions | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| C25_unauthorized_domain | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| C26_unauthorized_target_object | C | FAIL / FAIL | FAIL/FAIL | PASS/PASS | PASS/PASS | YES | MATCH |
| C27_unauthorized_loss_domain | C | FAIL / FAIL | PASS/PASS | PASS/PASS | FAIL/FAIL | YES | MATCH |
| D28_valid_initial_state | D | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| D29_min_bounds_breach | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D30_max_bounds_breach | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D31_protected_param_mutated | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D32_protected_value_violated | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D33_protected_flag_mutated | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D34_forbidden_flag_active | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| D35_required_flag_missing | D | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| E36_valid_dissipation | E | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| E37_unauthorized_dissipation_loss | E | FAIL / FAIL | PASS/PASS | PASS/PASS | FAIL/FAIL | YES | MATCH |
| E38_negative_resource_cost | E | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| E39_incompatible_units_mutation | E | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| E40_side_effect_mutates_protected | E | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F41_absolute_temperature_c_to_k | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F42_absolute_temperature_k_to_c | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F43_delta_temperature_c_to_k | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F44_delta_temperature_k_to_c | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F45_pressure_conversion | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F46_time_conversion | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F47_incompatible_dimensions | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| F48_unknown_unit | F | FAIL / FAIL | PASS/PASS | FAIL/FAIL | PASS/PASS | YES | MATCH |
| G49_valid_json | G | PASS / PASS | PASS/PASS | PASS/PASS | PASS/PASS | YES | MATCH |
| G50_missing_required_field | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G51_unknown_top_level_field | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G52_invalid_field_type | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G53_unsupported_protocol_version | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G54_invalid_nested_object | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G55_invalid_array | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G56_nan_numeric_value | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| G57_inline_evidence_records | G | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| H58_unauthorized_object_AND_min_bound_breach | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | PASS/PASS | YES | MATCH |
| H59_stale_evidence_AND_invariant_breach | H | FAIL / FAIL | REVIEW/REVIEW | FAIL/FAIL | PASS/PASS | YES | MATCH |
| H60_unauthorized_loss_AND_protected_param | H | FAIL / FAIL | PASS/PASS | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| H61_missing_evidence_AND_unit_incompatible | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | PASS/PASS | YES | MATCH |
| H62_null_authority_AND_negative_cost | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| H63_circular_inference_AND_protected_value | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | PASS/PASS | YES | MATCH |
| H64_future_timestamp_AND_unauthorized_loss | H | FAIL / FAIL | FAIL/FAIL | PASS/PASS | FAIL/FAIL | YES | MATCH |
| H65_stale_evidence_AND_unauthorized_loss | H | FAIL / FAIL | REVIEW/REVIEW | PASS/PASS | FAIL/FAIL | YES | MATCH |
| H66_three_way_failure | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
| H67_stale_evidence_AND_valid_CD_SD | H | REVIEW / REVIEW | REVIEW/REVIEW | PASS/PASS | PASS/PASS | YES | MATCH |
| H68_unsupported_protocol_AND_state_breach | H | FAIL / FAIL | FAIL/FAIL | FAIL/FAIL | FAIL/FAIL | YES | MATCH |
