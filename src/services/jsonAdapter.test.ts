/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * Test Suite for Step 4: JSON Adapter and Strict Schema Validation.
 *
 * Verifies parity with Python sol_triad/adapter.py v0.4.1 and schemas/
 */

import { SolTriadJsonAdapter } from "./jsonAdapter";
import { InMemoryEvidenceRegistry } from "./evidenceValidator";
import { EvidenceRecord } from "../types/triad";

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

console.log("=== SOL-Triad Step 4: JSON Adapter & Strict Schema Verification ===");

const currentTime = 1740000000.0;

function createSampleRegistry(): InMemoryEvidenceRegistry {
  const reg = new InMemoryEvidenceRegistry();
  reg.register({
    evidence_id: "ev-sensor-100",
    domain: "thermal_control",
    epistemic_status: "FACT",
    timestamp_sec: currentTime - 10.0,
    payload_hash: "sha256-hash-ok",
  });
  return reg;
}

function getBaseValidRequest(): Record<string, any> {
  return {
    request_id: "test-req-001",
    protocol_version: "0.4.0",
    engine_version: "0.4.1",
    source: {
      evidence_id: "ev-sensor-100",
      authority_domain: ["thermal_control"],
      granted_scope: ["pump_alpha"],
      granted_loss_domains: ["thermal_entropy"],
      epistemic_type: "FACT",
      timestamp_sec: currentTime - 10.0,
      max_age_sec: 300.0,
      payload_hash: "sha256-hash-ok",
    },
    constraint: {
      domain_scope: ["thermal_control"],
      target_objects: ["pump_alpha"],
      protected_set: ["emergency_valve"],
      max_bounds: { coolant_pressure: 10.0 },
      min_bounds: { coolant_pressure: 0.5 },
      units: { coolant_pressure: "bar" },
    },
    dissipate: {
      loss_domain: ["thermal_entropy"],
      target_states: ["coolant_flowing"],
      side_effects: ["pipe_vibration"],
      resource_cost: {},
      state_delta: { coolant_pressure: 1.5 },
      units: { coolant_pressure: "bar" },
    },
    initial_state: {
      current_values: { coolant_pressure: 3.0 },
      active_flags: {},
      units: { coolant_pressure: "bar" },
    },
  };
}

const registry = createSampleRegistry();
const adapter = new SolTriadJsonAdapter(registry);

// 1. Valid JSON Request Passes and Matches Schema Structure
{
  const req = getBaseValidRequest();
  const res: any = adapter.evaluateJson(req, undefined, currentTime);

  assert(res.request_id === "test-req-001", "1.1: request_id echoed");
  assert(res.protocol_version === "0.4.0", "1.2: protocol_version is 0.4.0");
  assert(res.engine_version === "0.4.1", "1.3: engine_version is 0.4.1");
  assert(res.verdict === "PASS", "1.4: verdict is PASS");
  assert(res.simulated_values.coolant_pressure === 4.5, "1.5: simulated coolant_pressure 3.0 + 1.5 = 4.5");
  assert(res.pairwise_checks.P_SC.is_valid === true, "1.6: P_SC is valid");
  assert(res.pairwise_checks.P_CD.is_valid === true, "1.7: P_CD is valid");
  assert(res.pairwise_checks.P_SD.is_valid === true, "1.8: P_SD is valid");
  assert(res.diagnostics.length > 0, "1.9: diagnostics list populated");
  assert(res.diagnostics.some((d: any) => d.code === "STATE_PASS"), "1.10: STATE_PASS present");
  assert(Array.isArray(res.messages), "1.11: messages is an array of strings");
  assert(typeof res.evaluation_timestamp === "number", "1.12: evaluation_timestamp is number");

  // String JSON input parsing
  const strReq = JSON.stringify(req);
  const strRes: any = adapter.evaluateJson(strReq, undefined, currentTime);
  assert(strRes.verdict === "PASS", "1.13: JSON string input evaluates to PASS");
}

// 2. Missing Required Fields Fails Closed
{
  // Missing request_id
  const reqNoId = getBaseValidRequest();
  delete reqNoId.request_id;
  const resNoId: any = adapter.evaluateJson(reqNoId, undefined, currentTime);
  assert(resNoId.verdict === "FAIL", "2.1: Missing request_id produces FAIL");
  assert(resNoId.request_id === "missing_request_id", "2.2: request_id set to missing_request_id");
  assert(resNoId.diagnostics[0].code === "STRUCTURAL_DEFECT", "2.3: Diagnostic code is STRUCTURAL_DEFECT");

  // Missing source
  const reqNoSource = getBaseValidRequest();
  delete reqNoSource.source;
  const resNoSource: any = adapter.evaluateJson(reqNoSource, undefined, currentTime);
  assert(resNoSource.verdict === "FAIL", "2.4: Missing source produces FAIL");
  assert(resNoSource.diagnostics[0].field_name === "source", "2.5: Diagnosed on field_name source");

  // Missing constraint
  const reqNoConstraint = getBaseValidRequest();
  delete reqNoConstraint.constraint;
  const resNoConstraint: any = adapter.evaluateJson(reqNoConstraint, undefined, currentTime);
  assert(resNoConstraint.verdict === "FAIL", "2.6: Missing constraint produces FAIL");

  // Missing dissipate
  const reqNoDissipate = getBaseValidRequest();
  delete reqNoDissipate.dissipate;
  const resNoDissipate: any = adapter.evaluateJson(reqNoDissipate, undefined, currentTime);
  assert(resNoDissipate.verdict === "FAIL", "2.7: Missing dissipate produces FAIL");

  // Missing initial_state
  const reqNoInit = getBaseValidRequest();
  delete reqNoInit.initial_state;
  const resNoInit: any = adapter.evaluateJson(reqNoInit, undefined, currentTime);
  assert(resNoInit.verdict === "FAIL", "2.8: Missing initial_state produces FAIL");
}

// 3. Invalid Field Types & Strict Numeric/Boolean Validation
{
  // Non-finite number (NaN / Infinity)
  const reqBadNum = getBaseValidRequest();
  reqBadNum.source.timestamp_sec = NaN;
  const resBadNum: any = adapter.evaluateJson(reqBadNum, undefined, currentTime);
  assert(resBadNum.verdict === "FAIL", "3.1: NaN timestamp produces FAIL");
  assert(resBadNum.diagnostics[0].code === "STRUCTURAL_DEFECT", "3.2: NaN produces STRUCTURAL_DEFECT");

  // Coerced string boolean ("false" instead of false)
  const reqBadBool = getBaseValidRequest();
  reqBadBool.initial_state.active_flags = { enabled: "false" };
  const resBadBool: any = adapter.evaluateJson(reqBadBool, undefined, currentTime);
  assert(resBadBool.verdict === "FAIL", "3.3: String 'false' instead of boolean produces FAIL");
  assert(resBadBool.diagnostics[0].message.includes("must be a boolean"), "3.4: Message indicates boolean required");

  // Number instead of string
  const reqBadType = getBaseValidRequest();
  reqBadType.source.evidence_id = 12345;
  const resBadType: any = adapter.evaluateJson(reqBadType, undefined, currentTime);
  assert(resBadType.verdict === "FAIL", "3.5: Number as evidence_id produces FAIL");
}

// 4. Invalid Enum Values
{
  const reqBadEnum = getBaseValidRequest();
  reqBadEnum.source.epistemic_type = "INVALID_STATUS";
  const resBadEnum: any = adapter.evaluateJson(reqBadEnum, undefined, currentTime);
  assert(resBadEnum.verdict === "FAIL", "4.1: Invalid epistemic_type produces FAIL");
  assert(resBadEnum.diagnostics[0].message.includes("Invalid source.epistemic_type"), "4.2: Diagnostic identifies invalid epistemic_type");
}

// 5. Unsupported Protocol Version
{
  const reqBadProto = getBaseValidRequest();
  reqBadProto.protocol_version = "99.0.0";
  const resBadProto: any = adapter.evaluateJson(reqBadProto, undefined, currentTime);
  assert(resBadProto.verdict === "FAIL", "5.1: Unsupported protocol_version 99.0.0 produces FAIL");
  assert(resBadProto.diagnostics[0].message.includes("Unsupported protocol_version '99.0.0'"), "5.2: Diagnostic lists supported versions");
}

// 6. Malformed JSON String & Non-Object Request Shape
{
  // Syntax error in JSON string
  const resSyntax: any = adapter.evaluateJson('{"request_id": "test", "unclosed...', undefined, currentTime);
  assert(resSyntax.verdict === "FAIL", "6.1: Malformed JSON string produces FAIL");
  assert(resSyntax.request_id === "malformed_json", "6.2: request_id set to malformed_json");
  assert(resSyntax.diagnostics[0].code === "STRUCTURAL_DEFECT", "6.3: Malformed JSON code is STRUCTURAL_DEFECT");

  // Non-object JSON (array)
  const resArray: any = adapter.evaluateJson('["not", "an", "object"]', undefined, currentTime);
  assert(resArray.verdict === "FAIL", "6.4: JSON array request produces FAIL");
  assert(resArray.request_id === "invalid_request_shape", "6.5: request_id set to invalid_request_shape");

  // Primitive string as input
  const resPrim: any = adapter.evaluateJson(12345, undefined, currentTime);
  assert(resPrim.verdict === "FAIL", "6.6: Primitive number input produces FAIL");
  assert(resPrim.request_id === "invalid_input_type", "6.7: request_id set to invalid_input_type");
}

// 7. Invalid Arrays & Nested Objects
{
  // Array of numbers where array of strings expected
  const reqBadArr = getBaseValidRequest();
  reqBadArr.constraint.domain_scope = [123, 456];
  const resBadArr: any = adapter.evaluateJson(reqBadArr, undefined, currentTime);
  assert(resBadArr.verdict === "FAIL", "7.1: Number array in domain_scope produces FAIL");
  assert(resBadArr.diagnostics[0].message.includes("must be an array of strings"), "7.2: Diagnostic requires array of strings");

  // Non-object for source
  const reqBadObj = getBaseValidRequest();
  reqBadObj.source = "invalid_source";
  const resBadObj: any = adapter.evaluateJson(reqBadObj, undefined, currentTime);
  assert(resBadObj.verdict === "FAIL", "7.3: Non-object source produces FAIL");
}

// 8. Distinction between null (Defect) and [] (Zero Privileges)
{
  // 8a: null authority_domain -> SCOPE_DEFECT_NONE (FAIL)
  const reqNull = getBaseValidRequest();
  reqNull.source.authority_domain = null;
  const resNull: any = adapter.evaluateJson(reqNull, undefined, currentTime);
  assert(resNull.verdict === "FAIL", "8.1: null authority_domain produces FAIL");
  assert(resNull.diagnostics.some((d: any) => d.code === "SCOPE_DEFECT_NONE"), "8.2: Emits SCOPE_DEFECT_NONE");

  // 8b: empty array [] authority_domain with non-empty constraint domain -> SCOPE_EXCEEDED_DOMAIN (FAIL)
  const reqEmpty = getBaseValidRequest();
  reqEmpty.source.authority_domain = [];
  const resEmpty: any = adapter.evaluateJson(reqEmpty, undefined, currentTime);
  assert(resEmpty.verdict === "FAIL", "8.3: Empty array authority_domain rejects non-empty domain");
  assert(resEmpty.diagnostics.some((d: any) => d.code === "SCOPE_EXCEEDED_DOMAIN"), "8.4: Emits SCOPE_EXCEEDED_DOMAIN");
  assert(!resEmpty.diagnostics.some((d: any) => d.code === "SCOPE_DEFECT_NONE"), "8.5: Empty array does NOT emit SCOPE_DEFECT_NONE");

  // 8c: Zero target and loss privileges with matching domain and zero requests -> PASS
  const zeroReg = new InMemoryEvidenceRegistry();
  zeroReg.register({
    evidence_id: "ev-zero-001",
    domain: "public",
    epistemic_status: "FACT",
    timestamp_sec: currentTime - 10.0,
  });
  const reqZeroValid = getBaseValidRequest();
  reqZeroValid.source.evidence_id = "ev-zero-001";
  reqZeroValid.source.authority_domain = ["public"];
  reqZeroValid.source.granted_scope = []; // Zero target objects granted!
  reqZeroValid.source.granted_loss_domains = []; // Zero loss domains granted!
  delete reqZeroValid.source.payload_hash;
  reqZeroValid.constraint.domain_scope = ["public"];
  reqZeroValid.constraint.target_objects = []; // Zero target objects requested!
  reqZeroValid.dissipate.loss_domain = []; // Zero loss domains requested!
  const resZeroValid: any = adapter.evaluateJson(reqZeroValid, zeroReg, currentTime);
  assert(resZeroValid.verdict === "PASS", "8.6: Zero object/loss privileges with zero requests evaluates to PASS");
}

// 9. Schema Errors Differentiate from Runtime Engine Failures
{
  // Runtime bound breach: schema is 100% valid, but physics/invariants fail
  const reqBreach = getBaseValidRequest();
  reqBreach.constraint.min_bounds.coolant_pressure = 5.0; // Simulated terminal is 4.5 < 5.0
  const resBreach: any = adapter.evaluateJson(reqBreach, undefined, currentTime);
  assert(resBreach.verdict === "FAIL", "9.1: Bound breach produces FAIL");
  assert(resBreach.diagnostics.some((d: any) => d.code === "STATE_MIN_BOUND_BREACH"), "9.2: Emits STATE_MIN_BOUND_BREACH");
  assert(!resBreach.diagnostics.some((d: any) => d.code === "STRUCTURAL_DEFECT"), "9.3: Does NOT emit STRUCTURAL_DEFECT");
  assert(resBreach.pairwise_checks.P_SC.verdict === "PASS", "9.4: P_SC is PASS despite P_CD bound failure");
  assert(resBreach.pairwise_checks.P_CD.verdict === "FAIL", "9.5: P_CD is FAIL due to bound breach");
}

// 10. Output Response Conforms to sol_triad_response.schema.json
{
  const req = getBaseValidRequest();
  const res: any = adapter.evaluateJson(req, undefined, currentTime);
  const requiredKeys = [
    "request_id",
    "protocol_version",
    "engine_version",
    "verdict",
    "pairwise_checks",
    "diagnostics",
    "simulated_values",
    "simulated_flags",
    "evaluation_timestamp",
  ];
  for (const k of requiredKeys) {
    assert(k in res, `10.1: Response has required key '${k}'`);
  }
  assert("P_SC" in res.pairwise_checks, "10.2: pairwise_checks has P_SC");
  assert("P_CD" in res.pairwise_checks, "10.3: pairwise_checks has P_CD");
  assert("P_SD" in res.pairwise_checks, "10.4: pairwise_checks has P_SD");
  assert(typeof res.pairwise_checks.P_SC.relationship === "string", "10.5: P_SC relationship is string");
  assert(typeof res.pairwise_checks.P_SC.is_valid === "boolean", "10.6: P_SC is_valid is boolean");
  assert(["PASS", "REVIEW", "FAIL"].includes(res.pairwise_checks.P_SC.verdict), "10.7: P_SC verdict is valid enum");
}

// 11. Unknown / Additional Fields Rejected per additionalProperties: false
{
  // Unknown top-level field (e.g. evaluation_time injected in request body)
  const reqExtra = getBaseValidRequest();
  reqExtra.evaluation_time = currentTime - 3600.0;
  const resExtra: any = adapter.evaluateJson(reqExtra, undefined, currentTime);
  assert(resExtra.verdict === "FAIL", "11.1: Request with additional top-level field produces FAIL");
  assert(resExtra.diagnostics[0].message.includes("contains unsupported field(s): evaluation_time"), "11.2: Diagnostic lists unsupported field");

  // Unknown field in source
  const reqExtraSource = getBaseValidRequest();
  reqExtraSource.source.unexpected_field = "hack";
  const resExtraSource: any = adapter.evaluateJson(reqExtraSource, undefined, currentTime);
  assert(resExtraSource.verdict === "FAIL", "11.3: Additional field in source produces FAIL");
  assert(resExtraSource.diagnostics[0].message.includes("unsupported field(s): unexpected_field"), "11.4: Diagnostic lists unexpected_field");
}

// 12. Security Boundary: Inline evidence_records Are Strictly Rejected
{
  const reqInline = getBaseValidRequest();
  reqInline.evidence_records = [
    {
      evidence_id: "ev-sensor-100",
      domain: "thermal_control",
      epistemic_status: "FACT",
      timestamp_sec: currentTime - 10.0,
      payload_hash: "sha256-hash-ok",
    },
  ];

  const resInline: any = adapter.evaluateJson(reqInline, undefined, currentTime);
  assert(resInline.verdict === "FAIL", "12.1: Inline evidence_records produces FAIL");
  assert(resInline.diagnostics.some((d: any) => d.code === "UNTRUSTED_EVIDENCE_SOURCE"), "12.2: Emits UNTRUSTED_EVIDENCE_SOURCE");
  assert(resInline.diagnostics[0].field_name === "evidence_records", "12.3: field_name is evidence_records");

  // If request_id is not a string, falls back to "untrusted_evidence_request"
  reqInline.request_id = 42;
  const resInlineBadId: any = adapter.evaluateJson(reqInline, undefined, currentTime);
  assert(resInlineBadId.request_id === "untrusted_evidence_request", "12.4: Untrusted evidence with bad id falls back to untrusted_evidence_request");
}

// 13. Cross-Validation: Parity with Python Test Vectors
{
  // 13a: Stale evidence -> REVIEW
  const reqStale = getBaseValidRequest();
  reqStale.source.timestamp_sec = currentTime - 1000.0;
  const staleRegistry = new InMemoryEvidenceRegistry();
  staleRegistry.register({
    evidence_id: "ev-sensor-100",
    domain: "thermal_control",
    epistemic_status: "FACT",
    timestamp_sec: currentTime - 1000.0,
    payload_hash: "sha256-hash-ok",
  });
  const resStale: any = adapter.evaluateJson(reqStale, staleRegistry, currentTime);
  assert(resStale.verdict === "REVIEW", "13.1: Stale evidence evaluates to REVIEW");
  assert(resStale.diagnostics.some((d: any) => d.code === "TEMPORAL_STALE"), "13.2: Emits TEMPORAL_STALE");
  assert(resStale.diagnostics.some((d: any) => d.severity === "WARNING"), "13.3: Emits WARNING severity");

  // 13b: Protected parameter mutation -> FAIL
  const reqProtected = getBaseValidRequest();
  reqProtected.dissipate.side_effects = ["emergency_valve"]; // In protected_set
  const resProtected: any = adapter.evaluateJson(reqProtected, undefined, currentTime);
  assert(resProtected.verdict === "FAIL", "13.4: Protected parameter mutation produces FAIL");
  assert(resProtected.diagnostics.some((d: any) => d.code === "STATE_PROTECTED_PARAM_MUTATED"), "13.5: Emits STATE_PROTECTED_PARAM_MUTATED");
  assert(resProtected.pairwise_checks.P_CD.is_valid === false, "13.6: P_CD is_valid is false");

  // 13c: Recursive INFERENCE chain via host registry
  const rootId = "ev-inference-root";
  const middleId = "ev-inference-middle";
  const factId = "ev-inference-fact";
  const chainReg = new InMemoryEvidenceRegistry();
  chainReg.register({
    evidence_id: rootId,
    domain: "thermal_control",
    epistemic_status: "INFERENCE",
    timestamp_sec: currentTime - 10.0,
    payload_hash: "sha256-hash-ok",
    corroborating_evidence_ids: [middleId],
  });
  chainReg.register({
    evidence_id: middleId,
    domain: "thermal_control",
    epistemic_status: "INFERENCE",
    timestamp_sec: currentTime - 20.0,
    corroborating_evidence_ids: [factId],
  });
  chainReg.register({
    evidence_id: factId,
    domain: "thermal_control",
    epistemic_status: "FACT",
    timestamp_sec: currentTime - 30.0,
  });

  const reqChain = getBaseValidRequest();
  reqChain.source.evidence_id = rootId;
  reqChain.source.epistemic_type = "INFERENCE";
  reqChain.source.corroborating_evidence_ids = [middleId];

  const resChain: any = adapter.evaluateJson(reqChain, chainReg, currentTime);
  assert(resChain.verdict === "PASS", "13.7: Recursive INFERENCE chain evaluates to PASS");
  assert(resChain.pairwise_checks.P_SC.is_valid === true, "13.8: P_SC is valid for recursive chain");
}

console.log(`\nResults: ${passedCount} passed, ${failedCount} failed.`);
if (failedCount > 0) {
  process.exit(1);
} else {
  console.log("ALL STEP 4 JSON ADAPTER TESTS PASSED PERFECTLY!");
}
