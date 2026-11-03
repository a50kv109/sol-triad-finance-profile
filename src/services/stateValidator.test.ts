import { StateValidator } from "./stateValidator";
import { ConstraintPrimitive, DissipatePrimitive, SystemState } from "../types/triad";

function assert(condition: boolean, msg: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${msg}`);
  }
}

console.log("Starting StateValidator Stage 5.1 Unit Tests...");

const validator = new StateValidator();

// 1. Pre-simulation fatal validation: NaN in current_values returns empty {} and {}
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: [],
    min_bounds: { pressure: 1.0 },
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["pressure"],
    side_effects: [],
    state_delta: { pressure: 2.0 },
  };
  const s: SystemState = {
    current_values: { pressure: NaN },
    active_flags: { valve_open: true },
    units: { pressure: "bar" },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(!ok, "NaN current_values must not be ok");
  assert(verdict === "FAIL", "NaN must result in FAIL");
  assert(diags.some((d) => d.code === "STATE_INVALID_NUMERIC"), "Must have STATE_INVALID_NUMERIC");
  assert(Object.keys(vals).length === 0, "simulated_values must be empty {} on pre-simulation numeric failure");
  assert(Object.keys(flags).length === 0, "simulated_flags must be empty {} on pre-simulation numeric failure");
  console.log("✓ Test 1 Passed: Pre-simulation NaN returns empty simulated state");
}

// 2. Pre-simulation fatal validation: Negative resource cost returns empty {} and {}
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: [],
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["energy"],
    side_effects: [],
    resource_cost: { battery: -10.0 },
  };
  const s: SystemState = {
    current_values: { energy: 100.0, battery: 50.0 },
    active_flags: { main_power: true },
    units: { energy: "j", battery: "j" },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(!ok, "Negative resource cost must not be ok");
  assert(verdict === "FAIL", "Negative resource cost must FAIL");
  assert(diags.some((d) => d.code === "STATE_NEGATIVE_RESOURCE_COST"), "Must have STATE_NEGATIVE_RESOURCE_COST");
  assert(Object.keys(vals).length === 0, "simulated_values must be empty {} on negative resource cost");
  assert(Object.keys(flags).length === 0, "simulated_flags must be empty {} on negative resource cost");
  console.log("✓ Test 2 Passed: Negative resource cost returns empty simulated state");
}

// 3. Pre-simulation fatal validation: Protected set mutation returns empty {} and {}
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: ["safety_lock"],
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["pressure", "safety_lock"],
    side_effects: [],
  };
  const s: SystemState = {
    current_values: { pressure: 1.0, safety_lock: 1.0 },
    active_flags: { armed: true },
    units: { pressure: "bar", safety_lock: "ratio" },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(!ok, "Protected set mutation must not be ok");
  assert(verdict === "FAIL", "Protected set mutation must FAIL");
  assert(diags.some((d) => d.code === "STATE_PROTECTED_PARAM_MUTATED"), "Must have STATE_PROTECTED_PARAM_MUTATED");
  assert(Object.keys(vals).length === 0, "simulated_values must be empty {} on protected set mutation");
  assert(Object.keys(flags).length === 0, "simulated_flags must be empty {} on protected set mutation");
  console.log("✓ Test 3 Passed: Protected set mutation returns empty simulated state");
}

// 4. Pre-simulation fatal validation: Unit incompatibility returns empty {} and {} with single diagnostic
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: [],
    units: { pressure: "bar" },
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["pressure"],
    side_effects: [],
    state_delta: { pressure: 5.0 },
    units: { pressure: "second" }, // time vs pressure
  };
  const s: SystemState = {
    current_values: { pressure: 2.0 },
    units: { pressure: "bar" },
    active_flags: { running: true },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(!ok, "Incompatible units must not be ok");
  assert(verdict === "FAIL", "Incompatible units must FAIL");
  const unitDiags = diags.filter((d) => d.code === "UNIT_INCOMPATIBLE");
  assert(unitDiags.length === 1, `Expected exactly 1 UNIT_INCOMPATIBLE diagnostic, got ${unitDiags.length}`);
  assert(Object.keys(vals).length === 0, "simulated_values must be empty {} on unit incompatibility");
  assert(Object.keys(flags).length === 0, "simulated_flags must be empty {} on unit incompatibility");
  console.log("✓ Test 4 Passed: Unit incompatibility returns single diagnostic and empty simulated state");
}

// 5. Protected flags mutation: Forbids illegal mutation, preserves initial flag value
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: [],
    protected_flags: ["emergency_stop"],
    units: { temp: "k" },
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["temp"],
    side_effects: [],
    flag_delta: { emergency_stop: false }, // illegal attempt to disable emergency_stop
    units: { temp: "k" },
  };
  const s: SystemState = {
    current_values: { temp: 300.0 },
    active_flags: { emergency_stop: true, cooling: false },
    units: { temp: "k" },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(!ok, "Protected flag mutation must fail");
  assert(verdict === "FAIL", "Protected flag mutation must FAIL");
  assert(diags.some((d) => d.code === "STATE_PROTECTED_FLAG_MUTATED"), "Must have STATE_PROTECTED_FLAG_MUTATED");
  // CRITICAL: emergency_stop must retain its initial value true, NOT false
  assert(flags["emergency_stop"] === true, "emergency_stop must retain its initial value true");
  console.log("✓ Test 5 Passed: Protected flag mutation preserves initial flag values");
}

// 6. Valid terminal state simulation with unit conversions
{
  const c: ConstraintPrimitive = {
    domain_scope: ["propulsion"],
    target_objects: ["tank_1"],
    protected_set: [],
    min_bounds: { temp: 250.0 }, // K
    max_bounds: { temp: 350.0 }, // K
    units: { temp: "k" },
  };
  const d: DissipatePrimitive = {
    loss_domain: ["thermal"],
    target_states: ["temp"],
    side_effects: [],
    state_delta: { temp: 10.0 }, // 10 C delta = 10 K delta
    units: { temp: "c" },
  };
  const s: SystemState = {
    current_values: { temp: 290.0 }, // K
    units: { temp: "k" },
    active_flags: { operational: true },
  };

  const [ok, verdict, diags, vals, flags] = validator.validate(c, d, s);
  assert(ok, "Valid state transition must pass");
  assert(verdict === "PASS", "Verdict must be PASS");
  assert(Math.abs(vals["temp"] - 300.0) < 1e-6, `Simulated temp should be 300.0 K, got ${vals["temp"]}`);
  assert(flags["operational"] === true, "Flags should be preserved");
  console.log("✓ Test 6 Passed: Temperature delta converted without affine offset in state simulation");
}

console.log("All 6 StateValidator unit tests PASSED!");
