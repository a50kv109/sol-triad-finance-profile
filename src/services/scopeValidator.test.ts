/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * Test Suite for Step 3: ScopeValidator, Trust Protection, and Pairwise Diagnostic Purity.
 */

import { ScopeValidator } from "./scopeValidator";
import { evaluateTriad } from "./engineService";
import {
  SourcePrimitive,
  ConstraintPrimitive,
  DissipatePrimitive,
  SystemState,
  EvidenceRecord,
} from "../types/triad";

let passedCount = 0;
let failedCount = 0;

function assert(condition: boolean, testName: string, detail?: string) {
  if (condition) {
    passedCount++;
    console.log(`  ✓ PASS: ${testName}`);
  } else {
    failedCount++;
    console.error(`  ✗ FAIL: ${testName}${detail ? ` - ${detail}` : ""}`);
  }
}

console.log("=== SOL-Triad Step 3: Scope & Diagnostic Purity Verification ===");

const validator = new ScopeValidator();

// 1. Valid Scope Grants Pass
{
  const s: SourcePrimitive = {
    evidence_id: "ev-1",
    authority_domain: ["physics", "thermal"],
    granted_scope: ["valve_1", "heater_2"],
    granted_loss_domains: ["heat_sink"],
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const c: ConstraintPrimitive = {
    domain_scope: ["physics"],
    target_objects: ["valve_1"],
    protected_set: [],
  };
  const d: DissipatePrimitive = {
    loss_domain: ["heat_sink"],
    target_states: [],
    side_effects: [],
  };

  const [ok, verdict, diags] = validator.validate(s, c, d);
  assert(ok === true, "1.1: Valid scope passes validation flag");
  assert(verdict === "PASS", "1.2: Valid scope gives PASS verdict");
  assert(diags.some((diag) => diag.code === "SCOPE_PASS"), "1.3: Emits SCOPE_PASS diagnostic");
}

// 2. Structural Defect: null / undefined fields must FAIL with SCOPE_DEFECT_NONE
{
  const sNullAuth: any = {
    evidence_id: "ev-1",
    authority_domain: null, // structural defect!
    granted_scope: ["valve_1"],
    granted_loss_domains: ["heat_sink"],
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const c: ConstraintPrimitive = { domain_scope: ["physics"], target_objects: ["valve_1"], protected_set: [] };
  const d: DissipatePrimitive = { loss_domain: ["heat_sink"], target_states: [], side_effects: [] };

  const [okAuth, verdictAuth, diagsAuth] = validator.validate(sNullAuth, c, d);
  assert(okAuth === false, "2.1: null authority_domain fails validation");
  assert(verdictAuth === "FAIL", "2.2: null authority_domain produces FAIL verdict");
  assert(diagsAuth.some((diag) => diag.code === "SCOPE_DEFECT_NONE" && diag.field_name === "authority_domain"), "2.3: SCOPE_DEFECT_NONE emitted for authority_domain");

  const sUndefScope: any = {
    evidence_id: "ev-1",
    authority_domain: ["physics"],
    granted_scope: undefined, // structural defect!
    granted_loss_domains: ["heat_sink"],
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const [okScope, verdictScope, diagsScope] = validator.validate(sUndefScope, c, d);
  assert(okScope === false, "2.4: undefined granted_scope fails validation");
  assert(verdictScope === "FAIL", "2.5: undefined granted_scope produces FAIL verdict");
  assert(diagsScope.some((diag) => diag.code === "SCOPE_DEFECT_NONE" && diag.field_name === "granted_scope"), "2.6: SCOPE_DEFECT_NONE emitted for granted_scope");

  const sNullLoss: any = {
    evidence_id: "ev-1",
    authority_domain: ["physics"],
    granted_scope: ["valve_1"],
    granted_loss_domains: null, // structural defect!
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const [okLoss, verdictLoss, diagsLoss] = validator.validate(sNullLoss, c, d);
  assert(okLoss === false, "2.7: null granted_loss_domains fails validation");
  assert(verdictLoss === "FAIL", "2.8: null granted_loss_domains produces FAIL verdict");
  assert(diagsLoss.some((diag) => diag.code === "SCOPE_DEFECT_NONE" && diag.field_name === "granted_loss_domains"), "2.9: SCOPE_DEFECT_NONE emitted for granted_loss_domains");
}

// 3. Zero-Privilege Grant ([]) Semantics
{
  // 3a. Zero privileges granted, and zero requested -> Valid PASS (not defect)
  const sZero: SourcePrimitive = {
    evidence_id: "ev-1",
    authority_domain: [], // Valid explicit grant: 0 privileges
    granted_scope: [],
    granted_loss_domains: [],
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const cZero: ConstraintPrimitive = { domain_scope: [], target_objects: [], protected_set: [] };
  const dZero: DissipatePrimitive = { loss_domain: [], target_states: [], side_effects: [] };

  const [okZero, verdictZero, diagsZero] = validator.validate(sZero, cZero, dZero);
  assert(okZero === true, "3.1: Zero privileges with zero requests is valid");
  assert(verdictZero === "PASS", "3.2: Zero privileges with zero requests passes");
  assert(!diagsZero.some((diag) => diag.code === "SCOPE_DEFECT_NONE"), "3.3: Empty array is NOT treated as SCOPE_DEFECT_NONE");

  // 3b. Zero privileges granted, but action requested -> Rejection with SCOPE_EXCEEDED_*
  const cReq: ConstraintPrimitive = {
    domain_scope: ["physics"],
    target_objects: ["valve_1"],
    protected_set: [],
  };
  const dReq: DissipatePrimitive = {
    loss_domain: ["heat_sink"],
    target_states: [],
    side_effects: [],
  };
  const [okExceeded, verdictExceeded, diagsExceeded] = validator.validate(sZero, cReq, dReq);
  assert(okExceeded === false, "3.4: Zero privileges reject non-empty requests");
  assert(verdictExceeded === "FAIL", "3.5: Rejection produces FAIL verdict");
  const exceededCodes = new Set(diagsExceeded.map((diag) => diag.code));
  assert(exceededCodes.has("SCOPE_EXCEEDED_DOMAIN"), "3.6: SCOPE_EXCEEDED_DOMAIN caught");
  assert(exceededCodes.has("SCOPE_EXCEEDED_OBJECTS"), "3.7: SCOPE_EXCEEDED_OBJECTS caught");
  assert(exceededCodes.has("SCOPE_EXCEEDED_LOSS"), "3.8: SCOPE_EXCEEDED_LOSS caught");
}

// 4. Unauthorized Loss Domain Isolation
{
  const s: SourcePrimitive = {
    evidence_id: "ev-1",
    authority_domain: ["physics"],
    granted_scope: ["valve_1"],
    granted_loss_domains: ["safe_cooling"],
    epistemic_type: "FACT",
    timestamp_sec: 100.0,
    max_age_sec: 60.0,
  };
  const c: ConstraintPrimitive = {
    domain_scope: ["physics"],
    target_objects: ["valve_1"],
    protected_set: [],
  };
  const d: DissipatePrimitive = {
    loss_domain: ["destructive_venting"], // unauthorized loss domain!
    target_states: [],
    side_effects: [],
  };

  const [okLoss, verdictLoss, diagsLoss] = validator.validate(s, c, d);
  assert(okLoss === false, "4.1: Unauthorized loss domain fails validation");
  assert(verdictLoss === "FAIL", "4.2: Unauthorized loss domain produces FAIL verdict");
  assert(diagsLoss.some((diag) => diag.code === "SCOPE_EXCEEDED_LOSS"), "4.3: Emits SCOPE_EXCEEDED_LOSS");
}

// 5. Pairwise Diagnostic Purity & Sub-Check Independence in evaluateTriad
{
  const baseClock = 1000.0;
  const registry: Record<string, EvidenceRecord> = {
    "ev-valid": {
      evidence_id: "ev-valid",
      domain: "power_grid",
      epistemic_status: "FACT",
      timestamp_sec: baseClock - 5.0,
    },
  };

  // Case 5A: Pure State Invariant Breach (P_CD fails, but P_SC and P_SD must be PASS and FREE of state diags)
  const sValid: SourcePrimitive = {
    evidence_id: "ev-valid",
    authority_domain: ["power_grid"],
    granted_scope: ["line_1"],
    granted_loss_domains: ["joule_heat"],
    epistemic_type: "FACT",
    timestamp_sec: baseClock - 5.0,
    max_age_sec: 60.0,
  };
  const cStateBreach: ConstraintPrimitive = {
    domain_scope: ["power_grid"],
    target_objects: ["line_1"],
    protected_set: [],
    min_bounds: { voltage: 200.0 },
  };
  const dStateBreach: DissipatePrimitive = {
    loss_domain: ["joule_heat"],
    target_states: [],
    side_effects: [],
    state_delta: { voltage: -50.0 }, // 220 - 50 = 170 < 200 min_bound!
  };
  const initState: SystemState = {
    current_values: { voltage: 220.0 },
    active_flags: {},
    units: {},
  };

  const reportA = evaluateTriad(sValid, cStateBreach, dStateBreach, initState, registry, baseClock);
  assert(reportA.verdict === "FAIL", "5.1: Overall verdict FAIL when state bound breached");
  assert(reportA.pairwise_checks.P_SC.verdict === "PASS", "5.2: P_SC is PASS despite state breach");
  assert(reportA.pairwise_checks.P_SC.is_valid === true, "5.3: P_SC is valid");
  assert(reportA.pairwise_checks.P_SC.diagnostics.length === 0, "5.4: P_SC diagnostics are pure (no state leaks)");
  assert(reportA.pairwise_checks.P_SD.verdict === "PASS", "5.5: P_SD is PASS");
  assert(reportA.pairwise_checks.P_SD.diagnostics.length === 0, "5.6: P_SD diagnostics are pure");
  assert(reportA.pairwise_checks.P_CD.verdict === "FAIL", "5.7: P_CD is FAIL due to state bound breach");
  assert(reportA.pairwise_checks.P_CD.diagnostics.some((d) => d.code === "STATE_MIN_BOUND_BREACH"), "5.8: P_CD contains STATE_MIN_BOUND_BREACH");

  // Case 5B: Pure Scope Breach (P_SC fails due to unauthorized target_objects, but P_CD is PASS)
  const cScopeBreach: ConstraintPrimitive = {
    domain_scope: ["power_grid"],
    target_objects: ["nuclear_core"], // UNAUTHORIZED TARGET OBJECT
    protected_set: [],
    min_bounds: { voltage: 200.0 },
  };
  const dNoMutation: DissipatePrimitive = {
    loss_domain: ["joule_heat"],
    target_states: [],
    side_effects: [],
    state_delta: {},
  };

  const reportB = evaluateTriad(sValid, cScopeBreach, dNoMutation, initState, registry, baseClock);
  assert(reportB.verdict === "FAIL", "5.9: Overall verdict FAIL when scope is unauthorized");
  assert(reportB.pairwise_checks.P_SC.verdict === "FAIL", "5.10: P_SC is FAIL");
  assert(reportB.pairwise_checks.P_SC.diagnostics.some((d) => d.code === "SCOPE_EXCEEDED_OBJECTS"), "5.11: P_SC contains SCOPE_EXCEEDED_OBJECTS");
  assert(reportB.pairwise_checks.P_CD.verdict === "PASS", "5.12: P_CD is PASS despite scope failure");
  assert(reportB.pairwise_checks.P_CD.is_valid === true, "5.13: P_CD is_valid is true");
  assert(!reportB.pairwise_checks.P_CD.diagnostics.some((d) => d.code === "SCOPE_EXCEEDED_OBJECTS"), "5.14: P_CD diagnostics do NOT contain scope errors");

  // Case 5C: Pure Loss Domain Breach (P_SD fails, but P_SC and P_CD are PASS)
  const dLossBreach: DissipatePrimitive = {
    loss_domain: ["explosive_decompression"], // UNAUTHORIZED LOSS DOMAIN
    target_states: [],
    side_effects: [],
    state_delta: {},
  };
  const cOk: ConstraintPrimitive = {
    domain_scope: ["power_grid"],
    target_objects: ["line_1"],
    protected_set: [],
    min_bounds: { voltage: 200.0 },
  };

  const reportC = evaluateTriad(sValid, cOk, dLossBreach, initState, registry, baseClock);
  assert(reportC.verdict === "FAIL", "5.15: Overall verdict FAIL when loss domain unauthorized");
  assert(reportC.pairwise_checks.P_SD.verdict === "FAIL", "5.16: P_SD is FAIL");
  assert(reportC.pairwise_checks.P_SD.diagnostics.some((d) => d.code === "SCOPE_EXCEEDED_LOSS"), "5.17: P_SD contains SCOPE_EXCEEDED_LOSS");
  assert(reportC.pairwise_checks.P_SC.verdict === "PASS", "5.18: P_SC is PASS");
  assert(!reportC.pairwise_checks.P_SC.diagnostics.some((d) => d.code === "SCOPE_EXCEEDED_LOSS"), "5.19: P_SC does NOT contain loss domain errors");
  assert(reportC.pairwise_checks.P_CD.verdict === "PASS", "5.20: P_CD is PASS");
}

console.log(`\nResults: ${passedCount} passed, ${failedCount} failed.`);
if (failedCount > 0) {
  process.exit(1);
} else {
  console.log("ALL STEP 3 TESTS PASSED PERFECTLY!");
}
