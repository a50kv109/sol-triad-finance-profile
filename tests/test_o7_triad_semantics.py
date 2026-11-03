"""
Unit and Semantic Tests for O7 Primitive Mapping and SOL-Triad Engine Semantics.

Validates the concrete operational semantics of each of the 7 primitives from O7:
  1. SOURCE: Epistemic provenance, authority domain, and anti-self-minting.
  2. STATE: Initial snapshot S_0 and simulated terminal state S'.
  3. FLOW: Static state/flag transitions vs dynamic execution graph gap.
  4. CONSTRAINT: Boundaries, protected invariants, numerical bounds, and unit types.
  5. COMPARE: Pairwise coherence projections (P_SC, P_CD, P_SD) vs goal utility gap.
  6. DISSIPATE: Entropy loss domains, side effects, and non-negative resource costs.
  7. CAPABILITY: Passive scope bounding vs executable tool API gap.
  8. O7 Mapping: Explicit audit trail with zero silent data loss.
  9. Epistemic Arbiter: Fail-closed review stability (REVIEW never silently promoted to PASS).

Framework: Standard library unittest (no external dependencies required).
"""

import unittest
from sol_triad.models import (
    SourcePrimitive,
    ConstraintPrimitive,
    DissipatePrimitive,
    SystemState,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
)
from sol_triad.evidence import InMemoryEvidenceRegistry
from sol_triad.engine import SolTriadEngine
from sol_triad.units import UnitRegistry
from sol_triad.o7_mapping import (
    O7Source,
    O7State,
    O7Flow,
    O7Constraint,
    O7Compare,
    O7Dissipate,
    O7Capability,
    O7Bundle,
    map_o7_to_triad,
)


class TestO7TriadSemantics(unittest.TestCase):
    """Semantic validation of O7 concepts against SOL-Triad Engine."""

    def setUp(self):
        self.fixed_time = 1700000000.0
        self.registry = InMemoryEvidenceRegistry()
        self.engine = SolTriadEngine(registry=self.registry, clock=lambda: self.fixed_time)

    def test_01_source_semantic_grounding_and_authority_containment(self):
        """SOURCE: Validates epistemic grounding, authority domain, and anti-self-minting."""
        # Register authoritative ground-truth
        self.registry.register(EvidenceRecord(
            evidence_id="ev-fs-001",
            domain="filesystem_ops",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 10.0,
        ))

        # Agent presents valid source
        source = SourcePrimitive(
            evidence_id="ev-fs-001",
            authority_domain={"filesystem_ops"},
            granted_scope={"config.json", "data.csv"},
            granted_loss_domains={"disk_space"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 10.0,
        )
        constraint = ConstraintPrimitive(
            domain_scope={"filesystem_ops"},
            target_objects={"config.json"},
            protected_set={"os_kernel"},
        )
        dissipate = DissipatePrimitive(
            loss_domain={"disk_space"},
            target_states={"config_updated"},
            side_effects={"write_disk"},
        )
        state = SystemState()

        report = self.engine.evaluate(source, constraint, dissipate, state, evaluation_time=self.fixed_time)
        self.assertEqual(report.verdict, CoherenceVerdict.PASS)
        self.assertTrue(report.pairwise_checks["P_SC"].is_valid)

        # Anti-self-minting: Agent requests unauthorized domain outside registry authority
        bad_constraint = ConstraintPrimitive(
            domain_scope={"system_admin_root"},  # Escalation attempt!
            target_objects={"config.json"},
            protected_set={"os_kernel"},
        )
        report_escalation = self.engine.evaluate(source, bad_constraint, dissipate, state, evaluation_time=self.fixed_time)
        self.assertEqual(report_escalation.verdict, CoherenceVerdict.FAIL)
        self.assertFalse(report_escalation.pairwise_checks["P_SC"].is_valid)
        diag_codes = [d.code for d in report_escalation.diagnostics]
        self.assertIn(DiagnosticCode.SCOPE_EXCEEDED_DOMAIN, diag_codes)

    def test_02_state_initial_snapshot_and_terminal_simulation(self):
        """STATE: SystemState provides initial S_0; engine computes S' = S_0 + Delta - Cost."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-power-01",
            domain="power_management",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 5.0,
        ))
        source = SourcePrimitive(
            evidence_id="ev-power-01",
            authority_domain={"power_management"},
            granted_scope={"battery", "cpu"},
            granted_loss_domains={"energy"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 5.0,
        )
        constraint = ConstraintPrimitive(
            domain_scope={"power_management"},
            target_objects={"battery"},
            protected_set=set(),
            min_bounds={"battery_level": 20.0},  # Invariant: cannot drop below 20%
            max_bounds={"battery_level": 100.0},
        )
        # S_0: battery at 50%
        initial_state = SystemState(
            current_values={"battery_level": 50.0},
            active_flags={"power_on": True},
        )
        # Actuation: cost of 15% -> terminal level = 35% (Valid, >= 20%)
        dissipate_safe = DissipatePrimitive(
            loss_domain={"energy"},
            target_states={"compute_done"},
            side_effects=set(),
            resource_cost={"battery_level": 15.0},
        )
        report_safe = self.engine.evaluate(source, constraint, dissipate_safe, initial_state, evaluation_time=self.fixed_time)
        self.assertEqual(report_safe.verdict, CoherenceVerdict.PASS)
        self.assertEqual(report_safe.simulated_values["battery_level"], 35.0)

        # Actuation: cost of 40% -> terminal level = 10% (Violates min_bounds 20.0)
        dissipate_excessive = DissipatePrimitive(
            loss_domain={"energy"},
            target_states={"compute_done"},
            side_effects=set(),
            resource_cost={"battery_level": 40.0},
        )
        report_breach = self.engine.evaluate(source, constraint, dissipate_excessive, initial_state, evaluation_time=self.fixed_time)
        self.assertEqual(report_breach.verdict, CoherenceVerdict.FAIL)
        self.assertEqual(report_breach.simulated_values["battery_level"], 10.0)
        diag_codes = [d.code for d in report_breach.diagnostics]
        self.assertIn(DiagnosticCode.STATE_MIN_BOUND_BREACH, diag_codes)

    def test_03_flow_static_transition_vs_dynamic_branching_gap(self):
        """FLOW: Triad models static delta transitions, but dynamic execution paths are absent."""
        # Verify that DISSIPATE accepts state_delta and flag_delta
        dissipate = DissipatePrimitive(
            loss_domain={"storage"},
            target_states={"file_written"},
            side_effects={"disk_io"},
            state_delta={"file_size_kb": 120.0},
            flag_delta={"file_synced": True},
        )
        self.assertEqual(dissipate.state_delta["file_size_kb"], 120.0)
        self.assertEqual(dissipate.flag_delta["file_synced"], True)

        # Confirm the architectural gap: DissipatePrimitive has NO fields for sequence loops,
        # branching logic, or temporal progression graphs.
        self.assertFalse(hasattr(dissipate, "branch_conditions"))
        self.assertFalse(hasattr(dissipate, "sequence_step"))
        self.assertFalse(hasattr(dissipate, "loop_iterations"))

    def test_04_constraint_invariants_bounds_and_units(self):
        """CONSTRAINT: Enforces boundary invariants, protected sets, bounds, and units."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-telemetry",
            domain="avionics",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        ))
        source = SourcePrimitive(
            evidence_id="ev-telemetry",
            authority_domain={"avionics"},
            granted_scope={"telemetry"},
            granted_loss_domains={"bandwidth"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        )
        # Protected parameter: "calibration_offset" must never be mutated
        constraint = ConstraintPrimitive(
            domain_scope={"avionics"},
            target_objects={"telemetry"},
            protected_set={"calibration_offset"},
            protected_flags={"safe_mode"},
        )
        initial_state = SystemState(
            current_values={"calibration_offset": 1.25, "altitude": 1000.0},
            active_flags={"safe_mode": True},
        )
        # Attempt to mutate protected parameter
        forbidden_dissipate = DissipatePrimitive(
            loss_domain={"bandwidth"},
            target_states={"calibration_altered"},
            side_effects=set(),
            state_delta={"calibration_offset": 0.5},
        )
        report = self.engine.evaluate(source, constraint, forbidden_dissipate, initial_state, evaluation_time=self.fixed_time)
        self.assertEqual(report.verdict, CoherenceVerdict.FAIL)
        diag_codes = [d.code for d in report.diagnostics]
        self.assertIn(DiagnosticCode.STATE_PROTECTED_PARAM_MUTATED, diag_codes)

    def test_05_compare_pairwise_topology_vs_goal_utility_gap(self):
        """COMPARE: Formalized as pairwise coherence (P_SC, P_CD, P_SD), not goal utility."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-compare-demo",
            domain="thermal",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 2.0,
        ))
        source = SourcePrimitive(
            evidence_id="ev-compare-demo",
            authority_domain={"thermal"},
            granted_scope={"heater"},
            granted_loss_domains={"heat_sink"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 2.0,
        )
        constraint = ConstraintPrimitive(
            domain_scope={"thermal"},
            target_objects={"heater"},
            protected_set=set(),
            max_bounds={"temp_c": 100.0},
        )
        dissipate = DissipatePrimitive(
            loss_domain={"heat_sink"},
            target_states={"warmed"},
            side_effects=set(),
            state_delta={"temp_c": 20.0},
        )
        state = SystemState(current_values={"temp_c": 50.0})

        report = self.engine.evaluate(source, constraint, dissipate, state, evaluation_time=self.fixed_time)
        # 1. Pairwise checks exist and are strictly verified
        self.assertIn("P_SC", report.pairwise_checks)
        self.assertIn("P_CD", report.pairwise_checks)
        self.assertIn("P_SD", report.pairwise_checks)
        self.assertTrue(report.pairwise_checks["P_SC"].is_valid)
        self.assertTrue(report.pairwise_checks["P_CD"].is_valid)
        self.assertTrue(report.pairwise_checks["P_SD"].is_valid)

        # 2. Confirm the architectural gap: The engine verifies logical coherence,
        # but does NOT evaluate expected goal utility, optimality, or reward functions.
        self.assertFalse(hasattr(report, "expected_utility"))
        self.assertFalse(hasattr(report, "goal_alignment_score"))

    def test_06_dissipate_entropy_loss_costs_and_domains(self):
        """DISSIPATE: Enforces non-negative costs and loss domain authorization."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-engine",
            domain="propulsion",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        ))
        source = SourcePrimitive(
            evidence_id="ev-engine",
            authority_domain={"propulsion"},
            granted_scope={"thruster"},
            granted_loss_domains={"fuel_tank_a"},  # Only tank A authorized
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        )
        constraint = ConstraintPrimitive(
            domain_scope={"propulsion"},
            target_objects={"thruster"},
            protected_set=set(),
        )
        state = SystemState(current_values={"fuel_kg": 100.0})

        # Subcase 6A: Negative resource cost is rejected as physical absurdity
        dissipate_negative = DissipatePrimitive(
            loss_domain={"fuel_tank_a"},
            target_states={"thrust_applied"},
            side_effects=set(),
            resource_cost={"fuel_kg": -10.0},  # Negative cost!
        )
        report_neg = self.engine.evaluate(source, constraint, dissipate_negative, state, evaluation_time=self.fixed_time)
        self.assertEqual(report_neg.verdict, CoherenceVerdict.FAIL)
        diag_codes = [d.code for d in report_neg.diagnostics]
        self.assertIn(DiagnosticCode.STATE_NEGATIVE_RESOURCE_COST, diag_codes)

        # Subcase 6B: Loss domain leakage (dissipating into unauthorized fuel_tank_b)
        dissipate_leakage = DissipatePrimitive(
            loss_domain={"fuel_tank_b"},  # Not in granted_loss_domains!
            target_states={"thrust_applied"},
            side_effects=set(),
            resource_cost={"fuel_kg": 10.0},
        )
        report_leak = self.engine.evaluate(source, constraint, dissipate_leakage, state, evaluation_time=self.fixed_time)
        self.assertEqual(report_leak.verdict, CoherenceVerdict.FAIL)
        self.assertFalse(report_leak.pairwise_checks["P_SD"].is_valid)
        diag_codes = [d.code for d in report_leak.diagnostics]
        self.assertIn(DiagnosticCode.SCOPE_EXCEEDED_LOSS, diag_codes)

    def test_07_capability_passive_scope_vs_tool_api_gap(self):
        """CAPABILITY: Authority is passive set-membership; executable tool APIs are absent."""
        # In Triad Engine, permissions are passive subsets in SourcePrimitive
        source = SourcePrimitive(
            evidence_id="ev-tool-auth",
            authority_domain={"devops"},
            granted_scope={"deploy_service"},
            granted_loss_domains={"cloud_spend"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time,
        )
        self.assertIn("deploy_service", source.granted_scope)
        # Gap: Engine does NOT have tool execution handlers or RPC stubs
        self.assertFalse(hasattr(source, "execute_tool"))
        self.assertFalse(hasattr(self.engine, "dispatch_tool"))

    def test_08_o7_mapping_layer_no_silent_information_loss(self):
        """O7 Mapping: Explicit audit trail with zero silent data loss on file edit action."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-file-edit-42",
                authority_domain={"codebase_maintenance"},
                granted_scope={"src/config.py"},
                granted_loss_domains={"disk_storage"},
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time - 5.0,
                creator_signature="ed25519:abcdef123456",  # Unrepresented in triad
                provenance_chain=["agent-planner-v1", "user-instruction-prompt"],  # Unrepresented
            ),
            state=O7State(
                current_values={"file_lines": 120.0},
                active_flags={"is_locked": False},
                units={"file_lines": "count"},
                memory_context={"conversation_turn": 3},  # Unrepresented
            ),
            flow=O7Flow(
                state_delta={"file_lines": 15.0},
                resource_cost={"disk_bytes": 512.0},
                units={"file_lines": "count", "disk_bytes": "bytes"},
                sequence_step=2,  # Unrepresented
                branch_conditions={"if_syntax_valid": True},  # Unrepresented
            ),
            constraint=O7Constraint(
                domain_scope={"codebase_maintenance"},
                target_objects={"src/config.py"},
                protected_set={"src/kernel.py"},
                max_bounds={"file_lines": 500.0},
                policy_rules=["Do not delete production keys"],  # Unrepresented
            ),
            compare=O7Compare(
                target_states={"config_updated"},
                goal_utility_function="maximize_maintainability()",  # Unrepresented
                tolerance_thresholds={"file_lines": 0.0},  # Unrepresented
            ),
            dissipate=O7Dissipate(
                loss_domain={"disk_storage"},
                side_effects={"disk_write"},
                entropy_delta=0.05,  # Unrepresented
            ),
            capability=O7Capability(
                tool_name="edit_file",
                allowed_operations={"write", "patch"},
            ),
        )

        mapping_result = map_o7_to_triad(bundle)
        self.assertTrue(mapping_result.is_valid)
        self.assertIsNotNone(mapping_result.source_primitive)
        self.assertIsNotNone(mapping_result.constraint_primitive)
        self.assertIsNotNone(mapping_result.dissipate_primitive)
        self.assertIsNotNone(mapping_result.system_state)

        # Execution gate: must be False because unrepresented fields exist
        self.assertFalse(mapping_result.is_executable)

        # Calling get_engine_inputs() without explicit allow_unrepresented must fail closed
        with self.assertRaises(ValueError):
            mapping_result.get_engine_inputs(allow_unrepresented=False)

        # With explicit acknowledgement, engine inputs can be retrieved
        inputs = mapping_result.get_engine_inputs(allow_unrepresented=True)
        self.assertEqual(len(inputs), 4)

        # CRITICAL INVARIANT: Zero silent data loss!
        # Unrepresented fields must be explicitly reported with their original values:
        unrep_str = " ".join(mapping_result.unrepresented_fields)
        self.assertIn("creator_signature", unrep_str)
        self.assertIn("provenance_chain", unrep_str)
        self.assertIn("policy_rules", unrep_str)
        self.assertIn("sequence_step", unrep_str)
        self.assertIn("branch_conditions", unrep_str)
        self.assertIn("goal_utility_function", unrep_str)
        self.assertIn("tolerance_thresholds", unrep_str)
        self.assertIn("entropy_delta", unrep_str)
        self.assertIn("O7Capability", unrep_str)
        self.assertIn("memory_context", unrep_str)

    def test_09_epistemic_arbiter_review_never_silently_promoted_to_pass(self):
        """Epistemic Arbiter: Stale evidence or UNKNOWN status yields REVIEW, NEVER PASS."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-stale",
            domain="maintenance",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1000.0,  # 1000s old
        ))
        source = SourcePrimitive(
            evidence_id="ev-stale",
            authority_domain={"maintenance"},
            granted_scope={"pump"},
            granted_loss_domains={"power"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1000.0,
            max_age_sec=300.0,  # Expired after 300s!
        )
        constraint = ConstraintPrimitive(
            domain_scope={"maintenance"},
            target_objects={"pump"},
            protected_set=set(),
        )
        dissipate = DissipatePrimitive(
            loss_domain={"power"},
            target_states={"inspected"},
            side_effects=set(),
        )
        state = SystemState()

        report = self.engine.evaluate(source, constraint, dissipate, state, evaluation_time=self.fixed_time)
        # CRITICAL FAIL-CLOSED INVARIANT: Stale evidence must yield REVIEW, never PASS!
        self.assertEqual(report.verdict, CoherenceVerdict.REVIEW)
        self.assertNotEqual(report.verdict, CoherenceVerdict.PASS)
        diag_codes = [d.code for d in report.diagnostics]
        self.assertIn(DiagnosticCode.TEMPORAL_STALE, diag_codes)

    def test_10_o7_mapping_empty_source_id_rejected(self):
        """O7 Mapping: Empty or whitespace source.id must return is_valid=False with clear rejection reason."""
        bundle = O7Bundle(
            source=O7Source(
                id="   ",
                authority_domain={"domain_a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_executable)
        self.assertIn("O7Source.id is empty or whitespace", res.rejection_reason)

    def test_11_o7_mapping_missing_authority_domain_rejected(self):
        """O7 Mapping: None authority_domain must return is_valid=False with clear rejection reason."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-valid-id",
                authority_domain=None,  # Structural defect!
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_executable)
        self.assertIn("authority_domain is None", res.rejection_reason)

    def test_12_o7_mapping_missing_units_rejected(self):
        """O7 Mapping: Missing units for numerical variables in flow/dissipate must reject fail-closed."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-valid-id",
                authority_domain={"domain_a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(units={}),  # No unit here
            flow=O7Flow(
                state_delta={"coolant_flow": 2.5},  # No unit in flow!
                units={},
            ),
            constraint=O7Constraint(units={}),
            compare=O7Compare(),
            dissipate=O7Dissipate(units={}),  # No unit in dissipate!
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_executable)
        self.assertIn("Missing physical unit for variable 'coolant_flow'", res.rejection_reason)

    def test_13_o7_mapping_conflicting_units_rejected(self):
        """O7 Mapping: Incompatible units across flow, dissipate, or state must reject fail-closed."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-valid-id",
                authority_domain={"domain_a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(
                current_values={"pressure": 5.0},
                units={"pressure": "bar"},  # Dimension: pressure
            ),
            flow=O7Flow(
                state_delta={"pressure": 1.0},
                units={"pressure": "sec"},  # Incompatible dimension: time!
            ),
            constraint=O7Constraint(units={"pressure": "bar"}),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_executable)
        self.assertIn("Conflicting units for variable 'pressure'", res.rejection_reason)
        self.assertIn("Incompatible physical dimensions", res.rejection_reason)

    def test_14_o7_mapping_tolerance_thresholds_captured(self):
        """O7 Mapping: tolerance_thresholds in O7Compare must be explicitly logged in unrepresented_fields."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-test",
                authority_domain={"thermal"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(
                target_states={"coolant_stable"},
                tolerance_thresholds={"temperature_k": 0.25},
            ),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.is_executable)
        unrep = " ".join(res.unrepresented_fields)
        self.assertIn("O7Compare.tolerance_thresholds", unrep)
        self.assertIn("temperature_k", unrep)
        self.assertIn("0.25", unrep)

    def test_15_o7_mapping_entropy_delta_captured(self):
        """O7 Mapping: Non-zero entropy_delta in O7Dissipate must be captured in unrepresented_fields."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-test",
                authority_domain={"thermal"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(
                loss_domain={"heat_sink"},
                entropy_delta=1.414,
            ),
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.is_executable)
        unrep = " ".join(res.unrepresented_fields)
        self.assertIn("O7Dissipate.entropy_delta=1.414", unrep)

    def test_16_o7_mapping_capability_none_handled_explicitly(self):
        """O7 Mapping: capability=None must be noted in transformations and not pollute unrepresented."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-test",
                authority_domain={"thermal"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
            capability=None,  # Explicit None
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        transforms = " ".join(res.applied_transformations)
        self.assertIn("O7Capability is None", transforms)
        unrep = " ".join(res.unrepresented_fields)
        self.assertNotIn("O7Capability", unrep)

    def test_17_o7_mapping_execution_gate_fail_closed(self):
        """O7 Mapping: Mapping with unrepresented fields raises ValueError when attempting execution."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-test",
                authority_domain={"thermal"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
                creator_signature="sig-12345",  # Unrepresented
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.is_executable)

        # Accidental execution attempt without acknowledgement MUST raise
        with self.assertRaises(ValueError) as ctx:
            res.get_engine_inputs()
        self.assertIn("unrepresented fields present", str(ctx.exception))

    def test_18_o7_mapping_lossless_bundle_is_executable(self):
        """O7 Mapping: Completely lossless bundle maps to is_executable=True and evaluates successfully."""
        self.registry.register(EvidenceRecord(
            evidence_id="ev-lossless-001",
            domain="thermal",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        ))
        bundle = O7Bundle(
            source=O7Source(
                id="ev-lossless-001",
                authority_domain={"thermal"},
                granted_scope={"radiator"},
                granted_loss_domains={"heat"},
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time - 1.0,
            ),
            state=O7State(
                current_values={"temp_c": 50.0},
                units={"temp_c": "c"},
            ),
            flow=O7Flow(
                state_delta={"temp_c": 5.0},
                units={"temp_c": "c"},
            ),
            constraint=O7Constraint(
                domain_scope={"thermal"},
                target_objects={"radiator"},
                max_bounds={"temp_c": 100.0},
                units={"temp_c": "c"},
            ),
            compare=O7Compare(
                target_states={"radiator_warm"},
            ),
            dissipate=O7Dissipate(
                loss_domain={"heat"},
            ),
            capability=None,
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_executable)
        self.assertEqual(len(res.unrepresented_fields), 0)

        # Retrieve inputs safely and evaluate via SolTriadEngine
        s, c, d, state = res.get_engine_inputs()
        report = self.engine.evaluate(s, c, d, state, evaluation_time=self.fixed_time)
        self.assertEqual(report.verdict, CoherenceVerdict.PASS)
        self.assertEqual(report.simulated_values["temp_c"], 55.0)

    def test_19_o7_mapping_get_engine_inputs_invalid_rejected_even_with_allow_unrepresented(self):
        """Contract: allow_unrepresented=True CANNOT bypass an invalid mapping."""
        bundle = O7Bundle(
            source=O7Source(
                id="   ",  # Invalid ID
                authority_domain={"domain_a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_executable)

        # Attempting execution with allow_unrepresented=True MUST fail closed
        with self.assertRaises(ValueError) as ctx:
            res.get_engine_inputs(allow_unrepresented=True)
        self.assertIn("Mapping is invalid", str(ctx.exception))

    def test_20_o7_mapping_unresolved_ambiguities_block_execution(self):
        """Contract: Ambiguities block execution even when allow_unrepresented=True."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-valid",
                authority_domain={"domain_a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)

        # Inject an ambiguity manually into the result
        res.ambiguities.append("Conflicting semantics in domain taxonomy")
        with self.assertRaises(ValueError) as ctx:
            res.get_engine_inputs(allow_unrepresented=True)
        self.assertIn("ambiguities present", str(ctx.exception))

    def test_21_o7_mapping_null_or_invalid_nested_primitives_rejected(self):
        """Contract: Null bundle or null nested primitives reject fail-closed without exception."""
        # 1. Null bundle
        res_null = map_o7_to_triad(None)
        self.assertFalse(res_null.is_valid)
        self.assertFalse(res_null.is_executable)
        self.assertIn("bundle is None", res_null.rejection_reason)

        # 2. Null source
        bundle_no_src = O7Bundle(
            source=None,
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_no_src = map_o7_to_triad(bundle_no_src)
        self.assertFalse(res_no_src.is_valid)
        self.assertIn("O7Bundle.source is None", res_no_src.rejection_reason)

        # 3. Null flow
        bundle_no_flow = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=None,
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_no_flow = map_o7_to_triad(bundle_no_flow)
        self.assertFalse(res_no_flow.is_valid)
        self.assertIn("O7Bundle.flow is None", res_no_flow.rejection_reason)

    def test_22_o7_mapping_explicit_zero_entropy_delta_captured(self):
        """Contract: Explicit entropy_delta=0.0 is captured as unrepresented (not silently ignored)."""
        bundle = O7Bundle(
            source=O7Source(
                id="ev-test",
                authority_domain={"thermal"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(
                loss_domain={"heat_sink"},
                entropy_delta=0.0,  # Explicitly zero entropy delta
            ),
        )
        res = map_o7_to_triad(bundle)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.is_executable)
        unrep = " ".join(res.unrepresented_fields)
        self.assertIn("O7Dissipate.entropy_delta=0.0", unrep)

    def test_23_o7_mapping_malformed_units_type_rejected(self):
        """Contract: Non-string or empty/whitespace unit values are rejected fail-closed."""
        # Non-string unit
        bundle_bad_type = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(units={"speed": 100}),  # Invalid type: int
            flow=O7Flow(),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_bad_type = map_o7_to_triad(bundle_bad_type)
        self.assertFalse(res_bad_type.is_valid)
        self.assertIn("must be a non-empty string", res_bad_type.rejection_reason)

        # Whitespace unit
        bundle_whitespace_unit = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(units={"pressure": "   "}),  # Whitespace
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_ws = map_o7_to_triad(bundle_whitespace_unit)
        self.assertFalse(res_ws.is_valid)
        self.assertIn("must be a non-empty string", res_ws.rejection_reason)

    def test_24_o7_mapping_pairwise_unit_conflict_source_order_independent(self):
        """Contract: Unit conflict across any pair of components is caught regardless of source order."""
        # Conflict between state ('sec') and constraint ('bar')
        bundle = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(current_values={"pressure": 10.0}, units={"pressure": "sec"}),
            flow=O7Flow(state_delta={"pressure": 1.0}),  # No unit in flow, candidates: state vs constraint
            constraint=O7Constraint(units={"pressure": "bar"}),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res = map_o7_to_triad(bundle)
        self.assertFalse(res.is_valid)
        self.assertIn("Conflicting units for variable 'pressure'", res.rejection_reason)

    def test_25_o7_mapping_non_numeric_deltas_or_costs_rejected(self):
        """Contract: Non-numeric values in state_delta or resource_cost are rejected fail-closed."""
        bundle_str_delta = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(state_delta={"var": "not_a_number"}, units={"var": "count"}),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_delta = map_o7_to_triad(bundle_str_delta)
        self.assertFalse(res_delta.is_valid)
        self.assertIn("must be a numeric value", res_delta.rejection_reason)

        bundle_str_cost = O7Bundle(
            source=O7Source(
                id="ev-1",
                authority_domain={"a"},
                granted_scope=set(),
                granted_loss_domains=set(),
                epistemic_status=EpistemicStatus.FACT,
                timestamp_sec=self.fixed_time,
            ),
            state=O7State(),
            flow=O7Flow(resource_cost={"fuel": [10.0]}, units={"fuel": "kg"}),
            constraint=O7Constraint(),
            compare=O7Compare(),
            dissipate=O7Dissipate(),
        )
        res_cost = map_o7_to_triad(bundle_str_cost)
        self.assertFalse(res_cost.is_valid)
        self.assertIn("must be a numeric value", res_cost.rejection_reason)

    def test_26_temperature_delta_and_resource_cost_conversions(self):
        """Temperature deltas and resource costs use convert_delta() without affine offset."""
        # 1. Direct UnitRegistry unit conversion checks
        self.assertEqual(UnitRegistry.convert_delta(10.0, "c", "k"), 10.0)
        self.assertEqual(UnitRegistry.convert(10.0, "c", "k"), 283.15)
        self.assertAlmostEqual(UnitRegistry.convert_delta(10.0, "f", "c"), 50.0 / 9.0, places=6)

        # 2. End-to-end engine simulation: state_delta in Celsius on Kelvin base state
        self.registry.register(EvidenceRecord(
            evidence_id="ev-thermal-01",
            domain="thermal",
            epistemic_status=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        ))
        source = SourcePrimitive(
            evidence_id="ev-thermal-01",
            authority_domain={"thermal"},
            granted_scope={"cooler"},
            granted_loss_domains={"heat"},
            epistemic_type=EpistemicStatus.FACT,
            timestamp_sec=self.fixed_time - 1.0,
        )
        constraint = ConstraintPrimitive(
            domain_scope={"thermal"},
            target_objects={"cooler"},
            protected_set=set(),
            min_bounds={"temp": 250.0},
            max_bounds={"temp": 350.0},
            units={"temp": "k"},
        )
        initial_state = SystemState(
            current_values={"temp": 300.0},
            units={"temp": "k"},
        )

        # state_delta of +10 C -> increments Kelvin state by 10 K to 310 K (not +283.15 K)
        dissipate_delta = DissipatePrimitive(
            loss_domain={"heat"},
            target_states={"temp_adjusted"},
            side_effects=set(),
            state_delta={"temp": 10.0},
            units={"temp": "c"},
        )
        report_delta = self.engine.evaluate(source, constraint, dissipate_delta, initial_state, evaluation_time=self.fixed_time)
        self.assertEqual(report_delta.verdict, CoherenceVerdict.PASS)
        self.assertAlmostEqual(report_delta.simulated_values["temp"], 310.0, places=6)

        # resource_cost of 10 C -> decrements Kelvin state by 10 K to 290 K (not -283.15 K)
        dissipate_cost = DissipatePrimitive(
            loss_domain={"heat"},
            target_states={"temp_cooled"},
            side_effects=set(),
            resource_cost={"temp": 10.0},
            units={"temp": "c"},
        )
        report_cost = self.engine.evaluate(source, constraint, dissipate_cost, initial_state, evaluation_time=self.fixed_time)
        self.assertEqual(report_cost.verdict, CoherenceVerdict.PASS)
        self.assertAlmostEqual(report_cost.simulated_values["temp"], 290.0, places=6)

        # Invariant checks: min_bounds uses absolute convert()
        # min_bound of 20 C = 293.15 K. Simulated value of 290 K violates min_bounds!
        constraint_with_celsius_bound = ConstraintPrimitive(
            domain_scope={"thermal"},
            target_objects={"cooler"},
            protected_set=set(),
            min_bounds={"temp": 20.0},  # 20 C = 293.15 K
            units={"temp": "c"},
        )
        report_bound_breach = self.engine.evaluate(
            source, constraint_with_celsius_bound, dissipate_cost, initial_state, evaluation_time=self.fixed_time
        )
        self.assertEqual(report_bound_breach.verdict, CoherenceVerdict.FAIL)
        diag_codes = [d.code for d in report_bound_breach.diagnostics]
        self.assertIn(DiagnosticCode.STATE_MIN_BOUND_BREACH, diag_codes)


if __name__ == "__main__":
    unittest.main()
