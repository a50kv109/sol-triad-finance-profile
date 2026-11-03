/**
 * Unit & Dimensional Verification Test Suite (Step 1)
 * Validates exact parity between unitsService.ts / engineService.ts and Python reference sol_triad/units.py
 */

import { UnitRegistry, DimensionalityError, UnknownUnitError } from "./unitsService";
import { evaluateTriad } from "./engineService";
import {
  SourcePrimitive,
  ConstraintPrimitive,
  DissipatePrimitive,
  SystemState,
  EvidenceRecord,
} from "../types/triad";

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertClose(actual: number, expected: number, tolerance: number = 1e-6, message: string = "") {
  if (Math.abs(actual - expected) > tolerance) {
    throw new Error(`Assertion failed: ${message} (Expected ${expected}, got ${actual})`);
  }
}

export function runStep1Tests() {
  console.log("=================================================================");
  console.log("RUNNING STEP 1 UNIT & DIMENSIONAL CONVERSION TESTS (TypeScript)");
  console.log("=================================================================\n");

  let passed = 0;
  let failed = 0;

  function test(name: string, fn: () => void) {
    try {
      fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (e) {
      console.error(`  [FAIL] ${name}: ${(e as Error).message}`);
      failed++;
    }
  }

  // --- 1. Absolute temperature conversions ---
  test("1.1 convert: 0 Celsius is 273.15 Kelvin", () => {
    const k = UnitRegistry.convert(0, "c", "k");
    assertClose(k, 273.15, 1e-6, "0 C -> K");
  });

  test("1.2 convert: 100 Celsius is 373.15 Kelvin", () => {
    const k = UnitRegistry.convert(100, "c", "k");
    assertClose(k, 373.15, 1e-6, "100 C -> K");
  });

  test("1.3 convert: 32 Fahrenheit is 273.15 Kelvin", () => {
    const k = UnitRegistry.convert(32, "f", "k");
    assertClose(k, 273.15, 1e-6, "32 F -> K");
  });

  test("1.4 convert: 212 Fahrenheit is 100 Celsius", () => {
    const c = UnitRegistry.convert(212, "f", "c");
    assertClose(c, 100.0, 1e-6, "212 F -> C");
  });

  // --- 2. Temperature delta conversions (WITHOUT affine offsets) ---
  test("2.1 convertDelta: Delta 10 Celsius is exactly 10.0 Kelvin (NOT 283.15 K)", () => {
    const deltaK = UnitRegistry.convertDelta(10, "c", "k");
    assertClose(deltaK, 10.0, 1e-6, "Delta 10 C -> 10 K");
  });

  test("2.2 convertDelta: Delta -5 Celsius is -5.0 Kelvin", () => {
    const deltaK = UnitRegistry.convertDelta(-5, "c", "k");
    assertClose(deltaK, -5.0, 1e-6, "Delta -5 C -> -5 K");
  });

  test("2.3 convertDelta: Delta 18 Fahrenheit is 10.0 Kelvin", () => {
    const deltaK = UnitRegistry.convertDelta(18, "f", "k");
    assertClose(deltaK, 10.0, 1e-6, "Delta 18 F -> 10 K");
  });

  test("2.4 convertDelta: Delta 10 Kelvin is 10.0 Celsius", () => {
    const deltaC = UnitRegistry.convertDelta(10, "k", "c");
    assertClose(deltaC, 10.0, 1e-6, "Delta 10 K -> 10 C");
  });

  // --- 3. Linear physical unit conversions ---
  test("3.1 convert & convertDelta: 50 kPa is 0.5 bar", () => {
    const bar = UnitRegistry.convert(50, "kpa", "bar");
    const deltaBar = UnitRegistry.convertDelta(50, "kpa", "bar");
    assertClose(bar, 0.5, 1e-6, "50 kPa -> 0.5 bar");
    assertClose(deltaBar, 0.5, 1e-6, "Delta 50 kPa -> 0.5 bar");
  });

  test("3.2 convert: 1 hour is 3600 seconds", () => {
    const s = UnitRegistry.convert(1, "hr", "s");
    assertClose(s, 3600, 1e-6, "1 hr -> 3600 s");
  });

  // --- 4. Anti-bypass & compatibility checks ---
  test("4.1 areCompatible: Incompatible dimensions (pressure vs time) reject", () => {
    const [ok, msg] = UnitRegistry.areCompatible("bar", "sec");
    assert(!ok, "bar vs sec should not be compatible");
    assert(msg.includes("Dimensional incompatibility"), "message explanation");
  });

  test("4.2 areCompatible: Asymmetric unit specification rejects", () => {
    const [ok, msg] = UnitRegistry.areCompatible("bar", null);
    assert(!ok, "bar vs null should not be compatible");
    assert(msg.includes("Asymmetric unit specification"), "message explanation");
  });

  test("4.3 areCompatible: Unknown units reject (no None==None bypass)", () => {
    const [ok, msg] = UnitRegistry.areCompatible("quantum_flux", "quantum_flux");
    assert(!ok, "unknown units should not be compatible with each other");
    assert(msg.includes("unknown to UnitRegistry"), "message explanation");
  });

  test("4.4 convert throws DimensionalityError on incompatible dimensions", () => {
    let thrown = false;
    try {
      UnitRegistry.convert(10, "bar", "sec");
    } catch (e) {
      thrown = e instanceof DimensionalityError;
    }
    assert(thrown, "Should throw DimensionalityError");
  });

  test("4.5 convert throws UnknownUnitError on unrecognized unit", () => {
    let thrown = false;
    try {
      UnitRegistry.convert(10, "magic_units", "bar");
    } catch (e) {
      thrown = e instanceof UnknownUnitError;
    }
    assert(thrown, "Should throw UnknownUnitError");
  });

  // --- 5. Integrated state simulation with temperature delta ---
  test("5.1 State simulation: T0 = 300 K + Delta 10 C results in 310 K (NOT 583.15 K)", () => {
    const s: SourcePrimitive = {
      evidence_id: "ev-sensor-temp",
      authority_domain: ["thermal_telemetry"],
      granted_scope: ["coolant_loop"],
      granted_loss_domains: ["heat_sink"],
      epistemic_type: "FACT",
      timestamp_sec: 1000.0,
      max_age_sec: 60.0,
    };
    const c: ConstraintPrimitive = {
      domain_scope: ["thermal_telemetry"],
      target_objects: ["coolant_loop"],
      protected_set: [],
      protected_values: {},
      min_bounds: { coolant_temp: 200.0 },
      max_bounds: { coolant_temp: 400.0 },
      units: { coolant_temp: "k" },
    };
    const d: DissipatePrimitive = {
      loss_domain: ["heat_sink"],
      target_states: ["coolant_temp"],
      side_effects: [],
      state_delta: { coolant_temp: 10.0 }, // +10 Celsius!
      resource_cost: {},
      units: { coolant_temp: "c" },
    };
    const initialState: SystemState = {
      current_values: { coolant_temp: 300.0 }, // 300 Kelvin
      active_flags: {},
      units: { coolant_temp: "k" },
    };
    const registry: Record<string, EvidenceRecord> = {
      "ev-sensor-temp": {
        evidence_id: "ev-sensor-temp",
        domain: "thermal_telemetry",
        epistemic_status: "FACT",
        timestamp_sec: 1000.0,
      },
    };

    const report = evaluateTriad(s, c, d, initialState, registry, 1000.0);
    assert(report.verdict === "PASS", `Expected PASS, got ${report.verdict}`);
    const simulatedTemp = report.simulated_values?.coolant_temp;
    assert(simulatedTemp !== undefined, "Simulated temperature exists");
    assertClose(simulatedTemp!, 310.0, 1e-6, "300 K + 10 C delta = 310 K");
  });

  // --- 6. Strict fail on bounds unit conversion error (No silent suppression) ---
  test("6.1 Bounds check: Incompatible bound dimension fails strictly with UNIT_CONVERSION_FAILED", () => {
    const s: SourcePrimitive = {
      evidence_id: "ev-pressure",
      authority_domain: ["hydraulic"],
      granted_scope: ["valve_1"],
      granted_loss_domains: ["overflow"],
      epistemic_type: "FACT",
      timestamp_sec: 1000.0,
      max_age_sec: 60.0,
    };
    const c: ConstraintPrimitive = {
      domain_scope: ["hydraulic"],
      target_objects: ["valve_1"],
      protected_set: [],
      protected_values: {},
      min_bounds: { pressure: 10.0 }, // 10 seconds? Incompatible with bar!
      max_bounds: {},
      units: { pressure: "s" }, // Time unit for pressure variable
    };
    const d: DissipatePrimitive = {
      loss_domain: ["overflow"],
      target_states: ["pressure"],
      side_effects: [],
      state_delta: { pressure: 1.0 },
      resource_cost: {},
      units: { pressure: "bar" },
    };
    const initialState: SystemState = {
      current_values: { pressure: 5.0 }, // 5 bar
      active_flags: {},
      units: { pressure: "bar" },
    };
    const registry: Record<string, EvidenceRecord> = {
      "ev-pressure": {
        evidence_id: "ev-pressure",
        domain: "hydraulic",
        epistemic_status: "FACT",
        timestamp_sec: 1000.0,
      },
    };

    const report = evaluateTriad(s, c, d, initialState, registry, 1000.0);
    assert(report.verdict === "FAIL", `Expected FAIL due to unit incompatibility, got ${report.verdict}`);
    const hasDiag = report.diagnostics.some(
      (diag) => diag.code === "UNIT_CONVERSION_FAILED" || diag.code === "UNIT_INCOMPATIBLE"
    );
    assert(hasDiag, "Diagnostics must contain UNIT_CONVERSION_FAILED or UNIT_INCOMPATIBLE");
  });

  console.log("\n=================================================================");
  console.log(`SUMMARY: ${passed} PASSED, ${failed} FAILED`);
  console.log("=================================================================\n");

  if (failed > 0) {
    throw new Error(`${failed} tests failed!`);
  }
}

// Auto-run if executed directly
if (typeof process !== "undefined" && process.argv[1]?.includes("unitsService.test")) {
  runStep1Tests();
}
