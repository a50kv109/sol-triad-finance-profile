"""
Generates the comprehensive 68-scenario fixture library for Cross-Implementation Consistency Testing.
Saved to cross-implementation/fixtures/fixtures.json.
"""

import json
import os

CURRENT_TIME = 1740000000.0


def base_request(req_id: str) -> dict:
    return {
        "request_id": req_id,
        "protocol_version": "0.4.0",
        "engine_version": "0.4.1",
        "source": {
            "evidence_id": "ev-sensor-100",
            "authority_domain": ["thermal_control"],
            "granted_scope": ["pump_alpha"],
            "granted_loss_domains": ["thermal_entropy"],
            "epistemic_type": "FACT",
            "timestamp_sec": CURRENT_TIME - 10.0,
            "max_age_sec": 300.0,
            "payload_hash": "sha256-hash-ok"
        },
        "constraint": {
            "domain_scope": ["thermal_control"],
            "target_objects": ["pump_alpha"],
            "protected_set": ["emergency_valve"],
            "max_bounds": {"coolant_pressure": 10.0},
            "min_bounds": {"coolant_pressure": 0.5},
            "units": {"coolant_pressure": "bar"}
        },
        "dissipate": {
            "loss_domain": ["thermal_entropy"],
            "target_states": ["coolant_flowing"],
            "side_effects": ["pipe_vibration"],
            "resource_cost": {},
            "state_delta": {"coolant_pressure": 1.5},
            "units": {"coolant_pressure": "bar"}
        },
        "initial_state": {
            "current_values": {"coolant_pressure": 3.0},
            "active_flags": {},
            "units": {"coolant_pressure": "bar"}
        }
    }


def base_record(ev_id="ev-sensor-100", domain="thermal_control", epistemic="FACT", ts_offset=10.0, corrob=None, p_hash="sha256-hash-ok"):
    rec = {
        "evidence_id": ev_id,
        "domain": domain,
        "epistemic_status": epistemic,
        "timestamp_sec": CURRENT_TIME - ts_offset,
    }
    if p_hash is not None:
        rec["payload_hash"] = p_hash
    if corrob is not None:
        rec["corroborating_evidence_ids"] = corrob
    return rec


fixtures = []

# =========================================================================
# GROUP A: SOURCE & Evidence (Scenarios 1-8)
# =========================================================================

# 1. A01: Valid SOURCE
r = base_request("req-a01")
fixtures.append({
    "id": "A01_valid_source",
    "group": "A",
    "name": "A01: Valid SOURCE and Evidence",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 2. A02: Missing evidence_id
r = base_request("req-a02")
r["source"]["evidence_id"] = "   "
fixtures.append({
    "id": "A02_missing_evidence_id",
    "group": "A",
    "name": "A02: Missing or whitespace evidence_id",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 3. A03: Stale evidence
r = base_request("req-a03")
r["source"]["timestamp_sec"] = CURRENT_TIME - 1000.0
fixtures.append({
    "id": "A03_stale_evidence",
    "group": "A",
    "name": "A03: Stale evidence (age 1000s > max_age 300s)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=1000.0)],
    "request": r
})

# 4. A04: Future timestamp
r = base_request("req-a04")
r["source"]["timestamp_sec"] = CURRENT_TIME + 100.0
fixtures.append({
    "id": "A04_future_timestamp",
    "group": "A",
    "name": "A04: Future evidence timestamp",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=-100.0)],
    "request": r
})

# 5. A05: Unknown epistemic_type
r = base_request("req-a05")
r["source"]["epistemic_type"] = "INVALID_STATUS"
fixtures.append({
    "id": "A05_unknown_epistemic_type",
    "group": "A",
    "name": "A05: Unknown epistemic_type in request",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 6. A06: Missing registry record
r = base_request("req-a06")
r["source"]["evidence_id"] = "ev-ghost-not-registered"
fixtures.append({
    "id": "A06_missing_registry_record",
    "group": "A",
    "name": "A06: Evidence ID missing from host registry",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 7. A07: Incomplete premise chain
r = base_request("req-a07")
r["source"]["evidence_id"] = "ev-inference-bare"
r["source"]["epistemic_type"] = "INFERENCE"
fixtures.append({
    "id": "A07_incomplete_premise_chain",
    "group": "A",
    "name": "A07: INFERENCE record lacks corroborating premise list",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [{
        "evidence_id": "ev-inference-bare",
        "domain": "thermal_control",
        "epistemic_status": "INFERENCE",
        "timestamp_sec": CURRENT_TIME - 10.0,
        "payload_hash": "sha256-hash-ok",
        "corroborating_evidence_ids": []
    }],
    "request": r
})

# 8. A08: Valid corroborating chain
r = base_request("req-a08")
r["source"]["evidence_id"] = "ev-inference-root"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-fact-premise"]
fixtures.append({
    "id": "A08_valid_corroborating_chain",
    "group": "A",
    "name": "A08: INFERENCE grounded in verified FACT premise",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record(ev_id="ev-inference-root", epistemic="INFERENCE", ts_offset=10.0, corrob=["ev-fact-premise"]),
        base_record(ev_id="ev-fact-premise", epistemic="FACT", ts_offset=20.0, p_hash=None)
    ],
    "request": r
})

# =========================================================================
# GROUP B: INFERENCE DAG Traversal (Scenarios 9-18)
# =========================================================================

# 9. B09: Single level inference A -> B
r = base_request("req-b09")
r["source"]["evidence_id"] = "ev-b09-root"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b09-fact"]
fixtures.append({
    "id": "B09_inference_single_level",
    "group": "B",
    "name": "B09: Single level inference A -> FACT",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b09-root", epistemic="INFERENCE", corrob=["ev-b09-fact"]),
        base_record("ev-b09-fact", epistemic="FACT", ts_offset=15.0, p_hash=None)
    ],
    "request": r
})

# 10. B10: Multi-step chain A -> B -> C -> FACT
r = base_request("req-b10")
r["source"]["evidence_id"] = "ev-b10-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b10-b"]
fixtures.append({
    "id": "B10_inference_multi_step_chain",
    "group": "B",
    "name": "B10: Multi-step chain A -> B -> C -> FACT",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b10-a", epistemic="INFERENCE", corrob=["ev-b10-b"]),
        base_record("ev-b10-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b10-c"], p_hash=None),
        base_record("ev-b10-c", epistemic="INFERENCE", ts_offset=20.0, corrob=["ev-b10-d"], p_hash=None),
        base_record("ev-b10-d", epistemic="FACT", ts_offset=25.0, p_hash=None)
    ],
    "request": r
})

# 11. B11: Nested chain (depth 10)
records_b11 = []
for i in range(10):
    curr = f"ev-b11-{i}"
    nxt = f"ev-b11-{i+1}"
    if i < 9:
        records_b11.append(base_record(curr, epistemic="INFERENCE", ts_offset=10.0+i, corrob=[nxt], p_hash="sha256-hash-ok" if i==0 else None))
    else:
        records_b11.append(base_record(curr, epistemic="FACT", ts_offset=10.0+i, p_hash=None))
r = base_request("req-b11")
r["source"]["evidence_id"] = "ev-b11-0"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b11-1"]
fixtures.append({
    "id": "B11_inference_nested_chain",
    "group": "B",
    "name": "B11: Nested inference chain of depth 10",
    "evaluation_time": CURRENT_TIME,
    "registry_records": records_b11,
    "request": r
})

# 12. B12: Branching tree A -> (B, C), B -> D, C -> E
r = base_request("req-b12")
r["source"]["evidence_id"] = "ev-b12-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b12-b", "ev-b12-c"]
fixtures.append({
    "id": "B12_inference_branching_tree",
    "group": "B",
    "name": "B12: Branching inference tree rooted in multiple facts",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b12-a", epistemic="INFERENCE", corrob=["ev-b12-b", "ev-b12-c"]),
        base_record("ev-b12-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b12-d"], p_hash=None),
        base_record("ev-b12-c", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b12-e"], p_hash=None),
        base_record("ev-b12-d", epistemic="FACT", ts_offset=20.0, p_hash=None),
        base_record("ev-b12-e", epistemic="FACT", ts_offset=20.0, p_hash=None)
    ],
    "request": r
})

# 13. B13: Diamond DAG A -> (B, C) -> D (no false cycle)
r = base_request("req-b13")
r["source"]["evidence_id"] = "ev-b13-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b13-b", "ev-b13-c"]
fixtures.append({
    "id": "B13_inference_diamond_dag",
    "group": "B",
    "name": "B13: Diamond DAG A -> (B, C) -> D -> FACT",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b13-a", epistemic="INFERENCE", corrob=["ev-b13-b", "ev-b13-c"]),
        base_record("ev-b13-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b13-d"], p_hash=None),
        base_record("ev-b13-c", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b13-d"], p_hash=None),
        base_record("ev-b13-d", epistemic="FACT", ts_offset=20.0, p_hash=None)
    ],
    "request": r
})

# 14. B14: 2-node cycle A -> B -> A
r = base_request("req-b14")
r["source"]["evidence_id"] = "ev-b14-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b14-b"]
fixtures.append({
    "id": "B14_inference_2_node_cycle",
    "group": "B",
    "name": "B14: 2-node circular dependency A -> B -> A",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b14-a", epistemic="INFERENCE", corrob=["ev-b14-b"]),
        base_record("ev-b14-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b14-a"], p_hash=None)
    ],
    "request": r
})

# 15. B15: 3-node cycle A -> B -> C -> A
r = base_request("req-b15")
r["source"]["evidence_id"] = "ev-b15-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b15-b"]
fixtures.append({
    "id": "B15_inference_3_node_cycle",
    "group": "B",
    "name": "B15: 3-node circular dependency A -> B -> C -> A",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b15-a", epistemic="INFERENCE", corrob=["ev-b15-b"]),
        base_record("ev-b15-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b15-c"], p_hash=None),
        base_record("ev-b15-c", epistemic="INFERENCE", ts_offset=20.0, corrob=["ev-b15-a"], p_hash=None)
    ],
    "request": r
})

# 16. B16: Deep cycle A -> B -> (C -> D -> E -> C)
r = base_request("req-b16")
r["source"]["evidence_id"] = "ev-b16-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b16-b"]
fixtures.append({
    "id": "B16_inference_deep_cycle",
    "group": "B",
    "name": "B16: Deep cycle embedded in DAG",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-b16-a", epistemic="INFERENCE", corrob=["ev-b16-b"]),
        base_record("ev-b16-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-b16-c"], p_hash=None),
        base_record("ev-b16-c", epistemic="INFERENCE", ts_offset=20.0, corrob=["ev-b16-d"], p_hash=None),
        base_record("ev-b16-d", epistemic="INFERENCE", ts_offset=25.0, corrob=["ev-b16-e"], p_hash=None),
        base_record("ev-b16-e", epistemic="INFERENCE", ts_offset=30.0, corrob=["ev-b16-c"], p_hash=None)
    ],
    "request": r
})

# 17. B17: Depth limit exceeded (depth 70 > 64)
records_b17 = []
for i in range(70):
    curr = f"ev-b17-{i}"
    nxt = f"ev-b17-{i+1}"
    if i < 69:
        records_b17.append(base_record(curr, epistemic="INFERENCE", ts_offset=10.0, corrob=[nxt], p_hash="sha256-hash-ok" if i==0 else None))
    else:
        records_b17.append(base_record(curr, epistemic="FACT", ts_offset=10.0, p_hash=None))
r = base_request("req-b17")
r["source"]["evidence_id"] = "ev-b17-0"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-b17-1"]
fixtures.append({
    "id": "B17_inference_max_depth_exceeded",
    "group": "B",
    "name": "B17: INFERENCE chain exceeds MAX_INFERENCE_DEPTH (64)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": records_b17,
    "request": r
})

# 18. B18: Node limit exceeded (1050 unique nodes > 1024)
records_b18 = []
root_corrob = [f"ev-b18-leaf-{i}" for i in range(1040)]
records_b18.append(base_record("ev-b18-root", epistemic="INFERENCE", ts_offset=10.0, corrob=root_corrob))
for i in range(1040):
    records_b18.append(base_record(f"ev-b18-leaf-{i}", epistemic="FACT", ts_offset=15.0, p_hash=None))
r = base_request("req-b18")
r["source"]["evidence_id"] = "ev-b18-root"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = root_corrob
fixtures.append({
    "id": "B18_inference_max_nodes_exceeded",
    "group": "B",
    "name": "B18: INFERENCE graph exceeds MAX_INFERENCE_NODES (1024)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": records_b18,
    "request": r
})

# =========================================================================
# GROUP C: SCOPE and Authority (Scenarios 19-27)
# =========================================================================

# 19. C19: Fully authorized scope
r = base_request("req-c19")
fixtures.append({
    "id": "C19_fully_authorized_scope",
    "group": "C",
    "name": "C19: Fully authorized domains, objects, and losses",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 20. C20: authority_domain = null
r = base_request("req-c20")
r["source"]["authority_domain"] = None
fixtures.append({
    "id": "C20_authority_domain_null",
    "group": "C",
    "name": "C20: authority_domain is null (structural defect)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 21. C21: granted_scope = null
r = base_request("req-c21")
r["source"]["granted_scope"] = None
fixtures.append({
    "id": "C21_granted_scope_null",
    "group": "C",
    "name": "C21: granted_scope is null (structural defect)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 22. C22: granted_loss_domains = null
r = base_request("req-c22")
r["source"]["granted_loss_domains"] = None
fixtures.append({
    "id": "C22_granted_loss_domains_null",
    "group": "C",
    "name": "C22: granted_loss_domains is null (structural defect)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 23. C23: All scopes empty with zero requests
r = base_request("req-c23")
r["source"]["evidence_id"] = "ev-zero-auth"
r["source"]["authority_domain"] = ["public"]
r["source"]["granted_scope"] = []
r["source"]["granted_loss_domains"] = []
del r["source"]["payload_hash"]
r["constraint"]["domain_scope"] = ["public"]
r["constraint"]["target_objects"] = []
r["dissipate"]["loss_domain"] = []
fixtures.append({
    "id": "C23_all_scopes_empty_zero_requests",
    "group": "C",
    "name": "C23: Zero privileges granted with zero requested (PASS)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record("ev-zero-auth", domain="public", p_hash=None)],
    "request": r
})

# 24. C24: Empty scope with non-empty requests
r = base_request("req-c24")
r["source"]["authority_domain"] = []  # Zero domains
fixtures.append({
    "id": "C24_empty_scope_with_actions",
    "group": "C",
    "name": "C24: Zero domains granted with actions attempted (FAIL)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 25. C25: Unauthorized domain
r = base_request("req-c25")
r["constraint"]["domain_scope"] = ["nuclear_safety", "thermal_control"]
fixtures.append({
    "id": "C25_unauthorized_domain",
    "group": "C",
    "name": "C25: Constraint domain exceeds granted authority",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 26. C26: Unauthorized target object
r = base_request("req-c26")
r["constraint"]["target_objects"] = ["reactor_core"]
fixtures.append({
    "id": "C26_unauthorized_target_object",
    "group": "C",
    "name": "C26: Target object exceeds granted scope",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 27. C27: Unauthorized loss domain
r = base_request("req-c27")
r["dissipate"]["loss_domain"] = ["explosive_decompression"]
fixtures.append({
    "id": "C27_unauthorized_loss_domain",
    "group": "C",
    "name": "C27: Dissipate loss domain exceeds granted losses",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# =========================================================================
# GROUP D: CONSTRAINT and State Invariants (Scenarios 28-35)
# =========================================================================

# 28. D28: Valid initial state and mutation
r = base_request("req-d28")
fixtures.append({
    "id": "D28_valid_initial_state",
    "group": "D",
    "name": "D28: Valid state invariants and bounds",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 29. D29: min_bounds breach
r = base_request("req-d29")
r["constraint"]["min_bounds"]["coolant_pressure"] = 5.0  # Simulated 4.5 < 5.0
fixtures.append({
    "id": "D29_min_bounds_breach",
    "group": "D",
    "name": "D29: Terminal value falls below min_bounds",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 30. D30: max_bounds breach
r = base_request("req-d30")
r["constraint"]["max_bounds"]["coolant_pressure"] = 4.0  # Simulated 4.5 > 4.0
fixtures.append({
    "id": "D30_max_bounds_breach",
    "group": "D",
    "name": "D30: Terminal value exceeds max_bounds",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 31. D31: Mutation of protected_set
r = base_request("req-d31")
r["dissipate"]["state_delta"]["emergency_valve"] = 1.0  # in protected_set!
r["constraint"]["units"]["emergency_valve"] = "dimensionless"
r["dissipate"]["units"]["emergency_valve"] = "dimensionless"
r["initial_state"]["units"]["emergency_valve"] = "dimensionless"
fixtures.append({
    "id": "D31_protected_param_mutated",
    "group": "D",
    "name": "D31: State delta attempts to mutate protected_set",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 32. D32: Violation of protected_values
r = base_request("req-d32")
r["constraint"]["protected_values"] = {"coolant_pressure": 3.0}  # Expected 3.0, simulated 4.5
fixtures.append({
    "id": "D32_protected_value_violated",
    "group": "D",
    "name": "D32: Terminal value violates protected_values expectation",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 33. D33: Mutation of protected_flags
r = base_request("req-d33")
r["constraint"]["protected_flags"] = ["cooling_active"]
r["initial_state"]["active_flags"] = {"cooling_active": True}
r["dissipate"]["flag_delta"] = {"cooling_active": False}
fixtures.append({
    "id": "D33_protected_flag_mutated",
    "group": "D",
    "name": "D33: Flag delta mutates protected flag",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 34. D34: Forbidden flag active
r = base_request("req-d34")
r["constraint"]["forbidden_flags"] = {"meltdown_alarm": True}
r["dissipate"]["flag_delta"] = {"meltdown_alarm": True}
fixtures.append({
    "id": "D34_forbidden_flag_active",
    "group": "D",
    "name": "D34: Terminal state activates forbidden flag",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 35. D35: Required flag missing
r = base_request("req-d35")
r["constraint"]["required_flags"] = {"safe_mode": True}
r["initial_state"]["active_flags"] = {"safe_mode": False}
fixtures.append({
    "id": "D35_required_flag_missing",
    "group": "D",
    "name": "D35: Terminal state missing required flag value",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# =========================================================================
# GROUP E: DISSIPATE & Resource Costs (Scenarios 36-40)
# =========================================================================

# 36. E36: Valid dissipation
r = base_request("req-e36")
r["dissipate"]["resource_cost"] = {"coolant_kg": 2.0}
r["initial_state"]["current_values"]["coolant_kg"] = 10.0
r["constraint"]["units"]["coolant_kg"] = "kg"
r["dissipate"]["units"]["coolant_kg"] = "kg"
r["initial_state"]["units"]["coolant_kg"] = "kg"
fixtures.append({
    "id": "E36_valid_dissipation",
    "group": "E",
    "name": "E36: Valid dissipation with positive resource cost",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 37. E37: Unauthorized dissipation loss
r = base_request("req-e37")
r["dissipate"]["loss_domain"] = ["toxic_venting"]
fixtures.append({
    "id": "E37_unauthorized_dissipation_loss",
    "group": "E",
    "name": "E37: Dissipate loss domain outside granted loss domains",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 38. E38: Negative resource cost
r = base_request("req-e38")
r["dissipate"]["resource_cost"] = {"coolant_kg": -5.0}  # Negative cost forbidden!
r["constraint"]["units"]["coolant_kg"] = "kg"
r["dissipate"]["units"]["coolant_kg"] = "kg"
r["initial_state"]["units"]["coolant_kg"] = "kg"
fixtures.append({
    "id": "E38_negative_resource_cost",
    "group": "E",
    "name": "E38: Negative resource cost is strictly forbidden",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 39. E39: Incompatible units in mutation
r = base_request("req-e39")
r["dissipate"]["units"]["coolant_pressure"] = "second"  # time vs pressure!
fixtures.append({
    "id": "E39_incompatible_units_mutation",
    "group": "E",
    "name": "E39: Incompatible units between dissipation and constraint",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 40. E40: Side effect mutates protected param
r = base_request("req-e40")
r["dissipate"]["side_effects"] = ["emergency_valve"]  # in protected_set!
fixtures.append({
    "id": "E40_side_effect_mutates_protected",
    "group": "E",
    "name": "E40: Side effect modifies protected parameter",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# =========================================================================
# GROUP F: Units of Measurement & Dimensionality (Scenarios 41-48)
# =========================================================================

# 41. F41: Absolute temp °C -> K (100 C = 373.15 K)
r = base_request("req-f41")
r["constraint"]["max_bounds"] = {"temp": 100.0}  # 100 C = 373.15 K
r["constraint"]["units"] = {"temp": "celsius"}
r["initial_state"]["current_values"] = {"temp": 370.0}
r["initial_state"]["units"] = {"temp": "kelvin"}
r["dissipate"]["state_delta"] = {}
r["dissipate"]["units"] = {}
fixtures.append({
    "id": "F41_absolute_temperature_c_to_k",
    "group": "F",
    "name": "F41: Absolute temperature conversion C to K",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 42. F42: Absolute temp K -> °C (273.15 K = 0 C)
r = base_request("req-f42")
r["constraint"]["max_bounds"] = {"temp": 300.0}  # 300 K = 26.85 C
r["constraint"]["units"] = {"temp": "kelvin"}
r["initial_state"]["current_values"] = {"temp": 20.0}
r["initial_state"]["units"] = {"temp": "celsius"}
r["dissipate"]["state_delta"] = {}
r["dissipate"]["units"] = {}
fixtures.append({
    "id": "F42_absolute_temperature_k_to_c",
    "group": "F",
    "name": "F42: Absolute temperature conversion K to C",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 43. F43: Delta temperature C to K (Δ 10 C = Δ 10 K)
r = base_request("req-f43")
r["initial_state"]["current_values"] = {"temp": 300.0}
r["initial_state"]["units"] = {"temp": "kelvin"}
r["dissipate"]["state_delta"] = {"temp": 10.0}  # Delta 10 C -> 310 K
r["dissipate"]["units"] = {"temp": "celsius"}
r["constraint"]["max_bounds"] = {"temp": 320.0}
r["constraint"]["units"] = {"temp": "kelvin"}
fixtures.append({
    "id": "F43_delta_temperature_c_to_k",
    "group": "F",
    "name": "F43: Temperature increment Delta C to Delta K (without affine shift)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 44. F44: Delta temperature K to C (Δ 10 K = Δ 10 C)
r = base_request("req-f44")
r["initial_state"]["current_values"] = {"temp": 25.0}
r["initial_state"]["units"] = {"temp": "celsius"}
r["dissipate"]["state_delta"] = {"temp": 5.0}  # Delta 5 K -> 30 C
r["dissipate"]["units"] = {"temp": "kelvin"}
r["constraint"]["max_bounds"] = {"temp": 35.0}
r["constraint"]["units"] = {"temp": "celsius"}
fixtures.append({
    "id": "F44_delta_temperature_k_to_c",
    "group": "F",
    "name": "F44: Temperature increment Delta K to Delta C",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 45. F45: Pressure conversion (50 kPa = 0.5 bar)
r = base_request("req-f45")
r["initial_state"]["current_values"] = {"p": 1.0}
r["initial_state"]["units"] = {"p": "bar"}
r["dissipate"]["state_delta"] = {"p": 50.0}  # 50 kPa = 0.5 bar -> simulated 1.5 bar
r["dissipate"]["units"] = {"p": "kpa"}
r["constraint"]["max_bounds"] = {"p": 2.0}
r["constraint"]["units"] = {"p": "bar"}
fixtures.append({
    "id": "F45_pressure_conversion",
    "group": "F",
    "name": "F45: Pressure conversion kPa to bar",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 46. F46: Time conversion (1 hr = 3600 s)
r = base_request("req-f46")
r["initial_state"]["current_values"] = {"duration": 1800.0}
r["initial_state"]["units"] = {"duration": "second"}
r["dissipate"]["state_delta"] = {"duration": 1.0}  # 1 hour = 3600 s -> 5400 s
r["dissipate"]["units"] = {"duration": "hour"}
r["constraint"]["max_bounds"] = {"duration": 6000.0}
r["constraint"]["units"] = {"duration": "second"}
fixtures.append({
    "id": "F46_time_conversion",
    "group": "F",
    "name": "F46: Time conversion hour to second",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 47. F47: Incompatible dimensions (pressure vs time)
r = base_request("req-f47")
r["initial_state"]["current_values"] = {"x": 10.0}
r["initial_state"]["units"] = {"x": "bar"}
r["constraint"]["units"] = {"x": "second"}  # Incompatible!
r["dissipate"]["state_delta"] = {"x": 1.0}
r["dissipate"]["units"] = {"x": "second"}
fixtures.append({
    "id": "F47_incompatible_dimensions",
    "group": "F",
    "name": "F47: Incompatible dimensions (pressure vs time)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 48. F48: Unknown unit
r = base_request("req-f48")
r["initial_state"]["current_values"] = {"x": 10.0}
r["initial_state"]["units"] = {"x": "unknown_alien_unit"}
r["constraint"]["units"] = {"x": "unknown_alien_unit"}
fixtures.append({
    "id": "F48_unknown_unit",
    "group": "F",
    "name": "F48: Unregistered unit name",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# =========================================================================
# GROUP G: JSON and Protocol Structure (Scenarios 49-57)
# =========================================================================

# 49. G49: Valid JSON
r = base_request("req-g49")
fixtures.append({
    "id": "G49_valid_json",
    "group": "G",
    "name": "G49: Valid complete JSON protocol payload",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 50. G50: Missing required field (protocol_version)
r = base_request("req-g50")
del r["protocol_version"]
fixtures.append({
    "id": "G50_missing_required_field",
    "group": "G",
    "name": "G50: Missing required top-level protocol_version",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 51. G51: Unknown top level field
r = base_request("req-g51")
r["evaluation_time"] = CURRENT_TIME - 3600.0  # forbidden in body!
fixtures.append({
    "id": "G51_unknown_top_level_field",
    "group": "G",
    "name": "G51: Unsupported top-level key (evaluation_time in request body)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 52. G52: Invalid field type (string boolean)
r = base_request("req-g52")
r["initial_state"]["active_flags"] = {"motor_on": "false"}  # coerced string!
fixtures.append({
    "id": "G52_invalid_field_type",
    "group": "G",
    "name": "G52: Invalid field type (string 'false' instead of boolean)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 53. G53: Unsupported protocol version
r = base_request("req-g53")
r["protocol_version"] = "99.0.0"
fixtures.append({
    "id": "G53_unsupported_protocol_version",
    "group": "G",
    "name": "G53: Unsupported protocol_version 99.0.0",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 54. G54: Invalid nested object (string instead of dict)
r = base_request("req-g54")
r["constraint"] = "not_an_object"
fixtures.append({
    "id": "G54_invalid_nested_object",
    "group": "G",
    "name": "G54: Nested constraint primitive is string instead of object",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 55. G55: Invalid array (numbers in string list)
r = base_request("req-g55")
r["constraint"]["domain_scope"] = [123, 456]
fixtures.append({
    "id": "G55_invalid_array",
    "group": "G",
    "name": "G55: String list contains integers",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 56. G56: NaN numeric value (simulated by malformed string constant)
fixtures.append({
    "id": "G56_nan_numeric_value",
    "group": "G",
    "name": "G56: Malformed unclosed JSON payload",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": '{"request_id": "req-g56", "unclosed_json...'
})

# 57. G57: Inline evidence records forbidden
r = base_request("req-g57")
r["evidence_records"] = [base_record()]
fixtures.append({
    "id": "G57_inline_evidence_records",
    "group": "G",
    "name": "G57: Inline evidence_records supplied by untrusted agent",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# =========================================================================
# GROUP H: Combined Multi-Violation Scenarios (Scenarios 58-68)
# =========================================================================

# 58. H58: Unauthorized object AND min_bound breach
r = base_request("req-h58")
r["constraint"]["target_objects"] = ["reactor_core"]  # P_SC fails
r["constraint"]["min_bounds"]["coolant_pressure"] = 5.0  # P_CD fails (4.5 < 5.0)
fixtures.append({
    "id": "H58_unauthorized_object_AND_min_bound_breach",
    "group": "H",
    "name": "H58: Multi-channel failure: P_SC scope breach + P_CD state breach",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 59. H59: Stale evidence AND invariant breach
r = base_request("req-h59")
r["source"]["timestamp_sec"] = CURRENT_TIME - 1000.0  # P_SC is REVIEW
r["constraint"]["max_bounds"]["coolant_pressure"] = 4.0  # P_CD is FAIL (4.5 > 4.0)
fixtures.append({
    "id": "H59_stale_evidence_AND_invariant_breach",
    "group": "H",
    "name": "H59: REVIEW in P_SC combined with FAIL in P_CD -> overall FAIL",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=1000.0)],
    "request": r
})

# 60. H60: Unauthorized loss AND protected param
r = base_request("req-h60")
r["dissipate"]["loss_domain"] = ["destructive_heat_dump"]  # P_SD fails
r["dissipate"]["side_effects"] = ["emergency_valve"]  # P_CD fails
fixtures.append({
    "id": "H60_unauthorized_loss_AND_protected_param",
    "group": "H",
    "name": "H60: P_SD loss breach + P_CD protected param mutation",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 61. H61: Missing evidence AND unit incompatible
r = base_request("req-h61")
r["source"]["evidence_id"] = "ev-ghost"  # P_SC fails
r["dissipate"]["units"]["coolant_pressure"] = "second"  # P_CD fails
fixtures.append({
    "id": "H61_missing_evidence_AND_unit_incompatible",
    "group": "H",
    "name": "H61: P_SC missing evidence + P_CD incompatible unit",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 62. H62: Null authority AND negative resource cost
r = base_request("req-h62")
r["source"]["authority_domain"] = None  # P_SC/SD structural defect FAIL
r["dissipate"]["resource_cost"] = {"coolant_pressure": -1.0}  # P_CD negative cost FAIL
fixtures.append({
    "id": "H62_null_authority_AND_negative_cost",
    "group": "H",
    "name": "H62: Null authority defect + P_CD negative resource cost",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 63. H63: Circular inference AND protected value violation
r = base_request("req-h63")
r["source"]["evidence_id"] = "ev-h63-a"
r["source"]["epistemic_type"] = "INFERENCE"
r["source"]["corroborating_evidence_ids"] = ["ev-h63-b"]
r["constraint"]["protected_values"] = {"coolant_pressure": 1.0}  # P_CD fails (4.5 != 1.0)
fixtures.append({
    "id": "H63_circular_inference_AND_protected_value",
    "group": "H",
    "name": "H63: P_SC circular inference + P_CD protected value violation",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [
        base_record("ev-h63-a", epistemic="INFERENCE", corrob=["ev-h63-b"]),
        base_record("ev-h63-b", epistemic="INFERENCE", ts_offset=15.0, corrob=["ev-h63-a"], p_hash=None)
    ],
    "request": r
})

# 64. H64: Future timestamp AND unauthorized loss domain
r = base_request("req-h64")
r["source"]["timestamp_sec"] = CURRENT_TIME + 200.0  # P_SC fails
r["dissipate"]["loss_domain"] = ["black_hole_radiation"]  # P_SD fails
fixtures.append({
    "id": "H64_future_timestamp_AND_unauthorized_loss",
    "group": "H",
    "name": "H64: P_SC future timestamp + P_SD unauthorized loss domain",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=-200.0)],
    "request": r
})

# 65. H65: Stale evidence AND unauthorized loss
r = base_request("req-h65")
r["source"]["timestamp_sec"] = CURRENT_TIME - 1200.0  # P_SC review
r["dissipate"]["loss_domain"] = ["unauthorized_vent"]  # P_SD fail
fixtures.append({
    "id": "H65_stale_evidence_AND_unauthorized_loss",
    "group": "H",
    "name": "H65: P_SC review + P_SD fail -> overall FAIL",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=1200.0)],
    "request": r
})

# 66. H66: Three-way simultaneous failure (P_SC, P_CD, P_SD all FAIL)
r = base_request("req-h66")
r["constraint"]["target_objects"] = ["unauthorized_pump"]  # P_SC fail
r["constraint"]["min_bounds"]["coolant_pressure"] = 100.0  # P_CD fail (4.5 < 100)
r["dissipate"]["loss_domain"] = ["unauthorized_loss"]  # P_SD fail
fixtures.append({
    "id": "H66_three_way_failure",
    "group": "H",
    "name": "H66: Three-way simultaneous channel failure (P_SC, P_CD, P_SD)",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

# 67. H67: Stale evidence with completely valid CD and SD -> overall REVIEW
r = base_request("req-h67")
r["source"]["timestamp_sec"] = CURRENT_TIME - 800.0  # P_SC is REVIEW
fixtures.append({
    "id": "H67_stale_evidence_AND_valid_CD_SD",
    "group": "H",
    "name": "H67: Stale evidence (P_SC REVIEW) with valid P_CD and P_SD -> overall REVIEW",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record(ts_offset=800.0)],
    "request": r
})

# 68. H68: Unsupported protocol AND state breach (Schema defect takes precedence)
r = base_request("req-h68")
r["protocol_version"] = "1.0.0"  # Protocol defect
r["constraint"]["min_bounds"]["coolant_pressure"] = 10.0  # Would also be state breach
fixtures.append({
    "id": "H68_unsupported_protocol_AND_state_breach",
    "group": "H",
    "name": "H68: Schema protocol defect takes precedence over state checks",
    "evaluation_time": CURRENT_TIME,
    "registry_records": [base_record()],
    "request": r
})

output_dir = os.path.join(os.path.dirname(__file__))
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "fixtures.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(fixtures, f, indent=2)

print(f"Successfully generated {len(fixtures)} fixtures at {output_path}")
