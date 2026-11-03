/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * State & Invariants Validator (P_CD Integrity).
 *
 * Implements exact parity with Python reference kernel:
 *   (sol_triad/validators.py:StateValidator v0.4.1)
 *
 * Enforces:
 *   1. Pre-simulation fatal validation (NaN/Inf, negative cost, protected_set mutation, unit incompatibility):
 *      Immediate fail-closed termination returning empty simulated_values {} and simulated_flags {}.
 *   2. Terminal state simulation with affine-aware / difference-aware conversions (convert / convertDelta).
 *   3. Strict protection of protected_flags:
 *      Prohibits applying illegal flag_delta mutations and preserves initial flag values.
 *   4. Elimination of duplicate UNIT_INCOMPATIBLE diagnostics.
 *   5. Invariant enforcement: required vars, forbidden flags, required flags, protected values, min/max bounds.
 */

import {
  ConstraintPrimitive,
  DissipatePrimitive,
  SystemState,
  CoherenceVerdict,
  CoherenceDiagnostic,
} from "../types/triad";
import { UnitRegistry, DimensionalityError, UnknownUnitError } from "./unitsService";

export class StateValidator {
  public validate(
    c: ConstraintPrimitive,
    d: DissipatePrimitive,
    initialState: SystemState
  ): [
    boolean,
    CoherenceVerdict,
    CoherenceDiagnostic[],
    Record<string, number>,
    Record<string, boolean>
  ] {
    const diagnostics: CoherenceDiagnostic[] = [];
    let simulatedValues: Record<string, number> = {};
    let simulatedFlags: Record<string, boolean> = {};

    // 1. Numeric Sanity Checks (Reject NaN, Inf)
    const allNumericDicts: [
      string,
      Record<string, number> | undefined,
      "DISSIPATE" | "CONSTRAINT"
    ][] = [
      ["initial_state.current_values", initialState.current_values, "CONSTRAINT"],
      ["dissipate.state_delta", d.state_delta, "DISSIPATE"],
      ["dissipate.resource_cost", d.resource_cost, "DISSIPATE"],
      ["constraint.min_bounds", c.min_bounds, "CONSTRAINT"],
      ["constraint.max_bounds", c.max_bounds, "CONSTRAINT"],
      ["constraint.protected_values", c.protected_values, "CONSTRAINT"],
    ];

    for (const [dictName, ndict, prim] of allNumericDicts) {
      if (!ndict) continue;
      for (const [k, val] of Object.entries(ndict)) {
        if (isNaN(val) || !isFinite(val)) {
          diagnostics.push({
            code: "STATE_INVALID_NUMERIC",
            severity: "ERROR",
            message: `Non-finite numeric value (${val}) detected in '${dictName}' for key '${k}'.`,
            primitive: prim,
            field_name: k,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 2. Resource Cost Sanity (No negative resource costs)
    if (d.resource_cost) {
      for (const [resName, cost] of Object.entries(d.resource_cost)) {
        if (cost < 0.0) {
          diagnostics.push({
            code: "STATE_NEGATIVE_RESOURCE_COST",
            severity: "ERROR",
            message: `Negative resource cost (${cost}) for '${resName}' is forbidden.`,
            primitive: "DISSIPATE",
            field_name: resName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 3. Unified Mutation Vectors vs Protected Set
    const allModifiedParams = new Set<string>([
      ...(d.target_states || []),
      ...(d.side_effects || []),
      ...Object.keys(d.state_delta || {}),
      ...Object.keys(d.resource_cost || {}),
      ...Object.keys(d.flag_delta || {}),
    ]);

    const protSet = new Set(c.protected_set || []);
    const protectedIntersection = [...allModifiedParams]
      .filter((p) => protSet.has(p))
      .sort();

    if (protectedIntersection.length > 0) {
      diagnostics.push({
        code: "STATE_PROTECTED_PARAM_MUTATED",
        severity: "ERROR",
        message: `Dissipation mutates protected parameters: [${protectedIntersection.join(", ")}].`,
        primitive: "DISSIPATE",
        field_name: "protected_set",
      });
      return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
    }

    // 4. Dimensionality & Unit Compatibility Checks (Stop on first mismatch to avoid duplicates)
    for (const param of allModifiedParams) {
      const dUnit = d.units?.[param];
      const cUnit = c.units?.[param];
      const sUnit = initialState.units?.[param];

      // Check D vs C unit
      if (dUnit || cUnit) {
        const [compDC, msgDC] = UnitRegistry.areCompatible(dUnit, cUnit);
        if (!compDC) {
          diagnostics.push({
            code: "UNIT_INCOMPATIBLE",
            severity: "ERROR",
            message: `Unit mismatch for param '${param}' between Dissipate ('${dUnit}') and Constraint ('${cUnit}'): ${msgDC}`,
            primitive: "DISSIPATE",
            field_name: param,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }

      // Check D vs S unit
      if (dUnit || sUnit) {
        const [compDS, msgDS] = UnitRegistry.areCompatible(dUnit, sUnit);
        if (!compDS) {
          diagnostics.push({
            code: "UNIT_INCOMPATIBLE",
            severity: "ERROR",
            message: `Unit mismatch for param '${param}' between Dissipate ('${dUnit}') and SystemState ('${sUnit}'): ${msgDS}`,
            primitive: "DISSIPATE",
            field_name: param,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 5. Terminal State Simulation: Numerical Values
    simulatedValues = { ...initialState.current_values };

    // Apply state deltas (with convertDelta for differences)
    if (d.state_delta) {
      for (const [varName, rawDelta] of Object.entries(d.state_delta)) {
        const baseUnit = initialState.units?.[varName];
        const deltaUnit = d.units?.[varName];
        let effectiveDelta = rawDelta;
        if (deltaUnit && baseUnit && deltaUnit.toLowerCase() !== baseUnit.toLowerCase()) {
          try {
            effectiveDelta = UnitRegistry.convertDelta(rawDelta, deltaUnit, baseUnit);
          } catch (err) {
            diagnostics.push({
              code: "UNIT_CONVERSION_FAILED",
              severity: "ERROR",
              message: `Failed to convert delta for '${varName}' from '${deltaUnit}' to '${baseUnit}': ${(err as Error).message}`,
              primitive: "DISSIPATE",
              field_name: varName,
            });
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }
        simulatedValues[varName] = (simulatedValues[varName] ?? 0.0) + effectiveDelta;
      }
    }

    // Apply resource costs (subtracted; temperature costs converted as delta)
    if (d.resource_cost) {
      for (const [varName, rawCost] of Object.entries(d.resource_cost)) {
        const baseUnit = initialState.units?.[varName];
        const costUnit = d.units?.[varName];
        let effectiveCost = rawCost;
        if (costUnit && baseUnit && costUnit.toLowerCase() !== baseUnit.toLowerCase()) {
          try {
            if (UnitRegistry.getDimension(costUnit) === "temperature") {
              effectiveCost = UnitRegistry.convertDelta(rawCost, costUnit, baseUnit);
            } else {
              effectiveCost = UnitRegistry.convert(rawCost, costUnit, baseUnit);
            }
          } catch (err) {
            diagnostics.push({
              code: "UNIT_CONVERSION_FAILED",
              severity: "ERROR",
              message: `Failed to convert resource cost for '${varName}' from '${costUnit}' to '${baseUnit}': ${(err as Error).message}`,
              primitive: "DISSIPATE",
              field_name: varName,
            });
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }
        const currentVal = simulatedValues[varName] ?? 0.0;
        simulatedValues[varName] = currentVal - effectiveCost;
      }
    }

    // 6. Terminal State Simulation: Flags (Strict rollback on protected flag mutation)
    simulatedFlags = { ...initialState.active_flags };
    if (d.flag_delta) {
      const protectedFlags = new Set(c.protected_flags || []);
      for (const [flagName, newVal] of Object.entries(d.flag_delta)) {
        if (protectedFlags.has(flagName)) {
          const initialVal = initialState.active_flags?.[flagName] ?? false;
          if (initialVal !== newVal) {
            diagnostics.push({
              code: "STATE_PROTECTED_FLAG_MUTATED",
              severity: "ERROR",
              message: `Flag '${flagName}' is in protected_flags and cannot be mutated from ${initialVal} to ${newVal}.`,
              primitive: "CONSTRAINT",
              field_name: flagName,
            });
            // Stop immediately and preserve initial flags without applying the illegal mutation
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }
        simulatedFlags[flagName] = newVal;
      }
    }

    // 7. Check Missing Variables (Fail-Closed)
    const requiredVars = new Set<string>([
      ...Object.keys(c.min_bounds || {}),
      ...Object.keys(c.max_bounds || {}),
      ...Object.keys(c.protected_values || {}),
    ]);
    const missingVars = [...requiredVars]
      .filter((v) => !(v in simulatedValues))
      .sort();

    if (missingVars.length > 0) {
      diagnostics.push({
        code: "STATE_MISSING_VAR",
        severity: "ERROR",
        message: `Missing required state variables in terminal simulation: [${missingVars.join(", ")}].`,
        primitive: "CONSTRAINT",
        field_name: "required_variables",
      });
      return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
    }

    // 8. Flag Invariants (Forbidden & Required flags)
    if (c.forbidden_flags) {
      for (const [flagName, forbiddenVal] of Object.entries(c.forbidden_flags)) {
        const activeVal = simulatedFlags[flagName] ?? false;
        if (activeVal === forbiddenVal) {
          diagnostics.push({
            code: "STATE_FORBIDDEN_FLAG_ACTIVE",
            severity: "ERROR",
            message: `Terminal state flag '${flagName}' holds forbidden value (${forbiddenVal}).`,
            primitive: "CONSTRAINT",
            field_name: flagName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    if (c.required_flags) {
      for (const [flagName, requiredVal] of Object.entries(c.required_flags)) {
        const activeVal = simulatedFlags[flagName] ?? false;
        if (activeVal !== requiredVal) {
          diagnostics.push({
            code: "STATE_REQUIRED_FLAG_MISSING",
            severity: "ERROR",
            message: `Terminal state flag '${flagName}' is ${activeVal}, but required to be ${requiredVal}.`,
            primitive: "CONSTRAINT",
            field_name: flagName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 9. Invariant Enforcement: Protected Values
    if (c.protected_values) {
      for (const [varName, expectedVal] of Object.entries(c.protected_values)) {
        const simVal = simulatedValues[varName];
        const cU = c.units?.[varName];
        const sU = initialState.units?.[varName];
        let effExpected = expectedVal;
        if (cU && sU && cU.toLowerCase() !== sU.toLowerCase()) {
          try {
            effExpected = UnitRegistry.convert(expectedVal, cU, sU);
          } catch (err) {
            diagnostics.push({
              code: "UNIT_CONVERSION_FAILED",
              severity: "ERROR",
              message: `Failed to convert protected_value for '${varName}': ${(err as Error).message}`,
              primitive: "CONSTRAINT",
              field_name: varName,
            });
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }

        if (Math.abs(simVal - effExpected) > 1e-9) {
          diagnostics.push({
            code: "STATE_PROTECTED_VALUE_VIOLATED",
            severity: "ERROR",
            message: `Protected value for '${varName}' violated: simulated ${simVal.toFixed(4)} != expected ${effExpected.toFixed(4)}.`,
            primitive: "CONSTRAINT",
            field_name: varName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 10. Bounds Checks (min_bounds & max_bounds)
    if (c.min_bounds) {
      for (const [varName, minBound] of Object.entries(c.min_bounds)) {
        const simVal = simulatedValues[varName];
        const cU = c.units?.[varName];
        const sU = initialState.units?.[varName];
        let effMin = minBound;
        if (cU && sU && cU.toLowerCase() !== sU.toLowerCase()) {
          try {
            effMin = UnitRegistry.convert(minBound, cU, sU);
          } catch (err) {
            diagnostics.push({
              code: "UNIT_CONVERSION_FAILED",
              severity: "ERROR",
              message: `Failed to convert min_bound for '${varName}': ${(err as Error).message}`,
              primitive: "CONSTRAINT",
              field_name: varName,
            });
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }

        if (simVal < effMin) {
          diagnostics.push({
            code: "STATE_MIN_BOUND_BREACH",
            severity: "ERROR",
            message: `Variable '${varName}' (${simVal.toFixed(4)}) falls below min_bound (${effMin.toFixed(4)}).`,
            primitive: "CONSTRAINT",
            field_name: varName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    if (c.max_bounds) {
      for (const [varName, maxBound] of Object.entries(c.max_bounds)) {
        const simVal = simulatedValues[varName];
        const cU = c.units?.[varName];
        const sU = initialState.units?.[varName];
        let effMax = maxBound;
        if (cU && sU && cU.toLowerCase() !== sU.toLowerCase()) {
          try {
            effMax = UnitRegistry.convert(maxBound, cU, sU);
          } catch (err) {
            diagnostics.push({
              code: "UNIT_CONVERSION_FAILED",
              severity: "ERROR",
              message: `Failed to convert max_bound for '${varName}': ${(err as Error).message}`,
              primitive: "CONSTRAINT",
              field_name: varName,
            });
            return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
          }
        }

        if (simVal > effMax) {
          diagnostics.push({
            code: "STATE_MAX_BOUND_BREACH",
            severity: "ERROR",
            message: `Variable '${varName}' (${simVal.toFixed(4)}) exceeds max_bound (${effMax.toFixed(4)}).`,
            primitive: "CONSTRAINT",
            field_name: varName,
          });
          return [false, "FAIL", diagnostics, simulatedValues, simulatedFlags];
        }
      }
    }

    // 11. All Checks Satisfied
    diagnostics.push({
      code: "STATE_PASS",
      severity: "INFO",
      message: "State simulation and invariant checks satisfied.",
      primitive: "STATE",
    });

    return [true, "PASS", diagnostics, simulatedValues, simulatedFlags];
  }
}
